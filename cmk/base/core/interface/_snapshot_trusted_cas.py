#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.base.core.active_config_layout import RELATIVE_PATH_TRUSTED_CAS


def snapshot_trusted_cas(trusted_cas_file: Path, config_path: Path) -> None:
    (config_path / RELATIVE_PATH_TRUSTED_CAS).write_bytes(trusted_cas_file.read_bytes())
