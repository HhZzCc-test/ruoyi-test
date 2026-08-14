import allure
from tests.core.client import RuoyiApiClient
from tests.core.assertions import (
    assert_http_ok,
    assert_business_success,
    assert_business_error,
    assert_field_exists,
    assert_field_not_empty,
    assert_field_type,
    assert_response_time,
    assert_all_unique,
)


class BaseTest:
    """测试基类 - 提供公共断言和API客户端"""

    BASE_URL = "http://localhost:18080"

    @classmethod
    def setup_class(cls):
        cls.client = RuoyiApiClient(cls.BASE_URL)

    def assert_http_ok(self, resp, msg=None):
        assert_http_ok(resp, msg)

    def assert_business_success(self, data, msg=None):
        assert_business_success(data, msg)

    def assert_business_error(self, data, msg=None):
        assert_business_error(data, msg)

    def assert_field_exists(self, data, field, msg=None):
        assert_field_exists(data, field, msg)

    def assert_field_not_empty(self, data, field, msg=None):
        assert_field_not_empty(data, field, msg)

    def assert_field_type(self, data, field, expected_type, msg=None):
        assert_field_type(data, field, expected_type, msg)

    def assert_response_time(self, elapsed, max_seconds=3.0, msg=None):
        assert_response_time(elapsed, max_seconds, msg)

    def assert_all_unique(self, items, msg=None):
        assert_all_unique(items, msg)

    def get_captcha_uuid(self):
        resp = self.client.get_captcha()
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        return data.get("uuid", "")

    def get_captcha_code_and_uuid(self):
        resp = self.client.get_captcha()
        self.assert_http_ok(resp)
        data = resp.json()
        self.assert_business_success(data)
        uuid = data.get("uuid", "")
        code = self.client._get_captcha_code(uuid) or "1234"
        return code, uuid