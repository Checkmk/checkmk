#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import logging
from collections.abc import Iterable, Iterator, Mapping, MutableMapping
from pathlib import Path

from cmk.ccc import store
from cmk.ccc.exceptions import MKTimeout
from cmk.snmplib import SNMPRawDataElem, SNMPRowInfo, SNMPSectionMarker, SNMPSectionName

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="comparison-overlap"


class WalkCache(MutableMapping[tuple[str, str, bool], SNMPRowInfo]):
    """A cache on a per-fetchoid basis

    This serves two purposes (which is poor design):
     * deduplicate the fetch operations in case multiple sections
       are using the same OIDs
     * persist some fetched OIDS (`OIDCached`) to update the values only
       during discovery, never during checking.

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


class ConfiguredFetchIntervallCache:
    """Implement the (increased) fetch interval that can be configured by the users.

    This works on a "per-section" basis.
    Note that this is not the same as the walk cache, and not the same as the datasource
    caches.
    """

    def __init__(self, path: Path | str, config: Mapping[SNMPSectionName, int], now: float) -> None:
        self._path = Path(path)
        self._config = config
        self._now = now

    @staticmethod
    def _serialize(fetched_section: tuple[float, SNMPRawDataElem]) -> str:
        return json.dumps(fetched_section)

    @staticmethod
    def _deserialize(raw: str) -> tuple[float, SNMPRawDataElem]:
        return tuple(json.loads(raw))

    def _read(self, section: SNMPSectionName) -> str | None:
        try:
            return (self._path / section).read_text()
        except FileNotFoundError:
            return None

    def _write(self, section: SNMPSectionName, content: str) -> None:
        store.save_text_to_file(self._path / section, content)

    def load(self) -> Mapping[SNMPSectionName, tuple[float, SNMPRawDataElem]]:
        return {
            name: cached
            for name, validity_period in self._config.items()
            if (raw := self._read(name)) is not None
            and (cached := self._deserialize(raw))[0] + validity_period > self._now
        }

    def store(self, fetched_sections: Mapping[SNMPSectionName, SNMPRawDataElem]) -> None:
        for section_name in self._config:
            try:
                self._write(
                    section_name, self._serialize((self._now, fetched_sections[section_name]))
                )
            except KeyError:
                pass

    def section_marker(
        self, section_name: SNMPSectionName, creation_time: float
    ) -> SNMPSectionMarker:
        try:
            validity = self._config[section_name]
        except KeyError:
            return SNMPSectionMarker(section_name)
        return SNMPSectionMarker(f"{section_name}:cached({int(creation_time)},{int(validity)})")
