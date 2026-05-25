from datetime import datetime
from .enums import UserStatus


class User:
    def __init__(
        self,
        id: int | None = None,
        username: str = "",
        password_hash: str = "",
        real_name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        agency_id: int | None = None,
        status: str = "active",
        last_login_time: datetime | None = None,
        last_login_ip: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.real_name = real_name
        self.phone = phone
        self.email = email
        self.agency_id = agency_id
        self._status = status
        self.last_login_time = last_login_time
        self.last_login_ip = last_login_ip
        self.created_at = created_at
        self.updated_at = updated_at

    @property
    def status(self) -> str:
        return self._status

    def is_active(self) -> bool:
        return self._status == UserStatus.ACTIVE.value

    def enable(self) -> None:
        self._status = UserStatus.ACTIVE.value

    def disable(self) -> None:
        self._status = UserStatus.DISABLED.value

    def record_login(self, ip_address: str | None = None) -> None:
        self.last_login_time = datetime.now()
        self.last_login_ip = ip_address
