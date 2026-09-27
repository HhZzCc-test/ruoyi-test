# RuoYi API 自动化测试

## 项目介绍

本项目是**若依（RuoYi）后台管理系统**的接口自动化测试框架，基于 **pytest + Requests + Allure** 技术栈从零搭建，覆盖认证、系统管理、系统监控三大核心业务模块共 **20+ 个 REST API 接口**，实现全链路自动化回归测试与可视化报告输出。

### 技术栈

| 组件 | 版本 | 用途 |
|------|------|------|
| Python | 3.8+ | 开发语言 |
| pytest | >=7.0.0 | 测试框架，用例组织、参数化、fixture 管理 |
| requests | >=2.28.0 | HTTP 请求库，调用后端 API |
| allure-pytest | >=2.13.0 | 生成 Allure 可视化测试报告 |
| redis | >=4.0.0 | 连接 Redis，读取验证码缓存 |
| urllib3 | >=1.26.0 | HTTP 底层重试与连接池管理 |

### 设计亮点

- **三层分离架构**：API 客户端层 → 测试基类层 → 测试用例层，职责清晰，易于扩展
- **Session 级 Token 复用**：整个测试套件只登录一次，避免重复鉴权开销
- **Redis 直连验证码**：直接从 Redis 读取验证码缓存，实现全自动化，无需人工干预
- **自动重试 + 连接池**：HTTP 请求自动重试（3 次），20 并发连接池，提升稳定性与效率
- **参数化测试**：大量使用 `@pytest.mark.parametrize` 减少重复代码 30%+
- **Allure 全链路报告**：每个断言失败都有清晰的错误消息，响应时间自动附加到报告中
- **pytest marker 分级**：支持按 `smoke` / `critical` / `auth` / `slow` 标签灵活筛选

### 测试覆盖范围

| 模块 | 测试文件 | 覆盖接口 | 覆盖场景 |
|------|---------|---------|---------|
| **认证（auth）** | 5 个文件 | `/captchaImage` `/login` `/register` `/getInfo` `/getRouters` | 正常流程、参数边界、权限校验（无 Token / 无效 Token / 过期 Token）、响应时间 |
| **系统管理（system）** | 8 个文件 | 用户/角色/菜单/部门/岗位/字典/配置/通知 | 列表查询、分页、搜索、按 ID 查询、状态筛选、部门筛选 |
| **系统监控（monitor）** | 7 个文件 | 服务监控/缓存监控/在线用户/定时任务/操作日志/登录日志 | 查询校验、分页、搜索 |

---

## AI 辅助用例生成（`aitest` 模块）

把 [skills/api-test-skill.md](skills/api-test-skill.md) 里那套人工执行的 AI 工作流
（Analyze → Design → Implement → Verify）工程化成**可重复运行的流水线**：

```
Swagger / OpenAPI ─► 接口元数据 ─► 业务知识库检索(RAG) ─► Claude 生成用例草稿
                                                              │
                     pytest 骨架 ◄── 规则去重/覆盖度校验 ◄──────┘
                                                              │
                                       失败归因（规则预筛 + 模型）◄── junit xml
```

### 设计要点

| 要点 | 说明 |
|---|---|
| **AI 只出草稿** | 生成结果必须过 `case_rules.validate_case`（拦住「只断言 HTTP 200」这类假绿灯用例），再经人工评审才允许入库 |
| **可插拔模型** | `LLMProvider` 协议 + `ClaudeProvider` + `MockProvider`；无 API Key 时自动降级为离线 mock，CI 与本地开发无需 Key |
| **提示词四要素** | 业务背景（知识库检索）+ 约束 + 示例（few-shot）+ 输出要求（严格 JSON 契约），见 `prompt_builder.py` |
| **归因分三类** | 失败结论区分 **用例问题 / 环境问题 / 真实缺陷**，且明确「结论是假设，需用日志复现确认」 |
| **规则预筛省调用** | 连接拒绝、Redis 不可用、401 等一眼可见的环境问题走规则判定，不浪费模型调用 |

### 目录结构

```
aitest/
├── models.py            # Endpoint / TestCase / ParamSpec 数据模型
├── swagger_parser.py    # OpenAPI 3.x 与 Swagger 2.0 解析（含 $ref 展开）
├── knowledge.py         # 业务知识库 + 关键词加权检索（轻量 RAG）
├── prompt_builder.py    # 提示词构建（四要素 + few-shot）
├── prompts.py           # 系统角色与 JSON 输出契约
├── llm.py               # ClaudeProvider / MockProvider / JSON 抽取
├── case_rules.py        # 校验、去重、覆盖度报告
├── generator.py         # 生成流水线 + 统计（草稿可用率等）
├── generator_pytest.py  # pytest 骨架渲染
├── analyzer.py          # 失败归因（规则预筛 + 模型）
└── cli.py               # 命令行入口

specs/ruoyi-openapi.json # 示例规格（节选自若依常用接口）
tests_aitest/            # aitest 自身单测（离线可跑）
tests_ai_generated/      # 生成的骨架示例（默认不纳入回归）
```

### 使用方式

```bash
pip install -r requirements.txt

# 1) 解析接口文档，产出接口清单
python -m aitest parse --spec specs/ruoyi-openapi.json

# 2) 生成用例草稿（含规则校验、去重、覆盖度报告），并同时产出 pytest 骨架
#    未设置 ANTHROPIC_API_KEY 时自动使用离线 mock
python -m aitest generate --spec specs/ruoyi-openapi.json \
    --out-dir reports/ai --scaffold-dir tests_ai_generated

# 3) 用真实模型生成（需先设置 Key）
export ANTHROPIC_API_KEY=sk-ant-xxx          # Windows: set ANTHROPIC_API_KEY=...
python -m aitest generate --spec specs/ruoyi-openapi.json --provider claude

# 4) 对失败用例做归因（输入 pytest 的 junit xml）
python -m aitest analyze --junit examples/junit-sample.xml --provider claude \
    --out reports/ai/failure_report.md

# 5) 单独查看覆盖度
python -m aitest report --cases reports/ai/cases.json --spec specs/ruoyi-openapi.json
```

生成产物：
- `reports/ai/cases.json` —— 机器可读（含 `stats` 生成统计与 `coverage` 覆盖度）
- `reports/ai/cases.md` —— 人工评审用（含评审要点提示）
- `tests_ai_generated/*.py` —— pytest 骨架，请求调用处留有需人工对齐的断点

### 自测与覆盖率

```bash
# aitest 模块单测（不需要若依服务与 API Key）
python -m pytest tests_aitest -q

# 覆盖率（实测约 90%）
python -m pytest tests_aitest --cov=aitest --cov-report=term-missing
```

CI 见 [.github/workflows/ci.yml](.github/workflows/ci.yml)：`offline` 作业跑单测 + 生成自检，
`coverage` 作业输出覆盖率报告并设 70% 门槛，`live` 作业留给需要真实服务的回归。

---


### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动后端服务

测试默认连接 `http://localhost:18080`，请确保若依后端服务已在该地址启动。

### 3. 确保 Redis 可访问

验证码通过 Redis 直连获取，请确保 Redis 服务正常运行且测试环境可访问。

---

## 项目结构

```
ruoyi-test/
├── pytest.ini                     # pytest 全局配置
├── requirements.txt               # 依赖清单
├── README.md                      # 项目说明
│
├── tests/                         # 测试用例目录
│   ├── core/                      # 核心基础设施
│   │   ├── base.py                # BaseTest 测试基类
│   │   ├── client.py              # RuoyiApiClient API 封装客户端
│   │   └── assertions.py          # 自定义断言函数库
│   │
│   ├── auth/                      # 认证模块测试
│   │   ├── conftest.py            # 认证模块 fixtures（token、headers）
│   │   ├── test_login.py          # 登录接口
│   │   ├── test_register.py       # 注册接口
│   │   ├── test_captcha.py        # 验证码接口
│   │   ├── test_get_info.py       # 获取用户信息接口
│   │   └── test_get_routers.py    # 获取路由接口
│   │
│   ├── system/                    # 系统管理模块测试
│   │   ├── conftest.py            # 系统管理 fixtures
│   │   ├── test_user.py           # 用户管理
│   │   ├── test_role.py           # 角色管理
│   │   ├── test_menu.py           # 菜单管理
│   │   ├── test_dept.py           # 部门管理
│   │   ├── test_post.py           # 岗位管理
│   │   ├── test_dict.py           # 字典管理
│   │   ├── test_config.py         # 参数配置
│   │   └── test_notice.py         # 通知公告
│   │
│   └── monitor/                   # 系统监控模块测试
│       ├── conftest.py            # 监控模块 fixtures
│       ├── test_server.py         # 服务监控
│       ├── test_cache.py          # 缓存监控
│       ├── test_online.py         # 在线用户
│       ├── test_job.py            # 定时任务
│       ├── test_job_log.py        # 定时任务日志
│       ├── test_operlog.py        # 操作日志
│       └── test_logininfor.py     # 登录日志
│
├── doc/                           # 测试文档
│   └── testcases/                 # 测试用例文档
│       ├── auth/                  # 认证模块用例
│       ├── system/                # 系统管理模块用例
│       └── monitor/               # 系统监控模块用例
│
└── allure-results/                # Allure 原始结果数据
```

---

## 运行测试

### 运行所有测试

```bash
pytest
```

### 按模块运行

```bash
pytest tests/auth/       # 认证模块
pytest tests/system/     # 系统管理模块
pytest tests/monitor/    # 系统监控模块
```

### 运行指定文件

```bash
pytest tests/auth/test_login.py
```

### 运行指定测试方法

```bash
pytest tests/auth/test_login.py::TestLogin::test_login_success
```

### 按标记（marker）筛选

| 标记 | 说明 | 示例 |
|------|------|------|
| `smoke` | 冒烟测试 | `pytest -m smoke` |
| `critical` | 关键测试 | `pytest -m critical` |
| `auth` | 认证相关测试 | `pytest -m auth` |
| `slow` | 慢速测试 | `pytest -m "not slow"` |

### 常用命令行选项

```bash
pytest -v                        # 详细输出
pytest -x                        # 遇到第一个失败就停止
pytest --lf                       # 只运行上次失败的用例
pytest --durations=10             # 显示最慢的 10 个测试
pytest --alluredir=allure-results # 指定 Allure 报告输出目录
```

---

## 查看 Allure 报告

```bash
# 生成并查看报告
allure serve allure-results

# 生成为静态 HTML
allure generate allure-results -o allure-report --clean
```

---

## 配置说明

[pytest.ini](pytest.ini) 主要配置项：

| 配置项 | 值 | 说明 |
|------|------|------|
| `testpaths` | `tests` | 测试文件搜索路径 |
| `python_files` | `test_*.py` | 测试文件匹配模式 |
| `python_classes` | `Test*` | 测试类匹配模式 |
| `python_functions` | `test_*` | 测试方法匹配模式 |
| `addopts` | `-v --tb=short --strict-markers --alluredir=allure-results` | 默认命令行参数 |
| `markers` | `smoke` `critical` `auth` `slow` | 自定义标记 |

---

## 自定义断言

项目封装了 8 个专用断言函数，位于 [tests/core/assertions.py](tests/core/assertions.py)：

| 断言函数 | 用途 |
|---------|------|
| `assert_http_ok(resp)` | 验证 HTTP 状态码为 200 |
| `assert_business_success(data)` | 验证业务 code == 200 |
| `assert_business_error(data)` | 验证业务 code != 200 |
| `assert_field_exists(data, field)` | 验证字段存在 |
| `assert_field_not_empty(data, field)` | 验证字段非空 |
| `assert_field_type(data, field, type)` | 验证字段类型 |
| `assert_response_time(elapsed)` | 验证响应时间 < 3s |
| `assert_all_unique(items)` | 验证集合元素唯一性 |