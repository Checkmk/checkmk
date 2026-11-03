#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""mk-oracle-tests-qemu: mk-oracle's Windows test binaries (lib unit tests
and component tests), in a Windows test VM, against a real database.

Environment: CI_ORA2_DB_TEST (required) and CI_ORA1_DB_TEST (optional, a
second endpoint with its own credentials, e.g. sys as sysdba). A localhost
endpoint, such as the --docker-tests database, becomes 10.0.2.2, which is
how the guest reaches the host.

Tests that return without testing anything when their environment is
missing would count as passed; they are skipped by name instead: always
the ones in the skip file, test_connection_with_explicit_sysdba_role
without CI_ORA1_DB_TEST.

The guest gets qemu_tests_stage (BUILD) and runs rust-test-qemu.cmd; see
qemu_windows/tier.py for how.

Usage: rust_test_qemu.py <skip-file>
"""

import os
import sys
from pathlib import Path

from qemu_windows import tier

_NO_ENDPOINT = """\
error: CI_ORA2_DB_TEST is not set; the component tests need an
       Oracle database. For a local one, start
       packages/mk-oracle/tests/files/docker/run-db.sh -v 23
       and run the tier with
       CI_ORA2_DB_TEST=localhost:sys:oracle:1521:_:sysdba:FREE:FREE:_:
       exported (or passed with --test_env).
"""


def main(argv: list[str]) -> int:
    (skip_file,) = map(Path, argv)
    if not (ora2 := os.environ.get("CI_ORA2_DB_TEST")):
        sys.stderr.write(_NO_ENDPOINT)
        return 1
    endpoints = {"CI_ORA2_DB_TEST": ora2}
    skip = tier.read_list(skip_file)
    if ora1 := os.environ.get("CI_ORA1_DB_TEST"):
        endpoints["CI_ORA1_DB_TEST"] = ora1
    else:
        sys.stdout.write(
            "skipping test_connection_with_explicit_sysdba_role: needs CI_ORA1_DB_TEST\n"
        )
        skip.append("test_connection_with_explicit_sysdba_role")
    env = {}
    for name, value in endpoints.items():
        try:
            env[name] = tier.cmd_literal(_guest_endpoint(value))
        except ValueError as e:
            sys.stderr.write(f"error: {name}: {e}\n")
            return 1
    return tier.run(
        "ora",
        script="rust-test-qemu.cmd",
        args=[arg for name in skip for arg in ("--skip", name)],
        env=env,
    )


def _guest_endpoint(endpoint: str) -> str:
    """The guest reaches the host's loopback (the Docker database) as
    10.0.2.2. Only the host field (the first one) is rewritten."""
    host, sep, rest = endpoint.partition(":")
    return f"10.0.2.2{sep}{rest}" if host in ("localhost", "127.0.0.1") else endpoint


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
