#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

import cmk.gui.watolib.host_attributes as attrs
from cmk.gui.config import active_config, Config
from cmk.gui.type_defs import CustomHostAttrSpec
from cmk.gui.watolib.host_attributes import all_host_attributes
from cmk.rulesets.v1 import Help, Title
from tests.testlib.common.repo import (
    is_pro_repo,
    is_ultimate_repo,
)

expected_attributes = {
    "additional_ipv4addresses": {
        "class_name": "ValueSpecAttribute",
        "depends_on_roles": [],
        "depends_on_tags": ["ip-v4"],
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
        "depends_on_tags": ["ip-v6"],
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
        "topic": "Network scan",
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
        "topic": "Network scan",
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
        if is_ultimate_repo()
        else {}
    ),
    **(
        {
            "metrics_association": {
                "depends_on_roles": [],
                "depends_on_tags": [],
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
        if is_ultimate_repo()
        else {}
    ),
    **(
        {
            "bake_agent_package": {
                "depends_on_roles": [],
                "depends_on_tags": [],
                "editable": True,
                "from_config": False,
                "show_in_folder": True,
                "show_in_form": False,
                "show_in_host_search": False,
                "show_in_table": False,
                "show_inherited_value": False,
                "topic": "Monitoring agents",
            },
        }
        if is_pro_repo()
        else {}
    ),
    **(
        {
            "relay": {
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
        }
        if is_ultimate_repo()
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
    "waiting_for_discovery": {
        "depends_on_roles": [],
        "depends_on_tags": [],
        "editable": False,
        "from_config": False,
        "show_in_folder": False,
        "show_in_form": False,
        "show_in_host_search": False,
        "show_in_table": False,
        "show_inherited_value": False,
        "topic": "Custom attributes",
    },
}


@pytest.mark.usefixtures("load_config")
def test_registered_host_attributes() -> None:
    names = all_host_attributes(
        active_config.wato_host_attrs, active_config.tags.get_tag_groups_by_topic()
    ).keys()
    assert sorted(expected_attributes.keys()) == sorted(names)

    for attr in all_host_attributes(
        active_config.wato_host_attrs, active_config.tags.get_tag_groups_by_topic()
    ).values():
        spec = expected_attributes[attr.name()]

        # assert spec["class_name"] == attr_class.__name__

        attr_topic = attr.topic()
        assert spec["topic"] == attr_topic.title, attr.name()
        assert spec["show_in_table"] == attr.show_in_table()
        assert spec["show_in_folder"] == attr.show_in_folder()
        assert spec["show_in_host_search"] == attr.show_in_host_search()
        assert spec["show_in_form"] == attr.show_in_form()
        assert spec["show_inherited_value"] == attr.show_inherited_value()
        assert spec["depends_on_tags"] == attr.depends_on_tags()
        assert spec["depends_on_roles"] == attr.depends_on_roles()
        assert spec["editable"] == attr.editable()
        assert spec["from_config"] == attr.from_config()


def test_legacy_register_rulegroup_with_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(attrs, "host_attribute_registry", attrs.HostAttributeRegistry())

    config = Config()
    assert "lat" not in all_host_attributes(
        config.wato_host_attrs, config.tags.get_tag_groups_by_topic()
    )

    attrs.declare_host_attribute(
        attrs.NagiosTextAttribute(
            "lat",
            "_LAT",
            "Latitude",
            "Latitude",
        ),
    )

    attr = all_host_attributes(config.wato_host_attrs, config.tags.get_tag_groups_by_topic())["lat"]
    assert isinstance(attr, attrs.ABCHostAttributeNagiosText)
    assert attr.show_in_table() is True
    assert attr.show_in_folder() is True
    assert attr.show_in_host_search() is True
    assert attr.show_in_form() is True
    assert attr.topic().ident == attrs.HOST_ATTRIBUTE_TOPIC_BASIC_SETTINGS.ident
    assert attr.depends_on_tags() == []
    assert attr.depends_on_roles() == []
    assert attr.editable() is True
    assert attr.show_inherited_value() is True
    assert attr.may_edit() is True
    assert attr.from_config() is False


def test_legacy_register_rulegroup_without_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(attrs, "host_attribute_registry", attrs.HostAttributeRegistry())

    config = Config()
    assert "lat" not in all_host_attributes(
        config.wato_host_attrs, config.tags.get_tag_groups_by_topic()
    )

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

    topic = attrs.host_attribute_topic_registry["xyz"]
    assert topic.title == "Xyz"
    assert topic.sort_index == 80

    attr = all_host_attributes(config.wato_host_attrs, config.tags.get_tag_groups_by_topic())["lat"]
    assert isinstance(attr, attrs.ABCHostAttributeNagiosText)
    assert attr.show_in_table() is False
    assert attr.show_in_folder() is False
    assert attr.show_in_host_search() is False
    assert attr.show_in_form() is False

    assert attr.topic().title == "Xyz"
    assert attr.depends_on_tags() == ["xxx"]
    assert attr.depends_on_roles() == ["guest"]
    assert attr.editable() is False
    assert attr.show_inherited_value() is False
    assert attr.may_edit() is False
    assert attr.from_config() is True


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
def test_host_attribute_topics(for_what: str) -> None:
    assert attrs.sorted_host_attribute_topics(
        all_host_attributes(
            active_config.wato_host_attrs, active_config.tags.get_tag_groups_by_topic()
        ),
        for_what=for_what,
        new=False,
    ) == [
        ("basic", "Basic settings"),
        ("address", "Network address"),
        ("monitoring_agents", "Monitoring agents"),
        ("custom_attributes", "Custom attributes"),
        ("management_board", "Management board"),
        ("meta_data", "Creation / Locking"),
    ]


@pytest.mark.usefixtures("load_config")
def test_host_attribute_topics_for_folders() -> None:
    assert attrs.sorted_host_attribute_topics(
        all_host_attributes(
            active_config.wato_host_attrs, active_config.tags.get_tag_groups_by_topic()
        ),
        "folder",
        new=False,
    ) == [
        ("basic", "Basic settings"),
        ("address", "Network address"),
        ("monitoring_agents", "Monitoring agents"),
        ("custom_attributes", "Custom attributes"),
        ("network_scan", "Network scan"),
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
def test_host_attributes(for_what: str, new: bool) -> None:
    topics = {
        "basic": [
            "alias",
            "site",
            *(["relay"] if is_ultimate_repo() else []),
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
            *(("cmk_agent_connection", "bake_agent_package") if is_pro_repo() else ()),
            "tag_snmp_ds",
            "snmp_community",
            "tag_piggyback",
            *(("metrics_association",) if is_ultimate_repo() else ()),
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
            "waiting_for_discovery",
        ],
    }

    if for_what == "folder":
        topics["network_scan"] = [
            "network_scan",
            "network_scan_result",
        ]

    if new:
        del topics["meta_data"]

    host_attributes = all_host_attributes(
        active_config.wato_host_attrs, active_config.tags.get_tag_groups_by_topic()
    )
    current_topics = attrs.sorted_host_attribute_topics(host_attributes, for_what, new)

    assert sorted(topics.keys()) == sorted(dict(current_topics).keys())

    for topic_id, _title in current_topics:
        names = [a.name() for a in attrs.sorted_host_attributes_by_topic(host_attributes, topic_id)]
        assert names == topics.get(topic_id, []), (
            "Expected attributes not specified for topic %r" % topic_id
        )


def test_custom_host_attribute_has_form_spec() -> None:
    custom_host_attribute = CustomHostAttrSpec(
        type="TextAscii",
        name="custom_attr",
        title="Custom Attribute",
        help="Custom attribute for testing",
        topic="Custom topic",
        add_custom_macro=False,
        show_in_table=None,
    )

    all_attributes = all_host_attributes([custom_host_attribute], [])

    attr = all_attributes["custom_attr"]
    assert isinstance(attr, attrs.ABCHostAttributeValueSpec)
    fs = attr.form_spec()
    assert fs.title == Title("Custom Attribute")
    assert fs.help_text == Help("Custom attribute for testing")
