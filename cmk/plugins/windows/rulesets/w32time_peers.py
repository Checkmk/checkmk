#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    LevelsType,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, HostCondition, Topic


def _make_form(summary_form: bool) -> Callable[[], Dictionary]:
    is_universal = {}
    if summary_form:
        is_universal = {
            "universal": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    label=Label("Only alert if all peers are failed"),
                    prefill=DefaultValue(False),
                    help_text=Help(
                        "When checked, alert if <i>all</i> peers exceed the defined thresholds. "
                        "Otherwise, alert only if <i>any</i> peer exceeds the defined thresholds."
                    ),
                ),
            ),
        }

    def form() -> Dictionary:
        return Dictionary(
            help_text=Help(
                "This check monitors the status of a peer configured in the Windows Time service."
            ),
            elements={
                "reachability_consecutive_failures": DictElement(
                    required=False,
                    parameter_form=SimpleLevels(
                        title=Title("Consecutive reachability failures (up to 8)"),
                        level_direction=LevelDirection.UPPER,
                        form_spec_template=Integer(),
                        prefill_levels_type=DefaultValue(LevelsType.NONE),
                        prefill_fixed_levels=DefaultValue((0, 0)),
                        help_text=Help(
                            "Normally, the Windows Time Service (being an NTP client) follows the NTP "
                            "convention of maintaining a 'reachability' register, which remembers the "
                            "result (success or failure) of the last (up to) 8 transactions with the "
                            "peer. This setting looks into the reachability register and checks for "
                            "consecutive, recent failures, alerting after too many consecutive "
                            "failures have occurred. "
                            "If reachability is 0, the 'resolve attempts' count reported by the "
                            "Windows Time Service is used instead to determine how many attempts "
                            "have been made."
                        ),
                    ),
                ),
                "reachability_total_failures": DictElement(
                    required=False,
                    parameter_form=SimpleLevels(
                        title=Title("Total reachability failures (up to 8)"),
                        level_direction=LevelDirection.UPPER,
                        form_spec_template=Integer(),
                        prefill_levels_type=DefaultValue(LevelsType.NONE),
                        prefill_fixed_levels=DefaultValue((0, 0)),
                        help_text=Help(
                            "Normally, the Windows Time service (being an NTP client) follows the NTP "
                            "convention of maintaining a 'reachability' register, which remembers the "
                            "result (success or failure) of the last (up to) 8 transactions with the "
                            "peer. This setting looks into the reachability register and counts the "
                            "total number of failed attempts, alerting when there have been too many. "
                            "If reachability is 0, the 'resolve attempts' count reported by the "
                            "Windows Time service is used instead to determine how many attempts "
                            "have been made."
                        ),
                    ),
                ),
                "stratum": DictElement(
                    required=False,
                    parameter_form=SimpleLevels(
                        title=Title("Stratum"),
                        level_direction=LevelDirection.UPPER,
                        form_spec_template=Integer(),
                        prefill_fixed_levels=DefaultValue((5, 5)),
                    ),
                ),
                **is_universal,
            },
        )

    return form


rule_spec_w32time_peers = CheckParameters(
    name="w32time_peers",
    title=Title("Windows Time service peers"),
    topic=Topic.WINDOWS,
    parameter_form=_make_form(False),
    condition=HostAndItemCondition(item_title=Title("Peer name")),
)


rule_spec_w32time_peers_summary = CheckParameters(
    name="w32time_peers_summary",
    title=Title("Windows time service peers summary"),
    topic=Topic.WINDOWS,
    parameter_form=_make_form(True),
    condition=HostCondition(),
)
