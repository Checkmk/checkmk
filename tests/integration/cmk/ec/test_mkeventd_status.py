#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from tests.testlib.site import Site


@pytest.mark.skip("needs to be analyzed later...")
def test_command_reload(site: Site, ec):
    live = site.live

    old_t = live.query_value("GET eventconsolestatus\nColumns: status_config_load_time\n")
    print("Old config load time: %s" % old_t)
    assert old_t > time.time() - 86400

    time.sleep(1)  # needed to have at least one second after EC start
    live.command("[%d] EC_RELOAD" % (int(time.time())))
    time.sleep(1)  # needed to have at least one second after EC reload

    new_t = live.query_value("GET eventconsolestatus\nColumns: status_config_load_time\n")
    print("New config load time: %s" % old_t)
    assert new_t > old_t


@pytest.mark.parametrize(("via_core"), [True, False])
@pytest.mark.skip("needs to be analyzed later...")
def test_status_table_via_core(site: Site, ec, via_core: bool) -> None:
    live = site.live if via_core else ec.status
    prefix = "eventconsole" if via_core else ""
    result = live.query_table_assoc("GET %sstatus\n" % prefix)
    assert len(result) == 1

    status = result[0]

    for column_name in [
        "status_config_load_time",
        "status_num_open_events",
        "status_messages",
        "status_message_rate",
        "status_average_message_rate",
        "status_connects",
        "status_connect_rate",
        "status_average_connect_rate",
        "status_rule_tries",
        "status_rule_trie_rate",
        "status_average_rule_trie_rate",
        "status_drops",
        "status_drop_rate",
        "status_average_drop_rate",
        "status_events",
        "status_event_rate",
        "status_average_event_rate",
        "status_rule_hits",
        "status_rule_hit_rate",
        "status_average_rule_hit_rate",
        "status_average_processing_time",
        "status_average_request_time",
        "status_average_sync_time",
        "status_replication_slavemode",
        "status_replication_last_sync",
        "status_replication_success",
        "status_event_limit_host",
        "status_event_limit_rule",
        "status_event_limit_overall",
    ]:
        assert column_name in status

    assert isinstance(status["status_event_limit_host"], int)
    assert isinstance(status["status_event_limit_rule"], int)
    assert isinstance(status["status_event_limit_overall"], int)


@pytest.mark.parametrize(("via_core"), [True, False])
@pytest.mark.skip("needs to be analyzed later...")
def test_rules_table_via_core(site: Site, ec, via_core: bool) -> None:
    live = site.live if via_core else ec.status
    prefix = "eventconsole" if via_core else ""
    result = live.query_table_assoc("GET %srules\n" % prefix)
    assert isinstance(result, list)
    # assert len(result) == 0
    # TODO: Add some rule before the test and then check the existing
    # keys and types in the result set
