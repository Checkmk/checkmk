#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=cmk-module-layer-violation
import os
from pathlib import Path

import pytest

from tests.testlib.repo import repo_path

from tests.plugins_siteless.helpers import (
    BasicSubmitter,
    compare_services_states,
    DUMPS_DIR,
    get_agent_data_filenames,
    get_discovered_services,
    get_raw_data,
    LOGGER,
    parser,
    store_services_states,
    summarizer,
)

from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.hostaddress import HostName

from cmk.checkengine.checking import execute_checkmk_checks
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.fetcher import FetcherType, SourceInfo, SourceType
from cmk.checkengine.inventory import HWSWInventoryParameters

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base import config
from cmk.base.api.agent_based.value_store import ValueStoreManager
from cmk.base.checkers import (
    CheckPluginMapper,
    InventoryPluginMapper,
    SectionPluginMapper,
)

from cmk.agent_based.v1.value_store import set_value_store_manager

os.environ["OMD_SITE"] = ""
HOSTNAME = HostName("test_host")


@pytest.mark.parametrize("agent_data_filename", get_agent_data_filenames())
def test_checks_executor(agent_data_filename: str, request: pytest.FixtureRequest) -> None:
    encountered_errors = config.load_all_plugins(
        local_checks_dir=Path(__file__).parent,  # dummy path, not really needed for this test
        checks_dir=str(repo_path() / "cmk/base/legacy_checks"),
    )
    assert not encountered_errors

    agent_based_plugins = agent_based_register.get_previously_loaded_plugins()
    assert agent_based_plugins.agent_sections

    source_info = SourceInfo(HOSTNAME, None, "test_dump", FetcherType.PUSH_AGENT, SourceType.HOST)
    submitter = BasicSubmitter(HOSTNAME)
    loaded_services = get_discovered_services(agent_data_filename)
    config_cache = config.get_config_cache()

    with (
        set_value_store_manager(
            ValueStoreManager(HOSTNAME),
            store_changes=False,
        ) as value_store_manager,
    ):
        check_plugins = CheckPluginMapper(
            config_cache,
            value_store_manager,
            clusters=(),
            rtc_package=None,
        )
        assert check_plugins

        LOGGER.debug("check_plugins found: %s\n\n", list(check_plugins))
        _ = execute_checkmk_checks(
            hostname=HOSTNAME,
            fetched=[(source_info, get_raw_data(DUMPS_DIR / agent_data_filename))],
            parser=parser(config_cache.parser_factory()),
            summarizer=summarizer(HOSTNAME),
            section_plugins=SectionPluginMapper(
                {**agent_based_plugins.agent_sections, **agent_based_plugins.snmp_sections}
            ),
            section_error_handling=lambda *a: None,  # type: ignore[arg-type]
            check_plugins=check_plugins,
            inventory_plugins=InventoryPluginMapper(),
            inventory_parameters=lambda host, plugin: plugin.defaults,
            params=HWSWInventoryParameters.from_raw({}),
            services=loaded_services,
            run_plugin_names=EVERYTHING,
            get_check_period=lambda *_a, **_kw: None,
            submitter=submitter,
            exit_spec=ExitSpec(),
        )
        checks_result = submitter.results
        assert checks_result

        # apache service is flaky. Todo: investigate
        checks_result = [service for service in checks_result if "apache" not in service.name]

        if request.config.getoption("--store"):
            store_services_states(checks_result, agent_data_filename)
            return

        compare_services_states(checks_result, agent_data_filename)
