#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.ccc.hostaddress import HostName

from cmk.gui.bi import get_cached_bi_packs

from cmk.bi.packs import BIHostRenamer


def rename_host_in_bi(oldname: HostName, newname: HostName) -> list[str]:
    return BIHostRenamer().rename_host(oldname, newname, get_cached_bi_packs())
