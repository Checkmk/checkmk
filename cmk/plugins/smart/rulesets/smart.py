#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DataSize,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    IECMagnitude,
    InputHint,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    HostAndItemCondition,
    Topic,
)


def _parameter_valuespec_smart_ata() -> Dictionary:
    return Dictionary(
        elements={
            "levels_5": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Reallocated sectors (id 5)"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="levels_upper",
                            title=Title("Configure levels"),
                            parameter_form=SimpleLevels[int](
                                form_spec_template=Integer(unit_symbol=""),
                                level_direction=LevelDirection.UPPER,
                                prefill_fixed_levels=InputHint((1, 1)),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="discovered_value",
                            title=Title("Alert if value has increased since discovery"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue(value="levels_upper"),
                ),
            ),
            "levels_10": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Spin retries (id 10)"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="levels_upper",
                            title=Title("Configure levels"),
                            parameter_form=SimpleLevels[int](
                                form_spec_template=Integer(unit_symbol=""),
                                level_direction=LevelDirection.UPPER,
                                prefill_fixed_levels=InputHint((1, 1)),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="discovered_value",
                            title=Title("Alert if value has increased since discovery"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue(value="levels_upper"),
                ),
            ),
            "levels_184": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("End-to-End Errors (id 184)"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="levels_upper",
                            title=Title("Configure levels"),
                            parameter_form=SimpleLevels[int](
                                form_spec_template=Integer(unit_symbol=""),
                                level_direction=LevelDirection.UPPER,
                                prefill_fixed_levels=InputHint((1, 1)),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="discovered_value",
                            title=Title("Alert if value has increased since discovery"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue(value="levels_upper"),
                ),
            ),
            "levels_187": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Uncorrectable Errors (id 187)"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="levels_upper",
                            title=Title("Configure levels"),
                            parameter_form=SimpleLevels[int](
                                form_spec_template=Integer(unit_symbol=""),
                                level_direction=LevelDirection.UPPER,
                                prefill_fixed_levels=InputHint((1, 1)),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="discovered_value",
                            title=Title("Alert if value has increased since discovery"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue(value="levels_upper"),
                ),
            ),
            "levels_196": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Reallocated events (id 196)"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="levels_upper",
                            title=Title("Configure levels"),
                            parameter_form=SimpleLevels[int](
                                form_spec_template=Integer(unit_symbol=""),
                                level_direction=LevelDirection.UPPER,
                                prefill_fixed_levels=InputHint((1, 1)),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="discovered_value",
                            title=Title("Alert if value has increased since discovery"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue(value="levels_upper"),
                ),
            ),
            "levels_197": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Pending sectors (id 197)"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="levels_upper",
                            title=Title("Configure levels"),
                            parameter_form=SimpleLevels[int](
                                form_spec_template=Integer(unit_symbol=""),
                                level_direction=LevelDirection.UPPER,
                                prefill_fixed_levels=InputHint((1, 1)),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="discovered_value",
                            title=Title("Alert if value has increased since discovery"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue(value="levels_upper"),
                ),
            ),
            "levels_199": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("CRC errors (id 199)"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="levels_upper",
                            title=Title("Configure levels"),
                            parameter_form=SimpleLevels[int](
                                form_spec_template=Integer(unit_symbol=""),
                                level_direction=LevelDirection.UPPER,
                                prefill_fixed_levels=InputHint((1, 1)),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="discovered_value",
                            title=Title("Alert if value has increased since discovery"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue(value="levels_upper"),
                ),
            ),
        },
        ignored_elements=(  # to render `AtaDiscoveredParams` correctly
            "id_5",
            "id_10",
            "id_184",
            "id_187",
            "id_188",
            "id_196",
            "id_197",
            "id_199",
        ),
    )


rule_spec_smart_ata = CheckParameters(
    name="smart_ata",
    title=Title("SMART ATA (incompatible with legacy plug-in)"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_valuespec_smart_ata,
    condition=HostAndItemCondition(item_title=Title("Disk")),
)


def _parameter_valuespec_smart_nvme() -> Dictionary:
    return Dictionary(
        elements={
            "levels_critical_warning": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Critical warning"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="levels_upper",
                            title=Title("Configure levels"),
                            parameter_form=SimpleLevels[int](
                                form_spec_template=Integer(unit_symbol=""),
                                level_direction=LevelDirection.UPPER,
                                prefill_fixed_levels=InputHint((1, 1)),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="discovered_value",
                            title=Title("Alert if value has increased since discovery"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue(value="levels_upper"),
                ),
            ),
            "levels_media_errors": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Media and data integrity errors"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="levels_upper",
                            title=Title("Configure levels"),
                            parameter_form=SimpleLevels[int](
                                form_spec_template=Integer(unit_symbol=""),
                                level_direction=LevelDirection.UPPER,
                                prefill_fixed_levels=InputHint((1, 1)),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="discovered_value",
                            title=Title("Alert if value has increased since discovery"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue(value="levels_upper"),
                ),
            ),
            "levels_available_spare": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Available spare"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="levels_lower",
                            title=Title("Configure levels"),
                            parameter_form=SimpleLevels[int](
                                form_spec_template=Integer(unit_symbol="%"),
                                level_direction=LevelDirection.LOWER,
                                prefill_fixed_levels=InputHint((20, 10)),
                            ),
                        ),
                        CascadingSingleChoiceElement(
                            name="threshold",
                            title=Title("Use the threshold reported by the device"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue(value="levels_lower"),
                ),
            ),
            "levels_spare_percentage_used": DictElement(
                required=False,
                parameter_form=SimpleLevels[int](
                    title=Title("Percentage used"),
                    form_spec_template=Integer(unit_symbol="%"),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((80, 90)),
                ),
            ),
            "levels_error_information_log_entries": DictElement(
                required=False,
                parameter_form=SimpleLevels[int](
                    title=Title("Error information log entries"),
                    form_spec_template=Integer(unit_symbol=""),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((1, 1)),
                ),
            ),
            "levels_data_units_read": DictElement(
                required=False,
                parameter_form=SimpleLevels[int](
                    title=Title("Data units read"),
                    form_spec_template=DataSize(
                        displayed_magnitudes=[
                            IECMagnitude.TEBI,
                            IECMagnitude.PEBI,
                            IECMagnitude.EXBI,
                        ]
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((1200 * 2**40, 2400 * 2**40)),
                ),
            ),
            "levels_data_units_written": DictElement(
                required=False,
                parameter_form=SimpleLevels[int](
                    title=Title("Data units written"),
                    form_spec_template=DataSize(
                        displayed_magnitudes=[
                            IECMagnitude.TEBI,
                            IECMagnitude.PEBI,
                            IECMagnitude.EXBI,
                        ]
                    ),
                    level_direction=LevelDirection.UPPER,
                    prefill_fixed_levels=InputHint((800 * 2**40, 1600 * 2**40)),
                ),
            ),
        },
        ignored_elements=(  # to render `NVMeDiscoveredParams` correctly
            "critical_warning",
            "media_errors",
        ),
    )


rule_spec_smart_nvme = CheckParameters(
    name="smart_nvme",
    title=Title("SMART NVMe (incompatible with legacy plug-in)"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_valuespec_smart_nvme,
    condition=HostAndItemCondition(item_title=Title("Disk")),
)
