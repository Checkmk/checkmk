#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.werks import parse_werk
from cmk.werks.format import format_as_werk_v1, format_as_werk_v2
from cmk.werks.parse import parse_werk_v2, WerkV2ParseResult


def test_markdown_parse_roundtrip() -> None:
    md = """[//]: # (werk v2)
# test < werk

key        | value
---------- | ---
class      | fix
component  | core
date       | 2022-12-12T11:08:08+00:00
level      | 1
version    | 2.0.0p7
compatible | yes
edition    | cre

this is the `description` with some *italic* and __bold__ ***formatting***.
"""
    parsed = parse_werk_v2(md, "123")

    # change version and expect another version in result
    parsed.metadata["version"] = "99.99.99p99"
    content = format_as_werk_v2(parsed)
    assert (
        content
        == """[//]: # (werk v2)
# test < werk

key        | value
---------- | ---
class      | fix
component  | core
date       | 2022-12-12T11:08:08+00:00
level      | 1
version    | 99.99.99p99
compatible | yes
edition    | cre

this is the `description` with some *italic* and __bold__ ***formatting***.
"""
    )

    # change version back, expect exactly the same result as the input
    parsed.metadata["version"] = "2.0.0p7"
    assert format_as_werk_v2(parsed) == md


def test_nowiki_parse_roundtrip() -> None:
    """
    for picking werks from master branch to older branches, we need the ability to write v1 werks
    """
    text = """Title: APT: Fix service discovery when getting unexpected output from apt
Level: 1
Component: checks
Compatible: incomp
Edition: cre
State: unknown
Class: fix
Version: 2.0.0i1
Date: 1569225628

some description and

LI: a list...
LI: ...with...
LI: ...entries!

"""
    parsed = parse_werk(text, "1234")
    assert parsed.metadata == {
        "id": "1234",
        "class": "fix",
        "compatible": "no",
        "component": "checks",
        "date": "2019-09-23T08:00:28+00:00",
        "edition": "cre",
        "level": "1",
        "title": "APT: Fix service discovery when getting unexpected output from apt",
        "version": "2.0.0i1",
    }
    assert (
        parsed.description
        == """some description and

* a list...
* ...with...
* ...entries!"""
    )

    parsed.metadata["version"] = "77.77.77p77"

    assert isinstance(parsed, WerkV2ParseResult)
    content = format_as_werk_v1(parsed)
    assert (
        content
        == """Title: APT: Fix service discovery when getting unexpected output from apt
Class: fix
Compatible: incomp
Component: checks
Date: 1569225628
Edition: cre
Level: 1
Version: 77.77.77p77

some description and

LI: a list...
LI: ...with...
LI: ...entries!
"""
    )
