"""等待请求 SQLAlchemy 数据模型"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

# 复用 mailbox 模块中定义的 Base 类，确保所有表在同一 metadata 中
from infrastructure.mailbox.models.mailbox_account_model import Base


class WaitRequestModel(Base):
    """
    等待请求数据库模型

    对应领域层的 WaitRequest 实体
    """

    __tablename__ = "wait_requests"

    # 主键
    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    # 关联信息
    mailbox_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # 业务信息
    service_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    callback_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    # 状态
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="pending", index=True
    )

    # 结果
    extraction_result: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # 版本（乐观锁）
    version: Mapped[int] = mapped_column(default=0)

    def __repr__(self) -> str:
        return f"<WaitRequestModel(id={self.id}, email={self.email}, service={self.service_name}, status={self.status})>"
