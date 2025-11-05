import logging
import re
from typing import override
from urllib.parse import quote_plus

from playwright.sync_api import expect, Locator

from tests.gui_e2e.testlib.playwright.helpers import DropdownListNameToID
from tests.gui_e2e.testlib.playwright.pom.page import CmkPage

logger = logging.getLogger(__name__)


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


class DesignGraph(CmkPage):
    graph_title: str = "My Custom Graph"
    page_title: str = f"Design graph '{graph_title}'"

    @override
    def navigate(self) -> None:
        create_custom_graph = CreateCustomGraph(self.page)
        create_custom_graph.add_title(self.graph_title)
        create_custom_graph.save_graph()
        self.validate_page()

    @override
    def validate_page(self) -> None:
        logger.info("Validate that current page is 'Design graph' page")
        _url_pattern = quote_plus("custom_graph_design.py")
        self.page.wait_for_url(url=re.compile(_url_pattern), wait_until="load")
        self.main_area.check_page_title(self.page_title)

    @override
    def _dropdown_list_name_to_id(self) -> DropdownListNameToID:
        return DropdownListNameToID()

    def add_graph_line_otel(self, metric_name: str) -> None:
        self.main_area.get_text("Metric name").click()
        self.main_area.get_text(metric_name).click()
        self.main_area.get_text("Add").click()

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
