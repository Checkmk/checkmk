#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import cmk.utils.paths
from cmk.ccc.version import __version__ as cmk_version
from cmk.ccc.version import Version


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


_LINUX_RPM_DOWNLOAD_URL = (
    "{{SERVER}}/{{SITE}}/check_mk/agents/check-mk-agent-{version}-1.noarch.rpm"
)
_LINUX_DEB_DOWNLOAD_URL = "{{SERVER}}/{{SITE}}/check_mk/agents/check-mk-agent_{version}-1_all.deb"


def raw_linux_agent_wget_commands(version: str) -> list[str]:
    """`wget` commands for the basic, unbaked Linux agent packages.

    The asymmetric naming (RPM uses `-`, DEB uses `_`) matches the on-disk
    filenames produced by the build (see `Makefile`, `tests/composition/utils.py`).
    """
    return [
        f"wget {_LINUX_RPM_DOWNLOAD_URL.format(version=version)}",
        f"wget {_LINUX_DEB_DOWNLOAD_URL.format(version=version)}",
    ]
