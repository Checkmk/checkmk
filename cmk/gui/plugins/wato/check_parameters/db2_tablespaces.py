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
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    Filesize,
    Float,
    Integer,
    ListOf,
    Percentage,
    TextInput,
    Tuple,
)


def db_levels_common():
    return [
        (
            "levels",
            Alternative(
                title=_("Levels for the Tablespace usage"),
                default_value=(10.0, 5.0),
                elements=[
                    Tuple(
                        title=_("Percentage free space"),
                        elements=[
                            Percentage(
                                title=_("Warning if below"),
                                # xgettext: no-python-format
                                unit=_("% free"),
                            ),
                            Percentage(
                                title=_("Critical if below"),
                                # xgettext: no-python-format
                                unit=_("% free"),
                            ),
                        ],
                    ),
                    Tuple(
                        title=_("Absolute free space"),
                        elements=[
                            Integer(title=_("Warning if below"), unit=_("MB"), default_value=1000),
                            Integer(title=_("Critical if below"), unit=_("MB"), default_value=500),
                        ],
                    ),
                    ListOf(
                        valuespec=Tuple(
                            orientation="horizontal",
                            elements=[
                                Filesize(title=_("Tablespace larger than")),
                                Alternative(
                                    title=_("Levels for the Tablespace size"),
                                    elements=[
                                        Tuple(
                                            title=_("Percentage free space"),
                                            elements=[
                                                Percentage(
                                                    title=_("Warning if below"),
                                                    # xgettext: no-python-format
                                                    unit=_("% free"),
                                                ),
                                                Percentage(
                                                    title=_("Critical if below"),
                                                    # xgettext: no-python-format
                                                    unit=_("% free"),
                                                ),
                                            ],
                                        ),
                                        Tuple(
                                            title=_("Absolute free space"),
                                            elements=[
                                                Integer(title=_("Warning if below"), unit=_("MB")),
                                                Integer(title=_("Critical if below"), unit=_("MB")),
                                            ],
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        title=_("Dynamic levels"),
                    ),
                ],
            ),
        ),
        (
            "magic",
            Float(
                title=_("Magic factor (automatic level adaptation for large tablespaces)"),
                help=_("This is only be used in case of percentual levels"),
                minvalue=0.1,
                maxvalue=1.0,
                default_value=0.9,
            ),
        ),
        (
            "magic_normsize",
            Integer(
                title=_("Reference size for magic factor"),
                minvalue=1,
                default_value=1000,
                unit=_("MB"),
            ),
        ),
        (
            "magic_maxlevels",
            Tuple(
                title=_("Maximum levels if using magic factor"),
                help=_(
                    "The tablespace levels will never be raise above these values, when using "
                    "the magic factor and the tablespace is very small."
                ),
                elements=[
                    Percentage(
                        title=_("Maximum warning level"),
                        # xgettext: no-python-format
                        unit=_("% free"),
                        allow_int=True,
                        default_value=60.0,
                    ),
                    Percentage(
                        title=_("Maximum critical level"),
                        # xgettext: no-python-format
                        unit=_("% free"),
                        allow_int=True,
                        default_value=50.0,
                    ),
                ],
            ),
        ),
    ]


def _item_spec_db2_tablespaces():
    return TextInput(
        title=_("Instance"),
        help=_(
            "The instance name, the database name and the tablespace name combined "
            "like this db2wps8:WPSCOMT8.USERSPACE1"
        ),
    )


def _parameter_valuespec_db2_tablespaces():
    return Dictionary(
        help=_(
            "A tablespace is a container for segments (tables, indexes, etc). A "
            "database consists of one or more tablespaces, each made up of one or "
            "more data files. Tables and indexes are created within a particular "
            "tablespace. "
            "This rule allows you to define checks on the size of tablespaces."
        ),
        elements=db_levels_common(),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="db2_tablespaces",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_db2_tablespaces,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_db2_tablespaces,
        title=lambda: _("DB2 Tablespaces"),
    )
)
