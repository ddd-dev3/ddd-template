"""AsyncMailPollingService 单元测试 - 包含并行轮询测试"""

import pytest
import asyncio
import threading
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from uuid import uuid4

from application.mail.services.async_mail_polling_service import AsyncMailPollingService
from application.mail.services.mail_polling_service import MailPollingService
from domain.mail.value_objects.parsed_email import ParsedEmail
from domain.mail.value_objects.email_content import EmailContent
from domain.mail.entities.email import Email


@pytest.fixture
def mock_mailbox_repository():
    """创建模拟邮箱仓储"""
    return Mock()


@pytest.fixture
def mock_imap_service():
    """创建模拟 IMAP 服务"""
    return Mock()


@pytest.fixture
def mock_email_repository():
    """创建模拟邮件仓储"""
    return Mock()


@pytest.fixture
def polling_service(mock_mailbox_repository, mock_imap_service, mock_email_repository):
    """创建轮询服务实例（使用短间隔便于测试）"""
    # 使用 lambda 工厂函数返回 mock，以便测试能正确追踪调用
    return AsyncMailPollingService(
        mailbox_repository=mock_mailbox_repository,
        imap_service=mock_imap_service,
        email_repository=lambda: mock_email_repository,  # 工厂函数
        interval=0.1,  # 测试用短间隔
        max_concurrent_connections=10,
        mailbox_poll_timeout=5.0,
    )


@pytest.fixture
def sample_mailbox():
    """创建测试用邮箱账号"""
    mailbox = Mock()
    mailbox.id = uuid4()
    mailbox.username = "test@example.com"
    return mailbox


@pytest.fixture
def sample_parsed_email():
    """创建测试用解析后的邮件"""
    return ParsedEmail(
        message_id="<test123@example.com>",
        from_address="sender@example.com",
        subject="Test Subject",
        content=EmailContent(text="Test body", html="<p>Test body</p>"),
        received_at=datetime.now(timezone.utc),
    )


class TestAsyncMailPollingServiceLifecycle:
    """生命周期测试"""

    @pytest.mark.asyncio
    async def test_start_sets_running_flag(self, polling_service, mock_mailbox_repository):
        """测试 start 设置运行标志"""
        mock_mailbox_repository.list_all.return_value = []

        assert not polling_service.is_running

        await polling_service.start()

        assert polling_service.is_running

        await polling_service.stop()

    @pytest.mark.asyncio
    async def test_stop_clears_running_flag(self, polling_service, mock_mailbox_repository):
        """测试 stop 清除运行标志"""
        mock_mailbox_repository.list_all.return_value = []

        await polling_service.start()
        await polling_service.stop()

        assert not polling_service.is_running

    @pytest.mark.asyncio
    async def test_start_when_already_running_does_nothing(
        self, polling_service, mock_mailbox_repository
    ):
        """测试重复启动不会创建多个任务"""
        mock_mailbox_repository.list_all.return_value = []

        await polling_service.start()
        task1 = polling_service._task

        await polling_service.start()  # 第二次启动
        task2 = polling_service._task

        assert task1 is task2  # 应该是同一个任务

        await polling_service.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_running_does_nothing(self, polling_service):
        """测试未运行时停止不会出错"""
        assert not polling_service.is_running

        await polling_service.stop()  # 应该不会报错

        assert not polling_service.is_running

    def test_interval_property(self, polling_service):
        """测试 interval 属性返回正确值"""
        assert polling_service.interval == 0.1

    def test_default_interval(self, mock_mailbox_repository, mock_imap_service, mock_email_repository):
        """测试默认轮询间隔"""
        service = AsyncMailPollingService(
            mailbox_repository=mock_mailbox_repository,
            imap_service=mock_imap_service,
            email_repository=mock_email_repository,
        )
        assert service.interval == MailPollingService.DEFAULT_INTERVAL

    def test_max_concurrent_connections_property(self, polling_service):
        """测试 max_concurrent_connections 属性"""
        assert polling_service.max_concurrent_connections == 10

    def test_mailbox_poll_timeout_property(self, polling_service):
        """测试 mailbox_poll_timeout 属性"""
        assert polling_service.mailbox_poll_timeout == 5.0

    def test_default_max_concurrent(self, mock_mailbox_repository, mock_imap_service, mock_email_repository):
        """测试默认最大并发数"""
        service = AsyncMailPollingService(
            mailbox_repository=mock_mailbox_repository,
            imap_service=mock_imap_service,
            email_repository=mock_email_repository,
        )
        assert service.max_concurrent_connections == MailPollingService.DEFAULT_MAX_CONCURRENT

    def test_default_timeout(self, mock_mailbox_repository, mock_imap_service, mock_email_repository):
        """测试默认超时"""
        service = AsyncMailPollingService(
            mailbox_repository=mock_mailbox_repository,
            imap_service=mock_imap_service,
            email_repository=mock_email_repository,
        )
        assert service.mailbox_poll_timeout == MailPollingService.DEFAULT_TIMEOUT


class TestAsyncMailPollingServicePolling:
    """轮询功能测试"""

    @pytest.mark.asyncio
    async def test_polls_immediately_on_start(
        self, polling_service, mock_mailbox_repository
    ):
        """测试启动后立即轮询"""
        mock_mailbox_repository.list_all.return_value = []

        await polling_service.start()
        await asyncio.sleep(0.05)  # 等待第一次轮询
        await polling_service.stop()

        mock_mailbox_repository.list_all.assert_called()

    @pytest.mark.asyncio
    async def test_polls_at_configured_interval(
        self, polling_service, mock_mailbox_repository
    ):
        """测试按配置间隔轮询"""
        mock_mailbox_repository.list_all.return_value = []

        await polling_service.start()

        # 等待至少两个轮询周期
        await asyncio.sleep(0.25)

        await polling_service.stop()

        # 应该至少调用了 2 次（启动时立即一次 + 至少一个周期）
        assert mock_mailbox_repository.list_all.call_count >= 2

    @pytest.mark.asyncio
    async def test_fetches_emails_for_each_mailbox(
        self,
        polling_service,
        mock_mailbox_repository,
        mock_imap_service,
        mock_email_repository,
        sample_mailbox,
    ):
        """测试为每个邮箱收取邮件"""
        mailbox1 = Mock(id=uuid4(), username="mail1@example.com")
        mailbox2 = Mock(id=uuid4(), username="mail2@example.com")

        mock_mailbox_repository.list_all.return_value = [mailbox1, mailbox2]
        mock_imap_service.fetch_new_emails.return_value = []

        await polling_service.start()
        await asyncio.sleep(0.05)
        await polling_service.stop()

        # 应该为每个邮箱调用 fetch_new_emails
        assert mock_imap_service.fetch_new_emails.call_count == 2


class TestAsyncMailPollingServiceParallelPolling:
    """并行轮询测试"""

    @pytest.mark.asyncio
    async def test_multiple_mailboxes_polled_in_parallel(
        self, mock_mailbox_repository, mock_imap_service, mock_email_repository
    ):
        """测试多邮箱并行执行"""
        polling_service = AsyncMailPollingService(
            mailbox_repository=mock_mailbox_repository,
            imap_service=mock_imap_service,
            email_repository=mock_email_repository,
            interval=1.0,
            max_concurrent_connections=10,
            mailbox_poll_timeout=5.0,
        )

        mailboxes = [
            Mock(id=uuid4(), username=f"mail{i}@example.com")
            for i in range(5)
        ]
        mock_mailbox_repository.list_all.return_value = mailboxes

        # 使用 threading.Lock 追踪并发数（run_in_executor 在线程中运行）
        lock = threading.Lock()
        concurrent_count = 0
        max_concurrent_seen = 0
        call_order = []

        def track_concurrent(mailbox):
            nonlocal concurrent_count, max_concurrent_seen
            with lock:
                concurrent_count += 1
                max_concurrent_seen = max(max_concurrent_seen, concurrent_count)
                call_order.append(('start', mailbox.username))

            time.sleep(0.1)  # 模拟耗时操作

            with lock:
                call_order.append(('end', mailbox.username))
                concurrent_count -= 1

            return []

        mock_imap_service.fetch_new_emails.side_effect = track_concurrent

        await polling_service.start()
        await asyncio.sleep(0.3)  # 等待轮询完成
        await polling_service.stop()

        # 验证所有邮箱都被轮询
        assert mock_imap_service.fetch_new_emails.call_count == 5

        # 验证并行执行（多个 start 在任何 end 之前）
        # 如果是并行，应该有多个任务同时启动
        assert max_concurrent_seen > 1, f"Should have concurrent execution, but max was {max_concurrent_seen}"

    @pytest.mark.asyncio
    async def test_fast_mailbox_completes_before_slow_mailbox(
        self, mock_mailbox_repository, mock_imap_service, mock_email_repository
    ):
        """测试快速邮箱不等待慢速邮箱"""
        polling_service = AsyncMailPollingService(
            mailbox_repository=mock_mailbox_repository,
            imap_service=mock_imap_service,
            email_repository=mock_email_repository,
            interval=1.0,
            max_concurrent_connections=10,
            mailbox_poll_timeout=5.0,
        )

        fast_mailbox = Mock(id=uuid4(), username="fast@example.com")
        slow_mailbox = Mock(id=uuid4(), username="slow@example.com")

        mock_mailbox_repository.list_all.return_value = [slow_mailbox, fast_mailbox]

        completion_order = []

        def fetch_with_delay(mailbox):
            if mailbox.username == "slow@example.com":
                time.sleep(0.3)  # 慢邮箱
                completion_order.append("slow")
            else:
                time.sleep(0.05)  # 快邮箱
                completion_order.append("fast")
            return []

        mock_imap_service.fetch_new_emails.side_effect = fetch_with_delay
        mock_email_repository.exists_by_message_id.return_value = False

        await polling_service.start()
        await asyncio.sleep(0.5)
        await polling_service.stop()

        # 快邮箱应该先完成
        assert completion_order[0] == "fast", f"Fast mailbox should complete first, but order was {completion_order}"


class TestAsyncMailPollingServiceConcurrencyLimit:
    """并发限制测试"""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_connections(
        self, mock_mailbox_repository, mock_imap_service, mock_email_repository
    ):
        """测试信号量限制并发连接数"""
        # 创建并发限制为 2 的服务
        polling_service = AsyncMailPollingService(
            mailbox_repository=mock_mailbox_repository,
            imap_service=mock_imap_service,
            email_repository=mock_email_repository,
            interval=1.0,
            max_concurrent_connections=2,  # 只允许 2 个并发
            mailbox_poll_timeout=5.0,
        )

        mailboxes = [
            Mock(id=uuid4(), username=f"mail{i}@example.com")
            for i in range(5)
        ]
        mock_mailbox_repository.list_all.return_value = mailboxes

        # 使用 threading.Lock 追踪并发数
        lock = threading.Lock()
        concurrent_count = 0
        max_concurrent_seen = 0

        def track_concurrent(mailbox):
            nonlocal concurrent_count, max_concurrent_seen

            with lock:
                concurrent_count += 1
                max_concurrent_seen = max(max_concurrent_seen, concurrent_count)

            time.sleep(0.1)  # 模拟工作

            with lock:
                concurrent_count -= 1

            return []

        mock_imap_service.fetch_new_emails.side_effect = track_concurrent

        await polling_service.start()
        await asyncio.sleep(0.6)  # 等待所有邮箱轮询完成
        await polling_service.stop()

        # 最大并发数不应超过限制
        assert max_concurrent_seen <= 2, f"Max concurrent should be <= 2, but was {max_concurrent_seen}"
        # 所有邮箱都应该被轮询
        assert mock_imap_service.fetch_new_emails.call_count == 5


class TestAsyncMailPollingServiceTimeout:
    """超时处理测试"""

    @pytest.mark.asyncio
    async def test_timeout_cancels_slow_mailbox(
        self, mock_mailbox_repository, mock_imap_service, mock_email_repository
    ):
        """测试超时取消慢速邮箱"""
        polling_service = AsyncMailPollingService(
            mailbox_repository=mock_mailbox_repository,
            imap_service=mock_imap_service,
            email_repository=mock_email_repository,
            interval=1.0,
            max_concurrent_connections=10,
            mailbox_poll_timeout=0.1,  # 100ms 超时
        )

        slow_mailbox = Mock(id=uuid4(), username="slow@example.com")
        mock_mailbox_repository.list_all.return_value = [slow_mailbox]

        def very_slow_fetch(mailbox):
            time.sleep(1.0)  # 1 秒，超过超时限制
            return []

        mock_imap_service.fetch_new_emails.side_effect = very_slow_fetch

        await polling_service.start()
        await asyncio.sleep(0.3)  # 等待超时处理
        await polling_service.stop()

        # 应该调用了 fetch，但因超时被中断
        mock_imap_service.fetch_new_emails.assert_called()

    @pytest.mark.asyncio
    async def test_timeout_does_not_affect_other_mailboxes(
        self, mock_mailbox_repository, mock_imap_service, mock_email_repository
    ):
        """测试超时不影响其他邮箱"""
        polling_service = AsyncMailPollingService(
            mailbox_repository=mock_mailbox_repository,
            imap_service=mock_imap_service,
            email_repository=mock_email_repository,
            interval=1.0,
            max_concurrent_connections=10,
            mailbox_poll_timeout=0.1,  # 100ms 超时
        )

        slow_mailbox = Mock(id=uuid4(), username="slow@example.com")
        fast_mailbox = Mock(id=uuid4(), username="fast@example.com")
        mock_mailbox_repository.list_all.return_value = [slow_mailbox, fast_mailbox]

        fast_completed = []

        def fetch_with_timeout(mailbox):
            if mailbox.username == "slow@example.com":
                time.sleep(1.0)  # 超时
            else:
                fast_completed.append(mailbox.username)
            return []

        mock_imap_service.fetch_new_emails.side_effect = fetch_with_timeout

        await polling_service.start()
        await asyncio.sleep(0.3)
        await polling_service.stop()

        # 快邮箱应该成功完成
        assert "fast@example.com" in fast_completed


class TestAsyncMailPollingServiceDynamicDiscovery:
    """动态邮箱发现测试"""

    @pytest.mark.asyncio
    async def test_new_mailbox_discovered_on_next_cycle(
        self, mock_mailbox_repository, mock_imap_service, mock_email_repository
    ):
        """测试新邮箱在下一周期自动发现"""
        polling_service = AsyncMailPollingService(
            mailbox_repository=mock_mailbox_repository,
            imap_service=mock_imap_service,
            email_repository=mock_email_repository,
            interval=0.1,  # 短间隔便于测试
            max_concurrent_connections=10,
            mailbox_poll_timeout=5.0,
        )

        mailbox1 = Mock(id=uuid4(), username="mail1@example.com")
        mailbox2 = Mock(id=uuid4(), username="mail2@example.com")

        # 第一次轮询只有 1 个邮箱
        # 第二次轮询有 2 个邮箱
        mock_mailbox_repository.list_all.side_effect = [
            [mailbox1],
            [mailbox1, mailbox2],
            [mailbox1, mailbox2],  # 额外返回以防多次调用
        ]
        mock_imap_service.fetch_new_emails.return_value = []

        await polling_service.start()
        await asyncio.sleep(0.25)  # 等待两个轮询周期
        await polling_service.stop()

        # 两个邮箱都应该被轮询
        call_args = [
            call[0][0].username
            for call in mock_imap_service.fetch_new_emails.call_args_list
        ]
        assert "mail1@example.com" in call_args
        assert "mail2@example.com" in call_args


class TestAsyncMailPollingServiceErrorIsolation:
    """错误隔离测试"""

    @pytest.mark.asyncio
    async def test_single_mailbox_failure_does_not_affect_others(
        self,
        polling_service,
        mock_mailbox_repository,
        mock_imap_service,
        mock_email_repository,
    ):
        """测试单邮箱失败不影响其他邮箱"""
        mailbox1 = Mock(id=uuid4(), username="mail1@example.com")
        mailbox2 = Mock(id=uuid4(), username="mail2@example.com")

        mock_mailbox_repository.list_all.return_value = [mailbox1, mailbox2]

        # 第一个邮箱失败，第二个成功
        mock_imap_service.fetch_new_emails.side_effect = [
            Exception("Connection timeout"),
            []  # 成功返回空列表
        ]

        await polling_service.start()
        await asyncio.sleep(0.05)
        await polling_service.stop()

        # 两个邮箱都应该被尝试
        assert mock_imap_service.fetch_new_emails.call_count == 2

    @pytest.mark.asyncio
    async def test_mailbox_list_failure_does_not_crash_service(
        self,
        polling_service,
        mock_mailbox_repository,
    ):
        """测试获取邮箱列表失败不会崩溃服务"""
        mock_mailbox_repository.list_all.side_effect = Exception("Database error")

        await polling_service.start()
        await asyncio.sleep(0.05)

        # 服务应该仍在运行
        assert polling_service.is_running

        await polling_service.stop()


class TestAsyncMailPollingServiceDeduplication:
    """邮件去重测试"""

    @pytest.mark.asyncio
    async def test_skips_existing_email_by_message_id(
        self,
        polling_service,
        mock_mailbox_repository,
        mock_imap_service,
        mock_email_repository,
        sample_mailbox,
        sample_parsed_email,
    ):
        """测试跳过已存在的邮件（通过 Message-ID）"""
        mock_mailbox_repository.list_all.return_value = [sample_mailbox]
        mock_imap_service.fetch_new_emails.return_value = [sample_parsed_email]

        # 邮件已存在
        mock_email_repository.exists_by_message_id.return_value = True

        await polling_service.start()
        await asyncio.sleep(0.05)
        await polling_service.stop()

        # 应该检查去重
        mock_email_repository.exists_by_message_id.assert_called_with(
            sample_parsed_email.message_id
        )

        # 不应该添加邮件
        mock_email_repository.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_saves_new_email(
        self,
        polling_service,
        mock_mailbox_repository,
        mock_imap_service,
        mock_email_repository,
        sample_mailbox,
        sample_parsed_email,
    ):
        """测试保存新邮件"""
        mock_mailbox_repository.list_all.return_value = [sample_mailbox]
        mock_imap_service.fetch_new_emails.return_value = [sample_parsed_email]

        # 邮件不存在
        mock_email_repository.exists_by_message_id.return_value = False

        await polling_service.start()
        await asyncio.sleep(0.05)
        await polling_service.stop()

        # 应该添加邮件
        mock_email_repository.add.assert_called_once()

        # 验证保存的邮件
        saved_email = mock_email_repository.add.call_args[0][0]
        assert isinstance(saved_email, Email)
        assert saved_email.mailbox_id == sample_mailbox.id
        assert saved_email.message_id == sample_parsed_email.message_id
        assert saved_email.from_address == sample_parsed_email.from_address
        assert saved_email.subject == sample_parsed_email.subject


class TestAsyncMailPollingServiceConversion:
    """ParsedEmail 到 Email 转换测试"""

    def test_convert_to_email(
        self,
        polling_service,
        sample_mailbox,
        sample_parsed_email,
    ):
        """测试 ParsedEmail 正确转换为 Email 实体"""
        email = polling_service._convert_to_email(sample_mailbox, sample_parsed_email)

        assert isinstance(email, Email)
        assert email.mailbox_id == sample_mailbox.id
        assert email.message_id == sample_parsed_email.message_id
        assert email.from_address == sample_parsed_email.from_address
        assert email.subject == sample_parsed_email.subject
        assert email.body_text == sample_parsed_email.content.text
        assert email.body_html == sample_parsed_email.content.html
        assert email.received_at == sample_parsed_email.received_at
        assert email.is_processed is False

    def test_convert_to_email_with_none_received_at(
        self,
        polling_service,
        sample_mailbox,
    ):
        """测试转换时 received_at 为 None 使用当前时间"""
        parsed_email = ParsedEmail(
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Test",
            content=EmailContent(text="body", html=None),
            received_at=None,
        )

        email = polling_service._convert_to_email(sample_mailbox, parsed_email)

        assert email.received_at is not None


class TestAsyncMailPollingServiceGracefulShutdown:
    """优雅停止测试"""

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, polling_service, mock_mailbox_repository):
        """测试停止会取消任务"""
        mock_mailbox_repository.list_all.return_value = []

        await polling_service.start()
        task = polling_service._task

        await polling_service.stop()

        assert task.cancelled() or task.done()
        assert polling_service._task is None

    @pytest.mark.asyncio
    async def test_stop_during_sleep_works(self, polling_service, mock_mailbox_repository):
        """测试在 sleep 期间停止能正常工作"""
        mock_mailbox_repository.list_all.return_value = []

        await polling_service.start()
        await asyncio.sleep(0.05)  # 让服务进入 sleep 状态

        # 应该能正常停止
        await polling_service.stop()

        assert not polling_service.is_running

    @pytest.mark.asyncio
    async def test_stop_cleans_up_resources(
        self, mock_mailbox_repository, mock_imap_service, mock_email_repository
    ):
        """测试停止会清理资源"""
        polling_service = AsyncMailPollingService(
            mailbox_repository=mock_mailbox_repository,
            imap_service=mock_imap_service,
            email_repository=mock_email_repository,
            interval=0.1,
            max_concurrent_connections=5,
            mailbox_poll_timeout=5.0,
        )

        mock_mailbox_repository.list_all.return_value = []

        await polling_service.start()

        # 验证资源已创建
        assert polling_service._semaphore is not None
        assert polling_service._executor is not None

        await polling_service.stop()

        # 验证资源已清理
        assert polling_service._semaphore is None
        assert polling_service._executor is None
        assert polling_service._task is None
