#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from cmk.ccc.version import __version__ as cmk_version
from cmk.ccc.version import Version

import cmk.utils.paths


def packed_agent_path_windows_msi() -> Path:
    return cmk.utils.paths.agents_dir / "windows/check_mk_agent.msi"


def packed_agent_path_linux_deb() -> Path:
    return (
        cmk.utils.paths.agents_dir
        / f"check-mk-agent_{Version.from_str(cmk_version).version_without_rc}-1_all.deb"
    )


def packed_agent_path_linux_rpm() -> Path:
    return (
        cmk.utils.paths.agents_dir
        / f"check-mk-agent-{Version.from_str(cmk_version).version_without_rc}-1.noarch.rpm"
    )
