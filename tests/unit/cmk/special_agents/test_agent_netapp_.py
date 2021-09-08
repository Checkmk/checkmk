#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.special_agents.agent_netapp import parse_arguments


def test_parse_arguments() -> None:
    parse_arguments(
        [
            "address",
            "user",
            "password",
            "--no_counters",
            "volumes",
        ]
    )
