import pytest  # type: ignore

# Triggers plugin loading of plugins.wato which registers all the plugins
import cmk.gui.wato  # pylint: disable=unused-import
import cmk.gui.watolib.host_attributes as attrs


@pytest.fixture()
def load_plugins(register_builtin_html):
    attrs.update_config_based_host_attributes()


expected_attributes = {
    'additional_ipv4addresses': {
        'class_name': 'ValueSpecAttribute',
        'depends_on_roles': [],
        'depends_on_tags': ['ip-v4'],
        'editable': True,
        'from_config': False,
        'show_in_folder': False,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': False,
        'show_inherited_value': True,
        'topic': u'Address'
    },
    'additional_ipv6addresses': {
        'class_name': 'ValueSpecAttribute',
        'depends_on_roles': [],
        'depends_on_tags': ['ip-v6'],
        'editable': True,
        'from_config': False,
        'show_in_folder': False,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': False,
        'show_inherited_value': True,
        'topic': u'Address'
    },
    'alias': {
        'class_name': 'NagiosTextAttribute',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': True,
        'from_config': False,
        'show_in_folder': False,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': True,
        'show_inherited_value': True,
        'topic': u'Basic settings',
    },
    'contactgroups': {
        'class_name': 'ContactGroupsAttribute',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': True,
        'from_config': False,
        'show_in_folder': True,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': False,
        'show_inherited_value': True,
        'topic': u'Basic settings',
    },
    'ipaddress': {
        'class_name': 'ValueSpecAttribute',
        'depends_on_roles': [],
        'depends_on_tags': ['ip-v4'],
        'editable': True,
        'from_config': False,
        'show_in_folder': False,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': True,
        'show_inherited_value': True,
        'topic': u'Address'
    },
    'ipv6address': {
        'class_name': 'ValueSpecAttribute',
        'depends_on_roles': [],
        'depends_on_tags': ['ip-v6'],
        'editable': True,
        'from_config': False,
        'show_in_folder': False,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': True,
        'show_inherited_value': True,
        'topic': u'Address'
    },
    'locked_attributes': {
        'class_name': 'ValueSpecAttribute',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': False,
        'from_config': False,
        'show_in_folder': False,
        'show_in_form': True,
        'show_in_host_search': False,
        'show_in_table': False,
        'show_inherited_value': False,
        'topic': u'Basic settings',
    },
    'locked_by': {
        'class_name': 'ValueSpecAttribute',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': False,
        'from_config': False,
        'show_in_folder': False,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': False,
        'show_inherited_value': False,
        'topic': u'Basic settings',
    },
    'management_address': {
        'class_name': 'ValueSpecAttribute',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': True,
        'from_config': False,
        'show_in_folder': False,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': False,
        'show_inherited_value': True,
        'topic': u'Management Board'
    },
    'management_ipmi_credentials': {
        'class_name': 'ValueSpecAttribute',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': True,
        'from_config': False,
        'show_in_folder': True,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': False,
        'show_inherited_value': True,
        'topic': u'Management Board'
    },
    'management_protocol': {
        'class_name': 'ValueSpecAttribute',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': True,
        'from_config': False,
        'show_in_folder': True,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': False,
        'show_inherited_value': True,
        'topic': u'Management Board'
    },
    'management_snmp_community': {
        'class_name': 'ValueSpecAttribute',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': True,
        'from_config': False,
        'show_in_folder': True,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': False,
        'show_inherited_value': True,
        'topic': u'Management Board'
    },
    'network_scan': {
        'class_name': 'HostAttributeNetworkScan',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': True,
        'from_config': False,
        'show_in_folder': True,
        'show_in_form': False,
        'show_in_host_search': False,
        'show_in_table': False,
        'show_inherited_value': False,
        'topic': u'Network Scan'
    },
    'network_scan_result': {
        'class_name': 'NetworkScanResultAttribute',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': False,
        'from_config': False,
        'show_in_folder': True,
        'show_in_form': False,
        'show_in_host_search': False,
        'show_in_table': False,
        'show_inherited_value': False,
        'topic': u'Network Scan'
    },
    'parents': {
        'class_name': 'ParentsAttribute',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': True,
        'from_config': False,
        'show_in_folder': True,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': True,
        'show_inherited_value': True,
        'topic': u'Basic settings',
    },
    'site': {
        'class_name': 'SiteAttribute',
        'depends_on_roles': [],
        'depends_on_tags': [],
        'editable': True,
        'from_config': False,
        'show_in_folder': True,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': True,
        'show_inherited_value': True,
        'topic': u'Basic settings',
    },
    'snmp_community': {
        'class_name': 'ValueSpecAttribute',
        'depends_on_roles': [],
        'depends_on_tags': ['snmp'],
        'editable': True,
        'from_config': False,
        'show_in_folder': True,
        'show_in_form': True,
        'show_in_host_search': True,
        'show_in_table': False,
        'show_inherited_value': True,
        'topic': u'Basic settings',
    },
}


def test_registered_host_attributes():
    names = attrs.host_attribute_registry.keys()
    assert sorted(expected_attributes.keys()) == sorted(names)

    for attr_class in attrs.host_attribute_registry.values():
        attr = attr_class()
        spec = expected_attributes[attr.name()]

        #assert spec["class_name"] == attr_class.__name__

        attr_topic_class = attr.topic()
        assert spec["topic"] == attr_topic_class().title
        assert spec["show_in_table"] == attr.show_in_table()
        assert spec["show_in_folder"] == attr.show_in_folder(), attr_class
        assert spec["show_in_host_search"] == attr.show_in_host_search()
        assert spec["show_in_form"] == attr.show_in_form()
        assert spec["show_inherited_value"] == attr.show_inherited_value()
        assert spec["depends_on_tags"] == attr.depends_on_tags()
        assert spec["depends_on_roles"] == attr.depends_on_roles()
        assert spec["editable"] == attr.editable()
        assert spec["from_config"] == attr.from_config()


def test_legacy_register_rulegroup_with_defaults(monkeypatch):
    monkeypatch.setattr(attrs, "host_attribute_registry", attrs.HostAttributeRegistry())

    assert "lat" not in attrs.host_attribute_registry

    cmk.gui.wato.declare_host_attribute(
        cmk.gui.wato.NagiosTextAttribute(
            "lat",
            "_LAT",
            "Latitude",
            "Latitude",
        ),)

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


def test_legacy_register_rulegroup_without_defaults(monkeypatch):
    monkeypatch.setattr(attrs, "host_attribute_registry", attrs.HostAttributeRegistry())

    assert "lat" not in attrs.host_attribute_registry

    cmk.gui.wato.declare_host_attribute(
        cmk.gui.wato.NagiosTextAttribute(
            "lat",
            "_LAT",
            "Latitude",
            "Latitude",
        ),
        show_in_table=False,
        show_in_folder=False,
        show_in_host_search=False,
        topic=u"Xyz",
        show_in_form=False,
        depends_on_tags=["xxx"],
        depends_on_roles=["guest"],
        editable=False,
        show_inherited_value=False,
        may_edit=lambda: False,
        from_config=True,
    )

    topic = attrs.host_attribute_topic_registry["xyz"]()
    assert topic.title == u"Xyz"
    assert topic.sort_index == 80

    attr = attrs.host_attribute_registry["lat"]()
    assert isinstance(attr, attrs.ABCHostAttributeNagiosText)
    assert attr.show_in_table() is False
    assert attr.show_in_folder() is False
    assert attr.show_in_host_search() is False
    assert attr.show_in_form() is False

    assert attr.topic()().title == u"Xyz"
    assert attr.depends_on_tags() == ["xxx"]
    assert attr.depends_on_roles() == ["guest"]
    assert attr.editable() is False
    assert attr.show_inherited_value() is False
    assert attr.may_edit() is False
    assert attr.from_config() is True


@pytest.mark.parametrize("old,new", [
    ('Basic settings', 'basic'),
    ('Management Board', 'management_board'),
    ("Custom attributes", 'custom_attributes'),
    ('Eigene Attribute', 'custom_attributes'),
    ('xyz_unknown', 'custom_attributes'),
])
def test_custom_host_attribute_transform(old, new):
    attributes = [{
        'add_custom_macro': True,
        'help': u'',
        'name': 'attr1',
        'show_in_table': True,
        'title': u'Attribute 1',
        'topic': old,
        'type': 'TextAscii',
    }]

    transformed_attributes = attrs.transform_pre_16_host_topics(attributes)
    assert transformed_attributes[0]["topic"] == new


@pytest.mark.parametrize("for_what", [
    "host",
    "cluster",
    "host_search",
    "bulk",
])
def test_host_attribute_topics(load_plugins, for_what):
    assert attrs.get_sorted_host_attribute_topics(for_what=for_what) == [
        ("basic", u"Basic settings"),
        ("address", u'Address'),
        ("data_sources", u'Data sources'),
        ("management_board", u'Management Board'),
    ]


def test_host_attribute_topics_for_folders(load_plugins):
    assert attrs.get_sorted_host_attribute_topics("folder") == [
        ("basic", u"Basic settings"),
        ('address', u'Address'),
        ('data_sources', u'Data sources'),
        ('network_scan', u'Network Scan'),
        ('management_board', u'Management Board'),
    ]


@pytest.mark.parametrize("for_what", [
    "host",
    "cluster",
    "folder",
    "host_search",
    "bulk",
])
def test_host_attributes(load_plugins, for_what):
    topics = {
        "basic": [
            'contactgroups',
            'alias',
            'snmp_community',
            'parents',
            'site',
            'locked_by',
            'locked_attributes',
        ],
        "address": [
            'tag_address_family',
            'ipaddress',
            'ipv6address',
            'additional_ipv4addresses',
            'additional_ipv6addresses',
        ],
        "data_sources": [
            'tag_agent',
            'tag_snmp',
        ],
        "management_board": [
            'management_address',
            'management_protocol',
            'management_snmp_community',
            'management_ipmi_credentials',
        ],
    }

    if for_what == "folder":
        topics["network_scan"] = [
            'network_scan',
            'network_scan_result',
        ]

    current_topics = attrs.get_sorted_host_attribute_topics(for_what)

    assert sorted(topics.keys()) == sorted(dict(current_topics).keys())

    for topic_id, _title in current_topics:
        names = [a.name() for a in attrs.get_sorted_host_attributes_by_topic(topic_id)]
        assert names == topics.get(topic_id,
                                   []), "Expected attributes not specified for topic %r" % topic_id
