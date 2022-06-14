#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

from cmk.base.plugins.agent_based.esx_vsphere_vm import parse_esx_vsphere_vm

checkname = 'esx_vsphere_vm'


parsed = parse_esx_vsphere_vm([
    [u'config.datastoreUrl',
         u'maintenanceMode',
         u'normal|url',
         u'ds:///vmfs/volumes/vsan:5239d5cbf4c95b8c-5977b0e019a35313/|uncommitted',
         u'9278987431936|name',
         u'vsanDatastore|type',
         u'vsan|accessible',
         u'true|capacity',
         u'31686121226240|freeSpace',
         u'20938787651584'],
        [u'config.hardware.device',
         u'virtualDeviceType',
         u'VirtualVmxnet3|label',
         u'Network',
         u'adapter',
         u'1|summary',
         u'DVSwitch:',
         u'49',
         u'76',
         u'2d',
         u'50',
         u'6a',
         u'ee',
         u'f6',
         u'2b-88',
         u'3f',
         u'37',
         u'1c',
         u'6c',
         u'44',
         u'cd',
         u'29|startConnected',
         u'true|allowGuestControl',
         u'true|connected',
         u'true|status',
         u'ok'],
        [u'config.hardware.memoryMB', u'16384'],
        [u'config.hardware.numCPU', u'4'],
        [u'config.hardware.numCoresPerSocket', u'4'],
        [u'config.template', u'false'],
        [u'guest.toolsVersion', u'2147483647'],
        [u'guest.toolsVersionStatus', u'guestToolsUnmanaged'],
        [u'guestHeartbeatStatus', u'green'],
        [u'name', u'scwagprc01.widag.local'],
        [u'runtime.host', u'zh1wagesx02.widag.local'],
        [u'runtime.powerState', u'poweredOn'],
        [u'summary.guest.hostName', u'ntnx-10-78-142-100-a-cvm'],
        [u'summary.quickStats.balloonedMemory', u'0'],
        [u'summary.quickStats.compressedMemory', u'0'],
        [u'summary.quickStats.consumedOverheadMemory', u'78'],
        [u'summary.quickStats.distributedCpuEntitlement', u'2936'],
        [u'summary.quickStats.distributedMemoryEntitlement', u'8049'],
        [u'summary.quickStats.guestMemoryUsage', u'4423'],
        [u'summary.quickStats.hostMemoryUsage', u'16354'],
        [u'summary.quickStats.overallCpuDemand', u'3479'],
        [u'summary.quickStats.overallCpuUsage', u'3479'],
        [u'summary.quickStats.privateMemory', u'16276'],
        [u'summary.quickStats.sharedMemory', u'102'],
        [u'summary.quickStats.staticCpuEntitlement', u'5167'],
        [u'summary.quickStats.staticMemoryEntitlement', u'16532'],
        [u'summary.quickStats.swappedMemory', u'0'],
        [u'summary.quickStats.uptimeSeconds', u'262571'],
    ],
)


discovery = {'cpu': [(None, None)],
             'datastores': [(None, None)],
             'guest_tools': [(None, {})],
             'heartbeat': [(None, {})],
             'mem_usage': [(None, {})],
             'mounted_devices': [(None, None)],
             'name': [(None, None)],
             'running_on': [(None, None)],
             }


checks = {'cpu': [(None,
                   {},
                   [(0,
                     'demand is 3.479 Ghz, 4 virtual CPUs',
                     [('demand', 3479, None, None, None, None)])])],
          'datastores': [(None,
                          {},
                          [(0, u'Stored on vsanDatastore (28.8 TiB/66.1% free)', [])])],
          'guest_tools': [(None,
                           {},
                           [(0,
                             'VMware Tools are installed, but are not managed by VMWare',
                             [])])],
          'heartbeat': [(None, {}, [(0, u'Heartbeat status is green', [])])],
          'mem_usage': [(None,
                         {'host': (10000000000, 20000000000)},
                         [
                             (1, 'Host: 16.0 GiB (warn/crit at 9.31 GiB/18.6 GiB)', [('host', 17148411904.0, 10000000000, 20000000000, None, None)]),
                             (0, 'Guest: 4.32 GiB', [('guest', 4637851648.0, None, None, None, None)]),
                             (0, 'Ballooned: 0 B', [('ballooned', 0.0, None, None, None, None)]),
                             (0, 'Private: 15.9 GiB', [('private', 17066622976.0, None, None, None, None)]),
                             (0, 'Shared: 102 MiB', [('shared', 106954752.0, None, None, None, None)]),
                            ])],
          'mounted_devices': [(None, {}, [(0, 'HA functionality guaranteed', [])])],
          'name': [(None, {}, [(0, u'scwagprc01.widag.local', [])])],
          'running_on': [(None, {}, [(0, u'Running on zh1wagesx02.widag.local', [])])],
}
