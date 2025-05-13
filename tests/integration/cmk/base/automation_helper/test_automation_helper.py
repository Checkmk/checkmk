#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import subprocess
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.integration.linux_test_host import create_linux_test_host

from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

from cmk.utils.rulesets.definition import RuleGroup

from cmk.automations.helper_api import AutomationPayload, AutomationResponse
from cmk.automations.results import AnalyseServiceResult, SerializedResult

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


def test_two_subsequent_automations_involving_ruleset_matcher_same_ruleset_different_hosts(
    request: pytest.FixtureRequest,
    site: Site,
) -> None:
    fs_rule_id = None
    try:
        create_linux_test_host(request, site, "host1")
        create_linux_test_host(request, site, "host2")
        site.openapi.service_discovery.run_discovery_and_wait_for_completion("host1")
        site.openapi.service_discovery.run_discovery_and_wait_for_completion("host2")
        fs_rule_id = site.openapi.rules.create(
            {"magic": 0.8},
            ruleset_name=RuleGroup.CheckgroupParameters("filesystem"),
        )
        site.activate_changes_and_wait_for_core_reload()

        with _set_automation_helper_worker_count_to_one(site):
            analyse_service_result_host1 = _query_analyse_service(site, ["host1", "Filesystem /"])
            analyse_service_result_host2 = _query_analyse_service(site, ["host2", "Filesystem /"])

        service_params_host1 = analyse_service_result_host1.service_info.get("parameters")
        service_params_host2 = analyse_service_result_host2.service_info.get("parameters")
        assert isinstance(service_params_host1, dict)
        assert isinstance(service_params_host2, dict)
        assert service_params_host1["magic"] == service_params_host2["magic"] == 0.8

    finally:
        if fs_rule_id is not None:
            site.openapi.rules.delete(fs_rule_id)
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
            unix_socket_path=default_configuration.server_config.unix_socket_path,
            unix_socket_permissions=default_configuration.server_config.unix_socket_permissions,
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
    site.write_file(RELATIVE_CONFIG_PATH_FOR_TESTING, adjusted_configuration.model_dump_json())
    _restart_automation_helper_and_wait_until_reachable(site)
    try:
        yield
    finally:
        site.delete_file(RELATIVE_CONFIG_PATH_FOR_TESTING)
        _restart_automation_helper_and_wait_until_reachable(site)


@contextmanager
def _set_automation_helper_worker_count_to_one(site: Site) -> Generator[None]:
    default_configuration = default_config(
        omd_root=site.root,
        run_directory=site.root / "tmp" / "run",
        log_directory=site.root / "var" / "log" / "automation-helper",
    )
    adjusted_configuration = Config(
        server_config=ServerConfig(
            unix_socket_path=default_configuration.server_config.unix_socket_path,
            unix_socket_permissions=default_configuration.server_config.unix_socket_permissions,
            pid_file=default_configuration.server_config.pid_file,
            access_log=default_configuration.server_config.access_log,
            error_log=default_configuration.server_config.error_log,
            num_workers=1,
        ),
        watcher_config=default_configuration.watcher_config,
        reloader_config=default_configuration.reloader_config,
    )
    site.write_file(RELATIVE_CONFIG_PATH_FOR_TESTING, adjusted_configuration.model_dump_json())
    _restart_automation_helper_and_wait_until_reachable(site)
    try:
        yield
    finally:
        site.delete_file(RELATIVE_CONFIG_PATH_FOR_TESTING)
        _restart_automation_helper_and_wait_until_reachable(site)


@contextmanager
def _fake_config_file(site: Site) -> Generator[None]:
    site.write_file("etc/check_mk/conf.d/aut_helper_reload_trigger.mk", "")
    try:
        yield
    finally:
        site.delete_file("etc/check_mk/conf.d/aut_helper_reload_trigger.mk")


def _query_automation_helper(site: Site, serialized_input: str) -> str:
    return site.python_helper("_helper_query_automation_helper.py").check_output(
        input_=serialized_input
    )


def _query_analyse_service(site: Site, args: Sequence[str]) -> AnalyseServiceResult:
    return AnalyseServiceResult.deserialize(
        SerializedResult(
            AutomationResponse.model_validate_json(
                _query_automation_helper(
                    site,
                    AutomationMode(
                        payload=AutomationPayload(
                            name="analyse-service",
                            args=args,
                            stdin="",
                            log_level=logging.INFO,
                        )
                    ).model_dump_json(),
                )
            ).serialized_result_or_error_code
        )
    )


def _restart_automation_helper_and_wait_until_reachable(site: Site) -> None:
    def health_endpoint_is_reachable() -> bool:
        try:
            HealthCheckResponse.model_validate_json(
                _query_automation_helper(site, HealthMode().model_dump_json())
            )
        except subprocess.CalledProcessError:
            return False
        return True

    site.omd("restart", "automation-helper", check=True)
    wait_until(
        health_endpoint_is_reachable,
        timeout=10,
        interval=0.25,
    )
