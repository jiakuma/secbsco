-- 群组数据备份
-- 备份时间: 2026-05-19 15:49:26.576968
-- 数据库: biosecurity_stat

-- 表结构: group_info
DROP TABLE IF EXISTS `group_info`;
CREATE TABLE `group_info` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_code` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '群组编码',
  `group_name` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '群组名称',
  `group_level` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '群组层级',
  `region_code` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '行政区划代码',
  `region_name` varchar(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '行政区划名称',
  `lead_agency_id` bigint DEFAULT NULL COMMENT '牵头机构ID',
  `description` text COLLATE utf8mb4_unicode_ci COMMENT '描述',
  `status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'draft' COMMENT '状态',
  `created_by` bigint DEFAULT NULL COMMENT '创建用户ID',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `activated_at` datetime DEFAULT NULL,
  `suspended_at` datetime DEFAULT NULL,
  `resumed_at` datetime DEFAULT NULL,
  `dissolving_at` datetime DEFAULT NULL,
  `dissolved_at` datetime DEFAULT NULL,
  `archived_at` datetime DEFAULT NULL,
  `dissolve_reason` text COLLATE utf8mb4_unicode_ci,
  `archive_policy` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creator_agency_id` bigint DEFAULT NULL COMMENT '创建人所属机构ID',
  `approval_required` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否需要审批',
  `approval_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'none' COMMENT '审批状态',
  `approval_agency_id` bigint DEFAULT NULL COMMENT '审批机构ID',
  `approved_by` bigint DEFAULT NULL COMMENT '审批通过人ID',
  `approved_at` datetime DEFAULT NULL COMMENT '审批通过时间',
  `rejected_by` bigint DEFAULT NULL COMMENT '驳回人ID',
  `rejected_at` datetime DEFAULT NULL COMMENT '驳回时间',
  `reject_reason` text COLLATE utf8mb4_unicode_ci COMMENT '驳回原因',
  PRIMARY KEY (`id`),
  UNIQUE KEY `group_code` (`group_code`),
  KEY `idx_group_code` (`group_code`),
  KEY `idx_group_status` (`status`),
  KEY `idx_group_lead_agency_id` (`lead_agency_id`),
  KEY `idx_group_region_code` (`region_code`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `group_info` (`id`, `group_code`, `group_name`, `group_level`, `region_code`, `region_name`, `lead_agency_id`, `description`, `status`, `created_by`, `created_at`, `updated_at`, `activated_at`, `suspended_at`, `resumed_at`, `dissolving_at`, `dissolved_at`, `archived_at`, `dissolve_reason`, `archive_policy`, `creator_agency_id`, `approval_required`, `approval_status`, `approval_agency_id`, `approved_by`, `approved_at`, `rejected_by`, `rejected_at`, `reject_reason`) VALUES (1, 'GROUP_FLU_HEBEI_001', '河北省流感样病例联合统计群组', 'province', '130000', '河北省', 2, '面向河北省范围内多级疾控机构开展流感样病例联合统计、阳性率分析、跨区域汇总和结果可信存证。', 'draft', 1, '2026-05-19 15:03:25', '2026-05-19 15:04:12', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'none', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO `group_info` (`id`, `group_code`, `group_name`, `group_level`, `region_code`, `region_name`, `lead_agency_id`, `description`, `status`, `created_by`, `created_at`, `updated_at`, `activated_at`, `suspended_at`, `resumed_at`, `dissolving_at`, `dissolved_at`, `archived_at`, `dissolve_reason`, `archive_policy`, `creator_agency_id`, `approval_required`, `approval_status`, `approval_agency_id`, `approved_by`, `approved_at`, `rejected_by`, `rejected_at`, `reject_reason`) VALUES (2, 'GROUP_RESP_SJZ_001', '石家庄市呼吸道传染病联合监测群组', 'city', '130100', '石家庄市', 3, '面向石家庄市下辖区县疾控机构开展呼吸道传染病病例数、去重人数、阳性人数和阳性率联合统计。', 'draft', 1, '2026-05-19 15:07:08', '2026-05-19 15:07:08', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'none', NULL, NULL, NULL, NULL, NULL, NULL);
INSERT INTO `group_info` (`id`, `group_code`, `group_name`, `group_level`, `region_code`, `region_name`, `lead_agency_id`, `description`, `status`, `created_by`, `created_at`, `updated_at`, `activated_at`, `suspended_at`, `resumed_at`, `dissolving_at`, `dissolved_at`, `archived_at`, `dissolve_reason`, `archive_policy`, `creator_agency_id`, `approval_required`, `approval_status`, `approval_agency_id`, `approved_by`, `approved_at`, `rejected_by`, `rejected_at`, `reject_reason`) VALUES (3, 'GROUP_CHANGAN_QIAOXI_001', '长安区-桥西区病例协同统计群组', 'county', '130102', '长安区、桥西区', 4, '用于长安区疾控中心与桥西区疾控中心之间开展跨区县病例数量、去重人数、阳性人数、阳性率和异常趋势的联合统计验证。', 'draft', 1, '2026-05-19 15:16:20', '2026-05-19 15:16:20', NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, 0, 'none', NULL, NULL, NULL, NULL, NULL, NULL);

-- 表结构: group_member
DROP TABLE IF EXISTS `group_member`;
CREATE TABLE `group_member` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` bigint NOT NULL COMMENT '群组ID',
  `agency_id` bigint NOT NULL COMMENT '机构ID',
  `member_role` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'participant',
  `is_lead` tinyint(1) NOT NULL DEFAULT '0',
  `join_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `joined_at` datetime DEFAULT NULL,
  `removed_at` datetime DEFAULT NULL,
  `disabled_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_group_member_group_agency` (`group_id`,`agency_id`),
  KEY `idx_group_member_group_id` (`group_id`),
  KEY `idx_group_member_agency_id` (`agency_id`),
  KEY `idx_group_member_status` (`join_status`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `group_member` (`id`, `group_id`, `agency_id`, `member_role`, `is_lead`, `join_status`, `joined_at`, `removed_at`, `disabled_at`, `created_at`, `updated_at`) VALUES (1, 1, 2, 'lead_agency', 1, 'active', '2026-05-19 15:03:25', NULL, NULL, '2026-05-19 15:03:25', '2026-05-19 15:03:25');
INSERT INTO `group_member` (`id`, `group_id`, `agency_id`, `member_role`, `is_lead`, `join_status`, `joined_at`, `removed_at`, `disabled_at`, `created_at`, `updated_at`) VALUES (2, 1, 3, 'participant', 0, 'active', '2026-05-19 15:03:25', NULL, NULL, '2026-05-19 15:03:25', '2026-05-19 15:03:25');
INSERT INTO `group_member` (`id`, `group_id`, `agency_id`, `member_role`, `is_lead`, `join_status`, `joined_at`, `removed_at`, `disabled_at`, `created_at`, `updated_at`) VALUES (3, 2, 3, 'lead_agency', 1, 'active', '2026-05-19 15:07:08', NULL, NULL, '2026-05-19 15:07:08', '2026-05-19 15:07:08');
INSERT INTO `group_member` (`id`, `group_id`, `agency_id`, `member_role`, `is_lead`, `join_status`, `joined_at`, `removed_at`, `disabled_at`, `created_at`, `updated_at`) VALUES (4, 2, 4, 'participant', 0, 'active', '2026-05-19 15:07:08', NULL, NULL, '2026-05-19 15:07:08', '2026-05-19 15:07:08');
INSERT INTO `group_member` (`id`, `group_id`, `agency_id`, `member_role`, `is_lead`, `join_status`, `joined_at`, `removed_at`, `disabled_at`, `created_at`, `updated_at`) VALUES (5, 2, 5, 'participant', 0, 'active', '2026-05-19 15:07:08', NULL, NULL, '2026-05-19 15:07:08', '2026-05-19 15:07:08');
INSERT INTO `group_member` (`id`, `group_id`, `agency_id`, `member_role`, `is_lead`, `join_status`, `joined_at`, `removed_at`, `disabled_at`, `created_at`, `updated_at`) VALUES (6, 3, 4, 'lead_agency', 1, 'active', '2026-05-19 15:16:20', NULL, NULL, '2026-05-19 15:16:20', '2026-05-19 15:16:20');
INSERT INTO `group_member` (`id`, `group_id`, `agency_id`, `member_role`, `is_lead`, `join_status`, `joined_at`, `removed_at`, `disabled_at`, `created_at`, `updated_at`) VALUES (7, 3, 5, 'participant', 0, 'active', '2026-05-19 15:16:20', NULL, NULL, '2026-05-19 15:16:20', '2026-05-19 15:16:20');

-- 表结构: group_node
DROP TABLE IF EXISTS `group_node`;
CREATE TABLE `group_node` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` bigint NOT NULL,
  `agency_id` bigint NOT NULL,
  `node_id` bigint NOT NULL,
  `node_usage_role` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `auth_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `resource_quota_json` json DEFAULT NULL,
  `priority_level` bigint NOT NULL DEFAULT '1',
  `max_concurrent_tasks` bigint NOT NULL DEFAULT '1',
  `usage_policy` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `authorized_by` bigint DEFAULT NULL,
  `authorized_at` datetime DEFAULT NULL,
  `revoked_at` datetime DEFAULT NULL,
  `archived_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_group_node_group_node` (`group_id`,`node_id`),
  KEY `idx_group_node_group_id` (`group_id`),
  KEY `idx_group_node_node_id` (`node_id`),
  KEY `idx_group_node_agency_id` (`agency_id`),
  KEY `idx_group_node_auth_status` (`auth_status`),
  KEY `idx_group_node_usage_role` (`node_usage_role`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 表结构: group_lifecycle_log
DROP TABLE IF EXISTS `group_lifecycle_log`;
CREATE TABLE `group_lifecycle_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` bigint NOT NULL,
  `event_type` varchar(64) COLLATE utf8mb4_unicode_ci NOT NULL,
  `before_status` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `after_status` varchar(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `operator_user_id` bigint DEFAULT NULL,
  `operator_name` varchar(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reason` text COLLATE utf8mb4_unicode_ci,
  `detail_json` json DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_group_lifecycle_group_id` (`group_id`),
  KEY `idx_group_lifecycle_event_type` (`event_type`),
  KEY `idx_group_lifecycle_created_at` (`created_at`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `group_lifecycle_log` (`id`, `group_id`, `event_type`, `before_status`, `after_status`, `operator_user_id`, `operator_name`, `reason`, `detail_json`, `created_at`) VALUES (1, 1, 'group_created', NULL, 'draft', 1, '平台管理员', '创建群组（直接创建）', '{"group_code": "GROUP_FLU_HEBEI_001", "group_name": "河北省流感样病例联合统计群组", "lead_agency_id": 2, "approval_status": "none", "approval_required": false, "approval_agency_id": null}', '2026-05-19 15:03:25');
INSERT INTO `group_lifecycle_log` (`id`, `group_id`, `event_type`, `before_status`, `after_status`, `operator_user_id`, `operator_name`, `reason`, `detail_json`, `created_at`) VALUES (2, 1, 'group_updated', 'draft', 'draft', 1, '平台管理员', '更新群组基础信息', '{"group_name": "河北省流感样病例联合统计群组", "description": "面向河北省范围内多级疾控机构开展流感样病例联合统计、阳性率分析、跨区域汇总和结果可信存证。", "group_level": "province", "region_code": "130000", "region_name": "河北省"}', '2026-05-19 15:04:12');
INSERT INTO `group_lifecycle_log` (`id`, `group_id`, `event_type`, `before_status`, `after_status`, `operator_user_id`, `operator_name`, `reason`, `detail_json`, `created_at`) VALUES (3, 2, 'group_created', NULL, 'draft', 1, '平台管理员', '创建群组（直接创建）', '{"group_code": "GROUP_RESP_SJZ_001", "group_name": "石家庄市呼吸道传染病联合监测群组", "lead_agency_id": 3, "approval_status": "none", "approval_required": false, "approval_agency_id": null}', '2026-05-19 15:07:08');
INSERT INTO `group_lifecycle_log` (`id`, `group_id`, `event_type`, `before_status`, `after_status`, `operator_user_id`, `operator_name`, `reason`, `detail_json`, `created_at`) VALUES (4, 3, 'group_created', NULL, 'draft', 1, '平台管理员', '创建群组（直接创建）', '{"group_code": "GROUP_CHANGAN_QIAOXI_001", "group_name": "长安区-桥西区病例协同统计群组", "lead_agency_id": 4, "approval_status": "none", "approval_required": false, "approval_agency_id": null}', '2026-05-19 15:16:20');

-- 表结构: sys_user_group
DROP TABLE IF EXISTS `sys_user_group`;
CREATE TABLE `sys_user_group` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `group_id` bigint NOT NULL,
  `agency_id` bigint DEFAULT NULL,
  `join_status` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'active',
  `authorized_by` bigint DEFAULT NULL,
  `authorized_at` datetime DEFAULT NULL,
  `disabled_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_sys_user_group_user_group` (`user_id`,`group_id`),
  KEY `idx_sys_user_group_user_id` (`user_id`),
  KEY `idx_sys_user_group_group_id` (`group_id`),
  KEY `idx_sys_user_group_agency_id` (`agency_id`),
  KEY `idx_sys_user_group_status` (`join_status`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `sys_user_group` (`id`, `user_id`, `group_id`, `agency_id`, `join_status`, `authorized_by`, `authorized_at`, `disabled_at`, `created_at`, `updated_at`) VALUES (1, 1, 1, NULL, 'active', 1, '2026-05-19 15:03:25', NULL, '2026-05-19 15:03:25', '2026-05-19 15:03:25');
INSERT INTO `sys_user_group` (`id`, `user_id`, `group_id`, `agency_id`, `join_status`, `authorized_by`, `authorized_at`, `disabled_at`, `created_at`, `updated_at`) VALUES (2, 1, 2, NULL, 'active', 1, '2026-05-19 15:07:08', NULL, '2026-05-19 15:07:08', '2026-05-19 15:07:08');
INSERT INTO `sys_user_group` (`id`, `user_id`, `group_id`, `agency_id`, `join_status`, `authorized_by`, `authorized_at`, `disabled_at`, `created_at`, `updated_at`) VALUES (3, 1, 3, NULL, 'active', 1, '2026-05-19 15:16:20', NULL, '2026-05-19 15:16:20', '2026-05-19 15:16:20');

