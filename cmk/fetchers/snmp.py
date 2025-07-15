#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any, Final, NamedTuple

from cmk.snmplib import (
    BackendSNMPTree,
    SNMPBackend,
    SNMPBackendEnum,
    SNMPDetectSpec,
    SNMPHostConfig,
)
from cmk.utils.sectionname import SectionMap, SectionName

from .snmp_backend import ClassicSNMPBackend, StoredWalkSNMPBackend

inline: ModuleType | None
try:
    from .cee.snmp_backend import inline  # type: ignore[import,no-redef,unused-ignore]
except ImportError:
    inline = None


__all__ = ["SNMPPluginStoreItem", "SNMPPluginStore", "make_backend"]


_force_stored_walks = False


def force_stored_walks() -> None:
    global _force_stored_walks
    _force_stored_walks = True


def get_force_stored_walks() -> bool:
    return _force_stored_walks


def make_backend(
    snmp_config: SNMPHostConfig,
    logger: logging.Logger,
    *,
    use_cache: bool | None = None,
    stored_walk_path: Path,
) -> SNMPBackend:
    if use_cache is None:
        use_cache = get_force_stored_walks()

    if use_cache or snmp_config.snmp_backend is SNMPBackendEnum.STORED_WALK:
        return StoredWalkSNMPBackend(
            snmp_config, logger, path=stored_walk_path / snmp_config.hostname
        )

    if inline and snmp_config.snmp_backend is SNMPBackendEnum.INLINE:
        return inline.InlineSNMPBackend(snmp_config, logger)

    if snmp_config.snmp_backend is SNMPBackendEnum.CLASSIC:
        return ClassicSNMPBackend(snmp_config, logger)

    raise NotImplementedError(f"Unknown SNMP backend: {snmp_config.snmp_backend}")


class SNMPPluginStoreItem(NamedTuple):
    trees: Sequence[BackendSNMPTree]
    detect_spec: SNMPDetectSpec
    inventory: bool

    @classmethod
    def deserialize(cls, serialized: Mapping[str, Any]) -> "SNMPPluginStoreItem":
        return cls(
            [BackendSNMPTree.from_json(tree) for tree in serialized["trees"]],
            SNMPDetectSpec.from_json(serialized["detect_spec"]),
            serialized["inventory"],
        )

    def serialize(self) -> Mapping[str, Any]:
        return {
            "trees": [tree.to_json() for tree in self.trees],
            "detect_spec": self.detect_spec.to_json(),
            "inventory": self.inventory,
        }


class SNMPPluginStore(SectionMap[SNMPPluginStoreItem]):
    def __init__(
        self,
        store: SectionMap[SNMPPluginStoreItem] | None = None,
    ) -> None:
        self._store: Final[SectionMap[SNMPPluginStoreItem]] = store if store else {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._store!r})"

    def __getitem__(self, key: SectionName) -> SNMPPluginStoreItem:
        return self._store.__getitem__(key)

    def __iter__(self) -> Iterator[SectionName]:
        return self._store.__iter__()

    def __len__(self) -> int:
        return self._store.__len__()

    @classmethod
    def deserialize(cls, serialized: Mapping[str, Any]) -> "SNMPPluginStore":
        return cls(
            {
                SectionName(k): SNMPPluginStoreItem.deserialize(v)
                for k, v in serialized["plugin_store"].items()
            }
        )

    def serialize(self) -> Mapping[str, Any]:
        return {"plugin_store": {str(k): v.serialize() for k, v in self.items()}}
