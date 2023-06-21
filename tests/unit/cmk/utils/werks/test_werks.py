#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.werks.werk import WerkError
from cmk.utils.werks.werkv1 import load_werk_v1
from cmk.utils.werks.werkv2 import load_werk_v2, RawWerkV2

WERK = {
    "class": "fix",
    "component": "core",
    "date": 0,
    "level": 1,
    "title": "Some Title",
    "version": "v42.0.0p7",
    "compatible": "comp",
    "edition": "cre",
    "description": [],
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


def get_werk_v1(werk_dict: Mapping[str, Any]) -> str:
    def generate():
        for key, value in werk_dict.items():
            if key == "description":
                continue
            yield f"{key}: {value}"
        assert isinstance(werk_dict["description"], list)
        yield from ("{line}" for line in werk_dict["description"])

    return "\n".join(generate())


def test_werk_loading(tmp_path: Path) -> None:
    loaded_data = load_werk_v1(get_werk_v1(WERK), 1).to_json_dict()
    # loaded_data contains id, and other default values, WERK does not have
    for key, value in WERK.items():
        assert loaded_data[key] == value


def test_werk_loading_missing_field(tmp_path: Path) -> None:
    bad_werk = dict(WERK)
    bad_werk.pop("class")
    with pytest.raises(MKGeneralException, match="class\n  field required"):
        load_werk_v1(get_werk_v1(bad_werk), 1)


def test_werk_loading_unknown_field(tmp_path: Path) -> None:
    bad_werk = dict(WERK)
    bad_werk["foo"] = "bar"
    with pytest.raises(
        MKGeneralException,
        match="validation error for RawWerkV1\nfoo\n  extra fields not permitted",
    ):
        load_werk_v1(get_werk_v1(bad_werk), 1)


def _markdown_string_to_werk(md: str) -> RawWerkV2:
    return load_werk_v2(md, werk_id="1234")


def test_loading_md_werk_missing_header() -> None:
    with pytest.raises(WerkError, match="Markdown formatted werks need to start with"):
        _markdown_string_to_werk("")


def test_loading_md_werk_missing_title() -> None:
    md = """[//]: # (werk v2)
this is the `description` with some *formatting.*
"""
    with pytest.raises(
        WerkError, match="First element after the header needs to be the title as a h1 headline."
    ):
        _markdown_string_to_werk(md)


def test_loading_md_werk_missing_table() -> None:
    with pytest.raises(WerkError, match="Expected a table after the title, found 'p'"):
        md = """[//]: # (werk v2)
# title

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
    with pytest.raises(WerkError, match="field required"):
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
    with pytest.raises(WerkError, match="invalid datetime format"):
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


def test_loading_md_werk_component_not_known() -> None:
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
    with pytest.raises(WerkError, match="Component smth not know. Choose from:"):
        _markdown_string_to_werk(md)


def test_loading_md_werk() -> None:
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

this is the `description` with some *formatting.*

"""
    assert _markdown_string_to_werk(md).to_json_dict() == {
        "__version__": "2",
        "id": 1234,
        "class": "fix",
        "compatible": "yes",
        "component": "core",
        "date": "2022-12-12T11:08:08+00:00",
        "edition": "cre",
        "level": 1,
        "title": "test werk",
        "version": "2.0.0p7",
        "description": "<p>this is the <code>description</code> with some <em>formatting.</em></p>",
    }


def test_parse_werkv1_missing_class() -> None:
    with pytest.raises(WerkError, match="class\n  field required"):
        assert load_werk_v1(WERK_V1_MISSING_CLASS, werk_id=1234)
