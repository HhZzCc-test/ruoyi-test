# -*- coding: utf-8 -*-
"""由 aitest 从用例文档生成的测试骨架 — 待人工补全后提交。

生成时间: 2026-09-27T19:08:56
用例来源: DeepSeek v4-pro 新契约 + 人工评审
说明: 每个测试方法上的注释标出对应用例 ID；请求调用处需按实际
      RuoyiApiClient 方法名对齐，断言与业务语义需人工复核。
"""
import pytest
import allure

from tests.core.base import BaseTest



@allure.feature("monitor")
class TestMonitorJobJobId(BaseTest):
    """DELETE /monitor/job/{jobId}"""

    @allure.title("删除定时任务 - 权限: 未携带 Token")
    @allure.story("auth")
    @pytest.mark.critical
    def test_token(self):
        """TC-MON-001: 删除定时任务 - 权限: 未携带 Token"""
        # 前置条件: 已存在 jobId=123 的定时任务，请求头中不携带 Authorization
        _saved_headers = {}
        _saved_headers['Authorization'] = self.client.session.headers.pop('Authorization', None)
        # 该接口在 client map 里没有映射，需人工按实际方法名对齐后再纳入执行
        # 请求数据: {}
        # 路径参数: {"jobId": 123}
        # 请求头覆盖: {"Authorization": ""}
        pytest.skip("接口未在 client map 中映射（DELETE /monitor/job/{jobId}），需人工补齐调用")
        # 恢复请求头
        _saved = locals().get('_saved_headers')
        if _saved:
            for _k, _v in _saved.items():
                if _v is None:
                    self.client.session.headers.pop(_k, None)
                else:
                    self.client.session.headers[_k] = _v

    @allure.title("删除定时任务 - 正常场景")
    @allure.story("normal")
    @pytest.mark.critical
    def test_case_003(self):
        """TC-MON-003: 删除定时任务 - 正常场景"""
        # 前置条件: 已存在 jobId=123 的定时任务，当前用户具有删除权限且已携带有效 Token
        # 该接口在 client map 里没有映射，需人工按实际方法名对齐后再纳入执行
        # 请求数据: {}
        # 路径参数: {"jobId": 123}
        pytest.skip("接口未在 client map 中映射（DELETE /monitor/job/{jobId}），需人工补齐调用")
        # 恢复请求头
        _saved = locals().get('_saved_headers')
        if _saved:
            for _k, _v in _saved.items():
                if _v is None:
                    self.client.session.headers.pop(_k, None)
                else:
                    self.client.session.headers[_k] = _v

    @allure.title("删除定时任务 - 边界: jobId 为 0")
    @allure.story("boundary")
    @pytest.mark.smoke
    def test_jobid_0(self):
        """TC-MON-005: 删除定时任务 - 边界: jobId 为 0"""
        # 前置条件: 假设 jobId 为正整数，最小值为 1，0 为非法值；当前用户已携带有效 Token
        # 该接口在 client map 里没有映射，需人工按实际方法名对齐后再纳入执行
        # 请求数据: {}
        # 路径参数: {"jobId": 0}
        pytest.skip("接口未在 client map 中映射（DELETE /monitor/job/{jobId}），需人工补齐调用")
        # 恢复请求头
        _saved = locals().get('_saved_headers')
        if _saved:
            for _k, _v in _saved.items():
                if _v is None:
                    self.client.session.headers.pop(_k, None)
                else:
                    self.client.session.headers[_k] = _v

    @allure.title("删除定时任务 - 异常: 使用 POST 方法调用")
    @allure.story("exception")
    @pytest.mark.smoke
    def test_post(self):
        """TC-MON-007: 删除定时任务 - 异常: 使用 POST 方法调用"""
        # 前置条件: 接口仅支持 DELETE 方法，当前用户已携带有效 Token
        # 用 POST 方法请求（该接口只允许 DELETE）
        resp = self.client.session.request('POST', self.client.base_url + '/monitor/job/123', headers=self.client.session.headers)
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            assert resp.status_code == 405 or _data.get("code") != 200   # HTTP 状态码为 405
            self.assert_business_error(_data)
            # 断言（需人工确认）: msg 包含 '方法不允许' 或 'Method Not Allowed'


@allure.feature("monitor")
class TestMonitorCacheGetNames(BaseTest):
    """GET /monitor/cache/getNames"""

    @allure.title("获取缓存名称列表 - 权限: 未携带 Token")
    @allure.story("auth")
    @pytest.mark.critical
    def test_token(self):
        """TC-MON-002: 获取缓存名称列表 - 权限: 未携带 Token"""
        # 前置条件: 无 Token
        _saved_headers = {}
        _saved_headers['Authorization'] = self.client.session.headers.pop('Authorization', None)
        resp = self.client.get_cache_names()
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            assert resp.status_code in (401, 403) or _data.get('code') in (401, 403)   # HTTP 状态码为 401 或业务 code 为 401/500（根据系统定义）
            # 断言（需人工确认）: msg 或错误信息中出现未授权或 Token 缺失提示
        # 恢复请求头
        for _k, _v in _saved_headers.items():
            if _v is None:
                self.client.session.headers.pop(_k, None)
            else:
                self.client.session.headers[_k] = _v

    @allure.title("获取缓存名称列表 - 正常场景")
    @allure.story("normal")
    @pytest.mark.critical
    def test_case_004(self):
        """TC-MON-004: 获取缓存名称列表 - 正常场景"""
        # 前置条件: 已获得有效 Token
        resp = self.client.get_cache_names()
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            # 断言（需人工确认）: HTTP 状态码为 200
            self.assert_business_success(_data)
            # 断言（需人工确认）: data 字段为数组

    @allure.title("获取缓存名称列表 - 边界: 缓存名称数量与长度上限")
    @allure.story("boundary")
    @pytest.mark.smoke
    def test_case_006(self):
        """TC-MON-006: 获取缓存名称列表 - 边界: 缓存名称数量与长度上限"""
        # 前置条件: 假设缓存名称列表数量不超过 1000，每个名称长度不超过 200（接口文档未给出约束，按常见监控系统约定）
        resp = self.client.get_cache_names()
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            self.assert_business_success(_data)
            # 断言（需人工确认）: data 数组长度 <= 1000
            # 断言（需人工确认）: data 中每个元素类型为 string 且长度 <= 200

    @allure.title("获取缓存名称列表 - 异常: 不支持的 HTTP 方法 POST")
    @allure.story("exception")
    @pytest.mark.smoke
    def test_http_post(self):
        """TC-MON-008: 获取缓存名称列表 - 异常: 不支持的 HTTP 方法 POST"""
        # 前置条件: 已获得有效 Token
        # 用 POST 方法请求（该接口只允许 GET）
        resp = self.client.session.request('POST', self.client.base_url + '/monitor/cache/getNames', headers=self.client.session.headers)
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            self.assert_business_error(_data)
            # 断言（需人工确认）: msg 或错误信息中出现方法不允许相关提示
