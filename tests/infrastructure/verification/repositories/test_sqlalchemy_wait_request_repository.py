"""SqlAlchemyWaitRequestRepository 集成测试

使用 SQLite 内存数据库测试仓储的实际行为。
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.mailbox.models.mailbox_account_model import Base
from infrastructure.verification.models.wait_request_model import WaitRequestModel
from infrastructure.verification.repositories.sqlalchemy_wait_request_repository import (
    SqlAlchemyWaitRequestRepository,
)
from domain.verification.entities.wait_request import WaitRequest
from domain.verification.value_objects.wait_request_status import WaitRequestStatus


@pytest.fixture
def engine():
    """创建 SQLite 内存数据库引擎"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """创建数据库会话"""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def repository(session: Session) -> SqlAlchemyWaitRequestRepository:
    """创建仓储实例"""
    return SqlAlchemyWaitRequestRepository(session)


def create_wait_request_entity(
    mailbox_id: str = None,
    email: str = "test@example.com",
    service_name: str = "claude",
    callback_url: str = "https://example.com/callback",
) -> WaitRequest:
    """创建测试用等待请求实体"""
    return WaitRequest.create(
        mailbox_id=uuid4() if mailbox_id is None else mailbox_id,
        email=email,
        service_name=service_name,
        callback_url=callback_url,
    )


class TestAddIntegration:
    """add 方法集成测试"""

    def test_add_wait_request(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试添加等待请求"""
        wait_request = create_wait_request_entity()

        repository.add(wait_request)

        # 验证数据库中存在
        model = session.query(WaitRequestModel).filter(
            WaitRequestModel.id == str(wait_request.id)
        ).first()
        assert model is not None
        assert model.email == "test@example.com"
        assert model.service_name == "claude"
        assert model.status == "pending"

    def test_add_multiple_wait_requests(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试添加多个等待请求"""
        request1 = create_wait_request_entity(email="user1@example.com")
        request2 = create_wait_request_entity(email="user2@example.com")

        repository.add(request1)
        repository.add(request2)

        # 验证数据库中存在两条记录
        count = session.query(WaitRequestModel).count()
        assert count == 2


class TestGetByIdIntegration:
    """get_by_id 方法集成测试"""

    def test_get_by_id_found(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试按 ID 获取存在的等待请求"""
        wait_request = create_wait_request_entity()
        repository.add(wait_request)

        result = repository.get_by_id(wait_request.id)

        assert result is not None
        assert result.id == wait_request.id
        assert result.email == wait_request.email
        assert result.service_name == wait_request.service_name

    def test_get_by_id_not_found(
        self,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试按 ID 获取不存在的等待请求"""
        result = repository.get_by_id(uuid4())

        assert result is None


class TestGetPendingByMailboxIdIntegration:
    """get_pending_by_mailbox_id 方法集成测试"""

    def test_get_pending_by_mailbox_id_found(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试获取邮箱的待处理请求"""
        mailbox_id = uuid4()
        wait_request = create_wait_request_entity(mailbox_id=mailbox_id)
        repository.add(wait_request)

        result = repository.get_pending_by_mailbox_id(mailbox_id)

        assert result is not None
        assert result.mailbox_id == mailbox_id
        assert result.status == WaitRequestStatus.PENDING

    def test_get_pending_by_mailbox_id_completed_not_found(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试已完成的请求不会被返回"""
        mailbox_id = uuid4()
        wait_request = create_wait_request_entity(mailbox_id=mailbox_id)
        wait_request.complete("123456")
        repository.add(wait_request)

        result = repository.get_pending_by_mailbox_id(mailbox_id)

        assert result is None

    def test_get_pending_by_mailbox_id_not_found(
        self,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试邮箱没有待处理请求"""
        result = repository.get_pending_by_mailbox_id(uuid4())

        assert result is None


class TestGetPendingByEmailIntegration:
    """get_pending_by_email 方法集成测试"""

    def test_get_pending_by_email_found(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试按邮箱地址获取待处理请求"""
        email = "pending@example.com"
        wait_request = create_wait_request_entity(email=email)
        repository.add(wait_request)

        result = repository.get_pending_by_email(email)

        assert result is not None
        assert result.email == email
        assert result.status == WaitRequestStatus.PENDING

    def test_get_pending_by_email_cancelled_not_found(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试已取消的请求不会被返回"""
        email = "cancelled@example.com"
        wait_request = create_wait_request_entity(email=email)
        wait_request.cancel()
        repository.add(wait_request)

        result = repository.get_pending_by_email(email)

        assert result is None


class TestUpdateIntegration:
    """update 方法集成测试"""

    def test_update_status(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试更新等待请求状态"""
        wait_request = create_wait_request_entity()
        repository.add(wait_request)

        # 完成请求
        wait_request.complete("verification_code_123")
        repository.update(wait_request)

        # 验证更新
        result = repository.get_by_id(wait_request.id)
        assert result.status == WaitRequestStatus.COMPLETED
        assert result.extraction_result == "verification_code_123"
        assert result.completed_at is not None

    def test_update_failure_reason(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试更新失败原因"""
        wait_request = create_wait_request_entity()
        repository.add(wait_request)

        # 标记失败
        failure_reason = "Callback timeout"
        wait_request.fail(reason=failure_reason)
        repository.update(wait_request)

        # 验证更新
        result = repository.get_by_id(wait_request.id)
        assert result.status == WaitRequestStatus.FAILED
        assert result.failure_reason == failure_reason


class TestListByStatusIntegration:
    """list_by_status 方法集成测试"""

    def test_list_by_status_pending(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试列出 PENDING 状态的请求"""
        # 创建不同状态的请求
        pending1 = create_wait_request_entity(email="pending1@example.com")
        pending2 = create_wait_request_entity(email="pending2@example.com")
        completed = create_wait_request_entity(email="completed@example.com")
        completed.complete("code")

        repository.add(pending1)
        repository.add(pending2)
        repository.add(completed)

        result = repository.list_by_status(WaitRequestStatus.PENDING)

        assert len(result) == 2
        assert all(r.status == WaitRequestStatus.PENDING for r in result)

    def test_list_by_status_with_pagination(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试列出请求时的分页"""
        # 创建 5 个 PENDING 请求
        for i in range(5):
            wait_request = create_wait_request_entity(email=f"user{i}@example.com")
            repository.add(wait_request)

        # 获取前 2 个
        result = repository.list_by_status(WaitRequestStatus.PENDING, limit=2, offset=0)
        assert len(result) == 2

        # 获取后 3 个
        result = repository.list_by_status(WaitRequestStatus.PENDING, limit=10, offset=2)
        assert len(result) == 3


class TestDeleteIntegration:
    """delete 方法集成测试"""

    def test_delete_existing(
        self,
        session: Session,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试删除存在的等待请求"""
        wait_request = create_wait_request_entity()
        repository.add(wait_request)

        result = repository.delete(wait_request.id)

        assert result is True
        assert repository.get_by_id(wait_request.id) is None

    def test_delete_not_existing(
        self,
        repository: SqlAlchemyWaitRequestRepository,
    ):
        """测试删除不存在的等待请求"""
        result = repository.delete(uuid4())

        assert result is False
