#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore
checkname = 'ceph_status'

info = [
    ['{'], ['"health":', '{'], ['"health":', '{'], ['"health_services":', '['],
    ['{'], ['"mons":', '['], ['{'], ['"name":', '"charon",'],
    ['"kb_total":', '72662176,'], ['"kb_used":', '4845960,'],
    ['"kb_avail":', '66764460,'], ['"avail_percent":', '91,'],
    ['"last_updated":', '"2017-04-11', '09:51:22.695117",'],
    ['"store_stats":', '{'], ['"bytes_total":', '731100461,'],
    ['"bytes_sst":', '0,'], ['"bytes_log":', '1384653,'],
    ['"bytes_misc":', '729715808,'], ['"last_updated":', '"0.000000"'], ['},'],
    ['"health":', '"HEALTH_OK"'], ['},'], ['{'], ['"name":', '"nix",'],
    ['"kb_total":', '74724384,'], ['"kb_used":', '4774220,'],
    ['"kb_avail":', '68869076,'], ['"avail_percent":', '92,'],
    ['"last_updated":', '"2017-04-11', '09:50:58.026649",'],
    ['"store_stats":', '{'], ['"bytes_total":', '728622881,'],
    ['"bytes_sst":', '0,'], ['"bytes_log":', '969152,'],
    ['"bytes_misc":', '727653729,'], ['"last_updated":', '"0.000000"'], ['},'],
    ['"health":', '"HEALTH_OK"'], ['},'], ['{'], ['"name":', '"hydra",'],
    ['"kb_total":', '74724384,'], ['"kb_used":', '4846784,'],
    ['"kb_avail":', '68796512,'], ['"avail_percent":', '92,'],
    ['"last_updated":', '"2017-04-11', '09:51:25.695034",'],
    ['"store_stats":', '{'], ['"bytes_total":', '729631480,'],
    ['"bytes_sst":', '0,'], ['"bytes_log":', '2220377,'],
    ['"bytes_misc":', '727411103,'], ['"last_updated":', '"0.000000"'], ['},'],
    ['"health":', '"HEALTH_OK"'], ['}'], [']'], ['}'], [']'], ['},'],
    ['"timechecks":', '{'], ['"epoch":', '108,'], ['"round":', '31626,'],
    ['"round_status":', '"finished",'], ['"mons":', '['], ['{'],
    ['"name":', '"charon",'], ['"skew":', '0.000000,'],
    ['"latency":', '0.000000,'], ['"health":', '"HEALTH_OK"'], ['},'], ['{'],
    ['"name":', '"nix",'], ['"skew":', '0.000000,'],
    ['"latency":', '0.000264,'], ['"health":', '"HEALTH_OK"'], ['},'], ['{'],
    ['"name":', '"hydra",'], ['"skew":', '0.000000,'],
    ['"latency":', '0.000274,'], ['"health":', '"HEALTH_OK"'], ['}'], [']'],
    ['},'], ['"summary":', '['], ['{'], ['"severity":', '"HEALTH_WARN",'],
    [
        '"summary":', '"too', 'many', 'PGs', 'per', 'OSD', '(409', '>', 'max',
        '300)"'
    ], ['},'], ['{'], ['"severity":', '"HEALTH_WARN",'],
    [
        '"summary":', '"pool', 'cephfs01', 'has', 'many', 'more', 'objects',
        'per', 'pg', 'than', 'average', '(too', 'few', 'pgs?)"'
    ], ['}'], ['],'], ['"overall_status":', '"HEALTH_WARN",'],
    ['"detail":', '[]'], ['},'],
    ['"fsid":', '"d9d08723-81e5-46b8-b2a4-b1590bc284c4",'],
    ['"election_epoch":', '108,'], ['"quorum":', '['], ['0,'], ['1,'], ['2'],
    ['],'], ['"quorum_names":', '['], ['"charon",'], ['"nix",'], ['"hydra"'],
    ['],'], ['"monmap":', '{'], ['"epoch":', '1,'],
    ['"fsid":', '"d9d08723-81e5-46b8-b2a4-b1590bc284c4",'],
    ['"modified":', '"0.000000",'], ['"created":', '"0.000000",'],
    ['"mons":', '['], ['{'], ['"rank":', '0,'], ['"name":', '"charon",'],
    ['"addr":', '"10.249.12.121:6789\\/0"'], ['},'], ['{'], ['"rank":', '1,'],
    ['"name":', '"nix",'], ['"addr":', '"10.249.12.122:6789\\/0"'], ['},'],
    ['{'], ['"rank":', '2,'], ['"name":', '"hydra",'],
    ['"addr":', '"10.249.12.123:6789\\/0"'], ['}'], [']'], ['},'],
    ['"osdmap":', '{'], ['"osdmap":', '{'], ['"epoch":', '95921,'],
    ['"num_osds":', '90,'], ['"num_up_osds":',
                             '90,'], ['"num_in_osds":', '90,'],
    ['"nearfull":', 'false,'], ['"num_remapped_pgs":', '0'], ['}'], ['},'],
    ['"pgmap":', '{'], ['"pgs_by_state":', '['], ['{'],
    ['"state_name":', '"active+clean",'], ['"count":', '6400'], ['}'], ['],'],
    ['"version":', '15285527,'], ['"num_pgs":', '6400,'],
    ['"data_bytes":', '9321031634464,'], ['"bytes_used":', '14768864055296,'],
    ['"bytes_avail":', '205284138250240,'],
    ['"bytes_total":', '220053002305536,'], ['"read_bytes_sec":', '291,'],
    ['"read_op_per_sec":', '0,'], ['"write_op_per_sec":', '0'], ['},'],
    ['"fsmap":', '{'], ['"epoch":', '35,'], ['"id":', '1,'], ['"up":', '1,'],
    ['"in":', '1,'], ['"max":', '1,'], ['"by_rank":', '['], ['{'],
    ['"filesystem_id":', '1,'], ['"rank":', '0,'], ['"name":', '"nix",'],
    ['"status":', '"up:active"'], ['}'], ['],'], ['"up:standby":', '2'], ['}'],
    ['}']
]

discovery = {
    '': [(None, {})],
    'osds': [(None, {})],
    'pgs': [(None, {})],
    'mgrs': []
}

checks = {
    '': [
        (
            None, {
                'epoch': (1, 3, 30)
            }, [
                (1, 'Health: warning', []),
                (0, 'Epoch rate (30 minutes 0 seconds average): 0.00', [])
            ]
        )
    ],
    'osds': [
        (
            None, {
                'epoch': (50, 100, 15),
                'num_out_osds': (7.0, 5.0),
                'num_down_osds': (7.0, 5.0)
            }, [
                (0, 'Epoch rate (15 minutes 0 seconds average): 0.00', []),
                (0, 'OSDs: 90, Remapped PGs: 0', []),
                (0, 'OSDs out: 0, 0%', []), (0, 'OSDs down: 0, 0%', [])
            ]
        )
    ],
    'pgs': [(None, {}, [(0, "PGs: 6400, Status 'active+clean': 6400", [])])]
}
