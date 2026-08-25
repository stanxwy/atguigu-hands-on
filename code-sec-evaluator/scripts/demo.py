#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动化安全评估系统 — 端到端演示脚本（Python 版，Windows 开发环境友好）。

用法：
    python scripts/demo.py
    # 或经环境变量覆盖：
    #   BASE_URL / ADMIN_USERNAME / ADMIN_PASSWORD / SOURCE_PATH / POLL_TIMEOUT

零第三方依赖（仅标准库 urllib/json），对齐《API接口文档》与 openapi.yaml。
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# 配置（集中在顶部，可经环境变量覆盖）
# ---------------------------------------------------------------------------
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000").rstrip("/")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@123456")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
SOURCE_PATH = os.environ.get("SOURCE_PATH") or os.path.join(
    REPO_ROOT, "examples", "sample-project"
)

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "3"))
POLL_TIMEOUT = int(os.environ.get("POLL_TIMEOUT", "300"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR") or os.path.join(SCRIPT_DIR, "output")

TOKEN = ""


def info(msg):
    print("[%s] [INFO] %s" % (time.strftime("%H:%M:%S"), msg))


def warn(msg):
    print("[%s] [WARN] %s" % (time.strftime("%H:%M:%S"), msg))


def fail(msg):
    print("[%s] [FAIL] %s" % (time.strftime("%H:%M:%S"), msg))
    sys.exit(1)


def request(method, path, body=None):
    """发起请求，返回 (HTTP 状态码, bytes 响应体)。"""
    url = BASE_URL + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()
    except urllib.error.URLError as exc:
        return 0, str(exc.reason).encode("utf-8")


def parse_json(raw):
    """解析响应体为 dict，失败返回空 dict。"""
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, AttributeError):
        return {}


def expect_ok(status, payload, step):
    if status != 200:
        fail("%s 失败：HTTP %s，响应：%s" % (step, status, payload))
    if payload.get("code") != 0:
        fail("%s 失败：业务码 %s，响应：%s" % (step, payload.get("code"), payload))


def main():
    global TOKEN

    # 1/9 前置探活
    info("=== 步骤 1/9：前置探活（%s）===" % BASE_URL)
    probe_ok = False
    for attempt in range(1, 11):
        status, _ = request("GET", "/openapi.json")
        if status == 200:
            info("后端已就绪")
            probe_ok = True
            break
        warn("后端未就绪（第 %d/10 次），2 秒后重试…" % attempt)
        time.sleep(2)
    if not probe_ok:
        fail("无法连接后端 %s，请确认已启动（uvicorn app.main:app --reload）" % BASE_URL)

    # 2/9 初始化管理员（幂等：1004 跳过）
    info("=== 步骤 2/9：初始化管理员 ===")
    status, raw = request("POST", "/api/system/init",
                          {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    payload = parse_json(raw)
    if payload.get("code") == 1004:
        warn("系统已初始化（错误码 1004），跳过本步")
    elif payload.get("code") == 0:
        info("管理员初始化成功：%s" % json.dumps(payload.get("data"), ensure_ascii=False))
    else:
        fail("初始化失败：业务码 %s，响应：%s" % (payload.get("code"), payload))

    # 3/9 登录
    info("=== 步骤 3/9：登录 ===")
    status, raw = request("POST", "/api/system/login",
                          {"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD})
    payload = parse_json(raw)
    expect_ok(status, payload, "登录")
    TOKEN = (payload.get("data") or {}).get("access_token", "")
    if not TOKEN:
        fail("登录未返回 access_token，响应：%s" % payload)
    info("登录成功，已获取 access_token（%d 字符）" % len(TOKEN))

    # 4/9 创建项目（幂等：同名已存在则复用）
    info("=== 步骤 4/9：创建项目（幂等：同名已存在则复用）===")
    if not os.path.isdir(SOURCE_PATH):
        fail("示例项目源码目录不存在：%s" % SOURCE_PATH)
    info("使用示例源码：%s" % SOURCE_PATH)
    project_name = "示例项目端到端演示"
    status, raw = request("GET", "/api/projects?page_size=100")
    payload = parse_json(raw)
    if payload.get("code") != 0:
        fail("查询项目列表失败：%s" % payload)
    project_id = next(
        (p["id"] for p in payload["data"]["list"] if p.get("project_name") == project_name),
        None,
    )
    if project_id:
        info("复用已存在项目：id=%s" % project_id)
    else:
        status, raw = request("POST", "/api/projects", {
            "project_name": project_name,
            "source_type": "local_path",
            "source_path": SOURCE_PATH,
            "task_content": "评估注入类、XSS、硬编码密钥、路径穿越、弱加密、敏感信息泄露漏洞",
        })
        payload = parse_json(raw)
        expect_ok(status, payload, "创建项目")
        project_id = payload["data"]["id"]
        info("项目创建成功：id=%s" % project_id)

    # 5/9 启动评估（已在运行则跳过，避免状态冲突 2002）
    info("=== 步骤 5/9：启动评估 ===")
    status, raw = request("GET", "/api/projects/%s" % project_id)
    payload = parse_json(raw)
    if payload.get("code") != 0:
        fail("查询项目详情失败：%s" % payload)
    if payload["data"]["project_status"] == "running":
        info("项目已在运行中（状态=running），跳过启动")
    else:
        status, raw = request("POST", "/api/projects/%s/start" % project_id, {})
        payload = parse_json(raw)
        expect_ok(status, payload, "启动评估")
        info("启动受理成功：状态=%s" % payload["data"]["project_status"])

    # 6/9 轮询阶段
    info("=== 步骤 6/9：轮询阶段状态（间隔 %ds / 超时 %ds）===" % (POLL_INTERVAL, POLL_TIMEOUT))
    status_name = "running"
    elapsed = 0
    while True:
        status, raw = request("GET", "/api/projects/%s" % project_id)
        payload = parse_json(raw)
        if payload.get("code") != 0:
            fail("查询项目详情失败：%s" % payload)
        status_name = payload["data"]["project_status"]

        status, raw = request("GET", "/api/projects/%s/stages" % project_id)
        stages = parse_json(raw)
        stage_str = " ".join(
            "%s=%s" % (s.get("stage_name"), s.get("stage_status"))
            for s in (stages.get("data") or {}).get("list", [])
        )
        info("项目状态=%s | 阶段：[%s]" % (status_name, stage_str))

        if status_name == "completed":
            info("评估已完成")
            break
        if status_name == "failed":
            fail("评估失败（project_status=failed），请查询运行日志定位原因")
        if elapsed >= POLL_TIMEOUT:
            fail("等待超时（%ds），项目仍处于 %s" % (POLL_TIMEOUT, status_name))
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    # 7/9 查询结果
    info("=== 步骤 7/9：查询结果 ===")
    status, raw = request("GET", "/api/projects/%s/vulnerabilities?page_size=100" % project_id)
    payload = parse_json(raw)
    expect_ok(status, payload, "查询漏洞列表")
    vuln_total = payload["data"]["total"]
    info("漏洞总数：%s" % vuln_total)
    for v in payload["data"]["list"]:
        info("  - [%s] %s %s @ %s (verify=%s)" % (
            v.get("risk_level"), v.get("vuln_code"), v.get("vuln_title"),
            v.get("file_path") or "-", v.get("verify_status"),
        ))

    status, raw = request("GET", "/api/projects/%s/attack-paths" % project_id)
    payload = parse_json(raw)
    expect_ok(status, payload, "查询攻击路径")
    path_total = payload["data"]["total"]
    info("攻击路径总数：%s" % path_total)
    for p in payload["data"]["list"]:
        info("  - %s %s（关联漏洞 %s 个）" % (
            p.get("path_code"), p.get("path_title"), p.get("vuln_count"),
        ))

    status, raw = request("GET", "/api/projects/%s/report" % project_id)
    payload = parse_json(raw)
    expect_ok(status, payload, "查询报告")
    report_id = payload["data"]["report_id"]
    report_md_len = len(payload["data"].get("report_markdown") or "")
    info("报告已生成：report_id=%s，Markdown 长度=%d 字符" % (report_id, report_md_len))

    # 8/9 下载报告
    info("=== 步骤 8/9：下载报告 ===")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    report_file = os.path.join(OUTPUT_DIR, "report-%s.md" % project_id)
    status, raw = request("GET", "/api/projects/%s/report/download" % project_id)
    if status != 200:
        fail("报告下载失败：HTTP %s" % status)
    with open(report_file, "wb") as fh:
        fh.write(raw)
    info("报告已下载：%s（%d 字节）" % (report_file, os.path.getsize(report_file)))

    # 9/9 汇总
    info("=== 步骤 9/9：汇总 ===")
    print("")
    print("==================================================")
    print(" 自动化安全评估系统 — 端到端演示完成")
    print("==================================================")
    print("  项目 ID    : %s" % project_id)
    print("  项目状态   : %s" % status_name)
    print("  漏洞数     : %s" % vuln_total)
    print("  攻击路径数 : %s" % path_total)
    print("  报告 ID    : %s" % report_id)
    print("  报告文件   : %s" % report_file)
    print("==================================================")


if __name__ == "__main__":
    main()
