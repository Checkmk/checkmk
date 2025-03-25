#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from ast import literal_eval
from collections.abc import (
    Iterator,
    MutableMapping,
)
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import cmk.utils.paths
from cmk.utils.hostaddress import HostName
from cmk.utils.log import logger

from ._utils import DiskSyncedMapping

_PluginName = str
_Item = str | None
_UserKey = str
_ValueStoreKey = tuple[HostName, _PluginName, _Item, _UserKey]


# In practice this will be Checkplugin/Item, but the value_store doesn't care, really.
_ServiceID = tuple[object, _Item]


class _ValueStore(MutableMapping[_UserKey, Any]):
    """Implements the mutable mapping that is exposed to the plugins

    This class ensures that every service has its own name space in the
    persisted values, by adding the service ID (check plug-in name and item) to
    the user supplied keys.
    """

    def __init__(
        self,
        *,
        data: MutableMapping[_ValueStoreKey, str],
        service_id: _ServiceID,
        host_name: HostName,
    ) -> None:
        self._prefix = (host_name, str(service_id[0]), service_id[1])
        self._data = data

    def _map_key(self, user_key: _UserKey) -> _ValueStoreKey:
        if not isinstance(user_key, _UserKey):
            raise TypeError(f"value store key must be {_UserKey}")
        return (self._prefix[0], self._prefix[1], self._prefix[2], user_key)

    def __getitem__(self, key: _UserKey) -> Any:
        """
        Deserialize the original value only here.
        This is called in the plugins scope, so deserialization
        should only fail here, not for the whole value store file.
        """
        return literal_eval(self._data.__getitem__(self._map_key(key)))

    def __setitem__(self, key: _UserKey, value: Any) -> Any:
        """
        Immediately serialize the value only here.
        That way we can be certain we can store and load the whole file,
        and failure to (de)serialize individual values will only affect the
        offending plugin.
        """
        return self._data.__setitem__(self._map_key(key), repr(value))

    def __delitem__(self, key: _UserKey) -> Any:
        return self._data.__delitem__(self._map_key(key))

    def __iter__(self) -> Iterator[_UserKey]:
        return (
            user_key
            for (host_name, check_name, item, user_key) in self._data
            if (host_name, check_name, item) == self._prefix
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
        self._value_store: DiskSyncedMapping[_ValueStoreKey, str] = DiskSyncedMapping.make(
            path=self.STORAGE_PATH / host_name,
            log_debug=lambda x: logger.debug("value store: %s", x),
            serializer=lambda d: json.dumps(list(d.items())),
            deserializer=lambda raw: {tuple(k): v for k, v in json.loads(raw)},
        )
        self.active_service_interface: MutableMapping[str, Any] | None = None
        self._host_name = host_name

    @contextmanager
    def namespace(
        self, service_id: _ServiceID, host_name: HostName | None = None
    ) -> Iterator[None]:
        """Return a context manager

        In the corresponding context the value store for the given service is active
        """
        if host_name is None:
            host_name = self._host_name
        old_sif = self.active_service_interface
        self.active_service_interface = _ValueStore(
            data=self._value_store, service_id=service_id, host_name=host_name
        )
        try:
            yield
        finally:
            self.active_service_interface = old_sif

    def save(self) -> None:
        """Write all current values of this host to disk"""
        if isinstance(self._value_store, DiskSyncedMapping):
            self._value_store.commit()
