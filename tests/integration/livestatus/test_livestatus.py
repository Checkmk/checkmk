#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json as _json
import time as _time
import uuid as _uuid
from typing import Dict, List

import pytest

from tests.testlib import create_linux_test_host
from tests.testlib.site import Site


@pytest.fixture(name="default_cfg", scope="module")
def default_cfg_fixture(request: pytest.FixtureRequest, site: Site, web) -> None:
    site.ensure_running()
    print("Applying default config")
    create_linux_test_host(request, site, "livestatus-test-host")
    create_linux_test_host(request, site, "livestatus-test-host.domain")
    web.discover_services("livestatus-test-host")  # Replace with RestAPI call, see CMK-9249
    site.activate_changes_and_wait_for_core_reload()


# Simply detects all tables by querying the columns table and then
# queries each of those tables without any columns and filters
@pytest.mark.usefixtures("default_cfg")
def test_tables(site: Site) -> None:
    columns_per_table: Dict[str, List[str]] = {}
    for row in site.live.query_table_assoc("GET columns\n"):
        columns_per_table.setdefault(row["table"], []).append(row["name"])
    assert len(columns_per_table) > 5

    for table, _columns in columns_per_table.items():
        print("Test table: %s" % table)

        if site.core_name() == "nagios" and table == "statehist":
            continue  # the statehist table in nagios can not be fetched without time filter

        result = site.live.query("GET %s\n" % table)
        assert isinstance(result, list)


@pytest.mark.usefixtures("default_cfg")
def test_host_table(site: Site) -> None:
    rows = site.live.query("GET hosts")
    assert isinstance(rows, list)
    assert len(rows) >= 2  # header + min 1 host


@pytest.mark.usefixtures("default_cfg")
def test_host_custom_variables(site: Site) -> None:
    rows = site.live.query(
        "GET hosts\nColumns: custom_variables tags\nFilter: name = livestatus-test-host\n"
    )
    assert isinstance(rows, list)
    assert len(rows) == 1
    custom_variables, tags = rows[0]
    assert custom_variables == {
        "ADDRESS_FAMILY": "4",
        "TAGS": "/wato/ auto-piggyback checkmk-agent cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:%s tcp"
        % site.id,
        "FILENAME": "/wato/hosts.mk",
        "ADDRESS_4": "127.0.0.1",
        "ADDRESS_6": "",
    }
    assert tags == {
        "address_family": "ip-v4-only",
        "agent": "cmk-agent",
        "criticality": "prod",
        "ip-v4": "ip-v4",
        "networking": "lan",
        "piggyback": "auto-piggyback",
        "site": str(site.id),
        "snmp_ds": "no-snmp",
        "tcp": "tcp",
        "checkmk-agent": "checkmk-agent",
    }


@pytest.mark.usefixtures("default_cfg")
def test_host_table_host_equal_filter(site: Site) -> None:
    queries = {
        "nagios": "GET hosts\n"
        "Columns: host_name\n"
        "Filter: host_name = livestatus-test-host.domain\n",
        "cmc": "GET hosts\n" "Columns: host_name\n" "Filter: host_name = livestatus-test-host\n",
    }
    results = {
        "nagios": [
            {
                "name": "livestatus-test-host.domain",
            },
        ],
        "cmc": [
            {
                "name": "livestatus-test-host",
            },
        ],
    }

    rows = site.live.query_table_assoc(queries[site.core_name()])
    assert rows == results[site.core_name()]


@pytest.mark.usefixtures("default_cfg")
def test_service_table(site: Site) -> None:
    rows = site.live.query(
        "GET services\nFilter: host_name = livestatus-test-host\n" "Columns: description\n"
    )
    assert isinstance(rows, list)
    assert len(rows) >= 20  # header + min 1 service

    descriptions = [r[0] for r in rows]

    assert "Check_MK" in descriptions
    assert "Check_MK Discovery" in descriptions
    assert "CPU load" in descriptions
    assert "Memory" in descriptions


@pytest.mark.usefixtures("default_cfg")
def test_usage_counters(site: Site) -> None:
    rows = site.live.query(
        "GET status\nColumns: helper_usage_cmk helper_usage_fetcher helper_usage_checker\n"
    )
    assert isinstance(rows, list)
    assert len(rows) == 1
    assert isinstance(rows[0], list)
    assert all(isinstance(v, (int, float)) for v in rows[0])


@pytest.fixture(name="configure_service_tags")
def configure_service_tags_fixture(site: Site, default_cfg):
    site.openapi.create_host(
        "modes-test-host",
        attributes={
            "ipaddress": "127.0.0.1",
        },
    )
    rule_id = site.openapi.create_rule(
        ruleset_name="service_tag_rules",
        value=[("criticality", "prod")],
        conditions={
            "host_name": {
                "match_on": ["livestatus-test-host"],
                "operator": "one_of",
            },
            "service_description": {
                "match_on": ["CPU load$"],
                "operator": "one_of",
            },
        },
    )
    site.activate_changes_and_wait_for_core_reload()
    yield
    site.openapi.delete_rule(rule_id)
    site.activate_changes_and_wait_for_core_reload()


@pytest.mark.usefixtures("configure_service_tags")
def test_service_custom_variables(site: Site) -> None:
    rows = site.live.query(
        "GET services\n"
        "Columns: custom_variables tags\n"
        "Filter: host_name = livestatus-test-host\n"
        "Filter: description = CPU load\n"
    )
    assert isinstance(rows, list)
    custom_variables, tags = rows[0]
    assert custom_variables == {}
    assert tags == {"criticality": "prod"}


@pytest.mark.usefixtures("default_cfg")
class TestCrashReport:
    @pytest.fixture
    def uuid(self):
        return str(_uuid.uuid4())

    @pytest.fixture
    def component(self):
        return "cmp"

    @pytest.fixture
    def crash_info(self, component, uuid):
        return {"component": component, "id": uuid}

    @pytest.fixture(autouse=True)
    def crash_report(self, site, component, uuid, crash_info):
        assert site.file_exists("var/check_mk/crashes")
        dir_path = "var/check_mk/crashes/%s/%s/" % (component, uuid)
        site.makedirs(dir_path)
        site.write_text_file(dir_path + "crash.info", _json.dumps(crash_info))
        yield
        site.delete_dir("var/check_mk/crashes/%s" % component)

    def test_list_crash_report(self, site, component, uuid):
        rows = site.live.query("GET crashreports")
        assert rows
        assert ["component", "id"] in rows
        assert [component, uuid] in rows

    def test_read_crash_report(self, site, component, uuid, crash_info):
        rows = site.live.query(
            "\n".join(
                (
                    "GET crashreports",
                    "Columns: file:f0:%s/%s/crash.info" % (component, uuid),
                    "Filter: id = %s" % uuid,
                )
            )
        )
        assert rows
        assert _json.loads(rows[0][0]) == crash_info

    def test_del_crash_report(self, site, component, uuid):
        before = site.live.query("GET crashreports")
        assert [component, uuid] in before

        site.live.command("[%i] DEL_CRASH_REPORT;%s" % (_time.mktime(_time.gmtime()), uuid))
        _time.sleep(0.1)  # Kindly let it complete.

        after = site.live.query("GET crashreports")
        assert after != before
        assert [component, uuid] not in after

    def test_other_crash_report(self, site, component, uuid):
        before = site.live.query("GET crashreports")
        assert [component, uuid] in before

        site.live.command(
            "[%i] DEL_CRASH_REPORT;%s"
            % (_time.mktime(_time.gmtime()), "01234567-0123-4567-89ab-0123456789ab")
        )

        after = site.live.query("GET crashreports")
        assert [component, uuid] in after
