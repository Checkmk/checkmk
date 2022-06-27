#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import enum
from dataclasses import dataclass, field
from typing import Any, Dict

from cmk.utils.type_defs import Labels


class ObjectRefType(enum.Enum):
    """Known types of objects"""

    Folder = "Folder"
    Host = "Host"
    User = "User"
    Rule = "Rule"
    Ruleset = "Ruleset"


@dataclass
class ObjectRef:
    """Persisted in audit log and site changes to reference a Checkmk configuration object"""

    object_type: ObjectRefType
    ident: str
    labels: Labels = field(default_factory=dict)

    def serialize(self):
        serialized: Dict[str, Any] = {
            "object_type": self.object_type.name,
            "ident": self.ident,
        }
        if self.labels:
            serialized["labels"] = self.labels
        return serialized

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> "ObjectRef":
        return cls(
            object_type=ObjectRefType(serialized["object_type"]),
            ident=serialized["ident"],
            labels=serialized.get("labels", {}),
        )
