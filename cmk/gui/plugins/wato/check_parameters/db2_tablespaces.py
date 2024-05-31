#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import math
from typing import Literal

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    DropdownChoice,
    Filesize,
    Float,
    Integer,
    ListOf,
    Percentage,
    TextInput,
    Transform,
    Tuple,
)

_IEC_UNITS = Literal["B", "KiB", "MiB", "GiB", "TiB"]


def _transform_abs_level_back(value: tuple[int, _IEC_UNITS]) -> int | float:
    level, dimension = value
    match dimension:
        case "B":
            return level / 1024**2
        case "KiB":
            return level / 1024
        case "MiB":
            return level
        case "GiB":
            return level * 1024
        case "TiB":
            return level * 1024**2


def _transform_abs_level_forth(value: int | float) -> tuple[int, _IEC_UNITS]:
    exponent = math.floor(math.log2(value))
    if exponent >= 20:
        return int(value / 1024**2), "TiB"
    if exponent >= 10:
        return int(value / 1024), "GiB"
    if exponent <= -10:
        return int(value * 1024**2), "B"
    if exponent <= 0:
        return int(value * 1024), "KiB"
    return int(value), "MiB"


def _absolute_level_common(title: str, default_value: int) -> Transform:
    # Note: The related check plug-ins expect levels in MiB
    return Transform(
        Tuple(
            title=title,
            elements=[
                Integer(default_value=default_value),
                DropdownChoice(
                    choices=[
                        ("B", _("Byte")),
                        ("KiB", _("KiB")),
                        ("MiB", _("MiB")),
                        ("GiB", _("GiB")),
                        ("TiB", _("TiB")),
                    ],
                    default_value="MiB",
                ),
            ],
            orientation="horizontal",
        ),
        back=_transform_abs_level_back,
        forth=_transform_abs_level_forth,
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
                            _absolute_level_common(_("Warning if below"), 1000),
                            _absolute_level_common(_("Critical if below"), 500),
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
                                                _absolute_level_common(_("Warning if below"), 1000),
                                                _absolute_level_common(_("Critical if below"), 500),
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
            _absolute_level_common(_("Reference size for magic factor"), 1000),
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
