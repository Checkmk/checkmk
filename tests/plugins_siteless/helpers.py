#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=cmk-module-layer-violation
import json
import logging
import os
import pprint
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from tests.testlib.common.repo import qa_test_data_path

import cmk.ccc.resulttype as result
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostName
from cmk.ccc.resulttype import OK

from cmk.utils.everythingtype import EVERYTHING

from cmk.fetchers import Mode
from cmk.fetchers.filecache import AgentFileCache, FileCacheMode, MaxAge

from cmk.checkengine.discovery import ABCDiscoveryConfig, commandline_discovery
from cmk.checkengine.discovery._autochecks import AutochecksStore
from cmk.checkengine.fetcher import SourceInfo
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.parser import NO_SELECTION
from cmk.checkengine.plugins import AgentBasedPlugins, ConfiguredService
from cmk.checkengine.submitters import (
    FormattedSubmittee,
    Submitter,
)
from cmk.checkengine.summarize import SummaryConfig

from cmk.base.checkers import (
    CMKParser,
    CMKSummarizer,
    DiscoveryPluginMapper,
    HostLabelPluginMapper,
    SectionPluginMapper,
)
from cmk.base.config import ConfigCache, ParserFactory

LOGGER = logging.getLogger(__name__)
DATA_DIR = qa_test_data_path() / "plugins_siteless"
DUMPS_DIR = DATA_DIR / "agent_data"
SERVICES_STATES_DIR = DATA_DIR / "services_states"


class BasicSubmitter(Submitter):
    """Patches the submission of check results to the core.

    Instead of submitting, we just store the results in an attribute for later use.
    """

    def __init__(self, hostname_: HostName) -> None:
        super().__init__(hostname_, perfdata_format="standard", show_perfdata=True)
        self.results: list[FormattedSubmittee] = []

    def _submit(self, formatted_submittees: Iterable[FormattedSubmittee]) -> None:
        self.results.extend(formatted_submittees)


def get_raw_data(dump_path: Path) -> OK:
    agent_cache = AgentFileCache(
        path_template=str(dump_path),
        max_age=MaxAge.unlimited(),
        simulation=False,
        use_only_cache=True,
        file_cache_mode=FileCacheMode.READ,
    )

    fetched_data = agent_cache.read(Mode.CHECKING)
    assert fetched_data
    LOGGER.debug("fetched_data: %s\n\n", fetched_data)
    return result.OK(fetched_data)


def parser(factory: ParserFactory) -> CMKParser:
    return CMKParser(
        factory=factory,
        selected_sections=NO_SELECTION,
        keep_outdated=False,
        logger=logging.getLogger("cmk.base.checking"),
    )


def summarizer(hostname_: HostName) -> CMKSummarizer:
    def _summary_config(host_name: HostName, source_id: str) -> SummaryConfig:
        return SummaryConfig(
            exit_spec={},
            time_settings=(),
            expect_data=False,
        )

    return CMKSummarizer(
        hostname_,
        _summary_config,
        override_non_ok_state=None,
    )


def get_agent_data_filenames() -> list[str]:
    assert DUMPS_DIR.exists()
    return [p for p in os.listdir(DUMPS_DIR) if os.path.isfile(os.path.join(DUMPS_DIR, p))]


def store_services_states(
    checks_result: list[FormattedSubmittee], services_states_filename: str
) -> None:
    services_states_dict = {
        service.name: {"expected_state": service.state} for service in checks_result
    }
    services_states_path = SERVICES_STATES_DIR / (services_states_filename + ".json")
    assert services_states_path.parent.exists()
    services_states_path.write_text(json.dumps(services_states_dict, indent=2))


def _load_expected_states(file_name: str) -> Mapping[str, int]:
    services_states_path = SERVICES_STATES_DIR / f"{file_name}.json"
    raw = json.loads(services_states_path.read_text())
    return {str(k): int(v["expected_state"]) for k, v in raw.items()}


def compare_services_states(
    checks_result: list[FormattedSubmittee], services_states_filename: str
) -> None:
    expected_services_states = _load_expected_states(services_states_filename)
    actual_states = {s.name: s.state for s in checks_result}
    LOGGER.info(
        "%s services executed. Services' states:\n%s",
        len(checks_result),
        pprint.pformat(actual_states),
    )
    LOGGER.debug(
        "Services' details:\n%s", pprint.pformat({s.name: s.details for s in checks_result})
    )
    assert actual_states == expected_services_states, (
        f"\nActual-states\n:"
        f"{pprint.pformat(actual_states)}\n"
        f"\nExpected-states:\n"
        f"{pprint.pformat(expected_services_states)}\n"
        f"\nDiff:\n"
        f"{pprint.pformat(set(actual_states.items()) ^ set(expected_services_states.items()))}\n"
    )


class _EmptyDiscoveryConfig(ABCDiscoveryConfig):
    def __call__(
        self, host_name: object, rule_set_name: object, rule_set_type: str
    ) -> Mapping[str, object] | Sequence[Mapping[str, object]]:
        return [] if rule_set_type == "all" else {}


def discover_services(
    hostname: HostName,
    agent_data_filename: str,
    config_cache: ConfigCache,
    agent_based_plugins: AgentBasedPlugins,
    source_info: SourceInfo,
) -> Sequence[ConfiguredService]:
    def _fetcher():
        return lambda *a, **ka: [(source_info, get_raw_data(DUMPS_DIR / agent_data_filename))]

    commandline_discovery(
        hostname,
        clear_ruleset_matcher_caches=config_cache.ruleset_matcher.clear_caches,
        parser=parser(config_cache.parser_factory()),
        fetcher=_fetcher(),
        section_plugins=SectionPluginMapper(
            {**agent_based_plugins.agent_sections, **agent_based_plugins.snmp_sections}
        ),
        section_error_handling=lambda *a: "",
        host_label_plugins=HostLabelPluginMapper(
            discovery_config=_EmptyDiscoveryConfig(),
            sections={
                **agent_based_plugins.agent_sections,
                **agent_based_plugins.snmp_sections,
            },
        ),
        plugins=DiscoveryPluginMapper(
            discovery_config=_EmptyDiscoveryConfig(),
            check_plugins=agent_based_plugins.check_plugins,
        ),
        run_plugin_names=EVERYTHING,
        ignore_plugin=config_cache.check_plugin_ignored,
        arg_only_new=False,
        only_host_labels=False,
        on_error=OnError.RAISE,
    )

    autochecks_store = AutochecksStore(hostname)
    autochecks = autochecks_store.read()

    discovered_services = [
        ConfiguredService(
            check_plugin_name=autocheck.check_plugin_name,
            item=autocheck.item,
            description=agent_based_plugins.check_plugins[autocheck.check_plugin_name].service_name
            if autocheck.item is None
            else agent_based_plugins.check_plugins[autocheck.check_plugin_name].service_name
            % autocheck.item,
            parameters=TimespecificParameters(
                [
                    TimespecificParameterSet.from_parameters(autocheck.parameters),
                    TimespecificParameterSet.from_parameters(
                        agent_based_plugins.check_plugins[
                            autocheck.check_plugin_name
                        ].check_default_parameters
                        or {}
                    ),
                ]
            ),
            discovered_parameters=autocheck.parameters,
            labels=autocheck.service_labels,
            discovered_labels=autocheck.service_labels,
            is_enforced=False,
        )
        for autocheck in autochecks
    ]
    LOGGER.info(
        "%s services discovered:\n%s",
        len(discovered_services),
        pprint.pformat(sorted([str(service.description) for service in discovered_services])),
    )
    return discovered_services
