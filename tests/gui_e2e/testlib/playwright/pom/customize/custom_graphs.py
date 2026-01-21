# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)
graph_title: str = "My Custom Graph"


class CustomGraphs(CmkPage):
    page_title: str = "Custom graphs"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to '%s' page", self.page_title)
        self.main_menu.customize_menu(f"{self.page_title}").click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s' page", self.page_title)
        _url_pattern: str = quote_plus("custom_graphs.py")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        expect(
            self.add_graph, f"'{self.add_graph}' button not visible in '{self.page_title}' page"
        ).to_be_visible()

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    @property
    def add_graph(self) -> Locator:
        return self.get_link("Add graph")


class CreateCustomGraph(CmkPage):
    page_title: str = "Create custom graph"

    @override
    def navigate(self) -> None:
        logger.info("Navigate to 'Create custom graph' page")
        custom_graphs = CustomGraphs(self.page)
        custom_graphs.add_graph.click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Create custom graph' page")
        _url_pattern = quote_plus("edit_custom_graph.py")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def add_title(self, title: str) -> None:
        logger.info("Add title '%s' to custom graph", title)
        title_bar = self.main_area.get_input("_p_title")
        title_bar.fill(title)

    def save_graph(self) -> None:
        logger.info("Save custom graph")
        self.main_area.get_suggestion("Save & go to Custom graph").click()


class BaseGraph(CmkPage):
    @override
    def navigate(self) -> None:
        raise NotImplementedError("'navigate' method should be overridden")

    @override
    def validate_page(self) -> None:
        raise NotImplementedError("'validate_page' method should be overridden")

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def _value_cell_selector(self, n_child: int) -> Locator:
        return self.main_area.locator(
            f"#graph_0 > div > table > tbody > tr:nth-child(2) > td:nth-child({n_child})"
        )

    @property
    def min_value_cell(self) -> Locator:
        return self._value_cell_selector(2)

    @property
    def max_value_cell(self) -> Locator:
        return self._value_cell_selector(3)

    @property
    def avg_value_cell(self) -> Locator:
        return self._value_cell_selector(4)

    @property
    def last_value_cell(self) -> Locator:
        return self._value_cell_selector(5)


class DesignGraph(BaseGraph):
    page_title: str = f"Design graph '{graph_title}'"

    @override
    def navigate(self) -> None:
        create_custom_graph = CreateCustomGraph(self.page)
        create_custom_graph.add_title(graph_title)
        create_custom_graph.save_graph()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Design graph' page")
        _url_pattern = quote_plus("custom_graph_design.py")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.main_area.check_page_title(self.page_title)

    def add_graph_line_otel(self, metric_name: str) -> None:
        self.main_area.get_text("Metric name", exact=False).click()
        self.main_area.get_text(metric_name).click()
        self.main_area.get_text("Add").click()

    def save_graph(self) -> None:
        logger.info("Save designed graph")
        self.main_area.get_suggestion("Save").click()

    def open_slide_in_for_metric_backend_rule(self) -> None:
        logger.info("Open 'Design graph' slide-in")
        slide_in_selector = (
            "#form_graph_designer_form_context > cmk-graph-designer > div > table > "
            "tbody > tr > td:nth-child(3) > img:nth-child(4)"
        )
        self.main_area.locator(slide_in_selector).click()
        ruleset_name = "special_agents:custom_query_metric_backend"
        expect(
            self.main_area.get_text(ruleset_name),
            f"Ruleset name'{ruleset_name}' not visible.",
        ).to_be_visible()

    def save_rule_via_slide_in(self) -> None:
        logger.info("Save rule via 'Design graph' slide-in")
        save_button_selector = (
            "body > div.cmk-vue-app.cmk-slide-in__container.cmk-slide-in--"
            "size-medium > div > div > div.form-edit-async__buttons > "
            "button.cmk-button.cmk-button--variant-secondary"
        )
        self.main_area.locator(save_button_selector).click()


class CustomGraph(BaseGraph):
    page_title: str = "Custom graph"

    @override
    def navigate(self) -> None:
        custom_graphs = CustomGraphs(self.page)
        custom_graphs.navigate()
        custom_graphs.get_link(graph_title).click()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is '%s page", self.page_title)
        _url_pattern: str = quote_plus("custom_graph.py")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        expect(
            self.edit_graph,
            f"'{self.edit_graph}' button not visible in '{self.page_title}' page",
        ).to_be_visible()

    @property
    def edit_graph(self) -> Locator:
        return self.get_link("Edit graph")
