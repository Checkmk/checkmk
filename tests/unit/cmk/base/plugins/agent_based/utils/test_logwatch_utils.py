#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Counter

from cmk.base.plugins.agent_based.utils.logwatch import reclassify


def test_logwatch_reclassify(monkeypatch) -> None:
    patterns = {
        "reclassify_patterns": [
            ("3", r"\\Error", ""),
            ("2", r"foobar", ""),
            ("2", r"bla.blup.bob.exe\)", ""),
        ],
    }
    counter: Counter[int] = Counter()

    assert reclassify(counter, patterns, "fÖöbÄr", "0") == "0"
    assert reclassify(counter, patterns, "foobar", "0") == "2"
    assert reclassify(counter, patterns, r"\Error", "0") == "3"
    assert reclassify(counter, patterns, r"\Error1337", "0") == "3"
    assert reclassify(counter, patterns, "bla.blup.bob.exe)", "0") == "2"
