#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.site import Site


@pytest.mark.parametrize("cmd", ["ssh -V", "curl -V", "pdftoppm -v"])
def test_command(site: Site, cmd: str) -> None:
    """
    Ensures that commands using OpenSSL, such as ssh and curl, are working.

    When executing ssh as a site user, usually, the system ssh is used. This binary is usually
    dynamically linked against OpenSSL. We ship OpenSSL with OMD and set LD_LIBRARY_PATH to within
    the site environment. Hence, when calling ssh as a site user, the OMD OpenSSL is used. There is
    no garantuee that this version is compatible with the ssh compilation available on the system
    (which is intended to compatible with the system OpenSSL). See also SUP-10161 and
    omd/packages/omd/ssh_system_openssl.

    We execute this test in the CI containers of all supported distros to ensure that commands using
    OpenSSL which are available there can be executed.
    """
    site.run(cmd.split())


def test_scp(site: Site) -> None:
    """
    Ensures that scp is working.

    When executing scp as a site user, usually, the system scp is used. This binary is usually
    dynamically linked against OpenSSL. We ship OpenSSL with OMD and set LD_LIBRARY_PATH to within
    the site environment. Hence, when calling scp as a site user, the OMD OpenSSL is used. There is
    no garantuee that this version is compatible with the scp compilation available on the system
    (which is intended to compatible with the system OpenSSL). See also SUP-17682.

    We execute this test in the CI containers of all supported distros to ensure that commands using
    OpenSSL which are available there can be executed.
    """
    site.run(["touch", "test_scp_source"])
    p = site.run(["scp", "test_scp_source", "test_scp_target"])
    print(p.stdout)
    print(p.stderr)
    site.run(["rm", "test_scp_target"])
