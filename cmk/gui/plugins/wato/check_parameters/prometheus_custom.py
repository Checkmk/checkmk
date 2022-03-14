#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, ListOf, TextInput, Tuple


def _parameter_valuespec_prometheus_custom():
    return Dictionary(
        elements=[
            (
                "metric_list",
                ListOf(
                    valuespec=Dictionary(
                        elements=[
                            (
                                "metric_label",
                                TextInput(
                                    title=_("Metric label"),
                                    allow_empty=False,
                                    help=_(
                                        "The defined levels will only apply if the metric label matches the one "
                                        "specified in the custom Prometheus service."
                                    ),
                                ),
                            ),
                            (
                                "levels",
                                Dictionary(
                                    elements=[
                                        (
                                            "lower_levels",
                                            Tuple(
                                                title=_("Lower levels"),
                                                elements=[
                                                    Float(title=_("Warning below")),
                                                    Float(title=_("Critical below")),
                                                ],
                                            ),
                                        ),
                                        (
                                            "upper_levels",
                                            Tuple(
                                                title=_("Upper levels"),
                                                elements=[
                                                    Float(title=_("Warning at")),
                                                    Float(title=_("Critical at")),
                                                ],
                                            ),
                                        ),
                                    ],
                                    validate=_verify_empty,
                                ),
                            ),
                        ],
                        optional_keys=[],
                    ),
                    title=_("Metric levels"),
                    add_label=_("Add metric level"),
                    allow_empty=False,
                    help=_(
                        "Specify upper and/or lower levels for a queried PromQL value. The matching happens "
                        "on a 2-level basis: First on the service description level where the regular "
                        "expression allows to target multiple services at once. Specify the regular "
                        "expression in the Conditions section below. A service can consist of multiple "
                        "metrics and you can add levels to each queried metric value. For the relevant "
                        "service, levels to the metric value will only apply if the metric label matches "
                        "the label specified in the custom Prometheus service definition. Levels for the "
                        "Prometheus custom check can be defined at two places: in the Prometheus Datasource "
                        "rule and here. The ruleset here always has priority over the levels defined in the "
                        "Datasource rule."
                    ),
                ),
            ),
        ],
        optional_keys=[],
        title=_("Levels for Prometheus services"),
        help=_(
            "This rule allows you to configure levels for the Prometheus custom check targeting "
            "specific service metric values"
        ),
    )


def _item_spec_custom_service():
    return TextInput(
        title=_("Prometheus custom service"),
        help=_("Name of the custom service"),
    )


def _verify_empty(value, varprefix):
    if not value:
        raise MKUserError(varprefix, _("Please specify at least one type of levels"))


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="prometheus_custom",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_custom_service,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_prometheus_custom,
        title=lambda: _("Prometheus custom services"),
    )
)
