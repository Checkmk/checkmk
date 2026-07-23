#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Graph discovery in a distributed setup (R1.1 Area 7). Skipped skeleton (CMK-35973).

Backend-phase. Complete once the graph-discovery endpoint exists; create the host on the
remote site and connect the sites (see tests/system/multisite/conftest.py).
"""

import pytest

from tests.testlib.graphing import SKIP_PENDING_GRAPH_BACKEND
from tests.testlib.site import Site


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_BACKEND)
def test_central_discovery_matches_remote_host(central_site: Site, remote_site: Site) -> None:
    """C-01 (R1.1 Area 7): central-site discovery for a remote host matches the remote's set.

    Do: create and check a host on the remote site; call graph-discovery on the central site.
    Assert: the central result equals a direct query to the remote site.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")
