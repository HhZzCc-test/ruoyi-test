import pytest
import allure

from tests.core.base import BaseTest


@allure.feature("认证模块")
@allure.story("登录接口")
class TestLogin(BaseTest):

    login_success_data = [
        pytest.param("admin", "admin123", id="normal_login"),
        pytest.param("admin", "admin123", id="boundary_username_max"),
        pytest.param("admin", "admin123", id="boundary_username_min"),
    ]

    @allure.title("登录 - 正常场景")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("username,password", login_success_data)
    def test_login_success(self, username, password):
        code, uuid = self.get_captcha_code_and_uuid()

        with allure.step("发送登录请求"):
            resp = self.client.login(username, password, code, uuid)

        self.assert_http_ok(resp)

        data = resp.json()
        self.assert_business_success(data)

        self.assert_field_exists(data, "token")
        self.assert_field_not_empty(data, "token")

    @allure.title("登录 - 异常: 参数为空")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("empty_field", [
        pytest.param("username", id="empty_username"),
        pytest.param("password", id="empty_password"),
        pytest.param("code", id="empty_code"),
        pytest.param("uuid", id="empty_uuid"),
    ])
    def test_login_empty_params(self, empty_field):
        payload = {"username": "admin", "password": "admin123", "code": "1234", "uuid": "placeholder"}
        payload[empty_field] = ""

        resp = self.client.login(**payload)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())

    @allure.title("登录 - 异常: 缺少参数")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("missing_field", [
        pytest.param("username", id="missing_username"),
        pytest.param("password", id="missing_password"),
        pytest.param("code", id="missing_code"),
        pytest.param("uuid", id="missing_uuid"),
    ])
    def test_login_missing_params(self, missing_field):
        payload = {"username": "admin", "password": "admin123", "code": "1234", "uuid": "placeholder"}
        payload[missing_field] = None

        resp = self.client.login(**payload)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())

    @allure.title("登录 - 异常: 错误密码")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_wrong_password(self):
        code, uuid = self.get_captcha_code_and_uuid()

        resp = self.client.login("admin", "wrong_password_123", code, uuid)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())

    @allure.title("登录 - 异常: 不存在的用户")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_nonexistent_user(self):
        code, uuid = self.get_captcha_code_and_uuid()

        resp = self.client.login("nonexistent_user_xyz", "admin123", code, uuid)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())

    @allure.title("登录 - 异常: 用户名超长")
    @allure.severity(allure.severity_level.NORMAL)
    def test_login_username_too_long(self):
        code, uuid = self.get_captcha_code_and_uuid()

        resp = self.client.login("a" * 1000, "admin123", code, uuid)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())