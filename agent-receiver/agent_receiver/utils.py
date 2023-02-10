#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import os
from pathlib import Path
from typing import Final
from uuid import UUID

from agent_receiver.models import ConnectionMode, RegistrationData, RegistrationStatusEnum
from agent_receiver.site_context import agent_output_dir, r4r_dir, users_dir
from cryptography.x509 import load_pem_x509_csr
from cryptography.x509.oid import NameOID
from fastapi.security import HTTPBasicCredentials

INTERNAL_REST_API_USER = "automation"


class NotRegisteredException(Exception):
    ...


class RegisteredHost:
    def __init__(self, uuid: UUID) -> None:
        self.source_path: Final = agent_output_dir() / str(uuid)
        if not self.source_path.is_symlink():
            raise NotRegisteredException("Source path is not a symlink")
        try:
            target_path = Path(os.readlink(self.source_path))
        except (FileNotFoundError, OSError) as excpt:
            raise NotRegisteredException("Failed to follow source path symlink") from excpt

        self.name: Final = target_path.name
        self.connection_mode: Final = self._connection_mode(target_path)

    @staticmethod
    def _connection_mode(target_path: Path) -> ConnectionMode:
        return (
            ConnectionMode.PUSH if target_path.parent.name == "push-agent" else ConnectionMode.PULL
        )


def read_rejection_notice_from_file(path: Path) -> str | None:
    try:
        registration_request = json.loads(path.read_text())
    except FileNotFoundError:
        return None

    return registration_request.get("state", {}).get("readable")


def update_file_access_time(path: Path) -> None:
    try:
        os.utime(path, None)
    except OSError:
        pass


def get_registration_status_from_file(uuid: UUID) -> RegistrationData | None:
    for status in RegistrationStatusEnum:
        path = r4r_dir() / status.name / f"{uuid}.json"
        if path.exists():
            message = (
                read_rejection_notice_from_file(path)
                if status is RegistrationStatusEnum.DECLINED
                else None
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


def internal_credentials() -> HTTPBasicCredentials:
    secret = (users_dir() / INTERNAL_REST_API_USER / "automation.secret").read_text().strip()
    return HTTPBasicCredentials(username=INTERNAL_REST_API_USER, password=secret)
