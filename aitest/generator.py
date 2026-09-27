# -*- coding: utf-8 -*-
"""用例生成器：接口元数据 → AI 草稿 → 规则校验/去重 → 最终用例。

对应 skills/api-test-skill.md 的「阶段二：用例文档」，
把原来靠人工执行的批量生成变成可重复运行的流水线。
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence

from aitest import case_rules
from aitest.knowledge import KnowledgeBase, default_knowledge_base
from aitest.llm import LLMProvider, extract_json, get_provider
from aitest.models import Endpoint, TestCase
from aitest.prompt_builder import build_prompt

# 模块路径 → 用例 ID 缩写（与 skill 文档中的缩写表对齐）
MODULE_ABBR = {
    "auth": "AUTH", "system": "SYS", "monitor": "MON", "tool": "TOOL",
    "login": "LOGIN", "user": "USER", "role": "ROLE", "menu": "MENU",
    "dept": "DEPT", "post": "POST", "dict": "DICT", "config": "CONFIG",
    "notice": "NOTICE", "job": "JOB", "cache": "CACHE", "server": "SERVER",
    "online": "ONLINE", "operlog": "OPERLOG", "logininfor": "LOGININFO",
}


def module_abbr(module: str) -> str:
    return MODULE_ABBR.get(module.lower(), module.upper()[:6] or "GEN")


@dataclass
class GenerationStats:
    """一次生成的可核对统计（替代拍脑袋的百分比）。"""

    endpoints_total: int = 0
    endpoints_processed: int = 0
    cases_generated: int = 0
    cases_valid: int = 0
    cases_invalid: int = 0
    cases_duplicated: int = 0
    cases_final: int = 0
    llm_calls: int = 0
    llm_failures: int = 0
    provider: str = ""
    duration_sec: float = 0.0
    # token 用量（provider 支持时记录，用于回答「跑一次多少钱」）
    prompt_tokens: int = 0
    completion_tokens: int = 0
    invalid_reasons: Dict[str, int] = field(default_factory=dict)
    files_written: List[str] = field(default_factory=list)
    # 模型彻底失败（重试后仍拿不到 JSON）的接口，必须留下接口名而不是只留计数，
    # 否则「哪个接口没生成」只能靠人工比对覆盖度报告反推
    endpoints_failed: List[str] = field(default_factory=list)
    endpoint_failure_reasons: Dict[str, str] = field(default_factory=dict)

    @property
    def usable_rate(self) -> float:
        """AI 初稿可用率 = 通过校验的草稿 / 生成总数。"""
        return (self.cases_valid / self.cases_generated * 100.0) if self.cases_generated else 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = dict(self.__dict__)
        d["usable_rate"] = round(self.usable_rate, 1)
        return d

    def summary(self) -> str:
        text = (
            "接口 %d 个，处理 %d 个；AI 草稿 %d 条（可用 %d / 不合格 %d / 去重 %d），"
            "最终用例 %d 条；模型调用 %d 次（失败 %d）；初稿可用率 %.1f%%；耗时 %.1fs"
            % (self.endpoints_total, self.endpoints_processed, self.cases_generated,
               self.cases_valid, self.cases_invalid, self.cases_duplicated,
               self.cases_final, self.llm_calls, self.llm_failures,
               self.usable_rate, self.duration_sec)
        )
        if self.endpoints_failed:
            text += "；未生成用例的接口 %d 个，需人工补写" % len(self.endpoints_failed)
        if self.prompt_tokens or self.completion_tokens:
            text += "；token 输入 %d / 输出 %d" % (self.prompt_tokens,
                                                  self.completion_tokens)
        return text


class CaseGenerator:
    """把接口清单批量转成用例。"""

    def __init__(self,
                 provider: Optional[LLMProvider] = None,
                 knowledge: Optional[KnowledgeBase] = None,
                 max_cases_per_endpoint: int = 8,
                 retries: int = 1,
                 include_fewshot: bool = True,
                 extra_rules: Sequence[str] = ()):
        self.provider = provider or get_provider(prefer="auto")
        self.knowledge = knowledge if knowledge is not None else default_knowledge_base()
        self.max_cases_per_endpoint = max_cases_per_endpoint
        self.retries = retries
        self.include_fewshot = include_fewshot
        self.extra_rules = tuple(extra_rules)

    # ------------------------------------------------------------------
    def generate_for_endpoint(self, endpoint: Endpoint,
                              stats: GenerationStats) -> List[TestCase]:
        parts = build_prompt(endpoint, self.knowledge,
                             include_fewshot=self.include_fewshot,
                             extra_rules=self.extra_rules)
        payload = None
        last_err = ""
        for attempt in range(self.retries + 1):
            stats.llm_calls += 1
            try:
                raw = self.provider.complete(parts.system, parts.user)
                payload = extract_json(raw)
                break
            except Exception as e:            # 网络异常 / JSON 解析失败都重试一次
                last_err = str(e)
                stats.llm_failures += 1
                payload = None
        if payload is None:
            # 记下具体是哪个接口失败、失败原因是什么，而不只是加一个计数：
            # 否则「哪些接口需要人工补写」只能靠人工比对覆盖度报告反推
            stats.endpoints_failed.append(endpoint.key)
            stats.endpoint_failure_reasons[endpoint.key] = last_err[:160]
            stats.invalid_reasons["llm_failed"] = stats.invalid_reasons.get("llm_failed", 0) + 1
            return []

        raw_cases = payload.get("cases") or []
        if not isinstance(raw_cases, list):
            stats.llm_failures += 1
            return []

        out: List[TestCase] = []
        for rc in raw_cases[: self.max_cases_per_endpoint]:
            if not isinstance(rc, dict):
                continue
            case = TestCase(
                case_id=rc.get("case_id") or "",
                title=str(rc.get("title") or "")[:120],
                endpoint=endpoint.key,
                case_type=str(rc.get("case_type") or "normal"),
                priority=str(rc.get("priority") or "P1"),
                precondition=str(rc.get("precondition") or ""),
                steps=[str(s) for s in (rc.get("steps") or [])],
                request_data=rc.get("request_data") or {},
                expected=str(rc.get("expected") or ""),
                assertions=[str(a) for a in (rc.get("assertions") or [])],
                source="ai",
                module=endpoint.module,
            )
            stats.cases_generated += 1
            # 生成阶段不校验 case_id：ID 在去重后由 renumber() 统一分配
            problems = case_rules.validate_case(case, require_case_id=False)
            if problems:
                stats.cases_invalid += 1
                case.diagnostics.extend(problems)
                for p in problems:
                    key = p.split(":")[0]
                    stats.invalid_reasons[key] = stats.invalid_reasons.get(key, 0) + 1
                continue
            stats.cases_valid += 1
            out.append(case)
        return out

    # ------------------------------------------------------------------
    def generate(self, endpoints: Sequence[Endpoint],
                 limit: Optional[int] = None) -> tuple[List[TestCase], GenerationStats]:
        import time
        t0 = time.time()
        stats = GenerationStats(endpoints_total=len(endpoints),
                                provider=getattr(self.provider, "name", "unknown"))

        targets = list(endpoints)[:limit] if limit else list(endpoints)
        collected: List[TestCase] = []
        for ep in targets:
            collected.extend(self.generate_for_endpoint(ep, stats))
            stats.endpoints_processed += 1

        # provider 支持用量统计时（DeepSeek / Claude）把 token 消耗带进报告
        usage = getattr(self.provider, "usage", None) or {}
        stats.prompt_tokens = int(usage.get("prompt_tokens") or 0)
        stats.completion_tokens = int(usage.get("completion_tokens") or 0)

        kept, dropped = case_rules.dedupe(collected)
        stats.cases_duplicated = len(dropped)
        for c in kept:
            c.source = "ai"

        # 按模块分组重新编号，保持 TC-XXX-NNN 连续
        grouped: Dict[str, List[TestCase]] = {}
        for c in kept:
            grouped.setdefault(c.module, []).append(c)
        final: List[TestCase] = []
        for mod, cases in grouped.items():
            cases.sort(key=lambda c: (c.priority, c.case_type, c.title))
            final.extend(case_rules.renumber(cases, module_abbr(mod)))

        stats.cases_final = len(final)
        stats.duration_sec = round(time.time() - t0, 2)
        return final, stats


# ----------------------------------------------------------------------
# 落盘：JSON（机器可读）+ Markdown（人工评审用）
# ----------------------------------------------------------------------
def write_json(cases: Iterable[TestCase], path: str,
               stats: Optional[GenerationStats] = None,
               endpoints: Optional[Sequence[Endpoint]] = None) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    payload: Dict[str, Any] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "cases": [c.to_dict() for c in cases],
    }
    if stats is not None:
        payload["stats"] = stats.to_dict()
    if endpoints is not None:
        payload["coverage"] = case_rules.coverage_report(list(cases), list(endpoints))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def render_markdown(cases: Sequence[TestCase],
                    stats: Optional[GenerationStats] = None,
                    endpoints: Optional[Sequence[Endpoint]] = None) -> str:
    lines: List[str] = ["# AI 辅助生成的接口测试用例（待人工评审）", ""]
    if stats is not None:
        lines.append("> 生成统计：%s" % stats.summary())
        lines.append("")
    if endpoints is not None:
        lines.append("```")
        lines.append(case_rules.format_report(
            case_rules.coverage_report(list(cases), list(endpoints))))
        lines.append("```")
        lines.append("")
    lines.append("> 评审要点：确认断言是否匹配真实业务语义；"
                 "确认边界值是否符合接口真实约束；不合格的用例请标注后剔除。")
    lines.append("")

    current_mod = None
    for c in cases:
        if c.module != current_mod:
            current_mod = c.module
            lines.append("\n## 模块：%s\n" % current_mod)
        lines.append("### %s %s\n" % (c.case_id, c.title))
        lines.append("| 项目 | 内容 |")
        lines.append("|------|------|")
        lines.append("| 接口 | `%s` |" % c.endpoint)
        lines.append("| 类型 | %s |" % c.case_type)
        lines.append("| 优先级 | %s |" % c.priority)
        lines.append("| 前置条件 | %s |" % (c.precondition or "-"))
        lines.append("| 来源 | %s |" % c.source)
        lines.append("")
        if c.steps:
            lines.append("**测试步骤：**")
            for i, s in enumerate(c.steps, 1):
                lines.append("%d. %s" % (i, s))
            lines.append("")
        if c.request_data:
            lines.append("**测试数据：**")
            lines.append("```json")
            lines.append(json.dumps(c.request_data, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
        if c.expected:
            lines.append("**预期结果：** %s" % c.expected)
            lines.append("")
        if c.assertions:
            lines.append("**断言清单：**")
            for a in c.assertions:
                lines.append("- [ ] %s" % a)
            lines.append("")
    return "\n".join(lines) + "\n"


def write_markdown(cases: Sequence[TestCase], path: str,
                   stats: Optional[GenerationStats] = None,
                   endpoints: Optional[Sequence[Endpoint]] = None) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_markdown(cases, stats, endpoints))
    return path
