#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import argparse
import logging
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import auto, Enum
from pathlib import Path
from typing import Final

import meraki  # type: ignore[import]

from cmk.utils.paths import tmp_dir

from cmk.special_agents.utils.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser
from cmk.special_agents.utils.misc import DataCache

_LOGGER = logging.getLogger("agent_cisco_meraki")

_BASE_CACHE_FILE_DIR = Path(tmp_dir) / "agents" / "agent_cisco_meraki"

_API_NAME_ORGANISATION_ID: Final = "organizationId"

_SEC_NAME_LICENSES_OVERVIEW: Final = "licenses-overview"

_SECTION_NAME_MAP = {
    _SEC_NAME_LICENSES_OVERVIEW: "licenses_overview",
}

MerakiAPIData = Mapping[str, object]

#   .--dashboard-----------------------------------------------------------.
#   |              _           _     _                         _           |
#   |           __| | __ _ ___| |__ | |__   ___   __ _ _ __ __| |          |
#   |          / _` |/ _` / __| '_ \| '_ \ / _ \ / _` | '__/ _` |          |
#   |         | (_| | (_| \__ \ | | | |_) | (_) | (_| | | | (_| |          |
#   |          \__,_|\__,_|___/_| |_|_.__/ \___/ \__,_|_|  \__,_|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def _configure_meraki_dashboard(
    api_key: str,
    debug: bool,
    proxy: str | None,
) -> meraki.DashboardAPI:
    return meraki.DashboardAPI(
        api_key=api_key,
        print_console=True,
        output_log=False,
        suppress_logging=not (debug),
        requests_proxy=proxy,
    )


# .
#   .--section-------------------------------------------------------------.
#   |                                 _   _                                |
#   |                   ___  ___  ___| |_(_) ___  _ __                     |
#   |                  / __|/ _ \/ __| __| |/ _ \| '_ \                    |
#   |                  \__ \  __/ (__| |_| | (_) | | | |                   |
#   |                  |___/\___|\___|\__|_|\___/|_| |_|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class MerakiAPIDataSource(Enum):
    org = auto()


@dataclass(frozen=True)
class Section:
    api_data_source: MerakiAPIDataSource
    name: str
    data: MerakiAPIData
    piggyback: str | None = None

    def get_name(self) -> str:
        return "_".join(["cisco_meraki", self.api_data_source.name, self.name])


# .
#   .--caches--------------------------------------------------------------.
#   |                                  _                                   |
#   |                    ___ __ _  ___| |__   ___  ___                     |
#   |                   / __/ _` |/ __| '_ \ / _ \/ __|                    |
#   |                  | (_| (_| | (__| | | |  __/\__ \                    |
#   |                   \___\__,_|\___|_| |_|\___||___/                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class GetOrganisationIDsCache(DataCache):
    def __init__(self, config: MerakiConfig) -> None:
        super().__init__(_BASE_CACHE_FILE_DIR / config.hostname / "organisations", "organisations")
        self._dashboard = config.dashboard

    @property
    def cache_interval(self) -> int:
        # Once per day
        return 86400

    def get_validity_from_args(self, *args: object) -> bool:
        return True

    def get_live_data(self, *args: object) -> Sequence[str]:
        try:
            return [
                organisation[_API_NAME_ORGANISATION_ID]
                for organisation in self._dashboard.organizations.getOrganizations()
            ]
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Get organisations: %r", e)
            return []


# .
#   .--queries-------------------------------------------------------------.
#   |                                        _                             |
#   |                   __ _ _   _  ___ _ __(_) ___  ___                   |
#   |                  / _` | | | |/ _ \ '__| |/ _ \/ __|                  |
#   |                 | (_| | |_| |  __/ |  | |  __/\__ \                  |
#   |                  \__, |\__,_|\___|_|  |_|\___||___/                  |
#   |                     |_|                                              |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class MerakiOrganisation:
    config: MerakiConfig
    organisation_id: str

    def query(self) -> Iterator[Section]:
        if _SEC_NAME_LICENSES_OVERVIEW in self.config.section_names:
            if licenses_overview := self._get_licenses_overview():
                yield self._make_section(
                    name=_SEC_NAME_LICENSES_OVERVIEW,
                    data=licenses_overview,
                )

    def _get_licenses_overview(self) -> MerakiAPIData | None:
        try:
            return self.config.dashboard.organizations.getOrganizationLicensesOverview(
                self.organisation_id,
            )
        except meraki.exceptions.APIError as e:
            _LOGGER.debug("Organisation ID: %r: Get license overview: %r", self.organisation_id, e)
            return None

    def _make_section(self, *, name: str, data: MerakiAPIData) -> Section:
        return Section(
            api_data_source=MerakiAPIDataSource.org,
            name=_SECTION_NAME_MAP[name],
            data=data,
        )


def _query_meraki_objects(*, organisations: Sequence[MerakiOrganisation]) -> Iterable[Section]:
    for organisation in organisations:
        yield from organisation.query()


def _write_sections(sections: Iterable[Section]) -> None:
    sections_by_piggyback: dict = {}
    for section in sections:
        sections_by_piggyback.setdefault(section.piggyback, {}).setdefault(
            section.get_name(), []
        ).append(section.data)

    for piggyback, pb_section in sections_by_piggyback.items():
        with ConditionalPiggybackSection(piggyback):
            for section_name, section_data in pb_section.items():
                with SectionWriter(section_name) as writer:
                    writer.append_json(section_data)


# .
#   .--main----------------------------------------------------------------.
#   |                                       _                              |
#   |                       _ __ ___   __ _(_)_ __                         |
#   |                      | '_ ` _ \ / _` | | '_ \                        |
#   |                      | | | | | | (_| | | | | |                       |
#   |                      |_| |_| |_|\__,_|_|_| |_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = create_default_argument_parser(description=__doc__)

    parser.add_argument("hostname")
    parser.add_argument(
        "apikey",
        help="API key for the Meraki API dashboard access.",
    )

    parser.add_argument("--proxy", type=str)

    parser.add_argument(
        "--sections",
        nargs="+",
        choices=list(_SECTION_NAME_MAP),
        default=[],
        help="Explicit sections that are collected.",
    )

    parser.add_argument(
        "--orgs",
        nargs="+",
        default=[],
        help="Explicit organisation IDs that are checked.",
    )

    return parser.parse_args(argv)


@dataclass(frozen=True)
class MerakiConfig:
    dashboard: meraki.DashboardAPI
    hostname: str
    section_names: Sequence[str]


def _get_organisation_ids(config: MerakiConfig, orgs: Sequence[str]) -> Sequence[str]:
    if not _need_organisations(config.section_names):
        return []
    return orgs if orgs else GetOrganisationIDsCache(config).get_live_data()


def _need_organisations(section_names: Sequence[str]) -> bool:
    return any(s in section_names for s in [_SEC_NAME_LICENSES_OVERVIEW])


def agent_cisco_meraki_main(args: Args) -> None:
    config = MerakiConfig(
        dashboard=_configure_meraki_dashboard(
            args.apikey,
            args.debug,
            args.proxy,
        ),
        hostname=args.hostname,
        section_names=args.sections,
    )

    sections = _query_meraki_objects(
        organisations=[
            MerakiOrganisation(config, organisation_id)
            for organisation_id in _get_organisation_ids(config, args.orgs)
        ]
    )

    _write_sections(sections)


def main() -> None:
    special_agent_main(parse_arguments, agent_cisco_meraki_main)
