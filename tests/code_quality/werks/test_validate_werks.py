#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from pathlib import Path

import pytest

from cmk.utils.werks.__main__ import main as cmk_utils_werks_main
from cmk.werks.flavor.cmk import CmkFlavor
from cmk.werks.tool.flavor import current_version as read_current_version
from cmk.werks.tool.utils import load_precompiled_werks_file
from cmk.werks.tool.utils.__main__ import main as cmk_werks_main
from cmk.werks.tool.validate import main as validate_main
from tests.code_quality.bazel_utils import bazel_repo_root

WERKS_DIR = bazel_repo_root() / ".werks"
CONFIG_PATH = WERKS_DIR / "config"


@pytest.fixture()
def current_version() -> str:
    return read_current_version(CmkFlavor(), bazel_repo_root())


def test_validate_all_werks() -> None:
    """Run the validation script on all the werks in the repo."""
    validate_main(
        werks_to_check=list(WERKS_DIR.iterdir()),
        werks_config=CONFIG_PATH,
        repo_root=bazel_repo_root(),
        version_regex=re.compile(r"^\d\.\d\.\d([ipb]\d+)?$"),
    )


@pytest.mark.parametrize("fmt", ["md", "txt"])
def test_announce(current_version: str, fmt: str) -> None:
    """Smoke test for `//cmk/utils:werks_bin -- announce`."""
    cmk_utils_werks_main(["announce", str(WERKS_DIR), current_version, "--format", fmt])


def test_precompile(tmp_path: Path) -> None:
    """Smoke test for `//packages/cmk-werks:utils-bin -- precompile`."""
    dest = tmp_path / "precompiled.json"

    cmk_werks_main(["precompile", str(WERKS_DIR), str(dest)])

    loaded = load_precompiled_werks_file(dest)
    assert loaded
