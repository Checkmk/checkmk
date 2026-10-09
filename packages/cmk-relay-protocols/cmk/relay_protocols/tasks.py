#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Final, Literal

from pydantic import Base64Bytes, BaseModel, Field, field_validator

# Where a relay keeps the files of one ad-hoc active check: the site's relative tmp
# directory (cmk.utils.paths.relative_tmp_dir), which the relay mirrors below its root.
AD_HOC_FILES_DIR: Final = PurePosixPath("tmp/check_mk")


class HEADERS(StrEnum):
    SERIAL = "X-CMK-SERIAL"
    VERSION = "X-CMK-VERSION"
    # Sent by the relay: comma separated ConfigEncoding values it can unpack.
    CONFIG_ENCODING = "X-CMK-CONFIG-ENCODING"


class ConfigEncoding(StrEnum):
    GZIP = "gzip"


class _TaskType(StrEnum):
    RELAY_CONFIG = "RELAY_CONFIG"
    FETCH_AD_HOC = "FETCH_AD_HOC"
    AD_HOC_ACTIVE_CHECK = "AD_HOC_ACTIVE_CHECK"


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class ResultType(StrEnum):
    OK = "OK"
    ERROR = "ERROR"


class FetchAdHocTask(BaseModel):
    payload: str
    timeout: float = Field(
        title="Fetcher timeout",
        description="Fetcher timeout for tasks in seconds",
        default=60.0,
        ge=0,
    )
    type: Literal[_TaskType.FETCH_AD_HOC] = _TaskType.FETCH_AD_HOC


class AdHocPasswordStore(BaseModel):
    """A password store the relay writes for one ad-hoc active check and removes after it.

    The command refers to its passwords as ``<id>:<path>``; the relay writes the values
    as a store at that path, encrypted with its active store key. The path is relative
    to the relay's root and must stay below AD_HOC_FILES_DIR.
    """

    path: str = Field(description="Relative path of the store the command refers to")
    values: Mapping[str, str] = Field(description="Password id to plaintext value")

    @field_validator("path")
    @classmethod
    def _strictly_below_ad_hoc_files_dir(cls, path: str) -> str:
        # A check of the path's shape, against mistakes: the relay's file system, and
        # whatever symlinks it holds, is out of reach here.
        pure = PurePosixPath(path)
        if (
            pure.is_absolute()
            or ".." in pure.parts
            or pure == AD_HOC_FILES_DIR
            or not pure.is_relative_to(AD_HOC_FILES_DIR)
        ):
            raise ValueError(f"path must be a relative path below {AD_HOC_FILES_DIR}: {path!r}")
        return path


class AdHocSiteStores(BaseModel):
    """The site's pending stores, for a check run from the service discovery page.

    The passwords and the CAs the user just saved, which the relay has not applied yet.
    """

    ca_bundle: str = Field(description="Trusted CAs as PEM text, for SSL_CERT_FILE; may be empty")
    passwords: AdHocPasswordStore | None = Field(
        default=None, description="The store the command refers to, if it refers to passwords"
    )


class AdHocActiveCheckTask(BaseModel):
    host: str
    command: str
    timeout: float = Field(
        title="Active check timeout",
        description="Active check timeout for tasks in seconds",
        default=60.0,
        ge=0,
    )
    # None: the relay's applied stores, as a forced check or an older site sends.
    site_stores: AdHocSiteStores | None = Field(
        default=None, description="The site's pending passwords and CAs the check is to use"
    )
    type: Literal[_TaskType.AD_HOC_ACTIVE_CHECK] = _TaskType.AD_HOC_ACTIVE_CHECK


class RelayConfigTask(BaseModel, frozen=True):
    serial: int
    tar_data: Base64Bytes = Field(
        title="Base64 encoded tar data",
        description="Base64 encoded tar data containing the configuration files for the relay",
    )
    type: Literal[_TaskType.RELAY_CONFIG] = _TaskType.RELAY_CONFIG


# Only the tasks that can be created via create task API endpoint
TaskCreateRequestSpec = FetchAdHocTask | AdHocActiveCheckTask

# Any task that can be stored in the backend
TaskResponseSpec = FetchAdHocTask | RelayConfigTask | AdHocActiveCheckTask


class TaskCreateRequest(BaseModel, frozen=True):
    spec: TaskCreateRequestSpec = Field(discriminator="type")
    version: int = 1


class TaskCreateResponse(BaseModel, frozen=True):
    task_id: str


class TaskResponse(BaseModel, frozen=True):
    spec: TaskResponseSpec = Field(discriminator="type")
    status: TaskStatus
    result_type: ResultType | None
    result_payload: str | None
    creation_timestamp: datetime
    update_timestamp: datetime
    id: str
    version: int = 1


class TaskListResponse(BaseModel, frozen=True):
    tasks: list[TaskResponse]


class TaskUpdateRequest(BaseModel, frozen=True):
    result_type: ResultType
    result_payload: str


class UpdateConfigResponse(BaseModel, frozen=True):
    created: Sequence[str]
    pending: Sequence[str]
    failed: Mapping[str, str]
