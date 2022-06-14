#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.base.plugins.agent_based.ceph_df as ceph_df

SECTION1 = [
    ("SUMMARY", 28536947.359375, 22427607.171875, 0),
    ("ceph-customer", 11599865.779748917, 6827158.5, 0),
    ("ceph-sb", 8122489.228297234, 6827158.5, 0),
    ("device_health_metrics", 6827267.730957031, 6827158.5, 0),
    ("ceph-customer-ec32", 12298968.8203125, 12288886.0, 0),
    ("rbd_ec32", 6827167.351711273, 6827158.5, 0),
]

STRING_TABLE1 = [
    ["15.2.1"],
    [
        '{"stats": {"total_bytes": 29923158114304, "total_avail_bytes": 23517050617856, "total_used_bytes": 6371378987008, "total_used_raw_bytes": 6406107496448, "total_used_raw_ratio": 0.21408526599407196, "num_osds": 30, "num_per_pool_osds": 30, "num_per_pool_omap_osds": 30}, "stats_by_class": {"ssd": {"total_bytes": 29923158114304, "total_avail_bytes": 23517050617856, "total_used_bytes": 6371378987008, "total_used_raw_bytes": 6406107496448, "total_used_raw_ratio": 0.21408526599407196}}, "pools": [{"name": "ceph-customer", "id": 1, "stats": {"stored": 1851559191360, "stored_data": 1850831667200, "stored_omap": 727524160, "objects": 541172, "kb_used": 4887252255, "bytes_used": 5004546308570, "data_bytes_used": 5002363736064, "omap_bytes_used": 2182572506, "percent_used": 0.18898680806159973, "max_avail": 7158794551296, "quota_objects": 0, "quota_bytes": 0, "dirty": 541172, "rd": 2557466288, "rd_bytes": 65823973399552, "wr": 7291734425, "wr_bytes": 131133035820032, "compress_bytes_used": 0, "compress_under_bytes": 0, "stored_raw": 5554677743616, "avail_raw": 21476385194297}}, {"name": "ceph-sb", "id": 2, "stats": {"stored": 455837183232, "stored_data": 455552499712, "stored_omap": 284683520, "objects": 145374, "kb_used": 1326418666, "bytes_used": 1358252713755, "data_bytes_used": 1357398663168, "omap_bytes_used": 854050587, "percent_used": 0.05948212742805481, "max_avail": 7158794551296, "quota_objects": 0, "quota_bytes": 0, "dirty": 145374, "rd": 922997893, "rd_bytes": 220341196681216, "wr": 18022648032, "wr_bytes": 135016178114560, "compress_bytes_used": 0, "compress_under_bytes": 0, "stored_raw": 1367511531520, "avail_raw": 21476385194297}}, {"name": "device_health_metrics", "id": 4, "stats": {"stored": 38178988, "stored_data": 0, "stored_omap": 38178988, "objects": 32, "kb_used": 111853, "bytes_used": 114536960, "data_bytes_used": 0, "omap_bytes_used": 114536960, "percent_used": 5.333129593054764e-06, "max_avail": 7158794551296, "quota_objects": 0, "quota_bytes": 0, "dirty": 32, "rd": 2682, "rd_bytes": 107807744, "wr": 2538, "wr_bytes": 39249920, "compress_bytes_used": 0, "compress_under_bytes": 0, "stored_raw": 114536960, "avail_raw": 21476385194297}}, {"name": "ceph-customer-ec32", "id": 6, "stats": {"stored": 6616424448, "stored_data": 6616424448, "stored_omap": 0, "objects": 1648, "kb_used": 10324808, "bytes_used": 10572603392, "data_bytes_used": 10572603392, "omap_bytes_used": 0, "percent_used": 0.000492047518491745, "max_avail": 12885830926336, "quota_objects": 0, "quota_bytes": 0, "dirty": 1648, "rd": 3518072, "rd_bytes": 32364277760, "wr": 1702485, "wr_bytes": 28672652288, "compress_bytes_used": 1446842368, "compress_under_bytes": 2893103104, "stored_raw": 11027374080, "avail_raw": 21476385194297}}, {"name": "rbd_ec32", "id": 8, "stats": {"stored": 3046864, "stored_data": 2119, "stored_omap": 3044745, "objects": 6, "kb_used": 9065, "bytes_used": 9281692, "data_bytes_used": 147456, "omap_bytes_used": 9134236, "percent_used": 4.321811388763308e-07, "max_avail": 7158794551296, "quota_objects": 0, "quota_bytes": 0, "dirty": 6, "rd": 153817, "rd_bytes": 148212736, "wr": 43558, "wr_bytes": 1871879168, "compress_bytes_used": 0, "compress_under_bytes": 0, "stored_raw": 9140592, "avail_raw": 21476385194297}}]}'
    ],
]


@pytest.mark.parametrize(
    "string_table, section",
    [
        (STRING_TABLE1, SECTION1),
    ],
)
def test_parse_ceph_df_json(string_table, section) -> None:
    assert ceph_df.parse_ceph_df_json(string_table) == section
