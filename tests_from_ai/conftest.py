# -*- coding: utf-8 -*-
"""tests_from_ai/ 的夹具：与 tests/system/conftest.py 保持同一套注入方式。

这些用例是 aitest 用真实模型生成、经人工评审后落地的可执行测试。
它们**不在默认回归里**（pytest.ini 的 testpaths 只含 tests），需要显式指定目录运行：

    python -m pytest tests_from_ai -q                 # 需要若依后端 + Redis 在线
    python -m pytest tests_from_ai -q -k 分页          # 只跑某几条

只有映射表里映射到的接口才会生成可执行调用，其余仍是带 TODO 的骨架。
"""
import pytest

from tests.core.client import RuoyiApiClient

BASE_URL = "http://localhost:18080"


@pytest.fixture(scope="session")
def api_client():
    return RuoyiApiClient(BASE_URL)


@pytest.fixture(scope="session")
def auth_headers(api_client):
    token = api_client.login_and_get_token("admin", "admin123")
    if token:
        api_client.set_auth_header(token)
    return {"Authorization": "Bearer %s" % token}


@pytest.fixture(scope="session")
def auth_token(api_client, auth_headers):
    return auth_headers.get("Authorization", "").replace("Bearer ", "")


@pytest.fixture(autouse=True)
def _reset_auth(api_client, auth_headers, request):
    """每个用例开始前重置鉴权头，并把客户端注入测试类。

    ★ 为什么必须这么做：权限类用例会**摘掉 Authorization 头**来验证 401，
    而恢复语句写在用例体里 —— 一旦断言失败或 `pytest.skip()` 抛异常，
    恢复就不会执行，同一个 session 客户端上的**后续用例全部拿到 401**。
    这种「跨用例污染」曾经真实发生：4 条不相干的用例因此集体失败。
    """
    api_client.session.headers.update(auth_headers)
    if request.cls:
        request.cls.client = api_client
