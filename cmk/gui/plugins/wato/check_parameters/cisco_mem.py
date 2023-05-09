#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import List

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Alternative,
    Dictionary,
    DictionaryEntry,
    Integer,
    Percentage,
    TextAscii,
    Transform,
    Tuple,
)

from cmk.gui.plugins.wato import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.plugins.wato.check_parameters.utils import (
    size_trend_elements,)


def _parameter_valuespec_cisco_mem():
    elements: List[DictionaryEntry] = [
        ("levels",
         Alternative(
             title=_("Levels for memory usage"),
             elements=[
                 Tuple(
                     title=_("Specify levels in percentage of total RAM"),
                     elements=[
                         Percentage(title=_("Warning at a usage of"),
                                    unit=_("% of RAM"),
                                    maxvalue=None),
                         Percentage(title=_("Critical at a usage of"),
                                    unit=_("% of RAM"),
                                    maxvalue=None)
                     ],
                 ),
                 Tuple(
                     title=_("Specify levels in absolute usage values"),
                     elements=[
                         Integer(title=_("Warning at"), unit=_("MB")),
                         Integer(title=_("Critical at"), unit=_("MB"))
                     ],
                 ),
             ],
         )),
    ]
    return Transform(
        Dictionary(elements=elements + size_trend_elements),
        forth=lambda spec: spec if isinstance(spec, dict) else {"levels": spec},
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="cisco_mem",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextAscii(title=_("Memory Pool Name"), allow_empty=False),
        parameter_valuespec=_parameter_valuespec_cisco_mem,
        title=lambda: _("Cisco Memory Usage"),
    ))
