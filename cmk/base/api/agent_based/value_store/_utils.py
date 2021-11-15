#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from ast import literal_eval
from contextlib import contextmanager
from pathlib import Path
from typing import (
    Any,
    Callable,
    Container,
    Dict,
    Final,
    Hashable,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import cmk.utils.cleanup
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.log import logger
from cmk.utils.type_defs import CheckPluginName, HostName, Item

_PluginName = str
_UserKey = str
_ValueStoreKey = Tuple[_PluginName, Item, _UserKey]

_TKey = TypeVar("_TKey", bound=Hashable)
_TValue = TypeVar("_TValue")
_TDefault = TypeVar("_TDefault")


class _DynamicDiskSyncedMapping(Dict[_TKey, _TValue]):
    """Represents the values that have been changed in a session

    This is a dict derivat that remembers if a key has been
    removed (having been removed is not the same as just not
    being in the dict at the moment!)
    """

    def __init__(self):
        super().__init__()
        self._removed_keys: Set[_TKey] = set()

    @property
    def removed_keys(self) -> Set[_TKey]:
        return self._removed_keys

    def __setitem__(self, key: _TKey, value: _TValue) -> None:
        self._removed_keys.discard(key)
        super().__setitem__(key, value)

    def __delitem__(self, key: _TKey) -> None:
        self._removed_keys.add(key)
        super().__delitem__(key)

    def pop(self, key: _TKey, *args: Union[_TValue, _TDefault]) -> Union[_TValue, _TDefault]:
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
        self._last_sync: Optional[float] = None
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
        removed: Container[_TKey] = (),
        updated: Iterable[Tuple[_TKey, _TValue]] = (),
    ) -> None:
        """Re-load and write the changes of the stored values

        This method will reload the values from disk, apply the changes (remove keys
        and update values) as specified by the arguments, and then write the result to disk.

        When this method returns, the data provided via the Mapping-interface and
        the data stored on disk must be in sync.
        """
        self._log_debug("synchronizing")

        self._path.parent.mkdir(parents=True, exist_ok=True)

        try:
            store.aquire_lock(self._path)

            if self._path.stat().st_mtime == self._last_sync:
                self._log_debug("already loaded")
            else:
                self._log_debug("loading from disk")
                self._data = self._deserializer(
                    store.load_text_from_file(self._path, default="{}", lock=False)
                )

            if removed or updated:
                data = {k: v for k, v in self._data.items() if k not in removed}
                data.update(updated)
                self._log_debug("writing to disk")
                store.save_text_to_file(self._path, self._serializer(data))
                self._data = data

            self._last_sync = self._path.stat().st_mtime
        except Exception as exc:
            raise MKGeneralException from exc
        finally:
            store.release_lock(self._path)


class _DiskSyncedMapping(MutableMapping[_TKey, _TValue]):  # pylint: disable=too-many-ancestors
    """Implements the overlay logic between dynamic and static value store"""

    @classmethod
    def make(
        cls,
        *,
        path: Path,
        log_debug: Callable[[str], None],
        serializer: Callable[[Mapping[_TKey, _TValue]], str],
        deserializer: Callable[[str], Mapping[_TKey, _TValue]],
    ) -> "_DiskSyncedMapping":
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

    def _keys(self) -> Set[_TKey]:
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

    def pop(self, key: _TKey, *args: Union[_TValue, _TDefault]) -> Union[_TValue, _TDefault]:
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


class _ValueStore(MutableMapping[_UserKey, Any]):  # pylint: disable=too-many-ancestors
    """Implements the mutable mapping that is exposed to the plugins

    This class ensures that every service has its own name space in the
    persisted values, by adding the service ID (check plugin name and item) to
    the user supplied keys.
    """

    def __init__(
        self,
        *,
        data: MutableMapping[_ValueStoreKey, Any],
        service_id: Tuple[CheckPluginName, Item],
    ) -> None:
        self._prefix = (str(service_id[0]), service_id[1])
        self._data = data

    def _map_key(self, user_key: _UserKey) -> _ValueStoreKey:
        if not isinstance(user_key, _UserKey):
            raise TypeError(f"value store key must be {_UserKey}")
        return (self._prefix[0], self._prefix[1], user_key)

    def __getitem__(self, key: _UserKey) -> Any:
        return self._data.__getitem__(self._map_key(key))

    def __setitem__(self, key: _UserKey, value: Any) -> Any:
        return self._data.__setitem__(self._map_key(key), value)

    def __delitem__(self, key: _UserKey) -> Any:
        return self._data.__delitem__(self._map_key(key))

    def __iter__(self) -> Iterator[_UserKey]:
        return (
            user_key
            for (check_name, item, user_key) in self._data
            if (check_name, item) == self._prefix
        )

    def __len__(self) -> int:
        return sum(1 for _ in self)


class ValueStoreManager:
    """Provide the ValueStores for one host

    This class provides method to load (upon __init__) and
    save a hosts value store, as well as selecting (via context manager)
    the name space for any given service.

    .. automethod:: ValueStoreManager.namespace

    .. automethod:: ValueStoreManager.save

    """

    STORAGE_PATH = Path(cmk.utils.paths.counters_dir)

    def __init__(self, host_name: HostName) -> None:
        self._value_store: _DiskSyncedMapping[_ValueStoreKey, Any] = _DiskSyncedMapping.make(
            path=self.STORAGE_PATH / str(host_name),
            log_debug=lambda x: logger.debug("value store: %s", x),
            serializer=repr,
            deserializer=literal_eval,
        )
        self.active_service_interface: Optional[_ValueStore] = None

    @contextmanager
    def namespace(self, service_id: Tuple[CheckPluginName, Item]) -> Iterator[None]:
        """Return a context manager

        In the corresponding context the value store for the given service is active
        """
        old_sif = self.active_service_interface
        self.active_service_interface = _ValueStore(data=self._value_store, service_id=service_id)
        try:
            yield
        finally:
            self.active_service_interface = old_sif

    def save(self) -> None:
        """Write all current values of this host to disk"""
        if isinstance(self._value_store, _DiskSyncedMapping):
            self._value_store.commit()
