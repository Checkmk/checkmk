#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Vue component embedding and props (R1.2 Area 1). Skipped skeletons (CMK-35973).

Backend-only: assert on the rendered page HTML, so enablable as soon as the backend
embeds <cmk-graph>. Fetch the page via site.openapi/requests and parse with BeautifulSoup.
"""

import pytest

from tests.testlib.graphing import SKIP_PENDING_GRAPH_BACKEND
from tests.testlib.site import Site


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_BACKEND)
def test_service_page_embeds_cmk_graph_without_legacy_markup(site: Site) -> None:
    """CE-01 (R1.2 Area 1): the page embeds <cmk-graph> and drops legacy markup.

    Do: create a host with a known check (e.g. PING), discover+check; fetch the page HTML.
    Assert: HTTP 200; >=1 <cmk-graph>; no legacy container (div.graph_container/
    graph_with_timeranges) for the same graph.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_BACKEND)
def test_cmk_graph_data_attribute_is_valid_discovery_result(site: Site) -> None:
    """CE-02 (R1.2 Area 1): the data attribute is a complete, valid discovery result.

    Do: as CE-01; extract the data attribute of the first <cmk-graph>.
    Assert: valid JSON with a non-empty title, >=1 line def with a non-empty expression,
    and a scalars map (possibly empty).
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_BACKEND)
def test_service_without_perfdata_embeds_no_cmk_graph(site: Site) -> None:
    """CE-03 (R1.2 Area 1): a perfdata-less service embeds no <cmk-graph>.

    Do: fetch the page HTML for a service with no perfdata.
    Assert: no <cmk-graph>; HTTP 200.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")
