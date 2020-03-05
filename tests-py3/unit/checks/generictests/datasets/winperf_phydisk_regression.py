#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = 'winperf_phydisk'


info = [[None, u'1435670669.29', u'234'],
        [None, u'2', u'instances:', u'0_C:', u'_Total'],
        [None, u'-36', u'0', u'0', u'rawcount'],
        [None, u'-34', u'2446915000', u'2446915000', u'type(20570500)'],
        [None,
         u'-34',
         u'130801442692895024',
         u'130801442692895024',
         u'type(40030500)'],
        [None, u'1166', u'2446915000', u'2446915000', u'type(550500)'],
        [None, u'-32', u'1552698000', u'1552698000', u'type(20570500)'],
        [None,
         u'-32',
         u'130801442692895024',
         u'130801442692895024',
         u'type(40030500)'],
        [None, u'1168', u'1552698000', u'1552698000', u'type(550500)'],
        [None, u'-30', u'894217000', u'894217000', u'type(20570500)'],
        [None,
         u'-30',
         u'130801442692895024',
         u'130801442692895024',
         u'type(40030500)'],
        [None, u'1170', u'894217000', u'894217000', u'type(550500)'],
        [None, u'-28', u'732825839', u'732825839', u'average_timer'],
        [None, u'-28', u'64858', u'64858', u'average_base'],
        [None, u'-26', u'465017058', u'465017058', u'average_timer'],
        [None, u'-26', u'40852', u'40852', u'average_base'],
        [None, u'-24', u'267808781', u'267808781', u'average_timer'],
        [None, u'-24', u'24006', u'24006', u'average_base'],
        [None, u'-22', u'64858', u'64858', u'counter'],
        [None, u'-20', u'40852', u'40852', u'counter'],
        [None, u'-18', u'24006', u'24006', u'counter'],
        [None, u'-16', u'2644868608', u'2644868608', u'bulk_count'],
        [None, u'-14', u'1725201408', u'1725201408', u'bulk_count'],
        [None, u'-12', u'919667200', u'919667200', u'bulk_count'],
        [None, u'-10', u'2644868608', u'2644868608', u'average_bulk'],
        [None, u'-10', u'64858', u'64858', u'average_base'],
        [None, u'-8', u'1725201408', u'1725201408', u'average_bulk'],
        [None, u'-8', u'40852', u'40852', u'average_base'],
        [None, u'-6', u'919667200', u'919667200', u'average_bulk'],
        [None, u'-6', u'24006', u'24006', u'average_base'],
        [None, u'1248', u'103228432000', u'103228432000', u'type(20570500)'],
        [None,
         u'1248',
         u'130801442692895024',
         u'130801442692895024',
         u'type(40030500)'],
        [None, u'1250', u'7908', u'7908', u'counter']]


discovery = {'': [('SUMMARY', 'diskstat_default_levels')]}


checks = {
    '': [
        ('SUMMARY', {}, [
            (0, 'Read: 0.00 B/s', [('disk_read_throughput', 0.0, None, None, None, None)]),
            (0, 'Write: 0.00 B/s', [('disk_write_throughput', 0.0, None, None, None, None)]),
            (0, 'Average Read Queue Length: 0.00', [('disk_read_ql', 0.0, None, None, None, None)]),
            (0, 'Average Write Queue Length: 0.00', [('disk_write_ql', 0.0, None, None, None, None)]),
            (0, 'Read operations: 0.00 1/s', [('disk_read_ios', 0.0, None, None, None, None)]),
            (0, 'Write operations: 0.00 1/s', [('disk_write_ios', 0.0, None, None, None, None)]),
        ]),
        ('SUMMARY', {"read_ios": (-2, 2), "write_ios": (-4, -2)}, [
            (0, 'Read: 0.00 B/s', [('disk_read_throughput', 0.0, None, None, None, None)]),
            (0, 'Write: 0.00 B/s', [('disk_write_throughput', 0.0, None, None, None, None)]),
            (0, 'Average Read Queue Length: 0.00', [('disk_read_ql', 0.0, None, None, None, None)]),
            (0, 'Average Write Queue Length: 0.00', [('disk_write_ql', 0.0, None, None, None, None)]),
            (1, 'Read operations: 0.00 1/s (warn/crit at -2.00 1/s/2.00 1/s)', [
                ('disk_read_ios', 0.0, -2, 2, None, None)]),
            (2, 'Write operations: 0.00 1/s (warn/crit at -4.00 1/s/-2.00 1/s)', [
                ('disk_write_ios', 0.0, -4, -2, None, None)]),
        ]),
    ],
}
