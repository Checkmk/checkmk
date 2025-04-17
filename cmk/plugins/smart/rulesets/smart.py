#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    InputHint,
    Integer,
    LevelDirection,
    SimpleLevels,
)
from cmk.rulesets.v1.rule_specs import (
    CheckParameters,
    DiscoveryParameters,
    HostAndItemCondition,
    Topic,
)


def _formspec_discovery_smart() -> Dictionary:
    return Dictionary(
        title=Title("Service discovery"),
        elements={
            "item_type": DictElement(
                required=False,
                parameter_form=CascadingSingleChoice(
                    title=Title("Select the type of item to discover"),
                    prefill=DefaultValue(value="model_serial"),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="model_serial",
                            title=Title("Model - Serial"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="device_name",
                            title=Title("Device name"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                ),
            ),
        },
    )


rule_spec_smart_ata_discovery = DiscoveryParameters(
    title=Title("SMART ATA discovery"),
    topic=Topic.STORAGE,
    parameter_form=_formspec_discovery_smart,
    name="smart_ata",
)

rule_spec_smart_nvme_discovery = DiscoveryParameters(
    title=Title("SMART NVMe discovery"),
    topic=Topic.STORAGE,
    parameter_form=_formspec_discovery_smart,
    name="smart_nvme",
)

rule_spec_smart_scsi_discovery = DiscoveryParameters(
    title=Title("SMART SCSI discovery"),
    topic=Topic.STORAGE,
    parameter_form=_formspec_discovery_smart,
    name="smart_scsi",
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
                            parameter_form=SimpleLevels(
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
                            parameter_form=SimpleLevels(
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
                            parameter_form=SimpleLevels(
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
                            parameter_form=SimpleLevels(
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
                            parameter_form=SimpleLevels(
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
                            parameter_form=SimpleLevels(
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
                            parameter_form=SimpleLevels(
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
            "key",
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
    title=Title("SMART ATA"),
    topic=Topic.STORAGE,
    parameter_form=_parameter_valuespec_smart_ata,
    condition=HostAndItemCondition(item_title=Title("Disk")),
)
