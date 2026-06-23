#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket

from cmk.automations.models.helper import AUTOMATION_HELPER_SOCKET_RELATIVE_PATH

with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
    client.connect(AUTOMATION_HELPER_SOCKET_RELATIVE_PATH)
