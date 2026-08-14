# RuoYi API 自动化测试

基于 pytest + requests + allure 的若依后端 API 自动化测试项目。

## 环境准备

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

依赖说明：

| 包名 | 版本 | 用途 |
|------|------|------|
| pytest | >=7.0.0 | 测试框架 |
| requests | >=2.28.0 | HTTP 请求库 |
| allure-pytest | >=2.13.0 | Allure 报告生成 |
| urllib3 | >=1.26.0 | HTTP 底层库 |

### 2. 启动后端服务

测试默认连接 `http://localhost:18080`，请确保若依后端服务已在该地址启动。

## 运行测试

### 运行所有测试

```bash
pytest
```

### 运行指定文件

```bash
pytest tests/test_login.py
```

### 运行指定测试类或方法

```bash
# 运行某个测试类
pytest tests/test_login.py::TestLogin

# 运行某个具体测试方法****
pytest tests/test_login.py::TestLogin::test_login_success

# 运行参数化用例（通过 id 指定）
pytest tests/test_login.py::TestLogin::test_login_success[normal_login]
```

### 按标记（marker）筛选运行

| 标记 | 说明 |
|------|------|
| `smoke` | 冒烟测试 |
| `critical` | 关键测试 |
| `auth` | 认证相关测试 |
| `slow` | 慢速测试 |

```bash
# 只运行冒烟测试
pytest -m smoke

# 只运行关键测试
pytest -m critical

# 运行认证相关测试
pytest -m auth

# 排除慢速测试
pytest -m "not slow"
```

### 常用命令行选项

```bash
# 详细输出（默认已启用）
pytest -v

# 遇到第一个失败就停止
pytest -x

# 只运行上次失败的用例
pytest --lf

# 显示最慢的 10 个测试
pytest --durations=10

# 指定 Allure 报告输出目录（默认已配置）
pytest --alluredir=allure-results

# 查看 Allure 报告
allure serve allure-results
```

## 项目结构

```
ruoyi-test/
├── tests/                  # 测试用例目录
│   ├── conftest.py         # pytest fixtures 配置
│   ├── test_login.py       # 登录接口测试
│   ├── test_captcha.py     # 验证码接口测试
│   ├── test_get_info.py    # 获取用户信息测试
│   ├── test_get_routers.py # 获取路由测试
│   ├── test_register.py    # 注册接口测试
│   └── auth/               # 认证模块测试
│       ├── test_login.py
│       └── test_captcha.py
├── pytest.ini              # pytest 配置文件
├── requirements.txt        # 依赖清单
└── allure-results/         # Allure 报告输出目录
```

## 配置说明

[pytest.ini](pytest.ini) 中已配置：

- `testpaths = tests` — 测试文件搜索路径
- `python_files = test_*.py` — 测试文件匹配模式
- `python_classes = Test*` — 测试类匹配模式
- `python_functions = test_*` — 测试方法匹配模式
- `--alluredir=allure-results` — Allure 报告默认输出目录