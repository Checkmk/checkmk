#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.check_parameters.mssql_utils import mssql_item_spec_instance_database_file
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Alternative, Dictionary, Filesize, Integer, ListOf, Percentage, Tuple


def levels_absolute_or_dynamic(name, value):
    return Alternative(
        title=_("Levels of %s %s") % (name, value),
        default_value=(80.0, 90.0),
        elements=[
            Tuple(
                title=_("Percentage %s space") % value,
                elements=[
                    Percentage(
                        title=_("Warning at"),
                        # xgettext: no-python-format
                        unit=_("% used"),
                    ),
                    Percentage(
                        title=_("Critical at"),
                        # xgettext: no-python-format
                        unit=_("% used"),
                    ),
                ],
            ),
            Tuple(
                title=_("Absolute %s space") % value,
                elements=[
                    Integer(title=_("Warning at"), unit=_("MB"), default_value=500),
                    Integer(title=_("Critical at"), unit=_("MB"), default_value=1000),
                ],
            ),
            ListOf(
                valuespec=Tuple(
                    orientation="horizontal",
                    elements=[
                        Filesize(title=_(" larger than")),
                        Alternative(
                            title=_("Levels for the %s %s size") % (name, value),
                            elements=[
                                Tuple(
                                    title=_("Percentage %s space") % value,
                                    elements=[
                                        Percentage(
                                            title=_("Warning at"),
                                            # xgettext: no-python-format
                                            unit=_("% used"),
                                        ),
                                        Percentage(
                                            title=_("Critical at"),
                                            # xgettext: no-python-format
                                            unit=_("% used"),
                                        ),
                                    ],
                                ),
                                Tuple(
                                    title=_("Absolute free space"),
                                    elements=[
                                        Integer(title=_("Warning at"), unit=_("MB")),
                                        Integer(title=_("Critical at"), unit=_("MB")),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                title=_("Dynamic levels"),
            ),
        ],
    )


def _parameter_valuespec_mssql_datafiles():
    return Dictionary(
        title=_("File Size Levels"),
        help=_(
            "Specify levels for datafiles of a database. Please note that relative "
            "levels will only work if there is a max_size set for the file on the database "
            "side."
        ),
        elements=[
            ("used_levels", levels_absolute_or_dynamic(_("Datafile"), _("used"))),
            (
                "allocated_used_levels",
                levels_absolute_or_dynamic(_("Datafile"), _("used of allocation")),
            ),
            ("allocated_levels", levels_absolute_or_dynamic(_("Datafile"), _("allocated"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mssql_datafiles",
        group=RulespecGroupCheckParametersApplications,
        item_spec=mssql_item_spec_instance_database_file,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mssql_datafiles,
        title=lambda: _("MSSQL Datafile Sizes"),
    )
)
