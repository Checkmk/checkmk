#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.bi.search import BIEmptySearch, BIFixedArgumentsSearch, BIHostSearch, BIServiceSearch
from cmk.utils.tags import TagGroupID, TagID

# NOTE: since the metadata is predominately written out to log, we want to mainly test what the
# string representation of the metadata looks like.


def test_empty_search_metadata() -> None:
    search = BIEmptySearch({"type": "empty"})

    value = str(search.metadata)
    expected = "EmptySearchMetadata()"

    assert value == expected


def test_host_search_metadata() -> None:
    search = BIHostSearch(
        {
            "type": "host_search",
            "conditions": {
                "host_folder": "",
                "host_label_groups": [("and", [("and", "cmk/check_mk_server:yes")])],
                "host_tags": {TagGroupID("clone-tag"): TagID("clone-tag")},
                "host_choice": {"type": "host_name_regex", "pattern": "(heute_cl).*"},
            },
            "refer_to": {"type": "host"},
        }
    )

    value = str(search.metadata)
    expected = "HostSearchMetadata(host_folder='', host_choice={'type': 'host_name_regex', 'pattern': '(heute_cl).*'}, host_tags_count=1, host_label_groups_count=1)"

    assert value == expected


def test_service_search_metadata() -> None:
    search = BIServiceSearch(
        {
            "type": "service_search",
            "conditions": {
                "host_folder": "",
                "host_label_groups": [("and", [("and", "cmk/check_mk_server:yes")])],
                "host_tags": {TagGroupID("clone-tag"): TagID("clone-tag")},
                "host_choice": {"type": "host_name_regex", "pattern": "(heute_cl).*"},
                "service_regex": "(cmk).*",
                "service_label_groups": [],
            },
        }
    )

    value = str(search.metadata)
    expected = "ServiceSearchMetadata(host_folder='', host_choice={'type': 'host_name_regex', 'pattern': '(heute_cl).*'}, service_regex='(cmk).*', host_tags_count=1, host_label_groups_count=1, service_label_groups_count=0)"

    assert value == expected


def test_fixed_argument_search_metadata() -> None:
    search = BIFixedArgumentsSearch(
        {
            "type": "fixed_arguments",
            "arguments": [
                {"key": "firstKey", "values": ["a", "b", "c", "e", "f"]},
                {"key": "secondKey", "values": ["e", "f", "g", "h"]},
            ],
        }
    )

    value = str(search.metadata)
    expected = "FixedArgsSearchMetadata(key_value_counts={'firstKey': 5, 'secondKey': 4})"

    assert value == expected
