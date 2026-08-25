# 自动化安全评估系统（Code Security Evaluator）

> 对源码项目进行自动化安全评估：接入源码 → 隔离环境扫描 → 代码分析 → 漏洞验证 → 攻击路径 → 报告输出。
> 完整规格见 `docs/`（PRD / SPEC / 编码规范 / 安全规范 / 测试规范 / 部署运维规范 / API 接口文档 / openapi.yaml）。

> [!WARNING]
> 本系统用于**授权范围内的安全评估**，严禁对未授权目标运行。

---

## 目录

- [后端启动](#后端启动)
- [端到端演示](#端到端演示)

---

## 后端启动

后端基于 **Python 3.11 + FastAPI + SQLAlchemy 2.0（异步）+ Pydantic v2**，依赖由 **pyproject.toml + uv** 管理。

### 1. 准备环境

```bash
cd backend

# 安装依赖（创建 .venv 并同步依赖，uv.lock 由 uv lock 生成）
uv sync

# 配置环境变量（首次：复制 .env.example 为 .env 并填入 SECRET_KEY）
cp .env.example .env
# 生成随机密钥（生产必须替换）：
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 2. 初始化数据库

```bash
# 建表 + 写入 system_config 种子（幂等）
uv run python scripts/init_db.py

# 初始化管理员（幂等；不传 --password 则交互式输入）
uv run python scripts/init_admin.py --username admin --password 'Admin@123456'
```

### 3. 启动服务

```bash
# 默认 http://localhost:8000（/docs 为 Swagger UI）
uv run uvicorn app.main:app --reload
```

> 说明：若未执行 `scripts/init_db.py`，应用启动时也会自动建表并写入配置种子（幂等）。
> 生产环境将 `DATABASE_URL` 切换为 MySQL（见 `.env.example`），业务 DDL 由 Alembic 迁移或 `init_db.py` 管理。

### 4. 端到端演示

```bash
# 从仓库根目录运行（后端已启动后）
python scripts/demo.py        # Windows 友好，零第三方依赖
# 或
bash scripts/demo.sh          # 需 bash + curl + jq
```

演示脚本将完成：初始化管理员 → 登录 → 创建项目 → 启动评估 → 轮询阶段 → 查询漏洞/攻击路径/报告 → 下载报告。

---

## 项目结构

```text
backend/              后端（FastAPI）
  app/
    api/              REST + WebSocket 路由（system / projects / results / ws）
    core/             常量 / JWT+bcrypt / 错误码
    models/           11 张业务表 + system_config（SQLAlchemy 2.0）
    schemas/          Pydantic v2 请求/响应模型（StrictModel）
    services/         调度 / 隔离 / 角色执行 / 报告 / 监控 / 配置
    ws/               WebSocket 连接管理 + 内存 Pub/Sub
    utils/            命令白名单 / 路径校验 / 日志脱敏 / 编号生成
    main.py           应用入口
  migrations/         Alembic 迁移
  rules/              内置关键字规则集
  scripts/            init_db.py / init_admin.py
db/init.sql           数据库与账号初始化（MySQL）
docker/evaluator.Dockerfile  隔离环境评估镜像
examples/sample-project/     含故意埋点漏洞的演示源码
scripts/demo.py|demo.sh      端到端演示脚本
```
