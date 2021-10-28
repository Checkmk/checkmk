#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import cmk.utils.paths
from cmk.utils.version import __version__ as cmk_version


def packed_agent_path_windows_msi() -> Path:
    return Path(cmk.utils.paths.agents_dir) / "windows" / "check_mk_agent.msi"


def packed_agent_path_linux_deb() -> Path:
    return Path(cmk.utils.paths.agents_dir) / f"check-mk-agent_{cmk_version}-1_all.deb"


def packed_agent_path_linux_rpm() -> Path:
    return Path(cmk.utils.paths.agents_dir) / f"check-mk-agent-{cmk_version}-1.noarch.rpm"
