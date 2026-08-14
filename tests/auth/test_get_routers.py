import pytest
import allure
import time

from tests.core.base import BaseTest


@allure.feature("认证模块")
@allure.story("路由接口")
class TestGetRouters(BaseTest):

    @allure.title("获取路由 - 正常: 已登录用户")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_routers_with_auth(self, auth_headers):
        resp = self.client.get_routers(headers=auth_headers)
        self.assert_http_ok(resp)

        data = resp.json()
        self.assert_business_success(data)
        self.assert_field_not_empty(data, "data")

    @allure.title("获取路由 - 权限: 无Token")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_routers_without_token(self, no_auth_headers):
        resp = self.client.get_routers(headers=no_auth_headers)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())

    @allure.title("获取路由 - 权限: 无效Token")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_routers_invalid_token(self, invalid_token_headers):
        resp = self.client.get_routers(headers=invalid_token_headers)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())

    @allure.title("获取路由 - 权限: 过期Token")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_routers_expired_token(self, expired_token_headers):
        resp = self.client.get_routers(headers=expired_token_headers)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())

    @allure.title("获取路由 - 响应时间")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_routers_response_time(self, auth_headers):
        start = time.time()
        resp = self.client.get_routers(headers=auth_headers)
        elapsed = time.time() - start

        self.assert_http_ok(resp)
        self.assert_response_time(elapsed)