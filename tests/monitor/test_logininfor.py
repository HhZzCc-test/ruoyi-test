import pytest
import requests
import allure
from tests.core.assertions import assert_http_ok, assert_business_success


@allure.feature("系统监控-登录日志")
class TestLogininfor:

    @pytest.fixture(autouse=True)
    def _setup(self, auth_token):
        self._token = auth_token

    @allure.story("登录日志列表")
    @allure.title("登录日志列表 - 正常场景: 获取登录日志列表")
    @pytest.mark.smoke
    def test_get_logininfor_list(self):
        """TC-LOGININFO-001: 获取登录日志列表"""
        resp = self.client.get_logininfor_list()
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert "rows" in data, "应包含rows字段"
        assert isinstance(data.get("rows"), list), "rows应为列表"

    @allure.story("登录日志列表")
    @allure.title("登录日志列表 - 异常场景: 未认证访问")
    @pytest.mark.critical
    def test_get_logininfor_list_no_auth(self):
        """TC-LOGININFO-002: 未认证访问登录日志列表"""
        resp = requests.get(
            self.client._url("/monitor/logininfor/list"),
            headers={"Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "未认证应返回401"

    @allure.story("登录日志列表")
    @allure.title("登录日志列表 - 异常场景: 无效Token访问")
    @pytest.mark.critical
    def test_get_logininfor_list_invalid_token(self):
        """TC-LOGININFO-003: 无效Token访问登录日志列表"""
        resp = requests.get(
            self.client._url("/monitor/logininfor/list"),
            headers={"Authorization": "Bearer invalid_token_12345", "Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "无效Token应返回401"

    @allure.story("登录日志列表")
    @allure.title("登录日志列表 - 边界场景: 按用户名筛选")
    def test_filter_logininfor_by_username(self):
        """TC-LOGININFO-004: 按用户名筛选登录日志"""
        params = {"userName": "admin"}
        resp = self.client.get_logininfor_list(params=params)
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        for row in data.get("rows", []):
            assert row.get("userName") == "admin", f"userName应为admin"
