"""等待请求 SQLAlchemy 仓储实现"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from domain.verification.entities.wait_request import WaitRequest
from domain.verification.repositories.wait_request_repository import (
    WaitRequestRepository,
)
from domain.verification.value_objects.wait_request_status import WaitRequestStatus
from infrastructure.verification.models.wait_request_model import WaitRequestModel


class SqlAlchemyWaitRequestRepository(WaitRequestRepository):
    """
    等待请求 SQLAlchemy 仓储实现

    提供等待请求的持久化操作
    """

    def __init__(self, session: Session):
        """
        初始化仓储

        Args:
            session: SQLAlchemy Session
        """
        self._session = session

    def add(self, wait_request: WaitRequest) -> None:
        """添加等待请求"""
        model = self._to_model(wait_request)
        self._session.add(model)
        self._session.commit()

    def get_by_id(self, request_id: UUID) -> Optional[WaitRequest]:
        """按 ID 获取等待请求"""
        model = (
            self._session.query(WaitRequestModel)
            .filter(WaitRequestModel.id == str(request_id))
            .first()
        )

        if model is None:
            return None

        return self._to_entity(model)

    def get_pending_by_mailbox_id(self, mailbox_id: UUID) -> Optional[WaitRequest]:
        """获取邮箱的待处理请求"""
        model = (
            self._session.query(WaitRequestModel)
            .filter(
                WaitRequestModel.mailbox_id == str(mailbox_id),
                WaitRequestModel.status == WaitRequestStatus.PENDING.value,
            )
            .first()
        )

        if model is None:
            return None

        return self._to_entity(model)

    def get_pending_by_email(self, email: str) -> Optional[WaitRequest]:
        """按邮箱地址获取待处理请求"""
        model = (
            self._session.query(WaitRequestModel)
            .filter(
                WaitRequestModel.email == email,
                WaitRequestModel.status == WaitRequestStatus.PENDING.value,
            )
            .first()
        )

        if model is None:
            return None

        return self._to_entity(model)

    def get_all_pending_by_email(self, email: str) -> List[WaitRequest]:
        """获取邮箱地址的所有待处理请求"""
        models = (
            self._session.query(WaitRequestModel)
            .filter(
                WaitRequestModel.email == email,
                WaitRequestModel.status == WaitRequestStatus.PENDING.value,
            )
            .order_by(WaitRequestModel.created_at.asc())
            .all()
        )

        return [self._to_entity(model) for model in models]

    def get_pending_by_email_and_service(
        self, email: str, service_name: str
    ) -> Optional[WaitRequest]:
        """按邮箱地址和服务名获取待处理请求"""
        model = (
            self._session.query(WaitRequestModel)
            .filter(
                WaitRequestModel.email == email,
                WaitRequestModel.service_name == service_name,
                WaitRequestModel.status == WaitRequestStatus.PENDING.value,
            )
            .first()
        )

        if model is None:
            return None

        return self._to_entity(model)

    def update(self, wait_request: WaitRequest) -> None:
        """更新等待请求"""
        model = (
            self._session.query(WaitRequestModel)
            .filter(WaitRequestModel.id == str(wait_request.id))
            .first()
        )

        if model is not None:
            self._update_model(model, wait_request)
            self._session.commit()

    def list_by_status(
        self,
        status: WaitRequestStatus,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WaitRequest]:
        """按状态列出等待请求"""
        models = (
            self._session.query(WaitRequestModel)
            .filter(WaitRequestModel.status == status.value)
            .order_by(WaitRequestModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [self._to_entity(model) for model in models]

    def delete(self, request_id: UUID) -> bool:
        """删除等待请求"""
        model = (
            self._session.query(WaitRequestModel)
            .filter(WaitRequestModel.id == str(request_id))
            .first()
        )

        if model is None:
            return False

        self._session.delete(model)
        self._session.commit()
        return True

    def _to_model(self, entity: WaitRequest) -> WaitRequestModel:
        """将领域实体转换为数据模型"""
        return WaitRequestModel(
            id=str(entity.id),
            mailbox_id=str(entity.mailbox_id),
            email=entity.email,
            service_name=entity.service_name,
            callback_url=entity.callback_url,
            status=entity.status.value,
            extraction_result=entity.extraction_result,
            completed_at=entity.completed_at,
            failure_reason=entity.failure_reason,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
        )

    def _to_entity(self, model: WaitRequestModel) -> WaitRequest:
        """将数据模型转换为领域实体"""
        return WaitRequest(
            id=UUID(model.id),
            mailbox_id=UUID(model.mailbox_id),
            email=model.email,
            service_name=model.service_name,
            callback_url=model.callback_url,
            status=WaitRequestStatus(model.status),
            extraction_result=model.extraction_result,
            completed_at=model.completed_at,
            failure_reason=model.failure_reason,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )

    def _update_model(self, model: WaitRequestModel, entity: WaitRequest) -> None:
        """更新数据模型"""
        model.mailbox_id = str(entity.mailbox_id)
        model.email = entity.email
        model.service_name = entity.service_name
        model.callback_url = entity.callback_url
        model.status = entity.status.value
        model.extraction_result = entity.extraction_result
        model.completed_at = entity.completed_at
        model.failure_reason = entity.failure_reason
        model.updated_at = entity.updated_at
        model.version = entity.version
