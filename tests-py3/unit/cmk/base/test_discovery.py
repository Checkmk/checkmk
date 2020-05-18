#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

import cmk.base.discovery as discovery
from cmk.base.discovered_labels import ServiceLabel, DiscoveredServiceLabels


def test_discovered_service_init():
    s = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None")
    assert s.check_plugin_name == "abc"
    assert s.item == u"Item"
    assert s.description == u"ABC Item"
    assert s.parameters_unresolved == "None"
    assert s.service_labels.to_dict() == {}

    s = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None",
                                    DiscoveredServiceLabels(ServiceLabel(u"läbel", u"lübel")))
    assert s.service_labels.to_dict() == {u"läbel": u"lübel"}

    with pytest.raises(AttributeError):
        s.xyz = "abc"  # type: ignore[attr-defined] # pylint: disable=assigning-non-slot


def test_discovered_service_eq():
    s1 = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None")
    s2 = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None")
    s3 = discovery.DiscoveredService("xyz", u"Item", u"ABC Item", "None")
    s4 = discovery.DiscoveredService("abc", u"Xtem", u"ABC Item", "None")
    s5 = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "[]")

    assert s1 == s1  # pylint: disable=comparison-with-itself
    assert s1 == s2
    assert s1 != s3
    assert s1 != s4
    assert s1 == s5

    assert s1 in [s1]
    assert s1 in [s2]
    assert s1 not in [s3]
    assert s1 not in [s4]
    assert s1 in [s5]

    assert s1 in {s1}
    assert s1 in {s2}
    assert s1 not in {s3}
    assert s1 not in {s4}
    assert s1 in {s5}
