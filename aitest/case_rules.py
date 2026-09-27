# -*- coding: utf-8 -*-
"""用例规则层：校验、去重、覆盖度统计。

这一层是「AI 产出」与「人工评审」之间的护栏：
- :func:`validate_case` 拦住结构性不合格的 AI 草稿（缺断言、类型非法…）
- :func:`dedupe` 去掉语义重复的候选
- :func:`coverage_report` 给出可核对的覆盖度，替代拍脑袋的百分比
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Sequence, Tuple

from aitest.models import CASE_TYPES, PRIORITIES, Endpoint, TestCase

# 一个接口至少应覆盖的类型（对应 skill 文档的质量要求）
REQUIRED_TYPES = ("normal", "boundary", "exception")

# 断言必须命中其中之一，否则视为「假绿灯」风险用例
_MEANINGFUL_ASSERT_HINTS = (
    "code", "token", "rows", "total", "data", "status", "msg",
    "length", "type", "unique", "elapsed", "字段",
)


def validate_case(case: TestCase, require_case_id: bool = True) -> List[str]:
    """返回问题列表；空列表表示通过。

    ``require_case_id=False`` 用于生成阶段：此时用例 ID 由
    :func:`renumber` 在去重后统一分配，不应因「缺 ID」把草稿判为不合格。
    """
    problems: List[str] = []
    if require_case_id and not case.case_id:
        problems.append("缺少用例 ID")
    if not case.title:
        problems.append("缺少用例标题")
    if not case.endpoint:
        problems.append("缺少接口标识")
    if case.case_type not in CASE_TYPES:
        problems.append("用例类型非法: %s" % case.case_type)
    if case.priority not in PRIORITIES:
        problems.append("优先级非法: %s" % case.priority)
    if not case.expected:
        problems.append("缺少预期结果")
    if not case.assertions:
        problems.append("缺少断言清单")
    else:
        joined = " ".join(case.assertions).lower()
        if not any(h.lower() in joined for h in _MEANINGFUL_ASSERT_HINTS):
            problems.append("断言未涉及业务字段，存在假绿灯风险")
    if case.case_type == "exception" and not case.request_data:
        problems.append("异常用例未给出具体请求数据")
    return problems


def dedupe(cases: Sequence[TestCase]) -> Tuple[List[TestCase], List[TestCase]]:
    """按语义指纹去重。

    返回 ``(保留, 剔除)``；被剔除的用例会带上 diagnostics 说明原因。
    """
    seen: Dict[str, TestCase] = {}
    kept: List[TestCase] = []
    dropped: List[TestCase] = []
    for c in cases:
        sig = c.signature()
        if sig in seen:
            c.diagnostics.append("与 %s 语义重复，已剔除" % seen[sig].case_id)
            dropped.append(c)
            continue
        seen[sig] = c
        kept.append(c)
    return kept, dropped


def renumber(cases: Iterable[TestCase], module_abbr: str) -> List[TestCase]:
    """按模块+顺序重排用例 ID，保证 ``TC-XXX-NNN`` 连续编号。"""
    out: List[TestCase] = []
    for i, c in enumerate(cases, start=1):
        c.case_id = "TC-%s-%03d" % (module_abbr.upper(), i)
        out.append(c)
    return out


def coverage_report(cases: Sequence[TestCase],
                    endpoints: Sequence[Endpoint]) -> Dict[str, object]:
    """生成可核对的覆盖度报告。"""
    by_endpoint: Dict[str, List[TestCase]] = defaultdict(list)
    for c in cases:
        by_endpoint[c.endpoint].append(c)

    covered = [e for e in endpoints if by_endpoint.get(e.key)]
    uncovered = [e for e in endpoints if not by_endpoint.get(e.key)]

    type_counter: Counter = Counter(c.case_type for c in cases)
    prio_counter: Counter = Counter(c.priority for c in cases)

    missing_required: Dict[str, List[str]] = {}
    for e in endpoints:
        have = {c.case_type for c in by_endpoint.get(e.key, [])}
        lack = [t for t in REQUIRED_TYPES if t not in have]
        if lack:
            missing_required[e.key] = lack

    auth_endpoints = [e for e in endpoints if e.need_auth]
    auth_covered = [e for e in auth_endpoints if by_endpoint.get(e.key)]
    auth_missing = [e.key for e in auth_endpoints
                    if "auth" not in {c.case_type for c in by_endpoint.get(e.key, [])}]

    total = len(endpoints)
    return {
        "endpoint_total": total,
        "endpoint_covered": len(covered),
        "endpoint_uncovered": [e.key for e in uncovered],
        "endpoint_coverage": (len(covered) / total * 100.0) if total else 0.0,
        "case_total": len(cases),
        "case_by_type": dict(type_counter),
        "case_by_priority": dict(prio_counter),
        "endpoints_missing_required_types": missing_required,
        "auth_endpoint_total": len(auth_endpoints),
        "auth_endpoint_covered": len(auth_covered),
        "auth_endpoints_missing_auth_case": auth_missing,
    }


def format_report(report: Dict[str, object]) -> str:
    """把覆盖度报告格式化为便于贴进 README / 提交信息的多行文本。"""
    lines = [
        "接口覆盖: %d/%d (%.1f%%)"
        % (report["endpoint_covered"], report["endpoint_total"],
           report["endpoint_coverage"]),
        "用例总数: %d" % report["case_total"],
        "按类型  : %s" % (report["case_by_type"] or "-"),
        "按优先级: %s" % (report["case_by_priority"] or "-"),
    ]
    if report["endpoint_uncovered"]:
        lines.append("未覆盖接口(%d): %s"
                     % (len(report["endpoint_uncovered"]),
                        ", ".join(report["endpoint_uncovered"][:8])))
    missing = report["endpoints_missing_required_types"]
    if missing:
        lines.append("缺少必需场景的接口(%d):" % len(missing))
        for k, v in list(missing.items())[:8]:
            lines.append("   - %s 缺 %s" % (k, "/".join(v)))
    if report["auth_endpoint_total"]:
        lines.append("鉴权接口权限用例缺失(%d): %s"
                     % (len(report["auth_endpoints_missing_auth_case"]),
                        ", ".join(report["auth_endpoints_missing_auth_case"][:6])))
    return "\n".join(lines)
