"""Verification 命令模块"""

from application.commands.verification.register_wait_request import (
    RegisterWaitRequestCommand,
    RegisterWaitRequestResult,
    RegisterWaitRequestHandler,
)
from application.commands.verification.process_email import (
    ProcessEmailCommand,
    ProcessEmailResult,
    ProcessEmailHandler,
)

__all__ = [
    "RegisterWaitRequestCommand",
    "RegisterWaitRequestResult",
    "RegisterWaitRequestHandler",
    "ProcessEmailCommand",
    "ProcessEmailResult",
    "ProcessEmailHandler",
]
