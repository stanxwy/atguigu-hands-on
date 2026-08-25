#!/usr/bin/env python3
"""初始化数据库：建表 + 写入 system_config 种子（幂等）。

用法（在 backend/ 目录下执行）：
    python scripts/init_db.py
    # 或经 uv：uv run python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# 确保以任意工作目录调用时都能导入 app 包
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import async_session_factory, init_models  # noqa: E402
from app.services.config_service import seed_configs  # noqa: E402


async def main() -> None:
    """执行建表与种子写入。"""
    await init_models()
    async with async_session_factory() as db:
        await seed_configs(db)
        await db.commit()
    print("[init_db] 数据库初始化完成：建表 + system_config 种子已写入")


if __name__ == "__main__":
    asyncio.run(main())
