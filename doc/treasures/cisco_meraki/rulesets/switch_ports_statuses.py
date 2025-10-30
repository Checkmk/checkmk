#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2024-02-02
# File  : cisco_meraki_switch_ports_statuses.py (WATO)

# 2024-05-12: added support for MerakiGetOrganizationSwitchPortsStatusesBySwitch (Early Access)
#             added traffic counters as perfdata
# 2024-05-19: reworked switch port traffic
# 2024-05-20: added discovery rule for port status
# 2024-06-27: refactored for CMK 2.3
# 2024-06-30: renamed from cisco_meraki_switch_ports_statuses.py in to switch_ports_statuses.py
#             added params from discovery as render only
# 2024-11-17: incompatible change to match changed port status check -> recreate your discovery rule
# 2024-11-23: added missing discovery parameters admin_state and operational_state
#             removed discovery parameters 'enabled' and 'status'
#             reference to section organization_switch_ports removed, missing traffic, lldp, cdp, stp, ...

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
