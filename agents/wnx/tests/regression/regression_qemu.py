#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""regression-qemu: the agent's pytest regression suite (test_section_*.py
against the built check_mk_agent.exe), in a Windows test VM.

The suite runs on the test Python (python_test_cab: PYTHON_VERSION_WINDOWS
with pytest, pyyaml and pywin32), which run-pytest-suite.cmd unpacks in the
guest. It asserts an unfiltered admin token, which the guest's elevated
session has.

The guest gets regression_qemu_stage (BUILD) and runs run-pytest-suite.cmd;
see qemu_windows/tier.py for how.
"""

import sys

import wnx_pytest_suite


def main() -> int:
    return wnx_pytest_suite.run("reg", "regression")


if __name__ == "__main__":
    sys.exit(main())
