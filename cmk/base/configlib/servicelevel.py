#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass

from cmk.base.configlib.loaded_config import BaseConfig
from cmk.ccc.hostaddress import HostName
from cmk.ruleset_matcher.labels import LabelManager, Labels
from cmk.ruleset_matcher.matcher import RulesetMatcher
from cmk.utils.servicename import ServiceName


@dataclass(frozen=True)
class ServiceLevelConfig:
    """The (event console) service level configuration per host/service."""

    of_host: Callable[[HostName], int | None]
    of_service: Callable[[HostName, ServiceName, Labels], int | None]
    effective: Callable[[HostName, ServiceName, Labels], int]


def make_service_level_config(
    loaded_config: BaseConfig,
    matcher: RulesetMatcher,
    label_manager: LabelManager,
) -> ServiceLevelConfig:
    """Create the callbacks that resolve the service level per host/service."""

    def of_host(host_name: HostName) -> int | None:
        entries = matcher.get_host_values_all(
            host_name,
            loaded_config.extra_host_conf.get("_ec_sl", []),
            label_manager.labels_of_host,
        )
        return entries[0] if entries else None

    def of_service(
        host_name: HostName, service_name: ServiceName, service_labels: Labels
    ) -> int | None:
        out = matcher.get_service_values_all(
            host_name,
            service_name,
            service_labels,
            loaded_config.extra_service_conf.get("_ec_sl", []),
            label_manager.labels_of_host,
        )
        return _parse(out[0], int) if out else None

    def effective(host_name: HostName, service_name: ServiceName, service_labels: Labels) -> int:
        """Get the service level that applies to the current service."""
        service_level = of_service(host_name, service_name, service_labels)
        if service_level is not None:
            return service_level

        return of_host(host_name) or 0

    return ServiceLevelConfig(of_host=of_host, of_service=of_service, effective=effective)


def _parse[T](raw: object, type_: Callable[..., T], /) -> T:
    return type_(raw)
