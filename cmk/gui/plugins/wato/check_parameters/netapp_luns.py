#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    Checkbox,
    Dictionary,
    FixedValue,
    Integer,
    Optional,
    Percentage,
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.plugins.wato.check_parameters.utils import (
    get_free_used_dynamic_valuespec,
    match_dual_level_type,
    transform_filesystem_free,
)


def _parameter_valuespec_netapp_luns():
    return Dictionary(
        title=_("Configure levels for used space"),
        elements=[
            ("ignore_levels",
             FixedValue(
                 title=_("Ignore used space (this option disables any other options)"),
                 help=_(
                     "Some luns, e.g. jfs formatted, tend to report incorrect used space values"),
                 totext=_("Ignore used space"),
                 value=True,
             )),
            ("levels",
             Alternative(
                 title=_("Levels for LUN"),
                 show_alternative_title=True,
                 default_value=(80.0, 90.0),
                 match=match_dual_level_type,
                 elements=[
                     get_free_used_dynamic_valuespec("used", "LUN"),
                     Transform(
                         get_free_used_dynamic_valuespec("free", "LUN", default_value=(20.0, 10.0)),
                         forth=transform_filesystem_free,
                         back=transform_filesystem_free,
                     )
                 ],
             )),
            ("trend_range",
             Optional(Integer(title=_("Time Range for lun filesystem trend computation"),
                              default_value=24,
                              minvalue=1,
                              unit=_("hours")),
                      title=_("Trend computation"),
                      label=_("Enable trend computation"))),
            ("trend_mb",
             Tuple(
                 title=_("Levels on trends in MB per time range"),
                 elements=[
                     Integer(title=_("Warning at"), unit=_("MB / range"), default_value=100),
                     Integer(title=_("Critical at"), unit=_("MB / range"), default_value=200)
                 ],
             )),
            ("trend_perc",
             Tuple(
                 title=_("Levels for the percentual growth per time range"),
                 elements=[
                     Percentage(
                         title=_("Warning at"),
                         unit=_("% / range"),
                         default_value=5,
                     ),
                     Percentage(
                         title=_("Critical at"),
                         unit=_("% / range"),
                         default_value=10,
                     ),
                 ],
             )),
            ("trend_timeleft",
             Tuple(
                 title=_("Levels on the time left until the lun filesystem gets full"),
                 elements=[
                     Integer(
                         title=_("Warning if below"),
                         unit=_("hours"),
                         default_value=12,
                     ),
                     Integer(
                         title=_("Critical if below"),
                         unit=_("hours"),
                         default_value=6,
                     ),
                 ],
             )),
            ("trend_showtimeleft",
             Checkbox(
                 title=_("Display time left in check output"),
                 label=_("Enable"),
                 help=_(
                     "Normally, the time left until the lun filesystem is full is only displayed when "
                     "the configured levels have been breached. If you set this option "
                     "the check always reports this information"))),
            ("trend_perfdata",
             Checkbox(title=_("Trend performance data"),
                      label=_("Enable generation of performance data from trends"))),
            ("read_only",
             Checkbox(title=_("LUN is read-only"),
                      help=_("Display a warning if a LUN is not read-only. Without "
                             "this setting a warning will be displayed if a LUN is "
                             "read-only."),
                      label=_("Enable"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="netapp_luns",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("LUN name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netapp_luns,
        title=lambda: _("NetApp LUNs"),
    ))
