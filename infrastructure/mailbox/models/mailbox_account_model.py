"""邮箱账号 SQLAlchemy 数据模型"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, Integer, Boolean, DateTime, LargeBinary, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from domain.mailbox.value_objects.mailbox_enums import MailboxType, MailboxStatus


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


class MailboxAccountModel(Base):
    """
    邮箱账号数据库模型

    对应领域层的 MailboxAccount 聚合根
    """

    __tablename__ = "mailbox_accounts"

    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 邮箱基本信息
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    mailbox_type: Mapped[str] = mapped_column(String(50), nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # IMAP 配置
    imap_server: Mapped[str] = mapped_column(String(255), nullable=False)
    imap_port: Mapped[int] = mapped_column(Integer, nullable=False, default=993)
    use_ssl: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 加密密码
    encrypted_password: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    # 状态
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="available")
    occupied_by_service: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 版本（乐观锁）
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<MailboxAccountModel(id={self.id}, username={self.username}, type={self.mailbox_type})>"
