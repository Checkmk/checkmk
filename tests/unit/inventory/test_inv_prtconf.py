#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]


@pytest.mark.parametrize('info, inventory_data', [
    (
        [
            ['System Model', ' IBM,8231-E2D'],
            ['Machine Serial Number', ' 06AAB2T'],
            ['Processor Type', ' PowerPC_POWER7'],
            ['Processor Implementation Mode', ' POWER 7'],
            ['Processor Version', ' PV_7_Compat'],
            ['Number Of Processors', ' 8'],
            ['Processor Clock Speed', ' 4284 MHz'],
            ['CPU Type', ' 64-bit'],
            ['Kernel Type', ' 64-bit'],
            ['LPAR Info', ' 1 wiaix001'],
            ['Memory Size', ' 257792 MB'],
            ['Good Memory Size', ' 257792 MB'],
            ['Platform Firmware level', ' AL770_076'],
            ['Firmware Version', ' IBM,AL770_076'],
            ['Console Login', ' enable'],
            ['Auto Restart', ' true'],
            ['Full Core', ' false'],
            ['Network Information'],
            ['Host Name', ' example1'],
            ['IP Address', ' 192.168.0.1'],
            ['Sub Netmask', ' 255.255.255.128'],
            ['Gateway', ' 192.168.0.2'],
            ['Name Server', ' 192.168.0.3'],
            ['Domain Name', ' example1.example.com'],
            ['Volume Groups Information'],
            ['Inactive VGs'],
            ['=============================================================================='],
            ['appvg'],
            ['=============================================================================='],
            ['Active VGs'],
            ['=============================================================================='],
            ['cow-daag0cvg', ''],
            ['PV_NAME           PV STATE          TOTAL PPs   FREE PPs    FREE '
             'DISTRIBUTION'],
            ['hdisk663          active            3218        0           '
             '00..00..00..00..00'],
            ['hdisk664          active            3218        0           '
             '00..00..00..00..00'],
            ['hdisk665          active            3218        0           '
             '00..00..00..00..00'],
            ['hdisk666          active            3218        0           '
             '00..00..00..00..00'],
            ['=============================================================================='],
            ['p2zgkbos4vg', ''],
            ['PV_NAME           PV STATE          TOTAL PPs   FREE PPs    FREE '
             'DISTRIBUTION'],
            ['hdisk5            active            643         0           '
             '00..00..00..00..00'],
            ['hdisk18           active            643         0           '
             '00..00..00..00..00'],
            ['=============================================================================='],
            ['INSTALLED RESOURCE LIST'],
        ],
        {
            'hardware.cpu.': {
                'arch': 'ppc64',
                'model': 'PowerPC_POWER7',
                'implementation_mode': 'POWER 7',
                'max_speed': 4284000000.0,
                'cpus': 8
            },
            'hardware.system.': {
                'serial': '06AAB2T',
                'product': '8231-E2D',
                'manufacturer': 'IBM'
            },
            'hardware.memory.': {
                'total_ram_usable': 270314504192
            },
            'software.firmware.': {
                'version': 'AL770_076',
                'vendor': 'IBM',
                'platform_level': 'AL770_076'
            },
            'networking.': {
                'domain_name': 'example1.example.com',
                'gateway': '192.168.0.2',
                'ip_address': '192.168.0.1',
                'name_server': '192.168.0.3',
                'sub_netmask': '255.255.255.128'
            },
            'software.os.': {
                'arch': 'ppc64'
            },
            '.hardware.volumes.physical_volumes.hdisk664:': {
                'volume_group_name': 'cow-daag0cvg',
                'physical_volume_name': 'hdisk664',
                'physical_volume_status': 'active',
                'physical_volume_total_partitions': '3218',
                'physical_volume_free_partitions': '0'
            },
            '.hardware.volumes.physical_volumes.hdisk665:': {
                'volume_group_name': 'cow-daag0cvg',
                'physical_volume_name': 'hdisk665',
                'physical_volume_status': 'active',
                'physical_volume_total_partitions': '3218',
                'physical_volume_free_partitions': '0'
            },
            '.hardware.volumes.physical_volumes.hdisk666:': {
                'volume_group_name': 'cow-daag0cvg',
                'physical_volume_name': 'hdisk666',
                'physical_volume_status': 'active',
                'physical_volume_total_partitions': '3218',
                'physical_volume_free_partitions': '0'
            },
            '.hardware.volumes.physical_volumes.hdisk18:': {
                'volume_group_name': 'p2zgkbos4vg',
                'physical_volume_name': 'hdisk18',
                'physical_volume_status': 'active',
                'physical_volume_total_partitions': '643',
                'physical_volume_free_partitions': '0'
            },
            '.hardware.volumes.physical_volumes.appvg:': {
                'volume_group_name': 'appvg',
                'physical_volume_name': '',
                'physical_volume_status': 'Inactive',
                'physical_volume_total_partitions': '',
                'physical_volume_free_partitions': ''
            }
        },
    ),
])
def test_inv_prtconf(inventory_plugin_manager, check_manager, info, inventory_data):
    inv_plugin = inventory_plugin_manager.get_inventory_plugin('prtconf')
    actual, _status_tree_data = inv_plugin.run_inventory(info)
    assert actual == inventory_data
