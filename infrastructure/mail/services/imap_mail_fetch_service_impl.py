"""IMAP 邮件收取服务实现"""

import imaplib
import ssl
import email
import time
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Optional, Union, Tuple, Generator

from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mail.services.imap_mail_fetch_service import (
    ImapMailFetchService,
    ImapConnectionError,
    ImapAuthenticationError,
)
from domain.mail.value_objects.parsed_email import ParsedEmail
from domain.mail.value_objects.email_content import EmailContent


class ImapMailFetchServiceImpl(ImapMailFetchService):
    """
    IMAP 邮件收取服务实现

    使用 Python 标准库 imaplib 实现 IMAP 邮件收取，支持：
    - SSL/TLS 安全连接（端口 993）
    - 未读邮件收取和标记已读
    - HTML 和纯文本邮件解析
    - 自动重连（指数退避策略）
    """

    MAX_RETRIES = 3
    BASE_DELAY = 1  # 秒
    DEFAULT_TIMEOUT = 30  # 秒

    def __init__(
        self,
        encryption_key: Union[str, bytes],
        logger: Optional[logging.Logger] = None,
    ):
        """
        初始化 IMAP 邮件收取服务

        Args:
            encryption_key: 用于解密邮箱密码的加密密钥
            logger: 可选的日志记录器
        """
        self._encryption_key = encryption_key
        self._logger = logger or logging.getLogger(__name__)

    def fetch_new_emails(self, mailbox: MailboxAccount) -> List[ParsedEmail]:
        """
        收取指定邮箱的新邮件

        连接到邮箱的 IMAP 服务器，获取所有未读邮件，
        解析邮件内容，并将邮件标记为已读。

        Args:
            mailbox: 邮箱账号实体

        Returns:
            解析后的邮件列表
        """
        with self._connection(mailbox) as imap:
            if imap is None:
                return []

            try:
                # 选择收件箱
                imap.select("INBOX")

                # 搜索未读邮件
                status, messages = imap.search(None, "UNSEEN")
                if status != "OK":
                    self._logger.warning(f"Failed to search emails: {status}")
                    return []

                email_ids = messages[0].split()
                if not email_ids:
                    self._logger.debug("No unread emails found")
                    return []

                self._logger.info(f"Found {len(email_ids)} unread email(s)")

                parsed_emails: List[ParsedEmail] = []

                for email_id in email_ids:
                    try:
                        parsed_email = self._fetch_and_parse_email(imap, email_id)
                        if parsed_email:
                            parsed_emails.append(parsed_email)
                            # 标记为已读
                            imap.store(email_id, "+FLAGS", "\\Seen")
                    except Exception as e:
                        self._logger.error(f"Failed to process email {email_id}: {e}")
                        continue

                return parsed_emails

            except Exception as e:
                self._logger.error(f"Error during email fetch: {e}")
                return []

    def test_connection(self, mailbox: MailboxAccount) -> bool:
        """
        测试邮箱的 IMAP 连接

        Args:
            mailbox: 邮箱账号实体

        Returns:
            True 如果连接成功，False 如果失败
        """
        try:
            imap = self._connect(mailbox)
            if imap:
                self._disconnect(imap)
                return True
            return False
        except (ImapConnectionError, ImapAuthenticationError) as e:
            self._logger.warning(f"Connection test failed: {e}")
            return False
        except Exception as e:
            self._logger.warning(f"Unexpected error during connection test: {e}")
            return False

    def _connect_with_retry(
        self, mailbox: MailboxAccount
    ) -> Optional[imaplib.IMAP4_SSL]:
        """
        带重试的连接逻辑（指数退避）

        Args:
            mailbox: 邮箱账号实体

        Returns:
            IMAP 连接对象，或 None 如果所有重试都失败
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                return self._connect(mailbox)
            except (ImapConnectionError, ImapAuthenticationError) as e:
                delay = self.BASE_DELAY * (2**attempt)  # 1s, 2s, 4s
                self._logger.warning(
                    f"IMAP connection attempt {attempt + 1}/{self.MAX_RETRIES} "
                    f"failed, retry in {delay}s: {e}"
                )
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(delay)

        self._logger.error(
            f"IMAP connection failed after {self.MAX_RETRIES} retries "
            f"for {mailbox.username}"
        )
        return None

    @contextmanager
    def _connection(
        self, mailbox: MailboxAccount
    ) -> Generator[Optional[imaplib.IMAP4_SSL], None, None]:
        """
        IMAP 连接上下文管理器

        确保连接在使用后正确关闭，即使发生异常。

        Args:
            mailbox: 邮箱账号实体

        Yields:
            IMAP 连接对象，或 None 如果连接失败

        用法:
            with self._connection(mailbox) as imap:
                if imap:
                    imap.select("INBOX")
                    # ... 操作邮件
        """
        imap = self._connect_with_retry(mailbox)
        try:
            yield imap
        finally:
            if imap:
                self._disconnect(imap)

    def _connect(self, mailbox: MailboxAccount) -> imaplib.IMAP4_SSL:
        """
        建立 IMAP SSL 连接

        Args:
            mailbox: 邮箱账号实体

        Returns:
            IMAP 连接对象

        Raises:
            ImapConnectionError: 连接失败
            ImapAuthenticationError: 认证失败
        """
        if mailbox.imap_config is None:
            raise ImapConnectionError(
                server="unknown",
                port=0,
                message="IMAP configuration is missing",
            )

        server = mailbox.imap_config.server
        port = mailbox.imap_config.port

        try:
            # 创建 SSL 上下文
            context = ssl.create_default_context()

            # 建立 SSL 连接
            self._logger.debug(f"Connecting to {server}:{port}")
            imap = imaplib.IMAP4_SSL(
                host=server,
                port=port,
                ssl_context=context,
                timeout=self.DEFAULT_TIMEOUT,
            )

        except Exception as e:
            raise ImapConnectionError(
                server=server,
                port=port,
                message=str(e),
            )

        # 获取解密后的密码
        password = mailbox.get_decrypted_password(self._encryption_key)

        try:
            # 登录
            self._logger.debug(f"Authenticating as {mailbox.username}")
            imap.login(mailbox.username, password)

        except imaplib.IMAP4.error as e:
            raise ImapAuthenticationError(
                username=mailbox.username,
                message=str(e),
            )

        self._logger.info(f"Successfully connected to {server}:{port}")
        return imap

    def _disconnect(self, imap: imaplib.IMAP4_SSL) -> None:
        """
        断开 IMAP 连接

        Args:
            imap: IMAP 连接对象
        """
        try:
            # close() 只能在 select() 成功后调用，否则会抛出异常
            # 检查 IMAP 状态，只有在 SELECTED 状态才调用 close()
            if imap.state == "SELECTED":
                imap.close()
        except Exception as e:
            self._logger.debug(f"Error during close: {e}")

        try:
            imap.logout()
        except Exception as e:
            self._logger.debug(f"Error during logout: {e}")

    def _fetch_and_parse_email(
        self, imap: imaplib.IMAP4_SSL, email_id: bytes
    ) -> Optional[ParsedEmail]:
        """
        获取并解析单封邮件

        Args:
            imap: IMAP 连接对象
            email_id: 邮件 ID

        Returns:
            解析后的邮件，或 None 如果解析失败
        """
        status, msg_data = imap.fetch(email_id, "(RFC822)")
        if status != "OK" or not msg_data or not msg_data[0]:
            return None

        raw_email = msg_data[0][1]
        if not isinstance(raw_email, bytes):
            return None

        msg = email.message_from_bytes(raw_email)

        # 解析 Message-ID
        message_id = msg.get("Message-ID", "")
        if not message_id:
            message_id = f"unknown-{email_id.decode()}"

        # 解析发件人
        from_address = self._decode_header_value(msg.get("From", ""))

        # 解析主题
        subject = self._decode_header_value(msg.get("Subject", ""))

        # 解析接收时间
        received_at = self._parse_date(msg.get("Date"))

        # 解析正文
        body_text, body_html = self._extract_body(msg)

        return ParsedEmail(
            message_id=message_id,
            from_address=from_address,
            subject=subject,
            content=EmailContent(text=body_text, html=body_html),
            received_at=received_at,
        )

    def _decode_header_value(self, value: Optional[str]) -> str:
        """
        解码邮件头部值（处理编码）

        Args:
            value: 原始头部值

        Returns:
            解码后的字符串
        """
        if not value:
            return ""

        decoded_parts = decode_header(value)
        result_parts = []

        for part, charset in decoded_parts:
            if isinstance(part, bytes):
                try:
                    decoded = part.decode(charset or "utf-8", errors="replace")
                except (LookupError, UnicodeDecodeError):
                    decoded = part.decode("utf-8", errors="replace")
                result_parts.append(decoded)
            else:
                result_parts.append(part)

        return "".join(result_parts)

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """
        解析邮件日期

        Args:
            date_str: 日期字符串

        Returns:
            datetime 对象，或 None 如果解析失败
        """
        if not date_str:
            return datetime.now(timezone.utc)

        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            return datetime.now(timezone.utc)

    def _extract_body(
        self, msg: email.message.Message
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        提取邮件正文（纯文本和 HTML）

        Args:
            msg: 邮件消息对象

        Returns:
            (纯文本正文, HTML 正文) 元组
        """
        body_text: Optional[str] = None
        body_html: Optional[str] = None

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                # 跳过附件
                if "attachment" in content_disposition:
                    continue

                payload = part.get_payload(decode=True)
                if payload is None:
                    continue

                charset = part.get_content_charset() or "utf-8"

                try:
                    decoded_content = payload.decode(charset, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    decoded_content = payload.decode("utf-8", errors="replace")

                if content_type == "text/plain" and body_text is None:
                    body_text = decoded_content
                elif content_type == "text/html" and body_html is None:
                    body_html = decoded_content

        else:
            content_type = msg.get_content_type()
            payload = msg.get_payload(decode=True)

            if payload is not None:
                charset = msg.get_content_charset() or "utf-8"

                try:
                    decoded_content = payload.decode(charset, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    decoded_content = payload.decode("utf-8", errors="replace")

                if content_type == "text/plain":
                    body_text = decoded_content
                elif content_type == "text/html":
                    body_html = decoded_content

        return body_text, body_html
