#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
from pathlib import Path
from typing import Optional
from uuid import UUID

from agent_receiver.models import HostTypeEnum, RegistrationData, RegistrationStatusEnum
from agent_receiver.site_context import agent_output_dir, r4r_dir
from cryptography.x509 import load_pem_x509_csr
from cryptography.x509.oid import NameOID


class Host:
    def __init__(self, uuid: UUID):
        self._hostname = None
        self._host_type = None
        self._source_path = agent_output_dir() / str(uuid)
        self._registered = self.source_path.is_symlink()

        if not self.registered:
            return

        target_path = self.source_path.resolve(strict=False)
        self._hostname = target_path.name
        self._host_type = HostTypeEnum.PUSH if target_path.exists() else HostTypeEnum.PULL

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
        path = r4r_dir() / status.name / f"{uuid}.json"
        if path.exists():
            message = (
                read_message_from_file(path) if status is RegistrationStatusEnum.DECLINED else None
            )
            # access time is used to determine when to remove registration request file
            update_file_access_time(path)
            return RegistrationData(status=status, message=message)

    return None


def uuid_from_pem_csr(pem_csr: str) -> str:
    try:
        return (
            load_pem_x509_csr(pem_csr.encode())
            .subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0]
            .value
        )
    except ValueError:
        return "[CSR parsing failed]"
