#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from cmk.base.plugins.agent_based.utils.logwatch import reclassify
from typing import Counter


def test_logwatch_reclassify(monkeypatch):
    patterns = {
        "reclassify_patterns": [
            ("3", r"\Error", ""),
            ("2", r"foobar", ""),
        ],
    }
    counter: Counter[int] = Counter()

    assert reclassify(counter, patterns, "fÖöbÄr", "0") == "0"
    assert reclassify(counter, patterns, "foobar", "0") == "2"
    assert reclassify(counter, patterns, "\Error", "0") == "3"  # pylint: disable=anomalous-backslash-in-string
    assert reclassify(counter, patterns, "\Error1337", "0") == "3"  # pylint: disable=anomalous-backslash-in-string
