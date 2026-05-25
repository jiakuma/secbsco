# DDD + 六边形架构重构方案

## 生物安全数据联合统计系统

---

## 1. 文档信息

| 项目 | 内容 |
|------|------|
| 产品名称 | 生物安全数据联合统计系统 |
| 文档类型 | 架构重构方案（HLD） |
| 版本 | V1.0 |
| 日期 | 2026-05-26 |
| 作者 | CodeArts |

---

## 2. 重构目标与原则

### 2.1 当前架构问题诊断

| 问题等级 | 问题 | 具体表现 |
|----------|------|----------|
| **严重** | 贫血领域模型 | 14个模型类均为纯数据持有者，无一包含业务行为；状态机逻辑分散在Service和API层 |
| **严重** | God方法 | `create_group_with_creator_admin`、`delete_agency`、`_mock_run_federated_learning_task`、`run_task`端点等均承担7+职责 |
| **严重** | 业务/基础设施混合 | Mock逻辑混入生产代码；env变量在业务代码中控制上链策略；SQLAlchemy inspector反射侵入业务层 |
| **严重** | 跨域服务依赖 | `group_service`依赖13个模型、8个access_control函数；`task_api`编排6个Service |
| **严重** | 查询逻辑散落 | Service中内联`db.query()`；API层（stat_template_api、dataset_api）绕过Service直接查DB |
| **严重** | 外部集成无抽象 | SecretFlow/Agent/FISCO均硬编码HTTP调用，无Port接口，无重试/熔断 |
| **中等** | API层过厚 | task_api.py 80KB、group_api.py 37KB，承担编排+权限+审计 |
| **中等** | 重复代码 | 哈希计算4处重复；`_format_dt()`4处重复；`_get_visible_agency_ids()`4处相似实现 |
| **中等** | Schema闲置 | 大量端点返回手写dict而非Pydantic Schema实例 |
| **轻微** | 事务边界不清 | 直接`db.commit()/db.rollback()`散落各处 |

### 2.2 重构目标

1. **领域驱动**：将业务逻辑从Service/API层下沉到领域模型，使模型成为"富领域模型"
2. **六边形隔离**：通过Port/Adapter明确区分核心业务与基础设施（DB、外部服务、消息）
3. **限界上下文**：按业务域拆分模块，显式化跨域依赖，消除循环引用
4. **可测试性**：领域逻辑可脱离数据库和外部服务独立单元测试
5. **最小改动**：渐进式重构，不重写整个模块，每一步均可独立验证

### 2.3 重构原则

- **渐进式**：每次重构一个限界上下文，保持系统可运行
- **依赖倒置**：核心域不依赖基础设施，基础设施实现核心域定义的Port接口
- **显式化隐式逻辑**：将散落在Service中的状态机、权限规则、计算逻辑提取为领域方法或领域服务
- **消除重复**：将重复的哈希、序列化、权限过滤逻辑收敛到统一位置

---

## 3. 限界上下文划分

### 3.1 上下文映射图

```
                    ┌─────────────┐
                    │   Identity   │  用户/角色/权限
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌──▼───┐ ┌──────▼──────┐
       │   Agency    │ │ Node │ │   Group     │
       └──────┬──────┘ └──┬───┘ └──────┬──────┘
              │            │            │
              │     ┌──────▼──────┐     │
              │     │ Computation │     │
              │     └──────┬──────┘     │
              │            │            │
       ┌──────▼────────────▼────────────▼──────┐
       │                 Task                   │
       └──────┬─────────────────────────┬──────┘
              │                         │
       ┌──────▼──────┐          ┌──────▼──────┐
       │    Chain     │          │    Audit    │
       └─────────────┘          └─────────────┘

   辅助上下文：Dataset、Template（被Task/Group引用，自身逻辑简单）
```

### 3.2 上下文定义

| 上下文 | 职责 | 核心聚合根 | 关键领域事件 |
|--------|------|------------|-------------|
| **Identity** | 用户认证、RBAC权限、操作日志 | User, Role, UserRoleBinding | UserLoggedIn, RoleBound, OperationLogged |
| **Agency** | 机构树形管理、层级判断 | Agency | AgencyCreated, AgencyDisabled |
| **Node** | 节点注册、状态管理、Agent控制 | Node | NodeChecked, NodeActivated, NodeDeactivated |
| **Group** | 群组生命周期、成员/资源授权、审批 | Group | GroupCreated, GroupApproved, GroupRejected, GroupDissolving, MemberAdded, ResourceAuthorized |
| **Task** | 任务创建/配置/执行/结果 | Task, TaskResult | TaskCreated, TaskRunning, TaskSucceeded, TaskFailed, ResultAnchored |
| **Computation** | 隐私计算调度（SecretFlow集成） | 无持久化聚合，为应用服务 | ComputationSubmitted, ComputationCompleted |
| **Chain** | 区块链存证、链上校验、合约管理 | ChainRecord, ContractInfo | ContentAnchored, VerifyCompleted |
| **Audit** | 审计日志记录与查询 | AuditLog | AuditLogCreated |
| **Dataset** | 数据集资源管理 | Dataset | - |
| **Template** | 统计模板管理 | StatTemplate | - |

---

## 4. 六边形架构目录结构

### 4.1 总体结构

```
backend/
├── app/
│   ├── main.py                          # FastAPI 应用组装（仅此文件知道所有Adapter）
│   │
│   ├── contexts/                        # 按限界上下文组织
│   │   ├── identity/                    # Identity 上下文
│   │   │   ├── domain/                  #   核心域（零外部依赖）
│   │   │   │   ├── models.py            #     领域模型（富模型）
│   │   │   │   ├── value_objects.py     #     值对象
│   │   │   │   ├── enums.py             #     枚举（状态、角色等）
│   │   │   │   ├── events.py            #     领域事件
│   │   │   │   ├── ports.py             #     Port 接口（抽象）
│   │   │   │   ├── services.py          #     领域服务（纯业务逻辑）
│   │   │   │   └── exceptions.py        #     领域异常
│   │   │   ├── application/             #   应用层
│   │   │   │   ├── use_cases.py         #     用例（编排领域模型+Port）
│   │   │   │   ├── dtos.py              #     DTO（进出应用层的数据结构）
│   │   │   │   └── unit_of_work.py      #     工作单元接口
│   │   │   └── adapters/               #   适配器层
│   │   │       ├── persistence.py       #     Repository 实现（SQLAlchemy）
│   │   │       ├── api.py               #     REST 适配器（FastAPI路由）
│   │   │       └── schemas.py           #     Pydantic 请求/响应 Schema
│   │   │
│   │   ├── agency/                      # Agency 上下文（同结构）
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   └── adapters/
│   │   │
│   │   ├── node/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   └── adapters/
│   │   │       ├── persistence.py
│   │   │       ├── api.py
│   │   │       ├── schemas.py
│   │   │       └── agent_client.py      #   Agent HTTP 客户端适配器
│   │   │
│   │   ├── group/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   └── adapters/
│   │   │
│   │   ├── task/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   └── adapters/
│   │   │
│   │   ├── computation/
│   │   │   ├── domain/
│   │   │   │   ├── ports.py             #     ComputationPort 接口
│   │   │   │   └── services.py          #     计算调度领域服务
│   │   │   ├── application/
│   │   │   │   └── use_cases.py         #     执行任务用例
│   │   │   └── adapters/
│   │   │       ├── secretflow_stat.py   #   SecretFlow 联合统计适配器
│   │   │       ├── secretflow_fl.py     #   SecretFlow 联邦学习适配器
│   │   │       └── mock_computation.py  #   Mock 计算适配器
│   │   │
│   │   ├── chain/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   └── adapters/
│   │   │       ├── persistence.py
│   │   │       ├── api.py
│   │   │       ├── schemas.py
│   │   │       ├── fisco_anchor.py      #   FISCO BCOS 存证适配器
│   │   │       └── mock_anchor.py       #   Mock 存证适配器
│   │   │
│   │   ├── audit/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   └── adapters/
│   │   │
│   │   ├── dataset/
│   │   │   ├── domain/
│   │   │   ├── application/
│   │   │   └── adapters/
│   │   │
│   │   └── template/
│   │       ├── domain/
│   │       ├── application/
│   │       └── adapters/
│   │
│   ├── shared/                          # 跨上下文共享内核
│   │   ├── domain_events.py             #   领域事件总线
│   │   ├── result.py                    #   统一响应封装
│   │   ├── hashing.py                   #   统一哈希计算
│   │   ├── serialization.py             #   统一日期序列化
│   │   └── pagination.py               #   统一分页
│   │
│   └── infrastructure/                  # 全局基础设施
│       ├── database.py                  #   SQLAlchemy 引擎/Session
│       ├── config.py                    #   全局配置
│       └── security.py                 #   JWT/bcrypt（Identity的Adapter共享）
```

### 4.2 各层职责与依赖规则

```
                    ┌─────────────────────┐
                    │      Adapters       │  REST API / DB / 外部服务
                    │  (api.py, persistence│
                    │   .py, agent_client) │
                    └────────┬────────────┘
                             │ 实现
                    ┌────────▼────────────┐
                    │    Application      │  用例编排 / DTO / UoW
                    │  (use_cases.py,     │
                    │     dtos.py)        │
                    └────────┬────────────┘
                             │ 调用
                    ┌────────▼────────────┐
                    │      Domain         │  领域模型 / Port / 领域服务
                    │  (models.py, ports.py│
                    │   services.py)      │
                    └─────────────────────┘

  依赖方向：Adapters → Application → Domain（向内依赖）
  Domain 零外部依赖（不import SQLAlchemy、FastAPI、requests等）
```

---

## 5. 核心域设计（Domain 层）

### 5.1 枚举与值对象 — 消除字符串魔法值

当前问题：状态字段均为 `String(32)`，无类型约束，状态流转靠散落的if/else判断。

重构方案：将所有状态定义为中心化枚举+值对象。

```python
# contexts/task/domain/enums.py

from enum import Enum

class TaskStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskType(str, Enum):
    FEDERATED_STAT = "federated_stat"           # T1
    FEDERATED_LEARNING = "federated_learning"    # T2
    VACCINE_EVAL = "vaccine_eval"                # T3
    OTHER = "other"                              # T4

class AnchorStatus(str, Enum):
    NONE = "none"
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class PartyStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
```

```python
# contexts/group/domain/enums.py

class GroupStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    REJECTED = "rejected"
    DISSOLVING = "dissolving"
    DISSOLVED = "dissolved"
    ARCHIVED = "archived"
    DISABLED = "disabled"

class MemberRole(str, Enum):
    LEAD_AGENCY = "lead_agency"
    PARTICIPANT = "participant"
    DATA_PROVIDER = "data_provider"
    COMPUTE_PROVIDER = "compute_provider"
    OBSERVER = "observer"

class GroupApprovalStatus(str, Enum):
    NONE = "none"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class AuthStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    REVOKED = "revoked"
    ARCHIVED = "archived"
```

### 5.2 富领域模型 — 将行为从Service下沉到模型

#### 5.2.1 Task 聚合根

```python
# contexts/task/domain/models.py

from datetime import datetime
from contextlib import contextmanager
from .enums import TaskStatus, TaskType, AnchorStatus, PartyStatus
from .exceptions import TaskAlreadyRunning, InvalidStatusTransition, TaskExecutionDenied


class Task:
    """任务聚合根 — 封装状态机与业务规则"""

    def __init__(self, id, task_code, task_name, template_id, group_id,
                 creator_user_id, creator_agency_id, lead_agency_id,
                 status=TaskStatus.CREATED, params=None, **kwargs):
        self.id = id
        self.task_code = task_code
        self.task_name = task_name
        self.template_id = template_id
        self.group_id = group_id
        self.creator_user_id = creator_user_id
        self.creator_agency_id = creator_agency_id
        self.lead_agency_id = lead_agency_id
        self._status = status
        self.params = params or {}
        self.parties: list[TaskParty] = []
        self._events: list = []

    @property
    def status(self) -> TaskStatus:
        return self._status

    @property
    def task_type(self) -> TaskType:
        return TaskType(self.params.get("task_type", "federated_stat"))

    def can_run(self) -> bool:
        return self._status == TaskStatus.CREATED

    def start(self) -> None:
        """开始执行 — 状态守卫"""
        if self._status != TaskStatus.CREATED:
            raise InvalidStatusTransition(
                f"Cannot start task in {self._status.value}, expected CREATED"
            )
        self._status = TaskStatus.RUNNING
        self._record_event(TaskRunning(task_id=self.id))

    def succeed(self) -> None:
        if self._status != TaskStatus.RUNNING:
            raise InvalidStatusTransition("Cannot succeed task not in RUNNING")
        self._status = TaskStatus.SUCCESS
        self._record_event(TaskSucceeded(task_id=self.id))

    def fail(self) -> None:
        if self._status not in (TaskStatus.RUNNING, TaskStatus.CREATED):
            raise InvalidStatusTransition("Cannot fail task not in RUNNING/CREATED")
        self._status = TaskStatus.FAILED
        self._record_event(TaskFailed(task_id=self.id))

    def cancel(self) -> None:
        if self._status != TaskStatus.CREATED:
            raise InvalidStatusTransition("Cannot cancel task not in CREATED")
        self._status = TaskStatus.CANCELLED

    def add_party(self, agency_id, node_id, dataset_id, party_role, field_mapping=None):
        party = TaskParty(
            task_id=self.id,
            agency_id=agency_id,
            node_id=node_id,
            dataset_id=dataset_id,
            party_role=party_role,
            field_mapping=field_mapping,
        )
        self.parties.append(party)
        return party

    def _record_event(self, event):
        self._events.append(event)

    def pull_events(self) -> list:
        events = self._events[:]
        self._events.clear()
        return events


class TaskParty:
    def __init__(self, task_id, agency_id, node_id, dataset_id,
                 party_role, field_mapping=None, status=PartyStatus.PENDING):
        self.task_id = task_id
        self.agency_id = agency_id
        self.node_id = node_id
        self.dataset_id = dataset_id
        self.party_role = party_role
        self.field_mapping = field_mapping or {}
        self._status = status

    @property
    def status(self) -> PartyStatus:
        return self._status

    def mark_running(self):
        self._status = PartyStatus.RUNNING

    def mark_success(self):
        self._status = PartyStatus.SUCCESS

    def mark_failed(self):
        self._status = PartyStatus.FAILED


class TaskResult:
    """任务结果 — 封装存证状态"""

    def __init__(self, task_id, result_data, metrics, result_hash,
                 task_type, anchor_status=AnchorStatus.NONE):
        self.task_id = task_id
        self.result_data = result_data
        self.metrics = metrics
        self.result_hash = result_hash
        self.task_type = task_type
        self._anchor_status = anchor_status
        self.chain_record_id = None

    @property
    def anchor_status(self) -> AnchorStatus:
        return self._anchor_status

    def is_anchored(self) -> bool:
        return self._anchor_status == AnchorStatus.SUCCESS

    def mark_anchoring(self):
        if self._anchor_status not in (AnchorStatus.NONE, AnchorStatus.FAILED):
            raise InvalidStatusTransition("Cannot re-anchor in current state")
        self._anchor_status = AnchorStatus.PENDING

    def mark_anchor_success(self, chain_record_id):
        self._anchor_status = AnchorStatus.SUCCESS
        self.chain_record_id = chain_record_id

    def mark_anchor_failed(self):
        self._anchor_status = AnchorStatus.FAILED
```

#### 5.2.2 Group 聚合根

```python
# contexts/group/domain/models.py

from .enums import GroupStatus, GroupApprovalStatus, MemberRole, AuthStatus
from .exceptions import GroupNotActive, InvalidGroupOperation, ApprovalNotAllowed


class Group:
    """群组聚合根 — 封装生命周期状态机与审批规则"""

    def __init__(self, id, group_code, group_name, lead_agency_id,
                 status=GroupStatus.DRAFT, approval_required=True, **kwargs):
        self.id = id
        self.group_code = group_code
        self.group_name = group_name
        self.lead_agency_id = lead_agency_id
        self._status = status
        self._approval_status = GroupApprovalStatus.NONE
        self.approval_required = approval_required
        self.members: list[GroupMember] = []
        self.authorized_nodes: list[GroupNode] = []
        self.authorized_datasets: list[GroupDataset] = []
        self.authorized_templates: list[GroupTemplate] = []
        self._events: list = []

    @property
    def status(self) -> GroupStatus:
        return self._status

    @property
    def is_active(self) -> bool:
        return self._status == GroupStatus.ACTIVE

    def submit_for_approval(self):
        """提交审批"""
        if self._status != GroupStatus.DRAFT:
            raise InvalidGroupOperation("Only DRAFT group can submit for approval")
        if self.approval_required:
            self._status = GroupStatus.PENDING_APPROVAL
            self._approval_status = GroupApprovalStatus.PENDING
        else:
            self._status = GroupStatus.ACTIVE
            self._approval_status = GroupApprovalStatus.APPROVED

    def approve(self, approver_id):
        """审批通过"""
        if self._status != GroupStatus.PENDING_APPROVAL:
            raise InvalidGroupOperation("Group not pending approval")
        self._status = GroupStatus.ACTIVE
        self._approval_status = GroupApprovalStatus.APPROVED
        self._record_event(GroupApproved(group_id=self.id, approver_id=approver_id))

    def reject(self, rejector_id, reason):
        """驳回"""
        if self._status != GroupStatus.PENDING_APPROVAL:
            raise InvalidGroupOperation("Group not pending approval")
        self._status = GroupStatus.REJECTED
        self._approval_status = GroupApprovalStatus.REJECTED
        self._record_event(GroupRejected(group_id=self.id, rejector_id=rejector_id, reason=reason))

    def dissolve(self, reason):
        """发起解散"""
        if not self.is_active:
            raise InvalidGroupOperation("Only ACTIVE group can dissolve")
        self._status = GroupStatus.DISSOLVING

    def confirm_dissolved(self):
        if self._status != GroupStatus.DISSOLVING:
            raise InvalidGroupOperation("Group not in dissolving")
        self._status = GroupStatus.DISSOLVED

    def add_member(self, agency_id, member_role, is_lead=False):
        if not self.is_active and self._status != GroupStatus.DRAFT:
            raise GroupNotActive("Cannot add member to non-active group")
        member = GroupMember(
            group_id=self.id, agency_id=agency_id,
            member_role=member_role, is_lead=is_lead
        )
        self.members.append(member)
        self._record_event(MemberAdded(group_id=self.id, agency_id=agency_id))
        return member

    def authorize_node(self, agency_id, node_id, usage_role, resource_quota=None):
        if not self.is_active:
            raise GroupNotActive("Cannot authorize node to non-active group")
        gn = GroupNode(group_id=self.id, agency_id=agency_id,
                       node_id=node_id, node_usage_role=usage_role,
                       resource_quota=resource_quota)
        self.authorized_nodes.append(gn)
        return gn

    def _record_event(self, event):
        self._events.append(event)

    def pull_events(self):
        events = self._events[:]
        self._events.clear()
        return events
```

#### 5.2.3 Node 聚合根

```python
# contexts/node/domain/models.py

from .enums import NodeStatus, ActivationStatus, NodeLoadStatus
from .exceptions import NodeNotReady, InvalidNodeOperation


class Node:
    """节点聚合根 — 封装激活/停用状态机"""

    def __init__(self, id, node_code, node_name, agency_id, node_type,
                 activation_status=ActivationStatus.NOT_ACTIVATED,
                 status=NodeStatus.REGISTERED, **kwargs):
        self.id = id
        self.node_code = node_code
        self.node_name = node_name
        self.agency_id = agency_id
        self.node_type = node_type
        self._activation_status = activation_status
        self._status = status
        self.agent_url = kwargs.get("agent_url")
        self.agent_token = kwargs.get("agent_token")

    @property
    def activation_status(self) -> ActivationStatus:
        return self._activation_status

    @property
    def status(self) -> NodeStatus:
        return self._status

    def can_activate(self) -> bool:
        return self._activation_status in (
            ActivationStatus.NOT_ACTIVATED,
            ActivationStatus.ACTIVATION_FAILED
        )

    def mark_checking(self):
        self._status = NodeStatus.CHECKING

    def mark_active(self):
        self._status = NodeStatus.ACTIVE

    def mark_offline(self):
        self._status = NodeStatus.OFFLINE

    def start_activation(self):
        if not self.can_activate():
            raise InvalidNodeOperation("Node cannot be activated in current state")
        self._activation_status = ActivationStatus.ACTIVATING

    def complete_activation(self):
        if self._activation_status != ActivationStatus.ACTIVATING:
            raise InvalidNodeOperation("Node not in activating state")
        self._activation_status = ActivationStatus.ACTIVATED
        self._status = NodeStatus.ACTIVE

    def fail_activation(self, message):
        self._activation_status = ActivationStatus.ACTIVATION_FAILED

    def deactivate(self):
        if self._activation_status != ActivationStatus.ACTIVATED:
            raise InvalidNodeOperation("Only activated node can be deactivated")
        self._activation_status = ActivationStatus.NOT_ACTIVATED
```

### 5.3 Port 接口定义 — 核心域对基础设施的抽象

```python
# contexts/task/domain/ports.py

from abc import ABC, abstractmethod
from .models import Task, TaskParty, TaskResult
from .enums import TaskStatus


class TaskRepository(ABC):
    """任务仓储接口 — 由基础设施层实现"""

    @abstractmethod
    def get_by_id(self, task_id: int) -> Task | None: ...

    @abstractmethod
    def get_by_code(self, task_code: str) -> Task | None: ...

    @abstractmethod
    def list_tasks(self, *, group_id=None, status=None, creator_agency_id=None,
                   page=1, page_size=20) -> tuple[list[Task], int]: ...

    @abstractmethod
    def save(self, task: Task) -> Task: ...

    @abstractmethod
    def update_status(self, task_id: int, status: TaskStatus) -> None: ...


class TaskPartyRepository(ABC):
    @abstractmethod
    def get_by_task(self, task_id: int) -> list[TaskParty]: ...

    @abstractmethod
    def save(self, party: TaskParty) -> TaskParty: ...

    @abstractmethod
    def delete(self, party_id: int) -> None: ...


class TaskResultRepository(ABC):
    @abstractmethod
    def get_by_task(self, task_id: int) -> TaskResult | None: ...

    @abstractmethod
    def save(self, result: TaskResult) -> TaskResult: ...


class ComputationPort(ABC):
    """隐私计算端口 — 由SecretFlow/Mock适配器实现"""

    @abstractmethod
    def run_statistic(self, task_code: str, parties: list[dict], params: dict) -> dict:
        """执行联合统计，返回结果数据"""
        ...

    @abstractmethod
    def run_federated_learning(self, task_code: str, parties: list[dict],
                               train_config: dict, privacy_config: dict) -> dict:
        """执行联邦学习训练，返回训练指标"""
        ...
```

```python
# contexts/chain/domain/ports.py

from abc import ABC, abstractmethod
from .models import ChainRecord


class ChainAnchorPort(ABC):
    """区块链存证端口 — 由FISCO/Mock适配器实现"""

    @abstractmethod
    def anchor(self, biz_type: str, biz_id: str, content_hash: str,
               group_id: int = None, agency_id: int = None) -> ChainRecord:
        """将内容哈希锚定到区块链，返回存证记录"""
        ...

    @abstractmethod
    def verify(self, chain_record_id: int) -> str:
        """校验链上数据一致性，返回校验状态"""
        ...
```

```python
# contexts/node/domain/ports.py

from abc import ABC, abstractmethod


class NodeAgentPort(ABC):
    """节点Agent端口 — 由HTTP/Mock适配器实现"""

    @abstractmethod
    def check_health(self, agent_url: str, agent_token: str) -> dict:
        """检测Agent服务状态"""
        ...

    @abstractmethod
    def activate(self, agent_url: str, agent_token: str, config: dict) -> bool:
        """通过Agent激活节点"""
        ...

    @abstractmethod
    def deactivate(self, agent_url: str, agent_token: str) -> bool:
        """通过Agent停用节点"""
        ...
```

```python
# contexts/identity/domain/ports.py

from abc import ABC, abstractmethod


class AccessControlPort(ABC):
    """权限控制端口 — 供其他上下文查询权限"""

    @abstractmethod
    def can_access_group(self, user_id: int, group_id: int) -> bool: ...

    @abstractmethod
    def can_admin_group(self, user_id: int, group_id: int) -> bool: ...

    @abstractmethod
    def can_run_task(self, user_id: int, group_id: int) -> bool: ...

    @abstractmethod
    def get_visible_group_ids(self, user_id: int) -> list[int]: ...

    @abstractmethod
    def get_visible_agency_ids(self, user_id: int) -> list[int]: ...


class AuditLogPort(ABC):
    """审计日志端口 — 供其他上下文写入操作日志"""

    @abstractmethod
    def log_operation(self, *, user_id, operation_type, resource_type,
                      resource_id=None, group_id=None, agency_id=None,
                      request_path=None, result_status="success",
                      ip_address=None): ...
```

### 5.4 领域事件

```python
# contexts/task/domain/events.py

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TaskRunning:
    task_id: int
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskSucceeded:
    task_id: int
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass
class TaskFailed:
    task_id: int
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass
class ResultAnchored:
    task_id: int
    chain_record_id: int
    occurred_at: datetime = field(default_factory=datetime.now)
```

```python
# contexts/group/domain/events.py

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class GroupApproved:
    group_id: int
    approver_id: int
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass
class GroupRejected:
    group_id: int
    rejector_id: int
    reason: str
    occurred_at: datetime = field(default_factory=datetime.now)


@dataclass
class MemberAdded:
    group_id: int
    agency_id: int
    occurred_at: datetime = field(default_factory=datetime.now)
```

### 5.5 领域服务 — 纯业务逻辑，无基础设施依赖

```python
# contexts/task/domain/services.py

from .models import Task, TaskResult
from .ports import ComputationPort
from .enums import TaskType
from shared.hashing import compute_hash


class TaskExecutionService:
    """任务执行领域服务 — 编排计算与结果生成"""

    def __init__(self, computation_port: ComputationPort):
        self._computation = computation_port

    def execute(self, task: Task) -> TaskResult:
        """执行任务并生成结果"""
        task.start()

        try:
            if task.task_type == TaskType.FEDERATED_STAT:
                result_data = self._computation.run_statistic(
                    task_code=task.task_code,
                    parties=[p.to_dict() for p in task.parties],
                    params=task.params,
                )
            elif task.task_type == TaskType.FEDERATED_LEARNING:
                result_data = self._computation.run_federated_learning(
                    task_code=task.task_code,
                    parties=[p.to_dict() for p in task.parties],
                    train_config=task.params.get("train_config", {}),
                    privacy_config=task.params.get("privacy_config", {}),
                )
            else:
                result_data = self._computation.run_statistic(
                    task_code=task.task_code,
                    parties=[p.to_dict() for p in task.parties],
                    params=task.params,
                )

            result_hash = compute_hash(result_data)
            result = TaskResult(
                task_id=task.id,
                result_data=result_data,
                metrics=result_data.get("metrics", {}),
                result_hash=result_hash,
                task_type=task.task_type,
            )
            task.succeed()
            return result

        except Exception:
            task.fail()
            raise
```

### 5.6 共享内核 — 消除重复

```python
# shared/hashing.py

import hashlib
import json
from datetime import datetime, date


def compute_hash(data: dict) -> str:
    """统一哈希计算 — 替代4处重复的SHA256实现"""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, default=_json_default)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _json_default(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
```

```python
# shared/serialization.py

from datetime import datetime


def format_dt(dt: datetime | None) -> str | None:
    """统一日期格式化 — 替代4处重复的_format_dt()"""
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None
```

---

## 6. 应用层设计（Application 层）

### 6.1 用例 — 替代当前God方法

```python
# contexts/task/application/use_cases.py

from ..domain.models import Task
from ..domain.ports import TaskRepository, TaskResultRepository, ComputationPort
from ..domain.services import TaskExecutionService
from contexts.identity.domain.ports import AccessControlPort, AuditLogPort
from contexts.chain.domain.ports import ChainAnchorPort
from shared.hashing import compute_hash


class CreateTaskUseCase:
    """创建任务 — 单一职责"""

    def __init__(self, task_repo: TaskRepository, access_control: AccessControlPort,
                 audit_log: AuditLogPort):
        self._repo = task_repo
        self._access_control = access_control
        self._audit_log = audit_log

    def execute(self, *, task_name, template_id, group_id, creator_user_id,
                creator_agency_id, params, **kwargs) -> Task:
        task_code = Task.generate_code()
        task = Task(
            task_code=task_code, task_name=task_name,
            template_id=template_id, group_id=group_id,
            creator_user_id=creator_user_id, creator_agency_id=creator_agency_id,
            params=params, **kwargs
        )
        task = self._repo.save(task)
        self._audit_log.log_operation(
            user_id=creator_user_id, operation_type="create_task",
            resource_type="task", resource_id=task.id, group_id=group_id
        )
        return task


class RunTaskUseCase:
    """执行任务 — 编排计算+存证+审计（当前run_task端点的核心逻辑）"""

    def __init__(self, task_repo: TaskRepository, result_repo: TaskResultRepository,
                 computation: ComputationPort, chain_anchor: ChainAnchorPort,
                 access_control: AccessControlPort, audit_log: AuditLogPort):
        self._task_repo = task_repo
        self._result_repo = result_repo
        self._execution = TaskExecutionService(computation)
        self._chain_anchor = chain_anchor
        self._access_control = access_control
        self._audit_log = audit_log

    def execute(self, *, task_id: int, user_id: int) -> TaskResult:
        task = self._task_repo.get_by_id(task_id)

        self._access_control.can_run_task(user_id, task.group_id)

        result = self._execution.execute(task)

        self._task_repo.save(task)
        result = self._result_repo.save(result)

        try:
            result.mark_anchoring()
            chain_record = self._chain_anchor.anchor(
                biz_type="task_result", biz_id=str(result.task_id),
                content_hash=result.result_hash,
                group_id=task.group_id, agency_id=task.creator_agency_id
            )
            result.mark_anchor_success(chain_record.id)
        except Exception:
            result.mark_anchor_failed()

        self._result_repo.save(result)
        self._task_repo.save(task)

        self._audit_log.log_operation(
            user_id=user_id, operation_type="run_task",
            resource_type="task", resource_id=task.id, group_id=task.group_id
        )
        return result
```

### 6.2 DTO — 替代手写dict

```python
# contexts/task/application/dtos.py

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TaskDTO:
    id: int
    task_code: str
    task_name: str
    status: str
    task_type: str
    template_id: int
    group_id: int
    creator_agency_id: int
    created_at: datetime
    party_count: int = 0


@dataclass
class TaskResultDTO:
    task_id: int
    task_type: str
    result_data: dict
    metrics: dict
    result_hash: str
    anchor_status: str
    created_at: datetime
```

---

## 7. 适配器层设计（Adapters 层）

### 7.1 持久化适配器 — Repository 实现

```python
# contexts/task/adapters/persistence.py

from sqlalchemy.orm import Session
from ..domain.models import Task, TaskParty, TaskResult
from ..domain.ports import TaskRepository, TaskResultRepository
from ..domain.enums import TaskStatus
from .orm_models import TaskORM, TaskPartyORM, TaskResultORM


class SQLAlchemyTaskRepository(TaskRepository):
    """SQLAlchemy实现的Task仓储 — 将领域模型与ORM模型隔离"""

    def __init__(self, session: Session):
        self._session = session

    def get_by_id(self, task_id: int) -> Task | None:
        orm = self._session.query(TaskORM).filter(TaskORM.id == task_id).first()
        return self._to_domain(orm) if orm else None

    def save(self, task: Task) -> Task:
        orm = self._to_orm(task)
        self._session.add(orm)
        self._session.flush()
        return self._to_domain(orm)

    def list_tasks(self, *, group_id=None, status=None, page=1, page_size=20):
        query = self._session.query(TaskORM)
        if group_id:
            query = query.filter(TaskORM.group_id == group_id)
        if status:
            query = query.filter(TaskORM.status == status.value if isinstance(status, TaskStatus) else status)
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()
        return [self._to_domain(i) for i in items], total

    @staticmethod
    def _to_domain(orm: TaskORM) -> Task:
        return Task(
            id=orm.id, task_code=orm.task_code, task_name=orm.task_name,
            template_id=orm.template_id, group_id=orm.group_id,
            creator_user_id=orm.creator_user_id, creator_agency_id=orm.creator_agency_id,
            lead_agency_id=orm.lead_agency_id, status=TaskStatus(orm.status),
            params=orm.params_json,
        )

    @staticmethod
    def _to_orm(task: Task) -> TaskORM:
        return TaskORM(
            id=task.id, task_code=task.task_code, task_name=task.task_name,
            template_id=task.template_id, group_id=task.group_id,
            creator_user_id=task.creator_user_id, creator_agency_id=task.creator_agency_id,
            lead_agency_id=task.lead_agency_id, status=task.status.value,
            params_json=task.params,
        )
```

### 7.2 外部服务适配器 — 实现Port接口

#### SecretFlow 适配器

```python
# contexts/computation/adapters/secretflow_stat.py

import urllib.request
import json
import logging
from ...domain.ports import ComputationPort


class SecretFlowStatAdapter(ComputationPort):
    """SecretFlow联合统计真实适配器"""

    def __init__(self, service_url: str, timeout: int = 60):
        self._url = service_url
        self._timeout = timeout
        self._logger = logging.getLogger(__name__)

    def run_statistic(self, task_code: str, parties: list[dict], params: dict) -> dict:
        payload = json.dumps({
            "task_code": task_code,
            "parties": parties,
            "params": params,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self._url}/run/flu-stat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def run_federated_learning(self, task_code, parties, train_config, privacy_config):
        raise NotImplementedError("Use SecretFlowFLAdapter for FL tasks")


class MockComputationAdapter(ComputationPort):
    """Mock计算适配器 — 开发/测试环境使用"""

    def run_statistic(self, task_code: str, parties: list[dict], params: dict) -> dict:
        return {
            "total_cases": 1500,
            "ili_cases": 230,
            "ili_rate": 0.153,
            "metrics": {"parties_count": len(parties)},
        }

    def run_federated_learning(self, task_code, parties, train_config, privacy_config):
        rounds = train_config.get("rounds", 10)
        return {
            "final_metrics": {"loss": 0.12, "accuracy": 0.91, "auc": 0.89},
            "round_metrics": [
                {"round": i, "loss": 0.5 - 0.04 * i, "accuracy": 0.5 + 0.04 * i}
                for i in range(1, rounds + 1)
            ],
        }
```

#### FISCO BCOS 存证适配器

```python
# contexts/chain/adapters/fisco_anchor.py

import requests
import logging
from ..domain.ports import ChainAnchorPort
from ..domain.models import ChainRecord


class FiscoAnchorAdapter(ChainAnchorPort):
    """FISCO BCOS真实存证适配器"""

    def __init__(self, service_url: str, api_key: str, contract_address: str):
        self._url = service_url
        self._api_key = api_key
        self._contract_address = contract_address
        self._logger = logging.getLogger(__name__)

    def anchor(self, biz_type, biz_id, content_hash, group_id=None, agency_id=None):
        resp = requests.post(
            f"{self._url}/anchor",
            json={
                "biz_type": biz_type,
                "biz_id": biz_id,
                "content_hash": content_hash,
                "contract_address": self._contract_address,
            },
            headers={"X-API-Key": self._api_key},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return ChainRecord(
            biz_type=biz_type, biz_id=biz_id, content_hash=content_hash,
            tx_hash=data["tx_hash"], block_number=data["block_number"],
            contract_address=self._contract_address, chain_type="fisco_bcos",
        )

    def verify(self, chain_record_id):
        # 真实链上校验实现
        ...


class MockAnchorAdapter(ChainAnchorPort):
    """Mock存证适配器 — 开发/测试环境使用"""

    def anchor(self, biz_type, biz_id, content_hash, group_id=None, agency_id=None):
        return ChainRecord(
            biz_type=biz_type, biz_id=biz_id, content_hash=content_hash,
            tx_hash=f"mock_tx_{biz_id}", block_number=1,
            contract_address="0x0", chain_type="mock",
        )

    def verify(self, chain_record_id):
        return "verify_success"
```

#### Node Agent 适配器

```python
# contexts/node/adapters/agent_client.py

import requests
import logging
from ..domain.ports import NodeAgentPort


class HttpNodeAgentAdapter(NodeAgentPort):
    """HTTP Agent真实适配器"""

    def __init__(self, timeout: int = 10):
        self._timeout = timeout
        self._logger = logging.getLogger(__name__)

    def check_health(self, agent_url: str, agent_token: str) -> dict:
        try:
            resp = requests.get(
                f"{agent_url}/health",
                headers={"Authorization": f"Bearer {agent_token}"},
                timeout=self._timeout,
            )
            return {"available": resp.status_code == 200, "detail": resp.json()}
        except Exception as e:
            self._logger.warning(f"Agent check failed: {e}")
            return {"available": False, "detail": str(e)}

    def activate(self, agent_url: str, agent_token: str, config: dict) -> bool:
        try:
            resp = requests.post(
                f"{agent_url}/activate",
                json=config,
                headers={"Authorization": f"Bearer {agent_token}"},
                timeout=self._timeout,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def deactivate(self, agent_url: str, agent_token: str) -> bool:
        try:
            resp = requests.post(
                f"{agent_url}/deactivate",
                headers={"Authorization": f"Bearer {agent_token}"},
                timeout=self._timeout,
            )
            return resp.status_code == 200
        except Exception:
            return False
```

### 7.3 REST API 适配器 — 瘦控制器

```python
# contexts/task/adapters/api.py

from fastapi import APIRouter, Depends
from .schemas import TaskCreateRequest, TaskResponse
from ..application.use_cases import CreateTaskUseCase, RunTaskUseCase
from ..application.dtos import TaskDTO


def create_task_router(
    create_uc: CreateTaskUseCase,
    run_uc: RunTaskUseCase,
    get_current_user,
) -> APIRouter:
    router = APIRouter(prefix="/api/tasks", tags=["tasks"])

    @router.post("", response_model=TaskResponse)
    async def create_task(req: TaskCreateRequest, user=Depends(get_current_user)):
        task = create_uc.execute(
            task_name=req.task_name, template_id=req.template_id,
            group_id=req.group_id, creator_user_id=user.id,
            creator_agency_id=user.agency_id, params=req.params,
        )
        return TaskResponse.from_dto(TaskDTO.from_domain(task))

    @router.post("/{task_id}/run")
    async def run_task(task_id: int, user=Depends(get_current_user)):
        result = run_uc.execute(task_id=task_id, user_id=user.id)
        return {"code": 0, "message": "success", "data": {"result_hash": result.result_hash}}

    return router
```

---

## 8. 应用组装 — 依赖注入

```python
# app/main.py

from fastapi import FastAPI
from infrastructure.config import settings
from infrastructure.database import SessionLocal

# Domain Ports → Adapter 绑定（六边形的右侧）
from contexts.task.adapters.persistence import SQLAlchemyTaskRepository
from contexts.task.adapters.api import create_task_router
from contexts.computation.adapters.secretflow_stat import SecretFlowStatAdapter, MockComputationAdapter
from contexts.computation.adapters.secretflow_fl import SecretFlowFLAdapter
from contexts.chain.adapters.fisco_anchor import FiscoAnchorAdapter, MockAnchorAdapter
from contexts.node.adapters.agent_client import HttpNodeAgentAdapter

# Application Use Cases
from contexts.task.application.use_cases import CreateTaskUseCase, RunTaskUseCase

# Identity
from contexts.identity.adapters.persistence import SQLAlchemyAccessControlAdapter, SQLAlchemyAuditLogAdapter


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME)

    # --- Adapter 选择（根据环境） ---
    if settings.APP_ENV == "prod":
        computation = SecretFlowStatAdapter(settings.SECRETFLOW_STAT_SERVICE_URL)
        fl_computation = SecretFlowFLAdapter(settings.SECRETFLOW_FL_SERVICE_URL)
        chain_anchor = FiscoAnchorAdapter(
            settings.FISCO_ANCHOR_SERVICE_URL,
            settings.FISCO_ANCHOR_API_KEY,
            settings.FISCO_CONTRACT_ADDRESS,
        )
    else:
        computation = MockComputationAdapter()
        fl_computation = MockComputationAdapter()
        chain_anchor = MockAnchorAdapter()

    agent_client = HttpNodeAgentAdapter()

    # --- 依赖注入（构造函数注入，非Service Locator） ---
    def get_task_repo():
        session = SessionLocal()
        return SQLAlchemyTaskRepository(session)

    def get_access_control():
        session = SessionLocal()
        return SQLAlchemyAccessControlAdapter(session)

    def get_audit_log():
        session = SessionLocal()
        return SQLAlchemyAuditLogAdapter(session)

    task_repo = get_task_repo()
    result_repo = ...
    access_control = get_access_control()
    audit_log = get_audit_log()

    create_task_uc = CreateTaskUseCase(task_repo, access_control, audit_log)
    run_task_uc = RunTaskUseCase(task_repo, result_repo, computation, chain_anchor, access_control, audit_log)

    # --- 注册路由 ---
    from contexts.identity.adapters.api import create_auth_router
    from contexts.group.adapters.api import create_group_router
    from contexts.node.adapters.api import create_node_router

    app.include_router(create_auth_router(...))
    app.include_router(create_task_router(create_task_uc, run_task_uc, ...))
    app.include_router(create_group_router(...))
    app.include_router(create_node_router(...))

    return app


app = create_app()
```

---

## 9. 跨上下文通信机制

### 9.1 同步调用（Port 接口）

跨上下文调用通过 Port 接口实现，不直接import其他上下文的内部实现：

| 调用方 | 被调用方 | Port 接口 | 方向 |
|--------|----------|-----------|------|
| Task | Identity | `AccessControlPort.can_run_task()` | 权限校验 |
| Task | Identity | `AuditLogPort.log_operation()` | 审计记录 |
| Task | Chain | `ChainAnchorPort.anchor()` | 结果存证 |
| Task | Computation | `ComputationPort.run_statistic()` | 隐私计算 |
| Group | Identity | `AccessControlPort.can_admin_group()` | 权限校验 |
| Group | Identity | `AuditLogPort.log_operation()` | 审计记录 |
| Node | Identity | `AccessControlPort` | 权限校验 |
| Node | External | `NodeAgentPort` | Agent控制 |

### 9.2 领域事件（异步，可选演进）

当需要解耦时（如存证、审计），可通过领域事件异步处理：

```python
# shared/domain_events.py

from typing import Callable
from collections import defaultdict


class DomainEventBus:
    """简易领域事件总线 — 进程内同步/异步分发"""

    def __init__(self):
        self._handlers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type, handler):
        self._handlers[event_type].append(handler)

    def publish(self, event):
        for handler in self._handlers.get(type(event), []):
            handler(event)


event_bus = DomainEventBus()
```

```python
# main.py 中订阅事件

from contexts.task.domain.events import TaskSucceeded
from contexts.chain.application.use_cases import AnchorResultUseCase

event_bus.subscribe(TaskSucceeded, lambda e: anchor_result_uc.execute(task_id=e.task_id))
```

---

## 10. 渐进式重构路线

### 10.1 重构阶段

| 阶段 | 范围 | 具体步骤 | 验证方式 |
|------|------|----------|----------|
| **P0** | 共享内核 | 创建 `shared/` 目录，提取 `hashing.py`、`serialization.py`、`pagination.py`、`result.py`；将4处重复哈希调用替换为 `shared.hashing.compute_hash` | 全量API回归测试 |
| **P1** | Task域 | ① 创建 `contexts/task/domain/` 目录；② 提取 `enums.py`（TaskStatus等）；③ 将 `Task` 模型改为富模型（`start/succeed/fail/cancel`）；④ 提取 `ports.py`（TaskRepository、ComputationPort）；⑤ 创建 `TaskExecutionService` 领域服务 | Task相关API回归测试 + 新增领域模型单元测试 |
| **P2** | Computation适配器 | ① 创建 `contexts/computation/adapters/secretflow_stat.py` 实现 `ComputationPort`；② 创建 `mock_computation.py`；③ 替换 `task_api.py` 中直接调用SecretFlow的代码 | Mock环境运行Task执行API |
| **P3** | Group域 | ① 提取Group富模型（生命周期方法）；② 提取Group Port接口；③ 拆分 `group_service.py` 的God方法为用例 | Group生命周期API测试 |
| **P4** | Chain域 | ① 提取 `ChainAnchorPort`；② 创建 `FiscoAnchorAdapter` / `MockAnchorAdapter`；③ 替换 `ChainRecordService.mock_anchor_content()` 中的混合逻辑 | 存证API测试 |
| **P5** | Node域 | ① 提取Node富模型（激活状态机）；② 提取 `NodeAgentPort`；③ 创建 `HttpNodeAgentAdapter` | Agent检测/激活API测试 |
| **P6** | Identity域 | ① 提取 `AccessControlPort` / `AuditLogPort`；② 创建 `SQLAlchemyAccessControlAdapter`；③ 消除 `access_control_service` 中散落的DB查询 | 权限相关API测试 |
| **P7** | Agency/Template/Dataset域 | 较简单CRUD，提取Repository + Port | 各自API测试 |
| **P8** | API瘦化 | 将 `task_api.py`、`group_api.py` 中的编排逻辑移入UseCase，API仅做参数校验+调用UseCase+响应格式化 | 全量API回归测试 |
| **P9** | ORM映射隔离 | 引入 `adapters/orm_models.py` 与领域模型分离，Repository负责双向转换 | 持久化测试 |
| **P10** | 事件驱动 | 对存证、审计等非核心路径改用领域事件异步处理 | 集成测试 |

### 10.2 每阶段产出物

```
P0: shared/ 目录 + 重复代码消除
P1: contexts/task/domain/ 富模型 + Port + 领域服务 + 单元测试
P2: contexts/computation/ 适配器（Mock + SecretFlow）
P3: contexts/group/domain/ 富模型 + UseCase 拆分
P4: contexts/chain/ Port + 适配器（Mock + FISCO）
P5: contexts/node/domain/ 富模型 + Agent适配器
P6: contexts/identity/ AccessControlPort + AuditLogPort + 实现类
P7: contexts/agency|template|dataset/ 基础CRUD重构
P8: 所有API层瘦化完成
P9: ORM映射层隔离
P10: 领域事件总线 + 异步处理
```

### 10.3 风险控制

| 风险 | 缓解措施 |
|------|----------|
| 重构期间系统不可用 | 每阶段完成后全量回归测试，新旧代码可共存（Adapter逐步替换） |
| 引入Bug | 富模型方法先在Service中调用验证，再逐步移除Service中的等价逻辑 |
| 性能回退 | Repository实现可优化查询（如缓存、批量查询），不影响领域模型 |
| ORM映射复杂度 | P9阶段引入，领域模型保持纯Python，ORM模型仅在Adapter层 |
| 跨上下文依赖循环 | 严格单向依赖：Task→Identity（通过Port），Identity不依赖Task |

---

## 11. 重构前后对比

### 11.1 任务执行 — 典型对比

**重构前（task_api.py 80KB中的run_task端点）：**

```python
@router.post("/{task_id}/run")
async def run_task(task_id: int, db=Depends(get_db), user=Depends(get_current_user)):
    # API层直接：权限校验
    check_task_run_access(db, user, task.group_id)
    # API层直接：类型判断 + SecretFlow调用
    if task_type == "federated_stat":
        stat_svc = SecretFlowStatService()
        result = stat_svc.run_flu_stat(...)
    elif task_type == "federated_learning":
        fl_svc = SecretFlowFLService()
        result = fl_svc.run_flu_fl_train(...)
    # API层直接：结果写入
    task_result = TaskResult(...)
    db.add(task_result)
    # API层直接：存证
    chain_svc = ChainRecordService()
    chain_record = chain_svc.mock_anchor_content(...)
    # API层直接：审计日志
    audit_svc = AuditLogService()
    audit_svc.create_log(...)
    # API层直接：状态更新
    task.status = "success"
    db.commit()
```

**重构后（API层3行 + UseCase编排）：**

```python
# adapters/api.py — 瘦控制器
@router.post("/{task_id}/run")
async def run_task(task_id: int, user=Depends(get_current_user)):
    result = run_task_uc.execute(task_id=task_id, user_id=user.id)
    return success(data={"result_hash": result.result_hash})

# application/use_cases.py — 编排逻辑
class RunTaskUseCase:
    def execute(self, task_id, user_id):
        task = self._task_repo.get_by_id(task_id)
        self._access_control.can_run_task(user_id, task.group_id)
        result = self._execution.execute(task)          # 领域服务
        self._task_repo.save(task)
        result = self._result_repo.save(result)
        chain_record = self._chain_anchor.anchor(...)    # Port接口
        result.mark_anchor_success(chain_record.id)
        self._result_repo.save(result)
        self._audit_log.log_operation(...)               # Port接口
        return result

# domain/services.py — 纯业务逻辑（可单元测试）
class TaskExecutionService:
    def execute(self, task):
        task.start()                                     # 富模型状态守卫
        result_data = self._computation.run_statistic()  # Port接口
        result = TaskResult(...)
        task.succeed()                                   # 富模型状态守卫
        return result
```

### 11.2 关键度量对比

| 度量 | 重构前 | 重构后 |
|------|--------|--------|
| task_api.py 行数 | ~2000行 (80KB) | ~200行 |
| task_service.py God方法数 | 3个 | 0个（拆为UseCase） |
| Mock代码混入生产 | 4处 | 0处（独立Adapter） |
| 重复哈希实现 | 4处 | 1处（shared） |
| 重复日期格式化 | 4处 | 1处（shared） |
| 外部服务硬编码调用 | 3处（urllib/requests直调） | 0处（通过Port接口） |
| 状态机逻辑散落 | Service+API层 | 领域模型内（可单元测试） |
| 领域逻辑可测试性 | 需启动DB+外部服务 | 纯Python单元测试（Mock Port） |
| 跨域依赖方式 | 直接import Service/Model | 通过Port接口 |
| 新Adapter开发量 | 需改Service代码 | 实现Port接口即可（开闭原则） |

---

## 12. 附录

### 12.1 术语表

| 术语 | 含义 |
|------|------|
| 限界上下文（Bounded Context） | DDD中明确边界的问题域，上下文内模型含义唯一 |
| 聚合根（Aggregate Root） | 一组关联对象的入口，外部只能通过聚合根访问内部对象 |
| 值对象（Value Object） | 无唯一标识、通过属性判断相等的对象（如枚举、地址） |
| Port | 六边形架构中核心域定义的接口，表示对外部依赖的抽象 |
| Adapter | Port接口的具体实现（如SQLAlchemy Repository、HTTP Client） |
| Use Case | 应用层用例，编排领域模型和Port完成一个业务操作 |
| DTO | 数据传输对象，用于应用层与适配器层之间的数据传递 |
| 领域事件 | 领域内发生的有业务意义的事件，用于跨聚合/上下文通信 |
| 富领域模型 | 包含数据+行为的领域模型（vs 贫血模型仅有数据） |
| 共享内核（Shared Kernel） | 多个限界上下文共享的小型模型/工具，双方均可依赖 |

### 12.2 参考资源

- *Domain-Driven Design* — Eric Evans
- *Implementing Domain-Driven Design* — Vaughn Vernon
- *Hexagonal Architecture* — Alistair Cockburn
- *Clean Architecture* — Robert C. Martin
