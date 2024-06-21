#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.hpux.agent_based import lvm

_TEST_RAW = """
vg_name=/dev/vg00:vg_write_access=read,write:vg_status=available:max_lv=255:\
cur_lv=8:open_lv=8:max_pv=16:cur_pv=4:act_pv=4:max_pe_per_pv=4384:vgda=8:pe_size=16:to
tal_pe=17388:alloc_pe=13920:free_pe=3468:total_pvg=0:total_spare_pvs=0:total_spare_pvs_in_use=0:vg_version=1.0.0
lv_name=/dev/vg00/lvol1:lv_status=available,syncd:lv_size=1792:current_le=112:allocated_pe=224:used_pv=2
lv_name=/dev/vg00/lvol2:lv_status=available,syncd,snapshot,space_efficient:lv_size=32768:current_le=2048:allocated_pe=4096:used_pv=2
lv_name=/dev/vg00/lvol3:lv_status=available,syncd,possesssed_by_demon:lv_size=2048:current_le=128:allocated_pe=256:used_pv=2
lv_name=/dev/vg00/lvol4:lv_status=available,syncd:lv_size=32768:current_le=2048:allocated_pe=4096:used_pv=2
lv_name=/dev/vg00/lvol5:lv_status=available,syncd:lv_size=12288:current_le=768:allocated_pe=1536:used_pv=2
lv_name=/dev/vg00/lvol6:lv_status=available,syncd:lv_size=5120:current_le=320:allocated_pe=640:used_pv=2
lv_name=/dev/vg00/lvol7:lv_status=available,syncd:lv_size=12288:current_le=768:allocated_pe=1536:used_pv=2
lv_name=/dev/vg00/lvol8:lv_status=available,syncd:lv_size=12288:current_le=768:allocated_pe=1536:used_pv=3
pv_name=/dev/disk/disk7_p2:pv_status=available:total_pe=4319:free_pe=0:autoswitch=On:proactive_polling=On
pv_name=/dev/disk/disk9:pv_status=available:total_pe=4375:free_pe=1734:autoswitch=On:proactive_polling=On
pv_name=/dev/disk/disk11_p2:pv_status=available:total_pe=4319:free_pe=175:autoswitch=On:proactive_polling=On
pv_name=/dev/disk/disk10:pv_status=available:total_pe=4375:free_pe=1559:autoswitch=On:proactive_polling=On
"""


def _test_section() -> lvm.Section:
    assert (
        section := lvm.agent_section_hpux_lvm.parse_function(
            [line.split(":") for line in _TEST_RAW.strip().split("\n")]
        )
    )
    return section


def test_discover_hpux_lvm() -> None:
    assert list(lvm.check_plugin_hpux_lvm.discovery_function(_test_section())) == [
        Service(item="/dev/vg00/lvol1"),
        Service(item="/dev/vg00/lvol2"),
        Service(item="/dev/vg00/lvol3"),
        Service(item="/dev/vg00/lvol4"),
        Service(item="/dev/vg00/lvol5"),
        Service(item="/dev/vg00/lvol6"),
        Service(item="/dev/vg00/lvol7"),
        Service(item="/dev/vg00/lvol8"),
    ]


def test_check_hpux_lvm_missing() -> None:
    assert not list(lvm.check_plugin_hpux_lvm.check_function("no-such-volume", _test_section()))


def test_check_hpux_lvm_ok() -> None:
    assert list(lvm.check_plugin_hpux_lvm.check_function("/dev/vg00/lvol1", _test_section())) == [
        Result(state=State.OK, summary="Status: available,syncd"),
        Result(state=State.OK, summary="Volume group: /dev/vg00"),
    ]


def test_check_hpux_lvm_ok2() -> None:
    assert list(lvm.check_plugin_hpux_lvm.check_function("/dev/vg00/lvol2", _test_section())) == [
        Result(state=State.OK, summary="Status: available,syncd,snapshot,space_efficient"),
        Result(state=State.OK, summary="Volume group: /dev/vg00"),
    ]


def test_check_hpux_lvm_made_up_not_ok() -> None:
    assert list(lvm.check_plugin_hpux_lvm.check_function("/dev/vg00/lvol3", _test_section())) == [
        Result(
            state=State.CRIT,
            summary="Status: available,syncd,possesssed_by_demon",  # that's probably not good
        ),
        Result(state=State.OK, summary="Volume group: /dev/vg00"),
    ]
