"""邮箱账号 SQLAlchemy 仓储实现"""

from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session

from domain.mailbox.entities.mailbox_account import MailboxAccount
from domain.mailbox.repositories.mailbox_account_repository import MailboxAccountRepository
from domain.mailbox.value_objects.imap_config import ImapConfig
from domain.mailbox.value_objects.encrypted_password import EncryptedPassword
from domain.mailbox.value_objects.mailbox_enums import MailboxType, MailboxStatus
from infrastructure.mailbox.models.mailbox_account_model import MailboxAccountModel


class SqlAlchemyMailboxAccountRepository(MailboxAccountRepository):
    """
    邮箱账号 SQLAlchemy 仓储实现

    提供邮箱账号的持久化操作
    """

    def __init__(self, session: Session):
        """
        初始化仓储

        Args:
            session: SQLAlchemy Session
        """
        self._session = session

    def add(self, mailbox: MailboxAccount) -> None:
        """添加邮箱账号"""
        model = self._to_model(mailbox)
        self._session.add(model)
        self._session.commit()

    def get_by_id(self, mailbox_id: UUID) -> Optional[MailboxAccount]:
        """根据 ID 获取邮箱账号"""
        model = self._session.query(MailboxAccountModel).filter(
            MailboxAccountModel.id == str(mailbox_id)
        ).first()

        if model is None:
            return None

        return self._to_entity(model)

    def get_by_username(self, username: str) -> Optional[MailboxAccount]:
        """根据用户名获取邮箱账号"""
        model = self._session.query(MailboxAccountModel).filter(
            MailboxAccountModel.username == username
        ).first()

        if model is None:
            return None

        return self._to_entity(model)

    def exists_by_username(self, username: str) -> bool:
        """检查用户名是否已存在"""
        count = self._session.query(MailboxAccountModel).filter(
            MailboxAccountModel.username == username
        ).count()

        return count > 0

    def remove(self, mailbox: MailboxAccount) -> None:
        """移除邮箱账号"""
        model = self._session.query(MailboxAccountModel).filter(
            MailboxAccountModel.id == str(mailbox.id)
        ).first()

        if model is not None:
            self._session.delete(model)
            self._session.commit()

    def update(self, mailbox: MailboxAccount) -> None:
        """更新邮箱账号"""
        model = self._session.query(MailboxAccountModel).filter(
            MailboxAccountModel.id == str(mailbox.id)
        ).first()

        if model is not None:
            self._update_model(model, mailbox)
            self._session.commit()

    def list_all(self) -> List[MailboxAccount]:
        """获取所有邮箱账号"""
        models = self._session.query(MailboxAccountModel).all()
        return [self._to_entity(model) for model in models]

    def list_filtered(
        self,
        service: Optional[str] = None,
        status: Optional[MailboxStatus] = None,
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[MailboxAccount], int]:
        """
        分页筛选查询邮箱列表

        Args:
            service: 按占用服务筛选（匹配 occupied_by_service）
            status: 按状态筛选（available/occupied）
            page: 页码，从 1 开始
            limit: 每页数量

        Returns:
            Tuple[items, total_count]: 当前页数据和总数
        """
        query = self._session.query(MailboxAccountModel)

        # 筛选条件
        if service is not None:
            query = query.filter(MailboxAccountModel.occupied_by_service == service)
        if status is not None:
            query = query.filter(MailboxAccountModel.status == status.value)

        # 总数统计
        total = query.count()

        # 排序（确保分页结果稳定）
        query = query.order_by(MailboxAccountModel.created_at.desc())

        # 分页
        offset = (page - 1) * limit
        models = query.offset(offset).limit(limit).all()

        return [self._to_entity(model) for model in models], total

    def _to_model(self, entity: MailboxAccount) -> MailboxAccountModel:
        """将领域实体转换为数据模型"""
        return MailboxAccountModel(
            id=str(entity.id),
            username=entity.username,
            mailbox_type=entity.mailbox_type.value,
            domain=entity.domain,
            imap_server=entity.imap_config.server if entity.imap_config else "",
            imap_port=entity.imap_config.port if entity.imap_config else 993,
            use_ssl=entity.imap_config.use_ssl if entity.imap_config else True,
            encrypted_password=entity.encrypted_password.encrypted_value if entity.encrypted_password else b"",
            status=entity.status.value,
            occupied_by_service=entity.occupied_by_service,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            version=entity.version,
        )

    def _to_entity(self, model: MailboxAccountModel) -> MailboxAccount:
        """将数据模型转换为领域实体"""
        imap_config = ImapConfig(
            server=model.imap_server,
            port=model.imap_port,
            use_ssl=model.use_ssl,
        )

        # 直接创建 EncryptedPassword，不经过验证（已加密的数据）
        encrypted_password = EncryptedPassword.__new__(EncryptedPassword)
        object.__setattr__(encrypted_password, "encrypted_value", model.encrypted_password)

        return MailboxAccount(
            id=UUID(model.id),
            username=model.username,
            mailbox_type=MailboxType(model.mailbox_type),
            imap_config=imap_config,
            encrypted_password=encrypted_password,
            domain=model.domain,
            status=MailboxStatus(model.status),
            occupied_by_service=model.occupied_by_service,
            created_at=model.created_at,
            updated_at=model.updated_at,
            version=model.version,
        )

    def _update_model(self, model: MailboxAccountModel, entity: MailboxAccount) -> None:
        """更新数据模型"""
        model.username = entity.username
        model.mailbox_type = entity.mailbox_type.value
        model.domain = entity.domain
        model.imap_server = entity.imap_config.server if entity.imap_config else ""
        model.imap_port = entity.imap_config.port if entity.imap_config else 993
        model.use_ssl = entity.imap_config.use_ssl if entity.imap_config else True
        model.encrypted_password = entity.encrypted_password.encrypted_value if entity.encrypted_password else b""
        model.status = entity.status.value
        model.occupied_by_service = entity.occupied_by_service
        model.updated_at = entity.updated_at
        model.version = entity.version
