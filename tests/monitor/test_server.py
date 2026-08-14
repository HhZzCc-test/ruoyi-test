import pytest
import requests
import allure
from tests.core.assertions import assert_http_ok, assert_business_success


@allure.feature("系统监控-服务监控")
class TestServer:

    @pytest.fixture(autouse=True)
    def _setup(self, auth_token):
        self._token = auth_token

    @allure.story("服务监控")
    @allure.title("服务监控 - 正常场景: 获取服务器信息")
    @pytest.mark.smoke
    def test_get_server_info(self):
        """TC-SERVER-001: 获取服务器信息"""
        resp = self.client.get_server_info()
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert "data" in data, "应包含data字段"
        assert isinstance(data.get("data"), dict), "data应为字典"
        server_data = data["data"]
        for field in ["cpu", "mem", "jvm", "sys"]:
            assert field in server_data, f"data应包含{field}字段"

    @allure.story("服务监控")
    @allure.title("服务监控 - 异常场景: 未认证访问")
    @pytest.mark.critical
    def test_get_server_info_no_auth(self):
        """TC-SERVER-002: 未认证访问服务监控"""
        resp = requests.get(
            self.client._url("/monitor/server"),
            headers={"Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "未认证应返回401"

    @allure.story("服务监控")
    @allure.title("服务监控 - 异常场景: 无效Token访问")
    @pytest.mark.critical
    def test_get_server_info_invalid_token(self):
        """TC-SERVER-003: 无效Token访问服务监控"""
        resp = requests.get(
            self.client._url("/monitor/server"),
            headers={"Authorization": "Bearer invalid_token_12345", "Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "无效Token应返回401"
