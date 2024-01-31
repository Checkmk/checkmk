#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Localizable
from cmk.rulesets.v1.form_specs.basic import Integer, Text, TimeSpan, TimeUnit
from cmk.rulesets.v1.form_specs.composed import DictElement, Dictionary, TupleDoNotUseWillbeRemoved
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _parameter_form_wlan_controllers_clients():
    return Dictionary(
        elements={
            "clients": DictElement(
                parameter_form=TupleDoNotUseWillbeRemoved(
                    title=Localizable("Maximum number of clients"),
                    elements=[
                        Integer(title=Localizable("Warning at")),
                        Integer(title=Localizable("Critical at")),
                    ],
                ),
            )
        },
    )


rule_spec_cisco_prime_wlan_controller_clients = CheckParameters(
    name="cisco_prime_wlan_controller_clients",
    topic=Topic.OPERATING_SYSTEM,
    condition=HostAndItemCondition(item_form=Text(title=Localizable("Clients"))),
    parameter_form=_parameter_form_wlan_controllers_clients,
    title=Localizable("Cisco Prime WLAN Controller Clients"),
)


def _parameter_form_wlan_controllers_access_points():
    return Dictionary(
        elements={
            "access_points": DictElement(
                parameter_form=TupleDoNotUseWillbeRemoved(
                    title=Localizable("Maximum number of access points"),
                    elements=[
                        Integer(title=Localizable("Warning at")),
                        Integer(title=Localizable("Critical at")),
                    ],
                ),
            ),
        },
    )


rule_spec_cisco_prime_wlan_controller_access_points = CheckParameters(
    name="cisco_prime_wlan_controller_access_points",
    topic=Topic.OPERATING_SYSTEM,
    condition=HostAndItemCondition(item_form=Text(title=Localizable("Access points"))),
    parameter_form=_parameter_form_wlan_controllers_access_points,
    title=Localizable("Cisco Prime WLAN Controller Access Points"),
)


def _parameter_form_wlan_controllers_last_backup():
    return Dictionary(
        elements={
            "last_backup": DictElement(
                parameter_form=TupleDoNotUseWillbeRemoved(
                    title=Localizable("Time since last backup"),
                    elements=[
                        TimeSpan(
                            title=Localizable("Warning at"),
                            displayed_units=[
                                TimeUnit.DAYS,
                                TimeUnit.HOURS,
                                TimeUnit.MINUTES,
                            ],
                            prefill_value=7 * 24 * 3600,
                        ),
                        TimeSpan(
                            title=Localizable("Critical at"),
                            displayed_units=[
                                TimeUnit.DAYS,
                                TimeUnit.HOURS,
                                TimeUnit.MINUTES,
                            ],
                            prefill_value=30 * 24 * 3600,
                        ),
                    ],
                ),
            )
        },
    )


rule_spec_cisco_prime_wlan_controller_last_backup = CheckParameters(
    name="cisco_prime_wlan_controller_last_backup",
    topic=Topic.OPERATING_SYSTEM,
    condition=HostAndItemCondition(item_form=Text(title=Localizable("Last backup"))),
    parameter_form=_parameter_form_wlan_controllers_last_backup,
    title=Localizable("Cisco Prime WLAN Controller Last Backup"),
)
