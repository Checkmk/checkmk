#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Literal

HostKind = Literal[
    "pods", "namespaces", "nodes", "deployments", "daemonsets", "statefulsets", "cronjobs"
]
HOST_KINDS: tuple[HostKind, ...] = (
    "pods",
    "namespaces",
    "nodes",
    "deployments",
    "daemonsets",
    "statefulsets",
    "cronjobs",
)


@dataclass(frozen=True, kw_only=True)
class MonitoringSettings:
    """Monitoring choices shared by push and pull deployments.

    Names and regex patterns are validated by the caller's forms. Namespace selection and
    annotation import each use a single choice, preventing conflicting Helm options.
    """

    cluster_name: str
    host_name: str
    host_kinds: frozenset[HostKind]
    namespaces: tuple[Literal["include", "exclude"], tuple[str, ...]] = ("include", ())
    annotations: Literal["none", "all"] | tuple[Literal["pattern"], str] = "none"
    excluded_node_roles: tuple[str, ...] = ("control-plane", "infra")
    include_pvcs: bool = False
    include_cronjob_pods: bool = False


def monitoring_values(settings: MonitoringSettings) -> dict[str, object]:
    """Build common Helm values; credentials and transport are supplied separately.

    Emit explicit false values and empty lists as well: Helm must not substitute chart
    defaults for resources or filters the user has disabled.
    """
    namespace_mode, patterns = settings.namespaces
    emit_all: dict[str, bool] = {kind: kind in settings.host_kinds for kind in HOST_KINDS}
    emit_all["pvcs"] = settings.include_pvcs
    return {
        "clusterName": settings.cluster_name,
        "clusterHostName": settings.host_name,
        "emitAll": emit_all,
        "podHosts": {"includeCronJobPods": settings.include_cronjob_pods},
        "namespaceFilter": {
            "includePatterns": list(patterns) if namespace_mode == "include" else [],
            "excludePatterns": list(patterns) if namespace_mode == "exclude" else [],
        },
        "hostLabels": {
            "importAllAnnotations": settings.annotations == "all",
            "importKeyPattern": (
                settings.annotations[1] if isinstance(settings.annotations, tuple) else ""
            ),
        },
        "clusterAggregation": {"excludedNodeRolePatterns": list(settings.excluded_node_roles)},
    }
