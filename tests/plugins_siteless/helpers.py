#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=cmk-module-layer-violation
import json
import logging
import os
import pickle
import pprint
import re
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from tests.testlib.repo import qa_test_data_path

import cmk.utils.resulttype as result
from cmk.utils.hostaddress import HostName
from cmk.utils.resulttype import OK

from cmk.fetchers import Mode
from cmk.fetchers.filecache import AgentFileCache, FileCacheMode, MaxAge

from cmk.checkengine.checking import ConfiguredService
from cmk.checkengine.parser import NO_SELECTION
from cmk.checkengine.submitters import (
    FormattedSubmittee,
    Submitter,
)
from cmk.checkengine.summarize import SummaryConfig

from cmk.base.checkers import (
    CMKParser,
    CMKSummarizer,
)
from cmk.base.config import ParserFactory
from cmk.base.modes.check_mk import (  # type: ignore[attr-defined]
    CheckPluginName,
)

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


def _get_discovered_services_path(target_name: str) -> Path:
    discovered_services_dir = DATA_DIR / "discovered_services"
    assert discovered_services_dir.exists()

    for file_name in os.listdir(discovered_services_dir):
        if target_name in file_name:
            return discovered_services_dir / file_name

    raise FileNotFoundError(f"No discovered services file found for target {target_name}")


def get_discovered_services(agent_data_filename: str) -> Sequence[ConfiguredService]:
    """Load ConfiguredService instances from a pickle file."""
    # agent_data_filename must be in the format 'agentVersion_targetName_targetVersion'
    # here we extract the targetName from the filename
    if match := re.match(r"^(.+?)_(.+?)_(.*)$", agent_data_filename):
        target_name = match.group(2)
    else:
        raise ValueError(
            f"Invalid agent data filename: {agent_data_filename}. "
            f"Expected format: 'agentVersion_targetName_targetVersion'"
        )

    with open(_get_discovered_services_path(target_name), "rb") as discovered_services_path:
        loaded_services = pickle.load(discovered_services_path)

    return [
        ConfiguredService(
            check_plugin_name=CheckPluginName(service["plugin_name"]),
            item=service["item"],
            description=service["description"],
            parameters=service["parameters"],
            discovered_parameters=service["discovered_parameters"],
            labels=service["labels"],
            discovered_labels=service["discovered_labels"],
            is_enforced=service["is_enforced"],
        )
        for service in loaded_services
    ]


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
    LOGGER.info("%s services found", len(checks_result))
    actual_states = {s.name: s.state for s in checks_result}
    LOGGER.info("Services' states:\n%s", pprint.pformat(actual_states))
    LOGGER.debug(
        "Services' details:\n%s", pprint.pformat({s.name: s.details for s in checks_result})
    )
    assert actual_states == expected_services_states
