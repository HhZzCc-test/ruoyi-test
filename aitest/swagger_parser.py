# -*- coding: utf-8 -*-
"""Swagger / OpenAPI 2.0 & 3.x 解析器。

把接口文档转成 :class:`aitest.models.Endpoint`，作为「阶段一：接口分析」的产物。

支持：
- OpenAPI 3.x（``components.schemas`` + ``requestBody``）
- Swagger 2.0（``definitions`` + ``parameters``）
- ``$ref`` 一层/多层引用解析
- 从参数约束中提取边界（minimum/maximum/maxLength/minLength/enum）
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from aitest.models import Endpoint, FieldSpec, ParamSpec

_METHODS = ("get", "post", "put", "delete", "patch")
_WRITE_METHODS = ("post", "put", "patch", "delete")

# 常见鉴权参数名，命中即认为需要 Token
_AUTH_HINTS = ("authorization", "token", "x-access-token")


def load_spec(path_or_url: str) -> Dict[str, Any]:
    """加载本地 JSON/YAML 规格文件。"""
    if not os.path.exists(path_or_url):
        raise FileNotFoundError("规格文件不存在: %s" % path_or_url)
    with open(path_or_url, "r", encoding="utf-8") as f:
        text = f.read()
    if path_or_url.lower().endswith((".yaml", ".yml")):
        import yaml  # 延迟导入，避免非 YAML 场景强依赖
        return yaml.safe_load(text)
    return json.loads(text)


class _RefResolver:
    """极简 $ref 解析（``#/components/schemas/X`` 与 ``#/definitions/X``）。"""

    def __init__(self, spec: Dict[str, Any]):
        self.spec = spec

    def resolve(self, node: Any, depth: int = 0) -> Any:
        if depth > 8 or not isinstance(node, dict):
            return node
        ref = node.get("$ref")
        if not ref:
            return node
        if not ref.startswith("#/"):
            return node
        target: Any = self.spec
        for part in ref[2:].split("/"):
            if isinstance(target, dict) and part in target:
                target = target[part]
            else:
                return node
        merged = dict(target)
        for k, v in node.items():          # $ref 同级字段覆盖被引用对象
            if k != "$ref":
                merged[k] = v
        return self.resolve(merged, depth + 1)


def _schema_to_params(schema: Dict[str, Any], location: str,
                      resolver: _RefResolver, required_names: List[str]) -> List[ParamSpec]:
    schema = resolver.resolve(schema)
    props = schema.get("properties") or {}
    required = set(schema.get("required") or required_names or [])
    out: List[ParamSpec] = []
    for name, raw in props.items():
        p = resolver.resolve(raw)
        out.append(ParamSpec(
            name=name,
            location=location,
            required=name in required,
            type=str(p.get("type") or ("object" if "properties" in p else "string")),
            format=p.get("format"),
            enum=list(p.get("enum") or []),
            maximum=p.get("maximum"),
            minimum=p.get("minimum"),
            max_length=p.get("maxLength"),
            min_length=p.get("minLength"),
            description=str(p.get("description") or "")[:80],
        ))
    return out


def _response_fields(operation: Dict[str, Any], resolver: _RefResolver) -> List[FieldSpec]:
    """取 200 响应模型字段（尽量浅层展开一层）。"""
    responses = operation.get("responses") or {}
    ok = responses.get("200") or responses.get(200) or {}
    schema = None
    if "content" in ok:                                  # OpenAPI 3
        content = ok.get("content") or {}
        for ctype in ("application/json", "application/*+json"):
            if ctype in content:
                schema = (content[ctype] or {}).get("schema")
                break
        if schema is None and content:
            schema = (list(content.values())[0] or {}).get("schema")
    else:                                                # Swagger 2
        schema = ok.get("schema")
    if not schema:
        return []
    schema = resolver.resolve(schema)
    props = schema.get("properties") or {}
    out: List[FieldSpec] = []
    for name, raw in props.items():
        p = resolver.resolve(raw)
        out.append(FieldSpec(name=name,
                             type=str(p.get("type") or "object"),
                             description=str(p.get("description") or "")[:60]))
    return out


def _needs_auth(operation: Dict[str, Any], params: List[ParamSpec]) -> bool:
    if operation.get("security"):
        return True
    for p in params:
        if p.name.lower() in _AUTH_HINTS:
            return True
    return False


def parse_swagger(spec: Dict[str, Any], spec_source: str = "") -> List[Endpoint]:
    """把 OpenAPI/Swagger 规格解析为接口清单。"""
    if not isinstance(spec, dict):
        raise ValueError("规格内容不是对象")
    resolver = _RefResolver(spec)
    paths = spec.get("paths") or {}
    if not isinstance(paths, dict) or not paths:
        raise ValueError("规格中没有 paths，无法解析接口")

    endpoints: List[Endpoint] = []
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        shared = item.get("parameters") or []
        for method in _METHODS:
            op = item.get(method)
            if not isinstance(op, dict):
                continue
            params: List[ParamSpec] = []

            # OpenAPI 3：requestBody
            rb = resolver.resolve(op.get("requestBody") or {})
            if rb:
                for ctype, media in (rb.get("content") or {}).items():
                    schema = (media or {}).get("schema")
                    if schema:
                        params.extend(_schema_to_params(schema, "body", resolver, []))
                        break

            # OpenAPI 2 / 共用：parameters
            for raw in list(shared) + list(op.get("parameters") or []):
                p = resolver.resolve(raw)
                loc = p.get("in")
                if loc == "body":
                    params.extend(_schema_to_params(p.get("schema") or {}, "body",
                                                    resolver, []))
                elif loc in ("query", "path", "header", "formData"):
                    params.append(ParamSpec(
                        name=str(p.get("name") or ""),
                        location="query" if loc == "formData" else loc,
                        required=bool(p.get("required")),
                        type=str(p.get("type") or "string"),
                        format=p.get("format"),
                        enum=list(p.get("enum") or []),
                        maximum=p.get("maximum"),
                        minimum=p.get("minimum"),
                        max_length=p.get("maxLength"),
                        min_length=p.get("minLength"),
                        description=str(p.get("description") or "")[:80],
                    ))

            # 去重（同名字段以 body 优先）
            seen: Dict[str, ParamSpec] = {}
            for p in params:
                if p.name and p.name not in seen:
                    seen[p.name] = p
            params = list(seen.values())

            risk = "high" if method in _WRITE_METHODS else "low"
            if any(k in path for k in ("delete", "remove", "reset", "clean")):
                risk = "high"

            endpoints.append(Endpoint(
                path=path,
                method=method.upper(),
                summary=str(op.get("summary") or op.get("description") or "")[:100],
                operation_id=str(op.get("operationId") or ""),
                tags=[str(t) for t in (op.get("tags") or [])],
                params=params,
                body_required=bool(rb.get("required")) if rb else False,
                response_fields=_response_fields(op, resolver),
                need_auth=_needs_auth(op, params),
                risk=risk,
                spec_source=spec_source,
            ))
    return endpoints
