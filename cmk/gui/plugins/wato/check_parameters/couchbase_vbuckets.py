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
from cmk.gui.valuespec import Dictionary, Filesize, Integer, Percentage, TextInput, Tuple


def _parameter_valuespec_couchbase_vbuckets():
    return Dictionary(
        title=_("Couchbase vBuckets"),
        elements=[
            (
                "item_memory",
                Tuple(
                    title="Item memory size",
                    elements=[
                        Filesize(title=_("Warning at")),
                        Filesize(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "resident_items_ratio",
                Tuple(
                    title="Active vBuckets: Lower levels for resident items ratio",
                    elements=[
                        Percentage(title=_("Warning at or below"), unit="%"),
                        Percentage(title=_("Critical at or below"), unit="%"),
                    ],
                ),
            ),
            (
                "vb_pending_num",
                Tuple(
                    title="Active vBuckets: Levels for number of pending vBuckets",
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
            (
                "vb_replica_num",
                Tuple(
                    title="Replica vBuckets: Levels for total number of replica vBuckets",
                    elements=[
                        Integer(title=_("Warning at")),
                        Integer(title=_("Critical at")),
                    ],
                ),
            ),
        ],
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_vbuckets",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Bucket name")),
        parameter_valuespec=_parameter_valuespec_couchbase_vbuckets,
        title=lambda: _("Couchbase vBuckets"),
    )
)
