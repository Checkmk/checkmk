#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.logwatch.agent_based.commons import reclassify, ReclassifyParameters


def test_logwatch_reclassify() -> None:
    reclassify_params = ReclassifyParameters(
        patterns=[
            ("C", r"\\Error", ""),
            ("W", r"foobar", ""),
            ("W", r"bla.blup.bob.exe\)", ""),
        ],
        states={},
    )

    assert reclassify(reclassify_params, "fÖöbÄr", "O") == "O"
    assert reclassify(reclassify_params, "foobar", "O") == "W"
    assert reclassify(reclassify_params, r"\Error", "O") == "C"
    assert reclassify(reclassify_params, r"\Error1337", "O") == "C"
    assert reclassify(reclassify_params, "bla.blup.bob.exe)", "O") == "W"
