#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What the tests of the Veeam special agent share, whatever Veeam user they connect as."""

from dataclasses import dataclass
from pathlib import Path

BACKUP_SERVER_HOST_NAME = "veeam-server"
PROTECTED_MACHINE_HOST_NAME = "ip-172-31-26-65"


@dataclass(frozen=True)
class VeeamAccount:
    """The Veeam user the special agent connects as."""

    user: str
    password_variable: str
    """The environment variable holding the user's password on a real server."""
    recording_file: Path
    """The responses the mocked server replays, recorded as this user."""
