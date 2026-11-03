#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Resumes the saved test VM the *-qemu test tiers start from (:core-state),
for exploring it by hand (README.md, "Exploring the test VM"):

  bazel run --config=test-vm //agents/wnx/test-vm:core-vm

which `winvm start` runs (and `winvm start --headless` with --no-shell). It
switches this terminal to PowerShell on the guest's serial console
(vm_console). Its exit (or Ctrl-], for a PowerShell that hangs) ends the VM,
whose disk layer is thrown away with it. With --no-shell it holds the VM
until Ctrl-C or SIGTERM (`winvm stop`) instead, for winvm exec, put and get.
Either way the VM is registered for winvm (vm_registry), which reaches it
through its guest agent.
"""

import argparse
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import vm_console
from qemu_windows import machine, process, state
from qemu_windows.errors import VmError
from vm_registry import default_root, Registry, RegistryError, START_TOKEN


def main(argv: Sequence[str] | None = None) -> int:
    # SIGTERM (winvm stop) ends the VM like Ctrl-C.
    process.setup()
    parser = argparse.ArgumentParser(description="Runs the saved Windows test VM.")
    for tool in ("qemu", "qemu-img", "bios", "image", "disk", "state", "fingerprint"):
        parser.add_argument(f"--{tool}", type=Path, required=True)
    parser.add_argument("--expires", type=date.fromisoformat, required=True)
    parser.add_argument("--cpus", type=int, required=True)
    parser.add_argument("--memory-mib", type=int, required=True)
    parser.add_argument(
        "--no-shell",
        action="store_true",
        help="hold the VM until Ctrl-C or SIGTERM instead of logging into it",
    )
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
        with (
            state.resume(saved, work) as (vm, guest),
            Registry(default_root()).register(
                vm.qga_socket,
                vm.console_socket,
                os.environ.get("BUILD_WORKSPACE_DIRECTORY", ""),
                os.environ.get(START_TOKEN, ""),
            ) as entry,
        ):
            # The guest agent serves one client at a time: winvm's.
            guest.agent.close()
            if args.no_shell:
                sys.stdout.write(
                    f"{entry.id} is running: winvm exec|put|get|stop --vm {entry.id}\n"
                )
                while vm.alive():
                    time.sleep(1)
            else:
                sys.stdout.write(
                    f"{entry.id} is running, also for winvm exec|put|get --vm {entry.id}\n"
                )
                vm_console.shell(vm.console_socket)
            vm.check()
    except KeyboardInterrupt:
        pass
    except (VmError, RegistryError) as e:
        sys.stderr.write(f"error: {e}\n")
        return 1
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
