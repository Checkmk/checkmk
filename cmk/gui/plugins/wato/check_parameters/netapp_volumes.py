#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    Checkbox,
    Dictionary,
    DropdownChoice,
    Float,
    Integer,
    ListChoice,
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


def _parameter_valuespec_netapp_volumes():
    return Dictionary(
        ignored_keys=["patterns"],
        elements=[
            ("levels",
             Alternative(
                 title=_("Levels for volume"),
                 show_alternative_title=True,
                 default_value=(80.0, 90.0),
                 match=match_dual_level_type,
                 elements=[
                     get_free_used_dynamic_valuespec("used", "volume", maxvalue=None),
                     Transform(
                         get_free_used_dynamic_valuespec("free",
                                                         "volume",
                                                         default_value=(20.0, 10.0)),
                         forth=transform_filesystem_free,
                         back=transform_filesystem_free,
                     )
                 ],
             )),
            ("perfdata",
             ListChoice(
                 title=_("Performance data for protocols"),
                 help=_("Specify for which protocol performance data should get recorded."),
                 choices=[
                     ("", _("Summarized data of all protocols")),
                     ("nfs", _("NFS")),
                     ("cifs", _("CIFS")),
                     ("san", _("SAN")),
                     ("fcp", _("FCP")),
                     ("iscsi", _("iSCSI")),
                 ],
             )),
            ("magic",
             Float(title=_("Magic factor (automatic level adaptation for large volumes)"),
                   default_value=0.8,
                   minvalue=0.1,
                   maxvalue=1.0)),
            ("magic_normsize",
             Integer(title=_("Reference size for magic factor"),
                     default_value=20,
                     minvalue=1,
                     unit=_("GB"))),
            ("levels_low",
             Tuple(
                 title=_("Minimum levels if using magic factor"),
                 help=_("The volume levels will never fall below these values, when using "
                        "the magic factor and the volume is very small."),
                 elements=[
                     Percentage(title=_("Warning if above"),
                                unit=_("% usage"),
                                allow_int=True,
                                default_value=50),
                     Percentage(title=_("Critical if above"),
                                unit=_("% usage"),
                                allow_int=True,
                                default_value=60)
                 ],
             )),
            ("inodes_levels",
             Alternative(
                 title=_("Levels for Inodes"),
                 help=_("The number of remaining inodes on the filesystem. "
                        "Please note that this setting has no effect on some filesystem checks."),
                 elements=[
                     Tuple(
                         title=_("Percentage free"),
                         elements=[
                             Percentage(title=_("Warning if less than")),
                             Percentage(title=_("Critical if less than")),
                         ],
                     ),
                     Tuple(
                         title=_("Absolute free"),
                         elements=[
                             Integer(title=_("Warning if less than"),
                                     size=10,
                                     unit=_("inodes"),
                                     minvalue=0,
                                     default_value=10000),
                             Integer(title=_("Critical if less than"),
                                     size=10,
                                     unit=_("inodes"),
                                     minvalue=0,
                                     default_value=5000),
                         ],
                     )
                 ],
                 default_value=(10.0, 5.0),
             )),
            ("show_inodes",
             DropdownChoice(
                 title=_("Display inode usage in check output..."),
                 choices=[
                     ("onproblem", _("Only in case of a problem")),
                     ("onlow", _("Only in case of a problem or if inodes are below 50%")),
                     ("always", _("Always")),
                 ],
                 default_value="onlow",
             )),
            ("trend_range",
             Optional(Integer(title=_("Time Range for filesystem trend computation"),
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
                 title=_("Levels on the time left until the filesystem gets full"),
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
             Checkbox(title=_("Display time left in check output"),
                      label=_("Enable"),
                      help=_(
                          "Normally, the time left until the disk is full is only displayed when "
                          "the configured levels have been breached. If you set this option "
                          "the check always reports this information"))),
            ("trend_perfdata",
             Checkbox(title=_("Trend performance data"),
                      label=_("Enable generation of performance data from trends"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="netapp_volumes",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("Volume name")),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_netapp_volumes,
        title=lambda: _("NetApp Volumes"),
    ))
