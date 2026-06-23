#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from pydantic import BaseModel

from cmk.automations.types import AutomationID

# Location of the automation helper's unix socket, relative to OMD_ROOT.
AUTOMATION_HELPER_SOCKET_RELATIVE_PATH = "tmp/run/automation-helper.sock"

# Arbitrary host label used to mount the unix-socket transport on a requests session; the actual
# routing is done via the socket, so the host part of the URL is irrelevant to the server.
AUTOMATION_HELPER_BASE_URL = "http://local-automation"


class AutomationPayload(BaseModel, frozen=True):
    name: AutomationID
    args: Sequence[str]
    stdin: str
    log_level: int


class AutomationResponse(BaseModel, frozen=True):
    serialized_result_or_error_code: str | int
    stdout: str
    stderr: str
