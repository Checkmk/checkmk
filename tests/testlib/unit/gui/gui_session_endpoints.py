#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Types shared by the tests of the internal gui_session endpoints and their fixtures."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol

from cmk.ccc.user import UserId
from cmk.gui.type_defs import SessionState


class SessionCookieFactory(Protocol):
    def __call__(
        self,
        user_id: UserId,
        *,
        state: SessionState = ...,
        age_seconds: int = ...,
        idle_seconds: int = ...,
    ) -> tuple[str, str]: ...


@dataclass(frozen=True, slots=True)
class LoggedSecurityEvent:
    """One event from the security log, as the security_events fixture records it"""

    summary: str
    details: Mapping[str, object]
