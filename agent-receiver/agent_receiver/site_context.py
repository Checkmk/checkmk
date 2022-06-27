#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import os
from pathlib import Path


@functools.lru_cache
def _omd_root() -> Path:
    return Path(os.environ["OMD_ROOT"])


@functools.lru_cache
def site_name() -> str:
    return os.environ["OMD_SITE"]


@functools.lru_cache
def agent_output_dir() -> Path:
    return _omd_root() / "var/agent-receiver/received-outputs"


@functools.lru_cache
def r4r_dir() -> Path:
    return _omd_root() / "var/check_mk/wato/requests-for-registration"


@functools.lru_cache
def site_config_path() -> Path:
    return _omd_root() / "etc" / "omd" / "site.conf"


@functools.lru_cache
def log_path() -> Path:
    return _omd_root() / "var/log/agent-receiver/agent-receiver.log"
