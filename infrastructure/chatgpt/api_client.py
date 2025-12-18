"""
ChatGPT Team API 客户端

使用 curl_cffi 绕过 Cloudflare 保护，与 ChatGPT API 交互。

功能：
- Token 管理（refresh_token -> access_token）
- 成员管理（邀请、获取、移除）
- 邀请管理（获取、取消）
"""

import logging
from typing import List, Dict, Any, Optional

from curl_cffi import requests

logger = logging.getLogger(__name__)


class ChatGPTAPIError(Exception):
    """ChatGPT API 错误"""
    pass


class ChatGPTApiClient:
    """
    ChatGPT Team API 客户端

    使用 curl_cffi 模拟浏览器请求，绕过 Cloudflare 保护。
    """

    def __init__(
        self,
        access_token: str,
        base_url: str = "https://chatgpt.com/backend-api",
        proxy: Optional[str] = None,
    ):
        """
        初始化客户端

        Args:
            access_token: 访问令牌
            base_url: API 基础 URL
            proxy: SOCKS5 代理地址（可选）
        """
        self.access_token = access_token
        self.base_url = base_url
        self.proxy = proxy

        # 基础 headers
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

        # 创建 curl_cffi session（模拟 Chrome 浏览器）
        self.session = requests.Session(impersonate="chrome")

        # 配置代理
        if self.proxy:
            self.session.proxies = {
                "http": self.proxy,
                "https": self.proxy,
            }
            logger.info(f"使用代理: {self.proxy}")

    # ============ Token 管理 ============

    @staticmethod
    def get_access_token_from_refresh_token(refresh_token: str) -> dict:
        """
        使用 refresh_token 获取新的 access_token

        Args:
            refresh_token: OpenAI refresh token

        Returns:
            包含 access_token、expires_in 等信息的字典

        Raises:
            ChatGPTAPIError: 如果请求失败
        """
        url = "https://auth.openai.com/oauth/token"

        payload = {
            "client_id": "app_LlGpXReQgckcGGUo2JrYvtJK",
            "grant_type": "refresh_token",
            "redirect_uri": "com.openai.chat://auth0.openai.com/ios/com.openai.chat/callback",
            "refresh_token": refresh_token,
        }

        headers = {"Content-Type": "application/json"}

        logger.info("使用 refresh_token 获取 access_token...")

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if 200 <= response.status_code < 300:
                result = response.json()
                expires_in = result.get("expires_in")
                logger.info(f"access_token 获取成功，有效期: {expires_in} 秒")
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"获取 access_token 失败: {error_msg}")
                raise ChatGPTAPIError(error_msg)

        except ChatGPTAPIError:
            raise
        except Exception as e:
            logger.error(f"获取 access_token 失败: {type(e).__name__}: {e}")
            raise ChatGPTAPIError(f"请求失败: {e}") from e

    # ============ 账户管理 ============

    def get_accounts(self) -> Dict[str, Any]:
        """
        获取用户的所有账户列表

        Returns:
            账户列表字典
        """
        logger.info("获取账户列表...")

        try:
            # 预热 - 先访问主页获取 Cloudflare cookies
            self.session.get("https://chatgpt.com/", timeout=30)

            url = f"{self.base_url}/accounts"

            headers = {
                **self.headers,
                "Accept": "application/json",
                "Origin": "https://chatgpt.com",
                "Referer": "https://chatgpt.com/",
            }

            response = self.session.get(url, headers=headers, timeout=30)

            if 200 <= response.status_code < 300:
                result = response.json() if response.text else {}
                logger.info("账户列表获取成功")
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"获取账户列表失败: {error_msg}")
                raise ChatGPTAPIError(error_msg)

        except ChatGPTAPIError:
            raise
        except Exception as e:
            logger.error(f"获取账户列表失败: {type(e).__name__}: {e}")
            raise ChatGPTAPIError(f"请求失败: {e}") from e

    def get_workspace_account_id(self) -> str:
        """
        获取 workspace 类型的 account_id（Team 账户 ID）

        Returns:
            workspace 账户的 ID

        Raises:
            ChatGPTAPIError: 如果没有找到 workspace 账户
        """
        logger.info("获取 workspace account ID...")

        accounts_data = self.get_accounts()
        accounts = accounts_data.get("items", [])

        workspace_accounts = [
            acc for acc in accounts if acc.get("structure") == "workspace"
        ]

        if workspace_accounts:
            account_id = workspace_accounts[0].get("id")
            logger.info(f"找到 workspace account ID: {account_id}")
            return account_id
        else:
            error_msg = "未找到 workspace 类型的账户"
            logger.error(error_msg)
            raise ChatGPTAPIError(error_msg)

    # ============ 成员管理 ============

    def get_users(
        self,
        account_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        获取 Team 成员列表

        Args:
            account_id: Team 账户 ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            成员列表字典
        """
        logger.info(f"获取成员列表: account_id={account_id}")

        try:
            url = f"{self.base_url}/accounts/{account_id}/users"

            params = {"limit": limit, "offset": offset}

            headers = {
                **self.headers,
                "chatgpt-account-id": account_id,
                "Accept": "application/json",
                "Origin": "https://chatgpt.com",
                "Referer": "https://chatgpt.com/admin/members",
            }

            response = self.session.get(
                url, headers=headers, params=params, timeout=30
            )

            if 200 <= response.status_code < 300:
                result = response.json() if response.text else {}
                total = result.get("total", 0)
                logger.info(f"成员列表获取成功: 共 {total} 个成员")
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"获取成员列表失败: {error_msg}")
                raise ChatGPTAPIError(error_msg)

        except ChatGPTAPIError:
            raise
        except Exception as e:
            logger.error(f"获取成员列表失败: {type(e).__name__}: {e}")
            raise ChatGPTAPIError(f"请求失败: {e}") from e

    def remove_member(
        self,
        account_id: str,
        user_identifier: str,
    ) -> Dict[str, Any]:
        """
        移除 Team 成员

        Args:
            account_id: Team 账户 ID
            user_identifier: 用户 ID 或邮箱地址

        Returns:
            操作结果
        """
        # 判断是邮箱还是 user_id
        if "@" in user_identifier:
            email = user_identifier
            logger.info(f"移除成员: email={email}")

            # 获取成员列表找 user_id
            users = self.get_users(account_id)
            user_id = None
            for user in users.get("items", []):
                if user.get("email") == email:
                    user_id = user.get("id")
                    break

            if not user_id:
                error_msg = f"未找到邮箱对应的成员: {email}"
                logger.error(error_msg)
                raise ChatGPTAPIError(error_msg)

            logger.info(f"找到成员: email={email}, user_id={user_id}")
        else:
            user_id = user_identifier
            logger.info(f"移除成员: user_id={user_id}")

        try:
            url = f"{self.base_url}/accounts/{account_id}/users/{user_id}"

            headers = {
                **self.headers,
                "chatgpt-account-id": account_id,
                "Accept": "application/json",
                "Origin": "https://chatgpt.com",
                "Referer": "https://chatgpt.com/admin/members",
            }

            response = self.session.delete(url, headers=headers, timeout=30)

            if 200 <= response.status_code < 300:
                result = response.json() if response.text else {"success": True}
                logger.info(f"成员移除成功: user_id={user_id}")
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"移除成员失败: {error_msg}")
                raise ChatGPTAPIError(error_msg)

        except ChatGPTAPIError:
            raise
        except Exception as e:
            logger.error(f"移除成员失败: {type(e).__name__}: {e}")
            raise ChatGPTAPIError(f"请求失败: {e}") from e

    # ============ 邀请管理 ============

    def invite_users(
        self,
        account_id: str,
        email_addresses: List[str],
        role: str = "standard-user",
        resend_emails: bool = True,
    ) -> Dict[str, Any]:
        """
        邀请用户到 ChatGPT Team

        Args:
            account_id: Team 账户 ID
            email_addresses: 邮箱地址列表
            role: 用户角色
            resend_emails: 是否重新发送邮件

        Returns:
            API 响应数据
        """
        url = f"{self.base_url}/accounts/{account_id}/invites"

        payload = {
            "email_addresses": email_addresses,
            "role": role,
            "resend_emails": resend_emails,
        }

        logger.info(f"邀请用户: {len(email_addresses)} 个邮箱")

        try:
            headers = {
                **self.headers,
                "chatgpt-account-id": account_id,
            }

            response = self.session.post(
                url, json=payload, headers=headers, timeout=30
            )

            if 200 <= response.status_code < 300:
                logger.info(f"邀请成功: {email_addresses}")
                try:
                    return response.json() if response.text else {}
                except ValueError:
                    return {}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"邀请失败: {error_msg}")
                raise ChatGPTAPIError(error_msg)

        except ChatGPTAPIError:
            raise
        except Exception as e:
            logger.error(f"邀请失败: {type(e).__name__}: {e}")
            raise ChatGPTAPIError(f"请求失败: {e}") from e

    def invite_single_user(
        self,
        account_id: str,
        email: str,
        role: str = "standard-user",
    ) -> Dict[str, Any]:
        """邀请单个用户"""
        return self.invite_users(account_id, [email], role)

    def get_invites(
        self,
        account_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """
        获取待处理的邀请列表

        Args:
            account_id: Team 账户 ID
            limit: 返回数量限制
            offset: 偏移量

        Returns:
            邀请列表字典
        """
        logger.info(f"获取邀请列表: account_id={account_id}")

        try:
            url = f"{self.base_url}/accounts/{account_id}/invites"

            params = {"limit": limit, "offset": offset}

            headers = {
                **self.headers,
                "chatgpt-account-id": account_id,
                "Accept": "application/json",
                "Origin": "https://chatgpt.com",
                "Referer": "https://chatgpt.com/admin/members",
            }

            response = self.session.get(
                url, headers=headers, params=params, timeout=30
            )

            if 200 <= response.status_code < 300:
                result = response.json() if response.text else {}
                total = result.get("total", 0)
                logger.info(f"邀请列表获取成功: 共 {total} 个待处理邀请")
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"获取邀请列表失败: {error_msg}")
                raise ChatGPTAPIError(error_msg)

        except ChatGPTAPIError:
            raise
        except Exception as e:
            logger.error(f"获取邀请列表失败: {type(e).__name__}: {e}")
            raise ChatGPTAPIError(f"请求失败: {e}") from e

    def cancel_invite(
        self,
        account_id: str,
        email_address: str,
    ) -> Dict[str, Any]:
        """
        取消待处理的邀请

        Args:
            account_id: Team 账户 ID
            email_address: 要取消邀请的邮箱地址

        Returns:
            操作结果
        """
        logger.info(f"取消邀请: email={email_address}")

        try:
            url = f"{self.base_url}/accounts/{account_id}/invites"

            headers = {
                **self.headers,
                "chatgpt-account-id": account_id,
                "Accept": "application/json",
                "Origin": "https://chatgpt.com",
                "Referer": "https://chatgpt.com/admin/members",
            }

            payload = {"email_address": email_address}

            response = self.session.delete(
                url, headers=headers, json=payload, timeout=30
            )

            if 200 <= response.status_code < 300:
                result = response.json() if response.text else {"success": True}
                logger.info(f"邀请取消成功: email={email_address}")
                return result
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"取消邀请失败: {error_msg}")
                raise ChatGPTAPIError(error_msg)

        except ChatGPTAPIError:
            raise
        except Exception as e:
            logger.error(f"取消邀请失败: {type(e).__name__}: {e}")
            raise ChatGPTAPIError(f"请求失败: {e}") from e
