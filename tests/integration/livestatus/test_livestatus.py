#!/usr/bin/env python
# encoding: utf-8
# pylint: disable=redefined-outer-name

import collections
import pytest

from testlib import web, create_linux_test_host  # pylint: disable=unused-import

DefaultConfig = collections.namedtuple("DefaultConfig", ["core"])


@pytest.fixture(scope="module", params=["nagios", "cmc"])
def default_cfg(request, site, web):
    config = DefaultConfig(core=request.param)
    site.set_config("CORE", config.core, with_restart=True)

    print "Applying default config (%s)" % config.core
    create_linux_test_host(request, web, site, "livestatus-test-host")
    create_linux_test_host(request, web, site, "livestatus-test-host.domain")
    web.discover_services("livestatus-test-host")
    web.activate_changes()
    return config


# Simply detects all tables by querying the columns table and then
# queries each of those tables without any columns and filters
def test_tables(default_cfg, site):
    existing_tables = set([])

    for row in site.live.query_table_assoc("GET columns\n"):
        existing_tables.add(row["table"])

    assert len(existing_tables) > 5

    for table in existing_tables:
        if default_cfg.core == "nagios" and table == "statehist":
            continue  # the statehist table in nagios can not be fetched without time filter

        result = site.live.query("GET %s\n" % table)
        assert isinstance(result, list)


def test_host_table(default_cfg, site):
    rows = site.live.query("GET hosts")
    assert isinstance(rows, list)
    assert len(rows) >= 2  # header + min 1 host


host_equal_queries = {
    "nagios": {
        "query": ("GET hosts\n"
                  "Columns: host_name\n"
                  "Filter: host_name = livestatus-test-host.domain\n"),
        "result": [{
            u'name': u'livestatus-test-host.domain',
        },],
    },
    "cmc": {
        "query": ("GET hosts\n"
                  "Columns: host_name\n"
                  "Filter: host_name = livestatus-test-host\n"),
        "result": [{
            u'name': u'livestatus-test-host',
        },],
    }
}


def test_host_table_host_equal_filter(default_cfg, site):
    query_and_result = host_equal_queries[default_cfg.core]
    rows = site.live.query_table_assoc(query_and_result["query"])
    assert rows == query_and_result["result"]


def test_service_table(default_cfg, site):
    rows = site.live.query("GET services\nFilter: host_name = livestatus-test-host\n"
                           "Columns: description\n")
    assert isinstance(rows, list)
    assert len(rows) >= 20  # header + min 1 service

    descriptions = [r[0] for r in rows]

    assert "Check_MK" in descriptions
    assert "Check_MK Discovery" in descriptions
    assert "CPU load" in descriptions
    assert "Memory" in descriptions
