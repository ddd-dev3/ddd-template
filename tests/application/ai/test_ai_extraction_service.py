"""AiExtractionService 单元测试"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from uuid import uuid4

from application.ai.services.ai_extraction_service import AiExtractionService
from domain.ai.value_objects.extraction_result import ExtractionResult
from domain.ai.value_objects.extraction_type import ExtractionType
from domain.mail.entities.email import Email


class TestAiExtractionServiceInit:
    """初始化测试"""

    def test_init_with_extractor(self):
        """测试使用提取器初始化"""
        mock_extractor = Mock()
        service = AiExtractionService(extractor=mock_extractor)
        assert service._extractor == mock_extractor

    def test_init_with_custom_logger(self):
        """测试使用自定义日志记录器"""
        mock_extractor = Mock()
        mock_logger = Mock()
        service = AiExtractionService(extractor=mock_extractor, logger=mock_logger)
        assert service._logger == mock_logger


class TestAiExtractionServiceExtractCodeFromEmail:
    """extract_code_from_email 方法测试（同步）"""

    @pytest.fixture
    def mock_extractor(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    @pytest.fixture
    def sample_email(self):
        return Email.create(
            mailbox_id=uuid4(),
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Your verification code",
            received_at=datetime.now(),
            body_text="Your verification code is 123456",
        )

    def test_extract_code_success(self, service, mock_extractor, sample_email):
        """测试成功提取验证码"""
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        mock_extractor.extract_code.return_value = expected_result

        result = service.extract_code_from_email(sample_email)

        assert result.type == ExtractionType.CODE
        assert result.code == "123456"
        assert result.confidence == 0.95
        mock_extractor.extract_code.assert_called_once_with(sample_email.body)

    def test_extract_code_not_found(self, service, mock_extractor, sample_email):
        """测试未找到验证码"""
        expected_result = ExtractionResult(
            type=ExtractionType.UNKNOWN,
            confidence=0.0,
        )
        mock_extractor.extract_code.return_value = expected_result

        result = service.extract_code_from_email(sample_email)

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None

    def test_extract_code_empty_body(self, service, mock_extractor):
        """测试空邮件正文"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<empty@example.com>",
            from_address="sender@example.com",
            subject="Empty email",
            received_at=datetime.now(),
            body_text=None,
            body_html=None,
        )

        result = service.extract_code_from_email(email)

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty email body" in result.raw_response
        mock_extractor.extract_code.assert_not_called()

    def test_extract_code_html_only_email(self, service, mock_extractor):
        """测试仅 HTML 正文的邮件"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<html@example.com>",
            from_address="sender@example.com",
            subject="HTML email",
            received_at=datetime.now(),
            body_text=None,
            body_html="<html><body>Your code is <b>AB12CD</b></body></html>",
        )
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="AB12CD",
            confidence=0.9,
        )
        mock_extractor.extract_code.return_value = expected_result

        result = service.extract_code_from_email(email)

        assert result.type == ExtractionType.CODE
        assert result.code == "AB12CD"
        # 验证使用的是 HTML 内容
        mock_extractor.extract_code.assert_called_once_with(email.body_html)

    def test_extract_code_prefers_text_over_html(self, service, mock_extractor):
        """测试优先使用纯文本而非 HTML"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<both@example.com>",
            from_address="sender@example.com",
            subject="Both bodies",
            received_at=datetime.now(),
            body_text="Text: Your code is 123456",
            body_html="<html><body>HTML: Your code is 123456</body></html>",
        )
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        mock_extractor.extract_code.return_value = expected_result

        result = service.extract_code_from_email(email)

        # 验证使用的是纯文本内容
        mock_extractor.extract_code.assert_called_once_with(email.body_text)


class TestAiExtractionServiceExtractCodeFromEmailAsync:
    """extract_code_from_email_async 方法测试（异步）"""

    @pytest.fixture
    def mock_extractor(self):
        extractor = Mock()
        extractor.extract_code_async = AsyncMock()
        return extractor

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    @pytest.fixture
    def sample_email(self):
        return Email.create(
            mailbox_id=uuid4(),
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Your verification code",
            received_at=datetime.now(),
            body_text="Your verification code is 123456",
        )

    @pytest.mark.asyncio
    async def test_extract_code_async_success(self, service, mock_extractor, sample_email):
        """测试异步成功提取验证码"""
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="ASYNC123",
            confidence=0.95,
        )
        mock_extractor.extract_code_async.return_value = expected_result

        result = await service.extract_code_from_email_async(sample_email)

        assert result.type == ExtractionType.CODE
        assert result.code == "ASYNC123"
        mock_extractor.extract_code_async.assert_called_once_with(sample_email.body)

    @pytest.mark.asyncio
    async def test_extract_code_async_empty_body(self, service, mock_extractor):
        """测试异步空邮件正文"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<empty@example.com>",
            from_address="sender@example.com",
            subject="Empty email",
            received_at=datetime.now(),
            body_text=None,
            body_html=None,
        )

        result = await service.extract_code_from_email_async(email)

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty email body" in result.raw_response
        mock_extractor.extract_code_async.assert_not_called()


class TestAiExtractionServiceMarkAsProcessed:
    """mark_as_processed 功能测试"""

    @pytest.fixture
    def mock_extractor(self):
        extractor = Mock()
        extractor.extract_code.return_value = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        return extractor

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    @pytest.fixture
    def sample_email(self):
        return Email.create(
            mailbox_id=uuid4(),
            message_id="<test@example.com>",
            from_address="sender@example.com",
            subject="Test",
            received_at=datetime.now(),
            body_text="Your code is 123456",
        )

    def test_mark_as_processed_true(self, service, sample_email):
        """测试 mark_as_processed=True 时标记邮件"""
        assert not sample_email.is_processed

        service.extract_code_from_email(sample_email, mark_as_processed=True)

        assert sample_email.is_processed

    def test_mark_as_processed_false(self, service, sample_email):
        """测试 mark_as_processed=False 时不标记邮件"""
        assert not sample_email.is_processed

        service.extract_code_from_email(sample_email, mark_as_processed=False)

        assert not sample_email.is_processed

    def test_mark_as_processed_default_false(self, service, sample_email):
        """测试 mark_as_processed 默认为 False"""
        assert not sample_email.is_processed

        service.extract_code_from_email(sample_email)

        assert not sample_email.is_processed

    def test_mark_as_processed_already_processed_email(self, service, sample_email):
        """测试已处理邮件不会重复标记"""
        sample_email.mark_as_processed()
        assert sample_email.is_processed

        # 不应抛出异常
        result = service.extract_code_from_email(sample_email, mark_as_processed=True)

        assert result.type == ExtractionType.CODE
        assert sample_email.is_processed


class TestAiExtractionServiceExtractFromContent:
    """extract_from_content 方法测试（同步）"""

    @pytest.fixture
    def mock_extractor(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    def test_extract_from_content_success(self, service, mock_extractor):
        """测试从内容直接提取成功"""
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="ABCD1234",
            confidence=0.9,
        )
        mock_extractor.extract_code.return_value = expected_result

        result = service.extract_from_content("Your code is ABCD1234")

        assert result.type == ExtractionType.CODE
        assert result.code == "ABCD1234"
        mock_extractor.extract_code.assert_called_once_with("Your code is ABCD1234")

    def test_extract_from_content_empty(self, service, mock_extractor):
        """测试空内容返回 UNKNOWN"""
        result = service.extract_from_content("")

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty content" in result.raw_response
        mock_extractor.extract_code.assert_not_called()

    def test_extract_from_content_html(self, service, mock_extractor):
        """测试从 HTML 内容提取"""
        html_content = "<html><body>Code: <span>XYZ789</span></body></html>"
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="XYZ789",
            confidence=0.85,
        )
        mock_extractor.extract_code.return_value = expected_result

        result = service.extract_from_content(html_content)

        assert result.type == ExtractionType.CODE
        assert result.code == "XYZ789"


class TestAiExtractionServiceExtractFromContentAsync:
    """extract_from_content_async 方法测试（异步）"""

    @pytest.fixture
    def mock_extractor(self):
        extractor = Mock()
        extractor.extract_code_async = AsyncMock()
        return extractor

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    @pytest.mark.asyncio
    async def test_extract_from_content_async_success(self, service, mock_extractor):
        """测试异步从内容直接提取成功"""
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="ASYNCCODE",
            confidence=0.9,
        )
        mock_extractor.extract_code_async.return_value = expected_result

        result = await service.extract_from_content_async("Your code is ASYNCCODE")

        assert result.type == ExtractionType.CODE
        assert result.code == "ASYNCCODE"
        mock_extractor.extract_code_async.assert_called_once_with("Your code is ASYNCCODE")

    @pytest.mark.asyncio
    async def test_extract_from_content_async_empty(self, service, mock_extractor):
        """测试异步空内容返回 UNKNOWN"""
        result = await service.extract_from_content_async("")

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty content" in result.raw_response
        mock_extractor.extract_code_async.assert_not_called()


class TestAiExtractionServiceIntegration:
    """集成测试 - 与 Mock 提取器协作"""

    def test_full_extraction_flow_chinese_email(self):
        """测试完整提取流程 - 中文邮件"""
        mock_extractor = Mock()
        mock_extractor.extract_code.return_value = ExtractionResult(
            type=ExtractionType.CODE,
            code="583921",
            confidence=0.95,
        )
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<chinese@example.com>",
            from_address="noreply@service.cn",
            subject="【验证码】您的验证码",
            received_at=datetime.now(),
            body_text="您的验证码是 583921，5分钟内有效。请勿泄露。",
        )

        result = service.extract_code_from_email(email, mark_as_processed=True)

        assert result.type == ExtractionType.CODE
        assert result.code == "583921"
        assert result.is_successful
        assert email.is_processed

    def test_full_extraction_flow_english_email(self):
        """测试完整提取流程 - 英文邮件"""
        mock_extractor = Mock()
        mock_extractor.extract_code.return_value = ExtractionResult(
            type=ExtractionType.CODE,
            code="AB12CD",
            confidence=0.9,
        )
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<english@example.com>",
            from_address="noreply@service.com",
            subject="Your verification code",
            received_at=datetime.now(),
            body_text="Your verification code is: AB12CD. Valid for 10 minutes.",
        )

        result = service.extract_code_from_email(email)

        assert result.type == ExtractionType.CODE
        assert result.code == "AB12CD"
        assert result.is_successful

    def test_full_extraction_flow_no_code_email(self):
        """测试完整提取流程 - 无验证码邮件"""
        mock_extractor = Mock()
        mock_extractor.extract_code.return_value = ExtractionResult(
            type=ExtractionType.UNKNOWN,
            confidence=0.0,
        )
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<newsletter@example.com>",
            from_address="newsletter@shop.com",
            subject="This week's deals",
            received_at=datetime.now(),
            body_text="Check out our latest products! Free shipping on orders over $50.",
        )

        result = service.extract_code_from_email(email)

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None
        assert not result.is_successful

    @pytest.mark.asyncio
    async def test_full_async_extraction_flow(self):
        """测试完整异步提取流程"""
        mock_extractor = Mock()
        mock_extractor.extract_code_async = AsyncMock(return_value=ExtractionResult(
            type=ExtractionType.CODE,
            code="ASYNCFULL",
            confidence=0.92,
        ))
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<async@example.com>",
            from_address="noreply@service.com",
            subject="Async code",
            received_at=datetime.now(),
            body_text="Your async code is ASYNCFULL",
        )

        result = await service.extract_code_from_email_async(email, mark_as_processed=True)

        assert result.type == ExtractionType.CODE
        assert result.code == "ASYNCFULL"
        assert result.is_successful
        assert email.is_processed


# ============ Story 3.2: 链接提取测试 ============


class TestAiExtractionServiceExtractLinkFromEmail:
    """extract_link_from_email 方法测试（同步）"""

    @pytest.fixture
    def mock_extractor(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    @pytest.fixture
    def sample_email(self):
        return Email.create(
            mailbox_id=uuid4(),
            message_id="<verify@example.com>",
            from_address="noreply@example.com",
            subject="Verify your email",
            received_at=datetime.now(),
            body_text="Please click https://example.com/verify?token=abc123 to verify",
        )

    def test_extract_link_success(self, service, mock_extractor, sample_email):
        """测试成功提取验证链接"""
        expected_result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://example.com/verify?token=abc123",
            confidence=0.95,
        )
        mock_extractor.extract_link.return_value = expected_result

        result = service.extract_link_from_email(sample_email)

        assert result.type == ExtractionType.LINK
        assert result.link == "https://example.com/verify?token=abc123"
        assert result.confidence == 0.95
        mock_extractor.extract_link.assert_called_once_with(sample_email.body)

    def test_extract_link_not_found(self, service, mock_extractor, sample_email):
        """测试未找到验证链接"""
        expected_result = ExtractionResult(
            type=ExtractionType.UNKNOWN,
            confidence=0.0,
        )
        mock_extractor.extract_link.return_value = expected_result

        result = service.extract_link_from_email(sample_email)

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None

    def test_extract_link_empty_body(self, service, mock_extractor):
        """测试空邮件正文"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<empty@example.com>",
            from_address="sender@example.com",
            subject="Empty email",
            received_at=datetime.now(),
            body_text=None,
            body_html=None,
        )

        result = service.extract_link_from_email(email)

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty email body" in result.raw_response
        mock_extractor.extract_link.assert_not_called()

    def test_extract_link_html_only_email(self, service, mock_extractor):
        """测试仅 HTML 正文的邮件"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<html@example.com>",
            from_address="sender@example.com",
            subject="HTML email",
            received_at=datetime.now(),
            body_text=None,
            body_html='<html><body><a href="https://auth.example.com/verify?token=xyz">Verify</a></body></html>',
        )
        expected_result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://auth.example.com/verify?token=xyz",
            confidence=0.9,
        )
        mock_extractor.extract_link.return_value = expected_result

        result = service.extract_link_from_email(email)

        assert result.type == ExtractionType.LINK
        assert result.link == "https://auth.example.com/verify?token=xyz"
        mock_extractor.extract_link.assert_called_once_with(email.body_html)

    def test_extract_link_mark_as_processed(self, service, mock_extractor, sample_email):
        """测试 mark_as_processed 功能"""
        expected_result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://example.com/verify?token=abc123",
            confidence=0.95,
        )
        mock_extractor.extract_link.return_value = expected_result

        assert not sample_email.is_processed
        service.extract_link_from_email(sample_email, mark_as_processed=True)
        assert sample_email.is_processed


class TestAiExtractionServiceExtractLinkFromEmailAsync:
    """extract_link_from_email_async 方法测试（异步）"""

    @pytest.fixture
    def mock_extractor(self):
        extractor = Mock()
        extractor.extract_link_async = AsyncMock()
        return extractor

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    @pytest.fixture
    def sample_email(self):
        return Email.create(
            mailbox_id=uuid4(),
            message_id="<async-verify@example.com>",
            from_address="noreply@example.com",
            subject="Verify your email",
            received_at=datetime.now(),
            body_text="Please verify: https://example.com/verify?token=async123",
        )

    @pytest.mark.asyncio
    async def test_extract_link_async_success(self, service, mock_extractor, sample_email):
        """测试异步成功提取验证链接"""
        expected_result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://example.com/verify?token=async123",
            confidence=0.92,
        )
        mock_extractor.extract_link_async.return_value = expected_result

        result = await service.extract_link_from_email_async(sample_email)

        assert result.type == ExtractionType.LINK
        assert result.link == "https://example.com/verify?token=async123"
        mock_extractor.extract_link_async.assert_called_once_with(sample_email.body)

    @pytest.mark.asyncio
    async def test_extract_link_async_empty_body(self, service, mock_extractor):
        """测试异步空邮件正文"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<empty@example.com>",
            from_address="sender@example.com",
            subject="Empty email",
            received_at=datetime.now(),
            body_text=None,
            body_html=None,
        )

        result = await service.extract_link_from_email_async(email)

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty email body" in result.raw_response
        mock_extractor.extract_link_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_link_async_mark_as_processed(self, service, mock_extractor, sample_email):
        """测试异步 mark_as_processed 功能"""
        expected_result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://example.com/verify?token=async123",
            confidence=0.92,
        )
        mock_extractor.extract_link_async.return_value = expected_result

        assert not sample_email.is_processed
        await service.extract_link_from_email_async(sample_email, mark_as_processed=True)
        assert sample_email.is_processed


class TestAiExtractionServiceExtractLinkFromContent:
    """extract_link_from_content 方法测试（同步）"""

    @pytest.fixture
    def mock_extractor(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    def test_extract_link_from_content_success(self, service, mock_extractor):
        """测试从内容直接提取链接成功"""
        expected_result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://verify.example.com/token123",
            confidence=0.9,
        )
        mock_extractor.extract_link.return_value = expected_result

        result = service.extract_link_from_content("Click https://verify.example.com/token123 to verify")

        assert result.type == ExtractionType.LINK
        assert result.link == "https://verify.example.com/token123"
        mock_extractor.extract_link.assert_called_once_with("Click https://verify.example.com/token123 to verify")

    def test_extract_link_from_content_empty(self, service, mock_extractor):
        """测试空内容返回 UNKNOWN"""
        result = service.extract_link_from_content("")

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty content" in result.raw_response
        mock_extractor.extract_link.assert_not_called()

    def test_extract_link_from_content_html(self, service, mock_extractor):
        """测试从 HTML 内容提取链接"""
        html_content = '<html><body><a href="https://auth.example.com/confirm?token=xyz">Confirm</a></body></html>'
        expected_result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://auth.example.com/confirm?token=xyz",
            confidence=0.88,
        )
        mock_extractor.extract_link.return_value = expected_result

        result = service.extract_link_from_content(html_content)

        assert result.type == ExtractionType.LINK
        assert result.link == "https://auth.example.com/confirm?token=xyz"


class TestAiExtractionServiceExtractLinkFromContentAsync:
    """extract_link_from_content_async 方法测试（异步）"""

    @pytest.fixture
    def mock_extractor(self):
        extractor = Mock()
        extractor.extract_link_async = AsyncMock()
        return extractor

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    @pytest.mark.asyncio
    async def test_extract_link_from_content_async_success(self, service, mock_extractor):
        """测试异步从内容直接提取链接成功"""
        expected_result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://async.example.com/verify?key=abc",
            confidence=0.9,
        )
        mock_extractor.extract_link_async.return_value = expected_result

        result = await service.extract_link_from_content_async("Verify: https://async.example.com/verify?key=abc")

        assert result.type == ExtractionType.LINK
        assert result.link == "https://async.example.com/verify?key=abc"
        mock_extractor.extract_link_async.assert_called_once_with("Verify: https://async.example.com/verify?key=abc")

    @pytest.mark.asyncio
    async def test_extract_link_from_content_async_empty(self, service, mock_extractor):
        """测试异步空内容返回 UNKNOWN"""
        result = await service.extract_link_from_content_async("")

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty content" in result.raw_response
        mock_extractor.extract_link_async.assert_not_called()


class TestAiExtractionServiceLinkIntegration:
    """链接提取集成测试"""

    def test_full_link_extraction_flow_chinese_email(self):
        """测试完整链接提取流程 - 中文邮件"""
        mock_extractor = Mock()
        mock_extractor.extract_link.return_value = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://claude.ai/verify?token=abc123def456",
            confidence=0.95,
        )
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<chinese-verify@example.com>",
            from_address="noreply@service.cn",
            subject="【验证】请验证您的邮箱",
            received_at=datetime.now(),
            body_text="请点击以下链接验证您的邮箱：https://claude.ai/verify?token=abc123def456",
        )

        result = service.extract_link_from_email(email, mark_as_processed=True)

        assert result.type == ExtractionType.LINK
        assert result.link == "https://claude.ai/verify?token=abc123def456"
        assert result.is_successful
        assert email.is_processed

    def test_full_link_extraction_flow_english_email(self):
        """测试完整链接提取流程 - 英文邮件"""
        mock_extractor = Mock()
        mock_extractor.extract_link.return_value = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://accounts.google.com/signin/v2/challenge?key=xyz",
            confidence=0.92,
        )
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<english-verify@example.com>",
            from_address="noreply@google.com",
            subject="Verify your Google account",
            received_at=datetime.now(),
            body_text="Click the link below to verify your account: https://accounts.google.com/signin/v2/challenge?key=xyz",
        )

        result = service.extract_link_from_email(email)

        assert result.type == ExtractionType.LINK
        assert "accounts.google.com" in result.link
        assert result.is_successful

    def test_full_link_extraction_flow_no_verification_link(self):
        """测试完整链接提取流程 - 无验证链接邮件"""
        mock_extractor = Mock()
        mock_extractor.extract_link.return_value = ExtractionResult(
            type=ExtractionType.UNKNOWN,
            confidence=0.0,
        )
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<newsletter@example.com>",
            from_address="newsletter@shop.com",
            subject="This week's deals",
            received_at=datetime.now(),
            body_text="Check out our latest products! Visit our website: https://shop.com/deals",
        )

        result = service.extract_link_from_email(email)

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None
        assert not result.is_successful

    @pytest.mark.asyncio
    async def test_full_async_link_extraction_flow(self):
        """测试完整异步链接提取流程"""
        mock_extractor = Mock()
        mock_extractor.extract_link_async = AsyncMock(return_value=ExtractionResult(
            type=ExtractionType.LINK,
            link="https://auth.example.com/email-verification/token123",
            confidence=0.88,
        ))
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<async-link@example.com>",
            from_address="noreply@service.com",
            subject="Email verification",
            received_at=datetime.now(),
            body_text="Please verify your email: https://auth.example.com/email-verification/token123",
        )

        result = await service.extract_link_from_email_async(email, mark_as_processed=True)

        assert result.type == ExtractionType.LINK
        assert "email-verification" in result.link
        assert result.is_successful
        assert email.is_processed


# ============ Story 3.3: 统一提取测试 ============


class TestAiExtractionServiceExtractFromEmailUnified:
    """extract_from_email 统一提取方法测试（同步）"""

    @pytest.fixture
    def mock_extractor(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    @pytest.fixture
    def sample_email(self):
        return Email.create(
            mailbox_id=uuid4(),
            message_id="<unified@example.com>",
            from_address="noreply@example.com",
            subject="Verification",
            received_at=datetime.now(),
            body_text="Your verification code is 123456",
        )

    def test_unified_extract_code_success(self, service, mock_extractor, sample_email):
        """测试统一提取成功提取验证码（AC1）"""
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        mock_extractor.extract.return_value = expected_result

        result = service.unified_extract_from_email(sample_email)

        assert result.type == ExtractionType.CODE
        assert result.code == "123456"
        mock_extractor.extract.assert_called_once_with(sample_email.body)

    def test_unified_extract_link_success(self, service, mock_extractor, sample_email):
        """测试统一提取成功提取验证链接（AC2）"""
        expected_result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://example.com/verify?token=abc",
            confidence=0.9,
        )
        mock_extractor.extract.return_value = expected_result

        result = service.unified_extract_from_email(sample_email)

        assert result.type == ExtractionType.LINK
        assert result.link == "https://example.com/verify?token=abc"

    def test_unified_extract_code_with_backup_link(self, service, mock_extractor, sample_email):
        """测试统一提取验证码带备用链接（AC3）"""
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="789012",
            backup_link="https://example.com/verify?token=xyz",
            confidence=0.92,
        )
        mock_extractor.extract.return_value = expected_result

        result = service.unified_extract_from_email(sample_email)

        assert result.type == ExtractionType.CODE
        assert result.code == "789012"
        assert result.backup_link == "https://example.com/verify?token=xyz"

    def test_unified_extract_unknown(self, service, mock_extractor, sample_email):
        """测试统一提取无验证信息时返回 UNKNOWN（AC4）"""
        expected_result = ExtractionResult(
            type=ExtractionType.UNKNOWN,
            confidence=0.0,
        )
        mock_extractor.extract.return_value = expected_result

        result = service.unified_extract_from_email(sample_email)

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None
        assert result.link is None

    def test_unified_extract_empty_body(self, service, mock_extractor):
        """测试统一提取空邮件正文"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<empty@example.com>",
            from_address="sender@example.com",
            subject="Empty email",
            received_at=datetime.now(),
            body_text=None,
            body_html=None,
        )

        result = service.unified_extract_from_email(email)

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty email body" in result.raw_response
        mock_extractor.extract.assert_not_called()

    def test_unified_extract_mark_as_processed(self, service, mock_extractor, sample_email):
        """测试统一提取 mark_as_processed 功能"""
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        mock_extractor.extract.return_value = expected_result

        assert not sample_email.is_processed
        service.unified_extract_from_email(sample_email, mark_as_processed=True)
        assert sample_email.is_processed

    def test_unified_extract_html_only_email(self, service, mock_extractor):
        """测试统一提取仅 HTML 正文的邮件"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<html@example.com>",
            from_address="sender@example.com",
            subject="HTML email",
            received_at=datetime.now(),
            body_text=None,
            body_html="<html><body>Your code is <b>HTML123</b></body></html>",
        )
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="HTML123",
            confidence=0.9,
        )
        mock_extractor.extract.return_value = expected_result

        result = service.unified_extract_from_email(email)

        assert result.type == ExtractionType.CODE
        assert result.code == "HTML123"
        # 验证使用的是 HTML 内容
        mock_extractor.extract.assert_called_once_with(email.body_html)


class TestAiExtractionServiceUnifiedExtractFromContent:
    """unified_extract_from_content 方法测试（同步）"""

    @pytest.fixture
    def mock_extractor(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    def test_unified_extract_from_content_code_success(self, service, mock_extractor):
        """测试从内容直接提取验证码成功"""
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="CONTENT123",
            confidence=0.9,
        )
        mock_extractor.extract.return_value = expected_result

        result = service.unified_extract_from_content("Your code is CONTENT123")

        assert result.type == ExtractionType.CODE
        assert result.code == "CONTENT123"
        mock_extractor.extract.assert_called_once_with("Your code is CONTENT123")

    def test_unified_extract_from_content_link_success(self, service, mock_extractor):
        """测试从内容直接提取验证链接成功"""
        expected_result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://example.com/verify?token=abc",
            confidence=0.9,
        )
        mock_extractor.extract.return_value = expected_result

        result = service.unified_extract_from_content("Click https://example.com/verify?token=abc")

        assert result.type == ExtractionType.LINK
        assert result.link == "https://example.com/verify?token=abc"

    def test_unified_extract_from_content_empty(self, service, mock_extractor):
        """测试空内容返回 UNKNOWN"""
        result = service.unified_extract_from_content("")

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty content" in result.raw_response
        mock_extractor.extract.assert_not_called()


class TestAiExtractionServiceUnifiedExtractFromContentAsync:
    """unified_extract_from_content_async 方法测试（异步）"""

    @pytest.fixture
    def mock_extractor(self):
        extractor = Mock()
        extractor.extract_async = AsyncMock()
        return extractor

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    @pytest.mark.asyncio
    async def test_unified_extract_from_content_async_success(self, service, mock_extractor):
        """测试异步从内容直接提取成功"""
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="ASYNCCONTENT",
            confidence=0.9,
        )
        mock_extractor.extract_async.return_value = expected_result

        result = await service.unified_extract_from_content_async("Your code is ASYNCCONTENT")

        assert result.type == ExtractionType.CODE
        assert result.code == "ASYNCCONTENT"
        mock_extractor.extract_async.assert_called_once_with("Your code is ASYNCCONTENT")

    @pytest.mark.asyncio
    async def test_unified_extract_from_content_async_empty(self, service, mock_extractor):
        """测试异步空内容返回 UNKNOWN"""
        result = await service.unified_extract_from_content_async("")

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty content" in result.raw_response
        mock_extractor.extract_async.assert_not_called()


class TestAiExtractionServiceExtractFromEmailUnifiedAsync:
    """extract_from_email_async 统一提取方法测试（异步）"""

    @pytest.fixture
    def mock_extractor(self):
        extractor = Mock()
        extractor.extract_async = AsyncMock()
        return extractor

    @pytest.fixture
    def service(self, mock_extractor):
        return AiExtractionService(extractor=mock_extractor)

    @pytest.fixture
    def sample_email(self):
        return Email.create(
            mailbox_id=uuid4(),
            message_id="<async-unified@example.com>",
            from_address="noreply@example.com",
            subject="Async Verification",
            received_at=datetime.now(),
            body_text="Please verify: https://example.com/verify?token=async123",
        )

    @pytest.mark.asyncio
    async def test_unified_extract_async_code_success(self, service, mock_extractor, sample_email):
        """测试异步统一提取成功提取验证码"""
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="ASYNC456",
            confidence=0.92,
        )
        mock_extractor.extract_async.return_value = expected_result

        result = await service.unified_extract_from_email_async(sample_email)

        assert result.type == ExtractionType.CODE
        assert result.code == "ASYNC456"
        mock_extractor.extract_async.assert_called_once_with(sample_email.body)

    @pytest.mark.asyncio
    async def test_unified_extract_async_link_success(self, service, mock_extractor, sample_email):
        """测试异步统一提取成功提取验证链接"""
        expected_result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://example.com/verify?token=async123",
            confidence=0.88,
        )
        mock_extractor.extract_async.return_value = expected_result

        result = await service.unified_extract_from_email_async(sample_email)

        assert result.type == ExtractionType.LINK
        assert result.link == "https://example.com/verify?token=async123"

    @pytest.mark.asyncio
    async def test_unified_extract_async_empty_body(self, service, mock_extractor):
        """测试异步统一提取空邮件正文"""
        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<empty@example.com>",
            from_address="sender@example.com",
            subject="Empty email",
            received_at=datetime.now(),
            body_text=None,
            body_html=None,
        )

        result = await service.unified_extract_from_email_async(email)

        assert result.type == ExtractionType.UNKNOWN
        assert "Empty email body" in result.raw_response
        mock_extractor.extract_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_unified_extract_async_mark_as_processed(self, service, mock_extractor, sample_email):
        """测试异步统一提取 mark_as_processed 功能"""
        expected_result = ExtractionResult(
            type=ExtractionType.CODE,
            code="ASYNC789",
            confidence=0.9,
        )
        mock_extractor.extract_async.return_value = expected_result

        assert not sample_email.is_processed
        await service.unified_extract_from_email_async(sample_email, mark_as_processed=True)
        assert sample_email.is_processed


class TestAiExtractionServiceUnifiedIntegration:
    """统一提取集成测试"""

    def test_unified_extraction_chinese_email(self):
        """测试统一提取流程 - 中文验证码邮件"""
        mock_extractor = Mock()
        mock_extractor.extract.return_value = ExtractionResult(
            type=ExtractionType.CODE,
            code="583921",
            confidence=0.95,
        )
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<chinese@example.com>",
            from_address="noreply@service.cn",
            subject="【验证码】您的验证码",
            received_at=datetime.now(),
            body_text="您的验证码是 583921，5分钟内有效。",
        )

        result = service.unified_extract_from_email(email, mark_as_processed=True)

        assert result.type == ExtractionType.CODE
        assert result.code == "583921"
        assert result.is_successful
        assert email.is_processed

    def test_unified_extraction_code_and_link(self):
        """测试统一提取流程 - 同时包含验证码和链接"""
        mock_extractor = Mock()
        mock_extractor.extract.return_value = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            backup_link="https://example.com/verify?token=xyz789",
            confidence=0.92,
        )
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<both@example.com>",
            from_address="noreply@service.com",
            subject="Verification",
            received_at=datetime.now(),
            body_text="验证码 123456，或点击 https://example.com/verify?token=xyz789",
        )

        result = service.unified_extract_from_email(email)

        assert result.type == ExtractionType.CODE
        assert result.code == "123456"
        assert result.backup_link == "https://example.com/verify?token=xyz789"
        assert result.is_successful

    def test_unified_extraction_no_verification(self):
        """测试统一提取流程 - 无验证信息邮件"""
        mock_extractor = Mock()
        mock_extractor.extract.return_value = ExtractionResult(
            type=ExtractionType.UNKNOWN,
            confidence=0.0,
        )
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<newsletter@example.com>",
            from_address="newsletter@shop.com",
            subject="This week's deals",
            received_at=datetime.now(),
            body_text="Check out our latest products!",
        )

        result = service.unified_extract_from_email(email)

        assert result.type == ExtractionType.UNKNOWN
        assert not result.is_successful

    @pytest.mark.asyncio
    async def test_unified_async_extraction_flow(self):
        """测试完整异步统一提取流程"""
        mock_extractor = Mock()
        mock_extractor.extract_async = AsyncMock(return_value=ExtractionResult(
            type=ExtractionType.LINK,
            link="https://auth.example.com/verify?token=async123",
            confidence=0.88,
        ))
        service = AiExtractionService(extractor=mock_extractor)

        email = Email.create(
            mailbox_id=uuid4(),
            message_id="<async@example.com>",
            from_address="noreply@service.com",
            subject="Email verification",
            received_at=datetime.now(),
            body_text="Please verify: https://auth.example.com/verify?token=async123",
        )

        result = await service.unified_extract_from_email_async(email, mark_as_processed=True)

        assert result.type == ExtractionType.LINK
        assert "auth.example.com" in result.link
        assert result.is_successful
        assert email.is_processed