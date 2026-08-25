import logging
import os
from logging.handlers import TimedRotatingFileHandler

import colorlog


def setup_logging(level: int = logging.INFO, log_dir: str = "./logs"):

    os.makedirs(log_dir, exist_ok=True)
    
    # log_filename = f"app_{datetime.now().strftime('%Y%m%d')}.log"
    # log_filepath = os.path.join(log_dir, log_filename)
    log_filepath = os.path.join(log_dir, "knowledge_base.log")

    logger = logging.getLogger()
    logger.setLevel(level)
    
    if logger.hasHandlers():
        logger.handlers.clear()
    
    file_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler = TimedRotatingFileHandler(
        log_filepath,
        when="midnight",
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.suffix = "%Y%m%d" # for backup files
    file_handler.setLevel(level)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # to be removed in prod
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors={
            'DEBUG': 'cyan',
            # 'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    logger.info(f"logging initialized: {log_filepath}")
    return logger