#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path

OMD_ROOT = Path(os.environ.get("OMD_ROOT", ""))

LOG_FILE = OMD_ROOT / "var/log/marcv/marcv.log"
AGENT_OUTPUT_DIR = OMD_ROOT / "var/marcv/received_output"

CERT_STORE = OMD_ROOT / "etc/ssl"
ROOT_CERT = CERT_STORE / "ca.pem"
SERVER_CERT = CERT_STORE / "marcv/server_cert.pem"
SERVER_PRIVATE_KEY = CERT_STORE / "marcv/server_key.pem"
SERVER_CN = "localhost"
CERT_NOT_AFTER = 999 * 365 * 24 * 60 * 60  # 999 years by default
