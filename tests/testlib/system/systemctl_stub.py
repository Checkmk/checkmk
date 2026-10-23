#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The systemctl stub that lets packages install in a container without systemd.

Without a bus, every systemctl call in a package's maintainer scripts fails with "Failed to
connect to bus: No such file or directory". So in a container without systemd, systemctl is
replaced by a symlink to /bin/true. Where systemd runs, the real binary has to be back.
"""

import logging
from pathlib import Path

from tests.testlib.common.utils2 import is_containerized, run, systemd_is_running

logger = logging.getLogger(__name__)

_SYSTEMCTL = Path("/bin/systemctl")
_SYSTEMCTL_SHADOWED = Path("/usr/bin/systemctl.cmk-test-backup")
_STUB = Path("/bin/true")


def _systemctl_is_shadowed() -> bool:
    # On a distribution with a merged /usr, Path("/bin/systemctl").resolve() is
    # "/usr/bin/true", never Path("/bin/true"), so both sides have to be resolved.
    return _SYSTEMCTL.is_symlink() and _SYSTEMCTL.resolve() == _STUB.resolve()


def shadow_systemctl() -> None:
    """Replace systemctl by the stub, keeping the real binary next to it.

    On a distribution with a merged /usr, /bin/systemctl is the real binary, so deleting it
    would lose it for good.
    """
    if _systemctl_is_shadowed():
        return
    if _SYSTEMCTL.exists() and not _SYSTEMCTL_SHADOWED.exists():
        logger.info("Moving %s aside to %s", _SYSTEMCTL, _SYSTEMCTL_SHADOWED)
        run(["mv", _SYSTEMCTL.as_posix(), _SYSTEMCTL_SHADOWED.as_posix()], sudo=True)
    logger.info("Replacing %s by a symlink to %s", _SYSTEMCTL, _STUB)
    run(["ln", "-sf", _STUB.as_posix(), _SYSTEMCTL.as_posix()], sudo=True)


def unshadow_systemctl() -> None:
    if not _SYSTEMCTL_SHADOWED.exists():
        return
    logger.info("Restoring %s from %s", _SYSTEMCTL, _SYSTEMCTL_SHADOWED)
    if _systemctl_is_shadowed():
        run(["rm", "-f", _SYSTEMCTL.as_posix()], sudo=True)
    run(["mv", "-f", _SYSTEMCTL_SHADOWED.as_posix(), _SYSTEMCTL.as_posix()], sudo=True)


def align_systemctl_with_environment() -> None:
    if not is_containerized():
        return
    if systemd_is_running():
        unshadow_systemctl()
    else:
        shadow_systemctl()
