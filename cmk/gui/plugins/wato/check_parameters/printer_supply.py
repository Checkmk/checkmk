#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersPrinters,
)
from cmk.gui.valuespec import (
    Checkbox,
    Dictionary,
    Migrate,
    MonitoringState,
    Percentage,
    TextInput,
    Tuple,
)


def _migrate_some_remaining_destiction(params: object) -> Mapping[str, object]:
    match params:
        case {"some_remaining": int(state), **rest}:
            return {
                "some_remaining_ink": state,
                "some_remaining_space": state,
                **{str(k): v for k, v in rest.items()},
            }
        case dict():
            return params
    raise ValueError(params)


def _parameter_valuespec_printer_supply() -> Migrate:
    return Migrate(
        migrate=_migrate_some_remaining_destiction,
        valuespec=Dictionary(
            elements=[
                (
                    "levels",
                    Tuple(
                        title=_("Levels for remaining supply"),
                        elements=[
                            Percentage(
                                title=_("Warning level for remaining"),
                                allow_int=True,
                                default_value=20.0,
                                help=_(
                                    "For consumable supplies, this is configured as the percentage of "
                                    "remaining capacity. For supplies that fill up, this is configured "
                                    "as remaining space."
                                ),
                            ),
                            Percentage(
                                title=_("Critical level for remaining"),
                                allow_int=True,
                                default_value=10.0,
                                help=_(
                                    "For consumable supplies, this is configured as the percentage of "
                                    "remaining capacity. For supplies that fill up, this is configured "
                                    "as remaining space."
                                ),
                            ),
                        ],
                    ),
                ),
                (
                    "some_remaining_ink",
                    MonitoringState(
                        title=_(
                            "State for containers if the exact amount of remaining ink is unknown"
                        ),
                        help=_(
                            "Some printers do not report a precise percentage but "
                            "just <i>some remaining</i> at a low fill state. Here you "
                            "can set the monitoring state for that situation."
                        ),
                        default_value=1,
                    ),
                ),
                (
                    "some_remaining_space",
                    MonitoringState(
                        title=_(
                            "State for receptacles if the exact amount of remaining space is unkown"
                        ),
                        help=_(
                            "Some printers do not report a precise percentage but "
                            "just <i>some remaining</i> at a high fill state. Here you "
                            "can set the monitoring state for that situation."
                        ),
                        default_value=1,
                    ),
                ),
                (
                    "upturn_toner",
                    Checkbox(
                        title=_("Upturn toner levels"),
                        label=_("Printer sends <i>used</i> material instead of <i>remaining</i>"),
                        help=_(
                            "Some Printers (e.g. Konica for Drum Cartdiges) returning the available"
                            " fuel instead of what is left. In this case it's possible"
                            " to upturn the levels to handle this behavior"
                        ),
                    ),
                ),
            ],
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="printer_supply",
        group=RulespecGroupCheckParametersPrinters,
        item_spec=lambda: TextInput(title=_("cartridge specification"), allow_empty=True),
        parameter_valuespec=_parameter_valuespec_printer_supply,
        title=lambda: _("Printer cartridge levels"),
    )
)
