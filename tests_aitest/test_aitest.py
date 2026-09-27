# -*- coding: utf-8 -*-
"""aitest 模块单元测试（离线可跑，不依赖被测服务与 API Key）。

运行:
    pytest tests_aitest -v
"""
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from aitest import case_rules                      # noqa: E402
from aitest.analyzer import FailureAnalyzer, render_report, rule_prefilter  # noqa: E402
from aitest.generator import CaseGenerator, GenerationStats, render_markdown  # noqa: E402
from aitest.generator_pytest import render_module  # noqa: E402
from aitest.knowledge import KnowledgeBase, default_knowledge_base  # noqa: E402
from aitest.llm import MockProvider, extract_json  # noqa: E402
from aitest.models import Endpoint, ParamSpec, TestCase  # noqa: E402
from aitest.prompt_builder import build_prompt     # noqa: E402
from aitest.swagger_parser import load_spec, parse_swagger  # noqa: E402

SPEC_PATH = os.path.join(ROOT, "specs", "ruoyi-openapi.json")


# ----------------------------------------------------------------------
# 解析器
# ----------------------------------------------------------------------
class TestSwaggerParser:

    def test_load_and_parse(self):
        spec = load_spec(SPEC_PATH)
        endpoints = parse_swagger(spec, spec_source=SPEC_PATH)
        assert len(endpoints) == 9, "样例规格应解析出 9 个接口（8 条路径中的 userId 路径含 GET+DELETE）"

    def test_method_and_path(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        keys = {e.key for e in endpoints}
        assert "POST /login" in keys
        assert "GET /system/user/list" in keys
        assert "DELETE /system/user/{userId}" in keys

    def test_body_ref_resolved(self):
        """$ref 应被展开成真实字段，并保留约束。"""
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        login = next(e for e in endpoints if e.key == "POST /login")
        names = {p.name for p in login.params}
        assert {"username", "password", "code", "uuid"} <= names
        username = next(p for p in login.params if p.name == "username")
        assert username.required is True
        assert username.max_length == 30

    def test_query_params_with_bounds(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        listing = next(e for e in endpoints if e.key == "GET /system/user/list")
        size = next(p for p in listing.params if p.name == "pageSize")
        assert size.location == "query"
        assert size.maximum == 1000
        status = next(p for p in listing.params if p.name == "status")
        assert status.enum == ["0", "1"]

    def test_auth_detection(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        by_key = {e.key: e for e in endpoints}
        assert by_key["POST /login"].need_auth is False
        assert by_key["GET /getInfo"].need_auth is True
        assert by_key["GET /system/user/list"].need_auth is True

    def test_risk_detection(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        by_key = {e.key: e for e in endpoints}
        assert by_key["DELETE /system/user/{userId}"].risk == "high"
        assert by_key["POST /system/user"].risk == "high"
        assert by_key["GET /getInfo"].risk == "low"

    def test_module_inference(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        by_key = {e.key: e for e in endpoints}
        assert by_key["GET /system/user/list"].module == "system"
        assert by_key["GET /monitor/cache/getNames"].module == "monitor"
        assert by_key["POST /login"].module == "auth"   # 单段路径归一到语义模块

    def test_response_fields(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        listing = next(e for e in endpoints if e.key == "GET /system/user/list")
        names = {f.name for f in listing.response_fields}
        assert {"code", "total", "rows"} <= names

    def test_invalid_spec_raises(self):
        with pytest.raises(ValueError):
            parse_swagger({}, spec_source="inline")
        with pytest.raises(ValueError):
            parse_swagger({"paths": {}}, spec_source="inline")


# ----------------------------------------------------------------------
# 知识库检索
# ----------------------------------------------------------------------
class TestKnowledge:

    def test_default_kb_loaded(self):
        kb = default_knowledge_base()
        stats = kb.stats()
        assert stats["items"] >= 5
        assert stats["bullets"] >= 15

    def test_retrieve_by_path(self):
        kb = default_knowledge_base()
        ep = Endpoint(path="/system/user/list", method="GET", summary="查询用户列表")
        hits = kb.retrieve(ep)
        assert hits, "用户列表接口应命中知识库"
        titles = " ".join(h.title for h in hits)
        assert ("用户" in titles) or ("分页" in titles)

    def test_retrieve_auth(self):
        kb = default_knowledge_base()
        ep = Endpoint(path="/login", method="POST", summary="用户登录")
        hits = kb.retrieve(ep)
        assert any("认证" in h.title for h in hits)

    def test_retrieve_empty_when_irrelevant(self):
        kb = default_knowledge_base()
        ep = Endpoint(path="/zzz/yyy", method="GET", summary="无关接口")
        assert kb.retrieve(ep) == []

    def test_context_fallback_text(self):
        kb = default_knowledge_base()
        ep = Endpoint(path="/zzz/yyy", method="GET")
        assert "没有" in kb.build_context(ep)


# ----------------------------------------------------------------------
# 提示词
# ----------------------------------------------------------------------
class TestPromptBuilder:

    def test_prompt_contains_four_elements(self):
        ep = Endpoint(path="/system/user", method="POST", summary="新增用户",
                      need_auth=True,
                      params=[ParamSpec(name="userName", required=True, max_length=30)])
        parts = build_prompt(ep, default_knowledge_base())
        # 业务背景
        assert "业务背景" in parts.user
        # 约束
        assert "约束" in parts.user
        # 示例
        assert "输出示例" in parts.user
        # 输出要求
        assert "输出要求" in parts.user and "cases" in parts.user

    def test_prompt_mentions_endpoint_constraints(self):
        ep = Endpoint(path="/system/user", method="POST", summary="新增用户",
                      params=[ParamSpec(name="userName", required=True, max_length=30)])
        parts = build_prompt(ep, default_knowledge_base())
        assert "maxLength=30" in parts.user
        assert "POST /system/user" in parts.user

    def test_need_auth_adds_auth_hint(self):
        ep = Endpoint(path="/system/user/list", method="GET", need_auth=True)
        parts = build_prompt(ep, default_knowledge_base())
        assert "权限" in parts.user

    def test_no_fewshot(self):
        ep = Endpoint(path="/x", method="GET")
        parts = build_prompt(ep, KnowledgeBase([]), include_fewshot=False)
        assert "输出示例" not in parts.user

    def test_knowledge_hits_counted(self):
        ep = Endpoint(path="/login", method="POST", summary="用户登录")
        parts = build_prompt(ep, default_knowledge_base())
        assert parts.knowledge_hits >= 1


# ----------------------------------------------------------------------
# 规则层
# ----------------------------------------------------------------------
class TestCaseRules:

    def _case(self, **kw):
        base = dict(case_id="TC-X-001", title="标题", endpoint="GET /a",
                    case_type="normal", priority="P0", expected="业务 code 为 200",
                    assertions=["业务 code 为 200"])
        base.update(kw)
        return TestCase(**base)

    def test_valid_case_passes(self):
        assert case_rules.validate_case(self._case()) == []

    @pytest.mark.parametrize("field,value,keyword", [
        ("title", "", "标题"),
        ("endpoint", "", "接口标识"),
        ("case_type", "unknown", "类型非法"),
        ("priority", "P9", "优先级非法"),
        ("expected", "", "预期结果"),
        ("assertions", [], "断言清单"),
    ])
    def test_invalid_fields_detected(self, field, value, keyword):
        problems = case_rules.validate_case(self._case(**{field: value}))
        assert any(keyword in p for p in problems)

    def test_meaningless_assertion_flagged(self):
        """只断言 HTTP 200 的用例应被拦下（假绿灯风险）。"""
        problems = case_rules.validate_case(
            self._case(assertions=["HTTP 状态码为 200"]))
        assert any("假绿灯" in p for p in problems)

    def test_exception_case_needs_data(self):
        problems = case_rules.validate_case(
            self._case(case_type="exception", request_data={}))
        assert any("异常用例未给出具体请求数据" in p for p in problems)

    def test_dedupe_removes_semantic_duplicates(self):
        a = self._case(case_id="TC-A-001", request_data={"x": 1})
        b = self._case(case_id="TC-A-002", request_data={"x": 1})   # 完全同签名
        c = self._case(case_id="TC-A-003", request_data={"x": 2})
        kept, dropped = case_rules.dedupe([a, b, c])
        assert len(kept) == 2
        assert len(dropped) == 1
        assert dropped[0].diagnostics, "被剔除的用例应带诊断说明"

    def test_renumber_is_continuous(self):
        cases = [self._case(case_id="") for _ in range(3)]
        out = case_rules.renumber(cases, "sys")
        assert [c.case_id for c in out] == ["TC-SYS-001", "TC-SYS-002", "TC-SYS-003"]

    def test_coverage_report_shape(self):
        eps = parse_swagger(load_spec(SPEC_PATH))
        cases = [self._case(endpoint="GET /getInfo", case_type="normal"),
                 self._case(endpoint="GET /getInfo", case_type="auth")]
        report = case_rules.coverage_report(cases, eps)
        assert report["endpoint_total"] == 9
        assert report["endpoint_covered"] == 1
        assert len(report["endpoint_uncovered"]) == 8
        assert "GET /getInfo" in report["endpoints_missing_required_types"]
        text = case_rules.format_report(report)
        assert "接口覆盖" in text and "用例总数" in text


# ----------------------------------------------------------------------
# 生成器（用 mock provider，离线）
# ----------------------------------------------------------------------
class TestGenerator:

    def test_mock_provider_generates_cases(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        provider = MockProvider(endpoints)
        gen = CaseGenerator(provider=provider, knowledge=default_knowledge_base())
        cases, stats = gen.generate(endpoints)
        assert stats.cases_final > 0
        assert stats.endpoints_processed == len(endpoints)
        assert stats.provider == "mock"
        # 每个接口至少 3 条（normal/boundary/exception）
        assert stats.cases_final >= len(endpoints) * 3 - stats.cases_duplicated

    def test_generated_cases_are_wellformed(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        gen = CaseGenerator(provider=MockProvider(endpoints))
        cases, _ = gen.generate(endpoints)
        for c in cases:
            assert c.is_wellformed(), "生成用例必须结构合格: %s" % c.to_dict()
            assert case_rules.validate_case(c) == [], c.title

    def test_case_ids_are_continuous_per_module(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        gen = CaseGenerator(provider=MockProvider(endpoints))
        cases, _ = gen.generate(endpoints)
        import collections
        by_mod = collections.defaultdict(list)
        for c in cases:
            by_mod[c.module].append(c.case_id)
        for mod, ids in by_mod.items():
            seq = [int(i.split("-")[-1]) for i in ids]
            assert seq == list(range(1, len(ids) + 1)), "模块 %s 编号不连续: %s" % (mod, ids)

    def test_auth_endpoints_get_auth_case(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        gen = CaseGenerator(provider=MockProvider(endpoints))
        cases, _ = gen.generate(endpoints)
        auth_endpoints = {e.key for e in endpoints if e.need_auth}
        got = {c.endpoint for c in cases if c.case_type == "auth"}
        assert auth_endpoints <= got, "需鉴权接口都应生成权限用例"

    def test_limit_option(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        gen = CaseGenerator(provider=MockProvider(endpoints))
        _, stats = gen.generate(endpoints, limit=2)
        assert stats.endpoints_processed == 2

    def test_stats_usable_rate(self):
        s = GenerationStats(cases_generated=10, cases_valid=8, cases_invalid=2)
        assert s.usable_rate == 80.0
        assert "初稿可用率 80.0%" in s.summary()

    def test_markdown_render_contains_review_hint(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        gen = CaseGenerator(provider=MockProvider(endpoints))
        cases, stats = gen.generate(endpoints, limit=1)
        md = render_markdown(cases, stats, endpoints)
        assert "人工评审" in md
        assert "断言清单" in md


# ----------------------------------------------------------------------
# LLM 输出解析
# ----------------------------------------------------------------------
class TestLLMParsing:

    def test_extract_plain_json(self):
        assert extract_json('{"cases": []}') == {"cases": []}

    def test_extract_from_code_fence(self):
        text = '下面是结果：\n```json\n{"cases": [{"title": "t"}]}\n```\n以上。'
        assert extract_json(text)["cases"][0]["title"] == "t"

    def test_extract_from_noisy_text(self):
        text = '好的，我给出如下 JSON: {"cases": []} 请查收'
        assert extract_json(text) == {"cases": []}

    def test_extract_raises_on_garbage(self):
        with pytest.raises(ValueError):
            extract_json("完全没有 JSON")

    def test_extract_raises_on_empty(self):
        with pytest.raises(ValueError):
            extract_json("")

    def test_mock_provider_matches_endpoints(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        provider = MockProvider(endpoints)
        ep = endpoints[0]
        parts = build_prompt(ep, default_knowledge_base())
        payload = extract_json(provider.complete(parts.system, parts.user))
        assert payload["cases"], "mock 应至少生成一条用例"


# ----------------------------------------------------------------------
# pytest 骨架生成
# ----------------------------------------------------------------------
class TestScaffold:

    def test_render_module_is_syntactically_valid(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        gen = CaseGenerator(provider=MockProvider(endpoints))
        cases, _ = gen.generate(endpoints, limit=2)
        src = render_module(cases, "system")
        compile(src, "<generated>", "exec")          # 语法必须合法
        assert "class Test" in src
        assert "BaseTest" in src
        assert "TODO" in src, "请求调用处应留待人工对齐的断点"
        assert "allure.title" in src

    def test_case_id_recorded_in_docstring(self):
        endpoints = parse_swagger(load_spec(SPEC_PATH))
        gen = CaseGenerator(provider=MockProvider(endpoints))
        cases, _ = gen.generate(endpoints, limit=1)
        src = render_module(cases, "login")
        for c in cases:
            assert c.case_id in src

    def test_priority_maps_to_marker(self):
        e = Endpoint(path="/a", method="GET")
        p0 = TestCase(case_id="TC-A-001", title="t0", endpoint="GET /a",
                      case_type="normal", priority="P0", expected="x",
                      assertions=["业务 code 为 200"])
        p1 = TestCase(case_id="TC-A-002", title="t1", endpoint="GET /a",
                      case_type="normal", priority="P1", expected="x",
                      assertions=["业务 code 为 200"])
        src = render_module([p0, p1], "mod")
        assert "pytest.mark.critical" in src
        assert "pytest.mark.smoke" in src

    def test_chinese_title_becomes_ascii_function(self):
        """纯中文标题必须退回用例编号，生成合法 ASCII 函数名。"""
        e = Endpoint(path="/a", method="GET")
        cn = TestCase(case_id="TC-A-007", title="正常场景-查询列表", endpoint="GET /a",
                      case_type="normal", priority="P0", expected="x",
                      assertions=["业务 code 为 200"])
        src = render_module([cn], "mod")
        import re as _re
        names = _re.findall(r"def (\w+)\(", src)
        assert names == ["test_case_007"], names
        for n in names:
            assert n.isascii() and n.isidentifier(), "函数名必须为合法 ASCII 标识符"
        compile(src, "<generated>", "exec")

    def test_latin_title_kept_readable(self):
        e = Endpoint(path="/a", method="GET")
        en = TestCase(case_id="TC-A-001", title="login success case", endpoint="GET /a",
                      case_type="normal", priority="P0", expected="x",
                      assertions=["业务 code 为 200"])
        src = render_module([en], "mod")
        assert "def test_login_success_case" in src


# ----------------------------------------------------------------------
# 失败归因
# ----------------------------------------------------------------------
class TestAnalyzer:

    def test_rule_prefilter_connection_error(self):
        item = rule_prefilter("test_x",
                              "requests.exceptions.ConnectionError: "
                              "HTTPConnectionPool: Max retries exceeded with url")
        assert item is not None
        assert item.issue == "env"
        assert item.source == "rule"
        assert item.need_rerun is True

    def test_rule_prefilter_redis(self):
        item = rule_prefilter("test_y", "redis.exceptions.ConnectionError: Error 10061")
        assert item is not None and item.issue == "env"

    def test_rule_prefilter_auth_401(self):
        item = rule_prefilter("test_z", "assert 401 == 200", status_code=401)
        assert item is not None and item.issue == "env"

    def test_rule_prefilter_passes_real_assertion_failure(self):
        assert rule_prefilter("test_ok", "AssertionError: business code: 500") is None

    def test_analyze_mixed_failures(self):
        failures = [
            {"test": "test_env", "traceback": "ConnectionRefusedError: [Errno 61]",
             "status_code": None},
            {"test": "test_assert", "traceback": "AssertionError: business code: 500",
             "status_code": 200},
        ]
        analyzer = FailureAnalyzer(provider=MockProvider())
        report = analyzer.analyze(failures)
        assert report["total"] == 2
        assert report["summary"]["env"] >= 1
        # 断言失败会走模型分支；mock 返回的不是 JSON，应被兜底为 unknown
        assert report["summary"]["unknown"] >= 1
        for it in report["items"]:
            assert it["issue"] in ("case", "env", "product", "unknown")

    def test_render_report_readable(self):
        report = {
            "provider": "mock", "ai_used": False, "total": 1,
            "summary": {"case": 0, "env": 1, "product": 0, "unknown": 0},
            "items": [{"test": "test_a", "issue": "env", "confidence": "high",
                       "reason": "服务未启动", "evidence": ["ConnectionRefused"],
                       "suggestion": "启动服务", "need_rerun": True, "source": "rule"}],
        }
        text = render_report(report)
        assert "环境问题" in text and "test_a" in text and "先重跑" in text

    def test_analyzer_handles_empty(self):
        report = FailureAnalyzer(provider=MockProvider()).analyze([])
        assert report["total"] == 0
        assert sum(report["summary"].values()) == 0


# ----------------------------------------------------------------------
# CLI（不依赖外部服务）
# ----------------------------------------------------------------------
class TestCLI:

    def test_parse_subcommand(self, tmp_path):
        from aitest.cli import main
        out = tmp_path / "endpoints.json"
        rc = main(["parse", "--spec", SPEC_PATH, "--out", str(out)])
        assert rc == 0
        data = json.loads(out.read_text(encoding="utf-8"))
        assert len(data) == 9

    def test_generate_with_mock(self, tmp_path):
        from aitest.cli import main
        out_dir = tmp_path / "ai"
        rc = main(["generate", "--spec", SPEC_PATH, "--provider", "mock",
                   "--out-dir", str(out_dir), "--scaffold-dir", str(out_dir / "tests")])
        assert rc == 0
        cases_json = json.loads((out_dir / "cases.json").read_text(encoding="utf-8"))
        assert cases_json["cases"], "应生成用例"
        assert "stats" in cases_json and "coverage" in cases_json
        assert (out_dir / "cases.md").exists()
        for p in (out_dir / "tests").glob("*.py"):
            compile(p.read_text(encoding="utf-8"), str(p), "exec")

    def test_report_subcommand(self, tmp_path, capsys):
        from aitest.cli import main
        out_dir = tmp_path / "ai"
        main(["generate", "--spec", SPEC_PATH, "--provider", "mock",
              "--out-dir", str(out_dir)])
        rc = main(["report", "--cases", str(out_dir / "cases.json"), "--spec", SPEC_PATH])
        assert rc == 0
        assert "接口覆盖" in capsys.readouterr().out

    def test_show_prompt_is_dry_run(self, capsys):
        from aitest.cli import main
        rc = main(["generate", "--spec", SPEC_PATH, "--show-prompt", "--limit", "1"])
        out = capsys.readouterr().out
        assert rc == 0
        # 干跑必须在提示词里给出六段结构，且不产生任何模型调用
        for block in ("## 一、待测接口", "## 二、业务背景",
                      "## 三、约束", "## 六、输出要求"):
            assert block in out, "提示词缺少 %s" % block
        assert "干跑模式" in out

    def test_extra_rules_reach_prompt(self, capsys):
        from aitest.cli import main
        rc = main(["generate", "--spec", SPEC_PATH, "--show-prompt", "--limit", "1",
                   "--extra-rules", "必须覆盖并发提交同一单据的场景"])
        out = capsys.readouterr().out
        assert rc == 0
        assert "## 四、额外要求" in out
        assert "必须覆盖并发提交同一单据的场景" in out

    def test_generate_reports_failed_endpoints(self, tmp_path, capsys, monkeypatch):
        """模型彻底失败时必须留下接口名与原因，而不是只留一个计数。"""
        from aitest.cli import main
        from aitest.llm import MockProvider

        def _boom(self, system, user, max_tokens=4000):
            raise RuntimeError("模拟模型不可用")

        monkeypatch.setattr(MockProvider, "complete", _boom)
        out_dir = tmp_path / "ai"
        rc = main(["generate", "--spec", SPEC_PATH, "--provider", "mock",
                   "--out-dir", str(out_dir)])
        out = capsys.readouterr().out
        assert rc == 0
        assert "需人工补写" in out and "POST /login" in out
        stats = json.loads((out_dir / "cases.json").read_text(encoding="utf-8"))["stats"]
        assert stats["cases_final"] == 0
        assert len(stats["endpoints_failed"]) == 9
        assert "模拟模型不可用" in stats["endpoint_failure_reasons"]["POST /login"]

    def test_analyze_subcommand(self, tmp_path, capsys):
        from aitest.cli import main
        junit = tmp_path / "report.xml"
        junit.write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<testsuites><testsuite name="pytest" tests="2" failures="1">'
            '<testcase classname="tests.auth.test_login" name="test_login_success">'
            '<failure message="ConnectionRefusedError">'
            'requests.exceptions.ConnectionError: Max retries exceeded'
            '</failure></testcase>'
            '<testcase classname="tests.auth.test_login" name="test_login_wrong_password"/>'
            '</testsuite></testsuites>', encoding="utf-8")
        out = tmp_path / "failure.md"
        rc = main(["analyze", "--junit", str(junit), "--provider", "mock",
                   "--out", str(out)])
        assert rc == 0
        assert "失败归因报告" in out.read_text(encoding="utf-8")
