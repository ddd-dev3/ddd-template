"""AI 提取结果值对象"""

from dataclasses import dataclass
from typing import Optional

from domain.ai.value_objects.extraction_type import ExtractionType
from domain.common.base_value_object import BaseValueObject


@dataclass(frozen=True)
class ExtractionResult(BaseValueObject):
    """
    AI 提取结果值对象

    不可变对象，封装 AI 提取的验证码/链接信息。

    Attributes:
        type: 提取类型（CODE/LINK/UNKNOWN）
        code: 验证码（如果是 CODE 类型）
        link: 验证链接（如果是 LINK 类型）
        backup_link: 备用验证链接（当同时存在验证码和链接时）
        confidence: 置信度 (0.0-1.0)
        raw_response: LLM 原始响应（用于调试）
    """

    type: ExtractionType
    code: Optional[str] = None
    link: Optional[str] = None
    backup_link: Optional[str] = None
    confidence: float = 0.0
    raw_response: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """
        提取是否成功

        Returns:
            True 如果类型不是 UNKNOWN 且有提取到值（code 或 link）
        """
        return self.type != ExtractionType.UNKNOWN and (
            self.code is not None or self.link is not None
        )

    @property
    def value(self) -> Optional[str]:
        """
        获取提取的值

        优先返回验证码，其次返回验证链接。

        Returns:
            验证码或验证链接，如果都没有则返回 None
        """
        return self.code or self.link
