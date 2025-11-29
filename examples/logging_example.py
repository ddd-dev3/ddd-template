"""
日志模块使用示例

演示如何使用 DDD Framework 的日志功能：
1. 使用不同的日志后端（simple/loguru/logfire）
2. 结构化日志
3. 上下文日志
"""

import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def example_1_simple_logging():
    """示例 1：使用标准 logging"""
    print("\n" + "=" * 60)
    print("示例 1：标准 logging（无额外依赖）")
    print("=" * 60)

    # 设置后端
    os.environ["LOG_BACKEND"] = "simple"
    os.environ["LOG_LEVEL"] = "INFO"

    from common.logging import get_logger

    logger = get_logger(__name__)

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # 结构化日志（需要手动格式化）
    user_id = 123
    logger.info(f"User created: user_id={user_id}")


def example_2_loguru():
    """示例 2：使用 Loguru"""
    print("\n" + "=" * 60)
    print("示例 2：Loguru（推荐，需要安装 loguru）")
    print("=" * 60)

    # 设置后端
    os.environ["LOG_BACKEND"] = "loguru"
    os.environ["LOG_LEVEL"] = "INFO"

    from common.logging import get_logger

    logger = get_logger(__name__)

    logger.info("Loguru 支持彩色输出！")
    logger.success("这是成功消息")
    logger.warning("这是警告消息")
    logger.error("这是错误消息")

    # 结构化日志（更优雅）
    user_data = {"id": 123, "name": "Alice", "email": "alice@example.com"}
    logger.info("用户已创建", user=user_data)

    # 异常追踪
    try:
        1 / 0
    except Exception as e:
        logger.exception("出错了！")


def example_3_logfire():
    """示例 3：使用 Logfire"""
    print("\n" + "=" * 60)
    print("示例 3：Logfire（现代化，需要安装 logfire）")
    print("=" * 60)
    print("注意：需要先运行 'logfire auth' 进行认证")
    print()

    # 设置后端
    os.environ["LOG_BACKEND"] = "logfire"

    from common.logging import get_logger

    logger = get_logger(__name__)

    logger.info("Logfire 支持分布式追踪！")

    # 结构化日志（自动序列化）
    user_data = {"id": 123, "name": "Bob", "email": "bob@example.com"}
    logger.info("用户已创建", user=user_data)

    # 使用 span 追踪性能
    try:
        import logfire
        with logfire.span("create_user"):
            import time
            time.sleep(0.1)  # 模拟耗时操作
            logger.info("用户创建完成")
    except ImportError:
        print("⚠️  Logfire 未安装，跳过 span 示例")


def example_4_switch_backend():
    """示例 4：动态切换日志后端"""
    print("\n" + "=" * 60)
    print("示例 4：动态切换日志后端")
    print("=" * 60)

    from common.logging import get_logger, set_log_backend

    # 使用 simple
    set_log_backend("simple")
    logger = get_logger(__name__)
    logger.info("当前使用: simple logging")

    # 切换到 loguru
    try:
        set_log_backend("loguru")
        logger = get_logger(__name__)
        logger.info("当前使用: Loguru")
    except Exception as e:
        print(f"⚠️  切换到 Loguru 失败: {e}")

    # 切换到 logfire
    try:
        set_log_backend("logfire")
        logger = get_logger(__name__)
        logger.info("当前使用: Logfire")
    except Exception as e:
        print(f"⚠️  切换到 Logfire 失败: {e}")


def example_5_in_domain_layer():
    """示例 5：在领域层使用日志"""
    print("\n" + "=" * 60)
    print("示例 5：在领域层使用日志")
    print("=" * 60)

    os.environ["LOG_BACKEND"] = "simple"

    # 模拟领域实体
    from dataclasses import dataclass
    from common.logging import get_logger

    @dataclass
    class User:
        id: int
        name: str

        def __post_init__(self):
            self.logger = get_logger(self.__class__.__name__)

        def change_name(self, new_name: str):
            old_name = self.name
            self.name = new_name
            self.logger.info(
                f"用户名称已更改: {old_name} -> {new_name}",
                extra={"user_id": self.id}
            )

    user = User(id=1, name="Alice")
    user.change_name("Alice Smith")


def main():
    """主函数 - 运行所有示例"""
    print("\n" + "=" * 60)
    print("DDD Framework 日志模块示例")
    print("=" * 60)

    try:
        example_1_simple_logging()

        print("\n" + "-" * 60)
        print("提示：以下示例需要安装可选依赖")
        print("  pip install loguru      # 安装 Loguru")
        print("  pip install logfire     # 安装 Logfire")
        print("-" * 60)

        example_2_loguru()
        example_3_logfire()
        example_4_switch_backend()
        example_5_in_domain_layer()

        print("\n" + "=" * 60)
        print("✅ 所有示例运行完成！")
        print("=" * 60)
        print("\n推荐配置：")
        print("  - 开发环境: LOG_BACKEND=loguru")
        print("  - 生产环境: LOG_BACKEND=logfire")
        print("  - 测试环境: LOG_BACKEND=simple")
        print()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
