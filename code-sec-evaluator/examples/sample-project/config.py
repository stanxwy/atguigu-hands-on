# -*- coding: utf-8 -*-
"""示例项目配置模块（故意埋点，仅供安全评估演示）。

本文件集中存放硬编码的密钥、口令与连接串，模拟真实项目中
「敏感信息硬编码」与「弱口令」的反模式。
"""

# 数据库连接串（内含明文口令）
DATABASE_URL = "mysql+pymysql://root:admin123@localhost:3306/sample_db"

# 云服务访问密钥（硬编码）
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

# 支付服务 API Key（硬编码）
PAYMENT_API_KEY = "pk_live_51Hxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# SMTP 邮箱口令（硬编码）
SMTP_PASSWORD = "P@ssw0rd!2024"

# 短信服务密钥（硬编码）
SMS_APP_SECRET = "sms-secret-9a8b7c6d5e4f"

# 弱口令字典（演示弱口令风险）
DEFAULT_PASSWORDS = ["admin", "admin123", "123456", "password", "qwerty"]
