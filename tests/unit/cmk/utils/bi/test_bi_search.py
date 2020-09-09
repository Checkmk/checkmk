#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import pytest  # type: ignore[import]

from cmk.utils.bi.bi_search import (
    BIEmptySearch,
    BIHostSearch,
    BIServiceSearch,
    BIFixedArgumentsSearch,
)


def test_empty_search():
    schema_config = BIEmptySearch.schema()().dump({}).data
    search = BIEmptySearch(schema_config)
    results = search.execute({})
    assert len(results) == 1
    assert results[0] == {}


@pytest.mark.parametrize("config, num_expected_keys, expected_total_length", [
    (
        [{
            "key": "firstKey",
            "values": ["a", "b", "c"]
        }],
        1,
        3,
    ),
    (
        [{
            "key": "firstKey",
            "values": ["a", "b", "c"]
        }, {
            "key": "secondKey",
            "values": ["e", "f", "g"]
        }],
        2,
        3,
    ),
    (
        [{
            "key": "firstKey",
            "values": ["a", "b", "c", "e", "f"]
        }, {
            "key": "secondKey",
            "values": ["e", "f", "g", "h"]
        }],
        2,
        5,
    ),
])
def test_fixed_argument_search(config, num_expected_keys, expected_total_length,
                               use_test_structure_data):
    schema_config = BIFixedArgumentsSearch.schema()().dump({"arguments": config}).data
    search = BIFixedArgumentsSearch(schema_config)
    results = search.execute({})
    assert len(results) == expected_total_length
    assert len(results[0].keys()) == num_expected_keys


@pytest.mark.parametrize("search_class", [
    BIHostSearch,
    BIServiceSearch,
])
def test_host_search(search_class, use_test_structure_data):
    schema_config = search_class.schema()().dump({}).data
    search = search_class(schema_config)
    results = search.execute({})
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert len(hostnames) == 2

    # Tag match
    schema_config = search_class.schema()().dump({
        "conditions": {
            "host_tags": {
                "cmk-agent": "clone-tag"
            }
        }
    }).data
    search = search_class(schema_config)
    results = search.execute({})
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert len(hostnames) == 1
    assert "heute_clone" in hostnames

    # Label match
    schema_config = search_class.schema()().dump({
        "conditions": {
            "host_labels": {
                "cmk/check_mk_server": "yes"
            }
        }
    }).data
    search = search_class(schema_config)
    results = search.execute({})
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert len(hostnames) == 1

    # Regex match hit
    schema_config = search_class.schema()().dump({
        "conditions": {
            "host_choice": {
                "type": "host_name_regex",
                "pattern": "heute_cl.*"
            }
        }
    }).data
    search = search_class(schema_config)
    results = search.execute({})
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert len(hostnames) == 1
    assert "heute_clone" in hostnames

    # Regex match miss
    schema_config = search_class.schema()().dump({
        "conditions": {
            "host_choice": {
                "type": "host_name_regex",
                "pattern": "heute_missing.*"
            }
        }
    }).data
    search = search_class(schema_config)
    results = search.execute({})
    assert len(results) == 0

    # Alias match
    schema_config = search_class.schema()().dump({
        "conditions": {
            "host_choice": {
                "type": "host_alias_regex",
                "pattern": "heute_alias"
            }
        }
    }).data
    search = search_class(schema_config)
    results = search.execute({})
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert len(hostnames) == 1


@pytest.mark.parametrize("service_regex, host_regex, expected_matches", [
    ("Interface", ".*", 7),
    ("Interface.*", ".*", 7),
    ("Interface$", ".*", 0),
    ("Interface (2|4)", ".*", 4),
    ("Interface", "heute", 3),
    ("Interface", "heute$", 3),
    ("Interface", "heute_clone", 4),
])
def test_service_search(service_regex, host_regex, expected_matches, use_test_structure_data):
    schema_config = BIServiceSearch.schema()().dump({
        "conditions": {
            "service_regex": service_regex,
            "host_choice": {
                "type": "host_name_regex",
                "pattern": host_regex,
            }
        }
    }).data
    search = BIServiceSearch(schema_config)
    results = search.execute({})
    assert len(results) == expected_matches
