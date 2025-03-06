#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import TypedDict

# TODO: replace this with an enum once we parse config files to proper types
PROGRAM_ID_DCD = "dcd"
PROGRAM_ID_QUICK_SETUP = "quick_setup"


class GlobalIdent(TypedDict):
    site_id: str
    program_id: str
    instance_id: str
