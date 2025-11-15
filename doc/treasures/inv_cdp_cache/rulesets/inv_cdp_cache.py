#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2016-04-08
# File  : cmk_addons/plugins/inventory/rulesets/inv_cdp_cache.py

# 2023-02-17: moved from ~/local/share/check_mk/web/plugins/wato -> ~/local/lib/check_mk/gui/plugins/wato
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


def _migrate_remove_columns(value: object) -> object:
    if isinstance(value, list):
        if 'last_change' in value:
            value.remove('last_change')
    return value

def _migrate_inv_cdp_cache(value: object) -> object:
    if isinstance(value, dict):
        if 'removecolumns' in value.keys():
            if not value['removecolumns']:
                _not_used = value.pop('removecolumns')
    return value

_remove_columns = [
    MultipleChoiceElement(name='platform_details', title=Title('Neighbour platform details')),
    MultipleChoiceElement(name='capabilities', title=Title('Capabilities')),
    MultipleChoiceElement(name='vtp_mgmt_domain', title=Title('VTP domain')),
    MultipleChoiceElement(name='native_vlan', title=Title('Native VLAN')),
    MultipleChoiceElement(name='duplex', title=Title('Duplex')),
    MultipleChoiceElement(name='power_consumption', title=Title('Power level')),
    MultipleChoiceElement(name='platform', title=Title('Neighbour Platform')),
]


def _parameter_form_inv_cdp_cache() -> Dictionary:
    return Dictionary(
        migrate=_migrate_inv_cdp_cache,
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
                    custom_validate=[LengthInRange(min_value=1, error_msg=Message('This field can not be empty.'))],
                )),
            'removecolumns': DictElement(
                parameter_form=MultipleChoice(
                    title=Title('Columns to remove'),
                    elements=_remove_columns,
                    migrate=_migrate_remove_columns,
                    custom_validate=[LengthInRange(min_value=1, error_msg=Message('Select at least one column.'))],
                )),
            'use_short_if_name': DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title('Use short interface names (i.e. Gi0/0 for GigabitEthernet0/0)'),
                    label=Label('enabled'),
                )),
        })


rule_spec_inv_cdp_cache = InventoryParameters(
    name="inv_cdp_cache",
    parameter_form=_parameter_form_inv_cdp_cache,
    title=Title("CDP cache"),
    topic=Topic.NETWORKING,
)
