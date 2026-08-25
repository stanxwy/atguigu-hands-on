# 示例项目（sample-project）

> 一份「看起来能跑、实则漏洞百出」的演示源码，用于验证自动化安全评估系统的
> **接入 → 关键字搜索 → 代码分析 → 漏洞验证 → 攻击路径 → 报告输出** 完整闭环（AC-7）。

> [!WARNING]
> 本项目包含**真实可利用的安全漏洞**，仅用于授权范围内的安全评估演示，
> **严禁在任何生产环境、对外服务或未授权目标上运行或部署**。

---

## 1. 项目结构

```text
examples/sample-project/
├── README.md              # 本文件（埋点漏洞清单 + 攻击路径 + 演示说明）
├── requirements.txt       # Flask + pycryptodome（弱加密演示用）
├── app.py                 # Web 主程序（SQL 注入、命令注入、XSS、硬编码密钥、debug=True）
├── config.py              # 硬编码密钥/口令/弱口令字典（环境扫描可发现）
├── utils.py               # 路径穿越、弱加密（MD5/SHA1/ECB）、敏感日志
├── templates/
│   └── index.html         # 反射型 XSS（| safe + innerHTML）
└── db/
    ├── query.sql          # 拼接 SQL 示例
    └── seed.sql           # 明文口令种子数据
```

技术栈：Python 3.11 + Flask + SQLite（演示用），跨语言混排模拟真实项目特征。

---

## 2. 埋点漏洞清单表

> 共 **9 处**漏洞，覆盖 **7 大类**（SQL 注入 / 命令注入 / XSS / 硬编码密钥 / 路径穿越 / 弱加密 / 敏感信息泄露），
> 横跨 **4 档风险等级**（critical / high / medium / low）。

| # | 位置（文件:行号） | 漏洞类型 | 风险等级 | 触发方式 / 关键字特征 | 发现角色 |
| --- | --- | --- | --- | --- | --- |
| 1 | `app.py:42` | SQL 注入 | high | 请求 `/api/user?name=' OR '1'='1--`；关键字 `SELECT` + 字符串拼接 | code_analyze（关键字搜索） |
| 2 | `app.py:53` | 命令注入 | critical | 请求 `/api/ping?host=; whoami`；关键字 `os.system` + 拼接 | code_analyze |
| 3 | `app.py:62-63` | 命令注入 | critical | 请求 `/api/report?file=; id`；关键字 `subprocess` + `shell=True` | code_analyze |
| 4 | `app.py:73` / `templates/index.html:12,17` | 反射型 XSS | medium | 请求 `/?q=<script>alert(1)</script>`；关键字 `render_template_string`、`\| safe`、`innerHTML` | code_analyze |
| 5 | `app.py:18-20,23` / `config.py:9,12-13,16,19,22` | 硬编码密钥/口令 | critical | 关键字 `api_key`、`password`、`secret`、`DATABASE_URL`、`AWS_` 等明文常量 | env_check（环境扫描） + code_analyze |
| 6 | `utils.py:26` | 路径穿越 | high | 请求 `read_file("../../etc/passwd")`；关键字 `os.path.join` + 未校验用户输入 | code_analyze |
| 7 | `utils.py:19-20,33,38,43` | 弱加密 | medium | 关键字 `md5`、`sha1`、`AES.MODE_ECB`、硬编码 IV | code_analyze |
| 8 | `utils.py:50` / `db/seed.sql:3-6` | 敏感信息泄露 | medium | 日志打印明文口令；种子数据明文口令存储 | code_analyze（日志审查） + ops |
| 9 | `app.py:85` | 调试模式开启 | low | 关键字 `debug=True`，暴露调试器 | env_check（环境扫描） |

### 2.1 六类角色与发现分工

| 角色 | 职责 | 在本示例中的发现 |
| --- | --- | --- |
| `generic` | 通用任务编排 / 兜底 | 任务分发 |
| `env_check` | 环境扫描（结构、依赖、配置、运行参数） | 硬编码密钥（config.py）、`debug=True` |
| `code_analyze` | 代码分析（关键字搜索 + 静态分析） | SQL/命令注入、XSS、路径穿越、弱加密、敏感日志 |
| `vuln_verify` | 漏洞验证（复现 / 确认） | 对以上候选漏洞逐一验证，产出 `verify_status` |
| `report_gen` | 报告生成 | 汇总漏洞、串联攻击路径、输出 Markdown/HTML 报告 |
| `ops` | 运维巡检（日志规范 / 资源） | 敏感信息泄露（日志打印口令）复核 |

> 说明：表中「发现角色」为**首次标记**该漏洞的角色；所有候选漏洞随后统一经
> `vuln_verify` 验证、`report_gen` 聚合入报告。

---

## 3. 攻击路径（Attack Path）

### 主路径：SQL 注入 → 拖库 → 明文口令 → 硬编码凭据 → 命令注入 → 服务器沦陷

| 步骤 | 利用的漏洞（位置） | 攻击动作 | 结果 |
| --- | --- | --- | --- |
| 1 | SQL 注入（`app.py:42`） | 向 `/api/user` 注入 `' OR '1'='1--` | 绕过查询条件，拖出 `users` 表全部记录 |
| 2 | 明文口令（`db/seed.sql:3-6`） | 读取被拖出的口令字段 | 获得 `admin` 等账号明文弱口令 |
| 3 | 硬编码凭据（`app.py:19-20`、`config.py:9`） | 从源码提取 `DB_PASSWORD`、`API_KEY`、`DATABASE_URL` | 获得数据库与第三方服务凭据 |
| 4 | 命令注入（`app.py:53` / `app.py:62-63`） | 注入 `; whoami` / `; cat /etc/passwd` 执行任意命令 | 获得服务器 shell 执行能力 |
| 5 | 路径穿越（`utils.py:26`） | 构造 `../../etc/passwd` 读取任意文件 | 读取越权敏感文件 |
| — | **最终影响** | — | **服务器完全沦陷 + 敏感数据大范围泄露** |

### 辅路径：反射型 XSS → 窃取会话 → 越权操作

`app.py:73` 与 `templates/index.html:12,17` 将用户输入未转义渲染，
攻击者可注入恶意脚本窃取管理员会话 Cookie，进而以管理员身份越权操作。

---

## 4. 如何运行演示（AC-7 端到端）

### 4.1 启动后端

```bash
cd backend
pip install -r requirements.txt
# 首次启动：初始化数据库（建表 + system_config）
python scripts/init_db.py
# 启动服务（默认 http://localhost:8000）
uvicorn app.main:app --reload
```

### 4.2 运行演示脚本

```bash
# Bash 版（bash + curl + jq，Linux/macOS/Git Bash）
bash scripts/demo.sh

# 可选覆盖配置
BASE_URL=http://localhost:8000 \
SOURCE_PATH=/abs/path/to/examples/sample-project \
bash scripts/demo.sh

# Python 版（Windows 开发环境友好，零第三方依赖）
python scripts/demo.py
```

### 4.3 演示脚本执行步骤（对齐 API 接口文档）

1. 前置探活：探测 `GET /openapi.json`，确认后端已起；
2. 初始化管理员：`POST /api/system/init`（已初始化返回 `1004` 时幂等跳过）；
3. 登录：`POST /api/system/login` 获取 `access_token`；
4. 创建项目：`POST /api/projects`（`source_type=local_path`，`source_path` 指向本示例项目）；
5. 启动：`POST /api/projects/{id}/start`；
6. 轮询：`GET /api/projects/{id}` + `GET /api/projects/{id}/stages` 直到 `completed`（`failed` 则报错退出）；
7. 查询结果：`GET .../vulnerabilities`、`GET .../attack-paths`、`GET .../report`；
8. 下载报告：`GET .../report/download` → 本地 `report-{id}.md`；
9. 汇总打印：漏洞数、攻击路径数、报告路径。

### 4.4 预期输出（摘要）

```text
[INFO] 漏洞总数：9
[INFO] 攻击路径总数：>=1
[INFO] 报告已下载：output/report-{id}.md
```

---

## 5. 关键字命中对照（供规则集回归验证）

| 规则关键字 | 命中位置 |
| --- | --- |
| `SELECT` | `app.py:42`、`db/query.sql:3,13` |
| `os.system` | `app.py:53` |
| `subprocess` / `shell=True` | `app.py:62-63` |
| `render_template_string` / `safe` / `innerHTML` | `app.py:73`、`templates/index.html:12,17` |
| `api_key` / `password` / `secret` / `DATABASE_URL` | `app.py:19-20`、`config.py` 全篇、`utils.py:50` |
| `os.path.join` | `utils.py:26` |
| `md5` / `sha1` / `ECB` | `utils.py:33,38,43` |
| `debug=True` | `app.py:85` |
