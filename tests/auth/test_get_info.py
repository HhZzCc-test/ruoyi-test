import pytest
import allure
import time

from tests.core.base import BaseTest


@allure.feature("认证模块")
@allure.story("用户信息接口")
class TestGetInfo(BaseTest):

    @allure.title("获取用户信息 - 正常: 已登录用户")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_info_with_auth(self, auth_headers):
        resp = self.client.get_info(headers=auth_headers)
        self.assert_http_ok(resp)

        data = resp.json()
        self.assert_business_success(data)

        user_data = data.get("user") or data.get("data")
        assert user_data is not None, "用户数据为空"

        if isinstance(user_data, dict):
            for field in ("userName", "nickName"):
                if field in user_data:
                    self.assert_field_not_empty(user_data, field)

    @allure.title("获取用户信息 - 权限: {desc}")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("fixture_name,desc", [
        pytest.param("no_auth_headers", "无Token", id="without_token"),
        pytest.param("invalid_token_headers", "无效Token", id="invalid_token"),
        pytest.param("expired_token_headers", "过期Token", id="expired_token"),
    ])
    def test_get_info_permission_denied(self, fixture_name, desc, request):
        headers = request.getfixturevalue(fixture_name)
        resp = self.client.get_info(headers=headers)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())

    @allure.title("获取用户信息 - 响应时间")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_info_response_time(self, auth_headers):
        start = time.time()
        resp = self.client.get_info(headers=auth_headers)
        elapsed = time.time() - start

        self.assert_http_ok(resp)
        self.assert_response_time(elapsed)