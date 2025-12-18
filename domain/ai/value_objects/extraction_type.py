"""提取类型枚举"""

from enum import Enum


class ExtractionType(str, Enum):
    """
    提取类型枚举

    用于标识 AI 提取结果的类型。
    继承 str 使枚举值可直接作为字符串使用。
    """

    CODE = "code"  # 验证码
    LINK = "link"  # 验证链接
    UNKNOWN = "unknown"  # 未知类型（提取失败或无验证信息）
