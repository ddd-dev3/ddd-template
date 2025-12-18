"""Tests for mailbox enum types"""

import pytest

from domain.mailbox.value_objects.mailbox_enums import MailboxType, MailboxStatus


class TestMailboxType:
    """MailboxType 枚举测试"""

    def test_domain_catchall_value(self):
        """测试 DOMAIN_CATCHALL 枚举值"""
        assert MailboxType.DOMAIN_CATCHALL.value == "domain_catchall"

    def test_hotmail_value(self):
        """测试 HOTMAIL 枚举值"""
        assert MailboxType.HOTMAIL.value == "hotmail"

    def test_enum_is_string(self):
        """测试枚举值是字符串类型"""
        assert isinstance(MailboxType.DOMAIN_CATCHALL, str)
        assert isinstance(MailboxType.HOTMAIL, str)

    def test_enum_from_string(self):
        """测试从字符串创建枚举"""
        assert MailboxType("domain_catchall") == MailboxType.DOMAIN_CATCHALL
        assert MailboxType("hotmail") == MailboxType.HOTMAIL


class TestMailboxStatus:
    """MailboxStatus 枚举测试"""

    def test_available_value(self):
        """测试 AVAILABLE 枚举值"""
        assert MailboxStatus.AVAILABLE.value == "available"

    def test_occupied_value(self):
        """测试 OCCUPIED 枚举值"""
        assert MailboxStatus.OCCUPIED.value == "occupied"

    def test_enum_is_string(self):
        """测试枚举值是字符串类型"""
        assert isinstance(MailboxStatus.AVAILABLE, str)
        assert isinstance(MailboxStatus.OCCUPIED, str)

    def test_enum_from_string(self):
        """测试从字符串创建枚举"""
        assert MailboxStatus("available") == MailboxStatus.AVAILABLE
        assert MailboxStatus("occupied") == MailboxStatus.OCCUPIED
