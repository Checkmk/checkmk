#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    Integer,
    List,
    ServiceState,
    String,
)
from cmk.rulesets.v1.rule_specs import CheckParameters, HostCondition, Topic


def _parameter_form_esx_vsphere_objects_count() -> Dictionary:
    return Dictionary(
        elements={
            "distribution": DictElement(
                parameter_form=List(
                    element_template=Dictionary(
                        elements={
                            "vm_names": DictElement(
                                parameter_form=List(
                                    element_template=String(), title=Title("VMs / Templates")
                                ),
                                required=True,
                            ),
                            "hosts_count": DictElement(
                                parameter_form=Integer(
                                    title=Title("Number of hosts"), prefill=DefaultValue(2)
                                ),
                                required=True,
                            ),
                            "state": DictElement(
                                parameter_form=ServiceState(
                                    title=Title("State if violated"),
                                    prefill=DefaultValue(ServiceState.WARN),
                                ),
                                required=True,
                            ),
                        },
                    ),
                    title=Title("VM distribution"),
                    help_text=Help(
                        "You can specify lists of VM or template names and a number of hosts,"
                        " to make sure the specified VMs are distributed across at least so many hosts."
                        " E.g. provide two VM names and set 'Number of hosts' to two,"
                        " to make sure those VMs are not running on the same host."
                    ),
                ),
                required=True,
            ),
        },
    )


rule_spec_esx_vsphere_objects_count = CheckParameters(
    name="esx_vsphere_objects_count",
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_esx_vsphere_objects_count,
    title=Title("ESX hosts: distribution of virtual machines"),
    condition=HostCondition(),
)
