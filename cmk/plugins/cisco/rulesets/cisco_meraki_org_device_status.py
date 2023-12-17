#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2023-11-04
# File  : cisco_meraki_org_device_status.py (WATO)

# 2023-12-03: moved to CMK 2.3 API v2
# 2012-12-17: splitt device status and power supply

from cmk.rulesets.v1 import (
    CheckParameterRuleSpecWithoutItem,
    DictElement,
    Dictionary,
    Integer,
    Localizable,
    MonitoringState,
    State,
    Topic,
    Tuple,
)


#
# Cisco Meraki Device Status
#
def _parameter_form_cisco_meraki_device_status():
    return Dictionary(
        elements={
            "last_reported_upper_levels": DictElement(
                parameter_form=Tuple(
                    title=Localizable("Max time for last reported"),
                    elements=[
                        Integer(
                            title=Localizable("Warning at"),
                            unit=Localizable("hours"),
                            prefill_value=2,
                            # missing size=5 minvalue=0
                        ),
                        Integer(
                            title=Localizable("Critical at"),
                            unit=Localizable("hours"),
                            prefill_value=3,
                            # missing size=5 minvalue=0
                        ),
                    ],
                )
            ),
            "status_map": DictElement(
                parameter_form=Dictionary(
                    title=Localizable("Map device status to monitoring state"),
                    elements={
                        "online": DictElement(
                            parameter_form=MonitoringState(
                                title=Localizable('Monitoring state for device state "online"'),
                                prefill_value=State.OK,
                            )
                        ),
                        "alerting": DictElement(
                            parameter_form=MonitoringState(
                                title=Localizable('Monitoring state for device state "alerting"'),
                                prefill_value=State.CRIT,
                            )
                        ),
                        "offline": DictElement(
                            parameter_form=MonitoringState(
                                title=Localizable('Monitoring state for device state "offline"'),
                                prefill_value=State.WARN,
                            )
                        ),
                        "dormant": DictElement(
                            parameter_form=MonitoringState(
                                title=Localizable('Monitoring state for device state "dormant"'),
                                prefill_value=State.WARN,
                            )
                        ),
                    },
                )
            ),
        },
    )


rule_spec_cisco_meraki_device_status = CheckParameterRuleSpecWithoutItem(
    name="cisco_meraki_org_device_status",
    topic=Topic.APPLICATIONS,  # missing HARDWARE
    # group=RulespecGroupCheckParametersHardware,
    parameter_form=_parameter_form_cisco_meraki_device_status,
    title=Localizable("Cisco Meraki Device status"),
)
