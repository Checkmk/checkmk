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
    ServiceState,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
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
                            "This checks consecutive sync failures within the last 8 attempts by "
                            "monitoring the 8-bit 'reachability' register within the Windows Time "
                            "service. It triggers a WARNING or CRITICAL alert when the <b>number of "
                            "consecutive failed attempts</b> exceeds the defined threshold. For "
                            "example, setting a threshold of 4 means that Checkmk will alert if the "
                            "<b>last</b> 4 of 8 attempts have consecutively failed."
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
                            "This checks consecutive sync failures within the last 8 attempts by "
                            "monitoring the 8-bit 'reachability' register within the Windows Time "
                            "service. It triggers a WARNING or CRITICAL alert when the <b>number of "
                            "total failed attempts</b> exceeds the defined threshold. For "
                            "example, setting a threshold of 4 means that Checkmk will alert if "
                            "<b>any</b> 4 of the last 8 attempts have failed."
                        ),
                    ),
                ),
                # The not-yet-synced case happens fairly regularly (e.g. after a
                # w32time restart), so we default to OK and only count the peer
                # as a failure after the levels below trip.
                "peer_never_synced_state": DictElement(
                    required=False,
                    parameter_form=ServiceState(
                        title=Title("State when peer has never synchronized"),
                        help_text=Help(
                            "The state to report when the peer has not yet synchronized (for "
                            "example, immediately after the w32time service has been restarted). "
                            "If the peer stays in this state for too long (configurable "
                            "using the levels below), an alert may be triggered. This time window "
                            "allows for restarting w32time and letting peers attempt to sync "
                            "rather than immediately alerting that they have not yet done so."
                        ),
                        prefill=DefaultValue(ServiceState.OK),
                    ),
                ),
                "peer_never_synced_levels": DictElement(
                    required=False,
                    parameter_form=SimpleLevels(
                        title=Title("Elapsed time never having synchronized"),
                        level_direction=LevelDirection.UPPER,
                        form_spec_template=TimeSpan(
                            displayed_magnitudes=[
                                TimeMagnitude.DAY,
                                TimeMagnitude.HOUR,
                                TimeMagnitude.MINUTE,
                                TimeMagnitude.SECOND,
                            ]
                        ),
                        help_text=Help(
                            "Determines how long a peer may remain in the never-synchronized "
                            "state before an alert is triggered. "
                            "This allows for, for example, restarting the Windows Time Service and "
                            "giving the configured peers a chance to synchronize before alerting."
                        ),
                        prefill_fixed_levels=DefaultValue(value=(10 * 60.0, 30 * 60.0)),
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
    title=Title("Windows Time service peers summary"),
    topic=Topic.WINDOWS,
    parameter_form=_make_form(True),
    condition=HostCondition(),
)
