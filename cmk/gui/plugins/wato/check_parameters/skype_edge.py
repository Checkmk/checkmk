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
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _item_spec_skype_edge():
    return TextInput(
        title=_("Interface"),
        help=_("The name of the interface (Public/Private IPv4/IPv6 Network Interface)"),
    )


def _parameter_valuespec_skype_edge():
    return Dictionary(
        elements=[
            (
                "authentication_failures",
                Dictionary(
                    title=_("Authentication Failures"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Integer(
                                        title=_("Warning at"),
                                        unit=_("per second"),
                                        default_value=20,
                                    ),
                                    Integer(
                                        title=_("Critical at"),
                                        unit=_("per second"),
                                        default_value=40,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "allocate_requests_exceeding",
                Dictionary(
                    title=_("Allocate Requests Exceeding Port Limit"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Integer(
                                        title=_("Warning at"),
                                        unit=_("per second"),
                                        default_value=20,
                                    ),
                                    Integer(
                                        title=_("Critical at"),
                                        unit=_("per second"),
                                        default_value=40,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
            (
                "packets_dropped",
                Dictionary(
                    title=_("Packets Dropped"),
                    elements=[
                        (
                            "upper",
                            Tuple(
                                elements=[
                                    Integer(
                                        title=_("Warning at"),
                                        unit=_("per second"),
                                        default_value=200,
                                    ),
                                    Integer(
                                        title=_("Critical at"),
                                        unit=_("per second"),
                                        default_value=400,
                                    ),
                                ],
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="skype_edge",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_skype_edge,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_skype_edge,
        title=lambda: _("Skype for Business Edge"),
    )
)
