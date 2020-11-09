#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict

import cmk.gui.bi as bi
import cmk.gui.watolib as watolib
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato import (
    IndividualOrStoredPassword,
    RulespecGroup,
    RulespecSubGroup,
    monitoring_macro_help,
    rulespec_group_registry,
    rulespec_registry,
    HostRulespec,
)
from cmk.gui.valuespec import (
    ID,
    Age,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    Float,
    HTTPUrl,
    Hostname,
    Integer,
    ListChoice,
    ListOf,
    ListOfStrings,
    MonitoringState,
    Password,
    RegExp,
    RegExpUnicode,
    TextAscii,
    TextUnicode,
    Transform,
    Tuple,
)
from cmk.gui.plugins.wato.utils import (
    PasswordFromStore,)
from cmk.utils import aws_constants
from cmk.gui.plugins.metrics.utils import MetricName


@rulespec_group_registry.register
class RulespecGroupVMCloudContainer(RulespecGroup):
    @property
    def name(self):
        return "vm_cloud_container"

    @property
    def title(self):
        return _("VM, Cloud, Container")

    @property
    def help(self):
        return _("Integrate with VM, cloud or container platforms")


@rulespec_group_registry.register
class RulespecGroupDatasourcePrograms(RulespecGroup):
    @property
    def name(self):
        return "datasource_programs"

    @property
    def title(self):
        return _("Other integrations")

    @property
    def help(self):
        return _("Integrate platforms using special agents, e.g. SAP R/3")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsOS(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "os"

    @property
    def title(self):
        return _("Operating systems")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsApps(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "apps"

    @property
    def title(self):
        return _("Applications")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsCloud(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "cloud"

    @property
    def title(self):
        return _("Cloud based environments")


class RulespecGroupDatasourceProgramsContainer(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "container"

    @property
    def title(self):
        return _("Containerization")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsCustom(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "custom"

    @property
    def title(self):
        return _("Custom integrations")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsHardware(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "hw"

    @property
    def title(self):
        return _("Hardware")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsTesting(RulespecSubGroup):
    @property
    def main_group(self):
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self):
        return "testing"

    @property
    def title(self):
        return _("Testing")


def _valuespec_datasource_programs():
    return TextAscii(
        title=_("Individual program call instead of agent access"),
        help=_("For agent based checks Check_MK allows you to specify an alternative "
               "program that should be called by Check_MK instead of connecting the agent "
               "via TCP. That program must output the agent's data on standard output in "
               "the same format the agent would do. This is for example useful for monitoring "
               "via SSH.") + monitoring_macro_help() +
        _("This option can only be used with the permission \"Can add or modify executables\"."),
        label=_("Command line to execute"),
        empty_text=_("Access Checkmk Agent via TCP"),
        size=80,
        attrencode=True,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsCustom,
        name="datasource_programs",
        valuespec=_valuespec_datasource_programs,
    ))


def _valuespec_special_agents_ddn_s2a():
    return Dictionary(
        elements=[
            ("username", TextAscii(title=_("Username"), allow_empty=False)),
            ("password", Password(title=_("Password"), allow_empty=False)),
            ("port", Integer(title=_("Port"), default_value=8008)),
        ],
        optional_keys=["port"],
        title=_("DDN S2A"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:ddn_s2a",
        valuespec=_valuespec_special_agents_ddn_s2a,
    ))


def _valuespec_special_agents_proxmox():
    return Dictionary(
        elements=[
            ("username", TextAscii(title=_("Username"), allow_empty=False)),
            ("password", IndividualOrStoredPassword(title=_("Password"), allow_empty=False)),
            ("port", Integer(title=_("Port"), default_value=8006)),
            ("no-cert-check",
             FixedValue(
                 True,
                 title=_("Disable SSL certificate validation"),
                 totext=_("SSL certificate validation is disabled"),
             )),
            ("timeout",
             Integer(
                 title=_("Connect Timeout"),
                 help=_("The network timeout in seconds"),
                 default_value=60,
                 minvalue=1,
                 unit=_("seconds"),
             )),
            ("log-cutoff-weeks",
             Integer(
                 title=_("Maximum log age"),
                 help=_("Age in weeks of log data to fetch"),
                 default_value=2,
                 unit=_("weeks"),
             )),
        ],
        title=_("Proxmox"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:proxmox",
        valuespec=_valuespec_special_agents_proxmox,
    ))


def _valuespec_special_agents_cisco_prime():
    return Dictionary(
        elements=[
            ("basicauth",
             Tuple(
                 title=_("BasicAuth settings (optional)"),
                 help=_("The credentials for api calls with authentication."),
                 elements=[
                     TextAscii(title=_("Username"), allow_empty=False),
                     PasswordFromStore(title=_("Password of the user"), allow_empty=False)
                 ],
             )),
            ("port", Integer(title=_("Port"), default_value=8080)),
            ("no-tls",
             FixedValue(
                 True,
                 title=_("Don't use TLS/SSL/Https (unsecure)"),
                 totext=_("TLS/SSL/Https disabled"),
             )),
            ("no-cert-check",
             FixedValue(
                 True,
                 title=_("Disable SSL certificate validation"),
                 totext=_("SSL certificate validation is disabled"),
             )),
            ("timeout",
             Integer(
                 title=_("Connect Timeout"),
                 help=_("The network timeout in seconds"),
                 default_value=60,
                 minvalue=1,
                 unit=_("seconds"),
             )),
        ],
        title=_("Cisco Prime"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsOS,
        name="special_agents:cisco_prime",
        valuespec=_valuespec_special_agents_cisco_prime,
    ))


def _special_agents_kubernetes_transform(value):
    if 'infos' not in value:
        value['infos'] = ['nodes']
    if 'no-cert-check' not in value:
        value['no-cert-check'] = False
    if 'namespaces' not in value:
        value['namespaces'] = False
    return value


def _valuespec_special_agents_kubernetes():
    return Transform(
        Dictionary(
            elements=[
                ("token", IndividualOrStoredPassword(
                    title=_("Token"),
                    allow_empty=False,
                )),
                ("no-cert-check",
                 Alternative(title=_("SSL certificate verification"),
                             elements=[
                                 FixedValue(False, title=_("Verify the certificate"), totext=""),
                                 FixedValue(True,
                                            title=_("Ignore certificate errors (unsecure)"),
                                            totext=""),
                             ],
                             default_value=False)),
                (
                    "namespaces",
                    Alternative(
                        title=_("Namespace prefix for hosts"),
                        elements=[
                            FixedValue(False, title=_("Don't use a namespace prefix"), totext=""),
                            FixedValue(True, title=_("Use a namespace prefix"), totext=""),
                        ],
                        help=
                        _("If a cluster uses multiple namespaces you need to activate this option. "
                          "Hosts for namespaced Kubernetes objects will then be prefixed with the "
                          "name of their namespace. This makes Kubernetes resources in different "
                          "namespaces that have the same name distinguishable, but results in "
                          "longer hostnames."),
                        default_value=False),
                ),
                ("infos",
                 ListChoice(choices=[
                     ("nodes", _("Nodes")),
                     ("services", _("Services")),
                     ("ingresses", _("Ingresses")),
                     ("deployments", _("Deployments")),
                     ("pods", _("Pods")),
                     ("endpoints", _("Endpoints")),
                     ("daemon_sets", _("Daemon sets")),
                     ("stateful_sets", _("Stateful sets")),
                     ("jobs", _("Job")),
                 ],
                            default_value=[
                                "nodes",
                                "endpoints",
                                "ingresses",
                            ],
                            allow_empty=False,
                            title=_("Retrieve information about..."))),
                ("port",
                 Integer(title=_("Port"),
                         help=_("If no port is given a default value of 443 will be used."),
                         default_value=443)),
                ("url-prefix",
                 HTTPUrl(title=_("Custom URL prefix"),
                         help=_("Defines the scheme (either HTTP or HTTPS) and host part "
                                "of Kubernetes API calls like e.g. \"https://example.com\". "
                                "If no prefix is specified HTTPS together with the IP of "
                                "the host will be used."),
                         allow_empty=False)),
                ("path-prefix",
                 TextAscii(
                     title=_("Custom path prefix"),
                     help=_(
                         "Specifies a URL path prefix which is prepended to the path in calls "
                         "to the Kubernetes API. This is e.g. useful if Rancher is used to "
                         "manage Kubernetes clusters. If no prefix is given \"/\" will be used."),
                     allow_empty=False)),
            ],
            optional_keys=["port", "url-prefix", "path-prefix"],
            title=_("Kubernetes"),
            help=
            _("This rule selects the Kubenetes special agent for an existing Checkmk host. "
              "If you want to monitor multiple Kubernetes clusters "
              "we strongly recommend to set up "
              "<a href=\"wato.py?mode=edit_ruleset&varname=piggyback_translation\">Piggyback translation rules</a> "
              "to avoid name collisions. Otherwise e.g. Pods with the same name in "
              "different Kubernetes clusters cannot be distinguished.<br>"
              "Please additionally keep in mind, that not every Kubernetes API is compatible with "
              "every version of the official Kubernetes Python client. E.g. client v11 is only "
              "with the API v1.15 fully compatible. Please check if the latest client version "
              "supports your Kubernetes API version."),
        ),
        forth=_special_agents_kubernetes_transform,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:kubernetes",
        valuespec=_valuespec_special_agents_kubernetes,
    ))


def _check_not_empty_exporter_dict(value, _varprefix):
    if not value:
        raise MKUserError("dict_selection", _("Please select at least one element"))


def _valuespec_generic_metrics_prometheus():
    return Dictionary(
        elements=[
            ("connection",
             CascadingDropdown(
                 choices=[
                     ("ip_address", _("IP Address")),
                     ("host_name", _("Host name")),
                 ],
                 title=_("Prometheus connection option"),
             )),
            ("port", Integer(
                title=_('Prometheus web port'),
                default_value=9090,
            )),
            ("exporter",
             ListOf(
                 CascadingDropdown(choices=[
                     ("node_exporter", _("Node Exporter"),
                      Dictionary(
                          elements=[
                              ("host_mapping",
                               Hostname(
                                   title=_('Explicitly map Node Exporter host'),
                                   allow_empty=True,
                                   help=
                                   _("Per default, Checkmk tries to map the underlying Checkmk host "
                                     "to the Node Exporter host which contains either the Checkmk "
                                     "hostname, host address or \"localhost\" in its endpoint address. "
                                     "The created services of the mapped Node Exporter will "
                                     "be assigned to the Checkmk host. A piggyback host for each "
                                     "Node Exporter host will be created if none of the options are "
                                     "valid."
                                     "This option allows you to explicitly map one of your Node "
                                     "Exporter hosts to the underlying Checkmk host. This can be "
                                     "used if the default options do not apply to your setup."),
                               )),
                              (
                                  "entities",
                                  ListChoice(
                                      choices=[
                                          ("df", _("Filesystems")),
                                          ("diskstat", _("Disk IO")),
                                          ("mem", _("Memory")),
                                          ("kernel", _("CPU utilization & Kernel performance")),
                                      ],
                                      default_value=["df", "diskstat", "mem", "kernel"],
                                      allow_empty=False,
                                      title=_("Retrieve information about..."),
                                      help=
                                      _("For your respective kernel select the hardware or OS entity "
                                        "you would like to retrieve information about.")),
                              ),
                          ],
                          title=_("Node Exporter metrics"),
                          optional_keys=["host_mapping"],
                      )),
                     ("kube_state", _("Kube-state-metrics"),
                      Dictionary(
                          elements=[
                              ("cluster_name",
                               Hostname(
                                   title=_('Cluster name'),
                                   allow_empty=False,
                                   help=
                                   _("You must specify a name for your Kubernetes cluster. The provided name"
                                     " will be used to create a piggyback host for the cluster related services."
                                    ),
                               )),
                              ("entities",
                               ListChoice(
                                   choices=[
                                       ("cluster", _("Cluster")),
                                       ("nodes", _("Nodes")),
                                       ("services", _("Services")),
                                       ("pods", _("Pods")),
                                       ("daemon_sets", _("Daemon sets")),
                                   ],
                                   default_value=[
                                       "cluster", "nodes", "services", "pods", "daemon_sets"
                                   ],
                                   allow_empty=False,
                                   title=_("Retrieve information about..."),
                                   help=
                                   _("For your Kubernetes cluster select for which entity levels "
                                     "you would like to retrieve information about. Piggyback hosts "
                                     "for the respective entities will be created."))),
                          ],
                          title=_("Kube state metrics"),
                          optional_keys=[],
                      )),
                     ("cadvisor", _("cAdvisor"),
                      Dictionary(
                          elements=[
                              ("entity_level",
                               CascadingDropdown(
                                   title=_("Entity level used to create Checkmk piggyback hosts"),
                                   help=
                                   _("The retrieved information from the cAdvisor will be aggregated according"
                                     " to the selected entity level. Resulting services will be allocated to the created"
                                     " Checkmk piggyback hosts."),
                                   choices=[
                                       ("container",
                                        _("Container - Display the information on container level"),
                                        Dictionary(
                                            elements=
                                            [("container_id",
                                              DropdownChoice(
                                                  title=_("Host name used for containers"),
                                                  help=
                                                  _("For Containers - Choose which identifier is used for the monitored containers."
                                                    " This will affect the name used for the piggyback host"
                                                    " corresponding to the container, as well as items for"
                                                    " services created on the node for each container."
                                                   ),
                                                  choices=[
                                                      ("short",
                                                       _("Short - Use the first 12 characters of the docker container ID"
                                                        )),
                                                      ("long",
                                                       _("Long - Use the full docker container ID")
                                                      ),
                                                      ("name",
                                                       _("Name - Use the containers' name")),
                                                  ],
                                              ))],
                                            optional_keys=[],
                                        )),
                                       ("pod", _("Pod - Display the information for pod level"),
                                        Dictionary(elements=[])),
                                       ("both",
                                        _("Both - Display the information for both, pod and container, levels"
                                         ),
                                        Dictionary(
                                            elements=
                                            [("container_id",
                                              DropdownChoice(
                                                  title=_("Host name used for containers"),
                                                  help=
                                                  _("For Containers - Choose which identifier is used for the monitored containers."
                                                    " This will affect the name used for the piggyback host"
                                                    " corresponding to the container, as well as items for"
                                                    " services created on the node for each container."
                                                   ),
                                                  choices=[
                                                      ("short",
                                                       _("Short - Use the first 12 characters of the docker container ID"
                                                        )),
                                                      ("long",
                                                       _("Long - Use the full docker container ID")
                                                      ),
                                                      ("name",
                                                       _("Name - Use the containers' name")),
                                                  ],
                                              ))],
                                            optional_keys=[],
                                        )),
                                   ],
                               )),
                              (
                                  "entities",
                                  ListChoice(
                                      choices=[
                                          ("diskio", _("Disk IO")),
                                          ("cpu", _("CPU utilization")),
                                          ("df", _("Filesystem")),
                                          ("if", _("Network")),
                                          ("memory", _("Memory")),
                                      ],
                                      default_value=["diskio", "cpu", "df", "if", "memory"],
                                      allow_empty=False,
                                      title=_("Retrieve information about..."),
                                      help=
                                      _("For your respective kernel select the hardware or OS entity "
                                        "you would like to retrieve information about.")),
                              ),
                          ],
                          title=_("CAdvisor"),
                          validate=_check_not_empty_exporter_dict,
                          optional_keys=["diskio", "cpu", "df", "if", "memory"],
                      )),
                 ]),
                 add_label=_("Add new Scrape Target"),
                 title=
                 _("Prometheus Scrape Targets (include Prometheus Exporters) to fetch information from"
                  ),
                 help=_("You can specify which Scrape Targets including Exporters "
                        "are connected to your Prometheus instance. The Prometheus "
                        "Special Agent will automatically generate services for the "
                        "selected monitoring information. You can create your own "
                        "defined services with the custom PromQL query option below "
                        "if one of the Scrape Target types are not listed here."),
             )),
            ("promql_checks",
             ListOf(
                 Dictionary(elements=[
                     ("service_description", TextUnicode(
                         title=_('Service name'),
                         allow_empty=False,
                     )),
                     ("host_name",
                      Hostname(
                          title=_('Assign service to following host'),
                          allow_empty=False,
                          help=_("Specify the host to which the resulting "
                                 "service will be assigned to. The host "
                                 "should be configured to allow Piggyback "
                                 "data"),
                      )),
                     ("metric_components",
                      ListOf(
                          Dictionary(
                              title=_('PromQL query'),
                              elements=[
                                  ("metric_label",
                                   TextAscii(
                                       title=_('Metric label'),
                                       allow_empty=False,
                                       help=_(
                                           "The metric label is displayed alongside the "
                                           "queried value in the status detail the resulting service. "
                                           "The metric name will be taken as label if "
                                           "nothing was specified."),
                                   )),
                                  ("metric_name", MetricName()),
                                  ("promql_query",
                                   TextAscii(
                                       title=_('PromQL query (only single return value permitted)'),
                                       allow_empty=False,
                                       size=80,
                                       help=_("Example PromQL query: up{job=\"node_exporter\"}"))),
                                  ("levels",
                                   Dictionary(
                                       elements=[
                                           ("lower_levels",
                                            Tuple(title=_("Lower levels"),
                                                  elements=[
                                                      Float(title=_("Warning below")),
                                                      Float(title=_("Critical below")),
                                                  ])),
                                           ("upper_levels",
                                            Tuple(
                                                title=_("Upper levels"),
                                                elements=[
                                                    Float(title=_("Warning at")),
                                                    Float(title=_("Critical at"))
                                                ],
                                            )),
                                       ],
                                       title="Metric levels",
                                       validate=_verify_prometheus_empty,
                                       help=
                                       _("Specify upper and/or lower levels for the queried PromQL value. This option "
                                         "should be used for simple cases where levels are only required once. You "
                                         "should use the Prometheus custom services monitoring rule if you want to "
                                         "specify a rule which applies to multiple Prometheus custom services at once. "
                                         "The custom rule always has priority over the rule specified here "
                                         "if the two overlap."),
                                   )),
                              ],
                              optional_keys=["metric_name", "levels"],
                          ),
                          title=_('PromQL queries for Service'),
                          add_label=_("Add new PromQL query"),
                          allow_empty=False,
                          magic='@;@',
                          validate=_validate_prometheus_service_metrics,
                      )),
                 ],
                            optional_keys=["host_name"]),
                 title=_("Service creation using PromQL queries"),
                 add_label=_("Add new Service"),
             )),
        ],
        title=_("Prometheus"),
        optional_keys=[],
    )


def _verify_prometheus_empty(value, varprefix):
    if not value:
        raise MKUserError(varprefix, _("Please specify at least one type of levels"))


def _validate_prometheus_service_metrics(value, _varprefix):
    used_metric_names = []
    for metric_details in value:
        metric_name = metric_details.get("metric_name")
        if not metric_name:
            continue
        if metric_name in used_metric_names:
            raise MKUserError(metric_name, _("Each metric must be unique for a service"))
        used_metric_names.append(metric_name)


rulespec_registry.register((HostRulespec(
    group=RulespecGroupVMCloudContainer,
    name="special_agents:prometheus",
    valuespec=_valuespec_generic_metrics_prometheus,
)))


def _factory_default_special_agents_vsphere():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_vsphere():
    return Transform(valuespec=Dictionary(
        elements=[
            ("user", TextAscii(
                title=_("vSphere User name"),
                allow_empty=False,
            )),
            ("secret", IndividualOrStoredPassword(
                title=_("vSphere secret"),
                allow_empty=False,
            )),
            ("direct",
             DropdownChoice(
                 title=_("Type of query"),
                 choices=[
                     (True, _("Queried host is a host system")),
                     ("hostsystem_agent",
                      _("Queried host is a host system with Checkmk Agent installed")),
                     (False, _("Queried host is the vCenter")),
                     ("agent", _("Queried host is the vCenter with Checkmk Agent installed")),
                 ],
                 default_value=True,
             )),
            ("tcp_port",
             Integer(
                 title=_("TCP Port number"),
                 help=_("Port number for HTTPS connection to vSphere"),
                 default_value=443,
                 minvalue=1,
                 maxvalue=65535,
             )),
            ("ssl",
             Alternative(
                 title=_("SSL certificate checking"),
                 elements=[
                     FixedValue(False, title=_("Deactivated"), totext=""),
                     FixedValue(True, title=_("Use hostname"), totext=""),
                     TextAscii(
                         title=_("Use other hostname"),
                         help=
                         _("The IP of the other hostname needs to be the same IP as the host address"
                          ))
                 ],
                 default_value=False)),
            ("timeout",
             Integer(
                 title=_("Connect Timeout"),
                 help=_(
                     "The network timeout in seconds when communicating with vSphere or "
                     "to the Check_MK Agent. The default is 60 seconds. Please note that this "
                     "is not a total timeout but is applied to each individual network transation."
                 ),
                 default_value=60,
                 minvalue=1,
                 unit=_("seconds"),
             )),
            ("infos",
             Transform(
                 ListChoice(
                     choices=[
                         ("hostsystem", _("Host Systems")),
                         ("virtualmachine", _("Virtual Machines")),
                         ("datastore", _("Datastores")),
                         ("counters", _("Performance Counters")),
                         ("licenses", _("License Usage")),
                     ],
                     default_value=["hostsystem", "virtualmachine", "datastore", "counters"],
                     allow_empty=False,
                 ),
                 forth=lambda v: [x.replace("storage", "datastore") for x in v],
                 title=_("Retrieve information about..."),
             )),
            ("skip_placeholder_vms",
             Checkbox(
                 title=_("Placeholder VMs"),
                 label=_("Do no monitor placeholder VMs"),
                 default_value=True,
                 true_label=_("ignore"),
                 false_label=_("monitor"),
                 help=
                 _("Placeholder VMs are created by the Site Recovery Manager(SRM) and act as backup "
                   "virtual machines in case the default vm is unable to start. This option tells the "
                   "vsphere agent to exclude placeholder vms in its output."),
             )),
            ("host_pwr_display",
             DropdownChoice(
                 title=_("Display ESX Host power state on"),
                 choices=[
                     (None, _("The queried ESX system (vCenter / Host)")),
                     ("esxhost", _("The ESX Host")),
                     ("vm", _("The Virtual Machine")),
                 ],
                 default_value=None,
             )),
            ("vm_pwr_display",
             DropdownChoice(
                 title=_("Display VM power state <i>additionally</i> on"),
                 help=_("The power state can be displayed additionally either "
                        "on the ESX host or the VM. This will result in services "
                        "for <i>both</i> the queried system and the ESX host / VM. "
                        "By disabling the unwanted services it is then possible "
                        "to configure where the services are displayed."),
                 choices=[
                     (None, _("The queried ESX system (vCenter / Host)")),
                     ("esxhost", _("The ESX Host")),
                     ("vm", _("The Virtual Machine")),
                 ],
                 default_value=None,
             )),
            ("snapshot_display",
             DropdownChoice(
                 title=_("<i>Additionally</i> display snapshots on"),
                 help=_("The created snapshots can be displayed additionally either "
                        "on the ESX host or the vCenter. This will result in services "
                        "for <i>both</i> the queried system and the ESX host / vCenter. "
                        "By disabling the unwanted services it is then possible "
                        "to configure where the services are displayed."),
                 choices=[
                     (None, _("The Virtual Machine")),
                     ("esxhost", _("The ESX Host")),
                     ("vCenter", _("The queried ESX system (vCenter / Host)")),
                 ],
                 default_value=None,
             )),
            ("vm_piggyname",
             DropdownChoice(
                 title=_("Piggyback name of virtual machines"),
                 choices=[
                     ("alias", _("Use the name specified in the ESX system")),
                     ("hostname",
                      _("Use the VMs hostname if set, otherwise fall back to ESX name")),
                 ],
                 default_value="alias",
             )),
            ("spaces",
             DropdownChoice(
                 title=_("Spaces in hostnames"),
                 choices=[
                     ("cut", _("Cut everything after first space")),
                     ("underscore", _("Replace with underscores")),
                 ],
                 default_value="underscore",
             )),
        ],
        optional_keys=[
            "tcp_port",
            "timeout",
            "vm_pwr_display",
            "host_pwr_display",
            "snapshot_display",
            "vm_piggyname",
        ],
        ignored_keys=["use_pysphere"],
    ),
                     title=_("VMWare ESX via vSphere"),
                     help=_(
                         "This rule selects the vSphere agent instead of the normal Check_MK Agent "
                         "and allows monitoring of VMWare ESX via the vSphere API. You can configure "
                         "your connection settings here."),
                     forth=lambda a: dict([("skip_placeholder_vms", True), ("ssl", False),
                                           ("use_pysphere", False),
                                           ("spaces", "underscore")] + list(a.items())))


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_vsphere(),
        group=RulespecGroupVMCloudContainer,
        name="special_agents:vsphere",
        valuespec=_valuespec_special_agents_vsphere,
    ))


def _valuespec_special_agents_hp_msa():
    return Dictionary(
        elements=[
            ("username", TextAscii(
                title=_("Username"),
                allow_empty=False,
            )),
            ("password", Password(
                title=_("Password"),
                allow_empty=False,
            )),
        ],
        optional_keys=False,
        title=_("HP MSA via Web Interface"),
        help=_("This rule selects the Agent HP MSA instead of the normal Check_MK Agent "
               "which collects the data through the HP MSA web interface"),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:hp_msa",
        valuespec=_valuespec_special_agents_hp_msa,
    ))


def _special_agents_ipmi_sensors_vs_ipmi_common_elements():
    return [
        ("username", TextAscii(
            title=_("Username"),
            allow_empty=False,
        )),
        ("password", Password(
            title=_("Password"),
            allow_empty=False,
        )),
        ("privilege_lvl",
         TextAscii(
             title=_("Privilege Level"),
             help=_("Possible are 'user', 'operator', 'admin'"),
             allow_empty=False,
         )),
    ]


def _special_agents_ipmi_sensors_transform_ipmi_sensors(params):
    if isinstance(params, dict):
        return ("freeipmi", params)
    return params


def _special_agents_ipmi_sensors_vs_freeipmi():
    return Dictionary(
        elements=_special_agents_ipmi_sensors_vs_ipmi_common_elements() + [
            ("ipmi_driver", TextAscii(title=_("IPMI driver"))),
            ("driver_type", TextAscii(title=_("IPMI driver type"))),
            ("BMC_key", TextAscii(title=_("BMC key"))),
            ("quiet_cache", Checkbox(title=_("Quiet cache"), label=_("Enable"))),
            ("sdr_cache_recreate", Checkbox(title=_("SDR cache recreate"), label=_("Enable"))),
            ("interpret_oem_data", Checkbox(title=_("OEM data interpretation"), label=_("Enable"))),
            ("output_sensor_state", Checkbox(title=_("Sensor state"), label=_("Enable"))),
            ("output_sensor_thresholds", Checkbox(title=_("Sensor threshold"), label=_("Enable"))),
            ("ignore_not_available_sensors",
             Checkbox(title=_("Suppress not available sensors"), label=_("Enable"))),
        ],
        optional_keys=[
            "ipmi_driver",
            "driver_type",
            "quiet_cache",
            "sdr_cache_recreate",
            "interpret_oem_data",
            "output_sensor_state",
            "output_sensor_thresholds",
            "ignore_not_available_sensors",
            "BMC_key",
        ],
    )


def _special_agents_ipmi_sensors_vs_ipmitool():
    return Dictionary(
        elements=_special_agents_ipmi_sensors_vs_ipmi_common_elements(),
        optional_keys=[],
    )


def _valuespec_special_agents_ipmi_sensors():
    return Transform(
        CascadingDropdown(
            choices=[
                ("freeipmi", _("Use FreeIPMI"), _special_agents_ipmi_sensors_vs_freeipmi()),
                ("ipmitool", _("Use IPMItool"), _special_agents_ipmi_sensors_vs_ipmitool()),
            ],
            title=_("IPMI Sensors via Freeipmi or IPMItool"),
            help=_("This rule selects the Agent IPMI Sensors instead of the normal Check_MK Agent "
                   "which collects the data through the FreeIPMI resp. IPMItool command"),
        ),
        forth=_special_agents_ipmi_sensors_transform_ipmi_sensors,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsOS,
        name="special_agents:ipmi_sensors",
        valuespec=_valuespec_special_agents_ipmi_sensors,
    ))


def _valuespec_special_agents_netapp():
    return Transform(Dictionary(
        elements=[
            ("username", TextAscii(
                title=_("Username"),
                allow_empty=False,
            )),
            ("password", Password(
                title=_("Password"),
                allow_empty=False,
            )),
            ("skip_elements",
             ListChoice(
                 choices=[
                     ("ctr_volumes", _("Do not query volume performance counters")),
                 ],
                 title=_("Performance improvements"),
                 help=_(
                     "Here you can configure whether the performance counters should get queried. "
                     "This can save quite a lot of CPU load on larger systems."),
             )),
        ],
        title=_("NetApp via WebAPI"),
        help=_(
            "This rule set selects the NetApp special agent instead of the normal Check_MK Agent "
            "and allows monitoring via the NetApp Web API. To access the data the "
            "user requires permissions to several API classes. They are shown when you call the agent with "
            "<tt>agent_netapp --help</tt>. The agent itself is located in the site directory under "
            "<tt>~/share/check_mk/agents/special</tt>."),
        optional_keys=False,
    ),
                     forth=lambda x: dict([("skip_elements", [])] + list(x.items())))


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:netapp",
        valuespec=_valuespec_special_agents_netapp,
    ))


def _special_agents_activemq_transform_activemq(value):
    if not isinstance(value, tuple):
        return value
    new_value = {}
    new_value["servername"] = value[0]
    new_value["port"] = value[1]
    new_value["use_piggyback"] = "piggybag" in value[2]  # piggybag...
    return new_value


def _factory_default_special_agents_activemq():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_activemq():
    return Transform(
        Dictionary(elements=[
            ("servername", TextAscii(
                title=_("Server Name"),
                allow_empty=False,
            )), ("port", Integer(title=_("Port Number"), default_value=8161)),
            ("use_piggyback", Checkbox(title=_("Use Piggyback"), label=_("Enable"))),
            ("basicauth",
             Tuple(title=_("BasicAuth settings (optional)"),
                   elements=[TextAscii(title=_("Username")),
                             Password(title=_("Password"))]))
        ],
                   optional_keys=["basicauth"]),
        title=_("Apache ActiveMQ queues"),
        forth=_special_agents_activemq_transform_activemq,
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_activemq(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:activemq",
        valuespec=_valuespec_special_agents_activemq,
    ))


def _factory_default_special_agents_emcvnx():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_emcvnx():
    return Dictionary(
        title=_("EMC VNX storage systems"),
        help=_("This rule selects the EMC VNX agent instead of the normal Check_MK Agent "
               "and allows monitoring of EMC VNX storage systems by calling naviseccli "
               "commandline tool locally on the monitoring system. Make sure it is installed "
               "and working. You can configure your connection settings here."),
        elements=[
            ("user",
             TextAscii(
                 title=_("EMC VNX admin user name"),
                 allow_empty=True,
                 help=_(
                     "If you leave user name and password empty, the special agent tries to "
                     "authenticate against the EMC VNX device by Security Files. "
                     "These need to be created manually before using. Therefor run as "
                     "instance user (if using OMD) or Nagios user (if not using OMD) "
                     "a command like "
                     "<tt>naviseccli -AddUserSecurity -scope 0 -password PASSWORD -user USER</tt> "
                     "This creates <tt>SecuredCLISecurityFile.xml</tt> and "
                     "<tt>SecuredCLIXMLEncrypted.key</tt> in the home directory of the user "
                     "and these files are used then."),
             )),
            ("password", Password(
                title=_("EMC VNX admin user password"),
                allow_empty=True,
            )),
            ("infos",
             Transform(
                 ListChoice(
                     choices=[
                         ("disks", _("Disks")),
                         ("hba", _("iSCSI HBAs")),
                         ("hwstatus", _("Hardware status")),
                         ("raidgroups", _("RAID groups")),
                         ("agent", _("Model and revsion")),
                         ("sp_util", _("Storage processor utilization")),
                         ("writecache", _("Write cache state")),
                         ("mirrorview", _("Mirror views")),
                         ("storage_pools", _("Storage pools")),
                     ],
                     default_value=[
                         "disks",
                         "hba",
                         "hwstatus",
                     ],
                     allow_empty=False,
                 ),
                 title=_("Retrieve information about..."),
             )),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_emcvnx(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:emcvnx",
        valuespec=_valuespec_special_agents_emcvnx,
    ))


def _factory_default_special_agents_ibmsvc():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_ibmsvc():
    return Dictionary(
        title=_("IBM SVC / V7000 storage systems"),
        help=_(
            "This rule set selects the <tt>ibmsvc</tt> agent instead of the normal Check_MK Agent "
            "and allows monitoring of IBM SVC / V7000 storage systems by calling "
            "ls* commands there over SSH. "
            "Make sure you have SSH key authentication enabled for your monitoring user. "
            "That means: The user your monitoring is running under on the monitoring "
            "system must be able to ssh to the storage system as the user you gave below "
            "without password."),
        elements=[
            ("user",
             TextAscii(
                 title=_("IBM SVC / V7000 user name"),
                 allow_empty=True,
                 help=_("User name on the storage system. Read only permissions are sufficient."),
             )),
            ("accept-any-hostkey",
             Checkbox(
                 title=_("Accept any SSH Host Key"),
                 label=_("Accept any SSH Host Key"),
                 default_value=False,
                 help=_(
                     "Accepts any SSH Host Key presented by the storage device. "
                     "Please note: This might be a security issue because man-in-the-middle "
                     "attacks are not recognized! Better solution would be to add the "
                     "SSH Host Key of the monitored storage devices to the .ssh/known_hosts "
                     "file for the user your monitoring is running under (on OMD: the site user)"))
            ),
            ("infos",
             Transform(
                 ListChoice(
                     choices=[
                         ("lshost", _("Hosts Connected")),
                         ("lslicense", _("Licensing Status")),
                         ("lsmdisk", _("MDisks")),
                         ("lsmdiskgrp", _("MDisksGrps")),
                         ("lsnode", _("IO Groups")),
                         ("lsnodestats", _("Node Stats")),
                         ("lssystem", _("System Info")),
                         ("lssystemstats", _("System Stats")),
                         ("lseventlog", _("Event Log")),
                         ("lsportfc", _("FC Ports")),
                         ("lsportsas", _("SAS Ports")),
                         ("lsenclosure", _("Enclosures")),
                         ("lsenclosurestats", _("Enclosure Stats")),
                         ("lsarray", _("RAID Arrays")),
                         ("disks", _("Physical Disks")),
                     ],
                     default_value=[
                         "lshost", "lslicense", "lsmdisk", "lsmdiskgrp", "lsnode", "lsnodestats",
                         "lssystem", "lssystemstats", "lsportfc", "lsenclosure", "lsenclosurestats",
                         "lsarray", "disks"
                     ],
                     allow_empty=False,
                 ),
                 title=_("Retrieve information about..."),
             )),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_ibmsvc(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:ibmsvc",
        valuespec=_valuespec_special_agents_ibmsvc,
    ))


def _factory_default_special_agents_random():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_random():
    return FixedValue(
        {},
        title=_("Create random monitoring data"),
        help=_("By configuring this rule for a host - instead of the normal "
               "Check_MK agent random monitoring data will be created."),
        totext=_("Create random monitoring data"),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_random(),
        group=RulespecGroupDatasourceProgramsTesting,
        name="special_agents:random",
        valuespec=_valuespec_special_agents_random,
    ))


def _factory_default_special_agents_acme_sbc():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_acme_sbc():
    return FixedValue(
        {},
        title=_("ACME Session Border Controller"),
        help=_("This rule activates an agent which connects "
               "to an ACME Session Border Controller (SBC). This agent uses SSH, so "
               "you have to exchange an SSH key to make a passwordless connect possible."),
        totext=_("Connect to ACME SBC"),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_acme_sbc(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:acme_sbc",
        valuespec=_valuespec_special_agents_acme_sbc,
    ))


def _factory_default_special_agents_fritzbox():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_fritzbox():
    return Dictionary(
        title=_("Fritz!Box Devices"),
        help=_("This rule selects the Fritz!Box agent, which uses UPNP to gather information "
               "about configuration and connection status information."),
        elements=[
            ("timeout",
             Integer(
                 title=_("Connect Timeout"),
                 help=_("The network timeout in seconds when communicating via UPNP. "
                        "The default is 10 seconds. Please note that this "
                        "is not a total timeout, instead it is applied to each API call."),
                 default_value=10,
                 minvalue=1,
                 unit=_("seconds"),
             )),
        ],
        optional_keys=["timeout"],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_fritzbox(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:fritzbox",
        valuespec=_valuespec_special_agents_fritzbox,
    ))


def _factory_default_special_agents_innovaphone():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_innovaphone():
    return Tuple(
        title=_("Innovaphone Gateways"),
        help=_("Please specify the user and password needed to access the xml interface"),
        elements=[
            TextAscii(title=_("Username")),
            Password(title=_("Password")),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_innovaphone(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:innovaphone",
        valuespec=_valuespec_special_agents_innovaphone,
    ))


def _factory_default_special_agents_hivemanager():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_hivemanager():
    return Tuple(title=_("Aerohive HiveManager"),
                 help=_("Activate monitoring of host via a HTTP connect to the HiveManager"),
                 elements=[
                     TextAscii(title=_("Username")),
                     Password(title=_("Password")),
                 ])


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_hivemanager(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:hivemanager",
        valuespec=_valuespec_special_agents_hivemanager,
    ))


def _factory_default_special_agents_hivemanager_ng():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_hivemanager_ng():
    return Dictionary(
        title=_("Aerohive HiveManager NG"),
        help=_("Activate monitoring of the HiveManagerNG cloud."),
        elements=[
            ("url",
             HTTPUrl(
                 title=_("URL to HiveManagerNG, e.g. https://cloud.aerohive.com"),
                 allow_empty=False,
             )),
            ("vhm_id", TextAscii(
                title=_("Numerical ID of the VHM, e.g. 102"),
                allow_empty=False,
            )),
            ("api_token", TextAscii(
                title=_("API Access Token"),
                size=64,
                allow_empty=False,
            )),
            ("client_id", TextAscii(
                title=_("Client ID"),
                allow_empty=False,
            )),
            ("client_secret", Password(
                title=_("Client secret"),
                allow_empty=False,
            )),
            ("redirect_url", HTTPUrl(
                title=_("Redirect URL (has to be https)"),
                allow_empty=False,
            )),
        ],
        optional_keys=False,
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_hivemanager_ng(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:hivemanager_ng",
        valuespec=_valuespec_special_agents_hivemanager_ng,
    ))


def _factory_default_special_agents_allnet_ip_sensoric():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_allnet_ip_sensoric():
    return Dictionary(
        title=_("ALLNET IP Sensoric Devices"),
        help=_("This rule selects the ALLNET IP Sensoric agent, which fetches "
               "/xml/sensordata.xml from the device by HTTP and extracts the "
               "needed monitoring information from this file."),
        elements=[
            ("timeout",
             Integer(
                 title=_("Connect Timeout"),
                 help=_("The network timeout in seconds when communicating via HTTP. "
                        "The default is 10 seconds."),
                 default_value=10,
                 minvalue=1,
                 unit=_("seconds"),
             )),
        ],
        optional_keys=["timeout"],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_allnet_ip_sensoric(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:allnet_ip_sensoric",
        valuespec=_valuespec_special_agents_allnet_ip_sensoric,
    ))


def _valuespec_special_agents_ucs_bladecenter():
    return Dictionary(
        title=_("UCS Bladecenter"),
        help=_("This rule selects the UCS Bladecenter agent instead of the normal Check_MK Agent "
               "which collects the data through the UCS Bladecenter Web API"),
        elements=[
            ("username", TextAscii(
                title=_("Username"),
                allow_empty=False,
            )),
            ("password", Password(
                title=_("Password"),
                allow_empty=False,
            )),
            ("no_cert_check",
             FixedValue(
                 True,
                 title=_("Disable SSL certificate validation"),
                 totext=_("SSL certificate validation is disabled"),
             )),
        ],
        optional_keys=['no_cert_check'],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:ucs_bladecenter",
        valuespec=_valuespec_special_agents_ucs_bladecenter,
    ))


def _special_agents_siemens_plc_validate_siemens_plc_values(value, varprefix):
    valuetypes: Dict[Any, Any] = {}
    for index, (_db_number, _address, _datatype, valuetype, ident) in enumerate(value):
        valuetypes.setdefault(valuetype, [])
        if ident in valuetypes[valuetype]:
            raise MKUserError("%s_%d_%d" % (varprefix, index + 1, 4),
                              _("The ident of a value needs to be unique per valuetype."))
        valuetypes[valuetype].append(ident)


def _special_agents_siemens_plc_siemens_plc_value():
    return [
        Transform(
            CascadingDropdown(
                title=_("The Area"),
                choices=[
                    ("db", _("Datenbaustein"),
                     Integer(
                         title="<nobr>%s</nobr>" % _("DB Number"),
                         minvalue=1,
                     )),
                    ("input", _("Input")),
                    ("output", _("Output")),
                    ("merker", _("Merker")),
                    ("timer", _("Timer")),
                    ("counter", _("Counter")),
                ],
                orientation="horizontal",
                sorted=True,
            ),
            # Transform old Integer() value spec to new cascading dropdown value
            forth=lambda x: isinstance(x, int) and ("db", x) or x,
        ),
        Float(
            title=_("Address"),
            display_format="%.1f",
            help=_("Addresses are specified with a dot notation, where number "
                   "before the dot specify the byte to fetch and the number after the "
                   "dot specifies the bit to fetch. The number of the bit is always "
                   "between 0 and 7."),
        ),
        CascadingDropdown(
            title=_("Datatype"),
            choices=[
                ("dint", _("Double Integer (DINT)")),
                ("real", _("Real Number (REAL)")),
                ("bit", _("Single Bit (BOOL)")),
                ("str", _("String (STR)"), Integer(
                    minvalue=1,
                    title=_("Size"),
                    unit=_("Bytes"),
                )),
                ("raw", _("Raw Bytes (HEXSTR)"),
                 Integer(
                     minvalue=1,
                     title=_("Size"),
                     unit=_("Bytes"),
                 )),
            ],
            orientation="horizontal",
            sorted=True,
        ),
        DropdownChoice(
            title=_("Type of the value"),
            choices=[
                (None, _("Unclassified")),
                ("temp", _("Temperature")),
                ("hours_operation", _("Hours of operation")),
                ("hours_since_service", _("Hours since service")),
                ("hours", _("Hours")),
                ("seconds_operation", _("Seconds of operation")),
                ("seconds_since_service", _("Seconds since service")),
                ("seconds", _("Seconds")),
                ("counter", _("Increasing counter")),
                ("flag", _("State flag (on/off)")),
                ("text", _("Text")),
            ],
            sorted=True,
        ),
        ID(
            title=_("Ident of the value"),
            help=_(" An identifier of your choice. This identifier "
                   "is used by the Check_MK checks to access "
                   "and identify the single values. The identifier "
                   "needs to be unique within a group of VALUETYPES."),
        ),
    ]


def _factory_default_special_agents_siemens_plc():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_siemens_plc():
    return Dictionary(
        elements=[
            ("devices",
             ListOf(
                 Dictionary(
                     elements=[
                         ('host_name',
                          TextAscii(
                              title=_('Name of the PLC'),
                              allow_empty=False,
                              help=_(
                                  'Specify the logical name, e.g. the hostname, of the PLC. This name '
                                  'is used to name the resulting services.'))),
                         ('host_address',
                          TextAscii(
                              title=_('Network Address'),
                              allow_empty=False,
                              help=
                              _('Specify the hostname or IP address of the PLC to communicate with.'
                               ))),
                         ("rack", Integer(
                             title=_("Number of the Rack"),
                             minvalue=0,
                         )),
                         ("slot", Integer(
                             title=_("Number of the Slot"),
                             minvalue=0,
                         )),
                         ("tcp_port",
                          Integer(
                              title=_("TCP Port number"),
                              help=_("Port number for communicating with the PLC"),
                              default_value=102,
                              minvalue=1,
                              maxvalue=65535,
                          )),
                         ("timeout",
                          Integer(
                              title=_("Connect Timeout"),
                              help=_(
                                  "The connect timeout in seconds when establishing a connection "
                                  "with the PLC."),
                              default_value=60,
                              minvalue=1,
                              unit=_("seconds"),
                          )),
                         ("values",
                          ListOf(
                              Tuple(
                                  elements=_special_agents_siemens_plc_siemens_plc_value(),
                                  orientation="horizontal",
                              ),
                              title=_("Values to fetch from this device"),
                              validate=_special_agents_siemens_plc_validate_siemens_plc_values,
                              magic='@;@',
                          )),
                     ],
                     optional_keys=["timeout"],
                 ),
                 title=_("Devices to fetch information from"),
             )),
            ("values",
             ListOf(
                 Tuple(
                     elements=_special_agents_siemens_plc_siemens_plc_value(),
                     orientation="horizontal",
                 ),
                 title=_("Values to fetch from all devices"),
                 validate=_special_agents_siemens_plc_validate_siemens_plc_values,
             )),
        ],
        optional_keys=["timeout"],
        title=_("Siemens PLC (SPS)"),
        help=_("This rule selects the Siemens PLC agent instead of the normal Check_MK Agent "
               "and allows monitoring of Siemens PLC using the Snap7 API. You can configure "
               "your connection settings and values to fetch here."),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_siemens_plc(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:siemens_plc",
        valuespec=_valuespec_special_agents_siemens_plc,
    ))


def _valuespec_special_agents_ruckus_spot():
    return Dictionary(
        elements=[
            ("address",
             Alternative(
                 title=_("Server Address"),
                 help=_("Here you can set a manual address if the server differs from the host"),
                 elements=[
                     FixedValue(
                         True,
                         title=_("Use host address"),
                         totext="",
                     ),
                     TextAscii(title=_("Enter address"),)
                 ],
                 default_value=True)),
            ("port", Integer(
                title=_("Port"),
                default_value=8443,
            )),
            ("venueid", TextAscii(
                title=_("Venue ID"),
                allow_empty=False,
            )),
            ("api_key", TextAscii(
                title=_("API key"),
                allow_empty=False,
                size=70,
            )),
            ("cmk_agent",
             Dictionary(
                 title=_("Also contact Checkmk agent"),
                 help=_("With this setting, the special agent will also contact the "
                        "Check_MK agent on the same system at the specified port."),
                 elements=[
                     ("port", Integer(
                         title=_("Port"),
                         default_value=6556,
                     )),
                 ],
                 optional_keys=[],
             )),
        ],
        title=_("Ruckus Spot"),
        help=_("This rule selects the Agent Ruckus Spot agent instead of the normal Check_MK Agent "
               "which collects the data through the Ruckus Spot web interface"),
        optional_keys=["cmk_agent"])


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:ruckus_spot",
        valuespec=_valuespec_special_agents_ruckus_spot,
    ))


def _factory_default_special_agents_appdynamics():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_appdynamics():
    return Dictionary(
        title=_('AppDynamics via REST API'),
        help=_(
            'This rule allows querying an AppDynamics server for information about Java applications'
            'via the AppDynamics REST API. You can configure your connection settings here.'),
        elements=[
            ('username', TextAscii(
                title=_('AppDynamics login username'),
                allow_empty=False,
            )),
            ('password', Password(
                title=_('AppDynamics login password'),
                allow_empty=False,
            )),
            ('application',
             TextAscii(
                 title=_('AppDynamics application name'),
                 help=
                 _('This is the application name used in the URL. If you enter for example the application '
                   'name <tt>foobar</tt>, this would result in the URL being used to contact the REST API: '
                   '<tt>/controller/rest/applications/foobar/metric-data</tt>'),
                 allow_empty=False,
                 size=40,
             )),
            ('port',
             Integer(
                 title=_('TCP port number'),
                 help=_('Port number that AppDynamics is listening on. The default is 8090.'),
                 default_value=8090,
                 minvalue=1,
                 maxvalue=65535,
             )),
            ('timeout',
             Integer(
                 title=_('Connection timeout'),
                 help=_('The network timeout in seconds when communicating with AppDynamics.'
                        'The default is 30 seconds.'),
                 default_value=30,
                 minvalue=1,
                 unit=_('seconds'),
             )),
        ],
        optional_keys=['port', 'timeout'],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_appdynamics(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:appdynamics",
        valuespec=_valuespec_special_agents_appdynamics,
    ))


def _special_agents_jolokia_mk_jolokia_elements():
    return [
        ("port",
         Integer(
             title=_("TCP port for connection"),
             default_value=8080,
             minvalue=1,
             maxvalue=65535,
         )),
        ("login",
         Tuple(title=_("Optional login (if required)"),
               elements=[
                   TextAscii(
                       title=_("User ID for web login (if login required)"),
                       default_value="monitoring",
                   ),
                   Password(title=_("Password for this user")),
                   DropdownChoice(title=_("Login mode"),
                                  choices=[
                                      ("basic", _("HTTP Basic Authentication")),
                                      ("digest", _("HTTP Digest")),
                                  ])
               ])),
        ("suburi",
         TextAscii(
             title=_("relative URI under which Jolokia is visible"),
             default_value="jolokia",
             size=30,
         )),
        ("instance",
         TextUnicode(title=_("Name of the instance in the monitoring"),
                     help=_("If you do not specify a name here, then the TCP port number "
                            "will be used as an instance name."))),
        ("protocol",
         DropdownChoice(title=_("Protocol"), choices=[
             ("http", "HTTP"),
             ("https", "HTTPS"),
         ])),
    ]


def _factory_default_special_agents_jolokia():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_jolokia():
    return Dictionary(
        title=_('Jolokia'),
        help=_('This rule allows querying the Jolokia web API.'),
        elements=_special_agents_jolokia_mk_jolokia_elements(),
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_jolokia(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:jolokia",
        valuespec=_valuespec_special_agents_jolokia,
    ))


def _valuespec_special_agents_tinkerforge():
    return Dictionary(
        title=_("Tinkerforge"),
        elements=[
            ("port",
             Integer(title=_('TCP port number'),
                     help=_('Port number that AppDynamics is listening on. The default is 8090.'),
                     default_value=4223,
                     minvalue=1,
                     maxvalue=65535)),
            ("segment_display_uid",
             TextAscii(
                 title=_("7-segment display uid"),
                 help=_(
                     "This is the uid of the sensor you want to display in the 7-segment display, "
                     "not the uid of the display itself. There is currently no support for "
                     "controling multiple displays."))),
            ("segment_display_brightness",
             Integer(title=_("7-segment display brightness"), minvalue=0, maxvalue=7))
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:tinkerforge",
        valuespec=_valuespec_special_agents_tinkerforge,
    ))


def _valuespec_special_agents_prism():
    return Dictionary(
        title=_("Nutanix Prism"),
        elements=[
            ("port",
             Integer(title=_("TCP port for connection"),
                     default_value=9440,
                     minvalue=1,
                     maxvalue=65535)),
            ("username", TextAscii(title=_("User ID for web login"),)),
            ("password", Password(title=_("Password for this user"))),
        ],
        optional_keys=["port"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsOS,
        name="special_agents:prism",
        valuespec=_valuespec_special_agents_prism,
    ))


def _special_agents_3par_transform_3par_add_verify_cert(v):
    v.setdefault("verify_cert", False)
    return v


def _valuespec_special_agents_3par():
    return Transform(
        Dictionary(
            title=_("3PAR Configuration"),
            elements=[
                ("user", TextAscii(
                    title=_("Username"),
                    allow_empty=False,
                )),
                ("password", IndividualOrStoredPassword(
                    title=_("Password"),
                    allow_empty=False,
                )),
                ("verify_cert",
                 DropdownChoice(
                     title=_("SSL certificate verification"),
                     choices=[
                         (True, _("Activate")),
                         (False, _("Deactivate")),
                     ],
                 )),
                ("values",
                 ListOfStrings(
                     title=_("Values to fetch"),
                     orientation="horizontal",
                     help=_("Possible values are the following: cpgs, volumes, hosts, capacity, "
                            "system, ports, remotecopy, hostsets, volumesets, vluns, flashcache, "
                            "users, roles, qos.\n"
                            "If you do not specify any value the first seven are used as default."),
                 )),
            ],
            optional_keys=["values"],
        ),
        forth=_special_agents_3par_transform_3par_add_verify_cert,
    )


# verify_cert was added with 1.5.0p1

rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:3par",
        title=lambda: _("3PAR Configuration"),
        valuespec=_valuespec_special_agents_3par,
    ))


def _valuespec_special_agents_storeonce():
    return Dictionary(
        title=_("HPE StoreOnce"),
        help=_("This rule set selects the special agent for HPE StoreOnce Applainces "
               "instead of the normal Check_MK agent and allows monitoring via Web API. "),
        optional_keys=["cert"],
        elements=[
            ("user", TextAscii(title=_("Username"), allow_empty=False)),
            ("password", Password(title=_("Password"), allow_empty=False)),
            ("cert",
             DropdownChoice(title=_("SSL certificate verification"),
                            choices=[
                                (True, _("Activate")),
                                (False, _("Deactivate")),
                            ])),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:storeonce",
        valuespec=_valuespec_special_agents_storeonce,
    ))


def _valuespec_special_agents_storeonce4x():
    return Dictionary(
        title=_("HPE StoreOnce via REST API 4.x"),
        help=_("This rule set selects the special agent for HPE StoreOnce Appliances "
               "instead of the normal Check_MK agent and allows monitoring via REST API v4.x or "
               "higher. "),
        optional_keys=["cert"],
        elements=[
            ("user", TextAscii(title=_("Username"), allow_empty=False)),
            ("password", Password(title=_("Password"), allow_empty=False)),
            ("cert",
             DropdownChoice(title=_("SSL certificate verification"),
                            choices=[
                                (True, _("Activate")),
                                (False, _("Deactivate")),
                            ])),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:storeonce4x",
        valuespec=_valuespec_special_agents_storeonce4x,
    ))


def _valuespec_special_agents_salesforce():
    return Dictionary(
        title=_("Salesforce"),
        help=_("This rule selects the special agent for Salesforce."),
        elements=[
            ("instances", ListOfStrings(
                title=_("Instances"),
                allow_empty=False,
            )),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        help_func=lambda: _("This rule selects the special agent for Salesforce."),
        name="special_agents:salesforce",
        title=lambda: _("Salesforce"),
        valuespec=_valuespec_special_agents_salesforce,
    ))


def _special_agents_azure_azure_explicit_config():
    return ListOf(
        Dictionary(
            elements=[
                ('group_name', TextAscii(
                    title=_('Name of the resource group'),
                    allow_empty=False,
                )),
                ('resources',
                 ListOfStrings(
                     title=_('Explicitly specify resources'),
                     allow_empty=False,
                 )),
            ],
            optional_keys=["resources"],
        ),
        title=_("explicitly specified groups"),
        allow_empty=False,
        add_label=_("Add resource group"),
    )


def _special_agents_azure_azure_tag_based_config():
    return ListOf(
        Tuple(
            orientation="horizontal",
            elements=[
                TextAscii(
                    title=_('The resource tag'),
                    allow_empty=False,
                ),
                CascadingDropdown(
                    orientation="horizontal",
                    choices=[
                        ('exists', _("exists")),
                        ('value', _("is"), TextUnicode(title=_('Tag value'), allow_empty=False)),
                    ],
                ),
            ],
        ),
        title=_('resources matching tag based criteria'),
        allow_empty=False,
        add_label=_("Add resource tag"),
    )


def _valuespec_special_agents_azure():
    return Dictionary(
        title=_("Microsoft Azure"),
        help=_("To monitor Azure resources add this datasource to <b>one</b> host. "
               "The data will be transported using the piggyback mechanism, so make "
               "sure to create one host for every monitored resource group. You can "
               "learn about the discovered groups in the <i>Azure Agent Info</i> "
               "service of the host owning the datasource program."),
        # element names starting with "--" will be passed do cmd line w/o parsing!
        elements=[
            ("subscription", TextAscii(
                title=_("Subscription ID"),
                allow_empty=False,
                size=45,
            )),
            ("tenant", TextAscii(
                title=_("Tenant ID / Directory ID"),
                allow_empty=False,
                size=45,
            )),
            ("client", TextAscii(
                title=_("Client ID / Application ID"),
                allow_empty=False,
                size=45,
            )),
            ("secret", Password(
                title=_("Client Secret"),
                allow_empty=False,
                size=45,
            )),
            (
                "config",
                Dictionary(
                    title=_("Retrieve information about..."),
                    # Since we introduced this, Microsoft has already reduced the number
                    # of allowed API requests. At the time of this writing (11/2018)
                    # you can find the number here:
                    # https://docs.microsoft.com/de-de/azure/azure-resource-manager/resource-manager-request-limits
                    help=_("By default, all resources associated to the configured tenant ID"
                           " will be monitored.") + " " +
                    _("However, since Microsoft limits API calls to %s per hour"
                      " (%s per minute), you can restrict the monitoring to individual"
                      " resource groups and resources.") % ("12000", "200"),
                    elements=[
                        ('explicit', _special_agents_azure_azure_explicit_config()),
                        ('tag_based', _special_agents_azure_azure_tag_based_config()),
                    ],
                )),
            ("piggyback_vms",
             DropdownChoice(
                 title=_("Map data relating to VMs"),
                 help=_("By default, data relating to a VM is sent to the group host"
                        " corresponding to the resource group of the VM, the same way"
                        " as for any other resource. If the VM is present in your "
                        " monitoring as a separate host, you can choose to send the data"
                        " to the VM itself."),
                 choices=[
                     ("grouphost", _("Map data to group host")),
                     ("self", _("Map data to the VM itself")),
                 ],
             )),
            ("sequential",
             DropdownChoice(
                 title=_("Force agent to run in single thread"),
                 help=_("Check this to turn off multiprocessing."
                        " Recommended for debugging purposes only."),
                 choices=[
                     (False, _("Run agent multithreaded")),
                     (True, _("Run agent in single thread")),
                 ],
             )),
        ],
        optional_keys=["piggyback_vms", "sequential"],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:azure",
        valuespec=_valuespec_special_agents_azure,
    ))


class MultisiteBiDatasource:
    def get_valuespec(self):
        return Dictionary(
            elements=self._get_dynamic_valuespec_elements(),
            optional_keys=["filter", "options", "assignments"],
        )

    def _get_dynamic_valuespec_elements(self):
        return [
            ("site",
             CascadingDropdown(choices=[
                 ("local", _("Connect to the local site")),
                 ("url", _("Connect to site url"),
                  HTTPUrl(help=_("URL of the remote site, for example https://10.3.1.2/testsite"))),
             ],
                               sorted=False,
                               orientation="horizontal",
                               title=_("Site connection"))),
            ("credentials",
             CascadingDropdown(
                 choices=[("automation", _("Use the credentials of the 'automation' user")),
                          ("configured", _("Use the following credentials"),
                           Tuple(elements=[
                               TextAscii(title=_("Automation Username"), allow_empty=True),
                               Password(title=_("Automation Secret"), allow_empty=True)
                           ],))],
                 help=_(
                     "Here you can configured the credentials to be used. Keep in mind that the <tt>automation</tt> user need "
                     "to exist if you choose this option"),
                 title=_("Login credentials"),
                 default_value="automation")),
            ("filter", self._vs_filters()),
            ("assignments", self._vs_aggregation_assignments()),
            ("options", self._vs_options()),
        ]

    def _vs_aggregation_assignments(self):
        return Dictionary(
            title=_("Aggregation assignment"),
            elements=[
                ("querying_host",
                 FixedValue("querying_host", totext="", title=_("Assign to the querying host"))),
                ("affected_hosts",
                 FixedValue("affected_hosts", totext="", title=_("Assign to the affected hosts"))),
                ("regex",
                 ListOf(
                     Tuple(
                         orientation="horizontal",
                         elements=[
                             RegExpUnicode(
                                 title=_("Regular expression"),
                                 help=_("Must contain at least one subgroup <tt>(...)</tt>"),
                                 mingroups=0,
                                 maxgroups=9,
                                 size=30,
                                 allow_empty=False,
                                 mode=RegExp.prefix,
                                 case_sensitive=False,
                             ),
                             TextUnicode(
                                 title=_("Replacement"),
                                 help=
                                 _("Use <tt>\\1</tt>, <tt>\\2</tt> etc. to replace matched subgroups"
                                  ),
                                 size=30,
                                 allow_empty=False,
                             )
                         ],
                     ),
                     title=_("Assign via regular expressions"),
                     help=
                     _("You can add any number of expressions here which are executed succesively until the first match. "
                       "Please specify a regular expression in the first field. This expression should at "
                       "least contain one subexpression exclosed in brackets - for example <tt>vm_(.*)_prod</tt>. "
                       "In the second field you specify the translated aggregation and can refer to the first matched "
                       "group with <tt>\\1</tt>, the second with <tt>\\2</tt> and so on, for example <tt>\\1.example.org</tt>. "
                       ""),
                     add_label=_("Add expression"),
                     movable=False,
                 )),
            ])

    def _vs_filters(self):
        return Dictionary(elements=[
            ("aggr_name_regex",
             ListOf(RegExp(mode=RegExp.prefix, title=_("Pattern")),
                    title=_("By regular expression"),
                    add_label=_("Add new pattern"),
                    movable=False)),
            ("aggr_groups",
             ListOf(DropdownChoice(choices=bi.aggregation_group_choices),
                    title=_("By aggregation groups"),
                    add_label=_("Add new group"),
                    movable=False)),
        ],
                          title=_("Filter aggregations"))

    def _vs_options(self):
        return Dictionary(
            elements=[
                ("state_scheduled_downtime",
                 MonitoringState(title=_("State, if BI aggregate is in scheduled downtime"))),
                ("state_acknowledged",
                 MonitoringState(title=_("State, if BI aggregate is acknowledged"))),
            ],
            optional_keys=["state_scheduled_downtime", "state_acknowledged"],
            title=_("Additional options"),
        )


def _valuespec_special_agents_bi():
    return ListOf(
        MultisiteBiDatasource().get_valuespec(),
        title=_("BI Aggregations"),
        help=_(
            "This rule allows you to check multiple BI aggregations from multiple sites at once. "
            "You can also assign aggregations to specific hosts through the piggyback mechanism."),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:bi",
        valuespec=_valuespec_special_agents_bi,
    ))


def _validate_aws_tags(value, varprefix):
    used_keys = []
    # KEY:
    # ve_p_services_p_ec2_p_choice_1_IDX_0
    # VALUES:
    # ve_p_services_p_ec2_p_choice_1_IDX_1_IDX
    for idx_tag, (tag_key, tag_values) in enumerate(value):
        tag_field = "%s_%s_0" % (varprefix, idx_tag + 1)
        if tag_key not in used_keys:
            used_keys.append(tag_key)
        else:
            raise MKUserError(tag_field,
                              _("Each tag must be unique and cannot be used multiple times"))
        if tag_key.startswith('aws:'):
            raise MKUserError(tag_field, _("Do not use 'aws:' prefix for the key."))
        if len(tag_key) > 128:
            raise MKUserError(tag_field, _("The maximum key length is 128 characters."))
        if len(tag_values) > 50:
            raise MKUserError(tag_field, _("The maximum number of tags per resource is 50."))

        for idx_values, v in enumerate(tag_values):
            values_field = "%s_%s_1_%s" % (varprefix, idx_tag + 1, idx_values + 1)
            if len(v) > 256:
                raise MKUserError(values_field, _("The maximum value length is 256 characters."))
            if v.startswith('aws:'):
                raise MKUserError(values_field, _("Do not use 'aws:' prefix for the values."))


def _vs_aws_tags(title):
    return ListOf(Tuple(help=_(
        "How to configure AWS tags please see "
        "https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/Using_Tags.html"),
                        orientation="horizontal",
                        elements=[
                            TextAscii(title=_("Key")),
                            ListOfStrings(title=_("Values"), orientation="horizontal")
                        ]),
                  add_label=_("Add new tag"),
                  movable=False,
                  title=title,
                  validate=_validate_aws_tags)


def _vs_element_aws_service_selection():
    return (
        'selection',
        CascadingDropdown(
            title=_("Selection of service instances"),
            help=_("<i>Gather all service instances and restrict by overall tags</i> means that "
                   "if overall tags are stated above then all service instances are filtered "
                   "by these tags. Otherwise all instances are gathered.<br>"
                   "With <i>Use explicit service tags and overwrite overall tags</i> you can "
                   "specify explicit tags for these services. The overall tags are ignored for "
                   "these services.<br>"
                   "<i>Use explicit service names and ignore overall tags</i>: With this selection "
                   "you can state explicit names. The overall tags are ignored for these service."),
            choices=[
                ('all', _("Gather all service instances and restrict by overall AWS tags")),
                ('tags', _("Use explicit AWS service tags and overrule overall AWS tags"),
                 _vs_aws_tags(_("AWS Tags"))),
                ('names', _("Use explicit service names and ignore overall AWS tags"),
                 ListOfStrings()),
            ]))


def _vs_element_aws_limits():
    return ("limits",
            FixedValue(True,
                       help=_("If limits are enabled all instances are fetched regardless of "
                              "possibly configured restriction to names or tags"),
                       title=_("Service limits"),
                       totext=_("Monitor service limits")))


def _transform_aws(d):
    services = d['services']
    if 'cloudwatch' in services:
        services['cloudwatch_alarms'] = services['cloudwatch']
        del services['cloudwatch']
    if 'assume_role' not in d:
        d['assume_role'] = {}
    return d


def _valuespec_special_agents_aws():
    return Transform(Dictionary(
        title=_('Amazon Web Services (AWS)'),
        elements=[
            ("access_key_id",
             TextAscii(
                 title=_("The access key ID for your AWS account"),
                 allow_empty=False,
                 size=50,
             )),
            ("secret_access_key",
             IndividualOrStoredPassword(
                 title=_("The secret access key for your AWS account"),
                 allow_empty=False,
             )),
            ("assume_role",
             Dictionary(
                 title=_("Assume a different IAM role"),
                 elements=[(
                     "role_arn_id",
                     Tuple(
                         title=_("Use STS AssumeRole to assume a different IAM role"),
                         elements=[
                             TextAscii(
                                 title=_("The ARN of the IAM role to assume"),
                                 size=50,
                                 help=_("The Amazon Resource Name (ARN) of the role to assume.")),
                             TextAscii(
                                 title=_("External ID (optional)"),
                                 size=50,
                                 help=
                                 _("A unique identifier that might be required when you assume a role in another "
                                   +
                                   "account. If the administrator of the account to which the role belongs provided "
                                   +
                                   "you with an external ID, then provide that value in the External ID parameter. "
                                  ))
                         ]))])),
            ("global_services",
             Dictionary(
                 title=_("Global services to monitor"),
                 elements=[("ce",
                            FixedValue(None,
                                       totext=_("Monitor costs and usage"),
                                       title=_("Costs and usage (CE)")))],
             )),
            ("regions",
             ListChoice(
                 title=_("Regions to use"),
                 choices=sorted(aws_constants.AWSRegions, key=lambda x: x[1]),
             )),
            ("services",
             Dictionary(
                 title=_("Services per region to monitor"),
                 elements=[
                     ("ec2",
                      Dictionary(
                          title=_("Elastic Compute Cloud (EC2)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("ebs",
                      Dictionary(
                          title=_("Elastic Block Storage (EBS)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("s3",
                      Dictionary(
                          title=_("Simple Storage Service (S3)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                              ("requests",
                               FixedValue(
                                   None,
                                   totext=_("Monitor request metrics"),
                                   title=_("Request metrics"),
                                   help=_("In order to monitor S3 request metrics you have to "
                                          "enable request metric monitoring in the AWS/S3 console. "
                                          "This is a paid feature"))),
                          ],
                          optional_keys=["limits", "requests"],
                          default_keys=["limits"],
                      )),
                     ("glacier",
                      Dictionary(
                          title=_("Amazon S3 Glacier (Glacier)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("elb",
                      Dictionary(
                          title=_("Classic Load Balancing (ELB)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("elbv2",
                      Dictionary(
                          title=_("Application and Network Load Balancing (ELBv2)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("rds",
                      Dictionary(
                          title=_("Relational Database Service (RDS)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("cloudwatch_alarms",
                      Dictionary(
                          title=_("CloudWatch Alarms"),
                          elements=[
                              ('alarms',
                               CascadingDropdown(title=_("Selection of alarms"),
                                                 choices=[
                                                     ('all', _("Gather all")),
                                                     ('names', _("Use explicit names"),
                                                      ListOfStrings()),
                                                 ])),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["alarms", "limits"],
                          default_keys=["alarms", "limits"],
                      )),
                     ("dynamodb",
                      Dictionary(
                          title=_("DynamoDB"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                          ],
                          optional_keys=["limits"],
                          default_keys=["limits"],
                      )),
                     ("wafv2",
                      Dictionary(
                          title=_("Web Application Firewall (WAFV2)"),
                          elements=[
                              _vs_element_aws_service_selection(),
                              _vs_element_aws_limits(),
                              ("cloudfront",
                               FixedValue(
                                   None,
                                   totext=_("Monitor CloudFront WAFs"),
                                   title=_("CloudFront WAFs"),
                                   help=_("Include WAFs in front of CloudFront resources in the "
                                          "monitoring"))),
                          ],
                          optional_keys=["limits", "cloudfront"],
                          default_keys=["limits", "cloudfront"],
                      )),
                 ],
                 default_keys=[
                     "ec2", "ebs", "s3", "glacier", "elb", "elbv2", "rds", "cloudwatch_alarms",
                     "dynamodb", "wafv2"
                 ],
             )),
            ("overall_tags",
             _vs_aws_tags(_("Restrict monitoring services by one of these AWS tags"))),
        ],
        optional_keys=["overall_tags"],
    ),
                     forth=_transform_aws)


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:aws",
        title=lambda: _("Amazon Web Services (AWS)"),
        valuespec=_valuespec_special_agents_aws,
    ))


def _factory_default_special_agents_vnx_quotas():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_vnx_quotas():
    return Dictionary(
        title=_("VNX quotas and filesystems"),
        elements=[
            ("user", TextAscii(title=_("NAS DB user name"))),
            ("password", Password(title=_("Password"))),
            ("nas_db", TextAscii(title=_("NAS DB path"))),
        ],
        optional_keys=[],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_vnx_quotas(),
        group=RulespecGroupDatasourceProgramsHardware,
        name="special_agents:vnx_quotas",
        valuespec=_valuespec_special_agents_vnx_quotas,
    ))


def _factory_default_special_agents_elasticsearch():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_elasticsearch():
    return Dictionary(
        optional_keys=["user", "password"],
        title=_("Elasticsearch"),
        help=_("Requests data about Elasticsearch clusters, nodes and indices."),
        elements=[
            ("hosts",
             ListOfStrings(
                 title=_("Hostnames to query"),
                 help=
                 _("Use this option to set which host should be checked by the special agent. If the "
                   "connection to the first server fails, the next server will be queried (fallback). "
                   "The check will only output data from the first host that sends a response."),
                 size=32,
                 allow_empty=False,
             )),
            ("user", TextAscii(title=_("Username"), size=32, allow_empty=True)),
            ("password", PasswordFromStore(
                title=_("Password of the user"),
                allow_empty=False,
            )),
            (
                "protocol",
                DropdownChoice(title=_("Protocol"),
                               choices=[
                                   ("http", "HTTP"),
                                   ("https", "HTTPS"),
                               ],
                               default_value="https"),
            ),
            ("port",
             Integer(
                 title=_("Port"),
                 help=_(
                     "Use this option to query a port which is different from standard port 9200."),
                 default_value=9200,
             )),
            (
                "infos",
                ListChoice(
                    title=_("Informations to query"),
                    help=_("Defines what information to query. "
                           "Checks for Cluster, Indices and Shard statistics follow soon."),
                    choices=[
                        ("cluster_health", _("Cluster health")),
                        ("nodes", _("Node statistics")),
                        ("stats", _("Cluster, Indices and Shard statistics")),
                    ],
                    default_value=["cluster_health", "nodes", "stats"],
                    allow_empty=False,
                ),
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_elasticsearch(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:elasticsearch",
        valuespec=_valuespec_special_agents_elasticsearch,
    ))


def _factory_default_special_agents_splunk():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_splunk():
    return Dictionary(
        title=_("Splunk"),
        help=_("Requests data from a Splunk instance."),
        optional_keys=["instance", "port"],
        elements=[
            ("instance",
             TextAscii(
                 title=_("Splunk instance to query."),
                 help=_("Use this option to set which host should be checked "
                        "by the special agent."),
                 size=32,
                 allow_empty=False,
             )),
            ("user", TextAscii(title=_("Username"), size=32, allow_empty=False)),
            ("password", PasswordFromStore(
                title=_("Password of the user"),
                allow_empty=False,
            )),
            (
                "protocol",
                DropdownChoice(title=_("Protocol"),
                               choices=[
                                   ("http", "HTTP"),
                                   ("https", "HTTPS"),
                               ],
                               default_value="https"),
            ),
            ("port",
             Integer(
                 title=_("Port"),
                 help=_(
                     "Use this option to query a port which is different from standard port 8089."),
                 default_value=8089,
             )),
            ("infos",
             ListChoice(
                 title=_("Informations to query"),
                 help=_("Defines what information to query. You can "
                        "choose to query license state and usage, Splunk "
                        "system messages, Splunk jobs, shown in the job "
                        "menu within Splunk. You can also query for "
                        "component health and fired alerts."),
                 choices=[
                     ("license_state", _("Licence state")),
                     ("license_usage", _("Licence usage")),
                     ("system_msg", _("System messages")),
                     ("jobs", _("Jobs")),
                     ("health", _("Health")),
                     ("alerts", _("Alerts")),
                 ],
                 default_value=[
                     "license_state", "license_usage", "system_msg", "jobs", "health", "alerts"
                 ],
                 allow_empty=False,
             )),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_splunk(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:splunk",
        valuespec=_valuespec_special_agents_splunk,
    ))


def _factory_default_special_agents_jenkins():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _transform_jenkins_infos(value):
    if "infos" in value:
        value["sections"] = value.pop("infos")
    return value


def _valuespec_special_agents_jenkins():
    return Transform(Dictionary(
        title=_("Jenkins jobs and builds"),
        help=_("Requests data from a jenkins instance."),
        optional_keys=["port"],
        elements=[
            ("instance",
             TextAscii(
                 title=_("Jenkins instance to query."),
                 help=_("Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "hostname here, eg. my_jenkins.com."),
                 size=32,
                 allow_empty=False,
             )),
            ("user",
             TextAscii(
                 title=_("Username"),
                 help=_("The username that should be used for accessing the "
                        "jenkins API. Has to have read permissions at least."),
                 size=32,
                 allow_empty=False,
             )),
            ("password",
             PasswordFromStore(
                 help=_("The password or API key of the user."),
                 title=_("Password of the user"),
                 allow_empty=False,
             )),
            (
                "protocol",
                DropdownChoice(title=_("Protocol"),
                               choices=[
                                   ("http", "HTTP"),
                                   ("https", "HTTPS"),
                               ],
                               default_value="https"),
            ),
            ("port",
             Integer(
                 title=_("Port"),
                 help=_(
                     "Use this option to query a port which is different from standard port 8080."),
                 default_value=443,
             )),
            ("sections",
             ListChoice(
                 title=_("Informations to query"),
                 help=_("Defines what information to query. You can choose "
                        "between the instance state, job states, node states "
                        "and the job queue."),
                 choices=[
                     ("instance", _("Instance state")),
                     ("jobs", _("Job state")),
                     ("nodes", _("Node state")),
                     ("queue", _("Queue info")),
                 ],
                 default_value=["instance", "jobs", "nodes", "queue"],
                 allow_empty=False,
             )),
        ],
    ),
                     forth=_transform_jenkins_infos)


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_jenkins(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:jenkins",
        valuespec=_valuespec_special_agents_jenkins,
    ))


def _factory_default_special_agents_zerto():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_zerto():
    return Dictionary(
        elements=[
            ("authentication",
             DropdownChoice(title=_('Authentication method'),
                            choices=[
                                ('windows', _('Windows authentication')),
                                ('vcenter', _('VCenter authentication')),
                            ],
                            help=_("Default is Windows authentication"))),
            ('username', TextAscii(title=_('Username'), allow_empty=False)),
            ('password', TextAscii(
                title=_('Password'),
                allow_empty=False,
            )),
        ],
        title=_("Zerto"),
        help=_("This rule selects the Zerto special agent for an existing Checkmk host"))


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:zerto",
        valuespec=_valuespec_special_agents_zerto,
    ))


def _factory_default_special_agents_graylog():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_graylog():
    return Dictionary(
        title=_("Graylog"),
        help=_("Requests node, cluster and indice data from a Graylog "
               "instance."),
        optional_keys=["port"],
        elements=[
            ("instance",
             TextAscii(
                 title=_("Graylog instance to query"),
                 help=_("Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "hostname here, eg. my_graylog.com."),
                 size=32,
                 allow_empty=False,
             )),
            ("user",
             TextAscii(
                 title=_("Username"),
                 help=_("The username that should be used for accessing the "
                        "Graylog API. Has to have read permissions at least."),
                 size=32,
                 allow_empty=False,
             )),
            ("password", PasswordFromStore(
                title=_("Password of the user"),
                allow_empty=False,
            )),
            ("protocol",
             DropdownChoice(
                 title=_("Protocol"),
                 choices=[
                     ("http", "HTTP"),
                     ("https", "HTTPS"),
                 ],
                 default_value="https",
             )),
            ("port",
             Integer(
                 title=_("Port"),
                 help=_(
                     "Use this option to query a port which is different from standard port 443."),
                 default_value=443,
             )),
            ("since",
             Age(
                 title=_("Time for coverage of failures"),
                 help=_("If you choose to query for failed index operations, use "
                        "this option to set the timeframe in which failures "
                        "should be covered. The check will output the total "
                        "number of failures and the number of failures in this "
                        "given timeframe."),
                 default_value=1800,
             )),
            ("sections",
             ListChoice(
                 title=_("Information to query"),
                 help=_("Defines what information to query."),
                 choices=[
                     ("alerts", _("Alarms")),
                     ("cluster_stats", _("Cluster statistics")),
                     ("cluster_traffic", _("Cluster traffic statistics")),
                     ("failures", _("Failed index operations")),
                     ("jvm", _("JVM heap size")),
                     ("license", _("License state")),
                     ("messages", _("Message count")),
                     ("nodes", _("Nodes")),
                     ("sidecars", _("Sidecars")),
                     ("sources", _("Sources")),
                     ("streams", _("Streams")),
                 ],
                 default_value=[
                     "alerts", "cluster_stats", "cluster_traffic", "failures", "jvm", "license",
                     "messages", "nodes", "sidecars", "sources", "streams"
                 ],
                 allow_empty=False,
             )),
            ("display_node_details",
             DropdownChoice(
                 title=_("Display node details on"),
                 help=_("The node details can be displayed either on the "
                        "queried host or the Graylog node."),
                 choices=[
                     ("host", _("The queried Graylog host")),
                     ("node", _("The Graylog node")),
                 ],
                 default_value="host",
             )),
            ("display_sidecar_details",
             DropdownChoice(
                 title=_("Display sidecar details on"),
                 help=_("The sidecar details can be displayed either on the "
                        "queried host or the sidecar host."),
                 choices=[
                     ("host", _("The queried Graylog host")),
                     ("sidecar", _("The sidecar host")),
                 ],
                 default_value="host",
             )),
            ("display_source_details",
             DropdownChoice(
                 title=_("Display source details on"),
                 help=_("The source details can be displayed either on the "
                        "queried host or the source host."),
                 choices=[
                     ("host", _("The queried Graylog host")),
                     ("source", _("The source host")),
                 ],
                 default_value="host",
             )),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_graylog(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:graylog",
        valuespec=_valuespec_special_agents_graylog,
    ))


def _valuespec_special_agents_couchbase():
    return Dictionary(
        title=_("Couchbase servers"),
        help=_("This rule allows to select a Couchbase server to monitor as well as "
               "configure buckets for further checks"),
        elements=[
            ("buckets",
             ListOfStrings(title=_("Bucket names"), help=_("Name of the Buckets to monitor."))),
            ("timeout",
             Integer(title=_("Timeout"),
                     default_value=10,
                     help=_("Timeout for requests in seconds."))),
            ("port",
             Integer(title=_("Port"),
                     default_value=8091,
                     help=_("The port that is used for the api call."))),
            ("authentication",
             Tuple(title=_("Authentication"),
                   help=_("The credentials for api calls with authentication."),
                   elements=[
                       TextAscii(title=_("Username"), allow_empty=False),
                       PasswordFromStore(title=_("Password of the user"), allow_empty=False)
                   ])),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=watolib.Rulespec.FACTORY_DEFAULT_UNUSED,
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:couchbase",
        valuespec=_valuespec_special_agents_couchbase,
    ))


def _factory_default_special_agents_jira():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _vs_jira_projects(title):
    return ListOf(
        Tuple(
            orientation="horizontal",
            elements=[
                TextAscii(
                    title=_("Project"),
                    help=_('Enter the full name of the '
                           'project here. You can find '
                           'the name in Jira within '
                           '"Projects" - "View all '
                           'projects" - column: "Project". '
                           'This field is case '
                           'insensitive'),
                    allow_empty=False,
                    regex="^[^']*$",
                    regex_error=_("Single quotes are not allowed here."),
                ),
                ListOfStrings(
                    title=_("Workflows"),
                    help=_('Enter the workflow name for the project here. E.g. "in progress".'),
                    valuespec=TextAscii(
                        allow_empty=False,
                        regex="^[^']*$",
                        regex_error=_("Single quotes are not allowed here."),
                    ),
                    orientation="horizontal",
                ),
            ],
        ),
        add_label=_("Add new project"),
        movable=False,
        title=title,
        validate=_validate_aws_tags,
    )


def _valuespec_special_agents_jira():
    return Dictionary(
        title=_("Jira statistics"),
        help=_("Use Jira Query Language (JQL) to get statistics out of your "
               "Jira instance."),
        elements=[
            ("instance",
             TextAscii(
                 title=_("Jira instance to query"),
                 help=_("Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "hostname here, eg. my_jira.com. If not set, the "
                        "assigned host is used as instance."),
                 size=32,
                 allow_empty=False,
             )),
            ("user",
             TextAscii(
                 title=_("Username"),
                 help=_("The username that should be used for accessing the "
                        "Jira API."),
                 size=32,
                 allow_empty=False,
             )),
            ("password", PasswordFromStore(
                title=_("Password of the user"),
                allow_empty=False,
            )),
            ("protocol",
             DropdownChoice(
                 title=_("Protocol"),
                 choices=[
                     ("http", "HTTP"),
                     ("https", "HTTPS"),
                 ],
                 default_value="https",
             )),
            (
                "project_workflows",
                _vs_jira_projects(
                    _("Monitor the number of issues for given projects and their "
                      "workflows. This results in a service for each project with "
                      "the number of issues per workflow."),),
            ),
            ("jql",
             ListOf(Dictionary(
                 elements=[
                     ("service_description",
                      TextAscii(
                          title=_('Service description: '),
                          help=_("The resulting service will get this entry as "
                                 "service description"),
                          allow_empty=False,
                      )),
                     (
                         "query",
                         TextAscii(
                             title=_('JQL query: '),
                             help=_('E.g. \'project = my_project and result = '
                                    '\"waiting for something\"\''),
                             allow_empty=False,
                             size=80,
                         ),
                     ),
                     ("result",
                      CascadingDropdown(
                          title=_("Type of result"),
                          help=_("Here you can define, what search result "
                                 "should be used. You can show the number of search "
                                 "results (count) or the summed up or average values "
                                 "of a given numeric field."),
                          choices=[
                              ('count', _("Number of "
                                          "search results")),
                              ('sum', _("Summed up values of "
                                        "the following numeric field:"),
                               Tuple(elements=[
                                   TextAscii(
                                       title=_("Field Name: "),
                                       allow_empty=False,
                                   ),
                                   Integer(
                                       title=_("Limit number of processed search results"),
                                       help=_("Here you can define, how many search results "
                                              "should be processed. The max. internal limit "
                                              "of Jira is 1000 results. If you want to "
                                              "ignore any limit, set -1 here. Default is 50."),
                                       default_value=50,
                                   ),
                               ],)),
                              ('average', _("Average value "
                                            "of the following numeric field: "),
                               Tuple(elements=[
                                   TextAscii(
                                       title=_("Field Name: "),
                                       allow_empty=False,
                                   ),
                                   Integer(
                                       title=_("Limit number of processed search results"),
                                       default_value=50,
                                   ),
                               ],)),
                          ],
                          sorted=False,
                      )),
                 ],
                 optional_keys=[],
             ),
                    title=_('Custom search query'))),
        ],
        optional_keys=[
            "jql",
            "project_workflows",
            "instance",
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_jira(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:jira",
        valuespec=_valuespec_special_agents_jira,
    ))


def _factory_default_special_agents_rabbitmq():
    # No default, do not use setting if no rule matches
    return watolib.Rulespec.FACTORY_DEFAULT_UNUSED


def _valuespec_special_agents_rabbitmq():
    return Dictionary(
        title=_("RabbitMQ"),
        help=_("Requests data from a RabbitMQ instance."),
        elements=[
            ("instance",
             TextAscii(
                 title=_("RabbitMQ instance to query"),
                 help=_("Use this option to set which instance should be "
                        "checked by the special agent. Please add the "
                        "hostname here, eg. my_rabbitmq.com. If not set, the "
                        "assigned host is used as instance."),
                 size=32,
                 allow_empty=False,
             )),
            ("user",
             TextAscii(
                 title=_("Username"),
                 help=_("The username that should be used for accessing the "
                        "RabbitMQ API."),
                 size=32,
                 allow_empty=False,
             )),
            ("password", PasswordFromStore(
                title=_("Password of the user"),
                allow_empty=False,
            )),
            ("protocol",
             DropdownChoice(
                 title=_("Protocol"),
                 choices=[
                     ("http", "HTTP"),
                     ("https", "HTTPS"),
                 ],
                 default_value="https",
             )),
            ("port",
             Integer(
                 title=_("Port"),
                 default_value=15672,
                 help=_("The port that is used for the api call."),
             )),
            ("sections",
             ListChoice(
                 title=_("Informations to query"),
                 help=_("Defines what information to query. You can choose "
                        "between the cluster, nodes, vhosts and queues."),
                 choices=[
                     ("cluster", _("Clusterwide")),
                     ("nodes", _("Nodes")),
                     ("vhosts", _("Vhosts")),
                     ("queues", _("Queues")),
                 ],
                 default_value=["cluster", "nodes", "vhosts", "queues"],
                 allow_empty=False,
             )),
        ],
        optional_keys=[
            "instance",
            "port",
        ],
    )


rulespec_registry.register(
    HostRulespec(
        factory_default=_factory_default_special_agents_rabbitmq(),
        group=RulespecGroupDatasourceProgramsApps,
        name="special_agents:rabbitmq",
        valuespec=_valuespec_special_agents_rabbitmq,
    ))
