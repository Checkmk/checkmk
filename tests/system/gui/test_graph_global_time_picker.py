#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The global time picker on the service detail page.

E2E rather than Vitest throughout: one interaction has to reach every graph on a real page,
the non-effect only shows across a real navigation, the preferred default range is stored
server-side, and the picker is mounted by the page rather than by any single Vue component.
"""

import logging
import re
from collections.abc import Iterator, Mapping
from typing import Final

import pytest
from playwright.sync_api import expect

from tests.system.gui.testlib.playwright.pom.graphing.fixtures import open_service_graphs
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import ServiceGraphs
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.testlib.site import ADMIN_USER, Site

logger = logging.getLogger(__name__)

# Absent a user preference the picker opens on the first configured range.
DEFAULT_PRESET = "Last 1 h"
OTHER_PRESET = "Last 25 h"

# Only a window wider than a day spans two dates, so a shifted hour cannot match.
_TWO_DATE_WINDOW: Final = re.compile(r"\d{4}-\d{2}-\d{2} — \d{4}-\d{2}-\d{2}")


def _mark_document(graphs: ServiceGraphs) -> None:
    """Tag the document so a full page reload is detectable by the tag's absence."""
    graphs.page.evaluate("window.__cmkGlobalTimePickerMarker = true")


def _document_survived(graphs: ServiceGraphs) -> bool:
    return bool(graphs.page.evaluate("window.__cmkGlobalTimePickerMarker === true"))


@pytest.fixture(name="preferred_default_range")
def fixture_preferred_default_range(test_site: Site) -> Iterator[None]:
    """`OTHER_PRESET` as the "Global time picker default range" of `ADMIN_USER`, whom the
    browser logs in as - not of the automation user the REST client acts as."""

    def set_default_time_range(time_range: Mapping[str, str | int]) -> None:
        user = test_site.openapi.users.get(ADMIN_USER)
        assert user is not None, f"The site has no {ADMIN_USER} to set the preference on"
        _user_spec, etag = user
        test_site.openapi.users.edit(
            ADMIN_USER,
            {"interface_options": {"time_picker": {"default_time_range": time_range}}},
            etag,
        )

    set_default_time_range({"option": "individual", "duration": 25 * 60 * 60})
    try:
        yield
    finally:
        set_default_time_range({"option": "default"})


def test_one_preset_selection_moves_every_graph_on_the_page(
    service_graphs: ServiceGraphs, javascript_errors: list[str]
) -> None:
    """One range selection drives every graph, without reloading the page.

    Do: note each panel's time axis, then pick a different preset in the one global picker.
    Assert: every panel's axis moved and now spans the picked window, the picked chip is the
    highlighted one, and the document was redrawn rather than reloaded.
    """
    panels = service_graphs.all_panels()
    assert len(panels) > 1, "The service rendered a single graph, so 'every graph' proves nothing"
    windows_before = [panel.graph.time_axis_label_texts() for panel in panels]
    _mark_document(service_graphs)

    service_graphs.time_picker.select_preset(OTHER_PRESET)

    for panel, window_before in zip(panels, windows_before):
        expect(
            panel.graph.time_axis_labels,
            "A graph rendered no time axis labels at all",
        ).not_to_have_count(0)
        expect(
            panel.graph.time_axis_labels,
            "A graph kept its own window although the page's time range was changed",
        ).not_to_have_text(window_before)
        expect(
            panel.timestamp,
            "A graph moved its window but not to the range that was picked",
        ).to_contain_text(_TWO_DATE_WINDOW)
    expect(
        service_graphs.time_picker.active_preset_chip,
        "The picker did not highlight the range that was just picked",
    ).to_have_text(OTHER_PRESET)
    assert _document_survived(service_graphs), (
        "Picking a range reloaded the page instead of redrawing the graphs"
    )
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


def test_selected_range_is_not_restored_after_navigating_away(
    service_graphs: ServiceGraphs, javascript_errors: list[str]
) -> None:
    """The picked range does not follow the user across a navigation.

    The shared range is in-memory only (`useGlobalTimeRange`), with no storage or URL backing,
    so a fresh document has to fall back to the configured default. Asserted across a real
    cross-page navigation: within one document the singleton legitimately survives.

    Do: pick a non-default range, leave for the dashboard, come back to the service page.
    Assert: the picker is back on the default range.
    """
    service_page = service_graphs.owner
    service_graphs.time_picker.select_preset(OTHER_PRESET)
    expect(
        service_graphs.time_picker.active_preset_chip,
        "The picker did not take the range that was just picked",
    ).to_have_text(OTHER_PRESET)

    # Constructing the page object navigates to it.
    MainDashboard(service_page.page)
    reopened = open_service_graphs(service_page.page, service_page.host_name)

    expect(
        reopened.time_picker.active_preset_chip,
        "Returning to the page restored the previous range instead of the default",
    ).to_have_text(DEFAULT_PRESET)
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


def test_page_carries_exactly_one_global_picker(
    service_graphs: ServiceGraphs, javascript_errors: list[str]
) -> None:
    """One picker drives every graph on the page, so a second one would desynchronise them.

    Do: open the service detail page.
    Assert: exactly one global picker.
    """
    expect(
        service_graphs.time_picker.root,
        "The page did not render exactly one global time picker",
    ).to_have_count(1)
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"


def test_user_preference_preselects_its_own_range(
    preferred_default_range: None,
    service_graphs: ServiceGraphs,
    javascript_errors: list[str],
) -> None:
    """The user's preferred default range is the one the picker opens on - the reported
    defect is this state reached without anyone asking for it.

    Do: set the preference, then open the service graphs page.
    Assert: the preferred range is the highlighted chip and every graph draws that window.
    """
    expect(
        service_graphs.time_picker.active_preset_chip,
        "The picker opened on a range other than the user's preferred default",
    ).to_have_text(OTHER_PRESET)

    service_graphs.wait_until_settled()
    for panel in service_graphs.all_panels():
        expect(
            panel.timestamp,
            "A graph drew a narrower window than the range the picker preselected",
        ).to_contain_text(_TWO_DATE_WINDOW)
    assert not javascript_errors, f"JavaScript errors were raised: {javascript_errors}"
