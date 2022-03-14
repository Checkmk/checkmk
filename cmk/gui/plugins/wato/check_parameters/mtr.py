#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersNetworking,
)
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Transform, Tuple


def _item_spec_mtr():
    return TextInput(
        title=_("MTR destination"),
        help=_("Specify the name of the destination host, i.e. <tt>checkmk.com</tt>"),
        allow_empty=False,
    )


def _transform_mtr_params(p):
    if "avg" in p:
        p["rta"] = p.pop("avg")
    if "stddev" in p:
        p["rtstddev"] = p.pop("stddev")
    if "loss" in p:
        p["pl"] = p.pop("loss")
    return p


def _parameter_valuespec_mtr():
    return Transform(
        valuespec=Dictionary(
            help=_(
                "This ruleset can be used to change MTR's (Matt's traceroute) warning and crit levels for packet loss, average "
                "roundtrip and standard deviation."
            ),
            elements=[
                (
                    "rta",
                    Tuple(
                        title=_("Average roundtrip time in ms"),
                        elements=[
                            Integer(
                                title=_("Warning at"), default_value=150, unit=_("ms"), minvalue=0
                            ),
                            Integer(
                                title=_("Critical at"), default_value=250, unit=_("ms"), minvalue=0
                            ),
                        ],
                        help=_(
                            "The maximum average roundtrip time in ms before this service goes into warning/critical. "
                            "This alarm only applies to the target host, not the hops in between."
                        ),
                    ),
                ),
                (
                    "rtstddev",
                    Tuple(
                        title=_("Standard deviation of roundtrip times in ms"),
                        elements=[
                            Integer(
                                title=_("Warning at"), default_value=150, unit=_("ms"), minvalue=0
                            ),
                            Integer(
                                title=_("Critical at"), default_value=250, unit=_("ms"), minvalue=0
                            ),
                        ],
                        help=_(
                            "The maximum standard deviation on the roundtrip time in ms before this service goes into"
                            "warning/critical. This alarm only applies to the target host, not the hops in between."
                        ),
                    ),
                ),
                (
                    "pl",
                    Tuple(
                        title=_("Packet loss in percentage"),
                        elements=[
                            Integer(
                                title=_("Warning at"), default_value=10, unit=_("%"), minvalue=0
                            ),
                            Integer(
                                title=_("Critical at"), default_value=25, unit=_("%"), minvalue=0
                            ),
                        ],
                        help=_(
                            "The maximum allowed percentage of packet loss to the destination before this service "
                            "goes into warning/critical."
                        ),
                    ),
                ),
            ],
            optional_keys=False,
        ),
        forth=_transform_mtr_params,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mtr",
        group=RulespecGroupCheckParametersNetworking,
        item_spec=_item_spec_mtr,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mtr,
        title=lambda: _("Traceroute with MTR"),
    )
)
