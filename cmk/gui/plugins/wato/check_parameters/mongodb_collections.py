#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    RulespecGroupCheckParametersStorage,
    rulespec_registry,
)
from cmk.gui.valuespec import Dictionary, Integer, TextAscii, Tuple


def _mongodb_collections_size_tuple(title, course, unit):
    return Tuple(title=_(title),
                 elements=[
                     Integer(title=_("Warning if %s") % course, unit=_(unit), minvalue=0),
                     Integer(title=_("Critical if %s") % course, unit=_(unit), minvalue=0),
                 ])


def _parameter_valuespec_mongodb_collections():
    return Dictionary(elements=[
        ("levels_size",
         _mongodb_collections_size_tuple("Uncompressed size in memory", "above", "MiB")),
        ("levels_storageSize",
         _mongodb_collections_size_tuple("Allocated for document storage", "above", "MiB")),
        ("levels_totalIndexSize",
         _mongodb_collections_size_tuple("Total size of all indexes for the collection", "above",
                                         "KByte")),
    ])


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="mongodb_collections",
        group=RulespecGroupCheckParametersStorage,
        item_spec=lambda: TextAscii(title=_("MongoDB Collection Size"),),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_mongodb_collections,
        title=lambda: _("MongoDB Collection Size"),
    ))
