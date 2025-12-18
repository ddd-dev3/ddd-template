"""异步邮件轮询服务实现 - 支持并行轮询"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Optional, List, Callable

from application.mail.services.mail_polling_service import MailPollingService
from domain.mailbox.repositories.mailbox_account_repository import MailboxAccountRepository
from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mail.services.imap_mail_fetch_service import ImapMailFetchService
from domain.mail.repositories.email_repository import EmailRepository
from domain.mail.entities.email import Email
from domain.mail.value_objects.parsed_email import ParsedEmail


class AsyncMailPollingService(MailPollingService):
    """
    异步邮件轮询服务实现

    使用 asyncio 实现周期性邮件轮询，支持：
    - 并行轮询所有邮箱（使用 asyncio.gather）
    - 并发连接数限制（使用 Semaphore）
    - 单邮箱超时处理（使用 wait_for）
    - 单邮箱失败不影响其他邮箱
    - 启动后立即执行第一次轮询
    - 优雅停止
    - 动态邮箱发现（每次轮询重新获取邮箱列表）
    """

    def __init__(
        self,
        mailbox_repository: MailboxAccountRepository,
        imap_service: ImapMailFetchService,
        email_repository: EmailRepository | Callable[[], EmailRepository],
        interval: float = MailPollingService.DEFAULT_INTERVAL,
        max_concurrent_connections: int = MailPollingService.DEFAULT_MAX_CONCURRENT,
        mailbox_poll_timeout: float = MailPollingService.DEFAULT_TIMEOUT,
        logger: Optional[logging.Logger] = None,
    ):
        """
        初始化异步邮件轮询服务

        Args:
            mailbox_repository: 邮箱账号仓储
            imap_service: IMAP 邮件收取服务
            email_repository: 邮件仓储实例或工厂函数（用于线程安全的并行处理）
            interval: 轮询间隔（秒），默认 5 秒
            max_concurrent_connections: 最大并发 IMAP 连接数，默认 10
            mailbox_poll_timeout: 单邮箱轮询超时（秒），默认 30 秒
            logger: 可选的日志记录器
        """
        self._mailbox_repository = mailbox_repository
        self._imap_service = imap_service
        # 支持工厂函数或直接实例（向后兼容）
        if callable(email_repository) and not isinstance(email_repository, EmailRepository):
            self._email_repository_factory: Callable[[], EmailRepository] = email_repository
        else:
            # 向后兼容：如果传入实例，包装为返回该实例的函数（单线程场景）
            self._email_repository_factory = lambda repo=email_repository: repo  # type: ignore
        self._interval = interval
        self._max_concurrent = max_concurrent_connections
        self._timeout = mailbox_poll_timeout
        self._logger = logger or logging.getLogger(__name__)

        self._semaphore: Optional[asyncio.Semaphore] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def is_running(self) -> bool:
        """检查轮询服务是否正在运行"""
        return self._running and self._task is not None

    @property
    def interval(self) -> float:
        """获取轮询间隔（秒）"""
        return self._interval

    @property
    def max_concurrent_connections(self) -> int:
        """获取最大并发连接数"""
        return self._max_concurrent

    @property
    def mailbox_poll_timeout(self) -> float:
        """获取单邮箱轮询超时（秒）"""
        return self._timeout

    async def start(self) -> None:
        """
        启动轮询服务

        启动后立即执行第一次轮询，之后按配置的间隔周期性执行。
        初始化并发控制的 Semaphore 和 ThreadPoolExecutor。
        """
        if self._running:
            self._logger.warning("Polling service already running")
            return

        self._running = True
        # 缓存事件循环（Fix L1）
        self._loop = asyncio.get_running_loop()
        # 初始化并发控制
        self._semaphore = asyncio.Semaphore(self._max_concurrent)
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_concurrent,
            thread_name_prefix="imap-poll-"
        )
        self._task = asyncio.create_task(self._polling_loop())
        self._logger.info(
            f"Mail polling service started "
            f"(interval={self._interval}s, "
            f"max_concurrent={self._max_concurrent}, "
            f"timeout={self._timeout}s)"
        )

    async def stop(self) -> None:
        """
        停止轮询服务（优雅关闭）

        取消轮询任务，关闭线程池，清理资源。
        """
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if self._executor:
            # 非阻塞关闭线程池（Fix M2）
            # 使用 wait=False 避免阻塞事件循环，让线程自然完成
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

        self._semaphore = None
        self._loop = None
        self._logger.info("Mail polling service stopped")

    async def _polling_loop(self) -> None:
        """轮询主循环"""
        # 启动后立即执行第一次轮询
        await self._poll_all_mailboxes()

        while self._running:
            await asyncio.sleep(self._interval)
            if self._running:  # 再次检查，防止 sleep 期间被停止
                await self._poll_all_mailboxes()

    async def _poll_all_mailboxes(self) -> None:
        """并行轮询所有邮箱"""
        poll_start = datetime.now(timezone.utc)
        self._logger.debug(f"Starting parallel mail polling cycle at {poll_start}")

        try:
            # 每次轮询重新获取邮箱列表（支持动态发现）
            mailboxes = self._mailbox_repository.list_all()
        except Exception as e:
            self._logger.error(f"Failed to fetch mailbox list: {e}")
            return

        if not mailboxes:
            self._logger.debug("No mailboxes configured, skipping poll")
            return

        self._logger.info(f"Polling {len(mailboxes)} mailboxes in parallel")

        # 并行执行所有邮箱轮询
        tasks = [
            self._poll_single_mailbox_with_timeout(mailbox)
            for mailbox in mailboxes
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        success_count = 0
        error_count = 0
        timeout_count = 0
        total_emails = 0

        for result in results:
            if isinstance(result, asyncio.TimeoutError):
                timeout_count += 1
            elif isinstance(result, Exception):
                error_count += 1
            elif isinstance(result, int):
                success_count += 1
                total_emails += result

        poll_duration = (datetime.now(timezone.utc) - poll_start).total_seconds()
        self._logger.info(
            f"Polling cycle complete: {len(mailboxes)} mailboxes, "
            f"{success_count} ok, {error_count} errors, {timeout_count} timeouts, "
            f"{total_emails} new emails, {poll_duration:.2f}s"
        )

    async def _poll_single_mailbox_with_timeout(self, mailbox: MailboxAccount) -> int:
        """
        带超时和并发控制的单邮箱轮询

        Args:
            mailbox: 邮箱账号

        Returns:
            收取并保存的新邮件数量

        Raises:
            asyncio.TimeoutError: 轮询超时
            Exception: 其他错误
        """
        # Fix L2: 防御性检查
        if self._semaphore is None:
            raise RuntimeError("Polling service not started. Call start() first.")

        try:
            # 获取信号量（限制并发）
            async with self._semaphore:
                self._logger.debug(f"Acquired semaphore for {mailbox.username}")

                # 带超时执行
                count = await asyncio.wait_for(
                    self._poll_single_mailbox(mailbox),
                    timeout=self._timeout
                )
                return count

        except asyncio.TimeoutError:
            self._logger.warning(
                f"Timeout polling mailbox {mailbox.username} after {self._timeout}s"
            )
            raise

        except Exception as e:
            self._logger.error(f"Failed to poll mailbox {mailbox.username}: {e}")
            raise

    async def _poll_single_mailbox(self, mailbox: MailboxAccount) -> int:
        """
        轮询单个邮箱

        Args:
            mailbox: 邮箱账号

        Returns:
            收取并保存的新邮件数量
        """
        # fetch_new_emails 是同步方法，在 executor 中运行避免阻塞
        # Fix L1: 使用缓存的事件循环
        loop = self._loop or asyncio.get_running_loop()
        parsed_emails: List[ParsedEmail] = await loop.run_in_executor(
            self._executor,
            self._imap_service.fetch_new_emails,
            mailbox
        )

        saved_count = 0
        # Fix H1/H2: 为每个邮箱创建独立的仓储实例（线程安全）
        email_repository = self._email_repository_factory()

        for parsed_email in parsed_emails:
            # Fix M3: 为每封邮件单独捕获异常，避免一封失败影响整批
            try:
                # 去重检查
                if email_repository.exists_by_message_id(parsed_email.message_id):
                    self._logger.debug(
                        f"Email {parsed_email.message_id} already exists, skipping"
                    )
                    continue

                # 转换并保存
                email = self._convert_to_email(mailbox, parsed_email)
                email_repository.add(email)
                saved_count += 1

                # 安全截取主题用于日志
                subject = parsed_email.subject or ""
                if subject:
                    subject_preview = subject[:50]
                    if len(subject) > 50:
                        subject_preview += "..."
                else:
                    subject_preview = "(no subject)"

                self._logger.info(f"[{mailbox.username}] Saved new email: {subject_preview}")

            except Exception as e:
                self._logger.error(
                    f"[{mailbox.username}] Failed to process email "
                    f"{parsed_email.message_id}: {e}"
                )
                # 继续处理下一封邮件

        return saved_count

    def _convert_to_email(
        self,
        mailbox: MailboxAccount,
        parsed_email: ParsedEmail
    ) -> Email:
        """
        将 ParsedEmail 转换为 Email 实体

        Args:
            mailbox: 邮箱账号
            parsed_email: 解析后的邮件

        Returns:
            Email 实体
        """
        return Email.create(
            mailbox_id=mailbox.id,
            message_id=parsed_email.message_id,
            from_address=parsed_email.from_address,
            subject=parsed_email.subject,
            received_at=parsed_email.received_at or datetime.now(timezone.utc),
            body_text=parsed_email.content.text,
            body_html=parsed_email.content.html,
        )
