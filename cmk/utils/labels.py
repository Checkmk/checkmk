#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for dealing with Checkmk labels of all kind"""

from __future__ import annotations

import os
from ast import literal_eval
from collections.abc import Mapping
from typing import Any, Final, TypedDict

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.site import omd_site
from cmk.utils.type_defs import HostName, SectionName

Labels = Mapping[str, str]
UpdatedHostLabelsEntry = tuple[str, float, str]


class HostLabelValueDict(TypedDict):
    value: str
    plugin_name: str | None


class _Label:
    """Representing a label in Checkmk"""

    __slots__ = "name", "value"

    def __init__(self, name: str, value: str) -> None:

        if not isinstance(name, str):
            raise MKGeneralException("Invalid label name given: Only unicode strings are allowed")
        self.name: Final = str(name)

        if not isinstance(value, str):
            raise MKGeneralException("Invalid label value given: Only unicode strings are allowed")
        self.value: Final = str(value)

    @property
    def label(self) -> str:
        return f"{self.name}:{self.value}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r}, {self.value!r})"

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            raise TypeError(f"cannot compare {type(self)} to {type(other)}")
        return self.name == other.name and self.value == other.value


class ServiceLabel(_Label):
    __slots__ = ()


class HostLabel(_Label):
    """Representing a host label in Checkmk during runtime

    Besides the label itself it keeps the information which plugin discovered the host label
    """

    __slots__ = ("plugin_name",)

    @classmethod
    def deserialize(cls, raw: Mapping[str, str]) -> "HostLabel":
        return cls(
            name=str(raw["name"]),
            value=str(raw["value"]),
            plugin_name=None
            if (raw_plugin_name := raw.get("plugin_name")) is None
            else SectionName(raw_plugin_name),
        )

    # rather use (de)serialize
    @classmethod
    def from_dict(cls, name: str, dict_label: HostLabelValueDict) -> "HostLabel":
        value = dict_label["value"]
        assert isinstance(value, str)

        raw_name = dict_label["plugin_name"]
        plugin_name = None if raw_name is None else SectionName(raw_name)

        return cls(name, value, plugin_name)

    def __init__(
        self,
        name: str,
        value: str,
        plugin_name: SectionName | None = None,
    ) -> None:
        super().__init__(name, value)
        self.plugin_name: Final = plugin_name

    def serialize(self) -> Mapping[str, str]:
        return (
            {
                "name": self.name,
                "value": self.value,
            }
            if self.plugin_name is None
            else {
                "name": self.name,
                "value": self.value,
                "plugin_name": str(self.plugin_name),
            }
        )

    # rather use (de)serialize
    def to_dict(self) -> HostLabelValueDict:
        return {
            "value": self.value,
            "plugin_name": None if self.plugin_name is None else str(self.plugin_name),
        }

    def __repr__(self) -> str:
        return f"HostLabel({self.name!r}, {self.value!r}, plugin_name={self.plugin_name!r})"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, HostLabel):
            raise TypeError(f"{other!r} is not of type HostLabel")
        return (
            self.name == other.name
            and self.value == other.value
            and self.plugin_name == other.plugin_name
        )

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)


class LabelsSerializer:
    def serialize(self, data: Mapping[str, HostLabelValueDict]) -> bytes:
        return repr(data).encode("utf-8")

    @staticmethod
    def deserialize(raw: bytes) -> Mapping[str, HostLabelValueDict]:
        # Skip labels discovered by the previous HW/SW inventory approach
        # (which was addded+removed in 1.6 beta)
        return {
            str(key): {
                "value": str(val["value"]),
                "plugin_name": str(val["plugin_name"]) if "plugin_name" in val else None,
            }
            for key, val in literal_eval(raw.decode("utf-8")).items()
            if isinstance(val, dict)
        }


class DiscoveredHostLabelsStore:
    """Managing persistence of discovered labels"""

    def __init__(self, hostname: HostName) -> None:
        super().__init__()
        self._store = store.ObjectStore(
            path=cmk.utils.paths.discovered_host_labels_dir / f"{hostname}.mk",
            serializer=LabelsSerializer(),
        )
        self.file_path: Final = self._store.path

    def load(self) -> Mapping[str, HostLabelValueDict]:
        return self._store.read_obj(default={})

    def save(self, labels: Mapping[str, HostLabelValueDict]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._store.write_obj(labels)


class BuiltinHostLabelsStore:
    def load(self) -> Mapping[str, HostLabelValueDict]:
        return {
            "cmk/site": {"value": omd_site(), "plugin_name": "builtin"},
        }


def get_host_labels_entry_of_host(host_name: HostName) -> UpdatedHostLabelsEntry:
    """Returns the host labels entry of the given host"""
    path = DiscoveredHostLabelsStore(host_name).file_path
    with path.open() as f:
        return (path.name, path.stat().st_mtime, f.read())


def get_updated_host_label_files(newer_than: float) -> list[UpdatedHostLabelsEntry]:
    """Returns the host label file content + meta data which are newer than the given timestamp"""
    updated_host_labels = []
    for path in sorted(cmk.utils.paths.discovered_host_labels_dir.glob("*.mk")):
        mtime = path.stat().st_mtime
        if path.stat().st_mtime <= newer_than:
            continue  # Already known to central site

        with path.open() as f:
            updated_host_labels.append((path.name, mtime, f.read()))
    return updated_host_labels


def save_updated_host_label_files(updated_host_labels: list[UpdatedHostLabelsEntry]) -> None:
    """Persists the data previously read by get_updated_host_label_files()"""
    for file_name, mtime, content in updated_host_labels:
        file_path = cmk.utils.paths.discovered_host_labels_dir / file_name
        store.save_text_to_file(file_path, content)
        os.utime(file_path, (mtime, mtime))
