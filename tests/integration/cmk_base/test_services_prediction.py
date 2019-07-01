# pylint: disable=redefined-outer-name

from datetime import datetime
import os
import time

import pytest
import cmk.prediction
from cmk_base import prediction
from cmk.exceptions import MKGeneralException

from testlib import web, repo_path  # pylint: disable=unused-import


def create_linux_test_host(request, web, site, hostname):
    def finalizer():
        web.delete_host(hostname)
        web.activate_changes()
        site.delete_file("var/check_mk/agent_output/%s" % hostname)
        site.delete_file("etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname)

    request.addfinalizer(finalizer)

    web.add_host(hostname, attributes={"ipaddress": "127.0.0.1"})

    site.write_file(
        "etc/check_mk/conf.d/linux_test_host_%s.mk" % hostname,
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ['%s']))\n" %
        hostname)

    site.makedirs("var/check_mk/agent_output/")
    site.write_file(
        "var/check_mk/agent_output/%s" % hostname,
        file("%s/tests/integration/cmk_base/test-files/linux-agent-output" % repo_path()).read())


@pytest.fixture(scope="module")
def cfg_setup(request, web, site):
    create_linux_test_host(request, web, site, "test-prediction")
    web.discover_services("test-prediction")
    web.activate_changes()

    # Enforce use of the pre-created RRD file from the git. The restart of the core
    # is needed to make it renew it's internal RRD file cache
    site.makedirs("var/check_mk/rrd/test-prediction/")
    site.write_file(
        "var/check_mk/rrd/test-prediction/CPU_load.rrd",
        file("%s/tests/integration/cmk_base/test-files/CPU_load.rrd" % repo_path()).read())
    site.write_file(
        "var/check_mk/rrd/test-prediction/CPU_load.info",
        file("%s/tests/integration/cmk_base/test-files/CPU_load.info" % repo_path()).read())
    site.omd("restart", "cmc")

    yield

    # Cleanup
    site.delete_dir("var/check_mk/rrd/")


@pytest.mark.parametrize('date, period, result', [
    pytest.param("2018-11-28 12", "minute", (60, 60), id='1 min resolution in hour query'),
    pytest.param("2018-11-27 12", "minute", (300, 12), id='5 min resolution in hour query'),
    pytest.param("2018-11-15 12", "minute", (1800, 2), id='30 min resolution in hour query'),
    pytest.param("2018-07-15 12", "minute", (21600, 0), id='hour query when resolution is 6hrs'),
    pytest.param("2018-11-28 12", "wday", (240, 360), id='max 360 points of data response'),
    pytest.param("2018-11-27 12", "wday", (300, 288), id='5 min resolution in day query'),
    pytest.param("2018-11-10 12", "day", (1800, 48), id='30 min resolution in day query'),
    pytest.param("2018-06-10 12", "hour", (21600, 4), id='6hrs resolution in day query'),
])
def test_get_rrd_data(cfg_setup, date, period, result):

    timestamp = time.mktime(datetime.strptime(date, "%Y-%m-%d %H").timetuple())
    _, from_time, until_time, _ = prediction.get_prediction_timegroup(
        timestamp, prediction.prediction_periods[period])

    step, data = cmk.prediction.get_rrd_data('test-prediction', 'CPU load', 'load15', 'MAX',
                                             from_time, until_time)
    assert (step, len(data)) == result


@pytest.mark.parametrize('now, params', [
    (1543503360.0, {
        'period': 'wday',
        'horizon': 90
    }),
    (1543215600.0, {
        'period': 'day',
        'horizon': 90
    }),
    (1541833200.0, {
        'period': 'hour',
        'horizon': 90
    }),
])
def test_aggregate_data_for_prediction_and_save(cfg_setup, now, params):
    hostname, service_description, dsname = 'test-prediction', "CPU load", 'load15'
    pred_dir = cmk.prediction.predictions_dir(hostname, service_description, dsname, create=True)

    period_info = prediction.prediction_periods[params['period']]
    timegroup = period_info["groupby"](now)[0]
    pred_file = os.path.join(pred_dir, timegroup)

    data_for_pred = prediction.aggregate_data_for_prediction_and_save(
        hostname, service_description, pred_file, params, period_info, dsname, 'MAX', now)

    reference = cmk.prediction.retrieve_data_for_prediction(
        "%s/tests/integration/cmk_base/test-files/%s" % (repo_path(), timegroup), timegroup)
    assert data_for_pred == reference


@pytest.mark.parametrize('timerange, result', [
    pytest.param((1543503060.0, 1543503300.0), (60, [0.08, 0.08, None, None]),
                 id='Instant data, window in past & future'),
    pytest.param(
        (1543587600.0, 1543587800.0),
        (60, [None, None, None, None]), id='Data ahead in the future'),
])
def test_get_rrd_data_incomplete(cfg_setup, timerange, result):
    from_time, until_time = timerange
    data_response = cmk.prediction.get_rrd_data('test-prediction', 'CPU load', 'load15', 'MAX',
                                                from_time, until_time)
    assert data_response == result


def test_get_rrd_data_fails(cfg_setup):
    timestamp = time.mktime(datetime.strptime("2018-11-28 12", "%Y-%m-%d %H").timetuple())
    _, from_time, until_time, _ = prediction.get_prediction_timegroup(
        timestamp, prediction.prediction_periods["hour"])

    # Fail to get data, because non-existent check
    with pytest.raises(MKGeneralException, match="Cannot get historic metrics via Livestatus:"):
        cmk.prediction.get_rrd_data('test-prediction', 'Nonexistent check', 'util', 'MAX',
                                    from_time, until_time)

    # Empty response, because non-existent perf_data variable
    step, data = cmk.prediction.get_rrd_data('test-prediction', 'CPU utilization',
                                             'untracked_prefdata', 'MAX', from_time, until_time)

    assert step == 0
    assert data == []
