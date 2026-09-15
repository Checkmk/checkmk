#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import os
from pathlib import Path

import pytest

from buildscripts.scripts.lib.common import cwd, flatten, load_editions_file, strtobool


def test_flatten_expands_nested_lists_and_keeps_plain_strings() -> None:
    assert list(flatten(["a", ["b", "c"], "d", []])) == ["a", "b", "c", "d"]


@pytest.mark.parametrize(
    "value",
    [pytest.param(v, id=v) for v in ("y", "Yes", "t", "TRUE", "on", "1")],
)
def test_strtobool_accepts_truthy_spellings(value: str) -> None:
    assert strtobool(value) is True


@pytest.mark.parametrize(
    "value",
    [pytest.param(v, id=v) for v in ("n", "No", "f", "FALSE", "off", "0")],
)
def test_strtobool_accepts_falsy_spellings(value: str) -> None:
    assert strtobool(value) is False


def test_strtobool_passes_booleans_through() -> None:
    assert strtobool(True) is True
    assert strtobool(False) is False


def test_strtobool_rejects_unknown_words() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        strtobool("maybe")


def test_load_editions_file_parses_yaml(tmp_path: Path) -> None:
    editions_file = tmp_path / "editions.yml"
    editions_file.write_text("editions:\n  pro:\n    release: [debian-12]\n")

    assert load_editions_file(editions_file) == {"editions": {"pro": {"release": ["debian-12"]}}}


def test_cwd_changes_directory_only_inside_the_block(tmp_path: Path) -> None:
    before = os.getcwd()

    with cwd(tmp_path):
        inside = Path(os.getcwd())

    assert inside == tmp_path.resolve()
    assert os.getcwd() == before


def test_cwd_restores_directory_after_exception(tmp_path: Path) -> None:
    before = os.getcwd()

    with pytest.raises(RuntimeError), cwd(tmp_path):
        raise RuntimeError("boom")

    assert os.getcwd() == before
