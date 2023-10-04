#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NewType

# TODO(ml): We may try to move the `Agent*` type to the fetchers or the
#           checkengine once the layering between these two packages has
#           been clarified.
AgentRawData = NewType("AgentRawData", bytes)
