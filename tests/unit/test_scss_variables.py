#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from itertools import chain
from pathlib import Path
from typing import Iterable, Set, Tuple

from tests.testlib import cmk_path, is_enterprise_repo


def _scss_files() -> Set[Path]:
    return set(
        chain(
            Path(cmk_path(), "web", "htdocs", "themes").glob("**/*.scss"),
            Path(cmk_path(), "enterprise", "web", "htdocs", "themes").glob("**/*.scss"),
        )
    )


def _scss_variables(scss_files: Iterable[Path]) -> Tuple[Set[str], Set[str]]:
    variable_definition = re.compile(r"\s*(\$[-_a-zA-Z0-9]+)\s*:")
    variable_usage = re.compile(r":[^$]*(\$[-_a-zA-Z0-9]+)")

    definitions, usages = set(), set()
    for file_ in scss_files:
        with open(file_) as f:
            for l in f:
                if definition := variable_definition.match(l):
                    definitions.add(definition.group(1))
                if usage := variable_usage.search(l):
                    usages.add(usage.group(1))
    return definitions, usages


def test_unused_scss_variables() -> None:
    definitions, usages = _scss_variables(_scss_files())
    unused = [var for var in definitions if var not in usages]
    expected = [
        "$self",  # used in interpolation with #{}
    ]

    if not is_enterprise_repo():
        expected.append("$ntop-protocol-painter-padding-top")

    assert sorted(unused) == sorted(expected), "Found unused SCSS variables"
