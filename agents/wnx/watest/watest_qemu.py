#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""watest-qemu-<tier>: one tier of the agent's watest.exe unit tests, in a
Windows test VM, as run_tests.ps1 (Invoke-UnitTest) runs them: the tier's
gtest filter, without the tests in qemu-excluded-tests.txt. Each tier is a
test of its own, so that a crash ends only its tier.

The run-as tests (WtoolsRunAsFixture, PluginTest.SyncPluginsGroup*) spawn
processes as other users, which needs the guest's interactive session.

The guest gets watest_qemu_stage (BUILD) and runs watest-qemu.cmd; see
qemu_windows/tier.py for how.

Usage: watest_qemu.py <tier> <qemu-excluded-tests.txt>
"""

import sys
from pathlib import Path

from qemu_windows import tier

# run_tests.ps1's tiers by name: the tests each runs, and those of the
# other tiers it leaves out.
_TIERS = {
    "unit": ("*", ["*_Simulation", "*Component", "*ComponentExt"]),
    "component": ("*Component", []),
    "ext": ("*ComponentExt", []),
    "simulation": ("*_Simulation", []),
}


def main(argv: list[str]) -> int:
    name, qemu_excluded = argv[0], Path(argv[1])
    positive, others = _TIERS[name]
    negative = [*others, *tier.read_list(qemu_excluded)]
    return tier.run(
        f"watest-{name}",
        script="watest-qemu.cmd",
        args=[f'"--gtest_filter={positive}:-{":".join(negative)}"'],
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
