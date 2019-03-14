# encoding: utf-8
# pylint: disable=redefined-outer-name

import pytest  # type: ignore
from pathlib2 import Path

from cmk.gui.exceptions import MKUserError

import cmk.gui.watolib.utils
import cmk.gui.config as config
import cmk.gui.tags as tags
import cmk.gui.watolib.tags
from cmk.gui.watolib.tags import TagConfigFile


@pytest.fixture()
def test_cfg(monkeypatch):
    multisite_dir = Path(cmk.gui.watolib.utils.multisite_dir())
    multisite_dir.mkdir(parents=True, exist_ok=True)
    tags_mk = multisite_dir / "tags.mk"
    hosttags_mk = multisite_dir / "hosttags.mk"

    with hosttags_mk.open("w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(u"""# Created by WATO
# encoding: utf-8

wato_host_tags += [
    ('criticality', u'Criticality', [
        ('prod', u'Productive system', ['bla']),
        ('critical', u'Business critical', []),
        ('test', u'Test system', []),
        ('offline', u'Do not monitor this host', [])]),
    ('networking', u'Networking Segment', [
        ('lan', u'Local network (low latency)', []),
        ('wan', u'WAN (high latency)', []),
        ('dmz', u'DMZ (low latency, secure access)', []),
    ]),
]

wato_aux_tags += [("bla", u"bläää")]
""")

    yield
    if hosttags_mk.exists():  # pylint: disable=no-member
        hosttags_mk.unlink()  # pylint: disable=no-member
    if tags_mk.exists():  # pylint: disable=no-member
        tags_mk.unlink()  # pylint: disable=no-member


def test_convert_pre_16_tags():
    dict_config = cmk.gui.tags.transform_pre_16_tags(
        [
            ('criticality', u'Criticality', [
                ('prod', u'Productive system', []),
                ('critical', u'Business critical', []),
                ('test', u'Test system', []),
                ('offline', u'Do not monitor this host', []),
            ]),
            ('networking', u'Networking Segment', [
                ('lan', u'Local network (low latency)', []),
                ('wan', u'WAN (high latency)', []),
                ('dmz', u'DMZ (low latency, secure access)', []),
            ]),
        ],
        [("bla", u"blüb")],
    )

    assert dict_config == {
        'aux_tags': [{
            'id': 'bla',
            'title': u'bl\xfcb'
        }],
        'tag_groups': [
            {
                'id': 'criticality',
                'tags': [{
                    'aux_tags': [],
                    'id': 'prod',
                    'title': u'Productive system'
                }, {
                    'aux_tags': [],
                    'id': 'critical',
                    'title': u'Business critical'
                }, {
                    'aux_tags': [],
                    'id': 'test',
                    'title': u'Test system'
                }, {
                    'aux_tags': [],
                    'id': 'offline',
                    'title': u'Do not monitor this host'
                }],
                'title': u'Criticality'
            },
            {
                'id': 'networking',
                'tags': [{
                    'aux_tags': [],
                    'id': 'lan',
                    'title': u'Local network (low latency)'
                }, {
                    'aux_tags': [],
                    'id': 'wan',
                    'title': u'WAN (high latency)'
                }, {
                    'aux_tags': [],
                    'id': 'dmz',
                    'title': u'DMZ (low latency, secure access)'
                }],
                'title': u'Networking Segment'
            },
        ],
    }


def test_tag_config():
    cfg = tags.TagConfig()
    assert cfg.tag_groups == []
    assert cfg.aux_tag_list.get_tags() == []


def test_tag_config_load(test_cfg):
    cfg = tags.TagConfig()
    cfg.parse_config(TagConfigFile().load_for_reading())

    assert len(cfg.tag_groups) == 2
    tag_group = cfg.tag_groups[0]
    assert tag_group.id == "criticality"
    assert tag_group.title == u"Criticality"
    assert tag_group.topic is None

    tag_group = cfg.tag_groups[1]
    assert tag_group.id == "networking"
    assert tag_group.title == u"Networking Segment"
    assert tag_group.topic is None

    assert len(cfg.aux_tag_list.get_tags()) == 1
    aux_tag = cfg.aux_tag_list.get_tags()[0]
    assert aux_tag.topic is None
    assert aux_tag.id == "bla"
    assert aux_tag.title == u"bläää"


def test_tag_config_get_topic_choices(test_cfg):
    cfg = tags.TagConfig()
    cfg.tag_groups.append(
        tags.HosttagGroup({
            "id": "tgid",
            "title": "Title",
            "topic": "Topigzr",
            "tags": [{
                "id": "tgid",
                "title": "titlr",
                "aux_tags": [],
            }],
        }))
    cfg.tag_groups.append(tags.HosttagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))
    cfg.aux_tag_list.append(tags.AuxTag(("bla", "BOOM/BLUB")))

    assert sorted(cfg.get_topic_choices()) == sorted([
        ("Topigzr", "Topigzr"),
        ("Topics", "Topics"),
        ("BOOM", "BOOM"),
    ])


def test_tag_config_remove_tag_group(test_cfg):
    cfg = tags.TagConfig()
    cfg.parse_config(TagConfigFile().load_for_reading())

    assert cfg.get_tag_group("xyz") is None
    cfg.remove_tag_group("xyz")  # not existing -> fine

    assert cfg.get_tag_group("networking") is not None
    cfg.remove_tag_group("networking")
    assert cfg.get_tag_group("networking") is None


def test_tag_config_remove_aux_tag(test_cfg):
    cfg = tags.TagConfig()
    cfg.parse_config(TagConfigFile().load_for_reading())

    assert "xyz" not in cfg.aux_tag_list.get_tag_ids()
    cfg.aux_tag_list.remove("xyz")  # not existing -> fine

    assert "bla" in cfg.aux_tag_list.get_tag_ids()
    cfg.aux_tag_list.remove("bla")
    assert "bla" not in cfg.aux_tag_list.get_tag_ids()


def test_tag_config_get_tag_group(test_cfg):
    cfg = tags.TagConfig()
    cfg.parse_config(TagConfigFile().load_for_reading())

    assert cfg.get_tag_group("xyz") is None
    assert isinstance(cfg.get_tag_group("networking"), tags.HosttagGroup)


def test_tag_config_get_aux_tags(test_cfg):
    cfg = tags.TagConfig()
    cfg.parse_config(TagConfigFile().load_for_reading())
    assert [a.id for a in cfg.get_aux_tags()] == ["bla"]


def test_get_aux_tags_by_tags(test_cfg):
    cfg = tags.TagConfig()
    cfg.parse_config(TagConfigFile().load_for_reading())
    assert cfg.get_aux_tags_by_tag() == {
        'critical': [],
        'dmz': [],
        'lan': [],
        'offline': [],
        'prod': ['bla'],
        'test': [],
        'wan': [],
    }


def test_tag_config_get_tag_ids(test_cfg):
    cfg = tags.TagConfig()
    cfg.parse_config(TagConfigFile().load_for_reading())
    assert cfg.get_tag_ids() == set(
        ['bla', 'critical', 'dmz', 'lan', 'offline', 'prod', 'test', 'wan'])


def test_tag_config_get_tag_ids_with_group_prefix(test_cfg):
    cfg = tags.TagConfig()
    cfg.parse_config(TagConfigFile().load_for_reading())
    assert cfg.get_tag_ids_with_group_prefix() == set([
        'bla',
        'criticality/critical',
        'criticality/offline',
        'criticality/prod',
        'criticality/test',
        'networking/dmz',
        'networking/lan',
        'networking/wan',
    ])


def test_tag_config_insert_tag_group(test_cfg):
    cfg = tags.TagConfig()
    cfg.insert_tag_group(tags.HosttagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))

    assert cfg.tag_groups[-1].id == "tgid2"

    with pytest.raises(MKUserError, match="already used"):
        cfg.insert_tag_group(
            tags.HosttagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))

    with pytest.raises(MKUserError, match="Please specify"):
        tg = tags.HosttagGroup()
        tg.id = ""
        cfg.insert_tag_group(tg)

    with pytest.raises(MKUserError, match="Please specify"):
        tg = tags.HosttagGroup()
        tg.id = "abc"
        tg.title = ""
        cfg.insert_tag_group(tg)

    with pytest.raises(MKUserError, match="Only one tag may be empty"):
        tg = tags.HosttagGroup(("tgid3", "Topics/titlor", [
            (None, "tagid2", []),
            ("", "tagid3", []),
        ]))
        cfg.insert_tag_group(tg)

    with pytest.raises(MKUserError, match="must be unique"):
        tg = tags.HosttagGroup(("tgid4", "Topics/titlor", [
            ("ding", "tagid2", []),
            ("ding", "tagid3", []),
        ]))
        cfg.insert_tag_group(tg)

    with pytest.raises(MKUserError, match="already being used"):
        tg = tags.HosttagGroup(("tgid5", "Topics/titlor", [
            ("tgid2", "tagid2", []),
        ]))
        cfg.insert_tag_group(tg)

    cfg.aux_tag_list.append(tags.AuxTag(("bla", "BLAAAA")))
    with pytest.raises(MKUserError, match="already being used as aux"):
        tg = tags.HosttagGroup(("tgid6", "Topics/titlor", [
            ("bla", "tagid2", []),
        ]))
        cfg.insert_tag_group(tg)

    with pytest.raises(MKUserError, match="at least one tag"):
        tg = tags.HosttagGroup(("tgid7", "Topics/titlor", []))
        cfg.insert_tag_group(tg)


def test_tag_config_update_tag_group(test_cfg):
    cfg = tags.TagConfig()

    with pytest.raises(MKUserError, match="Unknown tag group"):
        cfg.update_tag_group(
            tags.HosttagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))

    cfg.insert_tag_group(tags.HosttagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))
    cfg.update_tag_group(tags.HosttagGroup(("tgid2", "title", [("tgid2", "tagid2", [])])))
    assert cfg.tag_groups[-1].title == "title"


def test_tag_config_save(test_cfg, mocker):
    export_mock = mocker.patch.object(cmk.gui.watolib.tags, "_export_hosttags_to_php")

    config_file = TagConfigFile()

    cfg = tags.TagConfig()
    cfg.insert_tag_group(tags.HosttagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))
    config_file.save(cfg.get_dict_format())

    export_mock.assert_called_once()

    cfg = tags.TagConfig()
    cfg.parse_config(config_file.load_for_reading())
    assert len(cfg.tag_groups) == 1
    assert cfg.tag_groups[0].id == "tgid2"


def test_iadd_tag_config():
    cfg1 = tags.TagConfig()
    cfg1.insert_tag_group(tags.HosttagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))
    cfg1.aux_tag_list.append(tags.AuxTag(("bla", "BLAAAA")))

    cfg2 = tags.TagConfig()
    cfg2.insert_tag_group(tags.HosttagGroup(("tgid3", "Topics/titlor", [("tgid3", "tagid3", [])])))
    cfg2.insert_tag_group(tags.HosttagGroup(("tgid2", "BLAAA", [("tgid2", "tagid2", [])])))
    cfg2.aux_tag_list.append(tags.AuxTag(("blub", "BLUB")))
    cfg2.aux_tag_list.append(tags.AuxTag(("bla", "BLUB")))

    cfg1 += cfg2

    assert len(cfg1.tag_groups) == 2
    assert cfg1.tag_groups[0].id == "tgid2"
    assert cfg1.tag_groups[1].id == "tgid3"
    assert cfg1.tag_groups[1].title == "titlor"

    aux_tags = cfg1.get_aux_tags()
    assert len(aux_tags) == 2
    assert aux_tags[0].id == "bla"
    assert aux_tags[0].title == "BLAAAA"
    assert aux_tags[1].id == "blub"


def test_tag_groups_by_topic(load_config):
    groups = {
        u"Address": ["address_family"],
        u'Data sources': ["agent", "piggyback", "snmp"],
    }

    grouped = dict(config.tags.get_tag_groups_by_topic())
    assert sorted(grouped.keys()) == sorted(groups.keys())

    for topic, tag_group_ids in groups.items():
        tg_ids = [tg.id for tg in grouped[topic]]
        assert sorted(tg_ids) == sorted(tag_group_ids)


def test_aux_tags_by_topic(register_builtin_html, load_config):
    expected_groups = {
        u"Address": ["ip-v4", "ip-v6"],
        u'Data sources': ["snmp", "tcp", "ping"],
    }

    actual_groups = dict(config.tags.get_aux_tags_by_topic())
    assert sorted(actual_groups.keys()) == sorted(expected_groups.keys())

    for topic, tag_group_ids in expected_groups.items():
        tg_ids = [tg.id for tg in actual_groups[topic]]
        assert sorted(tg_ids) == sorted(tag_group_ids)
