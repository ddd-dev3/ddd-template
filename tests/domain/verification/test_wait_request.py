"""WaitRequest 实体测试"""

import pytest
from uuid import uuid4
from datetime import datetime, timezone

from domain.common.exceptions import InvalidStateTransitionException
from domain.verification.entities.wait_request import WaitRequest
from domain.verification.value_objects.wait_request_status import WaitRequestStatus


class TestWaitRequestCreate:
    """WaitRequest.create() 工厂方法测试"""

    def test_create_with_valid_params(self):
        """测试使用有效参数创建等待请求"""
        mailbox_id = uuid4()
        email = "test@example.com"
        service_name = "claude"
        callback_url = "https://api.example.com/callback"

        request = WaitRequest.create(
            mailbox_id=mailbox_id,
            email=email,
            service_name=service_name,
            callback_url=callback_url,
        )

        assert request.mailbox_id == mailbox_id
        assert request.email == email
        assert request.service_name == service_name
        assert request.callback_url == callback_url
        assert request.status == WaitRequestStatus.PENDING
        assert request.completed_at is None
        assert request.extraction_result is None
        assert request.id is not None

    def test_create_generates_unique_id(self):
        """测试每次创建生成唯一 ID"""
        mailbox_id = uuid4()
        request1 = WaitRequest.create(
            mailbox_id=mailbox_id,
            email="test1@example.com",
            service_name="service1",
            callback_url="https://example.com/callback1",
        )
        request2 = WaitRequest.create(
            mailbox_id=mailbox_id,
            email="test2@example.com",
            service_name="service2",
            callback_url="https://example.com/callback2",
        )

        assert request1.id != request2.id


class TestWaitRequestComplete:
    """WaitRequest.complete() 状态转换测试"""

    @pytest.fixture
    def pending_request(self):
        """创建一个 PENDING 状态的等待请求"""
        return WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/callback",
        )

    def test_complete_from_pending(self, pending_request):
        """测试从 PENDING 状态完成请求"""
        extraction_result = "123456"
        pending_request.complete(extraction_result)

        assert pending_request.status == WaitRequestStatus.COMPLETED
        assert pending_request.extraction_result == extraction_result
        assert pending_request.completed_at is not None
        assert pending_request.is_completed

    def test_complete_from_completed_raises_exception(self, pending_request):
        """测试从 COMPLETED 状态完成请求抛出异常"""
        pending_request.complete("123456")

        with pytest.raises(InvalidStateTransitionException):
            pending_request.complete("654321")

    def test_complete_from_cancelled_raises_exception(self, pending_request):
        """测试从 CANCELLED 状态完成请求抛出异常"""
        pending_request.cancel()

        with pytest.raises(InvalidStateTransitionException):
            pending_request.complete("123456")

    def test_complete_from_failed_raises_exception(self, pending_request):
        """测试从 FAILED 状态完成请求抛出异常"""
        pending_request.fail()

        with pytest.raises(InvalidStateTransitionException):
            pending_request.complete("123456")


class TestWaitRequestCancel:
    """WaitRequest.cancel() 状态转换测试"""

    @pytest.fixture
    def pending_request(self):
        """创建一个 PENDING 状态的等待请求"""
        return WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/callback",
        )

    def test_cancel_from_pending(self, pending_request):
        """测试从 PENDING 状态取消请求"""
        pending_request.cancel()

        assert pending_request.status == WaitRequestStatus.CANCELLED
        assert pending_request.is_cancelled

    def test_cancel_from_completed_raises_exception(self, pending_request):
        """测试从 COMPLETED 状态取消请求抛出异常"""
        pending_request.complete("123456")

        with pytest.raises(InvalidStateTransitionException):
            pending_request.cancel()

    def test_cancel_from_cancelled_raises_exception(self, pending_request):
        """测试从 CANCELLED 状态再次取消抛出异常"""
        pending_request.cancel()

        with pytest.raises(InvalidStateTransitionException):
            pending_request.cancel()

    def test_cancel_from_failed_raises_exception(self, pending_request):
        """测试从 FAILED 状态取消抛出异常"""
        pending_request.fail()

        with pytest.raises(InvalidStateTransitionException):
            pending_request.cancel()


class TestWaitRequestFail:
    """WaitRequest.fail() 状态转换测试"""

    @pytest.fixture
    def pending_request(self):
        """创建一个 PENDING 状态的等待请求"""
        return WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/callback",
        )

    def test_fail_from_pending(self, pending_request):
        """测试从 PENDING 状态标记失败"""
        pending_request.fail()

        assert pending_request.status == WaitRequestStatus.FAILED
        assert pending_request.is_failed
        assert pending_request.failure_reason is None

    def test_fail_with_reason(self, pending_request):
        """测试从 PENDING 状态标记失败并记录原因"""
        failure_reason = "Callback timeout after 30s"
        pending_request.fail(reason=failure_reason)

        assert pending_request.status == WaitRequestStatus.FAILED
        assert pending_request.is_failed
        assert pending_request.failure_reason == failure_reason

    def test_fail_from_completed_raises_exception(self, pending_request):
        """测试从 COMPLETED 状态标记失败抛出异常"""
        pending_request.complete("123456")

        with pytest.raises(InvalidStateTransitionException):
            pending_request.fail()

    def test_fail_from_cancelled_raises_exception(self, pending_request):
        """测试从 CANCELLED 状态标记失败抛出异常"""
        pending_request.cancel()

        with pytest.raises(InvalidStateTransitionException):
            pending_request.fail()

    def test_fail_from_failed_raises_exception(self, pending_request):
        """测试从 FAILED 状态再次标记失败抛出异常"""
        pending_request.fail()

        with pytest.raises(InvalidStateTransitionException):
            pending_request.fail()


class TestWaitRequestProperties:
    """WaitRequest 属性测试"""

    @pytest.fixture
    def pending_request(self):
        """创建一个 PENDING 状态的等待请求"""
        return WaitRequest.create(
            mailbox_id=uuid4(),
            email="test@example.com",
            service_name="claude",
            callback_url="https://example.com/callback",
        )

    def test_is_pending_true(self, pending_request):
        """测试 PENDING 状态 is_pending 为 True"""
        assert pending_request.is_pending is True

    def test_is_pending_false_after_complete(self, pending_request):
        """测试完成后 is_pending 为 False"""
        pending_request.complete("123456")
        assert pending_request.is_pending is False

    def test_is_terminal_false_for_pending(self, pending_request):
        """测试 PENDING 状态不是终态"""
        assert pending_request.is_terminal is False

    def test_is_terminal_true_for_completed(self, pending_request):
        """测试 COMPLETED 是终态"""
        pending_request.complete("123456")
        assert pending_request.is_terminal is True

    def test_is_terminal_true_for_cancelled(self, pending_request):
        """测试 CANCELLED 是终态"""
        pending_request.cancel()
        assert pending_request.is_terminal is True

    def test_is_terminal_true_for_failed(self, pending_request):
        """测试 FAILED 是终态"""
        pending_request.fail()
        assert pending_request.is_terminal is True
