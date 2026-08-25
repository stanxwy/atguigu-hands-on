#!/usr/bin/env bash
# =============================================================================
# 自动化安全评估系统 — 端到端演示脚本（AC-7）
#
# 用法：
#   bash scripts/demo.sh
#   BASE_URL=http://localhost:8000 bash scripts/demo.sh
#   SOURCE_PATH=/abs/path/to/examples/sample-project bash scripts/demo.sh
#
# 依赖：curl、jq
# 说明：对齐《API接口文档》与《docs/openapi.yaml》的端点/字段/错误码。
# =============================================================================
set -euo pipefail

# -----------------------------------------------------------------------------
# 配置变量（集中在顶部，可经环境变量覆盖）
# -----------------------------------------------------------------------------
BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin@123456}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_PATH="${SOURCE_PATH:-${REPO_ROOT}/examples/sample-project}"

POLL_INTERVAL="${POLL_INTERVAL:-3}"     # 阶段轮询间隔（秒）
POLL_TIMEOUT="${POLL_TIMEOUT:-300}"     # 轮询总超时（秒）
OUTPUT_DIR="${OUTPUT_DIR:-${SCRIPT_DIR}/output}"

TOKEN=""            # 登录后写入的 JWT
HTTP_CODE=""        # 最近一次请求的 HTTP 状态码
BIZ_CODE=""         # 最近一次请求的业务状态码（响应体 .code）
BODY_FILE="$(mktemp)"   # 最近一次响应体临时文件

# -----------------------------------------------------------------------------
# 工具函数
# -----------------------------------------------------------------------------
log()  { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
info() { printf '[%s] \033[32m[INFO]\033[0m %s\n' "$(date '+%H:%M:%S')" "$*"; }
warn() { printf '[%s] \033[33m[WARN]\033[0m %s\n' "$(date '+%H:%M:%S')" "$*"; }
fail() { printf '[%s] \033[31m[FAIL]\033[0m %s\n' "$(date '+%H:%M:%S')" "$*"; exit 1; }

# 依赖检查
for _bin in curl jq; do
  command -v "$_bin" >/dev/null 2>&1 || fail "缺少依赖命令：${_bin}（请先安装）"
done

# do_request <METHOD> <PATH> [JSON_BODY]
#   执行请求，响应体写入 BODY_FILE，并设置全局 HTTP_CODE / BIZ_CODE
do_request() {
  local method="$1" path="$2" body="${3:-}"
  local curl_args=(-sS --max-time 60 -o "$BODY_FILE" -w '%{http_code}' -X "$method")
  if [ -n "$TOKEN" ]; then
    curl_args+=(-H "Authorization: Bearer ${TOKEN}")
  fi
  if [ -n "$body" ]; then
    curl_args+=(-H "Content-Type: application/json" -d "$body")
  fi
  HTTP_CODE="$(curl "${curl_args[@]}" "${BASE_URL}${path}" 2>/dev/null || true)"
  BIZ_CODE="$(jq -r '.code // empty' "$BODY_FILE" 2>/dev/null || true)"
}

# expect_ok <步骤名>   —— 校验 HTTP 200 且业务码 0
expect_ok() {
  local step="$1"
  if [ "$HTTP_CODE" != "200" ]; then
    fail "${step} 失败：HTTP ${HTTP_CODE}，响应：$(cat "$BODY_FILE")"
  fi
  if [ "$BIZ_CODE" != "0" ]; then
    fail "${step} 失败：业务码 ${BIZ_CODE}，响应：$(cat "$BODY_FILE")"
  fi
}

trap 'rm -f "$BODY_FILE"' EXIT

# =============================================================================
# 步骤 1/9：前置探活
# =============================================================================
info "=== 步骤 1/9：前置探活（${BASE_URL}）==="
probe_ok=0
for attempt in $(seq 1 10); do
  if curl -sS --max-time 2 -o /dev/null "${BASE_URL}/openapi.json"; then
    info "后端已就绪"
    probe_ok=1
    break
  fi
  warn "后端未就绪（第 ${attempt}/10 次），2 秒后重试…"
  sleep 2
done
[ "$probe_ok" = "1" ] || fail "无法连接后端 ${BASE_URL}，请确认已启动（uvicorn app.main:app --reload）"

# =============================================================================
# 步骤 2/9：初始化管理员（幂等：已初始化返回 1004 时跳过）
# =============================================================================
info "=== 步骤 2/9：初始化管理员 ==="
do_request POST "/api/system/init" \
  "$(jq -n --arg u "$ADMIN_USERNAME" --arg p "$ADMIN_PASSWORD" '{username:$u,password:$p}')"
if [ "$BIZ_CODE" = "1004" ]; then
  warn "系统已初始化（错误码 1004），跳过本步"
elif [ "$BIZ_CODE" = "0" ]; then
  info "管理员初始化成功：$(jq -c '.data' "$BODY_FILE")"
else
  fail "初始化失败：业务码 ${BIZ_CODE}，响应：$(cat "$BODY_FILE")"
fi

# =============================================================================
# 步骤 3/9：登录获取 access_token
# =============================================================================
info "=== 步骤 3/9：登录 ==="
do_request POST "/api/system/login" \
  "$(jq -n --arg u "$ADMIN_USERNAME" --arg p "$ADMIN_PASSWORD" '{username:$u,password:$p}')"
expect_ok "登录"
TOKEN="$(jq -r '.data.access_token' "$BODY_FILE")"
if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  fail "登录未返回 access_token，响应：$(cat "$BODY_FILE")"
fi
info "登录成功，已获取 access_token（${#TOKEN} 字符）"

# =============================================================================
# 步骤 4/9：创建项目
# =============================================================================
info "=== 步骤 4/9：创建项目（幂等：同名已存在则复用）==="
if [ ! -d "$SOURCE_PATH" ]; then
  fail "示例项目源码目录不存在：${SOURCE_PATH}"
fi
info "使用示例源码：${SOURCE_PATH}"
PROJECT_NAME="示例项目端到端演示"
do_request GET "/api/projects?page_size=100"
[ "$BIZ_CODE" = "0" ] || fail "查询项目列表失败：$(cat "$BODY_FILE")"
PROJECT_ID="$(jq -r --arg n "$PROJECT_NAME" \
  '.data.list[]? | select(.project_name == $n) | .id' "$BODY_FILE" | head -n1)"
if [ -n "$PROJECT_ID" ] && [ "$PROJECT_ID" != "null" ]; then
  info "复用已存在项目：id=${PROJECT_ID}"
else
  do_request POST "/api/projects" \
    "$(jq -n --arg n "$PROJECT_NAME" --arg p "${SOURCE_PATH}" \
      '{project_name:$n, source_type:"local_path", source_path:$p,
        task_content:"评估注入类、XSS、硬编码密钥、路径穿越、弱加密、敏感信息泄露漏洞"}')"
  expect_ok "创建项目"
  PROJECT_ID="$(jq -r '.data.id' "$BODY_FILE")"
  info "项目创建成功：id=${PROJECT_ID}"
fi

# =============================================================================
# 步骤 5/9：启动评估（已在运行则跳过，避免状态冲突 2002）
# =============================================================================
info "=== 步骤 5/9：启动评估 ==="
do_request GET "/api/projects/${PROJECT_ID}"
[ "$BIZ_CODE" = "0" ] || fail "查询项目详情失败：$(cat "$BODY_FILE")"
CUR_STATUS="$(jq -r '.data.project_status' "$BODY_FILE")"
if [ "$CUR_STATUS" = "running" ]; then
  info "项目已在运行中（状态=running），跳过启动"
else
  do_request POST "/api/projects/${PROJECT_ID}/start" "{}"
  expect_ok "启动评估"
  info "启动受理成功：状态=$(jq -r '.data.project_status' "$BODY_FILE")"
fi

# =============================================================================
# 步骤 6/9：轮询阶段直到 completed（failed 则报错退出）
# =============================================================================
info "=== 步骤 6/9：轮询阶段状态（间隔 ${POLL_INTERVAL}s / 超时 ${POLL_TIMEOUT}s）==="
STATUS="running"
elapsed=0
while true; do
  do_request GET "/api/projects/${PROJECT_ID}"
  [ "$BIZ_CODE" = "0" ] || fail "查询项目详情失败：$(cat "$BODY_FILE")"
  STATUS="$(jq -r '.data.project_status' "$BODY_FILE")"

  do_request GET "/api/projects/${PROJECT_ID}/stages"
  STAGES="$(jq -r '[.data.list[]? | "\(.stage_name)=\(.stage_status)"] | join(" ")' "$BODY_FILE")"
  info "项目状态=${STATUS} | 阶段：[${STAGES}]"

  if [ "$STATUS" = "completed" ]; then
    info "评估已完成"
    break
  fi
  if [ "$STATUS" = "failed" ]; then
    fail "评估失败（project_status=failed），请查询运行日志定位原因"
  fi
  if [ "$elapsed" -ge "$POLL_TIMEOUT" ]; then
    fail "等待超时（${POLL_TIMEOUT}s），项目仍处于 ${STATUS}"
  fi
  sleep "$POLL_INTERVAL"
  elapsed=$((elapsed + POLL_INTERVAL))
done

# =============================================================================
# 步骤 7/9：查询结果（漏洞 / 攻击路径 / 报告）
# =============================================================================
info "=== 步骤 7/9：查询结果 ==="
do_request GET "/api/projects/${PROJECT_ID}/vulnerabilities?page_size=100"
expect_ok "查询漏洞列表"
VULN_TOTAL="$(jq -r '.data.total' "$BODY_FILE")"
info "漏洞总数：${VULN_TOTAL}"
jq -r '.data.list[]? | "  - [\(.risk_level)] \(.vuln_code) \(.vuln_title) @ \(.file_path // "-") (verify=\(.verify_status))"' "$BODY_FILE"

do_request GET "/api/projects/${PROJECT_ID}/attack-paths"
expect_ok "查询攻击路径"
PATH_TOTAL="$(jq -r '.data.total' "$BODY_FILE")"
info "攻击路径总数：${PATH_TOTAL}"
jq -r '.data.list[]? | "  - \(.path_code) \(.path_title)（关联漏洞 \(.vuln_count) 个）"' "$BODY_FILE"

do_request GET "/api/projects/${PROJECT_ID}/report"
expect_ok "查询报告"
REPORT_ID="$(jq -r '.data.report_id' "$BODY_FILE")"
REPORT_MD_LEN="$(jq -r '.data.report_markdown | length' "$BODY_FILE")"
info "报告已生成：report_id=${REPORT_ID}，Markdown 长度=${REPORT_MD_LEN} 字符"

# =============================================================================
# 步骤 8/9：下载报告
# =============================================================================
info "=== 步骤 8/9：下载报告 ==="
mkdir -p "$OUTPUT_DIR"
REPORT_FILE="${OUTPUT_DIR}/report-${PROJECT_ID}.md"
DL_CODE="$(curl -sS --max-time 60 -o "$REPORT_FILE" -w '%{http_code}' \
  -H "Authorization: Bearer ${TOKEN}" \
  "${BASE_URL}/api/projects/${PROJECT_ID}/report/download" 2>/dev/null || true)"
[ "$DL_CODE" = "200" ] || fail "报告下载失败：HTTP ${DL_CODE}"
info "报告已下载：${REPORT_FILE}（$(wc -c < "$REPORT_FILE") 字节）"

# =============================================================================
# 步骤 9/9：汇总
# =============================================================================
info "=== 步骤 9/9：汇总 ==="
echo ""
echo "=================================================="
echo " 自动化安全评估系统 — 端到端演示完成"
echo "=================================================="
echo "  项目 ID    : ${PROJECT_ID}"
echo "  项目状态   : ${STATUS}"
echo "  漏洞数     : ${VULN_TOTAL}"
echo "  攻击路径数 : ${PATH_TOTAL}"
echo "  报告 ID    : ${REPORT_ID}"
echo "  报告文件   : ${REPORT_FILE}"
echo "=================================================="
