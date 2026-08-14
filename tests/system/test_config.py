import pytest
import allure

from tests.core.base import BaseTest

@allure.feature("系统管理模块")
@allure.story("参数设置接口")
class TestConfigManagement(BaseTest):

    @pytest.fixture(autouse=True)
    def _setup(self, auth_token):
        self._token = auth_token

    @allure.title("参数列表 - 正常场景: 获取参数列表")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_get_config_list(self):
        resp = self.client.get_config_list()
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        self.assert_field_exists(data, "rows")
        self.assert_field_exists(data, "total")
        self.assert_field_type(data, "rows", list)
        self.assert_field_type(data, "total", int)
        self.assert_response_time(resp.elapsed.total_seconds())

    @allure.title("参数列表 - 权限场景: 无Token访问")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_config_list_no_auth(self):
        resp = self.client.session.get(
            self.client._url("/system/config/list"),
            headers={"Content-Type": "application/json"}
        )
        self.assert_http_ok(resp)
        self.assert_business_success(resp.json())

    @allure.title("参数列表 - 权限场景: 无效Token访问")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_config_list_invalid_token(self):
        resp = self.client.session.get(
            self.client._url("/system/config/list"),
            headers={"Authorization": "Bearer invalid_token_12345", "Content-Type": "application/json"}
        )
        self.assert_http_ok(resp)
        assert resp.json().get("code") == 401, "无效Token应返回401"