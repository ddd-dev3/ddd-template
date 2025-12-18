"""邮件 SQLAlchemy 仓储实现"""

from typing import Optional, List
from uuid import UUID

from sqlalchemy.orm import Session

from domain.mail.entities.email import Email
from domain.mail.repositories.email_repository import EmailRepository
from infrastructure.mail.models.email_model import EmailModel


class SqlAlchemyEmailRepository(EmailRepository):
    """
    邮件 SQLAlchemy 仓储实现

    提供邮件的持久化操作
    """

    def __init__(self, session: Session):
        """
        初始化仓储

        Args:
            session: SQLAlchemy Session
        """
        self._session = session

    def add(self, email: Email) -> None:
        """添加邮件记录"""
        model = self._to_model(email)
        self._session.add(model)
        self._session.commit()

    def get_by_id(self, email_id: UUID) -> Optional[Email]:
        """根据 ID 获取邮件"""
        model = self._session.query(EmailModel).filter(
            EmailModel.id == str(email_id)
        ).first()

        if model is None:
            return None

        return self._to_entity(model)

    def get_by_message_id(self, message_id: str) -> Optional[Email]:
        """根据 Message-ID 获取邮件"""
        model = self._session.query(EmailModel).filter(
            EmailModel.message_id == message_id
        ).first()

        if model is None:
            return None

        return self._to_entity(model)

    def exists_by_message_id(self, message_id: str) -> bool:
        """检查 Message-ID 是否已存在"""
        count = self._session.query(EmailModel).filter(
            EmailModel.message_id == message_id
        ).count()

        return count > 0

    def list_by_mailbox_id(self, mailbox_id: UUID) -> List[Email]:
        """获取指定邮箱的所有邮件"""
        models = self._session.query(EmailModel).filter(
            EmailModel.mailbox_id == str(mailbox_id)
        ).order_by(EmailModel.received_at.desc()).all()

        return [self._to_entity(model) for model in models]

    def list_unprocessed(self, limit: int = 100) -> List[Email]:
        """
        获取未处理的邮件

        Args:
            limit: 最大返回数量，默认 100

        Returns:
            未处理的邮件列表，按接收时间升序
        """
        models = self._session.query(EmailModel).filter(
            EmailModel.is_processed == False  # noqa: E712
        ).order_by(EmailModel.received_at.asc()).limit(limit).all()

        return [self._to_entity(model) for model in models]

    def update(self, email: Email) -> None:
        """更新邮件记录"""
        model = self._session.query(EmailModel).filter(
            EmailModel.id == str(email.id)
        ).first()

        if model is not None:
            self._update_model(model, email)
            self._session.commit()

    def remove(self, email: Email) -> None:
        """删除邮件记录"""
        model = self._session.query(EmailModel).filter(
            EmailModel.id == str(email.id)
        ).first()

        if model is not None:
            self._session.delete(model)
            self._session.commit()

    def _to_model(self, entity: Email) -> EmailModel:
        """将领域实体转换为数据模型"""
        return EmailModel(
            id=str(entity.id),
            mailbox_id=str(entity.mailbox_id),
            message_id=entity.message_id,
            from_address=entity.from_address,
            subject=entity.subject,
            body_text=entity.body_text,
            body_html=entity.body_html,
            received_at=entity.received_at,
            is_processed=entity.is_processed,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
        )

    def _to_entity(self, model: EmailModel) -> Email:
        """将数据模型转换为领域实体"""
        return Email(
            id=UUID(model.id),
            mailbox_id=UUID(model.mailbox_id),
            message_id=model.message_id,
            from_address=model.from_address,
            subject=model.subject,
            body_text=model.body_text,
            body_html=model.body_html,
            received_at=model.received_at,
            is_processed=model.is_processed,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )

    def _update_model(self, model: EmailModel, entity: Email) -> None:
        """更新数据模型"""
        model.from_address = entity.from_address
        model.subject = entity.subject
        model.body_text = entity.body_text
        model.body_html = entity.body_html
        model.received_at = entity.received_at
        model.is_processed = entity.is_processed
        model.updated_at = entity.updated_at
        model.version = entity.version
