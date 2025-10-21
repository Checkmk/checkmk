#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _make_form() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "This check monitors the status of a peer configured in the Windows Time Service."
        ),
        elements={
            "reachability_consecutive_failures": DictElement(
                required=False,
                parameter_form=SimpleLevels(
                    title=Title("Consecutive reachability failures (up to 8)"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=DefaultValue((4, 6)),
                    help_text=Help(
                        "Normally, the Windows Time Service (being an NTP client) follows the NTP "
                        "convention of maintaining a 'reachbility' register, which remembers the "
                        "result (success or failure) of the last (up to) 8 transactions with the "
                        "peer. This setting looks into the reachability register and checks for "
                        "consecutive, recent failures, alerting after too many consecutive "
                        "failures have occurred. "
                        "If reachability is 0, the 'Resolve Attempts' count reported by the "
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
                    prefill_fixed_levels=DefaultValue((4, 6)),
                    help_text=Help(
                        "Normally, the Windows Time Service (being an NTP client) follows the NTP "
                        "convention of maintaining a 'reachbility' register, which remembers the "
                        "result (success or failure) of the last (up to) 8 transactions with the "
                        "peer. This setting looks into the reachability register and counts the "
                        "total number of failed attempts, alerting when there have been too many. "
                        "If reachability is 0, the 'Resolve Attempts' count reported by the "
                        "Windows Time Service is used instead to determine how many attempts "
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
                    prefill_fixed_levels=DefaultValue((5, 10)),
                ),
            ),
        },
    )


rule_spec_w32time_peers = CheckParameters(
    name="w32time_peers",
    title=Title("Windows time service peers"),
    topic=Topic.WINDOWS,
    parameter_form=_make_form,
    condition=HostAndItemCondition(item_title=Title("Peer name")),
)
