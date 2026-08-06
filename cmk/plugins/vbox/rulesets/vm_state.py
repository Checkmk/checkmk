#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.rule_specs import EnforcedService, HostCondition, Topic

rule_spec_vm_state = EnforcedService(
    name="vm_state",
    title=Title("Overall state of a virtual machine (for example ESX VMs)"),
    topic=Topic.VIRTUALIZATION,
    parameter_form=None,
    condition=HostCondition(),
)
