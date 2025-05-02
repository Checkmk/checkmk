#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.graylog.agent_based import graylog_nodes


@dataclass
class GraylogNodeTestdata:
    node_id: str
    raw_data: str
    expected_check_results: list[Metric | Result]
    time_to_set: datetime


@pytest.fixture(
    scope="module",
    name="_test_data",
    params=[
        GraylogNodeTestdata(
            node_id="a56db164-78a6-4dc8-bec9-418b9edf9067",
            raw_data='{"a56db164-78a6-4dc8-bec9-418b9edf9067": {"inputstates": [{"message_input": {"node": "a56db164-78a6-4dc8-bec9-418b9edf9067", "name": "Beats", "title": "test", "created_at": "2019-09-30T10:40:05.226Z", "global": false, "content_pack": null, "attributes": {"tls_key_file": "", "tls_enable": false, "tcp_keepalive": false, "tls_key_password": "", "tls_cert_file": "", "no_beats_prefix": false, "recv_buffer_size": 1048576, "tls_client_auth": "disabled", "number_worker_threads": 8, "bind_address": "0.0.0.0", "tls_client_auth_cert_file": "", "port": 5044, "override_source": null}, "creator_user_id": "admin", "static_fields": {}, "type": "org.graylog.plugins.beats.Beats2Input", "id": "5d91db85dedfc2061e2371f0"}, "state": "RUNNING", "started_at": "2019-09-30T10:40:05.714Z", "detailed_message": null, "id": "5d91db85dedfc2061e2371f0"}, {"message_input": {"node": "a56db164-78a6-4dc8-bec9-418b9edf9067", "name": "Syslog TCP", "title": "syslog test", "created_at": "2019-09-30T07:11:19.932Z", "global": false, "content_pack": null, "attributes": {"tls_key_file": "", "tls_enable": false, "store_full_message": false, "tcp_keepalive": false, "tls_key_password": "", "tls_cert_file": "", "allow_override_date": true, "recv_buffer_size": 1048576, "port": 514, "max_message_size": 2097152, "number_worker_threads": 8, "bind_address": "0.0.0.0", "expand_structured_data": false, "tls_client_auth_cert_file": "", "tls_client_auth": "disabled", "use_null_delimiter": false, "force_rdns": false, "override_source": null}, "creator_user_id": "admin", "static_fields": {}, "type": "org.graylog2.inputs.syslog.tcp.SyslogTCPInput", "id": "5d91aa97dedfc2061e233e86"}, "state": "FAILED", "started_at": "2019-09-30T07:11:20.720Z", "detailed_message": "bind(..) failed: Keine Berechtigung.", "id": "5d91aa97dedfc2061e233e86"}, {"message_input": {"node": "a56db164-78a6-4dc8-bec9-418b9edf9067", "name": "Syslog UDP", "title": "test udp", "created_at": "2019-09-30T09:10:45.411Z", "global": false, "content_pack": null, "attributes": {"store_full_message": false, "expand_structured_data": false, "port": 514, "number_worker_threads": 8, "bind_address": "0.0.0.0", "recv_buffer_size": 262144, "allow_override_date": true, "force_rdns": false, "override_source": null}, "creator_user_id": "admin", "static_fields": {}, "type": "org.graylog2.inputs.syslog.udp.SyslogUDPInput", "id": "5d91c695dedfc2061e235bef"}, "state": "FAILED", "started_at": "2019-09-30T09:10:45.713Z", "detailed_message": "bind(..) failed: Keine Berechtigung.", "id": "5d91c695dedfc2061e235bef"}], "lb_status": "alive", "operating_system": "Linux 4.15.0-1056-oem", "version": "3.1.2+9e96b08", "facility": "graylog-server", "hostname": "my_server", "node_id": "a56db164-78a6-4dc8-bec9-418b9edf9067", "cluster_id": "d19bbcf9-9aaf-4812-a829-ba7cc4672ac9", "timezone": "Europe/Berlin", "codename": "Quantum Dog", "started_at": "2019-09-30T05:53:17.699Z", "lifecycle": "running", "is_processing": true}}',
            expected_check_results=[
                Result(state=State.OK, summary="Load balancer: alive"),
                Result(state=State.OK, summary="Lifecycle: running"),
                Result(state=State.OK, summary="Is processing: yes"),
                Result(state=State.OK, summary="Inputs: 3"),
                Metric("num_input", 3.0),
                Result(state=State.OK, notice="Input 1: Title: Test, Type: Beats, Status: RUNNING"),
                Result(
                    state=State.WARN,
                    summary="Input 2: Title: Syslog Test, Type: Syslog TCP, Status: FAILED",
                ),
                Result(
                    state=State.WARN,
                    summary="Input 3: Title: Test Udp, Type: Syslog UDP, Status: FAILED",
                ),
            ],
            time_to_set=datetime(2025, 2, 4, 16, 16, 50, tzinfo=ZoneInfo("UTC")),
        ),
        GraylogNodeTestdata(
            node_id="139f455e-0bb7-4db9-9b9d-bba11767a674",
            raw_data='{"139f455e-0bb7-4db9-9b9d-bba11767a674": {"facility": "graylog-server", "codename": "Noir", "node_id": "139f455e-0bb7-4db9-9b9d-bba11767a674", "cluster_id": "292914f7-9702-48fa-be55-8e0914366a7b", "version": "6.1.10+a308be3", "started_at": "2025-04-29T16:07:46.860Z", "hostname": "5f9efb6a40de", "lifecycle": "running", "lb_status": "alive", "timezone": "Europe/Berlin", "operating_system": "Linux 6.8.0-58-generic", "is_leader": true, "is_processing": true, "journal": {"enabled": true, "append_events_per_second": 23, "read_events_per_second": 0, "uncommitted_journal_entries": 23737897, "journal_size": 15689208510, "journal_size_limit": 21474836480, "number_of_segments": 150, "oldest_segment": "2025-05-02T07:13:32.657Z", "journal_config": {"directory": "file:///usr/share/graylog/data/journal/", "segment_size": 104857600, "segment_age": 3600000, "max_size": 21474836480, "max_age": 43200000, "flush_interval": 1000000, "flush_age": 60000}}, "inputstates": [{"id": "67b4c30a719a0d063158a7a1", "state": "RUNNING", "started_at": "2025-04-29T16:07:55.115Z", "detailed_message": null, "message_input": {"title": "Application Logs", "global": false, "name": "GELF TCP", "content_pack": null, "created_at": "2025-03-19T13:48:18.273Z", "type": "org.graylog2.inputs.gelf.tcp.GELFTCPInput", "creator_user_id": "niko.wenselowski", "attributes": {"recv_buffer_size": 1048576, "tcp_keepalive": false, "use_null_delimiter": true, "number_worker_threads": 4, "tls_client_auth_cert_file": "", "bind_address": "0.0.0.0", "tls_cert_file": "", "decompress_size_limit": 8388608, "port": 12201, "tls_key_file": "", "tls_enable": false, "tls_key_password": "", "max_message_size": 2097152, "tls_client_auth": "disabled", "override_source": null, "charset_name": "UTF-8"}, "static_fields": {}, "node": "139f455e-0bb7-4db9-9b9d-bba11767a674", "id": "67b4c30a719a0d063158a7a1"}}]}}',
            expected_check_results=[
                Result(state=State.OK, summary="Load balancer: alive"),
                Result(state=State.OK, summary="Lifecycle: running"),
                Result(state=State.OK, summary="Is processing: yes"),
                Result(state=State.OK, notice="Journal size: 14.6 GiB"),
                Metric("journal_size", 15689208510.0),
                Result(state=State.OK, notice="Journal size limit: 20.0 GiB"),
                Metric("journal_size_limit", 21474836480.0),
                Result(state=State.OK, summary="Journal usage: 73.06%"),
                Metric("journal_usage", 73.05857031606138, levels=(80.0, 90.0)),
                Result(state=State.OK, notice="Unprocessed messages in journal: 23737897"),
                Metric("journal_unprocessed_messages", 23737897.0),
                Result(state=State.OK, summary="Earliest entry in journal: 5 hours 58 minutes"),
                Metric("journal_oldest_segment", 21530.343),
                Result(state=State.OK, notice="Journal age limit: 12 hours 0 minutes"),
                Metric("journal_age_limit", 43200.0),
                Result(state=State.OK, summary="Inputs: 1"),
                Metric("num_input", 1.0),
                Result(
                    state=State.OK,
                    notice="Input 1: Title: Application Logs, Type: GELF TCP, Status: RUNNING",
                ),
            ],
            time_to_set=datetime(2025, 5, 2, 13, 12, 23, tzinfo=ZoneInfo("UTC")),
        ),
    ],
    ids=["legacy", "with-journal"],
)
def _test_data(request: pytest.FixtureRequest) -> GraylogNodeTestdata:
    return request.param


@pytest.fixture(scope="module", name="node_id")
def node_id(_test_data: GraylogNodeTestdata) -> str:
    return _test_data.node_id


@pytest.fixture(scope="module", name="section")
def _section(_test_data: GraylogNodeTestdata) -> graylog_nodes.Section:
    return graylog_nodes.parse_graylog_nodes([[_test_data.raw_data]])


@pytest.fixture(scope="module")
def expected_check_results(_test_data: GraylogNodeTestdata) -> list[Metric | Result]:
    return _test_data.expected_check_results


@pytest.fixture(scope="module")
def time_to_set(_test_data: GraylogNodeTestdata) -> datetime:
    return _test_data.time_to_set


def test_inventory_graylog_nodes(section: graylog_nodes.Section, node_id: str) -> None:
    returned_items = list(graylog_nodes.inventory_graylog_nodes(section))
    expected_items = [Service(item=node_id)]

    assert returned_items == expected_items


def test_parse_graylog_nodes(section: graylog_nodes.Section, node_id: str) -> None:
    assert isinstance(section, dict)

    assert node_id in section
    assert len(section[node_id]) == 1
    assert "inputstates" in section[node_id][0]


def test_check_graylog_nodes(
    section: graylog_nodes.Section,
    node_id: str,
    expected_check_results: list[Metric | Result],
    time_to_set: datetime,
) -> None:
    with time_machine.travel(time_to_set):
        check_results = list(
            graylog_nodes.check_graylog_nodes(node_id, graylog_nodes.DEFAULT_CHECK_PARAMS, section)
        )

        assert check_results == expected_check_results
