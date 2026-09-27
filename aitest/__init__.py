# -*- coding: utf-8 -*-
"""AI 辅助接口测试生成器。

把 skills/api-test-skill.md 里那套「Analyze → Design → Implement → Verify」
的人工 AI 工作流，工程化成可重复执行的代码：

    Swagger/OpenAPI ──► 接口元数据 ──► AI 生成用例草稿 ──► 规则去重/覆盖度校验
                                                              │
                          pytest 脚本骨架 ◄────────────────────┘

设计要点
- **AI 可插拔**：`LLMProvider` 协议 + Claude 实现 + Mock 实现。
  没有 API Key 时用 Mock 也能跑通全流程，便于离线开发与单测。
- **AI 只出草稿**：生成结果必须经 `case_rules.validate_case` 校验、
  经人工评审后才允许写入，对应简历里的「AI 产出 + 人工评审」。
- **失败归因可落地**：`analyzer` 把 traceback + 响应体归类为
  用例问题 / 环境问题 / 真实缺陷。
"""

from aitest.models import Endpoint, TestCase, ParamSpec, FieldSpec  # noqa: F401
from aitest.swagger_parser import parse_swagger, load_spec  # noqa: F401
from aitest.case_rules import dedupe, coverage_report, validate_case  # noqa: F401

__version__ = "1.0.0"

__all__ = [
    "Endpoint",
    "TestCase",
    "ParamSpec",
    "FieldSpec",
    "parse_swagger",
    "load_spec",
    "dedupe",
    "coverage_report",
    "validate_case",
    "__version__",
]
