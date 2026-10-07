#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    LevelDirection,
    migrate_to_float_simple_levels,
    migrate_to_integer_simple_levels,
    Percentage,
    SimpleLevels,
    TimeMagnitude,
    TimeSpan,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _migrate_handle_levels(model: object) -> Mapping[str, object]:
    # Both levels used to be optional.
    if not isinstance(model, dict):
        raise TypeError(f"Expected lower and upper levels, got {model!r}")
    return {
        "lower": migrate_to_integer_simple_levels(model.get("lower")),
        "upper": migrate_to_integer_simple_levels(model.get("upper")),
    }


def _handle_levels(title: Title, help_text: Help) -> Dictionary:
    return Dictionary(
        title=title,
        help_text=help_text,
        elements={
            "lower": DictElement(
                required=True,
                parameter_form=SimpleLevels[int](
                    title=Title("Lower levels"),
                    level_direction=LevelDirection.LOWER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
            "upper": DictElement(
                required=True,
                parameter_form=SimpleLevels[int](
                    title=Title("Upper levels"),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(),
                    prefill_fixed_levels=InputHint((0, 0)),
                ),
            ),
        },
        migrate=_migrate_handle_levels,
    )


def _age_levels(title: Title, help_text: Help) -> SimpleLevels[float]:
    return SimpleLevels[float](
        title=title,
        help_text=help_text,
        level_direction=LevelDirection.UPPER,
        form_spec_template=TimeSpan(
            displayed_magnitudes=[
                TimeMagnitude.DAY,
                TimeMagnitude.HOUR,
                TimeMagnitude.MINUTE,
                TimeMagnitude.SECOND,
            ]
        ),
        prefill_fixed_levels=InputHint((0.0, 0.0)),
        migrate=migrate_to_float_simple_levels,
    )


def _parameter_form_ibm_mq_queues() -> Dictionary:
    return Dictionary(
        help_text=Help(
            "See 'Queue status attributes' in IBM manual"
            "(https://www.ibm.com/support/knowledgecenter/en/SSFKSJ_9.2.0/com.ibm.mq.explorer.doc/e_status_queue.html)"
            " for detailed explanations of these parameters."
        ),
        elements={
            "curdepth": DictElement(
                parameter_form=SimpleLevels[int](
                    title=Title("Current queue depth"),
                    help_text=Help("CURDEPTH: the number of messages currently on the queue."),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Integer(unit_symbol="messages"),
                    prefill_fixed_levels=InputHint((0, 0)),
                    migrate=migrate_to_integer_simple_levels,
                ),
            ),
            "curdepth_perc": DictElement(
                parameter_form=SimpleLevels[float](
                    title=Title("Current queue depth in %"),
                    help_text=Help(
                        "CURDEPTH_PERC: percentage (CURDEPTH/MAXDEPTH) of the number of"
                        " messages currently on the queue."
                    ),
                    level_direction=LevelDirection.UPPER,
                    form_spec_template=Percentage(),
                    prefill_fixed_levels=DefaultValue((80.0, 90.0)),
                    migrate=migrate_to_float_simple_levels,
                ),
            ),
            "msgage": DictElement(
                parameter_form=_age_levels(
                    Title("Oldest message age"),
                    Help("MSGAGE: The age, in seconds, of the oldest message on the queue."),
                ),
            ),
            "lgetage": DictElement(
                parameter_form=_age_levels(
                    Title("Last get age"),
                    Help(
                        "The age, in seconds, when the last message was retrieved from the queue."
                        " Calculated by subtracting LGETDATE/LGETTIME from current timestamp."
                    ),
                ),
            ),
            "lputage": DictElement(
                parameter_form=_age_levels(
                    Title("Last put age"),
                    Help(
                        "The age, in seconds, when the last message was put to the queue."
                        " Calculated by subtracting LPUTDATE/LPUTTIME from current timestamp."
                    ),
                ),
            ),
            "ipprocs": DictElement(
                parameter_form=_handle_levels(
                    Title("Open input count"),
                    Help(
                        "IPPROCS: The number of applications that are currently connected to"
                        " the queue to get messages from the queue."
                    ),
                ),
            ),
            "opprocs": DictElement(
                parameter_form=_handle_levels(
                    Title("Open output count"),
                    Help(
                        "OPPROCS: The number of applications that are currently connected"
                        " to the queue to put messages on the queue."
                    ),
                ),
            ),
        },
    )


rule_spec_ibm_mq_queues = CheckParameters(
    name="ibm_mq_queues",
    title=Title("IBM MQ queues"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_ibm_mq_queues,
    condition=HostAndItemCondition(item_title=Title("Name of queue")),
)
