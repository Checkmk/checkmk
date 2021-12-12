#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersStorage,
)
from cmk.gui.valuespec import Dictionary, Integer, TextInput, Tuple


def _mongodb_collections_size_tuple(title: str, unit: str) -> Tuple:
    return Tuple(
        title=title,
        elements=[
            Integer(title=_("Warning if above"), unit=unit, minvalue=0),
            Integer(title=_("Critical if above"), unit=unit, minvalue=0),
        ],
    )


def _parameter_valuespec_mongodb_collections() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "levels_size",
                _mongodb_collections_size_tuple(
                    _("Uncompressed size in memory"),
                    _("MiB"),
                ),
            ),
            (
                "levels_storageSize",
                _mongodb_collections_size_tuple(
                    _("Allocated for document storage"),
                    _("MiB"),
                ),
            ),
            (
                "levels_totalIndexSize",
                _mongodb_collections_size_tuple(
                    _("Total size of all indexes for the collection"),
                    _("KByte"),
                ),
            ),
        ]
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mongodb_collections",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextInput(
            title=_("MongoDB Collection Size"),
        ),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mongodb_collections,
        title=lambda: _("MongoDB Collection Size"),
    )
)
