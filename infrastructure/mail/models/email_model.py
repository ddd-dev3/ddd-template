"""邮件 SQLAlchemy 数据模型"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.mailbox.models.mailbox_account_model import Base


class EmailModel(Base):
    """
    邮件数据库模型

    对应领域层的 Email 实体
    """

    __tablename__ = "emails"

    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 关联邮箱
    mailbox_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    # 邮件标识
    message_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # 邮件信息
    from_address: Mapped[str] = mapped_column(String(512), nullable=False)
    subject: Mapped[str] = mapped_column(String(1024), nullable=False, default="")

    # 邮件正文
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 时间
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 处理状态
    is_processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 版本（乐观锁）
    version: Mapped[int] = mapped_column(nullable=False, default=0)

    def __repr__(self) -> str:
        message_id_display = (self.message_id[:30] + "...") if self.message_id and len(self.message_id) > 30 else (self.message_id or "")
        subject_display = (self.subject[:30] + "...") if self.subject and len(self.subject) > 30 else (self.subject or "")
        return f"<EmailModel(id={self.id}, message_id={message_id_display}, subject={subject_display})>"
