#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
from pathlib import Path
from typing import Optional
from uuid import UUID

from agent_receiver.constants import AGENT_OUTPUT_DIR, REGISTRATION_REQUESTS
from agent_receiver.models import HostTypeEnum, RegistrationData, RegistrationStatusEnum


class Host:
    def __init__(self, uuid: UUID):
        self._source_path = AGENT_OUTPUT_DIR / str(uuid)

        self._registered = self.source_path.is_symlink()
        target_path = self._get_target_path() if self.registered else None

        self._hostname = target_path.name if target_path else None
        self._host_type = self._get_host_type(target_path)

    def _get_target_path(self) -> Optional[Path]:
        try:
            return Path(os.readlink(self.source_path))
        except (FileNotFoundError, OSError):
            return None

    @staticmethod
    def _get_host_type(target_path: Optional[Path]) -> Optional[HostTypeEnum]:
        if not target_path:
            return None

        return HostTypeEnum.PUSH if target_path.exists() else HostTypeEnum.PULL

    @property
    def source_path(self) -> Path:
        return self._source_path

    @property
    def registered(self) -> bool:
        return self._registered

    @property
    def hostname(self) -> Optional[str]:
        return self._hostname

    @property
    def host_type(self) -> Optional[HostTypeEnum]:
        return self._host_type


def read_message_from_file(path: Path) -> Optional[str]:
    try:
        registration_request = json.loads(path.read_text())
    except FileNotFoundError:
        return None

    return registration_request.get("message")


def update_file_access_time(path: Path) -> None:
    try:
        os.utime(path, None)
    except OSError:
        pass


def get_registration_status_from_file(uuid: UUID) -> Optional[RegistrationData]:
    for status in RegistrationStatusEnum:
        path = REGISTRATION_REQUESTS / status.name / f"{uuid}.json"
        if path.exists():
            message = (
                read_message_from_file(path) if status is RegistrationStatusEnum.DECLINED else None
            )
            # access time is used to determine when to remove registration request file
            update_file_access_time(path)
            return RegistrationData(status=status, message=message)

    return None


def site_name_prefix(app_name: str) -> str:
    site_prefix = f"/{site}" if (site := os.getenv("OMD_SITE")) else ""
    return f"{site_prefix}/{app_name}"
