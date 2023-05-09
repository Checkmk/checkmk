#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import hashlib
import logging
from pathlib import Path
from uuid import UUID

import livestatus

from cmk.utils import paths, store
from cmk.utils.licensing.handler import LicenseState
from cmk.utils.paths import log_dir


def init_logging() -> logging.Logger:
    Path(log_dir).mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s [%(levelno)s] [%(name)s %(process)d] %(message)s")

    handler = logging.FileHandler(filename=Path(log_dir, "licensing.log"), encoding="utf-8")
    handler.setFormatter(formatter)

    logger = logging.getLogger("licensing")
    del logger.handlers[:]  # Remove all previously existing handlers
    logger.addHandler(handler)
    logger.propagate = False

    return logger


def get_instance_id_filepath(omd_root: Path) -> Path:
    return omd_root / "etc/omd/instance_id"


def save_instance_id(*, filepath: Path, instance_id: UUID) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w", encoding="utf-8") as fp:
        fp.write(str(instance_id))


def load_instance_id(filepath: Path) -> UUID | None:
    try:
        with filepath.open("r", encoding="utf-8") as fp:
            return UUID(fp.read())
    except (FileNotFoundError, ValueError):
        return None


def hash_site_id(site_id: livestatus.SiteId) -> str:
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


def write_licensed_state(path: Path, state: LicenseState) -> None:
    state_repr = 1 if state is LicenseState.LICENSED else 0
    with store.locked(path):
        path.write_text(str(state_repr))


def get_state_file_created_path() -> Path:
    return paths.licensing_dir / "state_file_created"
