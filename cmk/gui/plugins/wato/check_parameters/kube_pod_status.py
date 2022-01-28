#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List, Literal, NamedTuple, Sequence, Tuple

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.kube import valuespec_age
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import CascadingDropdown, Dictionary

CONTAINER_STATUSES = [
    "CreateContainerConfigError",
    "ErrImagePull",
    "Error",
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "OOMKilled",
]

INIT_STATUSES = [f"Init:{status}" for status in CONTAINER_STATUSES]

DESIRED_PHASE = [
    "Running",
    "Succeded",
]

UNDESIRED_PHASE = [
    "Pending",
    "Failed",
    "Unknown",
]


class Section(NamedTuple):
    options: Sequence[str]
    default_choice: Literal["no_levels", "levels"]


def _parameter_valuespec_kube_pod_status(sections: Sequence[Section]):
    elements: List[Tuple[str, CascadingDropdown]] = []
    for options, default_choice in sections:
        elements.extend(
            (option, valuespec_age(option, default_choice=default_choice)) for option in options
        )
    elements.append(
        (
            "other",
            valuespec_age(title="Define levels for remaining statuses", default_choice="no_levels"),
        )
    )

    return lambda: Dictionary(
        title=_("Interpretation of pod status"),
        help=_(
            "Map the Kubernetes pod status shown in the summary to an upper level of its age. "
            "In order the configure pod statuses not within the list below, use the 'Other' option."
        ),
        elements=elements,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="kube_pod_status",
        group=RulespecGroupCheckParametersApplications,
        parameter_valuespec=_parameter_valuespec_kube_pod_status(
            [
                Section(options=CONTAINER_STATUSES, default_choice="levels"),
                Section(options=INIT_STATUSES, default_choice="levels"),
                Section(options=DESIRED_PHASE, default_choice="no_levels"),
                Section(options=UNDESIRED_PHASE, default_choice="levels"),
            ]
        ),
        title=lambda: _("Kubernetes pod status"),
    )
)
