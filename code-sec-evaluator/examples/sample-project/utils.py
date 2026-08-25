# -*- coding: utf-8 -*-
"""示例项目工具模块（故意埋点，仅供安全评估演示）。

本文件包含路径穿越、弱加密、敏感信息泄露三类反模式。
"""
import hashlib
import logging
import os

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

logger = logging.getLogger("sample-project")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

# 硬编码 AES 密钥与 IV（漏洞：弱加密——硬编码密钥 + 固定 IV + ECB 模式）
AES_KEY = b"this-is-a-hardcoded-aes-key-1234"
HARDCODED_IV = b"1234567890123456"


def read_file(filename):
    """按文件名读取 data 目录下的文件。"""
    # 漏洞：用户输入直接拼接路径，未校验，可用 ../ 穿越（路径穿越）
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def hash_password_md5(password):
    """使用 MD5 存储口令（漏洞：弱加密）。"""
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def hash_password_sha1(password):
    """使用 SHA1 存储口令（漏洞：弱加密）。"""
    return hashlib.sha1(password.encode("utf-8")).hexdigest()


def encrypt_ecb(plaintext):
    """使用 AES-ECB 模式加密（漏洞：弱加密——ECB 模式 + 硬编码 IV）。"""
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    return cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))


def login(username, password):
    """模拟用户登录。"""
    # 漏洞：日志打印明文口令（敏感信息泄露）
    logger.info("User %s login with password: %s", username, password)
    return username == "admin" and password == "admin123"
