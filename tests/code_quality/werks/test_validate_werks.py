#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re

from cmk.werks.validate import main
from tests.code_quality.bazel_utils import bazel_repo_root


def test_validate_all_werks() -> None:
    """Run the validation script on all the werks in the repo."""
    repo_root = bazel_repo_root()
    werks_dir = repo_root / "werks_dir"

    main(
        werks_to_check=list(werks_dir.iterdir()),
        werks_config=werks_dir / "config",
        defines_make=repo_root / "defines.make",
        version_regex=re.compile(r"^\d\.\d\.\d([ipb]\d+)?$"),
    )
