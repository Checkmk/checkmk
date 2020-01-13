#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-

from __future__ import print_function
import time

import pytest  # type: ignore[import]

from testlib import ec  # pylint: disable=unused-import

# pylint: disable=redefined-outer-name


def ensure_core_and_get_connection(site, ec, core):
    if core is None:
        return ec.status
    site.set_config("CORE", core, with_restart=True)
    return site.live


@pytest.mark.parametrize(("core"), ["nagios", "cmc"])
@pytest.mark.skip("needs to be analyzed later...")
def test_command_reload(site, ec, core):
    print("Checking core: %s" % core)
    live = ensure_core_and_get_connection(site, ec, core)

    old_t = live.query_value("GET eventconsolestatus\nColumns: status_config_load_time\n")
    print("Old config load time: %s" % old_t)
    assert old_t > time.time() - 86400

    time.sleep(1)  # needed to have at least one second after EC start
    live.command("[%d] EC_RELOAD" % (int(time.time())))
    time.sleep(1)  # needed to have at least one second after EC reload

    new_t = live.query_value("GET eventconsolestatus\nColumns: status_config_load_time\n")
    print("New config load time: %s" % old_t)
    assert new_t > old_t


# core is None means direct query to status socket
@pytest.mark.parametrize(("core"), [None, "nagios", "cmc"])
@pytest.mark.skip("needs to be analyzed later...")
def test_status_table_via_core(site, ec, core):
    print("Checking core: %s" % core)
    live = ensure_core_and_get_connection(site, ec, core)
    prefix = "" if core is None else "eventconsole"
    result = live.query_table_assoc("GET %sstatus\n" % prefix)
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
@pytest.mark.skip("needs to be analyzed later...")
def test_rules_table_via_core(site, ec, core):
    print("Checking core: %s" % core)
    live = ensure_core_and_get_connection(site, ec, core)
    prefix = "" if core is None else "eventconsole"
    result = live.query_table_assoc("GET %srules\n" % prefix)
    assert isinstance(result, list)
    #assert len(result) == 0
    # TODO: Add some rule before the test and then check the existing
    # keys and types in the result set
