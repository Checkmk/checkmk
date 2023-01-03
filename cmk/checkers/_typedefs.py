#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import NamedTuple

from cmk.utils.type_defs import HostName

from cmk.fetchers import SourceType


class HostKey(NamedTuple):
    hostname: HostName
    source_type: SourceType
