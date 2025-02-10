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

from cmk.automations.helper_api import AutomationPayload

from cmk.base.automation_helper._app import HealthCheckResponse
from cmk.base.automation_helper._config import (
    Config,
    default_config,
    RELATIVE_CONFIG_PATH_FOR_TESTING,
    ReloaderConfig,
    ServerConfig,
)

from ._helper_query_automation_helper import AutomationMode, HealthMode


def test_config_reloading_without_reloader(site: Site) -> None:
    with _disable_automation_helper_reloader_and_set_worker_count_to_one(site):
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
            + reloader_configuration.cooldown_interval
            + 2,
        )


def test_standard_workflow_involving_automations(site: Site) -> None:
    hostname = "aut-helper-test-host"
    try:
        site.openapi.hosts.create(
            hostname,
            attributes={"ipaddress": "127.0.0.1"},
        )
        site.activate_changes_and_wait_for_core_reload()
        show_host_response = site.openapi.get(f"objects/host/{hostname}")
        show_host_response.raise_for_status()
        assert show_host_response.json()["extensions"]["name"] == hostname
    finally:
        site.openapi.hosts.delete(hostname)
        site.activate_changes_and_wait_for_core_reload()


@contextmanager
def _disable_automation_helper_reloader_and_set_worker_count_to_one(site: Site) -> Generator[None]:
    default_configuration = default_config(
        omd_root=site.root,
        run_directory=site.root / "tmp" / "run",
        log_directory=site.root / "var" / "log" / "automation-helper",
    )
    adjusted_configuration = Config(
        server_config=ServerConfig(
            unix_socket=default_configuration.server_config.unix_socket,
            pid_file=default_configuration.server_config.pid_file,
            access_log=default_configuration.server_config.access_log,
            error_log=default_configuration.server_config.error_log,
            num_workers=1,
        ),
        watcher_config=default_configuration.watcher_config,
        reloader_config=ReloaderConfig(
            active=False,
            poll_interval=default_configuration.reloader_config.poll_interval,
            cooldown_interval=default_configuration.reloader_config.cooldown_interval,
        ),
    )
    site.write_text_file(RELATIVE_CONFIG_PATH_FOR_TESTING, adjusted_configuration.model_dump_json())
    site.run(["omd", "restart", "automation-helper"])
    try:
        yield
    finally:
        site.delete_file(RELATIVE_CONFIG_PATH_FOR_TESTING)
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
