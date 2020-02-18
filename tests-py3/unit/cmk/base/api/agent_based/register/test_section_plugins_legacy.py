# encoding: utf-8
# pylint: disable=protected-access

import pytest  # type: ignore[import]

from cmk.base.check_api_utils import Service
from cmk.base.discovered_labels import DiscoveredHostLabels, HostLabel
import cmk.base.api.agent_based.register.section_plugins_legacy as section_plugins_legacy
import cmk.base.api.agent_based.register.section_plugins as section_plugins


@pytest.mark.parametrize("name_in, name_out", [
    ("foo.bar", "foo"),
    ("foobar", "foobar"),
])
def test_get_section_name(name_in, name_out):
    assert name_out == section_plugins_legacy.get_section_name(name_in)


def old_school_parse_function(_info):
    return {"what": "ever"}


HOST_LABELS = [
    HostLabel("foo", "bar"),
    HostLabel("gee", "boo"),
    HostLabel("heinz", "hirn"),
]


def old_school_discover_function(parsed_extra):
    _parsed, _extra_section = parsed_extra
    yield "item1", {"discoverd_param": 42}
    yield HOST_LABELS[0]
    yield Service(
        "item2",
        {},
        host_labels=DiscoveredHostLabels(*HOST_LABELS[1:]),
    )
    yield "item3", "{'how_bad_is_this': 100}"


@pytest.mark.parametrize("creator_func", [
    section_plugins_legacy._create_agent_parse_function,
    lambda x: section_plugins_legacy._create_snmp_parse_function(x, lambda x: x),
])
def test_create_parse_function(creator_func):
    compliant_parse_function = creator_func(old_school_parse_function)

    with pytest.raises(ValueError):
        # raises b/c of wrong signature!
        section_plugins._validate_parse_function(old_school_parse_function)

    section_plugins._validate_parse_function(compliant_parse_function)

    assert old_school_parse_function([]) == compliant_parse_function([])


def test_create_host_label_function():
    host_label_function = section_plugins_legacy._create_host_label_function(
        old_school_discover_function, lambda x: x, ["some_extra_section"])

    section_plugins._validate_host_label_function(host_label_function)

    # check that we can pass an un-unpackable argument now!
    actual_labels = list(host_label_function({"parse": "result"}))

    assert actual_labels == HOST_LABELS
