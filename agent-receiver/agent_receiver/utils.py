#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from contextlib import suppress
from dataclasses import dataclass
from typing import Final, Self

from agent_receiver.models import ConnectionMode, R4RStatus, RequestForRegistration
from agent_receiver.site_context import agent_output_dir, r4r_dir, users_dir
from cryptography.x509 import load_pem_x509_csr
from cryptography.x509.oid import NameOID
from fastapi.security import HTTPBasicCredentials
from pydantic import UUID4

INTERNAL_REST_API_USER = "automation"


class NotRegisteredException(Exception):
    ...


class RegisteredHost:
    def __init__(self, uuid: UUID4) -> None:
        self.source_path: Final = agent_output_dir() / str(uuid)
        if not self.source_path.is_symlink():
            raise NotRegisteredException("Source path is not a symlink")

        target_path = self.source_path.resolve(strict=False)
        self.name: Final = target_path.name
        self.connection_mode: Final = (
            ConnectionMode.PUSH if target_path.parent.name == "push-agent" else ConnectionMode.PULL
        )


@dataclass(frozen=True)
class R4R:
    status: R4RStatus
    request: RequestForRegistration

    @classmethod
    def read(cls, uuid: UUID4) -> Self:
        for status in R4RStatus:
            if (path := r4r_dir() / status.name / f"{uuid}.json").exists():
                request = RequestForRegistration.parse_file(path)
                # access time is used to determine when to remove registration request file
                with suppress(OSError):
                    os.utime(path, None)
                return cls(status, request)
        raise FileNotFoundError(f"No request for registration with UUID {uuid} found")

    def write(self) -> None:
        (target_dir := r4r_dir() / self.status.name).mkdir(
            mode=0o770,
            parents=True,
            exist_ok=True,
        )
        (target_path := target_dir / f"{self.request.uuid}.json").write_text(self.request.json())
        target_path.chmod(0o660)


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
