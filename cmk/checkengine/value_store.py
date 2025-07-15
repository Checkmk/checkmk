#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from ast import literal_eval
from collections.abc import (
    Callable,
    Iterator,
    Mapping,
    MutableMapping,
)
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from cmk.ccc import store
from cmk.ccc.hostaddress import HostName

import cmk.utils.paths
from cmk.utils.log import logger

type _PluginName = str
type _Item = str | None
type ValueStoreKey = tuple[HostName, _PluginName, _Item]
# In practice this will be Checkplugin/Item, but the value_store doesn't care, really.
type _ServiceID = tuple[object, _Item]
type _SerializedValueStore = Mapping[str, str]


@dataclass(frozen=True)
class _LastState:
    timestamp: float
    data: Mapping[ValueStoreKey, _SerializedValueStore]


class AllValueStoresStore:
    """Read and write values stored on disk

    Make sure to only update the values we want to update,
    and not to overwrite the whole file.
    """

    def __init__(
        self,
        path: Path,
        *,
        log_debug: Callable[[str], object] | None = None,
    ) -> None:
        self.path: Final = path
        self._log_debug: Final = (
            lambda x: logger.debug("value store: %s", x) if log_debug is None else log_debug
        )
        self._last_known_state: None | _LastState = None

    @staticmethod
    def _serialize(value: Mapping[ValueStoreKey, _SerializedValueStore]) -> str:
        return json.dumps(list(value.items()))

    @staticmethod
    def _deserialize(raw: str) -> Mapping[ValueStoreKey, _SerializedValueStore]:
        return {
            (HostName(hn), str(cn), None if i is None else str(i)): v
            for (hn, cn, i), v in json.loads(raw)
        }

    def load(self) -> Mapping[ValueStoreKey, _SerializedValueStore]:
        self._log_debug("loading from disk")
        try:
            self._last_known_state = _LastState(
                self.path.stat().st_mtime,
                (
                    data := (
                        self._deserialize(content)
                        if (content := store.load_text_from_file(self.path, lock=False).strip())
                        else {}
                    )
                ),
            )
        except FileNotFoundError:
            self._last_known_state = None
            data = {}

        return data

    def update(self, updated: Mapping[ValueStoreKey, _SerializedValueStore]) -> None:
        """Re-load and write the changes of the stored values

        This method will reload the values from disk, apply the changes
        as specified by the argument, and then write the result to disk.
        """
        self._log_debug("updating")

        self.path.parent.mkdir(parents=True, exist_ok=True)

        with store.locked(self.path):
            if (
                self._last_known_state is not None
                and self.path.stat().st_mtime == self._last_known_state.timestamp
            ):
                self._log_debug("already loaded")
                data = self._last_known_state.data
            else:
                self._log_debug("loading from disk")
                data = self.load()

            self._log_debug("writing to disk")
            new_data = {**data, **updated}
            store.save_text_to_file(self.path, self._serialize(new_data))
            self._last_known_state = _LastState(timestamp=self.path.stat().st_mtime, data=new_data)


class _ValueStore(MutableMapping[str, object]):
    """Implements the mutable mapping that is exposed to the plugins

    This class ensures that users indeed use strings as keys, and that the
    (potentially) failing literal_eval is done in the plugin scope.

    It would be nice to also move the repr to the plugin scope,
    but I can't see a way to do that without adding a redundant serialization
    in every __setitem__ call.

    Consider the plugin doing this:

    ```
    vs = get_value_store()
    d = vs.setdefault("key", {})
    d["kez"] = "value"
    ```

    For now we just trust the users to not mess up the `repr` implementation.
    """

    def __init__(self, initial_data: Mapping[str, str]) -> None:
        self._serialized: Final = {**initial_data}
        self._raw_serializer: Final = repr
        self._deserialize: Final = literal_eval
        self._accessed: dict[str, object] = {}

    def _serialize(self, value: object) -> str:  # TODO: reconsider
        try:
            return self._raw_serializer(value)
        except Exception as e:
            return f"<Exception in `{self._raw_serializer.__name__}` call: {e!r}>"

    @staticmethod
    def _validate_key(key: object) -> str:
        """Ensure we got a str

        We type it as `str` to the outside world, but
        we must not trust the users.
        """
        if not isinstance(key, str):
            raise TypeError(f"value store key must be `str`, got {key!r}")
        return key

    def __getitem__(self, key: str) -> object:
        key = self._validate_key(key)
        try:
            return self._accessed[key]
        except KeyError:
            pass
        return self._accessed.setdefault(key, self._deserialize(self._serialized[key]))

    def __setitem__(self, key: str, value: object) -> None:
        """
        It would be nice to serialize immediately (to raise errors in plugin scope),
        but that will not allow users to keep a reference to the object and modify it.
        """
        self._accessed[self._validate_key(key)] = value

    def __delitem__(self, key: str) -> None:
        key = self._validate_key(key)
        if key not in self._serialized and key not in self._accessed:
            raise KeyError(key)
        self._serialized.pop(key, None)
        self._accessed.pop(key, None)

    def __iter__(self) -> Iterator[str]:
        return iter(self._serialized | self._accessed)

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def export(self) -> Mapping[str, str]:
        return self._serialized | {k: self._serialize(v) for k, v in self._accessed.items()}


class ValueStoreManager:
    """Provide the ValueStores for one host

    This class provides method to load (upon __init__) and
    save a hosts value store, as well as selecting (via context manager)
    the name space for any given service.

    .. automethod:: ValueStoreManager.namespace

    .. automethod:: ValueStoreManager.save

    """

    STORAGE_PATH = cmk.utils.paths.counters_dir

    def __init__(self, host_name: HostName, all_stores_store: AllValueStoresStore) -> None:
        self._store: Final = all_stores_store
        self._all_stores = {**all_stores_store.load()}
        self._accessed_stores: dict[ValueStoreKey, _ValueStore] = {}
        self.active_service_interface: _ValueStore | None = None
        self._host_name = host_name

    def _make_value_store_key(
        self, host_name: HostName | None, service_id: _ServiceID
    ) -> ValueStoreKey:
        return (host_name or self._host_name, str(service_id[0]), service_id[1])

    @contextmanager
    def namespace(
        self, service_id: _ServiceID, host_name: HostName | None = None
    ) -> Iterator[None]:
        """Return a context manager

        In the corresponding context the value store for the given service is active
        """
        vs_key = self._make_value_store_key(host_name, service_id)
        vs = _ValueStore(self._all_stores.get(vs_key, {}))

        old_sif = self.active_service_interface
        self.active_service_interface = vs
        try:
            yield
        finally:
            if vs:  # only bother if the plugin actually put something in
                self._accessed_stores[vs_key] = vs
            self.active_service_interface = old_sif

    def save(self) -> None:
        """Write all accessed value stores to disk"""
        self._store.update({k: vs.export() for k, vs in self._accessed_stores.items()})
