# DDD Framework

Python 领域驱动设计（DDD）基础框架 - 开箱即用的 DDD 架构模板

## ✨ 特性

- 🏗️ **完整的 DDD 分层架构**：Domain、Application、Infrastructure 层清晰分离
- 🔄 **多环境自动切换**：test/dev 用 SQLite，staging/prod 用 Supabase，零配置
- 💉 **依赖注入容器**：基于 dependency-injector，管理所有依赖
- 🧪 **测试友好**：测试环境自动使用 SQLite 内存数据库，超快速
- 🔧 **通用工具集**：`common/` 模块提供常用工具函数
- 📦 **开箱即用**：复制即可使用，适合快速启动新项目

---

## 📁 项目结构

```
ddd-framework/
├── domain/                      # 🏛️ 领域层（核心业务逻辑）
│   └── common/                  # 领域基础类
│       ├── base_entity.py       # 实体基类
│       ├── base_aggregate.py    # 聚合根基类
│       ├── base_value_object.py # 值对象基类
│       ├── base_event.py        # 领域事件基类
│       ├── base_repository.py   # 仓储接口基类
│       ├── specification.py     # 规约模式
│       └── exceptions.py        # 领域异常
│
├── application/                 # 📦 应用层（用例编排）
│
├── infrastructure/              # ⚙️ 基础设施层（技术实现）
│   ├── database/                # 数据库
│   │   ├── database_factory.py  # ⭐ 数据库工厂（多环境自动切换）
│   │   └── unit_of_work.py      # 工作单元模式
│   ├── config/                  # 配置
│   │   └── settings.py          # 配置类
│   └── containers/              # 依赖注入容器
│       └── app_containers.py    # ⭐ 应用容器
│
├── common/                      # 🔧 通用工具（跨层使用）
│   └── logging/                 # 日志模块

```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
uv sync
```

---

## 📖 核心功能

### 1️⃣ 多环境数据库自动切换

框架会根据 `APP_ENV` 环境变量**自动选择数据库**：

| 环境 | 数据库 | 特点 |
|------|--------|------|
| **test** | SQLite 内存 | 超快速，用于测试 |
| **dev** | SQLite 文件 | 持久化，用于开发 |
| **staging** | Supabase | 预发布测试 |
| **prod** | Supabase | 生产环境 |

```python
import os
from infrastructure.database import get_engine

# 设置环境
os.environ["APP_ENV"] = "dev"

# 自动选择对应的数据库！
engine = get_engine()
```

---

### 2️⃣ 智能日志系统（自动环境适配）

框架会**根据环境自动选择日志后端**：

| 环境 | 日志后端 | 特点 |
|------|----------|------|
| **test / dev** | Loguru | 彩色输出，本地调试 |
| **staging / prod** | Logfire | 云端监控，分布式追踪 |

**使用方式（零配置）**：

```python
import os
from common.logging import get_logger

# 设置环境（仅此一次）
os.environ["APP_ENV"] = "dev"

# 日志自动使用 Loguru ✅
logger = get_logger(__name__)
logger.info("Hello, world!")
```

**自动适配规则**：

```bash
# 开发/测试环境
export APP_ENV=dev
# → 自动使用 Loguru（本地日志）

# 生产环境
export APP_ENV=prod
# → 自动使用 Logfire（云端监控）
```

**手动覆盖（可选）**：

```bash
# 强制使用 Loguru（即使在生产环境）
export APP_ENV=prod
export LOG_BACKEND=loguru  # 手动覆盖
```

**生产环境准备**：

```bash
# Logfire 需要认证（仅首次）
uv add logfire
logfire auth
```

---

## 📄 许可证

MIT License
