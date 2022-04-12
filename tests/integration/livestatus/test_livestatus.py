#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import collections
import json as _json
import time as _time
import uuid as _uuid
from typing import Dict, List

import pytest  # type: ignore[import]

from testlib import web, create_linux_test_host  # noqa: F401 # pylint: disable=unused-import

DefaultConfig = collections.namedtuple("DefaultConfig", ["core"])


@pytest.fixture(name="default_cfg", scope="module", params=["nagios", "cmc"])
def default_cfg_fixture(request, site, web):  # noqa: F811 # pylint: disable=redefined-outer-name
    site.ensure_running()
    config = DefaultConfig(core=request.param)
    site.set_config("CORE", config.core, with_restart=True)

    print("Applying default config (%s)" % config.core)
    create_linux_test_host(request, web, site, "livestatus-test-host")
    create_linux_test_host(request, web, site, "livestatus-test-host.domain")
    web.discover_services("livestatus-test-host")
    web.activate_changes()
    return config


# Simply detects all tables by querying the columns table and then
# queries each of those tables without any columns and filters
def test_tables(default_cfg, site):
    columns_per_table: Dict[str, List[str]] = {}
    for row in site.live.query_table_assoc("GET columns\n"):
        columns_per_table.setdefault(row["table"], []).append(row["name"])
    assert len(columns_per_table) > 5

    for table, _columns in columns_per_table.items():
        print("Test table: %s" % table)

        if default_cfg.core == "nagios" and table == "statehist":
            continue  # the statehist table in nagios can not be fetched without time filter

        result = site.live.query("GET %s\n" % table)
        assert isinstance(result, list)


def test_host_table(default_cfg, site):
    rows = site.live.query("GET hosts")
    assert isinstance(rows, list)
    assert len(rows) >= 2  # header + min 1 host


def test_host_custom_variables(default_cfg, site):
    rows = site.live.query(
        "GET hosts\nColumns: custom_variables tags\nFilter: name = livestatus-test-host\n")
    assert isinstance(rows, list)
    assert len(rows) == 1
    custom_variables, tags = rows[0]
    assert custom_variables == {
        u'ADDRESS_FAMILY': u'4',
        u'TAGS': u'/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:%s tcp' %
                 site.id,
        u'FILENAME': u'/wato/hosts.mk',
        u'ADDRESSES_4': '',
        u'ADDRESSES_6': '',
        u'ADDRESS_4': u'127.0.0.1',
        u'ADDRESS_6': u'',
    }
    assert tags == {
        u'address_family': u'ip-v4-only',
        u'agent': u'cmk-agent',
        u'criticality': u'prod',
        u'ip-v4': u'ip-v4',
        u'networking': u'lan',
        u'piggyback': u'auto-piggyback',
        u'site': str(site.id),
        u'snmp_ds': u'no-snmp',
        u'tcp': u'tcp',
    }


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


def test_usage_counters(default_cfg, site):
    rows = site.live.query(
        "GET status\nColumns: helper_usage_cmk helper_usage_fetcher helper_usage_checker\n")
    assert isinstance(rows, list)
    assert len(rows) == 1
    assert isinstance(rows[0], list)
    assert all(isinstance(v, (int, float)) for v in rows[0])


@pytest.fixture(name="configure_service_tags")
def configure_service_tags_fixture(site, web, default_cfg):  # noqa: F811 # pylint: disable=redefined-outer-name
    web.set_ruleset(
        "service_tag_rules", {
            "ruleset": {
                "": [{
                    "value": [("criticality", "prod")],
                    "condition": {
                        "host_name": ["livestatus-test-host"],
                        "service_description": [{
                            "$regex": "CPU load$",
                        }],
                    },
                },],
            }
        })
    web.activate_changes()
    yield
    web.set_ruleset("service_tag_rules", {"ruleset": {"": [],}})
    web.activate_changes()


def test_service_custom_variables(configure_service_tags, default_cfg, site):
    rows = site.live.query("GET services\n"
                           "Columns: custom_variables tags\n"
                           "Filter: host_name = livestatus-test-host\n"
                           "Filter: description = CPU load\n")
    assert isinstance(rows, list)
    custom_variables, tags = rows[0]
    assert custom_variables == {}
    assert tags == {u'criticality': u'prod'}


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
        site.write_file(dir_path + "crash.info", _json.dumps(crash_info))
        yield
        site.delete_dir("var/check_mk/crashes/%s" % component)

    def test_list_crash_report(self, site, component, uuid):
        rows = site.live.query("GET crashreports")
        assert rows
        assert [u"component", u"id"] in rows
        assert [component, uuid] in rows

    def test_read_crash_report(self, site, component, uuid, crash_info):
        rows = site.live.query("\n".join(
            ("GET crashreports", "Columns: file:f0:%s/%s/crash.info" % (component, uuid),
             "Filter: id = %s" % uuid)))
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

        site.live.command("[%i] DEL_CRASH_REPORT;%s" %
                          (_time.mktime(_time.gmtime()), "01234567-0123-4567-89ab-0123456789ab"))

        after = site.live.query("GET crashreports")
        assert [component, uuid] in after
