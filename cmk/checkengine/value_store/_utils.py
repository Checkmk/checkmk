#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import (
    Callable,
    Collection,
    Hashable,
    Iterator,
    Mapping,
    MutableMapping,
)
from pathlib import Path
from typing import Final, Self, TypeVar

from cmk.ccc import store

_TKey = TypeVar("_TKey", bound=Hashable)
_TValue = TypeVar("_TValue")
_TDefault = TypeVar("_TDefault")


class _DynamicDiskSyncedMapping(dict[_TKey, _TValue]):
    """Represents the values that have been changed in a session

    This is a dict derivat that remembers if a key has been
    removed (having been removed is not the same as just not
    being in the dict at the moment!)
    """

    def __init__(self) -> None:
        super().__init__()
        self._removed_keys: set[_TKey] = set()

    @property
    def removed_keys(self) -> set[_TKey]:
        return self._removed_keys

    def __setitem__(self, key: _TKey, value: _TValue) -> None:
        self._removed_keys.discard(key)
        super().__setitem__(key, value)

    def __delitem__(self, key: _TKey) -> None:
        self._removed_keys.add(key)
        super().__delitem__(key)

    def pop(self, key: _TKey, *args: _TValue | _TDefault) -> _TValue | _TDefault:
        self._removed_keys.add(key)
        return super().pop(key, *args)


class _StaticDiskSyncedMapping(Mapping[_TKey, _TValue]):
    """Represents the values stored on disk

    This class provides a Mapping-interface for the values stored
    on disk.

    The only way to modify the values is the disksync method.
    """

    def __init__(
        self,
        *,
        path: Path,
        log_debug: Callable[[str], None],
        serializer: Callable[[Mapping[_TKey, _TValue]], str],
        deserializer: Callable[[str], Mapping[_TKey, _TValue]],
    ) -> None:
        self._path: Final = path
        self._last_sync: float | None = None
        self._data: Mapping[_TKey, _TValue] = {}
        self._log_debug = log_debug
        self._serializer: Final = serializer
        self._deserializer: Final = deserializer
        self.disksync()

    def __getitem__(self, key: _TKey) -> _TValue:
        return self._data.__getitem__(key)

    def __iter__(self) -> Iterator[_TKey]:
        return self._data.__iter__()

    def __len__(self) -> int:
        return len(self._data)

    def disksync(
        self,
        *,
        removed: Collection[_TKey] = (),
        updated: Collection[tuple[_TKey, _TValue]] = (),
    ) -> None:
        """Re-load and write the changes of the stored values

        This method will reload the values from disk, apply the changes (remove keys
        and update values) as specified by the arguments, and then write the result to disk.

        When this method returns, the data provided via the Mapping-interface and
        the data stored on disk must be in sync.
        """
        self._log_debug("synchronizing")

        self._path.parent.mkdir(parents=True, exist_ok=True)

        with store.locked(self._path):
            if self._path.stat().st_mtime == self._last_sync:
                self._log_debug("already loaded")
            else:
                self._log_debug("loading from disk")
                self._data = (
                    self._deserializer(content)
                    if (content := store.load_text_from_file(self._path, lock=False).strip())
                    else {}
                )

            if removed or updated:
                data = {k: v for k, v in self._data.items() if k not in removed}
                data.update(updated)
                self._log_debug("writing to disk")
                store.save_text_to_file(self._path, self._serializer(data))
                self._data = data

            self._last_sync = self._path.stat().st_mtime


class DiskSyncedMapping(MutableMapping[_TKey, _TValue]):
    """Implements the overlay logic between dynamic and static value store"""

    @classmethod
    def make(
        cls,
        *,
        path: Path,
        log_debug: Callable[[str], None],
        serializer: Callable[[Mapping[_TKey, _TValue]], str],
        deserializer: Callable[[str], Mapping[_TKey, _TValue]],
    ) -> Self:
        return cls(
            dynamic=_DynamicDiskSyncedMapping(),
            static=_StaticDiskSyncedMapping(
                path=path,
                log_debug=log_debug,
                serializer=serializer,
                deserializer=deserializer,
            ),
        )

    def __init__(
        self,
        *,
        dynamic: _DynamicDiskSyncedMapping[_TKey, _TValue],
        static: _StaticDiskSyncedMapping[_TKey, _TValue],
    ) -> None:
        self._dynamic = dynamic
        self.static = static

    def _keys(self) -> set[_TKey]:
        return {
            k
            for k in (set(self._dynamic) | set(self.static))
            if k not in self._dynamic.removed_keys
        }

    def __getitem__(self, key: _TKey) -> _TValue:
        if key in self._dynamic.removed_keys:
            raise KeyError(key)
        try:
            return self._dynamic.__getitem__(key)
        except KeyError:
            return self.static.__getitem__(key)

    def __delitem__(self, key: _TKey) -> None:
        if key in self._dynamic.removed_keys:
            raise KeyError(key)
        try:
            self._dynamic.__delitem__(key)
            # key is now marked as removed.
        except KeyError:
            _ = self.static[key]

    def pop(self, key: _TKey, *args: _TValue | _TDefault) -> _TValue | _TDefault:
        try:
            return self._dynamic.pop(key)
            # key is now marked as removed.
        except KeyError:
            return self.static[key] if key in self.static else args[0]

    def __setitem__(self, key: _TKey, value: _TValue) -> None:
        self._dynamic.__setitem__(key, value)

    def __iter__(self) -> Iterator[_TKey]:
        return iter(self._keys())

    def __len__(self) -> int:
        return len(self._keys())

    def commit(self) -> None:
        self.static.disksync(
            removed=self._dynamic.removed_keys,
            updated=self._dynamic.items(),
        )
        self._dynamic = _DynamicDiskSyncedMapping()
