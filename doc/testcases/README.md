# 认证模块 - 测试用例汇总

> 接口来源：http://localhost:18080/v3/api-docs
> 测试框架：Pytest + Requests + Allure
> 生成日期：2026-08-08

## 系统管理模块

| 接口 | 文档 | 用例数 | P0 | P1 | P2 |
|------|------|--------|----|----|----|
| 用户管理 GET /system/user/* | [TC-USER-用户管理.md](TC-USER-用户管理.md) | 5 | 3 | 2 | 0 |
| 角色管理 GET /system/role/* | [TC-ROLE-角色管理.md](TC-ROLE-角色管理.md) | 5 | 3 | 2 | 0 |
| 菜单管理 GET /system/menu/* | [TC-MENU-菜单管理.md](TC-MENU-菜单管理.md) | 4 | 3 | 1 | 0 |
| 部门管理 GET /system/dept/list | [TC-DEPT-部门管理.md](TC-DEPT-部门管理.md) | 3 | 2 | 1 | 0 |
| 岗位管理 GET /system/post/list | [TC-POST-岗位管理.md](TC-POST-岗位管理.md) | 3 | 2 | 1 | 0 |
| 字典管理 GET /system/dict/* | [TC-DICT-字典管理.md](TC-DICT-字典管理.md) | 4 | 3 | 1 | 0 |
| 参数设置 GET /system/config/list | [TC-CONFIG-参数设置.md](TC-CONFIG-参数设置.md) | 3 | 2 | 1 | 0 |
| 通知公告 GET /system/notice/list | [TC-NOTICE-通知公告.md](TC-NOTICE-通知公告.md) | 3 | 2 | 1 | 0 |
| **系统管理合计** | | **30** | **20** | **10** | **0** |

## 认证模块

| 接口 | 文档 | 用例数 | P0 | P1 | P2 |
|------|------|--------|-----|-----|-----|
| 验证码 GET /captchaImage | [TC-CAPTCHA-验证码.md](TC-CAPTCHA-验证码.md) | 3 | 1 | 0 | 2 |
| 登录 POST /login | [TC-LOGIN-登录.md](TC-LOGIN-登录.md) | 14 | 9 | 2 | 3 |
| 注册 POST /register | [TC-REG-注册.md](TC-REG-注册.md) | 15 | 10 | 2 | 3 |
| 路由 GET /getRouters | [TC-ROUTE-路由.md](TC-ROUTE-路由.md) | 5 | 3 | 0 | 2 |
| 用户信息 GET /getInfo | [TC-INFO-用户信息.md](TC-INFO-用户信息.md) | 5 | 3 | 0 | 2 |
| **认证模块合计** | | **42** | **26** | **4** | **12** |

## 全部汇总

| 模块 | 用例数 | P0 | P1 | P2 |
|------|--------|----|----|-----|
| 认证模块 | 42 | 26 | 4 | 12 |
| 系统管理模块 | 30 | 20 | 10 | 0 |
| **总计** | **72** | **46** | **14** | **12** |

## 场景覆盖

| 场景类型 | 覆盖用例数 | 占比 |
|----------|-----------|------|
| 正常场景 | 19 | 26% |
| 异常场景（参数为空/缺失/错误/超长/重复） | 23 | 32% |
| 权限场景（无Token/无效Token） | 30 | 42% |

## 优先级说明

| 优先级 | 含义 | 数量 |
|--------|------|------|
| P0 | 核心功能，必须通过 | 46 |
| P1 | 重要功能，边界值覆盖 | 14 |
| P2 | 辅助验证，性能/数据一致性 | 12 |

## 代码映射

| 用例文档 | 测试代码 |
|----------|----------|
| TC-CAPTCHA-验证码.md | tests/test_captcha.py |
| TC-LOGIN-登录.md | tests/test_login.py |
| TC-REG-注册.md | tests/test_register.py |
| TC-ROUTE-路由.md | tests/test_get_routers.py |
| TC-INFO-用户信息.md | tests/test_get_info.py |
| TC-USER-用户管理.md | tests/system/test_user.py |
| TC-ROLE-角色管理.md | tests/system/test_role.py |
| TC-MENU-菜单管理.md | tests/system/test_menu.py |
| TC-DEPT-部门管理.md | tests/system/test_dept.py |
| TC-POST-岗位管理.md | tests/system/test_post.py |
| TC-DICT-字典管理.md | tests/system/test_dict.py |
| TC-CONFIG-参数设置.md | tests/system/test_config.py |
| TC-NOTICE-通知公告.md | tests/system/test_notice.py |

## 运行命令

```bash
pytest tests/ -v --tb=short --alluredir=allure-results
```