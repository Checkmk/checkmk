#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from contextlib import ExitStack
from pathlib import Path

import pytest

from cmk.special_agents.agent_proxmox_ve import BackupTask, collect_vm_backup_info


@pytest.mark.parametrize(
    "logfile, expected_results, expected_exception",
    (
        (
            "proxmox_ve-backup-2020-12-30.log",
            {
                "105": {
                    "started_time": "2020-12-30 22:15:02",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-105-2020_12_30-22_15_02.vma.lzo",
                    "transfer_size": 32212254720,
                    "transfer_time": 137,
                    "archive_size": 5740000000,
                    "total_duration": 173,
                },
                "110": {
                    "started_time": "2020-12-30 22:17:55",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-lxc-110-2020_12_30-22_17_55.tar.lzo",
                    "bytes_written_size": 18494433280,
                    "bytes_written_bandwidth": 102760448,
                    "archive_size": 7480000000,
                    "total_duration": 205,
                },
                "114": {
                    "started_time": "2020-12-30 22:21:20",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-114-2020_12_30-22_21_20.vma.lzo",
                    "transfer_size": 42949672960,
                    "transfer_time": 198,
                    "archive_size": 24510000000,
                    "total_duration": 278,
                },
                "115": {
                    "started_time": "2020-12-30 22:25:58",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-115-2020_12_30-22_25_58.vma.lzo",
                    "transfer_size": 85899345920,
                    "transfer_time": 221,
                    "archive_size": 4690000000,
                    "total_duration": 223,
                },
                "117": {
                    "started_time": "2020-12-30 22:29:41",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-117-2020_12_30-22_29_41.vma.lzo",
                    "transfer_size": 268435456000,
                    "transfer_time": 1570,
                    "archive_size": 148100000000,
                    "total_duration": 1631,
                },
                "126": {
                    "started_time": "2020-12-30 22:56:52",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-126-2020_12_30-22_56_52.vma.lzo",
                    "transfer_size": 88261577933,
                    "transfer_time": 225,
                    "archive_size": 4410000000,
                    "total_duration": 227,
                },
                "130": {
                    "started_time": "2020-12-30 23:00:39",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-130-2020_12_30-23_00_39.vma.lzo",
                    "transfer_size": 68719476736,
                    "transfer_time": 326,
                    "archive_size": 15840000000,
                    "total_duration": 331,
                },
                "131": {
                    "started_time": "2020-12-30 23:06:10",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-131-2020_12_30-23_06_10.vma.lzo",
                    "transfer_size": 85899345920,
                    "transfer_time": 318,
                    "archive_size": 8210000000,
                    "total_duration": 328,
                },
                "132": {
                    "started_time": "2020-12-30 23:11:38",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-132-2020_12_30-23_11_38.vma.lzo",
                    "transfer_size": 111669149696,
                    "transfer_time": 188,
                    "archive_size": 1070000000,
                    "total_duration": 194,
                },
                "135": {
                    "started_time": "2020-12-30 23:14:52",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-135-2020_12_30-23_14_52.vma.lzo",
                    "transfer_size": 45311904973,
                    "transfer_time": 147,
                    "archive_size": 5050000000,
                    "total_duration": 149,
                },
                "138": {
                    "started_time": "2020-12-30 23:17:21",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-138-2020_12_30-23_17_21.vma.lzo",
                    "transfer_size": 45311904973,
                    "transfer_time": 128,
                    "archive_size": 3380000000,
                    "total_duration": 131,
                },
                "139": {
                    "started_time": "2020-12-30 23:19:32",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-139-2020_12_30-23_19_32.vma.lzo",
                    "transfer_size": 23837068493,
                    "transfer_time": 108,
                    "archive_size": 4210000000,
                    "total_duration": 112,
                },
                "141": {
                    "started_time": "2020-12-30 23:21:24",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-qemu-141-2020_12_30-23_21_24.vma.lzo",
                    "transfer_size": 36721970381,
                    "transfer_time": 177,
                    "archive_size": 7620000000,
                    "total_duration": 180,
                },
                "142": {
                    "started_time": "2020-12-30 23:24:24",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-lxc-142-2020_12_30-23_24_24.tar.lzo",
                    "bytes_written_size": 14282844160,
                    "bytes_written_bandwidth": 143654912,
                    "archive_size": 6540000000,
                    "total_duration": 110,
                },
                "144": {
                    "started_time": "2020-12-30 23:26:14",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-lxc-144-2020_12_30-23_26_14.tar.lzo",
                    "bytes_written_size": 3571548160,
                    "bytes_written_bandwidth": 87031808,
                    "archive_size": 1300000000,
                    "total_duration": 46,
                },
            },
            None,
        ),
        (
            "proxmox_ve-backup-2021-01-17.log",
            {
                "119": {
                    "started_time": "2021-01-17 02:30:02",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-lxc-119-2021_01_17-02_30_02.tar.zst",
                    "bytes_written_size": 62757529600,
                    "bytes_written_bandwidth": 82837504,
                    "error": "command 'set -o pipefail && lxc-usernsexec -m u:0:100000:65536 -m g:0:100000:65536 -- tar cpf - --totals --one-file-system -p --sparse --numeric-owner --acls --xattrs '--xattrs-include=user.*' '--xattrs-include=security.capability' '--warning=no-file-ignored' '--warning=no-xattr-write' --one-file-system '--warning=no-file-ignored' '--directory=/var/tmp/vzdumptmp112226_119' ./etc/vzdump/pct.conf ./etc/vzdump/pct.fw '--directory=/mnt/vzsnap0' --no-anchored '--exclude=lost+found' --anchored '--exclude=./tmp/?*' '--exclude=./var/tmp/?*' '--exclude=./var/run/?*.pid' ./ | zstd --rsyncable '--threads=1' >/mnt/pve/StorageBox-219063/dump/vzdump-lxc-119-2021_01_17-02_30_02.tar.dat' failed: exit code 1",
                },
                "120": {
                    "started_time": "2021-01-17 02:45:53",
                    "archive_name": "/mnt/pve/StorageBox-219063/dump/vzdump-lxc-120-2021_01_17-02_45_53.tar.zst",
                    "bytes_written_size": 399821598720,
                    "bytes_written_bandwidth": 56623104,
                    "error": "command 'set -o pipefail && lxc-usernsexec -m u:0:100000:65536 -m g:0:100000:65536 -- tar cpf - --totals --one-file-system -p --sparse --numeric-owner --acls --xattrs '--xattrs-include=user.*' '--xattrs-include=security.capability' '--warning=no-file-ignored' '--warning=no-xattr-write' --one-file-system '--warning=no-file-ignored' '--directory=/var/tmp/vzdumptmp112226_120' ./etc/vzdump/pct.conf ./etc/vzdump/pct.fw '--directory=/mnt/vzsnap0' --no-anchored '--exclude=lost+found' --anchored '--exclude=./tmp/?*' '--exclude=./var/tmp/?*' '--exclude=./var/run/?*.pid' ./ ./opt/sonatype/sonatype-work/ | zstd --rsyncable '--threads=1' >/mnt/pve/StorageBox-219063/dump/vzdump-lxc-120-2021_01_17-02_45_53.tar.dat' failed: exit code 1",
                },
            },
            None,
        ),
        (
            "proxmox_ve-backup-2021-02-11.log",
            {},
            BackupTask.LogParseWarning,
        ),
        (
            "proxmox_ve-backup-2021-04-11.log",
            {
                "101": {
                    "started_time": "2021-04-11 12:15:02",
                    "transfer_size": 5970004541,
                    "transfer_time": 537,
                    "total_duration": 547,
                },
                "102": {
                    "started_time": "2021-04-11 12:24:10",
                    "transfer_size": 1056964608,
                    "transfer_time": 79,
                    "total_duration": 109,
                },
                "105": {
                    "started_time": "2021-04-11 12:25:59",
                    "transfer_size": 1932735283,
                    "transfer_time": 307,
                    "total_duration": 339,
                },
                "110": {
                    "started_time": "2021-04-11 12:31:38",
                    "upload_amount": 877165281,
                    "upload_total": 19166291558,
                    "upload_time": 229.0,
                    "total_duration": 288,
                },
                "117": {
                    "started_time": "2021-04-11 12:36:26",
                    "error": "VM 117 qmp command 'backup' failed - got timeout",
                },
                "126": {
                    "started_time": "2021-04-11 12:37:27",
                    "error": "VM 126 qmp command 'backup' failed - got timeout",
                },
                "130": {
                    "started_time": "2021-04-11 12:38:33",
                    "transfer_size": 2652142305,
                    "transfer_time": 534,
                    "total_duration": 573,
                },
                "131": {
                    "started_time": "2021-04-11 12:48:06",
                    "transfer_size": 2050846884,
                    "transfer_time": 255,
                    "total_duration": 291,
                },
                "132": {
                    "started_time": "2021-04-11 12:52:57",
                    "transfer_size": 3629247365,
                    "transfer_time": 453,
                    "total_duration": 491,
                },
                "135": {
                    "started_time": "2021-04-11 13:01:08",
                    "transfer_size": 2695091978,
                    "transfer_time": 224,
                    "total_duration": 250,
                },
                "136": {
                    "started_time": "2021-04-11 13:05:19",
                    "transfer_size": 41875931136,
                    "transfer_time": 1474,
                    "total_duration": 1510,
                },
                "137": {
                    "started_time": "2021-04-11 13:30:29",
                    "transfer_size": 16417512489,
                    "transfer_time": 2260,
                    "total_duration": 2302,
                },
                "141": {
                    "started_time": "2021-04-11 14:08:51",
                    "transfer_size": 1728724337,
                    "transfer_time": 201,
                    "total_duration": 234,
                },
                "142": {
                    "started_time": "2021-04-11 14:12:45",
                    "upload_amount": 517723914,
                    "upload_total": 16589311181,
                    "upload_time": 128.7,
                    "total_duration": 158,
                },
                "144": {
                    "started_time": "2021-04-11 14:15:23",
                    "upload_amount": 247589765,
                    "upload_total": 6088116142,
                    "upload_time": 50.35,
                    "total_duration": 72,
                },
                "145": {
                    "started_time": "2021-04-11 14:16:35",
                    "transfer_size": 13035225743,
                    "transfer_time": 1167,
                    "total_duration": 1193,
                },
                "150": {
                    "started_time": "2021-04-11 14:36:28",
                    "transfer_size": 1385126953,
                    "transfer_time": 126,
                    "total_duration": 149,
                },
                "156": {
                    "started_time": "2021-04-11 14:38:57",
                    "transfer_size": 1245540516,
                    "transfer_time": 65,
                    "total_duration": 82,
                },
                "157": {"started_time": "2021-04-11 14:40:19", "error": "interrupted by signal"},
            },
            None,
        ),
        (
            "proxmox_ve-backup-2021-04-15.log",
            {
                "101": {
                    "started_time": "2021-04-15 20:00:02",
                    "transfer_size": 5712306504,
                    "transfer_time": 81,
                    "total_duration": 86,
                },
                "102": {
                    "started_time": "2021-04-15 20:01:28",
                    "transfer_size": 884998144,
                    "transfer_time": 21,
                    "total_duration": 26,
                },
                "105": {
                    "started_time": "2021-04-15 20:01:54",
                    "transfer_size": 1513975972,
                    "transfer_time": 41,
                    "total_duration": 47,
                },
                "110": {
                    "started_time": "2021-04-15 20:02:41",
                    "upload_amount": 197425889,
                    "upload_total": 19230716068,
                    "upload_time": 60.98,
                    "total_duration": 68,
                },
                "117": {
                    "started_time": "2021-04-15 20:03:49",
                    "transfer_size": 12659416105,
                    "transfer_time": 279,
                    "total_duration": 286,
                },
                "126": {
                    "started_time": "2021-04-15 20:08:35",
                    "transfer_size": 1632087572,
                    "transfer_time": 47,
                    "total_duration": 56,
                },
                "130": {
                    "started_time": "2021-04-15 20:09:32",
                    "transfer_size": 1352914698,
                    "transfer_time": 23,
                    "total_duration": 33,
                },
                "131": {
                    "started_time": "2021-04-15 20:10:05",
                    "transfer_size": 1513975972,
                    "transfer_time": 44,
                    "total_duration": 54,
                },
                "132": {
                    "started_time": "2021-04-15 20:10:59",
                    "transfer_size": 3532610601,
                    "transfer_time": 86,
                    "total_duration": 94,
                },
                "135": {
                    "started_time": "2021-04-15 20:12:33",
                    "transfer_size": 3060164198,
                    "transfer_time": 86,
                    "total_duration": 97,
                },
                "136": {
                    "started_time": "2021-04-15 20:14:10",
                    "transfer_size": 2072321720,
                    "transfer_time": 42,
                    "total_duration": 48,
                },
                "137": {
                    "started_time": "2021-04-15 20:14:58",
                    "transfer_size": 5293547192,
                    "transfer_time": 119,
                    "total_duration": 125,
                },
                "141": {
                    "started_time": "2021-04-15 20:17:03",
                    "transfer_size": 847249408,
                    "transfer_time": 17,
                    "total_duration": 21,
                },
                "142": {
                    "started_time": "2021-04-15 20:17:24",
                    "upload_amount": 880866755,
                    "upload_total": 16567836344,
                    "upload_time": 58.32,
                    "total_duration": 63,
                },
                "144": {
                    "started_time": "2021-04-15 20:18:28",
                    "upload_amount": 601012306,
                    "upload_total": 6378026435,
                    "upload_time": 29.79,
                    "total_duration": 36,
                },
                "145": {
                    "started_time": "2021-04-15 20:19:04",
                    "transfer_size": 12927851561,
                    "transfer_time": 278,
                    "total_duration": 286,
                },
                "150": {
                    "started_time": "2021-04-15 20:23:51",
                    "transfer_size": 784334848,
                    "transfer_time": 7,
                    "total_duration": 8,
                },
                "156": {
                    "started_time": "2021-04-15 20:23:59",
                    "transfer_size": 771751936,
                    "transfer_time": 16,
                    "total_duration": 18,
                },
                "157": {
                    "started_time": "2021-04-15 20:24:17",
                    "transfer_size": 1836098519,
                    "transfer_time": 45,
                    "total_duration": 52,
                },
                "158": {
                    "started_time": "2021-04-15 20:25:09",
                    "transfer_size": 180355072,
                    "transfer_time": 8,
                    "total_duration": 14,
                },
            },
            None,
        ),
        (
            "proxmox_ve-backup-2021-04-10.log",
            {
                "100": {
                    "error": "There is a max backup limit of 1 enforced by the target storage or the vzdump parameters. Either increase the limit or delete old backup(s).",
                    "started_time": "2021-04-10 12:19:30",
                },
            },
            None,
        ),
        (
            "proxmox_ve-backup-2021-05-17.log",
            {
                "103": {
                    "started_time": "2021-05-17 20:15:02",
                    "backup_amount": 28248637,
                    "backup_total": 2695091978,
                    "backup_time": 24.72,
                    "total_duration": 34,
                },
            },
            None,
        ),
    ),
)
def test_parse_backup_logs(logfile, expected_results, expected_exception) -> None:
    file_path = Path(os.path.dirname(__file__)) / "proxmox_ve-files" / logfile
    log = ({"n": i, "t": line} for i, line in enumerate(file_path.open().readlines()))
    with ExitStack() as exit_stack:
        if expected_exception:
            exit_stack.enter_context(pytest.raises(expected_exception))
        results = collect_vm_backup_info(
            [BackupTask({}, log, strict=True, dump_logs=False, dump_erroneous_logs=False)]
        )
        assert results == expected_results


if __name__ == "__main__":
    # Please keep these lines - they make TDD easy and have no effect on normal test runs.
    # Just run this file from your IDE and dive into the code.
    from tests.testlib.utils import cmk_path

    assert not pytest.main(
        [
            "--doctest-modules",
            os.path.join(cmk_path(), "cmk/special_agents/agent_proxmox_ve.py"),
        ]
    )
    pytest.main(["-T=unit", "-vvsx", __file__])
