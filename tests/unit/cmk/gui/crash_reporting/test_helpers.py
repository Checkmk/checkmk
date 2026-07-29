#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.crash_reporting.helpers import local_files_involved_in_crash


def test_local_files_involved_in_crash() -> None:
    assert local_files_involved_in_crash(
        [
            ("/omd/sites/heute/lib/python3/cmk/base/modes/check_mk.py", 1, "main", "do_check()"),
            (
                "/omd/sites/heute/local/lib/python3/cmk_addons/plugins/acme/agent_based/acme.py",
                2,
                "parse_acme",
                "return int(line)",
            ),
        ]
    ) == ["/omd/sites/heute/local/lib/python3/cmk_addons/plugins/acme/agent_based/acme.py"]


@pytest.mark.xfail(strict=True, reason="Crash group 3953: ValueError too many values to unpack")
def test_local_files_involved_in_crash_with_stringified_frames() -> None:
    # Some stored crash reports hold the string representation of the traceback
    # frames instead of the (filename, lineno, function, line) tuples.
    assert (
        local_files_involved_in_crash(
            [
                "<FrameSummary file /omd/sites/heute/lib/python3/cmk/checkengine/"  # type: ignore[list-item]
                "sectionparser.py, line 121 in _parse_raw_data>",
            ]
        )
        == []
    )
