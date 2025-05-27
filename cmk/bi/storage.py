#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import pickle
import shutil
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Final, NewType

from redis import Redis

from cmk.ccc import store

from cmk.bi.aggregation import BIAggregation
from cmk.bi.filesystem import BIFileSystem, BIFileSystemCache, BIFileSystemVar
from cmk.bi.trees import BICompiledAggregation

# The actual uuid value that is used here is arbitrary. The most important thing is that this
# remains constant. The purpose of this namespace to enable us to generate consistent uuids based on
# an input value, i.e. aggregation id.
_IDENTIFIER_NAMESPACE: Final = uuid.UUID("e98ebcdf-debb-4c60-a0b9-e9c6df9b7e5e")

Identifier = NewType("Identifier", str)


def generate_identifier(value: str) -> Identifier:
    return Identifier(uuid.uuid5(_IDENTIFIER_NAMESPACE, value).hex)


class AggregationNotFound(Exception): ...


class AggregationStore:
    def __init__(self, fs_cache: BIFileSystemCache) -> None:
        self.fs_cache = fs_cache

    def get_by_identifier(self, identifier: Identifier) -> BICompiledAggregation:
        if not (path := self.fs_cache.compiled_aggregations / identifier).exists():
            raise AggregationNotFound(path)

        schema = store.load_object_from_pickle_file(path, default={})
        return BIAggregation.create_trees_from_schema(schema)

    def get(self, aggregation_id: str) -> BICompiledAggregation:
        return self.get_by_identifier(generate_identifier(aggregation_id))

    def yield_stored_identifiers(self) -> Generator[Identifier, None, None]:
        for path in self.fs_cache.compiled_aggregations.iterdir():
            if path.is_dir() or path.name.endswith(".new"):
                continue
            yield Identifier(path.name)

    def save(self, aggregation: BICompiledAggregation) -> None:
        path = self.fs_cache.compiled_aggregations / generate_identifier(aggregation.id)
        store.save_bytes_to_file(path, pickle.dumps(aggregation.serialize()))

    def delete_by_identifier(self, identifier: Identifier) -> None:
        (self.fs_cache.compiled_aggregations / identifier).unlink(missing_ok=True)


class FrozenAggregationStore:
    def __init__(self, fs_var: BIFileSystemVar) -> None:
        self.fs_var = fs_var

    def get(self, aggregation_id: str, branch_title: str) -> BICompiledAggregation | None:
        if not (path := self.get_branch_path(aggregation_id, branch_title)).exists():
            return None

        schema = ast.literal_eval(store.load_text_from_file(path))
        return BIAggregation.create_trees_from_schema(schema)

    def delete_by_identifier(self, identifier: Identifier) -> None:
        shutil.rmtree(self.fs_var.frozen_aggregations / identifier, ignore_errors=True)

    def delete(self, aggregation_id: str) -> None:
        self.delete_by_identifier(generate_identifier(aggregation_id))

    def exists(self, aggregation_id: str, branch_title: str) -> bool:
        return self.get_branch_path(aggregation_id, branch_title).exists()

    def save(self, aggregation: BICompiledAggregation, original_id: str, branch_title: str) -> None:
        branch_path = self.get_branch_path(original_id, branch_title)
        branch_path.parent.mkdir(exist_ok=True, parents=True)
        store.save_object_to_file(branch_path, aggregation.serialize())

    def get_branch_path(self, aggregation_id: str, branch_title: str) -> Path:
        return (
            self.fs_var.frozen_aggregations
            / generate_identifier(aggregation_id)
            / generate_identifier(branch_title)
        )


class MetadataStore:
    def __init__(self, fs: BIFileSystem) -> None:
        self.fs = fs

    def update_last_compilation(self, timestamp: float) -> None:
        store.save_text_to_file(self.fs.cache.last_compilation, str(timestamp))

    def get_last_compilation(self) -> float:
        if self.fs.cache.last_compilation.exists():
            return float(self.fs.cache.last_compilation.read_text())
        return 0.0

    def get_last_config_change(self) -> float:
        # NOTE: we are looking for the latest change in the config itself and all the configurations
        # hosted in the `multisite.d` directory.
        last_change = 0.0

        if self.fs.etc.config.exists():
            last_change = float(self.fs.etc.config.stat().st_mtime)

        for path_object in (self.fs.etc.multisite).iterdir():
            if path_object.is_dir():
                continue
            last_change = max(last_change, path_object.stat().st_mtime)

        return last_change


class LookupStore:
    def __init__(self, redis_client: Redis) -> None:
        self._redis_client = redis_client
        self._lookup_key = "bi:aggregation_lookup"
        self._lookup_key_lock = "bi:aggregation_lookup_lock"

    def base_lookup_key_exists(self) -> bool:
        return bool(self._redis_client.exists(self._lookup_key))

    def aggregation_lookup_exists(self, host_name: str, service_description: str | None) -> bool:
        lookup_key = self._get_aggregation_lookup_key(host_name, service_description)
        return bool(self._redis_client.exists(lookup_key))

    @contextmanager
    def get_aggregation_lookup_lock(self) -> Generator:
        lock = self._redis_client.lock(self._lookup_key_lock)
        try:
            lock.acquire()
            yield
        finally:
            if lock.owned():
                lock.release()

    def generate_aggregation_lookups(
        self, compiled_aggregations: dict[str, BICompiledAggregation]
    ) -> None:
        # The main task here is to add/update/remove keys without causing other processes
        # to wait for the updated data. There is no tempfile -> live mechanism.
        # Updates are done on the live data via pipeline, using transactions.
        part_of_aggregation_map = self._get_aggregation_lookup_map(compiled_aggregations)

        # Fetch existing keys
        existing_keys = set(self._redis_client.scan_iter(f"{self._lookup_key}:*"))

        # Update keys
        pipeline = self._redis_client.pipeline()
        for key, values in part_of_aggregation_map.items():
            pipeline.sadd(key, *values)
        pipeline.set(self._lookup_key, "1")

        if obsolete_keys := existing_keys - set(part_of_aggregation_map.keys()):
            pipeline.delete(*obsolete_keys)

        pipeline.execute()

    def _get_aggregation_lookup_key(self, host_name: str, service_description: str | None) -> str:
        return f"{self._lookup_key}:{host_name}:{service_description}"

    def _get_aggregation_lookup_map(
        self, compiled_aggregations: dict[str, BICompiledAggregation]
    ) -> dict[str, list[str]]:
        aggregation_lookup_map: dict[str, list[str]] = {}
        for aggr_id, compiled_aggregation in compiled_aggregations.items():
            for branch in compiled_aggregation.branches:
                for _, host_name, service_description in branch.required_elements():
                    # This information can be used to selectively load the relevant compiled
                    # aggregation for any host/service. Right now it is only an indicator if this
                    # host/service is part of an aggregation
                    key = self._get_aggregation_lookup_key(host_name, service_description)
                    value = f"{aggr_id}\t{branch.properties.title}"
                    aggregation_lookup_map.setdefault(key, []).append(value)

        return aggregation_lookup_map
