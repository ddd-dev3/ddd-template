"""WaitRequestStatus 值对象测试"""

import pytest

from domain.verification.value_objects.wait_request_status import WaitRequestStatus


class TestWaitRequestStatus:
    """WaitRequestStatus 枚举测试"""

    def test_pending_value(self):
        """测试 PENDING 枚举值"""
        assert WaitRequestStatus.PENDING.value == "pending"

    def test_completed_value(self):
        """测试 COMPLETED 枚举值"""
        assert WaitRequestStatus.COMPLETED.value == "completed"

    def test_cancelled_value(self):
        """测试 CANCELLED 枚举值"""
        assert WaitRequestStatus.CANCELLED.value == "cancelled"

    def test_failed_value(self):
        """测试 FAILED 枚举值"""
        assert WaitRequestStatus.FAILED.value == "failed"

    def test_enum_is_string(self):
        """测试枚举值是字符串类型"""
        assert isinstance(WaitRequestStatus.PENDING, str)
        assert isinstance(WaitRequestStatus.COMPLETED, str)
        assert isinstance(WaitRequestStatus.CANCELLED, str)
        assert isinstance(WaitRequestStatus.FAILED, str)

    def test_enum_from_string(self):
        """测试从字符串创建枚举"""
        assert WaitRequestStatus("pending") == WaitRequestStatus.PENDING
        assert WaitRequestStatus("completed") == WaitRequestStatus.COMPLETED
        assert WaitRequestStatus("cancelled") == WaitRequestStatus.CANCELLED
        assert WaitRequestStatus("failed") == WaitRequestStatus.FAILED

    def test_enum_comparison(self):
        """测试枚举比较"""
        assert WaitRequestStatus.PENDING == "pending"
        assert WaitRequestStatus.COMPLETED == "completed"
        assert WaitRequestStatus.CANCELLED == "cancelled"
        assert WaitRequestStatus.FAILED == "failed"

    def test_enum_count(self):
        """测试枚举成员数量"""
        assert len(WaitRequestStatus) == 4
