#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from typing import Literal

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.kube import wrap_with_no_levels_dropdown
from cmk.gui.plugins.wato.check_parameters.memory_arbor import UsedSize
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import CascadingDropdown, Dictionary, Float, Percentage, Tuple


def valuespec_percentual(title: str, maxvalue: None | float = 101.0) -> CascadingDropdown:
    return wrap_with_no_levels_dropdown(
        title=title,
        value_spec=Tuple(
            elements=[
                Percentage(title=_("Warning at"), default_value=80.0, maxvalue=None),
                Percentage(title=_("Critical at"), default_value=90.0, maxvalue=None),
            ]
        ),
    )


def _parameter_valuespec_memory(
    valuespec_help: str,
    options: Sequence[Literal["usage", "request", "request_lower", "limit", "cluster", "node"]] = (
        "usage",
        "request",
        "request_lower",
        "limit",
        "cluster",
        "node",
    ),
) -> Dictionary:
    elements = []
    if "usage" in options:
        elements.append(
            (
                "usage",
                wrap_with_no_levels_dropdown(
                    title=_("Upper levels for usage"), value_spec=UsedSize()
                ),
            )
        )
    if "request" in options:
        elements.append(
            (
                "request",
                valuespec_percentual(
                    title=_("Upper levels for requests utilization"), maxvalue=None
                ),
            )
        )

    for option, help_text in (
        ("request_lower", _("Lower levels for requests utilization")),
        ("limit", _("Upper levels for limits utilization")),
        ("cluster", _("Upper levels for cluster utilization")),
        ("node", _("Upper levels for node utilization")),
    ):
        if option in options:
            elements.append(
                (
                    option,
                    valuespec_percentual(title=help_text),
                )
            )

    return Dictionary(
        help=valuespec_help,
        title=_("Memory"),
        elements=elements,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_memory",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=lambda: _parameter_valuespec_memory(
            valuespec_help=_(
                "Here you can configure levels for usage, requests "
                "utilization, limits utilization and node utilization, respectively."
            )
        ),
        title=lambda: _("Kubernetes memory resource utilization"),
    )
)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_resource_quota_memory",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=lambda: _parameter_valuespec_memory(
            valuespec_help=_(
                "Here you can configure levels for usage, requests "
                "utilization and limits utilization, respectively."
            ),
            options=["usage", "request", "request_lower", "limit"],
        ),
        title=lambda: _("Kubernetes resource quota memory utilization"),
    )
)


def _parameter_valuespec_cpu(
    valuespec_help: str,
    options: Sequence[Literal["usage", "request", "request_lower", "limit", "cluster", "node"]] = (
        "usage",
        "request",
        "request_lower",
        "limit",
        "cluster",
        "node",
    ),
) -> Dictionary:
    elements = []
    if "usage" in options:
        elements.append(
            (
                "usage",
                wrap_with_no_levels_dropdown(
                    title=_("Upper levels for usage"),
                    value_spec=Tuple(
                        elements=[
                            Float(title=_("Warning at"), default_value=0.5),
                            Float(title=_("Critical at"), default_value=1.0),
                        ]
                    ),
                ),
            )
        )
    if "request" in options:
        elements.append(
            (
                "request",
                valuespec_percentual(
                    title=_("Upper levels for requests utilization"), maxvalue=None
                ),
            )
        )

    for option, help_text in (
        ("request_lower", _("Lower levels for requests utilization")),
        ("limit", _("Upper levels for limits utilization")),
        ("cluster", _("Upper levels for cluster utilization")),
        ("node", _("Upper levels for node utilization")),
    ):
        if option in options:
            elements.append(
                (
                    option,
                    valuespec_percentual(title=help_text),
                )
            )

    return Dictionary(
        help=valuespec_help,
        title=_("CPU"),
        elements=elements,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_cpu",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=lambda: _parameter_valuespec_cpu(
            valuespec_help=_(
                "Here you can configure levels for usage, requests "
                "utilization, limits utilization and node utilization, respectively."
            )
        ),
        title=lambda: _("Kubernetes CPU resource utilization"),
    )
)


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_resource_quota_cpu",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        parameter_valuespec=lambda: _parameter_valuespec_cpu(
            valuespec_help=_(
                "Here you can configure levels for usage, requests "
                "utilization and limits utilization, respectively."
            ),
            options=["usage", "request", "request_lower", "limit"],
        ),
        title=lambda: _("Kubernetes resource quota cpu utilization"),
    )
)
