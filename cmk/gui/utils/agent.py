#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import cmk.utils.paths
from cmk.ccc.version import __version__ as cmk_version
from cmk.ccc.version import Version
from cmk.shared_typing.agent_slideout import UnbakedFallbackCommands


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


_AGENTS_URL = "{{SERVER}}/{{SITE}}/check_mk/agents"


def raw_linux_agent_commands(version: str) -> UnbakedFallbackCommands:
    """Download and install commands for the basic, unbaked Linux agent packages.

    The asymmetric naming (RPM uses `-`, DEB uses `_`) matches the on-disk
    filenames produced by the build (see `Makefile`, `tests/system/multisite/utils.py`).
    """
    deb = f"check-mk-agent_{version}-1_all.deb"
    rpm = f"check-mk-agent-{version}-1.noarch.rpm"
    return UnbakedFallbackCommands(
        linux_deb=f"wget {_AGENTS_URL}/{deb} && \\\nsudo dpkg -i {deb}",
        linux_rpm=f"wget {_AGENTS_URL}/{rpm} && \\\nsudo rpm -Uvh {rpm}",
    )
