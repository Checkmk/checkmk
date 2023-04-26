#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import itertools
from collections import Counter
from collections.abc import Container, Iterable, Mapping

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
import cmk.utils.tty as tty
from cmk.utils.exceptions import MKGeneralException, OnError
from cmk.utils.log import console, section
from cmk.utils.type_defs import HostName, SectionName

from cmk.checkers import (
    DiscoveryPlugin,
    FetcherFunction,
    HostKey,
    HostLabelDiscoveryPlugin,
    ParserFunction,
    SectionPlugin,
)
from cmk.checkers.checking import CheckPluginName
from cmk.checkers.discovery import AutochecksStore
from cmk.checkers.sectionparser import (
    filter_out_errors,
    make_providers,
    Provider,
    store_piggybacked_sections,
)
from cmk.checkers.sectionparserutils import check_parsing_errors

import cmk.base.core
from cmk.base.config import ConfigCache

from ._discovered_services import analyse_discovered_services
from ._host_labels import analyse_host_labels, discover_host_labels, do_load_labels

__all__ = ["commandline_discovery"]


def commandline_discovery(
    arg_hostnames: set[HostName],
    *,
    parser: ParserFunction,
    fetcher: FetcherFunction,
    config_cache: ConfigCache,
    section_plugins: Mapping[SectionName, SectionPlugin],
    host_label_plugins: Mapping[SectionName, HostLabelDiscoveryPlugin],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
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
    non_cluster_host_names = _preprocess_hostnames(arg_hostnames, config_cache, only_host_labels)

    # Now loop through all hosts
    for host_name in sorted(non_cluster_host_names):
        section.section_begin(host_name)
        try:
            fetched = fetcher(host_name, ip_address=None)
            host_sections = filter_out_errors(parser((f[0], f[1]) for f in fetched))
            store_piggybacked_sections(host_sections)
            providers = make_providers(host_sections, section_plugins)
            _commandline_discovery_on_host(
                real_host_name=host_name,
                host_label_plugins=host_label_plugins,
                config_cache=config_cache,
                providers=providers,
                plugins=plugins,
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

    # For clusters add their nodes to the list.
    # Clusters themselves cannot be discovered.
    # The user is allowed to specify them and we do discovery on the nodes instead.
    def _resolve_nodes(cluster_name: HostName) -> Iterable[HostName]:
        if (nodes := config_cache.nodes_of(cluster_name)) is None:
            raise MKGeneralException(f"Invalid cluster configuration: {cluster_name}")
        return nodes

    node_names = {
        node_name
        for host_name in arg_host_names
        for node_name in (
            _resolve_nodes(host_name) if config_cache.is_cluster(host_name) else (host_name,)
        )
    }

    console.verbose(
        "Discovering %shost labels on: %s\n"
        % ("services and " if not only_host_labels else "", ", ".join(sorted(node_names)))
    )

    return node_names


def _commandline_discovery_on_host(
    *,
    real_host_name: HostName,
    host_label_plugins: Mapping[SectionName, HostLabelDiscoveryPlugin],
    config_cache: ConfigCache,
    providers: Mapping[HostKey, Provider],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    run_plugin_names: Container[CheckPluginName],
    only_new: bool,
    load_labels: bool,
    only_host_labels: bool,
    on_error: OnError,
) -> None:
    section.section_step("Analyse discovered host labels")

    host_labels = analyse_host_labels(
        real_host_name,
        discovered_host_labels=discover_host_labels(
            real_host_name, host_label_plugins, providers=providers, on_error=on_error
        ),
        existing_host_labels=do_load_labels(real_host_name) if load_labels else (),
        ruleset_matcher=config_cache.ruleset_matcher,
        save_labels=True,
    )

    count = len(host_labels.new) if host_labels.new else ("no new" if only_new else "no")
    section.section_success(f"Found {count} host labels")

    if only_host_labels:
        return

    section.section_step("Analyse discovered services")

    service_result = analyse_discovered_services(
        config_cache,
        real_host_name,
        providers=providers,
        plugins=plugins,
        run_plugin_names=run_plugin_names,
        forget_existing=not only_new,
        keep_vanished=only_new,
        on_error=on_error,
    )

    # TODO (mo): for the labels the corresponding code is in _host_labels.
    # We should put the persisting in one place.
    AutochecksStore(real_host_name).write(service_result.present)

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
