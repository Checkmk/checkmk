#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Page object for the form that defines a telemetry metrics query."""

import logging

from playwright.sync_api import expect, Locator

from tests.system.gui.testlib.playwright.pom.page import MainArea
from tests.system.gui.testlib.playwright.pom.setup.otel.attribute_filter_editor import (
    AttributeFilterEditor,
)
from tests.system.gui.testlib.playwright.pom.setup.otel.suggestions import Suggestions

logger = logging.getLogger(__name__)


class TelemetryMetricsQueryForm:
    """The metric, attribute filter, consolidation and grouping of a telemetry metrics query.

    Args:
        root: the element holding the form.
        main_area: the page's main area, for the dropdowns that teleport out of `root`.
    """

    def __init__(self, root: Locator, main_area: MainArea) -> None:
        self.root = root
        self._main_area = main_area
        self._suggestions = Suggestions(main_area)

    @property
    def metric_name_select(self) -> Locator:
        return self.root.get_by_role("combobox", name="Metric name", exact=True)

    def select_metric(self, metric_name: str, metric_type: str) -> None:
        """Search for `metric_name` and pick it from the metric dropdown.

        The dropdown titles a metric with the types it carries ("metric (gauge)"), so the
        caller states the type it ingested. The untyped entry echoed back while the search
        is still in flight then cannot satisfy the selection.
        """
        logger.info("Select metric '%s (%s)'", metric_name, metric_type)
        self.metric_name_select.click()
        self._suggestions.search(metric_name)
        self._suggestions.pick(f"{metric_name} ({metric_type})")
        expect(
            self.metric_name_select,
            f"Metric {metric_name!r} was not selected",
        ).to_contain_text(metric_name)

    @property
    def attribute_filter(self) -> AttributeFilterEditor:
        return AttributeFilterEditor(
            self.root.get_by_role("group", name="Attributes", exact=True),
            self._main_area,
            self._leave_editing,
        )

    @property
    def group_by_summary(self) -> Locator:
        return self.root.get_by_role("group", name="Group by: grouping function and keys")

    def group_by(self, function_title: str, attribute_key: str) -> None:
        """Group the series by `attribute_key` with the grouping function `function_title`.

        `function_title` is the function as the dropdown names it, e.g. "avg by".
        """
        logger.info("Group by '%s' with '%s'", attribute_key, function_title)
        self.root.get_by_role("button", name="Edit group by").click()
        self._suggestions.pick(function_title)
        self.root.get_by_role("button", name="Add group key", exact=True).click()
        self._suggestions.search(attribute_key)
        self._suggestions.pick(attribute_key)
        self._leave_editing()
        expect(self.group_by_summary, "The grouping function was not applied").to_contain_text(
            function_title
        )
        expect(self.group_by_summary, "The group key was not applied").to_contain_text(
            attribute_key
        )

    @property
    def consolidation_summary(self) -> Locator:
        return self.root.get_by_role("group", name="Consolidation", exact=True)

    def change_consolidation(self, function_title: str, lookback_minutes: int) -> None:
        """Set the consolidation function, as its dropdown names it (e.g. "Max"), and lookback."""
        logger.info(
            "Change the consolidation to '%s' over the last %d minutes",
            function_title,
            lookback_minutes,
        )
        self.consolidation_summary.get_by_role("button", name="Edit consolidation").click()
        self.root.get_by_role("combobox", name="Consolidation function", exact=True).click()
        self._suggestions.pick(function_title)
        self.root.get_by_role("spinbutton", name="Lookback Minutes", exact=True).fill(
            str(lookback_minutes)
        )
        self._leave_editing()
        expect(
            self.consolidation_summary, "The consolidation function was not changed"
        ).to_contain_text(function_title, ignore_case=True)

    def _leave_editing(self) -> None:
        """Click outside the editor, which leaves editing and keeps what was entered.

        The caption above the consolidation is plain text, so the click lands on no control.
        """
        self.root.get_by_text("Consolidation", exact=True).click()
