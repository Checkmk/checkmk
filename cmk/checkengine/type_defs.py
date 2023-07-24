#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Package containing the fetchers to the data sources."""

from collections.abc import Sequence

from cmk.utils.sectionname import SectionMap

# Note that the inner Sequence[str] to AgentRawDataSectionElem
# is only **artificially** different from AgentRawData and
# obtained approximatively with `raw_data.decode("utf-8").split()`!
AgentRawDataSectionElem = Sequence[str]
AgentRawDataSection = SectionMap[Sequence[AgentRawDataSectionElem]]
