import pytest
import requests
import allure
from tests.core.assertions import assert_http_ok, assert_business_success


@allure.feature("系统监控-缓存监控")
class TestCache:

    @pytest.fixture(autouse=True)
    def _setup(self, auth_token):
        self._token = auth_token

    @allure.story("缓存总览")
    @allure.title("缓存监控 - 正常场景: 获取缓存总览信息")
    @pytest.mark.smoke
    def test_get_cache_info(self):
        """TC-CACHE-001: 获取缓存总览信息"""
        resp = self.client.get_cache_info()
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert "data" in data, "应包含data字段"
        assert isinstance(data.get("data"), dict), "data应为字典"
        cache_data = data["data"]
        for field in ["info", "dbSize", "commandStats"]:
            assert field in cache_data, f"data应包含{field}字段"

    @allure.story("缓存总览")
    @allure.title("缓存监控 - 异常场景: 未认证访问")
    @pytest.mark.critical
    def test_get_cache_info_no_auth(self):
        """TC-CACHE-002: 未认证访问缓存监控"""
        resp = requests.get(
            self.client._url("/monitor/cache"),
            headers={"Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "未认证应返回401"

    @allure.story("缓存总览")
    @allure.title("缓存监控 - 异常场景: 无效Token访问")
    @pytest.mark.critical
    def test_get_cache_info_invalid_token(self):
        """TC-CACHE-003: 无效Token访问缓存监控"""
        resp = requests.get(
            self.client._url("/monitor/cache"),
            headers={"Authorization": "Bearer invalid_token_12345", "Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "无效Token应返回401"

    @allure.story("缓存名称列表")
    @allure.title("缓存名称列表 - 正常场景: 获取所有缓存名称")
    @pytest.mark.smoke
    def test_get_cache_names(self):
        """TC-CACHE-004: 获取所有缓存名称"""
        resp = self.client.get_cache_names()
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert "data" in data, "应包含data字段"
        assert isinstance(data.get("data"), list), "data应为列表"

    @allure.story("缓存名称列表")
    @allure.title("缓存名称列表 - 异常场景: 未认证访问")
    @pytest.mark.critical
    def test_get_cache_names_no_auth(self):
        """TC-CACHE-005: 未认证访问缓存名称列表"""
        resp = requests.get(
            self.client._url("/monitor/cache/getNames"),
            headers={"Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "未认证应返回401"

    @allure.story("缓存键名列表")
    @allure.title("缓存键名列表 - 正常场景: 获取指定缓存的所有键名")
    def test_get_cache_keys(self):
        """TC-CACHE-006: 获取指定缓存的所有键名"""
        names_resp = self.client.get_cache_names()
        names_data = names_resp.json()
        cache_names = names_data.get("data", [])
        if not cache_names:
            pytest.skip("无可用缓存名称")
        cache_name = cache_names[0]
        resp = self.client.get_cache_keys(cache_name)
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert "data" in data, "应包含data字段"

    @allure.story("缓存键名列表")
    @allure.title("缓存键名列表 - 异常场景: 不存在的缓存名")
    def test_get_cache_keys_nonexistent(self):
        """TC-CACHE-007: 查询不存在缓存的键名"""
        resp = self.client.get_cache_keys("nonexistent_cache")
        assert_http_ok(resp)
        assert resp.json().get("code") == 200, "不存在缓存应返回200"

    @allure.story("缓存值查询")
    @allure.title("缓存值查询 - 正常场景: 获取指定键的缓存值")
    def test_get_cache_value(self):
        """TC-CACHE-008: 获取指定键的缓存值"""
        names_resp = self.client.get_cache_names()
        names_data = names_resp.json()
        cache_names = names_data.get("data", [])
        if not cache_names:
            pytest.skip("无可用缓存名称")
        cache_name = cache_names[0]
        keys_resp = self.client.get_cache_keys(cache_name)
        keys_data = keys_resp.json()
        cache_keys = keys_data.get("data", [])
        if not cache_keys:
            pytest.skip("无可用缓存键名")
        cache_key = cache_keys[0] if isinstance(cache_keys[0], str) else str(cache_keys[0])
        resp = self.client.get_cache_value(cache_name, cache_key)
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)

    @allure.story("缓存值查询")
    @allure.title("缓存值查询 - 异常场景: 不存在的缓存键")
    def test_get_cache_value_nonexistent(self):
        """TC-CACHE-009: 查询不存在的缓存键值"""
        resp = self.client.get_cache_value("nonexistent", "nonexistent")
        assert_http_ok(resp)
        assert resp.json().get("code") == 200, "不存在缓存键应返回200"
