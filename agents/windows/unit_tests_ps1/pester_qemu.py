#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""pester-qemu: the Windows agent plugins' Pester suites, in a Windows test VM.

The plugins run their Windows-only code for real (COM, CIM, registry) under
powershell.exe, the interpreter the agent starts .ps1 plugins with. The
Windows Update COM session (windows_updates.ps1) needs the guest's
interactive session.

Pester is pinned (@pester), with nothing installed at run time.

The guest gets pester_qemu_stage (BUILD) and runs run-pester.ps1; see
qemu_windows/tier.py for how.
"""

import sys

from qemu_windows import tier


def main() -> int:
    return tier.run("pester", script="run-pester.ps1")


if __name__ == "__main__":
    sys.exit(main())
