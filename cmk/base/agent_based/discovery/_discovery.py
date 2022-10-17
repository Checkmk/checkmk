#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from contextlib import suppress
from pathlib import Path
from typing import Callable, Container, Counter, Iterable, Optional, Sequence, Tuple

import cmk.utils.cleanup
import cmk.utils.debug
import cmk.utils.paths
from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import OnError
from cmk.utils.type_defs import CheckPluginName, HostName

import cmk.core_helpers.cache
from cmk.core_helpers.protocol import FetcherMessage
from cmk.core_helpers.type_defs import HostMeta, NO_SELECTION

import cmk.base.check_utils
import cmk.base.config as config
import cmk.base.core
import cmk.base.crash_reporting
from cmk.base.agent_based.data_provider import (
    make_broker,
    parse_messages,
    store_piggybacked_sections,
)
from cmk.base.agent_based.utils import check_parsing_errors, summarize_host_sections
from cmk.base.config import DiscoveryCheckParameters, HostConfig
from cmk.base.discovered_labels import HostLabel

from ._filters import ServiceFilters as _ServiceFilters
from ._host_labels import analyse_host_labels
from .autodiscovery import get_host_services, ServicesByTransition
from .utils import DiscoveryMode, QualifiedDiscovery

__all__ = ["execute_check_discovery"]


def execute_check_discovery(
    host_name: HostName,
    *,
    fetched: Sequence[Tuple[HostMeta, FetcherMessage]],
) -> ActiveCheckResult:
    # Note: '--cache' is set in core_cmc, nagios template or even on CL and means:
    # 1. use caches as default:
    #    - Set FileCacheGlobals.maybe = True (set max_cachefile_age, else 0)
    #    - Set FileCacheGlobals.use_outdated = True
    # 2. Then these settings are used to read cache file or not

    config_cache = config.get_config_cache()
    host_config = config_cache.get_host_config(host_name)
    params = host_config.discovery_check_parameters()

    discovery_mode = DiscoveryMode(params.rediscovery.get("mode"))

    host_sections, source_results = parse_messages(
        fetched,
        selected_sections=NO_SELECTION,
        logger=logging.getLogger("cmk.base.discovery"),
    )
    store_piggybacked_sections(host_sections)
    parsed_sections_broker = make_broker(host_sections)

    host_labels = analyse_host_labels(
        host_config=host_config,
        parsed_sections_broker=parsed_sections_broker,
        load_labels=True,
        save_labels=False,
        on_error=OnError.RAISE,
    )
    services = get_host_services(
        host_config,
        parsed_sections_broker,
        on_error=OnError.RAISE,
    )

    services_result, services_need_rediscovery = _check_service_lists(
        host_name=host_name,
        services_by_transition=services,
        params=params,
        service_filters=_ServiceFilters.from_settings(params.rediscovery),
        discovery_mode=discovery_mode,
    )

    host_labels_result, host_labels_need_rediscovery = _check_host_labels(
        host_labels,
        params.severity_new_host_labels,
        discovery_mode,
    )

    parsing_errors_results = check_parsing_errors(parsed_sections_broker.parsing_errors())

    return ActiveCheckResult.from_subresults(
        *services_result,
        host_labels_result,
        *summarize_host_sections(
            source_results=source_results,
            exit_spec_cb=host_config.exit_code_spec,
            time_settings_cb=lambda hostname: config.get_config_cache().get_piggybacked_hosts_time_settings(
                piggybacked_hostname=hostname,
            ),
            is_piggyback=host_config.is_piggyback_host,
        ),
        *parsing_errors_results,
        _schedule_rediscovery(
            host_config=host_config,
            need_rediscovery=(services_need_rediscovery or host_labels_need_rediscovery)
            and all(r.state == 0 for r in parsing_errors_results),
        ),
    )


def _check_service_lists(
    *,
    host_name: HostName,
    services_by_transition: ServicesByTransition,
    params: DiscoveryCheckParameters,
    service_filters: _ServiceFilters,
    discovery_mode: DiscoveryMode,
) -> Tuple[Sequence[ActiveCheckResult], bool]:

    subresults = []
    need_rediscovery = False

    for transition, t_services, title, severity, service_filter in [
        (
            "new",
            services_by_transition.get("new", []),
            "unmonitored",
            params.severity_new_services,
            service_filters.new,
        ),
        (
            "vanished",
            services_by_transition.get("vanished", []),
            "vanished",
            params.severity_vanished_services,
            service_filters.vanished,
        ),
    ]:

        affected_check_plugin_names: Counter[CheckPluginName] = Counter()
        unfiltered = False

        for (discovered_service, _found_on_nodes) in t_services:
            affected_check_plugin_names[discovered_service.check_plugin_name] += 1

            if not unfiltered and service_filter(
                config.service_description(host_name, *discovered_service.id())
            ):
                unfiltered = True

            subresults.append(
                ActiveCheckResult(
                    0,
                    "",
                    [
                        "%s: %s: %s"
                        % (
                            title.capitalize(),
                            discovered_service.check_plugin_name,
                            config.service_description(host_name, *discovered_service.id()),
                        )
                    ],
                )
            )

        if affected_check_plugin_names:
            info = ", ".join(["%s: %d" % e for e in affected_check_plugin_names.items()])
            count = sum(affected_check_plugin_names.values())
            subresults.append(
                ActiveCheckResult(severity, f"{title.capitalize()} services: {count} ({info})")
            )

            if unfiltered and (
                (
                    transition == "new"
                    and discovery_mode
                    in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH)
                )
                or (
                    transition == "vanished"
                    and discovery_mode
                    in (DiscoveryMode.REMOVE, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH)
                )
            ):
                need_rediscovery = True
        else:
            subresults.append(ActiveCheckResult(0, "", [f"No {title} services found"]))

    for (discovered_service, _found_on_nodes) in services_by_transition.get("ignored", []):
        subresults.append(
            ActiveCheckResult(
                0,
                "",
                [
                    "Ignored: %s: %s"
                    % (
                        discovered_service.check_plugin_name,
                        config.service_description(host_name, *discovered_service.id()),
                    )
                ],
            )
        )

    if not any(s.summary for s in subresults):
        subresults.insert(0, ActiveCheckResult(0, "All services up to date"))
    return subresults, need_rediscovery


def _check_host_labels(
    host_labels: QualifiedDiscovery[HostLabel],
    severity_new_host_label: int,
    discovery_mode: DiscoveryMode,
) -> Tuple[ActiveCheckResult, bool]:
    return (
        (
            ActiveCheckResult(severity_new_host_label, f"New host labels: {len(host_labels.new)}"),
            discovery_mode in (DiscoveryMode.NEW, DiscoveryMode.FIXALL, DiscoveryMode.REFRESH),
        )
        if host_labels.new
        else (
            ActiveCheckResult(0, "All host labels up to date"),
            False,
        )
    )


def _schedule_rediscovery(
    *,
    host_config: HostConfig,
    need_rediscovery: bool,
) -> ActiveCheckResult:
    if not need_rediscovery:
        return ActiveCheckResult()

    autodiscovery_queue = AutodiscoveryQueue()
    if host_config.is_cluster and host_config.nodes:
        for nodename in host_config.nodes:
            autodiscovery_queue.add(nodename)
    else:
        autodiscovery_queue.add(host_config.hostname)

    return ActiveCheckResult(0, "rediscovery scheduled")


class AutodiscoveryQueue:
    @staticmethod
    def _host_name(file_path: Path) -> HostName:
        return HostName(file_path.name)

    def _file_path(self, host_name: HostName) -> Path:
        return self._dir / str(host_name)

    def __init__(self) -> None:
        self._dir = Path(cmk.utils.paths.var_dir, "autodiscovery")

    def _ls(self) -> Sequence[Path]:
        try:
            # we must consume the .iterdir generator to make sure
            # the FileNotFoundError gets raised *here*.
            return list(self._dir.iterdir())
        except FileNotFoundError:
            return []

    def __len__(self) -> int:
        return len(self._ls())

    def oldest(self) -> Optional[float]:
        return min((f.stat().st_mtime for f in self._ls()), default=None)

    def queued_hosts(self) -> Iterable[HostName]:
        return (self._host_name(f) for f in self._ls())

    def add(self, host_name: HostName) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file_path(host_name).touch()

    def remove(self, host_name: HostName) -> None:
        with suppress(FileNotFoundError):
            self._file_path(host_name).unlink()

    def cleanup(self, *, valid_hosts: Container[HostName], logger: Callable[[str], None]) -> None:
        for host_name in (hn for f in self._ls() if (hn := self._host_name(f)) not in valid_hosts):
            logger(f"  Removing mark '{host_name}' (host not configured)\n")
            self.remove(host_name)
