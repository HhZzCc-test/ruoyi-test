# -*- coding: utf-8 -*-
"""命令行入口。

    python -m aitest parse    --spec specs/ruoyi.json
    python -m aitest generate --spec specs/ruoyi.json --out-dir reports/ai
    python -m aitest generate --spec specs/ruoyi.json --show-prompt --limit 1
    python -m aitest scaffold --cases reports/ai/cases.json --out-dir tests/ai
    python -m aitest analyze  --junit allure-results/report.xml --out reports/ai/failure_report.md
    python -m aitest report   --cases reports/ai/cases.json --spec specs/ruoyi.json

`--show-prompt` 是干跑模式：只打印最终提示词全文，不调用模型；
`--extra-rules` 可给单词生成追加「额外要求」（如「必须覆盖并发场景」）。
无 API Key 时自动降级为 mock provider，整条流水线仍可跑通（便于离线与 CI）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

from aitest import __version__, case_rules
from aitest.analyzer import FailureAnalyzer, render_report
from aitest.generator import CaseGenerator, write_json, write_markdown
from aitest.generator_pytest import render_all
from aitest.knowledge import KnowledgeBase, default_knowledge_base
from aitest.llm import get_provider
from aitest.models import TestCase
from aitest.prompt_builder import build_prompt
from aitest.swagger_parser import load_spec, parse_swagger


def _load_endpoints(spec_path: str):
    spec = load_spec(spec_path)
    return parse_swagger(spec, spec_source=spec_path)


def _print_endpoints(endpoints) -> None:
    print("接口总数: %d" % len(endpoints))
    by_module: Dict[str, int] = {}
    for e in endpoints:
        by_module[e.module] = by_module.get(e.module, 0) + 1
    print("按模块  : %s" % ", ".join("%s=%d" % kv for kv in sorted(by_module.items())))
    auth = sum(1 for e in endpoints if e.need_auth)
    high = sum(1 for e in endpoints if e.risk == "high")
    print("需鉴权  : %d    高风险(写/删): %d" % (auth, high))
    print("")
    shown = 0
    for e in endpoints:
        params = len(e.params)
        req = sum(1 for p in e.params if p.required)
        print("  %-7s %-42s 参数 %2d(必填 %2d) %s%s"
              % (e.method, e.path, params, req,
                 "[需鉴权]" if e.need_auth else "",
                 "[高风险]" if e.risk == "high" else ""))
        shown += 1
        if shown >= 40:
            print("  ... 其余 %d 个接口省略" % (len(endpoints) - shown))
            break


def cmd_parse(args) -> int:
    endpoints = _load_endpoints(args.spec)
    _print_endpoints(endpoints)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump([e.__dict__ for e in endpoints], f, ensure_ascii=False,
                      indent=2, default=str)
        print("\n接口清单已写入: %s" % args.out)
    return 0


def _preview_prompts(endpoints, kb: KnowledgeBase, include_fewshot: bool,
                     extra_rules, limit=None) -> None:
    """干跑：打印将要发给模型的提示词，不调用模型、不产生任何文件。

    调提示词时最需要看的就是最终 system / user 全文，
    但直接跑 generate 会白烧一次模型调用，所以单独给一个干跑入口。
    """
    targets = list(endpoints)[:limit] if limit else list(endpoints)
    for ep in targets:
        parts = build_prompt(ep, kb, include_fewshot=include_fewshot,
                             extra_rules=extra_rules)
        print("=" * 62)
        print("接口: %s    知识库命中: %d 条" % (ep.key, parts.knowledge_hits))
        print("-" * 62)
        print("[system]\n%s" % parts.system)
        print("-" * 62)
        print("[user]\n%s" % parts.user)
    print("\n共 %d 个接口。--show-prompt 为干跑模式：未调用模型、未生成用例。" % len(targets))


def cmd_generate(args) -> int:
    endpoints = _load_endpoints(args.spec)
    kb: KnowledgeBase = (KnowledgeBase.from_markdown(args.knowledge)
                         if args.knowledge else default_knowledge_base())
    print("知识库: %s" % kb.stats())

    extra_rules = tuple(args.extra_rules or ())
    if args.show_prompt:
        _preview_prompts(endpoints, kb, include_fewshot=not args.no_fewshot,
                         extra_rules=extra_rules, limit=args.limit)
        return 0

    provider = get_provider(endpoints, prefer=args.provider, model=args.model,
                            base_url=args.base_url)
    print("模型实现: %s" % provider.name
          + ("  （未检测到 DEEPSEEK_API_KEY / ANTHROPIC_API_KEY，使用离线 mock）"
             if provider.name == "mock" else ""))

    gen = CaseGenerator(provider=provider, knowledge=kb,
                        max_cases_per_endpoint=args.max_cases,
                        retries=args.retries,
                        include_fewshot=not args.no_fewshot,
                        extra_rules=extra_rules,
                        max_tokens=args.max_tokens)
    cases, stats = gen.generate(endpoints, limit=args.limit)

    report = case_rules.coverage_report(cases, endpoints)
    print("\n" + stats.summary())
    print("-" * 62)
    print(case_rules.format_report(report))
    if stats.endpoints_failed:
        print("-" * 62)
        print("以下接口未生成用例，需人工补写：")
        for key in stats.endpoints_failed:
            print("   - %s  (%s)" % (key, stats.endpoint_failure_reasons.get(key, "原因未知")))

    if args.out_dir:
        json_path = os.path.join(args.out_dir, "cases.json")
        md_path = os.path.join(args.out_dir, "cases.md")
        write_json(cases, json_path, stats, endpoints)
        write_markdown(cases, md_path, stats, endpoints)
        print("\n用例(JSON) : %s" % json_path)
        print("用例(MD)   : %s   <- 人工评审用" % md_path)
        if args.scaffold_dir:
            written = render_all(cases, args.scaffold_dir)
            print("测试骨架   : %s" % ", ".join(written))
    return 0


def cmd_scaffold(args) -> int:
    with open(args.cases, "r", encoding="utf-8") as f:
        payload = json.load(f)
    raw = payload.get("cases", payload if isinstance(payload, list) else [])
    cases = [TestCase.from_dict(d) for d in raw]
    cases = [c for c in cases if c.is_wellformed()]
    print("载入用例: %d 条" % len(cases))
    written = render_all(cases, args.out_dir, source=args.source)
    for p in written:
        print("  写出 %s" % p)
    print("\n提示：生成的是骨架，请求调用处需按实际 RuoyiApiClient 方法名对齐后再提交。")
    return 0


def _parse_junit(path: str) -> List[Dict[str, Any]]:
    """从 pytest 的 junit xml 中提取失败用例信息。"""
    tree = ET.parse(path)
    root = tree.getroot()
    cases = root.iter("testcase")
    failures: List[Dict[str, Any]] = []
    for tc in cases:
        bad = tc.find("failure")
        if bad is None:
            bad = tc.find("error")
        if bad is None:
            continue
        text = (bad.text or "") + " " + (bad.get("message") or "")
        status = None
        import re
        m = re.search(r"HTTP status:\s*(\d{3})", text)
        if m:
            status = int(m.group(1))
        failures.append({
            "test": "%s::%s" % (tc.get("classname", ""), tc.get("name", "")),
            "traceback": text,
            "status_code": status,
            "assertion": (bad.get("message") or "")[:300],
        })
    return failures


def cmd_analyze(args) -> int:
    failures = _parse_junit(args.junit)
    print("从 %s 解析到失败用例: %d 条" % (args.junit, len(failures)))
    if not failures:
        print("没有失败用例，无需归因。")
        return 0
    analyzer = FailureAnalyzer(provider=get_provider(prefer=args.provider,
                                                     model=args.model,
                                                     base_url=args.base_url))
    report = analyzer.analyze(failures)
    text = render_report(report)
    print("\n" + "-" * 62)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("归因报告已写入: %s" % args.out)
    return 0


def cmd_report(args) -> int:
    with open(args.cases, "r", encoding="utf-8") as f:
        payload = json.load(f)
    raw = payload.get("cases", [])
    cases = [TestCase.from_dict(d) for d in raw]
    endpoints = _load_endpoints(args.spec)
    report = case_rules.coverage_report(cases, endpoints)
    print(case_rules.format_report(report))
    if payload.get("stats"):
        print("\n生成统计: %s" % json.dumps(payload["stats"], ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="aitest",
        description="AI 辅助接口测试用例生成与失败归因（对应 skills/api-test-skill.md 的工程化实现）")
    p.add_argument("--version", action="version", version="aitest %s" % __version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("parse", help="解析 Swagger/OpenAPI，输出接口清单")
    a.add_argument("--spec", required=True)
    a.add_argument("--out", default=None, help="接口清单 JSON 输出路径")
    a.set_defaults(func=cmd_parse)

    b = sub.add_parser("generate", help="AI 生成用例草稿（含规则校验、去重、覆盖度）")
    b.add_argument("--spec", required=True)
    b.add_argument("--knowledge", default=None, help="业务知识库 Markdown（缺省用内置）")
    b.add_argument("--out-dir", default="reports/ai")
    b.add_argument("--scaffold-dir", default=None, help="同时生成 pytest 骨架到该目录")
    b.add_argument("--provider", default="auto",
                   choices=["auto", "deepseek", "claude", "mock"])
    b.add_argument("--model", default=None)
    b.add_argument("--base-url", default=None,
                   help="自定义模型网关地址（第三方 OpenAI 兼容网关，如硅基流动/火山方舟）")
    b.add_argument("--max-cases", type=int, default=8)
    b.add_argument("--limit", type=int, default=None, help="只处理前 N 个接口（省调用）")
    b.add_argument("--retries", type=int, default=1)
    b.add_argument("--max-tokens", type=int, default=None,
                   help="单次生成的最大输出 token（默认 8000；截断时会自动放大预算重试）")
    b.add_argument("--no-fewshot", action="store_true")
    b.add_argument("--show-prompt", action="store_true",
                   help="干跑：只打印将要发给模型的提示词全文，不调用模型")
    b.add_argument("--extra-rules", action="append", default=[],
                   help="追加到提示词「额外要求」段的约束，可重复使用")
    b.set_defaults(func=cmd_generate)

    c = sub.add_parser("scaffold", help="由已评审用例生成 pytest 骨架")
    c.add_argument("--cases", required=True)
    c.add_argument("--out-dir", required=True)
    c.add_argument("--source", default="aitest AI 草稿 + 人工评审")
    c.set_defaults(func=cmd_scaffold)

    d = sub.add_parser("analyze", help="对失败用例做归因（规则预筛 + 模型）")
    d.add_argument("--junit", required=True, help="pytest 的 junit xml 结果文件")
    d.add_argument("--out", default=None)
    d.add_argument("--provider", default="auto",
                   choices=["auto", "deepseek", "claude", "mock"])
    d.add_argument("--model", default=None)
    d.add_argument("--base-url", default=None, help="自定义模型网关地址")
    d.set_defaults(func=cmd_analyze)

    e = sub.add_parser("report", help="输出覆盖度报告")
    e.add_argument("--cases", required=True)
    e.add_argument("--spec", required=True)
    e.set_defaults(func=cmd_report)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
