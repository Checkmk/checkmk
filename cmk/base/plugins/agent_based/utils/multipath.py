#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import NamedTuple


class Group(NamedTuple):
    paths: list
    broken_paths: list
    luns: list
    uuid: str | None
    state: str | None
    numpaths: int
    device: str | None
    alias: str | None


Section = Mapping[str, Group]
