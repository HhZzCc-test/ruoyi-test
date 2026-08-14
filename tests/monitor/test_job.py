import pytest
import requests
import allure
from tests.core.assertions import assert_http_ok, assert_business_success


@allure.feature("系统监控-定时任务")
class TestJob:

    @pytest.fixture(autouse=True)
    def _setup(self, auth_token):
        self._token = auth_token

    @allure.story("定时任务列表")
    @allure.title("定时任务列表 - 正常场景: 获取定时任务列表")
    @pytest.mark.smoke
    def test_get_job_list(self):
        """TC-JOB-001: 获取定时任务列表"""
        resp = self.client.get_job_list()
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert "rows" in data, "返回数据应包含rows字段"
        assert isinstance(data.get("rows"), list), "rows应为列表类型"

    @allure.story("定时任务列表")
    @allure.title("定时任务列表 - 异常场景: 未认证访问")
    @pytest.mark.critical
    def test_get_job_list_no_auth(self):
        """TC-JOB-002: 未认证访问定时任务列表"""
        resp = requests.get(
            self.client._url("/monitor/job/list"),
            headers={"Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "未认证应返回401"

    @allure.story("定时任务列表")
    @allure.title("定时任务列表 - 异常场景: 无效Token访问")
    @pytest.mark.critical
    def test_get_job_list_invalid_token(self):
        """TC-JOB-003: 无效Token访问定时任务列表"""
        resp = requests.get(
            self.client._url("/monitor/job/list"),
            headers={"Authorization": "Bearer invalid_token_12345", "Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "无效Token应返回401"

    @allure.story("定时任务列表")
    @allure.title("定时任务列表 - 边界场景: 按任务名称搜索")
    def test_filter_job_by_name(self):
        """TC-JOB-004: 按任务名称搜索定时任务"""
        params = {"jobName": "test"}
        resp = self.client.get_job_list(params=params)
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)

    @allure.story("定时任务详情")
    @allure.title("定时任务详情 - 正常场景: 获取存在的定时任务")
    @pytest.mark.smoke
    def test_get_job_by_id(self):
        """TC-JOB-005: 获取存在的定时任务详情"""
        resp = self.client.get_job_by_id(1)
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert "data" in data, "返回数据应包含data字段"

    @allure.story("定时任务详情")
    @allure.title("定时任务详情 - 异常场景: 不存在的任务ID")
    def test_get_job_by_id_nonexistent(self):
        """TC-JOB-006: 获取不存在的定时任务"""
        resp = self.client.get_job_by_id(999999)
        assert_http_ok(resp)
        assert resp.json().get("code") == 200, "不存在任务应返回200"

    @allure.story("定时任务详情")
    @allure.title("定时任务详情 - 边界场景: 任务ID为0")
    def test_get_job_by_id_zero(self):
        """TC-JOB-007: 任务ID为0"""
        resp = self.client.get_job_by_id(0)
        assert_http_ok(resp)
        assert resp.json().get("code") == 200, "ID为0应返回200"
