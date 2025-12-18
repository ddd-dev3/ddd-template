"""邮箱使用状态追踪集成测试

测试完整的状态追踪流程：
- 添加邮箱 → 注册等待 → 验证占用 → 完成/取消 → 验证释放
- 筛选功能测试
- 数据库持久化测试
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4, UUID
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from infrastructure.mailbox.models.mailbox_account_model import (
    Base,
    MailboxAccountModel,
)
from infrastructure.mailbox.repositories.sqlalchemy_mailbox_account_repository import (
    SqlAlchemyMailboxAccountRepository,
)
from infrastructure.verification.repositories.sqlalchemy_wait_request_repository import (
    SqlAlchemyWaitRequestRepository,
)
from application.commands.verification.register_wait_request import (
    RegisterWaitRequestCommand,
    RegisterWaitRequestHandler,
)
from application.commands.verification.cancel_wait_request import (
    CancelWaitRequestCommand,
    CancelWaitRequestHandler,
)
from domain.mailbox.value_objects.mailbox_enums import MailboxStatus


# ============ Test Fixtures ============


@pytest.fixture
def engine():
    """创建 SQLite 内存数据库引擎"""
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
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
def mailbox_repo(session: Session) -> SqlAlchemyMailboxAccountRepository:
    """创建邮箱仓储实例"""
    return SqlAlchemyMailboxAccountRepository(session)


@pytest.fixture
def wait_request_repo(session: Session) -> SqlAlchemyWaitRequestRepository:
    """创建等待请求仓储实例"""
    return SqlAlchemyWaitRequestRepository(session)


@pytest.fixture
def register_handler(
    mailbox_repo: SqlAlchemyMailboxAccountRepository,
    wait_request_repo: SqlAlchemyWaitRequestRepository,
) -> RegisterWaitRequestHandler:
    """创建注册等待请求处理器"""
    return RegisterWaitRequestHandler(
        mailbox_repo=mailbox_repo,
        wait_request_repo=wait_request_repo,
    )


@pytest.fixture
def cancel_handler(
    wait_request_repo: SqlAlchemyWaitRequestRepository,
    mailbox_repo: SqlAlchemyMailboxAccountRepository,
) -> CancelWaitRequestHandler:
    """创建取消等待请求处理器"""
    return CancelWaitRequestHandler(
        wait_request_repo=wait_request_repo,
        mailbox_repo=mailbox_repo,
    )


def create_mailbox_model(
    session: Session,
    username: str,
    mailbox_type: str = "hotmail",
    status: str = "available",
    occupied_by_service: Optional[str] = None,
) -> MailboxAccountModel:
    """创建并保存测试用邮箱模型"""
    model = MailboxAccountModel(
        id=str(uuid4()),
        username=username,
        mailbox_type=mailbox_type,
        domain="example.com" if mailbox_type == "domain_catchall" else None,
        imap_server="imap.example.com",
        imap_port=993,
        use_ssl=True,
        encrypted_password=b"encrypted_password",
        status=status,
        occupied_by_service=occupied_by_service,
        created_at=datetime.now(timezone.utc),
    )
    session.add(model)
    session.commit()
    return model


# ============ 场景 1: 完整占用-释放流程 (AC1, AC2) ============


class TestCompleteStatusTrackingFlow:
    """测试完整的状态追踪流程"""

    def test_mailbox_occupy_and_release_via_cancel(
        self,
        session: Session,
        mailbox_repo: SqlAlchemyMailboxAccountRepository,
        register_handler: RegisterWaitRequestHandler,
        cancel_handler: CancelWaitRequestHandler,
    ):
        """测试完整流程：添加邮箱 → 注册等待 → 验证占用 → 取消 → 验证释放 (AC1, AC2)"""
        # 1. 添加邮箱 (status=available)
        model = create_mailbox_model(session, "test@example.com")
        mailbox_id = model.id

        # 验证初始状态
        mailbox = mailbox_repo.get_by_id(UUID(mailbox_id))
        assert mailbox is not None
        assert mailbox.status == MailboxStatus.AVAILABLE
        assert mailbox.occupied_by_service is None

        # 2. 注册等待请求 (status=occupied, service=claude)
        command = RegisterWaitRequestCommand(
            email="test@example.com",
            service_name="claude",
            callback_url="https://api.example.com/webhook",
        )
        result = register_handler.handle(command)

        assert result.success is True
        assert result.request_id is not None
        request_id = result.request_id

        # 3. 查询邮箱，验证占用状态 (AC1)
        # 重新加载邮箱
        mailbox = mailbox_repo.get_by_id(UUID(mailbox_id))
        assert mailbox.status == MailboxStatus.OCCUPIED
        assert mailbox.occupied_by_service == "claude"

        # 验证列表筛选
        items, total = mailbox_repo.list_filtered(status=MailboxStatus.OCCUPIED)
        assert total == 1
        assert items[0].username == "test@example.com"
        assert items[0].occupied_by_service == "claude"

        # 4. 取消请求 (status=available, service=None)
        cancel_command = CancelWaitRequestCommand(request_id=request_id)
        cancel_result = cancel_handler.handle(cancel_command)

        assert cancel_result.success is True

        # 5. 查询邮箱，验证释放状态 (AC2)
        mailbox = mailbox_repo.get_by_id(UUID(mailbox_id))
        assert mailbox.status == MailboxStatus.AVAILABLE
        assert mailbox.occupied_by_service is None

        # 验证列表筛选
        items, total = mailbox_repo.list_filtered(status=MailboxStatus.AVAILABLE)
        assert total == 1
        assert items[0].username == "test@example.com"
        assert items[0].occupied_by_service is None

    def test_multiple_mailboxes_different_statuses(
        self,
        session: Session,
        mailbox_repo: SqlAlchemyMailboxAccountRepository,
        register_handler: RegisterWaitRequestHandler,
    ):
        """测试多个邮箱的不同状态"""
        # 创建 3 个邮箱
        create_mailbox_model(session, "available1@example.com")
        create_mailbox_model(session, "available2@example.com")
        create_mailbox_model(session, "occupied@example.com")

        # 占用第三个邮箱
        command = RegisterWaitRequestCommand(
            email="occupied@example.com",
            service_name="openai",
            callback_url="https://api.example.com/webhook",
        )
        register_handler.handle(command)

        # 验证筛选结果
        available_items, available_total = mailbox_repo.list_filtered(
            status=MailboxStatus.AVAILABLE
        )
        assert available_total == 2
        assert all(m.status == MailboxStatus.AVAILABLE for m in available_items)

        occupied_items, occupied_total = mailbox_repo.list_filtered(
            status=MailboxStatus.OCCUPIED
        )
        assert occupied_total == 1
        assert occupied_items[0].username == "occupied@example.com"
        assert occupied_items[0].occupied_by_service == "openai"


# ============ 场景 2: 筛选功能测试 (AC1) ============


class TestFilterByStatusAndService:
    """测试状态和服务筛选功能"""

    def test_filter_by_service(
        self,
        session: Session,
        mailbox_repo: SqlAlchemyMailboxAccountRepository,
        register_handler: RegisterWaitRequestHandler,
    ):
        """测试按服务名筛选"""
        # 创建 3 个邮箱
        create_mailbox_model(session, "claude1@example.com")
        create_mailbox_model(session, "claude2@example.com")
        create_mailbox_model(session, "openai@example.com")

        # 注册等待请求
        register_handler.handle(RegisterWaitRequestCommand(
            email="claude1@example.com",
            service_name="claude",
            callback_url="https://api.example.com/webhook",
        ))
        register_handler.handle(RegisterWaitRequestCommand(
            email="claude2@example.com",
            service_name="claude",
            callback_url="https://api.example.com/webhook",
        ))
        register_handler.handle(RegisterWaitRequestCommand(
            email="openai@example.com",
            service_name="openai",
            callback_url="https://api.example.com/webhook",
        ))

        # 按服务筛选
        claude_items, claude_total = mailbox_repo.list_filtered(service="claude")
        assert claude_total == 2
        assert all(m.occupied_by_service == "claude" for m in claude_items)

        openai_items, openai_total = mailbox_repo.list_filtered(service="openai")
        assert openai_total == 1
        assert openai_items[0].occupied_by_service == "openai"

    def test_filter_by_status_and_service_combined(
        self,
        session: Session,
        mailbox_repo: SqlAlchemyMailboxAccountRepository,
        register_handler: RegisterWaitRequestHandler,
        cancel_handler: CancelWaitRequestHandler,
    ):
        """测试组合筛选：状态 + 服务"""
        # 创建 3 个邮箱
        create_mailbox_model(session, "user1@example.com")
        create_mailbox_model(session, "user2@example.com")
        create_mailbox_model(session, "user3@example.com")

        # 注册等待请求
        result1 = register_handler.handle(RegisterWaitRequestCommand(
            email="user1@example.com",
            service_name="claude",
            callback_url="https://api.example.com/webhook",
        ))
        register_handler.handle(RegisterWaitRequestCommand(
            email="user2@example.com",
            service_name="openai",
            callback_url="https://api.example.com/webhook",
        ))
        # user3 保持 available

        # 取消 user1 的请求，使其变为 available
        cancel_handler.handle(CancelWaitRequestCommand(request_id=result1.request_id))

        # 组合筛选测试
        # 1. status=occupied, service=openai
        items, total = mailbox_repo.list_filtered(
            status=MailboxStatus.OCCUPIED,
            service="openai",
        )
        assert total == 1
        assert items[0].username == "user2@example.com"

        # 2. status=available (user1 和 user3)
        items, total = mailbox_repo.list_filtered(status=MailboxStatus.AVAILABLE)
        assert total == 2

        # 3. service=claude (已释放，无结果)
        items, total = mailbox_repo.list_filtered(service="claude")
        assert total == 0


# ============ 场景 3: 持久化测试 (AC3) ============


class TestStatusPersistence:
    """测试状态持久化"""

    def test_status_persistence_after_reload(
        self,
        engine,
        session: Session,
    ):
        """测试状态持久化：创建记录 → 重新加载 → 验证状态 (AC3)"""
        # 1. 创建邮箱并占用
        model = create_mailbox_model(
            session,
            "persist-test@example.com",
            status="occupied",
            occupied_by_service="test-service",
        )
        mailbox_id = model.id

        # 验证初始状态
        assert model.status == "occupied"
        assert model.occupied_by_service == "test-service"

        # 2. 关闭当前会话
        session.close()

        # 3. 创建新会话（模拟系统重启）
        SessionLocal = sessionmaker(bind=engine)
        new_session = SessionLocal()

        try:
            # 4. 重新从数据库加载
            repo = SqlAlchemyMailboxAccountRepository(new_session)
            mailbox = repo.get_by_id(UUID(mailbox_id))

            # 5. 验证状态正确恢复
            assert mailbox is not None
            assert mailbox.status == MailboxStatus.OCCUPIED
            assert mailbox.occupied_by_service == "test-service"
        finally:
            new_session.close()

    def test_available_status_persistence(
        self,
        engine,
        session: Session,
    ):
        """测试 available 状态持久化"""
        # 创建 available 状态邮箱
        model = create_mailbox_model(
            session,
            "available-persist@example.com",
            status="available",
        )
        mailbox_id = model.id

        # 关闭会话
        session.close()

        # 创建新会话
        SessionLocal = sessionmaker(bind=engine)
        new_session = SessionLocal()

        try:
            repo = SqlAlchemyMailboxAccountRepository(new_session)
            mailbox = repo.get_by_id(UUID(mailbox_id))

            assert mailbox is not None
            assert mailbox.status == MailboxStatus.AVAILABLE
            assert mailbox.occupied_by_service is None
        finally:
            new_session.close()

    def test_status_change_persistence(
        self,
        engine,
        session: Session,
        mailbox_repo: SqlAlchemyMailboxAccountRepository,
        wait_request_repo: SqlAlchemyWaitRequestRepository,
    ):
        """测试状态变更后的持久化"""
        # 创建邮箱
        model = create_mailbox_model(session, "change-persist@example.com")
        mailbox_id = model.id

        # 创建处理器并注册等待请求
        register_handler = RegisterWaitRequestHandler(
            mailbox_repo=mailbox_repo,
            wait_request_repo=wait_request_repo,
        )
        result = register_handler.handle(RegisterWaitRequestCommand(
            email="change-persist@example.com",
            service_name="claude",
            callback_url="https://api.example.com/webhook",
        ))
        assert result.success is True

        # 关闭会话
        session.close()

        # 创建新会话验证状态持久化
        SessionLocal = sessionmaker(bind=engine)
        new_session = SessionLocal()

        try:
            repo = SqlAlchemyMailboxAccountRepository(new_session)
            mailbox = repo.get_by_id(UUID(mailbox_id))

            # 验证占用状态已持久化
            assert mailbox.status == MailboxStatus.OCCUPIED
            assert mailbox.occupied_by_service == "claude"
        finally:
            new_session.close()


# ============ 边界情况测试 ============


class TestEdgeCases:
    """边界情况测试"""

    def test_occupy_already_occupied_mailbox(
        self,
        session: Session,
        register_handler: RegisterWaitRequestHandler,
    ):
        """测试占用已被占用的邮箱"""
        create_mailbox_model(session, "occupied@example.com")

        # 第一次注册成功
        result1 = register_handler.handle(RegisterWaitRequestCommand(
            email="occupied@example.com",
            service_name="claude",
            callback_url="https://api.example.com/webhook",
        ))
        assert result1.success is True

        # 第二次注册失败（邮箱已被占用）
        result2 = register_handler.handle(RegisterWaitRequestCommand(
            email="occupied@example.com",
            service_name="openai",
            callback_url="https://api.example.com/webhook",
        ))
        assert result2.success is False
        assert result2.error_code == "MAILBOX_OCCUPIED"

    def test_cancel_and_reuse_mailbox(
        self,
        session: Session,
        mailbox_repo: SqlAlchemyMailboxAccountRepository,
        register_handler: RegisterWaitRequestHandler,
        cancel_handler: CancelWaitRequestHandler,
    ):
        """测试取消请求后重新使用邮箱"""
        create_mailbox_model(session, "reuse@example.com")

        # 第一次注册
        result1 = register_handler.handle(RegisterWaitRequestCommand(
            email="reuse@example.com",
            service_name="claude",
            callback_url="https://api.example.com/webhook",
        ))
        assert result1.success is True

        # 取消
        cancel_result = cancel_handler.handle(
            CancelWaitRequestCommand(request_id=result1.request_id)
        )
        assert cancel_result.success is True

        # 重新注册（应该成功，因为邮箱已释放）
        result2 = register_handler.handle(RegisterWaitRequestCommand(
            email="reuse@example.com",
            service_name="openai",
            callback_url="https://api.example.com/webhook2",
        ))
        assert result2.success is True

        # 验证邮箱被新服务占用
        mailbox = mailbox_repo.get_by_username("reuse@example.com")
        assert mailbox.status == MailboxStatus.OCCUPIED
        assert mailbox.occupied_by_service == "openai"

    def test_list_filtered_empty_database(
        self,
        mailbox_repo: SqlAlchemyMailboxAccountRepository,
    ):
        """测试空数据库筛选"""
        items, total = mailbox_repo.list_filtered(status=MailboxStatus.OCCUPIED)
        assert items == []
        assert total == 0

        items, total = mailbox_repo.list_filtered(service="claude")
        assert items == []
        assert total == 0
