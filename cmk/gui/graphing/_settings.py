#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.valuespec import Age, Dictionary, ListOf, TextInput
from cmk.gui.watolib.config_domain_name import ConfigVariable, GlobalSettingsContext
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupUserInterface


def _valuespec(context: GlobalSettingsContext) -> ListOf[dict[str, object]]:
    return ListOf(
        valuespec=Dictionary(
            optional_keys=[],
            elements=[
                (
                    "title",
                    TextInput(
                        title=_("Title"),
                        allow_empty=False,
                    ),
                ),
                (
                    "duration",
                    Age(
                        title=_("Duration"),
                    ),
                ),
            ],
        ),
        title=_("Custom graph time ranges"),
        movable=True,
        totext=_("%d time ranges"),
        default_value=[dict(graph_range) for graph_range in context.configured_graph_timeranges],
    )


ConfigVariableGraphTimeranges = ConfigVariable(
    group=ConfigVariableGroupUserInterface,
    primary_domain=ConfigDomainGUI,
    ident="graph_timeranges",
    valuespec=_valuespec,
)
