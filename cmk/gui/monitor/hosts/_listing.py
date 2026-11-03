#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from pydantic import TypeAdapter

from cmk.gui.monitor.shared import FILTER_NODE, FilterNode
from cmk.gui.monitor.table_widget import ListingParser

from ._api._list_hosts import HostsRequestBody

HOST_LISTING: Final = ListingParser[FilterNode](TypeAdapter(HostsRequestBody), FILTER_NODE)
