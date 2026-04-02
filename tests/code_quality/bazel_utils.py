#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from pathlib import Path


def bazel_repo_root() -> Path:
    """Resolve the repo root from Bazel runfiles."""
    try:
        test_srcdir = os.environ["TEST_SRCDIR"]
        test_workspace = os.environ["TEST_WORKSPACE"]
    except KeyError as exc:
        raise RuntimeError(
            "TEST_SRCDIR and TEST_WORKSPACE must be set. This test must be run via Bazel."
        ) from exc
    return Path(test_srcdir) / test_workspace
