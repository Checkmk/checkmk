#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Data pipeline: RRD consolidation functions (R1.1 Area 2). Skipped skeletons (CMK-35973).

Complete once the graph-data endpoint exists; inject RRD data over a few varying cycles.
"""

import pytest

from tests.testlib.graphing import SKIP_PENDING_GRAPH_BACKEND
from tests.testlib.site import Site


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_BACKEND)
def test_consolidation_functions_yield_distinct_non_empty_series(site: Site) -> None:
    """P-01 (R1.1 Area 2): min/max/average each return a non-empty, non-identical series.

    Do: inject varying RRD data; request graph-data once per CF (min, max, average).
    Assert: each is HTTP 200 with a non-empty series; the three are not all identical.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_BACKEND)
def test_average_consolidation_preserves_gaps(site: Site) -> None:
    """P-02 (R1.1 Area 2): a None gap stays null under the average CF.

    Do: as P-01 but with a None gap; request the average CF over a range covering it.
    Assert: the gap slot is null/absent; surrounding values are present.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")
