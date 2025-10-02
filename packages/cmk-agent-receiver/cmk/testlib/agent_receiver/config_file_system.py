#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import secrets
from pathlib import Path

RelayId = str
FileName = str
FileContent = str
RelayFiles = dict[FileName, FileContent]
ConfigFiles = dict[RelayId, RelayFiles]

_SUBPATH = Path("var/check_mk/core/helper_config")

_FOLDER_STRUCTURE: list[FileName] = [
    "some-config1.json",
    "workers/worker1.json",
    "workers/worker2.json",
    "maybe-some-hosts.json",
]


@dataclasses.dataclass(frozen=True)
class ConfigFolder:
    serial: str
    files: ConfigFiles


def create_config_folder(root: Path, relays: list[RelayId]) -> ConfigFolder:
    serial = secrets.token_urlsafe(8)

    # the serial folder exists even if no relay configured
    path_to_serial = root / _SUBPATH / serial
    path_to_serial.mkdir(parents=True, exist_ok=True)

    config_files: ConfigFiles = {}
    relay_files: RelayFiles = {}

    for relay_id in relays:
        relay_files = {}
        for filename in _FOLDER_STRUCTURE:
            file_path = path_to_serial / "relays" / relay_id / filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            content = secrets.token_urlsafe(20)
            file_path.write_text(content)
            relay_files[filename] = content
        config_files[relay_id] = relay_files

    symlink_path = root / _SUBPATH / "latest"
    if symlink_path.is_symlink():
        symlink_path.unlink()
    symlink_path.symlink_to(path_to_serial)

    return ConfigFolder(serial=serial, files=config_files)
