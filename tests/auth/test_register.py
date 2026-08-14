import pytest
import allure

from tests.core.base import BaseTest


@allure.feature("认证模块")
@allure.story("注册接口")
class TestRegister(BaseTest):

    @allure.title("注册 - 正常: 新用户注册")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_success(self):
        code, uuid = self.get_captcha_code_and_uuid()
        unique_user = self.client.generate_unique_username()

        resp = self.client.register(unique_user, "Test123456", code, uuid)
        self.assert_http_ok(resp)

        data = resp.json()
        if data.get("code") == 500 and "没有开启注册功能" in data.get("msg", ""):
            pytest.skip("系统未开启注册功能")
        self.assert_business_success(data)

    @allure.title("注册 - 正常: 边界值用户名")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("username", [
        pytest.param("ab", id="boundary_min"),
        pytest.param("a" * 30, id="boundary_max"),
    ])
    def test_register_boundary_username(self, username):
        code, uuid = self.get_captcha_code_and_uuid()

        resp = self.client.register(username, "Test123456", code, uuid)
        self.assert_http_ok(resp)
        data = resp.json()
        if data.get("code") == 500 and "没有开启注册功能" in data.get("msg", ""):
            pytest.skip("系统未开启注册功能")

    @allure.title("注册 - 异常: 参数为空")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("empty_field", [
        pytest.param("username", id="empty_username"),
        pytest.param("password", id="empty_password"),
        pytest.param("code", id="empty_code"),
        pytest.param("uuid", id="empty_uuid"),
    ])
    def test_register_empty_params(self, empty_field):
        code, uuid = self.get_captcha_code_and_uuid()
        payload = {
            "username": self.client.generate_unique_username(),
            "password": "Test123456",
            "code": code,
            "uuid": uuid,
        }
        payload[empty_field] = ""

        resp = self.client.register(**payload)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())

    @allure.title("注册 - 异常: 缺少参数")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("missing_field", [
        pytest.param("username", id="missing_username"),
        pytest.param("password", id="missing_password"),
        pytest.param("code", id="missing_code"),
        pytest.param("uuid", id="missing_uuid"),
    ])
    def test_register_missing_params(self, missing_field):
        code, uuid = self.get_captcha_code_and_uuid()
        payload = {
            "username": self.client.generate_unique_username(),
            "password": "Test123456",
            "code": code,
            "uuid": uuid,
        }
        payload[missing_field] = None

        resp = self.client.register(**payload)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())

    @allure.title("注册 - 异常: 重复用户名")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_duplicate_username(self):
        code1, uuid1 = self.get_captcha_code_and_uuid()
        unique_user = self.client.generate_unique_username()

        resp1 = self.client.register(unique_user, "Test123456", code1, uuid1)
        self.assert_http_ok(resp1)

        code2, uuid2 = self.get_captcha_code_and_uuid()
        resp2 = self.client.register(unique_user, "Test123456", code2, uuid2)
        self.assert_http_ok(resp2)
        self.assert_business_error(resp2.json())

    @allure.title("注册 - 异常: 弱密码")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("weak_password", [
        pytest.param("123", id="too_short"),
        pytest.param("12345678", id="digits_only"),
    ])
    def test_register_weak_password(self, weak_password):
        code, uuid = self.get_captcha_code_and_uuid()
        unique_user = self.client.generate_unique_username()

        resp = self.client.register(unique_user, weak_password, code, uuid)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())

    @allure.title("注册 - 异常: 密码超长")
    @allure.severity(allure.severity_level.NORMAL)
    def test_register_password_too_long(self):
        code, uuid = self.get_captcha_code_and_uuid()
        unique_user = self.client.generate_unique_username()

        resp = self.client.register(unique_user, "a" * 100, code, uuid)
        self.assert_http_ok(resp)
        self.assert_business_error(resp.json())