#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import Row
from cmk.gui.utils.urls import makeuri_contextless
from cmk.utils.tags import TagID

from .base import Icon


def _render_parent_child_topology_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
) -> tuple[str, str, str]:
    url = makeuri_contextless(
        request,
        [("host_regex", f"{row['host_name']}$"), ("topology_mesh_depth", 0)],
        filename="parent_child_topology.py",
    )
    return "aggr", _("Host parent/child topology"), url


ShowParentChildTopology = Icon(
    ident="parent_child_topology",
    title=_l("Host parent/child topology"),
    host_columns=["name"],
    sort_index=51,
    render=_render_parent_child_topology_icon,
)
