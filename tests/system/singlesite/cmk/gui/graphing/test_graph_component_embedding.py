#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Vue component embedding (R1.2 Area 1). Skipped skeletons (CMK-35973).

Backend-only: assert on the rendered page HTML, so enablable as soon as the backend embeds the
component. Fetch the page via site.openapi/requests and parse with BeautifulSoup. Note the
registered element is ``cmk-graph-group``, not ``cmk-graph``.

CE-02 (the payload itself) is covered by unit tests instead: the embedded data attribute holds
only the title plus the opaque ``internal`` definition, and the lines and scalars come from a
separate fetch_data call - neither needs a site. See
`tests/unit/cmk/gui/graphing/test_frontend.py` for the attribute and
`test_openapi_fetch_graph_data.py` for the fetched payload.
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
def test_service_without_perfdata_embeds_no_cmk_graph(site: Site) -> None:
    """CE-03 (R1.2 Area 1): a perfdata-less service embeds no <cmk-graph>.

    Do: fetch the page HTML for a service with no perfdata.
    Assert: no <cmk-graph>; HTTP 200.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")
