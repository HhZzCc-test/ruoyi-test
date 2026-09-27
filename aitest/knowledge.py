# -*- coding: utf-8 -*-
"""业务知识库：轻量检索增强（RAG）。

不需要外部向量库：用「关键词/路径/标签」打分检索业务规则与历史用例，
把最相关的片段拼进提示词，让模型产出贴近真实业务的用例而不是泛泛而谈。

知识库文件格式（Markdown）：
    ## 用户管理
    关键词: user, 用户, 账号
    - 用户名校验：长度 2-20，不允许重复
    - 停用用户不能登录
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence

from aitest.models import Endpoint


@dataclass
class KnowledgeItem:
    title: str
    keywords: List[str] = field(default_factory=list)
    bullets: List[str] = field(default_factory=list)
    raw: str = ""

    def text(self) -> str:
        lines = ["【%s】" % self.title]
        lines.extend("- %s" % b for b in self.bullets)
        return "\n".join(lines)


class KnowledgeBase:
    """关键词加权的轻量检索。"""

    def __init__(self, items: Sequence[KnowledgeItem] = ()):
        self.items: List[KnowledgeItem] = list(items)

    # ------------------------------------------------------------------
    @classmethod
    def from_markdown(cls, path: str) -> "KnowledgeBase":
        if not os.path.exists(path):
            return cls([])
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_text(f.read())

    @classmethod
    def from_text(cls, text: str) -> "KnowledgeBase":
        items: List[KnowledgeItem] = []
        current: KnowledgeItem | None = None
        for raw_line in text.splitlines():
            line = raw_line.rstrip()
            if line.startswith("## "):
                if current:
                    items.append(current)
                current = KnowledgeItem(title=line[3:].strip())
                continue
            if current is None:
                continue
            m = re.match(r"^\s*(?:关键词|keywords?)\s*[:：]\s*(.+)$", line, re.I)
            if m:
                current.keywords.extend(
                    k.strip() for k in re.split(r"[,，、/]", m.group(1)) if k.strip())
                continue
            m = re.match(r"^\s*[-*]\s+(.+)$", line)
            if m:
                current.bullets.append(m.group(1).strip())
        if current:
            items.append(current)
        return cls(items)

    # ------------------------------------------------------------------
    def retrieve(self, endpoint: Endpoint, top_k: int = 3) -> List[KnowledgeItem]:
        """按 路径 / 标签 / 摘要 与知识条目的关键词重合度打分。"""
        haystack = " ".join([
            endpoint.path, endpoint.summary, " ".join(endpoint.tags),
            " ".join(p.name for p in endpoint.params),
        ]).lower()
        scored = []
        for item in self.items:
            score = 0
            for kw in [item.title] + item.keywords:
                kw_l = kw.lower().strip()
                if kw_l and kw_l in haystack:
                    score += 3 if len(kw_l) > 2 else 1
            if score:
                scored.append((score, item))
        scored.sort(key=lambda x: -x[0])
        return [it for _, it in scored[:top_k]]

    def build_context(self, endpoint: Endpoint, top_k: int = 3) -> str:
        hits = self.retrieve(endpoint, top_k=top_k)
        if not hits:
            return "（知识库中没有与该接口直接匹配的业务规则）"
        return "\n\n".join(h.text() for h in hits)

    def stats(self) -> Dict[str, int]:
        return {
            "items": len(self.items),
            "bullets": sum(len(i.bullets) for i in self.items),
            "keywords": sum(len(i.keywords) for i in self.items),
        }


DEFAULT_KB_TEXT = """# 业务知识库（若依后台系统）

## 认证与鉴权
关键词: 认证, 登录, 鉴权, login, token, auth, 验证码, captcha
- 登录必须携带验证码 code 与 uuid，uuid 由 /captchaImage 下发
- 验证码答案缓存在 Redis，key 形如 captcha_codes:{uuid}
- 登录成功后返回 token，后续接口通过请求头 Authorization: Bearer {token}
- 未携带 Token 返回 401；Token 无效或过期同样返回 401
- 连续登录失败会触发账号锁定提示

## 分页与列表查询
关键词: 列表, 分页, pageNum, pageSize, list, 查询
- 列表接口统一使用 pageNum / pageSize 分页，返回结构含 rows 与 total
- pageNum 从 1 开始；pageSize 过大（如超过 1000）应有上限保护
- total 表示符合条件总数，rows 为当前页数据
- 关键字搜索参数通常为 name / userName / phonenumber 等

## 用户管理
关键词: 用户, user, 账号, 会员
- 用户名与登录账号唯一，重复创建应被拒绝
- 密码不允许通过列表接口返回
- 停用状态的用户不能登录
- 删除当前登录用户应被拒绝（业务保护）

## 写操作与数据保护
关键词: 新增, 修改, 删除, add, edit, remove, 写操作
- 写操作需校验必填字段，缺失时应返回明确的字段错误提示
- 删除类接口需校验权限，越权删除应被拒绝
- 写操作后应能通过查询接口反查到最新状态（一致性校验）

## 系统监控
关键词: 监控, 缓存, 在线用户, 定时任务, 日志, monitor, cache, job, log
- 缓存监控只读，非法 cacheName 应给出提示而不是异常堆栈
- 在线用户强退需 tokenId，非法 tokenId 应被拒绝
- 定时任务日志按 jobId 过滤时，不存在的 jobId 应返回空集而非报错
"""


def default_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase.from_text(DEFAULT_KB_TEXT)
