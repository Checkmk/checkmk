#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import pytest

from cmk.utils.bi.bi_search import (
    BIEmptySearch,
    BIFixedArgumentsSearch,
    BIHostSearch,
    BIServiceSearch,
)


def test_empty_search(bi_searcher) -> None:
    schema_config = BIEmptySearch.schema()().dump({})
    search = BIEmptySearch(schema_config)
    results = search.execute({}, bi_searcher)
    assert len(results) == 1
    assert results[0] == {}


@pytest.mark.parametrize(
    "config, num_expected_keys, expected_total_length",
    [
        (
            [{"key": "firstKey", "values": ["a", "b", "c"]}],
            1,
            3,
        ),
        (
            [
                {"key": "firstKey", "values": ["a", "b", "c"]},
                {"key": "secondKey", "values": ["e", "f", "g"]},
            ],
            2,
            3,
        ),
        (
            [
                {"key": "firstKey", "values": ["a", "b", "c", "e", "f"]},
                {"key": "secondKey", "values": ["e", "f", "g", "h"]},
            ],
            2,
            5,
        ),
    ],
)
def test_fixed_argument_search(
    config, num_expected_keys, expected_total_length, bi_searcher_with_sample_config
):
    schema_config = BIFixedArgumentsSearch.schema()().dump({"arguments": config})
    search = BIFixedArgumentsSearch(schema_config)
    results = search.execute({}, bi_searcher_with_sample_config)
    assert len(results) == expected_total_length
    assert len(results[0].keys()) == num_expected_keys


@pytest.mark.parametrize(
    "search_class",
    [
        BIHostSearch,
        BIServiceSearch,
    ],
)
@pytest.mark.parametrize(
    "folder_name, expected_hostnames",
    [
        pytest.param("subfolder", {"heute_clone"}, id="Match single host in subfolder"),
        pytest.param("", {"heute", "heute_clone"}, id="Match all hosts in config"),
        pytest.param("wrongfolder", set(), id="Match no host"),
    ],
)
def test_host_folder_search(
    search_class, bi_searcher_with_sample_config, folder_name, expected_hostnames
):
    schema_config = search_class.schema()().dump({"conditions": {"host_folder": folder_name}})
    search = search_class(schema_config)
    results = search.execute({}, bi_searcher_with_sample_config)
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert hostnames == expected_hostnames


@pytest.mark.parametrize(
    "search_class",
    [
        BIHostSearch,
        BIServiceSearch,
    ],
)
def test_host_search(search_class, bi_searcher_with_sample_config) -> None:
    schema_config = search_class.schema()().dump({})
    search = search_class(schema_config)
    results = search.execute({}, bi_searcher_with_sample_config)
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert len(hostnames) == 2

    # Tag match
    schema_config = search_class.schema()().dump(
        {"conditions": {"host_tags": {"clone-tag": "clone-tag"}}}
    )
    search = search_class(schema_config)
    results = search.execute({}, bi_searcher_with_sample_config)
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert len(hostnames) == 1
    assert "heute_clone" in hostnames

    # Label match
    schema_config = search_class.schema()().dump(
        {"conditions": {"host_labels": {"cmk/check_mk_server": "yes"}}}
    )
    search = search_class(schema_config)
    results = search.execute({}, bi_searcher_with_sample_config)
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert len(hostnames) == 1

    # Regex match hit without match group
    schema_config = search_class.schema()().dump(
        {"conditions": {"host_choice": {"type": "host_name_regex", "pattern": "heute_cl.*"}}}
    )
    search = search_class(schema_config)
    results = search.execute({}, bi_searcher_with_sample_config)
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert len(hostnames) == 1
    assert results[0]["$1$"] == ""
    assert "heute_clone" in hostnames

    # Regex match hit with match group
    schema_config = search_class.schema()().dump(
        {"conditions": {"host_choice": {"type": "host_name_regex", "pattern": "(heute_cl).*"}}}
    )
    search = search_class(schema_config)
    results = search.execute({}, bi_searcher_with_sample_config)
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert len(hostnames) == 1
    assert results[0]["$1$"] == "heute_cl"
    assert results[0]["$HOST_MG_0$"] == "heute_cl"
    assert results[0]["$HOSTNAME$"] == "heute_clone"

    # Regex match miss
    schema_config = search_class.schema()().dump(
        {"conditions": {"host_choice": {"type": "host_name_regex", "pattern": "heute_missing.*"}}}
    )
    search = search_class(schema_config)
    results = search.execute({}, bi_searcher_with_sample_config)
    assert len(results) == 0

    # Alias match
    schema_config = search_class.schema()().dump(
        {"conditions": {"host_choice": {"type": "host_alias_regex", "pattern": "heute_alias"}}}
    )
    search = search_class(schema_config)
    results = search.execute({}, bi_searcher_with_sample_config)
    hostnames = {x["$HOSTNAME$"] for x in results}
    assert len(hostnames) == 1


@pytest.mark.parametrize(
    "service_regex, host_regex, expected_matches",
    [
        ("Interface", ".*", 7),
        ("Interface.*", ".*", 7),
        ("Interface$", ".*", 0),
        ("Interface (2|4)", ".*", 4),
        ("Interface", "heute", 3),
        ("Interface", "heute$", 3),
        ("Interface", "heute_clone", 4),
    ],
)
def test_service_search(
    service_regex, host_regex, expected_matches, bi_searcher_with_sample_config
):
    schema_config = BIServiceSearch.schema()().dump(
        {
            "conditions": {
                "service_regex": service_regex,
                "host_choice": {
                    "type": "host_name_regex",
                    "pattern": host_regex,
                },
            }
        }
    )
    search = BIServiceSearch(schema_config)
    results = search.execute({}, bi_searcher_with_sample_config)
    assert len(results) == expected_matches
