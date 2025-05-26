#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import logging
from pathlib import Path
from uuid import UUID

from cmk.ccc.site import SiteId

from cmk.utils import paths
from cmk.utils.paths import log_dir


def get_licensing_logger() -> logging.Logger:
    return logging.getLogger("cmk.licensing")


def init_logging() -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s")

    handler = logging.FileHandler(filename=log_dir / "licensing.log", encoding="utf-8")
    handler.setFormatter(formatter)

    logger = get_licensing_logger()
    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)
    logger.propagate = False

    return logger


def get_instance_id_file_path(omd_root: Path) -> Path:
    return omd_root / "etc/omd/instance_id"


def save_instance_id(*, file_path: Path, instance_id: UUID) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as fp:
        fp.write(str(instance_id))


def load_instance_id(file_path: Path) -> UUID | None:
    try:
        with file_path.open("r", encoding="utf-8") as fp:
            return UUID(fp.read())
    except (FileNotFoundError, ValueError):
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


def get_licensed_state_file_path() -> Path:
    return paths.licensing_dir / "licensed_state"


def get_state_file_created_file_path() -> Path:
    return paths.licensing_dir / "state_file_created"


def get_state_change_path() -> Path:
    return paths.licensing_dir / "state_change"
