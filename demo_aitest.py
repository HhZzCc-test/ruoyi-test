# -*- coding: utf-8 -*-
"""aitest 作用演示 —— 一条命令看清这个模块到底做了什么。

不依赖若依服务、不依赖 Redis、不依赖 API Key，几秒跑完：

    第 0 步  接口文档  →  结构化元数据（机器抠出「人懒得抄」的参数约束）
    第 1 步  元数据    →  34 条用例草稿 + 覆盖度报告
    第 2 步  规则层拦下典型坏用例（含最危险的「只断言 HTTP 200」）
    第 3 步  ★ 同一份代码、同一个真缺陷，两种断言口径 → 两种结局
    第 4 步  失败归因：规则先拦环境问题，模型只处理剩下的

用法：
    python demo_aitest.py                 # 只看终端输出
    python demo_aitest.py --html          # 同时生成可视化报告 reports/ai/demo_report.html
    python demo_aitest.py --html out.html # 指定报告路径

说明：第 3 步会临时在 127.0.0.1 上起一个「有 bug 的假若依」来演示断言口径的差别。
      aitest 模块本身零 HTTP 调用，这个假服务只是为了让差别看得见。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib import request as urlrequest

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aitest import case_rules                                    # noqa: E402
from aitest.analyzer import FailureAnalyzer, render_report       # noqa: E402
from aitest.generator import CaseGenerator                       # noqa: E402
from aitest.llm import MockProvider                              # noqa: E402
from aitest.models import TestCase                               # noqa: E402
from aitest.swagger_parser import load_spec, parse_swagger       # noqa: E402

SPEC = os.path.join(ROOT, "specs", "ruoyi-openapi.json")
JUNIT = os.path.join(ROOT, "examples", "junit-sample.xml")
DEFAULT_HTML = os.path.join(ROOT, "reports", "ai", "demo_report.html")

# ----------------------------------------------------------------------
# 输出层：同一份内容，终端和 HTML 两种渲染
# ----------------------------------------------------------------------
OUT = []          # [(kind, text)]
_USE_COLOR = sys.stdout.isatty()

_COLORS = {"h1": "\033[1;36m", "h2": "\033[1;33m", "ok": "\033[32m",
           "bad": "\033[31m", "dim": "\033[90m", "warn": "\033[35m",
           "text": "", "code": ""}


def emit(kind: str, text: str = "") -> None:
    OUT.append((kind, text))
    if _USE_COLOR and _COLORS.get(kind):
        print("%s%s\033[0m" % (_COLORS[kind], text))
    else:
        print(text)


def rule(char: str = "-", n: int = 74) -> None:
    emit("dim", char * n)


def wrap(text: str, width: int = 72, indent: str = "  ") -> None:
    """按宽度折行输出（中文按 2 列算），避免长句糊成一片。"""
    line, cur = "", 0
    for ch in text:
        w = 2 if ord(ch) > 0x2E80 else 1
        if cur + w > width:
            emit("text", indent + line)
            line, cur = "", 0
        line += ch
        cur += w
    if line:
        emit("text", indent + line)


# ======================================================================
# 第 0 步：接口文档 → 结构化元数据
# ======================================================================
def step0():
    emit("h1", "")
    emit("h1", "第 0 步  接口文档 → 结构化元数据：机器抠出「人懒得抄」的约束")
    rule("=")
    endpoints = parse_swagger(load_spec(SPEC), spec_source=SPEC)
    emit("text", "  输入：specs/ruoyi-openapi.json（一份静态 Swagger 文件，没有连任何服务）")
    emit("text", "  产出：%d 个接口的结构化元数据" % len(endpoints))
    emit("text", "")
    emit("dim", "  %-6s %-26s %-6s %s" % ("方法", "路径", "鉴权", "从文档里抠出的参数约束"))
    rule()
    for e in endpoints:
        cons = []
        for p in e.params:
            bits = [p.name]
            if p.required:
                bits.append("必填")
            if p.max_length is not None:
                bits.append("maxLength=%d" % p.max_length)
            if p.enum:
                bits.append("enum=%s" % ",".join(str(v) for v in p.enum[:4]))
            cons.append("[%s]" % " ".join(bits))
        emit("text", "  %-6s %-26s %-6s %s"
             % (e.method, e.path, "是" if e.need_auth else "否",
                " ".join(cons) if cons else "(无参数)"))
    rule()
    emit("warn", "  ▸ 这些 maxLength / enum / 必填 全都写在文档里，但人工写用例时通常只抄个大概。")
    emit("warn", "  ▸ 机器不累：上面每一条都会被写进提示词，边界值不再靠猜。")
    return endpoints


# ======================================================================
# 第 1 步：生成用例草稿 + 覆盖度
# ======================================================================
def step1(endpoints):
    emit("h1", "")
    emit("h1", "第 1 步  元数据 → 用例草稿：起点从「从零写」变成「改草稿」")
    rule("=")
    provider = MockProvider(endpoints)
    gen = CaseGenerator(provider=provider)
    cases, stats = gen.generate(endpoints)
    emit("text", "  %s" % stats.summary())
    emit("dim", "  （--provider mock：没有 Key 也能跑，但生成质量只代表流水线，不代表模型）")
    emit("text", "")
    emit("h2", "  接口覆盖度报告（每个数字都能对着 cases.json 数出来）")
    for line in case_rules.format_report(
            case_rules.coverage_report(cases, endpoints)).splitlines():
        emit("text", "    " + line)
    emit("text", "")
    emit("h2", "  抽样三条，看草稿里到底写了什么")
    picks = []
    for want in ("boundary", "normal", "auth"):
        for c in cases:
            if c.case_type == want:
                picks.append(c)
                break
    for c in picks:
        emit("ok", "  [%s] %s  <%s>" % (c.case_id, c.title, c.case_type))
        emit("text", "        接口    : %s" % c.endpoint)
        emit("text", "        测试数据: %s" % json.dumps(c.request_data, ensure_ascii=False))
        emit("text", "        预期    : %s" % c.expected)
        for a in c.assertions:
            emit("text", "        断言    : %s" % a)
        emit("text", "")
    emit("warn", "  ▸ 边界用例的数据不是编的：它来自上一步从文档里抠出的 maxLength。")
    emit("warn", "  ▸ 但这些仍然是草稿 —— 业务语义对不对，必须人工评审（cases.md 抬头就写了评审要点）。")
    return cases


# ======================================================================
# 第 2 步：规则层拦坏用例
# ======================================================================
def step2():
    emit("h1", "")
    emit("h1", "第 2 步  规则层护栏：AI 会写出坏用例，确定性规则负责拦")
    rule("=")
    good = TestCase(case_id="TC-AUTH-001", title="登录 - 正常场景", endpoint="POST /login",
                    case_type="normal", priority="P0",
                    request_data={"username": "admin", "password": "admin123",
                                  "code": "1234", "uuid": "x"},
                    expected="业务 code 为 200 且返回 token",
                    assertions=["HTTP 状态码为 200", "业务 code 为 200", "token 字段非空"])
    bad = [
        ("只断言 HTTP 200（最危险的假绿灯）",
         TestCase(case_id="TC-X-001", title="登录 - 只验证接口通", endpoint="POST /login",
                  case_type="normal", priority="P0", request_data={"username": "admin"},
                  expected="接口能访问", assertions=["HTTP 状态码为 200"])),
        ("压根没写断言",
         TestCase(case_id="TC-X-002", title="登录 - 没断言", endpoint="POST /login",
                  case_type="normal", priority="P1", request_data={"username": "admin"},
                  expected="登录成功", assertions=[])),
        ("异常用例没给具体畸形数据",
         TestCase(case_id="TC-X-003", title="登录 - 异常", endpoint="POST /login",
                  case_type="exception", priority="P1", request_data={},
                  expected="登录失败", assertions=["业务 code 不等于 200"])),
        ("用例类型写错（模型偶尔会自创类型）",
         TestCase(case_id="TC-X-004", title="登录 - 类型乱写", endpoint="POST /login",
                  case_type="positive", priority="P0", request_data={"username": "admin"},
                  expected="成功", assertions=["业务 code 为 200"])),
        ("没写预期结果",
         TestCase(case_id="TC-X-005", title="登录 - 无预期", endpoint="POST /login",
                  case_type="normal", priority="P1", request_data={"username": "admin"},
                  expected="", assertions=["业务 code 为 200"])),
    ]
    emit("dim", "  %-34s %s" % ("用例", "validate_case 的判定"))
    rule()
    problems = case_rules.validate_case(good)
    verdict = "通过 ✓" if not problems else "拦下 ✗"
    emit("ok", "  %-34s %s" % ("【合格】断言落在业务字段上", verdict))
    blocked = 0
    for label, c in bad:
        problems = case_rules.validate_case(c, require_case_id=True)
        if problems:
            blocked += 1
            emit("bad", "  %-34s 拦下 ✗  %s" % ("【坏用例】" + label, problems[0]))
            for p in problems[1:]:
                emit("dim", "  %-34s          %s" % ("", p))
        else:
            emit("warn", "  %-34s 通过（漏网）" % ("【坏用例】" + label))
    rule()
    emit("warn", "  ▸ %d/%d 条坏用例被拦下，而且拦截不需要模型、不需要网络 —— 纯确定性规则。" % (blocked, len(bad)))
    emit("warn", "  ▸ 第一行是关键：业务层返回 code=500 时 HTTP 状态码仍是 200，")
    emit("warn", "    只断言「HTTP 200」的用例在真缺陷面前 100% 放行。下一步就把这件事跑给你看。")
    return blocked, len(bad)


# ======================================================================
# 第 3 步：真缺陷面前，断言口径决定漏不漏测
# ======================================================================
class _FakeRuoYi(BaseHTTPRequestHandler):
    """故意「有 bug」的假若依：HTTP 层一切正常，业务层报错。

    真实缺陷就长这样 —— /login 返回 HTTP 200，但 body 里 code=500。
    """

    def log_message(self, *a):        # 关掉访问日志
        pass

    def _send(self, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)                       # ← 注意：永远是 200
        self.send_header("Content-Type", "application/json;charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/system/user/list"):
            self._send({"code": 200, "msg": "操作成功",
                        "rows": [{"userId": 1, "userName": "admin"},
                                 {"userId": 2, "userName": "ry"}],
                        "total": 2})
        elif self.path.startswith("/captchaImage"):
            self._send({"code": 200, "uuid": "8f3c...", "img": "base64..."})
        else:
            self._send({"code": 200, "msg": "ok"})

    def do_POST(self):
        # ★ 缺陷在这里：HTTP 200 + 业务 code 500
        self._send({"code": 500, "msg": "系统内部错误"})


def _get(base, path, method="GET", body=None):
    req = urlrequest.Request(base + path, method=method,
                             data=json.dumps(body).encode() if body else None)
    with urlrequest.urlopen(req, timeout=5) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def step3():
    emit("h1", "")
    emit("h1", "第 3 步  ★ 同一份代码、同一个真缺陷，两种断言口径 → 两种结局")
    rule("=")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _FakeRuoYi)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % port
    emit("dim", "  临时起一个有 bug 的假若依：%s（跑完就关，用完即弃）" % base)
    emit("text", "  注入的缺陷：POST /login 返回 HTTP 200，但 body 里 code=500「系统内部错误」")
    emit("text", "")
    try:
        # 用例 A：人工赶工时最常写的那种
        status, body = _get(base, "/login", "POST", {"username": "admin", "password": "x"})
        try:
            assert status == 200                       # ← 只断言 HTTP 层
            emit("bad", "  用例 A（只断言 HTTP 200）      → 通过 ✅   —— 缺陷被放过去了！")
            emit("dim", "        实际拿到: HTTP %d  body=%s" % (status, json.dumps(body, ensure_ascii=False)))
        except AssertionError:
            emit("ok", "  用例 A（只断言 HTTP 200）      → 失败")

        # 用例 B：aitest 生成风格（断言落在业务字段）
        status, body = _get(base, "/login", "POST", {"username": "admin", "password": "x"})
        try:
            assert status == 200
            assert body["code"] == 200, "业务 code 应为 200，实际 %s（%s）" % (body["code"], body["msg"])
            emit("bad", "  用例 B（断言业务 code 为 200） → 通过 👍")
        except AssertionError as e:
            emit("ok", "  用例 B（断言业务 code 为 200） → 失败 ❌  —— 缺陷被抓住了")
            emit("text", "        断言信息: %s" % e)

        # 用例 C：正常业务校验（证明不是所有断言都失败，避免「只会红」的错觉）
        status, body = _get(base, "/system/user/list?pageNum=1&pageSize=10")
        n = len(body.get("rows") or [])
        ok = status == 200 and body["code"] == 200 and n == body["total"]
        emit("ok" if ok else "bad",
             "  用例 C（列表 rows 数 = total）  → %s   —— 正常接口正常通过" % ("通过 ✅" if ok else "失败"))
        emit("dim", "        实际拿到: rows=%d total=%d" % (n, body["total"]))
    finally:
        srv.shutdown()
        srv.server_close()
    rule()
    emit("warn", "  ▸ 三条用例打的是同一个服务、同一份代码。区别只在「断言写在哪一层」。")
    emit("warn", "  ▸ 用例 A 是人工赶工时最常见的写法，它会让这个缺陷一路绿灯进生产。")
    emit("warn", "  ▸ aitest 生成的就是用例 B 那种断言（规则层强制断言命中 code/rows/total 等业务字段）。")
    emit("warn", "  ▸ 注意：这个假服务是演示用的，aitest 本身一行 HTTP 调用都没有。")


# ======================================================================
# 第 4 步：失败归因，规则先拦、模型只处理剩下的
# ======================================================================
def step4():
    emit("h1", "")
    emit("h1", "第 4 步  失败归因：规则先拦环境问题，模型只处理真正需要判断的")
    rule("=")
    from aitest.cli import _parse_junit
    failures = _parse_junit(JUNIT)
    emit("text", "  输入：examples/junit-sample.xml（5 条用例、3 条失败）")
    emit("text", "")
    report = FailureAnalyzer(provider=MockProvider(), max_items_per_call=5).analyze(failures)
    s = report["summary"]
    emit("h2", "  分类统计")
    emit("text", "    环境问题 %d 条   ← 正则直接判定，没花模型调用" % s.get("env", 0))
    emit("text", "    用例问题 %d 条" % s.get("case", 0))
    emit("text", "    疑似真实缺陷 %d 条" % s.get("product", 0))
    emit("text", "    待人工确认 %d 条  ← 需要模型判断的那部分" % s.get("unknown", 0))
    emit("text", "")
    emit("h2", "  逐条结论（source=rule 是规则判的，source=ai 是模型判的）")
    for it in report["items"]:
        tag = "规则" if it["source"] == "rule" else "模型"
        emit("ok" if it["source"] == "rule" else "warn",
             "  [%s·%s] %s" % (tag, it["issue"], it["test"]))
        emit("text", "        结论: %s" % it["reason"])
        for ev in it.get("evidence", []):
            emit("dim", "        依据: %s" % ev)
        if it.get("suggestion"):
            emit("text", "        建议: %s" % it["suggestion"])
    rule()
    emit("warn", "  ▸ 3 条失败里 2 条被正则一眼看穿（服务没起 / Token 失效），省掉 2 次模型调用。")
    emit("warn", "  ▸ 剩下 1 条交给模型；现在是 mock，它如实降级成「待人工确认」而不是瞎猜 ——")
    emit("warn", "    换成真实 Key 时这条才会得到 case / env / product 的判定。")


# ======================================================================
# 第 5 步：一屏总结
# ======================================================================
def step5(cases, blocked, total_bad):
    emit("h1", "")
    emit("h1", "一屏总结：这个模块现在就能给你的三件事 + 未来的一件")
    rule("=")
    emit("ok", "  ① 覆盖度可核对      %d 个接口 → %d 条用例，哪个接口缺哪类场景一眼看到"
         % (len({c.endpoint for c in cases}), len(cases)))
    emit("ok", "  ② 假绿灯断言拦截    %d/%d 条典型坏用例被规则拦下，不依赖 AI"
         % (blocked, total_bad))
    emit("ok", "  ③ 环境问题预筛      失败先按正则分类，把模型调用留给真正需要判断的")
    emit("warn", "  ④ 草稿生成（AI 插槽）需真实 Key；34 条是 mock 产的，只证明流水线，不证明模型效果")
    emit("text", "")
    emit("text", "  它不做的：不执行用例（零 HTTP）／不猜客户端方法名（骨架留 TODO）／不下缺陷结论（标为假设）")
    emit("text", "")
    emit("dim", "  报告 HTML: python demo_aitest.py --html")
    rule("=")


# ======================================================================
# HTML 渲染
# ======================================================================
_HTML_CSS = """
* { box-sizing: border-box; }
body { margin:0; padding:28px 34px 40px; background:#f5f6f8;
       font-family:"Microsoft YaHei","Segoe UI",system-ui,sans-serif; color:#1f2328; }
.page { max-width:1080px; margin:0 auto; }
.title { font-size:23px; font-weight:700; margin:0 0 6px; }
.sub { color:#6b7280; font-size:13px; margin:0 0 22px; }
.card { background:#fff; border:1px solid #e3e6ea; border-radius:10px;
        padding:16px 20px 14px; margin:0 0 16px; }
.card > .h1 { font-size:16.5px; font-weight:700; color:#0b6bcb; margin:0 0 12px;
              padding-bottom:9px; border-bottom:1px solid #eef0f3; }
.line { font-family:"Cascadia Mono",Consolas,"Microsoft YaHei",monospace;
        font-size:12.5px; line-height:1.75; white-space:pre-wrap; word-break:break-all; }
.h2 { color:#8a6d00; font-weight:700; font-family:"Microsoft YaHei",sans-serif; }
.ok  { color:#1a7f37; }
.bad { color:#c62828; font-weight:700; }
.warn{ color:#8e24aa; }
.dim { color:#8b929c; }
.text{ color:#24292f; }
.legend { font-size:12.5px; color:#6b7280; margin:0 0 18px; }
.legend b { color:#1f2328; }
"""


def render_html(path: str, endpoints_count: int, cases_count: int) -> str:
    import html as _html
    body = []
    cur = None
    for kind, text in OUT:
        if kind == "h1":
            if cur is not None:
                body.append("</div>")
            if not text.strip():
                cur = None
                continue
            body.append('<div class="card"><div class="h1">%s</div>' % _html.escape(text))
            cur = "open"
            continue
        if cur is None:
            continue
        cls = kind if kind in ("h2", "ok", "bad", "warn", "dim", "text") else "text"
        body.append('<div class="line %s">%s</div>'
                    % (cls, _html.escape(text) if text else "&nbsp;"))
    if cur is not None:
        body.append("</div>")
    doc = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>aitest 作用演示</title><style>%s</style></head>
<body><div class="page">
<h1 class="title">aitest 作用演示</h1>
<p class="sub">%d 个接口 → %d 条用例 · 离线跑通（不需要若依服务 / Redis / API Key）·
   <b>绿色=好的结果，红色=问题或漏测，紫色=值得记住的结论</b></p>
%s
</div></body></html>
""" % (_HTML_CSS, endpoints_count, cases_count, "\n".join(body))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(doc)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="aitest 作用演示")
    ap.add_argument("--html", nargs="?", const=DEFAULT_HTML, default=None,
                    help="生成可视化报告（默认 reports/ai/demo_report.html）")
    args = ap.parse_args()

    emit("h1", "aitest 作用演示：从接口文档到用例草稿、护栏、归因")
    emit("dim", "  全程离线：不需要若依服务、不需要 Redis、不需要 API Key，几秒跑完")
    emit("dim", "  仓库: %s" % ROOT)

    endpoints = step0()
    cases = step1(endpoints)
    blocked, total_bad = step2()
    step3()
    step4()
    step5(cases, blocked, total_bad)

    if args.html:
        p = render_html(args.html, len(endpoints), len(cases))
        emit("")
        emit("ok", "  可视化报告已生成: %s" % p)
        emit("dim", "  用浏览器打开即可（不要用 IE）。")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")     # Windows 控制台中文
    except Exception:
        pass
    sys.exit(main())
