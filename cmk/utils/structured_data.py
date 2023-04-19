#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module handles tree structures for HW/SW Inventory system and
structured monitoring data of Check_MK.
"""

from __future__ import annotations

import gzip
import io
import pprint
from collections import Counter
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, NamedTuple, TypedDict

from cmk.utils import store
from cmk.utils.type_defs import HostName

# TODO Cleanup path in utils, base, gui, find ONE place (type defs or similar)
# TODO
# - is_empty -> __bool__
# - is_equal -> __eq__/__ne__
# - merge_with -> __add__
# - count_entries -> __len__?
# TODO Improve/clarify adding Attributes/Table while deserialization/filtering/merging/...

# TODO improve this
SDRawTree = dict
SDRawDeltaTree = dict

SDNodeName = str
SDPath = tuple[SDNodeName, ...]

SDKey = str
SDKeys = list[SDKey]
# TODO be more specific (None, str, float, int, DeltaValue:Tuple of previous)
SDValue = Any  # needs only to support __eq__

SDPairs = dict[SDKey, SDValue]
# TODO merge with cmk.base.api.agent_based.inventory_classes.py::AttrDict
SDPairsFromPlugins = Mapping[SDKey, SDValue]
LegacyPairs = dict[SDKey, SDValue]

# TODO SDRows and LegacyRows are the same for now, but SDRows will change in the future
# adapt werk 12389 if inner table structure changes from list[SDRow] to dict[SDRowIdent, SDRow]
SDKeyColumns = list[SDKey]
SDRowIdent = tuple[SDValue, ...]
SDRow = dict[SDKey, SDValue]
SDRows = dict[SDRowIdent, SDRow]
LegacyRows = list[SDRow]

# Used for de/serialization and retentions
ATTRIBUTES_KEY = "Attributes"
TABLE_KEY = "Table"

_PAIRS_KEY = "Pairs"
_KEY_COLUMNS_KEY = "KeyColumns"
_ROWS_KEY = "Rows"
_NODES_KEY = "Nodes"
_RETENTIONS_KEY = "Retentions"

SDEncodeAs = Callable[[SDValue], tuple[SDValue | None, SDValue | None]]
SDDeltaCounter = Counter[Literal["new", "changed", "removed"]]
SDFilterFunc = Callable[[SDKey], bool]


class SDFilter(NamedTuple):
    path: SDPath
    filter_nodes: SDFilterFunc
    filter_attributes: SDFilterFunc
    filter_columns: SDFilterFunc


class _RawIntervalFromConfigMandatory(TypedDict):
    interval: int
    visible_raw_path: str


class _RawIntervalFromConfig(_RawIntervalFromConfigMandatory, total=False):
    attributes: Literal["all"] | tuple[str, list[str]]
    columns: Literal["all"] | tuple[str, list[str]]


RawIntervalsFromConfig = Sequence[_RawIntervalFromConfig]


class RetentionIntervals(NamedTuple):
    cached_at: int
    cache_interval: int
    retention_interval: int

    @property
    def valid_until(self) -> int:
        return self.cached_at + self.cache_interval

    @property
    def keep_until(self) -> int:
        return self.cached_at + self.cache_interval + self.retention_interval

    def serialize(self) -> tuple[int, int, int]:
        return self.cached_at, self.cache_interval, self.retention_interval

    @classmethod
    def deserialize(cls, raw_intervals: tuple[int, int, int]) -> RetentionIntervals:
        return cls(*raw_intervals)


RawRetentionIntervalsByKeys = dict[SDKey, tuple[int, int, int]]
RetentionIntervalsByKeys = dict[SDKey, RetentionIntervals]


@dataclass(frozen=True)
class UpdateResult:
    reasons_by_path: dict[SDPath, list[str]] = field(default_factory=dict)

    @property
    def save_tree(self) -> bool:
        return bool(self.reasons_by_path)

    @classmethod
    def from_results(cls, results: Iterable[UpdateResult]) -> UpdateResult:
        update_result = cls()
        for result in results:
            for path, reasons in result.reasons_by_path.items():
                update_result.reasons_by_path.setdefault(path, []).extend(reasons)
        return update_result

    def add_attr_reason(self, path: SDPath, name: str, iterable: Iterable[str]) -> None:
        self.reasons_by_path.setdefault(path, []).append(
            f"[Attributes] Added {name}: {', '.join(iterable)}"
        )

    def add_row_reason(
        self, path: SDPath, ident: SDRowIdent, name: str, iterable: Iterable[str]
    ) -> None:
        self.reasons_by_path.setdefault(path, []).append(
            f"[Table] '{', '.join(ident)}': Added {name}: {', '.join(iterable)}"
        )

    def __repr__(self) -> str:
        if not self.reasons_by_path:
            return "No tree update.\n"

        lines = ["Updated inventory tree:"]
        for path, reasons in self.reasons_by_path.items():
            lines.append(f"  Path '{' > '.join(path)}':")
            lines.extend(f"    {r}" for r in reasons)
        return "\n".join(lines) + "\n"


#   .--IO------------------------------------------------------------------.
#   |                              ___ ___                                 |
#   |                             |_ _/ _ \                                |
#   |                              | | | | |                               |
#   |                              | | |_| |                               |
#   |                             |___\___/                                |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# TODO Centralize different stores and loaders of tree files:
#   - inventory/HOSTNAME, inventory/HOSTNAME.gz, inventory/.last
#   - inventory_archive/HOSTNAME/TIMESTAMP,
#   - inventory_delta_cache/HOSTNAME/TIMESTAMP_{TIMESTAMP,None}
#   - status_data/HOSTNAME, status_data/HOSTNAME.gz


def load_tree(filepath: Path) -> StructuredDataNode:
    if raw_tree := store.load_object_from_file(filepath, default=None):
        return StructuredDataNode.deserialize(raw_tree)
    return StructuredDataNode()


class TreeStore:
    def __init__(self, tree_dir: Path | str) -> None:
        self._tree_dir = Path(tree_dir)
        self._last_filepath = Path(tree_dir) / ".last"

    def load(self, *, host_name: HostName | str) -> StructuredDataNode:
        return load_tree(self._tree_file(host_name))

    def save(self, *, host_name: HostName, tree: StructuredDataNode, pretty: bool = False) -> None:
        self._tree_dir.mkdir(parents=True, exist_ok=True)

        tree_file = self._tree_file(host_name)

        output = tree.serialize()
        store.save_object_to_file(tree_file, output, pretty=pretty)

        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb") as f:
            f.write((repr(output) + "\n").encode("utf-8"))
        store.save_bytes_to_file(self._gz_file(host_name), buf.getvalue())

        # Inform Livestatus about the latest inventory update
        self._last_filepath.touch()

    def remove(self, *, host_name: HostName) -> None:
        self._tree_file(host_name).unlink(missing_ok=True)
        self._gz_file(host_name).unlink(missing_ok=True)

    def _tree_file(self, host_name: HostName) -> Path:
        return self._tree_dir / str(host_name)

    def _gz_file(self, host_name: HostName) -> Path:
        return self._tree_dir / f"{host_name}.gz"


class TreeOrArchiveStore(TreeStore):
    def __init__(self, tree_dir: Path | str, archive: Path | str) -> None:
        super().__init__(tree_dir)
        self._archive_dir = Path(archive)

    def load_previous(self, *, host_name: HostName | str) -> StructuredDataNode:
        if (tree_file := self._tree_file(host_name=host_name)).exists():
            return load_tree(tree_file)

        try:
            latest_archive_tree_file = max(
                self._archive_host_dir(host_name).iterdir(), key=lambda tp: int(tp.name)
            )
        except (FileNotFoundError, ValueError):
            return StructuredDataNode()

        return load_tree(latest_archive_tree_file)

    def _archive_host_dir(self, host_name: HostName) -> Path:
        return self._archive_dir / str(host_name)

    def archive(self, *, host_name: HostName) -> None:
        if not (tree_file := self._tree_file(host_name)).exists():
            return
        target_dir = self._archive_host_dir(host_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        tree_file.rename(target_dir / str(int(tree_file.stat().st_mtime)))
        self._gz_file(host_name).unlink(missing_ok=True)


# .
#   .--filters-------------------------------------------------------------.
#   |                       __ _ _ _                                       |
#   |                      / _(_) | |_ ___ _ __ ___                        |
#   |                     | |_| | | __/ _ \ '__/ __|                       |
#   |                     |  _| | | ||  __/ |  \__ \                       |
#   |                     |_| |_|_|\__\___|_|  |___/                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# TODO filter table rows?


def _use_all(_key: str) -> Literal[True]:
    return True


def _use_nothing(_key: str) -> Literal[False]:
    return False


def _make_choices_filter(choices: Sequence[str | int]) -> SDFilterFunc:
    return lambda key: key in choices


def make_filter(entry: tuple[SDPath, SDKeys | None] | dict) -> SDFilter:
    if isinstance(entry, tuple):
        path, keys = entry
        return (
            SDFilter(
                path=path,
                filter_nodes=_use_all,
                filter_attributes=_use_all,
                filter_columns=_use_all,
            )
            if keys is None
            else SDFilter(
                path=path,
                filter_nodes=_use_nothing,
                filter_attributes=_make_choices_filter(keys) if keys else _use_all,
                filter_columns=_make_choices_filter(keys) if keys else _use_all,
            )
        )

    return SDFilter(
        path=parse_visible_raw_path(entry["visible_raw_path"]),
        filter_attributes=make_filter_from_choice(entry.get("attributes")),
        filter_columns=make_filter_from_choice(entry.get("columns")),
        filter_nodes=make_filter_from_choice(entry.get("nodes")),
    )


def make_filter_from_choice(
    choice: tuple[str, Sequence[str]] | Literal["nothing"] | Literal["all"] | None
) -> SDFilterFunc:
    # TODO Improve:
    # For contact groups (via make_filter)
    #   - ('choices', ['some', 'keys'])
    #   - 'nothing' -> _use_nothing
    #   - None -> _use_all
    # For retention intervals (directly)
    #   - ('choices', ['some', 'keys'])
    #   - MISSING (see mk/base/agent_based/inventory.py::_get_intervals_from_config) -> _use_nothing
    #   - 'all' -> _use_all
    if isinstance(choice, tuple):
        return _make_choices_filter(choice[-1])
    if choice == "nothing":
        return _use_nothing
    return _use_all


# .
#   .--tree----------------------------------------------------------------.
#   |                          _                                           |
#   |                         | |_ _ __ ___  ___                           |
#   |                         | __| '__/ _ \/ _ \                          |
#   |                         | |_| | |  __/  __/                          |
#   |                          \__|_|  \___|\___|                          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class StructuredDataNode:
    def __init__(self, *, name: SDNodeName = "", path: SDPath | None = None) -> None:
        # Only root node has no name or path
        self.name = name
        self.path = path if path else tuple()
        self.attributes = Attributes(path=path)
        self.table = Table(path=path)
        self._nodes: dict[SDNodeName, StructuredDataNode] = {}

    def set_path(self, path: SDPath) -> None:
        self.path = path
        self.attributes.set_path(path)
        self.table.set_path(path)

    @property
    def nodes(self) -> Iterator[StructuredDataNode]:
        yield from self._nodes.values()

    #   ---common methods-------------------------------------------------------

    def is_empty(self) -> bool:
        if not (self.attributes.is_empty() and self.table.is_empty()):
            return False

        for node in self._nodes.values():
            if not node.is_empty():
                return False
        return True

    def is_equal(self, other: object) -> bool:
        if not isinstance(other, StructuredDataNode):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")

        if not (self.attributes.is_equal(other.attributes) and self.table.is_equal(other.table)):
            return False

        compared_keys = _compare_dict_keys(old_dict=other._nodes, new_dict=self._nodes)
        if compared_keys.only_old or compared_keys.only_new:
            return False

        for key in compared_keys.both:
            if not self._nodes[key].is_equal(other._nodes[key]):
                return False
        return True

    def count_entries(self) -> int:
        return sum(
            [
                self.attributes.count_entries(),
                self.table.count_entries(),
            ]
            + [node.count_entries() for node in self._nodes.values()]
        )

    def merge_with(self, other: object) -> StructuredDataNode:
        if not isinstance(other, StructuredDataNode):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")

        node = StructuredDataNode(name=self.name, path=self.path)

        node.add_attributes(self.attributes.merge_with(other.attributes))
        node.add_table(self.table.merge_with(other.table))

        compared_keys = _compare_dict_keys(old_dict=other._nodes, new_dict=self._nodes)

        for key in compared_keys.only_old:
            node.add_node(other._nodes[key])

        for key in compared_keys.both:
            node.add_node(self._nodes[key].merge_with(other._nodes[key]))

        for key in compared_keys.only_new:
            node.add_node(self._nodes[key])

        return node

    #   ---node methods---------------------------------------------------------

    def setdefault_node(self, path: SDPath) -> StructuredDataNode:
        if not path:
            return self

        name = path[0]
        node = self._nodes.setdefault(name, StructuredDataNode(name=name, path=self.path + (name,)))
        return node.setdefault_node(path[1:])

    def add_node(self, node: StructuredDataNode) -> StructuredDataNode:
        if not node.name:
            raise ValueError("Root cannot be added.")

        path = self.path + (node.name,)
        if node.name in self._nodes:
            the_node = self._nodes[node.name]
            the_node.set_path(path)
        else:
            dflt_node = StructuredDataNode(name=node.name, path=path)
            the_node = self._nodes.setdefault(node.name, dflt_node)

        the_node.add_attributes(node.attributes)
        the_node.add_table(node.table)

        for sub_node in node._nodes.values():
            the_node.add_node(sub_node)

        return the_node

    def add_attributes(self, attributes: Attributes) -> None:
        self.attributes.set_retentions(attributes.retentions)
        self.attributes.add_pairs(attributes.pairs)

    def add_table(self, table: Table) -> None:
        self.table.set_retentions(table.retentions)
        self.table.add_key_columns(table.key_columns)
        for ident, row in table._rows.items():
            self.table.add_row(ident, row)

    def get_node(self, path: SDPath) -> StructuredDataNode | None:
        if not path:
            return self
        return None if (node := self._nodes.get(path[0])) is None else node.get_node(path[1:])

    def get_table(self, path: SDPath) -> Table | None:
        return None if (node := self.get_node(path)) is None else node.table

    def get_attributes(self, path: SDPath) -> Attributes | None:
        return None if (node := self.get_node(path)) is None else node.attributes

    #   ---representation-------------------------------------------------------

    def __repr__(self) -> str:
        # Only used for repr/debug purposes
        return f"{self.__class__.__name__}({pprint.pformat(self.serialize())})"

    #   ---de/serializing-------------------------------------------------------

    def serialize(self) -> SDRawTree:
        return {
            ATTRIBUTES_KEY: self.attributes.serialize(),
            TABLE_KEY: self.table.serialize(),
            _NODES_KEY: {name: node.serialize() for name, node in self._nodes.items()},
        }

    @classmethod
    def deserialize(cls, raw_tree: SDRawTree) -> StructuredDataNode:
        if all(key in raw_tree for key in (ATTRIBUTES_KEY, TABLE_KEY, _NODES_KEY)):
            return cls._deserialize(name="", path=tuple(), raw_tree=raw_tree)
        return cls._deserialize_legacy(name="", path=tuple(), raw_tree=raw_tree)

    @classmethod
    def _deserialize(
        cls,
        *,
        name: SDNodeName,
        path: SDPath,
        raw_tree: SDRawTree,
    ) -> StructuredDataNode:
        node = cls(name=name, path=path)

        node.add_attributes(Attributes.deserialize(path=path, raw_pairs=raw_tree[ATTRIBUTES_KEY]))
        node.add_table(Table.deserialize(path=path, raw_rows=raw_tree[TABLE_KEY]))

        for raw_name, raw_node in raw_tree[_NODES_KEY].items():
            node.add_node(
                cls._deserialize(
                    name=raw_name,
                    path=path + (raw_name,),
                    raw_tree=raw_node,
                )
            )

        return node

    @classmethod
    def _deserialize_legacy(
        cls,
        *,
        name: SDNodeName,
        path: SDPath,
        raw_tree: SDRawTree,
    ) -> StructuredDataNode:
        node = cls(name=name, path=path)
        raw_pairs: SDPairs = {}

        for key, value in raw_tree.items():
            the_path = path + (key,)
            if isinstance(value, dict):
                if not value:
                    continue
                node.add_node(cls._deserialize_legacy(name=key, path=the_path, raw_tree=value))

            elif isinstance(value, list):
                if not value:
                    continue

                inst = node.setdefault_node((key,))
                if node._is_table(value):
                    inst.add_table(Table._deserialize_legacy(path=the_path, legacy_rows=value))
                    continue

                for idx, entry in enumerate(value):
                    inst.add_node(
                        cls._deserialize_legacy(
                            name=str(idx),
                            path=the_path + (str(idx),),
                            raw_tree=entry,
                        )
                    )

            else:
                raw_pairs.setdefault(key, value)

        node.add_attributes(Attributes._deserialize_legacy(path=path, legacy_pairs=raw_pairs))
        return node

    @staticmethod
    def _is_table(entries: list) -> bool:
        # Either we get:
        #   [
        #       {"column1": "value 11", "column2": "value 12",...},
        #       {"column1": "value 11", "column2": "value 12",...},
        #       ...
        #   ]
        # Or:
        #   [
        #       {"attr": "attr1", "table": [...], "node": {...}, "idx-node": [...]},
        #       ...
        #   ]
        return all(not isinstance(v, (list, dict)) for row in entries for v in row.values())

    #   ---delta----------------------------------------------------------------

    def compare_with(self, other: object) -> DeltaStructuredDataNode:
        if not isinstance(other, StructuredDataNode):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")

        delta_nodes: dict[SDNodeName, DeltaStructuredDataNode] = {}

        compared_keys = _compare_dict_keys(old_dict=other._nodes, new_dict=self._nodes)

        for key in compared_keys.only_new:
            node = self._nodes[key]
            if node.count_entries():
                delta_nodes[key] = DeltaStructuredDataNode.make_from_node(
                    node=node,
                    encode_as=_new_delta_tree_node,
                )

        for key in compared_keys.both:
            node = self._nodes[key]
            other_node = other._nodes[key]
            if node.is_equal(other_node):
                continue

            delta_node_result = node.compare_with(other_node)
            if delta_node_result.count_entries():
                delta_nodes[key] = delta_node_result

        for key in compared_keys.only_old:
            other_node = other._nodes[key]
            if other_node.count_entries():
                delta_nodes[key] = DeltaStructuredDataNode.make_from_node(
                    node=other_node,
                    encode_as=_removed_delta_tree_node,
                )

        return DeltaStructuredDataNode(
            name=self.name,
            path=self.path,
            attributes=self.attributes.compare_with(other.attributes),
            table=self.table.compare_with(other.table),
            _nodes=delta_nodes,
        )

    #   ---filtering------------------------------------------------------------

    def get_filtered_node(self, filters: list[SDFilter]) -> StructuredDataNode:
        filtered = StructuredDataNode(name=self.name, path=self.path)

        for f in filters:
            # First check if node exists
            node = self.get_node(f.path)
            if node is None:
                continue

            filtered_node = filtered.setdefault_node(f.path)

            filtered_node.add_attributes(
                node.attributes.get_filtered_attributes(f.filter_attributes)
            )
            filtered_node.add_table(node.table.get_filtered_table(f.filter_columns))

            for name, sub_node in node._nodes.items():
                # From GUI::permitted_paths: We always get a list of strs.
                if f.filter_nodes(str(name)):
                    filtered_node.add_node(sub_node)

        return filtered


# TODO Table: {IDENT: Attributes}?

TableRetentions = dict[SDRowIdent, RetentionIntervalsByKeys]


class Table:
    def __init__(
        self,
        *,
        path: SDPath | None = None,
        key_columns: SDKeyColumns | None = None,
        retentions: TableRetentions | None = None,
    ) -> None:
        self.path = path if path else tuple()
        self.key_columns = key_columns if key_columns else []
        self.retentions = retentions if retentions else {}
        self._rows: SDRows = {}

    def set_path(self, path: SDPath) -> None:
        self.path = path

    def add_key_columns(self, key_columns: SDKeyColumns) -> None:
        if not self.key_columns:
            self.key_columns = key_columns

    @property
    def rows(self) -> list[SDRow]:
        return list(self._rows.values())

    #   ---common methods-------------------------------------------------------

    def is_empty(self) -> bool:
        return not self._rows

    def is_equal(self, other: object) -> bool:
        if not isinstance(other, Table):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")

        compared_keys = _compare_dict_keys(old_dict=other._rows, new_dict=self._rows)
        if compared_keys.only_old or compared_keys.only_new:
            return False

        for key in compared_keys.both:
            if self._rows[key] != other._rows[key]:
                return False
        return True

    def count_entries(self) -> int:
        return sum(map(len, self._rows.values()))

    def merge_with(self, other: object) -> Table:
        if not isinstance(other, Table):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")

        if self.key_columns == other.key_columns:
            return self._merge_with(other)
        return self._merge_with_legacy(other)

    def _merge_with(self, other: Table) -> Table:
        table = Table(
            path=self.path,
            key_columns=self.key_columns,
            retentions={
                **self.retentions,
                **other.retentions,
            },
        )

        compared_keys = _compare_dict_keys(old_dict=other._rows, new_dict=self._rows)

        for key in compared_keys.only_old:
            table.add_row(key, other._rows[key])

        for key in compared_keys.both:
            table.add_row(key, {**self._rows[key], **other._rows[key]})

        for key in compared_keys.only_new:
            table.add_row(key, self._rows[key])

        return table

    def _merge_with_legacy(self, other: Table) -> Table:
        table = Table(
            path=self.path,
            key_columns=sorted(set(self.key_columns).intersection(other.key_columns)),
            retentions={
                **self.retentions,
                **other.retentions,
            },
        )

        # Re-calculates row identifiers
        table.add_rows(list(self._rows.values()))
        table.add_rows(list(other._rows.values()))

        return table

    #   ---table methods--------------------------------------------------------

    def add_rows(self, rows: Iterable[SDRow]) -> None:
        for row in rows:
            self.add_row(self._make_row_ident(row), row)

    def _make_row_ident(self, row: SDRow) -> SDRowIdent:
        return tuple(row[k] for k in self.key_columns if k in row)

    def add_row(self, ident: SDRowIdent, row: SDRow) -> None:
        if not self.key_columns:
            raise ValueError("Cannot add row due to missing key_columns")

        if not row:
            return

        self._rows.setdefault(ident, {}).update(row)

    def get_row(self, row: SDRow) -> SDRow:
        ident = self._make_row_ident(row)
        if ident in self.retentions:
            return {k: row[k] for k in self.retentions[ident] if k in row}
        return row

    #   ---retentions-----------------------------------------------------------

    def update_from_previous(  # pylint: disable=too-many-branches
        self,
        now: int,
        other: object,
        filter_func: SDFilterFunc,
        inv_intervals: RetentionIntervals,
    ) -> UpdateResult:
        if not isinstance(other, Table):
            raise TypeError(f"Cannot update {type(self)} from {type(other)}")

        self.add_key_columns(other.key_columns)

        old_filtered_rows = {
            ident: filtered_row
            for ident, row in other._rows.items()
            if (
                filtered_row := _get_filtered_dict(
                    row,
                    _make_retentions_filter_func(
                        filter_func=filter_func,
                        intervals_by_keys=other.retentions.get(ident),
                        now=now,
                    ),
                )
            )
        }
        self_filtered_rows = {
            ident: filtered_row
            for ident, row in self._rows.items()
            if (filtered_row := _get_filtered_dict(row, filter_func))
        }
        compared_filtered_idents = _compare_dict_keys(
            old_dict=old_filtered_rows,
            new_dict=self_filtered_rows,
        )

        retentions: TableRetentions = {}
        update_result = UpdateResult()
        for ident in compared_filtered_idents.only_old:
            old_row: SDRow = {}
            for key, value in old_filtered_rows[ident].items():
                old_row.setdefault(key, value)
                retentions.setdefault(ident, {})[key] = other.retentions[ident][key]

            if old_row:
                # Update row with key column entries
                old_row.update({k: other._rows[ident][k] for k in other.key_columns})
                self.add_row(ident, old_row)
                update_result.add_row_reason(self.path, ident, "row", old_row)

        for ident in compared_filtered_idents.both:
            compared_filtered_keys = _compare_dict_keys(
                old_dict=old_filtered_rows[ident],
                new_dict=self_filtered_rows[ident],
            )
            row: SDRow = {}
            for key in compared_filtered_keys.only_old:
                row.setdefault(key, other._rows[ident][key])
                retentions.setdefault(ident, {})[key] = other.retentions[ident][key]

            for key in compared_filtered_keys.both.union(compared_filtered_keys.only_new):
                retentions.setdefault(ident, {})[key] = inv_intervals

            if row:
                # Update row with key column entries
                row.update(
                    {
                        **{k: other._rows[ident][k] for k in other.key_columns},
                        **{k: self._rows[ident][k] for k in self.key_columns},
                    }
                )
                self.add_row(ident, row)
                update_result.add_row_reason(self.path, ident, "row", row)

        for ident in compared_filtered_idents.only_new:
            for key in self_filtered_rows[ident]:
                retentions.setdefault(ident, {})[key] = inv_intervals

        if retentions:
            self.set_retentions(retentions)
            for ident, intervals in retentions.items():
                update_result.add_row_reason(self.path, ident, "intervals", intervals)

        return update_result

    def set_retentions(self, table_retentions: TableRetentions) -> None:
        self.retentions = table_retentions

    def get_retention_intervals(self, key: SDKey, row: SDRow) -> RetentionIntervals | None:
        return self.retentions.get(self._make_row_ident(row), {}).get(key)

    #   ---representation-------------------------------------------------------

    def __repr__(self) -> str:
        # Only used for repr/debug purposes
        return f"{self.__class__.__name__}({pprint.pformat(self.serialize())})"

    #   ---de/serializing-------------------------------------------------------

    def serialize(self) -> SDRawTree:
        raw_table = {}
        if self._rows:
            raw_table.update(
                {
                    _KEY_COLUMNS_KEY: self.key_columns,
                    _ROWS_KEY: list(self._rows.values()),
                }
            )

        if self.retentions:
            raw_table[_RETENTIONS_KEY] = {
                ident: _serialize_retentions(intervals)
                for ident, intervals in self.retentions.items()
            }
        return raw_table

    @classmethod
    def deserialize(cls, *, path: SDPath, raw_rows: SDRawTree) -> Table:
        rows = raw_rows.get(_ROWS_KEY, [])
        if _KEY_COLUMNS_KEY in raw_rows:
            key_columns = raw_rows[_KEY_COLUMNS_KEY]
        else:
            key_columns = cls._get_default_key_columns(rows)

        table = cls(
            path=path,
            key_columns=key_columns,
            retentions={
                ident: _deserialize_retentions(raw_intervals)
                for ident, raw_intervals in raw_rows.get(_RETENTIONS_KEY, {}).items()
            },
        )
        table.add_rows(rows)
        return table

    @classmethod
    def _deserialize_legacy(cls, *, path: SDPath, legacy_rows: LegacyRows) -> Table:
        table = cls(
            path=path,
            key_columns=cls._get_default_key_columns(legacy_rows),
        )
        table.add_rows(legacy_rows)
        return table

    @staticmethod
    def _get_default_key_columns(rows: list[SDRow]) -> SDKeyColumns:
        return sorted({k for r in rows for k in r})

    #   ---delta----------------------------------------------------------------

    def compare_with(self, other: object) -> DeltaTable:
        if not isinstance(other, Table):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")

        key_columns = sorted(set(self.key_columns).union(other.key_columns))
        compared_keys = _compare_dict_keys(old_dict=other._rows, new_dict=self._rows)

        delta_rows: list[dict[SDKey, tuple[SDValue | None, SDValue | None]]] = []

        for key in compared_keys.only_old:
            delta_rows.append({k: _removed_delta_tree_node(v) for k, v in other._rows[key].items()})

        for key in compared_keys.both:
            # Note: Rows which have at least one change also provide all other fields.
            # Example:
            # If the version of a package (below "Software > Packages") has changed from 1.0 to 2.0
            # then it would be very annoying if the rest of the row is not shown.
            if (
                compared_dict_result := _compare_dicts(
                    old_dict=other._rows[key],
                    new_dict=self._rows[key],
                    keep_identical=True,
                )
            ).has_changes:
                delta_rows.append(compared_dict_result.result_dict)

        for key in compared_keys.only_new:
            delta_rows.append({k: _new_delta_tree_node(v) for k, v in self._rows[key].items()})

        return DeltaTable(
            path=self.path,
            key_columns=key_columns,
            rows=delta_rows,
        )

    #   ---filtering------------------------------------------------------------

    def get_filtered_table(self, filter_func: SDFilterFunc) -> Table:
        table = Table(path=self.path, key_columns=self.key_columns, retentions=self.retentions)
        for ident, row in self._rows.items():
            table.add_row(ident, _get_filtered_dict(row, filter_func))
        return table


class Attributes:
    def __init__(
        self,
        *,
        path: SDPath | None = None,
        retentions: RetentionIntervalsByKeys | None = None,
    ) -> None:
        self.path = path if path else tuple()
        self.retentions = retentions if retentions else {}
        self.pairs: SDPairs = {}

    def set_path(self, path: SDPath) -> None:
        self.path = path

    #   ---common methods-------------------------------------------------------

    def is_empty(self) -> bool:
        return self.pairs == {}

    def is_equal(self, other: object) -> bool:
        if not isinstance(other, Attributes):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")

        return self.pairs == other.pairs

    def count_entries(self) -> int:
        return len(self.pairs)

    def merge_with(self, other: object) -> Attributes:
        if not isinstance(other, Attributes):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")

        attributes = Attributes(
            path=self.path,
            retentions={
                **self.retentions,
                **other.retentions,
            },
        )
        attributes.add_pairs(self.pairs)
        attributes.add_pairs(other.pairs)

        return attributes

    #   ---attributes methods---------------------------------------------------

    def add_pairs(self, pairs: SDPairs | SDPairsFromPlugins) -> None:
        self.pairs.update(pairs)

    #   ---retentions-----------------------------------------------------------

    def update_from_previous(
        self,
        now: int,
        other: object,
        filter_func: SDFilterFunc,
        inv_intervals: RetentionIntervals,
    ) -> UpdateResult:
        if not isinstance(other, Attributes):
            raise TypeError(f"Cannot update {type(self)} from {type(other)}")

        compared_filtered_keys = _compare_dict_keys(
            old_dict=_get_filtered_dict(
                other.pairs,
                _make_retentions_filter_func(
                    filter_func=filter_func,
                    intervals_by_keys=other.retentions,
                    now=now,
                ),
            ),
            new_dict=_get_filtered_dict(self.pairs, filter_func),
        )

        pairs: SDPairs = {}
        retentions: RetentionIntervalsByKeys = {}
        for key in compared_filtered_keys.only_old:
            pairs.setdefault(key, other.pairs[key])
            retentions[key] = other.retentions[key]

        for key in compared_filtered_keys.both.union(compared_filtered_keys.only_new):
            retentions[key] = inv_intervals

        update_result = UpdateResult()
        if pairs:
            self.add_pairs(pairs)
            update_result.add_attr_reason(self.path, "pairs", pairs)

        if retentions:
            self.set_retentions(retentions)
            update_result.add_attr_reason(self.path, "intervals", retentions)

        return update_result

    def set_retentions(self, intervals_by_keys: RetentionIntervalsByKeys) -> None:
        self.retentions = intervals_by_keys

    def get_retention_intervals(self, key: SDKey) -> RetentionIntervals | None:
        return self.retentions.get(key)

    #   ---representation-------------------------------------------------------

    def __repr__(self) -> str:
        # Only used for repr/debug purposes
        return f"{self.__class__.__name__}({pprint.pformat(self.serialize())})"

    #   ---de/serializing-------------------------------------------------------

    def serialize(self) -> SDRawTree:
        raw_attributes = {}
        if self.pairs:
            raw_attributes[_PAIRS_KEY] = self.pairs

        if self.retentions:
            raw_attributes[_RETENTIONS_KEY] = _serialize_retentions(self.retentions)
        return raw_attributes

    @classmethod
    def deserialize(cls, *, path: SDPath, raw_pairs: SDRawTree) -> Attributes:
        attributes = cls(
            path=path,
            retentions=_deserialize_retentions(raw_pairs.get(_RETENTIONS_KEY)),
        )
        attributes.add_pairs(raw_pairs.get(_PAIRS_KEY, {}))
        return attributes

    @classmethod
    def _deserialize_legacy(cls, *, path: SDPath, legacy_pairs: LegacyPairs) -> Attributes:
        attributes = cls(path=path)
        attributes.add_pairs(legacy_pairs)
        return attributes

    #   ---delta----------------------------------------------------------------

    def compare_with(self, other: object) -> DeltaAttributes:
        if not isinstance(other, Attributes):
            raise TypeError(f"Cannot compare {type(self)} with {type(other)}")

        return DeltaAttributes(
            path=self.path,
            pairs=_compare_dicts(
                old_dict=other.pairs,
                new_dict=self.pairs,
                keep_identical=False,
            ).result_dict,
        )

    #   ---filtering------------------------------------------------------------

    def get_filtered_attributes(self, filter_func: SDFilterFunc) -> Attributes:
        attributes = Attributes(path=self.path, retentions=self.retentions)
        attributes.add_pairs(_get_filtered_dict(self.pairs, filter_func))
        return attributes


# .
#   .--delta tree----------------------------------------------------------.
#   |                  _      _ _          _                               |
#   |               __| | ___| | |_ __ _  | |_ _ __ ___  ___               |
#   |              / _` |/ _ \ | __/ _` | | __| '__/ _ \/ _ \              |
#   |             | (_| |  __/ | || (_| | | |_| | |  __/  __/              |
#   |              \__,_|\___|_|\__\__,_|  \__|_|  \___|\___|              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class DeltaStructuredDataNode:
    name: SDNodeName
    path: SDPath
    attributes: DeltaAttributes
    table: DeltaTable
    _nodes: dict[SDNodeName, DeltaStructuredDataNode]

    @classmethod
    def make_from_node(
        cls, *, node: StructuredDataNode, encode_as: SDEncodeAs
    ) -> DeltaStructuredDataNode:
        return cls(
            name=node.name,
            path=node.path,
            attributes=DeltaAttributes.make_from_attributes(
                attributes=node.attributes,
                encode_as=encode_as,
            ),
            table=DeltaTable.make_from_table(
                table=node.table,
                encode_as=encode_as,
            ),
            _nodes={
                child.name: cls.make_from_node(
                    node=child,
                    encode_as=encode_as,
                )
                for child in node.nodes
            },
        )

    def is_empty(self) -> bool:
        if not (self.attributes.is_empty() and self.table.is_empty()):
            return False

        for node in self._nodes.values():
            if not node.is_empty():
                return False
        return True

    def get_node(self, path: SDPath) -> DeltaStructuredDataNode | None:
        if not path:
            return self
        node = self._nodes.get(path[0])
        return None if node is None else node.get_node(path[1:])

    @property
    def nodes(self) -> Iterator[DeltaStructuredDataNode]:
        yield from self._nodes.values()

    def serialize(self) -> SDRawDeltaTree:
        return {
            "Attributes": self.attributes.serialize(),
            "Table": self.table.serialize(),
            "Nodes": {node.name: node.serialize() for node in self._nodes.values()},
        }

    @classmethod
    def deserialize(cls, raw_delta_tree: object) -> DeltaStructuredDataNode:
        return cls._deserialize(name="", path=tuple(), raw_delta_tree=raw_delta_tree)

    @classmethod
    def _deserialize(
        cls, *, name: SDNodeName, path: SDPath, raw_delta_tree: object
    ) -> DeltaStructuredDataNode:
        if not isinstance(raw_delta_tree, dict):
            raise TypeError()
        return cls(
            name=name,
            path=path,
            attributes=DeltaAttributes.deserialize(
                path=path,
                raw_delta_attributes=raw_delta_tree.get("Attributes", {}),
            ),
            table=DeltaTable.deserialize(
                path=path,
                raw_delta_table=raw_delta_tree.get("Table", {}),
            ),
            _nodes={
                raw_node_name: cls._deserialize(
                    name=raw_node_name,
                    path=path + (raw_node_name,),
                    raw_delta_tree=raw_node,
                )
                for raw_node_name, raw_node in raw_delta_tree.get("Nodes", {}).items()
            },
        )

    def count_entries(self) -> SDDeltaCounter:
        counter: SDDeltaCounter = Counter()
        counter.update(self.attributes.count_entries())
        counter.update(self.table.count_entries())
        for node in self._nodes.values():
            counter.update(node.count_entries())
        return counter


@dataclass(frozen=True)
class DeltaTable:
    path: SDPath
    key_columns: list[SDKey]
    rows: list[dict[SDKey, tuple[SDValue, SDValue]]]

    @classmethod
    def make_from_table(cls, *, table: Table, encode_as: SDEncodeAs) -> DeltaTable:
        return cls(
            path=table.path,
            key_columns=table.key_columns,
            rows=[{key: encode_as(value) for key, value in row.items()} for row in table.rows],
        )

    def is_empty(self) -> bool:
        return not self.rows

    def serialize(self) -> SDRawDeltaTree:
        return {"KeyColumns": self.key_columns, "Rows": self.rows} if self.rows else {}

    @classmethod
    def deserialize(cls, *, path: SDPath, raw_delta_table: object) -> DeltaTable:
        if not isinstance(raw_delta_table, dict):
            raise TypeError()
        return cls(
            path=path,
            key_columns=raw_delta_table.get("KeyColumns", []),
            rows=raw_delta_table.get("Rows", []),
        )

    def count_entries(self) -> SDDeltaCounter:
        counter: SDDeltaCounter = Counter()
        for row in self.rows:
            counter.update(_count_dict_entries(row))
        return counter


@dataclass(frozen=True)
class DeltaAttributes:
    path: SDPath
    pairs: dict[SDKey, tuple[SDValue, SDValue]]

    @classmethod
    def make_from_attributes(
        cls, *, attributes: Attributes, encode_as: SDEncodeAs
    ) -> DeltaAttributes:
        return cls(
            path=attributes.path,
            pairs={key: encode_as(value) for key, value in attributes.pairs.items()},
        )

    def is_empty(self) -> bool:
        return self.pairs == {}

    def serialize(self) -> SDRawDeltaTree:
        return {"Pairs": self.pairs} if self.pairs else {}

    @classmethod
    def deserialize(cls, *, path: SDPath, raw_delta_attributes: object) -> DeltaAttributes:
        if not isinstance(raw_delta_attributes, dict):
            raise TypeError()
        return cls(
            path=path,
            pairs=raw_delta_attributes.get("Pairs", {}),
        )

    def count_entries(self) -> SDDeltaCounter:
        return _count_dict_entries(self.pairs)


# .
#   .--helpers-------------------------------------------------------------.
#   |                  _          _                                        |
#   |                 | |__   ___| |_ __   ___ _ __ ___                    |
#   |                 | '_ \ / _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 | | | |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


class ComparedDictResult(NamedTuple):
    result_dict: dict[SDKey, tuple[SDValue | None, SDValue | None]]
    has_changes: bool


def _compare_dicts(*, old_dict: dict, new_dict: dict, keep_identical: bool) -> ComparedDictResult:
    """
    Format of compared entries:
      new:          {k: (None, new_value), ...}
      changed:      {k: (old_value, new_value), ...}
      removed:      {k: (old_value, None), ...}
      identical:    {k: (value, value), ...}
    """
    compared_keys = _compare_dict_keys(old_dict=old_dict, new_dict=new_dict)
    compared_dict: dict[SDKey, tuple[SDValue | None, SDValue | None]] = {}

    has_changes = False
    for k in compared_keys.both:
        if (new_value := new_dict[k]) != (old_value := old_dict[k]):
            compared_dict.setdefault(k, _changed_delta_tree_node(old_value, new_value))
            has_changes = True
        elif keep_identical:
            compared_dict.setdefault(k, _identical_delta_tree_node(old_value))

    compared_dict.update({k: _new_delta_tree_node(new_dict[k]) for k in compared_keys.only_new})
    compared_dict.update({k: _removed_delta_tree_node(old_dict[k]) for k in compared_keys.only_old})

    return ComparedDictResult(
        result_dict=compared_dict,
        has_changes=bool(has_changes or compared_keys.only_new or compared_keys.only_old),
    )


class ComparedDictKeys(NamedTuple):
    only_old: set
    both: set
    only_new: set


def _compare_dict_keys(*, old_dict: dict, new_dict: dict) -> ComparedDictKeys:
    """
    Returns the set relationships of the keys between two dictionaries:
    - relative complement of new_dict in old_dict
    - intersection of both
    - relative complement of old_dict in new_dict
    """
    old_keys, new_keys = set(old_dict), set(new_dict)
    return ComparedDictKeys(
        only_old=old_keys - new_keys,
        both=old_keys.intersection(new_keys),
        only_new=new_keys - old_keys,
    )


def _make_retentions_filter_func(
    *,
    filter_func: SDFilterFunc,
    intervals_by_keys: RetentionIntervalsByKeys | None,
    now: int,
) -> SDFilterFunc:
    return lambda k: bool(
        filter_func(k)
        and intervals_by_keys
        and (intervals := intervals_by_keys.get(k))
        and now <= intervals.keep_until
    )


def _get_filtered_dict(dict_: dict, filter_func: SDFilterFunc) -> dict:
    return {k: v for k, v in dict_.items() if filter_func(k)}


def _count_dict_entries(dict_: dict[SDKey, tuple[SDValue, SDValue]]) -> SDDeltaCounter:
    counter: SDDeltaCounter = Counter()
    for value0, value1 in dict_.values():
        match [value0 is None, value1 is None]:
            case [True, False]:
                counter["new"] += 1
            case [False, True]:
                counter["removed"] += 1
            case [False, False] if value0 != value1:
                counter["changed"] += 1
    return counter


def _new_delta_tree_node(value: SDValue) -> tuple[None, SDValue]:
    return (None, value)


def _removed_delta_tree_node(value: SDValue) -> tuple[SDValue, None]:
    return (value, None)


def _changed_delta_tree_node(old_value: SDValue, new_value: SDValue) -> tuple[SDValue, SDValue]:
    return (old_value, new_value)


def _identical_delta_tree_node(value: SDValue) -> tuple[SDValue, SDValue]:
    return (value, value)


def parse_visible_raw_path(raw_path: str) -> SDPath:
    return tuple(part for part in raw_path.split(".") if part)


def _serialize_retentions(
    intervals_by_keys: RetentionIntervalsByKeys,
) -> RawRetentionIntervalsByKeys:
    return {key: intervals.serialize() for key, intervals in intervals_by_keys.items()}


def _deserialize_retentions(
    raw_intervals_by_keys: RawRetentionIntervalsByKeys | None,
) -> RetentionIntervalsByKeys:
    if not raw_intervals_by_keys:
        return {}
    return {
        key: RetentionIntervals.deserialize(intervals)
        for key, intervals in raw_intervals_by_keys.items()
    }
