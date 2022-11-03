#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""EC History methods"""
import logging
import shlex
from pathlib import Path

from cmk.ec.history import _grep_pipeline, convert_history_line, History, parse_history_file


def test_convert_history_line(history: History) -> None:
    """History convert values."""
    values = "1	1666942292.2998602	DELETE	cmkadmin		5	1	some text	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin					host	heute	0	".split(
        "\t"
    )

    assert len(values) == 30

    convert_history_line(history._history_columns, values)

    assert values[0] == 1  # type: ignore[comparison-overlap]
    assert values[1] == 1666942292.2998602  # type: ignore[comparison-overlap]
    assert values[5] == 5  # type: ignore[comparison-overlap]


def test_history_parse(history: History, tmp_path: Path) -> None:
    """History parse file"""
    values = """
1666942211.07616	NEW			1002	1	999: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942208.0	1666942208.0		0	heute		OMD	0	6	9	asdf	0	open						host	heute	0	
1666942292.2998602	DELETE	cmkadmin		5	1	4: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin					host	heute	0	
1666942292.2999856	DELETE	cmkadmin		6	1	5: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin					host	heute	0	
1666942292.3000507	DELETE	cmkadmin		7	1	6: # Network services, Internet style # # Updated from https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml . # # New ports will be added on request if they have been officially assigned # by IANA and used in the real-world or are needed by a debian package. # If you need a huge list of used numbers please install the nmap package. tcpmux 1/tcp # TCP port service multiplexer echo 7/tcp	1666942205.0	1666942205.0		0	heute		OMD	0	6	9	asdf	0	closed	cmkadmin					host	heute	0	
    """

    path = tmp_path / "history_test.log"
    path.write_text(values)

    filter_ = ("event_id", "=", lambda x: True, "1")
    tac = f"nl -b a {shlex.quote(str(path))} | tac"
    cmd = " | ".join([tac] + _grep_pipeline([filter_]))  # type: ignore[list-item]

    new_entries = parse_history_file(
        history._history_columns,
        path,
        lambda x: True,
        cmd,
        None,
        logging.getLogger("cmk.mkeventd"),
    )

    assert len(new_entries) == 4
    assert new_entries[0][1] == 1666942292.3000507
