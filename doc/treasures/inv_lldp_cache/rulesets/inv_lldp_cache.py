#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2016-04-16

# 2023-06-14: moved wato file to check_parameters subdirectory
# 2025-03-23: moved to rulesets API v1

from cmk.rulesets.v1 import Label, Title
from cmk.rulesets.v1.form_specs import (
    DictElement,
    Dictionary,
    FixedValue,
    MultipleChoice,
    MultipleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, Message
from cmk.rulesets.v1.rule_specs import InventoryParameters, Topic


def _parameter_form_inv_lldp_cache():
    remove_columns = [
        MultipleChoiceElement(name='port_description', title=Title('Neighbour port description')),
        MultipleChoiceElement(name='system_description', title=Title('Neighbour description')),
        MultipleChoiceElement(name='capabilities_map_supported', title=Title('Capabilities map supported')),
        MultipleChoiceElement(name='capabilities', title=Title('Capabilities')),
    ]

    return Dictionary(
        elements={
            'remove_domain': DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title('Remove domain name from neighbour device name'),
                    label=Label('enabled'),
                )),
            'domain_name': DictElement(
                parameter_form=String(
                    title=Title('Specific domain name to remove from neighbour device name'),
                    custom_validate=(LengthInRange(min_value=1, error_msg=Message('This filed ca not be empty')),),
                )),
            'removecolumns': DictElement(
                parameter_form=MultipleChoice(
                    title=Title('Columns to remove'),
                    elements=remove_columns,
                )),
            'use_short_if_name': DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title('use short interface names (i.e. Gi0/0 for GigabitEthernet0/0)'),
                    label=Label('enabled'),
                )),
            'one_neighbour_per_port': DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title('Accept only one neighbour per local port'),
                    label=Label('enabled'),
                )),
        }
    )


rule_spec_inv_lldp_cache = InventoryParameters(
    name="inv_lldp_cache",
    parameter_form=_parameter_form_inv_lldp_cache,
    title=Title("LLDP cache"),
    topic=Topic.NETWORKING,
)
