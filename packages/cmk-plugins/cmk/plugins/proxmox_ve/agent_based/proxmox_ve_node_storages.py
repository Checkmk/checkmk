#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, MutableMapping, MutableSequence, Sequence

from pydantic import BaseModel

from cmk.agent_based.v2 import AgentSection, StringTable
from cmk.plugins.proxmox_ve.lib.node_storages import SectionNodeStorages, Storage, StorageLink


class _RawVMDisks(BaseModel, frozen=True):
    vmid: str
    disks: Mapping[str, str]


class _RawNodeStorage(BaseModel, frozen=True):
    node: str
    storages: Sequence[Storage]
    vm_disks: Sequence[_RawVMDisks]


def _pre_parse_proxmox_ve_node_storage(string_table: StringTable) -> _RawNodeStorage:
    return _RawNodeStorage.model_validate_json(string_table[0][0])


def _storage_links_for_vm(vm_disks: _RawVMDisks) -> Mapping[str, Sequence[StorageLink]]:
    storage_links: MutableMapping[str, MutableSequence[StorageLink]] = {}

    for key, value in vm_disks.disks.items():
        storage_name = value.partition(":")[0]
        size = ""
        for part in value.split(","):
            if part.startswith("size="):
                size = part[5:]
                break

        storage_links.setdefault(storage_name, []).append(
            StorageLink(type=key, size=size, vmid=vm_disks.vmid)
        )

    return storage_links


def parse_proxmox_ve_node_storage(string_table: StringTable) -> SectionNodeStorages:
    raw = _pre_parse_proxmox_ve_node_storage(string_table)

    storage_links: MutableMapping[str, MutableSequence[StorageLink]] = {}
    for vm_disks in raw.vm_disks:
        for storage_name, links in _storage_links_for_vm(vm_disks).items():
            storage_links.setdefault(storage_name, []).extend(links)

    return SectionNodeStorages(
        node=raw.node,
        storages=raw.storages,
        storage_links=storage_links,
    )


agent_section_proxmox_ve_node_storage = AgentSection(
    name="proxmox_ve_node_storage",
    parse_function=parse_proxmox_ve_node_storage,
)
