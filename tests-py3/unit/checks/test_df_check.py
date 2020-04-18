#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from checktestlib import (
    DiscoveryResult,
    CheckResult,
    assertDiscoveryResultsEqual,
    assertCheckResultsEqual,
    MockHostExtraConf,
)

pytestmark = pytest.mark.checks

#   .--Test info sections--------------------------------------------------.
#   |                _____         _     _        __                       |
#   |               |_   _|__  ___| |_  (_)_ __  / _| ___                  |
#   |                 | |/ _ \/ __| __| | | '_ \| |_ / _ \                 |
#   |                 | |  __/\__ \ |_  | | | | |  _| (_) |                |
#   |                 |_|\___||___/\__| |_|_| |_|_|  \___/                 |
#   |                                                                      |
#   |                               _   _                                  |
#   |                 ___  ___  ___| |_(_) ___  _ __  ___                  |
#   |                / __|/ _ \/ __| __| |/ _ \| '_ \/ __|                 |
#   |                \__ \  __/ (__| |_| | (_) | | | \__ \                 |
#   |                |___/\___|\___|\__|_|\___/|_| |_|___/                 |
#   |                                                                      |
#   '----------------------------------------------------------------------'

info_df_lnx = [
    [u'/dev/sda4', u'ext4', u'143786696', u'101645524', u'34814148', u'75%', u'/'],
    [u'[df_inodes_start]'],
    [u'/dev/sda4', u'ext4', u'9142272', u'1654272', u'7488000', u'19%', u'/'],
    [u'[df_inodes_end]'],
]

info_df_win = [
    [u'C:\\', u'NTFS', u'8192620', u'7724268', u'468352', u'95%', u'C:\\'],
    [u'New_Volume', u'NTFS', u'10240796', u'186256', u'10054540', u'2%', u'E:\\'],
    [u'New_Volume', u'NTFS', u'124929596', u'50840432', u'74089164', u'41%', u'F:\\'],
]

# yapf: disable
info_df_lnx_docker = [
    [u'/dev/sda2', u'ext4', u'143786696', u'101645524', u'34814148', u'75%', u'/var/lib/docker'],
    [u'/dev/sda3', u'ext4', u'143786696', u'101645524', u'34814148', u'75%', u'/var/lib/docker-latest'],
    [u'/dev/sda4', u'ext4', u'143786696', u'101645524', u'34814148', u'75%', u'/var/lib/docker/some-fs/mnt/grtzlhash'],
    [u'/dev/sdb1', u'ext4', u'131586052', u'75701024', u'49157812', u'61%', u'/var/lib/docker/volumes'],
    [u'[df_inodes_start]'],
    [u'/dev/sda2', u'ext4', u'9142272', u'1654272', u'7488000', u'19%', u'/var/lib/docker'],
    [u'/dev/sda3', u'ext4', u'9142272', u'1654272', u'7488000', u'19%', u'/var/lib/docker-latest'],
    [u'/dev/sda4', u'ext4', u'9142272', u'1654272', u'7488000', u'19%', u'/var/lib/docker/some-fs/mnt/grtzlhash'],
    [u'/dev/sdb1', u'ext4', u'8388608', u'586810', u'7801798', u'7%', u'/var/lib/docker/volumes'],
    [u'[df_inodes_end]']
]
# yapf:enable

info_df_lnx_tmpfs = [
    [u'tmpfs', u'tmpfs', u'8152820', u'76', u'8152744', u'1%', u'/opt/omd/sites/heute/tmp'],
    [u'tmpfs', u'tmpfs', u'8152840', u'118732', u'8034108', u'2%', u'/dev/shm'],
    [u'[df_inodes_start]'],
    [u'tmpfs', u'tmpfs', u'2038205', u'48', u'2038157', u'1%', u'/opt/omd/sites/heute/tmp'],
    [u'tmpfs', u'tmpfs', u'2038210', u'57', u'2038153', u'1%', u'/dev/shm'],
    [u'[df_inodes_end]'],
]

# NOTE: This gargantuan test info section is uncritically used data from an archived agent output.
#       I suspect that our handling of btrfs is not really adequate, test cases using this data
#       serve the sole purpose of not inadvertenty breaking the status quo. Thus:
# TODO: Replace this monstrosity with something more concise.
# yapf: disable
info_df_btrfs = [
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/'],
    [u'devtmpfs', u'devtmpfs', u'497396', u'0', u'497396', u'0%', u'/dev'],
    [u'tmpfs', u'tmpfs', u'506312', u'0', u'506312', u'0%', u'/dev/shm'],
    [u'tmpfs', u'tmpfs', u'506312', u'6980', u'499332', u'2%', u'/run'],
    [u'tmpfs', u'tmpfs', u'506312', u'0', u'506312', u'0%', u'/sys/fs/cgroup'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/.snapshots'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/var/tmp'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/var/spool'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/var/opt'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/var/log'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/var/lib/pgsql'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/var/lib/named'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/var/lib/mailman'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/var/crash'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/usr/local'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/tmp'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/srv'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/opt'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/home'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/boot/grub2/x86_64-efi'],
    [u'/dev/sda1', u'btrfs', u'20970496', u'4169036', u'16539348', u'21%', u'/boot/grub2/i386-pc'],
    [u'[df_inodes_start]'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/'],
    [u'devtmpfs', u'devtmpfs', u'124349', u'371', u'123978', u'1%', u'/dev'],
    [u'tmpfs', u'tmpfs', u'126578', u'1', u'126577', u'1%', u'/dev/shm'],
    [u'tmpfs', u'tmpfs', u'126578', u'481', u'126097', u'1%', u'/run'],
    [u'tmpfs', u'tmpfs', u'126578', u'12', u'126566', u'1%', u'/sys/fs/cgroup'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/.snapshots'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/tmp'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/spool'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/opt'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/log'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/lib/pgsql'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/lib/named'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/lib/mailman'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/var/crash'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/usr/local'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/tmp'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/srv'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/opt'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/home'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/boot/grub2/x86_64-efi'],
    [u'/dev/sda1', u'btrfs', u'0', u'0', u'0', u'-', u'/boot/grub2/i386-pc'],
    [u'[df_inodes_end]'],
]
# yapf: enable

info_empty_inodes = [
    [u'[df_inodes_start]'],
    [u'/dev/mapper/vgdns-lvbindauthlog', u'-', u'-', u'-', u'-', u'-', u'/dns/bindauth/log'],
    [u'[df_inodes_end]'],
]

#.
#   .--Test functions------------------------------------------------------.
#   |   _____         _      __                  _   _                     |
#   |  |_   _|__  ___| |_   / _|_   _ _ __   ___| |_(_) ___  _ __  ___     |
#   |    | |/ _ \/ __| __| | |_| | | | '_ \ / __| __| |/ _ \| '_ \/ __|    |
#   |    | |  __/\__ \ |_  |  _| |_| | | | | (__| |_| | (_) | | | \__ \    |
#   |    |_|\___||___/\__| |_|  \__,_|_| |_|\___|\__|_|\___/|_| |_|___/    |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@pytest.mark.parametrize(
    "info,expected_result,inventory_df_rules",
    [
        ([], [], {}),
        # Linux:
        (info_df_lnx, [(u'/', {
            "include_volume_name": False
        })], {}),
        # Linux w/ volume name unset:
        (
            info_df_lnx,
            [(u'/', {
                "include_volume_name": False
            })],
            {
                "include_volume_name": False
            },
        ),
        # Linux w/ volume name option:
        (
            info_df_lnx,
            [(u'/dev/sda4 /', {
                "include_volume_name": True
            })],
            {
                "include_volume_name": True
            },
        ),
        # Windows:
        (info_df_win, [(u'E:/', {
            "include_volume_name": False
        }), (u'F:/', {
            "include_volume_name": False
        }), (u'C:/', {
            "include_volume_name": False
        })], {}),
        # Windows w/ volume name option:
        (
            info_df_win,
            [(u'New_Volume E:/', {
                "include_volume_name": True
            }), (u'New_Volume F:/', {
                "include_volume_name": True
            }), (u'C:\\ C:/', {
                "include_volume_name": True
            })],
            {
                "include_volume_name": True
            },
        ),
        # Ignoring tmpfs:
        (info_df_lnx_tmpfs, [], {}),
        # Ignoring tmpfs explicitly:
        (
            info_df_lnx_tmpfs,
            [],
            {
                "ignore_fs_types": ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660']
            },
        ),
        # Ignoring tmpfs explicitly, but including one mountpoint explicitly:
        (
            info_df_lnx_tmpfs,
            [(u'/opt/omd/sites/heute/tmp', {
                "include_volume_name": False
            })],
            {
                "ignore_fs_types": ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'],
                "never_ignore_mountpoints": [u'/opt/omd/sites/heute/tmp']
            },
        ),
        # Including tmpfs:
        (
            info_df_lnx_tmpfs,
            [(u'/opt/omd/sites/heute/tmp', {
                "include_volume_name": False
            }), (u'/dev/shm', {
                "include_volume_name": False
            })],
            {
                "ignore_fs_types": ['nfs', 'smbfs', 'cifs', 'iso9660']
            },
        ),
        # Including tmpfs and volume name:
        (
            info_df_lnx_tmpfs,
            [(u'tmpfs /opt/omd/sites/heute/tmp', {
                "include_volume_name": True
            }), (u'tmpfs /dev/shm', {
                "include_volume_name": True
            })],
            {
                "ignore_fs_types": ['nfs', 'smbfs', 'cifs', 'iso9660'],
                "include_volume_name": True
            },
        ),
        # Including only check mk tmpfs via regex
        (
            info_df_lnx_tmpfs,
            [
                (u'tmpfs /opt/omd/sites/heute/tmp', {
                    "include_volume_name": True
                }),
            ],
            {
                "ignore_fs_types": ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'],
                "include_volume_name": True,
                "never_ignore_mountpoints": [u'~.*/omd/sites/[^/]+/tmp$']
            },
        ),

        # btrfs:
        (info_df_btrfs, [(u'btrfs /dev/sda1', {
            "include_volume_name": False
        })], {}),
        # btrfs w/ volume name option:
        (
            info_df_btrfs,
            [(u'/dev/sda1 btrfs /dev/sda1', {
                "include_volume_name": True
            })],
            {
                "include_volume_name": True
            },
        ),
        # empty inodes:
        (info_empty_inodes, [], {}),
        # Omit docker container filesystems, but not /var/lib/docker{,-latest}:
        (
            info_df_lnx_docker,
            [
                (u'/var/lib/docker', {
                    "include_volume_name": False
                }),
                (u'/var/lib/docker-latest', {
                    "include_volume_name": False
                }),
            ],
            {},
        ),
    ])
def test_df_discovery_with_parse(check_manager, info, expected_result, inventory_df_rules):
    check = check_manager.get_check("df")

    def mocked_host_extra_conf_merged(_hostname, ruleset):
        if ruleset is check.context.get("inventory_df_rules"):
            return inventory_df_rules
        raise AssertionError("Unknown/unhandled ruleset used in mock of host_extra_conf")

    with MockHostExtraConf(check, mocked_host_extra_conf_merged, "host_extra_conf_merged"):
        raw_discovery_result = check.run_discovery(check.run_parse(info))
        discovery_result = DiscoveryResult(raw_discovery_result)

    expected_result = DiscoveryResult(expected_result)
    assertDiscoveryResultsEqual(check, discovery_result, expected_result)


df_params = {
    'trend_range': 24,
    'show_levels': 'onmagic',
    'inodes_levels': (10.0, 5.0),
    'magic_normsize': 20,
    'show_inodes': 'onlow',
    'levels': (80.0, 90.0),
    'show_reserved': False,
    'levels_low': (50.0, 60.0),
    'trend_perfdata': True
}


@pytest.mark.parametrize(
    "item,params,info,expected_result",
    [
        (
            u"/",
            df_params,
            info_df_lnx,
            [(
                0,
                '75.79% used (103.92 of 137.13 GB)',
                [
                    (u'fs_used', 106418.50390625, 112333.35625, 126375.02578125, 0, 140416.6953125),
                    ('fs_size', 140416.6953125),
                    ('fs_used_percent', 75.78764310712029),
                    ('inodes_used', 1654272, 8228044.8, 8685158.4, 0, 9142272),
                ],
            )],
        ),
        (  # second test case: this time the item state is present
            u'/dev/sda4 /',
            df_params,
            info_df_lnx,
            [(
                0,
                '75.79% used (103.92 of 137.13 GB), trend: 0.00 B / 24 hours',
                [
                    (u'fs_used', 106418.50390625, 112333.35625, 126375.02578125, 0, 140416.6953125),
                    ('fs_size', 140416.6953125),
                    ('fs_used_percent', 75.78764310712029),
                    ('growth', 0.0),
                    ('trend', 0.0, None, None, 0, 5850.695638020833),
                    ('inodes_used', 1654272, 8228044.8, 8685158.4, 0, 9142272),
                ],
            )],
        ),
        (
            u'E:/',
            df_params,
            info_df_win,
            [(
                0,
                '1.82% used (181.89 MB of 9.77 GB)',
                [
                    (u'fs_used', 181.890625, 8000.621875, 9000.699609375, 0, 10000.77734375),
                    ('fs_size', 10000.77734375),
                    ('fs_used_percent', 1.8187648694496015),
                ],
            )],
        ),
        (
            u'New_Volume E:/',
            df_params,
            info_df_win,
            [(
                0,
                '1.82% used (181.89 MB of 9.77 GB), trend: 0.00 B / 24 hours',
                [
                    (u'fs_used', 181.890625, 8000.621875, 9000.699609375, 0, 10000.77734375),
                    ('fs_size', 10000.77734375, None, None, None, None),
                    ('fs_used_percent', 1.8187648694496015),
                    ('growth', 0.0, None, None, None, None),
                    ('trend', 0.0, None, None, 0, 416.6990559895833),
                ],
            )],
        ),
        (
            u'btrfs /dev/sda1',
            df_params,
            info_df_btrfs,
            [(
                0,
                '21.13% used (4.23 of 20.00 GB)',
                [
                    (u'fs_used', 4327.29296875, 16383.2, 18431.1, 0, 20479.0),
                    ('fs_size', 20479.0, None, None, None, None),
                    ('fs_used_percent', 21.130391956394355),
                ],
            )],
        ),
        (
            u"/home",
            df_params,
            info_df_lnx,
            [],
        ),
    ])
def test_df_check_with_parse(check_manager, item, params, info, expected_result):
    check = check_manager.get_check("df")

    actual = CheckResult(check.run_check(item, params, check.run_parse(info)))
    expected = CheckResult(expected_result)
    assertCheckResultsEqual(actual, expected)
