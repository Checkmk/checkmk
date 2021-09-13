#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

bi_sample_config = {
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
                        "disabled": True,
                        "escalate_downtimes_as_warn": False,
                        "use_hard_states": False,
                    },
                    "groups": {"names": ["Hosts"], "paths": []},
                    "id": "default_aggregation",
                    "comment": "",
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
            "comment": "",
            "public": True,
            "rules": [
                {
                    "aggregation_function": {"count": 1, "restrict_state": 2, "type": "worst"},
                    "computation_options": {"disabled": False},
                    "id": "applications",
                    "comment": "",
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
                    "comment": "",
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
                    "comment": "",
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
                    "comment": "",
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
                    "comment": "",
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
                    "comment": "",
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
                    "comment": "",
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
                    "comment": "",
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
                    "comment": "",
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
                    "comment": "",
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
                    "comment": "",
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
