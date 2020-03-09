#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    Filesize,
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


def _item_spec_memory_simple():
    return TextAscii(
        title=_("Module name or empty"),
        help=_("Leave this empty for systems without modules, which just "
               "have one global memory usage."),
        allow_empty=True,
    )


def _parameter_valuespec_memory_simple():
    return Transform(
        Dictionary(
            help=_("Memory levels for simple devices not running more complex OSs"),
            elements=[
                ("levels",
                 CascadingDropdown(
                     title=_("Levels for memory usage"),
                     choices=[
                         ("perc_used", _("Percentual levels for used memory"),
                          Tuple(elements=[
                              Percentage(title=_("Warning at a memory usage of"),
                                         default_value=80.0,
                                         maxvalue=None),
                              Percentage(title=_("Critical at a memory usage of"),
                                         default_value=90.0,
                                         maxvalue=None)
                          ],)),
                         ("abs_free", _("Absolute levels for free memory"),
                          Tuple(elements=[
                              Filesize(title=_("Warning below")),
                              Filesize(title=_("Critical below"))
                          ],)),
                         ("ignore", _("Do not impose levels")),
                     ],
                 )),
            ],
            optional_keys=[],
        ),
        # Convert default levels from discovered checks
        forth=lambda v: not isinstance(v, dict) and {"levels": ("perc_used", v)} or v,
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="memory_simple",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=_item_spec_memory_simple,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_simple,
        title=lambda: _("Main memory usage of simple devices"),
    ))
