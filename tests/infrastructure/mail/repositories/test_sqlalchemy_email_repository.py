"""SqlAlchemyEmailRepository 集成测试"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from infrastructure.mailbox.models.mailbox_account_model import Base
from infrastructure.mail.models.email_model import EmailModel
from infrastructure.mail.repositories.sqlalchemy_email_repository import (
    SqlAlchemyEmailRepository,
)
from domain.mail.entities.email import Email


@pytest.fixture
def db_session():
    """创建测试用的内存数据库 Session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def repository(db_session):
    """创建仓储实例"""
    return SqlAlchemyEmailRepository(db_session)


@pytest.fixture
def sample_email():
    """创建测试用邮件实体"""
    return Email.create(
        mailbox_id=uuid4(),
        message_id="<test123@example.com>",
        from_address="sender@example.com",
        subject="Test Email Subject",
        received_at=datetime.now(timezone.utc),
        body_text="This is the plain text body",
        body_html="<p>This is the HTML body</p>",
    )


class TestSqlAlchemyEmailRepositoryAdd:
    """add() 方法测试"""

    def test_add_email(self, repository, sample_email):
        """测试添加邮件"""
        repository.add(sample_email)

        # 验证能够通过 ID 获取
        retrieved = repository.get_by_id(sample_email.id)
        assert retrieved is not None
        assert retrieved.id == sample_email.id
        assert retrieved.message_id == sample_email.message_id
        assert retrieved.subject == sample_email.subject

    def test_add_email_persists_all_fields(self, repository, sample_email):
        """测试添加邮件时所有字段都被持久化"""
        repository.add(sample_email)

        retrieved = repository.get_by_id(sample_email.id)
        assert retrieved.mailbox_id == sample_email.mailbox_id
        assert retrieved.from_address == sample_email.from_address
        assert retrieved.body_text == sample_email.body_text
        assert retrieved.body_html == sample_email.body_html
        assert retrieved.is_processed == sample_email.is_processed


class TestSqlAlchemyEmailRepositoryGetById:
    """get_by_id() 方法测试"""

    def test_get_by_id_exists(self, repository, sample_email):
        """测试获取存在的邮件"""
        repository.add(sample_email)

        result = repository.get_by_id(sample_email.id)

        assert result is not None
        assert result.id == sample_email.id

    def test_get_by_id_not_exists(self, repository):
        """测试获取不存在的邮件"""
        result = repository.get_by_id(uuid4())

        assert result is None


class TestSqlAlchemyEmailRepositoryGetByMessageId:
    """get_by_message_id() 方法测试"""

    def test_get_by_message_id_exists(self, repository, sample_email):
        """测试根据 Message-ID 获取邮件"""
        repository.add(sample_email)

        result = repository.get_by_message_id(sample_email.message_id)

        assert result is not None
        assert result.message_id == sample_email.message_id

    def test_get_by_message_id_not_exists(self, repository):
        """测试获取不存在的 Message-ID"""
        result = repository.get_by_message_id("<nonexistent@example.com>")

        assert result is None


class TestSqlAlchemyEmailRepositoryExistsByMessageId:
    """exists_by_message_id() 方法测试"""

    def test_exists_by_message_id_true(self, repository, sample_email):
        """测试 Message-ID 存在"""
        repository.add(sample_email)

        result = repository.exists_by_message_id(sample_email.message_id)

        assert result is True

    def test_exists_by_message_id_false(self, repository):
        """测试 Message-ID 不存在"""
        result = repository.exists_by_message_id("<nonexistent@example.com>")

        assert result is False


class TestSqlAlchemyEmailRepositoryListByMailboxId:
    """list_by_mailbox_id() 方法测试"""

    def test_list_by_mailbox_id_returns_matching_emails(self, repository):
        """测试返回指定邮箱的邮件"""
        mailbox_id = uuid4()

        email1 = Email.create(
            mailbox_id=mailbox_id,
            message_id="<email1@example.com>",
            from_address="sender1@example.com",
            subject="Email 1",
            received_at=datetime.now(timezone.utc),
        )
        email2 = Email.create(
            mailbox_id=mailbox_id,
            message_id="<email2@example.com>",
            from_address="sender2@example.com",
            subject="Email 2",
            received_at=datetime.now(timezone.utc),
        )
        email3 = Email.create(
            mailbox_id=uuid4(),  # 不同的邮箱
            message_id="<email3@example.com>",
            from_address="sender3@example.com",
            subject="Email 3",
            received_at=datetime.now(timezone.utc),
        )

        repository.add(email1)
        repository.add(email2)
        repository.add(email3)

        result = repository.list_by_mailbox_id(mailbox_id)

        assert len(result) == 2
        message_ids = [e.message_id for e in result]
        assert "<email1@example.com>" in message_ids
        assert "<email2@example.com>" in message_ids

    def test_list_by_mailbox_id_empty(self, repository):
        """测试没有匹配邮件时返回空列表"""
        result = repository.list_by_mailbox_id(uuid4())

        assert result == []


class TestSqlAlchemyEmailRepositoryListUnprocessed:
    """list_unprocessed() 方法测试"""

    def test_list_unprocessed_returns_only_unprocessed(self, repository):
        """测试只返回未处理的邮件"""
        email1 = Email.create(
            mailbox_id=uuid4(),
            message_id="<unprocessed1@example.com>",
            from_address="sender@example.com",
            subject="Unprocessed 1",
            received_at=datetime.now(timezone.utc),
        )
        email2 = Email.create(
            mailbox_id=uuid4(),
            message_id="<processed@example.com>",
            from_address="sender@example.com",
            subject="Processed",
            received_at=datetime.now(timezone.utc),
        )
        email2.mark_as_processed()

        email3 = Email.create(
            mailbox_id=uuid4(),
            message_id="<unprocessed2@example.com>",
            from_address="sender@example.com",
            subject="Unprocessed 2",
            received_at=datetime.now(timezone.utc),
        )

        repository.add(email1)
        repository.add(email2)
        repository.add(email3)

        result = repository.list_unprocessed()

        assert len(result) == 2
        for email in result:
            assert email.is_processed is False

    def test_list_unprocessed_respects_limit(self, repository):
        """测试 limit 参数限制返回数量"""
        # 创建 5 封未处理邮件
        for i in range(5):
            email = Email.create(
                mailbox_id=uuid4(),
                message_id=f"<unprocessed{i}@example.com>",
                from_address="sender@example.com",
                subject=f"Unprocessed {i}",
                received_at=datetime.now(timezone.utc),
            )
            repository.add(email)

        # 请求只返回 3 封
        result = repository.list_unprocessed(limit=3)

        assert len(result) == 3


class TestSqlAlchemyEmailRepositoryUpdate:
    """update() 方法测试"""

    def test_update_email(self, repository, sample_email):
        """测试更新邮件"""
        repository.add(sample_email)

        # 修改邮件
        sample_email.mark_as_processed()

        repository.update(sample_email)

        # 验证更新
        retrieved = repository.get_by_id(sample_email.id)
        assert retrieved.is_processed is True


class TestSqlAlchemyEmailRepositoryRemove:
    """remove() 方法测试"""

    def test_remove_email(self, repository, sample_email):
        """测试删除邮件"""
        repository.add(sample_email)

        repository.remove(sample_email)

        # 验证删除
        result = repository.get_by_id(sample_email.id)
        assert result is None

    def test_remove_nonexistent_email(self, repository, sample_email):
        """测试删除不存在的邮件不抛出异常"""
        # 不应该抛出异常
        repository.remove(sample_email)
