#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""integration-qemu: the agent's pytest integration suite (the built agent,
controller and python-3.cab module together), in a Windows test VM.

Like regression-qemu, the suite runs on the test Python (python_test_cab),
which run-pytest-suite.cmd unpacks in the guest; python-3.cab is only the
module under test. It asserts an unfiltered admin token, which the guest's
elevated session has.

The guest gets integration_qemu_stage (BUILD) and runs run-pytest-suite.cmd;
see qemu_windows/tier.py for how.

Usage: integration_qemu.py <cmk_version.txt>
"""

import sys
from pathlib import Path

import wnx_pytest_suite


def main(argv: list[str]) -> int:
    (version,) = map(Path, argv)
    return wnx_pytest_suite.run("int", "integration", {"CMK_VERSION": version.read_text().strip()})


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
