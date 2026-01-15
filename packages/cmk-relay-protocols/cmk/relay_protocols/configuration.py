#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import enum
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Final, NamedTuple, NewType, Self

from pydantic import BaseModel, Field

RELAY_FETCHER_BASE_PATH: Final = Path(".")


# The name of the folder in the tar archive that contains the relay config files
CONFIG_ARCHIVE_ROOT_FOLDER_NAME: Final = "config"
CONFIG_ARCHIVE_RELATIVE_PATH_ENGINE_CONFIG: Final = "engine/config.json"
CONFIG_ARCHIVE_RELATIVE_PATH_SECRETS_KEY: Final = "secrets/key"
CONFIG_ARCHIVE_RELATIVE_PATH_ACTIVE_SECRETS: Final = "secrets/active_secrets"

Timestamp = NewType("Timestamp", float)
Seconds = NewType("Seconds", float)


class CheckPeriod(NamedTuple):
    start: Timestamp
    end: Timestamp


class Schedule(BaseModel):
    check_periods: Annotated[
        Sequence[CheckPeriod], Field(description="Periods during which to schedule checks")
    ]
    check_interval: Annotated[Seconds, Field(description="Check interval in seconds", gt=0)]
    retry_interval: Annotated[Seconds, Field(description="Retry interval in seconds", gt=0)]
    max_attempts: Annotated[int, Field(description="Maximum number of attempts", gt=0)]


class Service(BaseModel):
    name: Annotated[str, Field(description="name of the service in checkmk")]
    command: Annotated[str, Field(description="command for execute, can have routing prefix @cmk")]
    schedule: Annotated[Schedule, Field(description="Service scheduling configuration")]


class Host(BaseModel):
    id: Annotated[str, Field(description="Host ID")]
    services: Annotated[Sequence[Service], Field(description="Services of the host")]


class HistoryConfig(BaseModel):
    timeout: float = 60.0
    maxlen: int = 100


class LogLevel(enum.StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class UserEngineConfig(BaseModel):
    """configuration for relay engine as provided by user config during activation"""

    log_level: LogLevel
    num_fetchers: int
    hosts: Sequence[Host]


class EngineConfig(UserEngineConfig):
    """extended configuration for relay engine"""

    bin_fetcher: Path = Path("/opt/check-mk-relay/bin/fetcher")
    bin_adhoc_fetcher: Path = Path("/opt/check-mk-relay/bin/fetch-ad-hoc")
    num_adhoc_fetchers: int = 4
    poll_sleep: float = 0.5
    config_cleanup_schedule: float = 60
    host_scheduler_sleep: float = 0.5
    poll_history: HistoryConfig = HistoryConfig()
    third_party_log_level: LogLevel = LogLevel.CRITICAL

    @classmethod
    def load(cls, path: Path) -> Self:
        return cls.model_validate_json(path.read_text())
