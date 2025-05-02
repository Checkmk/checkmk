#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.graylog.agent_based import graylog_nodes

TEST_NODE_ID = "a56db164-78a6-4dc8-bec9-418b9edf9067"


@pytest.fixture(scope="module", name="section")
def _section() -> graylog_nodes.Section:
    return graylog_nodes.parse_graylog_nodes(
        [
            [
                '{"a56db164-78a6-4dc8-bec9-418b9edf9067": {"inputstates": [{"message_input": {"node": "a56db164-78a6-4dc8-bec9-418b9edf9067", "name": "Beats", "title": "test", "created_at": "2019-09-30T10:40:05.226Z", "global": false, "content_pack": null, "attributes": {"tls_key_file": "", "tls_enable": false, "tcp_keepalive": false, "tls_key_password": "", "tls_cert_file": "", "no_beats_prefix": false, "recv_buffer_size": 1048576, "tls_client_auth": "disabled", "number_worker_threads": 8, "bind_address": "0.0.0.0", "tls_client_auth_cert_file": "", "port": 5044, "override_source": null}, "creator_user_id": "admin", "static_fields": {}, "type": "org.graylog.plugins.beats.Beats2Input", "id": "5d91db85dedfc2061e2371f0"}, "state": "RUNNING", "started_at": "2019-09-30T10:40:05.714Z", "detailed_message": null, "id": "5d91db85dedfc2061e2371f0"}, {"message_input": {"node": "a56db164-78a6-4dc8-bec9-418b9edf9067", "name": "Syslog TCP", "title": "syslog test", "created_at": "2019-09-30T07:11:19.932Z", "global": false, "content_pack": null, "attributes": {"tls_key_file": "", "tls_enable": false, "store_full_message": false, "tcp_keepalive": false, "tls_key_password": "", "tls_cert_file": "", "allow_override_date": true, "recv_buffer_size": 1048576, "port": 514, "max_message_size": 2097152, "number_worker_threads": 8, "bind_address": "0.0.0.0", "expand_structured_data": false, "tls_client_auth_cert_file": "", "tls_client_auth": "disabled", "use_null_delimiter": false, "force_rdns": false, "override_source": null}, "creator_user_id": "admin", "static_fields": {}, "type": "org.graylog2.inputs.syslog.tcp.SyslogTCPInput", "id": "5d91aa97dedfc2061e233e86"}, "state": "FAILED", "started_at": "2019-09-30T07:11:20.720Z", "detailed_message": "bind(..) failed: Keine Berechtigung.", "id": "5d91aa97dedfc2061e233e86"}, {"message_input": {"node": "a56db164-78a6-4dc8-bec9-418b9edf9067", "name": "Syslog UDP", "title": "test udp", "created_at": "2019-09-30T09:10:45.411Z", "global": false, "content_pack": null, "attributes": {"store_full_message": false, "expand_structured_data": false, "port": 514, "number_worker_threads": 8, "bind_address": "0.0.0.0", "recv_buffer_size": 262144, "allow_override_date": true, "force_rdns": false, "override_source": null}, "creator_user_id": "admin", "static_fields": {}, "type": "org.graylog2.inputs.syslog.udp.SyslogUDPInput", "id": "5d91c695dedfc2061e235bef"}, "state": "FAILED", "started_at": "2019-09-30T09:10:45.713Z", "detailed_message": "bind(..) failed: Keine Berechtigung.", "id": "5d91c695dedfc2061e235bef"}], "lb_status": "alive", "operating_system": "Linux 4.15.0-1056-oem", "version": "3.1.2+9e96b08", "facility": "graylog-server", "hostname": "my_server", "node_id": "a56db164-78a6-4dc8-bec9-418b9edf9067", "cluster_id": "d19bbcf9-9aaf-4812-a829-ba7cc4672ac9", "timezone": "Europe/Berlin", "codename": "Quantum Dog", "started_at": "2019-09-30T05:53:17.699Z", "lifecycle": "running", "is_processing": true}}'
            ]
        ]
    )


def test_inventory_graylog_nodes(section: graylog_nodes.Section) -> None:
    returned_items = list(graylog_nodes.inventory_graylog_nodes(section))
    expected_items = [Service(item=TEST_NODE_ID)]

    assert returned_items == expected_items


def test_parse_graylog_nodes(section: graylog_nodes.Section) -> None:
    assert isinstance(section, dict)

    assert TEST_NODE_ID in section
    assert len(section[TEST_NODE_ID]) == 1
    assert "inputstates" in section[TEST_NODE_ID][0]


def test_check_graylog_nodes(section: graylog_nodes.Section) -> None:
    check_results = list(
        graylog_nodes.check_graylog_nodes(TEST_NODE_ID, graylog_nodes.DEFAULT_CHECK_PARAMS, section)
    )

    expected_results = [
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
            state=State.WARN, summary="Input 3: Title: Test Udp, Type: Syslog UDP, Status: FAILED"
        ),
    ]

    assert check_results == expected_results
