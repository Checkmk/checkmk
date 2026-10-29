#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Runs one tier of the cross-compiled watest.exe inside a real-Windows
QEMU VM, as run_tests.ps1 (Invoke-UnitTest) runs it: one watest.exe with
that tier's filter in a fresh test root, without *Flaky and the
QEMU-specific exclusions from qemu-excluded-tests.txt. Each tier is a
test of its own, so that a crash ends only its tier.

The guest contract and the environment are those of
bazel/tools/windows_vm/qemu_windows/tier.py. The suite must run
inside the guest's interactive session: run-as tests (WtoolsRunAsFixture,
PluginTest.SyncPluginsGroup*) spawn processes as other users, which fails
with STATUS_DLL_INIT_FAILED outside it.

Usage: watest_qemu.py <tier> <qemu-excluded-tests.txt> <watest.exe>
"""

import os
import sys
from pathlib import Path

from qemu_windows import tier
from qemu_windows.stage import read_list, Stage

# run_tests.ps1's tiers by name: the tests each runs, and those of the
# other tiers it leaves out.
_TIERS = {
    "unit": ("*", ["*_Simulation", "*Component", "*ComponentExt"]),
    "component": ("*Component", []),
    "ext": ("*ComponentExt", []),
    "simulation": ("*_Simulation", []),
}


def main(argv: list[str]) -> int:
    name, qemu_excluded, exe = argv[0], Path(argv[1]), Path(argv[2])
    positive, others = _TIERS[name]
    # run_tests.ps1 leaves *Flaky tests out.
    negative = [*others, "*Flaky", *read_list(qemu_excluded)]

    stage = Stage(Path(os.environ["TEST_TMPDIR"], "stage"))
    stage.add(Path("agents/wnx/install"), "agents/wnx/install")
    stage.add(Path("agents/wnx/test_files"), "agents/wnx/test_files")
    stage.add(Path("doc/treasures/windows/ohm"), "doc/treasures/windows/ohm")
    # The WNX_TEST_ROOT tree, mirroring run_tests.ps1's Create_UnitTestDir:
    # without it watest falls back to SOLUTION_DIR resolution, and the tests
    # reading the staged root (PluginTest.FilesAndFoldersComponent,
    # PlayerTest.RealLifeInventory_Simulation) skip or fail on the empty
    # plugins dir.
    (stage.root / "test/root/plugins").mkdir(parents=True)
    (stage.root / "test/data/bin").mkdir(parents=True)
    stage.add_files(Path("agents/windows/plugins").iterdir(), "test/root/plugins")
    config = Path("agents/wnx/test_files/config")
    stage.add(Path("agents/wnx/install/resources/check_mk.yml"), "test/root/check_mk.yml")
    stage.add_files(config.glob("*.yml"), "test/root")
    stage.add_files(
        [
            *config.glob("*.cfg"),
            *config.glob("*.test.ini"),
            *Path("agents/wnx/test_files/cap").glob("*.test.cap"),
            *(
                path
                for pattern in ("*.ini", "*.dat", "*.state")
                for path in Path("agents/wnx/test_files/unit_test").glob(pattern)
            ),
            *config.glob("*.yml"),
        ],
        "test/data",
    )
    # Fixture text files are compared by size or run through cmd.exe.
    for directory in ("agents/wnx/test_files", "test"):
        stage.to_crlf(directory, (".output", ".cmd", ".bat", ".ps1"))
    stage.add(exe, "watest.exe")
    # The share FileInfoTest.Unc and FileInfoTest.Unicode read.
    stage.add(Path("agents/wnx/watest/watest-qemu-share.ps1"), "watest-qemu-share.ps1")
    stage.write(
        "task.cmd",
        "@echo off\n"
        "set WNX_TEST_ROOT=%~dp0\n"
        'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0watest-qemu-share.ps1"'
        " || (echo error: creating the shared_public share failed& exit /b 1)\n"
        f'watest.exe "--gtest_filter={positive}:-{":".join(negative)}"\n',
    )
    return tier.run(f"watest-{name}", stage)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
