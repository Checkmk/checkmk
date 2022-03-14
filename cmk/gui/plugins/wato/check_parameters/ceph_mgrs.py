#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Float, Integer, Tuple


def ceph_epoch_element(title):
    return [
        (
            "epoch",
            Tuple(
                title=title,
                elements=[
                    Float(title=_("Warning at")),
                    Float(title=_("Critical at")),
                    Integer(title=_("Average interval"), unit=_("minutes")),
                ],
            ),
        )
    ]


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ceph_mgrs",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=lambda: Dictionary(
            elements=ceph_epoch_element(_("MGRs epoch levels and average")),
        ),
        title=lambda: _("Ceph MGRs"),
    )
)
