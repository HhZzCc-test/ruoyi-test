import pytest
import requests
import allure
from tests.core.assertions import assert_http_ok, assert_business_success


@allure.feature("系统监控-定时任务日志")
class TestJobLog:

    @pytest.fixture(autouse=True)
    def _setup(self, auth_token):
        self._token = auth_token

    @allure.story("定时任务日志列表")
    @allure.title("定时任务日志列表 - 正常场景: 获取日志列表")
    @pytest.mark.smoke
    def test_get_job_log_list(self):
        """TC-JOBLOG-001: 获取定时任务日志列表"""
        resp = self.client.get_job_log_list()
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert "rows" in data, "返回数据应包含rows字段"
        assert isinstance(data.get("rows"), list), "rows应为列表类型"

    @allure.story("定时任务日志列表")
    @allure.title("定时任务日志列表 - 异常场景: 未认证访问")
    @pytest.mark.critical
    def test_get_job_log_list_no_auth(self):
        """TC-JOBLOG-002: 未认证访问定时任务日志列表"""
        resp = requests.get(
            self.client._url("/monitor/jobLog/list"),
            headers={"Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "未认证应返回401"

    @allure.story("定时任务日志列表")
    @allure.title("定时任务日志列表 - 异常场景: 无效Token访问")
    @pytest.mark.critical
    def test_get_job_log_list_invalid_token(self):
        """TC-JOBLOG-003: 无效Token访问定时任务日志列表"""
        resp = requests.get(
            self.client._url("/monitor/jobLog/list"),
            headers={"Authorization": "Bearer invalid_token_12345", "Content-Type": "application/json"}
        )
        assert_http_ok(resp)
        assert resp.json().get("code") == 401, "无效Token应返回401"

    @allure.story("定时任务日志列表")
    @allure.title("定时任务日志列表 - 边界场景: 按任务名称筛选")
    def test_filter_job_log_by_name(self):
        """TC-JOBLOG-004: 按任务名称筛选日志"""
        params = {"jobName": "test"}
        resp = self.client.get_job_log_list(params=params)
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)

    @allure.story("定时任务日志详情")
    @allure.title("定时任务日志详情 - 正常场景: 获取存在的日志")
    @pytest.mark.smoke
    def test_get_job_log_by_id(self):
        """TC-JOBLOG-005: 获取存在的日志详情"""
        resp = self.client.get_job_log_by_id(1)
        assert_http_ok(resp)
        data = resp.json()
        assert_business_success(data)
        assert "data" in data or "rows" in data or data.get("code") == 200, "返回数据格式正确"

    @allure.story("定时任务日志详情")
    @allure.title("定时任务日志详情 - 异常场景: 不存在的日志ID")
    def test_get_job_log_by_id_nonexistent(self):
        """TC-JOBLOG-006: 获取不存在的日志"""
        resp = self.client.get_job_log_by_id(999999)
        assert_http_ok(resp)
        assert resp.json().get("code") == 200, "不存在日志应返回200"
