#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""mk-sql-tests-qemu: mk-sql's Windows test binaries (lib and integration
tests), in a Windows test VM, against the image's SQL Server instances.

The image has the three instances the tests expect, MSSQLSERVER,
SQLEXPRESS_NAME and SQLEXPRESS_WOW, all 64-bit (SQL Server 2022
Developer). On the legacy nodes SQLEXPRESS_WOW is 32-bit, under
WOW6432Node; this tier does not cover that discovery path.

The remote tests run against the guest's own instances too: the script
sets CI_TEST_SQL_DB_ENDPOINT to localhost, as sa with the image's
Administrator password (install-mssql.ps1), which tier.py passes to it as
QEMU_VM_PASSWORD. The host's CI_TEST_SQL_DB_ENDPOINT is not passed on:
some tests build a localhost config from it, which needs the guest's
credentials.

The guest gets qemu_tests_stage (BUILD) and runs rust-test-qemu.cmd; see
qemu_windows/tier.py for how.

Usage: rust_test_qemu.py <skip-file>
"""

import sys
from pathlib import Path

from qemu_windows import tier


def main(argv: list[str]) -> int:
    (skip_file,) = map(Path, argv)
    return tier.run(
        "sql",
        script="rust-test-qemu.cmd",
        # One thread: the tests share the instances and the registry.
        args=["--test-threads=1", *tier.skip_args(tier.read_list(skip_file))],
    )


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
