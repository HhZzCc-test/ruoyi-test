# -*- coding: utf-8 -*-
"""真实环境自检（跑 live 回归前必做）。

按顺序验证 6 件事，任何一步失败就明确指出卡在哪，避免把环境问题误判成用例问题：

    1  后端端口：探测 18080 / 8080 等常见端口，哪个在监听
    2  接口连通：GET /captchaImage 能不能拿到 uuid
    3  Redis    ：能不能读到 captcha_codes:{uuid}（简历里「直连 Redis 读验证码」的实证）
    4  登录链路 ：用真实验证码 POST /login admin/admin123 能不能拿到 token
    5  客户端参数：验证 RuoyiApiClient 有没有把 params 传给服务端（已知可疑）
    6  live 回归前置条件汇总

用法：
    python check_live_env.py                 # 自动探测端口
    python check_live_env.py --base http://localhost:18080
    python check_live_env.py --user admin --password admin123
"""
from __future__ import annotations

import argparse
import json
import socket
import sys

import requests

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PORTS = [18080, 8080, 18081, 9090, 8000]
OK, BAD, WARN, DIM, END = "\033[32m", "\033[31m", "\033[35m", "\033[90m", "\033[0m"


def line(msg: str = "") -> None:
    print(msg)


def tcp_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    with socket.socket() as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=None, help="被测服务地址，默认自动探测")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", default="admin123")
    ap.add_argument("--redis-host", default="localhost")
    ap.add_argument("--redis-port", type=int, default=6379)
    args = ap.parse_args()

    base = args.base
    line("=" * 72)
    line("真实环境自检")
    line("=" * 72)

    # ---- 1 端口 --------------------------------------------------------
    line("")
    line("[1] 后端端口探测")
    if base is None:
        for p in PORTS:
            if tcp_open(p):
                line("    %s127.0.0.1:%d 在监听%s" % (OK, p, END))
                if base is None:
                    base = "http://127.0.0.1:%d" % p
            else:
                line("    %s127.0.0.1:%d 未监听%s" % (DIM, p, END))
        if base is None:
            line("    %s✗ 常见端口都没监听 —— 若依后端还没起来%s" % (BAD, END))
            line("    提示：测试代码里写死的是 18080（若依默认是 8080）")
            return 1
    line("    使用被测地址: %s%s%s" % (OK, base, END))

    # ---- 2 验证码 ------------------------------------------------------
    line("")
    line("[2] GET /captchaImage")
    try:
        r = requests.get(base + "/captchaImage", timeout=5)
    except Exception as e:
        line("    %s✗ 请求失败: %s: %s%s" % (BAD, type(e).__name__, e, END))
        return 1
    line("    HTTP %s" % r.status_code)
    try:
        data = r.json()
    except Exception:
        line("    %s✗ 响应不是 JSON: %s%s" % (BAD, r.text[:200], END))
        return 1
    uuid = data.get("uuid", "")
    line("    body: code=%s uuid=%s captchaEnabled=%s"
         % (data.get("code"), uuid[:12] + "..." if uuid else "(空)", data.get("captchaEnabled")))
    if data.get("captchaEnabled") is False:
        line("    %s⚠ 该实例关闭了验证码（captchaEnabled=false），Redis 那步不再是必需%s" % (WARN, END))
    if not uuid and data.get("captchaEnabled") is not False:
        line("    %s✗ 没拿到 uuid%s" % (BAD, END))
        return 1

    # ---- 3 Redis ------------------------------------------------------
    line("")
    line("[3] 从 Redis 读验证码答案（captcha_codes:%s）" % (uuid[:12] + "..." if uuid else "-"))
    captcha_code = None
    try:
        import redis
        rd = redis.Redis(host=args.redis_host, port=args.redis_port,
                         protocol=2, decode_responses=True)
        line("    PING -> %s" % rd.ping())
        if uuid:
            raw = rd.get("captcha_codes:%s" % uuid)
            line("    GET captcha_codes:%s -> %s" % (uuid[:12] + "...", repr(raw)))
            if raw:
                captcha_code = raw.strip('"')
                line("    %s✓ 读到验证码答案: %s%s%s" % (OK, OK, captcha_code, END))
            else:
                line("    %s✗ 键不存在（可能已过期，或验证码开关关闭）%s" % (BAD, END))
    except Exception as e:
        line("    %s✗ Redis 不可用: %s: %s%s" % (BAD, type(e).__name__, e, END))

    # ---- 4 登录 --------------------------------------------------------
    line("")
    line("[4] POST /login（%s / %s + 真实验证码）" % (args.user, args.password))
    token = ""
    if captcha_code is None and data.get("captchaEnabled") is not False:
        line("    %s⚠ 拿不到验证码答案，登录大概率失败 —— 先修第 3 步%s" % (WARN, END))
    try:
        r = requests.post(base + "/login", timeout=8, json={
            "username": args.user, "password": args.password,
            "code": captcha_code or "1234", "uuid": uuid})
        body = r.json() if r.headers.get("Content-Type", "").startswith("application/json") else {}
        token = body.get("token", "") or ""
        line("    HTTP %s  code=%s msg=%s" % (r.status_code, body.get("code"), body.get("msg")))
        if token:
            line("    %s✓ 登录成功，token 前 20 位: %s%s..." % (OK, OK, token[:20]))
        else:
            line("    %s✗ 没拿到 token%s" % (BAD, END))
    except Exception as e:
        line("    %s✗ 请求失败: %s: %s%s" % (BAD, type(e).__name__, e, END))

    # ---- 5 params 是否真的传给服务端 ------------------------------------
    line("")
    line("[5] RuoyiApiClient 有没有把 params 传给服务端（已知可疑点）")
    if not token:
        line("    %s跳过（没有 token）%s" % (DIM, END))
    else:
        h = {"Authorization": "Bearer %s" % token}
        raw = requests.get(base + "/system/user/list", headers=h,
                           params={"pageNum": 1, "pageSize": 1}, timeout=8).json()
        raw_n = len(raw.get("rows") or [])
        line("    直接用 requests 传 pageSize=1      -> rows=%d  (服务端遵守参数? %s)"
             % (raw_n, "是" if raw_n == 1 else "否"))
        try:
            sys.path.insert(0, ".")
            from tests.core.client import RuoyiApiClient
            c = RuoyiApiClient(base)
            c.set_auth_header(token)
            cli = c.get_user_list(params={"pageNum": 1, "pageSize": 1}).json()
            cli_n = len(cli.get("rows") or [])
            line("    经 RuoyiApiClient.get_user_list -> rows=%d" % cli_n)
            if raw_n == 1 and cli_n != 1:
                line("    %s✗ 确认 BUG：client 把 params 丢了（调用方传了 pageSize=1 却没生效）%s"
                     % (BAD, END))
                line("      影响：tests/system/test_user.py 里 4 条分页/搜索用例从未真正生效，")
                line("            它们因为库里用户少而「巧合通过」")
            elif raw_n == cli_n:
                line("    %s✓ 参数传递正常%s" % (OK, END))
        except Exception as e:
            line("    %s✗ 调用 client 失败: %s: %s%s" % (BAD, type(e).__name__, e, END))

    # ---- 6 汇总 --------------------------------------------------------
    line("")
    line("[6] 结论")
    ready = bool(token)
    if ready:
        line("    %s✓ 环境就绪，可以跑真实回归：%s" % (OK, END))
        line("        python -m pytest tests -m smoke        # 21 处 smoke")
        line("        python -m pytest tests                  # 全量 116 collected")
        line("        python -m aitest analyze --junit allure-results/report.xml")
    else:
        line("    %s✗ 环境未就绪（见上面 ✗ 的那一步）%s" % (BAD, END))
    line("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
