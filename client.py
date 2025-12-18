"""
Mail Service 客户端

使用示例：
    python client.py
"""

import httpx

# ========== 配置 ==========
BASE_URL = "http://207.58.173.163:8000"
API_KEY = "9-NNhvtKKx95FoEAO9WqK7j8BHck1lg66rQaEUu4lQg"

# 邮箱配置
MAILBOX_CONFIG = {
    "username": "catchall@linkflow.run",
    "password": "jonthern4523",  # <-- 填写邮箱密码
    "mailbox_type": "domain_catchall",
    "domain": "linkflow.run",
    "imap_server": "mxe9e9.netcup.net",
    "imap_port": 993,
    "use_ssl": True,
}


class MailServiceClient:
    """Mail Service API 客户端"""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json",
        }

    def add_account(
        self,
        username: str,
        password: str,
        mailbox_type: str = "dedicated",
        domain: str = None,
        imap_server: str = None,
        imap_port: int = 993,
        use_ssl: bool = True,
    ) -> dict:
        """添加邮箱账号"""
        data = {
            "username": username,
            "password": password,
            "type": mailbox_type,  # API 字段名是 type
            "imap_server": imap_server,
            "imap_port": imap_port,
            "use_ssl": use_ssl,
        }
        if domain:
            data["domain"] = domain

        response = httpx.post(
            f"{self.base_url}/api/v1/accounts",
            headers=self.headers,
            json=data,
            timeout=30.0,
        )
        return response.json()

    def list_accounts(self) -> dict:
        """列出所有邮箱账号"""
        response = httpx.get(
            f"{self.base_url}/api/v1/accounts",
            headers=self.headers,
            timeout=10.0,
        )
        return response.json()

    def delete_account(self, account_id: str) -> dict:
        """删除邮箱账号"""
        response = httpx.delete(
            f"{self.base_url}/api/v1/accounts/{account_id}",
            headers=self.headers,
            timeout=10.0,
        )
        return response.json()

    def register_wait(
        self,
        email: str,
        sender_filter: str = None,
        subject_filter: str = None,
        timeout_seconds: int = 300,
        webhook_url: str = None,
    ) -> dict:
        """注册等待验证码请求"""
        data = {
            "email": email,
            "timeout_seconds": timeout_seconds,
        }
        if sender_filter:
            data["sender_filter"] = sender_filter
        if subject_filter:
            data["subject_filter"] = subject_filter
        if webhook_url:
            data["webhook_url"] = webhook_url

        response = httpx.post(
            f"{self.base_url}/api/v1/register",
            headers=self.headers,
            json=data,
            timeout=30.0,
        )
        return response.json()

    def get_code(self, request_id: str) -> dict:
        """查询验证码结果"""
        response = httpx.get(
            f"{self.base_url}/api/v1/code/{request_id}",
            headers=self.headers,
            timeout=10.0,
        )
        return response.json()

    def cancel_wait(self, request_id: str) -> dict:
        """取消等待请求"""
        response = httpx.delete(
            f"{self.base_url}/api/v1/register/{request_id}",
            headers=self.headers,
            timeout=10.0,
        )
        return response.json()


def main():
    client = MailServiceClient(BASE_URL, API_KEY)

    print("=" * 50)
    print("Mail Service 客户端")
    print("=" * 50)

    # 1. 列出邮箱账号
    print("\n[1] 列出邮箱账号...")
    result = client.list_accounts()
    print(f"    结果: {result}")

    # 2. 注册等待验证码请求
    print("\n[2] 注册等待验证码请求...")
    result = client.register_wait(
        email="fjdsuoifjiosd523@linkflow.run",  # catchall 会收到所有 @linkflow.run 邮件
        timeout_seconds=300,
    )
    print(f"    结果: {result}")

    if "id" in result:
        request_id = result["id"]

        # 3. 查询验证码
        print(f"\n[3] 查询验证码 (request_id: {request_id})...")
        import time
        for i in range(5):
            print(f"    第 {i+1} 次查询...")
            code_result = client.get_code(request_id)
            print(f"    结果: {code_result}")

            if code_result.get("status") == "completed":
                print(f"\n    验证码: {code_result.get('code')}")
                break

            time.sleep(5)  # 等待 5 秒后重试


if __name__ == "__main__":
    main()
