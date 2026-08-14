# 用户信息接口 - 测试用例

> 接口：GET /getInfo
> 说明：获取当前登录用户的详细信息（用户、角色、权限等）
> 模块：认证模块
> 认证：需要 Bearer Token

---

## TC-INFO-001

| 项目 | 内容 |
|------|------|
| **用例ID** | TC-INFO-001 |
| **用例标题** | 正常场景 - 已登录用户获取信息 |
| **优先级** | P0（Critical） |
| **前置条件** | 1. 已通过 /login 获取有效Token；2. Token 在 Header 中传递 |
| **测试类型** | 功能测试 - 正常场景 |

**请求头：**
| Header | 值 |
|--------|-----|
| Authorization | Bearer {token} |
| Content-Type | application/json |

**测试步骤：**

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | POST /login 获取Token | 登录成功，返回有效Token |
| 2 | GET /getInfo（携带Token） | HTTP 200 |
| 3 | 检查 code 字段 | code == 200 |
| 4 | 检查 user/data 字段 | 用户信息不为 null |
| 5 | 检查 userName 字段 | 返回当前登录用户名 |
| 6 | 检查 nickName 字段 | 昵称不为空 |
| 7 | 检查 roles 字段 | 角色列表存在 |
| 8 | 检查 permissions 字段 | 权限列表存在 |

**断言清单：**
- `resp.status_code == 200`
- `data["code"] == 200`
- `user_data is not None`
- `user_data["userName"] is not None`

---

## TC-INFO-002

| 项目 | 内容 |
|------|------|
| **用例ID** | TC-INFO-002 |
| **用例标题** | 权限场景 - 无Token请求 |
| **优先级** | P0（Critical） |
| **前置条件** | 服务正常运行 |
| **测试类型** | 功能测试 - 权限场景 |

**请求头：** 不携带 Authorization

**测试步骤：**

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | GET /getInfo（无Token） | HTTP 200 |
| 2 | 检查 code 字段 | code != 200，返回未授权错误 |

**断言清单：**
- `data["code"] != 200`

---

## TC-INFO-003

| 项目 | 内容 |
|------|------|
| **用例ID** | TC-INFO-003 |
| **用例标题** | 权限场景 - 无效Token |
| **优先级** | P0（Critical） |
| **前置条件** | 服务正常运行 |
| **测试类型** | 功能测试 - 权限场景 |

**请求头：**
| Header | 值 |
|--------|-----|
| Authorization | Bearer invalid_token_12345 |

**预期结果：** code != 200，返回"Token无效"或"未授权"

---

## TC-INFO-004

| 项目 | 内容 |
|------|------|
| **用例ID** | TC-INFO-004 |
| **用例标题** | 权限场景 - 过期Token |
| **优先级** | P2（Normal） |
| **前置条件** | 准备一个已过期的Token |
| **测试类型** | 功能测试 - 权限场景 |

**请求头：**
| Header | 值 |
|--------|-----|
| Authorization | Bearer eyJhbGciOiJIUzUxMiJ9.expired_token_for_test |

**预期结果：** code != 200，返回"Token已过期"

---

## TC-INFO-005

| 项目 | 内容 |
|------|------|
| **用例ID** | TC-INFO-005 |
| **用例标题** | 性能 - 用户信息接口响应时间 |
| **优先级** | P2（Normal） |
| **前置条件** | 已登录获取有效Token |
| **测试类型** | 性能测试 |

**测试步骤：**

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 记录请求前时间 | - |
| 2 | GET /getInfo（携带Token） | HTTP 200 |
| 3 | 计算响应耗时 | 耗时 < 3 秒 |

**断言清单：**
- `elapsed_time < 3.0`

---

> 用例总数：5 条 | P0: 3 | P2: 2