#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os

AGENT_OUTPUT_DIR = f"{os.path.dirname(__file__)}/agent_output"
EXPECTED_OUTPUT_DIR = f"{os.path.dirname(__file__)}/check_output"
SECTION_NAMES = [_ for _ in os.getenv("SECTION_NAMES", "").split(",") if _]
HOST_NAMES = [_ for _ in os.getenv("HOST_NAMES", "").split(",") if _]
CHECK_NAMES = [_ for _ in os.getenv("CHECK_NAMES", "").split(",") if _]

API_SERVICES_COLS = [
    "host_name",
    "check_command",
    "check_command_expanded",
    "check_options",
    "check_period",
    "check_type",
    "description",
    "display_name",
    "has_been_checked",
    "labels",
    "plugin_output",
    "state",
    "state_type",
    "tags",
]
