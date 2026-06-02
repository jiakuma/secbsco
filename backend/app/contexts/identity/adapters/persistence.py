from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models.sys_user import SysUser
from app.models.user import SysUserRoleBinding, SysUserGroup, SysUserOperateLog
from ..domain.models import User
from ..domain.ports import UserRepository, AuthPort, AccessControlPort, AuditLogPort, MenuPort, RoleBindingPort, UserGroupPort, AgencyQueryPort


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _to_domain(orm: SysUser) -> User:
    return User(
        id=orm.id, username=orm.username, password_hash=orm.password_hash,
        real_name=orm.real_name, phone=orm.phone, email=orm.email,
        agency_id=orm.agency_id, status=orm.status,
        last_login_time=orm.last_login_time, last_login_ip=orm.last_login_ip,
        created_at=orm.created_at, updated_at=orm.updated_at,
    )


def _apply_to_orm(orm: SysUser, user: User) -> None:
    for attr in ["username", "password_hash", "real_name", "phone", "email",
                  "agency_id", "status", "last_login_time", "last_login_ip"]:
        setattr(orm, attr, getattr(user, attr))
    if user.updated_at:
        orm.updated_at = user.updated_at


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, db: Session):
        self._db = db

    def get_by_id(self, user_id: int) -> User | None:
        orm = self._db.query(SysUser).filter(SysUser.id == user_id).first()
        return _to_domain(orm) if orm else None

    def get_by_username(self, username: str) -> User | None:
        orm = self._db.query(SysUser).filter(SysUser.username == username).first()
        return _to_domain(orm) if orm else None

    def list_users(self, *, manageable_ids=None, keyword=None, status=None, agency_id=None, role_code=None, page=1, page_size=10) -> tuple[list[User], int]:
        query = self._db.query(SysUser)
        if manageable_ids is not None:
            query = query.filter(SysUser.agency_id.in_(manageable_ids))
        if keyword:
            like = f"%{keyword}%"
            query = query.filter(or_(SysUser.username.like(like), SysUser.real_name.like(like)))
        if status:
            query = query.filter(SysUser.status == status)
        if agency_id:
            query = query.filter(SysUser.agency_id == agency_id)
        if role_code:
            binding_user_ids = self._db.query(SysUserRoleBinding.user_id).filter(
                SysUserRoleBinding.role_code == role_code, SysUserRoleBinding.status == "active"
            ).subquery()
            query = query.filter(SysUser.id.in_(binding_user_ids))
        total = query.count()
        items = query.order_by(SysUser.id.asc()).offset((page - 1) * page_size).limit(page_size).all()
        return [_to_domain(i) for i in items], total

    def save(self, user: User) -> User:
        if user.id is not None:
            orm = self._db.query(SysUser).filter(SysUser.id == user.id).first()
            if orm:
                _apply_to_orm(orm, user)
                self._db.flush()
                self._db.refresh(orm)
                return _to_domain(orm)
        orm = SysUser(
            username=user.username, password_hash=user.password_hash,
            real_name=user.real_name, phone=user.phone, email=user.email,
            agency_id=user.agency_id, status=user.status,
        )
        self._db.add(orm)
        self._db.flush()
        self._db.refresh(orm)
        return _to_domain(orm)

    def delete(self, user_id: int) -> None:
        user = self._db.query(SysUser).filter(SysUser.id == user_id).first()
        if user:
            self._db.query(SysUserRoleBinding).filter(SysUserRoleBinding.user_id == user_id).delete(synchronize_session=False)
            self._db.query(SysUserGroup).filter(SysUserGroup.user_id == user_id).delete(synchronize_session=False)
            self._db.delete(user)
            self._db.flush()


class BridgeAuthPort(AuthPort):
    def __init__(self, db: Session = None):
        self._db = db

    def authenticate(self, username: str, password: str, db: Session = None) -> User | None:
        session = db or self._db
        from app.contexts.shared.auth_service import AuthService
        orm = AuthService.authenticate_user(session, username, password)
        return _to_domain(orm) if orm else None

    def hash_password(self, password: str) -> str:
        from app.core.security import get_password_hash
        return get_password_hash(password)

    def create_token(self, user_id: int, username: str) -> str:
        from app.core.security import create_access_token
        return create_access_token(subject=str(user_id), extra_data={"username": username})


class BridgeAccessControlPort(AccessControlPort):
    def __init__(self, db: Session):
        self._db = db

    def get_user_context(self, user_id: int) -> dict:
        from app.contexts.shared.access_control_service import get_user_context
        return get_user_context(self._db, user_id)

    def get_accessible_group_ids(self, user_id: int) -> list[int] | None:
        from app.contexts.shared.access_control_service import get_accessible_group_ids
        return get_accessible_group_ids(self._db, user_id)

    def check_group_admin_access(self, user_id: int, group_id: int) -> None:
        from app.contexts.shared.access_control_service import check_group_admin_access
        check_group_admin_access(self._db, user_id, group_id)

    def is_platform_admin(self, user_id: int) -> bool:
        from app.contexts.shared.access_control_service import is_platform_admin
        return is_platform_admin(self._db, user_id)

    def get_manageable_agency_ids(self, current_user) -> list[int] | None:
        from app.contexts.shared.resource_permission_service import get_manageable_agency_ids
        return get_manageable_agency_ids(self._db, current_user)

    def require_agency_in_scope(self, current_user, agency_id: int) -> None:
        from app.contexts.shared.resource_permission_service import require_agency_in_scope
        require_agency_in_scope(self._db, current_user, agency_id)

    def check_can_manage_user(self, current_user, target_user_id: int) -> None:
        from app.contexts.shared.resource_permission_service import check_can_manage_user
        check_can_manage_user(self._db, current_user, target_user_id)


class BridgeAuditLogPort(AuditLogPort):
    def write_operate_log(self, *, db, user_id, username, operation_type, resource_type=None, resource_id=None, agency_id=None, group_id=None, request=None) -> None:
        from app.contexts.shared.access_control_service import write_operate_log
        write_operate_log(db=db, user_id=user_id, username=username, operation_type=operation_type,
                          resource_type=resource_type, resource_id=resource_id, agency_id=agency_id, group_id=group_id, request=request)

    def anchor_resource_operation(self, db, *, resource_type, resource_id, operation_type, operator, agency_id=None, before_data=None, after_data=None):
        from app.contexts.shared.resource_chain_service import anchor_resource_operation
        return anchor_resource_operation(db, resource_type=resource_type, resource_id=resource_id,
                                        operation_type=operation_type, operator=operator,
                                        agency_id=agency_id, before_data=before_data, after_data=after_data)


class BridgeMenuPort(MenuPort):
    def get_menus_for_roles(self, roles: list[dict]) -> list[dict]:
        from app.contexts.shared.menu_service import get_menus_for_roles
        return get_menus_for_roles(roles)


class BridgeRoleBindingPort(RoleBindingPort):
    def __init__(self, db: Session):
        self._db = db

    def get_user_roles(self, user_id: int) -> list[dict]:
        bindings = self._db.query(SysUserRoleBinding).filter(SysUserRoleBinding.user_id == user_id, SysUserRoleBinding.status == "active").all()
        return [{"id": b.id, "user_id": b.user_id, "role_code": b.role_code, "scope_type": b.scope_type, "scope_id": b.scope_id, "status": b.status, "created_at": _format_dt(b.created_at)} for b in bindings]

    def bind_role(self, user_id: int, role_code: str, scope_type: str, scope_id: int | None, current_user, request=None) -> dict:
        existing = self._db.query(SysUserRoleBinding).filter(SysUserRoleBinding.user_id == user_id, SysUserRoleBinding.role_code == role_code, SysUserRoleBinding.scope_type == scope_type, SysUserRoleBinding.scope_id == scope_id, SysUserRoleBinding.status == "active").first()
        if existing:
            return {"id": existing.id, "user_id": user_id, "role_code": role_code, "scope_type": scope_type, "scope_id": scope_id, "status": "active"}
        binding = SysUserRoleBinding(user_id=user_id, role_code=role_code, scope_type=scope_type, scope_id=scope_id, created_by=current_user.id if current_user else None)
        self._db.add(binding)
        self._db.flush()
        return {"id": binding.id, "user_id": user_id, "role_code": role_code, "scope_type": scope_type, "scope_id": scope_id, "status": "active"}

    def unbind_role(self, binding_id: int) -> None:
        binding = self._db.query(SysUserRoleBinding).filter(SysUserRoleBinding.id == binding_id).first()
        if binding:
            binding.status = "disabled"
            binding.disabled_at = datetime.now()
            self._db.flush()


class BridgeUserGroupPort(UserGroupPort):
    def __init__(self, db: Session):
        self._db = db

    def get_user_groups(self, user_id: int) -> list[dict]:
        from app.models.group import GroupInfo
        ugs = self._db.query(SysUserGroup).filter(SysUserGroup.user_id == user_id, SysUserGroup.join_status == "active").all()
        result = []
        for ug in ugs:
            gi = self._db.query(GroupInfo).filter(GroupInfo.id == ug.group_id).first()
            result.append({"id": ug.id, "user_id": ug.user_id, "group_id": ug.group_id, "group_name": gi.group_name if gi else None, "agency_id": ug.agency_id, "join_status": ug.join_status, "created_at": _format_dt(ug.created_at)})
        return result

    def add_user_to_group(self, user_id: int, group_id: int, agency_id: int | None, current_user, request=None) -> dict:
        existing = self._db.query(SysUserGroup).filter(SysUserGroup.user_id == user_id, SysUserGroup.group_id == group_id).first()
        if existing:
            existing.join_status = "active"
            existing.agency_id = agency_id
            self._db.flush()
            return {"id": existing.id, "user_id": user_id, "group_id": group_id}
        ug = SysUserGroup(user_id=user_id, group_id=group_id, agency_id=agency_id, authorized_by=current_user.id if current_user else None)
        self._db.add(ug)
        self._db.flush()
        return {"id": ug.id, "user_id": user_id, "group_id": group_id}

    def remove_user_from_group(self, user_id: int, group_id: int) -> None:
        ug = self._db.query(SysUserGroup).filter(SysUserGroup.user_id == user_id, SysUserGroup.group_id == group_id, SysUserGroup.join_status == "active").first()
        if ug:
            ug.join_status = "disabled"
            ug.disabled_at = datetime.now()
            self._db.flush()


class BridgeAgencyQueryPort(AgencyQueryPort):
    def __init__(self, db: Session):
        self._db = db

    def get_agency_name(self, agency_id: int | None) -> str | None:
        if not agency_id:
            return None
        from app.models.agency import Agency
        a = self._db.query(Agency).filter(Agency.id == agency_id).first()
        return a.agency_name if a else None
