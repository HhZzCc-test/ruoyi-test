# -*- coding: utf-8 -*-
"""提示词构建：把接口元数据 + 业务知识库片段 + 输出契约拼成一次生成请求。

对应简历里的「提示词设计（业务背景 + 约束 + 示例 + 输出要求）」，
四个要素在这里各有对应实现，便于以后单独调优。
"""
from __future__ import annotations

from typing import List, Optional, Sequence

from aitest.knowledge import KnowledgeBase
from aitest.models import Endpoint
from aitest.prompts import JSON_CONTRACT, SYSTEM_PROMPT

__all__ = ["build_prompt", "PromptParts"]

# 少样本示例：用一条完整的期望产出锚定格式与粒度
FEWSHOT = """示例（仅示范粒度与断言写法，不要照抄内容）：

接口: POST /system/user
说明: 新增用户
参数:
  - userName [body] (string 必填 maxLength=30)
  - password [body] (string 必填)
  - status [body] (string 可选 枚举=0,1)

产出：
{
  "cases": [
    {
      "title": "新增用户 - 正常场景",
      "case_type": "normal",
      "priority": "P0",
      "precondition": "已获得管理员 Token",
      "steps": ["构造合法 userName/password/status", "调用新增接口", "用查询接口反查该用户"],
      "request_data": {"userName": "auto_user_001", "password": "Abc@12345", "status": "0"},
      "expected": "业务 code 为 200，且能在用户列表中查到该 userName",
      "assertions": ["HTTP 状态码为 200", "业务 code 为 200",
                     "查询接口返回的 rows 中包含该 userName"]
    },
    {
      "title": "新增用户 - 边界: userName 取最大长度 30",
      "case_type": "boundary",
      "priority": "P1",
      "precondition": "userName 长度上限 30",
      "steps": ["userName 设为 30 个字符", "调用新增接口"],
      "request_data": {"userName": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "password": "Abc@12345"},
      "expected": "恰好 30 字符被接受；超过 30 应被拒绝",
      "assertions": ["业务 code 为 200", "返回的 userName 长度等于 30"]
    },
    {
      "title": "新增用户 - 异常: 缺少必填 userName",
      "case_type": "exception",
      "priority": "P1",
      "precondition": "userName 为必填",
      "steps": ["不传 userName", "调用新增接口"],
      "request_data": {"password": "Abc@12345"},
      "expected": "请求被拒绝，提示 userName 不能为空",
      "assertions": ["业务 code 不等于 200", "msg 中出现 userName 相关提示"]
    }
  ]
}"""


class PromptParts:
    """保留中间产物，便于在 CLI 中 `--show-prompt` 打印与人工评审。"""

    def __init__(self, system: str, user: str, knowledge_hits: int):
        self.system = system
        self.user = user
        self.knowledge_hits = knowledge_hits

    def __repr__(self) -> str:  # pragma: no cover
        return "PromptParts(knowledge_hits=%d, user_chars=%d)" % (
            self.knowledge_hits, len(self.user))


def build_prompt(endpoint: Endpoint,
                 knowledge: Optional[KnowledgeBase] = None,
                 include_fewshot: bool = True,
                 extra_rules: Sequence[str] = ()) -> PromptParts:
    """构建单个接口的生成提示词。"""
    kb = knowledge or KnowledgeBase([])
    hits = kb.retrieve(endpoint, top_k=3)
    context = kb.build_context(endpoint, top_k=3)

    blocks: List[str] = []
    blocks.append("## 一、待测接口\n\n" + endpoint.prompt_block())
    blocks.append("## 二、业务背景（来自知识库检索，务必据此设计断言）\n\n" + context)
    blocks.append(
        "## 三、约束\n\n"
        "- 用例数量：3~6 条，覆盖 正常 / 边界 / 异常"
        + ("，并额外覆盖 权限" if endpoint.need_auth else "")
        + "\n"
        "- 边界值必须来自接口文档中的真实约束；文档没给约束时按常见约定并在 precondition 说明假设\n"
        "- 异常用例要给出具体的畸形数据，不要写「传错误参数」这类空话\n"
        "- request_data 的键必须是接口文档中真实存在的字段\n"
        "- 要测请求维度（HTTP 方法 / 请求头）上的异常，用 method_override / "
        "header_overrides 表达，不要塞进 request_data\n"
        "- 每个接口最多 1 条仅校验 HTTP 200 的用例")
    if extra_rules:
        blocks.append("## 四、额外要求\n\n" + "\n".join("- %s" % r for r in extra_rules))
    if include_fewshot:
        blocks.append("## 五、输出示例\n\n" + FEWSHOT)
    blocks.append("## 六、输出要求\n\n" + JSON_CONTRACT)

    return PromptParts(SYSTEM_PROMPT, "\n\n".join(blocks), len(hits))
