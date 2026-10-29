#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Resumes the saved test VM the *-qemu test tiers start from (:core-state),
for exploring it by hand (README.md, "Exploring the test VM"):

  bazel run --config=test-vm //agents/wnx/test-vm:core-vm

It switches this terminal to PowerShell on the guest's serial console
(vm_console). Its exit (or Ctrl-], for a PowerShell that hangs) ends the VM,
whose disk layer is thrown away with it.
"""

import argparse
import shutil
import sys
import tempfile
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import vm_console
from qemu_windows import machine, process, state
from qemu_windows.errors import VmError


def main(argv: Sequence[str] | None = None) -> int:
    # SIGTERM ends the VM like Ctrl-C.
    process.setup()
    parser = argparse.ArgumentParser(description="Runs the saved Windows test VM.")
    for tool in ("qemu", "qemu-img", "bios", "image", "disk", "state", "fingerprint"):
        parser.add_argument(f"--{tool}", type=Path, required=True)
    parser.add_argument("--expires", type=date.fromisoformat, required=True)
    parser.add_argument("--cpus", type=int, required=True)
    parser.add_argument("--memory-mib", type=int, required=True)
    args = parser.parse_args(argv)
    saved = state.SavedVm.of(
        qemu=args.qemu,
        qemu_img=args.qemu_img,
        bios=args.bios,
        image=args.image,
        disk=args.disk,
        state=args.state,
        size=machine.Size(args.cpus, args.memory_mib),
    )
    work = Path(tempfile.mkdtemp(prefix="core-vm."))
    try:
        state.check(saved, args.fingerprint, args.expires)
        with state.resume(saved, work) as (vm, _guest):
            vm_console.shell(vm.console_socket)
            vm.check()
    except KeyboardInterrupt:
        pass
    except VmError as e:
        sys.stderr.write(f"error: {e}\n")
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
