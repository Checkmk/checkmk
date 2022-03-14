#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Alternative, Dictionary, FixedValue, Integer, TextInput, Tuple


def _item_spec_ibm_svc_enclosure():
    return TextInput(
        title=_("Name of enclosure"),
        help=_("Name of the enclosure, e.g. Enclosure 1"),
    )


def _parameter_valuespec_ibm_svc_enclosure():
    return Dictionary(
        elements=[
            (
                "levels_lower_online_canisters",
                Alternative(
                    title="Lower levels for online canisters",
                    elements=[
                        FixedValue(
                            value=False,
                            title=_("All must be online"),
                            totext="",
                        ),
                        Tuple(
                            title=_("Specify levels"),
                            elements=[
                                Integer(
                                    title=_("Warning below"),
                                    minvalue=-1,
                                    unit=_("online canisters"),
                                ),
                                Integer(
                                    title=_("Critical below"),
                                    minvalue=-1,
                                    unit=_("online canisters"),
                                ),
                            ],
                        ),
                    ],
                ),
            )
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="ibm_svc_enclosure",
        group=RulespecGroupCheckParametersStorage,
        item_spec=_item_spec_ibm_svc_enclosure,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ibm_svc_enclosure,
        title=lambda: _("IBM SVC Enclosure"),
    )
)
