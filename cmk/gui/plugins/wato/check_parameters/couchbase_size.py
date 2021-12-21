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
from cmk.gui.valuespec import Dictionary, Filesize, TextInput, Tuple


def _tuple(title):
    return Tuple(
        title=title,
        elements=[
            Filesize(
                title="Warning",
            ),
            Filesize(
                title="Critical",
            ),
        ],
    )


def _valuespec_couchbase_size(title):
    def _get_spec():
        return Dictionary(
            title=title,
            elements=[
                ("size_on_disk", _tuple(_("Levels for size on disk"))),
                ("size", _tuple(_("Levels for data size"))),
            ],
        )

    return _get_spec


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_size_docs",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Node name")),
        parameter_valuespec=_valuespec_couchbase_size(_("Couchbase Node: Size of documents")),
        title=lambda: _("Couchbase Node: Size of documents"),
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_size_spacial",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Node name")),
        parameter_valuespec=_valuespec_couchbase_size(_("Couchbase Node: Size of spacial views")),
        title=lambda: _("Couchbase Node: Size of spacial views"),
    )
)

rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="couchbase_size_couch",
        group=RulespecGroupCheckParametersApplications,
        match_type="dict",
        item_spec=lambda: TextInput(title=_("Node name")),
        parameter_valuespec=_valuespec_couchbase_size(_("Couchbase Node: Size of couch views")),
        title=lambda: _("Couchbase Node: Size of couch views"),
    )
)
