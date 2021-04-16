#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple, Sequence, Mapping, Optional, List, Set, NamedTuple
from contextlib import suppress

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import register

DfBlock = NamedTuple("DfBlock", [
    ("device", str),
    ("fs_type", Optional[str]),
    ("size_mb", float),
    ("avail_mb", float),
    ("reserved_mb", float),
    ("mountpoint", str),
])

DfInode = NamedTuple("DfInode", [
    ("device", Optional[str]),
    ("total", int),
    ("avail", int),
    ("mountpoint", str),
])

BlocksSubsection = Sequence[DfBlock]
MpToDevice = Mapping[str, str]
InodesSubsection = Sequence[DfInode]


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
) -> Optional[DfBlock]:
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
        return DfBlock(
            device=device,
            fs_type=fs_type or None,
            size_mb=size_mb,
            avail_mb=avail_mb,
            reserved_mb=size_mb - avail_mb - used_mb,
            mountpoint=mountpoint,
        )
    return None


def parse_blocks_subsection(blocks_subsection: StringTable) -> Tuple[BlocksSubsection, MpToDevice]:
    seen_btrfs_devices: Set[str] = set()
    df_blocks = tuple(item  #
                      for line in blocks_subsection
                      for item in (processed(reformat_line(padded_line(line)), seen_btrfs_devices),)
                      if item is not None)

    # Be aware regarding 'mp_to_device': The first entry wins
    return df_blocks, {df_block.mountpoint: df_block.device for df_block in df_blocks}


def parse_inodes_subsection(inodes_subsection: StringTable,
                            mp_to_device: MpToDevice) -> InodesSubsection:
    def to_entry(line: Sequence[str]) -> Optional[DfInode]:
        with suppress(ValueError):
            mountpoint = line[-1]
            return DfInode(
                device=mp_to_device.get(mountpoint),
                total=int(line[2]),
                avail=int(line[4]),
                mountpoint=mountpoint,
            )
        return None

    return tuple(entry for l in inodes_subsection for entry in (to_entry(padded_line(l)),) if entry)


def parse_df(string_table: StringTable) -> Tuple[BlocksSubsection, InodesSubsection]:
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
    DfBlock(device='/dev/mapper/vgsystem-lvroot', fs_type='btrfs', size_mb=20480.0, avail_mb=9660.4375, reserved_mb=426.4375, mountpoint='btrfs /dev/mapper/vgsystem-lvroot')
    DfBlock(device='tmpfs', fs_type='tmpfs', size_mb=3193.125, avail_mb=3190.4375, reserved_mb=0.0, mountpoint='/run')
    DfBlock(device='/dev/nvme0n1p1', fs_type='vfat', size_mb=510.984375, avail_mb=504.94140625, reserved_mb=0.0, mountpoint='/boot/efi')
    ==
    DfInode(device='tmpfs', total=4087195, avail=4085541, mountpoint='/run')
    DfInode(device=None, total=31121408, avail=27714363, mountpoint='/')
    >>> for s in parse_df([
    ...     ['C:\\\\', 'NTFS', '31463268', '16510812', '14952456', '53%', 'C:\\\\'],
    ...     ['W:\\\\', 'NTFS', '52420092', '33605812', '18814280', '65%', 'W:\\\\'],
    ... ]):
    ...   print("==")
    ...   for l in s:
    ...     print(l)
    ==
    DfBlock(device='C:\\\\', fs_type='NTFS', size_mb=30725.84765625, avail_mb=14602.0078125, reserved_mb=0.0, mountpoint='C:/')
    DfBlock(device='W:\\\\', fs_type='NTFS', size_mb=51191.49609375, avail_mb=18373.3203125, reserved_mb=0.0, mountpoint='W:/')
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
    DfBlock(device='dev', fs_type=None, size_mb=777.00390625, avail_mb=777.00390625, reserved_mb=0.0, mountpoint='/dev')
    DfBlock(device='/dev/sda5', fs_type=None, size_mb=12371.9765625, avail_mb=11396.71484375, reserved_mb=623.51953125, mountpoint='/persist')
    DfBlock(device='devtmpfs', fs_type=None, size_mb=777.00390625, avail_mb=777.00390625, reserved_mb=0.0, mountpoint='/dev')
    ==
    DfInode(device='devtmpfs', total=198913, avail=198548, mountpoint='/dev')
    DfInode(device=None, total=65536, avail=40003, mountpoint='/')
    DfInode(device='/dev/sda5', total=799680, avail=799562, mountpoint='/persist')
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

    df_blocks, mp_to_device = parse_blocks_subsection(blocks_subsection)
    return df_blocks, parse_inodes_subsection(inodes_subsection, mp_to_device)


register.agent_section(
    name="df",
    parse_function=parse_df,
    supersedes=['hr_fs'],
)
