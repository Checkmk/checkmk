#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import os
from contextlib import suppress
from dataclasses import dataclass
from typing import Final, NewType, Self

from cryptography.x509 import load_pem_x509_csr
from cryptography.x509.oid import NameOID
from pydantic import UUID4

from .models import ConnectionMode, R4RStatus, RequestForRegistration
from .site_context import agent_output_dir, internal_secret_path, r4r_dir


class NotRegisteredException(Exception): ...


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
                with open(path, encoding="utf-8") as file:
                    request = RequestForRegistration.model_validate_json(file.read())
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
        (target_path := target_dir / f"{self.request.uuid}.json").write_text(
            self.request.model_dump_json(),
            encoding="utf-8",
        )
        target_path.chmod(0o660)


def uuid_from_pem_csr(pem_csr: str) -> str:
    try:
        v = (
            load_pem_x509_csr(pem_csr.encode())
            .subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0]
            .value
        )
        assert isinstance(v, str)
        return v
    except ValueError:
        return "[CSR parsing failed]"


B64SiteInternalSecret = NewType("B64SiteInternalSecret", str)


def internal_credentials() -> B64SiteInternalSecret:
    return B64SiteInternalSecret(
        base64.b64encode(internal_secret_path().read_bytes()).decode("ascii")
    )
