#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Literal

import pytest

from cmk.gui.monitor.hosts.search_filters import host_search_filter
from cmk.gui.monitor.shared import (
    AndNode,
    FilterNode,
    FolderCondition,
    LabelChoiceCondition,
    NameChoiceCondition,
    StringCondition,
    StringField,
)
from cmk.gui.search.spec import parse, PrefixedSearch, UnsupportedSearchError
from cmk.ruleset_matcher.tags import TagConfig, TagGroupID, TagGroupSpec, TagID


def _tag_group(group: str, *tags: str) -> TagGroupSpec:
    return {
        "id": TagGroupID(group),
        "title": group,
        "tags": [{"id": TagID(tag), "title": tag, "aux_tags": []} for tag in tags],
    }


_TAGS = TagConfig.from_config(
    {
        "tag_groups": [
            _tag_group("criticality", "prod", "test"),
            _tag_group("dc", "fra", "shared"),
            _tag_group("rack", "r1", "shared"),
        ],
        "aux_tags": [{"id": TagID("snmp"), "title": "SNMP"}],
    }
)


_FOLDERS = {
    "": "Main",
    "dc_muc": "Data center Munich",
    "dc_muc/rack1": "Data center Munich / Rack 1",
    "dc_muc/rack10": "Data center Munich / Rack 10",
    "linux": "Linux servers",
    "linux10": "Linux 10",
}


def _filter(query: str, folders: Mapping[str, str] = _FOLDERS) -> FilterNode:
    spec = parse(query)
    assert isinstance(spec, PrefixedSearch)
    return host_search_filter(spec, _TAGS, lambda: folders)


def _contains(field: StringField, value: str) -> StringCondition:
    return StringCondition(type="condition", field=field, op="contains", value=value)


def _all_of(field: Literal["labels", "tags"], *pairs: str) -> LabelChoiceCondition:
    return LabelChoiceCondition(type="condition", field=field, op="all_of", value=list(pairs))


def _groups(*names: str) -> NameChoiceCondition:
    return NameChoiceCondition(type="condition", field="groups", op="one_of", value=list(names))


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("h:web", _contains("name", "web"), id="h"),
        pytest.param("al:db*", _contains("alias", "db.*"), id="al"),
        pytest.param("ad:10.", _contains("address", "10."), id="ad"),
        pytest.param("hl:os:linux", _all_of("labels", "os:linux"), id="hl"),
        pytest.param("tg:criticality:prod", _all_of("tags", "criticality:prod"), id="tg"),
        pytest.param("h:a h:b", _contains("name", "a|b"), id="repeated-pattern"),
        pytest.param("hl:os:lin*", _all_of("labels", "os:lin*"), id="hl-prefix"),
        pytest.param("hl:cmk/aws*", _all_of("labels", "cmk/aws*"), id="hl-key-prefix"),
        pytest.param("tg:os:lin*", _all_of("tags", "os:lin*"), id="tg-prefix"),
        pytest.param("hl:os:*", _all_of("labels", "os:*"), id="hl-any-value"),
        pytest.param("tg:os:*", _all_of("tags", "os:*"), id="tg-any-tag"),
        pytest.param("hg:linux", _groups("linux"), id="hg"),
        pytest.param("hg:linux hg:web*", _groups("linux", "web*"), id="hg-or-ed"),
        pytest.param("hg:linux hg:linux", _groups("linux"), id="hg-repeated"),
    ],
)
def test_clause_becomes_one_condition(query: str, expected: FilterNode) -> None:
    assert _filter(query) == expected


@pytest.mark.parametrize(
    "query, children",
    [
        pytest.param(
            "h:web ad:10.", [_contains("name", "web"), _contains("address", "10.")], id="prefixes"
        ),
        pytest.param(
            "hl:os:linux h:web tg:dc:fra hl:env:prod",
            [
                _all_of("labels", "os:linux", "env:prod"),
                _contains("name", "web"),
                _all_of("tags", "dc:fra"),
            ],
            id="labels-and-tags",
        ),
    ],
)
def test_clauses_are_top_level_and_conditions(query: str, children: list[FilterNode]) -> None:
    assert _filter(query) == AndNode(type="and", children=children)


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("tg:prod", _all_of("tags", "criticality:prod"), id="grouped-tag"),
        pytest.param("tg:snmp", _all_of("tags", "snmp:snmp"), id="aux-tag"),
        pytest.param(
            "tg:prod tg:dc:fra", _all_of("tags", "criticality:prod", "dc:fra"), id="with-explicit"
        ),
    ],
)
def test_tag_without_group_is_resolved_to_its_group(query: str, expected: FilterNode) -> None:
    assert _filter(query) == expected


@pytest.mark.parametrize(
    "query, expected",
    [
        pytest.param("hl:os:linux hl:env:prod", _all_of("labels", "os:linux", "env:prod"), id="hl"),
        pytest.param("tg:dc:fra tg:os:lin*", _all_of("tags", "dc:fra", "os:lin*"), id="tg"),
        pytest.param("hl:os:linux hl:os:linux", _all_of("labels", "os:linux"), id="repeated-pair"),
    ],
)
def test_labels_or_tags_are_one_condition_with_every_pair(query: str, expected: FilterNode) -> None:
    # A column filter shows a single condition per field. "all_of" ands the pairs like the clauses.
    assert _filter(query) == expected


@pytest.mark.parametrize(
    "query, message",
    [
        pytest.param("tg:unknown", 'Unknown host tag "unknown"', id="unknown-tag"),
        pytest.param("tg:shared", "several tag groups: dc, rack", id="tag-in-several-groups"),
        pytest.param("tg:pro*", "Please specify the tag group", id="tag-prefix-without-group"),
        pytest.param("s:cpu", "can only be searched by", id="service"),
        pytest.param("h:web s:cpu", "can only be searched by", id="host-and-service"),
        pytest.param("hf:dc_ber", 'No folder matches "dc_ber"', id="unknown-folder"),
        pytest.param(
            "hf:linux", "Linux servers, Linux 10", id="folder-path-matching-several-titles"
        ),
        pytest.param(
            "hf:dc_muc hf:linux", "cannot be shown as one folder title", id="several-folders"
        ),
    ],
)
def test_spec_all_hosts_cannot_filter_on_is_rejected(query: str, message: str) -> None:
    with pytest.raises(UnsupportedSearchError, match=message):
        _filter(query)


def test_rejected_folder_path_names_only_the_first_folder_titles() -> None:
    folders = {f"rack{n}": f"Rack {n:02}" for n in range(1, 8)}

    with pytest.raises(UnsupportedSearchError) as error:
        _filter("hf:rack", folders)

    assert "(Rack 01, Rack 02, Rack 03, Rack 04, Rack 05, ...)" in str(error.value)


def _folder(title: str) -> FolderCondition:
    return FolderCondition(type="condition", field="folder", op="contains", value=title)


@pytest.mark.parametrize(
    "query, title",
    [
        pytest.param("hf:dc_muc", "Data center Munich", id="folder-with-subfolders"),
        pytest.param("hf:/DC_MUC/", "Data center Munich", id="case-and-slashes"),
        pytest.param("hf:dc_muc/rack1", "Data center Munich / Rack 1", id="path-prefix"),
        pytest.param("hf:*/rack1", "Data center Munich / Rack 1", id="wildcard"),
        pytest.param("hf:dc_muc hf:dc_muc/rack1", "Data center Munich", id="folder-and-subfolder"),
    ],
)
def test_folder_path_becomes_the_title_selecting_the_same_folders(query: str, title: str) -> None:
    # "dc_muc/rack1" also matches "dc_muc/rack10", as does the title of rack1.
    assert _filter(query) == _folder(title)


def test_folders_are_only_read_for_a_folder_path() -> None:
    spec = parse("h:web")
    assert isinstance(spec, PrefixedSearch)

    def unused() -> Mapping[str, str]:
        raise AssertionError("the spec has no folder")

    assert host_search_filter(spec, _TAGS, unused) == _contains("name", "web")
