#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Optional, Union

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
    FixedValue,
    TextInput,
    Transform,
    Tuple,
)


def _item_spec_mysql_db_size():
    return TextInput(
        title=_("Name of the database"),
        help=_("Don't forget the instance: instance:dbname"),
    )


def _NoLevels() -> FixedValue:
    return FixedValue(
        value=None,
        title=_("No Levels"),
        totext=_("Do not impose levels, always be OK"),
    )


def _FixedLevels() -> Tuple:
    return Tuple(
        title=_("Fixed Levels"),
        elements=[
            Filesize(
                title=_("Warning at"),
            ),
            Filesize(
                title=_("Critical at"),
            ),
        ],
    )


def SizeLevels(
    help: Optional[str] = None,  # pylint: disable=redefined-builtin
    title: Optional[str] = None,
) -> Alternative:
    """
    Internal API. Might change between versions
    See Also:
        :func: cmk.gui.plugins.wato.utils.Levels
    """

    def match_levels_alternative(v: Optional[tuple[int, int]]) -> int:
        if v is None:
            return 0
        return 1

    elements = [
        _NoLevels(),
        _FixedLevels(),
    ]
    return Alternative(
        title=title,
        help=help,
        elements=elements,
        match=match_levels_alternative,
        default_value=None,
    )


def _transform(
    params: Union[dict, tuple[float, float]]
) -> dict[str, Optional[tuple[float, float]]]:
    if isinstance(params, dict):
        # old style check api default
        if params == {}:
            return {"levels": None}
        return params
    return {"levels": params}


def _parameter_valuespec_mysql_db_size():
    return Transform(
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    SizeLevels(
                        help=_(
                            "The service will trigger a warning or critical state if the size of the "
                            "database exceeds these levels."
                        ),
                        title=_("Impose limits on the size of the database"),
                    ),
                )
            ],
            optional_keys=False,
        ),
        forth=_transform,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mysql_db_size",
        match_type="dict",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_mysql_db_size,
        parameter_valuespec=_parameter_valuespec_mysql_db_size,
        title=lambda: _("MySQL database sizes"),
    )
)
