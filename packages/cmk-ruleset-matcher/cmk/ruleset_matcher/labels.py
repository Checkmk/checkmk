#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for dealing with Checkmk labels of all kind"""

from __future__ import annotations

import contextlib
import json
from abc import ABC, abstractmethod
from ast import literal_eval
from collections.abc import Callable, Iterable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Literal, Self, TypedDict

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName

from ._type_defs import ServiceName

Labels = Mapping[str, str]

LabelSource = Literal["discovered", "ruleset", "explicit"]
LabelSources = dict[str, LabelSource]


class HostLabelValueDict(TypedDict):
    value: str
    plugin_name: str | None


class BaseLabel:
    """Representing a label in Checkmk"""

    __slots__ = "name", "value"

    def __init__(self, name: str, value: str) -> None:
        if not isinstance(name, str):
            raise MKGeneralException("Invalid label name given: Only unicode strings are allowed")
        self.name: Final = name

        if not isinstance(value, str):
            raise MKGeneralException("Invalid label value given: Only unicode strings are allowed")
        self.value: Final = value

    @property
    def label(self) -> str:
        return f"{self.name}:{self.value}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name!r}, {self.value!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            raise TypeError(f"cannot compare {type(self)} to {type(other)}")
        return self.name == other.name and self.value == other.value

    @classmethod
    def from_str(cls, label: str) -> BaseLabel:
        name, value = label.split(":", 1)
        return cls(name=name, value=value)


class ServiceLabel(BaseLabel):
    __slots__ = ()


class HostLabel(BaseLabel):
    """Representing a host label in Checkmk during runtime

    Besides the label itself it keeps the information which plug-in discovered the host label
    """

    __slots__ = ("plugin_name",)

    @classmethod
    def deserialize(cls, raw: Mapping[str, str]) -> Self:
        return cls(
            name=str(raw["name"]),
            value=str(raw["value"]),
            plugin_name=(
                None
                if (raw_plugin_name := raw.get("plugin_name")) is None
                else str(raw_plugin_name)
            ),
        )

    # rather use (de)serialize
    @classmethod
    def from_dict(cls, name: str, dict_label: HostLabelValueDict) -> Self:
        value = dict_label["value"]
        assert isinstance(value, str)

        raw_name = dict_label["plugin_name"]
        plugin_name = None if raw_name is None else str(raw_name)

        return cls(name, value, plugin_name)

    def __init__(
        self,
        name: str,
        value: str,
        plugin_name: str | None = None,
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
                "plugin_name": self.plugin_name,
            }
        )

    def id(self) -> str:
        """The identity of the label.

        This is important for discovery.
        As long as this does not change, we're talking about "the same" label (but it might have changed).
        """
        return self.label  # Fairly certain this is wrong. Shouldn't this be 'name'?

    def comparator(self) -> str:
        return self.value

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
        # Skip labels discovered by the previous HW/SW Inventory approach
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

    def __init__(self, node_name: HostName, discovered_host_labels_dir: Path) -> None:
        super().__init__()
        self._store = store.ObjectStore(
            path=discovered_host_labels_dir / f"{node_name}.mk",
            serializer=LabelsSerializer(),
        )
        self.file_path: Final = self._store.path

    def load(self) -> Sequence[HostLabel]:
        return [
            HostLabel(
                name,
                raw["value"],
                None if (raw_name := raw["plugin_name"]) is None else str(raw_name),
            )
            for name, raw in self._store.read_obj(default={}).items()
        ]

    def save(self, labels: Iterable[HostLabel]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._store.write_obj({l.name: l.to_dict() for l in labels})


class BuiltinLabelsKey(StrEnum):
    """Centralized place for all possible builtin labels.

    This is to ease documentation.
    """

    SITE = "cmk/site"
    CUSTOMER = "cmk/customer"


type BuiltinLabels = Mapping[BuiltinLabelsKey, str]


class _BuiltinLabelsSerializer:
    def serialize(self, data: Labels) -> bytes:
        return json.dumps(data).encode("utf-8")

    @staticmethod
    def deserialize(raw: bytes) -> Labels:
        return {str(k): str(v) for k, v in json.loads(raw.decode("utf-8")).items()}


class BuiltinHostLabelsStore:
    """Persistence of the builtin host labels.

    Unlike the discovered host labels this is a *single* file per site: the builtin labels
    (``cmk/site`` and, on managed sites, ``cmk/customer``) are identical for every host
    monitored on the site. It is written when the config is (re)generated (activation, site
    creation, update) and only read - never written - on the checking/base side.
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._store = store.ObjectStore(path=path, serializer=_BuiltinLabelsSerializer())
        self.file_path: Final = self._store.path
        self.locked: Final = self._store.locked

    def load(self) -> Labels:
        return self._store.read_obj(default={})

    def save(self, labels: Labels) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._store.write_obj(labels)


def update_builtin_host_labels(file_path: Path, labels: BuiltinLabels) -> None:
    """Merge ``labels`` into the per-site builtin host labels file, preserving other keys.

    Each owner writes only its own keys (base config generation: ``cmk/site``; managed
    services: ``cmk/customer``), so the independent config-generation, update-config and
    sample-config plugins never clobber one another.
    """
    store = BuiltinHostLabelsStore(file_path)
    with store.locked():
        store.save({**store.load(), **{str(k): v for k, v in labels.items()}})


# Label group specific types
AndOrNotLiteral = Literal["and", "or", "not"]
LabelGroup = Sequence[tuple[AndOrNotLiteral, str]]
LabelGroups = Sequence[tuple[AndOrNotLiteral, LabelGroup]]


def single_label_group_from_labels(
    labels: Sequence[str] | dict[str, Any], operator: AndOrNotLiteral = "and"
) -> LabelGroups:
    if isinstance(labels, dict):
        # Convert the old condition labels to a label group
        # e.g.: labels = {"os": "linux", "foo": {"$ne": "bar"}}
        #           ->   [("and", [("and", "os:linux"), ("not", "foo:bar")])]
        andornot_labels: list[tuple[AndOrNotLiteral, str]] = []
        for key, value in labels.items():
            if isinstance(value, dict):
                andornot_labels.append(("not", f"{key}:{value['$ne']}"))
            else:
                andornot_labels.append(("and", f"{key}:{value}"))
        return [("and", andornot_labels)]

    return [
        (
            "and",
            [(operator, label) for label in labels],
        )
    ]


class ABCLabelConfig(ABC):
    @abstractmethod
    def host_labels(self, host_name: HostName, /) -> Labels:
        """Returns the configured labels for a host"""

    @abstractmethod
    def service_labels(
        self,
        host_name: HostName,
        service_name: ServiceName,
        labels_of_host: Callable[[HostName], Labels],
        /,
    ) -> Labels:
        """Returns the configured labels for a service"""


class LabelManager:
    """Helper class to manage access to the host and service labels"""

    def __init__(
        self,
        label_config: ABCLabelConfig,
        nodes_of: Mapping[HostName, Sequence[HostName]],
        explicit_host_labels: Mapping[HostName, Labels],
        *,
        discovered_host_labels_dir: Path,
        builtin_host_labels_file: Path,
    ) -> None:
        self._nodes_of: Final = nodes_of
        self._label_config: Final = label_config
        # Public + mutable: the keepalive checker reassigns these per command to point
        # at the per-serial helper config dir. Long term we should detach the label file
        # lookups from LabelManager and pass the paths through the call chain at the points
        # where labels are actually read.
        # Once this is immutable, see if we should make 'discovered_labels_of_host' private again.
        self.discovered_host_labels_dir = discovered_host_labels_dir
        self.builtin_host_labels_file = builtin_host_labels_file
        self.explicit_host_labels: Mapping[HostName, Labels] = explicit_host_labels

        self.__labels_of_host: dict[HostName, Labels] = {}
        self.__builtin_host_labels: Labels | None = None
        self.__builtin_host_labels_path: Path | None = None

    def labels_of_host(self, hostname: HostName) -> Labels:
        """Returns the effective set of host labels from all available sources

        1. Discovered labels
        2. Ruleset "Host labels"
        3. Explicit labels (via host/folder config)
        4. Builtin labels

        Last one wins.
        """
        with contextlib.suppress(KeyError):
            return self.__labels_of_host[hostname]

        return self.__labels_of_host.setdefault(
            hostname,
            {
                **self._discovered_labels_of_host(hostname),
                **self._label_config.host_labels(hostname),
                **self.explicit_host_labels.get(hostname, {}),
                **self._builtin_host_labels(),
            },
        )

    def label_sources_of_host(self, hostname: HostName) -> LabelSources:
        """Returns the effective set of host label keys with their source
        identifier instead of the value Order and merging logic is equal to
        _get_host_labels()"""
        labels: LabelSources = {}
        labels.update(dict.fromkeys(self._discovered_labels_of_host(hostname), "discovered"))
        labels.update(dict.fromkeys(self._label_config.host_labels(hostname), "ruleset"))
        labels.update(dict.fromkeys(self.explicit_host_labels.get(hostname, {}), "explicit"))
        labels.update(dict.fromkeys(self._builtin_host_labels(), "discovered"))
        return labels

    def _builtin_host_labels(self) -> Labels:
        # Read once per file path; re-read when the keepalive checker repoints
        # builtin_host_labels_file at a per-serial helper config dir.
        if (
            self.__builtin_host_labels is None
            or self.__builtin_host_labels_path != self.builtin_host_labels_file
        ):
            self.__builtin_host_labels_path = self.builtin_host_labels_file
            self.__builtin_host_labels = BuiltinHostLabelsStore(
                self.builtin_host_labels_file
            ).load()
        return self.__builtin_host_labels

    # I am not sure if this really should be public (see above).
    def discovered_labels_of_host(self, hostname: HostName) -> Sequence[HostLabel]:
        return (
            DiscoveredHostLabelsStore(hostname, self.discovered_host_labels_dir).load()
            if (nodes := self._nodes_of.get(hostname)) is None
            else merge_cluster_labels(
                [
                    DiscoveredHostLabelsStore(node, self.discovered_host_labels_dir).load()
                    for node in nodes
                ]
            )
        )

    def _discovered_labels_of_host(self, hostname: HostName) -> Labels:
        return {l.name: l.value for l in self.discovered_labels_of_host(hostname)}

    def labels_of_service(
        self,
        hostname: HostName,
        service_desc: ServiceName,
        discovered_labels: Labels,
    ) -> Labels:
        """Returns the effective set of service labels from all available sources

        1. Discovered labels
        2. Ruleset "Host labels"

        Last one wins.
        """
        labels: dict[str, str] = {}
        labels.update(discovered_labels)
        labels.update(
            self._label_config.service_labels(hostname, service_desc, self.labels_of_host)
        )

        return labels

    def label_sources_of_service(
        self,
        hostname: HostName,
        service_desc: ServiceName,
        discovered_labels: Labels,
    ) -> LabelSources:
        """Returns the effective set of host label keys with their source
        identifier instead of the value Order and merging logic is equal to
        _get_host_labels()"""
        labels: LabelSources = {}
        labels.update(dict.fromkeys(discovered_labels, "discovered"))
        labels.update(
            dict.fromkeys(
                self._label_config.service_labels(hostname, service_desc, self.labels_of_host),
                "ruleset",
            )
        )

        return labels


def merge_cluster_labels(all_node_labels: Iterable[Iterable[HostLabel]]) -> Sequence[HostLabel]:
    """A cluster has all its nodes labels. Last node wins."""
    return list({l.name: l for node_labels in all_node_labels for l in node_labels}.values())
