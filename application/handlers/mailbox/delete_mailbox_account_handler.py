"""删除邮箱账号处理器"""

from uuid import UUID

from application.commands.mailbox.delete_mailbox_account import (
    DeleteMailboxAccountCommand,
    DeleteMailboxAccountResult,
)
from domain.mailbox.repositories.mailbox_account_repository import MailboxAccountRepository
from domain.mailbox.value_objects.mailbox_enums import MailboxStatus


class DeleteMailboxAccountHandler:
    """
    删除邮箱账号处理器

    处理 DeleteMailboxAccountCommand，验证邮箱状态后执行删除。
    """

    def __init__(self, repository: MailboxAccountRepository):
        """
        初始化处理器

        Args:
            repository: 邮箱账号仓储
        """
        self._repository = repository

    async def handle(self, command: DeleteMailboxAccountCommand) -> DeleteMailboxAccountResult:
        """
        处理删除命令

        Args:
            command: 删除命令

        Returns:
            DeleteMailboxAccountResult: 删除结果
        """
        # 1. 验证 UUID 格式并查找邮箱
        try:
            mailbox_uuid = UUID(command.mailbox_id)
        except ValueError:
            return DeleteMailboxAccountResult(
                success=False,
                mailbox_id=command.mailbox_id,
                message=f"Invalid mailbox ID format: '{command.mailbox_id}'",
                error_code="MAILBOX_NOT_FOUND",
            )

        mailbox = self._repository.get_by_id(mailbox_uuid)
        if mailbox is None:
            return DeleteMailboxAccountResult(
                success=False,
                mailbox_id=command.mailbox_id,
                message=f"Mailbox with ID '{command.mailbox_id}' not found",
                error_code="MAILBOX_NOT_FOUND",
            )

        # 2. 检查状态 - 只有 available 状态才能删除
        if mailbox.status == MailboxStatus.OCCUPIED:
            return DeleteMailboxAccountResult(
                success=False,
                mailbox_id=command.mailbox_id,
                username=mailbox.username,
                message="Cannot delete occupied mailbox. Release it first.",
                error_code="MAILBOX_OCCUPIED",
            )

        # 3. 执行删除
        username = mailbox.username
        self._repository.remove(mailbox)

        return DeleteMailboxAccountResult(
            success=True,
            mailbox_id=command.mailbox_id,
            username=username,
            message=f"Mailbox '{username}' deleted successfully",
        )
