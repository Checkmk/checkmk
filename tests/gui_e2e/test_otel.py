#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.setup.otel.add_open_telemetry_collector_prometheus_scraping import (
    AddOpenTelemetryCollectorPrometheusScraping,
)
from tests.gui_e2e.testlib.playwright.pom.setup.otel.add_open_telemetry_collector_receiver import (
    AddOpenTelemetryCollectorReceiver,
)
from tests.gui_e2e.testlib.playwright.pom.setup.otel.open_telemetry_collector_prometheus_scraping import (
    OpenTelemetryCollectorPrometheusScraping,
)
from tests.gui_e2e.testlib.playwright.pom.setup.otel.open_telemetry_collector_receiver import (
    OpenTelemetryCollectorReceiver,
)
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

OTEL_COLLECTOR_FILE_PATH = Path("etc/otel-collector/setup.yaml")
FIRST_PASSWORD_ID = "first_pwd_id"
FIRST_PASSWORD_TITLE = "OTel test password"
SECOND_PASSWORD_ID = "second_pwd_id"
SECOND_PASSWORD_TITLE = "Another OTel test password"

GRPC_CONFIG: dict[str, Any] = {
    "endpoint": {
        "address": "address.local",
        "auth": {
            "type": "basicauth",
            "userlist": [
                {
                    "username": "User name",
                    "password": {"type": "store", "value": FIRST_PASSWORD_TITLE},
                },
            ],
        },
        "export_to_syslog": False,
        "host_name_rules": [
            [
                {"type": "key", "value": "test.attribute"},
                {"type": "free", "value": "_"},
                {"type": "key", "value": "another.attribute"},
            ],
            [{"type": "free", "value": "fallback_host"}],
        ],
        "encryption": True,
        "port": "4317",
    }
}

HTTP_CONFIG: dict[str, Any] = {
    "endpoint": {
        "address": "127.0.0.1",
        "auth": {
            "type": "basicauth",
            "userlist": [
                {
                    "username": "User name",
                    "password": {"type": "store", "value": FIRST_PASSWORD_TITLE},
                },
                {
                    "username": "Another user name",
                    "password": {"type": "store", "value": SECOND_PASSWORD_TITLE},
                },
            ],
        },
        "export_to_syslog": True,
        "host_name_rules": [
            [{"type": "key", "value": "service.name"}],
        ],
        "encryption": False,
        "port": "4318",
    }
}


@pytest.fixture
def create_password(test_site: Site) -> Iterator[None]:
    """Create and delete passwords via API."""
    test_site.openapi.passwords.create(
        FIRST_PASSWORD_ID, FIRST_PASSWORD_TITLE, "Test password", "Test comment"
    )
    test_site.openapi.passwords.create(
        SECOND_PASSWORD_ID, SECOND_PASSWORD_TITLE, "Test password", "Test comment"
    )
    test_site.openapi.changes.activate_and_wait_for_completion()
    yield
    if test_site.openapi.passwords.exists(FIRST_PASSWORD_ID):
        test_site.openapi.passwords.delete(FIRST_PASSWORD_ID)
    if test_site.openapi.passwords.exists(SECOND_PASSWORD_ID):
        test_site.openapi.passwords.delete(SECOND_PASSWORD_ID)
    test_site.openapi.changes.activate_and_wait_for_completion()


def read_collector_configuration_file(site: Site) -> Any:
    file_content = site.read_file(OTEL_COLLECTOR_FILE_PATH)
    return yaml.safe_load(file_content)


@pytest.mark.skip_if_not_edition("cloud", "managed")
def test_open_telemetry_collector_receiver(
    test_site: Site,
    dashboard_page: Dashboard,
    create_password: None,
) -> None:
    """Test adding, verifying, and deleting OpenTelemetry collector receiver configuration via UI.

    The test creates a new OpenTelemetry collector receiver configuration, verifies its presence,
    and then deletes it. It also compares the configuration file created via UI with the one created
    via API.
    """
    collector_id = "otel_collector_id"
    collector_title = "OTel collector title"

    logger.info("Add OpenTelemetry collector receiver configuration via UI")
    add_otel_collector_receiver_page = AddOpenTelemetryCollectorReceiver(dashboard_page.page)
    add_otel_collector_receiver_page.unique_id_textfield.fill(collector_id)
    add_otel_collector_receiver_page.title_textfield.fill(collector_title)
    add_otel_collector_receiver_page.site_restriction_checkbox(test_site.id).check()
    add_otel_collector_receiver_page.fill_collector_receiver_properties(
        "Receiver protocol GRPC",
        GRPC_CONFIG,
    )
    add_otel_collector_receiver_page.fill_collector_receiver_properties(
        "Receiver protocol HTTP",
        HTTP_CONFIG,
    )
    add_otel_collector_receiver_page.save_configuration_button.click()
    otel_collector_receiver_page = OpenTelemetryCollectorReceiver(
        add_otel_collector_receiver_page.page, navigate_to_page=False
    )
    otel_collector_receiver_page.activate_changes()

    try:
        logger.info("Verify OpenTelemetry collector receiver configuration is present in UI")
        otel_collector_receiver_page.navigate()
        expect(
            otel_collector_receiver_page.collector_configuration_row(collector_id)
        ).to_be_visible()
        ui_collector_config = read_collector_configuration_file(test_site)

        # TODO: Uncomment when error handling is implemented
        # otel_collector_receiver_page.add_open_telemetry_collector_receiver_configuration_btn.click()
        # expect(otel_collector_receiver_page.check_error("Some error text")).to_be_visible()
    finally:
        logger.info("Delete OpenTelemetry collector receiver configuration via UI")
        otel_collector_receiver_page.delete_collector_configuration_button(collector_id).click()
        otel_collector_receiver_page.delete_confirmation_button.click()
        expect(
            otel_collector_receiver_page.collector_configuration_row(collector_id)
        ).not_to_be_visible()
        otel_collector_receiver_page.activate_changes()

    # Update the password references in the configs to use IDs for API creation
    GRPC_CONFIG["endpoint"]["auth"]["userlist"][0]["password"]["value"] = FIRST_PASSWORD_ID
    HTTP_CONFIG["endpoint"]["auth"]["userlist"][0]["password"]["value"] = FIRST_PASSWORD_ID
    HTTP_CONFIG["endpoint"]["auth"]["userlist"][1]["password"]["value"] = SECOND_PASSWORD_ID
    try:
        logger.info(
            "Recreate OpenTelemetry collector receiver configuration via API to compare configs"
        )
        test_site.openapi.otel_collector.create_receivers(
            collector_id,
            collector_title,
            False,
            receiver_protocol_grpc=GRPC_CONFIG,
            receiver_protocol_http=HTTP_CONFIG,
        )
        test_site.openapi.changes.activate_and_wait_for_completion()
        api_collector_config = read_collector_configuration_file(test_site)
        assert (
            ui_collector_config == api_collector_config
        ), "The collector configuration created via UI does not match the one created via API."
    finally:
        logger.info("Delete OpenTelemetry collector receiver configuration via API")
        test_site.openapi.otel_collector.delete_receivers(collector_id)
        test_site.openapi.changes.activate_and_wait_for_completion()


PROMETHEUS_CONFIG = {
    "job_name": "test_job",
    "scrape_interval": 30,
    "metrics_path": "/metrics",
    "targets": [{"address": "localhost", "port": 9090}],
    "host_name_rules": [
        {"type": "service_instance_id"},
        {
            "type": "custom",
            "value": [
                {"type": "key", "value": "test.attribute"},
                {"type": "free", "value": "_"},
                {"type": "key", "value": "another.attribute"},
            ],
        },
    ],
    "encryption": False,
}


@pytest.mark.skip_if_not_edition("cloud", "managed")
def test_open_telemetry_collector_prometheus_scraping(
    test_site: Site,
    dashboard_page: Dashboard,
) -> None:
    """Test adding, verifying, and deleting OpenTelemetry collector scrape configuration via UI.

    The test creates a new OpenTelemetry collector scrape configuration, verifies its presence,
    and then deletes it. It also compares the configuration file created via UI with the one
    created via API.
    """
    collector_id = "otel_collector_prometheus_scraping_id"
    collector_title = "OTel collector Prometheus scraping title"

    logger.info("Add OpenTelemetry collector: Prometheus scraping configuration via UI")
    add_otel_collector_prom_scrape_page = AddOpenTelemetryCollectorPrometheusScraping(
        dashboard_page.page
    )
    add_otel_collector_prom_scrape_page.unique_id_textfield.fill(collector_id)
    add_otel_collector_prom_scrape_page.title_textfield.fill(collector_title)
    add_otel_collector_prom_scrape_page.site_restriction_checkbox(test_site.id).check()
    add_otel_collector_prom_scrape_page.fill_collector_scrape_properties(PROMETHEUS_CONFIG)

    add_otel_collector_prom_scrape_page.save_configuration_button.click()
    otel_collector_prom_scrape_page = OpenTelemetryCollectorPrometheusScraping(
        add_otel_collector_prom_scrape_page.page, navigate_to_page=False
    )
    otel_collector_prom_scrape_page.activate_changes()

    try:
        logger.info("Verify OpenTelemetry collector scrape configuration is present in UI")
        otel_collector_prom_scrape_page.navigate()
        expect(
            otel_collector_prom_scrape_page.collector_configuration_row(collector_id)
        ).to_be_visible()
        ui_collector_config = read_collector_configuration_file(test_site)

        # TODO: Uncomment when error handling is implemented
        # otel_collector_prom_scrape_page.add_open_telemetry_collector_configuration_btn.click()
        # expect(otel_collector_prom_scrape_page.check_error("Some error text")).to_be_visible()
    finally:
        logger.info("Delete OpenTelemetry collector scrape configuration via UI")
        otel_collector_prom_scrape_page.delete_collector_configuration_button(collector_id).click()
        otel_collector_prom_scrape_page.delete_confirmation_button.click()
        expect(
            otel_collector_prom_scrape_page.collector_configuration_row(collector_id)
        ).not_to_be_visible()
        otel_collector_prom_scrape_page.activate_changes()

    try:
        logger.info(
            "Recreate OpenTelemetry collector scrape configuration via API to compare configs"
        )
        test_site.openapi.otel_collector.create_prom_scrape(
            collector_id,
            collector_title,
            False,
            prometheus_scrape_configs=[PROMETHEUS_CONFIG],
        )
        test_site.openapi.changes.activate_and_wait_for_completion()
        api_collector_config = read_collector_configuration_file(test_site)
        assert (
            ui_collector_config == api_collector_config
        ), "The collector configuration created via UI does not match the one created via API."
    finally:
        logger.info("Delete OpenTelemetry collector scrape configuration via API")
        test_site.openapi.otel_collector.delete_prom_scrape(collector_id)
        test_site.openapi.changes.activate_and_wait_for_completion()
