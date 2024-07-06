#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    CheckParameterRulespecWithItem,
    rulespec_registry,
    RulespecGroupCheckParametersApplications,
)
from cmk.gui.valuespec import Dictionary, Float, Integer, Migrate, TextInput, Transform, Tuple


def _ms_to_s(v: float) -> float:
    return v / 1000.0


def _s_to_ms(v: float) -> float:
    return v * 1000.0


def _migrate_milliseconds(values: object) -> dict:
    if not isinstance(values, dict):
        raise TypeError(values)

    if "store_latency_s" in values:
        return values

    values["store_latency_s"] = tuple(_ms_to_s(x) for x in values.pop("store_latency"))
    values["clienttype_latency_s"] = tuple(_ms_to_s(x) for x in values.pop("clienttype_latency"))

    return values


def _item_spec_msx_info_store():
    return TextInput(
        title=_("Store"),
        help=_("Specify the name of a store (This is either a mailbox or public folder)"),
    )


def _parameter_valuespec_msx_info_store():
    return Migrate(
        migrate=_migrate_milliseconds,
        valuespec=Dictionary(
            title=_("Set Levels"),
            elements=[
                (
                    "store_latency_s",
                    Tuple(
                        title=_("Average latency for store requests"),
                        elements=[
                            Transform(
                                valuespec=Float(
                                    title=_("Warning at"), unit=_("ms"), default_value=40.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                            Transform(
                                valuespec=Float(
                                    title=_("Critical at"), unit=_("ms"), default_value=50.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                        ],
                    ),
                ),
                (
                    "clienttype_latency_s",
                    Tuple(
                        title=_("Average latency for client type requests"),
                        elements=[
                            Transform(
                                valuespec=Float(
                                    title=_("Warning at"), unit=_("ms"), default_value=40.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                            Transform(
                                valuespec=Float(
                                    title=_("Critical at"), unit=_("ms"), default_value=50.0
                                ),
                                back=_ms_to_s,
                                forth=_s_to_ms,
                            ),
                        ],
                    ),
                ),
                (
                    "clienttype_requests",
                    Tuple(
                        title=_("Maximum number of client type requests per second"),
                        elements=[
                            Integer(title=_("Warning at"), unit=_("requests"), default_value=60),
                            Integer(title=_("Critical at"), unit=_("requests"), default_value=70),
                        ],
                    ),
                ),
            ],
            optional_keys=[],
        ),
    )


rulespec_registry.register(
    CheckParameterRulespecWithItem(
        check_group_name="msx_info_store",
        group=RulespecGroupCheckParametersApplications,
        item_spec=_item_spec_msx_info_store,
        match_type="dict",
        parameter_valuespec=_parameter_valuespec_msx_info_store,
        title=lambda: _("MS Exchange Information Store"),
    )
)
