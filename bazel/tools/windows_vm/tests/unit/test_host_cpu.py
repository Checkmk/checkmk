# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest
from qemu_windows.errors import VmError
from qemu_windows.host_cpu import check, host_props

PROBE = '{"execute": "query-cpu-model-expansion"}\n'
FINGERPRINT = json.dumps(
    {"probe": PROBE, "volatile": ["apic-id"], "props": {"avx2": True, "family": 6, "model": 154}}
)


def test_matching_cpu_passes() -> None:
    check(FINGERPRINT, {"avx2": True, "family": 6, "model": 154})


def test_changed_cpu_names_the_differing_properties() -> None:
    with pytest.raises(VmError, match=r"no longer matches @qemu_host_cpu \(avx2, vmx\)"):
        check(FINGERPRINT, {"avx2": False, "family": 6, "model": 154, "vmx": True})


def test_fingerprint_taken_without_kvm_is_refused_with_the_refetch_hint() -> None:
    with pytest.raises(VmError, match="out of date: bazel fetch --force --repo=@qemu_host_cpu"):
        check("no-kvm: /dev/kvm was missing\n", {})


def test_fingerprint_qemu_failed_is_not_called_out_of_date() -> None:
    with pytest.raises(VmError, match="QEMU failed although /dev/kvm was usable") as error:
        check("no-kvm: QEMU exited 1: boom\n", {})
    assert "out of date" not in str(error.value)


def test_host_props_leave_out_what_the_fingerprint_calls_volatile(tmp_path: Path) -> None:
    # Stands in for QEMU: answers the probe with a CPU model.
    qemu = tmp_path / "qemu"
    reply = {"return": {"model": {"props": {"apic-id": 3, "avx2": True}}}}
    qemu.write_text(f"#!/bin/sh\ncat >/dev/null\necho '{json.dumps(reply)}'\n")
    qemu.chmod(0o755)
    assert host_props(qemu, PROBE, ["apic-id"]) == {"avx2": True}
