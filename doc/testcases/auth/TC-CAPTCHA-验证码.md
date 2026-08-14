# 验证码接口 - 测试用例

> 接口：GET /captchaImage
> 说明：获取登录验证码图片及uuid
> 模块：认证模块

---

## TC-CAPTCHA-001

| 项目 | 内容 |
|------|------|
| **用例ID** | TC-CAPTCHA-001 |
| **用例标题** | 正常获取验证码 |
| **优先级** | P0（Critical） |
| **前置条件** | 服务正常运行 |
| **测试类型** | 功能测试 - 正常场景 |

**测试步骤：**

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 发送 GET 请求到 `/captchaImage` | HTTP 状态码 200 |
| 2 | 解析响应 JSON | 响应体为有效 JSON |
| 3 | 检查 code 字段 | code == 200 |
| 4 | 检查 uuid 字段 | uuid 存在且不为空，类型为 string |
| 5 | 检查 img 字段 | img 存在且不为空，类型为 string |
| 6 | 检查 msg 字段 | msg 存在，类型为 string |

**断言清单：**
- `resp.status_code == 200`
- `data["code"] == 200`
- `"uuid" in data and data["uuid"] is not None`
- `"img" in data and data["img"] is not None`
- `isinstance(data["uuid"], str)`
- `isinstance(data["img"], str)`
- `isinstance(data["code"], int)`
- `isinstance(data["msg"], str)`

---

## TC-CAPTCHA-002

| 项目 | 内容 |
|------|------|
| **用例ID** | TC-CAPTCHA-002 |
| **用例标题** | 多次请求验证码UUID唯一性 |
| **优先级** | P2（Normal） |
| **前置条件** | 服务正常运行 |
| **测试类型** | 功能测试 - 数据一致性 |

**测试步骤：**

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 第1次请求 `/captchaImage`，记录 uuid1 | HTTP 200 |
| 2 | 第2次请求 `/captchaImage`，记录 uuid2 | HTTP 200 |
| 3 | 第3次请求 `/captchaImage`，记录 uuid3 | HTTP 200 |
| 4 | 比较 uuid1、uuid2、uuid3 | 三者互不相同 |

**断言清单：**
- 每次请求状态码均为 200
- `len({uuid1, uuid2, uuid3}) == 3`

---

## TC-CAPTCHA-003

| 项目 | 内容 |
|------|------|
| **用例ID** | TC-CAPTCHA-003 |
| **用例标题** | 验证码接口响应时间 |
| **优先级** | P2（Normal） |
| **前置条件** | 服务正常运行 |
| **测试类型** | 性能测试 |

**测试步骤：**

| 步骤 | 操作 | 预期结果 |
|------|------|----------|
| 1 | 记录当前时间 t1 | - |
| 2 | 发送 GET 请求到 `/captchaImage` | HTTP 200 |
| 3 | 记录响应时间 t2 | - |
| 4 | 计算耗时 = t2 - t1 | 耗时 < 3 秒 |

**断言清单：**
- `resp.status_code == 200`
- `elapsed_time < 3.0`

---

> 用例总数：3 条 | P0: 1 | P2: 2