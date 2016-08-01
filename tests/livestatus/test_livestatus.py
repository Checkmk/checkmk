#!/usr/bin/env python
# encoding: utf-8

import pytest
from testlib import web

@pytest.fixture(scope="module")
def default_cfg(web):
    try:
        web.add_host("livestatus-test-host", attributes={
            "ipaddress": "127.0.0.1",
        })

        web.discover_services("livestatus-test-host")

        web.activate_changes()
    finally:
        web.delete_host("livestatus-test-host")


# Simply detects all tables by querying the columns table and then
# queries each of those tables without any columns and filters
def test_tables(default_cfg, site):
    existing_tables = set([])

    for row in site.live.query_table_assoc("GET columns\n"):
        existing_tables.add(row["table"])

    assert len(existing_tables) > 5

    for table in existing_tables:
        result = site.live.query("GET %s\n" % table)
        assert type(result) == list


def test_host_table(default_cfg, site):
    rows = site.live.query("GET hosts")
    assert type(rows) == list
    assert len(rows) >= 2 # header + min 1 host


def test_service_table(default_cfg, site):
    rows = site.live.query("GET services\nFilter: host_name = livestatus-test-host\n"
                           "Columns: description\n")
    assert type(rows) == list
    assert len(rows) >= 20 # header + min 1 service

    descriptions = [ r[0] for r in rows ]

    assert "Check_MK" in descriptions
    assert "Check_MK Discovery" in descriptions
    assert "CPU load" in descriptions
    assert "Memory" in descriptions
