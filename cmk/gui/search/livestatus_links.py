#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What a livestatus search result stands for, and how its link is built."""

from dataclasses import dataclass
from typing import Literal, Protocol

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.web.utils.urls import HTTPVariable


@dataclass(frozen=True)
class ResultHost:
    site_id: SiteId
    host_name: HostName


@dataclass(frozen=True)
class ResultService:
    site_id: SiteId
    host_name: HostName
    service: str


@dataclass(frozen=True)
class ResultGroup:
    kind: Literal["host", "service"]
    name: str


type ResultTarget = ResultHost | ResultService | ResultGroup


@dataclass(frozen=True)
class LivestatusMatch:
    target: ResultTarget
    view_vars: tuple[HTTPVariable, ...]


class ResultUrlBuilder(Protocol):
    def __call__(self, result: LivestatusMatch) -> str: ...
