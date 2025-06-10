#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
import time
from collections.abc import Collection, Iterable, Iterator, Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import Any, Final

from cmk.ccc import store
from cmk.ccc.exceptions import MKFetcherError, MKTimeout

from cmk.utils.sectionname import SectionMap, SectionName

from cmk.snmplib import (
    get_snmp_table,
    SNMPBackend,
    SNMPHostConfig,
    SNMPRawData,
    SNMPRawDataElem,
    SNMPRowInfo,
)

from cmk.checkengine.parser import SectionStore

from ._abstract import Fetcher, Mode
from ._snmpscan import gather_available_raw_section_names, SNMPScanConfig
from .snmp import make_backend, SNMPPluginStore

__all__ = ["SNMPFetcher", "SNMPSectionMeta", "SNMPScanConfig"]


class WalkCache(MutableMapping[tuple[str, str, bool], SNMPRowInfo]):
    """A cache on a per-fetchoid basis

    This cache is different from section stores in that is per-fetchoid,
    which means it deduplicates fetch operations across section definitions.

    The fetched data is always saved to a file *if* the respective OID is marked as being cached
    by the plug-in using `OIDCached` (that is: if the save_to_cache attribute of the OID object
    is true).
    """

    __slots__ = ("_store", "_path", "_logger")

    def __init__(self, walk_cache: Path, logger: logging.Logger) -> None:
        self._store: dict[tuple[str, str, bool], SNMPRowInfo] = {}
        self._path = walk_cache
        self._logger = logger

    def _read_row(self, path: Path) -> SNMPRowInfo:
        return store.load_object_from_file(path, default=None)

    def _write_row(self, path: Path, rowinfo: SNMPRowInfo) -> None:
        return store.save_object_to_file(path, rowinfo, pprint_value=False)

    @staticmethod
    def _oid2name(fetchoid: str, context_hash: str) -> str:
        return f"OID{fetchoid}-{context_hash}"

    @staticmethod
    def _name2oid(basename: str) -> tuple[str, str]:
        name_parts = basename[3:].split("-", 1)
        return name_parts[0], name_parts[1]

    def _iterfiles(self) -> Iterable[Path]:
        return self._path.iterdir() if self._path.is_dir() else ()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._store!r})"

    def __getitem__(self, key: tuple[str, str, bool]) -> SNMPRowInfo:
        return self._store.__getitem__(key)

    def __setitem__(self, key: tuple[str, str, bool], value: SNMPRowInfo) -> None:
        return self._store.__setitem__(key, value)

    def __delitem__(self, key: tuple[str, str, bool]) -> None:
        return self._store.__delitem__(key)

    def __iter__(self) -> Iterator[tuple[str, str, bool]]:
        return self._store.__iter__()

    def __len__(self) -> int:
        return self._store.__len__()

    def clear(self) -> None:
        for path in self._iterfiles():
            path.unlink(missing_ok=True)

    def load(self) -> None:
        """Try to read the OIDs data from cache files"""
        for path in self._iterfiles():
            fetchoid, context_hash = self._name2oid(path.name)

            self._logger.debug(f"  Loading {fetchoid} from walk cache {path}")
            try:
                read_walk = self._read_row(path)
            except MKTimeout:
                raise
            except Exception:
                self._logger.debug(f"  Failed to load {fetchoid} from walk cache {path}")
                continue

            if read_walk is not None:
                self._store[(fetchoid, context_hash, True)] = read_walk

    def save(self) -> None:
        self._path.mkdir(parents=True, exist_ok=True)

        for (fetchoid, context_hash, save_flag), rowinfo in self._store.items():
            if not save_flag:
                continue

            path = self._path / self._oid2name(fetchoid, context_hash)
            self._logger.debug(f"  Saving walk of {fetchoid} to walk cache {path}")
            self._write_row(path, rowinfo)


@dataclasses.dataclass(kw_only=True)
class SNMPSectionMeta:
    """Metadata for the section names."""

    checking: bool
    disabled: bool
    redetect: bool

    def serialize(self) -> Mapping[str, Any]:
        return dataclasses.asdict(self)

    @classmethod
    def deserialize(cls, serialized: Mapping[str, Any]) -> "SNMPSectionMeta":
        return cls(**serialized)


class SNMPFetcher(Fetcher[SNMPRawData]):
    CPU_SECTIONS_WITHOUT_CPU_IN_NAME = {
        SectionName("brocade_sys"),
        SectionName("bvip_util"),
    }
    plugin_store: SNMPPluginStore = SNMPPluginStore()

    def __init__(
        self,
        *,
        sections: SectionMap[SNMPSectionMeta],
        scan_config: SNMPScanConfig,
        do_status_data_inventory: bool,
        section_store_path: Path | str,
        stored_walk_path: Path | str,
        walk_cache_path: Path | str,
        snmp_config: SNMPHostConfig,
    ) -> None:
        super().__init__()
        self.sections: Final = sections
        self.scan_config: Final = scan_config
        self.do_status_data_inventory: Final = do_status_data_inventory
        self.stored_walk_path: Final = Path(stored_walk_path)
        self.walk_cache_path: Final = Path(walk_cache_path)
        self.snmp_config: Final = snmp_config
        self._logger: Final = logging.getLogger("cmk.helper.snmp")
        self._section_store = SectionStore[SNMPRawDataElem](
            section_store_path,
            logger=self._logger,
        )
        self._backend: SNMPBackend | None = None

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SNMPFetcher):
            return False
        return (
            self.sections == other.sections
            and self.scan_config == other.scan_config
            and self.do_status_data_inventory == other.do_status_data_inventory
            and self.stored_walk_path == other.stored_walk_path
            and self.walk_cache_path == other.walk_cache_path
            and self.snmp_config == other.snmp_config
        )

    @property
    def disabled_sections(self) -> frozenset[SectionName]:
        return frozenset(name for name, meta in self.sections.items() if meta.disabled)

    @property
    def checking_sections(self) -> frozenset[SectionName]:
        return frozenset(name for name, meta in self.sections.items() if meta.checking)

    @property
    def inventory_sections(self) -> frozenset[SectionName]:
        return frozenset(name for name, data in self.plugin_store.items() if data.inventory)

    @property
    def section_store_path(self) -> Path:
        return self._section_store.path

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                (
                    f"sections={self.sections!r}",
                    f"scan_config={self.scan_config!r}",
                    f"do_status_data_inventory={self.do_status_data_inventory!r}",
                    f"section_store_path={self.section_store_path!r}",
                    f"stored_walk_path={self.stored_walk_path!r}",
                    f"walk_cache_path={self.walk_cache_path!r}",
                    f"snmp_config={self.snmp_config!r}",
                )
            )
            + ")"
        )

    def open(self) -> None:
        self._backend = make_backend(
            self.snmp_config, self._logger, stored_walk_path=self.stored_walk_path
        )

    def close(self) -> None:
        self._backend = None

    def _detect(
        self, *, select_from: Collection[SectionName], backend: SNMPBackend
    ) -> frozenset[SectionName]:
        """Detect the applicable sections for the device in question"""
        return gather_available_raw_section_names(
            sections=[(name, self.plugin_store[name].detect_spec) for name in select_from],
            scan_config=self.scan_config,
            backend=backend,
        )

    def _get_selection(self, mode: Mode) -> frozenset[SectionName]:
        """Determine the sections fetched unconditionally (without detection)"""
        if mode is Mode.CHECKING:
            return frozenset(
                {name for name in self.checking_sections if not self.sections[name].redetect}
                - self.disabled_sections
            )

        if mode is Mode.FORCE_SECTIONS:
            return self.checking_sections

        return frozenset()

    def _get_detected_sections(self, mode: Mode) -> frozenset[SectionName]:
        """Determine the sections fetched after successful detection"""
        if mode is Mode.CHECKING:
            return frozenset(
                {name for name in self.checking_sections if self.sections[name].redetect}
                | (self.inventory_sections if self.do_status_data_inventory else frozenset())
                - self.disabled_sections
            )

        if mode is Mode.INVENTORY:
            return self.inventory_sections - self.disabled_sections

        if mode is Mode.DISCOVERY:
            return frozenset(self.plugin_store) - self.disabled_sections

        return frozenset()

    def _fetch_from_io(self, mode: Mode) -> SNMPRawData:
        """Select the sections we need to fetch and do that

        Note:
            There still may be some fetching from cache involved
            if the fetch interval was overridden by the user.

        Detection:

         * Mode.DISCOVERY:
           In this straight forward case we must determine all applicable sections for
           the device in question.

         * Mode.INVENTORY
           There is no need to try to detect all sections: For the inventory we have a
           set of sections known to be relevant for inventory plugins, and we can restrict
           detection to those.

         * Mode.CHECKING
           Sections needed for checking are known without detection. If the status data
           inventory is enabled, we detect from the inventory sections; but not those,
           which are fetched for checking anyway.

        """
        if self._backend is None:
            raise TypeError("missing backend")

        now = int(time.time())
        persisted_sections = self._section_store.load() if mode is Mode.CHECKING else {}
        section_names = self._get_selection(mode)
        section_names |= self._detect(
            select_from=self._get_detected_sections(mode) - section_names, backend=self._backend
        )
        if mode is Mode.DISCOVERY and not section_names:
            # Nothing to discover? That can't be right.
            raise MKFetcherError("Got no data")

        walk_cache = WalkCache(self.walk_cache_path / str(self._backend.hostname), self._logger)
        if mode is Mode.CHECKING:
            walk_cache_msg = "SNMP walk cache is enabled: Use any locally cached information"
            walk_cache.load()
        else:
            walk_cache.clear()
            walk_cache_msg = "SNMP walk cache cleared"

        fetched_data: dict[SectionName, SNMPRawDataElem] = {}
        for section_name in self._sort_section_names(section_names):
            try:
                _from, until, _section = persisted_sections[section_name]
                if now > until:
                    raise LookupError(section_name)
            except LookupError:
                self._logger.debug("%s: Fetching data (%s)", section_name, walk_cache_msg)

                fetched_data[section_name] = [
                    get_snmp_table(
                        section_name=section_name,
                        tree=tree,
                        walk_cache=walk_cache,
                        backend=self._backend,
                        log=self._logger.debug,
                    )
                    for tree in self.plugin_store[section_name].trees
                ]

        walk_cache.save()

        return fetched_data

    @classmethod
    def _sort_section_names(
        cls,
        section_names: Iterable[SectionName],
    ) -> Sequence[SectionName]:
        # In former Checkmk versions (<=1.4.0) CPU check plug-ins were
        # checked before other check plug-ins like interface checks.
        # In Checkmk 1.5 the order was random and
        # interface sections where executed before CPU check plug-ins.
        # This lead to high CPU utilization sent by device. Thus we have
        # to re-order the section names.
        return sorted(
            section_names,
            key=lambda x: (not ("cpu" in str(x) or x in cls.CPU_SECTIONS_WITHOUT_CPU_IN_NAME), x),
        )
