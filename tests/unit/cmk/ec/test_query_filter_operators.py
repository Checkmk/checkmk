#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for EC query filter operators."""

from cmk.ec.query import operator_for


def test_tilde_tilde_keeps_the_meaning_of_uppercase_regex_escapes() -> None:
    _, func = operator_for("~~")
    assert func("Disk full", r"^\S+ full$") is True
