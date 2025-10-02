#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, NamedTuple, NewType, Self

from pydantic import BaseModel, Field, HttpUrl

Timestamp = NewType("Timestamp", float)
Seconds = NewType("Seconds", float)


class CheckPeriod(NamedTuple):
    start: Timestamp
    end: Timestamp


class Schedule(BaseModel):
    check_periods: Annotated[
        list[CheckPeriod], Field(description="Periods during which to schedule checks")
    ]
    check_interval: Annotated[Seconds, Field(description="Check interval in seconds", gt=0)]
    retry_interval: Annotated[Seconds, Field(description="Retry interval in seconds", gt=0)]
    max_attempts: Annotated[int, Field(description="Maximum number of attempts", gt=0)]


class Host(BaseModel):
    id: Annotated[str, Field(description="Host ID")]
    schedule: Annotated[Schedule, Field(description="Host scheduling configuration")]


class HistoryConfig(BaseModel):
    timeout: float = 60.0
    maxlen: int = 100


class SiteConfig(BaseModel):
    """
    Configuration which site we are connecting to, and additional information for the connection.

    We separate this from the other configuration for reliability.
    A problem during a change in the engine configuration should not break the site connection.
    """

    site_url: HttpUrl
    relay_id: str

    @classmethod
    def load(cls, path: Path) -> Self:
        return cls.model_validate_json(path.read_text())


class UserEngineConfig(BaseModel):
    """configuration for relay engine as provided by user config during activation"""

    num_fetchers: int
    hosts: Sequence[Host]


class EngineConfig(UserEngineConfig):
    """extended configuration for relay engine"""

    bin_fetcher: Path = Path("/opt/check-mk-relay/bin/fetcher")
    bin_adhoc_fetcher: Path = Path("/opt/check-mk-relay/bin/fetch-ad-hoc")
    num_adhoc_fetchers: int = 4
    daemon_sleep: float = 0.5
    poll_sleep: float = 0.5
    host_scheduler_sleep: float = 0.5
    poll_history: HistoryConfig = HistoryConfig()
    log_level: str = "INFO"
    third_party_log_level: str = "CRITICAL"

    @classmethod
    def load(cls, path: Path) -> Self:
        return cls.model_validate_json(path.read_text())
