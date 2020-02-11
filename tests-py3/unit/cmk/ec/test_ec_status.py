#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-

import ast
import logging
import pathlib  # pylint: disable=import-error
import threading
import time

import pytest  # type: ignore[import]

from testlib import CMKEventConsole
import cmk.utils.paths
import cmk.ec.history
import cmk.ec.main
import cmk.ec.export as ec


class FakeStatusSocket:
    def __init__(self, query):
        # type: (bytes) -> None
        self._query = query
        self._sent = False
        self._response = b""

    def recv(self, size):
        # type: (int) -> bytes
        if self._sent:
            return b""

        self._sent = True
        return self._query

    def sendall(self, data):
        # type: (bytes) -> None
        self._response += data

    def close(self):
        # type: () -> None
        pass

    def get_response(self):
        response = ast.literal_eval(self._response.decode("utf-8"))
        assert isinstance(response, list)
        return response


@pytest.fixture(name="settings", scope="function")
def fixture_settings():
    return ec.settings('1.2.3i45', pathlib.Path(cmk.utils.paths.omd_root),
                       pathlib.Path(cmk.utils.paths.default_config_dir), ['mkeventd'])


@pytest.fixture(name="lock_configuration", scope="function")
def fixture_lock_configuration():
    return cmk.ec.main.ECLock(logging.getLogger("cmk.mkeventd.configuration"))


@pytest.fixture(name="slave_status", scope="function")
def fixture_slave_status():
    return cmk.ec.main.default_slave_status_master()


@pytest.fixture(name="config", scope="function")
def fixture_config():
    return ec.default_config()


@pytest.fixture(name="history", scope="function")
def fixture_history(settings, config):
    return cmk.ec.history.History(settings, config, logging.getLogger("cmk.mkeventd"),
                                  cmk.ec.main.StatusTableEvents.columns,
                                  cmk.ec.main.StatusTableHistory.columns)


@pytest.fixture(name="perfcounters", scope="function")
def fixture_perfcounters():
    return cmk.ec.main.Perfcounters(logging.getLogger("cmk.mkeventd.lock.perfcounters"))


@pytest.fixture(name="event_status", scope="function")
def fixture_event_status(settings, config, perfcounters, history):
    return cmk.ec.main.EventStatus(settings, config, perfcounters, history,
                                   logging.getLogger("cmk.mkeventd.EventStatus"))


@pytest.fixture(name="status_server", scope="function")
def fixture_status_server(settings, config, slave_status, perfcounters, lock_configuration, history,
                          event_status):
    return cmk.ec.main.StatusServer(logging.getLogger("cmk.mkeventd.StatusServer"), settings,
                                    config, slave_status, perfcounters, lock_configuration, history,
                                    event_status, None, threading.Event())


def test_handle_client(status_server):
    s = FakeStatusSocket(b"GET events")

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

    s = FakeStatusSocket(b"GET events\n"
                         b"Filter: event_host in heute-1 127.0.0.1 heute123\n"
                         b"Filter: event_phase in open ack\n"
                         #b"OutputFormat: plain\n"
                         #b"Filter: event_application ~~ xxx\n"
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
