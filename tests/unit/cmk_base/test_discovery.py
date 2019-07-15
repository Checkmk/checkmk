# pylint: disable=redefined-outer-name

import pytest  # type: ignore

import cmk_base.discovery as discovery


def test_discovered_service_init():
    s = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None")
    assert s.check_plugin_name == "abc"
    assert s.item == u"Item"
    assert s.description == u"ABC Item"
    assert s.paramstr == "None"

    with pytest.raises(AttributeError):
        s.xyz = "abc"  # pylint: disable=assigning-non-slot


def test_discovered_service_eq():
    s1 = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None")
    s2 = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None")
    s3 = discovery.DiscoveredService("xyz", u"Item", u"ABC Item", "None")
    s4 = discovery.DiscoveredService("abc", u"Xtem", u"ABC Item", "None")
    s5 = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "[]")

    assert s1 == s1
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
