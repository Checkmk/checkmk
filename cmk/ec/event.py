#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Optional, TypedDict


# This is far from perfect, but at least we see all possible keys.
class Event(TypedDict, total=False):
    # guaranteed after parsing
    facility: int
    priority: int
    text: str
    host: str
    ipaddress: str
    application: str
    pid: int
    time: float
    core_host: str
    host_in_downtime: bool
    # added later
    comment: str
    contact: str
    contact_groups: Optional[Iterable[str]]  # TODO: Do we really need the Optional?
    contact_groups_notify: bool
    contact_groups_precedence: str
    count: int
    delay_until: float
    first: float
    id: int
    last: float
    live_until: float
    live_until_phases: Iterable[str]
    match_groups: Iterable[str]
    match_groups_syslog_application: Iterable[str]
    orig_host: str
    owner: str
    phase: str
    rule_id: Optional[str]
    sl: int
    state: int
