#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from uuid import UUID


def get_instance_id_file_path(omd_root: Path) -> Path:
    return omd_root / "etc/omd/instance_id"


def save_instance_id(*, file_path: Path, instance_id: UUID) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as fp:
        fp.write(str(instance_id))
