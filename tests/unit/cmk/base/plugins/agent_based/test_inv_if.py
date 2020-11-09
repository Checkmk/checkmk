#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from testlib import on_time
from cmk.base.plugins.agent_based.agent_based_api.v1 import Attributes, TableRow
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import Parameters
from cmk.base.plugins.agent_based.inv_if import Interface, inventory_if, parse_inv_if, SectionInvIf
from cmk.base.plugins.agent_based.utils import uptime

SECTION_INV_IF = SectionInvIf(
    interfaces=[
        Interface(index='1',
                  descr='Vlan-interface1',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=1,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=401.05),
        Interface(index='32769',
                  descr='port-channel 1',
                  alias='',
                  type='6',
                  speed=1000000000,
                  oper_status=1,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=7587252.59),
        Interface(index='49152',
                  descr='AUX0',
                  alias='',
                  type='23',
                  speed=0,
                  oper_status=1,
                  phys_address='',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49153',
                  descr='gigabitEthernet 1/0/1',
                  alias='Uplink sw-ks-01',
                  type='6',
                  speed=1000000000,
                  oper_status=1,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=400.98),
        Interface(index='49154',
                  descr='gigabitEthernet 1/0/2',
                  alias='Uplink sw-ks-01',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=7587252.53),
        Interface(index='49155',
                  descr='gigabitEthernet 1/0/3',
                  alias='pve-muc',
                  type='6',
                  speed=1000000000,
                  oper_status=1,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=2569670.7),
        Interface(index='49156',
                  descr='gigabitEthernet 1/0/4',
                  alias='pve-muc-ipmi',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=1042.15),
        Interface(index='49157',
                  descr='gigabitEthernet 1/0/5',
                  alias='monitoring',
                  type='6',
                  speed=1000000000,
                  oper_status=1,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=1046.32),
        Interface(index='49158',
                  descr='gigabitEthernet 1/0/6',
                  alias='monitoring-ipmi',
                  type='6',
                  speed=1000000000,
                  oper_status=1,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=1138.26),
        Interface(index='49159',
                  descr='gigabitEthernet 1/0/7',
                  alias='pve-muc',
                  type='6',
                  speed=10000000,
                  oper_status=1,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=2040.41),
        Interface(index='49160',
                  descr='gigabitEthernet 1/0/8',
                  alias='pve-muc1-ipmi',
                  type='6',
                  speed=1000000000,
                  oper_status=1,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=7611167.02),
        Interface(index='49161',
                  descr='gigabitEthernet 1/0/9',
                  alias='esxi',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=5344674.7),
        Interface(index='49162',
                  descr='gigabitEthernet 1/0/10',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49163',
                  descr='gigabitEthernet 1/0/11',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49164',
                  descr='gigabitEthernet 1/0/12',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=370.01),
        Interface(index='49165',
                  descr='gigabitEthernet 1/0/13',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49166',
                  descr='gigabitEthernet 1/0/14',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49167',
                  descr='gigabitEthernet 1/0/15',
                  alias='',
                  type='6',
                  speed=1000000000,
                  oper_status=1,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=3544593.37),
        Interface(index='49168',
                  descr='gigabitEthernet 1/0/16',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49169',
                  descr='gigabitEthernet 1/0/17',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49170',
                  descr='gigabitEthernet 1/0/18',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49171',
                  descr='gigabitEthernet 1/0/19',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49172',
                  descr='gigabitEthernet 1/0/20',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49173',
                  descr='gigabitEthernet 1/0/21',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49174',
                  descr='gigabitEthernet 1/0/22',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49175',
                  descr='gigabitEthernet 1/0/23',
                  alias=' ',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49176',
                  descr='gigabitEthernet 1/0/24',
                  alias=' ',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49177',
                  descr='gigabitEthernet 1/0/25',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49178',
                  descr='gigabitEthernet 1/0/26',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49179',
                  descr='gigabitEthernet 1/0/27',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0),
        Interface(index='49180',
                  descr='gigabitEthernet 1/0/28',
                  alias='',
                  type='6',
                  speed=0,
                  oper_status=2,
                  phys_address='74:DA:88:58:16:11',
                  admin_status=1,
                  last_change=0.0)
    ],
    n_interfaces_total=31,
)


def test_parse_inv_if():
    assert parse_inv_if([
        [
            [
                '1', 'Vlan-interface1', '', '6', '1000000000', '0', '1', '1',
                [116, 218, 136, 88, 22, 17], '40105'
            ],
            [
                '32769', 'port-channel 1', '', '6', '1000000000', '1000', '1', '1',
                [116, 218, 136, 88, 22, 17], '758725259'
            ],
            ['49152', 'AUX0', '', '23', '0', '0', '1', '1', [], '0'],
            [
                '49153', 'gigabitEthernet 1/0/1', 'Uplink sw-ks-01', '6', '1000000000', '1000', '1',
                '1', [116, 218, 136, 88, 22, 17], '40098'
            ],
            [
                '49154', 'gigabitEthernet 1/0/2', 'Uplink sw-ks-01', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '758725253'
            ],
            [
                '49155', 'gigabitEthernet 1/0/3', 'pve-muc', '6', '1000000000', '1000', '1', '1',
                [116, 218, 136, 88, 22, 17], '256967070'
            ],
            [
                '49156', 'gigabitEthernet 1/0/4', 'pve-muc-ipmi', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '104215'
            ],
            [
                '49157', 'gigabitEthernet 1/0/5', 'monitoring', '6', '1000000000', '1000', '1', '1',
                [116, 218, 136, 88, 22, 17], '104632'
            ],
            [
                '49158', 'gigabitEthernet 1/0/6', 'monitoring-ipmi', '6', '1000000000', '1000', '1',
                '1', [116, 218, 136, 88, 22, 17], '113826'
            ],
            [
                '49159', 'gigabitEthernet 1/0/7', 'pve-muc', '6', '10000000', '10', '1', '1',
                [116, 218, 136, 88, 22, 17], '204041'
            ],
            [
                '49160', 'gigabitEthernet 1/0/8', 'pve-muc1-ipmi', '6', '1000000000', '1000', '1',
                '1', [116, 218, 136, 88, 22, 17], '761116702'
            ],
            [
                '49161', 'gigabitEthernet 1/0/9', 'esxi', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '534467470'
            ],
            [
                '49162', 'gigabitEthernet 1/0/10', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49163', 'gigabitEthernet 1/0/11', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49164', 'gigabitEthernet 1/0/12', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '37001'
            ],
            [
                '49165', 'gigabitEthernet 1/0/13', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49166', 'gigabitEthernet 1/0/14', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49167', 'gigabitEthernet 1/0/15', '', '6', '1000000000', '1000', '1', '1',
                [116, 218, 136, 88, 22, 17], '354459337'
            ],
            [
                '49168', 'gigabitEthernet 1/0/16', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49169', 'gigabitEthernet 1/0/17', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49170', 'gigabitEthernet 1/0/18', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49171', 'gigabitEthernet 1/0/19', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49172', 'gigabitEthernet 1/0/20', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49173', 'gigabitEthernet 1/0/21', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49174', 'gigabitEthernet 1/0/22', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49175', 'gigabitEthernet 1/0/23', ' ', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49176', 'gigabitEthernet 1/0/24', ' ', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49177', 'gigabitEthernet 1/0/25', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49178', 'gigabitEthernet 1/0/26', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49179', 'gigabitEthernet 1/0/27', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
            [
                '49180', 'gigabitEthernet 1/0/28', '', '6', '0', '0', '2', '1',
                [116, 218, 136, 88, 22, 17], '0'
            ],
        ],
    ]) == SECTION_INV_IF


def test_inventory_if():
    with on_time(1601310544, 'UTC'):
        assert list(inventory_if(
            Parameters({}),
            SECTION_INV_IF,
            uptime.Section(7612999, None),
        )) == [
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 1},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 1,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': False
                     },
                     status_columns={
                         'description': 'Vlan-interface1',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 32769},
                     inventory_columns={
                         'speed': 1000000000,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 1,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': False
                     },
                     status_columns={
                         'description': 'port-channel 1',
                         'alias': '',
                         'last_change': 1601251200
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49152},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '',
                         'oper_status': 1,
                         'admin_status': 1,
                         'port_type': 23
                     },
                     status_columns={
                         'description': 'AUX0',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49153},
                     inventory_columns={
                         'speed': 1000000000,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 1,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': False
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/1',
                         'alias': 'Uplink sw-ks-01',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49154},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': False
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/2',
                         'alias': 'Uplink sw-ks-01',
                         'last_change': 1601251200
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49155},
                     inventory_columns={
                         'speed': 1000000000,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 1,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': False
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/3',
                         'alias': 'pve-muc',
                         'last_change': 1596240000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49156},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/4',
                         'alias': 'pve-muc-ipmi',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49157},
                     inventory_columns={
                         'speed': 1000000000,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 1,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': False
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/5',
                         'alias': 'monitoring',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49158},
                     inventory_columns={
                         'speed': 1000000000,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 1,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': False
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/6',
                         'alias': 'monitoring-ipmi',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49159},
                     inventory_columns={
                         'speed': 10000000,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 1,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': False
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/7',
                         'alias': 'pve-muc',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49160},
                     inventory_columns={
                         'speed': 1000000000,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 1,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': False
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/8',
                         'alias': 'pve-muc1-ipmi',
                         'last_change': 1601251200
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49161},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': False
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/9',
                         'alias': 'esxi',
                         'last_change': 1599004800
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49162},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/10',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49163},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/11',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49164},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/12',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49165},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/13',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49166},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/14',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49167},
                     inventory_columns={
                         'speed': 1000000000,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 1,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': False
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/15',
                         'alias': '',
                         'last_change': 1597190400
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49168},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/16',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49169},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/17',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49170},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/18',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49171},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/19',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49172},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/20',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49173},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/21',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49174},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/22',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49175},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/23',
                         'alias': ' ',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49176},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/24',
                         'alias': ' ',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49177},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/25',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49178},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/26',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49179},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/27',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            TableRow(path=['networking', 'interfaces'],
                     key_columns={'index': 49180},
                     inventory_columns={
                         'speed': 0,
                         'phys_address': '74:DA:88:58:16:11',
                         'oper_status': 2,
                         'admin_status': 1,
                         'port_type': 6,
                         'available': True
                     },
                     status_columns={
                         'description': 'gigabitEthernet 1/0/28',
                         'alias': '',
                         'last_change': 1593648000
                     }),
            Attributes(path=['networking'],
                       inventory_attributes={
                           'available_ethernet_ports': 19,
                           'total_ethernet_ports': 30,
                           'total_interfaces': 31
                       },
                       status_attributes={}),
        ]
