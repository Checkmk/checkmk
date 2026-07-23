#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest

from tests.testlib.site import Site


@pytest.mark.parametrize(
    "cmd",
    [
        "ssh -V",
        "curl -V",
        "pdftoppm -v",
        "nslookup -version",
        "rpmbuild --version",
        pytest.param(
            "zypper",
            marks=pytest.mark.skipif(
                not os.environ.get("DISTRO", "").startswith("sles"), reason="Only relevant for SLES"
            ),
        ),
    ],
)
def test_command(site: Site, cmd: str) -> None:
    """
    Ensures that commands using OpenSSL, such as ssh and curl, are working.

    In the past we set LD_LIBRARY_PATH to use the installed OMD site's library folder.
    This was to force our binaries/shared libraries to use our OpenSSL.
    We no longer do this, since our dependencies have the RPATH set correctly.

    This test is to ensure that we do not regress to the previous behaviour.
    See also SUP-10161.

    We execute this test in the CI containers of all supported distros to ensure that commands using
    OpenSSL which are available there can be executed.
    """
    site.run(cmd.split())


def test_scp(site: Site) -> None:
    """
    Ensures that scp is working.

    In the past we set LD_LIBRARY_PATH to use the installed OMD site's library folder.
    This was to force our binaries/shared libraries to use our OpenSSL.
    We no longer do this, since our dependencies have the RPATH set correctly.

    This test is to ensure that we do not regress to the previous behaviour.

    See also SUP-17682.

    We execute this test in the CI containers of all supported distros to ensure that commands using
    OpenSSL which are available there can be executed.
    """
    site.run(["touch", "test_scp_source"])
    p = site.run(["scp", "test_scp_source", "test_scp_target"])
    print(p.stdout)
    print(p.stderr)
    site.run(["rm", "test_scp_target"])
