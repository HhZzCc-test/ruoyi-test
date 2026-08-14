import requests
import time
import random
import redis
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class RuoyiApiClient:
    """Ruoyi API 客户端 - 封装所有API调用"""

    def __init__(self, base_url="http://localhost:18080", redis_host="localhost", redis_port=6379):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=20,
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self._redis = redis.Redis(host=redis_host, port=redis_port, protocol=2, decode_responses=True)

    def _url(self, path):
        return f"{self.base_url}{path}"

    def _get(self, path, headers=None, params=None):
        return self.session.get(self._url(path), headers=headers, params=params)

    def _post(self, path, json_data=None, headers=None):
        return self.session.post(self._url(path), json=json_data, headers=headers)

    def _delete(self, path, headers=None):
        return self.session.delete(self._url(path), headers=headers)

    def set_auth_header(self, token):
        header = {"Authorization": f"Bearer {token}"}
        self.session.headers.update(header)
        return header

    def _get_captcha_code(self, uuid):
        try:
            code = self._redis.get(f"captcha_codes:{uuid}")
            if code:
                code = code.strip('"')
            return code
        except Exception:
            return None

    def get_captcha(self):
        resp = self._get("/captchaImage")
        return resp

    def login(self, username, password, code, uuid):
        payload = {
            "username": username,
            "password": password,
            "code": code,
            "uuid": uuid,
        }
        return self._post("/login", json_data=payload)

    def register(self, username, password, code, uuid):
        payload = {
            "username": username,
            "password": password,
            "code": code,
            "uuid": uuid,
        }
        return self._post("/register", json_data=payload)

    def get_routers(self, headers=None):
        return self._get("/getRouters", headers=headers)

    def get_info(self, headers=None):
        return self._get("/getInfo", headers=headers)

    def login_and_get_token(self, username="admin", password="admin123"):
        captcha_resp = self.get_captcha()
        captcha_data = captcha_resp.json()
        uuid = captcha_data.get("uuid", "")

        captcha_code = self._get_captcha_code(uuid)
        if captcha_code is None:
            captcha_code = "1234"

        login_resp = self.login(username, password, captcha_code, uuid)
        data = login_resp.json()
        token = data.get("token", "")
        return token

    def generate_unique_username(self, prefix="testuser"):
        return f"{prefix}_{int(time.time())}_{random.randint(1000, 9999)}"

    def get_user_list(self, params=None):
        return self._get("/system/user/list", headers=self.session.headers)

    def get_user_by_id(self, user_id):
        return self._get(f"/system/user/{user_id}", headers=self.session.headers)

    def get_role_list(self, params=None):
        return self._get("/system/role/list", headers=self.session.headers)

    def get_role_by_id(self, role_id):
        return self._get(f"/system/role/{role_id}", headers=self.session.headers)

    def get_menu_list(self, params=None):
        return self._get("/system/menu/list", headers=self.session.headers)

    def get_menu_tree(self):
        return self._get("/system/menu/treeselect", headers=self.session.headers)

    def get_dept_list(self, params=None):
        return self._get("/system/dept/list", headers=self.session.headers)

    def get_post_list(self, params=None):
        return self._get("/system/post/list", headers=self.session.headers)

    def get_dict_type_list(self, params=None):
        return self._get("/system/dict/type/list", headers=self.session.headers)

    def get_dict_data_list(self, params=None):
        return self._get("/system/dict/data/list", headers=self.session.headers)

    def get_config_list(self, params=None):
        return self._get("/system/config/list", headers=self.session.headers)

    def get_notice_list(self, params=None):
        return self._get("/system/notice/list", headers=self.session.headers)
    # ==================== 系统监控模块 ====================

    def get_online_list(self, params=None):
        return self._get("/monitor/online/list", headers=self.session.headers, params=params)

    def force_logout(self, token_id):
        return self._delete(f"/monitor/online/{token_id}", headers=self.session.headers)

    def get_job_list(self, params=None):
        return self._get("/monitor/job/list", headers=self.session.headers, params=params)

    def get_job_by_id(self, job_id):
        return self._get(f"/monitor/job/{job_id}", headers=self.session.headers)

    def get_job_log_list(self, params=None):
        return self._get("/monitor/jobLog/list", headers=self.session.headers, params=params)

    def get_job_log_by_id(self, job_log_id):
        return self._get(f"/monitor/jobLog/{job_log_id}", headers=self.session.headers)

    def get_server_info(self):
        return self._get("/monitor/server", headers=self.session.headers)

    def get_cache_info(self):
        return self._get("/monitor/cache", headers=self.session.headers)

    def get_cache_names(self):
        return self._get("/monitor/cache/getNames", headers=self.session.headers)

    def get_cache_keys(self, cache_name):
        return self._get(f"/monitor/cache/getKeys/{cache_name}", headers=self.session.headers)

    def get_cache_value(self, cache_name, cache_key):
        return self._get(f"/monitor/cache/getValue/{cache_name}/{cache_key}", headers=self.session.headers)

    def get_operlog_list(self, params=None):
        return self._get("/monitor/operlog/list", headers=self.session.headers, params=params)

    def get_logininfor_list(self, params=None):
        return self._get("/monitor/logininfor/list", headers=self.session.headers, params=params)