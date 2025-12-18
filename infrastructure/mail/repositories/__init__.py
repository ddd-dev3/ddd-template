"""邮件仓储实现模块"""

from infrastructure.mail.repositories.sqlalchemy_email_repository import (
    SqlAlchemyEmailRepository,
)

__all__ = ["SqlAlchemyEmailRepository"]
