#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Sequence, Tuple, Union

from cmk.base.plugins.agent_based.utils.interfaces import Section as InterfaceSection

SectionInventory = Dict[str, Dict[str, Union[str, Sequence[str]]]]
Section = Tuple[InterfaceSection, SectionInventory]
