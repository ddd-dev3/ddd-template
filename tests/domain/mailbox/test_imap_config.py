"""Tests for ImapConfig value object"""

import pytest

from domain.mailbox.value_objects.imap_config import ImapConfig
from domain.common.exceptions import InvalidValueObjectException


class TestImapConfig:
    """ImapConfig 值对象测试"""

    def test_create_with_defaults(self):
        """测试使用默认值创建"""
        config = ImapConfig(server="imap.example.com")

        assert config.server == "imap.example.com"
        assert config.port == 993
        assert config.use_ssl is True

    def test_create_with_custom_port(self):
        """测试使用自定义端口创建"""
        config = ImapConfig(server="imap.example.com", port=143, use_ssl=False)

        assert config.server == "imap.example.com"
        assert config.port == 143
        assert config.use_ssl is False

    def test_create_with_empty_server_raises_error(self):
        """测试空服务器地址抛出异常"""
        with pytest.raises(InvalidValueObjectException) as exc_info:
            ImapConfig(server="")

        assert "IMAP server cannot be empty" in str(exc_info.value.message)

    def test_create_with_whitespace_server_raises_error(self):
        """测试空白服务器地址抛出异常"""
        with pytest.raises(InvalidValueObjectException) as exc_info:
            ImapConfig(server="   ")

        assert "IMAP server cannot be empty" in str(exc_info.value.message)

    def test_create_with_invalid_port_zero_raises_error(self):
        """测试端口为0抛出异常"""
        with pytest.raises(InvalidValueObjectException) as exc_info:
            ImapConfig(server="imap.example.com", port=0)

        assert "Invalid port number" in str(exc_info.value.message)

    def test_create_with_invalid_port_negative_raises_error(self):
        """测试负数端口抛出异常"""
        with pytest.raises(InvalidValueObjectException) as exc_info:
            ImapConfig(server="imap.example.com", port=-1)

        assert "Invalid port number" in str(exc_info.value.message)

    def test_create_with_invalid_port_too_large_raises_error(self):
        """测试端口超出范围抛出异常"""
        with pytest.raises(InvalidValueObjectException) as exc_info:
            ImapConfig(server="imap.example.com", port=65536)

        assert "Invalid port number" in str(exc_info.value.message)

    def test_connection_string_with_ssl(self):
        """测试 SSL 连接字符串"""
        config = ImapConfig(server="imap.example.com", port=993, use_ssl=True)

        assert config.connection_string == "imaps://imap.example.com:993"

    def test_connection_string_without_ssl(self):
        """测试非 SSL 连接字符串"""
        config = ImapConfig(server="imap.example.com", port=143, use_ssl=False)

        assert config.connection_string == "imap://imap.example.com:143"

    def test_immutability(self):
        """测试值对象不可变性"""
        config = ImapConfig(server="imap.example.com")

        with pytest.raises(Exception):  # FrozenInstanceError
            config.server = "other.example.com"

    def test_equality(self):
        """测试值对象相等性"""
        config1 = ImapConfig(server="imap.example.com", port=993)
        config2 = ImapConfig(server="imap.example.com", port=993)

        assert config1 == config2

    def test_inequality(self):
        """测试值对象不相等性"""
        config1 = ImapConfig(server="imap.example.com", port=993)
        config2 = ImapConfig(server="imap.example.com", port=143)

        assert config1 != config2
