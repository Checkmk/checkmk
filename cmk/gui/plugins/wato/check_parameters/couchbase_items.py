#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Integer,
    TextAscii,
    Tuple,
    Dictionary,
)
from cmk.gui.plugins.wato import (
    RulespecGroupCheckParametersApplications,
    CheckParameterRulespecWithItem,
    rulespec_registry,
)


def _tuple(title):
    return Tuple(
        title=title,
        elements=[
            Integer(title='Warning',),
            Integer(title='Critical',),
        ],
    )


def _parameter_valuespec_couchbase_operations():
    return Dictionary(
        title=_('Couchbase Nodes: Items'),
        elements=[
            ('curr_items', _tuple(_('Levels for active items'))),
            ('non_residents', _tuple(_('Levels for non-resident items'))),
            ('curr_items_tot', _tuple(_('Levels for total number of items'))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_items",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextAscii(title=_('Node name')),
        parameter_valuespec=_parameter_valuespec_couchbase_operations,
        title=lambda: _("Couchbase Node Items"),
    ))
