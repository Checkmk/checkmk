#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple, Sequence, Mapping, Optional, List, Set
from contextlib import suppress

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import register

BlocksEntry = Tuple[str, float, float, float]
VolumeInfo = Mapping[str, Mapping[str, Optional[str]]]
Inode = Tuple[str, int, int]
BlocksSubsection = Tuple[Sequence[BlocksEntry], VolumeInfo]
InodesSubsection = Sequence[Inode]
Section = Tuple[BlocksSubsection, InodesSubsection]


def is_int(string: str) -> bool:
    with suppress(ValueError):
        return bool(int(string)) or True
    return False


def padded_line(line: List[str]) -> List[str]:
    return ([line[0], ""] + line[1:]) if is_int(line[1]) else line


def reformat_line(line: List[str]) -> List[str]:
    # Handle known cases, where the file system contains spaces
    for index, entry in enumerate(line):
        if entry == "NTFS":
            line = [" ".join(line[:index])
                   ] + [line[index]] + line[index + 1:index + 5] + [" ".join(line[index + 5:])]
            break

    if line[2] == "File" and line[3] == "System":
        line = [line[0], " ".join(line[1:4])] + line[4:]
    return line


def get_mountpoint(
    fs_type: str,
    device: str,
    rest: Sequence[str],
    btrfs_devices: Set[str],
) -> Optional[str]:
    # This particular bit of magic originated in Werk #2671 and has the purpose of avoiding duplicate checks,
    # as btrfs filesystems are often mounted at multiple mountpoints. We keep it for compatibility.
    if fs_type == "btrfs":
        if device in btrfs_devices:
            return None
        btrfs_devices.add(device)
        return "btrfs " + device

    return " ".join(rest).replace('\\', '/')  # Windows \ is replaced with /


def processed(
    line: List[str],
    btrfs_devices: Set[str],
) -> Optional[Tuple[str, str, Optional[str], float, float, float]]:
    with suppress(ValueError):
        device, fs_type, size_kb, used_kb, avail_kb, _, *rest = line
        mountpoint = get_mountpoint(fs_type, device, rest, btrfs_devices)

        # Beware: the 6th column of df ("used perc") may includes 5% which are reserved
        # for the superuser, whereas the 4th colum ("used MB") does *not* include that.
        # Beware(2): the column used_mb does not account for the reserved space for
        # superusers. So we rather use the column 'avail' and subtract that from total
        # to compute the used space.
        size_mb, used_mb, avail_mb = (int(i) / 1024 for i in (size_kb, used_kb, avail_kb))

        # exclude filesystems without size
        if size_mb == 0 or mountpoint in {None, "/etc/resolv.conf", "/etc/hostname", "/etc/hosts"}:
            return None
        assert mountpoint is not None
        return mountpoint, device, fs_type or None, size_mb, avail_mb, used_mb
    return None


def parse_blocks_subsection(blocks_subsection: StringTable) -> BlocksSubsection:
    seen_btrfs_devices: Set[str] = set()
    preprocessed = tuple(
        item  #
        for line in blocks_subsection
        for item in (processed(reformat_line(padded_line(line)), seen_btrfs_devices),)
        if item is not None)

    df_blocks = tuple((mountpoint, size_mb, avail_mb, size_mb - avail_mb - used_mb)
                      for mountpoint, device, fs_type, size_mb, avail_mb, used_mb in preprocessed)
    volume_info = {
        mountpoint: {
            "volume_name": device,
            "fs_type": fs_type,
        } for mountpoint, device, fs_type, size_mb, avail_mb, used_mb in preprocessed
    }

    return df_blocks, volume_info


def parse_inodes_subsection(inodes_subsection: StringTable) -> InodesSubsection:
    def to_entry(line: Sequence[str]) -> Optional[Inode]:
        with suppress(ValueError):
            return line[-1], int(line[2]), int(line[4])
        return None

    return tuple(entry for l in inodes_subsection for entry in (to_entry(padded_line(l)),) if entry)


def parse_df(string_table: StringTable) -> Section:
    """
    >>> for s in parse_df([
    ...     ['/dev/empty', 'vfat', '0', '6188', '517060', '2%', '/boot/efi'] ,
    ...     ['/dev/empty2', 'vfat', 'null', '6188', '517060', '2%', '/boot/efi'] ,
    ...     ['/dev/mapper/vgsystem-lvroot', 'btrfs', '20971520', '10642560', '9892288', '52%', '/.snapshots'] ,
    ...     ['/dev/mapper/vgsystem-lvroot', 'btrfs', '20971520', '10642560', '9892288', '52%', '/.snapshots'] ,
    ...     ['tmpfs', 'tmpfs', '3269760', '2752', '3267008', '1%', '/run'] ,
    ...     ['/dev/nvme0n1p1', 'vfat', '523248', '6188', '517060', '2%', '/boot/efi'] ,
    ...     ['[df_inodes_start]'],
    ...     ['tmpfs', 'tmpfs', '4087195', '1654', '4085541', '1%', '/run'] ,
    ...     ['/dev/mapper/ubuntu--mate--vg-root', 'ext4', '31121408', '3407045', '27714363', '11%', '/'] ,
    ...     ['tmpfs', 'tmpfs', 'null', '1654', '4085541', '1%', '/run'] ,
    ...     ['[df_inodes_end]'] ,
    ... ]):
    ...   print("==")
    ...   for l in s:
    ...     print(l)
    ==
    (('btrfs /dev/mapper/vgsystem-lvroot', 20480.0, 9660.4375, 426.4375), ('/run', 3193.125, 3190.4375, 0.0), ('/boot/efi', 510.984375, 504.94140625, 0.0))
    {'btrfs /dev/mapper/vgsystem-lvroot': {'volume_name': '/dev/mapper/vgsystem-lvroot', 'fs_type': 'btrfs'}, '/run': {'volume_name': 'tmpfs', 'fs_type': 'tmpfs'}, '/boot/efi': {'volume_name': '/dev/nvme0n1p1', 'fs_type': 'vfat'}}
    ==
    ('/run', 4087195, 4085541)
    ('/', 31121408, 27714363)
    >>> for s in parse_df([
    ...     ['C:\\\\', 'NTFS', '31463268', '16510812', '14952456', '53%', 'C:\\\\'] ,
    ...     ['W:\\\\', 'NTFS', '52420092', '33605812', '18814280', '65%', 'W:\\\\'] ,
    ... ]):
    ...   print("==")
    ...   for l in s:
    ...     print(l)
    ==
    (('C:/', 30725.84765625, 14602.0078125, 0.0), ('W:/', 51191.49609375, 18373.3203125, 0.0))
    {'C:/': {'volume_name': 'C:\\\\', 'fs_type': 'NTFS'}, 'W:/': {'volume_name': 'W:\\\\', 'fs_type': 'NTFS'}}
    ==
    >>> for s in parse_df([
    ...     ['dev', '795652', '0', '795652', '0%', '/dev'],
    ...     ['/dev/sda5', '12668904', '360184', '11670236', '3%', '/persist'],
    ...     ['[df_inodes_start]'],
    ...     ['dev', '198913', '365', '198548', '0%', '/dev'],
    ...     ['/dev/sda2', '65536', '25533', '40003', '39%', '/'],
    ...     ['/dev/sda5', '799680', '118', '799562', '0%', '/persist'],
    ...     ['[df_inodes_end]'],
    ...     ['devtmpfs', '795652', '0', '795652', '0%', '/dev'],
    ... ]):
    ...   print("==")
    ...   for l in s:
    ...     print(l)
    ==
    (('/dev', 777.00390625, 777.00390625, 0.0), ('/persist', 12371.9765625, 11396.71484375, 623.51953125), ('/dev', 777.00390625, 777.00390625, 0.0))
    {'/dev': {'volume_name': 'devtmpfs', 'fs_type': None}, '/persist': {'volume_name': '/dev/sda5', 'fs_type': None}}
    ==
    ('/dev', 198913, 198548)
    ('/', 65536, 40003)
    ('/persist', 799680, 799562)
    """
    blocks_subsection: StringTable = []
    inodes_subsection: StringTable = []
    current_list = blocks_subsection
    for line in string_table:
        if line[-1] == '[df_inodes_start]':
            current_list = inodes_subsection
            continue
        if line[-1] == '[df_inodes_end]':
            current_list = blocks_subsection
            continue
        current_list.append(line)

    return parse_blocks_subsection(blocks_subsection), parse_inodes_subsection(inodes_subsection)


register.agent_section(
    name="df",
    parse_function=parse_df,
)
