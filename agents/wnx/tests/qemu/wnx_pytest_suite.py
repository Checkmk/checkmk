# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What the *-qemu runners of the Windows agent's pytest suites (regression,
integration) share: running a suite with run-pytest-suite.cmd, on the stage
the BUILD files declare (see :pytest_stage).
"""

from collections.abc import Mapping

from qemu_windows import tier

# What run-pytest-suite.cmd leaves for triage.
_LOGS = "logs.tgz"

_SCRIPT = "run-pytest-suite.cmd"


def run(name: str, suite: str, env: Mapping[str, str] | None = None) -> int:
    """Runs suite with run-pytest-suite.cmd in the guest (tier.run()), with
    its WNX_<SUITE>_BASE_DIR at the stage's base and env, and collects its
    logs."""
    return tier.run(
        name,
        script=_SCRIPT,
        args=[suite],
        env={f"WNX_{suite.upper()}_BASE_DIR": r"%QEMU_GDIR%\base", **(env or {})},
        collect=[_LOGS],
    )
