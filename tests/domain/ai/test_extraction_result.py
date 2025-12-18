"""ExtractionResult 值对象单元测试"""

import pytest
from domain.ai.value_objects.extraction_result import ExtractionResult
from domain.ai.value_objects.extraction_type import ExtractionType


class TestExtractionType:
    """ExtractionType 枚举测试"""

    def test_code_type_value(self):
        """测试 CODE 类型值"""
        assert ExtractionType.CODE == "code"
        assert ExtractionType.CODE.value == "code"

    def test_link_type_value(self):
        """测试 LINK 类型值"""
        assert ExtractionType.LINK == "link"
        assert ExtractionType.LINK.value == "link"

    def test_unknown_type_value(self):
        """测试 UNKNOWN 类型值"""
        assert ExtractionType.UNKNOWN == "unknown"
        assert ExtractionType.UNKNOWN.value == "unknown"

    def test_enum_is_string(self):
        """测试枚举值可作为字符串使用"""
        # str(Enum) 返回 "EnumName.VALUE" 格式，但 .value 返回实际值
        assert ExtractionType.CODE.value == "code"
        # 继承 str 使得在字符串比较时可用
        assert ExtractionType.CODE == "code"
        assert ExtractionType.LINK == "link"


class TestExtractionResult:
    """ExtractionResult 值对象测试"""

    def test_successful_code_extraction(self):
        """测试成功提取验证码"""
        result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        assert result.is_successful
        assert result.value == "123456"
        assert result.code == "123456"
        assert result.link is None
        assert result.confidence == 0.95

    def test_successful_link_extraction(self):
        """测试成功提取验证链接"""
        result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://example.com/verify?token=abc",
            confidence=0.9,
        )
        assert result.is_successful
        assert result.value == "https://example.com/verify?token=abc"
        assert result.link == "https://example.com/verify?token=abc"
        assert result.code is None

    def test_unknown_type_not_successful(self):
        """测试 UNKNOWN 类型不算成功"""
        result = ExtractionResult(type=ExtractionType.UNKNOWN)
        assert not result.is_successful
        assert result.value is None
        assert result.confidence == 0.0

    def test_code_type_without_code_not_successful(self):
        """测试 CODE 类型但无 code 值不算成功"""
        result = ExtractionResult(
            type=ExtractionType.CODE,
            code=None,
            confidence=0.5,
        )
        assert not result.is_successful

    def test_value_property_prefers_code_over_link(self):
        """测试 value 属性优先返回 code"""
        result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            link="https://example.com",
            confidence=0.9,
        )
        assert result.value == "123456"

    def test_value_property_returns_link_when_no_code(self):
        """测试无 code 时 value 返回 link"""
        result = ExtractionResult(
            type=ExtractionType.LINK,
            code=None,
            link="https://example.com",
            confidence=0.9,
        )
        assert result.value == "https://example.com"

    def test_raw_response_storage(self):
        """测试存储原始 LLM 响应"""
        raw = '{"found": true, "code": "123456"}'
        result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
            raw_response=raw,
        )
        assert result.raw_response == raw

    def test_immutability(self):
        """测试值对象不可变性"""
        result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        with pytest.raises(AttributeError):
            result.code = "654321"

    def test_equality(self):
        """测试值对象相等性"""
        result1 = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        result2 = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            confidence=0.95,
        )
        assert result1 == result2

    def test_default_values(self):
        """测试默认值"""
        result = ExtractionResult(type=ExtractionType.UNKNOWN)
        assert result.code is None
        assert result.link is None
        assert result.confidence == 0.0
        assert result.raw_response is None


# ============ Story 3.3: backup_link 字段测试 ============


class TestExtractionResultBackupLink:
    """backup_link 字段测试（Story 3.3）"""

    def test_backup_link_default_none(self):
        """测试 backup_link 默认值为 None"""
        result = ExtractionResult(type=ExtractionType.CODE, code="123456")
        assert result.backup_link is None

    def test_backup_link_with_code_type(self):
        """测试 CODE 类型带 backup_link"""
        result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            backup_link="https://example.com/verify?token=abc",
            confidence=0.95,
        )
        assert result.type == ExtractionType.CODE
        assert result.code == "123456"
        assert result.backup_link == "https://example.com/verify?token=abc"
        assert result.is_successful

    def test_backup_link_with_link_type(self):
        """测试 LINK 类型时 backup_link 通常为 None"""
        result = ExtractionResult(
            type=ExtractionType.LINK,
            link="https://example.com/verify?token=abc",
            backup_link=None,
            confidence=0.9,
        )
        assert result.type == ExtractionType.LINK
        assert result.link == "https://example.com/verify?token=abc"
        assert result.backup_link is None
        assert result.is_successful

    def test_backup_link_equality(self):
        """测试带 backup_link 的相等性比较"""
        result1 = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            backup_link="https://example.com/verify",
            confidence=0.9,
        )
        result2 = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            backup_link="https://example.com/verify",
            confidence=0.9,
        )
        assert result1 == result2

    def test_backup_link_inequality_different_link(self):
        """测试不同 backup_link 导致不相等"""
        result1 = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            backup_link="https://example.com/verify1",
            confidence=0.9,
        )
        result2 = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            backup_link="https://example.com/verify2",
            confidence=0.9,
        )
        assert result1 != result2

    def test_backup_link_immutability(self):
        """测试 backup_link 不可变"""
        result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            backup_link="https://example.com/verify",
        )
        with pytest.raises(AttributeError):
            result.backup_link = "https://other.com"

    def test_value_property_ignores_backup_link(self):
        """测试 value 属性不受 backup_link 影响"""
        result = ExtractionResult(
            type=ExtractionType.CODE,
            code="123456",
            backup_link="https://example.com/verify",
            confidence=0.9,
        )
        # value 应该返回 code，不是 backup_link
        assert result.value == "123456"
