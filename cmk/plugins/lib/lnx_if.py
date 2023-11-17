#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from .interfaces import InterfaceWithCounters
from .interfaces import Section as InterfaceSection

SectionInventory = Mapping[str, Mapping[str, str | Sequence[str]]]
Section = tuple[InterfaceSection[InterfaceWithCounters], SectionInventory]
