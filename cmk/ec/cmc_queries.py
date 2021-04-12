#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List

from cmk.utils.type_defs import Timestamp
from livestatus import LocalConnection, MKLivestatusNotFoundError  # noqa: F401 # pylint: disable=unused-import

################################################################################

# TODO: Improve this vague type, using e.g. a NamedTuple.
HostInfo = Dict[str, Any]


def query_host_configs() -> List[HostInfo]:
    return LocalConnection().query_table_assoc(
        "GET hosts\n"
        "Columns: name alias address custom_variables contacts contact_groups")


################################################################################


def query_config_timestamp() -> Timestamp:
    return LocalConnection().query_value("GET status\n"  #
                                         "Columns: program_start")
