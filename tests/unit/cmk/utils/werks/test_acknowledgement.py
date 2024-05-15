#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import json
from pathlib import Path

from cmk.utils.werks import load

from cmk.werks.models import Class, Compatibility, Edition, Level, Werk

WERK_V1 = {
    "15374": {
        "class": "fix",
        "component": "rest-api",
        "date": 1676973331,
        "level": 1,
        "title": "crash-reporting: Improve crash reporting information",
        "version": "2.2.0b3",
        "compatible": "incomp",
        "edition": "cre",
        "knowledge": "doc",
        "state": "unknown",
        "id": 15374,
        "targetversion": None,
        "description": [
            "In the event of a crash when calling the rest-api, having more",
            "useful information helps find the root cause which helps",
            "fix the issue quicker. This werk introduces the changes to",
            "the data returned in a crash report.",
            "",
            "",
        ],
    }
}


def test_load(tmp_path: Path) -> None:
    with (tmp_path / "werks").open("w") as fo:
        json.dump(WERK_V1, fo)

    result = load(tmp_path)

    assert result == {
        15374: Werk(
            werk_version="2",
            id=15374,
            class_=Class.FIX,
            component="rest-api",
            level=Level.LEVEL_1,
            date=datetime.datetime(2023, 2, 21, 9, 55, 31, tzinfo=datetime.UTC),
            compatible=Compatibility.NOT_COMPATIBLE,
            edition=Edition.CRE,
            description="<p>In the event of a crash when calling the rest-api, having more\n"
            "useful information helps find the root cause which helps\n"
            "fix the issue quicker. This werk introduces the changes to\n"
            "the data returned in a crash report.</p>",
            title="crash-reporting: Improve crash reporting information",
            version="2.2.0b3",
        )
    }
