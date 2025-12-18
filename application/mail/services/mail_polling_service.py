"""邮件轮询服务接口"""

from abc import ABC, abstractmethod


class MailPollingService(ABC):
    """
    邮件轮询服务接口

    定义邮件轮询调度器的契约，负责：
    - 按固定间隔轮询所有邮箱
    - 并行收取新邮件并存储
    - 并发连接数限制
    - 单邮箱超时处理
    - 优雅启动和停止
    """

    DEFAULT_INTERVAL: float = 5.0  # 默认轮询间隔（秒）
    DEFAULT_MAX_CONCURRENT: int = 10  # 默认最大并发连接数
    DEFAULT_TIMEOUT: float = 30.0  # 默认单邮箱超时（秒）

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """
        检查轮询服务是否正在运行

        Returns:
            True 如果服务正在运行，False 如果已停止
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def interval(self) -> float:
        """
        获取轮询间隔（秒）

        Returns:
            轮询间隔秒数
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def max_concurrent_connections(self) -> int:
        """
        获取最大并发连接数

        Returns:
            最大并发 IMAP 连接数
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def mailbox_poll_timeout(self) -> float:
        """
        获取单邮箱轮询超时（秒）

        Returns:
            超时秒数
        """
        raise NotImplementedError

    @abstractmethod
    async def start(self) -> None:
        """
        启动轮询服务

        启动后立即执行第一次轮询，之后按配置的间隔周期性执行。
        如果服务已在运行，则不会重复启动。
        """
        raise NotImplementedError

    @abstractmethod
    async def stop(self) -> None:
        """
        停止轮询服务

        优雅关闭：等待当前轮询周期完成后停止。
        如果服务未运行，则此方法无效。
        """
        raise NotImplementedError
