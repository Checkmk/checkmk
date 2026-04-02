#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from pathlib import Path

from cmk.werks.validate import main


def _bazel_repo_root() -> Path:
    """Resolve the repo root from Bazel runfiles."""
    test_srcdir = os.environ.get("TEST_SRCDIR")
    test_workspace = os.environ.get("TEST_WORKSPACE")
    if not test_srcdir or not test_workspace:
        raise RuntimeError(
            "TEST_SRCDIR and TEST_WORKSPACE must be set. This test must be run via Bazel."
        )
    return Path(test_srcdir) / test_workspace


def test_validate_all_werks() -> None:
    """Run the validation script on all the werks in the repo."""
    repo_root = _bazel_repo_root()
    werks_dir = repo_root / "werks_dir"

    main(
        werks_to_check=list(werks_dir.iterdir()),
        werks_config=werks_dir / "config",
        defines_make=repo_root / "defines.make",
        version_regex=re.compile(r"^\d\.\d\.\d([ipb]\d+)?$"),
    )
