#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import itertools
from collections import Counter
from collections.abc import Callable, Container, Mapping, Sequence

import cmk.ccc.cleanup
import cmk.ccc.debug
from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException, OnError
from cmk.ccc.hostaddress import HostName

from cmk.utils.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.log import console, section
from cmk.utils.sectionname import SectionMap, SectionName

from cmk.checkengine.fetcher import FetcherFunction, HostKey
from cmk.checkengine.parser import group_by_host, ParserFunction
from cmk.checkengine.plugins import CheckPluginName, DiscoveryPlugin
from cmk.checkengine.sectionparser import (
    make_providers,
    Provider,
    SectionPlugin,
    store_piggybacked_sections,
)
from cmk.checkengine.sectionparserutils import check_parsing_errors

from ._autochecks import AutochecksStore
from ._host_labels import discover_host_labels, HostLabelPlugin
from ._services import analyse_services, discover_services, find_plugins
from ._utils import QualifiedDiscovery

__all__ = ["commandline_discovery"]


def commandline_discovery(
    host_name: HostName,
    *,
    parser: ParserFunction,
    fetcher: FetcherFunction,
    clear_ruleset_matcher_caches: Callable[[], object],
    section_plugins: SectionMap[SectionPlugin],
    section_error_handling: Callable[[SectionName, Sequence[object]], str],
    host_label_plugins: SectionMap[HostLabelPlugin],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    run_plugin_names: Container[CheckPluginName],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    arg_only_new: bool,
    only_host_labels: bool = False,
    on_error: OnError,
) -> None:
    """Implementing cmk -I and cmk -II

    This is directly called from the main option parsing code.
    The list of hostnames is already prepared by the main code.
    If it is empty then we use all hosts and switch to using cache files.
    """
    section.section_begin(host_name)
    try:
        fetched = fetcher(host_name, ip_address=None)
        host_sections = parser((f[0], f[1]) for f in fetched)
        host_sections_by_host = group_by_host(
            ((HostKey(s.hostname, s.source_type), r.ok) for s, r in host_sections if r.is_ok()),
            console.debug,
        )
        store_piggybacked_sections(host_sections_by_host, cmk.utils.paths.omd_root)
        providers = make_providers(
            host_sections_by_host,
            section_plugins,
            error_handling=section_error_handling,
        )
        _commandline_discovery_on_host(
            real_host_name=host_name,
            host_label_plugins=host_label_plugins,
            clear_ruleset_matcher_caches=clear_ruleset_matcher_caches,
            providers=providers,
            plugins=plugins,
            run_plugin_names=run_plugin_names,
            ignore_plugin=ignore_plugin,
            only_new=arg_only_new,
            load_labels=arg_only_new,
            only_host_labels=only_host_labels,
            on_error=on_error,
        )

    except Exception as e:
        if cmk.ccc.debug.enabled():
            raise
        section.section_error("%s" % e)
    finally:
        cmk.ccc.cleanup.cleanup_globals()


def _commandline_discovery_on_host(
    *,
    real_host_name: HostName,
    host_label_plugins: SectionMap[HostLabelPlugin],
    clear_ruleset_matcher_caches: Callable[[], object],
    providers: Mapping[HostKey, Provider],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    run_plugin_names: Container[CheckPluginName],
    ignore_plugin: Callable[[HostName, CheckPluginName], bool],
    only_new: bool,
    load_labels: bool,
    only_host_labels: bool,
    on_error: OnError,
) -> None:
    section.section_step("Analyse discovered host labels")

    host_labels = QualifiedDiscovery[HostLabel](
        preexisting=DiscoveredHostLabelsStore(real_host_name).load() if load_labels else (),
        current=discover_host_labels(
            real_host_name, host_label_plugins, providers=providers, on_error=on_error
        ),
    )

    DiscoveredHostLabelsStore(real_host_name).save(host_labels.present)
    if host_labels.new or host_labels.vanished:  # add 'changed' once it exists.
        # Rulesets for service discovery can match based on the hosts labels.
        # The ruleset matcher does not properly handle the case where the host labels
        # are changed. So we need to clear the caches of the ruleset matcher.
        # This is not something we should have to deal with here, but currently
        # the ruleset matcher can't be easily changed.
        clear_ruleset_matcher_caches()

    count = len(host_labels.new) if host_labels.new else ("no new" if only_new else "no")
    section.section_success(f"Found {count} host labels")

    if only_host_labels:
        return

    section.section_step("Analyse discovered services")

    autocheck_store = AutochecksStore(real_host_name)
    candidates = find_plugins(
        providers,
        [
            (plugin_name, plugin.sections)
            for plugin_name, plugin in plugins.items()
            if plugin_name in run_plugin_names
        ],
    )
    skip = {plugin_name for plugin_name in candidates if ignore_plugin(real_host_name, plugin_name)}

    section.section_step("Executing discovery plugins (%d)" % len(candidates))
    console.debug(f"  Trying discovery with: {', '.join(str(n) for n in candidates)}")
    # The host name must be set for the host_name() calls commonly used to determine the
    # host name for get_host_values{_merged,} calls in the legacy checks.

    for plugin_name in skip:
        console.debug(f"  Skip ignored check plug-in name {plugin_name!r}")

    try:
        discovered_services = discover_services(
            real_host_name,
            candidates - skip,
            providers=providers,
            plugins=plugins,
            on_error=on_error,
        )
    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")

    service_result = analyse_services(
        existing_services=autocheck_store.read(),
        discovered_services=discovered_services,
        run_plugin_names=run_plugin_names,
        forget_existing=not only_new,
        keep_vanished=only_new,
    )
    autocheck_store.write(service_result.present)

    new_per_plugin = Counter(s.check_plugin_name for s in service_result.new)
    for name, count in sorted(new_per_plugin.items()):
        console.verbose(f"{tty.green}{tty.bold}{count:>3}{tty.normal} {name}")

    count = len(service_result.new) if service_result.new else ("no new" if only_new else "no")
    section.section_success(f"Found {count} services")

    for result in check_parsing_errors(
        itertools.chain.from_iterable(resolver.parsing_errors for resolver in providers.values())
    ):
        for line in result.details:
            console.warning(tty.format_warning(f"{line}"))
