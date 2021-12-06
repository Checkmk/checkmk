#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Age, CascadingDropdown, Dictionary, MonitoringState, Tuple


def _parameter_valuespec_kube_pod_resources(help_text: str):
    return Dictionary(
        elements=[
            (
                "pending",
                CascadingDropdown(
                    title=_("Define levels for pending pods"),
                    choices=[
                        (
                            "no_levels",
                            _("No levels"),
                            None,
                        ),
                        (
                            "levels",
                            _("Impose levels"),
                            Tuple(
                                elements=[
                                    Age(title=_("Warning after"), default_value=300),
                                    Age(title=_("Critical after"), default_value=600),
                                ],
                            ),
                        ),
                    ],
                    default_value="no_levels",
                ),
            ),
            (
                "unknown",
                MonitoringState(
                    title=_("Set state for unknown pods"),
                    default_value=3,
                ),
            ),
        ],
        help=help_text,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_pod_resources",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=lambda: _parameter_valuespec_kube_pod_resources(
            _(
                "According to the Kubernetes docs, the phase of a Pod is a simple, high-level "
                "summary of where the Pod is in its lifecycle. The phase is not intended to be a "
                "comprehensive rollup of observations of container or Pod state, nor is it intended"
                " to be a comprehensive state machine. For the pending pods, the check keeps track "
                "for how long they have been pending. If a tolerating time period is set, the "
                "service goes WARN/CRIT after any of the pods has been pending for longer than the "
                "set duration. If there is at least one unknown pod, the service goes UNKNOWN by "
                "default. The state the service goes can be configured. This rule affects any Pod "
                "Resources service, except for those on the Nodes and the Clusters. The "
                "configuration for Clusters and Nodes can be done via the rule Kubernetes Pod "
                "Resources: Clusters, Nodes."
            )
        ),
        title=lambda: _("Kubernetes Pod Resources: Deployments"),
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_pod_resources_with_capacity",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=lambda: _parameter_valuespec_kube_pod_resources(
            _(
                "According to the Kubernetes docs, the phase of a Pod is a simple, high-level "
                "summary of where the Pod is in its lifecycle. The phase is not intended to be a "
                "comprehensive rollup of observations of container or Pod state, nor is it intended"
                " to be a comprehensive state machine. For the pending pods, the check keeps track "
                "for how long they have been pending. If a tolerating time period is set, the "
                "service goes WARN/CRIT after any of the pods has been pending for longer than the "
                "set duration. If there is at least one unknown pod, the service goes UNKNOWN by "
                "default. The state the service goes can be configured. This rule affects the Pod"
                "Resources services of Kubernetes Nodes and Kubernetes Clusters. The configuration"
                " of other Pod Resources services can be done via the rule Kubernetes Pod "
                "Resources: Deployments."
            )
        ),
        title=lambda: _("Kubernetes Pod Resources: Clusters, Nodes"),
    )
)
