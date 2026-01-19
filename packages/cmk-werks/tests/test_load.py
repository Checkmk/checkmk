#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator, Mapping

import pytest

from cmk.werks import load_werk
from cmk.werks.error import WerkError
from cmk.werks.load import _format_title, load_werk_v2, load_werk_v3
from cmk.werks.models import WerkV2
from cmk.werks.parse import parse_werk_v2, parse_werk_v3

WERK_V1 = {
    "class": "fix",
    "component": "core",
    "date": 0,
    "level": 1,
    "title": "Some Title",
    "version": "42.0.0p7",
    "compatible": "compat",
    "edition": "cre",
    "description": [],
}

WERK_V2 = {
    "class": "fix",
    "component": "core",
    "date": "1970-01-01T00:00:00Z",
    "level": 1,
    "title": "Some Title",
    "version": "42.0.0p7",
    "compatible": "yes",
    "edition": "cre",
    "description": "",
}


WERK_V1_MISSING_CLASS = """Title: APT: Fix service discovery when getting unexpected output from apt
Level: 1
Component: checks
Compatible: compat
Edition: cre
State: unknown
Version: 2.0.0i1
Date: 1569225628

"""


def get_werk_v1(werk_dict: Mapping[str, object]) -> str:
    def generate() -> Iterator[str]:
        for key, value in werk_dict.items():
            if key == "description":
                continue
            yield f"{key}: {value}"
        assert isinstance(werk_dict["description"], list)
        yield from ("{line}" for line in werk_dict["description"])

    return "\n".join(generate())


def test_werk_loading() -> None:
    loaded_data = load_werk(file_content=get_werk_v1(WERK_V1), file_name="1").to_json_dict()
    # loaded_data contains id, and other default values, WERK_V1 does not have
    for key, value in WERK_V2.items():
        assert loaded_data[key] == value


def test_werk_loading_missing_field() -> None:
    bad_werk = dict(WERK_V1)
    bad_werk.pop("class")
    with pytest.raises(TypeError, match="class\n  Field required"):
        load_werk(file_content=get_werk_v1(bad_werk), file_name="1")


def test_werk_loading_unknown_field() -> None:
    bad_werk = dict(WERK_V1)
    bad_werk["foo"] = "bar"
    with pytest.raises(
        TypeError,
        match="validation error for WerkV2\nfoo\n  Extra inputs are not permitted",
    ):
        load_werk(file_content=get_werk_v1(bad_werk), file_name="1")


def _markdown_string_to_werk(md: str) -> WerkV2:
    return load_werk_v2(parse_werk_v2(md, werk_id="1234"))


def test_loading_md_werk_missing_header() -> None:
    with pytest.raises(WerkError, match="Markdown formatted werks need to start with"):
        _markdown_string_to_werk("")


def test_loading_md_werk_missing_title() -> None:
    md = """[//]: # (werk v2)
this is the `description` with some *formatting.*

table

body
"""
    with pytest.raises(
        WerkError, match="First element after the header needs to be the title as a h1 headline."
    ):
        _markdown_string_to_werk(md)


def test_loading_md_werk_missing_table() -> None:
    with pytest.raises(
        WerkError,
        match="Table should have exactly two columns, found 'table' instead",
    ):
        md = """[//]: # (werk v2)
# title

table

this is the `description` with some *formatting.*
"""
        _markdown_string_to_werk(md)


def test_loading_md_werk_missing_key_value_pair() -> None:
    md = """[//]: # (werk v2)
# title

key | value
--- | ---
class | fix
component | core
level | 1
version | 2.0.0p7
edition | cre

this is the `description` with some *formatting.*
"""
    with pytest.raises(WerkError, match="Field required"):
        _markdown_string_to_werk(md)


def test_loading_md_werk_no_iso_date() -> None:
    md = """[//]: # (werk v2)
# title

key | value
--- | ---
class | fix
component | core
date | smth
level | 1
version | 2.0.0p7
compatible | yes
edition | cre

this is the `description` with some *formatting.*
"""
    with pytest.raises(WerkError, match="Input should be a valid datetime"):
        _markdown_string_to_werk(md)


def test_loading_md_werk_level_not_an_int() -> None:
    md = """[//]: # (werk v2)
# title

key | value
--- | ---
class | fix
component | core
date | 2022-12-12T11:08:08+00:00
level | asd
version | 2.0.0p7
compatible | yes
edition | cre

this is the `description` with some *formatting.*
"""
    with pytest.raises(WerkError, match="Expected level to be in"):
        _markdown_string_to_werk(md)


# wait for CMK-14587
# def test_loading_md_werk_component_not_known() -> None:
#     md = """[//]: # (werk v2)
# # title
#
# key | value
# --- | ---
# class | fix
# component | smth
# date | 2022-12-12T11:08:08+00:00
# level | 3
# version | 2.0.0p7
# compatible | yes
# edition | cre
#
# this is the `description` with some *formatting.*
# """
#     with pytest.raises(TypeError, match="Component smth not know. Choose from:"):
#         _markdown_string_to_werk(md)


def test_loading_md_werk_missing_newline() -> None:
    md = """[//]: # (werk v2)
# title
key | value
--- | ---
class | fix
component | smth
date | 2022-12-12T11:08:08+00:00
level | 3
version | 2.0.0p7
compatible | yes
edition | cre
this is the `description` with some *formatting.*
"""
    with pytest.raises(WerkError, match="Structure of markdown werk could not be detected"):
        _markdown_string_to_werk(md)


def test_loading_md_werk_formatting_in_title() -> None:
    md = """[//]: # (werk v2)
# test `werk` ***test*** [a](#href) asd

key | value
--- | ---
class | fix
component | core
date | 2022-12-12T11:08:08+00:00
level | 1
version | 2.0.0p7
compatible | yes
edition | cre

this is the `description` with some *formatting.*

# test `werk` ***test*** [a](#href)

"""
    with pytest.raises(WerkError, match="Werk title contains formatting, this is not allowed"):
        _markdown_string_to_werk(md)


@pytest.mark.parametrize(
    ("str_in", "str_out"),
    [
        ("a < b", "a < b"),
        ("&amp;", "&"),
        ("&", "&"),
        (r"\*bold*", "*bold*"),
        (r"&lt;br/>", "<br/>"),
    ],
)
def test_title_formatting(str_in: str, str_out: str) -> None:
    assert _format_title(str_in) == str_out


def test_loading_md_werk_tags_not_in_whitelist() -> None:
    md = """[//]: # (werk v2)
# test werk

key | value
--- | ---
class | fix
component | core
date | 2022-12-12T11:08:08+00:00
level | 1
version | 2.0.0p7
compatible | yes
edition | cre

this is <script>forbidden</script>

"""
    with pytest.raises(
        WerkError, match="Found tag <script> which is not in the list of allowed tags"
    ):
        _markdown_string_to_werk(md)


def test_loading_md_werk_tags_not_in_whitelist_nested() -> None:
    md = """[//]: # (werk v2)
# test werk

key | value
--- | ---
class | fix
component | core
date | 2022-12-12T11:08:08+00:00
level | 1
version | 2.0.0p7
compatible | yes
edition | cre

## this is <script>forbidden</script>

"""
    with pytest.raises(
        WerkError, match="Found tag <script> which is not in the list of allowed tags"
    ):
        _markdown_string_to_werk(md)


def test_loading_md_werk() -> None:
    md = """[//]: # (werk v2)
# test < werk

key | value
--- | ---
class | fix
component | core
date | 2022-12-12T11:08:08+00:00
level | 1
version | 2.0.0p7
compatible | yes
edition | cre

this is the `description` with some *italic* and __bold__ ***formatting***.

"""
    assert _markdown_string_to_werk(md).to_json_dict() == {
        "__version__": "2",
        "id": 1234,
        "class": "fix",
        "compatible": "yes",
        "component": "core",
        "date": "2022-12-12T11:08:08Z",
        "edition": "cre",
        "level": 1,
        "title": "test < werk",
        "version": "2.0.0p7",
        "description": "<p>this is the <code>description</code> with some <em>italic</em> and "
        "<strong>bold</strong> <strong><em>formatting</em></strong>.</p>",
    }


def test_parse_werkv1_missing_class() -> None:
    with pytest.raises(WerkError, match="class\n  Field required"):
        load_werk(file_content=WERK_V1_MISSING_CLASS, file_name="1234")


def test_loading_md_werk_without_body() -> None:
    md = """[//]: # (werk v2)
# test < werk

key | value
--- | ---
class | fix
component | core
date | 2022-12-12T11:08:08+00:00
level | 1
version | 2.0.0p7
compatible | yes
edition | cre
"""
    expected = {
        "__version__": "2",
        "id": 1234,
        "class": "fix",
        "compatible": "yes",
        "component": "core",
        "date": "2022-12-12T11:08:08Z",
        "edition": "cre",
        "level": 1,
        "title": "test < werk",
        "version": "2.0.0p7",
        "description": "",
    }
    assert _markdown_string_to_werk(md).to_json_dict() == expected
    assert _markdown_string_to_werk(md + "\n").to_json_dict() == expected
    assert _markdown_string_to_werk(md + "\n\n").to_json_dict() == expected
    assert _markdown_string_to_werk(md + "\n\n\n").to_json_dict() == expected
    assert _markdown_string_to_werk(md + "\n\n\n\n").to_json_dict() == expected


def test_loading_v3_werk() -> None:
    md = """[//]: # (werk v3)
# Oooooo weeeee

key | value
--- | ---
class | fix
component | core
date | 2025-12-22T14:19:19+00:00
level | 1
version | 2.5.0b1
compatible | yes
edition | community
"""
    expected = {
        "__version__": "3",
        "id": 1234,
        "class": "fix",
        "compatible": "yes",
        "component": "core",
        "date": "2025-12-22T14:19:19Z",
        "edition": "community",
        "level": 1,
        "title": "Oooooo weeeee",
        "version": "2.5.0b1",
        "description": "",
    }
    assert load_werk_v3(parse_werk_v3(md, werk_id="1234")).to_json_dict() == expected
