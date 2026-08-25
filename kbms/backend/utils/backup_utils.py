import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def backup_json(file_path: Path, json_data: dict | list ) -> None:
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(
                json_data,
                f,
                # 开启 True："title": "\u4e00\u7ea7\u6807\u9898"（乱码，无法直接看）；
                # 开启 False："title": "一级标题"（正常中文，人工可直接阅读）。
                ensure_ascii=False,
                indent=2
            )
        logger.debug(f"Successfully backed up json: {file_path}")
    except Exception as e:
        logger.exception(f"Error backing up json: {e!s}", stack_info=True)

def backup_file(file_path: Path, content: str) -> None:
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug(f"Successfully backed up file: {file_path}")
    except Exception as e:
        logger.exception(f"Error backing up file: {e!s}", stack_info=True)