from datetime import datetime, timedelta
from ..domain.models import User
from ..domain.ports import UserRepository, AuthPort, AccessControlPort, AuditLogPort, MenuPort, RoleBindingPort, UserGroupPort, AgencyQueryPort
from ..domain.exceptions import UserNotFound, InvalidCredentials, UserAlreadyExists, UserDisabled
from .dtos import UserDTO, LoginResultDTO, UserContextDTO, PaginatedUsersDTO


def _format_dt(dt) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None


def _to_dto(user: User, agency_name: str | None = None) -> UserDTO:
    return UserDTO(
        id=user.id, username=user.username, real_name=user.real_name,
        phone=user.phone, email=user.email, agency_id=user.agency_id,
        agency_name=agency_name, status=user.status,
        last_login_time=_format_dt(user.last_login_time),
        created_at=_format_dt(user.created_at), updated_at=_format_dt(user.updated_at),
    )


class LoginUseCase:
    def __init__(self, auth: AuthPort, audit: AuditLogPort, agency: AgencyQueryPort, user_repo: UserRepository):
        self._auth = auth
        self._audit = audit
        self._agency = agency
        self._user_repo = user_repo

    def execute(self, username: str, password: str, db=None, request=None) -> LoginResultDTO:
        user = self._auth.authenticate(username, password, db=db)
        if not user:
            raise InvalidCredentials()
        token = self._auth.create_token(user.id, user.username)
        user.record_login(ip_address=request.client.host if request and request.client else None)
        self._user_repo.save(user)
        agency_name = self._agency.get_agency_name(user.agency_id)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=user.id, username=user.username,
                operation_type="USER_LOGIN", agency_id=user.agency_id, request=request,
            )
        from app.core.config import settings
        return LoginResultDTO(
            access_token=token, token_type="bearer",
            expires_in=settings.JWT_EXPIRE_MINUTES * 60,
            user={"id": user.id, "username": user.username, "real_name": user.real_name,
                  "agency_id": user.agency_id, "agency_name": agency_name},
        )


class GetCurrentUserUseCase:
    def __init__(self, access_control: AccessControlPort):
        self._access_control = access_control

    def execute(self, user_id: int) -> UserContextDTO:
        ctx = self._access_control.get_user_context(user_id)
        return UserContextDTO(
            id=ctx["user"].id, username=ctx["user"].username,
            real_name=ctx["user"].real_name, agency_id=ctx["user"].agency_id,
            agency_name=ctx["agency_name"], current_group_id=ctx["current_group_id"],
            roles=ctx["roles"], groups=ctx["groups"], permissions=ctx["permissions"],
        )


class GetMenusUseCase:
    def __init__(self, access_control: AccessControlPort, menu: MenuPort):
        self._access_control = access_control
        self._menu = menu

    def execute(self, user_id: int) -> list[dict]:
        ctx = self._access_control.get_user_context(user_id)
        return self._menu.get_menus_for_roles(ctx["roles"])


class LogoutUseCase:
    def __init__(self, audit: AuditLogPort):
        self._audit = audit

    def execute(self, user, db=None) -> None:
        if db:
            self._audit.write_operate_log(
                db=db, user_id=user.id, username=user.username,
                operation_type="USER_LOGOUT", agency_id=user.agency_id,
            )


class ListUsersUseCase:
    def __init__(self, user_repo: UserRepository, access_control: AccessControlPort, agency: AgencyQueryPort):
        self._repo = user_repo
        self._access_control = access_control
        self._agency = agency

    def execute(self, current_user, **filters) -> PaginatedUsersDTO:
        manageable_ids = self._access_control.get_manageable_agency_ids(current_user)
        users, total = self._repo.list_users(manageable_ids=manageable_ids, **filters)
        items = [_to_dto(u, self._agency.get_agency_name(u.agency_id)) for u in users]
        return PaginatedUsersDTO(total=total, page=filters.get("page", 1), page_size=filters.get("page_size", 10), items=items)


class GetUserDetailUseCase:
    def __init__(self, user_repo: UserRepository, agency: AgencyQueryPort):
        self._repo = user_repo
        self._agency = agency

    def execute(self, user_id: int) -> UserDTO:
        user = self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFound()
        return _to_dto(user, self._agency.get_agency_name(user.agency_id))


class CreateUserUseCase:
    def __init__(self, user_repo: UserRepository, auth: AuthPort, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = user_repo
        self._auth = auth
        self._audit = audit
        self._agency = agency

    def execute(self, payload: dict, current_user, db=None, request=None) -> UserDTO:
        username = payload.get("username")
        if self._repo.get_by_username(username):
            raise UserAlreadyExists()
        user = User(
            username=username,
            password_hash=self._auth.hash_password(payload.get("password", "")),
            real_name=payload.get("real_name"),
            phone=payload.get("phone"),
            email=payload.get("email"),
            agency_id=payload.get("agency_id"),
            status=payload.get("status", "active"),
        )
        user = self._repo.save(user)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="USER_CREATE", resource_type="user",
                resource_id=user.id, agency_id=user.agency_id, request=request,
            )
        return _to_dto(user, self._agency.get_agency_name(user.agency_id))


class UpdateUserUseCase:
    def __init__(self, user_repo: UserRepository, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = user_repo
        self._audit = audit
        self._agency = agency

    def execute(self, user_id: int, payload: dict, current_user, db=None, request=None) -> UserDTO:
        user = self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFound()
        for field in ["real_name", "phone", "email", "agency_id", "status"]:
            if field in payload and payload[field] is not None:
                setattr(user, field, payload[field])
        user.updated_at = datetime.now()
        user = self._repo.save(user)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="USER_UPDATE", resource_type="user",
                resource_id=user.id, agency_id=user.agency_id, request=request,
            )
        return _to_dto(user, self._agency.get_agency_name(user.agency_id))


class EnableUserUseCase:
    def __init__(self, user_repo: UserRepository, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = user_repo
        self._audit = audit
        self._agency = agency

    def execute(self, user_id: int, current_user, db=None, request=None) -> UserDTO:
        user = self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFound()
        user.enable()
        user = self._repo.save(user)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="USER_ENABLE", resource_type="user",
                resource_id=user.id, request=request,
            )
        return _to_dto(user, self._agency.get_agency_name(user.agency_id))


class DisableUserUseCase:
    def __init__(self, user_repo: UserRepository, audit: AuditLogPort, agency: AgencyQueryPort):
        self._repo = user_repo
        self._audit = audit
        self._agency = agency

    def execute(self, user_id: int, current_user, db=None, request=None) -> UserDTO:
        user = self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFound()
        user.disable()
        user = self._repo.save(user)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="USER_DISABLE", resource_type="user",
                resource_id=user.id, request=request,
            )
        return _to_dto(user, self._agency.get_agency_name(user.agency_id))


class DeleteUserUseCase:
    def __init__(self, user_repo: UserRepository, audit: AuditLogPort):
        self._repo = user_repo
        self._audit = audit

    def execute(self, user_id: int, current_user, db=None, request=None) -> dict:
        user = self._repo.get_by_id(user_id)
        if not user:
            raise UserNotFound()
        self._repo.delete(user_id)
        if db:
            self._audit.write_operate_log(
                db=db, user_id=current_user.id, username=current_user.username,
                operation_type="USER_DELETE", resource_type="user",
                resource_id=user_id, request=request,
            )
        return {"deleted": True, "user_id": user_id}
