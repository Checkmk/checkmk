#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Navigation page-object for the custom graph designer (Pro+).

``custom_graph.py`` serves both modes of the same Vue app: viewing a saved graph, and
editing its definition with "mode=edit".

This page takes the graph to show as a mandatory parameter, so it is reached by URL: even
the "build a graph from scratch" cases need a saved graph to open.
"""

import logging
import re
from typing import override
from urllib.parse import urljoin

from playwright.sync_api import expect, Locator, Page

from tests.system.gui.testlib.playwright.helpers import DropdownListNameToID
from tests.system.gui.testlib.playwright.pom.graphing.timeseries_graph import TimeSeriesGraph
from tests.system.gui.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)

_PREVIEW_SELECTOR = ".graphing-designer-body__preview"
_LEGEND_ROW_SELECTOR = ".graphing-graph-legend__row"
_ERROR_NOTICE_SELECTOR = ".graphing-graph-notice--error"

# The metrics selection tab - the designer's default tab in edit mode.
_METRICS_TABLE_SELECTOR = ".graphing-metrics-table"
_SOURCE_ROW_SELECTOR = ".monitoring-editable-table__row"
_SOURCE_FORM_NAME = re.compile(r"^Source \w+ details$")
# Only one dropdown list is mounted at a time, so this need not be scoped to its field.
_SUGGESTIONS_SELECTOR = ".cmk-suggestions"
_FILTER_BOX_SELECTOR = "input[aria-label='filter']"
_ADD_SOURCE_SELECTOR = "button[aria-label='Add source']"


class CustomGraphDesigner(CmkPage):
    """The custom graph designer, in either view or edit mode."""

    def __init__(
        self,
        page: Page,
        graph_name: str,
        *,
        edit: bool = False,
        navigate_to_page: bool = True,
    ) -> None:
        self.graph_name = graph_name
        self._edit = edit
        super().__init__(page=page, navigate_to_page=navigate_to_page)

    @override
    def navigate(self) -> None:
        mode = "&mode=edit" if self._edit else ""
        logger.info(
            "Navigate to the custom graph designer for '%s' in %s mode",
            self.graph_name,
            "edit" if self._edit else "view",
        )
        self.goto(urljoin(self.page.url, f"custom_graph.py?name={self.graph_name}{mode}"))
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is the custom graph designer")
        self.page.wait_for_url(url=re.compile(r"(?<!edit_)custom_graph\.py"), wait_until="load")
        # The app shows a loading icon until the graph definition and the filter
        # definitions have arrived; the body only mounts once both are in.
        expect(
            self.main_area.locator(".graphing-designer-body"),
            "The custom graph designer never finished loading its graph",
        ).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def preview(self) -> Locator:
        """The graph the new engine rendered for this graph definition."""
        return self.main_area.locator(_PREVIEW_SELECTOR)

    @property
    def graph(self) -> TimeSeriesGraph:
        """The graph the preview draws, with the same canvas and axes as on any other surface."""
        return TimeSeriesGraph(
            self.preview.locator(".graphing-time-series-graph"), self.page, self.main_area
        )

    @property
    def legend_rows(self) -> Locator:
        """One row per drawn metric; rendered in view mode only."""
        return self.main_area.locator(_LEGEND_ROW_SELECTOR)

    @property
    def error_notices(self) -> Locator:
        """The engine's error state, shown over the graph when it cannot be drawn."""
        return self.main_area.locator(_ERROR_NOTICE_SELECTOR)

    @property
    def source_rows(self) -> Locator:
        """One row per data source in the metrics selection tab (edit mode only)."""
        return self.main_area.locator(_METRICS_TABLE_SELECTOR).locator(_SOURCE_ROW_SELECTOR)

    def add_rrd_metric(self, host_name: str, service_name: str, metric_title: str) -> None:
        """Add a Checkmk RRD metric as a data source, filling its host, service and metric.

        The metric is named by its *title* ("RAM used"), not its metric name ("mem_used"):
        the dropdown labels its suggestions with the title alone.
        """
        logger.info("Add RRD metric '%s/%s/%s'", host_name, service_name, metric_title)
        rows_before = self.source_rows.count()
        self.main_area.locator(_ADD_SOURCE_SELECTOR).click()
        # The source types are a fixed list, offered in full and without a filter box.
        self._select_suggestion(self._open_suggestions("Checkmk RRD"), "Checkmk RRD")
        expect(
            self.source_rows,
            "Adding a Checkmk RRD source did not add a row to the metrics table",
        ).to_have_count(rows_before + 1)

        # The new row is appended and auto-expanded, so its form is the last one.
        form = self.main_area.locator().get_by_role("group", name=_SOURCE_FORM_NAME).last
        self._fill_autocompleter(form, "Host name", host_name)
        self._fill_autocompleter(form, "Service", service_name)
        self._fill_autocompleter(form, "Service metric", metric_title)

    def save(self) -> None:
        """Commit the edited definition; the designer returns to view mode."""
        logger.info("Save the custom graph definition")
        self.main_area.locator().get_by_role("button", name="Save", exact=True).click()
        expect(
            self.main_area.locator().get_by_role("button", name="Edit custom graph", exact=True),
            "The designer stayed in edit mode after saving",
        ).to_be_visible()

    def _fill_autocompleter(self, form: Locator, field_name: str, value: str) -> None:
        # Exact matching: "Service" is otherwise also the metric field's name.
        button = form.get_by_role("combobox", name=field_name, exact=True)
        button.click()
        suggestions = self._open_suggestions(value)
        # An unqueried autocompleter offers every host/service/metric there is, and the
        # backend caps how many it returns - narrow the list before picking out of it.
        filter_box = suggestions.locator(_FILTER_BOX_SELECTOR)
        expect(
            filter_box,
            f"The autocompleter offering {value!r} never showed its filter box",
        ).to_be_visible()
        filter_box.fill(value)
        self._select_suggestion(suggestions, value)
        # A row that did not take the value is merely incomplete, and the designer then
        # draws nothing - which reads as a missing graph rather than a missing selection.
        expect(
            button,
            f"The field still does not show {value!r} after that option was picked",
        ).to_contain_text(value)

    def _open_suggestions(self, title: str) -> Locator:
        """The dropdown list that is currently open; portalled, so not under its field."""
        suggestions = self.main_area.locator(_SUGGESTIONS_SELECTOR)
        expect(suggestions, f"No dropdown opened to offer {title!r}").to_be_visible()
        return suggestions

    def _select_suggestion(self, suggestions: Locator, title: str) -> None:
        """Pick the entry titled `title`, rather than whichever one the list highlights."""
        option = suggestions.locator(f"[role='option'][aria-label='{title}']")
        expect(option, f"No suggestion titled {title!r} was offered").to_be_visible()
        option.click()
