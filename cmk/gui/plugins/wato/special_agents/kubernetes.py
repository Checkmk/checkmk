#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

###########################################################################
# NOTE: This special agent is deprecated and will be
#       removed in Checkmk version 2.2.
###########################################################################

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.special_agents.common import (
    filter_kubernetes_namespace_element,
    RulespecGroupVMCloudContainer,
)
from cmk.gui.plugins.wato.utils import HostRulespec, IndividualOrStoredPassword, rulespec_registry
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Dictionary,
    FixedValue,
    Integer,
    ListChoice,
    TextInput,
    Transform,
)


def _transform_kubernetes_connection_params(value):
    """Check_mk version 2.0: rework input of connection paramters to improve intuitive use.
    Note that keys are removed from the parameters dictionary!
    """
    if "url-prefix" in value:
        # it is theoretically possible that a customer has split up the custom URL into
        # base URL, port and path prefix in their rule.
        url_suffix = ""
        port = value.pop("port", None)
        if port:
            url_suffix += f":{port}"
        path_prefix = value.pop("path-prefix", None)
        if path_prefix:
            url_suffix += f"/{path_prefix}"
        return "url_custom", value.pop("url-prefix") + url_suffix

    return "ipaddress", {k: value.pop(k) for k in ["port", "path-prefix"] if k in value}


def special_agents_kubernetes_transform(value):
    if "infos" not in value:
        value["infos"] = ["nodes"]
    if "no-cert-check" not in value:
        value["no-cert-check"] = False
    if "namespaces" not in value:
        value["namespaces"] = False

    if "api-server-endpoint" in value:
        return value

    value["api-server-endpoint"] = _transform_kubernetes_connection_params(value)

    return value


def _kubernetes_connection_elements():
    return [
        (
            "port",
            Integer(
                title=_("Port"),
                help=_("If no port is given, a default value of 443 will be used."),
                default_value=443,
            ),
        ),
        (
            "path-prefix",
            TextInput(
                title=_("Custom path prefix"),
                help=_(
                    "Specifies a URL path prefix, which is prepended to API calls "
                    "to the Kubernetes API. This is a useful option for Rancher "
                    "installations (more information can be found in the manual). "
                    "If this option is not relevant for your installation, "
                    "please leave it unchecked."
                ),
                allow_empty=False,
            ),
        ),
    ]


def _valuespec_special_agents_kubernetes():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "api-server-endpoint",
                    CascadingDropdown(
                        choices=[
                            (
                                "hostname",
                                _("Hostname"),
                                Dictionary(elements=_kubernetes_connection_elements()),
                            ),
                            (
                                "ipaddress",
                                _("IP address"),
                                Dictionary(elements=_kubernetes_connection_elements()),
                            ),
                            (
                                "url_custom",
                                _("Custom URL"),
                                TextInput(
                                    allow_empty=False,
                                    size=80,
                                ),
                            ),
                        ],
                        orientation="horizontal",
                        title=_("API server endpoint"),
                        help=_(
                            'The URL that will be contacted for Kubernetes API calls. If the "Hostname" '
                            'or the "IP Address" options are selected, the DNS hostname or IP address and '
                            "a secure protocol (HTTPS) are used."
                        ),
                    ),
                ),
                (
                    "token",
                    IndividualOrStoredPassword(
                        title=_("Token"),
                        allow_empty=False,
                    ),
                ),
                (
                    "no-cert-check",
                    Alternative(
                        title=_("SSL certificate verification"),
                        elements=[
                            FixedValue(value=False, title=_("Verify the certificate"), totext=""),
                            FixedValue(
                                value=True,
                                title=_("Ignore certificate errors (unsecure)"),
                                totext="",
                            ),
                        ],
                        default_value=False,
                    ),
                ),
                (
                    "namespaces",
                    Alternative(
                        title=_("Namespace prefix for hosts"),
                        elements=[
                            FixedValue(
                                value=False, title=_("Don't use a namespace prefix"), totext=""
                            ),
                            FixedValue(value=True, title=_("Use a namespace prefix"), totext=""),
                        ],
                        help=_(
                            "If a cluster uses multiple namespaces you need to activate this option. "
                            "Hosts for namespaced Kubernetes objects will then be prefixed with the "
                            "name of their namespace. This makes Kubernetes resources in different "
                            "namespaces that have the same name distinguishable, but results in "
                            "longer hostnames."
                        ),
                        default_value=False,
                    ),
                ),
                (
                    "infos",
                    ListChoice(
                        choices=[
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
                        title=_("Retrieve information about..."),
                    ),
                ),
                filter_kubernetes_namespace_element(),
            ],
            optional_keys=["port", "url-prefix", "path-prefix", "namespace_include_patterns"],
            title=_("Kubernetes (deprecated)"),
            help=_(
                "This special agent is deprecated and will be removed in "
                'Checkmk version 2.2.0. Please use the "Kubernetes" ruleset to '
                "configure the new special agent for Kubernetes."
            ),
        ),
        forth=special_agents_kubernetes_transform,
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupVMCloudContainer,
        name="special_agents:kubernetes",
        valuespec=_valuespec_special_agents_kubernetes,
        is_deprecated=True,
    )
)
