#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterable, Iterator, Mapping, Sequence
from enum import auto, Enum
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Result,
    Service,
    State,
)
from cmk.plugins.lib.df import (
    df_check_filesystem_list,
    df_discovery,
    DfBlock,
    DfInode,
    DfSection,
    EXCLUDED_MOUNTPOINTS,
    FILESYSTEM_DEFAULT_PARAMS,
)

_INVENTORY_DF_EXCLUDE_FS = ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"]


def _filter_df_blocks(
    df_blocks: Iterable[DfBlock], inventory_options: Mapping[str, Any]
) -> Iterator[DfBlock]:
    ignore_fs_types = inventory_options.get("ignore_fs_types", _INVENTORY_DF_EXCLUDE_FS)
    never_ignore_mountpoints = inventory_options.get("never_ignore_mountpoints", [])

    for df_block in df_blocks:
        if df_block.mountpoint in EXCLUDED_MOUNTPOINTS:
            continue

        if df_block.mountpoint.startswith("/var/lib/docker/"):
            # Always exclude filesystems below dockers local storage area
            # and also exclude docker mounts in containers which are reported
            # by the agent when the agent is executed in the container context
            continue

        if df_block.fs_type not in ignore_fs_types:
            yield df_block
            continue

        if not _ignore_mountpoint(df_block.mountpoint, never_ignore_mountpoints):
            yield df_block
            continue


def _ignore_mountpoint(mountpoint: str, never_ignore_mountpoints: Iterable[str]) -> bool:
    # Filesystem is not ignored, so check against mount point patterns
    for p in never_ignore_mountpoints:
        if p[0] == "~" and re.match(p[1:], mountpoint):
            return False

        if mountpoint == p:
            return False
    return True


class ItemBehaviour(Enum):
    default = auto()
    volume_name = auto()
    uuid = auto()


class ItemAndGrouping(NamedTuple):
    item: str
    grouping: str
    for_all: ItemBehaviour
    for_single: ItemBehaviour


def _get_item_behaviour_for_block_devices(params: Mapping[str, Any]) -> ItemBehaviour:
    # The first one comes from WATO ruleset the second one is set during discovery
    # which is kind of normalized name.
    if params.get("mountpoint_for_block_devices") in ["uuid_as_mountpoint", "uuid"]:
        return ItemBehaviour.uuid
    return ItemBehaviour.volume_name


def _get_item_and_grouping(params: Mapping[str, Any]) -> ItemAndGrouping:
    item = params.get("item_appearance", "mountpoint")
    grouping = params.get("grouping_behaviour", "mountpoint")

    for_all = ItemBehaviour.default
    for_single = ItemBehaviour.default
    if item == "volume_name_and_mountpoint":
        if grouping == "volume_name_and_mountpoint":
            for_all = ItemBehaviour.volume_name
        else:
            for_single = ItemBehaviour.volume_name

    elif item == "uuid_and_mountpoint":
        if grouping == "uuid_and_mountpoint":
            for_all = ItemBehaviour.uuid
        else:
            for_single = ItemBehaviour.uuid

    return ItemAndGrouping(
        item=item,
        grouping=grouping,
        for_all=for_all,
        for_single=for_single,
    )


def _prepare_item_name(entry: DfBlock | DfInode, behaviour: ItemBehaviour) -> str:
    if entry.device and behaviour == ItemBehaviour.volume_name:
        return f"{entry.device} {entry.mountpoint}"

    if entry.uuid and behaviour == ItemBehaviour.uuid:
        return f"{entry.uuid} {entry.mountpoint}"

    return entry.mountpoint


def _handle_block_devices(
    df_blocks: Iterable[DfBlock],
    mountpoint_for_block_devices: ItemBehaviour,
) -> Sequence[DfBlock]:
    # TODO What about df_inodes?
    # Not sure but it seems that inodes of btrfs FS are always zero (seen in our data pool):
    # /dev/sda1      btrfs         0     0      0     - /.snapshots
    # /dev/sda1      btrfs         0     0      0     - /var/tm
    # ...
    handled_df_blocks = []
    for df_block in df_blocks:
        if df_block.fs_type == "btrfs":
            # This particular bit of magic originated in Werk #2671 and has the purpose
            # of avoiding duplicate checks.
            # Compatibility: Before filtering/grouping/... we use '"btrfs " + device' as
            # mountpoint - regardless which field for mountpoint is set in df_section.

            if df_block.uuid and mountpoint_for_block_devices == ItemBehaviour.uuid:
                suffix = df_block.uuid
            else:  # mountpoint_for_block_devices == ItemBehaviour.volume_name
                suffix = df_block.device

            mountpoint = " ".join([df_block.fs_type, suffix])

            df_block = DfBlock(
                device=df_block.device,
                fs_type=df_block.fs_type,
                size_mb=df_block.size_mb,
                avail_mb=df_block.avail_mb,
                reserved_mb=df_block.reserved_mb,
                mountpoint=mountpoint,
                uuid=df_block.uuid,
            )

        handled_df_blocks.append(df_block)
    return handled_df_blocks


def discover_df(params: Mapping[str, Any], section: DfSection) -> DiscoveryResult:
    mountpoint_for_block_devices = _get_item_behaviour_for_block_devices(params)
    item_and_grouping = _get_item_and_grouping(params)

    df_blocks, _df_inodes = section
    df_blocks = _handle_block_devices(df_blocks, mountpoint_for_block_devices)

    filtered_blocks = _filter_df_blocks(df_blocks, params)

    mplist = [
        _prepare_item_name(df_block, item_and_grouping.for_all) for df_block in filtered_blocks
    ]

    # TODO Cleanup df_inventory + mp_to_df_block:
    #      df_inventory should also return a list of DfBlocks or similar.
    mp_to_df_block: dict[str | None, DfBlock] = {
        df_block.mountpoint: df_block for df_block in df_blocks
    }

    for service in df_discovery([params], mplist):
        mountpoint = service.item
        df_block = mp_to_df_block.get(service.item)
        additional_params = {}
        if "patterns" in service.parameters:
            # Add the grouping_behaviour info to the discovered parameters of this service.
            # With this information the check can easily reconstruct the discovered grouping.
            additional_params = {"grouping_behaviour": item_and_grouping.grouping}

        elif df_block:
            # Somehow the user wanted to see the volume name in the service name,
            # but the grouping itself is based on the mountpoint only
            # => The df_inventory returns a list of mountpoints and mountpoint groups
            # Add the volume name as prefix for single mountpoints
            mountpoint = _prepare_item_name(df_block, item_and_grouping.for_single)

        # We have to add these parameters in any case in order to reconstruct df blocks
        # in the check because "mountpoint" may contain a free-text group name.
        additional_params["mountpoint_for_block_devices"] = mountpoint_for_block_devices.name
        additional_params["item_appearance"] = item_and_grouping.item
        yield Service(item=mountpoint, parameters={**service.parameters, **additional_params})


# Legacy params
def _get_mountpoint_from_item(
    item: str, params: Mapping[str, Any], df_blocks: Iterable[DfBlock]
) -> str:
    item_to_mp = {
        _prepare_item_name(df_block, ItemBehaviour.volume_name): df_block.mountpoint
        for df_block in df_blocks
    }
    item_to_mp.update(
        {
            _prepare_item_name(df_block, ItemBehaviour.uuid): df_block.mountpoint
            for df_block in df_blocks
        }
    )

    if "patterns" in params or item in [df_block.mountpoint for df_block in df_blocks]:
        return item

    if item in item_to_mp:
        return item_to_mp[item]

    return item


def check_df(item: str, params: Mapping[str, Any], section: DfSection) -> CheckResult:
    mountpoint_for_block_devices = _get_item_behaviour_for_block_devices(params)
    item_and_grouping = _get_item_and_grouping(params)

    df_blocks, df_inodes = section
    df_blocks = _handle_block_devices(df_blocks, mountpoint_for_block_devices)

    item = _get_mountpoint_from_item(item, params, df_blocks)

    raw_df_blocks = [
        (
            _prepare_item_name(df_block, item_and_grouping.for_all),
            df_block.size_mb,
            df_block.avail_mb,
            df_block.reserved_mb,
        )
        for df_block in df_blocks
    ]
    raw_df_inodes = [
        (_prepare_item_name(df_inode, item_and_grouping.for_all), df_inode.total, df_inode.avail)
        for df_inode in df_inodes
    ]

    if (
        params.get("show_volume_name")
        # we might have no matching device in the cluster case
        and (volume_name := next((d.device for d in df_blocks if d.mountpoint == item), None))
    ):
        yield Result(state=State.OK, summary=f"[{volume_name}]")

    yield from df_check_filesystem_list(
        value_store=get_value_store(),
        item=item,
        params=params,
        fslist_blocks=raw_df_blocks,
        fslist_inodes=raw_df_inodes,
    )


check_plugin_df = CheckPlugin(
    name="df",
    service_name="Filesystem %s",
    discovery_function=discover_df,
    discovery_default_parameters={},
    discovery_ruleset_name="inventory_df_rules",
    check_function=check_df,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
