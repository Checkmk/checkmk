#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    MonitoringState,
    TextAscii,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    register_check_parameters,
)

register_check_parameters(
    RulespecGroupCheckParametersApplications, "oracle_sql", _("Oracle Custom SQLs"),
    Dictionary(elements=[
        ("instance_error_state", MonitoringState(title=_("Instance error state"))),
        ("perfdata_error_state", MonitoringState(title=_("Perfdata error state"))),
    ],), TextAscii(title=_("Custom SQL")), "dict")
