#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic

_OTHER_HELP = Help(
    "The instrument agent does not recognize the value. You may need to upgrade the "
    "instrument agent."
)


def _state(
    title: Title, default: Literal[0, 1, 2, 3], help_text: Help | None = None
) -> DictElement[Literal[0, 1, 2, 3]]:
    return DictElement(
        parameter_form=ServiceState(
            title=title,
            help_text=help_text,
            prefill=DefaultValue(default),
        )
    )


def _conditions(title: Title) -> DictElement[Mapping[str, object]]:
    return DictElement(
        parameter_form=Dictionary(
            title=title,
            elements={
                "other": _state(Title("Other"), ServiceState.WARN, _OTHER_HELP),
                "ok": _state(Title("OK"), ServiceState.OK),
                "degraded": _state(Title("Degraded"), ServiceState.WARN),
                "failed": _state(Title("Failed"), ServiceState.CRIT),
            },
        )
    )


def _board_statuses() -> DictElement[Mapping[str, object]]:
    return DictElement(
        parameter_form=Dictionary(
            title=Title("Board status"),
            elements={
                "other": _state(Title("Other"), ServiceState.WARN, _OTHER_HELP),
                "ok": _state(Title("OK"), ServiceState.OK),
                "general_failure": _state(Title("General failure"), ServiceState.CRIT),
                "cable_problem": _state(Title("Cable problem"), ServiceState.CRIT),
                "powered_off": _state(Title("Powered off"), ServiceState.CRIT),
                "cache_module_missing": _state(Title("Cache module missing"), ServiceState.WARN),
                "degraded": _state(Title("Degraded"), ServiceState.CRIT),
                "enabled": _state(Title("Enabled"), ServiceState.OK),
                "disabled": _state(Title("Disabled"), ServiceState.OK),
                "standby_offline": _state(Title("Standby (offline)"), ServiceState.WARN),
                "standby_spare": _state(Title("Standby (spare)"), ServiceState.OK),
                "in_test": _state(Title("In test"), ServiceState.WARN),
                "starting": _state(Title("Starting"), ServiceState.OK),
                "absent": _state(Title("Absent"), ServiceState.CRIT),
                "unavailable_offline": _state(Title("Unavailable (offline)"), ServiceState.CRIT),
                "deferring": _state(Title("Deferring"), ServiceState.OK),
                "quiesced": _state(Title("Quiesced"), ServiceState.OK),
                "updating": _state(Title("Updating"), ServiceState.WARN),
                "qualified": _state(Title("Qualified"), ServiceState.OK),
            },
        )
    )


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "The RAID controllers of HPE ProLiant servers report a condition, a board "
            "condition and a board status. Here you can set the monitoring state for each "
            "value they report."
        ),
        elements={
            "condition": _conditions(Title("Condition")),
            "board_condition": _conditions(Title("Board condition")),
            "board_status": _board_statuses(),
        },
    )


rule_spec_hp_proliant_da_cntlr = CheckParameters(
    name="hp_proliant_da_cntlr",
    title=Title("HPE ProLiant RAID controller"),
    topic=Topic.STORAGE,
    parameter_form=_make_form,
    condition=HostAndItemCondition(item_title=Title("Controller index")),
)
