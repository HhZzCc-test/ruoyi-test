import pytest
import requests
import allure
from tests.core.assertions import assert_http_ok, assert_business_success


@allure.feature("系统监控-操作日志")
class TestOperlog:

    @pytest.fixture(autouse=True)
    def _setup(self, auth_token):
        self._token = auth_token

    @allure.story("操作日志列表")
    @allure.title("操作日志列表 - 正常场景: 获取操作日志列表")
    @pytest.mark.smoke
    def test_get_operlog_list(self):
        """TC-OPERLOG-001: 获取操作日志列表"""
        resp = self.client.get_operlog_list()
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert "rows" in data, "应包含rows字段"
        assert isinstance(data.get("rows"), list), "rows应为列表"

    @allure.story("操作日志列表")
    @allure.title("操作日志列表 - 异常场景: 未认证访问")
    @pytest.mark.critical
    def test_get_operlog_list_no_auth(self):
        """TC-OPERLOG-002: 未认证访问操作日志列表"""
        resp = requests.get(
            self.client._url("/monitor/operlog/list"),
            headers={"Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "未认证应返回401"

    @allure.story("操作日志列表")
    @allure.title("操作日志列表 - 异常场景: 无效Token访问")
    @pytest.mark.critical
    def test_get_operlog_list_invalid_token(self):
        """TC-OPERLOG-003: 无效Token访问操作日志列表"""
        resp = requests.get(
            self.client._url("/monitor/operlog/list"),
            headers={"Authorization": "Bearer invalid_token_12345", "Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "无效Token应返回401"

    @allure.story("操作日志列表")
    @allure.title("操作日志列表 - 边界场景: 按操作人员筛选")
    def test_filter_operlog_by_name(self):
        """TC-OPERLOG-004: 按操作人员筛选操作日志"""
        params = {"operName": "admin"}
        resp = self.client.get_operlog_list(params=params)
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        for row in data.get("rows", []):
            assert row.get("operName") == "admin", f"operName应为admin"
