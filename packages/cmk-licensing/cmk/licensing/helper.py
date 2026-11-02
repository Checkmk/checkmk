#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import logging
import threading
from logging.handlers import WatchedFileHandler
from pathlib import Path
from uuid import UUID

from cmk.ccc.log import CMKFormatter
from cmk.ccc.site import SiteId

# Threads of one process, for example the jobs of the UI job scheduler, may set up the licensing
# logger at the same time.
_SETUP_LOCK = threading.Lock()


def get_licensing_logger() -> logging.Logger:
    return logging.getLogger("cmk.licensing")


def _init_logging(log_dir: Path) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)

    # logrotate rotates licensing.log while a long-lived process keeps the handler. The handler
    # reopens the file when its inode changes.
    handler = WatchedFileHandler(filename=log_dir / "licensing.log", encoding="utf-8")
    handler.setFormatter(CMKFormatter(with_process=True))

    logger = get_licensing_logger()
    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)
    logger.propagate = False

    return logger


def init_logging_if_missing(log_dir: Path) -> logging.Logger:
    """Return the licensing logger, set up to write to licensing.log in log_dir.

    The first call in a process adds a handler for that file. Later calls for the same log_dir
    return the logger unchanged. They neither open the file again nor remove handlers that other
    code added. Callers can therefore call this function every time they need the logger."""
    logger = get_licensing_logger()
    log_file = log_dir.absolute() / "licensing.log"
    with _SETUP_LOCK:
        if any(
            isinstance(handler, WatchedFileHandler) and Path(handler.baseFilename) == log_file
            for handler in logger.handlers
        ):
            return logger
        return _init_logging(log_dir)


def load_instance_id(file_path: Path) -> UUID | None:
    try:
        with file_path.open("r", encoding="utf-8") as fp:
            return UUID(fp.read())
    except FileNotFoundError, ValueError:
        return None


def hash_site_id(site_id: SiteId) -> str:
    # We have to hash the site ID because some sites contain project names.
    # This hash also has to be constant because it will be used as an DB index.
    h = hashlib.new("sha256")
    h.update(str(site_id).encode("utf-8"))
    return h.hexdigest()


def rot47(input_str: str) -> str:
    return "".join(_rot47_char(c) for c in input_str)


def _rot47_char(c: str) -> str:
    ord_c = ord(c)
    return chr(33 + ((ord_c + 14) % 94)) if 33 <= ord_c <= 126 else c
