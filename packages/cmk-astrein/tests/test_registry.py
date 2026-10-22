#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
import inspect
import re
from pathlib import Path

import pytest

from cmk.astrein import checkers
from cmk.astrein.framework import ASTVisitorChecker
from cmk.astrein.registry import ALL_CHECKERS, all_summaries

_KEBAB_CASE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
_FORBIDDEN_WORDS = {"cmk", "check", "checker"}


def test_checker_ids_are_unique() -> None:
    ids = [checker.checker_id for checker in ALL_CHECKERS]
    assert len(set(ids)) == len(ids)


@pytest.mark.parametrize("reported_id", sorted(all_summaries()))
def test_reported_id_follows_format(reported_id: str) -> None:
    assert _KEBAB_CASE.fullmatch(reported_id)
    assert _FORBIDDEN_WORDS.isdisjoint(reported_id.split("-"))


def test_every_reported_id_has_a_nonempty_summary() -> None:
    assert all(all_summaries().values())


@pytest.mark.parametrize("checker_module", sorted({checker.__module__ for checker in ALL_CHECKERS}))
def test_checker_module_has_a_test_module(checker_module: str) -> None:
    *packages, module_name = checker_module.removeprefix("cmk.astrein.checkers.").split(".")
    assert Path(__file__).parent.joinpath("checkers", *packages, f"test_{module_name}.py").is_file()


def test_every_defined_checker_is_discovered() -> None:
    package_directory = Path(checkers.__file__).parent
    module_names = [
        ".".join([checkers.__name__, *source.relative_to(package_directory).with_suffix("").parts])
        for source in package_directory.rglob("*.py")
        if source.name != "__init__.py"
    ]

    defined_checkers = {
        member
        for module_name in module_names
        for _, member in inspect.getmembers(importlib.import_module(module_name), inspect.isclass)
        if issubclass(member, ASTVisitorChecker) and member.__module__ == module_name
    }

    assert defined_checkers <= set(ALL_CHECKERS)
