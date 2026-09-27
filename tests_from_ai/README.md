# tests_from_ai —— AI 生成、人工评审后落地的可执行测试

这个目录里的用例**不是手写的**：由 `aitest` 调用真实模型（DeepSeek `deepseek-v4-pro`）
对 `specs/ruoyi-openapi.json` 的 9 个接口生成草稿，再用人工维护的
`specs/ruoyi-client-map.json` 映射到 `RuoyiApiClient` 的方法后自动生成的。

## 为什么单独放一个目录

`pytest.ini` 的 `testpaths` 只含 `tests`，所以这些用例**不在默认回归里**，必须显式指定：

```bash
python -m pytest tests_from_ai -q        # 需要若依后端(:18080) + Redis(:6379) 在线
```

刻意不放进 `tests/`：那会把正式回归的用例数从 98 改掉，属于「要不要纳入回归」的决策，
应该由人决定，而不是工具偷偷决定。

## 生成与运行方式

```bash
# 1) 真实模型生成用例草稿（需要 DEEPSEEK_API_KEY）
python -m aitest generate --spec specs/ruoyi-openapi.json --provider deepseek \
    --model deepseek-v4-pro --out-dir reports/ai/run

# 2) 用 client map 生成可执行测试
python -m aitest scaffold --cases reports/ai/run/cases.json \
    --out-dir tests_from_ai --client-map specs/ruoyi-client-map.json

# 3) 在真实服务上跑
python -m pytest tests_from_ai -q
```

## 当前状态（一次真实运行）

```
4 failed, 23 passed, 12 skipped
```

| 类别 | 条数 | 说明 |
|---|---|---|
| 通过 | 23 | 生成 → 评审 → 执行 全链路打通的用例 |
| 显式跳过 | 12 | 3 个接口（`POST /system/user`、`DELETE /system/user/{userId}`、`DELETE /monitor/job/{jobId}`）在客户端里没有封装方法，**显式 `pytest.skip` 而不是空跑通过** |
| 失败 | 4 | 2 条用了不存在的账号（`testuser`）；2 条 AI 认为「应该被拒绝」但服务正常返回（分页上限、状态筛选）——需要人工判断是产品问题还是断言过严 |

## 关于 client map

`specs/ruoyi-client-map.json` 是**人工维护**的：它声明「哪个接口 → 调用哪个客户端方法」，
以及哪些参数要在运行时取（例如登录验证码必须实时从 Redis 读，不能写死）。
**映射不到的接口不会被猜方法名**，而是生成 `pytest.skip` 并提示需要人工补齐 ——
猜错方法名会产出「语法正确但语义错误」的代码，比显式跳过危险得多。

## 维护须知

- `conftest.py` 里的 `_reset_auth` 是**必需**的：权限类用例会摘掉 `Authorization` 头，
  而用例体内的恢复语句在断言失败或 `pytest.skip()` 时不会执行，
  会导致同一个 session 客户端上的后续用例全部拿到 401（曾真实发生过，4 条用例集体失败）。
- 新增接口时要同步更新 client map，否则新用例只是被跳过。
