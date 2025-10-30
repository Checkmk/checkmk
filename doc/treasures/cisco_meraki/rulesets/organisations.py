#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    SingleChoice,
    SingleChoiceElement,
)
from cmk.rulesets.v1.rule_specs import DiscoveryParameters, HostCondition, Topic


def _discovery_form() -> Dictionary:
    return Dictionary(
        elements={
            'item_variant': DictElement(
                parameter_form=SingleChoice(
                    title=Title('Information to use as item'),
                    help_text=Help(
                        'You can select how to build the item for this service. By default the Organization ID/name\n'
                        'is used to stay compatible with the build in check. The information not used for the item\n'
                        'will be added to the service output.'
                    ),
                    elements=[
                        SingleChoiceElement(
                            name='org_id',
                            title=Title('Organization ID')
                        ),
                        SingleChoiceElement(
                            name='org_name',
                            title=Title('Organization name')
                        ),
                        SingleChoiceElement(
                            name='org_id_name',
                            title=Title('Organization ID/name')
                        ),
                    ],
                    prefill=DefaultValue('org_id_name')
                ))
        }
    )


rule_spec_discovery_meraki_organisations = DiscoveryParameters(
    name="discovery_meraki_organisations",
    topic=Topic.NETWORKING,
    parameter_form=_discovery_form,
    title=Title("Cisco Meraki Organisation (API/Licenses)"),
)
