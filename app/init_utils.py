# -*- coding: utf-8 -*-
import logging
from pathlib import Path
import os
import shutil


def create_directory(directory: Path, purge: bool = False) -> None:
    if purge:
        shutil.rmtree(directory, ignore_errors=True)
    os.makedirs(directory, exist_ok=True)


def get_default_logger(name: str, log_directory: Path) -> logging.Logger:
    # Configure logging
    # Log >=INFO to console and write to file app.log in c.PUBLIC_MOUNT_DIR.
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_stream_handler = logging.StreamHandler()
    log_stream_handler.setLevel(logging.INFO)
    log_stream_handler.setFormatter(log_formatter)
    logger.addHandler(log_stream_handler)
    log_file_handler = logging.FileHandler(log_directory / f"{name}.log", "w")
    log_file_handler.setLevel(logging.INFO)
    log_file_handler.setFormatter(log_formatter)
    logger.addHandler(log_file_handler)
    return logger
