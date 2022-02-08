#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Callable, Sequence

import pytest

from cmk.base.api.agent_based.checking_classes import Service, ServiceLabel
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, State
from cmk.base.plugins.agent_based.gcp_function import (
    check_gcp_function_egress,
    check_gcp_function_execution,
    check_gcp_function_instances,
    discover,
    parse_gcp_function,
)

SECTION_TABLE = [
    ['[{"name": "function-1"}, {"name": "function-2"}, {"name": "function-3"}]'],
    [
        "CjgaNmNsb3VkZnVuY3Rpb25zLmdvb2dsZWFwaXMuY29tL2Z1bmN0aW9uL2V4ZWN1dGlvbl9jb3VudBJKCg5jbG91ZF9mdW5jdGlvbhIbCgpwcm9qZWN0X2lkEg1iYWNrdXAtMjU1ODIwEhsKDWZ1bmN0aW9uX25hbWUSCmZ1bmN0aW9uLTIYASADKikKHAoMCOKCvpAGEMiwyNoBEgwI4oK+kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAimgr6QBhDIsMjaARIMCKaCvpAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwI6oG+kAYQyLDI2gESDAjqgb6QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCK6BvpAGEMiwyNoBEgwIroG+kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAjygL6QBhDIsMjaARIMCPKAvpAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwItoC+kAYQyLDI2gESDAi2gL6QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCPr/vZAGEMiwyNoBEgwI+v+9kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAi+/72QBhDIsMjaARIMCL7/vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwIgv+9kAYQyLDI2gESDAiC/72QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCMb+vZAGEMiwyNoBEgwIxv69kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAiK/r2QBhDIsMjaARIMCIr+vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwIzv29kAYQyLDI2gESDAjO/b2QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCJL9vZAGEMiwyNoBEgwIkv29kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAjW/L2QBhDIsMjaARIMCNb8vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwImvy9kAYQyLDI2gESDAia/L2QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCN77vZAGEMiwyNoBEgwI3vu9kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAii+72QBhDIsMjaARIMCKL7vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwI5vq9kAYQyLDI2gESDAjm+r2QBhDIsMjaARIJGQAAAAAAAAAA"
    ],
    [
        "CjgaNmNsb3VkZnVuY3Rpb25zLmdvb2dsZWFwaXMuY29tL2Z1bmN0aW9uL2V4ZWN1dGlvbl9jb3VudBJKCg5jbG91ZF9mdW5jdGlvbhIbCgpwcm9qZWN0X2lkEg1iYWNrdXAtMjU1ODIwEhsKDWZ1bmN0aW9uX25hbWUSCmZ1bmN0aW9uLTMYASADKikKHAoMCKaCvpAGEMiwyNoBEgwIpoK+kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAjqgb6QBhDIsMjaARIMCOqBvpAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwIroG+kAYQyLDI2gESDAiugb6QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCPKAvpAGEMiwyNoBEgwI8oC+kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAi2gL6QBhDIsMjaARIMCLaAvpAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwI+v+9kAYQyLDI2gESDAj6/72QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCL7/vZAGEMiwyNoBEgwIvv+9kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAiC/72QBhDIsMjaARIMCIL/vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwIxv69kAYQyLDI2gESDAjG/r2QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCIr+vZAGEMiwyNoBEgwIiv69kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAjO/b2QBhDIsMjaARIMCM79vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwIkv29kAYQyLDI2gESDAiS/b2QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCNb8vZAGEMiwyNoBEgwI1vy9kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAia/L2QBhDIsMjaARIMCJr8vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwI3vu9kAYQyLDI2gESDAje+72QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCKL7vZAGEMiwyNoBEgwIovu9kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAjm+r2QBhDIsMjaARIMCOb6vZAGEMiwyNoBEgkZAAAAAAAAAAA="
    ],
    [
        "CjcaNWNsb3VkZnVuY3Rpb25zLmdvb2dsZWFwaXMuY29tL2Z1bmN0aW9uL25ldHdvcmtfZWdyZXNzEkoKDmNsb3VkX2Z1bmN0aW9uEhsKCnByb2plY3RfaWQSDWJhY2t1cC0yNTU4MjASGwoNZnVuY3Rpb25fbmFtZRIKZnVuY3Rpb24tMhgBIAMqKQocCgwIpoK+kAYQyLDI2gESDAimgr6QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCOqBvpAGEMiwyNoBEgwI6oG+kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAiugb6QBhDIsMjaARIMCK6BvpAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwI8oC+kAYQyLDI2gESDAjygL6QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCLaAvpAGEMiwyNoBEgwItoC+kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAj6/72QBhDIsMjaARIMCPr/vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwIvv+9kAYQyLDI2gESDAi+/72QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCIL/vZAGEMiwyNoBEgwIgv+9kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAjG/r2QBhDIsMjaARIMCMb+vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwIiv69kAYQyLDI2gESDAiK/r2QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCM79vZAGEMiwyNoBEgwIzv29kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAiS/b2QBhDIsMjaARIMCJL9vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwI1vy9kAYQyLDI2gESDAjW/L2QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCJr8vZAGEMiwyNoBEgwImvy9kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAje+72QBhDIsMjaARIMCN77vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwIovu9kAYQyLDI2gESDAii+72QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCOb6vZAGEMiwyNoBEgwI5vq9kAYQyLDI2gESCRkAAAAAAAAAAA=="
    ],
    [
        "CjcaNWNsb3VkZnVuY3Rpb25zLmdvb2dsZWFwaXMuY29tL2Z1bmN0aW9uL25ldHdvcmtfZWdyZXNzEkoKDmNsb3VkX2Z1bmN0aW9uEhsKDWZ1bmN0aW9uX25hbWUSCmZ1bmN0aW9uLTMSGwoKcHJvamVjdF9pZBINYmFja3VwLTI1NTgyMBgBIAMqKQocCgwIpoK+kAYQyLDI2gESDAimgr6QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCOqBvpAGEMiwyNoBEgwI6oG+kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAiugb6QBhDIsMjaARIMCK6BvpAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwI8oC+kAYQyLDI2gESDAjygL6QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCLaAvpAGEMiwyNoBEgwItoC+kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAj6/72QBhDIsMjaARIMCPr/vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwIvv+9kAYQyLDI2gESDAi+/72QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCIL/vZAGEMiwyNoBEgwIgv+9kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAjG/r2QBhDIsMjaARIMCMb+vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwIiv69kAYQyLDI2gESDAiK/r2QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCM79vZAGEMiwyNoBEgwIzv29kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAiS/b2QBhDIsMjaARIMCJL9vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwI1vy9kAYQyLDI2gESDAjW/L2QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCJr8vZAGEMiwyNoBEgwImvy9kAYQyLDI2gESCRkAAAAAAAAAACopChwKDAje+72QBhDIsMjaARIMCN77vZAGEMiwyNoBEgkZAAAAAAAAAAAqKQocCgwIovu9kAYQyLDI2gESDAii+72QBhDIsMjaARIJGQAAAAAAAAAAKikKHAoMCOb6vZAGEMiwyNoBEgwI5vq9kAYQyLDI2gESCRkAAAAAAAAAAA=="
    ],
    [
        "CjcaNWNsb3VkZnVuY3Rpb25zLmdvb2dsZWFwaXMuY29tL2Z1bmN0aW9uL2luc3RhbmNlX2NvdW50EkoKDmNsb3VkX2Z1bmN0aW9uEhsKDWZ1bmN0aW9uX25hbWUSCmZ1bmN0aW9uLTISGwoKcHJvamVjdF9pZBINYmFja3VwLTI1NTgyMBgBIAIqIgocCgwIpoK+kAYQyLDI2gESDAimgr6QBhDIsMjaARICEAAqIgocCgwI6oG+kAYQyLDI2gESDAjqgb6QBhDIsMjaARICEAAqIgocCgwIroG+kAYQyLDI2gESDAiugb6QBhDIsMjaARICEAAqIgocCgwI8oC+kAYQyLDI2gESDAjygL6QBhDIsMjaARICEAEqIgocCgwItoC+kAYQyLDI2gESDAi2gL6QBhDIsMjaARICEAEqIgocCgwI+v+9kAYQyLDI2gESDAj6/72QBhDIsMjaARICEAEqIgocCgwIvv+9kAYQyLDI2gESDAi+/72QBhDIsMjaARICEAEqIgocCgwIgv+9kAYQyLDI2gESDAiC/72QBhDIsMjaARICEAEqIgocCgwIxv69kAYQyLDI2gESDAjG/r2QBhDIsMjaARICEAEqIgocCgwIiv69kAYQyLDI2gESDAiK/r2QBhDIsMjaARICEAEqIgocCgwIzv29kAYQyLDI2gESDAjO/b2QBhDIsMjaARICEAEqIgocCgwIkv29kAYQyLDI2gESDAiS/b2QBhDIsMjaARICEAEqIgocCgwI1vy9kAYQyLDI2gESDAjW/L2QBhDIsMjaARICEAIqIgocCgwImvy9kAYQyLDI2gESDAia/L2QBhDIsMjaARICEAIqIgocCgwI3vu9kAYQyLDI2gESDAje+72QBhDIsMjaARICEAIqIgocCgwIovu9kAYQyLDI2gESDAii+72QBhDIsMjaARICEAIqIgocCgwI5vq9kAYQyLDI2gESDAjm+r2QBhDIsMjaARICEAQ="
    ],
    [
        "CjcaNWNsb3VkZnVuY3Rpb25zLmdvb2dsZWFwaXMuY29tL2Z1bmN0aW9uL2luc3RhbmNlX2NvdW50EkoKDmNsb3VkX2Z1bmN0aW9uEhsKCnByb2plY3RfaWQSDWJhY2t1cC0yNTU4MjASGwoNZnVuY3Rpb25fbmFtZRIKZnVuY3Rpb24tMxgBIAIqIgocCgwIpoK+kAYQyLDI2gESDAimgr6QBhDIsMjaARICEAAqIgocCgwI6oG+kAYQyLDI2gESDAjqgb6QBhDIsMjaARICEAAqIgocCgwIroG+kAYQyLDI2gESDAiugb6QBhDIsMjaARICEAAqIgocCgwI8oC+kAYQyLDI2gESDAjygL6QBhDIsMjaARICEAAqIgocCgwItoC+kAYQyLDI2gESDAi2gL6QBhDIsMjaARICEAAqIgocCgwI+v+9kAYQyLDI2gESDAj6/72QBhDIsMjaARICEAAqIgocCgwIvv+9kAYQyLDI2gESDAi+/72QBhDIsMjaARICEAUqIgocCgwIgv+9kAYQyLDI2gESDAiC/72QBhDIsMjaARICEAYqIgocCgwIxv69kAYQyLDI2gESDAjG/r2QBhDIsMjaARICEAYqIgocCgwIiv69kAYQyLDI2gESDAiK/r2QBhDIsMjaARICEAYqIgocCgwIzv29kAYQyLDI2gESDAjO/b2QBhDIsMjaARICEAYqIgocCgwIkv29kAYQyLDI2gESDAiS/b2QBhDIsMjaARICEAcqIgocCgwI1vy9kAYQyLDI2gESDAjW/L2QBhDIsMjaARICEAcqIgocCgwImvy9kAYQyLDI2gESDAia/L2QBhDIsMjaARICEAcqIgocCgwI3vu9kAYQyLDI2gESDAje+72QBhDIsMjaARICEAcqIgocCgwIovu9kAYQyLDI2gESDAii+72QBhDIsMjaARICEAgqIgocCgwI5vq9kAYQyLDI2gESDAjm+r2QBhDIsMjaARICEAg="
    ],
    [
        "CjkaN2Nsb3VkZnVuY3Rpb25zLmdvb2dsZWFwaXMuY29tL2Z1bmN0aW9uL2FjdGl2ZV9pbnN0YW5jZXMSSgoOY2xvdWRfZnVuY3Rpb24SGwoNZnVuY3Rpb25fbmFtZRIKZnVuY3Rpb24tMhIbCgpwcm9qZWN0X2lkEg1iYWNrdXAtMjU1ODIwGAEgAioiChwKDAjigr6QBhDIsMjaARIMCOKCvpAGEMiwyNoBEgIQACoiChwKDAimgr6QBhDIsMjaARIMCKaCvpAGEMiwyNoBEgIQACoiChwKDAjqgb6QBhDIsMjaARIMCOqBvpAGEMiwyNoBEgIQACoiChwKDAiugb6QBhDIsMjaARIMCK6BvpAGEMiwyNoBEgIQACoiChwKDAjygL6QBhDIsMjaARIMCPKAvpAGEMiwyNoBEgIQACoiChwKDAi2gL6QBhDIsMjaARIMCLaAvpAGEMiwyNoBEgIQACoiChwKDAj6/72QBhDIsMjaARIMCPr/vZAGEMiwyNoBEgIQACoiChwKDAi+/72QBhDIsMjaARIMCL7/vZAGEMiwyNoBEgIQACoiChwKDAiC/72QBhDIsMjaARIMCIL/vZAGEMiwyNoBEgIQACoiChwKDAjG/r2QBhDIsMjaARIMCMb+vZAGEMiwyNoBEgIQACoiChwKDAiK/r2QBhDIsMjaARIMCIr+vZAGEMiwyNoBEgIQACoiChwKDAjO/b2QBhDIsMjaARIMCM79vZAGEMiwyNoBEgIQACoiChwKDAiS/b2QBhDIsMjaARIMCJL9vZAGEMiwyNoBEgIQACoiChwKDAjW/L2QBhDIsMjaARIMCNb8vZAGEMiwyNoBEgIQACoiChwKDAia/L2QBhDIsMjaARIMCJr8vZAGEMiwyNoBEgIQACoiChwKDAje+72QBhDIsMjaARIMCN77vZAGEMiwyNoBEgIQACoiChwKDAii+72QBhDIsMjaARIMCKL7vZAGEMiwyNoBEgIQACoiChwKDAjm+r2QBhDIsMjaARIMCOb6vZAGEMiwyNoBEgIQAA=="
    ],
    [
        "CjkaN2Nsb3VkZnVuY3Rpb25zLmdvb2dsZWFwaXMuY29tL2Z1bmN0aW9uL2FjdGl2ZV9pbnN0YW5jZXMSSgoOY2xvdWRfZnVuY3Rpb24SGwoKcHJvamVjdF9pZBINYmFja3VwLTI1NTgyMBIbCg1mdW5jdGlvbl9uYW1lEgpmdW5jdGlvbi0zGAEgAioiChwKDAimgr6QBhDIsMjaARIMCKaCvpAGEMiwyNoBEgIQACoiChwKDAjqgb6QBhDIsMjaARIMCOqBvpAGEMiwyNoBEgIQACoiChwKDAiugb6QBhDIsMjaARIMCK6BvpAGEMiwyNoBEgIQACoiChwKDAjygL6QBhDIsMjaARIMCPKAvpAGEMiwyNoBEgIQACoiChwKDAi2gL6QBhDIsMjaARIMCLaAvpAGEMiwyNoBEgIQACoiChwKDAj6/72QBhDIsMjaARIMCPr/vZAGEMiwyNoBEgIQACoiChwKDAi+/72QBhDIsMjaARIMCL7/vZAGEMiwyNoBEgIQACoiChwKDAiC/72QBhDIsMjaARIMCIL/vZAGEMiwyNoBEgIQACoiChwKDAjG/r2QBhDIsMjaARIMCMb+vZAGEMiwyNoBEgIQACoiChwKDAiK/r2QBhDIsMjaARIMCIr+vZAGEMiwyNoBEgIQACoiChwKDAjO/b2QBhDIsMjaARIMCM79vZAGEMiwyNoBEgIQACoiChwKDAiS/b2QBhDIsMjaARIMCJL9vZAGEMiwyNoBEgIQACoiChwKDAjW/L2QBhDIsMjaARIMCNb8vZAGEMiwyNoBEgIQACoiChwKDAia/L2QBhDIsMjaARIMCJr8vZAGEMiwyNoBEgIQACoiChwKDAje+72QBhDIsMjaARIMCN77vZAGEMiwyNoBEgIQACoiChwKDAii+72QBhDIsMjaARIMCKL7vZAGEMiwyNoBEgIQACoiChwKDAjm+r2QBhDIsMjaARIMCOb6vZAGEMiwyNoBEgIQAA=="
    ],
]


def test_parse_gcp():
    section = parse_gcp_function(SECTION_TABLE)
    n_rows = sum(len(i.rows) for i in section.values())
    # first row contains general section information and no metrics
    assert n_rows == len(SECTION_TABLE) - 1


@pytest.fixture(name="section")
def fixture_section():
    return parse_gcp_function(SECTION_TABLE)


def test_item_without_data_is_invalid(section):
    for name, item in section.items():
        if name == "nodata":
            assert not item.is_valid


@pytest.fixture(name="functions")
def fixture_functions(section):
    return sorted(list(discover(section)))


def test_discover_two_functions(functions: Sequence[Service]):
    assert len(functions) == 2
    assert {b.item for b in functions} == {"function-2", "function-3"}


def test_discover_project_labels(functions: Sequence[Service]):
    for bucket in functions:
        assert ServiceLabel("gcp_project_id", "backup-255820") in bucket.labels


def test_discover_bucket_labels(functions: Sequence[Service]):
    labels = functions[0].labels
    assert len(labels) == 2
    assert ServiceLabel("gcp_function_name", "function-2") in labels


@dataclass(frozen=True)
class Plugin:
    metrics: Sequence[str]
    function: Callable


PLUGINS = [
    Plugin(
        function=check_gcp_function_egress,
        metrics=[
            "net_data_sent",
        ],
    ),
    Plugin(
        function=check_gcp_function_execution,
        metrics=["faas_execution_count", "aws_lambda_memory_size_absolute", "faas_execution_times"],
    ),
    Plugin(
        function=check_gcp_function_instances,
        metrics=[
            "faas_total_instance_count",
            "faas_active_instance_count",
        ],
    ),
]
ITEM = "function-3"


@pytest.fixture(params=PLUGINS, name="checkplugin")
def fixture_checkplugin(request):
    return request.param


@pytest.fixture(name="results")
def fixture_results(checkplugin, section):
    params = {k: None for k in checkplugin.metrics}
    results = list(checkplugin.function(item=ITEM, params=params, section=section))
    return results, checkplugin


def test_yield_metrics_as_specified(results):
    results, checkplugin = results
    res = {r.name: r for r in results if isinstance(r, Metric)}
    assert len(res) == len(checkplugin.metrics)
    assert set(res.keys()) == set(checkplugin.metrics)


def test_yield_results_as_specified(results):
    results, checkplugin = results
    res = [r for r in results if isinstance(r, Result)]
    assert len(res) == len(checkplugin.metrics)
    for r in res:
        assert r.state == State.OK


class TestDefaultMetricValues:
    # requests does not contain example data
    def test_zero_default_if_metric_does_not_exist(self, section):
        params = {k: None for k in ["requests"]}
        results = (
            el
            for el in check_gcp_function_instances(item=ITEM, params=params, section=section)
            if isinstance(el, Metric)
        )
        for result in results:
            assert result.value == 0.0


class TestConfiguredNotificationLevels:
    # In the example sections we do not have data for all metrics. To be able to test all check plugins
    # use 0, the default value, to check notification levels.
    def test_warn_levels(self, checkplugin, section):
        params = {k: (0, None) for k in checkplugin.metrics}
        results = list(checkplugin.function(item=ITEM, params=params, section=section))
        results = [r for r in results if isinstance(r, Result)]
        for r in results:
            assert r.state == State.WARN

    def test_crit_levels(self, checkplugin, section):
        params = {k: (None, 0) for k in checkplugin.metrics}
        results = list(checkplugin.function(item=ITEM, params=params, section=section))
        results = [r for r in results if isinstance(r, Result)]
        for r in results:
            assert r.state == State.CRIT
