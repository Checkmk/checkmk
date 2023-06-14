#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.visuals.utils import visual_info_registry, VisualInfo
from cmk.gui.utils.autocompleter_config import ContextAutocompleterConfig
from cmk.gui.valuespec import (
    Integer,
    MonitoredHostname,
    MonitoredServiceDescription,
    TextInput,
    ValueSpec,
)


@visual_info_registry.register
class VisualInfoHost(VisualInfo):
    @property
    def ident(self) -> str:
        return "host"

    @property
    def title(self) -> str:
        return _("Host")

    @property
    def title_plural(self):
        return _("Hosts")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("host", MonitoredHostname(title=_("Hostname"), strict="True"))]

    @property
    def multiple_site_filters(self):
        return ["hostgroup"]

    @property
    def sort_index(self) -> int:
        return 10


@visual_info_registry.register
class VisualInfoService(VisualInfo):
    @property
    def ident(self) -> str:
        return "service"

    @property
    def title(self) -> str:
        return _("Service")

    @property
    def title_plural(self):
        return _("Services")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "service",
                MonitoredServiceDescription(
                    # TODO: replace MonitoredServiceDescription with AjaxDropdownChoice
                    title=_("Service Description"),
                    autocompleter=ContextAutocompleterConfig(
                        ident=MonitoredServiceDescription.ident,
                        strict=True,
                        show_independent_of_context=True,
                    ),
                ),
            )
        ]

    @property
    def multiple_site_filters(self):
        return ["servicegroup"]

    @property
    def sort_index(self) -> int:
        return 10


@visual_info_registry.register
class VisualInfoHostgroup(VisualInfo):
    @property
    def ident(self) -> str:
        return "hostgroup"

    @property
    def title(self) -> str:
        return _("Host group")

    @property
    def title_plural(self):
        return _("Host groups")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "hostgroup",
                TextInput(
                    title=_("Host group name"),
                ),
            )
        ]

    @property
    def single_site(self):
        return False

    @property
    def sort_index(self) -> int:
        return 10


@visual_info_registry.register
class VisualInfoServicegroup(VisualInfo):
    @property
    def ident(self) -> str:
        return "servicegroup"

    @property
    def title(self) -> str:
        return _("Service group")

    @property
    def title_plural(self):
        return _("Service groups")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "servicegroup",
                TextInput(
                    title=_("Service group name"),
                ),
            ),
        ]

    @property
    def single_site(self):
        return False

    @property
    def sort_index(self) -> int:
        return 10


@visual_info_registry.register
class VisualInfoLog(VisualInfo):
    @property
    def ident(self) -> str:
        return "log"

    @property
    def title(self) -> str:
        return _("Log Entry")

    @property
    def title_plural(self):
        return _("Log Entries")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return []


@visual_info_registry.register
class VisualInfoComment(VisualInfo):
    @property
    def ident(self) -> str:
        return "comment"

    @property
    def title(self) -> str:
        return _("Comment")

    @property
    def title_plural(self):
        return _("Comments")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "comment_id",
                Integer(
                    title=_("Comment ID"),
                ),
            ),
        ]


@visual_info_registry.register
class VisualInfoDowntime(VisualInfo):
    @property
    def ident(self) -> str:
        return "downtime"

    @property
    def title(self) -> str:
        return _("Downtime")

    @property
    def title_plural(self):
        return _("Downtimes")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "downtime_id",
                Integer(
                    title=_("Downtime ID"),
                ),
            ),
        ]


@visual_info_registry.register
class VisualInfoContact(VisualInfo):
    @property
    def ident(self) -> str:
        return "contact"

    @property
    def title(self) -> str:
        return _("Contact")

    @property
    def title_plural(self):
        return _("Contacts")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "log_contact_name",
                TextInput(
                    title=_("Contact Name"),
                ),
            ),
        ]


@visual_info_registry.register
class VisualInfoCommand(VisualInfo):
    @property
    def ident(self) -> str:
        return "command"

    @property
    def title(self) -> str:
        return _("Command")

    @property
    def title_plural(self):
        return _("Commands")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "command_name",
                TextInput(
                    title=_("Command Name"),
                ),
            ),
        ]


@visual_info_registry.register
class VisualInfoBIAggregation(VisualInfo):
    @property
    def ident(self) -> str:
        return "aggr"

    @property
    def title(self) -> str:
        return _("BI Aggregation")

    @property
    def title_plural(self):
        return _("BI Aggregations")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "aggr_name",
                TextInput(
                    title=_("Aggregation Name"),
                ),
            ),
        ]

    @property
    def sort_index(self) -> int:
        return 20


@visual_info_registry.register
class VisualInfoBIAggregationGroup(VisualInfo):
    @property
    def ident(self) -> str:
        return "aggr_group"

    @property
    def title(self) -> str:
        return _("BI Aggregation Group")

    @property
    def title_plural(self):
        return _("BI Aggregation Groups")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "aggr_group",
                TextInput(
                    title=_("Aggregation group"),
                ),
            ),
        ]

    @property
    def sort_index(self) -> int:
        return 20


@visual_info_registry.register
class VisualInfoDiscovery(VisualInfo):
    @property
    def ident(self) -> str:
        return "discovery"

    @property
    def title(self) -> str:
        return _("Discovery Output")

    @property
    def title_plural(self):
        return _("Discovery Outputs")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return []


@visual_info_registry.register
class VisualInfoEvent(VisualInfo):
    @property
    def ident(self) -> str:
        return "event"

    @property
    def title(self) -> str:
        return _("Event Console Event")

    @property
    def title_plural(self):
        return _("Event Console Events")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "event_id",
                Integer(
                    title=_("Event ID"),
                ),
            ),
        ]


@visual_info_registry.register
class VisualInfoEventHistory(VisualInfo):
    @property
    def ident(self) -> str:
        return "history"

    @property
    def title(self) -> str:
        return _("Historic Event Console Event")

    @property
    def title_plural(self):
        return _("Historic Event Console Events")

    @property
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
                    title=_("History Line Number"),
                ),
            ),
        ]


@visual_info_registry.register
class VisualInfoCrash(VisualInfo):
    @property
    def ident(self) -> str:
        return "crash"

    @property
    def title(self) -> str:
        return _("Crash report")

    @property
    def title_plural(self):
        return _("Crash reports")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [
            (
                "crash_id",
                TextInput(
                    title=_("Crash ID"),
                ),
            ),
        ]


@visual_info_registry.register
class VisualInfoKubernetesCluser(VisualInfo):
    @property
    def ident(self) -> str:
        return "kubecluster"

    @property
    def title(self) -> str:
        return _("Kubernetes Cluster")

    @property
    def title_plural(self):
        return _("Kubernetes Clusters")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("kubernetes_cluster", TextInput(title=self.title))]


@visual_info_registry.register
class VisualInfoKubernetesNamespace(VisualInfo):
    @property
    def ident(self) -> str:
        return "kubenamespace"

    @property
    def title(self) -> str:
        return _("Kubernetes Namespace")

    @property
    def title_plural(self):
        return _("Kubernetes Namespaces")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("kubernetes_namespace", TextInput(title=self.title))]


@visual_info_registry.register
class VisualInfoKubernetesDaemonset(VisualInfo):
    @property
    def ident(self) -> str:
        return "kubedaemonset"

    @property
    def title(self) -> str:
        return _("Kubernetes Daemonset")

    @property
    def title_plural(self):
        return _("Kubernetes Daemonsets")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("kubernetes_daemonset", TextInput(title=self.title))]


@visual_info_registry.register
class VisualInfoKubernetesDeployment(VisualInfo):
    @property
    def ident(self) -> str:
        return "kubedeployment"

    @property
    def title(self) -> str:
        return _("Kubernetes Deployment")

    @property
    def title_plural(self):
        return _("Kubernetes Deployments")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("kubernetes_deployment", TextInput(title=self.title))]


@visual_info_registry.register
class VisualInfoKubernetesStatefulset(VisualInfo):
    @property
    def ident(self) -> str:
        return "kubestatefulset"

    @property
    def title(self) -> str:
        return _("Kubernetes Statefulset")

    @property
    def title_plural(self):
        return _("Kubernetes Statefulsets")

    @property
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        return [("kubernetes_statefulset", TextInput(title=self.title))]
