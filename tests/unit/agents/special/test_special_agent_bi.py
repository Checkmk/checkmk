#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import pytest

from cmk.special_agents.agent_bi import AggregationData

legacy_response_example = {
    "missing_aggr": [],
    "missing_sites": [],
    "rows": [
        {
            "groups": ["Hosts"],
            "tree": {
                "aggr_assumed_state": None,
                "aggr_effective_state": {
                    "acknowledged": False,
                    "in_downtime": False,
                    "in_service_period": True,
                    "output": "",
                    "state": 2,
                },
                "aggr_group": "Hosts",
                "aggr_hosts": [("heute", "heute")],
                "aggr_name": "Host heute",
                "aggr_output": "",
                "aggr_state": {
                    "acknowledged": False,
                    "in_downtime": False,
                    "in_service_period": True,
                    "output": "",
                    "state": 2,
                },
                "aggr_tree": {
                    "aggr_group_tree": ["Hosts"],
                    "aggr_type": "multi",
                    "aggregation_id": "default_aggregation",
                    "downtime_aggr_warn": False,
                    "node_visualization": {
                        "ignore_rule_styles": False,
                        "layout_id": "builtin_default",
                        "line_style": "round",
                    },
                    "nodes": [
                        {
                            "nodes": [
                                {
                                    "host": ("heute", "heute"),
                                    "reqhosts": [("heute", "heute")],
                                    "title": "heute",
                                    "type": 1,
                                },
                                {
                                    "nodes": [
                                        {
                                            "host": ("heute", "heute"),
                                            "reqhosts": [("heute", "heute")],
                                            "service": "Check_MK " "HW/SW " "Inventory",
                                            "title": "heute " "- " "Check_MK " "HW/SW " "Inventory",
                                            "type": 1,
                                        },
                                        {
                                            "host": ("heute", "heute"),
                                            "reqhosts": [("heute", "heute")],
                                            "service": "Check_MK",
                                            "title": "heute " "- " "Check_MK",
                                            "type": 1,
                                        },
                                    ],
                                    "reqhosts": [("heute", "heute")],
                                    "rule_id": "checkmk",
                                    "rule_layout_style": {"style_config": {}, "type": "none"},
                                    "title": "Check_MK",
                                    "type": 2,
                                },
                            ],
                            "reqhosts": [("heute", "heute")],
                            "rule_id": "general",
                            "rule_layout_style": {"style_config": {}, "type": "none"},
                            "title": "General State",
                            "type": 2,
                        },
                        {
                            "nodes": [
                                {
                                    "host": ("heute", "heute"),
                                    "reqhosts": [("heute", "heute")],
                                    "service": "BI " "Datasource " "Connection",
                                    "title": "heute - BI " "Datasource " "Connection",
                                    "type": 1,
                                },
                                {
                                    "host": ("heute", "heute"),
                                    "reqhosts": [("heute", "heute")],
                                    "service": "Aggr Host " "heute",
                                    "title": "heute - Aggr " "Host heute",
                                    "type": 1,
                                },
                            ],
                            "reqhosts": [],
                            "rule_id": "other",
                            "rule_layout_style": {"style_config": {}, "type": "none"},
                            "title": "Other",
                            "type": 2,
                        },
                    ],
                    "reqhosts": [("heute", "heute")],
                    "rule_id": "host",
                    "rule_layout_style": {"style_config": {}, "type": "none"},
                    "title": "Host heute",
                    "type": 2,
                    "use_hard_states": False,
                },
                "aggr_treestate": (
                    {
                        "acknowledged": False,
                        "in_downtime": False,
                        "in_service_period": True,
                        "output": "",
                        "state": 2,
                    },
                    None,
                    {
                        "aggr_group_tree": ["Hosts"],
                        "aggr_type": "multi",
                        "aggregation_id": "default_aggregation",
                        "downtime_aggr_warn": False,
                        "node_visualization": {
                            "ignore_rule_styles": False,
                            "layout_id": "builtin_default",
                            "line_style": "round",
                        },
                        "nodes": [
                            {
                                "nodes": [
                                    {
                                        "host": ("heute", "heute"),
                                        "reqhosts": [("heute", "heute")],
                                        "title": "heute",
                                        "type": 1,
                                    },
                                    {
                                        "nodes": [
                                            {
                                                "host": ("heute", "heute"),
                                                "reqhosts": [("heute", "heute")],
                                                "service": "Check_MK " "HW/SW " "Inventory",
                                                "title": "heute "
                                                "- "
                                                "Check_MK "
                                                "HW/SW "
                                                "Inventory",
                                                "type": 1,
                                            },
                                            {
                                                "host": ("heute", "heute"),
                                                "reqhosts": [("heute", "heute")],
                                                "service": "Check_MK",
                                                "title": "heute " "- " "Check_MK",
                                                "type": 1,
                                            },
                                        ],
                                        "reqhosts": [("heute", "heute")],
                                        "rule_id": "checkmk",
                                        "rule_layout_style": {"style_config": {}, "type": "none"},
                                        "title": "Check_MK",
                                        "type": 2,
                                    },
                                ],
                                "reqhosts": [("heute", "heute")],
                                "rule_id": "general",
                                "rule_layout_style": {"style_config": {}, "type": "none"},
                                "title": "General State",
                                "type": 2,
                            },
                            {
                                "nodes": [
                                    {
                                        "host": ("heute", "heute"),
                                        "reqhosts": [("heute", "heute")],
                                        "service": "BI " "Datasource " "Connection",
                                        "title": "heute " "- BI " "Datasource " "Connection",
                                        "type": 1,
                                    },
                                    {
                                        "host": ("heute", "heute"),
                                        "reqhosts": [("heute", "heute")],
                                        "service": "Aggr " "Host " "heute",
                                        "title": "heute " "- Aggr " "Host " "heute",
                                        "type": 1,
                                    },
                                ],
                                "reqhosts": [],
                                "rule_id": "other",
                                "rule_layout_style": {"style_config": {}, "type": "none"},
                                "title": "Other",
                                "type": 2,
                            },
                        ],
                        "reqhosts": [("heute", "heute")],
                        "rule_id": "host",
                        "rule_layout_style": {"style_config": {}, "type": "none"},
                        "title": "Host heute",
                        "type": 2,
                        "use_hard_states": False,
                    },
                    [
                        (
                            {
                                "acknowledged": False,
                                "in_downtime": False,
                                "in_service_period": True,
                                "output": "",
                                "state": 2,
                            },
                            None,
                            {
                                "nodes": [
                                    {
                                        "host": ("heute", "heute"),
                                        "reqhosts": [("heute", "heute")],
                                        "title": "heute",
                                        "type": 1,
                                    },
                                    {
                                        "nodes": [
                                            {
                                                "host": ("heute", "heute"),
                                                "reqhosts": [("heute", "heute")],
                                                "service": "Check_MK " "HW/SW " "Inventory",
                                                "title": "heute "
                                                "- "
                                                "Check_MK "
                                                "HW/SW "
                                                "Inventory",
                                                "type": 1,
                                            },
                                            {
                                                "host": ("heute", "heute"),
                                                "reqhosts": [("heute", "heute")],
                                                "service": "Check_MK",
                                                "title": "heute " "- " "Check_MK",
                                                "type": 1,
                                            },
                                        ],
                                        "reqhosts": [("heute", "heute")],
                                        "rule_id": "checkmk",
                                        "rule_layout_style": {"style_config": {}, "type": "none"},
                                        "title": "Check_MK",
                                        "type": 2,
                                    },
                                ],
                                "reqhosts": [("heute", "heute")],
                                "rule_id": "general",
                                "rule_layout_style": {"style_config": {}, "type": "none"},
                                "title": "General State",
                                "type": 2,
                            },
                            [
                                (
                                    {
                                        "acknowledged": False,
                                        "in_downtime": False,
                                        "in_service_period": True,
                                        "output": "Packet received via " "smart PING",
                                        "state": 0,
                                    },
                                    None,
                                    {
                                        "host": ("heute", "heute"),
                                        "reqhosts": [("heute", "heute")],
                                        "title": "heute",
                                        "type": 1,
                                    },
                                ),
                                (
                                    {
                                        "acknowledged": False,
                                        "in_downtime": False,
                                        "in_service_period": True,
                                        "output": "",
                                        "state": 2,
                                    },
                                    None,
                                    {
                                        "nodes": [
                                            {
                                                "host": ("heute", "heute"),
                                                "reqhosts": [("heute", "heute")],
                                                "service": "Check_MK " "HW/SW " "Inventory",
                                                "title": "heute - "
                                                "Check_MK "
                                                "HW/SW "
                                                "Inventory",
                                                "type": 1,
                                            },
                                            {
                                                "host": ("heute", "heute"),
                                                "reqhosts": [("heute", "heute")],
                                                "service": "Check_MK",
                                                "title": "heute - " "Check_MK",
                                                "type": 1,
                                            },
                                        ],
                                        "reqhosts": [("heute", "heute")],
                                        "rule_id": "checkmk",
                                        "rule_layout_style": {"style_config": {}, "type": "none"},
                                        "title": "Check_MK",
                                        "type": 2,
                                    },
                                    [
                                        (
                                            {
                                                "acknowledged": False,
                                                "in_downtime": False,
                                                "in_service_period": True,
                                                "output": "OK - Found 382 "
                                                "inventory entries, "
                                                "software changes, "
                                                "Found 233 status "
                                                "entries",
                                                "state": 0,
                                            },
                                            None,
                                            {
                                                "host": ("heute", "heute"),
                                                "reqhosts": [("heute", "heute")],
                                                "service": "Check_MK HW/SW " "Inventory",
                                                "title": "heute - Check_MK HW/SW " "Inventory",
                                                "type": 1,
                                            },
                                        ),
                                        (
                                            {
                                                "acknowledged": False,
                                                "in_downtime": False,
                                                "in_service_period": True,
                                                "output": "CRIT - [special_bi] "
                                                "Version: unknown, OS: "
                                                "unknown, Got no "
                                                "information from "
                                                "host, execution time "
                                                "0.2 sec ",
                                                "state": 2,
                                            },
                                            None,
                                            {
                                                "host": ("heute", "heute"),
                                                "reqhosts": [("heute", "heute")],
                                                "service": "Check_MK",
                                                "title": "heute - Check_MK",
                                                "type": 1,
                                            },
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        (
                            {
                                "acknowledged": False,
                                "in_downtime": False,
                                "in_service_period": True,
                                "output": "",
                                "state": 2,
                            },
                            None,
                            {
                                "nodes": [
                                    {
                                        "host": ("heute", "heute"),
                                        "reqhosts": [("heute", "heute")],
                                        "service": "BI Datasource " "Connection",
                                        "title": "heute - BI " "Datasource " "Connection",
                                        "type": 1,
                                    },
                                    {
                                        "host": ("heute", "heute"),
                                        "reqhosts": [("heute", "heute")],
                                        "service": "Aggr Host " "heute",
                                        "title": "heute - Aggr " "Host heute",
                                        "type": 1,
                                    },
                                ],
                                "reqhosts": [],
                                "rule_id": "other",
                                "rule_layout_style": {"style_config": {}, "type": "none"},
                                "title": "Other",
                                "type": 2,
                            },
                            [
                                (
                                    {
                                        "acknowledged": False,
                                        "in_downtime": False,
                                        "in_service_period": True,
                                        "output": "OK - No connection " "problems",
                                        "state": 0,
                                    },
                                    None,
                                    {
                                        "host": ("heute", "heute"),
                                        "reqhosts": [("heute", "heute")],
                                        "service": "BI Datasource " "Connection",
                                        "title": "heute - BI Datasource " "Connection",
                                        "type": 1,
                                    },
                                ),
                                (
                                    {
                                        "acknowledged": False,
                                        "in_downtime": False,
                                        "in_service_period": True,
                                        "output": "CRIT - Aggregation "
                                        "state: Critical(!!), In "
                                        "downtime: no, "
                                        "Acknowledged: no",
                                        "state": 2,
                                    },
                                    None,
                                    {
                                        "host": ("heute", "heute"),
                                        "reqhosts": [("heute", "heute")],
                                        "service": "Aggr Host heute",
                                        "title": "heute - Aggr Host heute",
                                        "type": 1,
                                    },
                                ),
                            ],
                        ),
                    ],
                ),
                "aggr_type": "multi",
                "tree": {
                    "aggr_group_tree": ["Hosts"],
                    "aggr_type": "multi",
                    "aggregation_id": "default_aggregation",
                    "downtime_aggr_warn": False,
                    "node_visualization": {
                        "ignore_rule_styles": False,
                        "layout_id": "builtin_default",
                        "line_style": "round",
                    },
                    "nodes": [
                        {
                            "nodes": [
                                {
                                    "host": ("heute", "heute"),
                                    "reqhosts": [("heute", "heute")],
                                    "title": "heute",
                                    "type": 1,
                                },
                                {
                                    "nodes": [
                                        {
                                            "host": ("heute", "heute"),
                                            "reqhosts": [("heute", "heute")],
                                            "service": "Check_MK " "HW/SW " "Inventory",
                                            "title": "heute " "- " "Check_MK " "HW/SW " "Inventory",
                                            "type": 1,
                                        },
                                        {
                                            "host": ("heute", "heute"),
                                            "reqhosts": [("heute", "heute")],
                                            "service": "Check_MK",
                                            "title": "heute " "- " "Check_MK",
                                            "type": 1,
                                        },
                                    ],
                                    "reqhosts": [("heute", "heute")],
                                    "rule_id": "checkmk",
                                    "rule_layout_style": {"style_config": {}, "type": "none"},
                                    "title": "Check_MK",
                                    "type": 2,
                                },
                            ],
                            "reqhosts": [("heute", "heute")],
                            "rule_id": "general",
                            "rule_layout_style": {"style_config": {}, "type": "none"},
                            "title": "General State",
                            "type": 2,
                        },
                        {
                            "nodes": [
                                {
                                    "host": ("heute", "heute"),
                                    "reqhosts": [("heute", "heute")],
                                    "service": "BI Datasource " "Connection",
                                    "title": "heute - BI " "Datasource " "Connection",
                                    "type": 1,
                                },
                                {
                                    "host": ("heute", "heute"),
                                    "reqhosts": [("heute", "heute")],
                                    "service": "Aggr Host heute",
                                    "title": "heute - Aggr Host " "heute",
                                    "type": 1,
                                },
                            ],
                            "reqhosts": [],
                            "rule_id": "other",
                            "rule_layout_style": {"style_config": {}, "type": "none"},
                            "title": "Other",
                            "type": 2,
                        },
                    ],
                    "reqhosts": [("heute", "heute")],
                    "rule_id": "host",
                    "rule_layout_style": {"style_config": {}, "type": "none"},
                    "title": "Host heute",
                    "type": 2,
                    "use_hard_states": False,
                },
            },
        }
    ],
}

latest_response_example = {
    "aggregations": {
        "Host heute": {
            "acknowledged": False,
            "hosts": ["heute"],
            "in_downtime": False,
            "in_service_period": True,
            "infos": [],
            "state": 2,
        }
    },
    "missing_aggr": [],
    "missing_sites": [],
}


@pytest.mark.parametrize(
    "webapi_data",
    [
        legacy_response_example,
        latest_response_example,
    ],
)
def test_bi_legacy_webapi_data_parsing(webapi_data):
    assert "missing_aggr" in webapi_data
    assert "missing_sites" in webapi_data

    parsed_aggregations = AggregationData.parse_aggregation_response(webapi_data)
    assert len(parsed_aggregations) == 1
    aggregation = parsed_aggregations.get("Host heute")
    assert aggregation is not None

    expected_values = [
        ("acknowledged", False),
        ("hosts", ["heute"]),
        ("in_downtime", False),
        ("in_service_period", True),
        ("state", 2),
        ("infos", []),
    ]
    assert len(aggregation) == len(expected_values)
    for key, expected_value in expected_values:
        assert aggregation[key] == expected_value
