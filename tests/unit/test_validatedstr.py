#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import pickle
from collections.abc import Container

import pytest

from cmk.utils.sectionname import SectionName
from cmk.utils.validatedstr import ValidatedString


class VS(ValidatedString):
    @classmethod
    def exceptions(cls) -> Container[str]:
        return super().exceptions()


@pytest.mark.parametrize(
    "str_name", ["", 23] + list("\"'^°!²³§$½¬%&/{([])}=?ß\\'`*+~#-.:,;ÜÖÄüöä<>|")
)
def test_invalid_plugin_name(str_name) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises((TypeError, ValueError)):
        VS(str_name)


def test_plugin_name_repr() -> None:
    assert repr(VS("Margo")) == "VS('Margo')"


def test_plugin_name_str() -> None:
    assert str(VS("Margo")) == "Margo"


def test_plugin_name_equal() -> None:
    assert VS("Stuart") == VS("Stuart")
    with pytest.raises(TypeError):
        _ = VS("Stuart") == "Stuart"


def test_copyability() -> None:
    section_name = SectionName("SectionName")
    assert section_name == copy.copy(section_name)
    assert section_name == copy.deepcopy(section_name)
    assert section_name == pickle.loads(pickle.dumps(section_name))


def test_plugin_name_as_key() -> None:
    plugin_dict = {
        VS("Stuart"): None,
    }
    assert VS("Stuart") in plugin_dict


def test_plugin_name_sort() -> None:
    plugin_dict = {
        VS("Stuart"): None,
        VS("Bob"): None,
        VS("Dave"): None,
    }

    assert sorted(plugin_dict) == [
        VS("Bob"),
        VS("Dave"),
        VS("Stuart"),
    ]


def test_cross_class_comparison_fails() -> None:
    with pytest.raises(TypeError):
        _ = VS("foo") == SectionName("foo")
