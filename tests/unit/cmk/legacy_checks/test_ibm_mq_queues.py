#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import IgnoreResultsError, Metric, Result, Service, State
from cmk.legacy_checks.ibm_mq_queues import (
    _QueueParams,
    check_ibm_mq_queues,
    discover_ibm_mq_queues,
)
from cmk.plugins.ibm.agent_based.ibm_mq_queues import parse_ibm_mq_queues

pytestmark = pytest.mark.checks


def parse_info(lines: str, separator: str | None = None) -> list[list[str]]:
    result = []
    for line in lines.splitlines():
        line = line.strip()
        result.append(line.split(separator))
    return result


def test_parse() -> None:
    lines = """\
QMNAME(MY.TEST)                                           STATUS(RUNNING) NOW(2020-04-03T17:27:02+0200)
5724-H72 (C) Copyright IBM Corp. 1994, 2015.
Starting MQSC for queue manager MY.TEST.


AMQ8409: Display Queue details.
   QUEUE(MY.QUEUE.ONE)
   TYPE(QLOCAL)                            MAXDEPTH(5000)
AMQ8409: Display Queue details.
   QUEUE(MY.QUEUE.TWO)
   TYPE(QLOCAL)                            MAXDEPTH(200000)
AMQ8450: Display queue status details.
   QUEUE(MY.QUEUE.ONE)
   TYPE(QUEUE)                             CURDEPTH(0)
   LGETDATE( )                             LGETTIME( )
   LPUTDATE( )                             LPUTTIME( )
   MONQ(MEDIUM)                            MSGAGE(0)
   QTIME( , )
AMQ8450: Display queue status details.
   QUEUE(MY.QUEUE.TWO)
   TYPE(QUEUE)                             CURDEPTH(1400)
   LGETDATE(2017-03-09)                    LGETTIME(08.49.13)
   LPUTDATE( )                             LPUTTIME( )
   OPPROCS(0)                              IPPROCS(5)
   MONQ(MEDIUM)                            MSGAGE(2201)
   QTIME(999999999, 999999999)
2 MQSC commands read.
No commands have a syntax error.
All valid MQSC commands were processed.
"""
    section = parse_info(lines, chr(10))
    parsed = parse_ibm_mq_queues(section)
    assert 2 + 1 == len(parsed)

    attrs = parsed["MY.TEST"]
    assert attrs["STATUS"] == "RUNNING"
    assert attrs["NOW"] != ""

    attrs = parsed["MY.TEST:MY.QUEUE.TWO"]
    assert attrs["CURDEPTH"] == "1400"
    assert attrs["LGETDATE"] == "2017-03-09"
    assert attrs["LGETTIME"] == "08.49.13"
    assert attrs["CURDEPTH"] == "1400"
    assert attrs["MAXDEPTH"] == "200000"
    assert attrs["MSGAGE"] == "2201"


def test_discovery_qmgr_not_included() -> None:
    parsed: dict[str, dict[str, str]] = {
        "QM1": {"STATUS": "RUNNING"},
        "QM2": {"STATUS": "RUNNING"},
        "QM1:QUEUE1": {"CURDEPTH": "0"},
        "QM1:QUEUE2": {"CURDEPTH": "1400"},
        "QM2:QUEUE3": {"CURDEPTH": "530"},
        "QM2:QUEUE4": {"CURDEPTH": "10"},
    }
    discovery = list(discover_ibm_mq_queues(parsed))
    assert len(discovery) == 4
    assert Service(item="QM1:QUEUE2") in discovery
    assert Service(item="QM2:QUEUE3") in discovery


def test_check() -> None:
    params: _QueueParams = {"curdepth": (1500, 2000), "ipprocs": {"upper": (4, 8)}}
    parsed: dict[str, dict[str, str]] = {
        "QM1": {"STATUS": "RUNNING"},
        "QM1:MY.QUEUE": {
            "CURDEPTH": "1400",
            "MAXDEPTH": "200000",
            "MSGAGE": "2201",
            "IPPROCS": "5",
            "OPPROCS": "0",
            "QTIME": ",",
        },
    }
    actual = list(check_ibm_mq_queues("QM1:MY.QUEUE", params, parsed))
    assert actual == [
        Result(state=State.OK, summary="Queue depth: 1400"),
        Metric("curdepth", 1400.0, levels=(1500.0, 2000.0), boundaries=(0.0, 200000.0)),
        Result(state=State.OK, summary="Oldest message: 36 minutes 41 seconds"),
        Metric("msgage", 2201.0),
        Result(state=State.WARN, summary="Open input handles: 5 (warn/crit at 4/8)"),
        Metric("ipprocs", 5.0, levels=(4.0, 8.0)),
        Result(state=State.OK, summary="Open output handles: 0"),
        Metric("opprocs", 0.0),
        Result(state=State.OK, summary="Qtime short: n/a"),
        Metric("qtime_short", 0.0),
        Result(state=State.OK, summary="Qtime long: n/a"),
        Metric("qtime_long", 0.0),
    ]


def test_stale_service_for_not_running_qmgr() -> None:
    params: _QueueParams = {}
    parsed: dict[str, dict[str, str]] = {"QM1": {"STATUS": "ENDED NORMALLY"}}
    with pytest.raises(IgnoreResultsError, match=r"Stale because queue manager ENDED NORMALLY"):
        list(check_ibm_mq_queues("QM1:MY.QUEUE", params, parsed))


def test_vanished_service_for_running_qmgr() -> None:
    params: _QueueParams = {}
    parsed: dict[str, dict[str, str]] = {
        "QM1": {"STATUS": "RUNNING"},
        "QM1:QUEUE1": {"CURDEPTH": "0"},
    }
    actual = list(check_ibm_mq_queues("QM1:VANISHED", params, parsed))
    assert len(actual) == 0


#
# CURDEPTH, MAXDEPTH
#
def test_depth_no_params() -> None:
    params: _QueueParams = {}
    curdepth, maxdepth = 0, 5000
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Queue depth: 0"),
        Metric("curdepth", 0.0, boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_with_percentage() -> None:
    params: _QueueParams = {}
    curdepth, maxdepth = 50, 5000
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Queue depth: 50"),
        Metric("curdepth", 50.0, boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_no_max_depth() -> None:
    params: _QueueParams = {}
    curdepth, maxdepth = 50, None
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Queue depth: 50"),
        Metric("curdepth", 50.0),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_param_ok() -> None:
    params: _QueueParams = {"curdepth": (100, 500)}
    curdepth, maxdepth = 50, 5000
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Queue depth: 50"),
        Metric("curdepth", 50.0, levels=(100.0, 500.0), boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_param_warn() -> None:
    params: _QueueParams = {"curdepth": (100, 500)}
    curdepth, maxdepth = 100, 5000
    expected: list[Result | Metric] = [
        Result(state=State.WARN, summary="Queue depth: 100 (warn/crit at 100/500)"),
        Metric("curdepth", 100.0, levels=(100.0, 500.0), boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_param_crit() -> None:
    params: _QueueParams = {"curdepth": (100, 500)}
    curdepth, maxdepth = 500, 5000
    expected: list[Result | Metric] = [
        Result(state=State.CRIT, summary="Queue depth: 500 (warn/crit at 100/500)"),
        Metric("curdepth", 500.0, levels=(100.0, 500.0), boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_param_percentage_ok() -> None:
    params: _QueueParams = {"curdepth_perc": (80.0, 90.0)}
    curdepth, maxdepth = 50, 5000
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Queue depth: 50"),
        Metric("curdepth", 50.0, boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_param_percentage_warn() -> None:
    params: _QueueParams = {"curdepth_perc": (80.0, 90.0)}
    curdepth, maxdepth = 4000, 5000
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Queue depth: 4000"),
        Metric("curdepth", 4000.0, boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_param_percentage_error() -> None:
    params: _QueueParams = {"curdepth_perc": (80.0, 90.0)}
    curdepth, maxdepth = 4900, 5000
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Queue depth: 4900"),
        Metric("curdepth", 4900.0, boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_param_percentage_ignored_in_wato() -> None:
    params: _QueueParams = {"curdepth_perc": (None, None)}
    curdepth, maxdepth = 4900, 5000
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Queue depth: 4900"),
        Metric("curdepth", 4900.0, boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_param_both_ok() -> None:
    params: _QueueParams = {"curdepth": (100, 500), "curdepth_perc": (80.0, 90.0)}
    curdepth, maxdepth = 50, 5000
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Queue depth: 50"),
        Metric("curdepth", 50.0, levels=(100.0, 500.0), boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_param_one_of_them_warn() -> None:
    params: _QueueParams = {"curdepth": (100, 500), "curdepth_perc": (80.0, 90.0)}
    curdepth, maxdepth = 100, 5000
    expected: list[Result | Metric] = [
        Result(state=State.WARN, summary="Queue depth: 100 (warn/crit at 100/500)"),
        Metric("curdepth", 100.0, levels=(100.0, 500.0), boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def test_depth_param_one_warn_one_crit() -> None:
    params: _QueueParams = {"curdepth": (100, 4950), "curdepth_perc": (80.0, 90.0)}
    curdepth, maxdepth = 4900, 5000
    expected: list[Result | Metric] = [
        Result(state=State.WARN, summary="Queue depth: 4900 (warn/crit at 100/4950)"),
        Metric("curdepth", 4900.0, levels=(100.0, 4950.0), boundaries=(0.0, 5000.0)),
    ]
    assert_depth(curdepth, maxdepth, params, expected)


def assert_depth(
    curdepth: int,
    maxdepth: int | None,
    params: _QueueParams,
    expected: Sequence[Result | Metric],
) -> None:
    queue_data: dict[str, str] = {
        "CURDEPTH": str(curdepth),
        "MSGAGE": "2201",
        "IPPROCS": "5",
        "OPPROCS": "0",
    }
    if maxdepth is not None:
        queue_data["MAXDEPTH"] = str(maxdepth)
    parsed: dict[str, dict[str, str]] = {
        "QM1": {"STATUS": "RUNNING"},
        "QM1:MY.QUEUE": queue_data,
    }
    actual = list(check_ibm_mq_queues("QM1:MY.QUEUE", params, parsed))
    assert actual[:2] == expected


#
# MSGAGE
#


def test_age_no_params() -> None:
    params: _QueueParams = {}
    msgage = 1800
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Oldest message: 30 minutes 0 seconds"),
        Metric("msgage", 1800.0),
    ]
    assert_age(msgage, params, expected)


def test_age_no_msgage() -> None:
    params: _QueueParams = {}
    msgage = None
    expected = [Result(state=State.OK, summary="Oldest message: n/a")]
    assert_age(msgage, params, expected)


def test_age_ok() -> None:
    params: _QueueParams = {"msgage": (1800, 3600)}
    msgage = 1200
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Oldest message: 20 minutes 0 seconds"),
        Metric("msgage", 1200.0, levels=(1800.0, 3600.0)),
    ]
    assert_age(msgage, params, expected)


def test_age_warn() -> None:
    params: _QueueParams = {"msgage": (1800, 3600)}
    msgage = 1801
    expected: list[Result | Metric] = [
        Result(
            state=State.WARN,
            summary="Oldest message: 30 minutes 1 second (warn/crit at 30 minutes 0 seconds/1 hour 0 minutes)",
        ),
        Metric("msgage", 1801.0, levels=(1800.0, 3600.0)),
    ]
    assert_age(msgage, params, expected)


def test_age_crit() -> None:
    params: _QueueParams = {"msgage": (1800, 3600)}
    msgage = 3601
    expected: list[Result | Metric] = [
        Result(
            state=State.CRIT,
            summary="Oldest message: 1 hour 0 minutes (warn/crit at 30 minutes 0 seconds/1 hour 0 minutes)",
        ),
        Metric("msgage", 3601.0, levels=(1800.0, 3600.0)),
    ]
    assert_age(msgage, params, expected)


def assert_age(
    msgage: int | None, params: _QueueParams, expected: Sequence[Result | Metric]
) -> None:
    queue_data: dict[str, str] = {
        "CURDEPTH": "13",
        "MAXDEPTH": "5000",
        "MSGAGE": "" if msgage is None else str(msgage),
        "IPPROCS": "5",
        "OPPROCS": "0",
    }
    parsed: dict[str, dict[str, str]] = {
        "QM1": {"STATUS": "RUNNING"},
        "QM1:MY.QUEUE": queue_data,
    }
    actual = list(check_ibm_mq_queues("QM1:MY.QUEUE", params, parsed))
    # First two results are the depth Result+Metric; msgage follows.
    assert actual[2 : 2 + len(expected)] == expected


#
#  Last GET (or PUT) age
#


def test_lget_ok_no_params() -> None:
    lget = ("2018-04-19", "10.19.05")
    now = ("2018-04-19", "11.19.05")
    params: _QueueParams = {}
    expected = [Result(state=State.OK, summary="Last get: 1 hour 0 minutes")]
    assert_last_get_age(lget, now, params, expected)


def test_lget_ok_no_info() -> None:
    lget = ("", "")
    now = ("2018-04-19", "11.19.05")
    params: _QueueParams = {}
    expected = [Result(state=State.OK, summary="Last get: n/a")]
    assert_last_get_age(lget, now, params, expected)


def test_lget_ok() -> None:
    lget = ("2018-04-19", "10.19.05")
    now = ("2018-04-19", "10.19.15")
    params: _QueueParams = {"lgetage": (1800, 3600)}
    expected = [Result(state=State.OK, summary="Last get: 10 seconds")]
    assert_last_get_age(lget, now, params, expected)


def test_lget_warn() -> None:
    lget = ("2018-04-19", "09.49.14")
    now = ("2018-04-19", "10.19.15")
    params: _QueueParams = {"lgetage": (1800, 3600)}
    expected = [
        Result(
            state=State.WARN,
            summary="Last get: 30 minutes 1 second (warn/crit at 30 minutes 0 seconds/1 hour 0 minutes)",
        ),
    ]
    assert_last_get_age(lget, now, params, expected)


def test_lget_no_info_with_params() -> None:
    lget = ("", "")
    now = ("2018-04-19", "10.19.15")
    params: _QueueParams = {"lgetage": (1800, 3600)}
    expected = [Result(state=State.OK, summary="Last get: n/a")]
    assert_last_get_age(lget, now, params, expected)


def test_lget_crit() -> None:
    lget = ("2018-04-19", "09.19.14")
    now = ("2018-04-19", "10.19.15")
    params: _QueueParams = {"lgetage": (1800, 3600)}
    expected = [
        Result(
            state=State.CRIT,
            summary="Last get: 1 hour 0 minutes (warn/crit at 30 minutes 0 seconds/1 hour 0 minutes)",
        ),
    ]
    assert_last_get_age(lget, now, params, expected)


def assert_last_get_age(
    lget: tuple[str, str],
    now: tuple[str, str],
    params: _QueueParams,
    expected: Sequence[Result | Metric],
) -> None:
    lgetdate, lgettime = lget
    reference_iso_time = "{}T{}+0200".format(now[0], now[1].replace(".", ":"))
    parsed: dict[str, dict[str, str]] = {
        "QM1": {
            "STATUS": "RUNNING",
            "NOW": reference_iso_time,
        },
        "QM1:MY.QUEUE": {
            "CURDEPTH": "0",
            "MAXDEPTH": "5000",
            "LGETDATE": lgetdate,
            "LGETTIME": lgettime,
        },
    }

    actual = list(check_ibm_mq_queues("QM1:MY.QUEUE", params, parsed))
    # Skip the depth result+metric (2 items) at the start.
    assert actual[2 : 2 + len(expected)] == expected


#
# IPPROCS/OPPROCS
#


def test_procs_no_params() -> None:
    params: _QueueParams = {}
    opprocs = 3
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Open output handles: 3"),
        Metric("opprocs", 3.0),
    ]
    assert_procs(opprocs, params, expected)


def test_procs_upper() -> None:
    params: _QueueParams = {"opprocs": {"upper": (10, 20)}}

    opprocs = 3
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Open output handles: 3"),
        Metric("opprocs", 3.0, levels=(10.0, 20.0)),
    ]
    assert_procs(opprocs, params, expected)

    opprocs = 10
    expected = [
        Result(state=State.WARN, summary="Open output handles: 10 (warn/crit at 10/20)"),
        Metric("opprocs", 10.0, levels=(10.0, 20.0)),
    ]
    assert_procs(opprocs, params, expected)

    opprocs = 11
    expected = [
        Result(state=State.WARN, summary="Open output handles: 11 (warn/crit at 10/20)"),
        Metric("opprocs", 11.0, levels=(10.0, 20.0)),
    ]
    assert_procs(opprocs, params, expected)

    opprocs = 20
    expected = [
        Result(state=State.CRIT, summary="Open output handles: 20 (warn/crit at 10/20)"),
        Metric("opprocs", 20.0, levels=(10.0, 20.0)),
    ]
    assert_procs(opprocs, params, expected)

    opprocs = 21
    expected = [
        Result(state=State.CRIT, summary="Open output handles: 21 (warn/crit at 10/20)"),
        Metric("opprocs", 21.0, levels=(10.0, 20.0)),
    ]
    assert_procs(opprocs, params, expected)


def test_procs_lower() -> None:
    params: _QueueParams = {"opprocs": {"lower": (3, 1)}}

    opprocs = 3
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Open output handles: 3"),
        Metric("opprocs", 3.0),
    ]
    assert_procs(opprocs, params, expected)

    opprocs = 2
    expected = [
        Result(state=State.WARN, summary="Open output handles: 2 (warn/crit below 3/1)"),
        Metric("opprocs", 2.0),
    ]
    assert_procs(opprocs, params, expected)

    opprocs = 1
    expected = [
        Result(state=State.WARN, summary="Open output handles: 1 (warn/crit below 3/1)"),
        Metric("opprocs", 1.0),
    ]
    assert_procs(opprocs, params, expected)

    opprocs = 0
    expected = [
        Result(state=State.CRIT, summary="Open output handles: 0 (warn/crit below 3/1)"),
        Metric("opprocs", 0.0),
    ]
    assert_procs(opprocs, params, expected)


def test_procs_lower_and_upper() -> None:
    params: _QueueParams = {
        "opprocs": {
            "lower": (3, 1),
            "upper": (10, 20),
        }
    }

    opprocs = 1
    expected: list[Result | Metric] = [
        Result(state=State.WARN, summary="Open output handles: 1 (warn/crit below 3/1)"),
        Metric("opprocs", 1.0, levels=(10.0, 20.0)),
    ]
    assert_procs(opprocs, params, expected)

    opprocs = 0
    expected = [
        Result(state=State.CRIT, summary="Open output handles: 0 (warn/crit below 3/1)"),
        Metric("opprocs", 0.0, levels=(10.0, 20.0)),
    ]
    assert_procs(opprocs, params, expected)

    opprocs = 21
    expected = [
        Result(state=State.CRIT, summary="Open output handles: 21 (warn/crit at 10/20)"),
        Metric("opprocs", 21.0, levels=(10.0, 20.0)),
    ]
    assert_procs(opprocs, params, expected)


def assert_procs(opprocs: int, params: _QueueParams, expected: Sequence[Result | Metric]) -> None:
    parsed: dict[str, dict[str, str]] = {
        "QM1": {"STATUS": "RUNNING"},
        "QM1:MY.QUEUE": {
            "CURDEPTH": "0",
            "MAXDEPTH": "5000",
            "OPPROCS": str(opprocs),
        },
    }
    actual = list(check_ibm_mq_queues("QM1:MY.QUEUE", params, parsed))
    # Skip depth Result+Metric at the start.
    assert actual[2 : 2 + len(expected)] == expected


#
# QTIME
#


def test_qtime_no_values() -> None:
    params: _QueueParams = {}
    qtime = ","
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Qtime short: n/a"),
        Metric("qtime_short", 0.0),
        Result(state=State.OK, summary="Qtime long: n/a"),
        Metric("qtime_long", 0.0),
    ]
    assert_qtime(qtime, params, expected)


def test_qtime_only_short() -> None:
    params: _QueueParams = {}
    qtime = "300000000,"
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Qtime short: 5 minutes 0 seconds"),
        Metric("qtime_short", 300.0),
        Result(state=State.OK, summary="Qtime long: n/a"),
        Metric("qtime_long", 0.0),
    ]
    assert_qtime(qtime, params, expected)


def test_qtime_both() -> None:
    params: _QueueParams = {}
    qtime = "300000000,420000000"
    expected: list[Result | Metric] = [
        Result(state=State.OK, summary="Qtime short: 5 minutes 0 seconds"),
        Metric("qtime_short", 300.0),
        Result(state=State.OK, summary="Qtime long: 7 minutes 0 seconds"),
        Metric("qtime_long", 420.0),
    ]
    assert_qtime(qtime, params, expected)


def assert_qtime(qtime: str, params: _QueueParams, expected: Sequence[Result | Metric]) -> None:
    parsed: dict[str, dict[str, str]] = {
        "QM1": {"STATUS": "RUNNING"},
        "QM1:MY.QUEUE": {
            "CURDEPTH": "0",
            "MAXDEPTH": "5000",
            "QTIME": qtime,
        },
    }
    actual = list(check_ibm_mq_queues("QM1:MY.QUEUE", params, parsed))
    # Skip depth Result+Metric at the start.
    assert actual[2:] == expected
