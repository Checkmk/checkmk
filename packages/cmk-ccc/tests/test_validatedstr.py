#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import pickle

import pytest

from cmk.ccc.validatedstr import ValidatedString


class SectionName(ValidatedString): ...


@pytest.mark.parametrize(
    "str_name", ["", 23] + list("\"'^°!²³§$½¬%&/{([])}=?ß\\'`*+~#-.:,;ÜÖÄüöä<>|")
)
def test_invalid_plugin_name(str_name: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        ValidatedString(str_name)  # type: ignore[arg-type]


def test_plugin_name_repr() -> None:
    assert repr(ValidatedString("Margo")) == "ValidatedString('Margo')"


def test_plugin_name_str() -> None:
    assert str(ValidatedString("Margo")) == "Margo"


def test_plugin_name_equal() -> None:
    assert ValidatedString("Stuart") == ValidatedString("Stuart")
    with pytest.raises(TypeError):
        _ = ValidatedString("Stuart") == "Stuart"


def test_copyability() -> None:
    section_name = SectionName("SectionName")
    assert section_name == copy.copy(section_name)
    assert section_name == copy.deepcopy(section_name)
    assert section_name == pickle.loads(pickle.dumps(section_name))  # nosec


def test_plugin_name_as_key() -> None:
    plugin_dict = {
        ValidatedString("Stuart"): None,
    }
    assert ValidatedString("Stuart") in plugin_dict


def test_plugin_name_sort() -> None:
    plugin_dict = {
        ValidatedString("Stuart"): None,
        ValidatedString("Bob"): None,
        ValidatedString("Dave"): None,
    }

    assert sorted(plugin_dict) == [
        ValidatedString("Bob"),
        ValidatedString("Dave"),
        ValidatedString("Stuart"),
    ]


def test_cross_class_comparison_fails() -> None:
    with pytest.raises(TypeError):
        _ = ValidatedString("foo") == SectionName("foo")
