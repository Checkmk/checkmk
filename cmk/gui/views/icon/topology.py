#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.utils.tags import TagID

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.type_defs import Row
from cmk.gui.utils.urls import makeuri_contextless

from .base import Icon


class ShowParentChildTopology(Icon):
    @classmethod
    def ident(cls) -> str:
        return "parent_child_topology"

    @classmethod
    def title(cls) -> str:
        return _("Host parent/child topology")

    def host_columns(self) -> list[str]:
        return ["name"]

    def default_sort_index(self) -> int:
        return 51

    def render(
        self,
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
