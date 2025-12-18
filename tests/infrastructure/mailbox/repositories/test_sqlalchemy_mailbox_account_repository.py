"""SqlAlchemyMailboxAccountRepository 集成测试

使用 SQLite 内存数据库测试仓储的实际行为。
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from infrastructure.mailbox.models.mailbox_account_model import Base, MailboxAccountModel
from infrastructure.mailbox.repositories.sqlalchemy_mailbox_account_repository import (
    SqlAlchemyMailboxAccountRepository,
)
from domain.mailbox.value_objects.mailbox_enums import MailboxStatus


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
def repository(session: Session) -> SqlAlchemyMailboxAccountRepository:
    """创建仓储实例"""
    return SqlAlchemyMailboxAccountRepository(session)


def create_mailbox_model(
    session: Session,
    username: str,
    mailbox_type: str = "hotmail",
    status: str = "available",
    occupied_by_service: str = None,
    created_at: datetime = None,
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
        created_at=created_at or datetime.now(timezone.utc),
    )
    session.add(model)
    session.commit()
    return model


class TestListFilteredIntegration:
    """list_filtered 方法集成测试"""

    def test_list_filtered_empty_database(
        self,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试空数据库返回空列表"""
        items, total = repository.list_filtered()

        assert items == []
        assert total == 0

    def test_list_filtered_returns_all_items(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试返回所有项"""
        create_mailbox_model(session, "user1@example.com")
        create_mailbox_model(session, "user2@example.com")
        create_mailbox_model(session, "user3@example.com")

        items, total = repository.list_filtered()

        assert len(items) == 3
        assert total == 3

    def test_list_filtered_by_service(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试按服务筛选"""
        create_mailbox_model(
            session, "user1@example.com",
            status="occupied", occupied_by_service="service_a"
        )
        create_mailbox_model(
            session, "user2@example.com",
            status="occupied", occupied_by_service="service_b"
        )
        create_mailbox_model(
            session, "user3@example.com",
            status="occupied", occupied_by_service="service_a"
        )

        items, total = repository.list_filtered(service="service_a")

        assert len(items) == 2
        assert total == 2
        assert all(m.occupied_by_service == "service_a" for m in items)

    def test_list_filtered_by_status_available(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试按 available 状态筛选"""
        create_mailbox_model(session, "user1@example.com", status="available")
        create_mailbox_model(session, "user2@example.com", status="occupied")
        create_mailbox_model(session, "user3@example.com", status="available")

        items, total = repository.list_filtered(status=MailboxStatus.AVAILABLE)

        assert len(items) == 2
        assert total == 2
        assert all(m.status == MailboxStatus.AVAILABLE for m in items)

    def test_list_filtered_by_status_occupied(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试按 occupied 状态筛选"""
        create_mailbox_model(session, "user1@example.com", status="available")
        create_mailbox_model(session, "user2@example.com", status="occupied")
        create_mailbox_model(session, "user3@example.com", status="occupied")

        items, total = repository.list_filtered(status=MailboxStatus.OCCUPIED)

        assert len(items) == 2
        assert total == 2
        assert all(m.status == MailboxStatus.OCCUPIED for m in items)

    def test_list_filtered_by_service_and_status(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试同时按服务和状态筛选"""
        create_mailbox_model(
            session, "user1@example.com",
            status="occupied", occupied_by_service="service_a"
        )
        create_mailbox_model(
            session, "user2@example.com",
            status="available"
        )
        create_mailbox_model(
            session, "user3@example.com",
            status="occupied", occupied_by_service="service_b"
        )

        items, total = repository.list_filtered(
            service="service_a",
            status=MailboxStatus.OCCUPIED,
        )

        assert len(items) == 1
        assert total == 1
        assert items[0].occupied_by_service == "service_a"

    def test_list_filtered_pagination(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试分页"""
        # 创建 5 个邮箱
        for i in range(5):
            create_mailbox_model(session, f"user{i}@example.com")

        # 第一页，每页 2 条
        items, total = repository.list_filtered(page=1, limit=2)
        assert len(items) == 2
        assert total == 5

        # 第二页
        items, total = repository.list_filtered(page=2, limit=2)
        assert len(items) == 2
        assert total == 5

        # 第三页（只有 1 条）
        items, total = repository.list_filtered(page=3, limit=2)
        assert len(items) == 1
        assert total == 5

    def test_list_filtered_ordering_by_created_at_desc(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试按创建时间降序排序"""
        # 创建 3 个邮箱，时间依次递增
        create_mailbox_model(
            session, "oldest@example.com",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        create_mailbox_model(
            session, "middle@example.com",
            created_at=datetime(2024, 6, 1, tzinfo=timezone.utc)
        )
        create_mailbox_model(
            session, "newest@example.com",
            created_at=datetime(2024, 12, 1, tzinfo=timezone.utc)
        )

        items, total = repository.list_filtered()

        # 应该按创建时间降序排列
        assert items[0].username == "newest@example.com"
        assert items[1].username == "middle@example.com"
        assert items[2].username == "oldest@example.com"

    def test_list_filtered_service_not_found(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试筛选不存在的服务"""
        create_mailbox_model(session, "user1@example.com")

        items, total = repository.list_filtered(service="nonexistent_service")

        assert items == []
        assert total == 0

    def test_list_filtered_with_combined_filters_and_pagination(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试组合筛选和分页"""
        # 创建 10 个由 service_a 占用的邮箱
        for i in range(10):
            create_mailbox_model(
                session, f"service_a_user{i}@example.com",
                status="occupied", occupied_by_service="service_a"
            )
        # 创建 5 个由 service_b 占用的邮箱
        for i in range(5):
            create_mailbox_model(
                session, f"service_b_user{i}@example.com",
                status="occupied", occupied_by_service="service_b"
            )

        # 筛选 service_a，第 2 页，每页 3 条
        items, total = repository.list_filtered(
            service="service_a",
            page=2,
            limit=3,
        )

        assert len(items) == 3
        assert total == 10  # service_a 总共 10 个
        assert all(m.occupied_by_service == "service_a" for m in items)


class TestRemoveIntegration:
    """remove 方法集成测试"""

    def test_remove_existing_mailbox(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试删除已存在的邮箱"""
        model = create_mailbox_model(session, "delete-me@example.com")
        mailbox_id = model.id

        # 使用 get_by_id 获取实体
        from uuid import UUID
        mailbox = repository.get_by_id(UUID(mailbox_id))
        assert mailbox is not None

        # 删除
        repository.remove(mailbox)

        # 验证已删除
        result = repository.get_by_id(UUID(mailbox_id))
        assert result is None

    def test_remove_does_not_affect_other_mailboxes(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试删除不影响其他邮箱"""
        model1 = create_mailbox_model(session, "keep@example.com")
        model2 = create_mailbox_model(session, "delete@example.com")
        model3 = create_mailbox_model(session, "also-keep@example.com")

        from uuid import UUID

        # 删除 model2
        mailbox = repository.get_by_id(UUID(model2.id))
        repository.remove(mailbox)

        # 验证其他邮箱仍存在
        assert repository.get_by_id(UUID(model1.id)) is not None
        assert repository.get_by_id(UUID(model3.id)) is not None

        # 验证 model2 已删除
        assert repository.get_by_id(UUID(model2.id)) is None

    def test_remove_updates_list_count(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试删除后列表数量更新"""
        create_mailbox_model(session, "user1@example.com")
        model2 = create_mailbox_model(session, "user2@example.com")
        create_mailbox_model(session, "user3@example.com")

        from uuid import UUID

        # 初始数量
        items, total = repository.list_filtered()
        assert total == 3

        # 删除一个
        mailbox = repository.get_by_id(UUID(model2.id))
        repository.remove(mailbox)

        # 验证数量减少
        items, total = repository.list_filtered()
        assert total == 2
        assert len(items) == 2

    def test_remove_available_mailbox(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试删除 available 状态的邮箱"""
        model = create_mailbox_model(
            session, "available@example.com", status="available"
        )

        from uuid import UUID

        mailbox = repository.get_by_id(UUID(model.id))
        assert mailbox.status == MailboxStatus.AVAILABLE

        # 删除
        repository.remove(mailbox)

        # 验证已删除
        assert repository.get_by_id(UUID(model.id)) is None

    def test_remove_and_verify_database_persistence(
        self,
        session: Session,
        repository: SqlAlchemyMailboxAccountRepository,
    ):
        """测试删除后数据库持久化"""
        model = create_mailbox_model(session, "persist-test@example.com")
        mailbox_id = model.id

        from uuid import UUID

        # 删除
        mailbox = repository.get_by_id(UUID(mailbox_id))
        repository.remove(mailbox)

        # 直接查询数据库验证
        db_result = session.query(MailboxAccountModel).filter(
            MailboxAccountModel.id == mailbox_id
        ).first()
        assert db_result is None
