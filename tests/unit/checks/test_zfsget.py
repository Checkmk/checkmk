import pytest
from checktestlib import DiscoveryResult, assertDiscoveryResultsEqual

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info,expected_discovery_result",
    [
        ([], []),
        # no zfsget items and no df item
        (
            [
                [u'[zfs]'],
                [u'[df]'],
            ],
            [],
        ),
        # no zfsget items and pass-through filesystem
        (
            [
                [u'[zfs]'],
                [u'[df]'],
                [u'/', u'10255636', u'1836517', u'8419119', u'18%', u'/'],
                [u'/dev', u'10255636', u'1836517', u'8419119', u'18%', u'/dev'],
                [u'foo', u'zfs', u'457758604', u'88', u'457758516', u'0%', u'/mnt/foo'],
                [u'foo/bar', u'zfs', u'45977', u'2012596', u'457758516', u'0%', u'/mnt/foo/bar'],
            ],
            [("/mnt/foo", {}), ("/mnt/foo/bar", {}), ("/", {})],
        ),
        # no zfsget items and pass-through filesystem
        (
            [
                [u'[zfs]'],
                [u'[df]'],
                [u'/', u'10255636', u'1836517', u'8419119', u'18%', u'/'],
                [u'/dev', u'10255636', u'1836517', u'8419119', u'18%', u'/dev'],
            ],
            [("/", {})],
        ),
        # no whitespace in device-names/mountpoints
        (
            [
                [u'[zfs]'],
                [u'foo', u'name', u'foo', u'-'],
                [u'foo', u'quota', u'0', u'default'],
                [u'foo', u'used', u'9741332480', u'-'],
                [u'foo', u'available', u'468744720384', u'-'],
                [u'foo', u'mountpoint', u'/mnt/foo', u'default'],
                [u'foo', u'type', u'filesystem', u'-'],
                [u'foo/bar-baz', u'name', u'foo/bar-baz', u'-'],
                [u'foo/bar-baz', u'quota', u'0', u'default'],
                [u'foo/bar-baz', u'used', u'2060898304', u'-'],
                [u'foo/bar-baz', u'available', u'468744720384', u'-'],
                [u'foo/bar-baz', u'mountpoint', u'/mnt/foo/bar-baz', u'default'],
                [u'foo/bar-baz', u'type', u'filesystem', u'-'],
                [u'[df]'],
                [u'/', u'10255636', u'1836517', u'8419119', u'18%', u'/'],
                [u'/dev', u'10255636', u'1836517', u'8419119', u'18%', u'/dev'],
                [u'foo', u'457758604', u'88', u'457758516', u'0%', u'/mnt/foo'],
                [u'foo/bar-baz', u'45977', u'2012596', u'457758516', u'0%', u'/mnt/foo/bar-baz'],
            ],
            [("/mnt/foo/bar-baz", {}), ("/mnt/foo", {}), ("/", {})],
        ),
        # no whitespace in device-names/mountpoints + FS_TYPE
        (
            [
                [u'[zfs]'],
                [u'foo', u'name', u'foo', u'-'],
                [u'foo', u'quota', u'0', u'default'],
                [u'foo', u'used', u'9741332480', u'-'],
                [u'foo', u'available', u'468744720384', u'-'],
                [u'foo', u'mountpoint', u'/mnt/foo', u'default'],
                [u'foo', u'type', u'filesystem', u'-'],
                [u'foo/bar', u'baz', u'name', u'foo/bar', u'-'],
                [u'foo/bar', u'baz', u'quota', u'0', u'default'],
                [u'foo/bar', u'baz', u'used', u'2060898304', u'-'],
                [u'foo/bar', u'baz', u'available', u'468744720384', u'-'],
                [u'foo/bar', u'baz', u'mountpoint', u'/mnt/foo/bar', u'default'],
                [u'foo/bar', u'baz', u'type', u'filesystem', u'-'],
                [u'[df]'],
                [u'/', u'10255636', u'1836517', u'8419119', u'18%', u'/'],
                [u'/dev', u'10255636', u'1836517', u'8419119', u'18%', u'/dev'],
                [u'foo', u'zfs', u'457758604', u'88', u'457758516', u'0%', u'/mnt/foo'],
                [u'foo/bar', u'zfs', u'45977', u'2012596', u'457758516', u'0%', u'/mnt/foo/bar'],
            ],
            [("/mnt/foo", {}), ("/mnt/foo/bar", {}), ("/", {})],
        ),
    ])
def test_zfsget_discovery(check_manager, info, expected_discovery_result):
    check_zfsget = check_manager.get_check("zfsget")
    discovery_result = DiscoveryResult(check_zfsget.run_discovery(check_zfsget.run_parse(info)))
    assertDiscoveryResultsEqual("zfsget", discovery_result,
                                DiscoveryResult(expected_discovery_result))
