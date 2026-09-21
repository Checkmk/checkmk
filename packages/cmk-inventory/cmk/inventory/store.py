#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import gzip
import io
import json
import os
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict

from cmk.ccc import store
from cmk.ccc.hostaddress import HostName

from .paths import InventoryPaths, TreePath, TreePathGz
from .serialization import deserialize_tree, SDRawTree, serialize_tree
from .structured_data import ImmutableTree, MutableTree


def _transform_tree_path(tree_path: TreePath, mtime: float) -> None:
    with store.locked(tree_path.path), store.locked(tree_path.legacy):
        if raw_tree := store.load_object_from_file(tree_path.legacy, default=None):
            _save_raw_tree(tree_path, raw_tree)
            os.utime(tree_path.path, (mtime, mtime))
    tree_path.legacy.unlink(missing_ok=True)


def _transform_tree_path_gz(tree_path_gz: TreePathGz, mtime: float) -> None:
    with store.locked(tree_path_gz.path), store.locked(tree_path_gz.legacy):
        if gzipped := store.load_bytes_from_file(tree_path_gz.legacy, default=b""):
            _save_raw_tree_gz(tree_path_gz, parse_from_gzipped(gzipped))
            os.utime(tree_path_gz.path, (mtime, mtime))
    tree_path_gz.legacy.unlink(missing_ok=True)


def transform(tree_path: TreePath | TreePathGz, mtime: float) -> None:
    match tree_path:
        case TreePath():
            _transform_tree_path(tree_path, mtime)
        case TreePathGz():
            _transform_tree_path_gz(tree_path, mtime)


def rename(
    omd_root: Path, *, old_host_name: HostName, new_host_name: HostName
) -> Sequence[Literal["inv", "invarch"]]:
    inv_paths = InventoryPaths(omd_root)
    old_inv_tree_path = inv_paths.inventory_tree(HostName(old_host_name))
    old_inv_tree_path_gz = inv_paths.inventory_tree_gz(HostName(old_host_name))
    old_stat_tree_path = inv_paths.status_data_tree(HostName(old_host_name))
    new_inv_tree_path = inv_paths.inventory_tree(HostName(new_host_name))
    new_inv_tree_path_gz = inv_paths.inventory_tree_gz(HostName(new_host_name))
    new_stat_tree_path = inv_paths.status_data_tree(HostName(new_host_name))
    actions: set[Literal["inv", "invarch"]] = set()
    for old_file_path, new_file_path in [
        (old_inv_tree_path.path, new_inv_tree_path.path),
        (old_inv_tree_path.legacy, new_inv_tree_path.legacy),
        (old_inv_tree_path_gz.path, new_inv_tree_path_gz.path),
        (old_inv_tree_path_gz.legacy, new_inv_tree_path_gz.legacy),
        (old_stat_tree_path.path, new_stat_tree_path.path),
        (old_stat_tree_path.legacy, new_stat_tree_path.legacy),
    ]:
        try:
            old_file_path.rename(new_file_path)
            actions.add("inv")
        except FileNotFoundError:
            pass

    for old_directory, new_directory in [
        (
            inv_paths.archive_host(HostName(old_host_name)),
            inv_paths.archive_host(HostName(new_host_name)),
        ),
        (
            inv_paths.delta_cache_host(HostName(old_host_name)),
            inv_paths.delta_cache_host(HostName(new_host_name)),
        ),
    ]:
        try:
            shutil.move(old_directory, new_directory)
            actions.add("invarch")
        except FileNotFoundError:
            pass

    return list(actions)


def load_tree_from_tree_path(tree_path: TreePath) -> ImmutableTree:
    if raw_tree := store.load_text_from_file(tree_path.path):
        return deserialize_tree(json.loads(raw_tree))
    if raw_tree := store.load_object_from_file(tree_path.legacy, default=None):
        return deserialize_tree(raw_tree)
    return ImmutableTree()


class SDMeta(TypedDict):
    version: Literal["1"]
    do_archive: bool


def _save_raw_tree(tree_path: TreePath, raw_tree: SDRawTree) -> None:
    tree_path.path.parent.mkdir(parents=True, exist_ok=True)
    store.save_text_to_file(tree_path.path, json.dumps(raw_tree) + "\n")


def _save_raw_tree_gz(tree_path_gz: TreePathGz, meta_and_raw_tree: SDMetaAndRawTree) -> None:
    tree_path_gz.path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write((json.dumps(meta_and_raw_tree) + "\n").encode("utf-8"))
    store.save_bytes_to_file(tree_path_gz.path, buf.getvalue())


@dataclass(frozen=True)
class _TreePathMTime:
    mtime: float
    is_json: bool


def _compute_mtime(tree_path: TreePath) -> _TreePathMTime | None:
    try:
        return _TreePathMTime(tree_path.path.stat().st_mtime, True)
    except FileNotFoundError:
        # TODO CMK-23408
        try:
            return _TreePathMTime(tree_path.legacy.stat().st_mtime, False)
        except FileNotFoundError:
            return None


def _archive_inventory_tree(inv_paths: InventoryPaths, host_name: HostName) -> None:
    tree_path = inv_paths.inventory_tree(host_name)
    if (tree_path_mtime := _compute_mtime(tree_path)) is None:
        return

    tree_path_gz = inv_paths.inventory_tree_gz(host_name)
    archive_tree = inv_paths.archive_tree(host_name, int(tree_path_mtime.mtime))

    if tree_path_mtime.is_json:
        inv_paths.archive_host(host_name).mkdir(parents=True, exist_ok=True)
        tree_path.path.rename(archive_tree.path)
        tree_path_gz.path.unlink(missing_ok=True)
        tree_path.legacy.unlink(missing_ok=True)
        tree_path_gz.legacy.unlink(missing_ok=True)
        return

    if raw_tree := store.load_object_from_file(tree_path.legacy, default=None):
        inv_paths.archive_host(host_name).mkdir(parents=True, exist_ok=True)
        store.save_text_to_file(archive_tree.path, json.dumps(raw_tree))
        tree_path.legacy.unlink(missing_ok=True)
        tree_path_gz.legacy.unlink(missing_ok=True)


def make_meta(*, do_archive: bool) -> SDMeta:
    return SDMeta(version="1", do_archive=do_archive)


class SDMetaAndRawTree(TypedDict):
    meta: SDMeta
    raw_tree: SDRawTree


def _parse_raw_meta(raw_meta: object) -> SDMeta:
    if not isinstance(raw_meta, dict):
        raise TypeError(raw_meta)
    if not isinstance(version := raw_meta.get("version"), str):
        raise TypeError(version)
    if not isinstance(do_archive := raw_meta.get("do_archive"), bool):
        raise TypeError(do_archive)
    match version:
        case "1":
            return SDMeta(version=version, do_archive=do_archive)
        case _:
            raise ValueError(version)


def _parse_raw_tree(raw_tree: object) -> SDRawTree:
    if not isinstance(raw_tree, dict):
        raise TypeError(raw_tree)
    return SDRawTree(
        Attributes=raw_tree.get("Attributes", {}),
        Table=raw_tree.get("Table", {}),
        Nodes=raw_tree.get("Nodes", {}),
    )


def _parse_from_unzipped(raw: object) -> SDMetaAndRawTree:
    if not isinstance(raw, dict):
        raise TypeError(raw)
    if set(raw) == {"meta", "raw_tree"}:
        # Handle future versions
        return SDMetaAndRawTree(
            meta=_parse_raw_meta(raw.get("meta")),
            raw_tree=_parse_raw_tree(raw.get("raw_tree")),
        )
    return SDMetaAndRawTree(
        meta=SDMeta(
            version="1",
            do_archive=raw.get("meta_do_archive", True),
        ),
        raw_tree=SDRawTree(
            Attributes=raw.get("Attributes", {}),
            Table=raw.get("Table", {}),
            Nodes=raw.get("Nodes", {}),
        ),
    )


def _parse_dump(dump: bytes) -> object:
    try:
        return json.loads(dump.decode("utf-8"))
    except json.JSONDecodeError:
        # TODO CMK-23408
        return ast.literal_eval(dump.decode("utf-8"))


def parse_from_gzipped(gzipped: bytes) -> SDMetaAndRawTree:
    # Note: Since Checkmk 2.1 we explicitly extract "Attributes", "Table" or "Nodes" while
    # deserialization. This means that "meta_*" are not taken into account and we stay
    # compatible.
    return _parse_from_unzipped(_parse_dump(gzip.GzipFile(fileobj=io.BytesIO(gzipped)).read()))


def parse_from_raw_status_data_tree(dump: bytes) -> ImmutableTree:
    return deserialize_tree(_parse_dump(dump))


class RawInventoryStore:
    def __init__(self, omd_root: Path) -> None:
        self.inv_paths = InventoryPaths(omd_root)

    def save_meta_and_raw_inventory_tree(
        self, *, host_name: HostName, meta_and_raw_tree: SDMetaAndRawTree, timestamp: int
    ) -> None:
        tree_path = self.inv_paths.inventory_tree(host_name)
        _save_raw_tree(tree_path, meta_and_raw_tree["raw_tree"])
        tree_path.legacy.unlink(missing_ok=True)
        os.utime(tree_path.path, (timestamp, timestamp))

        tree_path_gz = self.inv_paths.inventory_tree_gz(host_name)
        _save_raw_tree_gz(tree_path_gz, meta_and_raw_tree)
        tree_path_gz.legacy.unlink(missing_ok=True)
        os.utime(tree_path_gz.path, (timestamp, timestamp))

    def archive_inventory_tree(self, *, host_name: HostName) -> None:
        _archive_inventory_tree(self.inv_paths, host_name)


class InventoryStore:
    def __init__(self, omd_root: Path) -> None:
        self.inv_paths = InventoryPaths(omd_root)

    def load_inventory_tree(self, *, host_name: HostName) -> ImmutableTree:
        return load_tree_from_tree_path(self.inv_paths.inventory_tree(host_name))

    def save_inventory_tree(
        self, *, host_name: HostName, tree: MutableTree | ImmutableTree, meta: SDMeta
    ) -> None:
        raw_tree = serialize_tree(tree)

        tree_path = self.inv_paths.inventory_tree(host_name)
        _save_raw_tree(tree_path, raw_tree)
        tree_path.legacy.unlink(missing_ok=True)

        tree_path_gz = self.inv_paths.inventory_tree_gz(host_name)
        _save_raw_tree_gz(tree_path_gz, SDMetaAndRawTree(meta=meta, raw_tree=raw_tree))
        tree_path_gz.legacy.unlink(missing_ok=True)

        # Inform Livestatus about the latest inventory update
        self.inv_paths.inventory_marker_file.touch()

    def remove_inventory_tree(self, *, host_name: HostName) -> None:
        tree_path = self.inv_paths.inventory_tree(host_name)
        tree_path.path.unlink(missing_ok=True)
        tree_path.legacy.unlink(missing_ok=True)

        tree_path_gz = self.inv_paths.inventory_tree_gz(host_name)
        tree_path_gz.path.unlink(missing_ok=True)
        tree_path_gz.legacy.unlink(missing_ok=True)

    def load_status_data_tree(self, *, host_name: HostName) -> ImmutableTree:
        return load_tree_from_tree_path(self.inv_paths.status_data_tree(host_name))

    def save_status_data_tree(
        self, *, host_name: HostName, tree: MutableTree | ImmutableTree
    ) -> None:
        tree_path = self.inv_paths.status_data_tree(host_name)
        _save_raw_tree(tree_path, serialize_tree(tree))
        tree_path.legacy.unlink(missing_ok=True)

        # Inform Livestatus about the latest inventory update
        self.inv_paths.status_data_marker_file.touch()

    def remove_status_data_tree(self, *, host_name: HostName) -> None:
        tree_path = self.inv_paths.status_data_tree(host_name)
        tree_path.path.unlink(missing_ok=True)
        tree_path.legacy.unlink(missing_ok=True)

    def load_previous_inventory_tree(self, *, host_name: HostName) -> ImmutableTree:
        if tree := load_tree_from_tree_path(self.inv_paths.inventory_tree(host_name)):
            return tree

        try:
            latest_archive_file_path = max(
                self.inv_paths.archive_host(host_name).iterdir(),
                key=lambda fp: int(fp.with_suffix("").name),
            )
        except FileNotFoundError, ValueError:
            return ImmutableTree()

        return load_tree_from_tree_path(
            TreePath.from_archive_or_delta_cache_file_path(latest_archive_file_path)
        )

    def archive_inventory_tree(self, *, host_name: HostName) -> None:
        _archive_inventory_tree(self.inv_paths, host_name)
