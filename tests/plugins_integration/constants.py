#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os

DUMP_DIR = "dumps"
DUMP_DIR_PATH = f"{os.path.dirname(__file__)}/{DUMP_DIR}"
RESPONSE_DIR = "responses"
RESPONSE_DIR_PATH = f"{os.path.dirname(__file__)}/{RESPONSE_DIR}"

HOST_NAMES = [_ for _ in os.getenv("HOST_NAMES", "").split(",") if _]
CHECK_NAMES = [_ for _ in os.getenv("CHECK_NAMES", "").split(",") if _]
DUMP_TYPES = [_ for _ in os.getenv("DUMP_TYPES", "agent,snmp").split(",") if _]

# these columns of the SERVICES table will be returned via the get_host_services() openapi call
# NOTE: extending this list will require an update of the check output (--update-checks)
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
