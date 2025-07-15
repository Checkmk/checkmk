#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Callable, Sequence

from cmk.ccc.hostaddress import HostName

from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.logged_in import user
from cmk.gui.utils.selection_id import SelectionId
from cmk.gui.watolib.hosts_and_folders import Folder, Host, SearchFolder


def get_hostnames_from_checkboxes(
    folder: Folder | SearchFolder,
    filterfunc: Callable[[Host], bool] | None = None,
    deflt: bool = False,
) -> Sequence[HostName]:
    """Create list of all host names that are select with checkboxes in the current file.
    This is needed for bulk operations."""
    selected = user.get_rowselection(
        SelectionId.from_request(request), "wato-folder-/" + folder.path()
    )
    search_text = request.var("search")

    selected_host_names: list[HostName] = []
    for host_name, host in sorted(folder.hosts().items()):
        if (not search_text or _search_text_matches(host, search_text)) and (
            "_c_" + host_name
        ) in selected:
            if filterfunc is None or filterfunc(host):
                selected_host_names.append(host_name)
    return selected_host_names


def _search_text_matches(
    host: Host,
    search_text: str,
) -> bool:
    match_regex = re.compile(search_text, re.IGNORECASE)
    for pattern in [
        host.name(),
        str(host.effective_attributes()),
        str(active_config.sites[host.site_id()]["alias"]),
    ]:
        if match_regex.search(pattern):
            return True
    return False


def get_hosts_from_checkboxes(
    folder: Folder | SearchFolder, filterfunc: Callable[[Host], bool] | None = None
) -> list[Host]:
    """Create list of all host objects that are select with checkboxes in the current file.
    This is needed for bulk operations."""
    return [
        folder.load_host(host_name)
        for host_name in get_hostnames_from_checkboxes(folder, filterfunc)
    ]
