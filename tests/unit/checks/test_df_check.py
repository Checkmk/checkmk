#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]
from checktestlib import (
    DiscoveryResult,
    CheckResult,
    assertDiscoveryResultsEqual,
    assertCheckResultsEqual,
    MockHostExtraConf,
)
from cmk.base.plugins.agent_based.df_section import parse_df

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
    ['/dev/sda4', 'ext4', '143786696', '101645524', '34814148', '75%', '/'],
    ['[df_inodes_start]'],
    ['/dev/sda4', 'ext4', '9142272', '1654272', '7488000', '19%', '/'],
    ['[df_inodes_end]'],
]

info_df_win = [
    ['C:\\', 'NTFS', '8192620', '7724268', '468352', '95%', 'C:\\'],
    ['New_Volume', 'NTFS', '10240796', '186256', '10054540', '2%', 'E:\\'],
    ['New_Volume', 'NTFS', '124929596', '50840432', '74089164', '41%', 'F:\\'],
]

# yapf: disable
info_df_lnx_docker = [
    ['/dev/sda2', 'ext4', '143786696', '101645524', '34814148', '75%', '/var/lib/docker'],
    ['/dev/sda3', 'ext4', '143786696', '101645524', '34814148', '75%', '/var/lib/docker-latest'],
    ['/dev/sda4', 'ext4', '143786696', '101645524', '34814148', '75%', '/var/lib/docker/some-fs/mnt/grtzlhash'],
    ['/dev/sdb1', 'ext4', '131586052', '75701024', '49157812', '61%', '/var/lib/docker/volumes'],
    ['[df_inodes_start]'],
    ['/dev/sda2', 'ext4', '9142272', '1654272', '7488000', '19%', '/var/lib/docker'],
    ['/dev/sda3', 'ext4', '9142272', '1654272', '7488000', '19%', '/var/lib/docker-latest'],
    ['/dev/sda4', 'ext4', '9142272', '1654272', '7488000', '19%', '/var/lib/docker/some-fs/mnt/grtzlhash'],
    ['/dev/sdb1', 'ext4', '8388608', '586810', '7801798', '7%', '/var/lib/docker/volumes'],
    ['[df_inodes_end]'],
]
# yapf:enable

info_df_lnx_tmpfs = [
    ['tmpfs', 'tmpfs', '8152820', '76', '8152744', '1%', '/opt/omd/sites/heute/tmp'],
    ['tmpfs', 'tmpfs', '8152840', '118732', '8034108', '2%', '/dev/shm'],
    ['[df_inodes_start]'],
    ['tmpfs', 'tmpfs', '2038205', '48', '2038157', '1%', '/opt/omd/sites/heute/tmp'],
    ['tmpfs', 'tmpfs', '2038210', '57', '2038153', '1%', '/dev/shm'],
    ['[df_inodes_end]'],
]

# NOTE: This gargantuan test info section is uncritically used data from an archived agent output.
#       I suspect that our handling of btrfs is not really adequate, test cases using this data
#       serve the sole purpose of not inadvertenty breaking the status quo. Thus:
# TODO: Replace this monstrosity with something more concise.
# yapf: disable
info_df_btrfs = [
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/'],
    ['devtmpfs', 'devtmpfs', '497396', '0', '497396', '0%', '/dev'],
    ['tmpfs', 'tmpfs', '506312', '0', '506312', '0%', '/dev/shm'],
    ['tmpfs', 'tmpfs', '506312', '6980', '499332', '2%', '/run'],
    ['tmpfs', 'tmpfs', '506312', '0', '506312', '0%', '/sys/fs/cgroup'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/.snapshots'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/var/tmp'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/var/spool'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/var/opt'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/var/log'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/var/lib/pgsql'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/var/lib/named'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/var/lib/mailman'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/var/crash'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/usr/local'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/tmp'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/srv'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/opt'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/home'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/boot/grub2/x86_64-efi'],
    ['/dev/sda1', 'btrfs', '20970496', '4169036', '16539348', '21%', '/boot/grub2/i386-pc'],
    ['[df_inodes_start]'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/'],
    ['devtmpfs', 'devtmpfs', '124349', '371', '123978', '1%', '/dev'],
    ['tmpfs', 'tmpfs', '126578', '1', '126577', '1%', '/dev/shm'],
    ['tmpfs', 'tmpfs', '126578', '481', '126097', '1%', '/run'],
    ['tmpfs', 'tmpfs', '126578', '12', '126566', '1%', '/sys/fs/cgroup'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/.snapshots'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/var/tmp'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/var/spool'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/var/opt'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/var/log'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/var/lib/pgsql'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/var/lib/named'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/var/lib/mailman'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/var/crash'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/usr/local'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/tmp'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/srv'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/opt'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/home'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/boot/grub2/x86_64-efi'],
    ['/dev/sda1', 'btrfs', '0', '0', '0', '-', '/boot/grub2/i386-pc'],
    ['[df_inodes_end]'],
]
# yapf: enable

info_empty_inodes = [
    ['[df_inodes_start]'],
    ['/dev/mapper/vgdns-lvbindauthlog', '-', '-', '-', '-', '-', '/dns/bindauth/log'],
    ['[df_inodes_end]'],
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


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.parametrize(
    "info,expected_result,inventory_df_rules",
    [
        (
            [],
            [],
            {},
        ),
        # Linux:
        (
            info_df_lnx,
            [
                (
                    '/',
                    {
                        "include_volume_name": False
                    },
                ),
            ],
            {},
        ),
        # Linux w/ volume name unset:
        (
            info_df_lnx,
            [
                (
                    '/',
                    {
                        "include_volume_name": False
                    },
                ),
            ],
            {
                "include_volume_name": False
            },
        ),
        # Linux w/ volume name option:
        (
            info_df_lnx,
            [
                (
                    '/dev/sda4 /',
                    {
                        "include_volume_name": True
                    },
                ),
            ],
            {
                "include_volume_name": True
            },
        ),
        # Windows:
        (
            info_df_win,
            [
                (
                    'E:/',
                    {
                        "include_volume_name": False
                    },
                ),
                (
                    'F:/',
                    {
                        "include_volume_name": False
                    },
                ),
                (
                    'C:/',
                    {
                        "include_volume_name": False
                    },
                ),
            ],
            {},
        ),
        # Windows w/ volume name option:
        (
            info_df_win,
            [
                (
                    'New_Volume E:/',
                    {
                        "include_volume_name": True
                    },
                ),
                (
                    'New_Volume F:/',
                    {
                        "include_volume_name": True
                    },
                ),
                (
                    'C:\\ C:/',
                    {
                        "include_volume_name": True
                    },
                ),
            ],
            {
                "include_volume_name": True
            },
        ),
        # Ignoring tmpfs:
        (
            info_df_lnx_tmpfs,
            [],
            {},
        ),
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
            [
                (
                    '/opt/omd/sites/heute/tmp',
                    {
                        "include_volume_name": False
                    },
                ),
            ],
            {
                "ignore_fs_types": ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'],
                "never_ignore_mountpoints": ['/opt/omd/sites/heute/tmp']
            },
        ),
        # Including tmpfs:
        (
            info_df_lnx_tmpfs,
            [
                (
                    '/opt/omd/sites/heute/tmp',
                    {
                        "include_volume_name": False
                    },
                ),
                (
                    '/dev/shm',
                    {
                        "include_volume_name": False
                    },
                ),
            ],
            {
                "ignore_fs_types": ['nfs', 'smbfs', 'cifs', 'iso9660']
            },
        ),
        # Including tmpfs and volume name:
        (
            info_df_lnx_tmpfs,
            [
                (
                    'tmpfs /opt/omd/sites/heute/tmp',
                    {
                        "include_volume_name": True
                    },
                ),
                (
                    'tmpfs /dev/shm',
                    {
                        "include_volume_name": True
                    },
                ),
            ],
            {
                "ignore_fs_types": ['nfs', 'smbfs', 'cifs', 'iso9660'],
                "include_volume_name": True
            },
        ),
        # Including only check mk tmpfs via regex
        (
            info_df_lnx_tmpfs,
            [
                (
                    'tmpfs /opt/omd/sites/heute/tmp',
                    {
                        "include_volume_name": True
                    },
                ),
            ],
            {
                "ignore_fs_types": ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'],
                "include_volume_name": True,
                "never_ignore_mountpoints": ['~.*/omd/sites/[^/]+/tmp$']
            },
        ),

        # btrfs:
        (
            info_df_btrfs,
            [
                (
                    'btrfs /dev/sda1',
                    {
                        "include_volume_name": False
                    },
                ),
            ],
            {},
        ),
        # btrfs w/ volume name option:
        (
            info_df_btrfs,
            [
                (
                    '/dev/sda1 btrfs /dev/sda1',
                    {
                        "include_volume_name": True
                    },
                ),
            ],
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
                (
                    '/var/lib/docker',
                    {
                        "include_volume_name": False
                    },
                ),
                (
                    '/var/lib/docker-latest',
                    {
                        "include_volume_name": False
                    },
                ),
            ],
            {},
        ),
    ])
def test_df_discovery_with_parse(info, expected_result, inventory_df_rules):
    check = Check('df')

    def mocked_host_extra_conf_merged(_hostname, ruleset):
        if ruleset is check.context.get("inventory_df_rules"):
            return inventory_df_rules
        raise AssertionError("Unknown/unhandled ruleset used in mock of host_extra_conf")

    with MockHostExtraConf(check, mocked_host_extra_conf_merged, "host_extra_conf_merged"):
        raw_discovery_result = check.run_discovery(parse_df(info))
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


@pytest.mark.usefixtures("config_load_all_checks")
@pytest.mark.parametrize(
    "item,params,info,expected_result",
    [
        (
            '/',
            df_params,
            info_df_lnx,
            [
                (
                    0,
                    '75.79% used (103.92 of 137.13 GB)',
                    [
                        ('fs_used', 106418.50390625, 112333.35625, 126375.02578125, 0,
                         140416.6953125),
                        ('fs_size', 140416.6953125),
                        ('fs_used_percent', 75.78764310712029),
                    ],
                ),
                (
                    0,
                    '',
                    [
                        ('inodes_used', 1654272, 8228044.8, 8685158.4, 0, 9142272),
                    ],
                ),
            ],
        ),
        (  # second test case: this time the item state is present
            '/dev/sda4 /',
            df_params,
            info_df_lnx,
            [
                (
                    0,
                    '75.79% used (103.92 of 137.13 GB)',
                    [
                        ('fs_used', 106418.50390625, 112333.35625, 126375.02578125, 0,
                         140416.6953125),
                        ('fs_size', 140416.6953125),
                        ('fs_used_percent', 75.78764310712029),
                    ],
                ),
                (
                    0,
                    'trend: 0.00 B / 24 hours',
                    [
                        ('growth', 0.0),
                        ('trend', 0.0, None, None, 0, 5850.695638020833),
                    ],
                ),
                (
                    0,
                    '',
                    [
                        ('inodes_used', 1654272, 8228044.8, 8685158.4, 0, 9142272),
                    ],
                ),
            ],
        ),
        (
            'E:/',
            df_params,
            info_df_win,
            [
                (
                    0,
                    '1.82% used (181.89 MB of 9.77 GB)',
                    [
                        ('fs_used', 181.890625, 8000.621875, 9000.699609375, 0, 10000.77734375),
                        ('fs_size', 10000.77734375),
                        ('fs_used_percent', 1.8187648694496015),
                    ],
                ),
            ],
        ),
        (
            'New_Volume E:/',
            df_params,
            info_df_win,
            [
                (
                    0,
                    '1.82% used (181.89 MB of 9.77 GB)',
                    [
                        ('fs_used', 181.890625, 8000.621875, 9000.699609375, 0, 10000.77734375),
                        ('fs_size', 10000.77734375, None, None, None, None),
                        ('fs_used_percent', 1.8187648694496015),
                    ],
                ),
                (
                    0,
                    'trend: 0.00 B / 24 hours',
                    [
                        ('growth', 0.0, None, None, None, None),
                        ('trend', 0.0, None, None, 0, 416.6990559895833),
                    ],
                ),
            ],
        ),
        (
            'btrfs /dev/sda1',
            df_params,
            info_df_btrfs,
            [(
                0,
                '21.13% used (4.23 of 20.00 GB)',
                [
                    ('fs_used', 4327.29296875, 16383.2, 18431.1, 0, 20479.0),
                    ('fs_size', 20479.0, None, None, None, None),
                    ('fs_used_percent', 21.130391956394355),
                ],
            )],
        ),
        (
            '/home',
            df_params,
            info_df_lnx,
            [],
        ),
    ])
def test_df_check_with_parse(item, params, info, expected_result):
    check = Check('df')

    actual = CheckResult(check.run_check(item, params, parse_df(info)))
    expected = CheckResult(expected_result)
    assertCheckResultsEqual(actual, expected)
