# 缓存监控 - 测试用例

> 接口：GET /monitor/cache, GET /monitor/cache/getNames, GET /monitor/cache/getKeys/{cacheName}, GET /monitor/cache/getValue/{cacheName}/{cacheKey}
> 说明：缓存监控总览、缓存名称列表、键名列表、缓存值查询
> 模块：系统监控 > 缓存监控

## TC-CACHE-001

| 项目 | 内容 |
|------|------|
| 用例ID | TC-CACHE-001 |
| 用例标题 | 缓存监控 - 正常场景: 获取缓存总览信息 |
| 优先级 | P0 |
| 前置条件 | 已登录 |
| 测试类型 | 功能测试 |

**测试数据：** 无参数

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET /monitor/cache | code=200, 返回 data |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 200
- 返回数据包含 data 字段
- data 包含 info、dbSize、commandStats 等关键字段

## TC-CACHE-002

| 项目 | 内容 |
|------|------|
| 用例ID | TC-CACHE-002 |
| 用例标题 | 缓存监控 - 异常场景: 未认证访问 |
| 优先级 | P1 |
| 前置条件 | 无 Token |
| 测试类型 | 权限测试 |

**测试数据：** 请求头不携带 Authorization

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET /monitor/cache（无Token） | code=401 |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 401

## TC-CACHE-003

| 项目 | 内容 |
|------|------|
| 用例ID | TC-CACHE-003 |
| 用例标题 | 缓存监控 - 异常场景: 无效Token访问 |
| 优先级 | P1 |
| 前置条件 | 使用无效 Token |
| 测试类型 | 权限测试 |

**测试数据：** Authorization: Bearer invalid_token_12345

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET /monitor/cache（无效Token） | code=401 |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 401

## TC-CACHE-004

| 项目 | 内容 |
|------|------|
| 用例ID | TC-CACHE-004 |
| 用例标题 | 缓存名称列表 - 正常场景: 获取所有缓存名称 |
| 优先级 | P0 |
| 前置条件 | 已登录 |
| 测试类型 | 功能测试 |

**测试数据：** GET /monitor/cache/getNames

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET /monitor/cache/getNames | code=200, 返回 data 列表 |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 200
- 返回数据包含 data 字段
- data 为列表类型

## TC-CACHE-005

| 项目 | 内容 |
|------|------|
| 用例ID | TC-CACHE-005 |
| 用例标题 | 缓存名称列表 - 异常场景: 未认证访问 |
| 优先级 | P1 |
| 前置条件 | 无 Token |
| 测试类型 | 权限测试 |

**测试数据：** 请求头不携带 Authorization

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET /monitor/cache/getNames（无Token） | code=401 |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 401

## TC-CACHE-006

| 项目 | 内容 |
|------|------|
| 用例ID | TC-CACHE-006 |
| 用例标题 | 缓存键名列表 - 正常场景: 获取指定缓存的所有键名 |
| 优先级 | P1 |
| 前置条件 | 已登录，存在缓存名称 |
| 测试类型 | 功能测试 |

**测试数据：** GET /monitor/cache/getKeys/{已知缓存名}

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 先调用 getNames 获取第一个缓存名 | code=200 |
| 2 | 发送 GET /monitor/cache/getKeys/{cacheName} | code=200, 返回 data |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 200
- 返回数据包含 data 字段

## TC-CACHE-007

| 项目 | 内容 |
|------|------|
| 用例ID | TC-CACHE-007 |
| 用例标题 | 缓存键名列表 - 异常场景: 不存在的缓存名 |
| 优先级 | P1 |
| 前置条件 | 已登录 |
| 测试类型 | 异常测试 |

**测试数据：** GET /monitor/cache/getKeys/nonexistent_cache

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET /monitor/cache/getKeys/nonexistent | code=500 |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 500

## TC-CACHE-008

| 项目 | 内容 |
|------|------|
| 用例ID | TC-CACHE-008 |
| 用例标题 | 缓存值查询 - 正常场景: 获取指定键的缓存值 |
| 优先级 | P1 |
| 前置条件 | 已登录，存在缓存名称和键名 |
| 测试类型 | 功能测试 |

**测试数据：** GET /monitor/cache/getValue/{cacheName}/{cacheKey}

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 先调用 getNames 获取缓存名 | code=200 |
| 2 | 调用 getKeys 获取键名 | code=200 |
| 3 | 发送 GET /monitor/cache/getValue/{cacheName}/{cacheKey} | code=200 |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 200

## TC-CACHE-009

| 项目 | 内容 |
|------|------|
| 用例ID | TC-CACHE-009 |
| 用例标题 | 缓存值查询 - 异常场景: 不存在的缓存键 |
| 优先级 | P2 |
| 前置条件 | 已登录 |
| 测试类型 | 异常测试 |

**测试数据：** GET /monitor/cache/getValue/nonexistent/nonexistent

**测试步骤：**
| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET /monitor/cache/getValue/nonexistent/nonexistent | code=500 |

**断言清单：**
- HTTP 状态码 = 200
- 业务码 code = 500
