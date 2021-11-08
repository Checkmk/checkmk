#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.gui.utils.speaklater import LazyString


def test_lazystring() -> None:
    s = LazyString(lambda a: "xxx" + a, "yyy")

    assert isinstance(s, LazyString)
    assert not isinstance(s, str)

    assert isinstance("" + s, str)
    assert ("" + s) == "xxxyyy"


def test_lazystring_to_json() -> None:
    s = LazyString(lambda a: "xxx" + a, "yyy")
    assert json.dumps(s) == '"xxxyyy"'
