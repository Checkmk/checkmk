#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

bi_structure_states = {
    "heute": (
        "heute",
        {
            ("piggyback", "auto-piggyback"),
            ("agent", "cmk-agent"),
            ("site", "heute"),
            ("ip-v4", "ip-v4"),
            ("address_family", "ip-v4-only"),
            ("networking", "lan"),
            ("snmp_ds", "no-snmp"),
            ("criticality", "prod"),
            ("tcp", "tcp"),
        },
        {"cmk/check_mk_server": "yes"},
        "",
        {
            "Check_MK Discovery": ({}, {"cmk_is_discoverylabel": "yes"}),
            "Check_MK HW/SW Inventory": ({"custom": "tag"}, {}),
            "Filesystem /opt/omd/sites/heute/tmp": ({}, {}),
            "Interface 2": ({}, {}),
            "Interface 3": ({}, {}),
            "Interface 4": ({}, {}),
            "OMD heute Event Console": ({}, {}),
            "OMD heute Notification Spooler": ({}, {}),
            "OMD heute apache": ({}, {}),
            "OMD heute performance": ({}, {}),
            "Temperature Zone 9": ({}, {}),
            "Uptime": ({}, {}),
        },
        (),
        (),
        "heute_alias",
        "heute",
    ),
    "heute_clone": (
        "heute",
        {
            ("piggyback", "auto-piggyback"),
            ("agent", "cmk-agent"),
            ("site", "heute"),
            ("ip-v4", "ip-v4"),
            ("address_family", "ip-v4-only"),
            ("networking", "lan"),
            ("snmp_ds", "no-snmp"),
            ("criticality", "prod"),
            ("tcp", "tcp"),
            ("clone-tag", "clone-tag"),
        },
        {"cmk/check_mk_server": "no"},
        "subfolder/",
        {
            "Check_MK Discovery": ({}, {"cmk_is_discoverylabel": "yes"}),
            "Check_MK HW/SW Inventory": ({"custom": "tag"}, {}),
            "Filesystem /opt/omd/sites/heute/tmp": ({}, {}),
            "Interface 2": ({}, {}),
            "Interface 3": ({}, {}),
            "Interface 4": ({}, {}),
            "Interface 5": ({}, {}),
            "OMD heute Event Console": ({}, {}),
            "OMD heute Notification Spooler": ({}, {}),
            "OMD heute apache": ({}, {}),
            "OMD heute performance": ({}, {}),
            "Temperature Zone 9": ({}, {}),
            "Uptime": ({}, {}),
        },
        (),
        (),
        "heute_clone_alias",
        "heute_clone",
    ),
}

bi_status_rows = [
    [
        "heute",
        "heute",
        0,
        1,
        0,
        "Packet received via smart PING",
        0,
        1,
        0,
        [
            [
                "Check_MK Discovery",
                1,
                1,
                "WARN - 38 unmonitored services (timesyncd:1, tcp_conn_stats:1, "
                "systemd_units_services_summary:1, omd_status:1, omd_apache:5, mounts:2, "
                "mknotifyd:2, mkeventd_status:1, mem_linux:1, lnx_thermal:13, lnx_if:1, "
                "livestatus_status:1, kernel_util:1, kernel_performance:1, diskstat:1, "
                "df:3, cpu_threads:1, cpu_loads:1)(!), no vanished services found, no new "
                "host labels",
                1,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Check_MK",
                0,
                1,
                "OK - [agent] Version: 2020.07.04, OS: linux, execution time 1.0 sec ",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Check_MK HW/SW Inventory",
                0,
                1,
                "OK - Found 187 inventory entries, Found 157 status entries",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "OMD heute apache",
                0,
                1,
                "OK - 2.01 Requests/s, 0.03 Seconds serving/s, 203.10 kB Sent/s",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "OMD heute Event Console",
                0,
                1,
                "OK - Current events: 0, Virtual memory: 191.69 MB, Overall event limit "
                "inactive, No hosts event limit active, No rules event limit active, "
                "Received messages: 0.00/s, Rule hits: 0.00/s, Rule tries: 0.00/s, Message "
                "drops: 0.00/s, Created events: 0.00/s, Client connects: 0.07/s, Rule hit "
                "ratio: -, Processing time per message: -, Time per client request: 0.16 "
                "ms",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            ["Temperature Zone 9", 0, 1, "OK - 42.0 °C", 0, 1, 1, 0, 0, 1],
            [
                "Interface 4",
                1,
                1,
                "WARN - [enx000e2e413816], Operational state: up, MAC: 00:0E:2E:41:38:16, "
                "100 MBit/s (wrong speed, expected: 0 Bit/s)(!), In: 607 B/s (0.0%), Out: "
                "415 B/s (0.0%)",
                1,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "OMD heute Notification Spooler",
                0,
                1,
                "OK - Version: 2020.09.03, Spooler running",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Interface 3",
                0,
                1,
                "OK - [docker0], Operational state: up, MAC: 02:42:BE:0A:7B:5A, assuming "
                "10 MBit/s, In: 0.00 B/s (0.0%), Out: 0.00 B/s (0.0%)",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Interface 2",
                1,
                1,
                "WARN - [tun0], Operational state: up, 10 MBit/s (wrong speed, expected: 0 "
                "Bit/s)(!), In: 280 B/s (0.0%), Out: 87.2 B/s (0.0%)",
                1,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "OMD heute performance",
                0,
                1,
                "OK - HostChecks: 14.4/s, ServiceChecks: 0.4/s, ProcessCreations: 0.0/s, "
                "LivestatusConnects: 0.2/s, LivestatusRequests: 0.9/s, LogMessages: 0.1/s, "
                "Average check latency: 1.571s, Average Checkmk latency: 0.359s, Check "
                "helper usage: 0.07%, Checkmk helper usage: 0.77%, Livestatus usage: 0%, "
                "Livestatus overflow rate: 0.0/s, Monitored Hosts: 2.00, Services: 27.00, "
                "Core version: Checkmk 2020.09.03, Livestatus version: 2020.09.03, Site "
                "certificate validity (until 3019-01-05 11:38:09): 364633.93",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Uptime",
                0,
                1,
                "OK - Up since Fri Sep  4 09:45:36 2020, uptime: 4:37:11",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Filesystem /opt/omd/sites/heute/tmp",
                0,
                1,
                "OK - 0.04% used (6.52 MB of 15.49 GB), trend: +317.48 kB / 24 hours",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
        ],
    ],
    [
        "heute",
        "heute_clone",
        0,
        1,
        0,
        "Packet received via smart PING",
        0,
        1,
        0,
        [
            [
                "Check_MK Discovery",
                1,
                1,
                "WARN - 37 unmonitored services (timesyncd:1, tcp_conn_stats:1, "
                "systemd_units_services_summary:1, omd_status:1, omd_apache:5, mounts:2, "
                "mknotifyd:2, mkeventd_status:1, mem_linux:1, lnx_thermal:13, "
                "livestatus_status:1, kernel_util:1, kernel_performance:1, diskstat:1, "
                "df:3, cpu_threads:1, cpu_loads:1)(!), no vanished services found, no new "
                "host labels",
                1,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Filesystem /opt/omd/sites/heute/tmp",
                0,
                1,
                "OK - 0.04% used (6.52 MB of 15.49 GB), trend: 0.00 B / 24 hours",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Interface 2",
                1,
                1,
                "WARN - [tun0], Operational state: up, 10 MBit/s (wrong speed, expected: 0 "
                "Bit/s)(!), In: 279 B/s (0.0%), Out: 86.2 B/s (0.0%)",
                1,
                1,
                1,
                0,
                0,
                1,
            ],
            ["OMD heute apache", 0, 1, "OK - No activity since last check", 0, 1, 1, 0, 0, 1],
            [
                "Interface 3",
                0,
                1,
                "OK - [docker0], Operational state: up, MAC: 02:42:BE:0A:7B:5A, assuming "
                "10 MBit/s, In: 0.00 B/s (0.0%), Out: 0.00 B/s (0.0%)",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Interface 4",
                1,
                1,
                "WARN - [enx000e2e413816], Operational state: up, MAC: 00:0E:2E:41:38:16, "
                "100 MBit/s (wrong speed, expected: 0 Bit/s)(!), In: 603 B/s (0.0%), Out: "
                "410 B/s (0.0%)",
                1,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "OMD heute Notification Spooler",
                0,
                1,
                "OK - Version: 2020.09.03, Spooler running",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            ["OMD heute performance", 0, 0, "", 0, 1, 1, 0, 0, 1],
            [
                "Interface 5",
                0,
                1,
                "OK - [wlp59s0], Operational state: up, MAC: 3C:58:C2:FF:34:8A, speed "
                "unknown, In: 0.00 B/s, Out: 0.00 B/s",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "OMD heute Event Console",
                0,
                1,
                "OK - Current events: 0, Virtual memory: 191.69 MB, Overall event limit "
                "inactive, No hosts event limit active, No rules event limit active, "
                "Received messages: 0.00/s, Rule hits: 0.00/s, Rule tries: 0.00/s, Message "
                "drops: 0.00/s, Created events: 0.00/s, Client connects: 0.07/s, Rule hit "
                "ratio: -, Processing time per message: -, Time per client request: 0.16 "
                "ms",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            ["Temperature Zone 9", 0, 1, "OK - 42.0 °C", 0, 1, 1, 0, 0, 1],
            [
                "Uptime",
                0,
                1,
                "OK - Up since Fri Sep  4 09:45:36 2020, uptime: 4:37:12",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Check_MK HW/SW Inventory",
                0,
                1,
                "OK - Found 187 inventory entries, software changes, Found 157 status entries",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Check_MK",
                0,
                1,
                "OK - [agent] Version: 2020.07.04, OS: linux, execution time 1.2 sec ",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
        ],
    ],
]

bi_acknowledgment_status_rows = [
    [
        "heute",
        "heute",
        0,
        1,
        0,
        "Packet received via smart PING",
        0,
        1,
        0,
        [
            [
                "Check_MK Discovery",
                1,
                1,
                "WARN - 38 unmonitored services (timesyncd:1, tcp_conn_stats:1, "
                "systemd_units_services_summary:1, omd_status:1, omd_apache:5, mounts:2, "
                "mknotifyd:2, mkeventd_status:1, mem_linux:1, lnx_thermal:13, lnx_if:1, "
                "livestatus_status:1, kernel_util:1, kernel_performance:1, diskstat:1, "
                "df:3, cpu_threads:1, cpu_loads:1)(!), no vanished services found, no new "
                "host labels",
                1,
                1,
                1,
                0,
                1,
                1,
            ],
            [
                "Check_MK",
                0,
                1,
                "OK - [agent] Version: 2020.07.04, OS: linux, execution time 1.0 sec ",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Check_MK HW/SW Inventory",
                0,
                1,
                "OK - Found 187 inventory entries, Found 157 status entries",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "OMD heute apache",
                0,
                1,
                "OK - 2.01 Requests/s, 0.03 Seconds serving/s, 203.10 kB Sent/s",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
        ],
    ]
]

bi_downtime_status_rows = [
    [
        "heute",
        "heute",
        0,
        1,
        0,
        "Packet received via smart PING",
        0,
        1,
        0,
        [
            [
                "Check_MK Discovery",
                1,
                1,
                "WARN - 38 unmonitored services (timesyncd:1, tcp_conn_stats:1, "
                "systemd_units_services_summary:1, omd_status:1, omd_apache:5, mounts:2, "
                "mknotifyd:2, mkeventd_status:1, mem_linux:1, lnx_thermal:13, lnx_if:1, "
                "livestatus_status:1, kernel_util:1, kernel_performance:1, diskstat:1, "
                "df:3, cpu_threads:1, cpu_loads:1)(!), no vanished services found, no new "
                "host labels",
                1,
                1,
                1,
                1,
                0,
                1,
            ],
            [
                "Check_MK",
                0,
                1,
                "OK - [agent] Version: 2020.07.04, OS: linux, execution time 1.0 sec ",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Check_MK HW/SW Inventory",
                0,
                1,
                "OK - Found 187 inventory entries, Found 157 status entries",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "OMD heute apache",
                0,
                1,
                "OK - 2.01 Requests/s, 0.03 Seconds serving/s, 203.10 kB Sent/s",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
        ],
    ]
]

bi_service_period_status_rows = [
    [
        "heute",
        "heute",
        0,
        1,
        0,
        "Packet received via smart PING",
        0,
        1,
        0,
        [
            [
                "Check_MK Discovery",
                1,
                1,
                "WARN - 38 unmonitored services (timesyncd:1, tcp_conn_stats:1, "
                "systemd_units_services_summary:1, omd_status:1, omd_apache:5, mounts:2, "
                "mknotifyd:2, mkeventd_status:1, mem_linux:1, lnx_thermal:13, lnx_if:1, "
                "livestatus_status:1, kernel_util:1, kernel_performance:1, diskstat:1, "
                "df:3, cpu_threads:1, cpu_loads:1)(!), no vanished services found, no new "
                "host labels",
                1,
                1,
                1,
                0,
                0,
                0,
            ],
            [
                "Check_MK",
                0,
                1,
                "OK - [agent] Version: 2020.07.04, OS: linux, execution time 1.0 sec ",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "Check_MK HW/SW Inventory",
                0,
                1,
                "OK - Found 187 inventory entries, Found 157 status entries",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
            [
                "OMD heute apache",
                0,
                1,
                "OK - 2.01 Requests/s, 0.03 Seconds serving/s, 203.10 kB Sent/s",
                0,
                1,
                1,
                0,
                0,
                1,
            ],
        ],
    ]
]

bi_packs_config = {
    "packs": [
        {
            "aggregations": [
                {
                    "aggregation_visualization": {
                        "ignore_rule_styles": False,
                        "layout_id": "builtin_default",
                        "line_style": "round",
                    },
                    "computation_options": {
                        "disabled": False,
                        "escalate_downtimes_as_warn": False,
                        "use_hard_states": False,
                    },
                    "groups": {"names": ["Hosts"], "paths": []},
                    "id": "default_aggregation",
                    "node": {
                        "action": {
                            "params": {"arguments": ["$HOSTNAME$"]},
                            "rule_id": "host",
                            "type": "call_a_rule",
                        },
                        "search": {
                            "conditions": {
                                "host_choice": {"type": "all_hosts"},
                                "host_folder": "",
                                "host_labels": {},
                                "host_tags": {"tcp": "tcp"},
                            },
                            "refer_to": "host",
                            "type": "host_search",
                        },
                    },
                }
            ],
            "contact_groups": [],
            "id": "default",
            "public": True,
            "rules": [
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "applications",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "ASM|ORACLE|proc",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        }
                    ],
                    "params": {"arguments": ["HOSTNAME"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "Applications",
                    },
                },
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "checkmk",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "Check_MK|Uptime",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        }
                    ],
                    "params": {"arguments": ["HOSTNAME"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "Check_MK",
                    },
                },
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "filesystem",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "fs_$FS$$",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "Filesystem$FS$$",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "Mount options " "of $FS$$",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        },
                    ],
                    "params": {"arguments": ["HOSTNAME", "FS"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "$FS$",
                    },
                },
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "filesystems",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "Disk|MD",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$"]},
                                "rule_id": "multipathing",
                                "type": "call_a_rule",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$", "$1$"]},
                                "rule_id": "filesystem",
                                "type": "call_a_rule",
                            },
                            "search": {
                                "conditions": {
                                    "host_choice": {
                                        "pattern": "$HOSTNAME$",
                                        "type": "host_name_regex",
                                    },
                                    "host_folder": "",
                                    "host_labels": {},
                                    "host_tags": {},
                                    "service_labels": {},
                                    "service_regex": "fs_(.*)",
                                },
                                "type": "service_search",
                            },
                        },
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$", "$1$"]},
                                "rule_id": "filesystem",
                                "type": "call_a_rule",
                            },
                            "search": {
                                "conditions": {
                                    "host_choice": {
                                        "pattern": "$HOSTNAME$",
                                        "type": "host_name_regex",
                                    },
                                    "host_folder": "",
                                    "host_labels": {},
                                    "host_tags": {},
                                    "service_labels": {},
                                    "service_regex": "Filesystem(.*)",
                                },
                                "type": "service_search",
                            },
                        },
                    ],
                    "params": {"arguments": ["HOSTNAME"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "Disk & Filesystems",
                    },
                },
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "general",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {"host_regex": "$HOSTNAME$", "type": "state_of_host"},
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "Uptime",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$"]},
                                "rule_id": "checkmk",
                                "type": "call_a_rule",
                            },
                            "search": {"type": "empty"},
                        },
                    ],
                    "params": {"arguments": ["HOSTNAME"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "General State",
                    },
                },
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "hardware",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "IPMI|RAID",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        }
                    ],
                    "params": {"arguments": ["HOSTNAME"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "Hardware",
                    },
                },
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "host",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$"]},
                                "rule_id": "general",
                                "type": "call_a_rule",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$"]},
                                "rule_id": "performance",
                                "type": "call_a_rule",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$"]},
                                "rule_id": "filesystems",
                                "type": "call_a_rule",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$"]},
                                "rule_id": "networking",
                                "type": "call_a_rule",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$"]},
                                "rule_id": "applications",
                                "type": "call_a_rule",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$"]},
                                "rule_id": "logfiles",
                                "type": "call_a_rule",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$"]},
                                "rule_id": "hardware",
                                "type": "call_a_rule",
                            },
                            "search": {"type": "empty"},
                        },
                        {
                            "action": {
                                "params": {"arguments": ["$HOSTNAME$"]},
                                "rule_id": "other",
                                "type": "call_a_rule",
                            },
                            "search": {"type": "empty"},
                        },
                    ],
                    "params": {"arguments": ["HOSTNAME"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "Host $HOSTNAME$",
                    },
                },
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "logfiles",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "LOG",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        }
                    ],
                    "params": {"arguments": ["HOSTNAME"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "Logfiles",
                    },
                },
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "multipathing",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "Multipath",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        }
                    ],
                    "params": {"arguments": ["HOSTNAME"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "Multipathing",
                    },
                },
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "networking",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "NFS|Interface|TCP",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        }
                    ],
                    "params": {"arguments": ["HOSTNAME"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "Networking",
                    },
                },
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "other",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "type": "state_of_remaining_services",
                            },
                            "search": {"type": "empty"},
                        }
                    ],
                    "params": {"arguments": ["HOSTNAME"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "Other",
                    },
                },
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "performance",
                    "node_visualization": {"style_config": {}, "type": "none"},
                    "nodes": [
                        {
                            "action": {
                                "host_regex": "$HOSTNAME$",
                                "service_regex": "CPU|Memory|Vmalloc|Kernel|Number " "of threads",
                                "type": "state_of_service",
                            },
                            "search": {"type": "empty"},
                        }
                    ],
                    "params": {"arguments": ["HOSTNAME"]},
                    "properties": {
                        "comment": "",
                        "docu_url": "",
                        "icon": "",
                        "state_messages": {},
                        "title": "Performance",
                    },
                },
            ],
            "title": "Default Pack",
        }
    ]
}

LEGACY_BI_PACKS_CONFIG_STRING = """
bi_packs['default'] = {
 'aggregations': [],
 'contact_groups': [],
 'host_aggregations': [({'disabled': False,
                         'downtime_aggr_warn': False,
                         'hard_states': False,
                         'ID': 'default_aggregation',
                         'node_visualization': {}},
                        [u'Hosts'],
                        FOREACH_HOST,
                        ['tcp'],
                        ALL_HOSTS,
                        'host',
                        ['$HOSTNAME$'])],
 'id': 'default',
 'public': True,
 'rules': {'applications': {'aggregation': 'worst',
                            'nodes': [('$HOSTNAME$',
                                       'ASM|ORACLE|proc')],
                            'params': ['HOSTNAME'],
                            'title': 'Applications'},
           'checkmk': {'aggregation': 'worst',
                       'nodes': [('$HOSTNAME$',
                                  'Check_MK|Uptime')],
                       'params': ['HOSTNAME'],
                       'title': 'Check_MK'},
           'filesystem': {'aggregation': 'worst',
                          'nodes': [('$HOSTNAME$',
                                     'fs_$FS$$'),
                                    ('$HOSTNAME$',
                                     'Filesystem$FS$$'),
                                    ('$HOSTNAME$',
                                     'Mount options of $FS$$')],
                          'params': ['HOSTNAME',
                                     'FS'],
                          'title': '$FS$'},
           'filesystems': {'aggregation': 'worst',
                           'nodes': [('$HOSTNAME$',
                                      'Disk|MD'),
                                     ('multipathing',
                                      ['$HOSTNAME$']),
                                     (FOREACH_SERVICE,
                                      [],
                                      '$HOSTNAME$',
                                      'fs_(.*)',
                                      'filesystem',
                                      ['$HOSTNAME$',
                                       '$1$']),
                                     (FOREACH_SERVICE,
                                      [],
                                      '$HOSTNAME$',
                                      'Filesystem(.*)',
                                      'filesystem',
                                      ['$HOSTNAME$',
                                       '$1$'])],
                           'params': ['HOSTNAME'],
                           'title': 'Disk & Filesystems'},
           'general': {'aggregation': 'worst',
                       'nodes': [('$HOSTNAME$',
                                  HOST_STATE),
                                 ('$HOSTNAME$',
                                  'Uptime'),
                                 ('checkmk',
                                  ['$HOSTNAME$'])],
                       'params': ['HOSTNAME'],
                       'title': 'General State'},
           'hardware': {'aggregation': 'worst',
                        'nodes': [('$HOSTNAME$',
                                   'IPMI|RAID')],
                        'params': ['HOSTNAME'],
                        'title': 'Hardware'},
           'host': {'aggregation': 'worst',
                    'nodes': [('general',
                               ['$HOSTNAME$']),
                              ('performance',
                               ['$HOSTNAME$']),
                              ('filesystems',
                               ['$HOSTNAME$']),
                              ('networking',
                               ['$HOSTNAME$']),
                              ('applications',
                               ['$HOSTNAME$']),
                              ('logfiles',
                               ['$HOSTNAME$']),
                              ('hardware',
                               ['$HOSTNAME$']),
                              ('other',
                               ['$HOSTNAME$'])],
                    'params': ['HOSTNAME'],
                    'title': 'Host $HOSTNAME$'},
           'logfiles': {'aggregation': 'worst',
                        'nodes': [('$HOSTNAME$',
                                   'LOG')],
                        'params': ['HOSTNAME'],
                        'title': 'Logfiles'},
           'multipathing': {'aggregation': 'worst',
                            'nodes': [('$HOSTNAME$',
                                       'Multipath')],
                            'params': ['HOSTNAME'],
                            'title': 'Multipathing'},
           'networking': {'aggregation': 'worst',
                          'nodes': [('$HOSTNAME$',
                                     'NFS|Interface|TCP')],
                          'params': ['HOSTNAME'],
                          'title': 'Networking'},
           'other': {'aggregation': 'worst',
                     'nodes': [('$HOSTNAME$',
                                REMAINING)],
                     'params': ['HOSTNAME'],
                     'title': 'Other'},
           'performance': {'aggregation': 'worst',
                           'nodes': [('$HOSTNAME$',
                                      'CPU|Memory|Vmalloc|Kernel|Number of threads')],
                           'params': ['HOSTNAME'],
                           'title': 'Performance'}},
 'title': u'Default Pack'
}
"""
