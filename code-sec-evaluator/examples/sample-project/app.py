# -*- coding: utf-8 -*-
"""示例项目主程序（故意埋点，仅供安全评估演示）。

本文件是一份「看起来能跑、实则漏洞百出」的 Web 服务入口，专门用于验证
自动化安全评估系统的「关键字搜索 -> 代码分析 -> 漏洞验证」能力。

!! 警告：本文件包含真实可利用的安全漏洞，请勿在任何生产环境运行 !!
"""
import os
import sqlite3
import subprocess

from flask import Flask, jsonify, render_template, render_template_string, request

# =====================================================================
# 漏洞：硬编码密钥 / 口令（敏感信息硬编码）
# =====================================================================
FLASK_SECRET_KEY = "hardcoded-flask-secret-key-2024"   # 硬编码 Flask 密钥
API_KEY = "sk-live-9f8e7d6c5b4a3210a1b2c3d4e5f60718"    # 硬编码第三方 API Key
DB_PASSWORD = "Sup3rS3cret!Passw0rd"                    # 硬编码数据库口令

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# 数据库文件路径（SQLite，演示用）
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db")


def get_db():
    """获取数据库连接（行工厂便于转 dict）。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/api/user")
def get_user():
    """按用户名查询用户信息。"""
    username = request.args.get("name", "")
    conn = get_db()
    # 漏洞：直接字符串拼接 SQL，未参数化（SQL 注入）
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    row = conn.execute(query).fetchone()
    conn.close()
    return jsonify(dict(row) if row else {"error": "user not found"})


@app.route("/api/ping")
def ping():
    """对目标主机执行 ping 探测。"""
    host = request.args.get("host", "127.0.0.1")
    # 漏洞：os.system 拼接用户输入执行 shell（命令注入）
    os.system("ping -c 1 " + host)
    return jsonify({"status": "ok", "host": host})


@app.route("/api/report")
def report():
    """读取报告文件内容。"""
    filename = request.args.get("file", "report.txt")
    # 漏洞：subprocess + shell=True 拼接用户输入（命令注入）
    output = subprocess.run(
        "cat " + filename, shell=True, capture_output=True, text=True
    )
    return output.stdout


@app.route("/")
def index():
    """首页（反射型 XSS：服务端拼接未转义用户输入）。"""
    q = request.args.get("q", "")
    # 漏洞：render_template_string 直接拼接用户输入渲染 HTML，未转义
    return render_template_string("<h1>示例项目</h1><p>搜索关键词：" + q + "</p>")


@app.route("/search")
def search():
    """搜索页（反射型 XSS：模板中使用 | safe 输出用户输入）。"""
    q = request.args.get("q", "")
    return render_template("index.html", query=q)


if __name__ == "__main__":
    # 漏洞：debug=True 开启调试模式（敏感信息泄露 / 调试接口暴露）
    app.run(host="0.0.0.0", port=5000, debug=True)
