#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "graylog_nodes"

info = [
    [
        '{"a56db164-78a6-4dc8-bec9-418b9edf9067": {"inputstates": [{"message_input": {"node": "a56db164-78a6-4dc8-bec9-418b9edf9067", "name": "Beats", "title": "test", "created_at": "2019-09-30T10:40:05.226Z", "global": false, "content_pack": null, "attributes": {"tls_key_file": "", "tls_enable": false, "tcp_keepalive": false, "tls_key_password": "", "tls_cert_file": "", "no_beats_prefix": false, "recv_buffer_size": 1048576, "tls_client_auth": "disabled", "number_worker_threads": 8, "bind_address": "0.0.0.0", "tls_client_auth_cert_file": "", "port": 5044, "override_source": null}, "creator_user_id": "admin", "static_fields": {}, "type": "org.graylog.plugins.beats.Beats2Input", "id": "5d91db85dedfc2061e2371f0"}, "state": "RUNNING", "started_at": "2019-09-30T10:40:05.714Z", "detailed_message": null, "id": "5d91db85dedfc2061e2371f0"}, {"message_input": {"node": "a56db164-78a6-4dc8-bec9-418b9edf9067", "name": "Syslog TCP", "title": "syslog test", "created_at": "2019-09-30T07:11:19.932Z", "global": false, "content_pack": null, "attributes": {"tls_key_file": "", "tls_enable": false, "store_full_message": false, "tcp_keepalive": false, "tls_key_password": "", "tls_cert_file": "", "allow_override_date": true, "recv_buffer_size": 1048576, "port": 514, "max_message_size": 2097152, "number_worker_threads": 8, "bind_address": "0.0.0.0", "expand_structured_data": false, "tls_client_auth_cert_file": "", "tls_client_auth": "disabled", "use_null_delimiter": false, "force_rdns": false, "override_source": null}, "creator_user_id": "admin", "static_fields": {}, "type": "org.graylog2.inputs.syslog.tcp.SyslogTCPInput", "id": "5d91aa97dedfc2061e233e86"}, "state": "FAILED", "started_at": "2019-09-30T07:11:20.720Z", "detailed_message": "bind(..) failed: Keine Berechtigung.", "id": "5d91aa97dedfc2061e233e86"}, {"message_input": {"node": "a56db164-78a6-4dc8-bec9-418b9edf9067", "name": "Syslog UDP", "title": "test udp", "created_at": "2019-09-30T09:10:45.411Z", "global": false, "content_pack": null, "attributes": {"store_full_message": false, "expand_structured_data": false, "port": 514, "number_worker_threads": 8, "bind_address": "0.0.0.0", "recv_buffer_size": 262144, "allow_override_date": true, "force_rdns": false, "override_source": null}, "creator_user_id": "admin", "static_fields": {}, "type": "org.graylog2.inputs.syslog.udp.SyslogUDPInput", "id": "5d91c695dedfc2061e235bef"}, "state": "FAILED", "started_at": "2019-09-30T09:10:45.713Z", "detailed_message": "bind(..) failed: Keine Berechtigung.", "id": "5d91c695dedfc2061e235bef"}], "lb_status": "alive", "operating_system": "Linux 4.15.0-1056-oem", "version": "3.1.2+9e96b08", "facility": "graylog-server", "hostname": "my_server", "node_id": "a56db164-78a6-4dc8-bec9-418b9edf9067", "cluster_id": "d19bbcf9-9aaf-4812-a829-ba7cc4672ac9", "timezone": "Europe/Berlin", "codename": "Quantum Dog", "started_at": "2019-09-30T05:53:17.699Z", "lifecycle": "running", "is_processing": true}}'
    ]
]

discovery = {"": [("a56db164-78a6-4dc8-bec9-418b9edf9067", {})]}

checks = {
    "": [
        (
            "a56db164-78a6-4dc8-bec9-418b9edf9067",
            {
                "lc_uninitialized": 1,
                "lb_dead": 2,
                "ps_true": 0,
                "input_state": 1,
                "lc_running": 0,
                "lc_throttled": 2,
                "lc_halting": 1,
                "lb_alive": 0,
                "lc_override_lb_throttled": 1,
                "lb_throttled": 2,
                "lc_failed": 2,
                "lc_override_lb_alive": 0,
                "lc_paused": 1,
                "ps_false": 2,
                "lc_starting": 1,
                "lc_override_lb_dead": 1,
            },
            [
                (0, "Load balancer state: alive", []),
                (0, "Lifecycle is: running", []),
                (0, "Is processing: yes", []),
                (0, "Inputs: 3", [("num_input", 3, None, None, None, None)]),
                (
                    1,
                    "One or more inputs not in state running, see long output for more details",
                    [],
                ),
                (0, "\nName: Beats, Title: Test, Status: RUNNING", []),
                (1, "\nName: Syslog TCP, Title: Syslog Test, Status: FAILED", []),
                (1, "\nName: Syslog UDP, Title: Test Udp, Status: FAILED", []),
            ],
        )
    ]
}
