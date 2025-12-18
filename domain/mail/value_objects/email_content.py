"""邮件内容值对象"""

from dataclasses import dataclass
from typing import Optional

from domain.common.base_value_object import BaseValueObject


@dataclass(frozen=True)
class EmailContent(BaseValueObject):
    """
    邮件内容值对象

    封装邮件的正文内容，支持纯文本和 HTML 两种格式。

    Attributes:
        text: 纯文本正文
        html: HTML 正文
    """

    text: Optional[str] = None
    html: Optional[str] = None

    @property
    def has_text(self) -> bool:
        """检查是否有纯文本内容"""
        return self.text is not None and len(self.text) > 0

    @property
    def has_html(self) -> bool:
        """检查是否有 HTML 内容"""
        return self.html is not None and len(self.html) > 0

    @property
    def is_empty(self) -> bool:
        """检查内容是否为空"""
        return not self.has_text and not self.has_html

    @property
    def preferred_content(self) -> str:
        """
        获取优先内容

        优先返回纯文本，如果不存在则返回 HTML。
        """
        if self.has_text:
            return self.text  # type: ignore
        if self.has_html:
            return self.html  # type: ignore
        return ""
