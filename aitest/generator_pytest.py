# -*- coding: utf-8 -*-
"""pytest 脚本生成器：把已评审的用例渲染成可运行的测试骨架。

对应 skills/api-test-skill.md 的「阶段三：代码编写」。
生成结果刻意保持「骨架」定位：请求调用留了清晰的 TODO 断点，
因为不同接口的客户端方法名需要人确认，模型不该直接改业务客户端。
"""
from __future__ import annotations

import os
import re
from typing import Dict, List, Sequence

from aitest.models import TestCase

HEADER = '''# -*- coding: utf-8 -*-
"""由 aitest 从用例文档生成的测试骨架 — 待人工补全后提交。

生成时间: {ts}
用例来源: {source}
说明: 每个测试方法上的注释标出对应用例 ID；请求调用处需按实际
      RuoyiApiClient 方法名对齐，断言与业务语义需人工复核。
"""
import pytest
import allure

from tests.core.base import BaseTest


'''

MARK_BY_PRIORITY = {"P0": "pytest.mark.critical", "P1": "pytest.mark.smoke"}


def _safe_ident(text: str) -> str:
    text = re.sub(r"[^0-9a-zA-Z_\u4e00-\u9fff]+", "_", text).strip("_")
    return text or "case"


def _ascii_ident(text: str, fallback: str) -> str:
    """生成 ASCII 标识符：只保留字母数字下划线。

    纯中文标题（如「正常场景」）会被清空，此时退回 fallback
    （调用方用用例编号作为 fallback，保证函数名稳定且可读）。
    """
    cleaned = re.sub(r"[^0-9a-zA-Z_]+", "_", text or "").strip("_").lower()
    cleaned = re.sub(r"_+", "_", cleaned)
    if len(cleaned) < 3 or cleaned.isdigit():
        return fallback
    if cleaned[0].isdigit():
        cleaned = "c" + cleaned
    return cleaned


def _func_name(case: TestCase) -> str:
    """标题去掉用例编号前缀后 ASCII 化；中文标题退回用例编号。"""
    stripped = re.sub(r"^TC-[A-Za-z]+-\d+\s*", "", case.title or "").strip()
    suffix = (case.case_id or "").rsplit("-", 1)[-1] or "x"
    base = _ascii_ident(stripped, "case_%s" % suffix)
    return "test_%s" % base


def _py_literal(value) -> str:
    """把 Python 值渲染成源码字面量（保持中文可读）。"""
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return '"%s"' % value.replace("\\", "\\\\").replace('"', '\\"')
    if isinstance(value, dict):
        inner = ", ".join('"%s": %s' % (k, _py_literal(v)) for k, v in value.items())
        return "{%s}" % inner
    if isinstance(value, (list, tuple)):
        return "[%s]" % ", ".join(_py_literal(v) for v in value)
    return repr(value)


def _group_by_endpoint(cases: Sequence[TestCase]) -> Dict[str, List[TestCase]]:
    grouped: Dict[str, List[TestCase]] = {}
    for c in cases:
        grouped.setdefault(c.endpoint, []).append(c)
    return grouped


def _class_name(endpoint: str, used: set) -> str:
    method, _, path = endpoint.partition(" ")
    parts = [p for p in re.split(r"[/_\-{}.]+", path) if p and not p.startswith("}")]
    base = "Test" + "".join(p[:1].upper() + p[1:] for p in (parts[-3:] or ["Api"]))
    base = re.sub(r"[^0-9a-zA-Z]", "", base) or "TestApi"
    name, i = base, 2
    while name in used:
        name = "%s%d" % (base, i)
        i += 1
    used.add(name)
    return name


def render_module(cases: Sequence[TestCase], module: str,
                  source: str = "aitest AI 草稿 + 人工评审") -> str:
    from datetime import datetime
    out: List[str] = [HEADER.format(ts=datetime.now().isoformat(timespec="seconds"),
                                    source=source)]
    used_names: set = set()
    for endpoint, group in _group_by_endpoint(cases).items():
        method = endpoint.split(" ")[0]
        cls = _class_name(endpoint, used_names)
        out.append('@allure.feature("%s")' % module)
        out.append('class %s(BaseTest):' % cls)
        out.append('    """%s"""' % endpoint)
        out.append("")
        seen_funcs: Dict[str, int] = {}
        for case in group:
            fn = _func_name(case)
            if fn in seen_funcs:
                seen_funcs[fn] += 1
                fn = "%s_%d" % (fn, seen_funcs[fn])
            else:
                seen_funcs[fn] = 1

            out.append('    @allure.title("%s")' % case.title.replace('"', "'"))
            out.append('    @allure.story("%s")' % (case.case_type))
            mark = MARK_BY_PRIORITY.get(case.priority)
            if mark:
                out.append("    @%s" % mark)
            out.append("    def %s(self):" % fn)
            out.append('        """%s: %s"""' % (case.case_id, case.title))
            if case.precondition:
                out.append("        # 前置条件: %s" % case.precondition)
            out.append("        # TODO 按实际客户端方法名对齐请求调用")
            out.append("        # 请求数据: %s" % _py_literal(case.request_data))
            out.append("        resp = None  # e.g. self.client.get_user_list(params=...)")
            out.append("")
            out.append('        with allure.step("发送请求"):')
            out.append("            pass  # 调用接口")
            out.append("")
            out.append('        with allure.step("校验响应"):')
            out.append("            self.assert_http_ok(resp) if resp is not None else None")
            if case.expected:
                out.append("            # 预期: %s" % case.expected.replace("\n", " "))
            for a in case.assertions:
                out.append("            # 断言: %s" % a.replace("\n", " "))
            out.append("")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_module(cases: Sequence[TestCase], module: str, path: str,
                 source: str = "aitest AI 草稿 + 人工评审") -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_module(cases, module, source))
    return path


def render_all(cases: Sequence[TestCase], out_dir: str,
               source: str = "aitest AI 草稿 + 人工评审") -> List[str]:
    """按模块生成多个文件，返回写出的路径列表。"""
    by_module: Dict[str, List[TestCase]] = {}
    for c in cases:
        by_module.setdefault(c.module or "generated", []).append(c)
    written: List[str] = []
    for module, group in sorted(by_module.items()):
        path = os.path.join(out_dir, "test_%s_ai.py" % _ascii_ident(module, "module"))
        written.append(write_module(group, module, path, source))
    return written
