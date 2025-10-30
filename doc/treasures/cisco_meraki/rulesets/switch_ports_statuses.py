#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Original author: thl-cmk[at]outlook[dot]com

from cmk.rulesets.v1 import Label, Title, Help
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    ServiceState,
    MultipleChoice,
    MultipleChoiceElement,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, DiscoveryParameters, HostAndItemCondition, Topic


def _parameter_form():
    return Dictionary(
        elements={
            'state_disabled': DictElement(
                parameter_form=ServiceState(
                    title=Title('Monitoring state if port is "disabled"'),
                    prefill=DefaultValue(ServiceState.OK),
                )),
            'state_not_connected': DictElement(
                parameter_form=ServiceState(
                    title=Title('Monitoring state if port is "not connected"'),
                    prefill=DefaultValue(ServiceState.OK),
                )),
            'state_not_full_duplex': DictElement(
                parameter_form=ServiceState(
                    title=Title('Monitoring state if port is "not full duplex"'),
                    prefill=DefaultValue(ServiceState.WARN),
                )),
            'state_speed_change': DictElement(
                parameter_form=ServiceState(
                    title=Title('Monitoring state if speed has changed'),
                    prefill=DefaultValue(ServiceState.WARN),
                )),
            'state_admin_change': DictElement(
                parameter_form=ServiceState(
                    title=Title('Monitoring state if admin state has changed'),
                    prefill=DefaultValue(ServiceState.WARN),
                )),
            'state_op_change': DictElement(
                parameter_form=ServiceState(
                    title=Title('Monitoring state if operational state has changed'),
                    prefill=DefaultValue(ServiceState.WARN),
                )),
            'show_traffic': DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title('Show bandwidth (use only with cache disabled)'),
                    label=Label('Bandwidth monitoring enabled'),
                    help_text=Help(
                        'Use only with cache disabled in the Meraki special agent settings. '
                        'Depending on your Meraki organization size (in terms of number of switches) '
                        'this will exceeds the limits of the allowed API requests per second.'
                    ),
                )),
            # params from discovery
            'admin_state': DictElement(
                render_only=True,
                parameter_form=String(
                    title=Title('Discovered admin state')
                )
            ),
            'operational_state': DictElement(
                render_only=True,
                parameter_form=String(
                    title=Title('Discovered operational state')
                )
            ),
            'speed': DictElement(
                render_only=True,
                parameter_form=String(
                    title=Title('Discovered speed')
                )
            ),
        },
    )


rule_spec_cisco_meraki_switch_ports_statuses = CheckParameters(
    name="cisco_meraki_switch_ports_statuses",
    topic=Topic.NETWORKING,
    parameter_form=_parameter_form,
    title=Title("Cisco Meraki Switch Ports"),
    condition=HostAndItemCondition(item_title=Title('Port ID')),
)


def _discovery_form():
    return Dictionary(
        elements={
            'operational_port_states': DictElement(
                parameter_form=MultipleChoice(
                    title=Title('Match port states'),
                    elements=[
                        MultipleChoiceElement(
                            title=Title('1 - up'),
                            name='up',
                        ),
                        MultipleChoiceElement(
                            title=Title('2 - down'),
                            name='down',
                        ),
                    ],
                    help_text=Help('Apply this rule only to interfaces whose port state is listed below.'),
                    prefill=DefaultValue([
                        'up',
                        'down',
                    ])
                )),
            'admin_port_states': DictElement(
                parameter_form=MultipleChoice(
                    title=Title('Match admin states'),
                    elements=[
                        MultipleChoiceElement(
                            title=Title('1 - up'),
                            name='up',
                        ),
                        MultipleChoiceElement(
                            title=Title('2 - down'),
                            name='down',
                        ),
                    ],
                    help_text=Help('Apply this rule only to interfaces whose admin state is listed below'),
                    prefill=DefaultValue([
                        'up',
                        'down',
                    ])
                )),
        },
    )


rule_spec_cisco_meraki_switch_ports_statuses_discovery = DiscoveryParameters(
    name="discovery_cisco_meraki_switch_ports_statuses",
    topic=Topic.NETWORKING,
    parameter_form=_discovery_form,
    title=Title("Cisco Meraki Switch Ports"),
)
