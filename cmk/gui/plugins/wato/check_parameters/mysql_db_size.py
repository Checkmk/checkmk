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
from cmk.gui.valuespec import Filesize, Optional, TextInput, Tuple


def _item_spec_mysql_db_size():
    return TextInput(
        title=_("Name of the database"),
        help=_("Don't forget the instance: instance:dbname"),
    )


def _parameter_valuespec_mysql_db_size():
    return Optional(
        valuespec=Tuple(
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
