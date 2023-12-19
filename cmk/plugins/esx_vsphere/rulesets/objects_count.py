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
    ServiceState,
    TextInput,
    Topic,
)


def _parameter_form_esx_vsphere_objects_count() -> Dictionary:
    return Dictionary(
        elements={
            "distribution": DictElement(
                parameter_form=List(
                    parameter_form=Dictionary(
                        elements={
                            "vm_names": DictElement(
                                parameter_form=List(
                                    parameter_form=TextInput(), title=Localizable("VMs")
                                ),
                                required=True,
                            ),
                            "hosts_count": DictElement(
                                parameter_form=Integer(
                                    title=Localizable("Number of hosts"), prefill_value=2
                                ),
                                required=True,
                            ),
                            "state": DictElement(
                                parameter_form=ServiceState(
                                    title=Localizable("State if violated"),
                                    prefill_value=ServiceState.WARN,
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


rule_spec_esx_vsphere_objects_count = CheckParameterRuleSpecWithoutItem(
    name="esx_vsphere_objects_count",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_esx_vsphere_objects_count,
    title=Localizable("ESX hosts: distribution of virtual machines"),
)
