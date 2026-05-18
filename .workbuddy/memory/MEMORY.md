# 项目长期记忆

## 项目概况
- 生物安全数据联合统计系统 (secbcos)
- FastAPI + SQLAlchemy + MySQL + Alembic 后端
- Vue 3 + TypeScript + Pinia + Element Plus 前端
- JWT Bearer 认证，bcrypt 密码哈希

## 已完成阶段
- 第1阶段：数据库底座与默认演示数据
- 第2阶段：用户系统与三类角色作用域控制
- 第3阶段：群组基础管理与生命周期起步

## 关键约定
- 角色: admin / user / governor
- 作用域: platform / agency / group
- 后端服务风格：函数式（task_service, access_control_service）和静态类方法混合（AuthService）
- API 返回格式：`{"code": 0, "message": "success", "data": ...}`
- 菜单由后端 menu_service.py 动态返回
- 前端群组管理路由：/groups（不是 /group-manage）
- 权限检查：get_accessible_group_ids 返回用户所有加入群组（不限状态），因为 draft 状态的创建人仍需访问
- group_code 唯一性校验在创建时检查
- 群组创建是6表事务：group_info + group_member + sys_user_group + sys_user_role_binding + group_lifecycle_log + sys_user_operate_log

## 数据库关键 ID
- 机构：北京市疾控中心 id=10, 海淀区医院 Alice id=11, 朝阳区医院 Bob id=12
- 用户：platform_admin id=5, group_admin id=8, business_user id=6, chain_governor id=7
- 默认群组：GROUP_FLU_BEIJING_2026 id=1, lead_agency_id=10

## 下一步
- 第4阶段：群组成员、用户、节点授权配置
