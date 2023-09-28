#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterable
from itertools import chain
from pathlib import Path

from tests.testlib import cmk_path
from tests.testlib.utils import is_enterprise_repo


def scss_files() -> set[Path]:
    return set(
        chain(
            Path(cmk_path(), "web", "htdocs", "themes").glob("**/*.scss"),
            Path(cmk_path(), "enterprise", "web", "htdocs", "themes").glob("**/*.scss"),
        )
    )


def _scss_variables(_scss_files: Iterable[Path]) -> tuple[set[str], set[str]]:
    variable_definition = re.compile(r"\s*(\$[-_a-zA-Z0-9]+)\s*:")
    variable_usage = re.compile(r"(\$[-_a-zA-Z0-9]+)")

    definitions, usages = set(), set()
    for file_ in _scss_files:
        with open(file_) as f:
            for l in f:
                if definition := variable_definition.match(l):
                    definitions.add(definition.group(1))

                # Need to search for usages like this - after splitting away potential definitions
                # (before a colon) - because re does not support overlapping matches, and there may
                # be more than one variable usage per line.
                after_colon: str = l.split(":", 1)[-1]
                if usage := variable_usage.findall(after_colon):
                    usages.update(usage)
    return definitions, usages


def test_unused_scss_variables() -> None:
    definitions, usages = _scss_variables(scss_files())
    unused = [var for var in definitions if var not in usages]
    expected = []

    if not is_enterprise_repo():
        expected.append("$ntop-protocol-painter-padding-top")

    assert sorted(unused) == sorted(expected), "Found unused SCSS variables"
