#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The legend of a dashboard graph widget, and the setting choosing it.

E2E rather than Vitest: the mode the wizard shows on reopening comes from the widget the
dashboard stored, through the save and load round trip with the backend, and the legend names
the series the backend fetched for the graph.
"""

import json
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Final, NamedTuple

import pytest
from playwright.sync_api import expect, Page, Response

from tests.system.gui.testlib.playwright.pom.graphing.dashboard_graph_widget import (
    DashboardGraphWidget,
)
from tests.system.gui.testlib.playwright.pom.graphing.fixtures import (
    open_service_graphs,
    SERVICE_WITH_GRAPHS,
)
from tests.system.gui.testlib.playwright.pom.graphing.global_time_picker import (
    GlobalTimePicker,
    PickerMoment,
)
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import GraphPanel
from tests.system.gui.testlib.playwright.pom.monitor.custom_dashboard import CustomDashboard
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.sidebar.widget_graph_legend_settings import (
    GraphLegendMode,
    LEGEND_STYLES,
)
from tests.system.gui.testlib.playwright.pom.sidebar.widget_wizard_sidebar import (
    MetricsAndGraphsWidgetWizard,
)
from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.system.site import ADMIN_USER, Site

_LEGEND_MODES: Final = [pytest.param(mode, id=mode.name.lower()) for mode in GraphLegendMode]


def _open_new_graph_widget_legend_settings(
    dashboard: CustomDashboard, host_name: str
) -> MetricsAndGraphsWidgetWizard:
    """Start adding a combined graph of the host's service with several metrics, and go on to
    its legend setting."""
    dashboard.enter_edit_widgets_mode()
    wizard = dashboard.open_add_widget_sidebar(MetricsAndGraphsWidgetWizard)
    wizard.select_single_host(host_name)
    wizard.select_single_service(SERVICE_WITH_GRAPHS)
    wizard.combined_graph_toggle.click()
    wizard.open_service_graph_dropdown().first.click()
    wizard.next_step_visualization_button.click()
    return wizard


def _add_graph_widget(dashboard: CustomDashboard, host_name: str, mode: GraphLegendMode) -> str:
    """Add a graph widget with the legend mode, save the dashboard and return the widget's
    title."""
    wizard = _open_new_graph_widget_legend_settings(dashboard, host_name)
    wizard.graph_legend_settings.select_mode(mode)
    expect(wizard.preview_title, "The preview never titled the widget").not_to_be_empty()
    widget_title = wizard.preview_title.inner_text().strip()
    wizard.add_and_place_widget_button.click()
    dashboard.save_widgets()
    return widget_title


def _reopen_legend_settings(
    dashboard: CustomDashboard, widget_title: str
) -> MetricsAndGraphsWidgetWizard:
    """Open the stored widget's wizard on its legend setting; the dashboard is in edit mode."""
    wizard = dashboard.open_edit_widget_sidebar(MetricsAndGraphsWidgetWizard, widget_title)
    wizard.next_step_visualization_button.click()
    return wizard


def _save_widget(wizard: MetricsAndGraphsWidgetWizard) -> None:
    wizard.save_widget_button.click()
    expect(
        wizard.locator(check=False), "The wizard stayed open after saving the widget"
    ).to_be_hidden()


def test_new_graph_widget_shows_the_compact_legend_and_offers_the_extended_one(
    linux_hosts: list[str],
    cloned_linux_hosts_dashboard: CustomDashboard,
) -> None:
    """A new graph widget shows its legend, in the compact style, and offers the extended
    style as the only other one."""
    wizard = _open_new_graph_widget_legend_settings(cloned_linux_hosts_dashboard, linux_hosts[0])

    legend = wizard.graph_legend_settings
    legend.expect_mode(
        GraphLegendMode.COMPACT, "A new graph widget does not show the compact legend"
    )
    expect(
        legend.style_radios, "The legend setting does not offer exactly two styles"
    ).to_have_count(len(LEGEND_STYLES))
    for style in LEGEND_STYLES:
        expect(
            legend.style_radio(style), f"The legend setting does not offer {style!r}"
        ).to_be_visible()


@pytest.mark.parametrize("mode", _LEGEND_MODES)
def test_saved_legend_mode_is_shown_after_a_reload(
    mode: GraphLegendMode,
    linux_hosts: list[str],
    cloned_linux_hosts_dashboard: CustomDashboard,
) -> None:
    """A graph widget saved with a legend mode opens on that mode again after a reload."""
    widget_title = _add_graph_widget(cloned_linux_hosts_dashboard, linux_hosts[0], mode)

    cloned_linux_hosts_dashboard.navigate()
    cloned_linux_hosts_dashboard.enter_edit_widgets_mode()
    wizard = _reopen_legend_settings(cloned_linux_hosts_dashboard, widget_title)

    wizard.graph_legend_settings.expect_mode(
        mode, f"The widget saved with {mode!r} does not show it after a reload"
    )


def test_legend_setting_shows_the_last_saved_mode_on_every_reopening(
    linux_hosts: list[str],
    cloned_linux_hosts_dashboard: CustomDashboard,
) -> None:
    """Reopening a graph widget's settings shows the legend mode saved last, whether it was
    changed or saved unchanged, never an earlier or the default one."""
    saved = GraphLegendMode.EXTENDED
    widget_title = _add_graph_widget(cloned_linux_hosts_dashboard, linux_hosts[0], saved)
    # Saving the dashboard leaves the edit mode, which is what offers to edit a widget.
    cloned_linux_hosts_dashboard.enter_edit_widgets_mode()

    for mode in (GraphLegendMode.NO_LEGEND, GraphLegendMode.COMPACT, GraphLegendMode.EXTENDED):
        wizard = _reopen_legend_settings(cloned_linux_hosts_dashboard, widget_title)
        wizard.graph_legend_settings.expect_mode(
            saved, f"The settings do not show the last saved {saved!r} before switching to {mode!r}"
        )
        wizard.graph_legend_settings.select_mode(mode)
        _save_widget(wizard)
        saved = mode
    _save_widget(_reopen_legend_settings(cloned_linux_hosts_dashboard, widget_title))
    wizard = _reopen_legend_settings(cloned_linux_hosts_dashboard, widget_title)

    wizard.graph_legend_settings.expect_mode(
        saved, f"The settings do not show {saved!r} after saving them unchanged"
    )


_COMPACT_DASHBOARD_ID: Final = "e2e_compact_graph_legend_dashboard"
_COMPACT_DASHBOARD_TITLE: Final = "E2E compact graph legend dashboard"
_COMPACT_WIDGET_TITLE: Final = "Graph with compact legend"

_EXTENDED_DASHBOARD_ID: Final = "e2e_extended_graph_legend_dashboard"
_EXTENDED_DASHBOARD_TITLE: Final = "E2E extended graph legend dashboard"
_EXTENDED_WIDGET_TITLE: Final = "Graph with extended legend"
# The stat columns of the extended legend, in `GraphStat` order.
_EXTENDED_LEGEND_STATS: Final = ["Min", "Average", "Max", "Last"]

_FETCHED_SECONDS: Final = 4 * 60 * 60
# A window both surfaces are set to: in the past, so no new data point changes its stats
# between the two reads, and short, so both fetch it at the storage's own resolution however
# wide they draw it.
_COMPARED_RANGE_START_AGO: Final = 30 * 60
_COMPARED_RANGE_END_AGO: Final = 2 * 60
# The module creates its hosts right before the tests, so the window holds no sample until
# the first checks are a few minutes old.
_COMPARED_RANGE_DATA_TIMEOUT: Final = 5 * 60

# A moment some time back, in the browser's time zone and to the minute, as the picker's
# fields take it.
_BROWSER_MOMENT_AGO: Final = """(secondsAgo) => {
    const moment = new Date(Date.now() - secondsAgo * 1000);
    moment.setSeconds(0, 0);
    return [moment.getFullYear(), moment.getMonth() + 1, moment.getDate(),
            moment.getHours(), moment.getMinutes()];
}"""

_FORMATTED_VALUE: Final = re.compile(r"^(?P<number>-?\d+(?:\.(?P<decimals>\d+))?)\s*(?P<unit>\S*)$")
_UNIT_PREFIXES: Final = {
    "Ki": 2**10,
    "Mi": 2**20,
    "Gi": 2**30,
    "Ti": 2**40,
    "Pi": 2**50,
    "k": 1e3,
    "K": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
    "P": 1e15,
    "m": 1e-3,
    "µ": 1e-6,
    "n": 1e-9,
}


class _GraphWithSeries(NamedTuple):
    """A template graph of a service, as the backend fetches it.

    `series` names everything its legend lists - metrics, threshold lines and shaded regions -
    while `metrics` names only the curves, which the extended legend gives a row of stats each.
    """

    graph_id: str
    internal: dict[str, object]
    title: str
    metrics: list[str]
    series: list[str]


def _graph_with_several_metrics(test_site: Site, host_name: str) -> _GraphWithSeries:
    """The first template graph of the host's service that draws more than one metric."""
    discovered = test_site.openapi.graph.discover_template_graphs(host_name, SERVICE_WITH_GRAPHS)
    end = int(time.time())
    for graph in discovered["graphs"]:
        if graph["add_to_specification"] is None:
            continue
        internal = json.loads(graph["internal"])
        fetched = test_site.openapi.graph.fetch_data(
            internal,
            {"start": end - _FETCHED_SECONDS, "end": end, "step": 60},
            "avg",
        )
        metrics = [metric["metadata"]["title"] for metric in fetched["metrics"]]
        if len(metrics) > 1:
            return _GraphWithSeries(
                graph_id=graph["add_to_specification"]["graph_id"],
                internal=internal,
                title=fetched["title"],
                metrics=metrics,
                series=[
                    *metrics,
                    *(line["title"] for line in fetched["horizontal_lines"]),
                    *(region["title"] for region in fetched["shaded_regions"]),
                ],
            )
    raise AssertionError(
        f"{host_name}/{SERVICE_WITH_GRAPHS} yielded no template graph of several metrics: "
        f"{discovered['no_data_message']}"
    )


@contextmanager
def _graph_dashboard(
    test_site: Site,
    host_name: str,
    graph: _GraphWithSeries,
    *,
    dashboard_id: str,
    title: str,
    widget_title: str,
    legend_style: str,
) -> Iterator[None]:
    """A dashboard of one template graph widget on the legend style, following the dashboard's
    time range.

    Built through the REST API: the wizard is not what is under test here. Shared with all
    users, because on the cloud edition the browser does not log in as `ADMIN_USER`.
    """
    widget = {
        "general_settings": {
            "title": {"text": widget_title, "render_mode": "with_background"},
            "render_background": True,
        },
        "content": {
            "type": "performance_graph",
            "timerange": "dashboard",
            "graph_render_options": {"show_legend": True, "legend_style": legend_style},
            "source": graph.graph_id,
        },
        "filters": {"host": {"host": host_name}, "service": {"service": SERVICE_WITH_GRAPHS}},
        "layout": {
            "type": "relative_grid",
            "position": {"x": 1, "y": 1},
            "size": {"width": 40, "height": 20},
        },
    }
    payload = {
        "id": dashboard_id,
        "general_settings": {
            "title": {"text": title, "render": True, "include_context": False},
            "description": "",
            "menu": {
                "topic": "overview",
                "sort_index": 99,
                "search_terms": [],
                "is_show_more": False,
            },
            "visibility": {
                "hide_in_monitor_menu": False,
                "hide_in_drop_down_menus": False,
                "share": {"type": "with_all_users"},
            },
        },
        "filter_context": {
            "restricted_to_single": [],
            "filters": {},
            "mandatory_context_filters": [],
        },
        "widgets": {"legend_graph": widget},
        "layout": {"type": "relative_grid"},
    }
    with test_site.openapi.acting_as(ADMIN_USER, test_site.admin_password):
        test_site.openapi.dashboard.create_relative_grid_dashboard(payload)
    try:
        yield
    finally:
        if is_cleanup_enabled():
            with test_site.openapi.acting_as(ADMIN_USER, test_site.admin_password):
                test_site.openapi.dashboard.delete(dashboard_id)


def _open_dashboard(
    dashboard_page: MainDashboard, test_site: Site, dashboard_id: str, title: str
) -> CustomDashboard:
    dashboard_page.page.goto(
        test_site.internal_url + f"dashboard.py?name={dashboard_id}&owner={ADMIN_USER}",
        wait_until="load",
    )
    return CustomDashboard(dashboard_page.page, page_title=title, navigate_to_page=False)


@pytest.fixture(name="legend_graph")
def fixture_legend_graph(test_site: Site, linux_hosts: list[str]) -> _GraphWithSeries:
    return _graph_with_several_metrics(test_site, linux_hosts[0])


@pytest.fixture(name="compact_legend_dashboard")
def fixture_compact_legend_dashboard(
    dashboard_page: MainDashboard,
    test_site: Site,
    linux_hosts: list[str],
    legend_graph: _GraphWithSeries,
) -> Iterator[CustomDashboard]:
    """A dashboard of one graph widget on the compact legend, opened in the browser."""
    with _graph_dashboard(
        test_site,
        linux_hosts[0],
        legend_graph,
        dashboard_id=_COMPACT_DASHBOARD_ID,
        title=_COMPACT_DASHBOARD_TITLE,
        widget_title=_COMPACT_WIDGET_TITLE,
        legend_style="compact",
    ):
        yield _open_dashboard(
            dashboard_page, test_site, _COMPACT_DASHBOARD_ID, _COMPACT_DASHBOARD_TITLE
        )


@pytest.fixture(name="extended_legend_dashboard")
def fixture_extended_legend_dashboard(
    test_site: Site,
    linux_hosts: list[str],
    legend_graph: _GraphWithSeries,
) -> Iterator[None]:
    """A dashboard of one graph widget on the extended legend, not opened yet."""
    with _graph_dashboard(
        test_site,
        linux_hosts[0],
        legend_graph,
        dashboard_id=_EXTENDED_DASHBOARD_ID,
        title=_EXTENDED_DASHBOARD_TITLE,
        widget_title=_EXTENDED_WIDGET_TITLE,
        legend_style="extended",
    ):
        yield


def test_compact_legend_names_every_series_in_a_single_row(
    compact_legend_dashboard: CustomDashboard,
    legend_graph: _GraphWithSeries,
) -> None:
    """A graph widget on the compact legend names every series its graph draws, each with its
    color swatch and visibility toggle, all in a single row."""
    graph = DashboardGraphWidget(compact_legend_dashboard, _COMPACT_WIDGET_TITLE)

    graph.wait_until_rendered()

    legend = graph.compact_legend
    expect(legend.root, "The widget does not show the compact legend").to_be_visible()
    expect(legend.items, "The compact legend does not name every series").to_have_count(
        len(legend_graph.series)
    )
    assert sorted(legend.names()) == sorted(legend_graph.series), (
        "The compact legend names other series than the graph draws"
    )
    for name in legend_graph.series:
        expect(legend.swatch(name), f"The series {name!r} has no color swatch").to_be_visible()
        expect(
            legend.visibility_toggle(name), f"The series {name!r} has no visibility toggle"
        ).to_have_attribute("aria-pressed", "true")
    boxes = legend.item_boxes()
    assert max(box.top for box in boxes) - min(box.top for box in boxes) < min(
        box.height for box in boxes
    ), f"The compact legend spreads over more than one row: {boxes}"


def _wait_for_samples_in_compared_range(test_site: Site, graph: _GraphWithSeries) -> None:
    """Wait until every metric of the graph has a sample in the compared range.

    Without one, both surfaces show n/a for every stat and the comparison proves nothing.
    """

    def _every_metric_has_a_sample() -> bool:
        now = int(time.time())
        # The picker takes the range to the minute, which only ever moves its end earlier.
        end = (now - _COMPARED_RANGE_END_AGO) // 60 * 60
        fetched = test_site.openapi.graph.fetch_data(
            graph.internal,
            {"start": now - _COMPARED_RANGE_START_AGO, "end": end, "step": 60},
            "avg",
        )
        return all(
            any(point is not None for point in metric["data_points"])
            for metric in fetched["metrics"]
        )

    wait_until(
        _every_metric_has_a_sample,
        timeout=_COMPARED_RANGE_DATA_TIMEOUT,
        interval=10,
        condition_name=f"every metric of {graph.title!r} to have a sample in the compared range",
    )


def _browser_moment_ago(page: Page, seconds: int) -> PickerMoment:
    return PickerMoment(*page.evaluate(_BROWSER_MOMENT_AGO, seconds))


def _is_graph_fetch(response: Response) -> bool:
    return response.url.endswith("/domain-types/graph/actions/fetch_data/invoke")


def _service_page_legend(
    page: Page, host_name: str, graph: _GraphWithSeries, start: PickerMoment, end: PickerMoment
) -> dict[str, list[str]]:
    """The legend values the service page shows for the graph over the range."""
    service_graphs = open_service_graphs(page, host_name)
    with page.expect_response(_is_graph_fetch):
        service_graphs.time_picker.apply_custom_range(start, end)
    service_graphs.wait_until_settled()
    panel = GraphPanel(
        service_graphs.panels.filter(has=page.get_by_text(graph.title, exact=True)),
        page,
        service_graphs.owner.main_area,
    )
    expect(
        panel.legend_rows, f"The service page does not list every metric of {graph.title!r}"
    ).to_have_count(len(graph.metrics))
    return panel.legend_values()


def _as_quantity(shown: str) -> tuple[float, float, str] | None:
    """A legend value as its magnitude, the rounding its precision allows, and its base unit;
    None if it is not a number, e.g. while there is no data."""
    if (match := _FORMATTED_VALUE.match(shown)) is None:
        return None
    unit = match["unit"]
    factor: float = 1
    for prefix, prefix_factor in _UNIT_PREFIXES.items():
        if unit.startswith(prefix) and len(unit) > len(prefix):
            unit, factor = unit.removeprefix(prefix), prefix_factor
            break
    rounding = 0.5 * 10 ** -len(match["decimals"] or "") * factor
    return float(match["number"]) * factor, rounding, unit


def _same_value(shown: str, expected: str) -> bool:
    """Whether two legend values state the same quantity at the precision each is shown with.

    The precision follows the value axis, whose ticks depend on the graph's height, so the
    widget and the service page may round the same value differently.
    """
    if shown == expected:
        return True
    if (left := _as_quantity(shown)) is None or (right := _as_quantity(expected)) is None:
        return False
    return left[2] == right[2] and abs(left[0] - right[0]) <= left[1] + right[1]


def _same_legend(shown: dict[str, list[str]], expected: dict[str, list[str]]) -> bool:
    return shown.keys() == expected.keys() and all(
        len(shown[title]) == len(expected[title])
        and all(map(_same_value, shown[title], expected[title]))
        for title in expected
    )


@pytest.mark.usefixtures("extended_legend_dashboard")
def test_extended_legend_shows_the_stats_of_every_series_as_the_service_page(
    dashboard_page: MainDashboard,
    test_site: Site,
    linux_hosts: list[str],
    legend_graph: _GraphWithSeries,
) -> None:
    """A graph widget on the extended legend lists every metric of its graph with its min,
    average, max and last value, the same values the service page shows for that range.

    The service page is the reference, not the backend: both surfaces render the same legend
    component, so this proves the dashboard feeds it the same graph, range and consolidation.
    That the stats themselves are computed and formatted right is up to the component's own
    tests (legendUtils.test.ts).
    """
    _wait_for_samples_in_compared_range(test_site, legend_graph)
    page = dashboard_page.page
    start = _browser_moment_ago(page, _COMPARED_RANGE_START_AGO)
    end = _browser_moment_ago(page, _COMPARED_RANGE_END_AGO)
    expected = _service_page_legend(page, linux_hosts[0], legend_graph, start, end)
    assert any(_as_quantity(value) for values in expected.values() for value in values), (
        f"The service page shows no value for the compared range, so it proves nothing: {expected}"
    )
    dashboard = _open_dashboard(
        dashboard_page, test_site, _EXTENDED_DASHBOARD_ID, _EXTENDED_DASHBOARD_TITLE
    )
    graph = DashboardGraphWidget(dashboard, _EXTENDED_WIDGET_TITLE)
    graph.wait_until_rendered()

    GlobalTimePicker(dashboard.main_area).apply_custom_range(start, end)

    legend = graph.panel
    expect(legend.legend, "The widget does not show the extended legend").to_be_visible()
    expect(legend.legend_stat_headers, "The extended legend shows other stats").to_have_text(
        _EXTENDED_LEGEND_STATS
    )
    expect(legend.legend_rows, "The extended legend does not list every metric").to_have_count(
        len(legend_graph.metrics)
    )
    wait_until(
        lambda: _same_legend(legend.legend_values(), expected),
        timeout=15,
        condition_name=f"the widget's legend to show the service page's values {expected}",
    )
