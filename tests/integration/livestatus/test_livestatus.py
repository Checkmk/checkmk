#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json as _json
import logging
import time as _time
import uuid as _uuid
from collections.abc import Iterator, Mapping

import pytest

from tests.integration.linux_test_host import create_linux_test_host

from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

logger = logging.getLogger(__name__)


@pytest.fixture(name="default_cfg", scope="module")
def default_cfg_fixture(request: pytest.FixtureRequest, site: Site) -> None:
    site.ensure_running()
    print("Applying default config")
    create_linux_test_host(request, site, "livestatus-test-host")
    create_linux_test_host(request, site, "livestatus-test-host.domain")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion("livestatus-test-host")
    site.activate_changes_and_wait_for_core_reload()


# Simply detects all tables by querying the columns table and then
# queries each of those tables without any columns and filters
@pytest.mark.usefixtures("default_cfg")
def test_tables(site: Site) -> None:
    columns_per_table: dict[str, list[str]] = {}
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
    expected_variables = {
        "ADDRESS_FAMILY": "4",
        "TAGS": "/wato/ auto-piggyback checkmk-agent cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:%s tcp"
        % site.id,
        "FILENAME": "/wato/hosts.mk",
        "ADDRESSES_4": "",
        "ADDRESSES_6": "",
        "ADDRESS_4": "127.0.0.1",
        "ADDRESS_6": "",
    }
    if site.edition.is_managed_edition():
        expected_variables["CUSTOMER"] = "provider"
    assert custom_variables == expected_variables
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
        "cmc": "GET hosts\nColumns: host_name\nFilter: host_name = livestatus-test-host\n",
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
        "GET services\nFilter: host_name = livestatus-test-host\nColumns: description\n"
    )
    assert isinstance(rows, list)
    assert len(rows) >= 20  # header + min 1 service

    descriptions = [r[0] for r in rows]

    logger.info("Service table: %s", ",".join(descriptions))

    assert "Check_MK" in descriptions
    assert "Check_MK Discovery" in descriptions
    assert "CPU load" in descriptions
    assert "Memory" in descriptions


@pytest.mark.usefixtures("default_cfg")
def test_usage_counters(site: Site) -> None:
    rows = site.live.query(
        "GET status\nColumns: helper_usage_generic helper_usage_real_time helper_usage_fetcher helper_usage_checker\n"
    )
    assert isinstance(rows, list)
    assert len(rows) == 1
    assert isinstance(rows[0], list)
    assert all(isinstance(v, int | float) for v in rows[0])


@pytest.fixture(name="configure_service_tags")
def configure_service_tags_fixture(site: Site) -> Iterator[None]:
    site.openapi.hosts.create(
        (hostname := "modes-test-host"),
        attributes={
            "ipaddress": "127.0.0.1",
        },
    )
    rule_id = site.openapi.rules.create(
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
    try:
        yield
    finally:
        site.openapi.rules.delete(rule_id)
        site.openapi.hosts.delete(hostname)
        site.activate_changes_and_wait_for_core_reload()


@pytest.mark.usefixtures("default_cfg", "configure_service_tags")
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
        dir_path = f"var/check_mk/crashes/{component}/{uuid}/"
        site.makedirs(dir_path)
        site.write_file(dir_path + "crash.info", _json.dumps(crash_info))
        yield
        site.delete_dir("var/check_mk/crashes/%s" % component)

    def test_list_crash_report(self, site: Site, component: str, uuid: str) -> None:
        rows = site.live.query("GET crashreports")
        assert rows
        assert ["component", "id"] in rows
        assert [component, uuid] in rows

    def test_read_crash_report(
        self, site: Site, component: str, uuid: str, crash_info: Mapping[str, str]
    ) -> None:
        rows = site.live.query(
            "\n".join(
                (
                    "GET crashreports",
                    f"Columns: file:f0:{component}/{uuid}/crash.info",
                    "Filter: id = %s" % uuid,
                )
            )
        )
        assert rows
        assert _json.loads(rows[0][0]) == crash_info

    def test_del_crash_report(self, site: Site, component: str, uuid: str) -> None:
        assert [component, uuid] in site.live.query("GET crashreports")
        site.live.command("[%i] DEL_CRASH_REPORT;%s" % (_time.mktime(_time.gmtime()), uuid))
        wait_until(
            lambda: [component, uuid] not in site.live.query("GET crashreports"),
            timeout=1,
            interval=0.1,
        )

    def test_other_crash_report(self, site: Site, component: str, uuid: str) -> None:
        before = site.live.query("GET crashreports")
        assert [component, uuid] in before

        site.live.command(
            "[%i] DEL_CRASH_REPORT;%s"
            % (_time.mktime(_time.gmtime()), "01234567-0123-4567-89ab-0123456789ab")
        )

        after = site.live.query("GET crashreports")
        assert [component, uuid] in after
