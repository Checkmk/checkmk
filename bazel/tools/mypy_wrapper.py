#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#!/usr/bin/env python3
"""
MyPy wrapper that filters out problematic site-packages paths from MYPYPATH
to avoid "Source file found twice under different module names" errors.

This compensates an issue with rules_python's handling of namespace packages.
"""

import os
import subprocess
import sys


def filter_mypypath() -> None:
    mypypath = os.environ.get("MYPYPATH", "")
    if not mypypath:
        return

    # Filters paths like: "rules_python++pip+cmk_requirements_312_meraki/site-packages"
    os.environ["MYPYPATH"] = ":".join(
        [path for path in mypypath.split(":") if "_meraki/site-packages" not in path]
    )


def main() -> None:
    filter_mypypath()

    runfiles_dir = os.environ.get("RUNFILES_DIR")
    if not runfiles_dir:
        print("Error: RUNFILES_DIR not set in bazel context", file=sys.stderr)
        sys.exit(1)

    original_executable = os.path.join(runfiles_dir, "_main/bazel/tools/mypy_cli_original")

    if not os.path.exists(original_executable) or not os.access(original_executable, os.X_OK):
        print(f"Error: Cannot find original mypy_cli at {original_executable}", file=sys.stderr)
        sys.exit(1)

    result = subprocess.run([original_executable] + sys.argv[1:], check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
