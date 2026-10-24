#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""cmk-agent-ctl-tests-qemu: the controller's Windows test binaries, in a
Windows test VM.

The tests that need an elevated token (test_pull, test_status_ok, most of
test_cli) skip themselves under Wine; the guest's elevated session runs
them.

The guest gets qemu_tests_stage (BUILD) and runs run-rust-tests.cmd; see
qemu_windows/tier.py for how.
"""

import sys

from qemu_windows import tier


def main() -> int:
    # One thread: the tests bind loopback ports.
    return tier.run("ctl", script="run-rust-tests.cmd", args=["--test-threads=1"])


if __name__ == "__main__":
    sys.exit(main())
