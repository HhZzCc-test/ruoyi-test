# -*- coding: utf-8 -*-
"""pytest 脚本生成器：把已评审的用例渲染成可运行的测试骨架。

对应 skills/api-test-skill.md 的「阶段三：代码编写」。
生成结果刻意保持「骨架」定位：请求调用留了清晰的 TODO 断点，
因为不同接口的客户端方法名需要人确认，模型不该直接改业务客户端。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence

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


def _restore_headers(out: List[str], I: str) -> None:
    """渲染「恢复被覆盖的请求头」代码（供正常路径与未映射路径共用）。"""
    out.append("%s# 恢复请求头" % I)
    out.append("%s_saved = locals().get('_saved_headers')" % I)
    out.append("%sif _saved:" % I)
    out.append("%s    for _k, _v in _saved.items():" % I)
    out.append("%s        if _v is None:" % I)
    out.append("%s            self.client.session.headers.pop(_k, None)" % I)
    out.append("%s        else:" % I)
    out.append("%s            self.client.session.headers[_k] = _v" % I)


def _kwarg_pairs(m: Dict[str, Any], key: str) -> List[tuple]:
    """把映射里的参数声明转成 [(客户端关键字, 用例字段名)]。

    支持两种写法：
      "args": ["username", "password"]      —— 两边同名
      "path": {"user_id": "userId"}         —— 客户端关键字 : 用例字段名
    （后者用于 client 的参数名与接口文档字段名不一致的情况，如 user_id ↔ userId）
    """
    spec = m.get(key) or []
    if isinstance(spec, dict):
        return list(spec.items())
    return [(n, n) for n in spec]


def _render_case_body(case: TestCase, mapping: Optional[Dict[str, Any]],
                      indent: str = "        ") -> List[str]:
    """渲染一个测试方法的函数体。

    ``mapping`` 为该接口对应的客户端方法映射（来自人工维护的 client map）。
    **映射不到就退回骨架 + TODO** —— 客户端方法名是项目私有约定，猜错比留空危险：
    猜错会生成「语法正确但语义错误」的代码，比一个显眼的 TODO 更容易蒙混过关。
    """
    I = indent
    m = (mapping or {}).get(case.endpoint)
    pairs_args = _kwarg_pairs(m, "args") if m else []
    pairs_path = _kwarg_pairs(m, "path") if m else []

    # 用例里声明的参数是否都齐（缺参数就不生成半截调用）
    # 注意：字段名以 @ 开头表示「运行时取值」（如 @_code），不要求用例里存在
    if m:
        declared = [f for _, f in pairs_args + pairs_path if not f.startswith("@")]
        available = set(case.request_data) | set(case.path_params)
        missing = [f for f in declared if f not in available]
        if missing:
            m = None

    out: List[str] = []
    needs_restore: List[str] = []

    # ---- 请求头覆盖：值为空字符串表示移除该请求头（如「不带 Token」）----
    # 注意：下面的恢复只在用例正常跑完时执行；断言失败或 pytest.skip 会跳过它。
    # 因此**不能依赖它来防止污染** —— 生成的测试目录必须有一个 autouse fixture，
    # 在每个用例开始前重置鉴权头（见 tests_from_ai/conftest.py 的 _reset_auth）。
    if case.header_overrides:
        out.append("%s_saved_headers = {}" % I)
        for k, v in case.header_overrides.items():
            if v == "":
                out.append('%s_saved_headers[%r] = self.client.session.headers.pop(%r, None)'
                           % (I, k, k))
            else:
                out.append('%s_saved_headers[%r] = self.client.session.headers.get(%r)'
                           % (I, k, k))
                out.append('%sself.client.session.headers[%r] = %r' % (I, k, v))
        needs_restore.append("headers")

    # ---- 运行时前置代码（如取验证码：映射表里用 pre 声明）----
    if m and not case.method_override:
        for line in m.get("pre") or []:
            out.append("%s%s" % (I, line))

    # ---- 组装调用 ----
    if m and not case.method_override:
        kw = []
        for kwname, field in pairs_args + pairs_path:
            val = case.request_data.get(field, case.path_params.get(field))
            if isinstance(val, str) and val.startswith("@"):
                # 映射表声明该参数在运行时取（值为 @变量名），不写死用例里的数据
                kw.append("%s=%s" % (kwname, val[1:]))
            elif field.startswith("@"):
                kw.append("%s=%s" % (kwname, field[1:]))
            else:
                kw.append("%s=%s" % (kwname, _py_literal(val)))
        if m.get("params"):
            declared = set(f for _, f in pairs_args + pairs_path)
            rest = {k: v for k, v in case.request_data.items() if k not in declared}
            kw.append("params=%s" % _py_literal(rest))
        out.append("%sresp = self.client.%s(%s)" % (I, m["method"], ", ".join(kw)))
    elif case.method_override:
        # 用不支持的 HTTP 方法请求同一路径（测方法不允许）
        method = case.method_override.upper()
        path = _endpoint_path(case.endpoint)
        for m0 in re.findall(r"\{(\w+)\}", path):
            val = case.path_params.get(m0, case.request_data.get(m0, 1))
            path = path.replace("{%s}" % m0, str(val))
        out.append("%s# 用 %s 方法请求（该接口只允许 %s）" % (I, method, _endpoint_method(case.endpoint)))
        out.append("%sresp = self.client.session.request("
                   "%r, self.client.base_url + %r, headers=self.client.session.headers)"
                   % (I, method, path))
    else:
        # 映射不到：**显式 skip，而不是空跑通过**
        # （早先的写法是 resp = None + if resp is not None，断言全被跳过，
        #   测试会「假装通过」—— 这正是本项目要防的假绿灯，不能自己犯）
        out.append("%s# 该接口在 client map 里没有映射，需人工按实际方法名对齐后再纳入执行" % I)
        out.append("%s# 请求数据: %s" % (I, _py_literal(case.request_data)))
        if case.path_params:
            out.append("%s# 路径参数: %s" % (I, _py_literal(case.path_params)))
        if case.method_override:
            out.append("%s# 请求方法覆盖: %s" % (I, case.method_override))
        if case.header_overrides:
            out.append("%s# 请求头覆盖: %s" % (I, _py_literal(case.header_overrides)))
        out.append('%spytest.skip("接口未在 client map 中映射（%s），需人工补齐调用")'
                   % (I, case.endpoint))
        _restore_headers(out, I)
        return out

    # ---- 断言：能机械识别的先落成代码，其余留注释 ----
    out.append("%sif resp is not None:" % I)
    body = "    "
    data_var = "_data"
    out.append("%s%sself.assert_http_ok(resp)" % (I, body))
    out.append("%s%s%s = resp.json()" % (I, body, data_var))
    recognized = 0
    for a in case.assertions:
        s = a.strip()
        if "假绿灯" in s:
            continue
        if re.search(r"业务\s*code\s*(为|等于)\s*200", s) or "业务成功" in s:
            out.append("%s%sself.assert_business_success(%s)" % (I, body, data_var))
            recognized += 1
        elif re.search(r"业务\s*code\s*(不等于|非|!=)\s*200", s) or "业务失败" in s:
            out.append("%s%sself.assert_business_error(%s)" % (I, body, data_var))
            recognized += 1
        elif "401" in s or "403" in s:
            # 若依约定：鉴权失败时 HTTP 状态码仍为 200，401/403 落在业务 code 上。
            # 两边都接受，避免把「产品约定」误判成测试失败。
            out.append("%s%sassert resp.status_code in (401, 403) or "
                       "%s.get('code') in (401, 403)   # %s"
                       % (I, body, data_var, s))
            recognized += 1
        elif "405" in s:
            out.append("%s%sassert resp.status_code == 405 or "
                       "%s.get(\"code\") != 200   # %s" % (I, body, data_var, s))
            recognized += 1
        elif "响应时间" in s:
            out.append("%s%sself.assert_response_time(resp.elapsed.total_seconds())   # %s"
                       % (I, body, s))
            recognized += 1
        else:
            out.append("%s%s# 断言（需人工确认）: %s" % (I, body, s))
    if recognized == 0:
        out.append("%s%s# 注意：本用例的断言未能自动落成代码，必须人工补齐" % (I, body))

    # ---- 恢复被覆盖的请求头 ----
    if needs_restore:
        out.append("%s# 恢复请求头" % I)
        out.append("%sfor _k, _v in _saved_headers.items():" % I)
        out.append("%s    if _v is None:" % I)
        out.append("%s        self.client.session.headers.pop(_k, None)" % I)
        out.append("%s    else:" % I)
        out.append("%s        self.client.session.headers[_k] = _v" % I)
    return out


def _endpoint_method(endpoint: str) -> str:
    return endpoint.split(" ")[0].upper()


def _endpoint_path(endpoint: str) -> str:
    return endpoint.split(" ", 1)[1] if " " in endpoint else endpoint


def load_client_map(path: str) -> Dict[str, Any]:
    """读取人工维护的「接口 → 客户端方法」映射表（JSON）。

    格式（每项均可选 args / path / params）::

        {
          "POST /login": {"method": "login",
                          "args": ["username", "password", "code", "uuid"]},
          "GET /system/user/list": {"method": "get_user_list", "params": true},
          "GET /system/user/{userId}": {"method": "get_user_by_id", "path": ["userId"]}
        }

    ``args`` 按顺序作为关键字参数从用例的 request_data/path_params 取值；
    ``params: true`` 表示把剩余字段作为 query 参数整体传入。
    **映射不到接口时生成的仍是骨架 + TODO**，不会去猜方法名。
    """
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("client map 必须是一个对象: 接口 -> 方法映射")
    return data


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
                  source: str = "aitest AI 草稿 + 人工评审",
                  client_map: Optional[Dict[str, Any]] = None) -> str:
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
            if client_map:
                # 有映射表：生成可执行代码（映射不到的接口仍退回 TODO 骨架）
                out.extend(_render_case_body(case, client_map))
            else:
                # 无映射表：保持骨架定位
                out.append("        # TODO 按实际客户端方法名对齐请求调用")
                out.append("        # 请求数据: %s" % _py_literal(case.request_data))
                if case.method_override:
                    out.append("        # 请求方法覆盖: %s（用于测方法不允许等场景）"
                               % case.method_override)
                if case.header_overrides:
                    out.append("        # 请求头覆盖: %s（值为空字符串表示移除该请求头）"
                               % _py_literal(case.header_overrides))
                if case.path_params:
                    out.append("        # 路径参数: %s" % _py_literal(case.path_params))
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
                 source: str = "aitest AI 草稿 + 人工评审",
                 client_map: Optional[Dict[str, Any]] = None) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_module(cases, module, source, client_map))
    return path


def render_all(cases: Sequence[TestCase], out_dir: str,
               source: str = "aitest AI 草稿 + 人工评审",
               client_map: Optional[Dict[str, Any]] = None) -> List[str]:
    """按模块生成多个文件，返回写出的路径列表。"""
    by_module: Dict[str, List[TestCase]] = {}
    for c in cases:
        by_module.setdefault(c.module or "generated", []).append(c)
    written: List[str] = []
    for module, group in sorted(by_module.items()):
        path = os.path.join(out_dir, "test_%s_ai.py" % _ascii_ident(module, "module"))
        written.append(write_module(group, module, path, source, client_map))
    return written
