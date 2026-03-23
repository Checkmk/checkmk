# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import NotRequired, TypedDict


class JSONOwnerReference(TypedDict):
    uid: str
    controller: NotRequired[bool]
    kind: str
    name: str
    namespace: NotRequired[str]


JSONOwnerReferences = Sequence[JSONOwnerReference]
