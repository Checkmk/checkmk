#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based import esx_vsphere_counters


def test_parse_esx_vsphere_counters():
    assert esx_vsphere_counters.parse_esx_vsphere_counters(
        [['disk.numberRead', 'naa.5000cca05688e814', '0#0', 'number'],
         ['disk.numberRead', 'naa.60002ac0000000000000000e0000586d', '0#0', 'number'],
         ['disk.write', 'naa.6000eb39f31c58130000000000000015', '0#0', 'kiloBytesPerSecond'],
         ['net.bytesRx', 'vmnic0', '1#1', 'kiloBytesPerSecond'],
         ['net.droppedRx', 'vmnic1', '0#0', 'number'], ['net.errorsRx', '', '0#0', 'number'],
         ['net.errorsRx', 'vmnic2', '0#0', 'number'], ['net.errorsTx', '', '0#0', 'number'],
         ['net.packetsTx', '', '3162#3488', 'number'],
         ['net.received', 'vmnic0', '1#1', 'kiloBytesPerSecond'],
         ['net.received', 'vmnic5', '63#46', 'kiloBytesPerSecond'],
         ['net.transmitted', 'vmnic3', '0#0', 'kiloBytesPerSecond'],
         ['sys.resourceMemConsumed', 'host/user', '83527720#83529784', 'kiloBytes'],
         ['sys.resourceMemConsumed', 'host/vim/vmvisor', '291820#291832', 'kiloBytes'],
         ['sys.resourceMemConsumed', 'host/vim/vmvisor/init', '1568#1568', 'kiloBytes'],
         ['sys.resourceMemConsumed', 'host/vim/vmvisor/ntpd', '1572#1572', 'kiloBytes'],
         ['sys.resourceMemConsumed', 'host/vim/vmvisor/vmkdevmgr', '5304#5304', 'kiloBytes'],
         ['sys.resourceMemConsumed', 'host/vim/vmvisor/vmsupport', '0#0', 'kiloBytes'],
         ['sys.resourceMemConsumed', 'host/vim/vmvisor/vvold', '9192#9192', 'kiloBytes'],
         ['net.macaddress', 'vmnic4', '64:51:06:f0:c5:d0', 'mac']]) == {
             'disk.numberRead': {
                 'naa.5000cca05688e814': [(['0', '0'], 'number')],
                 'naa.60002ac0000000000000000e0000586d': [(['0', '0'], 'number')]
             },
             'disk.write': {
                 'naa.6000eb39f31c58130000000000000015': [(['0', '0'], 'kiloBytesPerSecond')]
             },
             'net.bytesRx': {
                 'vmnic0': [(['1', '1'], 'kiloBytesPerSecond')]
             },
             'net.droppedRx': {
                 'vmnic1': [(['0', '0'], 'number')]
             },
             'net.errorsRx': {
                 '': [(['0', '0'], 'number')],
                 'vmnic2': [(['0', '0'], 'number')]
             },
             'net.errorsTx': {
                 '': [(['0', '0'], 'number')]
             },
             'net.macaddress': {
                 'vmnic4': [(['64:51:06:f0:c5:d0'], 'mac')]
             },
             'net.packetsTx': {
                 '': [(['3162', '3488'], 'number')]
             },
             'net.received': {
                 'vmnic0': [(['1', '1'], 'kiloBytesPerSecond')],
                 'vmnic5': [(['63', '46'], 'kiloBytesPerSecond')]
             },
             'net.transmitted': {
                 'vmnic3': [(['0', '0'], 'kiloBytesPerSecond')]
             },
             'sys.resourceMemConsumed': {
                 'host/user': [(['83527720', '83529784'], 'kiloBytes')],
                 'host/vim/vmvisor': [(['291820', '291832'], 'kiloBytes')],
                 'host/vim/vmvisor/init': [(['1568', '1568'], 'kiloBytes')],
                 'host/vim/vmvisor/ntpd': [(['1572', '1572'], 'kiloBytes')],
                 'host/vim/vmvisor/vmkdevmgr': [(['5304', '5304'], 'kiloBytes')],
                 'host/vim/vmvisor/vmsupport': [(['0', '0'], 'kiloBytes')],
                 'host/vim/vmvisor/vvold': [(['9192', '9192'], 'kiloBytes')]
             }
         }
