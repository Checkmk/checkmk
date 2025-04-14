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
)
from cmk.rulesets.v1.rule_specs import (
    DiscoveryParameters,
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
