#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Test the rrdtool python binding and CLI

This tests works on the rrdtool itself and is not related to our
livestatus. It is just a simpler test to keep things working the way we
understand them today. This same message is on RRDColumn.cc


XPORT takes a closed timewindow in its query and returns the timestamped
values that represent an intersection with the query window. The returned
interval description is right closed.

The timestamps associated with a value in RRDtool ALWAYS represent the time
the sample was taken. Since any value you sample will represent some sort
of past state your sampling apparatus has gathered, the timestamp will
always be at the end of the sampling period.

LEGEND
O timestamps of measurements
| query values, _start_time and _end_time
x returned start, no data contained
v returned data rows, includes end y

--O---O---O---O---O---O---O---O
        |---------------|
      x---v---v---v---v---y
"""

import ast
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from tests.testlib.site import Site


@pytest.fixture(scope="session", name="rrd_database")
def fixture_rrd_database(site: Site) -> Path:
    "Create rrd database for integration test"
    with site.python_helper("helper_rrd_database.py").execute() as p:
        assert p.wait() == 0
    return site.path("test.rrd")


@pytest.mark.parametrize(
    "bounds, result",
    [
        pytest.param(
            (1500000343, 1500000401),
            {
                "data": [(350.0,), (360.0,), (370.0,), (380.0,), (390.0,), (400.0,), (None,)],
                "meta": {
                    "start": 1500000340,
                    "end": 1500000410,
                    "step": 10,
                    "rows": 7,
                    "columns": 1,
                    "legend": [""],
                },
            },
            id="High res",
        ),
        pytest.param(
            (1500000066, 1500000360),
            {
                "data": [
                    (65.0,),
                    (105.0,),
                    (145.0,),
                    (185.0,),
                    (225.0,),
                    (265.0,),
                    (305.0,),
                    (345.0,),
                ],
                "meta": {
                    "start": 1500000040,
                    "end": 1500000360,
                    "step": 40,
                    "rows": 8,
                    "columns": 1,
                    "legend": [""],
                },
            },
            id="Low res, large span",
        ),
        pytest.param(
            (1500000022, 1500000048),
            {
                "data": [(25.0,), (65.0,)],
                "meta": {
                    "start": 1500000000,
                    "end": 1500000080,
                    "step": 40,
                    "rows": 2,
                    "columns": 1,
                    "legend": [""],
                },
            },
            id="Low res, old data",
        ),
    ],
)
def test_xport(
    site: Site, rrd_database: Path, bounds: tuple[int, int], result: Mapping[str, object]
) -> None:
    "Test python binding and that direct memory access behaves correctly"
    qstart, qend = bounds

    output = ast.literal_eval(
        site.python_helper("helper_test_xport.py")
        .check_output(input=repr((str(rrd_database), qstart, qend)))
        .rstrip()
    )
    assert output == result


@pytest.mark.parametrize(
    "bounds, out_fmt, result",
    [
        pytest.param(
            (1500000322, 1500000378),
            ["-t", "--json"],
            """{ "about": "RRDtool graph JSON output",
  "meta": {
    "start": 1500000320,
    "end": 1500000380,
    "step": 10,
    "legend": [
      ""
          ]
     },
  "data": [
    [ "1500000330",3.3000000000e+02 ],
    [ "1500000340",3.4000000000e+02 ],
    [ "1500000350",3.5000000000e+02 ],
    [ "1500000360",3.6000000000e+02 ],
    [ "1500000370",3.7000000000e+02 ],
    [ "1500000380",3.8000000000e+02 ]
  ]
}\n""",
            id="JSON output",
        ),
        pytest.param(
            (1500000126, 1500000158),
            ["-t"],
            """<?xml version="1.0" encoding="ISO-8859-1"?>\n
<xport>
  <meta>
    <start>1500000120</start>
    <end>1500000160</end>
    <step>40</step>
    <rows>1</rows>
    <columns>1</columns>
    <legend>
      <entry></entry>
    </legend>
  </meta>
  <data>
    <row><t>1500000160</t><v>1.4500000000e+02</v></row>
  </data>
</xport>\n""",
            id="XML output",
        ),
    ],
)
def test_cli_xport(
    site: Site, rrd_database: str, bounds: tuple[int, int], out_fmt: Sequence[str], result: str
) -> None:
    """Test CLI so that when debugging output from tool it matches state in memory

    RRDTool composes the XML/JSON outputs explicitly and one may rely for
    now that the order of elements be always the same."""
    qstart, qend = bounds
    stdout = site.check_output(
        [
            "rrdtool",
            "xport",
            f"DEF:fir={rrd_database}:one:AVERAGE",
            "XPORT:fir",
            "-s",
            str(qstart),
            "-e",
            str(qend),
        ]
        + list(out_fmt),
    )

    assert stdout == result
