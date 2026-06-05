#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Mapping, Sequence
from typing import Self


class ConnectorObject[HostT: str](abc.ABC):
    """Abstract base class for transporting connector infos.

    Children of this class are used to transport objects between
    the two execution phases of connections.

    The main purpose is to ensure that the objects can be
    serialized and deserialized between sites.
    """

    @classmethod
    def deserialize_attributes(cls, serialized: dict) -> Self:  # type: ignore[type-arg]
        """Construct an object from the serialized attributes"""
        raise NotImplementedError()

    def serialize(self) -> dict:  # type: ignore[type-arg]
        """Serialize the object for transport

        Nested structures are allowed. Only objects that can be handled by
        ast.literal_eval() are allowed.
        """
        return {
            "class_name": self.__class__.__name__,
            "attributes": self._serialize_attributes(),
        }

    @abc.abstractmethod
    def _serialize_attributes(
        self,
    ) -> Mapping[
        str,
        Sequence[HostT]
        | int
        | Mapping[str, Mapping[str, str]]
        | Mapping[str, Mapping[str, Mapping[str, str]]],
    ]:
        """Serialize object type specific attributes for transport"""
        raise NotImplementedError()

    def is_empty(self) -> bool:
        return True


class NullObject[HostT: str](ConnectorObject[HostT]):
    @classmethod
    def deserialize_attributes(cls, _serialized: dict) -> Self:  # type: ignore[type-arg]
        return cls()

    def _serialize_attributes(self) -> Mapping[str, Sequence[HostT] | int]:
        return {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class FailedToContactRemoteSite[HostT: str](ConnectorObject[HostT]):
    @classmethod
    def deserialize_attributes(cls, _serialized: dict) -> Self:  # type: ignore[type-arg]
        return cls()

    def _serialize_attributes(self) -> Mapping[str, Sequence[HostT] | int]:
        return {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
