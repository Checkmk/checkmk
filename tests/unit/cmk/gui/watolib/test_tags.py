# encoding: utf-8
# pylint: disable=redefined-outer-name

import pytest  # type: ignore
from pathlib2 import Path

from cmk.gui.exceptions import MKUserError

import cmk.gui.watolib.utils
import cmk.gui.config as config
import cmk.gui.watolib.tags as tags


@pytest.fixture()
def test_cfg(monkeypatch):
    multisite_dir = Path(cmk.gui.watolib.utils.multisite_dir())
    multisite_dir.mkdir(parents=True, exist_ok=True)
    hosttags_mk = multisite_dir / "hosttags.mk"

    with hosttags_mk.open("w", encoding="utf-8") as f:  # pylint: disable=no-member
        f.write(u"""# Created by WATO
# encoding: utf-8

wato_host_tags += [
    ('criticality', u'Criticality', [
        ('prod', u'Productive system', []),
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


def test_tag_config():
    cfg = tags.HosttagsConfiguration()
    assert cfg.tag_groups == []
    assert cfg.aux_tag_list.get_tags() == []


def test_tag_config_load(test_cfg):
    cfg = tags.HosttagsConfiguration()
    cfg.load()

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


def test_tag_config_get_hosttag_topics(test_cfg):
    cfg = tags.HosttagsConfiguration()
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

    assert sorted(cfg.get_hosttag_topics()) == sorted([("Topigzr", "Topigzr"), ("Topics",
                                                                                "Topics")])


def test_tag_config_remove_tag_group(test_cfg):
    cfg = tags.HosttagsConfiguration()
    cfg.load()

    assert cfg.get_tag_group("xyz") is None
    cfg.remove_tag_group("xyz")  # not existing -> fine

    assert cfg.get_tag_group("networking") is not None
    cfg.remove_tag_group("networking")
    assert cfg.get_tag_group("networking") is None


def test_tag_config_remove_aux_tag(test_cfg):
    cfg = tags.HosttagsConfiguration()
    cfg.load()

    assert "xyz" not in cfg.aux_tag_list.get_tag_ids()
    cfg.aux_tag_list.remove("xyz")  # not existing -> fine

    assert "bla" in cfg.aux_tag_list.get_tag_ids()
    cfg.aux_tag_list.remove("bla")
    assert "bla" not in cfg.aux_tag_list.get_tag_ids()


def test_tag_config_get_tag_group(test_cfg):
    cfg = tags.HosttagsConfiguration()
    cfg.load()

    assert cfg.get_tag_group("xyz") is None
    assert isinstance(cfg.get_tag_group("networking"), tags.HosttagGroup)


def test_tag_config_get_aux_tags(test_cfg):
    cfg = tags.HosttagsConfiguration()
    cfg.load()
    assert [a.id for a in cfg.get_aux_tags()] == ["bla"]


def test_tag_config_get_tag_ids(test_cfg):
    cfg = tags.HosttagsConfiguration()
    cfg.load()
    assert cfg.get_tag_ids() == set(
        ['bla', 'critical', 'dmz', 'lan', 'offline', 'prod', 'test', 'wan'])


def test_tag_config_get_tag_ids_with_group_prefix(test_cfg):
    cfg = tags.HosttagsConfiguration()
    cfg.load()
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
    cfg = tags.HosttagsConfiguration()
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
    cfg = tags.HosttagsConfiguration()

    with pytest.raises(MKUserError, match="Unknown tag group"):
        cfg.update_tag_group(
            tags.HosttagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))

    cfg.insert_tag_group(tags.HosttagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))
    cfg.update_tag_group(tags.HosttagGroup(("tgid2", "title", [("tgid2", "tagid2", [])])))
    assert cfg.tag_groups[-1].title == "title"


def test_tag_config_save(test_cfg, mocker):
    export_mock = mocker.patch.object(tags, "_export_hosttags_to_php")

    cfg = tags.HosttagsConfiguration()
    cfg.insert_tag_group(tags.HosttagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))
    cfg.save()

    export_mock.assert_called_once()

    cfg = tags.HosttagsConfiguration()
    cfg.load()
    assert len(cfg.tag_groups) == 1
    assert cfg.tag_groups[0].id == "tgid2"


def test_builtin_tags_get_effective_tag_groups():
    cfg = tags.HosttagsConfiguration()
    cfg.insert_tag_group(tags.HosttagGroup(("tgid2", "Topics/titlor", [("tgid2", "tagid2", [])])))

    merged = config.BuiltinTags().get_effective_tag_groups(cfg.get_legacy_format()[0])

    merged_cfg = tags.HosttagsConfiguration()
    merged_cfg._parse_legacy_format(merged, [])
    assert sorted(merged_cfg.get_tag_ids()) == sorted([
        None,
        'piggyback',
        'no-piggyback',
        'all-agents',
        'cmk-agent',
        'ip-v4-only',
        'ip-v4v6',
        'ip-v6-only',
        'no-agent',
        'no-ip',
        'no-snmp',
        'snmp-v1',
        'snmp-v2',
        'special-agents',
        'tgid2',
    ])


def test_builtin_tags_get_effective_aux_tags():
    cfg = tags.HosttagsConfiguration()
    cfg.aux_tag_list.append(tags.AuxTag(("bla", "BLAAAA")))

    merged = config.BuiltinTags().get_effective_aux_tags(cfg.get_legacy_format()[1])

    assert ('bla', 'BLAAAA') in merged
    assert ('ip-v4', u'Address/IPv4') in merged
