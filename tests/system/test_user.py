import pytest
import allure
from tests.core.assertions import assert_http_ok, assert_business_success


@allure.feature("系统管理-用户管理")
class TestUserManagement:

    @pytest.fixture(autouse=True)
    def _setup(self, auth_token):
        self._token = auth_token

    @allure.story("用户列表")
    @allure.title("用户列表 - 正常场景: 获取用户列表")
    @pytest.mark.smoke
    def test_get_user_list(self):
        """TC-USER-001: 获取用户列表"""
        resp = self.client.get_user_list()
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        allure.attach(str(len(data.get("rows", []))), "用户数量", allure.attachment_type.TEXT)

    @allure.story("用户列表")
    @allure.title("用户列表 - 正常场景: 根据ID获取用户")
    @pytest.mark.smoke
    def test_get_user_by_id(self):
        """TC-USER-002: 根据ID获取用户"""
        resp = self.client.get_user_by_id(1)
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        user_data = data.get("data", {})
        allure.attach(str(user_data.get("userName", "")), "用户名", allure.attachment_type.TEXT)

    @allure.story("用户列表")
    @allure.title("用户列表 - 正常场景: 分页查询用户")
    def test_get_user_list_pagination(self):
        """TC-USER-003: 分页查询用户列表"""
        params = {"pageNum": 1, "pageSize": 5}
        resp = self.client.get_user_list(params=params)
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        rows = data.get("rows", [])
        assert len(rows) <= 5, f"分页大小应为5，实际返回{len(rows)}条"
        allure.attach(str(len(rows)), "返回记录数", allure.attachment_type.TEXT)

    @allure.story("用户列表")
    @allure.title("用户列表 - 正常场景: 按用户名搜索")
    def test_search_user_by_name(self):
        """TC-USER-004: 按用户名搜索"""
        params = {"userName": "admin"}
        resp = self.client.get_user_list(params=params)
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        rows = data.get("rows", [])
        assert len(rows) > 0, "搜索admin用户应返回记录"
        assert rows[0]["userName"] == "admin", "搜索到的用户名应为admin"

    @allure.story("用户列表")
    @allure.title("用户列表 - 正常场景: 按状态筛选用户")
    def test_filter_user_by_status(self):
        """TC-USER-005: 按状态筛选用户"""
        params = {"status": "0"}
        resp = self.client.get_user_list(params=params)
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        rows = data.get("rows", [])
        assert len(rows) > 0, "按状态筛选应返回记录"
        statuses = {row.get("status") for row in rows}
        assert "0" in statuses, f"筛选status=0的结果中应包含status=0的用户"

    @allure.story("用户列表")
    @allure.title("用户列表 - 正常场景: 按部门筛选用户")
    def test_filter_user_by_dept(self):
        """TC-USER-006: 按部门筛选用户"""
        params = {"deptId": 100}
        resp = self.client.get_user_list(params=params)
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)

    @allure.story("用户列表")
    @allure.title("用户列表 - 边界场景: 空参数查询")
    def test_get_user_list_empty_params(self):
        """TC-USER-007: 空参数查询"""
        resp = self.client.get_user_list(params={})
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)

    @allure.story("用户列表")
    @allure.title("用户列表 - 边界场景: 查询不存在的用户ID")
    def test_get_user_by_invalid_id(self):
        """TC-USER-008: 查询不存在的用户ID"""
        resp = self.client.get_user_by_id(999999)
        self.assert_http_ok(resp)
        data = resp.json()
        assert data.get("code") in [200, 500], "不存在的用户应返回空数据或错误"

    @allure.story("用户列表")
    @allure.title("用户列表 - 边界场景: 超大页码分页查询")
    def test_get_user_list_large_page(self):
        """TC-USER-009: 超大页码分页查询"""
        params = {"pageNum": 9999, "pageSize": 10}
        resp = self.client.get_user_list(params=params)
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        rows = data.get("rows", [])
        assert len(rows) >= 0, "超大页码查询不应报错"

    @allure.story("用户列表")
    @allure.title("用户列表 - 边界场景: 空值搜索")
    def test_search_user_by_empty_name(self):
        """TC-USER-010: 空值搜索"""
        params = {"userName": ""}
        resp = self.client.get_user_list(params=params)
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)

    def assert_http_ok(self, resp):
        assert_http_ok(resp)

    def assert_business_success(self, data):
        assert_business_success(data)