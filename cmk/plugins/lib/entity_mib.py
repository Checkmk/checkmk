#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from enum import Enum


# Source: https://www.circitor.fr/Mibs/Html/E/ENTITY-MIB.php#PhysicalClass
class PhysicalClasses(Enum):
    other = "1"
    unknown = "2"
    chassis = "3"
    backplane = "4"
    container = "5"
    powerSupply = "6"
    fan = "7"
    sensor = "8"
    module = "9"
    port = "10"
    stack = "11"
    cpu = "12"

    # SUP-10602: Cisco decided to not stick to the official MiB ...
    @classmethod
    def parse_cisco(cls, raw_phys_class: str) -> "PhysicalClasses":
        try:
            return cls(raw_phys_class)
        except ValueError:
            return cls.unknown
