#!/usr/bin/env python
# encoding: utf-8

import pytest
import time
import ast
import pathlib2 as pathlib
import threading
import logging

from testlib import CMKEventConsole, ec, web
import cmk.ec.settings
import cmk.utils.paths
import cmk.ec.main


class FakeStatusSocket(object):
    def __init__(self, query):
        self._query = query
        self._sent = False
        self._response = ""

    def recv(self, size):
        if self._sent:
            return ""

        self._sent = True
        return self._query

    def sendall(self, data):
        self._response += data

    def close(self):
        pass

    def get_response(self):
        response = ast.literal_eval(self._response)
        assert isinstance(response, list)
        return response


@pytest.fixture(scope="function")
def settings():
    return cmk.ec.settings.settings('1.2.3i45', pathlib.Path(cmk.utils.paths.omd_root),
                                    pathlib.Path(cmk.utils.paths.default_config_dir), ['mkeventd'])


@pytest.fixture(scope="function")
def lock_configuration():
    return cmk.ec.main.ECLock(logging.getLogger("cmk.mkeventd.configuration"))


@pytest.fixture(scope="function")
def slave_status():
    return cmk.ec.main.default_slave_status_master()


@pytest.fixture(scope="function")
def config(settings, slave_status):
    return cmk.ec.main.load_configuration(settings, logging.getLogger("cmk.mkeventd"), slave_status)


@pytest.fixture(scope="function")
def history(settings, config):
    return cmk.ec.history.History(settings, config, logging.getLogger("cmk.mkeventd"),
                                  cmk.ec.main.StatusTableEvents.columns,
                                  cmk.ec.main.StatusTableHistory.columns)


@pytest.fixture(scope="function")
def perfcounters():
    return cmk.ec.main.Perfcounters(logging.getLogger("cmk.mkeventd.lock.perfcounters"))


@pytest.fixture(scope="function")
def event_status(settings, config, perfcounters, history):
    return cmk.ec.main.EventStatus(settings, config, perfcounters, history,
                                   logging.getLogger("cmk.mkeventd.EventStatus"))


@pytest.fixture(scope="function")
def event_server(settings, config, slave_status, perfcounters, lock_configuration, history,
                 event_status):
    return cmk.ec.main.EventServer(
        logging.getLogger("cmk.mkeventd.EventServer"), settings, config, slave_status, perfcounters,
        lock_configuration, history, event_status, cmk.ec.main.StatusTableEvents.columns)


@pytest.fixture(scope="function")
def status_server(settings, config, slave_status, perfcounters, lock_configuration, history,
                  event_status, event_server):
    return cmk.ec.main.StatusServer(
        logging.getLogger("cmk.mkeventd.StatusServer"), settings, config, slave_status,
        perfcounters, lock_configuration, history, event_status, event_server, threading.Event())


def test_handle_client(status_server):
    s = FakeStatusSocket("GET events")

    status_server.handle_client(s, True, "127.0.0.1")

    response = s.get_response()
    assert len(response) == 1
    assert "event_id" in response[0]


def test_mkevent_check_query_perf(config, event_status, status_server):
    for num in range(10000):
        event_status.new_event(CMKEventConsole.new_event({
            "host": "heute-%d" % num,
            "text": "%s %s BLA BLUB DINGELING ABASD AD R#@A AR@AR A@ RA@R A@RARAR ARKNLA@RKA@LRKNA@KRLNA@RLKNA@äRLKA@RNKAL@R" \
                    " j:O#A@J$ KLA@J $L:A@J :AMW: RAMR@: RMA@:LRMA@ L:RMA@ :AL@R MA:L@RM A@:LRMA@ :RLMA@ R:LA@RMM@RL:MA@R: AM@" % \
                    (time.time(), num),
        }))

    assert len(event_status.events()) == 10000

    s = FakeStatusSocket("GET events\n"
                         "Filter: event_host in heute-1 127.0.0.1 heute123\n"
                         "Filter: event_phase in open ack\n"
                         #"OutputFormat: plain\n"
                         #"Filter: event_application ~~ xxx\n"
                        )

    before = time.time()

    #import cProfile, StringIO, pstats
    #pr = cProfile.Profile()
    #pr.enable()
    status_server.handle_client(s, True, "127.0.0.1")
    #pr.disable()
    #ps = pstats.Stats(pr, stream=StringIO.StringIO())
    #ps.dump_stats("/tmp/test_mkevent_check_query_perf.profile")

    duration = time.time() - before

    response = s.get_response()
    assert len(response) == 2
    assert "event_id" in response[0]

    assert duration < 0.2


#
# INTEGRATION TESTS
#


def ensure_core_and_get_connection(site, ec, core):
    if core is not None:
        site.set_config("CORE", core, with_restart=True)
        live = site.live
    else:
        live = ec.status

    return live


@pytest.mark.parametrize(("core"), ["nagios", "cmc"])
def test_command_reload(site, ec, core):
    print "Checking core: %s" % core

    live = ensure_core_and_get_connection(site, ec, core)

    old_t = live.query_value("GET eventconsolestatus\nColumns: status_config_load_time\n")
    print "Old config load time: %s" % old_t
    assert old_t > time.time() - 86400

    time.sleep(1)  # needed to have at least one second after EC start
    live.command("[%d] EC_RELOAD" % (int(time.time())))
    time.sleep(1)  # needed to have at least one second after EC reload

    new_t = live.query_value("GET eventconsolestatus\nColumns: status_config_load_time\n")
    print "New config load time: %s" % old_t
    assert new_t > old_t


# core is None means direct query to status socket
@pytest.mark.parametrize(("core"), [None, "nagios", "cmc"])
def test_status_table_via_core(site, ec, core):
    print "Checking core: %s" % core

    live = ensure_core_and_get_connection(site, ec, core)
    if core is None:
        result = live.query_table_assoc("GET status\n")
    else:
        result = live.query_table_assoc("GET eventconsolestatus\n")

    assert len(result) == 1

    status = result[0]

    for column_name in [
            'status_config_load_time',
            'status_num_open_events',
            'status_messages',
            'status_message_rate',
            'status_average_message_rate',
            'status_connects',
            'status_connect_rate',
            'status_average_connect_rate',
            'status_rule_tries',
            'status_rule_trie_rate',
            'status_average_rule_trie_rate',
            'status_drops',
            'status_drop_rate',
            'status_average_drop_rate',
            'status_events',
            'status_event_rate',
            'status_average_event_rate',
            'status_rule_hits',
            'status_rule_hit_rate',
            'status_average_rule_hit_rate',
            'status_average_processing_time',
            'status_average_request_time',
            'status_average_sync_time',
            'status_replication_slavemode',
            'status_replication_last_sync',
            'status_replication_success',
            'status_event_limit_host',
            'status_event_limit_rule',
            'status_event_limit_overall',
    ]:
        assert column_name in status

    assert isinstance(status["status_event_limit_host"], int)
    assert isinstance(status["status_event_limit_rule"], int)
    assert isinstance(status["status_event_limit_overall"], int)


# core is None means direct query to status socket
@pytest.mark.parametrize(("core"), [None, "nagios", "cmc"])
def test_rules_table_via_core(site, ec, core):
    print "Checking core: %s" % core

    live = ensure_core_and_get_connection(site, ec, core)
    if core is None:
        result = live.query_table_assoc("GET rules\n")
    else:
        result = live.query_table_assoc("GET eventconsolerules\n")

    assert isinstance(result, list)
    #assert len(result) == 0
    # TODO: Add some rule before the test and then check the existing
    # keys and types in the result set
