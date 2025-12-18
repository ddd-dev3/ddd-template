"""Tests for GetCodeQuery"""

import pytest
from uuid import uuid4, UUID

from application.queries.verification.get_code import GetCodeQuery


class TestGetCodeQuery:
    """GetCodeQuery 测试"""

    def test_create_with_uuid(self):
        """测试使用 UUID 创建 Query"""
        request_id = uuid4()
        query = GetCodeQuery(request_id=request_id)

        assert query.request_id == request_id
        assert isinstance(query.request_id, UUID)

    def test_create_with_different_uuids(self):
        """测试不同 UUID 创建不同的 Query"""
        id1 = uuid4()
        id2 = uuid4()

        query1 = GetCodeQuery(request_id=id1)
        query2 = GetCodeQuery(request_id=id2)

        assert query1.request_id != query2.request_id

    def test_query_is_dataclass(self):
        """测试 Query 是 dataclass"""
        request_id = uuid4()
        query = GetCodeQuery(request_id=request_id)

        # dataclass 应该有 __dataclass_fields__ 属性
        assert hasattr(query, "__dataclass_fields__")
        assert "request_id" in query.__dataclass_fields__

    def test_query_immutability_like(self):
        """测试 Query 像值对象一样使用"""
        request_id = uuid4()
        query = GetCodeQuery(request_id=request_id)

        # Query 应该能正常访问属性
        assert query.request_id is not None

    def test_query_equality(self):
        """测试 Query 相等性"""
        request_id = uuid4()
        query1 = GetCodeQuery(request_id=request_id)
        query2 = GetCodeQuery(request_id=request_id)

        # 同一 request_id 的 Query 应该相等
        assert query1 == query2

    def test_query_inequality(self):
        """测试 Query 不相等性"""
        query1 = GetCodeQuery(request_id=uuid4())
        query2 = GetCodeQuery(request_id=uuid4())

        # 不同 request_id 的 Query 应该不相等
        assert query1 != query2
