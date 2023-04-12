#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import itertools
from collections import Counter
from collections.abc import Container, Mapping

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, OnError
from cmk.utils.labels import HostLabel
from cmk.utils.log import console, section
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher
from cmk.utils.type_defs import CheckPluginName, HostName, SectionName

from cmk.checkers import (
    FetcherFunction,
    HostKey,
    ParserFunction,
    PHostLabelDiscoveryPlugin,
    PSectionPlugin,
)
from cmk.checkers.discovery import AutochecksStore

import cmk.base.core
from cmk.base.agent_based.data_provider import (
    filter_out_errors,
    make_providers,
    Provider,
    store_piggybacked_sections,
)
from cmk.base.agent_based.utils import check_parsing_errors
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.config import ConfigCache

from ._discovered_services import analyse_discovered_services
from ._host_labels import (
    analyse_host_labels,
    discover_cluster_labels,
    discover_host_labels,
    do_load_labels,
)
from .utils import QualifiedDiscovery

__all__ = ["commandline_discovery"]


def commandline_discovery(
    arg_hostnames: set[HostName],
    *,
    parser: ParserFunction,
    fetcher: FetcherFunction,
    config_cache: ConfigCache,
    section_plugins: Mapping[SectionName, PSectionPlugin],
    host_label_plugins: Mapping[SectionName, PHostLabelDiscoveryPlugin],
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
    run_plugin_names: Container[CheckPluginName],
    arg_only_new: bool,
    only_host_labels: bool = False,
    on_error: OnError,
) -> None:
    """Implementing cmk -I and cmk -II

    This is directly called from the main option parsing code.
    The list of hostnames is already prepared by the main code.
    If it is empty then we use all hosts and switch to using cache files.
    """
    host_names = _preprocess_hostnames(arg_hostnames, config_cache, only_host_labels)

    # Now loop through all hosts
    for host_name in sorted(host_names):
        section.section_begin(host_name)
        try:
            fetched = fetcher(host_name, ip_address=None)
            host_sections = filter_out_errors(parser((f[0], f[1]) for f in fetched))
            store_piggybacked_sections(host_sections)
            providers = make_providers(host_sections, section_plugins)
            _commandline_discovery_on_host(
                host_name=host_name,
                host_label_plugins=host_label_plugins,
                config_cache=config_cache,
                providers=providers,
                check_plugins=check_plugins,
                run_plugin_names=run_plugin_names,
                only_new=arg_only_new,
                load_labels=arg_only_new,
                only_host_labels=only_host_labels,
                on_error=on_error,
            )

        except Exception as e:
            if cmk.utils.debug.enabled():
                raise
            section.section_error("%s" % e)
        finally:
            cmk.utils.cleanup.cleanup_globals()


def _preprocess_hostnames(
    arg_host_names: set[HostName],
    config_cache: ConfigCache,
    only_host_labels: bool,
) -> set[HostName]:
    """Default to all hosts and expand cluster names to their nodes"""
    if not arg_host_names:
        console.verbose(
            "Discovering %shost labels on all hosts\n"
            % ("services and " if not only_host_labels else "")
        )
        return set(config_cache.all_active_realhosts())

    console.verbose(
        "Discovering %shost labels on: %s\n"
        % ("services and " if not only_host_labels else "", ", ".join(sorted(arg_host_names)))
    )

    host_names: set[HostName] = set()
    # For clusters add their nodes to the list. Clusters itself
    # cannot be discovered but the user is allowed to specify
    # them and we do discovery on the nodes instead.
    for host_name in arg_host_names:
        if not config_cache.is_cluster(host_name):
            host_names.add(host_name)
            continue

        nodes = config_cache.nodes_of(host_name)
        if nodes is None:
            raise MKGeneralException("Invalid cluster configuration")
        host_names.update(nodes)

    return host_names


def _analyse_node_labels(
    host_name: HostName,
    host_label_plugins: Mapping[SectionName, PHostLabelDiscoveryPlugin],
    *,
    config_cache: ConfigCache,
    providers: Mapping[HostKey, Provider],
    ruleset_matcher: RulesetMatcher,
    load_labels: bool,
    save_labels: bool,
    on_error: OnError,
) -> QualifiedDiscovery[HostLabel]:
    """Discovery and analysis for hosts and clusters."""
    if config_cache.is_cluster(host_name):
        nodes = config_cache.nodes_of(host_name)
        if not nodes:
            return QualifiedDiscovery.empty()

        discovered_host_labels = discover_cluster_labels(
            nodes,
            host_label_plugins,
            providers=providers,
            load_labels=load_labels,
            save_labels=save_labels,
            on_error=on_error,
        )
    else:
        discovered_host_labels = discover_host_labels(
            host_name, host_label_plugins, providers=providers, on_error=on_error
        )
    return analyse_host_labels(
        host_name,
        discovered_host_labels=discovered_host_labels,
        existing_host_labels=do_load_labels(host_name) if load_labels else (),
        ruleset_matcher=ruleset_matcher,
        save_labels=save_labels,
    )


def _commandline_discovery_on_host(
    *,
    host_name: HostName,
    host_label_plugins: Mapping[SectionName, PHostLabelDiscoveryPlugin],
    config_cache: ConfigCache,
    providers: Mapping[HostKey, Provider],
    check_plugins: Mapping[CheckPluginName, CheckPlugin],
    run_plugin_names: Container[CheckPluginName],
    only_new: bool,
    load_labels: bool,
    only_host_labels: bool,
    on_error: OnError,
) -> None:

    section.section_step("Analyse discovered host labels")

    host_labels = _analyse_node_labels(
        host_name,
        host_label_plugins,
        config_cache=config_cache,
        providers=providers,
        ruleset_matcher=config_cache.ruleset_matcher,
        load_labels=load_labels,
        save_labels=True,
        on_error=on_error,
    )

    count = len(host_labels.new) if host_labels.new else ("no new" if only_new else "no")
    section.section_success(f"Found {count} host labels")

    if only_host_labels:
        return

    section.section_step("Analyse discovered services")

    service_result = analyse_discovered_services(
        config_cache,
        host_name,
        providers=providers,
        check_plugins=check_plugins,
        run_plugin_names=run_plugin_names,
        forget_existing=not only_new,
        keep_vanished=only_new,
        on_error=on_error,
    )

    # TODO (mo): for the labels the corresponding code is in _host_labels.
    # We should put the persisting in one place.
    AutochecksStore(host_name).write(service_result.present)

    new_per_plugin = Counter(s.check_plugin_name for s in service_result.new)
    for name, count in sorted(new_per_plugin.items()):
        console.verbose("%s%3d%s %s\n" % (tty.green + tty.bold, count, tty.normal, name))

    count = len(service_result.new) if service_result.new else ("no new" if only_new else "no")
    section.section_success(f"Found {count} services")

    for result in check_parsing_errors(
        itertools.chain.from_iterable(resolver.parsing_errors for resolver in providers.values())
    ):
        for line in result.details:
            console.warning(line)
