#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

OMD_ROOT = Path(os.environ.get("OMD_ROOT", ""))

LOG_FILE = OMD_ROOT / "var/log/agent-receiver/agent-receiver.log"
AGENT_OUTPUT_DIR = OMD_ROOT / "var/agent-receiver/received-outputs"
DATA_SOURCE_DIR = OMD_ROOT / "tmp/check_mk/data_source_cache/push-agent"
REGISTRATION_REQUESTS = OMD_ROOT / "var/check_mk/wato/requests-for-registration"
