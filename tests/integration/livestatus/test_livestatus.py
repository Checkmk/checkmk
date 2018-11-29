#!/usr/bin/env python
# encoding: utf-8

import pytest
import itertools

from testlib import web


@pytest.fixture(scope="module")
def default_cfg(web):
    print "Applying default config"
    web.add_host(
        "livestatus-test-host", attributes={
            "ipaddress": "127.0.0.1",
        })
    web.add_host(
        "livestatus-test-host.domain", attributes={
            "ipaddress": "127.0.0.1",
        })

    web.discover_services("livestatus-test-host")

    web.activate_changes()
    yield None

    #
    # Cleanup code
    #
    print "Cleaning up default config"

    web.delete_host("livestatus-test-host")
    web.delete_host("livestatus-test-host.domain")


# Simply detects all tables by querying the columns table and then
# queries each of those tables without any columns and filters
@pytest.mark.parametrize(("core"), ["nagios", "cmc"])
def test_tables(default_cfg, site, core):
    site.set_config("CORE", core, with_restart=True)

    existing_tables = set([])

    for row in site.live.query_table_assoc("GET columns\n"):
        existing_tables.add(row["table"])

    assert len(existing_tables) > 5

    for table in existing_tables:
        if core == "nagios" and table == "statehist":
            continue  # the statehist table in nagios can not be fetched without time filter

        result = site.live.query("GET %s\n" % table)
        assert isinstance(result, list)


@pytest.mark.parametrize(("core"), ["nagios", "cmc"])
def test_host_table(default_cfg, site, core):
    site.set_config("CORE", core, with_restart=True)

    rows = site.live.query("GET hosts")
    assert isinstance(rows, list)
    assert len(rows) >= 2  # header + min 1 host


@pytest.mark.parametrize("core,query_and_result",
                         itertools.product([
                             "nagios",
                             "cmc",
                         ], [
                             {
                                 "query": ("GET hosts\n"
                                           "Columns: host_name\n"
                                           "Filter: host_name = livestatus-test-host.domain\n"),
                                 "result": [{
                                     u'name': u'livestatus-test-host.domain',
                                 },],
                             },
                             {
                                 "query": ("GET hosts\n"
                                           "Columns: host_name\n"
                                           "Filter: host_name = livestatus-test-host\n"),
                                 "result": [{
                                     u'name': u'livestatus-test-host',
                                 },],
                             },
                         ]))
def test_host_table_host_equal_filter(default_cfg, site, core, query_and_result):
    site.set_config("CORE", core, with_restart=True)

    rows = site.live.query_table_assoc(query_and_result["query"])
    assert rows == query_and_result["result"]


@pytest.mark.parametrize(("core"), ["nagios", "cmc"])
def test_service_table(default_cfg, site, core):
    site.set_config("CORE", core, with_restart=True)

    rows = site.live.query("GET services\nFilter: host_name = livestatus-test-host\n"
                           "Columns: description\n")
    assert isinstance(rows, list)
    assert len(rows) >= 20  # header + min 1 service

    descriptions = [r[0] for r in rows]

    assert "Check_MK" in descriptions
    assert "Check_MK Discovery" in descriptions
    assert "CPU load" in descriptions
    assert "Memory" in descriptions
