#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from typing import override

from cmk.gui.i18n import _
from cmk.gui.openapi.framework import VersionedEndpointRegistry
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamilyRegistry
from cmk.gui.valuespec import (
    Integer,
    MonitoredHostname,
    MonitoredServiceDescription,
    TextInput,
    ValueSpec,
)
from cmk.gui.visuals.filter import components
from cmk.gui.visuals.filter.components import DynamicDropdown, FilterComponent
from cmk.web.utils.autocompleter_config import AutocompleterConfig, ContextAutocompleterConfig

from ._base import VisualInfo
from ._openapi import register_endpoints
from ._registry import VisualInfoRegistry


def register(
    visual_info_registry: VisualInfoRegistry,
    endpoint_family_registry: EndpointFamilyRegistry,
    versioned_endpoint_registry: VersionedEndpointRegistry,
) -> None:
    visual_info_registry.register(VisualInfoHost)
    visual_info_registry.register(VisualInfoService)
    visual_info_registry.register(VisualInfoHostgroup)
    visual_info_registry.register(VisualInfoServicegroup)
    visual_info_registry.register(VisualInfoLog)
    visual_info_registry.register(VisualInfoComment)
    visual_info_registry.register(VisualInfoDowntime)
    visual_info_registry.register(VisualInfoContact)
    visual_info_registry.register(VisualInfoCommand)
    visual_info_registry.register(VisualInfoBIAggregation)
    visual_info_registry.register(VisualInfoBIAggregationGroup)
    visual_info_registry.register(VisualInfoDiscovery)
    visual_info_registry.register(VisualInfoEvent)
    visual_info_registry.register(VisualInfoEventHistory)
    visual_info_registry.register(VisualInfoCrash)
    visual_info_registry.register(VisualInfoKubernetesCluser)
    visual_info_registry.register(VisualInfoKubernetesNamespace)
    visual_info_registry.register(VisualInfoKubernetesDaemonset)
    visual_info_registry.register(VisualInfoKubernetesDeployment)
    visual_info_registry.register(VisualInfoKubernetesStatefulset)

    register_endpoints(
        endpoint_family_registry,
        versioned_endpoint_registry,
    )


class VisualInfoHost(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "host"

    @property
    @override
    def title(self) -> str:
        return _("Host")

    @property
    @override
    def title_plural(self) -> str:
        return _("Hosts")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("host", MonitoredHostname(title=_("Host name"), strict="True"))]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [
            DynamicDropdown(
                id="host",
                autocompleter=AutocompleterConfig(ident="monitored_hostname", strict=True),
            )
        ]

    @property
    @override
    def multiple_site_filters(self) -> list[str]:
        return ["hostgroup"]

    @property
    @override
    def sort_index(self) -> int:
        return 10


class VisualInfoService(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "service"

    @property
    @override
    def title(self) -> str:
        return _("Service")

    @property
    @override
    def title_plural(self) -> str:
        return _("Services")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "service",
                MonitoredServiceDescription(
                    # TODO: replace MonitoredServiceDescription with AjaxDropdownChoice
                    title=_("Service name"),
                    autocompleter=ContextAutocompleterConfig(
                        ident=MonitoredServiceDescription.ident,
                        strict=True,
                        show_independent_of_context=True,
                    ),
                ),
            )
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [
            DynamicDropdown(
                id="service",
                autocompleter=ContextAutocompleterConfig(
                    ident=MonitoredServiceDescription.ident,
                    strict=True,
                    show_independent_of_context=True,
                    literal_search=True,
                ),
            )
        ]

    @property
    @override
    def multiple_site_filters(self) -> list[str]:
        return ["servicegroup"]

    @property
    @override
    def sort_index(self) -> int:
        return 10


class VisualInfoHostgroup(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "hostgroup"

    @property
    @override
    def title(self) -> str:
        return _("Host group")

    @property
    @override
    def title_plural(self) -> str:
        return _("Host groups")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "hostgroup",
                TextInput(
                    title=_("Host group name"),
                ),
            )
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="hostgroup", label=_("Host group name"))]

    @property
    @override
    def single_site(self) -> bool:
        return False

    @property
    @override
    def sort_index(self) -> int:
        return 10


class VisualInfoServicegroup(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "servicegroup"

    @property
    @override
    def title(self) -> str:
        return _("Service group")

    @property
    @override
    def title_plural(self) -> str:
        return _("Service groups")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "servicegroup",
                TextInput(
                    title=_("Service group name"),
                ),
            ),
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="servicegroup", label=_("Service group name"))]

    @property
    @override
    def single_site(self) -> bool:
        return False

    @property
    @override
    def sort_index(self) -> int:
        return 10


class VisualInfoLog(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "log"

    @property
    @override
    def title(self) -> str:
        return _("Log entry")

    @property
    @override
    def title_plural(self) -> str:
        return _("Log entries")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return []

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return []


class VisualInfoComment(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "comment"

    @property
    @override
    def title(self) -> str:
        return _("Comment")

    @property
    @override
    def title_plural(self) -> str:
        return _("Comments")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "comment_id",
                Integer(
                    title=_("Comment ID"),
                ),
            ),
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="comment_id", label=_("Comment ID"))]


class VisualInfoDowntime(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "downtime"

    @property
    @override
    def title(self) -> str:
        return _("Downtime")

    @property
    @override
    def title_plural(self) -> str:
        return _("Downtimes")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "downtime_id",
                Integer(
                    title=_("Downtime ID"),
                ),
            ),
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="downtime_id", label=_("Downtime ID"))]


class VisualInfoContact(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "contact"

    @property
    @override
    def title(self) -> str:
        return _("Contact")

    @property
    @override
    def title_plural(self) -> str:
        return _("Contacts")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "log_contact_name",
                TextInput(
                    title=_("Contact name"),
                ),
            ),
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="log_contact_name", label=_("Contact name"))]


class VisualInfoCommand(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "command"

    @property
    @override
    def title(self) -> str:
        return _("Command")

    @property
    @override
    def title_plural(self) -> str:
        return _("Commands")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "command_name",
                TextInput(
                    title=_("Command Name"),
                ),
            ),
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="command_name", label=_("Command Name"))]


class VisualInfoBIAggregation(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "aggr"

    @property
    @override
    def title(self) -> str:
        return _("BI aggregation")

    @property
    @override
    def title_plural(self) -> str:
        return _("BI aggregations")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "aggr_name",
                TextInput(
                    title=_("Aggregation name"),
                ),
            ),
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="aggr_name", label=_("Aggregation name"))]

    @property
    @override
    def sort_index(self) -> int:
        return 20


class VisualInfoBIAggregationGroup(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "aggr_group"

    @property
    @override
    def title(self) -> str:
        return _("BI aggregation group")

    @property
    @override
    def title_plural(self) -> str:
        return _("BI aggregation groups")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "aggr_group",
                TextInput(
                    title=_("Aggregation group"),
                ),
            ),
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="aggr_group", label=_("Aggregation group"))]

    @property
    @override
    def sort_index(self) -> int:
        return 20


class VisualInfoDiscovery(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "discovery"

    @property
    @override
    def title(self) -> str:
        return _("Discovery output")

    @property
    @override
    def title_plural(self) -> str:
        return _("Discovery outputs")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return []

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return []


class VisualInfoEvent(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "event"

    @property
    @override
    def title(self) -> str:
        return _("Event Console event")

    @property
    @override
    def title_plural(self) -> str:
        return _("Event Console events")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "event_id",
                Integer(
                    title=_("Event ID"),
                ),
            ),
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="event_id", label=_("Event ID"))]


class VisualInfoEventHistory(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "history"

    @property
    @override
    def title(self) -> str:
        return _("Historic Event Console event")

    @property
    @override
    def title_plural(self) -> str:
        return _("Historic Event Console events")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "event_id",
                Integer(
                    title=_("Event ID"),
                ),
            ),
            (
                "history_line",
                Integer(
                    title=_("History line number"),
                ),
            ),
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [
            components.TextInput(id="event_id", label=_("Event ID")),
            components.TextInput(id="history_line", label=_("History line number")),
        ]


class VisualInfoCrash(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "crash"

    @property
    @override
    def title(self) -> str:
        return _("Crash report")

    @property
    @override
    def title_plural(self) -> str:
        return _("Crash reports")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "crash_id",
                TextInput(
                    title=_("Crash ID"),
                ),
            ),
        ]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="crash_id", label=_("Crash ID"))]


class VisualInfoKubernetesCluser(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "kubecluster"

    @property
    @override
    def title(self) -> str:
        return _("Kubernetes cluster")

    @property
    @override
    def title_plural(self) -> str:
        return _("Kubernetes clusters")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("kubernetes_cluster", TextInput(title=self.title))]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="kubernetes_cluster", label=self.title)]


class VisualInfoKubernetesNamespace(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "kubenamespace"

    @property
    @override
    def title(self) -> str:
        return _("Kubernetes Namespace")

    @property
    @override
    def title_plural(self) -> str:
        return _("Kubernetes Namespaces")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("kubernetes_namespace", TextInput(title=self.title))]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="kubernetes_namespace", label=self.title)]


class VisualInfoKubernetesDaemonset(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "kubedaemonset"

    @property
    @override
    def title(self) -> str:
        return _("Kubernetes DaemonSet")

    @property
    @override
    def title_plural(self) -> str:
        return _("Kubernetes DaemonSets")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("kubernetes_daemonset", TextInput(title=self.title))]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="kubernetes_daemonset", label=self.title)]


class VisualInfoKubernetesDeployment(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "kubedeployment"

    @property
    @override
    def title(self) -> str:
        return _("Kubernetes deployment")

    @property
    @override
    def title_plural(self) -> str:
        return _("Kubernetes deployments")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("kubernetes_deployment", TextInput(title=self.title))]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="kubernetes_deployment", label=self.title)]


class VisualInfoKubernetesStatefulset(VisualInfo):
    @property
    @override
    def ident(self) -> str:
        return "kubestatefulset"

    @property
    @override
    def title(self) -> str:
        return _("Kubernetes StatefulSet")

    @property
    @override
    def title_plural(self) -> str:
        return _("Kubernetes StatefulSets")

    @property
    @override
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("kubernetes_statefulset", TextInput(title=self.title))]

    @override
    def single_spec_components(self) -> list[FilterComponent]:
        return [components.TextInput(id="kubernetes_statefulset", label=self.title)]
