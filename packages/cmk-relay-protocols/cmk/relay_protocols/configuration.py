#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Final, NamedTuple, NewType, Self

from pydantic import BaseModel, Field

RELAY_FETCHER_BASE_PATH: Final = Path(".")


# The name of the folder in the tar archive that contains the relay config files
CONFIG_ARCHIVE_ROOT_FOLDER_NAME: Final = "config"
CONFIG_ARCHIVE_RELATIVE_PATH_ENGINE_CONFIG: Final = "engine/config.json"
CONFIG_ARCHIVE_RELATIVE_PATH_SECRETS_KEY: Final = "secrets/key"
CONFIG_ARCHIVE_RELATIVE_PATH_ACTIVE_SECRETS: Final = "secrets/active_secrets"
CONFIG_ARCHIVE_RELATIVE_PATH_CA_FILE: Final = "ssl/ca-certificates.crt"

Timestamp = NewType("Timestamp", float)
Seconds = NewType("Seconds", float)


class ServiceKind(StrEnum):
    FETCHER = "FETCHER"
    ACTIVE_CHECK = "ACTIVE_CHECK"


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
    timeout: Annotated[
        Seconds, Field(description="Timeout for the fetching task passed into the fetcher", gt=0)
    ]


class Service(BaseModel):
    name: Annotated[str, Field(description="name of the service in checkmk")]
    command: Annotated[str, Field(description="command for execute, can have routing prefix @cmk")]
    schedule: Annotated[Schedule, Field(description="Service scheduling configuration")]
    service_kind: ServiceKind = ServiceKind.FETCHER


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


# Default size of both checkhelper pools (scheduled and ad-hoc active checks).
# The single source for this number: the engine's built-in defaults, the relay
# setup form and REST API on the site, and the relay config writer all import it.
DEFAULT_NUM_CHECKHELPERS: Final = 5


class UserEngineConfig(BaseModel):
    """configuration for relay engine as provided by user config during activation"""

    log_level: LogLevel
    num_fetchers: int
    # Every site version that knows this field writes it, so the default serves
    # the reader, not the writer: on start-up a relay re-reads the last config the
    # site pushed, and right after an engine update that file may predate the
    # field. A field missing there must not make the whole config invalid, or the
    # engine would fall back to its built-in defaults and drop every host until
    # the next activation. Fields added later get a default here for the same
    # reason; do not special-case them in load().
    num_checkhelpers: int = DEFAULT_NUM_CHECKHELPERS
    hosts: Sequence[Host]


class EngineConfig(UserEngineConfig):
    """extended configuration for relay engine"""

    bin_fetcher: Path = Path("/opt/check-mk-relay/bin/fetcher")
    bin_adhoc_fetcher: Path = Path("/opt/check-mk-relay/bin/fetch-ad-hoc")
    num_adhoc_fetchers: int = 4
    bin_checkhelper: Path = Path("/opt/check-mk-relay/lib/cmc/checkhelper")
    num_adhoc_checkhelpers: int = DEFAULT_NUM_CHECKHELPERS
    poll_sleep: float = 0.5
    config_cleanup_schedule: float = 60
    host_scheduler_sleep: float = 0.5
    poll_history: HistoryConfig = HistoryConfig()
    third_party_log_level: LogLevel = LogLevel.CRITICAL
    # Certificate rotation check frequency in seconds (24 hours)
    cert_rotation_schedule: float = 24 * 60 * 60
    # Relay status check frequency in seconds (1 minute)
    relay_status_schedule: float = 60
    # Minimum interval between site version update triggers in seconds (1 minute)
    site_version_trigger_interval: float = 60

    @classmethod
    def load(cls, path: Path) -> Self:
        return cls.model_validate_json(path.read_text())

    def dumps(self) -> str:
        return self.model_dump_json()
