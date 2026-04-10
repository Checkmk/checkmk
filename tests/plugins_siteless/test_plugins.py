#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path

import pytest

from cmk.agent_based.v1.value_store import set_value_store_manager
from cmk.agent_based.v2 import CheckPlugin
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.checkers import (
    CheckerConfig,
    CheckerPluginMapper,
    SectionPluginMapper,
)
from cmk.ccc.hostaddress import HostName
from cmk.ccc.version import edition
from cmk.checkengine import value_store
from cmk.checkengine.checking import execute_checkmk_checks
from cmk.checkengine.exitspec import ExitSpec
from cmk.checkengine.inventory import HWSWInventoryParameters
from cmk.helper_interface import FetcherType, SourceInfo, SourceType
from cmk.logwatch.config import ParameterLogwatchEc, ParameterLogwatchRules, set_global_state
from cmk.utils import paths
from cmk.utils.everythingtype import EVERYTHING
from cmk.utils.timeperiod import TimeperiodName
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
from tests.testlib.common.empty_config import EMPTY_CONFIG
from tests.testlib.common.repo import repo_path

os.environ["OMD_SITE"] = ""
HOSTNAME = HostName("test_host")


@pytest.fixture(name="setup_dirs", scope="function")
def _setup_dirs() -> Iterator[None]:
    var_dir = Path(os.getcwd()) / "var"
    if var_dir.exists():
        shutil.rmtree(var_dir)
    autochecks_dir = var_dir / "check_mk/autochecks/"
    os.makedirs(autochecks_dir)
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


class _LogwatchConfigMocker:
    def __init__(self) -> None:
        self.base_spool_path = paths.var_dir / "logwatch_spool"
        self.msg_dir = paths.var_dir / "logwatch"
        self.omd_root = paths.omd_root
        self.debug = False

    def logwatch_rules_all(
        self, *, host_name: str, plugin: CheckPlugin, logfile: str
    ) -> Sequence[ParameterLogwatchRules]:
        return ()

    def logwatch_ec_all(self, host_name: str) -> Sequence[ParameterLogwatchEc]:
        return ()


@pytest.mark.medium_test_chain
@pytest.mark.parametrize("agent_data_filename", get_agent_data_filenames())
def test_checks_executor(
    agent_data_filename: str, request: pytest.FixtureRequest, setup_dirs: Iterator[None]
) -> None:
    xfail_list = [
        "agent-2.3.0b1-special-openshift-v1.27.1-3507",
        "agent-2.2.0p16-special-eks-v1.27.8-eks-8cb36c9",
        "agent-2.2.0p16-special-openshift-v1.22.1-1839",
        "agent-0.0.0p0-kubernetes",
    ]

    if any(_ in request.node.name for _ in xfail_list):
        pytest.xfail(reason="CMK-33440: Failing plugin_siteless tests...")

    agent_based_plugins = config.load_all_pluginX(repo_path() / "cmk/legacy_checks")
    assert not agent_based_plugins.errors
    assert agent_based_plugins.agent_sections

    source_info = SourceInfo(HOSTNAME, None, "test_dump", FetcherType.PUSH_AGENT, SourceType.HOST)
    submitter = BasicSubmitter(HOSTNAME)
    config_cache = config.ConfigCache(
        EMPTY_CONFIG,
        (get_builtin_host_labels := make_app(edition(paths.omd_root)).get_builtin_host_labels),
        edition(paths.omd_root),
    ).initialize(get_builtin_host_labels)
    parser_config = config.make_parser_config(
        EMPTY_CONFIG,
        config_cache.ruleset_matcher,
        config_cache.label_manager,
        ip_address_of=config_cache.primary_ip_address_of,
    )

    # make sure logwatch doesn't crash
    set_global_state(_LogwatchConfigMocker())

    discovered_services = discover_services(
        HOSTNAME,
        agent_data_filename,
        parser_config,
        config_cache.ruleset_matcher,
        config_cache.check_plugin_ignored,
        agent_based_plugins,
        source_info,
    )

    with (
        set_value_store_manager(
            value_store.ValueStoreManager(HOSTNAME, _AllValueStoresStoreMocker()),
            store_changes=False,
        ) as value_store_manager,
    ):
        check_plugins = CheckerPluginMapper(
            CheckerConfig(
                only_from=config_cache.only_from,
                effective_service_level=config_cache.effective_service_level,
                get_clustered_service_configuration=config_cache.get_clustered_service_configuration,
                nodes=config_cache.nodes,
                effective_host=config_cache.effective_host,
                get_snmp_backend=config_cache.get_snmp_backend,
                timeperiods_active={},
            ),
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
            omd_root=Path(""),
            fetched=[(source_info, get_raw_data(DUMPS_DIR / agent_data_filename))],
            parser=parser(parser_config),
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
            get_check_period=lambda *_a, **_kw: TimeperiodName("24X7"),
            submitter=submitter,
            exit_spec=ExitSpec(),
            timeperiods_active={},
        )
        checks_result = submitter.results
        assert checks_result

        if request.config.getoption("--store"):
            store_services_states(checks_result, agent_data_filename)
            return

        compare_services_states(checks_result, agent_data_filename)
