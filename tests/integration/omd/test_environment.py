#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import subprocess
from pathlib import Path

import pytest

from tests.testlib.site import Site
from tests.testlib.version import edition_from_env


@pytest.mark.skipif(
    edition_from_env().is_cloud_edition(),
    reason="mkbackup is not shipped in the cloud edition",
)
def test_backup_dir(site: Site) -> None:
    # Typically, applications create these directories by using RuntimeDirectory in systemd.
    # However, since we don't ask users to use systemd on Debian-based distros (on RPM distros we
    # require systemd as a dependency), we create this directory every time `omd` runs as root.
    # Current version of Checkmk don't need this directory. However, users may use a new version of
    # `omd` as the one called by systemd (and thus during boot). In those cases, `omd` needs to
    # create this directory, so old versions of Checkmk remain working correctly.
    mkbackup_lock_dir = Path("/run/lock/mkbackup")
    backup_permission_mask = oct(mkbackup_lock_dir.stat().st_mode)[-4:]
    assert backup_permission_mask == "0770"
    assert mkbackup_lock_dir.group() == "omd"


def test_locales(site: Site) -> None:
    p = site.execute(["locale"], stdout=subprocess.PIPE)
    output = p.communicate()[0]

    assert "LANG=C.UTF-8" in output or "LANG=C.utf8" in output or "LANG=en_US.utf8" in output

    assert "LC_ALL=C.UTF-8" in output or "LC_ALL=C.utf8" in output or "LC_ALL=en_US.utf8" in output
