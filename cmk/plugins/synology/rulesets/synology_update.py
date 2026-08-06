#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    MultipleChoice,
    MultipleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic

# The legacy ListChoice stored the raw SYNOLOGY-SYSTEM-MIB values. MultipleChoiceElement
# names have to be Python identifiers, so rules are migrated onto these names.
_STATUS_NAMES: Mapping[int, str] = {
    1: "available",
    2: "unavailable",
    4: "disconnected",
    5: "others",
}

_UPDATE_STATES = (
    MultipleChoiceElement(name="available", title=Title("Available")),
    MultipleChoiceElement(name="unavailable", title=Title("Unavailable")),
    MultipleChoiceElement(name="disconnected", title=Title("Disconnected")),
    MultipleChoiceElement(name="others", title=Title("Others")),
)

_STATE_KEYS = ("ok_states", "warn_states", "crit_states")


def _migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise TypeError(value)
    return {
        key: [
            _STATUS_NAMES.get(entry, str(entry)) if isinstance(entry, int) else entry
            for entry in states
        ]
        if key in _STATE_KEYS and isinstance(states, list)
        else states
        for key, states in value.items()
    }


def _state_element(title: Title, default: Sequence[str]) -> DictElement[Sequence[str]]:
    return DictElement(
        required=True,
        parameter_form=MultipleChoice(
            title=title,
            elements=_UPDATE_STATES,
            prefill=DefaultValue(default),
        ),
    )


def _parameter_form_synology_update() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "Map the update status reported by the device to a monitoring state. A status "
            "that appears in none of the three lists results in UNKNOWN. The status "
            "'Connecting' is not offered: while the device is contacting the update server "
            "the service keeps its previous result instead of flapping."
        ),
        elements={
            "ok_states": _state_element(Title("States which result in OK"), ["unavailable"]),
            "warn_states": _state_element(Title("States which result in WARN"), ["others"]),
            "crit_states": _state_element(
                Title("States which result in CRIT"), ["available", "disconnected"]
            ),
        },
        migrate=_migrate,
    )


rule_spec_synology_update = CheckParameters(
    name="synology_update",
    title=Title("Synology updates"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_synology_update,
    condition=HostCondition(),
)
