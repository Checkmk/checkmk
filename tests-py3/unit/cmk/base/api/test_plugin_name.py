#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.api import PluginName


@pytest.mark.parametrize("str_name",
                         ['', 23] + list("\"'^°!²³§$½¬%&/{([])}=?ß\\'`*+~#-.:,;ÜÖÄüöä<>|"))
def test_invalid_plugin_name(str_name):
    with pytest.raises((TypeError, ValueError)):
        PluginName(str_name)


def test_forbidden_plugin_name():
    with pytest.raises(ValueError):
        PluginName("Foo", forbidden_names=["Foo", "Bar"])


def test_plugin_name_repr():
    assert repr(PluginName("Margo")) == "PluginName('Margo')"


def test_plugin_name_str():
    assert str(PluginName("Margo")) == 'Margo'


def test_plugin_name_equal():
    assert PluginName("Stuart") == PluginName("Stuart")
    with pytest.raises(TypeError):
        _ = PluginName("Stuart") == "Stuart"


def test_plugin_name_as_key():
    plugin_dict = {
        PluginName("Stuart"): None,
    }
    assert PluginName("Stuart") in plugin_dict


def test_plugin_name_sort():
    plugin_dict = {
        PluginName("Stuart"): None,
        PluginName("Bob"): None,
        PluginName("Dave"): None,
    }

    assert sorted(plugin_dict) == [PluginName("Bob"), PluginName("Dave"), PluginName("Stuart")]
