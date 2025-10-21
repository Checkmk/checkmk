#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import io
import secrets
import tarfile
from pathlib import Path

from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import (
    _ARCHIVE_ROOT_NAME as ROOT,
)

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

# TODO find a way to determine this number
_NUMBER_OF_FOLDERS_IN_STRUCTURE = 2  # config and config/workers


@dataclasses.dataclass(frozen=True)
class ConfigFolder:
    serial: str
    files: ConfigFiles

    def assert_tar_content(self, relay_id: RelayId, tar_data: bytes) -> None:
        relay_files = self.files[relay_id]
        tar_buffer = io.BytesIO(tar_data)
        with tarfile.open(fileobj=tar_buffer, mode="r") as tar:
            members = tar.getmembers()
            assert len(members) == len(_FOLDER_STRUCTURE) + _NUMBER_OF_FOLDERS_IN_STRUCTURE
            for filename in _FOLDER_STRUCTURE:
                tar_info = tar.getmember(f"{ROOT}/{filename}")
                file_obj = tar.extractfile(tar_info)
                assert file_obj is not None
                file_content = file_obj.read().decode("utf-8")
                assert relay_files[filename] == file_content, f"Failed for {relay_id=}, {filename=}"


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

    # Update "latest" symlink to point to the new serial folder
    symlink_path = root / _SUBPATH / "latest"
    if symlink_path.is_symlink():
        symlink_path.unlink()
    symlink_path.symlink_to(path_to_serial)

    return ConfigFolder(serial=serial, files=config_files)
