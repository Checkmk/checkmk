#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, NamedTuple, Optional

from cmk.base.plugins.agent_based.agent_based_api.v1 import State


class VirtualService(NamedTuple):
    name: str
    connections: Optional[int]
    state: State
    state_txt: str
    oid_end: str


VSSection = Mapping[str, VirtualService]
