"""
工作单元模式实现（Unit of Work）

用于管理事务边界和数据库会话生命周期
"""

from typing import Optional
from sqlalchemy.orm import Session, sessionmaker
from contextlib import contextmanager


class UnitOfWork:
    """
    工作单元 - SQLAlchemy 实现

    用法：
        with UnitOfWork(session_factory) as uow:
            # 执行业务逻辑
            user = User(name="test")
            uow.session.add(user)
            uow.commit()  # 提交事务
    """

    def __init__(self, session_factory: sessionmaker):
        """
        初始化工作单元

        Args:
            session_factory: SQLAlchemy sessionmaker
        """
        self._session_factory = session_factory
        self._session: Optional[Session] = None

    def __enter__(self):
        """进入上下文管理器"""
        self._session = self._session_factory()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        if exc_type is not None:
            # 发生异常，回滚
            self.rollback()

        # 关闭 session
        if self._session:
            self._session.close()
            self._session = None

    @property
    def session(self) -> Session:
        """获取当前 Session"""
        if self._session is None:
            raise RuntimeError("UnitOfWork not started. Use 'with UnitOfWork() as uow'")
        return self._session

    def commit(self):
        """提交事务"""
        if self._session:
            self._session.commit()

    def rollback(self):
        """回滚事务"""
        if self._session:
            self._session.rollback()

    def flush(self):
        """刷新到数据库（不提交）"""
        if self._session:
            self._session.flush()


@contextmanager
def unit_of_work(session_factory: sessionmaker):
    """
    工作单元上下文管理器（函数式）

    用法：
        with unit_of_work(session_factory) as session:
            user = User(name="test")
            session.add(user)
            # 自动提交
    """
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
