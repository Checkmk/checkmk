#!/usr/bin/env python
# encoding: utf-8

import pytest
import time
from testlib import web, ec, cmk_path

#
# UNIT TESTS
#

import imp
mkeventd = imp.load_source("mkeventd", "%s/bin/mkeventd" % cmk_path())

def test_mkeventd_unit():
    assert mkeventd


def test_handle_client(monkeypatch):
    class FakeSocket(object):
        def __init__(self, sock):
            pass

        def __iter__(self):
            return self

        def next(self):
            return ["GET events"]

        def close(self):
            pass

    monkeypatch.setattr(mkeventd, "Queries", FakeSocket)
    monkeypatch.setattr(mkeventd.StatusServer, "open_sockets", lambda x: None)
    status = mkeventd.StatusServer()

    print status.handle_client(None, True, "127.0.0.1")


#
# INTEGRATION TESTS
#

def ensure_core_and_get_connection(site, ec, core):
    if core != None:
        site.set_config("CORE", core, with_restart=True)
        live = site.live
    else:
        live = ec.status

    return live


@pytest.mark.parametrize(("core"), [ "nagios", "cmc" ])
def test_command_reload(site, ec, core):
    print "Checking core: %s" % core

    live = ensure_core_and_get_connection(site, ec, core)

    old_t = live.query_value("GET eventconsolestatus\nColumns: status_config_load_time\n")
    print "Old config load time: %s" % old_t
    assert old_t > time.time() - 86400

    time.sleep(1) # needed to have at least one second after EC start
    live.command("[%d] EC_RELOAD" % (int(time.time())))
    time.sleep(1) # needed to have at least one second after EC reload

    new_t = live.query_value("GET eventconsolestatus\nColumns: status_config_load_time\n")
    print "New config load time: %s" % old_t
    assert new_t > old_t


# core == None means direct query to status socket
@pytest.mark.parametrize(("core"), [ None, "nagios", "cmc" ])
def test_status_table_via_core(site, ec, core):
    print "Checking core: %s" % core

    live = ensure_core_and_get_connection(site, ec, core)
    if core == None:
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

    assert type(status["status_event_limit_host"]) == int
    assert type(status["status_event_limit_rule"]) == int
    assert type(status["status_event_limit_overall"]) == int

# core == None means direct query to status socket
@pytest.mark.parametrize(("core"), [ None, "nagios", "cmc" ])
def test_rules_table_via_core(site, ec, core):
    print "Checking core: %s" % core

    live = ensure_core_and_get_connection(site, ec, core)
    if core == None:
        result = live.query_table_assoc("GET rules\n")
    else:
        result = live.query_table_assoc("GET eventconsolerules\n")

    assert type(result) == list
    #assert len(result) == 0
    # TODO: Add some rule before the test and then check the existing
    # keys and types in the result set
