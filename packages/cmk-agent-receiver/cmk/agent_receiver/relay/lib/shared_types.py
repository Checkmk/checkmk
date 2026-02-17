#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import secrets
from dataclasses import dataclass
from http import HTTPStatus
from typing import NewType, override

from fastapi import HTTPException

RelayID = NewType("RelayID", str)
TaskID = NewType("TaskID", str)
Version = NewType("Version", str)


@dataclass(frozen=True, slots=True)
class Serial:
    s: int

    @override
    def __repr__(self) -> str:
        return str(self.s)

    @property
    def value(self) -> int:
        return self.s

    @classmethod
    def random(cls) -> Serial:
        return cls(secrets.randbelow(10000) + 1)

    @classmethod
    def default(cls) -> Serial:
        return cls(0)


class RelayNotFoundError(HTTPException):
    def __init__(self, relay_id: RelayID):
        super().__init__(
            status_code=HTTPStatus.NOT_FOUND, detail=f"Relay with ID '{relay_id}' not found"
        )


class TaskNotFoundError(HTTPException):
    def __init__(self, task_id: TaskID):
        super().__init__(
            status_code=HTTPStatus.NOT_FOUND, detail=f"Task with ID '{task_id}' not found"
        )


class TooManyTasksError(HTTPException):
    def __init__(self, max_number_of_tasks: int):
        super().__init__(
            status_code=HTTPStatus.FORBIDDEN,
            detail=f"The maximum number of tasks {max_number_of_tasks} has been reached",
        )


class CertificateCNError(HTTPException):
    def __init__(self, expected_cn: str, actual_cn: str):
        super().__init__(
            status_code=HTTPStatus.BAD_GATEWAY,
            detail=f"Unexpected certificate CN value: expected '{expected_cn}', actual '{actual_cn}'",
        )


class RemoteSiteError(HTTPException):
    def __init__(self) -> None:
        super().__init__(
            status_code=HTTPStatus.FORBIDDEN,
            detail="Relay registration is not supported on remote sites. "
            "Please register the Relay with the central site instead.",
        )
