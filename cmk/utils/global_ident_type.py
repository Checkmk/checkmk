#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import TypedDict

PROGRAM_ID_DCD = "dcd"


class GlobalIdent(TypedDict):
    site_id: str
    program_id: str
    instance_id: str
