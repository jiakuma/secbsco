# domain/ports.py
# 领域端口定义文件。
#
# 在六边形架构中，port 表示“领域层需要什么能力”，但不关心这些能力具体如何实现。
# 例如：
# - AgencyRepository 表示机构数据读写能力
# - AgencyPermissionPort 表示机构权限校验能力
# - AgencyAuditPort 表示审计日志和上链存证能力
#
# 领域层只依赖这些抽象接口，不直接依赖数据库、FastAPI、SQLAlchemy、区块链 SDK 等技术细节。
# 具体实现由 adapters 层完成。

from abc import ABC, abstractmethod
from typing import Any, Optional, List, Tuple, Dict

# 机构领域实体
from .models import Agency

# 用户上下文与审计元数据值对象
from .value_objects import UserContext, AuditMetadata


class AgencyRepository(ABC):
    """
    机构仓储端口。

    职责：
    定义机构数据访问所需的抽象能力，包括查询、列表、树结构、保存、删除等。

    注意：
    这里不写 SQL，也不直接操作数据库。
    具体数据库实现应放在 adapters/persistence.py 中，
    例如 SQLAlchemyAgencyRepository。
    """

    @abstractmethod
    def get_by_id(self, agency_id: int) -> Optional[Agency]:
        """
        根据机构 ID 查询机构。

        参数：
        - agency_id：机构主键 ID

        返回：
        - Agency：查询到的机构领域对象
        - None：机构不存在
        """
        ...

    @abstractmethod
    def get_by_code(self, agency_code: str) -> Optional[Agency]:
        """
        根据机构编码查询机构。

        参数：
        - agency_code：机构编码，例如 CDC_CHANGAN

        返回：
        - Agency：查询到的机构领域对象
        - None：机构不存在
        """
        ...

    @abstractmethod
    def list_agencies(
        self,
        manageable_ids: Optional[List[int]] = None,
        keyword: Optional[str] = None,
        agency_level: Optional[str] = None,
        agency_type: Optional[str] = None,
        status: Optional[str] = None,
        parent_agency_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Agency], int]:
        """
        分页查询机构列表。

        参数：
        - manageable_ids：当前用户可管理的机构 ID 范围；
          如果为 None，通常表示不限制机构范围，例如平台管理员。
        - keyword：关键词，可用于匹配机构名称、机构编码等。
        - agency_level：机构层级筛选，例如 national / province / city / county。
        - agency_type：机构类型筛选，例如 cdc / hospital / lab。
        - status：机构状态筛选，例如 active / disabled。
        - parent_agency_id：上级机构 ID，用于查询某个机构的下级机构。
        - page：页码，默认第 1 页。
        - page_size：每页数量，默认 10 条。

        返回：
        - List[Agency]：当前页机构列表
        - int：符合条件的总数量
        """
        ...

    @abstractmethod
    def get_agency_tree(self, manageable_ids: Optional[List[int]] = None) -> List[Dict]:
        """
        获取机构树。

        参数：
        - manageable_ids：当前用户可查看或管理的机构 ID 范围；
          如果为 None，通常表示查询全部机构树。

        返回：
        - List[Dict]：树形结构数据，通常用于前端机构级联选择器或机构树展示。
        """
        ...

    @abstractmethod
    def save(self, agency: Agency) -> Agency:
        """
        保存机构。

        职责：
        - 新增机构时，将领域对象持久化到数据库。
        - 编辑机构时，将领域对象的变更同步到数据库。

        参数：
        - agency：机构领域对象

        返回：
        - 保存后的 Agency 对象，通常包含数据库生成的 ID、时间字段等。
        """
        ...

    @abstractmethod
    def delete(self, agency_id: int) -> Dict:
        """
        删除机构。

        参数：
        - agency_id：待删除机构 ID

        返回：
        - Dict：删除结果，可包含删除机构、关联用户、节点等统计信息。

        注意：
        当前项目规则中，删除机构可能涉及关联数据处理。
        具体删除逻辑由 persistence 适配器实现。
        """
        ...

    @abstractmethod
    def get_agency_and_descendant_ids(self, root_agency_id: int) -> List[int]:
        """
        获取某个机构及其所有下级机构 ID。

        参数：
        - root_agency_id：根机构 ID

        返回：
        - List[int]：包含 root_agency_id 自身及所有子孙机构 ID。

        使用场景：
        机构管理员查看本机构及下辖机构范围内的数据。
        """
        ...

    @abstractmethod
    def get_agency_name(self, agency_id: Optional[int]) -> Optional[str]:
        """
        根据机构 ID 获取机构名称。

        参数：
        - agency_id：机构 ID，可为空。

        返回：
        - str：机构名称
        - None：机构不存在或 agency_id 为空
        """
        ...

    @abstractmethod
    def get_summary(self, agency_id: int) -> Dict:
        """
        获取机构摘要信息。

        参数：
        - agency_id：机构 ID

        返回：
        - Dict：机构摘要数据，例如下级机构数量、用户数量、节点数量等。
        """
        ...


class AgencyPermissionPort(ABC):
    """
    机构权限端口。

    职责：
    定义机构相关操作需要的权限能力。

    领域服务或应用服务通过该端口进行权限判断，
    不直接依赖具体权限表、角色表或 SQL 查询逻辑。
    """

    @abstractmethod
    def get_manageable_agency_ids(self, user: UserContext) -> Optional[List[int]]:
        """
        获取当前用户可管理的机构 ID 范围。

        参数：
        - user：当前操作用户上下文

        返回：
        - List[int]：用户可管理的机构 ID 列表
        - None：不限制机构范围，通常表示平台管理员

        使用场景：
        查询机构列表、节点列表、用户列表时，用于权限过滤。
        """
        ...

    @abstractmethod
    def check_can_create_child_agency(
        self,
        user: UserContext,
        parent_agency_id: Optional[int],
        agency_level: Optional[str],
    ) -> None:
        """
        校验当前用户是否可以在指定父机构下创建子机构。

        参数：
        - user：当前操作用户上下文
        - parent_agency_id：拟创建机构的上级机构 ID
        - agency_level：拟创建机构层级

        返回：
        - None：校验通过

        异常：
        - 如果没有权限，应在具体实现中抛出权限异常。
        """
        ...

    @abstractmethod
    def check_can_manage_agency(self, user: UserContext, agency_id: int) -> None:
        """
        校验当前用户是否可以管理指定机构。

        参数：
        - user：当前操作用户上下文
        - agency_id：目标机构 ID

        返回：
        - None：校验通过

        使用场景：
        编辑机构、删除机构、启用机构、停用机构前进行权限校验。
        """
        ...


class AgencyAuditPort(ABC):
    """
    机构审计端口。

    职责：
    定义机构操作后的审计记录和资源操作存证能力。

    领域层只声明需要写日志、做存证，
    但不关心日志写入哪张表，也不关心区块链如何调用。
    """

    @abstractmethod
    def write_operate_log(self, metadata: AuditMetadata, user: UserContext) -> None:
        """
        写入机构操作日志。

        参数：
        - metadata：审计元数据，例如操作类型、资源类型、资源 ID、机构 ID。
        - user：当前操作用户上下文。

        返回：
        - None

        使用场景：
        新增、编辑、删除、启用、停用机构等操作完成后记录日志。
        """
        ...

    @abstractmethod
    def anchor_resource_operation(
        self,
        *,
        resource_type: str,
        resource_id: int,
        operation_type: str,
        operator: UserContext,
        agency_id: Optional[int],
        before_data: Optional[Agency],
        after_data: Optional[Agency],
    ) -> None:
        """
        对资源操作进行存证。

        参数：
        - resource_type：资源类型，例如 agency。
        - resource_id：资源 ID。
        - operation_type：操作类型，例如 create / update / delete / enable / disable。
        - operator：操作人上下文。
        - agency_id：资源所属机构 ID。
        - before_data：操作前的机构数据，新增时通常为 None。
        - after_data：操作后的机构数据，删除时通常为 None。

        返回：
        - None

        使用场景：
        机构新增、修改、删除等关键操作后，将操作摘要写入区块链或存证服务。
        """
        ...