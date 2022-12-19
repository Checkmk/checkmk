#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass

from cmk.utils.type_defs import UserId

from cmk.gui.type_defs import SessionInfo


@dataclass
class Session:
    """Container object for encapsulating the session of the currently logged in user"""

    user_id: UserId
    session_info: SessionInfo
