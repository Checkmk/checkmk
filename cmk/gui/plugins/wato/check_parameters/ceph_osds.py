#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.ceph_mgrs import ceph_epoch_element
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Percentage, Tuple


def _parameter_valuespec_ceph_osds():
    return Dictionary(
        elements=[
            (
                "num_out_osds",
                Tuple(
                    title=_("Upper levels for number of OSDs which are out"),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "num_down_osds",
                Tuple(
                    title=_("Upper levels for number of OSDs which are down"),
                    elements=[
                        Percentage(title=_("Warning at")),
                        Percentage(title=_("Critical at")),
                    ],
                ),
            ),
        ]
        + ceph_epoch_element(_("OSDs epoch levels and average")),
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ceph_osds",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_ceph_osds,
        title=lambda: _("Ceph OSDs"),
    )
)
