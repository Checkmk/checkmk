#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import Field
from typing import ClassVar, Protocol


# copied from typeshed
class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[object]]]
