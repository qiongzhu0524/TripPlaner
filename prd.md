# 前端


#后端
- fastapi框架 pydantic V2参数约束
``` text
backend/
├── app/
│   ├── api/                # 路由层 (API Routes)
│   │   ├── dependencies.py # 依赖注入 (如: get_db, get_current_user)
│   │   └── v1/             # API 版本控制
│   │       └── users.py    # 具体的路由定义
│   ├── core/               # 核心配置层
│   │   ├── config.py       # 环境变量与全局配置 (pydantic-settings)
│   │   └── security.py     # 密码哈希、JWT 生成与校验
│   ├── db/                 # 数据库层
│   │   ├── base.py         # SQLAlchemy  declarative_base
│   │   └── session.py      # 数据库引擎与 Session 工厂
│   ├── models/             # 数据模型层 (ORM Models)
│   │   └── user.py         # 数据库表结构定义
│   ├── schemas/            # 数据校验层 (Pydantic Schemas)
│   │   └── user.py         # 请求体(Request)和响应体(Response)定义
│   ├── repositories/       # 数据访问层 (Repository / CRUD)
│   │   └── user.py         # 纯粹的数据库增删改查操作
│   ├── services/           # 业务逻辑层 (Service)
│   │   └── user.py         # 核心业务规则，调用 Repository
│   └── main.py             # 应用入口 (App 实例化、中间件、路由注册)
├── alembic/                # 数据库迁移脚本 (可选但推荐)
├── tests/                  # 测试层 (pytest)
├── .env                    # 环境变量
└── pyproject.toml          # 依赖包
```

