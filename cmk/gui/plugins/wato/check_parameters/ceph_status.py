#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.plugins.wato.check_parameters.ceph_mgrs import ceph_epoch_element

rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="ceph_status",
        group=RulespecGroupCheckParametersStorage,
        match_type="dict",
        parameter_valuespec=lambda: Dictionary(elements=ceph_epoch_element(
            _("Status epoch levels and average")),),
        title=lambda: _("Ceph Status"),
    ))
