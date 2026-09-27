# -*- coding: utf-8 -*-
"""可插拔的大模型层。

- :class:`ClaudeProvider` —— 调用 Claude API（Anthropic SDK），提示词按
  「业务背景 + 约束 + 示例 + 输出要求」组织，并要求返回严格 JSON。
- :class:`MockProvider` —— 离线确定性实现，不需要 API Key，
  用于单元测试与无网络环境验证整条流水线。

环境变量：
    ANTHROPIC_API_KEY   有则使用 ClaudeProvider
    AITEST_MODEL        模型名，默认 claude-sonnet-4-5
    AITEST_BASE_URL     自定义网关地址（可选）
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Protocol

from aitest.models import Endpoint, TestCase
from aitest.prompts import JSON_CONTRACT, SYSTEM_PROMPT  # noqa: F401  (对外复用)

DEFAULT_MODEL = os.environ.get("AITEST_MODEL", "claude-sonnet-4-5")


class LLMProvider(Protocol):
    name: str

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        ...


def extract_json(text: str) -> Dict[str, Any]:
    """从模型输出中稳健地取出 JSON（容忍代码块与前后解释）。"""
    if not text:
        raise ValueError("模型返回为空")
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if start >= 0 and end > start:
        return json.loads(text[start:end + 1])
    raise ValueError("无法从模型输出中解析 JSON: %s" % text[:200])


class ClaudeProvider:
    """调用 Claude API。未安装 anthropic 或未配置 Key 时给出明确错误。"""

    name = "claude"

    def __init__(self, model: str = DEFAULT_MODEL, api_key: Optional[str] = None,
                 base_url: Optional[str] = None, temperature: float = 0.2):
        try:
            import anthropic  # 延迟导入：离线环境不应影响其它功能
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "未安装 anthropic SDK，请先执行: pip install anthropic") from e
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "缺少 API Key：请设置环境变量 ANTHROPIC_API_KEY，"
                "或改用 MockProvider 离线跑通流程")
        kwargs: Dict[str, Any] = {"api_key": key}
        url = base_url or os.environ.get("AITEST_BASE_URL")
        if url:
            kwargs["base_url"] = url
        self.model = model
        self.temperature = temperature
        self._client = anthropic.Anthropic(**kwargs)

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=self.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts: List[str] = []
        for block in resp.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts)


class MockProvider:
    """离线确定性实现：按接口元数据与规则生成草稿，供无 Key 环境验证流水线。

    它不替代真实模型，但能保证 CI 与单测不依赖外部网络。
    生成质量刻意做得「中等」——真正的价值由 ClaudeProvider 提供。
    """

    name = "mock"

    def __init__(self, endpoints: Optional[List[Endpoint]] = None):
        self._endpoints = {e.key: e for e in (endpoints or [])}

    def complete(self, system: str, user: str, max_tokens: int = 4000) -> str:
        # 只在「待测接口」段内解析，避免把 few-shot 里的示例接口也当成待测目标
        section = user.split("## 二、")[0]
        cases: List[Dict[str, Any]] = []
        seen_keys = set()
        # 逐行取 "接口: METHOD /path"，比一次性正则更稳（路径里可能含花括号）
        for line in section.splitlines():
            m = re.match(r"\s*接口[:：]\s*(GET|POST|PUT|DELETE|PATCH)\s+(\S+)", line)
            if not m:
                continue
            method, path = m.group(1), m.group(2)
            key = "%s %s" % (method, path)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            ep = self._endpoints.get(key) or Endpoint(path=path, method=method)
            cases.extend(self._cases_for(ep))
        return json.dumps({"cases": cases}, ensure_ascii=False)

    # ------------------------------------------------------------------
    @staticmethod
    def _sample_value(param) -> Any:
        """按参数约束造一个合法样例值（离线 mock 用）。"""
        if param.enum:
            return param.enum[0]
        t = (param.type or "string").lower()
        if t in ("integer", "number"):
            base = param.minimum if param.minimum is not None else 1
            return int(base)
        if t == "boolean":
            return True
        if t == "array":
            return []
        name = (param.name or "").lower()
        if "password" in name or "pwd" in name:
            return "Abc@12345"
        if "phone" in name or "mobile" in name:
            return "13800138000"
        if "email" in name or "mail" in name:
            return "auto_test@example.com"
        if name in ("code", "captcha"):
            return "1234"
        if "uuid" in name:
            return "00000000-0000-0000-0000-000000000000"
        if "status" in name:
            return "0"
        if "id" in name:
            return 1
        if "time" in name or "date" in name:
            return "2026-01-01 00:00:00"
        limit = param.max_length or 20
        return "auto_%s" % ("x" * max(0, min(limit, 20) - 4))

    # ------------------------------------------------------------------
    def _cases_for(self, ep: Endpoint) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        required = [p for p in ep.params if p.required]
        sample = {p.name: self._sample_value(p) for p in required}

        out.append({
            "title": "%s - 正常场景" % (ep.summary or ep.key),
            "case_type": "normal",
            "priority": "P0",
            "precondition": "已启动服务；如接口需要鉴权，使用有效 Token",
            "steps": ["按文档构造合法请求", "发送请求", "校验业务返回"],
            "request_data": sample,
            "expected": "HTTP 200 且业务 code 为 200，返回结构与文档一致",
            "assertions": ["HTTP 状态码为 200", "业务 code 为 200",
                           "响应时间小于 3s"],
        })

        longest = next((p for p in ep.params if p.max_length), None)
        if longest:
            boundary_value = "a" * int(longest.max_length)
            boundary_title = "%s 取最大长度 %s" % (longest.name, longest.max_length)
        else:
            boundary_value = ""
            boundary_title = "参数取边界值"
        data = dict(sample)
        if longest:
            data[longest.name] = boundary_value
        out.append({
            "title": "%s - 边界: %s" % (ep.summary or ep.key, boundary_title),
            "case_type": "boundary",
            "priority": "P1",
            "precondition": "已知参数长度约束",
            "steps": ["将目标参数设为边界值", "发送请求", "校验返回未被截断或报错"],
            "request_data": data,
            "expected": "边界值被正确处理，业务 code 为 200 或给出明确参数错误",
            "assertions": ["HTTP 状态码为 200",
                           "业务 code 为 200 或字段非法提示",
                           "字段长度符合约束"],
        })

        target = required[0].name if required else (ep.params[0].name if ep.params else "id")
        bad = dict(sample)
        bad[target] = None
        out.append({
            "title": "%s - 异常: %s 缺失" % (ep.summary or ep.key, target),
            "case_type": "exception",
            "priority": "P1",
            "precondition": "服务正常运行",
            "steps": ["将 %s 置为缺失" % target, "发送请求", "校验被拒绝"],
            "request_data": bad,
            "expected": "请求被拒绝，业务 code 非 200 且提示参数缺失",
            "assertions": ["HTTP 状态码为 200（业务层返回错误）",
                           "业务 code 不等于 200", "msg 字段包含参数提示"],
        })

        if ep.need_auth:
            out.append({
                "title": "%s - 权限: 未携带 Token" % (ep.summary or ep.key),
                "case_type": "auth",
                "priority": "P0",
                "precondition": "不携带 Authorization 头",
                "steps": ["发送请求且不带 Token", "校验被鉴权拦截"],
                "request_data": sample,
                "expected": "被鉴权拦截，返回未授权状态",
                "assertions": ["HTTP 状态码为 401 或业务 code 为 401",
                               "响应体包含未授权提示"],
            })
        return out


def get_provider(endpoints: Optional[List[Endpoint]] = None,
                 prefer: str = "auto", model: str = DEFAULT_MODEL) -> LLMProvider:
    """选择可用的大模型实现。

    prefer: ``auto`` | ``claude`` | ``mock``
    """
    if prefer == "mock":
        return MockProvider(endpoints)
    try:
        return ClaudeProvider(model=model)
    except Exception:
        if prefer == "claude":
            raise
        return MockProvider(endpoints)
