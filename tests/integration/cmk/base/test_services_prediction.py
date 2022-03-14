#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import time
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

import pytest

from tests.testlib import create_linux_test_host, on_time, repo_path
from tests.testlib.site import Site

import cmk.utils.prediction
from cmk.utils import version as cmk_version
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import HostName

from cmk.base import prediction


@pytest.fixture(name="cfg_setup", scope="module")
def cfg_setup_fixture(request, web, site: Site):
    hostname = "test-prediction"

    # Enforce use of the pre-created RRD file from the git. The restart of the core
    # is needed to make it renew it's internal RRD file cache
    site.makedirs("var/check_mk/rrd/test-prediction")
    with open(site.path("var/check_mk/rrd/test-prediction/CPU_load.rrd"), "wb") as f:
        f.write(
            Path(
                repo_path(), "tests", "integration", "cmk", "base", "test-files", "CPU_load.rrd"
            ).read_bytes()
        )

    site.write_text_file(
        "var/check_mk/rrd/test-prediction/CPU_load.info",
        Path(
            repo_path(), "tests", "integration", "cmk", "base", "test-files", "CPU_load.info"
        ).read_text(),
    )

    site.restart_core()

    create_linux_test_host(request, site, "test-prediction")

    site.write_text_file(
        "etc/check_mk/conf.d/linux_test_host_%s_cpu_load.mk" % hostname,
        """
globals().setdefault('custom_checks', [])

custom_checks = [
    ( {'service_description': u'CPU load', 'has_perfdata': True}, [], ALL_HOSTS, {} ),
] + custom_checks
""",
    )

    site.activate_changes_and_wait_for_core_reload()

    yield

    # Cleanup
    site.delete_file("etc/check_mk/conf.d/linux_test_host_%s_cpu_load.mk" % hostname)
    site.delete_dir("var/check_mk/rrd")


# This test has a conflict with daemon usage. Since we now don't use
# daemon, the lower resolution is somehow preferred. Despite having a
# higher available. See https://github.com/oetiker/rrdtool-1.x/issues/1063
@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="rrd data currently not working on nagios")
@pytest.mark.parametrize(
    "utcdate, timezone, period, result",
    [
        pytest.param(
            "2018-11-28 12", "UTC", "minute", (60, 60), id="1 min resolution in hour query"
        ),
        pytest.param(
            "2018-11-27 12", "UTC", "minute", (300, 12), id="5 min resolution in hour query"
        ),
        pytest.param(
            "2018-11-15 12:25", "UTC", "minute", (1800, 2), id="30 min resolution in hour query"
        ),
        pytest.param(
            "2018-07-15 12", "UTC", "minute", (21600, 1), id="hour query when resolution is 6hrs"
        ),
        pytest.param(
            "2018-11-28 12",
            "UTC",
            "wday",
            (300, 288),
            id="max 400(default) points of data response",
        ),
        pytest.param(
            "2018-11-27 12", "UTC", "wday", (300, 288), id="5 min resolution in day query"
        ),
        pytest.param(
            "2018-11-10 12", "UTC", "day", (1800, 48), id="30 min resolution in day query"
        ),
        pytest.param(
            "2018-06-10 12", "UTC", "hour", (21600, 4), id="6hrs resolution in day query, in UTC"
        ),
        pytest.param(
            "2018-06-10 12",
            "Europe/Berlin",
            "hour",
            (21600, 5),
            id="6hrs resolution in day query, in Berlin",
        ),
        pytest.param(
            "2018-06-10 12",
            "America/New_York",
            "hour",
            (21600, 5),
            id="6hrs resolution in day query, in New_York",
        ),
    ],
)
def test_get_rrd_data(cfg_setup, utcdate, timezone, period, result):

    with on_time(utcdate, timezone):
        timestamp = time.time()
        _, from_time, until_time, _ = prediction._get_prediction_timegroup(
            int(timestamp), prediction._PREDICTION_PERIODS[period]
        )

    timeseries = cmk.utils.prediction.get_rrd_data(
        HostName("test-prediction"), "CPU load", "load15", "MAX", from_time, until_time
    )

    assert timeseries.start <= from_time
    assert timeseries.end >= until_time
    assert (timeseries.step, len(timeseries.values)) == result


# This test has a conflict with daemon usage. Since we now don't use
# daemon, the lower resolution is somehow preferred. Despite having a
# higher available. See https://github.com/oetiker/rrdtool-1.x/issues/1063
@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="rrd data currently not working on nagios")
@pytest.mark.parametrize(
    "max_entries, result",
    [(400, (180, 401)), (20, (3600, 21)), (50, (1800, 41)), (1000, (120, 600)), (1200, (60, 1200))],
)
def test_get_rrd_data_point_max(cfg_setup, max_entries, result):
    from_time, until_time = 1543430040, 1543502040
    timeseries = cmk.utils.prediction.get_rrd_data(
        HostName("test-prediction"), "CPU load", "load15", "MAX", from_time, until_time, max_entries
    )
    assert timeseries.start <= from_time
    assert timeseries.end >= until_time
    assert (timeseries.step, len(timeseries.values)) == result


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="rrd data currently not working on nagios")
@pytest.mark.parametrize(
    "utcdate, timezone, params, reference",
    [
        (
            "2018-09-01 07:00",
            "Europe/Berlin",
            {"period": "wday", "horizon": 10},
            (
                (1535752800, 1535839200, 1800),
                [
                    [
                        0.0966667,
                        0.1,
                        0.14,
                        0.120167,
                        0.0986667,
                        0.11,
                        0.0953333,
                        0.08,
                        0.1,
                        0.1,
                        0.118333,
                        0.0966667,
                        0.21,
                        0.163667,
                        0.1,
                        0.158,
                        0.107333,
                        0.08,
                        0.06,
                        0.12,
                        0.1085,
                        0.1,
                        0.0953333,
                        0.09,
                        0.11,
                        0.125,
                        0.13,
                        0.12,
                        0.1,
                        0.12,
                        0.0978333,
                        0.13,
                        0.08,
                        0.0775,
                        0.3045,
                        0.11,
                        0.09,
                        0.126667,
                        0.098,
                        0.24,
                        0.1995,
                        0.12,
                        0.134833,
                        0.14,
                        0.13,
                        0.13,
                        0.139333,
                        0.185333,
                    ],
                    [0.203833] * 4 + [0.115583] * 12 + [0.463333] * 12 + [0.13] * 12 + [0.1645] * 8,
                ],
            ),
        ),
        (
            "2018-09-02 10:00",
            "America/New_York",
            {
                "period": "wday",
                "horizon": 10,
            },
            (
                (1535860800, 1535947200, 1800),
                [
                    [
                        0.0981667,
                        0.18,
                        0.0853333,
                        0.0886667,
                        0.122,
                        0.16,
                        0.15475,
                        0.12,
                        0.07,
                        0.04,
                        0.0493333,
                        0.118667,
                        0.1,
                        0.08,
                        0.0891667,
                        0.12,
                        0.0996667,
                        0.0248333,
                        0.06,
                        0.0958333,
                        0.15,
                        0.11,
                        0.1,
                        0.0956667,
                        0.1,
                        0.0918333,
                        0.12,
                        0.11,
                        0.1,
                        0.124333,
                        0.05,
                        0.115667,
                        0.135833,
                        0.1,
                        0.0646667,
                        0.12,
                        0.203167,
                        0.13,
                        0.0483333,
                        0.0438333,
                        0.09,
                        0.12,
                        0.12,
                        0.12,
                        0.109167,
                        0.0745,
                        0.11,
                        0.114167,
                    ],
                    [0.2] * 4 + [0.201333] * 12 + [0.16] * 12 + [0.13] * 12 + [0.1585] * 8,
                ],
            ),
        ),
        (
            "2018-09-02 10:00",
            "Asia/Yekaterinburg",
            {
                "period": "wday",
                "horizon": 10,
            },
            (
                (1535828400, 1535914800, 1800),
                [
                    [
                        0.134833,
                        0.14,
                        0.13,
                        0.13,
                        0.139333,
                        0.185333,
                        0.242833,
                        0.11,
                        0.12,
                        0.09,
                        0.0513333,
                        0.0951667,
                        0.0891667,
                        0.06,
                        0.1,
                        0.1905,
                        0.11,
                        0.1,
                        0.0981667,
                        0.18,
                        0.0853333,
                        0.0886667,
                        0.122,
                        0.16,
                        0.15475,
                        0.12,
                        0.07,
                        0.04,
                        0.0493333,
                        0.118667,
                        0.1,
                        0.08,
                        0.0891667,
                        0.12,
                        0.0996667,
                        0.0248333,
                        0.06,
                        0.0958333,
                        0.15,
                        0.11,
                        0.1,
                        0.0956667,
                        0.1,
                        0.0918333,
                        0.12,
                        0.11,
                        0.1,
                        0.124333,
                    ],
                    [0.1645] * 10 + [0.2] * 12 + [0.201333] * 12 + [0.16] * 12 + [0.13, 0.13],
                ],
            ),
        ),
        (
            "2018-09-03 10:00",
            "UTC",
            {
                "period": "wday",
                "horizon": 10,
            },
            (
                (1535932800, 1536019200, 1800),
                [
                    [
                        0.09,
                        0.12,
                        0.12,
                        0.12,
                        0.109167,
                        0.0745,
                        0.11,
                        0.114167,
                        0.257,
                        0.2,
                        0.14,
                        0.09,
                        0.14,
                        0.124833,
                        0.11,
                        0.09,
                        0.18,
                        0.121333,
                        0.086,
                        0.0963333,
                        0.13,
                        0.09,
                        0.2,
                        0.13,
                        0.136,
                        0.1695,
                        0.16,
                        0.17,
                        0.186833,
                        0.0873333,
                        0.131333,
                        0.115833,
                        0.11,
                        0.14,
                        0.25,
                        0.169,
                        0.0905,
                        0.0885,
                        0.11,
                        0.1,
                        0.067,
                        0.1,
                        0.13,
                        0.130833,
                        0.18,
                        0.11,
                        0.109333,
                        0.105833,
                    ],
                    [0.1585] * 12 + [0.13] * 12 + [0.26] * 12 + [0.3] * 12,
                ],
            ),
        ),
    ],
)
def test_retieve_grouped_data_from_rrd(cfg_setup, utcdate, timezone, params, reference):
    "This mostly verifies the up-sampling"

    period_info = prediction._PREDICTION_PERIODS[params["period"]]
    with on_time(utcdate, timezone):
        now = int(time.time())
        assert callable(period_info.groupby)
        timegroup = period_info.groupby(now)[0]
        time_windows = prediction._time_slices(
            now, int(params["horizon"] * 86400), period_info, timegroup
        )

    hostname, service_description, dsname = HostName("test-prediction"), "CPU load", "load15"
    rrd_datacolumn = cmk.utils.prediction.rrd_datacolum(
        hostname, service_description, dsname, "MAX"
    )
    result = prediction._retrieve_grouped_data_from_rrd(rrd_datacolumn, time_windows)

    assert result == reference


def _load_expected_result(path: str) -> object:
    return json.loads(open(path).read())


# This test has a conflict with daemon usage. Since we now don't use
# daemon, the lower resolution is somehow preferred. Despite having a
# higher available. See https://github.com/oetiker/rrdtool-1.x/issues/1063
@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="rrd data currently not working on nagios")
@pytest.mark.parametrize(
    "utcdate, timezone, params",
    [
        ("2018-11-29 14:56", "Europe/Berlin", {"period": "wday", "horizon": 90}),
        ("2018-11-26 07:00", "Europe/Berlin", {"period": "day", "horizon": 90}),
        ("2018-11-10 07:00", "Europe/Berlin", {"period": "hour", "horizon": 90}),
        (
            "2018-07-15 10:00",
            "America/New_York",
            {
                "period": "hour",
                "horizon": 10,
            },
        ),
        (
            "2018-07-15 10:00",
            "UTC",
            {
                "period": "wday",
                "horizon": 10,
            },
        ),
    ],
)
def test_calculate_data_for_prediction(cfg_setup, utcdate, timezone, params):

    period_info = prediction._PREDICTION_PERIODS[params["period"]]
    with on_time(utcdate, timezone):
        now = int(time.time())
        assert callable(period_info.groupby)
        timegroup = period_info.groupby(now)[0]

        time_windows = prediction._time_slices(
            now, int(params["horizon"] * 86400), period_info, timegroup
        )

    hostname, service_description, dsname = HostName("test-prediction"), "CPU load", "load15"
    rrd_datacolumn = cmk.utils.prediction.rrd_datacolum(
        hostname, service_description, dsname, "MAX"
    )
    data_for_pred = prediction._calculate_data_for_prediction(time_windows, rrd_datacolumn)

    expected_reference = _load_expected_result(
        "%s/tests/integration/cmk/base/test-files/%s/%s" % (repo_path(), timezone, timegroup)
    )

    assert isinstance(expected_reference, dict)
    assert sorted(asdict(data_for_pred)) == sorted(expected_reference)
    for key in expected_reference:
        if key == "points":
            for cal, ref in zip(data_for_pred.points, expected_reference["points"]):
                assert cal == pytest.approx(ref, rel=1e-12, abs=1e-12)
        else:
            assert getattr(data_for_pred, key) == expected_reference[key]


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="rrd data currently not working on nagios")
@pytest.mark.parametrize(
    "timerange, result",
    [
        pytest.param(
            (1543503060.0, 1543503300.0),
            (60, [0.08, 0.08, None, None]),
            id="Instant data, window in past & future",
        ),
        pytest.param(
            (1543587600.0, 1543587800.0),
            (60, [None, None, None, None]),
            id="Data ahead in the future",
        ),
    ],
)
def test_get_rrd_data_incomplete(cfg_setup, timerange, result):
    from_time, until_time = timerange
    timeseries = cmk.utils.prediction.get_rrd_data(
        HostName("test-prediction"), "CPU load", "load15", "MAX", from_time, until_time
    )

    assert timeseries.start <= from_time
    assert timeseries.end >= until_time
    assert (timeseries.step, timeseries.values) == result


def test_get_rrd_data_fails(cfg_setup):
    timestamp = time.mktime(datetime.strptime("2018-11-28 12", "%Y-%m-%d %H").timetuple())
    _, from_time, until_time, _ = prediction._get_prediction_timegroup(
        int(timestamp), prediction._PREDICTION_PERIODS["hour"]
    )

    # Fail to get data, because non-existent check
    with pytest.raises(MKGeneralException, match="Cannot get historic metrics via Livestatus:"):
        cmk.utils.prediction.get_rrd_data(
            HostName("test-prediction"), "Nonexistent check", "util", "MAX", from_time, until_time
        )

    # Empty response, because non-existent perf_data variable
    timeseries = cmk.utils.prediction.get_rrd_data(
        HostName("test-prediction"), "CPU load", "untracked_prefdata", "MAX", from_time, until_time
    )

    assert timeseries == cmk.utils.prediction.TimeSeries([0, 0, 0])
