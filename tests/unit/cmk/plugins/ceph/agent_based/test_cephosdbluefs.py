#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Service
from cmk.plugins.ceph.agent_based.cephosdbluefs import (
    discovery_cephosdbluefs_db,
    discovery_cephosdbluefs_slow,
    discovery_cephosdbluefs_wal,
    parse_cephosdbluefs,
)

STRING_TABLE = [
    [
        '{"end": {}, "0": {"bluefs": {"db_total_bytes": 7681481900032, "db_used_bytes": 1404056371'
        "2, "
        '"wal_total_bytes": 123, "wal_used_bytes": 456, '  # tampered with
        '"slow_total_bytes": 0, "slow_used_bytes": 0'
        ', "num_files": 232, "log_bytes": 6303744, "log_compactions": 83406, "log_write_count": 33'
        '9045129, "logged_bytes": 1388728901632, "files_written_wal": 60333, "files_written_sst": '
        '22429, "write_count_wal": 338843306, "write_count_sst": 928749, "bytes_written_wal": 2288'
        '951676928, "bytes_written_sst": 491151826944, "bytes_written_slow": 0, "max_bytes_wal": 0'
        ', "max_bytes_db": 19242024960, "max_bytes_slow": 0, "alloc_unit_main": 0, "alloc_unit_db"'
        ': 65536, "alloc_unit_wal": 0, "read_random_count": 20389379, "read_random_bytes": 5723605'
        '03191, "read_random_disk_count": 10001020, "read_random_disk_bytes": 531106772026, "read_'
        'random_disk_bytes_wal": 0, "read_random_disk_bytes_db": 531106772026, "read_random_disk_b'
        'ytes_slow": 0, "read_random_buffer_count": 10522889, "read_random_buffer_bytes": 41253731'
        '165, "read_count": 3109904, "read_bytes": 114321741948, "read_disk_count": 2323489, "read'
        '_disk_bytes": 93161410560, "read_disk_bytes_wal": 0, "read_disk_bytes_db": 93161414656, "'
        'read_disk_bytes_slow": 0, "read_prefetch_count": 3081261, "read_prefetch_bytes": 11343480'
        '2557, "write_count": 678914654, "write_disk_count": 679096544, "write_bytes": 41798274580'
        '48, "compact_lat": {"avgcount": 83427, "sum": 62.599810092, "avgtime": 0.000750354}, "com'
        'pact_lock_lat": {"avgcount": 83406, "sum": 27.48880848, "avgtime": 0.000329578}, "alloc_s'
        'low_fallback": 0, "alloc_slow_size_fallback": 0, "read_zeros_candidate": 0, "read_zeros_e'
        'rrors": 0}}, "1": {"bluefs": {"db_total_bytes": 7681481900032, "db_used_bytes": 132190699'
        '52, "wal_total_bytes": 0, "wal_used_bytes": 0, "slow_total_bytes": 0, "slow_used_bytes": '
        '0, "num_files": 205, "log_bytes": 7704576, "log_compactions": 67979, "log_write_count": 2'
        '76333535, "logged_bytes": 1131862171648, "files_written_wal": 40197, "files_written_sst":'
        ' 14619, "write_count_wal": 276187156, "write_count_sst": 469557, "bytes_written_wal": 173'
        '4980427776, "bytes_written_sst": 246828310528, "bytes_written_slow": 0, "max_bytes_wal": '
        '0, "max_bytes_db": 16054026240, "max_bytes_slow": 0, "alloc_unit_main": 0, "alloc_unit_db'
        '": 65536, "alloc_unit_wal": 0, "read_random_count": 14928692, "read_random_bytes": 307629'
        '101126, "read_random_disk_count": 7084682, "read_random_disk_bytes": 276583005758, "read_'
        'random_disk_bytes_wal": 0, "read_random_disk_bytes_db": 276583005758, "read_random_disk_b'
        'ytes_slow": 0, "read_random_buffer_count": 7930782, "read_random_buffer_bytes": 310460953'
        '68, "read_count": 2224061, "read_bytes": 82615028060, "read_disk_count": 1615219, "read_d'
        'isk_bytes": 65941417984, "read_disk_bytes_wal": 0, "read_disk_bytes_db": 65941422080, "re'
        'ad_disk_bytes_slow": 0, "read_prefetch_count": 2194649, "read_prefetch_bytes": 8173717011'
        '0, "write_count": 553067566, "write_disk_count": 553191930, "write_bytes": 3122622775296,'
        ' "compact_lat": {"avgcount": 67987, "sum": 44.991480303, "avgtime": 0.000661765}, "compac'
        't_lock_lat": {"avgcount": 67979, "sum": 18.98473363, "avgtime": 0.000279273}, "alloc_slow'
        '_fallback": 0, "alloc_slow_size_fallback": 0, "read_zeros_candidate": 0, "read_zeros_erro'
        'rs": 0}}, "2": {"bluefs": {"db_total_bytes": 7681481900032, "db_used_bytes": 9904193536, '
        '"wal_total_bytes": 0, "wal_used_bytes": 0, "slow_total_bytes": 0, "slow_used_bytes": 0, "'
        'num_files": 182, "log_bytes": 6975488, "log_compactions": 69820, "log_write_count": 28381'
        '8371, "logged_bytes": 1162520059904, "files_written_wal": 50438, "files_written_sst": 170'
        '32, "write_count_wal": 283652936, "write_count_sst": 695879, "bytes_written_wal": 1913094'
        '324224, "bytes_written_sst": 368069107712, "bytes_written_slow": 0, "max_bytes_wal": 0, "'
        'max_bytes_db": 14614462464, "max_bytes_slow": 0, "alloc_unit_main": 0, "alloc_unit_db": 6'
        '5536, "alloc_unit_wal": 0, "read_random_count": 14314484, "read_random_bytes": 4259375113'
        '47, "read_random_disk_count": 6087230, "read_random_disk_bytes": 393391100877, "read_rand'
        'om_disk_bytes_wal": 0, "read_random_disk_bytes_db": 393391100877, "read_random_disk_bytes'
        '_slow": 0, "read_random_buffer_count": 8322503, "read_random_buffer_bytes": 32546410470, '
        '"read_count": 1988282, "read_bytes": 73174573388, "read_disk_count": 1353943, "read_disk_'
        'bytes": 55817281536, "read_disk_bytes_wal": 0, "read_disk_bytes_db": 55817285632, "read_d'
        'isk_bytes_slow": 0, "read_prefetch_count": 1953487, "read_prefetch_bytes": 72081858726, "'
        'write_count": 568248785, "write_disk_count": 568384101, "write_bytes": 3452887195648, "co'
        'mpact_lat": {"avgcount": 69834, "sum": 47.504663203, "avgtime": 0.000680251}, "compact_lo'
        'ck_lat": {"avgcount": 69820, "sum": 20.141270723, "avgtime": 0.000288474}, "alloc_slow_fa'
        'llback": 0, "alloc_slow_size_fallback": 0, "read_zeros_candidate": 0, "read_zeros_errors"'
        ': 0}}, "3": {"bluefs": {"db_total_bytes": 7681481900032, "db_used_bytes": 11931287552, "w'
        'al_total_bytes": 0, "wal_used_bytes": 0, '
        '"slow_total_bytes": 2, "slow_used_bytes": 1, '  # tampered with
        '"nu'
        'm_files": 190, "log_bytes": 10362880, "log_compactions": 67518, "log_write_count": 274460'
        '802, "logged_bytes": 1124191457280, "files_written_wal": 43889, "files_written_sst": 1571'
        '9, "write_count_wal": 274308223, "write_count_sst": 514575, "bytes_written_wal": 17808912'
        '05632, "bytes_written_sst": 270489272320, "bytes_written_slow": 0, "max_bytes_wal": 0, "m'
        'ax_bytes_db": 16012017664, "max_bytes_slow": 0, "alloc_unit_main": 0, "alloc_unit_db": 65'
        '536, "alloc_unit_wal": 0, "read_random_count": 14375808, "read_random_bytes": 32819404801'
        '5, "read_random_disk_count": 6906964, "read_random_disk_bytes": 298612745006, "read_rando'
        'm_disk_bytes_wal": 0, "read_random_disk_bytes_db": 298612745006, "read_random_disk_bytes_'
        'slow": 0, "read_random_buffer_count": 7560016, "read_random_buffer_bytes": 29581303009, "'
        'read_count": 2230616, "read_bytes": 79834117734, "read_disk_count": 1649923, "read_disk_b'
        'ytes": 63887679488, "read_disk_bytes_wal": 0, "read_disk_bytes_db": 63887683584, "read_di'
        'sk_bytes_slow": 0, "read_prefetch_count": 2217180, "read_prefetch_bytes": 79462494893, "w'
        'rite_count": 549361398, "write_disk_count": 549489791, "write_bytes": 3184467472384, "com'
        'pact_lat": {"avgcount": 67528, "sum": 44.826896133, "avgtime": 0.000663826}, "compact_loc'
        'k_lat": {"avgcount": 67518, "sum": 18.821832839, "avgtime": 0.000278767}, "alloc_slow_fal'
        'lback": 0, "alloc_slow_size_fallback": 0, "read_zeros_candidate": 0, "read_zeros_errors":'
        " 0}}}"
    ]
]


def test_discovery_cephosdbluefs_db() -> None:
    assert list(discovery_cephosdbluefs_db(parse_cephosdbluefs(STRING_TABLE))) == [
        Service(item="0"),
        Service(item="1"),
        Service(item="2"),
        Service(item="3"),
    ]


def test_discovery_cephosdbluefs_wal() -> None:
    assert list(discovery_cephosdbluefs_wal(parse_cephosdbluefs(STRING_TABLE))) == [
        Service(item="0"),
    ]


def test_discovery_cephosdbluefs_slow() -> None:
    assert list(discovery_cephosdbluefs_slow(parse_cephosdbluefs(STRING_TABLE))) == [
        Service(item="3"),
    ]
