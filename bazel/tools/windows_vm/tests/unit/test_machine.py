# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from qemu_windows.machine import argv, Disk


def test_argv_is_the_saved_states_device_set() -> None:
    result = argv(Path("/q/qemu"), Path("/q/fw"), [Disk("disk", Path("/d.qcow2"))])

    assert result == [
        "/q/qemu",
        *("-L", "/q/fw", "-nodefaults"),
        *("-machine", "pc-i440fx-11.1,accel=kvm", "-cpu", "host", "-m", "4G", "-smp", "4"),
        *("-vga", "std", "-display", "none"),
        *("-blockdev", "driver=file,node-name=disk-file,filename=/d.qcow2,discard=unmap"),
        "-blockdev",
        "driver=qcow2,node-name=disk,file=disk-file,discard=unmap,detect-zeroes=unmap",
        *("-device", "ide-hd,drive=disk,bus=ide.0,unit=0"),
        *("-netdev", "user,id=net0", "-device", "e1000,netdev=net0"),
        *("-netdev", "user,id=net1,net=10.0.3.0/24", "-device", "e1000,netdev=net1,id=nic1"),
        *("-device", "vmgenid,guid=auto"),
        *("-device", "virtio-serial-pci,id=vser0"),
        *("-device", "virtserialport,bus=vser0.0,chardev=qga,name=org.qemu.guest_agent.0"),
        *("-device", "isa-serial,chardev=console"),
    ]


def test_guest_disk_is_the_top_of_the_chain() -> None:
    disks = [
        Disk("image", Path("/i.qcow2"), mode="ro"),
        Disk("test", Path("/t.qcow2"), backing="image", mode="scratch"),
    ]

    result = argv(Path("/q/qemu"), Path("/q/fw"), disks)

    assert "ide-hd,drive=test,bus=ide.0,unit=0" in result


# fmt: off
@pytest.mark.parametrize(
    "disk, expected",
    [
        pytest.param(
            Disk("base", Path("/b.qcow2"), mode="ro"),
            ["driver=file,node-name=base-file,filename=/b.qcow2,read-only=on",
             "driver=qcow2,node-name=base,file=base-file,read-only=on"],
            id="read-only layer",
        ),
        pytest.param(
            Disk("test", Path("/t.qcow2"), backing="state", mode="scratch"),
            ["driver=file,node-name=test-file,filename=/t.qcow2,discard=unmap,cache.no-flush=on",
             ("driver=qcow2,node-name=test,file=test-file,discard=unmap,detect-zeroes=unmap,"
              "backing=state")],
            id="scratch layer on a backing node",
        ),
    ],
)
# fmt: on
def test_blockdev_options_follow_the_layer_mode(disk: Disk, expected: list[str]) -> None:
    assert disk.blockdev_args()[1::2] == expected
