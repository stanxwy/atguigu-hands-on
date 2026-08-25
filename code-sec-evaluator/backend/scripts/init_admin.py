#!/usr/bin/env python3
"""命令行初始化管理员账户（幂等：已存在管理员则提示并退出）。

用法（在 backend/ 目录下执行）：
    python scripts/init_admin.py --username admin --password 'Admin@123456'
    # 不传 --password 时交互式输入（不回显）
"""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.errors import AlreadyInitializedError  # noqa: E402
from app.database import async_session_factory, init_models  # noqa: E402
from app.services.auth_service import init_admin  # noqa: E402


async def main(username: str, password: str) -> None:
    """建表并创建首个管理员。"""
    await init_models()
    async with async_session_factory() as db:
        try:
            user = await init_admin(db, username, password)
            await db.commit()
            print(f"[init_admin] 管理员 {user.username} 创建成功（id={user.id}）")
        except AlreadyInitializedError:
            print("[init_admin] 系统已初始化，跳过创建（如需重建请清空 users 表）")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化管理员账户")
    parser.add_argument("--username", default="admin", help="管理员用户名（默认 admin）")
    parser.add_argument("--password", default=None, help="管理员密码（缺省交互式输入）")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    password = args.password or getpass.getpass("请输入管理员密码（8~64 位）：")
    asyncio.run(main(args.username, password))
