#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes
from cmk.base.plugins.agent_based.lnx_cpuinfo import (
    inventory_lnx_cpuinfo,
    parse_lnx_cpuinfo,
    Section,
)

OUTPUT_1 = """processor:0
vendor_id:AuthenticAMD
cpu family:15
model:6
model name:Common KVM processor
stepping:1
microcode:0x1000065
cpu MHz:2799.998
cache size:512 KB
physical id:0
siblings:2
core id:0
cpu cores:2
apicid:0
initial apicid:0
fpu:yes
fpu_exception:yes
cpuid level:13
wp:yes
flags:fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx lm rep_good nopl cpuid extd_apicid tsc_known_freq pni cx16 x2apic hypervisor cmp_legacy 3dnowprefetch vmmcall
bugs:fxsave_leak sysret_ss_attrs null_seg swapgs_fence spectre_v1 spectre_v2
bogomips:5599.99
TLB size:1024 4K pages
clflush size:64
cache_alignment:64
address sizes:40 bits physical, 48 bits virtual
power management:

processor:1
vendor_id:AuthenticAMD
cpu family:15
model:6
model name:Common KVM processor
stepping:1
microcode:0x1000065
cpu MHz:2799.998
cache size:512 KB
physical id:0
siblings:2
core id:1
cpu cores:2
apicid:1
initial apicid:1
fpu:yes
fpu_exception:yes
cpuid level:13
wp:yes
flags:fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx lm rep_good nopl cpuid extd_apicid tsc_known_freq pni cx16 x2apic hypervisor cmp_legacy 3dnowprefetch vmmcall
bugs:fxsave_leak sysret_ss_attrs null_seg swapgs_fence spectre_v1 spectre_v2
bogomips:5599.99
TLB size:1024 4K pages
clflush size:64
cache_alignment:64
address sizes:40 bits physical, 48 bits virtual
power management:

processor:2
vendor_id:AuthenticAMD
cpu family:15
model:6
model name:Common KVM processor
stepping:1
microcode:0x1000065
cpu MHz:2799.998
cache size:512 KB
physical id:1
siblings:2
core id:0
cpu cores:2
apicid:2
initial apicid:2
fpu:yes
fpu_exception:yes
cpuid level:13
wp:yes
flags:fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx lm rep_good nopl cpuid extd_apicid tsc_known_freq pni cx16 x2apic hypervisor cmp_legacy 3dnowprefetch vmmcall
bugs:fxsave_leak sysret_ss_attrs null_seg swapgs_fence spectre_v1 spectre_v2
bogomips:5599.99
TLB size:1024 4K pages
clflush size:64
cache_alignment:64
address sizes:40 bits physical, 48 bits virtual
power management:

processor:3
vendor_id:AuthenticAMD
cpu family:15
model:6
model name:Common KVM processor
stepping:1
microcode:0x1000065
cpu MHz:2799.998
cache size:512 KB
physical id:1
siblings:2
core id:1
cpu cores:2
apicid:3
initial apicid:3
fpu:yes
fpu_exception:yes
cpuid level:13
wp:yes
flags:fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx lm rep_good nopl cpuid extd_apicid tsc_known_freq pni cx16 x2apic hypervisor cmp_legacy 3dnowprefetch vmmcall
bugs:fxsave_leak sysret_ss_attrs null_seg swapgs_fence spectre_v1 spectre_v2
bogomips:5599.99
TLB size:1024 4K pages
clflush size:64
cache_alignment:64
address sizes:40 bits physical, 48 bits virtual
power management:

processor:4
vendor_id:AuthenticAMD
cpu family:15
model:6
model name:Common KVM processor
stepping:1
microcode:0x1000065
cpu MHz:2799.998
cache size:512 KB
physical id:2
siblings:2
core id:0
cpu cores:2
apicid:4
initial apicid:4
fpu:yes
fpu_exception:yes
cpuid level:13
wp:yes
flags:fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx lm rep_good nopl cpuid extd_apicid tsc_known_freq pni cx16 x2apic hypervisor cmp_legacy 3dnowprefetch vmmcall
bugs:fxsave_leak sysret_ss_attrs null_seg swapgs_fence spectre_v1 spectre_v2
bogomips:5599.99
TLB size:1024 4K pages
clflush size:64
cache_alignment:64
address sizes:40 bits physical, 48 bits virtual
power management:

processor:5
vendor_id:AuthenticAMD
cpu family:15
model:6
model name:Common KVM processor
stepping:1
microcode:0x1000065
cpu MHz:2799.998
cache size:512 KB
physical id:2
siblings:2
core id:1
cpu cores:2
apicid:5
initial apicid:5
fpu:yes
fpu_exception:yes
cpuid level:13
wp:yes
flags:fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ht syscall nx lm rep_good nopl cpuid extd_apicid tsc_known_freq pni cx16 x2apic hypervisor cmp_legacy 3dnowprefetch vmmcall
bugs:fxsave_leak sysret_ss_attrs null_seg swapgs_fence spectre_v1 spectre_v2
bogomips:5599.99
TLB size:1024 4K pages
clflush size:64
cache_alignment:64
address sizes:40 bits physical, 48 bits virtual
power management:
"""


@pytest.fixture(scope="module", name="section_1")
def _get_info_1():
    return parse_lnx_cpuinfo([line.split(":") for line in OUTPUT_1.split("\n") if line.strip()])


def test_inventory_lnx_cpuinfo(section_1: Section) -> None:
    assert list(inventory_lnx_cpuinfo(section_1)) == [
        Attributes(
            path=["hardware", "cpu"],
            inventory_attributes={
                "vendor": "amd",
                "model": "Common KVM processor",
                "cache_size": 524288,
                "threads_per_cpu": 2,
                "cores_per_cpu": 2,
                "arch": "x86_64",
                "cores": 6,
                "threads": 6,
                "cpus": 3,
            },
        ),
    ]
