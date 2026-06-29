#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.kube import wrap_with_no_levels_dropdown
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, DictionaryEntry, Integer, ListOfStrings, TextInput, Tuple


def __levels(key: str, title_upper: str | None, title_lower: str | None) -> list[DictionaryEntry]:
    return [
        (
            key + "_levels_upper",
            wrap_with_no_levels_dropdown(
                title_upper,
                Tuple(
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
        ),
        (
            key + "_levels_lower",
            wrap_with_no_levels_dropdown(
                title_lower,
                Tuple(
                    elements=[
                        Integer(title=_("Warning below")),
                        Integer(title=_("Critical below")),
                    ],
                ),
            ),
        ),
    ]


def __control_plane_roles() -> list[DictionaryEntry]:
    return [
        (
            "control_plane_roles",
            ListOfStrings(
                title=_("Specify roles of a control plane node"),
                valuespec=TextInput(size=80),
                default_value=["master", "control-plane"],
                help=_(
                    "If a node has any of these roles, then it is considered a control plane "
                    "node by Checkmk. A control plane might in some cases also be a worker node."
                ),
            ),
        ),
    ]


def __worker_node_roles() -> list[DictionaryEntry]:
    return [
        (
            "worker_node_roles",
            ListOfStrings(
                title=_("Specify roles of a worker node"),
                valuespec=TextInput(size=80),
                default_value=["worker"],
                help=_(
                    "If a node has any of these roles, then it is considered a worker "
                    "node by Checkmk. A worker node might in some cases also be a control "
                    "plane node. Some Kubernetes distributions automatically assign a role "
                    "such as 'worker' to worker nodes. If yours does not and you have nodes "
                    "that are both control plane and worker nodes, you can assign them a "
                    "role and ensure it is in this list to make Checkmk count the node as "
                    "both roles. Nodes without a control plane role (specified above) are "
                    "automatically counted as worker nodes."
                ),
            ),
        ),
    ]


def _parameter_valuespec_kube_node_count() -> Dictionary:
    return Dictionary(
        elements=__control_plane_roles()
        + __worker_node_roles()
        + __levels(
            "worker",
            _("Maximum number of ready worker nodes"),
            _("Minimum number of ready worker nodes"),
        )
        + __levels(
            "control_plane",
            _("Maximum number of ready control plane nodes"),
            _("Minimum number of ready control plane nodes"),
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_node_count",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_kube_node_count,
        title=lambda: _("Kubernetes node count"),
    )
)
