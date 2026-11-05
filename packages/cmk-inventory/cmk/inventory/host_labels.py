#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from pathlib import Path

from cmk.ccc import store
from cmk.ccc.hostaddress import HostName


class _LabelsSerializer:
    def serialize(self, data: Mapping[str, str]) -> bytes:
        return json.dumps(data).encode("utf-8")

    @staticmethod
    def deserialize(raw: bytes) -> Mapping[str, str]:
        return {str(k): str(v) for k, v in json.loads(raw.decode("utf-8")).items()}


class InventorizedHostLabelsStore:
    def __init__(self, host_name: HostName, inventorized_host_labels_dir: Path) -> None:
        self._store = store.ObjectStore(
            path=inventorized_host_labels_dir / f"{host_name}.json",
            serializer=_LabelsSerializer(),
        )

    def load(self, *, debug: bool) -> Mapping[str, str]:
        return self._store.read_obj_explicit(default={}, debug=debug)

    def save(self, labels: Mapping[str, str]) -> None:
        self._store.path.parent.mkdir(parents=True, exist_ok=True)
        self._store.write_obj(labels)
