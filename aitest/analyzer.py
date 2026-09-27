# -*- coding: utf-8 -*-
"""失败归因分析：把 pytest 失败信息 + 接口响应交给大模型做分类。

对应简历里的「把 traceback 与接口响应交 AI 定位，再由我用日志复现确认」。

产出三类结论（问题归属是分析的**假设**，需人工用日志复现确认）：
    case       —— 用例本身写错（断言不匹配、数据不当、依赖顺序）
    env        —— 环境问题（服务未启动、Redis 未就绪、Token 失效）
    product    —— 真实缺陷（业务返回与需求不符）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from aitest.llm import LLMProvider, extract_json, get_provider

ISSUE_TYPES = ("case", "env", "product", "unknown")

SYSTEM = """你是资深测试工程师，负责对失败的自动化用例做归因。
必须区分三类原因，并给出可执行的下一步动作：
- case：用例自身问题（断言写错、测试数据不当、依赖了执行顺序、定位方式错误）
- env：环境问题（被测服务未启动、Redis/数据库不可用、Token 失效、网络抖动、端口占用）
- product：被测系统的真实缺陷（业务返回与需求/文档不符）
结论是**假设**，必须说明依据（traceback 关键行、状态码、业务 code、msg 内容），
并给出验证方式。不确定时给出 unknown 而不是猜。
只输出 JSON，不要 Markdown 代码块。"""

CONTRACT = """输出结构：
{
  "items": [
    {
      "test": "测试方法名或用例ID",
      "issue": "case | env | product | unknown",
      "confidence": "high | medium | low",
      "reason": "一句话结论",
      "evidence": ["依据1", "依据2"],
      "suggestion": "下一步动作",
      "need_rerun": true
    }
  ],
  "summary": {"case": 0, "env": 0, "product": 0, "unknown": 0}
}"""

# 环境问题的强特征：命中即可直接判定，无需调用模型
_ENV_PATTERNS = [
    (r"ConnectionRefusedError|Max retries exceeded|NewConnectionError|"
     r"Failed to establish a new connection", "被测服务未启动或端口不可达"),
    (r"redis\.exceptions\.\w+|ConnectionError.*redis", "Redis 不可用"),
    (r"Timeout|ReadTimeout|ConnectTimeout", "请求超时（网络或服务响应慢）"),
    (r"selenium\.common\.exceptions\.(WebDriverException|SessionNotCreatedException|"
     r"NoSuchDriverException)", "浏览器/驱动环境问题"),
    (r"OperationalError|Lost connection to MySQL", "数据库连接异常"),
]


@dataclass
class FailureItem:
    test: str
    issue: str = "unknown"
    confidence: str = "low"
    reason: str = ""
    evidence: List[str] = field(default_factory=list)
    suggestion: str = ""
    need_rerun: bool = False
    source: str = "rule"          # rule | ai

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


def rule_prefilter(test_name: str, tb_text: str,
                   status_code: Optional[int] = None) -> Optional[FailureItem]:
    """先用规则拦掉一眼就是环境问题的失败，省掉模型调用。"""
    for pat, reason in _ENV_PATTERNS:
        m = re.search(pat, tb_text, re.I)
        if m:
            return FailureItem(
                test=test_name, issue="env", confidence="high", reason=reason,
                evidence=["traceback 命中: %s" % m.group(0)[:80]],
                suggestion="确认被测服务 / Redis / 驱动状态后重跑，不要先改用例",
                need_rerun=True, source="rule")
    if status_code in (401, 403) and "assert" in tb_text.lower():
        return FailureItem(
            test=test_name, issue="env", confidence="medium",
            reason="鉴权失败，可能是 Token 失效或权限配置变化",
            evidence=["HTTP %d" % status_code],
            suggestion="检查登录流程与 Token 有效期；确认账号权限未被改动",
            need_rerun=True, source="rule")
    return None


def build_user_prompt(items: Sequence[Dict[str, Any]]) -> str:
    blocks = ["## 待归因的失败用例\n"]
    for i, it in enumerate(items, 1):
        blocks.append("### %d) %s" % (i, it.get("test", "?")))
        if it.get("status_code") is not None:
            blocks.append("HTTP 状态码: %s" % it["status_code"])
        if it.get("assertion"):
            blocks.append("断言信息: %s" % str(it["assertion"])[:300])
        if it.get("response"):
            blocks.append("响应体(截断): %s" % str(it["response"])[:500])
        tb = str(it.get("traceback") or "")
        blocks.append("traceback(截断):\n```\n%s\n```" % tb[-1200:])
        blocks.append("")
    blocks.append("## 输出要求\n\n" + CONTRACT)
    return "\n".join(blocks)


class FailureAnalyzer:
    """失败归因器。"""

    def __init__(self, provider: Optional[LLMProvider] = None,
                 max_items_per_call: int = 5):
        self.provider = provider or get_provider(prefer="auto")
        self.max_items_per_call = max_items_per_call

    # ------------------------------------------------------------------
    def analyze(self, failures: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """failures: [{test, traceback, status_code?, response?, assertion?}]"""
        results: List[FailureItem] = []
        pending: List[Dict[str, Any]] = []

        for f in failures:
            hit = rule_prefilter(str(f.get("test", "?")),
                                 str(f.get("traceback") or ""),
                                 f.get("status_code"))
            if hit is not None:
                results.append(hit)
            else:
                pending.append(f)

        ai_used = False
        for chunk_start in range(0, len(pending), self.max_items_per_call):
            chunk = pending[chunk_start:chunk_start + self.max_items_per_call]
            try:
                raw = self.provider.complete(
                    SYSTEM, build_user_prompt(chunk), max_tokens=3000)
                # 复用 llm.extract_json：与生成链路用同一套容错（代码块 / 前后解释）
                payload = extract_json(raw)
            except Exception as e:
                for f in chunk:
                    results.append(FailureItem(
                        test=str(f.get("test", "?")), issue="unknown", confidence="low",
                        reason="AI 归因不可用: %s" % str(e)[:80],
                        suggestion="人工排查；确认 ANTHROPIC_API_KEY 或改用 --provider mock",
                        source="rule"))
                continue
            ai_used = True
            returned = payload.get("items") or []
            by_test = {str(it.get("test")): it for it in returned if isinstance(it, dict)}
            for f in chunk:
                it = by_test.get(str(f.get("test")))
                if not it:
                    results.append(FailureItem(
                        test=str(f.get("test", "?")), issue="unknown", source="ai",
                        reason="模型未返回该用例的归因"))
                    continue
                issue = str(it.get("issue") or "unknown")
                results.append(FailureItem(
                    test=str(f.get("test", "?")),
                    issue=issue if issue in ISSUE_TYPES else "unknown",
                    confidence=str(it.get("confidence") or "low"),
                    reason=str(it.get("reason") or ""),
                    evidence=[str(x) for x in (it.get("evidence") or [])],
                    suggestion=str(it.get("suggestion") or ""),
                    need_rerun=bool(it.get("need_rerun")),
                    source="ai"))

        summary = {k: 0 for k in ISSUE_TYPES}
        for r in results:
            summary[r.issue] = summary.get(r.issue, 0) + 1
        return {
            "provider": getattr(self.provider, "name", "unknown"),
            "ai_used": ai_used,
            "total": len(results),
            "summary": summary,
            "items": [r.to_dict() for r in results],
        }


def render_report(report: Dict[str, Any]) -> str:
    """把归因结果渲染成便于贴进缺陷单 / 日报的文本。"""
    label = {"case": "用例问题", "env": "环境问题",
             "product": "疑似真实缺陷", "unknown": "待人工确认"}
    lines = ["# 失败归因报告", "",
             "统计: " + ", ".join("%s=%d" % (label.get(k, k), v)
                                 for k, v in report.get("summary", {}).items()),
             "归因来源: %s%s" % (report.get("provider"),
                                "（规则预筛 + 模型）" if report.get("ai_used")
                                else "（仅规则预筛）"),
             ""]
    for item in report.get("items", []):
        lines.append("## %s" % item["test"])
        lines.append("- 归属: **%s**（置信度 %s，来源 %s）"
                     % (label.get(item["issue"], item["issue"]),
                        item["confidence"], item["source"]))
        if item["reason"]:
            lines.append("- 结论: %s" % item["reason"])
        for ev in item.get("evidence", []):
            lines.append("- 依据: %s" % ev)
        if item["suggestion"]:
            lines.append("- 建议: %s" % item["suggestion"])
        if item.get("need_rerun"):
            lines.append("- 处理: 先重跑确认，不要直接改用例")
        lines.append("")
    return "\n".join(lines)
