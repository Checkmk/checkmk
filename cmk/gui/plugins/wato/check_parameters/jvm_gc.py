#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, Percentage, TextInput, Transform, Tuple


def _item_spec_jvm_gc():
    return TextInput(
        title=_("Name of the virtual machine and/or<br>garbage collection type"),
        help=_("The name of the application server"),
        allow_empty=False,
    )


def transform_units(params):
    """transform 1/min to 1/s and ms/min to %"""
    if "CollectionTime" in params:
        ms_per_min = params.pop("CollectionTime")
        params["collection_time"] = (ms_per_min[0] / 600.0, ms_per_min[1] / 600.0)
    if "CollectionCount" in params:
        count_rate_per_min = params.pop("CollectionCount")
        params["collection_count"] = (count_rate_per_min[0] / 60.0, count_rate_per_min[1] / 60.0)
    return params


def _parameter_valuespec_jvm_gc():
    return Transform(
        valuespec=Dictionary(
            help=_("This ruleset also covers Tomcat, Jolokia and JMX. "),
            elements=[
                (
                    "collection_time",
                    Tuple(
                        title=_("Time spent collecting garbage in percent"),
                        elements=[
                            Percentage(title=_("Warning at")),
                            Percentage(title=_("Critical at")),
                        ],
                    ),
                ),
                (
                    "collection_count",
                    Tuple(
                        title=_("Count of garbage collections per second"),
                        elements=[
                            Float(title=_("Warning at")),
                            Float(title=_("Critical at")),
                        ],
                    ),
                ),
            ],
        ),
        forth=transform_units,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="jvm_gc",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_jvm_gc,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_jvm_gc,
        title=lambda: _("JVM garbage collection levels"),
    )
)
