# 系统监控模块 - 测试用例汇总

> 模块：系统监控 (monitor)
> 接口数量：21 个
> 基础路径：/monitor

## 场景覆盖矩阵

| 接口 | 用例ID | 正常 | 异常 | 边界 | 权限 | 总计 |
|------|--------|:----:|:----:|:----:|:----:|:----:|
| 在线用户列表 | TC-ONLINE-001~004 | 1 | 1 | 1 | 1 | 4 |
| 在线用户强退 | TC-ONLINE-005~006 | 1 | 1 | - | - | 2 |
| 定时任务列表 | TC-JOB-001~004 | 1 | 1 | 1 | 1 | 4 |
| 定时任务详情 | TC-JOB-005~007 | 1 | 1 | 1 | - | 3 |
| 定时任务日志列表 | TC-JOBLOG-001~004 | 1 | 1 | 1 | 1 | 4 |
| 定时任务日志详情 | TC-JOBLOG-005~006 | 1 | 1 | - | - | 2 |
| 服务监控 | TC-SERVER-001~003 | 1 | 1 | - | 1 | 3 |
| 缓存监控总览 | TC-CACHE-001~003 | 1 | 1 | - | 1 | 3 |
| 缓存名称列表 | TC-CACHE-004~005 | 1 | 1 | - | - | 2 |
| 缓存键名列表 | TC-CACHE-006~007 | 1 | 1 | - | - | 2 |
| 缓存值查询 | TC-CACHE-008~009 | 1 | 1 | - | - | 2 |
| 操作日志列表 | TC-OPERLOG-001~004 | 1 | 1 | 1 | 1 | 4 |
| 登录日志列表 | TC-LOGININFO-001~004 | 1 | 1 | 1 | 1 | 4 |
| **合计** | | **13** | **13** | **7** | **6** | **39** |

## 优先级分布

| 优先级 | 数量 | 占比 |
|:------:|:----:|:----:|
| P0 | 13 | 33% |
| P1 | 19 | 49% |
| P2 | 7 | 18% |

## 代码映射

| 用例文档 | 测试代码 |
|----------|----------|
| TC-ONLINE-在线用户.md | tests/monitor/test_online.py |
| TC-JOB-定时任务.md | tests/monitor/test_job.py |
| TC-JOBLOG-定时任务日志.md | tests/monitor/test_job_log.py |
| TC-SERVER-服务监控.md | tests/monitor/test_server.py |
| TC-CACHE-缓存监控.md | tests/monitor/test_cache.py |
| TC-OPERLOG-操作日志.md | tests/monitor/test_operlog.py |
| TC-LOGININFO-登录日志.md | tests/monitor/test_logininfor.py |
