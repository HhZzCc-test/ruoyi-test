import pytest
import allure
import time

from tests.core.base import BaseTest


@allure.feature("认证模块")
@allure.story("验证码接口")
class TestCaptchaImage(BaseTest):

    @allure.title("获取验证码 - 正常场景")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_get_captcha_success(self):
        with allure.step("发送GET请求获取验证码"):
            resp = self.client.get_captcha()

        self.assert_http_ok(resp)

        data = resp.json()
        self.assert_business_success(data)

        self.assert_field_exists(data, "uuid")
        self.assert_field_not_empty(data, "uuid")
        self.assert_field_type(data, "uuid", str)

        self.assert_field_exists(data, "img")
        self.assert_field_not_empty(data, "img")
        self.assert_field_type(data, "img", str)

        self.assert_field_type(data, "code", int)
        self.assert_field_type(data, "msg", str)

    @allure.title("获取验证码 - 多次请求UUID唯一性")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_captcha_unique_uuids(self):
        uuids = []
        for i in range(3):
            with allure.step(f"第{i+1}次请求验证码"):
                resp = self.client.get_captcha()
                self.assert_http_ok(resp)
                uuids.append(resp.json().get("uuid"))

        self.assert_all_unique(uuids, "多次请求的uuid应互不相同")

    @allure.title("获取验证码 - 响应时间")
    @allure.severity(allure.severity_level.NORMAL)
    def test_get_captcha_response_time(self):
        start = time.time()
        resp = self.client.get_captcha()
        elapsed = time.time() - start

        self.assert_http_ok(resp)
        self.assert_response_time(elapsed)