#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
import pytest

from cmk.utils.version import is_plus_edition

import cmk.gui.watolib.host_attributes as attrs

expected_attributes = {
    "additional_ipv4addresses": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Network address",
    },
    "additional_ipv6addresses": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Network address",
    },
    "alias": {
        "class_name": "NagiosTextAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": True,
        "show_inherited_value": True,
        "topic": "Basic settings",
    },
    "contactgroups": {
        "class_name": "ContactGroupsAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Basic settings",
    },
    "ipaddress": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": ["ip-v4"],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": True,
        "show_inherited_value": True,
        "topic": "Network address",
    },
    "ipv6address": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": ["ip-v6"],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": True,
        "show_inherited_value": True,
        "topic": "Network address",
    },
    "locked_attributes": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Creation / Locking",
    },
    "locked_by": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Creation / Locking",
    },
    "management_address": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Management board",
    },
    "management_ipmi_credentials": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Management board",
    },
    "management_protocol": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Management board",
    },
    "management_snmp_community": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Management board",
    },
    "meta_data": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Creation / Locking",
    },
    "network_scan": {
        "class_name": "HostAttributeNetworkScan",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": False,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Network Scan",
    },
    "network_scan_result": {
        "class_name": "NetworkScanResultAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": False,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Network Scan",
    },
    "parents": {
        "class_name": "ParentsAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": True,
        "show_inherited_value": True,
        "topic": "Basic settings",
    },
    "site": {
        "class_name": "SiteAttribute",
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": True,
        "show_inherited_value": True,
        "topic": "Basic settings",
    },
    "snmp_community": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": ["snmp"],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Monitoring agents",
    },
    "tag_address_family": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": True,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Network address",
    },
    "tag_agent": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": True,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Monitoring agents",
    },
    **(
        {
            "cmk_agent_connection": {
                "depends_on_roles": [],
                "depends_on_tags": ["checkmk-agent"],
                "editable": True,
                "from_config": False,
                "show_in_folder": True,
                "show_in_form": True,
                "show_in_host_search": True,
                "show_in_table": False,
                "show_inherited_value": True,
                "topic": "Monitoring agents",
            },
        }
        if is_plus_edition()
        else {}
    ),
    "tag_snmp_ds": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": True,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Monitoring agents",
    },
    "tag_piggyback": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": True,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Monitoring agents",
    },
    "labels": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": True,
        "from_config": False,
        "show_in_folder": True,
        "show_in_form": True,
        "show_in_host_search": True,
        "show_in_table": False,
        "show_inherited_value": True,
        "topic": "Custom attributes",
    },
    "inventory_failed": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": False,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Creation / Locking",
    },
}


def test_registered_host_attributes(load_config) -> None:
    names = attrs.host_attribute_registry.keys()
    assert sorted(expected_attributes.keys()) == sorted(names)

    for attr_class in attrs.host_attribute_registry.values():
        attr = attr_class()
        spec = expected_attributes[attr.name()]

        # assert spec["class_name"] == attr_class.__name__

        attr_topic_class = attr.topic()
        assert spec["topic"] == attr_topic_class().title, attr.name()
        assert spec["show_in_table"] == attr.show_in_table()
        assert spec["show_in_folder"] == attr.show_in_folder(), attr_class
        assert spec["show_in_host_search"] == attr.show_in_host_search()
        assert spec["show_in_form"] == attr.show_in_form()
        assert spec["show_inherited_value"] == attr.show_inherited_value()
        assert spec["depends_on_tags"] == attr.depends_on_tags()
        assert spec["depends_on_roles"] == attr.depends_on_roles()
        assert spec["editable"] == attr.editable()
        assert spec["from_config"] == attr.from_config()


def test_legacy_register_rulegroup_with_defaults(monkeypatch) -> None:
    monkeypatch.setattr(attrs, "host_attribute_registry", attrs.HostAttributeRegistry())

    assert "lat" not in attrs.host_attribute_registry

    attrs.declare_host_attribute(
        attrs.NagiosTextAttribute(
            "lat",
            "_LAT",
            "Latitude",
            "Latitude",
        ),
    )

    attr = attrs.host_attribute_registry["lat"]()
    assert isinstance(attr, attrs.ABCHostAttributeNagiosText)
    assert attr.show_in_table() is True
    assert attr.show_in_folder() is True
    assert attr.show_in_host_search() is True
    assert attr.show_in_form() is True
    assert attr.topic() == attrs.HostAttributeTopicBasicSettings
    assert attr.depends_on_tags() == []
    assert attr.depends_on_roles() == []
    assert attr.editable() is True
    assert attr.show_inherited_value() is True
    assert attr.may_edit() is True
    assert attr.from_config() is False


def test_legacy_register_rulegroup_without_defaults(monkeypatch) -> None:
    monkeypatch.setattr(attrs, "host_attribute_registry", attrs.HostAttributeRegistry())

    assert "lat" not in attrs.host_attribute_registry

    attrs.declare_host_attribute(
        attrs.NagiosTextAttribute(
            "lat",
            "_LAT",
            "Latitude",
            "Latitude",
        ),
        show_in_table=False,
        show_in_folder=False,
        show_in_host_search=False,
        topic="Xyz",
        show_in_form=False,
        depends_on_tags=["xxx"],
        depends_on_roles=["guest"],
        editable=False,
        show_inherited_value=False,
        may_edit=lambda: False,
        from_config=True,
    )

    topic = attrs.host_attribute_topic_registry["xyz"]()
    assert topic.title == "Xyz"
    assert topic.sort_index == 80

    attr = attrs.host_attribute_registry["lat"]()
    assert isinstance(attr, attrs.ABCHostAttributeNagiosText)
    assert attr.show_in_table() is False
    assert attr.show_in_folder() is False
    assert attr.show_in_host_search() is False
    assert attr.show_in_form() is False

    assert attr.topic()().title == "Xyz"
    assert attr.depends_on_tags() == ["xxx"]
    assert attr.depends_on_roles() == ["guest"]
    assert attr.editable() is False
    assert attr.show_inherited_value() is False
    assert attr.may_edit() is False
    assert attr.from_config() is True


@pytest.mark.parametrize(
    "old,new",
    [
        ("Basic settings", "basic"),
        ("Management board", "management_board"),
        ("Custom attributes", "custom_attributes"),
        ("Eigene Attribute", "custom_attributes"),
        ("xyz_unknown", "custom_attributes"),
    ],
)
def test_custom_host_attribute_transform(old, new) -> None:
    attributes = [
        {
            "add_custom_macro": True,
            "help": "",
            "name": "attr1",
            "show_in_table": True,
            "title": "Attribute 1",
            "topic": old,
            "type": "TextAscii",
        }
    ]

    transformed_attributes = attrs.transform_pre_16_host_topics(attributes)
    assert transformed_attributes[0]["topic"] == new


@pytest.mark.usefixtures("load_config")
@pytest.mark.parametrize(
    "for_what",
    [
        "host",
        "cluster",
        "host_search",
        "bulk",
    ],
)
def test_host_attribute_topics(for_what) -> None:
    assert attrs.get_sorted_host_attribute_topics(for_what=for_what, new=False) == [
        ("basic", "Basic settings"),
        ("address", "Network address"),
        ("monitoring_agents", "Monitoring agents"),
        ("custom_attributes", "Custom attributes"),
        ("management_board", "Management board"),
        ("meta_data", "Creation / Locking"),
    ]


@pytest.mark.usefixtures("load_config")
def test_host_attribute_topics_for_folders() -> None:
    assert attrs.get_sorted_host_attribute_topics("folder", new=False) == [
        ("basic", "Basic settings"),
        ("address", "Network address"),
        ("monitoring_agents", "Monitoring agents"),
        ("custom_attributes", "Custom attributes"),
        ("network_scan", "Network Scan"),
        ("management_board", "Management board"),
        ("meta_data", "Creation / Locking"),
    ]


@pytest.mark.usefixtures("load_config")
@pytest.mark.parametrize(
    "for_what",
    [
        "host",
        "cluster",
        "folder",
        "host_search",
        "bulk",
    ],
)
@pytest.mark.parametrize("new", [True, False])
def test_host_attributes(for_what, new) -> None:
    topics = {
        "basic": [
            "alias",
            "site",
            "contactgroups",
            "parents",
        ],
        "address": [
            "tag_address_family",
            "ipaddress",
            "ipv6address",
            "additional_ipv4addresses",
            "additional_ipv6addresses",
        ],
        "monitoring_agents": [
            "tag_agent",
            *(("cmk_agent_connection",) if is_plus_edition() else ()),
            "tag_snmp_ds",
            "snmp_community",
            "tag_piggyback",
        ],
        "management_board": [
            "management_protocol",
            "management_address",
            "management_snmp_community",
            "management_ipmi_credentials",
        ],
        "meta_data": [
            "meta_data",
            "locked_by",
            "locked_attributes",
            "inventory_failed",
        ],
        "custom_attributes": [
            "labels",
        ],
    }

    if for_what == "folder":
        topics["network_scan"] = [
            "network_scan",
            "network_scan_result",
        ]

    if new:
        del topics["meta_data"]

    current_topics = attrs.get_sorted_host_attribute_topics(for_what, new)

    assert sorted(topics.keys()) == sorted(dict(current_topics).keys())

    for topic_id, _title in current_topics:
        names = [a.name() for a in attrs.get_sorted_host_attributes_by_topic(topic_id)]
        assert names == topics.get(topic_id, []), (
            "Expected attributes not specified for topic %r" % topic_id
        )
