import pytest
import allure

from tests.core.base import BaseTest

@allure.feature("系统管理模块")
@allure.story("角色管理接口")
class TestRoleManagement(BaseTest):

    @pytest.fixture(autouse=True)
    def _setup(self, auth_token):
        self._token = auth_token

    @allure.title("角色列表 - 正常场景: 获取角色列表")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_get_role_list(self):
        with allure.step("发送获取角色列表请求"):
            resp = self.client.get_role_list()
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        self.assert_field_exists(data, "rows")
        self.assert_field_exists(data, "total")
        self.assert_field_type(data, "rows", list)
        self.assert_field_type(data, "total", int)
        self.assert_response_time(resp.elapsed.total_seconds())

    @allure.title("角色列表 - 权限场景: 无Token访问")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_role_list_no_auth(self):
        resp = self.client.session.get(
            self.client._url("/system/role/list"),
            headers={"Content-Type": "application/json"}
        )
        self.assert_http_ok(resp)
        self.assert_business_success(resp.json())

    @allure.title("角色列表 - 权限场景: 无效Token访问")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_role_list_invalid_token(self):
        resp = self.client.session.get(
            self.client._url("/system/role/list"),
            headers={"Authorization": "Bearer invalid_token_12345", "Content-Type": "application/json"}
        )
        self.assert_http_ok(resp)
        assert resp.json().get("code") == 401, "无效Token应返回401"

    @allure.title("角色详情 - 正常场景: 获取角色详情")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    def test_get_role_by_id(self):
        list_resp = self.client.get_role_list()
        rows = list_resp.json().get("rows", [])
        if not rows:
            pytest.skip("角色列表为空")
        role_id = rows[0].get("roleId")
        resp = self.client.get_role_by_id(role_id)
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        self.assert_field_exists(data, "data")
        if data.get("data"):
            self.assert_field_exists(data["data"], "roleName")

    @allure.title("角色详情 - 异常场景: 不存在的角色ID")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_role_by_id_not_exist(self):
        resp = self.client.get_role_by_id(999999)
        self.assert_http_ok(resp)
        self.assert_business_success(resp.json())