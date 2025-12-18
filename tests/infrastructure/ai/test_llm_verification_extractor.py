"""LlmVerificationExtractor 单元测试"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from infrastructure.ai.llm_verification_extractor import LlmVerificationExtractor
from domain.ai.value_objects.extraction_type import ExtractionType
from domain.ai.value_objects.extraction_result import ExtractionResult


class TestLlmVerificationExtractorInit:
    """初始化测试"""

    def test_init_with_required_params(self):
        """测试使用必需参数初始化"""
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI"):
            extractor = LlmVerificationExtractor(api_key="test-key")
            assert extractor._api_key == "test-key"
            assert extractor._model == "gpt-4o-mini"  # 默认模型
            assert extractor._api_base == "https://api.openai.com/v1"

    def test_init_with_custom_params(self):
        """测试使用自定义参数初始化"""
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI"):
            extractor = LlmVerificationExtractor(
                api_key="custom-key",
                model="gpt-4",
                api_base="https://custom.api.com/v1",
                timeout=60.0,
                max_retries=5,
            )
            assert extractor._api_key == "custom-key"
            assert extractor._model == "gpt-4"
            assert extractor._api_base == "https://custom.api.com/v1"
            assert extractor._timeout == 60.0
            assert extractor._max_retries == 5

    def test_init_empty_api_key_raises_error(self):
        """测试空 API Key 抛出 ValueError"""
        with pytest.raises(ValueError) as exc_info:
            LlmVerificationExtractor(api_key="")
        assert "OPENAI_API_KEY is required" in str(exc_info.value)

    def test_init_whitespace_api_key_raises_error(self):
        """测试空白 API Key 抛出 ValueError"""
        with pytest.raises(ValueError) as exc_info:
            LlmVerificationExtractor(api_key="   ")
        assert "OPENAI_API_KEY is required" in str(exc_info.value)

    def test_init_none_api_key_raises_error(self):
        """测试 None API Key 抛出 ValueError"""
        with pytest.raises(ValueError) as exc_info:
            LlmVerificationExtractor(api_key=None)  # type: ignore
        assert "OPENAI_API_KEY is required" in str(exc_info.value)


class TestLlmVerificationExtractorParseResponse:
    """响应解析测试"""

    @pytest.fixture
    def extractor(self):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI"):
            return LlmVerificationExtractor(api_key="test-key")

    def test_parse_valid_code_response(self, extractor):
        """测试解析有效的验证码响应"""
        response = '{"found": true, "code": "123456", "confidence": 0.95}'
        result = extractor._parse_response(response)

        assert result.type == ExtractionType.CODE
        assert result.code == "123456"
        assert result.confidence == 0.95
        assert result.raw_response == response

    def test_parse_alphanumeric_code_response(self, extractor):
        """测试解析字母数字混合验证码"""
        response = '{"found": true, "code": "AB12CD", "confidence": 0.9}'
        result = extractor._parse_response(response)

        assert result.type == ExtractionType.CODE
        assert result.code == "AB12CD"

    def test_parse_no_code_found_response(self, extractor):
        """测试解析未找到验证码的响应"""
        response = '{"found": false, "code": null, "confidence": 0.0}'
        result = extractor._parse_response(response)

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None
        assert result.confidence == 0.0

    def test_parse_response_with_extra_text(self, extractor):
        """测试解析带有额外文字的响应"""
        response = '''Here is the result:
{"found": true, "code": "583921", "confidence": 0.85}
The code was found in the email body.'''
        result = extractor._parse_response(response)

        assert result.type == ExtractionType.CODE
        assert result.code == "583921"
        assert result.confidence == 0.85

    def test_parse_invalid_json_response(self, extractor):
        """测试解析无效 JSON 响应"""
        response = "This is not valid JSON"
        result = extractor._parse_response(response)

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None
        assert result.raw_response == response

    def test_parse_empty_response(self, extractor):
        """测试解析空响应"""
        response = ""
        result = extractor._parse_response(response)

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None

    def test_parse_response_missing_confidence(self, extractor):
        """测试解析缺少 confidence 字段的响应"""
        response = '{"found": true, "code": "123456"}'
        result = extractor._parse_response(response)

        assert result.type == ExtractionType.CODE
        assert result.code == "123456"
        assert result.confidence == 0.9  # 默认值


class TestLlmVerificationExtractorPrompt:
    """Prompt 生成测试"""

    @pytest.fixture
    def extractor(self):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI"):
            return LlmVerificationExtractor(api_key="test-key")

    def test_prompt_template_exists(self, extractor):
        """测试 Prompt 模板存在"""
        assert hasattr(extractor, "PROMPT_TEMPLATE")
        assert "{content}" in extractor.PROMPT_TEMPLATE

    def test_prompt_includes_json_format_instruction(self, extractor):
        """测试 Prompt 包含 JSON 格式说明"""
        assert "JSON" in extractor.PROMPT_TEMPLATE
        assert "found" in extractor.PROMPT_TEMPLATE
        assert "code" in extractor.PROMPT_TEMPLATE
        assert "confidence" in extractor.PROMPT_TEMPLATE


class TestLlmVerificationExtractorExtractCode:
    """extract_code 方法测试（同步）"""

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        return mock

    @pytest.fixture
    def extractor(self, mock_llm):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI", return_value=mock_llm):
            ext = LlmVerificationExtractor(api_key="test-key")
            ext._llm = mock_llm
            return ext

    def test_extract_code_success(self, extractor, mock_llm):
        """测试成功提取验证码"""
        mock_response = MagicMock()
        mock_response.content = '{"found": true, "code": "AB12CD", "confidence": 0.9}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract_code("Your verification code is AB12CD")

        assert result.type == ExtractionType.CODE
        assert result.code == "AB12CD"
        mock_llm.invoke.assert_called_once()

    def test_extract_code_not_found(self, extractor, mock_llm):
        """测试未找到验证码"""
        mock_response = MagicMock()
        mock_response.content = '{"found": false, "code": null, "confidence": 0.0}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract_code("This is a regular email without code")

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None

    def test_extract_code_llm_error(self, extractor, mock_llm):
        """测试 LLM 调用失败时优雅降级"""
        mock_llm.invoke.side_effect = Exception("API Error")

        result = extractor.extract_code("Some email content")

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None
        assert "API Error" in result.raw_response

    def test_extract_code_truncates_long_content(self, extractor, mock_llm):
        """测试长内容被截断"""
        mock_response = MagicMock()
        mock_response.content = '{"found": false, "code": null, "confidence": 0.0}'
        mock_llm.invoke.return_value = mock_response
        long_content = "x" * 10000

        extractor.extract_code(long_content)

        # 验证传给 LLM 的内容被截断（通过检查调用参数）
        call_args = mock_llm.invoke.call_args[0][0]
        # HumanMessage 的 content 应该包含截断后的内容
        assert len(call_args[0].content) < len(long_content) + 500


class TestLlmVerificationExtractorExtractCodeAsync:
    """extract_code_async 方法测试（异步）"""

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        mock.ainvoke = AsyncMock()
        return mock

    @pytest.fixture
    def extractor(self, mock_llm):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI", return_value=mock_llm):
            ext = LlmVerificationExtractor(api_key="test-key")
            ext._llm = mock_llm
            return ext

    @pytest.mark.asyncio
    async def test_extract_code_async_success(self, extractor, mock_llm):
        """测试异步成功提取验证码"""
        mock_response = MagicMock()
        mock_response.content = '{"found": true, "code": "ASYNC123", "confidence": 0.95}'
        mock_llm.ainvoke.return_value = mock_response

        result = await extractor.extract_code_async("Your code is ASYNC123")

        assert result.type == ExtractionType.CODE
        assert result.code == "ASYNC123"
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_code_async_not_found(self, extractor, mock_llm):
        """测试异步未找到验证码"""
        mock_response = MagicMock()
        mock_response.content = '{"found": false, "code": null, "confidence": 0.0}'
        mock_llm.ainvoke.return_value = mock_response

        result = await extractor.extract_code_async("Regular email")

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None

    @pytest.mark.asyncio
    async def test_extract_code_async_error(self, extractor, mock_llm):
        """测试异步 LLM 调用失败时优雅降级"""
        mock_llm.ainvoke.side_effect = Exception("Async API Error")

        result = await extractor.extract_code_async("Content")

        assert result.type == ExtractionType.UNKNOWN
        assert "Async API Error" in result.raw_response


class TestLlmVerificationExtractorIntegration:
    """集成测试 - Mock LLM 响应验证完整提取流程"""

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        mock.ainvoke = AsyncMock()
        return mock

    @pytest.fixture
    def extractor(self, mock_llm):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI", return_value=mock_llm):
            ext = LlmVerificationExtractor(api_key="test-key")
            ext._llm = mock_llm
            return ext

    def test_full_extraction_flow_numeric_code(self, extractor, mock_llm):
        """测试完整提取流程 - 纯数字验证码"""
        mock_response = MagicMock()
        mock_response.content = '{"found": true, "code": "583921", "confidence": 0.95}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract_code("您的验证码是 583921，5分钟内有效")

        assert result.type == ExtractionType.CODE
        assert result.code == "583921"
        assert result.confidence == 0.95
        assert result.is_successful

    def test_full_extraction_flow_html_email(self, extractor, mock_llm):
        """测试完整提取流程 - HTML 邮件"""
        html_content = """
        <html>
        <body>
            <p>您好，</p>
            <p>您的验证码是：<strong>AB12CD</strong></p>
            <p>请勿将验证码告诉他人。</p>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.content = '{"found": true, "code": "AB12CD", "confidence": 0.9}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract_code(html_content)

        assert result.type == ExtractionType.CODE
        assert result.code == "AB12CD"

    def test_full_extraction_flow_no_code(self, extractor, mock_llm):
        """测试完整提取流程 - 无验证码邮件"""
        mock_response = MagicMock()
        mock_response.content = '{"found": false, "code": null, "confidence": 0.0}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract_code("感谢您的购买，订单已发货。")

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None
        assert not result.is_successful

    @pytest.mark.asyncio
    async def test_full_async_extraction_flow(self, extractor, mock_llm):
        """测试完整异步提取流程"""
        mock_response = MagicMock()
        mock_response.content = '{"found": true, "code": "ASYNCTEST", "confidence": 0.92}'
        mock_llm.ainvoke.return_value = mock_response

        result = await extractor.extract_code_async("Your async code: ASYNCTEST")

        assert result.type == ExtractionType.CODE
        assert result.code == "ASYNCTEST"
        assert result.confidence == 0.92
        assert result.is_successful


# ============ Story 3.2: 链接提取测试 ============


class TestLlmVerificationExtractorParseLinkResponse:
    """链接响应解析测试"""

    @pytest.fixture
    def extractor(self):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI"):
            return LlmVerificationExtractor(api_key="test-key")

    def test_parse_valid_link_response(self, extractor):
        """测试解析有效的验证链接响应"""
        response = '{"found": true, "link": "https://claude.ai/verify?token=abc123", "confidence": 0.95}'
        result = extractor._parse_link_response(response)

        assert result.type == ExtractionType.LINK
        assert result.link == "https://claude.ai/verify?token=abc123"
        assert result.confidence == 0.95
        assert result.raw_response == response

    def test_parse_link_with_query_params(self, extractor):
        """测试解析带查询参数的验证链接"""
        response = '{"found": true, "link": "https://accounts.google.com/signin/v2/challenge?key=xxx&redirect=https://example.com", "confidence": 0.9}'
        result = extractor._parse_link_response(response)

        assert result.type == ExtractionType.LINK
        assert "accounts.google.com" in result.link
        assert "key=xxx" in result.link

    def test_parse_no_link_found_response(self, extractor):
        """测试解析未找到验证链接的响应"""
        response = '{"found": false, "link": null, "confidence": 0.0}'
        result = extractor._parse_link_response(response)

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None
        assert result.confidence == 0.0

    def test_parse_link_response_with_extra_text(self, extractor):
        """测试解析带有额外文字的响应"""
        response = '''Here is the result:
{"found": true, "link": "https://auth.example.com/email-verification/token123", "confidence": 0.88}
The link was found in the email body.'''
        result = extractor._parse_link_response(response)

        assert result.type == ExtractionType.LINK
        assert result.link == "https://auth.example.com/email-verification/token123"
        assert result.confidence == 0.88

    def test_parse_invalid_url_format(self, extractor):
        """测试解析无效 URL 格式"""
        response = '{"found": true, "link": "not-a-valid-url", "confidence": 0.5}'
        result = extractor._parse_link_response(response)

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None

    def test_parse_empty_link_response(self, extractor):
        """测试解析空响应 (M3)"""
        response = ""
        result = extractor._parse_link_response(response)

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None

    def test_parse_empty_link_string(self, extractor):
        """测试解析空链接字符串 (H3)"""
        response = '{"found": true, "link": "", "confidence": 0.9}'
        result = extractor._parse_link_response(response)

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None

    def test_parse_whitespace_link_string(self, extractor):
        """测试解析空白链接字符串 (H3)"""
        response = '{"found": true, "link": "   ", "confidence": 0.9}'
        result = extractor._parse_link_response(response)

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None

    def test_parse_url_without_domain(self, extractor):
        """测试解析无域名 URL (M1)"""
        response = '{"found": true, "link": "https://", "confidence": 0.9}'
        result = extractor._parse_link_response(response)

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None

    def test_parse_url_with_port(self, extractor):
        """测试解析带端口号的 URL"""
        response = '{"found": true, "link": "https://example.com:8080/verify?token=abc", "confidence": 0.9}'
        result = extractor._parse_link_response(response)

        assert result.type == ExtractionType.LINK
        assert result.link == "https://example.com:8080/verify?token=abc"

    def test_parse_link_response_missing_confidence(self, extractor):
        """测试解析缺少 confidence 字段的响应"""
        response = '{"found": true, "link": "https://verify.example.com/token"}'
        result = extractor._parse_link_response(response)

        assert result.type == ExtractionType.LINK
        assert result.link == "https://verify.example.com/token"
        assert result.confidence == 0.9  # 默认值


class TestLlmVerificationExtractorLinkPrompt:
    """链接 Prompt 模板测试"""

    @pytest.fixture
    def extractor(self):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI"):
            return LlmVerificationExtractor(api_key="test-key")

    def test_link_prompt_template_exists(self, extractor):
        """测试链接 Prompt 模板存在"""
        assert hasattr(extractor, "LINK_PROMPT_TEMPLATE")
        assert "{content}" in extractor.LINK_PROMPT_TEMPLATE

    def test_link_prompt_includes_json_format(self, extractor):
        """测试链接 Prompt 包含 JSON 格式说明"""
        assert "JSON" in extractor.LINK_PROMPT_TEMPLATE
        assert "found" in extractor.LINK_PROMPT_TEMPLATE
        assert "link" in extractor.LINK_PROMPT_TEMPLATE
        assert "confidence" in extractor.LINK_PROMPT_TEMPLATE

    def test_link_prompt_includes_verification_rules(self, extractor):
        """测试链接 Prompt 包含验证规则"""
        assert "verify" in extractor.LINK_PROMPT_TEMPLATE.lower()
        assert "confirm" in extractor.LINK_PROMPT_TEMPLATE.lower()
        assert "token" in extractor.LINK_PROMPT_TEMPLATE.lower()

    def test_link_prompt_includes_exclusion_rules(self, extractor):
        """测试链接 Prompt 包含排除规则"""
        assert "unsubscribe" in extractor.LINK_PROMPT_TEMPLATE.lower()
        assert "facebook" in extractor.LINK_PROMPT_TEMPLATE.lower()


class TestLlmVerificationExtractorExtractLink:
    """extract_link 方法测试（同步）"""

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        return mock

    @pytest.fixture
    def extractor(self, mock_llm):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI", return_value=mock_llm):
            ext = LlmVerificationExtractor(api_key="test-key")
            ext._llm = mock_llm
            return ext

    def test_extract_link_success(self, extractor, mock_llm):
        """测试成功提取验证链接"""
        mock_response = MagicMock()
        mock_response.content = '{"found": true, "link": "https://claude.ai/verify?token=abc123", "confidence": 0.95}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract_link("Please click the link to verify your email")

        assert result.type == ExtractionType.LINK
        assert result.link == "https://claude.ai/verify?token=abc123"
        mock_llm.invoke.assert_called_once()

    def test_extract_link_not_found(self, extractor, mock_llm):
        """测试未找到验证链接"""
        mock_response = MagicMock()
        mock_response.content = '{"found": false, "link": null, "confidence": 0.0}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract_link("This is a regular email without verification link")

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None

    def test_extract_link_llm_error(self, extractor, mock_llm):
        """测试 LLM 调用失败时优雅降级"""
        mock_llm.invoke.side_effect = Exception("API Error")

        result = extractor.extract_link("Some email content")

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None
        assert "API Error" in result.raw_response

    def test_extract_link_from_html_email(self, extractor, mock_llm):
        """测试从 HTML 邮件提取链接"""
        html_content = """
        <html>
        <body>
            <p>Please verify your email:</p>
            <a href="https://example.com/verify?token=xyz">Click here</a>
        </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.content = '{"found": true, "link": "https://example.com/verify?token=xyz", "confidence": 0.92}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract_link(html_content)

        assert result.type == ExtractionType.LINK
        assert "verify?token=xyz" in result.link

    def test_extract_link_truncates_long_content(self, extractor, mock_llm):
        """测试长内容被截断 (H1)"""
        mock_response = MagicMock()
        mock_response.content = '{"found": false, "link": null, "confidence": 0.0}'
        mock_llm.invoke.return_value = mock_response
        long_content = "x" * 10000

        extractor.extract_link(long_content)

        # 验证传给 LLM 的内容被截断（通过检查调用参数）
        call_args = mock_llm.invoke.call_args[0][0]
        # HumanMessage 的 content 应该包含截断后的内容
        assert len(call_args[0].content) < len(long_content) + 500


class TestLlmVerificationExtractorExtractLinkAsync:
    """extract_link_async 方法测试（异步）"""

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        mock.ainvoke = AsyncMock()
        return mock

    @pytest.fixture
    def extractor(self, mock_llm):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI", return_value=mock_llm):
            ext = LlmVerificationExtractor(api_key="test-key")
            ext._llm = mock_llm
            return ext

    @pytest.mark.asyncio
    async def test_extract_link_async_success(self, extractor, mock_llm):
        """测试异步成功提取验证链接"""
        mock_response = MagicMock()
        mock_response.content = '{"found": true, "link": "https://verify.example.com/token123", "confidence": 0.9}'
        mock_llm.ainvoke.return_value = mock_response

        result = await extractor.extract_link_async("Please verify your email by clicking the link")

        assert result.type == ExtractionType.LINK
        assert result.link == "https://verify.example.com/token123"
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_link_async_not_found(self, extractor, mock_llm):
        """测试异步未找到验证链接"""
        mock_response = MagicMock()
        mock_response.content = '{"found": false, "link": null, "confidence": 0.0}'
        mock_llm.ainvoke.return_value = mock_response

        result = await extractor.extract_link_async("Regular newsletter email")

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None

    @pytest.mark.asyncio
    async def test_extract_link_async_error(self, extractor, mock_llm):
        """测试异步 LLM 调用失败时优雅降级"""
        mock_llm.ainvoke.side_effect = Exception("Async API Error")

        result = await extractor.extract_link_async("Content")

        assert result.type == ExtractionType.UNKNOWN
        assert "Async API Error" in result.raw_response


class TestLlmVerificationExtractorLinkIntegration:
    """链接提取集成测试"""

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        mock.ainvoke = AsyncMock()
        return mock

    @pytest.fixture
    def extractor(self, mock_llm):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI", return_value=mock_llm):
            ext = LlmVerificationExtractor(api_key="test-key")
            ext._llm = mock_llm
            return ext

    def test_full_link_extraction_flow(self, extractor, mock_llm):
        """测试完整链接提取流程"""
        mock_response = MagicMock()
        mock_response.content = '{"found": true, "link": "https://claude.ai/verify?token=abc123def456", "confidence": 0.95}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract_link("请点击以下链接验证您的邮箱：https://claude.ai/verify?token=abc123def456")

        assert result.type == ExtractionType.LINK
        assert result.link == "https://claude.ai/verify?token=abc123def456"
        assert result.confidence == 0.95
        assert result.is_successful

    def test_full_link_extraction_multiple_links(self, extractor, mock_llm):
        """测试多链接场景智能识别"""
        mock_response = MagicMock()
        mock_response.content = '{"found": true, "link": "https://auth.example.com/email-verification/token123", "confidence": 0.92}'
        mock_llm.invoke.return_value = mock_response

        email_content = """
        点击验证: https://auth.example.com/email-verification/token123
        退订: https://example.com/unsubscribe
        关注我们: https://facebook.com/example
        """
        result = extractor.extract_link(email_content)

        assert result.type == ExtractionType.LINK
        assert "email-verification" in result.link
        assert "unsubscribe" not in result.link
        assert "facebook" not in result.link

    def test_full_link_extraction_no_verification_link(self, extractor, mock_llm):
        """测试无验证链接邮件"""
        mock_response = MagicMock()
        mock_response.content = '{"found": false, "link": null, "confidence": 0.0}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract_link("感谢您的购买，订单已发货。查看订单详情请访问我们的网站。")

        assert result.type == ExtractionType.UNKNOWN
        assert result.link is None
        assert not result.is_successful

    @pytest.mark.asyncio
    async def test_full_async_link_extraction_flow(self, extractor, mock_llm):
        """测试完整异步链接提取流程"""
        mock_response = MagicMock()
        mock_response.content = '{"found": true, "link": "https://accounts.google.com/signin/v2/challenge/key=xyz", "confidence": 0.88}'
        mock_llm.ainvoke.return_value = mock_response

        result = await extractor.extract_link_async("Verify your Google account by clicking the link below")

        assert result.type == ExtractionType.LINK
        assert "accounts.google.com" in result.link
        assert result.is_successful


# ============ Story 3.3: 统一提取测试 ============


class TestLlmVerificationExtractorUnifiedPrompt:
    """统一 Prompt 模板测试"""

    @pytest.fixture
    def extractor(self):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI"):
            return LlmVerificationExtractor(api_key="test-key")

    def test_unified_prompt_template_exists(self, extractor):
        """测试统一 Prompt 模板存在"""
        assert hasattr(extractor, "UNIFIED_PROMPT_TEMPLATE")
        assert "{content}" in extractor.UNIFIED_PROMPT_TEMPLATE

    def test_unified_prompt_includes_json_format(self, extractor):
        """测试统一 Prompt 包含 JSON 格式说明"""
        assert "JSON" in extractor.UNIFIED_PROMPT_TEMPLATE
        assert "type" in extractor.UNIFIED_PROMPT_TEMPLATE
        assert "code" in extractor.UNIFIED_PROMPT_TEMPLATE
        assert "link" in extractor.UNIFIED_PROMPT_TEMPLATE
        assert "backup_link" in extractor.UNIFIED_PROMPT_TEMPLATE
        assert "confidence" in extractor.UNIFIED_PROMPT_TEMPLATE

    def test_unified_prompt_includes_type_options(self, extractor):
        """测试统一 Prompt 包含类型选项"""
        prompt = extractor.UNIFIED_PROMPT_TEMPLATE.lower()
        assert '"code"' in prompt or "'code'" in prompt
        assert '"link"' in prompt or "'link'" in prompt
        assert '"unknown"' in prompt or "'unknown'" in prompt

    def test_unified_prompt_includes_priority_rules(self, extractor):
        """测试统一 Prompt 包含优先级规则"""
        prompt = extractor.UNIFIED_PROMPT_TEMPLATE
        # 应该提到同时存在时验证码优先
        assert "优先" in prompt or "priority" in prompt.lower()


class TestLlmVerificationExtractorParseUnifiedResponse:
    """统一响应解析测试"""

    @pytest.fixture
    def extractor(self):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI"):
            return LlmVerificationExtractor(api_key="test-key")

    def test_parse_code_only_response(self, extractor):
        """测试解析仅验证码响应"""
        response = '{"type": "code", "code": "123456", "link": null, "backup_link": null, "confidence": 0.95}'
        result = extractor._parse_unified_response(response)

        assert result.type == ExtractionType.CODE
        assert result.code == "123456"
        assert result.link is None
        assert result.backup_link is None
        assert result.confidence == 0.95

    def test_parse_link_only_response(self, extractor):
        """测试解析仅验证链接响应"""
        response = '{"type": "link", "code": null, "link": "https://example.com/verify?token=abc", "backup_link": null, "confidence": 0.9}'
        result = extractor._parse_unified_response(response)

        assert result.type == ExtractionType.LINK
        assert result.code is None
        assert result.link == "https://example.com/verify?token=abc"
        assert result.backup_link is None

    def test_parse_code_with_backup_link_response(self, extractor):
        """测试解析验证码带备用链接响应（AC3）"""
        response = '{"type": "code", "code": "789012", "link": null, "backup_link": "https://example.com/verify?token=xyz", "confidence": 0.92}'
        result = extractor._parse_unified_response(response)

        assert result.type == ExtractionType.CODE
        assert result.code == "789012"
        assert result.link is None
        assert result.backup_link == "https://example.com/verify?token=xyz"

    def test_parse_unknown_response(self, extractor):
        """测试解析无验证信息响应（AC4）"""
        response = '{"type": "unknown", "code": null, "link": null, "backup_link": null, "confidence": 0.0}'
        result = extractor._parse_unified_response(response)

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None
        assert result.link is None
        assert result.backup_link is None

    def test_parse_response_with_extra_text(self, extractor):
        """测试解析带有额外文字的响应"""
        response = '''Here is the analysis:
{"type": "code", "code": "ABCD12", "link": null, "backup_link": null, "confidence": 0.88}
This appears to be a verification code.'''
        result = extractor._parse_unified_response(response)

        assert result.type == ExtractionType.CODE
        assert result.code == "ABCD12"

    def test_parse_invalid_json_response(self, extractor):
        """测试解析无效 JSON 响应"""
        response = "This is not valid JSON"
        result = extractor._parse_unified_response(response)

        assert result.type == ExtractionType.UNKNOWN

    def test_parse_empty_response(self, extractor):
        """测试解析空响应"""
        response = ""
        result = extractor._parse_unified_response(response)

        assert result.type == ExtractionType.UNKNOWN

    def test_parse_invalid_link_format(self, extractor):
        """测试解析无效链接格式"""
        response = '{"type": "link", "code": null, "link": "not-a-valid-url", "backup_link": null, "confidence": 0.5}'
        result = extractor._parse_unified_response(response)

        assert result.type == ExtractionType.UNKNOWN

    def test_parse_invalid_backup_link_format(self, extractor):
        """测试解析无效备用链接格式"""
        response = '{"type": "code", "code": "123456", "link": null, "backup_link": "invalid-url", "confidence": 0.9}'
        result = extractor._parse_unified_response(response)

        assert result.type == ExtractionType.CODE
        assert result.code == "123456"
        assert result.backup_link is None  # 无效链接应被过滤

    def test_parse_missing_confidence(self, extractor):
        """测试解析缺少 confidence 字段的响应"""
        response = '{"type": "code", "code": "999888"}'
        result = extractor._parse_unified_response(response)

        assert result.type == ExtractionType.CODE
        assert result.code == "999888"
        assert result.confidence == 0.9  # 默认值

    def test_parse_uppercase_type(self, extractor):
        """测试解析大写类型"""
        response = '{"type": "CODE", "code": "ABC123", "link": null, "backup_link": null, "confidence": 0.9}'
        result = extractor._parse_unified_response(response)

        assert result.type == ExtractionType.CODE
        assert result.code == "ABC123"


class TestLlmVerificationExtractorExtract:
    """extract 方法测试（同步）"""

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        return mock

    @pytest.fixture
    def extractor(self, mock_llm):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI", return_value=mock_llm):
            ext = LlmVerificationExtractor(api_key="test-key")
            ext._llm = mock_llm
            return ext

    def test_extract_code_success(self, extractor, mock_llm):
        """测试成功提取验证码（AC1）"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "code", "code": "123456", "link": null, "backup_link": null, "confidence": 0.95}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract("您的验证码是 123456")

        assert result.type == ExtractionType.CODE
        assert result.code == "123456"
        mock_llm.invoke.assert_called_once()

    def test_extract_link_success(self, extractor, mock_llm):
        """测试成功提取验证链接（AC2）"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "link", "code": null, "link": "https://example.com/verify?token=abc", "backup_link": null, "confidence": 0.9}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract("请点击链接验证：https://example.com/verify?token=abc")

        assert result.type == ExtractionType.LINK
        assert result.link == "https://example.com/verify?token=abc"

    def test_extract_code_with_backup_link(self, extractor, mock_llm):
        """测试同时存在时优先返回验证码并带备用链接（AC3）"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "code", "code": "789012", "link": null, "backup_link": "https://example.com/verify?token=xyz", "confidence": 0.92}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract("验证码 789012，或点击 https://example.com/verify?token=xyz")

        assert result.type == ExtractionType.CODE
        assert result.code == "789012"
        assert result.backup_link == "https://example.com/verify?token=xyz"

    def test_extract_unknown(self, extractor, mock_llm):
        """测试无验证信息时返回 UNKNOWN（AC4）"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "unknown", "code": null, "link": null, "backup_link": null, "confidence": 0.0}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract("欢迎订阅我们的新闻通讯")

        assert result.type == ExtractionType.UNKNOWN
        assert result.code is None
        assert result.link is None

    def test_extract_llm_error(self, extractor, mock_llm):
        """测试 LLM 调用失败时优雅降级"""
        mock_llm.invoke.side_effect = Exception("API Error")

        result = extractor.extract("Some email content")

        assert result.type == ExtractionType.UNKNOWN
        assert "API Error" in result.raw_response

    def test_extract_truncates_long_content(self, extractor, mock_llm):
        """测试长内容被截断"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "unknown", "code": null, "link": null, "backup_link": null, "confidence": 0.0}'
        mock_llm.invoke.return_value = mock_response
        long_content = "x" * 10000

        extractor.extract(long_content)

        call_args = mock_llm.invoke.call_args[0][0]
        assert len(call_args[0].content) < len(long_content) + 500


class TestLlmVerificationExtractorExtractAsync:
    """extract_async 方法测试（异步）"""

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        mock.ainvoke = AsyncMock()
        return mock

    @pytest.fixture
    def extractor(self, mock_llm):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI", return_value=mock_llm):
            ext = LlmVerificationExtractor(api_key="test-key")
            ext._llm = mock_llm
            return ext

    @pytest.mark.asyncio
    async def test_extract_async_code_success(self, extractor, mock_llm):
        """测试异步成功提取验证码"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "code", "code": "ASYNC123", "link": null, "backup_link": null, "confidence": 0.95}'
        mock_llm.ainvoke.return_value = mock_response

        result = await extractor.extract_async("Your code is ASYNC123")

        assert result.type == ExtractionType.CODE
        assert result.code == "ASYNC123"
        mock_llm.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_async_link_success(self, extractor, mock_llm):
        """测试异步成功提取验证链接"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "link", "code": null, "link": "https://verify.example.com/token", "backup_link": null, "confidence": 0.9}'
        mock_llm.ainvoke.return_value = mock_response

        result = await extractor.extract_async("Click to verify: https://verify.example.com/token")

        assert result.type == ExtractionType.LINK
        assert result.link == "https://verify.example.com/token"

    @pytest.mark.asyncio
    async def test_extract_async_code_with_backup_link(self, extractor, mock_llm):
        """测试异步同时存在时优先返回验证码并带备用链接"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "code", "code": "ABC789", "link": null, "backup_link": "https://example.com/alt-verify", "confidence": 0.88}'
        mock_llm.ainvoke.return_value = mock_response

        result = await extractor.extract_async("Code: ABC789 or click https://example.com/alt-verify")

        assert result.type == ExtractionType.CODE
        assert result.code == "ABC789"
        assert result.backup_link == "https://example.com/alt-verify"

    @pytest.mark.asyncio
    async def test_extract_async_unknown(self, extractor, mock_llm):
        """测试异步无验证信息时返回 UNKNOWN"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "unknown", "code": null, "link": null, "backup_link": null, "confidence": 0.0}'
        mock_llm.ainvoke.return_value = mock_response

        result = await extractor.extract_async("Regular newsletter content")

        assert result.type == ExtractionType.UNKNOWN

    @pytest.mark.asyncio
    async def test_extract_async_error(self, extractor, mock_llm):
        """测试异步 LLM 调用失败时优雅降级"""
        mock_llm.ainvoke.side_effect = Exception("Async API Error")

        result = await extractor.extract_async("Content")

        assert result.type == ExtractionType.UNKNOWN
        assert "Async API Error" in result.raw_response


class TestLlmVerificationExtractorUnifiedIntegration:
    """统一提取集成测试"""

    @pytest.fixture
    def mock_llm(self):
        mock = MagicMock()
        mock.ainvoke = AsyncMock()
        return mock

    @pytest.fixture
    def extractor(self, mock_llm):
        with patch("infrastructure.ai.llm_verification_extractor.ChatOpenAI", return_value=mock_llm):
            ext = LlmVerificationExtractor(api_key="test-key")
            ext._llm = mock_llm
            return ext

    def test_full_unified_extraction_code_chinese(self, extractor, mock_llm):
        """测试完整统一提取流程 - 中文验证码邮件"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "code", "code": "583921", "link": null, "backup_link": null, "confidence": 0.95}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract("您的验证码是 583921，5分钟内有效。")

        assert result.type == ExtractionType.CODE
        assert result.code == "583921"
        assert result.is_successful

    def test_full_unified_extraction_link_english(self, extractor, mock_llm):
        """测试完整统一提取流程 - 英文验证链接邮件"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "link", "code": null, "link": "https://accounts.google.com/verify?token=abc123", "backup_link": null, "confidence": 0.9}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract("Please verify your account by clicking: https://accounts.google.com/verify?token=abc123")

        assert result.type == ExtractionType.LINK
        assert "accounts.google.com" in result.link
        assert result.is_successful

    def test_full_unified_extraction_code_and_link(self, extractor, mock_llm):
        """测试完整统一提取流程 - 同时包含验证码和链接"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "code", "code": "123456", "link": null, "backup_link": "https://example.com/verify?token=xyz789", "confidence": 0.92}'
        mock_llm.invoke.return_value = mock_response

        content = """
        您的验证码是 123456。
        如果验证码输入不便，也可以点击以下链接完成验证：
        https://example.com/verify?token=xyz789
        """
        result = extractor.extract(content)

        assert result.type == ExtractionType.CODE
        assert result.code == "123456"
        assert result.backup_link == "https://example.com/verify?token=xyz789"
        assert result.is_successful

    def test_full_unified_extraction_no_verification(self, extractor, mock_llm):
        """测试完整统一提取流程 - 无验证信息邮件"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "unknown", "code": null, "link": null, "backup_link": null, "confidence": 0.0}'
        mock_llm.invoke.return_value = mock_response

        result = extractor.extract("欢迎订阅我们的新闻通讯！查看最新优惠请访问 https://shop.com/deals")

        assert result.type == ExtractionType.UNKNOWN
        assert not result.is_successful

    @pytest.mark.asyncio
    async def test_full_async_unified_extraction(self, extractor, mock_llm):
        """测试完整异步统一提取流程"""
        mock_response = MagicMock()
        mock_response.content = '{"type": "code", "code": "ASYNCTEST", "link": null, "backup_link": null, "confidence": 0.88}'
        mock_llm.ainvoke.return_value = mock_response

        result = await extractor.extract_async("Your verification code is ASYNCTEST")

        assert result.type == ExtractionType.CODE
        assert result.code == "ASYNCTEST"
        assert result.is_successful
