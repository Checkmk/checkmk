#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for dealing with Checkmk labels of all kind"""

from __future__ import annotations

from ast import literal_eval
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Final, Literal, Self, TypedDict

from cmk.ccc import store
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site

import cmk.utils.paths
from cmk.utils.hostaddress import HostName
from cmk.utils.sectionname import SectionName

Labels = Mapping[str, str]

LabelSource = Literal["discovered", "ruleset", "explicit"]
LabelSources = dict[str, LabelSource]


class HostLabelValueDict(TypedDict):
    value: str
    plugin_name: str | None


class _Label:
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


class ServiceLabel(_Label):
    __slots__ = ()


class HostLabel(_Label):
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
                else SectionName(raw_plugin_name)
            ),
        )

    # rather use (de)serialize
    @classmethod
    def from_dict(cls, name: str, dict_label: HostLabelValueDict) -> Self:
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

    def __init__(self, hostname: HostName) -> None:
        super().__init__()
        self._store = store.ObjectStore(
            path=cmk.utils.paths.discovered_host_labels_dir / f"{hostname}.mk",
            serializer=LabelsSerializer(),
        )
        self.file_path: Final = self._store.path

    def load(self) -> Sequence[HostLabel]:
        return [
            HostLabel(
                name,
                raw["value"],
                None if (raw_name := raw["plugin_name"]) is None else SectionName(raw_name),
            )
            for name, raw in self._store.read_obj(default={}).items()
        ]

    def save(self, labels: Iterable[HostLabel]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._store.write_obj({l.name: l.to_dict() for l in labels})


def get_builtin_host_labels() -> Labels:
    return {"cmk/site": omd_site()}


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
