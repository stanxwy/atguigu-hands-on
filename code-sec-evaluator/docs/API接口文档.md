# 自动化安全评估系统 — API 接口文档

| 项目 | 内容 |
| --- | --- |
| 文档名称 | 自动化安全评估系统 API 接口文档 |
| 版本 | v1.0 |
| 日期 | 2026-08-25 |
| 作者 | 寇豆码（工程师） |
| 依据 | SPEC-自动化安全评估系统 v1.0（§2 数据模型、§3 API 接口设计、§1.3 认证决策） |
| 配套契约 | `docs/openapi.yaml`（OpenAPI 3.1 规范） |

---

## 1. 概览

本系统后端采用 **FastAPI**，对外提供 REST + WebSocket 两类接口：

- **REST 接口（20 个）**：覆盖系统初始化/登录/配置、项目生命周期、评估结果查询。
- **WebSocket 接口（1 个）**：`/api/projects/{project_id}/stream`，用于实时推送评估进度、日志、资源消耗等 8 种消息。

### 1.1 基础信息

| 项 | 值 |
| --- | --- |
| Base URL | `http://localhost:8000` |
| 数据格式 | `application/json`（报告下载接口为 `application/octet-stream`） |
| 认证方式 | JWT Bearer（无状态令牌） |
| 交互式文档 | `/docs`（Swagger UI）、`/redoc`（ReDoc） |
| OpenAPI 规范 | `openapi: 3.1.0`，见 `docs/openapi.yaml` |

---

## 2. 认证方式（JWT Bearer）

- 登录成功后返回 `access_token`（JWT），默认有效期 **24 小时**，可经系统配置调整。
- 除 `/api/system/init`、`/api/system/login` 外，所有接口均需在请求头携带：

```http
Authorization: Bearer <access_token>
```

- 系统配置读写接口（`GET/PUT /api/system/config`）额外要求管理员权限（`role == admin`），非管理员访问返回错误码 `1003`。
- WebSocket 握手时，通过查询参数 `?token=<jwt>` 或 `Authorization` 头进行鉴权。

---

## 3. 统一响应封装

所有 REST JSON 响应体统一为以下结构：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | 业务状态码，`0` 表示成功，非 `0` 表示业务错误 |
| message | string | 状态说明 |
| data | object / null | 业务数据；列表接口为 `{ list, total }`，详情接口为对象，错误时为 `null` |

- 列表数据统一返回 `data.list` + `data.total`；详情返回 `data` 对象。
- 例外：`GET /api/projects/{project_id}/report/download` 直接返回二进制文件流，不套用统一封装。

---

## 4. 错误码表

| code | HTTP 状态码 | 含义 |
| --- | --- | --- |
| 0 | 200 | 成功 |
| 1001 | 400 | 参数校验失败 |
| 1002 | 401 | 未认证 / 登录态失效 |
| 1003 | 403 | 权限不足（非管理员操作管理接口） |
| 1004 | 409 | 系统已初始化（重复初始化） |
| 2001 | 404 | 资源不存在 |
| 2002 | 409 | 状态冲突（如非 `created/completed/failed/stopped` 状态启动） |
| 3001 | 500 | 隔离环境异常（容器创建/启动失败） |
| 5000 | 500 | 内部错误 |

> HTTP 状态码约定：成功 `200`，参数错误 `400`，未认证 `401`，权限不足 `403`，资源不存在 `404`，冲突 `409`，内部错误 `500`。

---

## 5. REST 端点总览

> 与 `docs/openapi.yaml` 中 `paths` 一一对应，共 **20 个 REST 端点**。

### 5.1 认证与系统接口

| 方法 | 路径 | 说明 | 鉴权 | 关键请求字段 | 关键响应字段（data） |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/system/init` | 初始化管理员账户 | 无需 | `username`、`password`(8~64) | `id`、`username`、`role` |
| POST | `/api/system/login` | 登录 | 无需 | `username`、`password` | `access_token`、`token_type`、`expires_in`、`user` |
| GET | `/api/system/config` | 查询系统配置 | Bearer + admin | — | `isolation`、`task`、`retention` |
| PUT | `/api/system/config` | 更新系统配置 | Bearer + admin | `config`(键值对) | 更新后的配置片段 |

### 5.2 项目接口

| 方法 | 路径 | 说明 | 鉴权 | 关键请求字段/查询参数 | 关键响应字段（data） |
| --- | --- | --- | --- | --- | --- |
| POST | `/api/projects` | 创建项目 | Bearer | `project_name`(1~128)、`source_type`、`source_path`、`task_content`(可选) | 项目完整字段（含 `project_status=created`） |
| GET | `/api/projects` | 查询项目列表 | Bearer | `page`、`page_size`、`project_status` | `total` + `list[]` |
| GET | `/api/projects/{project_id}` | 查询项目详情 | Bearer | 路径参数 `project_id` | `project_status`、`vuln_count`、`attack_path_count`、`report_status` 等 |
| POST | `/api/projects/{project_id}/start` | 启动评估任务 | Bearer | 路径参数 `project_id`（请求体可空） | `project_id`、`project_status=running` |
| POST | `/api/projects/{project_id}/stop` | 停止评估任务 | Bearer | 路径参数 `project_id` | `project_id`、`project_status=stopped` |
| DELETE | `/api/projects/{project_id}` | 删除项目 | Bearer | 路径参数 `project_id` | `deleted_project_id` |

### 5.3 结果查询接口

| 方法 | 路径 | 说明 | 鉴权 | 关键查询参数 | 关键响应字段（data） |
| --- | --- | --- | --- | --- | --- |
| GET | `/api/projects/{project_id}/stages` | 查询阶段状态 | Bearer | — | `list[]`（`stage_name`/`stage_status`/时间） |
| GET | `/api/projects/{project_id}/workers` | 查询角色执行状态 | Bearer | — | `list[]`（`worker_role`/`task_status`/`stage_name`） |
| GET | `/api/projects/{project_id}/vulnerabilities` | 查询漏洞列表 | Bearer | `risk_level`、`verify_status`、`page`、`page_size` | `total` + `list[]` |
| GET | `/api/projects/{project_id}/vulnerabilities/{vuln_id}` | 查询漏洞详情 | Bearer | 路径参数 `vuln_id` | 漏洞完整字段 |
| GET | `/api/projects/{project_id}/attack-paths` | 查询攻击路径列表 | Bearer | — | `total` + `list[]` |
| GET | `/api/projects/{project_id}/attack-paths/{path_id}` | 查询攻击路径详情 | Bearer | 路径参数 `path_id` | 路径字段 + `items[]` |
| GET | `/api/projects/{project_id}/report` | 查询最终报告 | Bearer | — | `report_id`、`report_markdown`、`report_html` |
| GET | `/api/projects/{project_id}/report/download` | 下载报告（二进制） | Bearer | — | 文件流 `report-{project_id}.md` |
| GET | `/api/projects/{project_id}/logs` | 查询运行日志 | Bearer | `log_level`、`page`、`page_size` | `total` + `list[]` |
| GET | `/api/projects/{project_id}/resources` | 查询资源消耗 | Bearer | `limit`（默认 100） | `list[]`（`cpu_usage`/`memory_usage`/`token_count`） |

---

## 6. 端点请求/响应示例

### 6.1 POST /api/system/init

```json
// 请求
{"username":"admin","password":"Admin@123456"}

// 响应
{"code":0,"message":"success","data":{"id":1,"username":"admin","role":"admin"}}
```

> 仅当 `users` 表无 admin 用户时可调用；已初始化返回 `1004`。

### 6.2 POST /api/system/login

```json
// 请求
{"username":"admin","password":"Admin@123456"}

// 响应
{"code":0,"message":"success","data":{
  "access_token":"eyJhbGciOiJIUzI1NiIs...",
  "token_type":"Bearer",
  "expires_in":86400,
  "user":{"id":1,"username":"admin","role":"admin"}
}}
```

### 6.3 GET /api/system/config

```json
{"code":0,"message":"success","data":{
  "isolation":{"default_image":"sec-evaluator:latest","mount_readonly":true,"network_mode":"none"},
  "task":{"default_timeout_seconds":1800,"max_concurrency":2},
  "retention":{"days":30}
}}
```

### 6.4 PUT /api/system/config

```json
// 请求
{"config":{"task.max_concurrency":4,"task.default_timeout_seconds":3600}}

// 响应
{"code":0,"message":"success","data":{"task":{"default_timeout_seconds":3600,"max_concurrency":4}}}
```

### 6.5 POST /api/projects

```json
// 请求
{"project_name":"示例评估项目","source_type":"local_path","source_path":"/data/src/demo","task_content":"评估注入类漏洞"}

// 响应
{"code":0,"message":"success","data":{
  "id":1,"project_name":"示例评估项目","source_type":"local_path",
  "source_path":"/data/src/demo","task_content":"评估注入类漏洞",
  "project_status":"created","created_at":"2026-08-25T12:00:00Z"
}}
```

### 6.6 GET /api/projects

```json
{"code":0,"message":"success","data":{
  "total":1,
  "list":[{
    "id":1,"project_name":"示例评估项目","source_type":"local_path",
    "project_status":"completed",
    "last_started_at":"2026-08-25T12:01:00Z",
    "last_finished_at":"2026-08-25T12:20:00Z"
  }]
}}
```

### 6.7 GET /api/projects/{project_id}

```json
{"code":0,"message":"success","data":{
  "id":1,"project_name":"示例评估项目","source_type":"local_path",
  "source_path":"/data/src/demo","task_content":"评估注入类漏洞",
  "project_status":"running",
  "vuln_count":3,"attack_path_count":1,"report_status":"none",
  "created_at":"2026-08-25T12:00:00Z","updated_at":"2026-08-25T12:05:00Z"
}}
```

### 6.8 POST /api/projects/{project_id}/start

```json
// 前置校验：项目状态须为 created/completed/failed/stopped，否则返回 2002
{"code":0,"message":"success","data":{"project_id":1,"project_status":"running"}}
```

### 6.9 POST /api/projects/{project_id}/stop

```json
// 前置校验：项目状态须为 running
{"code":0,"message":"success","data":{"project_id":1,"project_status":"stopped"}}
```

### 6.10 DELETE /api/projects/{project_id}

```json
{"code":0,"message":"success","data":{"deleted_project_id":1}}
```

### 6.11 GET /api/projects/{project_id}/stages

```json
{"code":0,"message":"success","data":{
  "list":[
    {"stage_name":"environment_scan","stage_status":"success","started_at":"...","finished_at":"..."},
    {"stage_name":"code_analysis","stage_status":"running","started_at":"...","finished_at":null},
    {"stage_name":"vulnerability_verify","stage_status":"pending","started_at":null,"finished_at":null},
    {"stage_name":"report_generate","stage_status":"pending","started_at":null,"finished_at":null}
  ]
}}
```

### 6.12 GET /api/projects/{project_id}/workers

```json
{"code":0,"message":"success","data":{
  "list":[
    {"id":12,"worker_role":"code_analyze","task_status":"running","stage_name":"code_analysis","started_at":"...","finished_at":null}
  ]
}}
```

### 6.13 GET /api/projects/{project_id}/vulnerabilities

```json
{"code":0,"message":"success","data":{"total":3,"list":[
  {"id":8,"vuln_code":"VULN-0001","vuln_title":"SQL 注入","risk_level":"high","file_path":"src/UserService.java","verify_status":"verified","created_at":"..."}
]}}
```

### 6.14 GET /api/projects/{project_id}/vulnerabilities/{vuln_id}

```json
{"code":0,"message":"success","data":{
  "id":8,"vuln_code":"VULN-0001","vuln_title":"SQL 注入","risk_level":"high",
  "file_path":"src/UserService.java","condition_text":"未过滤用户输入","evidence_text":"...",
  "verify_status":"verified","reproduce_steps_text":"...","verify_code_text":"...","created_at":"..."
}}
```

### 6.15 GET /api/projects/{project_id}/attack-paths

```json
{"code":0,"message":"success","data":{"total":1,"list":[
  {"id":5,"path_code":"PATH-0001","path_title":"SQL 注入链","path_summary":"...","final_impact_text":"数据泄露","vuln_count":2,"created_at":"..."}
]}}
```

### 6.16 GET /api/projects/{project_id}/attack-paths/{path_id}

```json
{"code":0,"message":"success","data":{
  "id":5,"path_code":"PATH-0001","path_title":"SQL 注入链",
  "path_summary":"...","final_impact_text":"数据泄露",
  "items":[
    {"step_order":1,"step_text":"利用登录接口注入","vuln_id":8,"vuln_code":"VULN-0001","vuln_title":"SQL 注入"},
    {"step_order":2,"step_text":"读取敏感数据","vuln_id":9,"vuln_code":"VULN-0002","vuln_title":"敏感信息泄露"}
  ]
}}
```

### 6.17 GET /api/projects/{project_id}/report

```json
{"code":0,"message":"success","data":{
  "report_id":3,
  "report_markdown":"# 安全评估报告\n...",
  "report_html":"<h1>安全评估报告</h1>...",
  "created_at":"2026-08-25T12:20:00Z"
}}
```

### 6.18 GET /api/projects/{project_id}/report/download

- 返回 `application/octet-stream`，文件名为 `report-{project_id}.md`（P0 默认 Markdown）。

### 6.19 GET /api/projects/{project_id}/logs

```json
{"code":0,"message":"success","data":{"total":120,"list":[
  {"id":900,"log_level":"info","log_content":"扫描 /src 目录...","stage_name":"code_analysis","created_at":"..."}
]}}
```

### 6.20 GET /api/projects/{project_id}/resources

```json
{"code":0,"message":"success","data":{
  "list":[
    {"cpu_usage":42.5,"memory_usage":512.0,"token_count":12800,"recorded_at":"..."}
  ]
}}
```

---

## 7. WebSocket 接口说明

> OpenAPI 3.1 不原生支持 WebSocket，故本接口在本文档单独说明，未纳入 `openapi.yaml`。

### 7.1 WS /api/projects/{project_id}/stream —— 实时订阅

| 项 | 说明 |
| --- | --- |
| 握手地址 | `ws://<host>/api/projects/{project_id}/stream?token=<jwt>` |
| 鉴权 | 校验 token 与项目访问权限（`?token=` 或 `Authorization` 头） |
| 行为 | 连接后服务端推送 8 种实时消息，服务端不接收客户端消息（仅支持心跳 ping） |

**连接示例**：

```javascript
const ws = new WebSocket(`ws://localhost:8000/api/projects/${projectId}/stream?token=${token}`);
ws.onmessage = (e) => {
  const msg = JSON.parse(e.data); // msg.type ∈ {project_status, stage_status, ...}
};
```

### 7.2 消息外层结构

```json
{
  "type": "<消息类型>",
  "project_id": 1,
  "timestamp": "2026-08-25T12:00:00Z",
  "data": { }
}
```

### 7.3 8 种消息类型

| # | type | data 字段 | 说明 |
| --- | --- | --- | --- |
| 1 | `project_status` | `project_status` | 项目状态变化 |
| 2 | `stage_status` | `stage_name`、`stage_status` | 阶段状态变化 |
| 3 | `worker_status` | `worker_task_id`、`worker_role`、`task_status` | 角色任务状态变化 |
| 4 | `chat_message` | `worker_role`、`message_type`、`message_text` | 角色对话消息 |
| 5 | `runtime_log` | `log_level`、`log_content` | 运行日志 |
| 6 | `resource_usage` | `cpu_usage`、`memory_usage`、`token_count` | 资源消耗 |
| 7 | `vulnerability_found` | `vuln_id`、`vuln_title`、`risk_level` | 新发现漏洞 |
| 8 | `report_ready` | `report_id` | 报告生成完成 |

**消息 JSON 示例**：

```json
// 1. project_status
{"type":"project_status","project_id":1,"timestamp":"...","data":{"project_status":"running"}}

// 2. stage_status
{"type":"stage_status","project_id":1,"timestamp":"...","data":{"stage_name":"code_analysis","stage_status":"running"}}

// 3. worker_status
{"type":"worker_status","project_id":1,"timestamp":"...","data":{"worker_task_id":12,"worker_role":"code_analyze","task_status":"running"}}

// 4. chat_message
{"type":"chat_message","project_id":1,"timestamp":"...","data":{"worker_role":"code_analyze","message_type":"info","message_text":"开始目录遍历"}}

// 5. runtime_log
{"type":"runtime_log","project_id":1,"timestamp":"...","data":{"log_level":"info","log_content":"扫描 /src 目录..."}}

// 6. resource_usage
{"type":"resource_usage","project_id":1,"timestamp":"...","data":{"cpu_usage":42.5,"memory_usage":512.0,"token_count":12800}}

// 7. vulnerability_found
{"type":"vulnerability_found","project_id":1,"timestamp":"...","data":{"vuln_id":8,"vuln_title":"SQL 注入","risk_level":"high"}}

// 8. report_ready
{"type":"report_ready","project_id":1,"timestamp":"...","data":{"report_id":3}}
```

---

## 8. 数据模型与枚举对照

以下枚举取值与 SPEC §2、§3 一致：

| 枚举 | 取值 |
| --- | --- |
| source_type | `local_path` / `git_repo` |
| project_status | `created` / `running` / `completed` / `failed` / `stopped` |
| stage_name | `environment_scan` / `code_analysis` / `vulnerability_verify` / `report_generate` / `done` |
| stage_status | `pending` / `running` / `success` / `failed` |
| worker_role | `generic` / `env_check` / `code_analyze` / `vuln_verify` / `report_gen` / `ops` |
| task_status | `idle` / `running` / `success` / `failed` |
| risk_level | `critical` / `high` / `medium` / `low` |
| verify_status | `unverified` / `verifying` / `verified` / `failed` |
| log_level | `debug` / `info` / `warn` / `error` |
| message_type | `info` / `warning` / `error` / `critical` / `success` |

---

## 9. 如何查看文档

- **Swagger UI**：启动后端后访问 `http://localhost:8000/docs`，可视化调试全部 REST 接口。
- **ReDoc**：访问 `http://localhost:8000/redoc`，查看更适合阅读的 API 文档。
- **OpenAPI JSON**：FastAPI 默认在 `http://localhost:8000/openapi.json` 输出自动生成的 OpenAPI 规范。

### openapi.yaml 与 FastAPI 自动生成的关系

- FastAPI 会基于 **Pydantic schema** 与路由装饰器**自动生成** OpenAPI 文档（`/docs`、`/redoc`、`/openapi.json`）。
- 本仓库的 `docs/openapi.yaml` 是**手工维护的契约基线**（Contract Baseline），严格对齐 SPEC §3 的接口、请求/响应结构与错误码约定，供前端、测试、联调方先行参考，并在实现后与 FastAPI 自动生成文档做一致性核对。
- 两处差异如出现，以 **SPEC** 与 `docs/openapi.yaml`（契约）为准，回推修正后端 Pydantic 模型实现。

---

> **一致性声明**：本文档 REST 端点（20 个）、WebSocket 消息（8 种）、统一响应封装、错误码、枚举取值与 `docs/openapi.yaml` 及 SPEC v1.0 完全对齐。
