# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Whether this host's CPU, as the pinned QEMU sees it under KVM, still
matches the @qemu_host_cpu fingerprint (bazel/rules/xcomp/qemu_host_cpu.bzl).

The fingerprint is part of a saved VM state's cache key: a state saved under a
stale one (a kernel command line or KVM module parameter changed the CPU
features, which the repository rule does not watch) would be shared with hosts
it does not fit, and a test on a host whose fingerprint is stale would resume
a state saved on another CPU. Both the state action and every test check.

The fingerprint holds the QMP probe and the properties it leaves out along with
the properties, so this module reads the host CPU exactly as the repository
rule did.
"""

import json
import subprocess
from collections.abc import Collection, Mapping
from pathlib import Path

from qemu_windows.errors import VmError

_REFETCH = "bazel fetch --force --repo=@qemu_host_cpu"

# How the repository rule's fingerprint starts when it could not open
# /dev/kvm (bazel/rules/xcomp/qemu_host_cpu.bzl), as opposed to QEMU failing.
_NO_DEV_KVM = "no-kvm: /dev/kvm"


def check(fingerprint: str, props: Mapping[str, object]) -> None:
    """Fails unless fingerprint (the repository's file) describes props,
    the host CPU model's properties. KVM is usable here (the callers run
    machine.check_kvm() first). The message says why and the way out."""
    if fingerprint.startswith("no-kvm"):
        message = f"@qemu_host_cpu says {fingerprint.strip()}"
        if fingerprint.startswith(_NO_DEV_KVM):
            message += f"\nKVM is usable now, so that is out of date: {_REFETCH}"
        else:
            message += (
                "\nQEMU failed although /dev/kvm was usable, and it may still fail: once"
                f" the cause is fixed, take the fingerprint anew: {_REFETCH}"
            )
        raise VmError(message)
    expected = json.loads(fingerprint)["props"]
    if differ := sorted(
        k for k in expected.keys() | props.keys() if expected.get(k) != props.get(k)
    ):
        raise VmError(
            f"this host's CPU no longer matches @qemu_host_cpu ({', '.join(differ[:10])}),"
            f" the key of the saved VM state, which then does not fit this host: {_REFETCH}"
        )


def check_host(qemu: Path, fingerprint: Path) -> None:
    """check() against this host's CPU, on a host with usable KVM."""
    text = fingerprint.read_text()
    if text.startswith("no-kvm"):
        check(text, {})
    else:
        taken = json.loads(text)
        check(text, host_props(qemu, taken["probe"], taken["volatile"]))


def host_props(qemu: Path, probe: str, volatile: Collection[str]) -> dict[str, object]:
    """The properties of QEMU's host CPU model as the probe (QMP commands)
    reads them, without the volatile ones."""
    try:
        result = subprocess.run(
            [str(qemu), "-machine", "none", "-accel", "kvm", "-display", "none", "-nodefaults"]
            + ["-qmp", "stdio"],
            input=probe,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
    except (OSError, subprocess.SubprocessError) as e:
        stderr = getattr(e, "stderr", None) or ""
        raise VmError(
            f"cannot read this host's CPU through QEMU: {e}\n{stderr}"
            f"if KVM changed since @qemu_host_cpu was taken: {_REFETCH}"
        ) from None
    for line in result.stdout.splitlines():
        reply = json.loads(line)
        if isinstance(reply.get("return"), dict) and "model" in reply["return"]:
            props = reply["return"]["model"]["props"]
            return {k: v for k, v in props.items() if k not in volatile}
    raise VmError("no CPU model in QEMU's reply")
