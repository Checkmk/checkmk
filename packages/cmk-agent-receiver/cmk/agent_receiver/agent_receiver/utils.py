#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from contextlib import suppress
from dataclasses import dataclass
from typing import Final, Self

from pydantic import UUID4, ValidationError

from cmk.agent_receiver.agent_receiver.models import (
    AgentUpdateAuthorization,
    ConnectionMode,
    R4RStatus,
    RequestForRegistration,
    UUIDRegistration,
)
from cmk.agent_receiver.lib.config import get_config
from cmk.agent_receiver.lib.log import logger


class NotRegisteredException(Exception): ...


class RegisteredHost:
    def __init__(self, uuid: UUID4) -> None:
        config = get_config()
        self.source_path: Final = config.agent_output_dir / str(uuid)
        if not self.source_path.is_symlink():
            raise NotRegisteredException("Source path is not a symlink")

        target_path = self.source_path.resolve(strict=False)
        self.name: Final = target_path.name
        self.connection_mode: Final = (
            ConnectionMode.PUSH if target_path.parent.name == "push-agent" else ConnectionMode.PULL
        )


def agent_update_authorization(uuid: UUID4) -> AgentUpdateAuthorization:
    try:
        raw = (get_config().registrations_dir / f"{uuid}.json").read_bytes()
        registration = UUIDRegistration.model_validate_json(raw)
    except (OSError, ValidationError) as e:
        logger.warning(
            "uuid=%(uuid)s Reading the registration file failed: %(error)s",
            {"uuid": uuid, "error": e},
        )
        return AgentUpdateAuthorization.UNAVAILABLE
    match registration.agent_updates_permitted:
        case True:
            return AgentUpdateAuthorization.AUTHORIZED
        case False:
            return AgentUpdateAuthorization.NOT_PERMITTED
        case None:
            return AgentUpdateAuthorization.UNAVAILABLE


@dataclass(frozen=True)
class R4R:
    status: R4RStatus
    request: RequestForRegistration

    @classmethod
    def read(cls, uuid: UUID4) -> Self:
        config = get_config()
        for status in R4RStatus:
            if (path := config.r4r_dir / status.name / f"{uuid}.json").exists():
                with open(path, encoding="utf-8") as file:
                    request = RequestForRegistration.model_validate_json(file.read())
                # access time is used to determine when to remove registration request file
                with suppress(OSError):
                    os.utime(path, None)
                return cls(status, request)
        raise FileNotFoundError(f"No request for registration with UUID {uuid} found")

    def write(self) -> None:
        config = get_config()
        (target_dir := config.r4r_dir / self.status.name).mkdir(
            mode=0o770,
            parents=True,
            exist_ok=True,
        )
        (target_path := target_dir / f"{self.request.uuid}.json").write_text(
            self.request.model_dump_json(),
            encoding="utf-8",
        )
        target_path.chmod(0o660)
