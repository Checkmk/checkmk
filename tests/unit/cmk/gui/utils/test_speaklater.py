#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json

from cmk.gui.utils.json import CustomObjectJSONEncoder
from cmk.gui.utils.speaklater import LazyString


def test_lazystring() -> None:
    s = LazyString(lambda a: "xxx" + a, "yyy")
    assert isinstance(s, LazyString)
    assert isinstance("" + s, str)
    assert ("" + s) == "xxxyyy"


def test_lazystring_to_json() -> None:
    s = LazyString(lambda a: "xxx" + a, "yyy")
    assert json.dumps(s, cls=CustomObjectJSONEncoder) == '"xxxyyy"'
