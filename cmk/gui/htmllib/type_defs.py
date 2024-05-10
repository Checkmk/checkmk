#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass
class RequireConfirmation:
    html: str
    confirmButtonText: str = "Yes"
    cancelButtonText: str = "No"
    customClass = {
        "confirmButton": "confirm_question",
        "icon": "confirm_icon confirm_question",
    }

    def serialize(self) -> str:
        return json.dumps(asdict(self))
