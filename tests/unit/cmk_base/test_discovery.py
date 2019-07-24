# encoding: utf-8
# pylint: disable=redefined-outer-name

import pytest  # type: ignore

import cmk_base.discovery as discovery
from cmk_base.check_api_utils import Service
from cmk_base.discovered_labels import (
    DiscoveredServiceLabelsOfHost,
    DiscoveredServiceLabels,
    ServiceLabel,
)


def test_discovered_service_init():
    s = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None")
    assert s.check_plugin_name == "abc"
    assert s.item == u"Item"
    assert s.description == u"ABC Item"
    assert s.parameters_unresolved == "None"
    assert s.service_labels == {}

    s = discovery.DiscoveredService("abc", u"Item", u"ABC Item", "None", {u"läbel": u"lübel"})
    assert s.service_labels == {u"läbel": u"lübel"}

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


def test_discovered_service_labels_of_host():
    def discovery_function():
        yield Service(item=u"itäm1",
                      parameters=None,
                      service_labels=DiscoveredServiceLabels(ServiceLabel(u"bla", u"blüb"),))
        yield Service(item=u"itäm1",
                      parameters=None,
                      service_labels=DiscoveredServiceLabels(ServiceLabel(u"bla", u"bläb"),))
        yield Service(item=u"itäm2",
                      parameters=None,
                      service_labels=DiscoveredServiceLabels(ServiceLabel(u"blä", u"bläb"),))

    labels = DiscoveredServiceLabelsOfHost()

    for service in discovery_function():
        labels.add_labels(service.item, service.service_labels)

    assert labels.to_dict() == {
        u"itäm1": {
            u"bla": u"bläb",
        },
        u"itäm2": {
            u"blä": u"bläb",
        },
    }
