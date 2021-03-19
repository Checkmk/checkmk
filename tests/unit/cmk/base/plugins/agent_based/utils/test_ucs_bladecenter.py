#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.utils.ucs_bladecenter import generic_parse


def test_generic_parse():
    assert generic_parse([
        [
            'fcStats', 'Dn sys/switch-B/slot-1/switch-fc/port-1/stats', 'BytesRx 27132984565284',
            'BytesTx 2905866392424', 'PacketsRx 13332284889', 'PacketsTx 1589971733', 'Suspect no'
        ],
        [
            'fcStats', 'Dn sys/switch-B/slot-1/switch-fc/port-2/stats', 'BytesRx 237449751667472',
            'BytesTx 12235876160004', 'PacketsRx 116056665429', 'PacketsTx 7246334177', 'Suspect no'
        ],
        [
            'fcStats', 'Dn sys/switch-B/slot-1/switch-fc/port-3/stats', 'BytesRx 6001821657771360',
            'BytesTx 11967977907125040', 'PacketsRx 3366025998633630', 'PacketsTx 2991977296912080',
            'Suspect no'
        ],
        [
            'fcStats', 'Dn sys/switch-B/slot-1/switch-fc/port-4/stats', 'BytesRx 6000859585097280',
            'BytesTx 11491133458164960', 'PacketsRx 3217012108333605', 'PacketsTx 2872766184672060',
            'Suspect no'
        ],
        [
            'fcStats', 'Dn sys/switch-B/slot-1/switch-fc/port-5/stats', 'BytesRx 6000859585097280',
            'BytesTx 11433477817196880', 'PacketsRx 3199011900400260', 'PacketsTx 2858352274430040',
            'Suspect no'
        ],
        [
            'fcStats', 'Dn sys/switch-B/slot-1/switch-fc/port-6/stats', 'BytesRx 6000859585097280',
            'BytesTx 11433477817196880', 'PacketsRx 3198977540661900', 'PacketsTx 2858352274430040',
            'Suspect no'
        ],
        [
            'fcStats', 'Dn sys/switch-A/slot-1/switch-fc/port-1/stats', 'BytesRx 27132982650552',
            'BytesTx 2907081927340', 'PacketsRx 13332289971', 'PacketsTx 1590572107', 'Suspect no'
        ],
        [
            'fcStats', 'Dn sys/switch-A/slot-1/switch-fc/port-2/stats', 'BytesRx 237293119662108',
            'BytesTx 12238375145120', 'PacketsRx 115981398636', 'PacketsTx 7247679957', 'Suspect no'
        ],
        [
            'fcStats', 'Dn sys/switch-A/slot-1/switch-fc/port-3/stats', 'BytesRx 6545461438103280',
            'BytesTx 12503233911297120', 'PacketsRx 3516538832519610', 'PacketsTx 3125791297955100',
            'Suspect no'
        ],
        [
            'fcStats', 'Dn sys/switch-A/slot-1/switch-fc/port-4/stats', 'BytesRx 6269002983258720',
            'BytesTx 12028107449255040', 'PacketsRx 3368061813131460', 'PacketsTx 3007009682444580',
            'Suspect no'
        ],
        [
            'fcStats', 'Dn sys/switch-A/slot-1/switch-fc/port-5/stats', 'BytesRx 6269002983258720',
            'BytesTx 11970108210903360', 'PacketsRx 3349919871277380', 'PacketsTx 2992509872856660',
            'Suspect no'
        ],
        [
            'fcStats', 'Dn sys/switch-A/slot-1/switch-fc/port-6/stats', 'BytesRx 6269002983258720',
            'BytesTx 11970108210903360', 'PacketsRx 3349919871277380', 'PacketsTx 2992509872856660',
            'Suspect no'
        ],
        [
            'fcErrStats', 'Dn sys/switch-B/slot-1/switch-fc/port-1/err-stats', 'Rx 0', 'Tx 0',
            'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fcErrStats', 'Dn sys/switch-B/slot-1/switch-fc/port-2/err-stats', 'Rx 0', 'Tx 0',
            'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fcErrStats', 'Dn sys/switch-B/slot-1/switch-fc/port-3/err-stats', 'Rx 747994324228020',
            'Tx 0', 'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fcErrStats', 'Dn sys/switch-B/slot-1/switch-fc/port-4/err-stats', 'Rx 718191546168015',
            'Tx 0', 'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fcErrStats', 'Dn sys/switch-B/slot-1/switch-fc/port-5/err-stats', 'Rx 714588068607510',
            'Tx 0', 'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fcErrStats', 'Dn sys/switch-B/slot-1/switch-fc/port-6/err-stats', 'Rx 714588068607510',
            'Tx 0', 'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fcErrStats', 'Dn sys/switch-A/slot-1/switch-fc/port-1/err-stats', 'Rx 0', 'Tx 0',
            'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fcErrStats', 'Dn sys/switch-A/slot-1/switch-fc/port-2/err-stats', 'Rx 0', 'Tx 0',
            'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fcErrStats', 'Dn sys/switch-A/slot-1/switch-fc/port-3/err-stats', 'Rx 781452119456070',
            'Tx 0', 'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fcErrStats', 'Dn sys/switch-A/slot-1/switch-fc/port-4/err-stats', 'Rx 751756715578440',
            'Tx 0', 'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fcErrStats', 'Dn sys/switch-A/slot-1/switch-fc/port-5/err-stats', 'Rx 748131763181460',
            'Tx 0', 'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fcErrStats', 'Dn sys/switch-A/slot-1/switch-fc/port-6/err-stats', 'Rx 748131763181460',
            'Tx 0', 'CrcRx 0', 'DiscardRx 0', 'DiscardTx 0'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/A/phys-slot-1-port-6',
            'EpDn sys/switch-A/slot-1/switch-fc/port-6', 'AdminState disabled', 'OperState up',
            'PortId 6', 'SwitchId A', 'SlotId 1'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/A/phys-slot-1-port-5',
            'EpDn sys/switch-A/slot-1/switch-fc/port-5', 'AdminState disabled', 'OperState up',
            'PortId 5', 'SwitchId A', 'SlotId 1'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/A/phys-slot-1-port-4',
            'EpDn sys/switch-A/slot-1/switch-fc/port-4', 'AdminState disabled', 'OperState up',
            'PortId 4', 'SwitchId A', 'SlotId 1'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/A/phys-slot-1-port-3',
            'EpDn sys/switch-A/slot-1/switch-fc/port-3', 'AdminState disabled', 'OperState up',
            'PortId 3', 'SwitchId A', 'SlotId 1'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/A/phys-slot-1-port-2',
            'EpDn sys/switch-A/slot-1/switch-fc/port-2', 'AdminState enabled', 'OperState up',
            'PortId 2', 'SwitchId A', 'SlotId 1'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/A/phys-slot-1-port-1',
            'EpDn sys/switch-A/slot-1/switch-fc/port-1', 'AdminState enabled', 'OperState up',
            'PortId 1', 'SwitchId A', 'SlotId 1'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/B/phys-slot-1-port-6',
            'EpDn sys/switch-B/slot-1/switch-fc/port-6', 'AdminState disabled', 'OperState up',
            'PortId 6', 'SwitchId B', 'SlotId 1'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/B/phys-slot-1-port-5',
            'EpDn sys/switch-B/slot-1/switch-fc/port-5', 'AdminState disabled', 'OperState up',
            'PortId 5', 'SwitchId B', 'SlotId 1'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/B/phys-slot-1-port-4',
            'EpDn sys/switch-B/slot-1/switch-fc/port-4', 'AdminState disabled', 'OperState up',
            'PortId 4', 'SwitchId B', 'SlotId 1'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/B/phys-slot-1-port-3',
            'EpDn sys/switch-B/slot-1/switch-fc/port-3', 'AdminState disabled', 'OperState up',
            'PortId 3', 'SwitchId B', 'SlotId 1'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/B/phys-slot-1-port-2',
            'EpDn sys/switch-B/slot-1/switch-fc/port-2', 'AdminState enabled', 'OperState up',
            'PortId 2', 'SwitchId B', 'SlotId 1'
        ],
        [
            'fabricFcSanEp', 'Dn fabric/san/B/phys-slot-1-port-1',
            'EpDn sys/switch-B/slot-1/switch-fc/port-1', 'AdminState enabled', 'OperState up',
            'PortId 1', 'SwitchId B', 'SlotId 1'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-7/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-8/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-9/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-10/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-11/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-12/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-13/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-14/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-15/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-16/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-17/tx-stats',
            'TotalBytes 67771511563937', 'UnicastPackets 32615801329', 'MulticastPackets 29898043',
            'BroadcastPackets 32111737'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-18/tx-stats',
            'TotalBytes 67693606295274', 'UnicastPackets 32567240018', 'MulticastPackets 14196305',
            'BroadcastPackets 27297800'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-19/tx-stats',
            'TotalBytes 67815080004453', 'UnicastPackets 32656250869', 'MulticastPackets 14346004',
            'BroadcastPackets 65208907'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-20/tx-stats',
            'TotalBytes 67709065269502', 'UnicastPackets 32605946491', 'MulticastPackets 12005117',
            'BroadcastPackets 41008202'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-21/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-22/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-23/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-24/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-25/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-26/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-27/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-28/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-29/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-30/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-31/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-32/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-33/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-34/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-35/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-36/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-37/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-38/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-39/tx-stats',
            'TotalBytes 451717191374', 'UnicastPackets 713153873', 'MulticastPackets 446525',
            'BroadcastPackets 4297755'
        ],
        [
            'etherTxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-40/tx-stats',
            'TotalBytes 604575844325', 'UnicastPackets 812847342', 'MulticastPackets 531366',
            'BroadcastPackets 744572'
        ],
        [
            'etherTxStats', 'Dn fabric/lan/B/pc-1/tx-stats', 'TotalBytes 1056293035699',
            'UnicastPackets 1526001215', 'MulticastPackets 977891', 'BroadcastPackets 5042327'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-7/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-8/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-9/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-10/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-11/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-12/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-13/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-14/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-15/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-16/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-17/tx-stats',
            'TotalBytes 67682818314784', 'UnicastPackets 32465954049', 'MulticastPackets 29780053',
            'BroadcastPackets 32100470'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-18/tx-stats',
            'TotalBytes 67659649503111', 'UnicastPackets 32450868523', 'MulticastPackets 13939489',
            'BroadcastPackets 27288639'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-19/tx-stats',
            'TotalBytes 67680063204015', 'UnicastPackets 32469355827', 'MulticastPackets 14398383',
            'BroadcastPackets 65183590'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-20/tx-stats',
            'TotalBytes 67653582675993', 'UnicastPackets 32442178134', 'MulticastPackets 10985573',
            'BroadcastPackets 40994656'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-21/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-22/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-23/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-24/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-25/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-26/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-27/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-28/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-29/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-30/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-31/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-32/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-33/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-34/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-35/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-36/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-37/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-38/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-39/tx-stats',
            'TotalBytes 255134958066', 'UnicastPackets 311838874', 'MulticastPackets 499453',
            'BroadcastPackets 1107648'
        ],
        [
            'etherTxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-40/tx-stats',
            'TotalBytes 253607896014', 'UnicastPackets 311627730', 'MulticastPackets 464545',
            'BroadcastPackets 453021'
        ],
        [
            'etherTxStats', 'Dn fabric/lan/A/pc-1/tx-stats', 'TotalBytes 508742854080',
            'UnicastPackets 623466604', 'MulticastPackets 963998', 'BroadcastPackets 1560669'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-2/host/port-16/tx-stats',
            'TotalBytes 18865358320', 'UnicastPackets 23589467', 'MulticastPackets 0',
            'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-1/host/port-4/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-1/host/port-8/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-1/host/port-16/tx-stats',
            'TotalBytes 20259206624', 'UnicastPackets 28300788', 'MulticastPackets 0',
            'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-2/host/port-4/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-2/host/port-8/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-2/host/port-12/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 31028158'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-1/host/port-12/tx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 31027842'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-1/host/port-29/tx-stats', 'TotalBytes 8276',
            'UnicastPackets 87377042821', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-1/host/port-31/tx-stats',
            'TotalBytes 182713123339062', 'UnicastPackets 0', 'MulticastPackets 0',
            'BroadcastPackets 152666456'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-2/host/port-29/tx-stats', 'TotalBytes 9830',
            'UnicastPackets 87612967653', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherTxStats', 'Dn sys/chassis-1/slot-2/host/port-31/tx-stats',
            'TotalBytes 182935433105076', 'UnicastPackets 0', 'MulticastPackets 0',
            'BroadcastPackets 152667232'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-7/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-8/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-9/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-10/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-11/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-12/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-13/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-14/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-15/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-16/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-17/rx-stats',
            'TotalBytes 4279535288715', 'UnicastPackets 2671010934', 'MulticastPackets 1527909',
            'BroadcastPackets 122258'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-18/rx-stats',
            'TotalBytes 4072180590802', 'UnicastPackets 2550163237', 'MulticastPackets 1530910',
            'BroadcastPackets 94263'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-19/rx-stats',
            'TotalBytes 4129479887282', 'UnicastPackets 2546795868', 'MulticastPackets 1547672',
            'BroadcastPackets 81318'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-20/rx-stats',
            'TotalBytes 4212562062785', 'UnicastPackets 2655928449', 'MulticastPackets 2486223',
            'BroadcastPackets 13883616'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-21/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-22/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-23/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-24/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-25/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-26/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-27/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-28/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-29/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-30/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-31/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-32/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-33/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-34/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-35/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-36/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-37/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-38/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-39/rx-stats',
            'TotalBytes 325471864254', 'UnicastPackets 559917156', 'MulticastPackets 451179895',
            'BroadcastPackets 503217529'
        ],
        [
            'etherRxStats', 'Dn sys/switch-B/slot-1/switch-ether/port-40/rx-stats',
            'TotalBytes 6466125443913', 'UnicastPackets 16412790036', 'MulticastPackets 489310416',
            'BroadcastPackets 621360253'
        ],
        [
            'etherRxStats', 'Dn fabric/lan/B/pc-1/rx-stats', 'TotalBytes 6791597308167',
            'UnicastPackets 16972707192', 'MulticastPackets 940490311',
            'BroadcastPackets 1124577782'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-7/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-8/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-9/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-10/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-11/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-12/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-13/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-14/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-15/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-16/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-17/rx-stats',
            'TotalBytes 4030543727852', 'UnicastPackets 2373221013', 'MulticastPackets 1687112',
            'BroadcastPackets 9391829'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-18/rx-stats',
            'TotalBytes 4020329596730', 'UnicastPackets 2362938494', 'MulticastPackets 1512050',
            'BroadcastPackets 177739'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-19/rx-stats',
            'TotalBytes 4026114380220', 'UnicastPackets 2373129092', 'MulticastPackets 1561286',
            'BroadcastPackets 46825'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-20/rx-stats',
            'TotalBytes 4004457090968', 'UnicastPackets 2361570431', 'MulticastPackets 1579078',
            'BroadcastPackets 1099918'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-21/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-22/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-23/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-24/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-25/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-26/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-27/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-28/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-29/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
        [
            'etherRxStats', 'Dn sys/switch-A/slot-1/switch-ether/port-30/rx-stats', 'TotalBytes 0',
            'UnicastPackets 0', 'MulticastPackets 0', 'BroadcastPackets 0'
        ],
    ]) == {
        'etherRxStats': {
            'fabric/lan/B/pc-1/rx-stats': {
                'BroadcastPackets': '1124577782',
                'Dn': 'fabric/lan/B/pc-1/rx-stats',
                'MulticastPackets': '940490311',
                'TotalBytes': '6791597308167',
                'UnicastPackets': '16972707192'
            },
            'sys/switch-A/slot-1/switch-ether/port-10/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-10/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-11/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-11/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-12/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-12/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-13/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-13/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-14/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-14/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-15/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-15/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-16/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-16/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-17/rx-stats': {
                'BroadcastPackets': '9391829',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-17/rx-stats',
                'MulticastPackets': '1687112',
                'TotalBytes': '4030543727852',
                'UnicastPackets': '2373221013'
            },
            'sys/switch-A/slot-1/switch-ether/port-18/rx-stats': {
                'BroadcastPackets': '177739',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-18/rx-stats',
                'MulticastPackets': '1512050',
                'TotalBytes': '4020329596730',
                'UnicastPackets': '2362938494'
            },
            'sys/switch-A/slot-1/switch-ether/port-19/rx-stats': {
                'BroadcastPackets': '46825',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-19/rx-stats',
                'MulticastPackets': '1561286',
                'TotalBytes': '4026114380220',
                'UnicastPackets': '2373129092'
            },
            'sys/switch-A/slot-1/switch-ether/port-20/rx-stats': {
                'BroadcastPackets': '1099918',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-20/rx-stats',
                'MulticastPackets': '1579078',
                'TotalBytes': '4004457090968',
                'UnicastPackets': '2361570431'
            },
            'sys/switch-A/slot-1/switch-ether/port-21/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-21/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-22/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-22/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-23/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-23/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-24/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-24/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-25/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-25/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-26/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-26/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-27/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-27/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-28/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-28/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-29/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-29/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-30/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-30/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-7/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-7/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-8/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-8/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-9/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-9/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-10/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-10/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-11/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-11/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-12/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-12/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-13/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-13/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-14/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-14/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-15/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-15/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-16/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-16/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-17/rx-stats': {
                'BroadcastPackets': '122258',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-17/rx-stats',
                'MulticastPackets': '1527909',
                'TotalBytes': '4279535288715',
                'UnicastPackets': '2671010934'
            },
            'sys/switch-B/slot-1/switch-ether/port-18/rx-stats': {
                'BroadcastPackets': '94263',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-18/rx-stats',
                'MulticastPackets': '1530910',
                'TotalBytes': '4072180590802',
                'UnicastPackets': '2550163237'
            },
            'sys/switch-B/slot-1/switch-ether/port-19/rx-stats': {
                'BroadcastPackets': '81318',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-19/rx-stats',
                'MulticastPackets': '1547672',
                'TotalBytes': '4129479887282',
                'UnicastPackets': '2546795868'
            },
            'sys/switch-B/slot-1/switch-ether/port-20/rx-stats': {
                'BroadcastPackets': '13883616',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-20/rx-stats',
                'MulticastPackets': '2486223',
                'TotalBytes': '4212562062785',
                'UnicastPackets': '2655928449'
            },
            'sys/switch-B/slot-1/switch-ether/port-21/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-21/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-22/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-22/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-23/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-23/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-24/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-24/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-25/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-25/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-26/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-26/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-27/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-27/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-28/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-28/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-29/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-29/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-30/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-30/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-31/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-31/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-32/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-32/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-33/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-33/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-34/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-34/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-35/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-35/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-36/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-36/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-37/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-37/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-38/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-38/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-39/rx-stats': {
                'BroadcastPackets': '503217529',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-39/rx-stats',
                'MulticastPackets': '451179895',
                'TotalBytes': '325471864254',
                'UnicastPackets': '559917156'
            },
            'sys/switch-B/slot-1/switch-ether/port-40/rx-stats': {
                'BroadcastPackets': '621360253',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-40/rx-stats',
                'MulticastPackets': '489310416',
                'TotalBytes': '6466125443913',
                'UnicastPackets': '16412790036'
            },
            'sys/switch-B/slot-1/switch-ether/port-7/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-7/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-8/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-8/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-9/rx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-9/rx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            }
        },
        'etherTxStats': {
            'fabric/lan/A/pc-1/tx-stats': {
                'BroadcastPackets': '1560669',
                'Dn': 'fabric/lan/A/pc-1/tx-stats',
                'MulticastPackets': '963998',
                'TotalBytes': '508742854080',
                'UnicastPackets': '623466604'
            },
            'fabric/lan/B/pc-1/tx-stats': {
                'BroadcastPackets': '5042327',
                'Dn': 'fabric/lan/B/pc-1/tx-stats',
                'MulticastPackets': '977891',
                'TotalBytes': '1056293035699',
                'UnicastPackets': '1526001215'
            },
            'sys/chassis-1/slot-1/host/port-12/tx-stats': {
                'BroadcastPackets': '31027842',
                'Dn': 'sys/chassis-1/slot-1/host/port-12/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/chassis-1/slot-1/host/port-16/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/chassis-1/slot-1/host/port-16/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '20259206624',
                'UnicastPackets': '28300788'
            },
            'sys/chassis-1/slot-1/host/port-29/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/chassis-1/slot-1/host/port-29/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '8276',
                'UnicastPackets': '87377042821'
            },
            'sys/chassis-1/slot-1/host/port-31/tx-stats': {
                'BroadcastPackets': '152666456',
                'Dn': 'sys/chassis-1/slot-1/host/port-31/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '182713123339062',
                'UnicastPackets': '0'
            },
            'sys/chassis-1/slot-1/host/port-4/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/chassis-1/slot-1/host/port-4/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/chassis-1/slot-1/host/port-8/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/chassis-1/slot-1/host/port-8/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/chassis-1/slot-2/host/port-12/tx-stats': {
                'BroadcastPackets': '31028158',
                'Dn': 'sys/chassis-1/slot-2/host/port-12/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/chassis-1/slot-2/host/port-16/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/chassis-1/slot-2/host/port-16/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '18865358320',
                'UnicastPackets': '23589467'
            },
            'sys/chassis-1/slot-2/host/port-29/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/chassis-1/slot-2/host/port-29/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '9830',
                'UnicastPackets': '87612967653'
            },
            'sys/chassis-1/slot-2/host/port-31/tx-stats': {
                'BroadcastPackets': '152667232',
                'Dn': 'sys/chassis-1/slot-2/host/port-31/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '182935433105076',
                'UnicastPackets': '0'
            },
            'sys/chassis-1/slot-2/host/port-4/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/chassis-1/slot-2/host/port-4/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/chassis-1/slot-2/host/port-8/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/chassis-1/slot-2/host/port-8/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-10/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-10/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-11/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-11/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-12/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-12/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-13/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-13/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-14/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-14/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-15/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-15/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-16/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-16/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-17/tx-stats': {
                'BroadcastPackets': '32100470',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-17/tx-stats',
                'MulticastPackets': '29780053',
                'TotalBytes': '67682818314784',
                'UnicastPackets': '32465954049'
            },
            'sys/switch-A/slot-1/switch-ether/port-18/tx-stats': {
                'BroadcastPackets': '27288639',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-18/tx-stats',
                'MulticastPackets': '13939489',
                'TotalBytes': '67659649503111',
                'UnicastPackets': '32450868523'
            },
            'sys/switch-A/slot-1/switch-ether/port-19/tx-stats': {
                'BroadcastPackets': '65183590',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-19/tx-stats',
                'MulticastPackets': '14398383',
                'TotalBytes': '67680063204015',
                'UnicastPackets': '32469355827'
            },
            'sys/switch-A/slot-1/switch-ether/port-20/tx-stats': {
                'BroadcastPackets': '40994656',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-20/tx-stats',
                'MulticastPackets': '10985573',
                'TotalBytes': '67653582675993',
                'UnicastPackets': '32442178134'
            },
            'sys/switch-A/slot-1/switch-ether/port-21/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-21/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-22/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-22/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-23/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-23/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-24/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-24/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-25/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-25/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-26/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-26/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-27/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-27/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-28/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-28/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-29/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-29/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-30/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-30/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-31/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-31/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-32/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-32/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-33/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-33/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-34/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-34/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-35/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-35/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-36/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-36/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-37/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-37/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-38/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-38/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-39/tx-stats': {
                'BroadcastPackets': '1107648',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-39/tx-stats',
                'MulticastPackets': '499453',
                'TotalBytes': '255134958066',
                'UnicastPackets': '311838874'
            },
            'sys/switch-A/slot-1/switch-ether/port-40/tx-stats': {
                'BroadcastPackets': '453021',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-40/tx-stats',
                'MulticastPackets': '464545',
                'TotalBytes': '253607896014',
                'UnicastPackets': '311627730'
            },
            'sys/switch-A/slot-1/switch-ether/port-7/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-7/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-8/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-8/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-A/slot-1/switch-ether/port-9/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-A/slot-1/switch-ether/port-9/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-10/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-10/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-11/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-11/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-12/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-12/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-13/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-13/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-14/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-14/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-15/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-15/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-16/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-16/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-17/tx-stats': {
                'BroadcastPackets': '32111737',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-17/tx-stats',
                'MulticastPackets': '29898043',
                'TotalBytes': '67771511563937',
                'UnicastPackets': '32615801329'
            },
            'sys/switch-B/slot-1/switch-ether/port-18/tx-stats': {
                'BroadcastPackets': '27297800',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-18/tx-stats',
                'MulticastPackets': '14196305',
                'TotalBytes': '67693606295274',
                'UnicastPackets': '32567240018'
            },
            'sys/switch-B/slot-1/switch-ether/port-19/tx-stats': {
                'BroadcastPackets': '65208907',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-19/tx-stats',
                'MulticastPackets': '14346004',
                'TotalBytes': '67815080004453',
                'UnicastPackets': '32656250869'
            },
            'sys/switch-B/slot-1/switch-ether/port-20/tx-stats': {
                'BroadcastPackets': '41008202',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-20/tx-stats',
                'MulticastPackets': '12005117',
                'TotalBytes': '67709065269502',
                'UnicastPackets': '32605946491'
            },
            'sys/switch-B/slot-1/switch-ether/port-21/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-21/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-22/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-22/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-23/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-23/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-24/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-24/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-25/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-25/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-26/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-26/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-27/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-27/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-28/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-28/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-29/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-29/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-30/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-30/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-31/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-31/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-32/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-32/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-33/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-33/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-34/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-34/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-35/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-35/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-36/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-36/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-37/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-37/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-38/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-38/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-39/tx-stats': {
                'BroadcastPackets': '4297755',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-39/tx-stats',
                'MulticastPackets': '446525',
                'TotalBytes': '451717191374',
                'UnicastPackets': '713153873'
            },
            'sys/switch-B/slot-1/switch-ether/port-40/tx-stats': {
                'BroadcastPackets': '744572',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-40/tx-stats',
                'MulticastPackets': '531366',
                'TotalBytes': '604575844325',
                'UnicastPackets': '812847342'
            },
            'sys/switch-B/slot-1/switch-ether/port-7/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-7/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-8/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-8/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            },
            'sys/switch-B/slot-1/switch-ether/port-9/tx-stats': {
                'BroadcastPackets': '0',
                'Dn': 'sys/switch-B/slot-1/switch-ether/port-9/tx-stats',
                'MulticastPackets': '0',
                'TotalBytes': '0',
                'UnicastPackets': '0'
            }
        },
        'fabricFcSanEp': {
            'fabric/san/A/phys-slot-1-port-1': {
                'AdminState': 'enabled',
                'Dn': 'fabric/san/A/phys-slot-1-port-1',
                'EpDn': 'sys/switch-A/slot-1/switch-fc/port-1',
                'OperState': 'up',
                'PortId': '1',
                'SlotId': '1',
                'SwitchId': 'A'
            },
            'fabric/san/A/phys-slot-1-port-2': {
                'AdminState': 'enabled',
                'Dn': 'fabric/san/A/phys-slot-1-port-2',
                'EpDn': 'sys/switch-A/slot-1/switch-fc/port-2',
                'OperState': 'up',
                'PortId': '2',
                'SlotId': '1',
                'SwitchId': 'A'
            },
            'fabric/san/A/phys-slot-1-port-3': {
                'AdminState': 'disabled',
                'Dn': 'fabric/san/A/phys-slot-1-port-3',
                'EpDn': 'sys/switch-A/slot-1/switch-fc/port-3',
                'OperState': 'up',
                'PortId': '3',
                'SlotId': '1',
                'SwitchId': 'A'
            },
            'fabric/san/A/phys-slot-1-port-4': {
                'AdminState': 'disabled',
                'Dn': 'fabric/san/A/phys-slot-1-port-4',
                'EpDn': 'sys/switch-A/slot-1/switch-fc/port-4',
                'OperState': 'up',
                'PortId': '4',
                'SlotId': '1',
                'SwitchId': 'A'
            },
            'fabric/san/A/phys-slot-1-port-5': {
                'AdminState': 'disabled',
                'Dn': 'fabric/san/A/phys-slot-1-port-5',
                'EpDn': 'sys/switch-A/slot-1/switch-fc/port-5',
                'OperState': 'up',
                'PortId': '5',
                'SlotId': '1',
                'SwitchId': 'A'
            },
            'fabric/san/A/phys-slot-1-port-6': {
                'AdminState': 'disabled',
                'Dn': 'fabric/san/A/phys-slot-1-port-6',
                'EpDn': 'sys/switch-A/slot-1/switch-fc/port-6',
                'OperState': 'up',
                'PortId': '6',
                'SlotId': '1',
                'SwitchId': 'A'
            },
            'fabric/san/B/phys-slot-1-port-1': {
                'AdminState': 'enabled',
                'Dn': 'fabric/san/B/phys-slot-1-port-1',
                'EpDn': 'sys/switch-B/slot-1/switch-fc/port-1',
                'OperState': 'up',
                'PortId': '1',
                'SlotId': '1',
                'SwitchId': 'B'
            },
            'fabric/san/B/phys-slot-1-port-2': {
                'AdminState': 'enabled',
                'Dn': 'fabric/san/B/phys-slot-1-port-2',
                'EpDn': 'sys/switch-B/slot-1/switch-fc/port-2',
                'OperState': 'up',
                'PortId': '2',
                'SlotId': '1',
                'SwitchId': 'B'
            },
            'fabric/san/B/phys-slot-1-port-3': {
                'AdminState': 'disabled',
                'Dn': 'fabric/san/B/phys-slot-1-port-3',
                'EpDn': 'sys/switch-B/slot-1/switch-fc/port-3',
                'OperState': 'up',
                'PortId': '3',
                'SlotId': '1',
                'SwitchId': 'B'
            },
            'fabric/san/B/phys-slot-1-port-4': {
                'AdminState': 'disabled',
                'Dn': 'fabric/san/B/phys-slot-1-port-4',
                'EpDn': 'sys/switch-B/slot-1/switch-fc/port-4',
                'OperState': 'up',
                'PortId': '4',
                'SlotId': '1',
                'SwitchId': 'B'
            },
            'fabric/san/B/phys-slot-1-port-5': {
                'AdminState': 'disabled',
                'Dn': 'fabric/san/B/phys-slot-1-port-5',
                'EpDn': 'sys/switch-B/slot-1/switch-fc/port-5',
                'OperState': 'up',
                'PortId': '5',
                'SlotId': '1',
                'SwitchId': 'B'
            },
            'fabric/san/B/phys-slot-1-port-6': {
                'AdminState': 'disabled',
                'Dn': 'fabric/san/B/phys-slot-1-port-6',
                'EpDn': 'sys/switch-B/slot-1/switch-fc/port-6',
                'OperState': 'up',
                'PortId': '6',
                'SlotId': '1',
                'SwitchId': 'B'
            }
        },
        'fcErrStats': {
            'sys/switch-A/slot-1/switch-fc/port-1/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-1/err-stats',
                'Rx': '0',
                'Tx': '0'
            },
            'sys/switch-A/slot-1/switch-fc/port-2/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-2/err-stats',
                'Rx': '0',
                'Tx': '0'
            },
            'sys/switch-A/slot-1/switch-fc/port-3/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-3/err-stats',
                'Rx': '781452119456070',
                'Tx': '0'
            },
            'sys/switch-A/slot-1/switch-fc/port-4/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-4/err-stats',
                'Rx': '751756715578440',
                'Tx': '0'
            },
            'sys/switch-A/slot-1/switch-fc/port-5/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-5/err-stats',
                'Rx': '748131763181460',
                'Tx': '0'
            },
            'sys/switch-A/slot-1/switch-fc/port-6/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-6/err-stats',
                'Rx': '748131763181460',
                'Tx': '0'
            },
            'sys/switch-B/slot-1/switch-fc/port-1/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-1/err-stats',
                'Rx': '0',
                'Tx': '0'
            },
            'sys/switch-B/slot-1/switch-fc/port-2/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-2/err-stats',
                'Rx': '0',
                'Tx': '0'
            },
            'sys/switch-B/slot-1/switch-fc/port-3/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-3/err-stats',
                'Rx': '747994324228020',
                'Tx': '0'
            },
            'sys/switch-B/slot-1/switch-fc/port-4/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-4/err-stats',
                'Rx': '718191546168015',
                'Tx': '0'
            },
            'sys/switch-B/slot-1/switch-fc/port-5/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-5/err-stats',
                'Rx': '714588068607510',
                'Tx': '0'
            },
            'sys/switch-B/slot-1/switch-fc/port-6/err-stats': {
                'CrcRx': '0',
                'DiscardRx': '0',
                'DiscardTx': '0',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-6/err-stats',
                'Rx': '714588068607510',
                'Tx': '0'
            }
        },
        'fcStats': {
            'sys/switch-A/slot-1/switch-fc/port-1/stats': {
                'BytesRx': '27132982650552',
                'BytesTx': '2907081927340',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-1/stats',
                'PacketsRx': '13332289971',
                'PacketsTx': '1590572107',
                'Suspect': 'no'
            },
            'sys/switch-A/slot-1/switch-fc/port-2/stats': {
                'BytesRx': '237293119662108',
                'BytesTx': '12238375145120',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-2/stats',
                'PacketsRx': '115981398636',
                'PacketsTx': '7247679957',
                'Suspect': 'no'
            },
            'sys/switch-A/slot-1/switch-fc/port-3/stats': {
                'BytesRx': '6545461438103280',
                'BytesTx': '12503233911297120',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-3/stats',
                'PacketsRx': '3516538832519610',
                'PacketsTx': '3125791297955100',
                'Suspect': 'no'
            },
            'sys/switch-A/slot-1/switch-fc/port-4/stats': {
                'BytesRx': '6269002983258720',
                'BytesTx': '12028107449255040',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-4/stats',
                'PacketsRx': '3368061813131460',
                'PacketsTx': '3007009682444580',
                'Suspect': 'no'
            },
            'sys/switch-A/slot-1/switch-fc/port-5/stats': {
                'BytesRx': '6269002983258720',
                'BytesTx': '11970108210903360',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-5/stats',
                'PacketsRx': '3349919871277380',
                'PacketsTx': '2992509872856660',
                'Suspect': 'no'
            },
            'sys/switch-A/slot-1/switch-fc/port-6/stats': {
                'BytesRx': '6269002983258720',
                'BytesTx': '11970108210903360',
                'Dn': 'sys/switch-A/slot-1/switch-fc/port-6/stats',
                'PacketsRx': '3349919871277380',
                'PacketsTx': '2992509872856660',
                'Suspect': 'no'
            },
            'sys/switch-B/slot-1/switch-fc/port-1/stats': {
                'BytesRx': '27132984565284',
                'BytesTx': '2905866392424',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-1/stats',
                'PacketsRx': '13332284889',
                'PacketsTx': '1589971733',
                'Suspect': 'no'
            },
            'sys/switch-B/slot-1/switch-fc/port-2/stats': {
                'BytesRx': '237449751667472',
                'BytesTx': '12235876160004',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-2/stats',
                'PacketsRx': '116056665429',
                'PacketsTx': '7246334177',
                'Suspect': 'no'
            },
            'sys/switch-B/slot-1/switch-fc/port-3/stats': {
                'BytesRx': '6001821657771360',
                'BytesTx': '11967977907125040',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-3/stats',
                'PacketsRx': '3366025998633630',
                'PacketsTx': '2991977296912080',
                'Suspect': 'no'
            },
            'sys/switch-B/slot-1/switch-fc/port-4/stats': {
                'BytesRx': '6000859585097280',
                'BytesTx': '11491133458164960',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-4/stats',
                'PacketsRx': '3217012108333605',
                'PacketsTx': '2872766184672060',
                'Suspect': 'no'
            },
            'sys/switch-B/slot-1/switch-fc/port-5/stats': {
                'BytesRx': '6000859585097280',
                'BytesTx': '11433477817196880',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-5/stats',
                'PacketsRx': '3199011900400260',
                'PacketsTx': '2858352274430040',
                'Suspect': 'no'
            },
            'sys/switch-B/slot-1/switch-fc/port-6/stats': {
                'BytesRx': '6000859585097280',
                'BytesTx': '11433477817196880',
                'Dn': 'sys/switch-B/slot-1/switch-fc/port-6/stats',
                'PacketsRx': '3198977540661900',
                'PacketsTx': '2858352274430040',
                'Suspect': 'no'
            },
        }
    }
