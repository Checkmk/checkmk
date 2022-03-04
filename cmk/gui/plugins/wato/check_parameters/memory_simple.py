#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
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
    Transform,
    Tuple,
)


def _item_spec_memory_simple():
    return TextInput(
        title=_("Module name or empty"),
        help=_(
            "Leave this empty for systems without modules, which just "
            "have one global memory usage."
        ),
        allow_empty=True,
    )


def _parameter_valuespec_memory_simple():
    return Transform(
        valuespec=Dictionary(
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
    )
)
