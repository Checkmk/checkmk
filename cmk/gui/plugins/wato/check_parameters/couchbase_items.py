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
from cmk.gui.valuespec import Dictionary, Float, Integer, TextInput, Tuple


def _int_tuple(title):
    return Tuple(
        title=title,
        elements=[
            Integer(
                title="Warning",
            ),
            Integer(
                title="Critical",
            ),
        ],
    )


def _float_tuple(title):
    return Tuple(
        title=title,
        elements=[
            Float(title="Warning", unit="/s"),
            Float(title="Critical", unit="/s"),
        ],
    )


def _parameter_valuespec_couchbase_operations():
    return Dictionary(
        title=_("Couchbase Nodes: Items"),
        elements=[
            ("curr_items", _int_tuple(_("Levels for active items"))),
            ("non_residents", _int_tuple(_("Levels for non-resident items"))),
            ("curr_items_tot", _int_tuple(_("Levels for total number of items"))),
            (
                "fetched_items",
                _int_tuple(_("Buckets only: Levels for number of items fetched from disk")),
            ),
            ("disk_write_ql", _int_tuple(_("Buckets only: Levels for length of disk write queue"))),
            ("disk_fill_rate", _float_tuple(_("Buckets only: Levels for disk queue fill rate"))),
            ("disk_drain_rate", _float_tuple(_("Buckets only: Levels for disk queue drain rate"))),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_items",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Node or Bucket name")),
        parameter_valuespec=_parameter_valuespec_couchbase_operations,
        title=lambda: _("Couchbase Items"),
    )
)
