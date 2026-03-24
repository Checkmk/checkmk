# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NotRequired, TypedDict


class JSONResourceRequirement(TypedDict):
    # In reality, this type is much more complex; for now we just extract cpu and memory
    # as we use this for container and pod resource requirements, and these are
    # the only two resources we care about currently.
    cpu: NotRequired[str]
    memory: NotRequired[str]


class JSONResourceRequirements(TypedDict):
    limits: NotRequired[JSONResourceRequirement]
    requests: NotRequired[JSONResourceRequirement]
