#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
These functions allow checks to keep a memory until the next time
the check is being executed. The most frequent use case is compu-
tation of rates from two succeeding counter values. This is done
via the helper function get_rate(). Averaging is another example
and done by get_average().

While a host is being checked this memory is kept in _cached_item_states.
That is a dictionary. The keys are unique to one check type and
item. The value is free form.

Note: The item state is kept in tmpfs and not reboot-persistant.
Do not store long-time things here. Also do not store complex
structures like log files or stuff.
"""

from contextlib import contextmanager
from pathlib import Path
import traceback
from typing import (
    Any,
    Callable,
    Dict,
    Final,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    Set,
    Tuple,
)
import cmk.utils.cleanup
import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckPluginName, HostName, Item
from cmk.utils.log import logger

_PluginName = str
_UserKey = str
_ValueStoreKey = Tuple[_PluginName, Item, _UserKey]


class _DynamicValueStore(Dict[_ValueStoreKey, Any]):
    """Represents the values that have been changed in a session

    This is a dict derivat that remembers if a key has been
    removed (having been removed is not the same as just not
    being in the dict at the moment!)
    """
    def __init__(self):
        super().__init__()
        self._removed_keys: Set[_ValueStoreKey] = set()

    @property
    def removed_keys(self) -> Set[_ValueStoreKey]:
        return self._removed_keys

    def __setitem__(self, key: _ValueStoreKey, value: Any) -> None:
        self._removed_keys.discard(key)
        super().__setitem__(key, value)

    def __delitem__(self, key: _ValueStoreKey) -> None:
        self._removed_keys.add(key)
        super().__delitem__(key)

    def pop(self, key: _ValueStoreKey, *args: Any) -> Any:
        self._removed_keys.add(key)
        return super().pop(key, *args)


class _StaticValueStore(Mapping[_ValueStoreKey, Any]):
    """Represents the values stored on disk"""

    STORAGE_PATH = Path(cmk.utils.paths.counters_dir)

    def __init__(self, host_name: HostName, log_debug: Callable[[str], None]) -> None:
        self._path: Final = self.STORAGE_PATH / host_name
        self._loaded_mtime: Optional[float] = None
        self._data: Mapping[_ValueStoreKey, Any] = {}
        self._log_debug = log_debug
        self.initial_load()

    def __getitem__(self, key: _ValueStoreKey) -> Any:
        return self._data.__getitem__(key)

    def __iter__(self) -> Iterator[_ValueStoreKey]:
        return self._data.__iter__()

    def __len__(self) -> int:
        return len(self._data)

    # TODO: 'load' is actually 'store' with falsey arguments,
    # and 'store' does more than storing.
    # -> we should consolidate those into a single 'disksync' method
    def initial_load(self) -> None:
        self._log_debug("Loading item states")

        try:
            store.aquire_lock(self._path)
            self._load()
        finally:
            store.release_lock(self._path)

    def _load(self) -> None:
        try:
            current_mtime = self._path.stat().st_mtime
        except FileNotFoundError:
            return

        if current_mtime == self._loaded_mtime:
            self._log_debug("already loaded")
            return

        self._data = store.load_object_from_file(self._path, default={}, lock=False)
        self._loaded_mtime = current_mtime

    def store(
        self,
        *,
        removed: Set[_ValueStoreKey],
        updated: Mapping[_ValueStoreKey, Any],
    ) -> None:
        """Re-load and then store the changes of the item state to disk

        Make sure the object is in sync with the file after writing.
        """
        self._log_debug("Storing item states")
        if not (removed or updated):
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)

        try:
            store.aquire_lock(self._path)
            self._load()

            data = {
                **{k: v for k, v in self._data.items() if k not in removed},
                **updated,
            }
            store.save_object_to_file(self._path, data, pretty=False)
            self._mtime = self._path.stat().st_mtime
            self._data = data
        except Exception:
            raise MKGeneralException(f"Cannot write to {self._path}: {traceback.format_exc()}")
        finally:
            store.release_lock(self._path)


class _EffectiveValueStore(MutableMapping[_ValueStoreKey, Any]):  # pylint: disable=too-many-ancestors
    """Implements the overlay logic between dynamic and static value store"""
    def __init__(
        self,
        *,
        dynamic: _DynamicValueStore,
        static: _StaticValueStore,
    ) -> None:
        self._dynamic = dynamic
        self.static = static

    def _keys(self) -> Set[_ValueStoreKey]:
        return {
            k for k in (set(self._dynamic) | set(self.static))
            if k not in self._dynamic.removed_keys
        }

    def __getitem__(self, key: _ValueStoreKey) -> Any:
        if key in self._dynamic.removed_keys:
            raise KeyError(key)
        try:
            return self._dynamic.__getitem__(key)
        except KeyError:
            return self.static.__getitem__(key)

    def __delitem__(self, key: _ValueStoreKey) -> None:
        if key in self._dynamic.removed_keys:
            raise KeyError(key)
        try:
            self._dynamic.__delitem__(key)
            # key is now marked as removed.
        except KeyError:
            _ = self.static[key]

    def pop(self, key: _ValueStoreKey, *args: Any) -> Any:
        try:
            return self._dynamic.pop(key)
            # key is now marked as removed.
        except KeyError:
            return self.static.get(key, *args)

    def __setitem__(self, key: _ValueStoreKey, value: Any) -> None:
        self._dynamic.__setitem__(key, value)

    def __iter__(self) -> Iterator[_ValueStoreKey]:
        return iter(self._keys())

    def __len__(self) -> int:
        return len(self._keys())

    def commit(self) -> None:
        self.static.store(
            removed=self._dynamic.removed_keys,
            updated=self._dynamic,
        )
        self._dynamic = _DynamicValueStore()


class _ValueStore(MutableMapping[_UserKey, Any]):  # pylint: disable=too-many-ancestors
    def __init__(
        self,
        *,
        data: MutableMapping[_ValueStoreKey, Any],
        service_id: Tuple[CheckPluginName, Item],
    ) -> None:
        self._prefix = (str(service_id[0]), service_id[1])
        self._data = data

    def _map_key(self, user_key: _UserKey) -> _ValueStoreKey:
        if self._prefix is None:
            raise MKGeneralException("accessing value store outside service context")
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
        return (user_key for (check_name, item, user_key) in self._data
                if (check_name, item) == self._prefix)

    def __len__(self) -> int:
        return sum(1 for _ in self)


class ValueStoreManager:
    def __init__(self, host_name: HostName) -> None:
        self._value_store = _EffectiveValueStore(
            dynamic=_DynamicValueStore(),
            static=_StaticValueStore(host_name, logger.debug),
        )
        self.active_service_interface: Optional[_ValueStore] = None

    @contextmanager
    def namespace(self, service_id: Tuple[CheckPluginName, Item]) -> Iterator[None]:
        old_sif = self.active_service_interface
        self.active_service_interface = _ValueStore(data=self._value_store, service_id=service_id)
        try:
            yield
        finally:
            self.active_service_interface = old_sif

    def save(self) -> None:
        if isinstance(self._value_store, _EffectiveValueStore):
            self._value_store.commit()
