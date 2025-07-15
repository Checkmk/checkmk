#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=cmk-module-layer-violation
import os
import shutil
from collections.abc import Iterator, Mapping
from pathlib import Path

import pytest

from tests.testlib.common.repo import repo_path

from tests.plugins_siteless.helpers import (
    BasicSubmitter,
    compare_services_states,
    discover_services,
    DUMPS_DIR,
    get_agent_data_filenames,
    get_raw_data,
    LOGGER,
    parser,
    store_services_states,
    summarizer,
)
from tests.unit.cmk.base.emptyconfig import EMPTYCONFIG

from cmk.ccc.hostaddress import HostName

from cmk.utils.everythingtype import EVERYTHING

from cmk.checkengine import value_store
from cmk.checkengine.checking import execute_checkmk_checks
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.fetcher import FetcherType, SourceInfo, SourceType
from cmk.checkengine.inventory import HWSWInventoryParameters

from cmk.base import config
from cmk.base.checkers import (
    CheckerPluginMapper,
    SectionPluginMapper,
)

from cmk.agent_based.v1.value_store import set_value_store_manager

os.environ["OMD_SITE"] = ""
HOSTNAME = HostName("test_host")


@pytest.fixture(name="setup_dirs", scope="function")
def _setup_dirs() -> Iterator[None]:
    var_dir = Path(os.getcwd()) / "var"
    assert not var_dir.exists()
    autochecks_dir = var_dir / "check_mk/autochecks/"
    os.makedirs(autochecks_dir, exist_ok=False)
    yield
    shutil.rmtree(var_dir)


class _AllValueStoresStoreMocker(value_store.AllValueStoresStore):
    """Mock the AllValueStoresStore class to avoid writing to disk"""

    def __init__(self) -> None:
        super().__init__(Path(), log_debug=lambda x: None)
        self.update_count = 0

    def load(self) -> Mapping[value_store.ValueStoreKey, Mapping[str, str]]:
        return {}

    def update(self, update: object) -> None:
        pass


@pytest.mark.parametrize("agent_data_filename", get_agent_data_filenames())
def test_checks_executor(
    agent_data_filename: str, request: pytest.FixtureRequest, setup_dirs: Iterator[None]
) -> None:
    agent_based_plugins = config.load_all_pluginX(repo_path() / "cmk/base/legacy_checks")
    assert not agent_based_plugins.errors
    assert agent_based_plugins.agent_sections

    source_info = SourceInfo(HOSTNAME, None, "test_dump", FetcherType.PUSH_AGENT, SourceType.HOST)
    submitter = BasicSubmitter(HOSTNAME)
    config_cache = config.ConfigCache(EMPTYCONFIG).initialize()

    # make sure logwatch doesn't crash
    config._globally_cache_config_cache(config_cache)

    discovered_services = discover_services(
        HOSTNAME, agent_data_filename, config_cache, agent_based_plugins, source_info
    )

    with (
        set_value_store_manager(
            value_store.ValueStoreManager(HOSTNAME, _AllValueStoresStoreMocker()),
            store_changes=False,
        ) as value_store_manager,
    ):
        check_plugins = CheckerPluginMapper(
            config_cache,
            agent_based_plugins.check_plugins,
            value_store_manager,
            logger=LOGGER,
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
            section_error_handling=lambda *a: "",
            check_plugins=check_plugins,
            inventory_plugins={},
            inventory_parameters=lambda host, plugin: plugin.defaults,
            params=HWSWInventoryParameters.from_raw({}),
            services=discovered_services,
            run_plugin_names=EVERYTHING,
            get_check_period=lambda *_a, **_kw: None,
            submitter=submitter,
            exit_spec=ExitSpec(),
        )
        checks_result = submitter.results
        assert checks_result

        if request.config.getoption("--store"):
            store_services_states(checks_result, agent_data_filename)
            return

        compare_services_states(checks_result, agent_data_filename)
