#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from uuid import UUID


def create_instance_id(*, site_home: Path, instance_id: UUID) -> None:
    instance_id_file_path = site_home / "etc/omd/instance_id"
    instance_id_file_path.write_text(str(instance_id))
