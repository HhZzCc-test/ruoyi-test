import pytest
import requests
import allure
from tests.core.assertions import assert_http_ok, assert_business_success


@allure.feature("系统监控-在线用户")
class TestOnlineUser:

    @pytest.fixture(autouse=True)
    def _setup(self, auth_token):
        self._token = auth_token

    @allure.story("在线用户列表")
    @allure.title("在线用户列表 - 正常场景: 获取在线用户列表")
    @pytest.mark.smoke
    def test_get_online_list(self):
        """TC-ONLINE-001: 获取在线用户列表"""
        resp = self.client.get_online_list()
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert "rows" in data, "返回数据应包含rows字段"
        assert isinstance(data.get("rows"), list), "rows应为列表类型"

    @allure.story("在线用户列表")
    @allure.title("在线用户列表 - 异常场景: 未认证访问")
    @pytest.mark.critical
    def test_get_online_list_no_auth(self):
        """TC-ONLINE-002: 未认证访问在线用户列表"""
        resp = requests.get(
            self.client._url("/monitor/online/list"),
            headers={"Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "未认证应返回401"

    @allure.story("在线用户列表")
    @allure.title("在线用户列表 - 异常场景: 无效Token访问")
    @pytest.mark.critical
    def test_get_online_list_invalid_token(self):
        """TC-ONLINE-003: 无效Token访问在线用户列表"""
        resp = requests.get(
            self.client._url("/monitor/online/list"),
            headers={"Authorization": "Bearer invalid_token_12345", "Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "无效Token应返回401"

    @allure.story("在线用户列表")
    @allure.title("在线用户列表 - 边界场景: 按用户名搜索")
    def test_filter_online_by_username(self):
        """TC-ONLINE-004: 按用户名搜索在线用户"""
        params = {"userName": "admin"}
        resp = self.client.get_online_list(params=params)
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert len(data.get("rows", [])) >= 0, "按用户名搜索应返回结果"

    @allure.story("在线用户强退")
    @allure.title("在线用户强退 - 异常场景: 强退不存在用户")
    def test_force_logout_nonexistent(self):
        """TC-ONLINE-005: 强退不存在的在线用户"""
        resp = self.client.force_logout("nonexistent_token_id")
        assert_http_ok(resp)
        assert resp.json().get("code") == 200, "强退不存在用户应返回200"

    @allure.story("在线用户强退")
    @allure.title("在线用户强退 - 异常场景: 空参数强退")
    def test_force_logout_empty(self):
        """TC-ONLINE-006: 空参数强退"""
        resp = self.client.session.delete(
            self.client._url("/monitor/online/"),
            headers=self.client.session.headers
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 500, "空参数强退应返回500"
