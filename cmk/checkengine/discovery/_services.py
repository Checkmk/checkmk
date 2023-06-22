#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Container, Iterable, Mapping, Sequence

from cmk.checkengine._typedefs import HostKey, SourceType
from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.sectionparser import ParsedSectionName, Provider

from ._autochecks import AutocheckEntry
from ._utils import QualifiedDiscovery

__all__ = ["analyse_services", "find_plugins"]


def find_plugins(
    providers: Mapping[HostKey, Provider],
    preliminary_candidates: Sequence[tuple[CheckPluginName, Sequence[ParsedSectionName]]],
) -> set[CheckPluginName]:
    """Return names of check plugins that this multi_host_section may
    contain data for.

    Given this mutli_host_section, there is no point in trying to discover
    any check plugins not returned by this function.  This does not
    address the question whether or not the returned check plugins will
    discover something.

    We have to consider both the host, and the management board as source
    type. Note that the determination of the plugin names is not quite
    symmetric: For the host, we filter out all management plugins,
    for the management board we create management variants from all
    plugins that are not already designed for management boards.

    """

    def __iter(
        section_names: Iterable[ParsedSectionName], providers: Mapping[HostKey, Provider]
    ) -> Iterable[tuple[HostKey, ParsedSectionName]]:
        for host_key, provider in providers.items():
            # filter section names for sections that cannot be resolved
            for section_name in (
                section_name
                for section_name in section_names
                if provider.resolve(section_name) is not None
            ):
                yield host_key, section_name

    parsed_sections_of_interest: Sequence[ParsedSectionName] = list(
        frozenset(
            itertools.chain.from_iterable(sections for (_name, sections) in preliminary_candidates)
        )
    )
    resolved: Sequence[tuple[HostKey, ParsedSectionName]] = tuple(
        __iter(parsed_sections_of_interest, providers)
    )

    return _find_host_plugins(
        preliminary_candidates,
        frozenset(
            section_name
            for host_key, section_name in resolved
            if host_key.source_type is SourceType.HOST
        ),
    ) | _find_mgmt_plugins(
        preliminary_candidates,
        frozenset(
            section_name
            for host_key, section_name in resolved
            if host_key.source_type is SourceType.MANAGEMENT
        ),
    )


def _find_host_plugins(
    preliminary_candidates: Iterable[tuple[CheckPluginName, Iterable[ParsedSectionName]]],
    available_parsed_sections: Container[ParsedSectionName],
) -> set[CheckPluginName]:
    return {
        name
        for (name, sections) in preliminary_candidates
        # *filter out* all names of management only check plugins
        if not name.is_management_name()
        and any(section in available_parsed_sections for section in sections)
    }


def _find_mgmt_plugins(
    preliminary_candidates: Iterable[tuple[CheckPluginName, Iterable[ParsedSectionName]]],
    available_parsed_sections: Container[ParsedSectionName],
) -> set[CheckPluginName]:
    return {
        # *create* all management only names of the plugins
        name.create_management_name()
        for (name, sections) in preliminary_candidates
        if any(section in available_parsed_sections for section in sections)
    }


def analyse_services(
    *,
    existing_services: Sequence[AutocheckEntry],
    discovered_services: Iterable[AutocheckEntry],
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
    keep_vanished: bool,
) -> QualifiedDiscovery[AutocheckEntry]:
    return QualifiedDiscovery(
        preexisting=list(
            _services_to_remember(
                choose_from=existing_services,
                run_plugin_names=run_plugin_names,
                forget_existing=forget_existing,
            )
        ),
        current=list(
            itertools.chain(
                discovered_services,
                _services_to_keep(
                    choose_from=existing_services,
                    run_plugin_names=run_plugin_names,
                    keep_vanished=keep_vanished,
                ),
            )
        ),
    )


def _services_to_remember(
    *,
    choose_from: Sequence[AutocheckEntry],
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
) -> Iterable[AutocheckEntry]:
    """Compile a list of services to regard as being the last known state

    This list is used to classify services into new/old/vanished.
    Remembering is not the same as keeping!
    Always remember the services of plugins that are not being run.
    """
    return _drop_plugins_services(choose_from, run_plugin_names) if forget_existing else choose_from


def _services_to_keep(
    *,
    choose_from: Sequence[AutocheckEntry],
    run_plugin_names: Container[CheckPluginName],
    keep_vanished: bool,
) -> Iterable[AutocheckEntry]:
    """Compile a list of services to keep in addition to the discovered ones

    These services are considered to be currently present (even if they are not discovered).
    Always keep the services of plugins that are not being run.
    """
    return (
        list(choose_from)
        if keep_vanished
        else _drop_plugins_services(choose_from, run_plugin_names)
    )


def _drop_plugins_services(
    services: Sequence[AutocheckEntry],
    plugin_names: Container[CheckPluginName],
) -> Iterable[AutocheckEntry]:
    return (s for s in services if s.check_plugin_name not in plugin_names)
