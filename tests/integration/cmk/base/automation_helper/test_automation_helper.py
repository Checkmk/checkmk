#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from tests.testlib.site import Site
from tests.testlib.utils import wait_until

from cmk.base.automation_helper import RELATIVE_PATH_FLAG_DISABLE_RELOADER
from cmk.base.automation_helper._app import AutomationPayload, HealthCheckResponse
from cmk.base.automation_helper._config import default_config

from ._helper_query_automation_helper import AutomationMode, HealthMode


def test_config_reloading_without_reloader(site: Site) -> None:
    with _disable_automation_helper_reloader(site):
        current_last_reload_timestamp = HealthCheckResponse.model_validate_json(
            _query_automation_helper(site, HealthMode().model_dump_json())
        ).last_reload_at
        with _fake_config_file(site):
            _query_automation_helper(
                site,
                AutomationMode(
                    payload=AutomationPayload(
                        # it doesn't matter that this automation doesn't exist, we just want to trigger a reload
                        name="non-existing-automation",
                        args=[],
                        stdin="",
                        log_level=logging.INFO,
                    )
                ).model_dump_json(),
            )
            assert (
                HealthCheckResponse.model_validate_json(
                    _query_automation_helper(site, HealthMode().model_dump_json())
                ).last_reload_at
                > current_last_reload_timestamp
            )


def test_config_reloading_with_reloader(site: Site) -> None:
    reloader_configuration = default_config(
        omd_root=Path(),
        run_directory=Path(),
        log_directory=Path(),
    ).reloader_config
    current_last_reload_timestamp = HealthCheckResponse.model_validate_json(
        _query_automation_helper(site, HealthMode().model_dump_json())
    ).last_reload_at
    with _fake_config_file(site):
        wait_until(
            lambda: (
                HealthCheckResponse.model_validate_json(
                    _query_automation_helper(site, HealthMode().model_dump_json())
                ).last_reload_at
                > current_last_reload_timestamp
            ),
            timeout=reloader_configuration.poll_interval
            + reloader_configuration.aggregation_interval
            + 2,
        )


def test_standard_workflow_involving_automations(site: Site) -> None:
    hostname = "aut-helper-test-host"
    try:
        site.openapi.hosts.create(hostname)
        site.activate_changes_and_wait_for_core_reload()
        show_host_response = site.openapi.get(f"objects/host/{hostname}")
        show_host_response.raise_for_status()
        assert show_host_response.json()["extensions"]["name"] == hostname
    finally:
        site.openapi.hosts.delete(hostname)
        site.activate_changes_and_wait_for_core_reload()


@contextmanager
def _disable_automation_helper_reloader(site: Site) -> Generator[None]:
    site.write_text_file(RELATIVE_PATH_FLAG_DISABLE_RELOADER, "")
    site.run(["omd", "restart", "automation-helper"])
    try:
        yield
    finally:
        site.delete_file(RELATIVE_PATH_FLAG_DISABLE_RELOADER)
        site.run(["omd", "restart", "automation-helper"])


@contextmanager
def _fake_config_file(site: Site) -> Generator[None]:
    site.write_text_file("etc/check_mk/conf.d/aut_helper_reload_trigger.mk", "")
    try:
        yield
    finally:
        site.delete_file("etc/check_mk/conf.d/aut_helper_reload_trigger.mk")


def _query_automation_helper(site: Site, serialized_input: str) -> str:
    return site.python_helper("_helper_query_automation_helper.py").check_output(
        input=serialized_input
    )
