#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    CheckParameterRulespecWithoutItem,
    rulespec_registry,
    RulespecGroupCheckParametersOperatingSystem,
)
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    Filesize,
    MonitoringState,
    Percentage,
    TextInput,
    Tuple,
)


def _parameter_valuespec_memory_simple() -> Dictionary:
    return Dictionary(
        help=_("Memory levels for simple devices not running more complex OSs"),
        elements=[
            (
                "levels",
                CascadingDropdown(
                    title=_("Levels for RAM usage"),
                    choices=[
                        (
                            "perc_used",
                            _("Percentual levels for used RAM"),
                            Tuple(
                                elements=[
                                    Percentage(
                                        title=_("Warning at a RAM usage of"),
                                        default_value=80.0,
                                        maxvalue=None,
                                    ),
                                    Percentage(
                                        title=_("Critical at a RAM usage of"),
                                        default_value=90.0,
                                        maxvalue=None,
                                    ),
                                ],
                            ),
                        ),
                        (
                            "abs_free",
                            _("Absolute levels for free RAM"),
                            Tuple(
                                elements=[
                                    Filesize(title=_("Warning below")),
                                    Filesize(title=_("Critical below")),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
            (
                "levels_swap",
                CascadingDropdown(
                    title=_("Levels for swap usage"),
                    choices=[
                        (
                            "perc_used",
                            _("Percentual levels for used swap"),
                            Tuple(
                                elements=[
                                    Percentage(
                                        title=_("Warning at a swap usage of"), maxvalue=None
                                    ),
                                    Percentage(
                                        title=_("Critical at a swap usage of"), maxvalue=None
                                    ),
                                ],
                            ),
                        ),
                        (
                            "abs_free",
                            _("Absolute levels for free swap"),
                            Tuple(
                                elements=[
                                    Filesize(title=_("Warning below")),
                                    Filesize(title=_("Critical below")),
                                ],
                            ),
                        ),
                    ],
                ),
            ),
            (
                "swap_errors",
                MonitoringState(
                    title=_("Monitoring state in case of swap errors"),
                    default_value=0,
                ),
            ),
        ],
        optional_keys=True,
    )


rulespec_registry.register(
    CheckParameterRulespecWithoutItem(
        check_group_name="memory_simple_single",
        group=RulespecGroupCheckParametersOperatingSystem,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_simple,
        title=lambda: _("Main memory usage of simple devices with single services"),
    )
)


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="memory_simple",
        group=RulespecGroupCheckParametersOperatingSystem,
        item_spec=lambda: TextInput(title=_("Module name"), allow_empty=True),
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_memory_simple,
        title=lambda: _("Main memory usage of simple devices with multiple services"),
    )
)
