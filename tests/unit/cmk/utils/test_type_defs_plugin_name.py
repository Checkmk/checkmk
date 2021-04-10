#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.utils.type_defs import CheckPluginName, SectionName


@pytest.mark.parametrize("str_name",
                         ['', 23] + list("\"'^°!²³§$½¬%&/{([])}=?ß\\'`*+~#-.:,;ÜÖÄüöä<>|"))
def test_invalid_plugin_name(str_name):
    with pytest.raises((TypeError, ValueError)):
        CheckPluginName(str_name)


def test_plugin_name_repr():
    assert repr(CheckPluginName("Margo")) == "CheckPluginName('Margo')"


def test_plugin_name_str():
    assert str(CheckPluginName("Margo")) == 'Margo'


def test_plugin_name_equal():
    assert CheckPluginName("Stuart") == CheckPluginName("Stuart")
    with pytest.raises(TypeError):
        _ = CheckPluginName("Stuart") == "Stuart"


def test_plugin_name_as_key():
    plugin_dict = {
        CheckPluginName("Stuart"): None,
    }
    assert CheckPluginName("Stuart") in plugin_dict


def test_plugin_name_sort():
    plugin_dict = {
        CheckPluginName("Stuart"): None,
        CheckPluginName("Bob"): None,
        CheckPluginName("Dave"): None,
    }

    assert sorted(plugin_dict) == [
        CheckPluginName("Bob"),
        CheckPluginName("Dave"),
        CheckPluginName("Stuart")
    ]


def test_cross_class_comparison_fails():
    with pytest.raises(TypeError):
        _ = CheckPluginName("foo") == SectionName("foo")
