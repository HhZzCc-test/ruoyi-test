# -*- coding: utf-8 -*-
"""数据模型：接口元数据与测试用例。

保持轻量（仅用 dataclass），便于 JSON 序列化与人工评审。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

# 用例类型与优先级（与 skills/api-test-skill.md 的定义保持一致）
CASE_TYPES = ("normal", "boundary", "exception", "auth")
PRIORITIES = ("P0", "P1", "P2")


@dataclass
class ParamSpec:
    """单个请求参数/字段的约束。"""

    name: str
    location: str = "body"           # path | query | body | header
    required: bool = False
    type: str = "string"
    format: Optional[str] = None
    enum: List[Any] = field(default_factory=list)
    maximum: Optional[float] = None
    minimum: Optional[float] = None
    max_length: Optional[int] = None
    min_length: Optional[int] = None
    description: str = ""

    def constraint_text(self) -> str:
        """给提示词用的紧凑约束描述。"""
        bits = [self.type]
        if self.required:
            bits.append("必填")
        else:
            bits.append("可选")
        if self.enum:
            bits.append("枚举=%s" % ",".join(str(v) for v in self.enum[:8]))
        if self.maximum is not None:
            bits.append("max=%s" % self.maximum)
        if self.minimum is not None:
            bits.append("min=%s" % self.minimum)
        if self.max_length is not None:
            bits.append("maxLength=%s" % self.max_length)
        if self.min_length is not None:
            bits.append("minLength=%s" % self.min_length)
        return "(%s)" % " ".join(bits)


@dataclass
class FieldSpec:
    """响应字段。"""

    name: str
    type: str = "string"
    description: str = ""


# 路径首段 → 业务模块（单段路径的接口归到语义模块，避免出现 test_getinfo_ai.py）
PATH_MODULE_MAP = {
    "login": "auth",
    "logout": "auth",
    "register": "auth",
    "captchaImage": "auth",
    "getInfo": "auth",
    "getRouters": "auth",
}


@dataclass
class Endpoint:
    """一个接口的元数据。"""

    path: str
    method: str
    summary: str = ""
    operation_id: str = ""
    tags: List[str] = field(default_factory=list)
    params: List[ParamSpec] = field(default_factory=list)
    body_required: bool = False
    response_fields: List[FieldSpec] = field(default_factory=list)
    need_auth: bool = False
    risk: str = "low"                # low | medium | high（写操作/删除类为 high）
    spec_source: str = ""            # 来源文件，便于追溯

    @property
    def key(self) -> str:
        return "%s %s" % (self.method.upper(), self.path)

    @property
    def module(self) -> str:
        """推断业务模块：/system/user/list -> system；/login -> auth。"""
        parts = [p for p in self.path.split("/") if p and not p.startswith("{")]
        if not parts:
            return "root"
        if len(parts) == 1:
            return PATH_MODULE_MAP.get(parts[0], parts[0])
        return parts[0]

    def prompt_block(self) -> str:
        """拼给大模型的接口描述块。"""
        lines = [
            "接口: %s %s" % (self.method.upper(), self.path),
            "说明: %s" % (self.summary or "-"),
            "模块: %s" % self.module,
            "是否需要鉴权: %s" % ("是" if self.need_auth else "否"),
            "风险等级: %s" % self.risk,
        ]
        if self.params:
            lines.append("参数:")
            for p in self.params:
                lines.append("  - %s [%s] %s %s"
                             % (p.name, p.location, p.constraint_text(), p.description))
        else:
            lines.append("参数: 无")
        if self.response_fields:
            lines.append("响应字段: %s"
                         % ", ".join("%s:%s" % (f.name, f.type) for f in self.response_fields[:12]))
        return "\n".join(lines)


@dataclass
class TestCase:
    """一条测试用例（AI 草稿 / 人工修订后的最终稿）。"""

    # 名字以 Test 开头会让 pytest 误当作测试类收集，显式排除
    __test__ = False

    case_id: str
    title: str
    endpoint: str                 # "POST /login"
    case_type: str                # normal | boundary | exception | auth
    priority: str = "P1"          # P0 | P1 | P2
    precondition: str = ""
    steps: List[str] = field(default_factory=list)
    request_data: Dict[str, Any] = field(default_factory=dict)
    expected: str = ""
    assertions: List[str] = field(default_factory=list)
    source: str = "ai"            # ai | human | ai+human
    module: str = ""
    # ---- 请求维度覆盖（真实模型生成过「换用不支持的 HTTP 方法」这类用例，
    #      而 request_data 只能表达请求体，表达不了方法与请求头维度）----
    method_override: Optional[str] = None          # 覆盖 HTTP 方法，如 "PUT"
    header_overrides: Dict[str, str] = field(default_factory=dict)
    #                                               值为 "" 表示移除该请求头（如去掉 Authorization）
    path_params: Dict[str, Any] = field(default_factory=dict)   # 路径参数，与 request_data 分开
    # 校验/去重过程中写入的诊断信息，不进入交付文档
    diagnostics: List[str] = field(default_factory=list)

    # ---------- 校验辅助 ----------
    def is_wellformed(self) -> bool:
        return bool(self.case_id and self.title and self.endpoint
                    and self.case_type in CASE_TYPES and self.priority in PRIORITIES)

    def signature(self) -> str:
        """用于去重的语义指纹：同接口 + 同类型 + 同请求 + 同预期。

        请求维度覆盖必须一起进指纹，否则「换 PUT 方法」的用例会被误判成
        与同接口的 GET 正常用例重复而丢掉。
        """
        payload = json.dumps({"data": self.request_data,
                              "path": self.path_params,
                              "method": self.method_override,
                              "headers": self.header_overrides},
                             sort_keys=True, ensure_ascii=False)
        return "|".join([self.endpoint, self.case_type, payload, self.expected.strip()])

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("diagnostics", None)
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "TestCase":
        allowed = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in allowed})
