#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import itertools
from collections import Counter
from collections.abc import Callable, Container, Mapping, Sequence
from pathlib import Path

import cmk.ccc.cleanup
import cmk.ccc.debug
import cmk.utils.paths
from cmk.ccc import tty
from cmk.ccc.exceptions import MKGeneralException, OnError
from cmk.ccc.hostaddress import HostName
from cmk.checkengine.discovery._autochecks import AutochecksConfig, AutochecksStore
from cmk.checkengine.discovery._autodiscovery import (
    DiscoveryReport,
    get_host_services_by_host_name,
    get_post_discovery_autocheck_services,
)
from cmk.checkengine.discovery._discover.host_labels import discover_host_labels, HostLabelPlugin
from cmk.checkengine.discovery._discover.services import (
    discover_services,
    find_plugins,
)
from cmk.checkengine.discovery._utils.filters import ServiceFilters
from cmk.checkengine.discovery.types import DiscoverySettings, QualifiedDiscovery
from cmk.checkengine.fetcher_abc import FetcherFunction
from cmk.checkengine.helper_interface import HostKey
from cmk.checkengine.parser import group_by_host, ParserFunction
from cmk.checkengine.plugins import CheckPluginName, DiscoveryPlugin, SectionName, ServiceID
from cmk.checkengine.sectionparser import (
    make_providers,
    Provider,
    SectionPlugin,
    store_piggybacked_sections,
)
from cmk.ruleset_matcher.labels import DiscoveredHostLabelsStore, HostLabel
from cmk.utils.log import console, section

__all__ = ["commandline_discovery"]


def commandline_discovery(
    host_name: HostName,
    *,
    parser: ParserFunction,
    fetcher: FetcherFunction,
    clear_ruleset_matcher_caches: Callable[[], object],
    section_plugins: Mapping[SectionName, SectionPlugin],
    section_error_handling: Callable[[SectionName, Sequence[object]], str],
    host_label_plugins: Mapping[SectionName, HostLabelPlugin],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    run_plugin_names: Container[CheckPluginName],
    autochecks_config: AutochecksConfig,
    enforced_services: Container[ServiceID],
    arg_only_new: bool,
    only_host_labels: bool = False,
    on_error: OnError,
    autochecks_dir: Path,
    discovered_host_labels_dir: Path,
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
            ((HostKey(s.hostname, s.source_type), r.ok) for s, r in host_sections if r.is_ok())
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
            autochecks_config=autochecks_config,
            enforced_services=enforced_services,
            only_new=arg_only_new,
            load_labels=arg_only_new,
            only_host_labels=only_host_labels,
            on_error=on_error,
            autochecks_dir=autochecks_dir,
            discovered_host_labels_dir=discovered_host_labels_dir,
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
    host_label_plugins: Mapping[SectionName, HostLabelPlugin],
    clear_ruleset_matcher_caches: Callable[[], object],
    providers: Mapping[HostKey, Provider],
    plugins: Mapping[CheckPluginName, DiscoveryPlugin],
    run_plugin_names: Container[CheckPluginName],
    autochecks_config: AutochecksConfig,
    enforced_services: Container[ServiceID],
    only_new: bool,
    load_labels: bool,
    only_host_labels: bool,
    on_error: OnError,
    autochecks_dir: Path,
    discovered_host_labels_dir: Path,
) -> None:
    section.section_step("Analyse discovered host labels")

    host_labels = QualifiedDiscovery[HostLabel](
        preexisting=(
            DiscoveredHostLabelsStore(real_host_name, discovered_host_labels_dir).load()
            if load_labels
            else ()
        ),
        current=discover_host_labels(
            real_host_name, host_label_plugins, providers=providers, on_error=on_error
        ),
    )

    DiscoveredHostLabelsStore(real_host_name, discovered_host_labels_dir).save(host_labels.present)
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

    autocheck_store = AutochecksStore(real_host_name, autochecks_dir)
    candidates = find_plugins(
        providers,
        [
            (plugin_name, plugin.sections)
            for plugin_name, plugin in plugins.items()
            if plugin_name in run_plugin_names
        ],
    )

    section.section_step("Executing discovery plugins (%d)" % len(candidates))
    console.debug(f"  Trying discovery with: {', '.join(str(n) for n in candidates)}")
    # The host name must be set for the host_name() calls commonly used to determine the
    # host name for get_host_values{_merged,} calls in the legacy checks.
    try:
        discovered_services = discover_services(
            real_host_name,
            candidates,
            providers=providers,
            plugins=plugins,
            on_error=on_error,
        )
    except KeyboardInterrupt:
        raise MKGeneralException("Interrupted by Ctrl-C.")

    # Route through the same transition-table layer the other discovery entrypoints use, so
    # disabled services, disabled checks and enforced-service shadowing are applied consistently
    # (werk 22108).  '-I' (only_new) only adds new services and keeps everything else, '-II'
    # additionally drops vanished services and adopts changed parameters/labels.
    services_by_transition = get_host_services_by_host_name(
        real_host_name,
        existing_services={real_host_name: autocheck_store.read()},
        discovered_services={real_host_name: discovered_services},
        is_cluster=False,
        cluster_nodes=(),
        autochecks_config=autochecks_config,
        enforced_services=enforced_services,
        run_plugin_names=run_plugin_names,
    )[real_host_name]

    discovery_report = DiscoveryReport()
    post_discovery_services = get_post_discovery_autocheck_services(
        real_host_name,
        services_by_transition,
        ServiceFilters.accept_all(),
        discovery_report,
        autochecks_config.service_description,
        DiscoverySettings(
            update_host_labels=False,
            add_new_services=True,
            remove_vanished_services=not only_new,
            update_changed_service_labels=not only_new,
            update_changed_service_parameters=not only_new,
        ),
        keep_clustered_vanished_services=True,
    )
    autocheck_store.write([s.service.newer for s in post_discovery_services.values()])

    new_per_plugin = Counter(
        entry.service.newer.check_plugin_name for entry in services_by_transition.get("new", [])
    )
    for name, count in sorted(new_per_plugin.items()):
        console.verbose(f"{tty.green}{tty.bold}{count:>3}{tty.normal} {name}")

    # '-I' reports how many services were newly added, while '-II' rediscovers from scratch and
    # reports the total number of services now present.
    if only_new:
        count = discovery_report.services.new if discovery_report.services.new else "no new"
    else:
        count = len(post_discovery_services) if post_discovery_services else "no"
    section.section_success(f"Found {count} services")

    for result in itertools.chain.from_iterable(
        resolver.parsing_errors() for resolver in providers.values()
    ):
        for line in result.details:
            console.warning(tty.format_warning(f"{line}"))
