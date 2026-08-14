import pytest
import allure

from tests.core.base import BaseTest

@allure.feature("系统管理模块")
@allure.story("部门管理接口")
class TestDeptManagement(BaseTest):

    @pytest.fixture(autouse=True)
    def _setup(self, auth_token):
        self._token = auth_token

    @allure.title("部门列表 - 正常场景: 获取部门列表")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_get_dept_list(self):
        resp = self.client.get_dept_list()
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        self.assert_field_exists(data, "data")
        self.assert_field_type(data, "data", list)
        self.assert_response_time(resp.elapsed.total_seconds())

    @allure.title("部门列表 - 权限场景: 无Token访问")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_dept_list_no_auth(self):
        resp = self.client.session.get(
            self.client._url("/system/dept/list"),
            headers={"Content-Type": "application/json"}
        )
        self.assert_http_ok(resp)
        self.assert_business_success(resp.json())

    @allure.title("部门列表 - 权限场景: 无效Token访问")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_dept_list_invalid_token(self):
        resp = self.client.session.get(
            self.client._url("/system/dept/list"),
            headers={"Authorization": "Bearer invalid_token_12345", "Content-Type": "application/json"}
        )
        self.assert_http_ok(resp)
        assert resp.json().get("code") == 401, "无效Token应返回401"