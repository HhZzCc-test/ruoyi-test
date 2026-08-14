# 登录日志 - 测试用例

> 接口：GET /monitor/logininfor/list
> 说明：查询系统登录日志记录
> 模块：系统监控 > 日志管理 > 登录日志

## TC-LOGININFO-001

| 项目 | 内容 |
|------|------|
| 用例ID | TC-LOGININFO-001 |
| 用例标题 | 登录日志列表 - 正常场景: 获取登录日志列表 |
| 优先级 | P0 |
| 前置条件 | 已登录 |
| 测试类型 | 功能测试 |

**测试数据：** 无额外参数

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET /monitor/logininfor/list | code=200, 返回 rows 列表 |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 200
- 返回数据包含 rows 字段
- rows 为列表类型

## TC-LOGININFO-002

| 项目 | 内容 |
|------|------|
| 用例ID | TC-LOGININFO-002 |
| 用例标题 | 登录日志列表 - 异常场景: 未认证访问 |
| 优先级 | P1 |
| 前置条件 | 无 Token |
| 测试类型 | 权限测试 |

**测试数据：** 请求头不携带 Authorization

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET /monitor/logininfor/list（无Token） | code=401 |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 401

## TC-LOGININFO-003

| 项目 | 内容 |
|------|------|
| 用例ID | TC-LOGININFO-003 |
| 用例标题 | 登录日志列表 - 异常场景: 无效Token访问 |
| 优先级 | P1 |
| 前置条件 | 使用无效 Token |
| 测试类型 | 权限测试 |

**测试数据：** Authorization: Bearer invalid_token_12345

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET /monitor/logininfor/list（无效Token） | code=401 |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 401

## TC-LOGININFO-004

| 项目 | 内容 |
|------|------|
| 用例ID | TC-LOGININFO-004 |
| 用例标题 | 登录日志列表 - 边界场景: 按用户名筛选 |
| 优先级 | P1 |
| 前置条件 | 已登录 |
| 测试类型 | 功能测试 |

**测试数据：** params={"userName": "admin"}

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET /monitor/logininfor/list?userName=admin | code=200 |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 200
- rows 中每条记录的 userName 为 admin
