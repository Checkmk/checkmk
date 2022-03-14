#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.db2_tablespaces import db_levels_common
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, DropdownChoice, ListOf, MonitoringState, TextInput, Tuple


def _item_spec_oracle_tablespaces():
    return TextInput(
        title=_("Explicit tablespaces"),
        help=_(
            "Here you can set explicit tablespaces by defining them via SID and the tablespace name, separated by a dot, for example <b>pengt.TEMP</b>"
        ),
        regex=r".+\..+",
        allow_empty=False,
    )


def _parameter_valuespec_oracle_tablespaces():
    return Dictionary(
        help=_(
            "A tablespace is a container for segments (tables, indexes, etc). A "
            "database consists of one or more tablespaces, each made up of one or "
            "more data files. Tables and indexes are created within a particular "
            "tablespace. "
            "This rule allows you to define checks on the size of tablespaces."
        ),
        elements=db_levels_common()
        + [
            (
                "autoextend",
                DropdownChoice(
                    title=_("Expected autoextend setting"),
                    choices=[
                        (True, _("Autoextend is expected to be ON")),
                        (False, _("Autoextend is expected to be OFF")),
                        (None, _("Autoextend will be ignored")),
                    ],
                ),
            ),
            (
                "autoextend_severity",
                MonitoringState(
                    title=_("Severity of invalid autoextend setting"),
                    default_value=2,
                ),
            ),
            (
                "defaultincrement",
                DropdownChoice(
                    title=_("Default Increment"),
                    choices=[
                        (True, _("State is WARNING in case the next extent has the default size.")),
                        (False, _("Ignore default increment")),
                    ],
                ),
            ),
            (
                "map_file_online_states",
                ListOf(
                    valuespec=Tuple(
                        orientation="horizontal",
                        elements=[
                            DropdownChoice(
                                choices=[
                                    ("RECOVER", _("Recover")),
                                    ("OFFLINE", _("Offline")),
                                ],
                            ),
                            MonitoringState(),
                        ],
                    ),
                    title=_("Map file online states"),
                ),
            ),
            (
                "temptablespace",
                DropdownChoice(
                    title=_("Monitor temporary Tablespace"),
                    choices=[
                        (False, _("Ignore temporary Tablespaces (Default)")),
                        (True, _("Apply rule to temporary Tablespaces")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="oracle_tablespaces",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_oracle_tablespaces,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_oracle_tablespaces,
        title=lambda: _("Oracle Tablespaces"),
    )
)
