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
from cmk.gui.valuespec import Filesize, Optional, TextInput, Tuple, Integer, Percentage, Checkbox, Dictionary, Transform


def _item_spec_mysql_db_size():
    return TextInput(
        title=_("Name of the database"),
        help=_("Don't forget the instance: instance:dbname"),
    )


def convert_old_params(params):
    if not isinstance(params, dict):
        params = {"mysql_size": params}
    return params


def _parameter_valuespec_mysql_db_size():
    return Transform(
        Dictionary(elements=[
            ("mysql_size",
             Optional(
                 Tuple(
                     elements=[
                         Filesize(title=_("warning at")),
                         Filesize(title=_("critical at")),
                     ],
                 ),
                 help=_(
                     "The check will trigger a warning or critical state if the size of the "
                     "database exceeds these levels."
                 ),
                 title=_("Impose limits on the size of the database"),
             )),
            ("trend_range",
             Optional(Integer(title=_("Time Range for trend computation"),
                              default_value=24,
                              minvalue=1,
                              unit=_("hours")),
                      title=_("Trend computation"),
                      label=_("Enable trend computation"))),
            ("trend_mb",
             Tuple(title=_("Levels on trends in MB per time range"),
                   elements=[
                       Integer(title=_("Warning at"), unit=_("MB / range"), default_value=100),
                       Integer(title=_("Critical at"), unit=_("MB / range"), default_value=200)
                   ])),
            ("trend_perc",
             Tuple(title=_("Levels for the percentual growth per time range"),
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
                   ])),
            ("trend_perfdata",
             Checkbox(title=_("Trend performance data"),
                      label=_("Enable generation of performance data from trends"))),
        ]),
        forth=convert_old_params,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mysql_db_size",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_mysql_db_size,
        parameter_valuespec=_parameter_valuespec_mysql_db_size,
        title=lambda: _("MySQL database sizes"),
    )
)
