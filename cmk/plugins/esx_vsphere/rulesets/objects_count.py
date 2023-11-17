#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import (
    CheckParameterRuleSpecWithoutItem,
    DictElement,
    Dictionary,
    Integer,
    List,
    Localizable,
    MonitoringState,
    State,
    TextInput,
    Topic,
)


def _parameter_valuespec_esx_vsphere_objects_count():
    return Dictionary(
        elements={
            "distribution": DictElement(
                value_spec=List(
                    value_spec=Dictionary(
                        elements={
                            "vm_names": DictElement(
                                value_spec=List(value_spec=TextInput(), title=Localizable("VMs")),
                                required=True,
                            ),
                            "hosts_count": DictElement(
                                value_spec=Integer(
                                    title=Localizable("Number of hosts"), prefill_value=2
                                ),
                                required=True,
                            ),
                            "state": DictElement(
                                value_spec=MonitoringState(
                                    title=Localizable("State if violated"), prefill_value=State.WARN
                                ),
                                required=True,
                            ),
                        },
                    ),
                    title=Localizable("VM distribution"),
                    help_text=Localizable(
                        "You can specify lists of VM names and a number of hosts,"
                        " to make sure the specified VMs are distributed across at least so many hosts."
                        " E.g. provide two VM names and set 'Number of hosts' to two,"
                        " to make sure those VMs are not running on the same host."
                    ),
                ),
                required=True,
            ),
        },
    )


rulespec_esx_vsphere_objects_count = CheckParameterRuleSpecWithoutItem(
    name="esx_vsphere_objects_count",
    topic=Topic.APPLICATIONS,
    value_spec=_parameter_valuespec_esx_vsphere_objects_count,
    title=Localizable("ESX hosts: distribution of virtual machines"),
)
