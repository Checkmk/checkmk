#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'heartbeat_crm'


freeze_time = '2019-04-11 12:38:36'


info = [[u'Stack:', u'corosync'],
        [u'Current',
         u'DC:',
         u'cluster',
         u'(version',
         u'1.1.16-12.el7_4.8-94ff4df)',
         u'-',
         u'partition',
         u'with',
         u'quorum'],
        [u'Last', u'updated:', u'Tue', u'Oct', u'26', u'13:58:47', u'2019'],
        [u'Last',
         u'change:',
         u'Sat',
         u'Oct',
         u'24',
         u'10:54:28',
         u'2019',
         u'by',
         u'root',
         u'via',
         u'cibadmin',
         u'on',
         u'cluster'],
        [u'2', u'nodes', u'configured'],
        [u'6', u'resources', u'configured'],
        [u'Online:', u'[', u'cluster1', u'cluster2', u']'],
        [u'Full', u'list', u'of', u'resources:'],
        [u'Resource', u'Group:', u'mysqldb1'],
        [u'_', u'mysqldb1_lvm', u'(ocf::heartbeat:LVM):Started', u'cluster1'],
        [u'_', u'mysqldb1_fs', u'(ocf::heartbeat:Filesystem):Started', u'cluster1'],
        [u'_', u'mysqldb1_ip', u'(ocf::heartbeat:IPaddr2):Started', u'cluster1'],
        [u'_', u'mysqldb1_mysql', u'(service:mysqldb1):Started', u'cluster1'],
        [u'cluster1_fence(stonith:fence_ipmilan):', u'Started', u'cluster2'],
        [u'cluster2_fence(stonith:fence_ipmilan):', u'Started', u'cluster1'],
        [u'Failed', u'Actions:'],
        [u'*',
         u'mysqldb1_lvm_monitor_10000',
         u'on',
         u'cluster1',
         u"'unknown",
         u"error'",
         u'(1):',
         u'call=158,',
         u'status=Timed',
         u'Out,',
         u"exitreason='none',"],
        [u'_',
         u"last-rc-change='Fri",
         u'Feb',
         u'22',
         u'22:54:52',
         u"2019',",
         u'queued=0ms,',
         u'exec=0ms']]


discovery = {'': [(None, {'num_nodes': 2, 'num_resources': 6})],
             'resources': [(u'cluster1_fence(stonith:fence_ipmilan):', {}),
                           (u'cluster2_fence(stonith:fence_ipmilan):', {}),
                           (u'mysqldb1', {})]}


checks = {
    '': [
        (None,
         {'max_age': 60, 'num_nodes': 2, 'num_resources': 6},
         [(0, u'DC: cluster', []),
          (0, u'Nodes: 2', []),
          (0, u'Resources: 6', [])]),
        (None,
         {'max_age': 60, 'num_nodes': 2, 'num_resources': 6, 'show_failed_actions': True},
         [(0, u'DC: cluster', []),
          (0, u'Nodes: 2', []),
          (0, u'Resources: 6', []),
          (1, u"Failed: mysqldb1_lvm_monitor_10000 on cluster1 'unknown error' (1): call=158, "
              u"status=Timed Out, exitreason='none', last-rc-change='Fri Feb 22 22:54:52 2019', "
              u"queued=0ms, exec=0ms", [])]),
    ],
    'resources': [
        (u'cluster1_fence(stonith:fence_ipmilan):',
         {},
         [(0,
           u'cluster1_fence(stonith:fence_ipmilan): Started cluster2',
           []),
          (2, u'Resource is in state "cluster2"', [])]),
        (u'cluster2_fence(stonith:fence_ipmilan):',
         {},
         [(0,
           u'cluster2_fence(stonith:fence_ipmilan): Started cluster1',
           []),
          (2, u'Resource is in state "cluster1"', [])]),
        (u'mysqldb1',
         {},
         [(0,
           u'mysqldb1_lvm (ocf::heartbeat:LVM):Started cluster1',
           []),
          (2, u'Resource is in state "cluster1"', []),
          (0,
           u'mysqldb1_fs (ocf::heartbeat:Filesystem):Started cluster1',
           []),
          (2, u'Resource is in state "cluster1"', []),
          (0,
           u'mysqldb1_ip (ocf::heartbeat:IPaddr2):Started cluster1',
           []),
          (2, u'Resource is in state "cluster1"', []),
          (0,
           u'mysqldb1_mysql (service:mysqldb1):Started cluster1',
           []),
          (2, u'Resource is in state "cluster1"', [])])
    ],
}
