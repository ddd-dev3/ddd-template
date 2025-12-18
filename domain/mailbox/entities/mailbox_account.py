"""邮箱账号聚合根实体"""

from dataclasses import dataclass, field
from typing import Optional, Union
from uuid import UUID

from domain.common.base_entity import BaseEntity
from domain.common.exceptions import (
    InvalidOperationException,
    InvalidStateTransitionException,
)
from domain.mailbox.value_objects.mailbox_enums import MailboxType, MailboxStatus
from domain.mailbox.value_objects.imap_config import ImapConfig
from domain.mailbox.value_objects.encrypted_password import EncryptedPassword


@dataclass(eq=False)
class MailboxAccount(BaseEntity):
    """
    邮箱账号聚合根

    管理邮箱账号的完整生命周期，包括：
    - 邮箱基本信息（用户名、类型）
    - IMAP 连接配置
    - 加密存储的密码
    - 使用状态追踪

    Attributes:
        username: 邮箱地址/用户名
        mailbox_type: 邮箱类型（domain_catchall, hotmail）
        imap_config: IMAP 服务器配置
        encrypted_password: 加密存储的密码
        domain: 域名（仅 domain_catchall 类型需要）
        status: 邮箱状态（available, occupied）
        occupied_by_service: 占用该邮箱的服务名称
    """

    username: str = field(default="")
    mailbox_type: MailboxType = field(default=MailboxType.DOMAIN_CATCHALL)
    imap_config: Optional[ImapConfig] = field(default=None)
    encrypted_password: Optional[EncryptedPassword] = field(default=None)
    domain: Optional[str] = field(default=None)
    status: MailboxStatus = field(default=MailboxStatus.AVAILABLE)
    occupied_by_service: Optional[str] = field(default=None)

    def __post_init__(self) -> None:
        """初始化后验证"""
        self._validate()

    def _validate(self) -> None:
        """验证邮箱账号的有效性"""
        if not self.username:
            raise InvalidOperationException(
                operation="create_mailbox_account",
                reason="Username cannot be empty"
            )

        if self.mailbox_type == MailboxType.DOMAIN_CATCHALL and not self.domain:
            raise InvalidOperationException(
                operation="create_mailbox_account",
                reason="Domain is required for domain_catchall mailbox type"
            )

    @classmethod
    def create_domain_catchall(
        cls,
        username: str,
        domain: str,
        imap_config: ImapConfig,
        password: str,
        encryption_key: Union[str, bytes],
        id: Optional[UUID] = None,
    ) -> "MailboxAccount":
        """
        工厂方法：创建域名 Catch-All 邮箱

        Args:
            username: 邮箱地址
            domain: 域名
            imap_config: IMAP 配置
            password: 明文密码（将被加密存储）
            encryption_key: 加密密钥
            id: 可选的 UUID，不提供则自动生成

        Returns:
            MailboxAccount 实例
        """
        encrypted_password = EncryptedPassword.from_plain(password, encryption_key)

        kwargs = {
            "username": username,
            "mailbox_type": MailboxType.DOMAIN_CATCHALL,
            "imap_config": imap_config,
            "encrypted_password": encrypted_password,
            "domain": domain,
            "status": MailboxStatus.AVAILABLE,
        }

        if id is not None:
            kwargs["id"] = id

        return cls(**kwargs)

    @classmethod
    def create_hotmail(
        cls,
        username: str,
        imap_config: ImapConfig,
        password: str,
        encryption_key: Union[str, bytes],
        id: Optional[UUID] = None,
    ) -> "MailboxAccount":
        """
        工厂方法：创建 Hotmail 邮箱

        Args:
            username: 邮箱地址
            imap_config: IMAP 配置
            password: 明文密码（将被加密存储）
            encryption_key: 加密密钥
            id: 可选的 UUID，不提供则自动生成

        Returns:
            MailboxAccount 实例
        """
        encrypted_password = EncryptedPassword.from_plain(password, encryption_key)

        kwargs = {
            "username": username,
            "mailbox_type": MailboxType.HOTMAIL,
            "imap_config": imap_config,
            "encrypted_password": encrypted_password,
            "domain": None,
            "status": MailboxStatus.AVAILABLE,
        }

        if id is not None:
            kwargs["id"] = id

        return cls(**kwargs)

    def occupy(self, service_name: str) -> None:
        """
        标记邮箱被某服务占用

        Args:
            service_name: 占用服务的名称

        Raises:
            InvalidStateTransitionException: 如果邮箱已被占用
        """
        if self.status == MailboxStatus.OCCUPIED:
            raise InvalidStateTransitionException(
                entity="MailboxAccount",
                from_state=self.status.value,
                to_state=MailboxStatus.OCCUPIED.value,
                reason=f"Mailbox is already occupied by service: {self.occupied_by_service}"
            )

        self.status = MailboxStatus.OCCUPIED
        self.occupied_by_service = service_name
        self.update_timestamp()

    def release(self) -> None:
        """
        释放邮箱占用

        Raises:
            InvalidStateTransitionException: 如果邮箱未被占用
        """
        if self.status == MailboxStatus.AVAILABLE:
            raise InvalidStateTransitionException(
                entity="MailboxAccount",
                from_state=self.status.value,
                to_state=MailboxStatus.AVAILABLE.value,
                reason="Mailbox is not occupied"
            )

        self.status = MailboxStatus.AVAILABLE
        self.occupied_by_service = None
        self.update_timestamp()

    def get_decrypted_password(self, encryption_key: Union[str, bytes]) -> str:
        """
        获取解密后的密码

        Args:
            encryption_key: 加密密钥

        Returns:
            明文密码

        Raises:
            InvalidOperationException: 如果没有设置密码
        """
        if self.encrypted_password is None:
            raise InvalidOperationException(
                operation="get_decrypted_password",
                reason="No password has been set"
            )

        return self.encrypted_password.decrypt(encryption_key)

    @property
    def is_available(self) -> bool:
        """检查邮箱是否可用"""
        return self.status == MailboxStatus.AVAILABLE

    @property
    def is_occupied(self) -> bool:
        """检查邮箱是否被占用"""
        return self.status == MailboxStatus.OCCUPIED
