# -*- coding: utf-8 -*-
"""由 aitest 从用例文档生成的测试骨架 — 待人工补全后提交。

生成时间: 2026-09-27T19:08:56
用例来源: DeepSeek v4-pro 新契约 + 人工评审
说明: 每个测试方法上的注释标出对应用例 ID；请求调用处需按实际
      RuoyiApiClient 方法名对齐，断言与业务语义需人工复核。
"""
import pytest
import allure

from tests.core.base import BaseTest



@allure.feature("auth")
class TestGetInfo(BaseTest):
    """GET /getInfo"""

    @allure.title("获取当前登录用户信息 - 权限: 未携带 Token")
    @allure.story("auth")
    @pytest.mark.critical
    def test_token(self):
        """TC-AUTH-001: 获取当前登录用户信息 - 权限: 未携带 Token"""
        # 前置条件: 无
        _saved_headers = {}
        _saved_headers['Authorization'] = self.client.session.headers.pop('Authorization', None)
        resp = self.client.get_info()
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            assert resp.status_code in (401, 403) or _data.get('code') in (401, 403)   # HTTP 状态码为 401
            self.assert_business_error(_data)
        # 恢复请求头
        for _k, _v in _saved_headers.items():
            if _v is None:
                self.client.session.headers.pop(_k, None)
            else:
                self.client.session.headers[_k] = _v

    @allure.title("获取当前登录用户信息 - 正常场景")
    @allure.story("normal")
    @pytest.mark.critical
    def test_case_003(self):
        """TC-AUTH-003: 获取当前登录用户信息 - 正常场景"""
        # 前置条件: 已通过登录接口获得有效 Token，用户已分配角色和权限
        resp = self.client.get_info()
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            # 断言（需人工确认）: HTTP 状态码为 200
            self.assert_business_success(_data)
            # 断言（需人工确认）: 返回体中的 user 字段为对象且非 null
            # 断言（需人工确认）: user 对象中不包含 password 字段
            # 断言（需人工确认）: roles 字段为数组类型
            # 断言（需人工确认）: permissions 字段为数组类型

    @allure.title("获取当前登录用户信息 - 边界: 用户无角色无权限")
    @allure.story("boundary")
    @pytest.mark.smoke
    def test_case_006(self):
        """TC-AUTH-006: 获取当前登录用户信息 - 边界: 用户无角色无权限"""
        # 前置条件: 假设存在一个用户，未分配任何角色和权限，即 roles 和 permissions 应为空数组；该用户已登录并持有有效 Token（接口文档未明确角色/权限边界，按常见业务约定假设空数组为合法边界）
        resp = self.client.get_info()
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            # 断言（需人工确认）: HTTP 状态码为 200
            self.assert_business_success(_data)
            # 断言（需人工确认）: roles 字段为数组且长度为 0
            # 断言（需人工确认）: permissions 字段为数组且长度为 0

    @allure.title("获取当前登录用户信息 - 异常: Authorization 头格式错误")
    @allure.story("exception")
    @pytest.mark.smoke
    def test_authorization(self):
        """TC-AUTH-010: 获取当前登录用户信息 - 异常: Authorization 头格式错误"""
        # 前置条件: 已获得有效 Token，但 Authorization 头未按 Bearer 格式携带
        _saved_headers = {}
        _saved_headers['Authorization'] = self.client.session.headers.get('Authorization')
        self.client.session.headers['Authorization'] = 'InvalidToken'
        resp = self.client.get_info()
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            assert resp.status_code in (401, 403) or _data.get('code') in (401, 403)   # HTTP 状态码为 401
            self.assert_business_error(_data)
            # 断言（需人工确认）: 返回体中的 msg 或 error 字段包含 token 无效相关提示
        # 恢复请求头
        for _k, _v in _saved_headers.items():
            if _v is None:
                self.client.session.headers.pop(_k, None)
            else:
                self.client.session.headers[_k] = _v

    @allure.title("获取当前登录用户信息 - 异常: 不支持的 HTTP 方法")
    @allure.story("exception")
    @pytest.mark.smoke
    def test_http(self):
        """TC-AUTH-011: 获取当前登录用户信息 - 异常: 不支持的 HTTP 方法"""
        # 前置条件: 已获得有效 Token
        # 用 POST 方法请求（该接口只允许 GET）
        resp = self.client.session.request('POST', self.client.base_url + '/getInfo', headers=self.client.session.headers)
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            assert resp.status_code == 405 or _data.get("code") != 200   # HTTP 状态码为 405
            self.assert_business_error(_data)


@allure.feature("auth")
class TestLogin(BaseTest):
    """POST /login"""

    @allure.title("登录 - 正常场景")
    @allure.story("normal")
    @pytest.mark.critical
    def test_case_002(self):
        """TC-AUTH-002: 登录 - 正常场景"""
        # 前置条件: 已通过 /captchaImage 获取有效 uuid 及对应验证码 code，且用户名密码正确
        _code, _uuid = self.get_captcha_code_and_uuid()
        resp = self.client.login(username="admin", password="Admin@123", code=_code, uuid=_uuid)
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            # 断言（需人工确认）: HTTP 状态码为 200
            self.assert_business_success(_data)
            # 断言（需人工确认）: token 字段非空且为字符串

    @allure.title("登录 - 边界: username/password/code 均取最大长度")
    @allure.story("boundary")
    @pytest.mark.smoke
    def test_username_password_code(self):
        """TC-AUTH-005: 登录 - 边界: username/password/code 均取最大长度"""
        # 前置条件: username maxLength=30, password maxLength=20, code maxLength=4（文档约束）；uuid 合法
        _code, _uuid = self.get_captcha_code_and_uuid()
        resp = self.client.login(username="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", password="bbbbbbbbbbbbbbbbbbbb", code=_code, uuid=_uuid)
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            # 断言（需人工确认）: HTTP 状态码为 200
            self.assert_business_success(_data)
            # 断言（需人工确认）: token 字段非空

    @allure.title("登录 - 异常: 缺少必填 username")
    @allure.story("exception")
    @pytest.mark.smoke
    def test_username(self):
        """TC-AUTH-008: 登录 - 异常: 缺少必填 username"""
        # 前置条件: username 为必填字段
        # 该接口在 client map 里没有映射，需人工按实际方法名对齐后再纳入执行
        # 请求数据: {"password": "Admin@123", "code": "1234", "uuid": "valid-uuid-123"}
        pytest.skip("接口未在 client map 中映射（POST /login），需人工补齐调用")
        # 恢复请求头
        _saved = locals().get('_saved_headers')
        if _saved:
            for _k, _v in _saved.items():
                if _v is None:
                    self.client.session.headers.pop(_k, None)
                else:
                    self.client.session.headers[_k] = _v

    @allure.title("登录 - 异常: 验证码错误")
    @allure.story("exception")
    @pytest.mark.smoke
    def test_case_009(self):
        """TC-AUTH-009: 登录 - 异常: 验证码错误"""
        # 前置条件: uuid 合法但 code 与缓存中的不一致
        _code, _uuid = self.get_captcha_code_and_uuid()
        resp = self.client.login(username="admin", password="Admin@123", code=_code, uuid=_uuid)
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            # 断言（需人工确认）: HTTP 状态码为 400
            self.assert_business_error(_data)
            # 断言（需人工确认）: msg 中包含 '验证码'

    @allure.title("登录 - 异常: username 超过最大长度 30")
    @allure.story("exception")
    def test_username_30(self):
        """TC-AUTH-013: 登录 - 异常: username 超过最大长度 30"""
        # 前置条件: username maxLength=30
        _code, _uuid = self.get_captcha_code_and_uuid()
        resp = self.client.login(username="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", password="Admin@123", code=_code, uuid=_uuid)
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            # 断言（需人工确认）: HTTP 状态码为 400
            self.assert_business_error(_data)
            # 断言（需人工确认）: msg 中包含 '长度' 或 '超长'

    @allure.title("登录 - 异常: 使用 GET 方法调用 /login")
    @allure.story("exception")
    def test_get_login(self):
        """TC-AUTH-014: 登录 - 异常: 使用 GET 方法调用 /login"""
        # 前置条件: 接口仅支持 POST 方法
        # 用 GET 方法请求（该接口只允许 POST）
        resp = self.client.session.request('GET', self.client.base_url + '/login', headers=self.client.session.headers)
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            assert resp.status_code == 405 or _data.get("code") != 200   # HTTP 状态码为 405
            self.assert_business_error(_data)
            # 断言（需人工确认）: msg 中包含 '方法' 或 '不支持'


@allure.feature("auth")
class TestCaptchaImage(BaseTest):
    """GET /captchaImage"""

    @allure.title("获取验证码 - 正常场景")
    @allure.story("normal")
    @pytest.mark.critical
    def test_case_004(self):
        """TC-AUTH-004: 获取验证码 - 正常场景"""
        # 前置条件: 无
        resp = self.client.get_captcha()
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            # 断言（需人工确认）: HTTP 状态码为 200
            self.assert_business_success(_data)
            # 断言（需人工确认）: uuid 字段非空
            # 断言（需人工确认）: img 字段非空

    @allure.title("获取验证码 - 边界: uuid 格式与 img 非空")
    @allure.story("boundary")
    @pytest.mark.smoke
    def test_uuid_img(self):
        """TC-AUTH-007: 获取验证码 - 边界: uuid 格式与 img 非空"""
        # 前置条件: 假设 uuid 为标准 UUID 格式（36 字符，8-4-4-4-12 结构），img 为 base64 图片字符串，长度至少 10
        resp = self.client.get_captcha()
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            # 断言（需人工确认）: HTTP 状态码为 200
            self.assert_business_success(_data)
            # 断言（需人工确认）: 第一次 uuid 长度等于 36
            # 断言（需人工确认）: 第一次 uuid 符合 UUID 格式（8-4-4-4-12）
            # 断言（需人工确认）: 第二次 uuid != 第一次 uuid
            # 断言（需人工确认）: 第一次 img 长度 > 10

    @allure.title("获取验证码 - 异常: 不支持的 HTTP 方法 POST")
    @allure.story("exception")
    @pytest.mark.smoke
    def test_http_post(self):
        """TC-AUTH-012: 获取验证码 - 异常: 不支持的 HTTP 方法 POST"""
        # 前置条件: 接口仅支持 GET 方法
        # 用 POST 方法请求（该接口只允许 GET）
        resp = self.client.session.request('POST', self.client.base_url + '/captchaImage', headers=self.client.session.headers)
        if resp is not None:
            self.assert_http_ok(resp)
            _data = resp.json()
            assert resp.status_code == 405 or _data.get("code") != 200   # HTTP 状态码为 405
            self.assert_business_error(_data)
