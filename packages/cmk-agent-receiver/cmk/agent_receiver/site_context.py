#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path


def _omd_root() -> Path:
    return Path(os.environ["OMD_ROOT"])


def site_name() -> str:
    return os.environ["OMD_SITE"]


def agent_output_dir() -> Path:
    return _omd_root() / "var/agent-receiver/received-outputs"


def r4r_dir() -> Path:
    return _omd_root() / "var/check_mk/wato/requests-for-registration"


def internal_secret_path() -> Path:
    return _omd_root() / "etc" / "site_internal.secret"


def site_config_path() -> Path:
    return _omd_root() / "etc" / "omd" / "site.conf"


def log_path() -> Path:
    return _omd_root() / "var/log/agent-receiver/agent-receiver.log"


def site_ca_path() -> Path:
    return _omd_root() / "etc" / "ssl" / "ca.pem"


def agent_ca_path() -> Path:
    return _omd_root() / "etc" / "ssl" / "agents" / "ca.pem"
