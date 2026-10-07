#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Dynamic host tag painters and sorters based on the site configuration"""

from collections.abc import Sequence
from functools import partial
from typing import override

from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.type_defs import Row
from cmk.gui.view_utils import CellSpec
from cmk.ruleset_matcher.tags import TagGroup
from cmk.web.utils.speaklater import LazyText

from .base import Cell, InternalPainter, PainterContext
from .helpers import get_tag_groups, tag_choices_for_group


class HashableTagGroups:
    def __init__(self, tag_groups: Sequence[TagGroup]) -> None:
        self.tag_groups = tag_groups

    @override
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HashableTagGroups):
            return False
        return hash(self) == hash(other)

    @override
    def __hash__(self) -> int:
        return hash(tuple(self.tag_groups))


@request_memoize()
def host_tag_config_based_painters(
    hashed_tag_groups: HashableTagGroups,
) -> dict[str, InternalPainter]:
    return {
        "host_tag_" + tag_group.id: make_host_tag_painter(tag_group)
        for tag_group in hashed_tag_groups.tag_groups
    }


def _paint_host_tag(row: Row, *, tag_group: TagGroup) -> CellSpec:
    tag_id = get_tag_groups(row, "host").get(tag_group.id)
    return "", tag_choices_for_group(tag_group).get(tag_id, _("N/A"))


def _render_host_tag(
    tag_group: TagGroup, row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _paint_host_tag(row, tag_group=tag_group)


def _group_by_host_tag(tag_group: TagGroup, row: Row, _cell: Cell, _context: PainterContext) -> str:
    return str(_paint_host_tag(row, tag_group=tag_group)[1])


def _host_tag_title(tag_group: TagGroup) -> str:
    return (
        _("Host tag:")
        + " "
        + (f"{tag_group.topic}  / {tag_group.title}" if tag_group.topic else tag_group.title)
    )


def make_host_tag_painter(tag_group: TagGroup) -> InternalPainter:
    return InternalPainter(
        ident="host_tag_" + tag_group.id,
        title=LazyText(partial(_host_tag_title, tag_group)),
        render=partial(_render_host_tag, tag_group),
        short_title=tag_group.title,
        columns=["host_tags"],
        group_by=partial(_group_by_host_tag, tag_group),
    )
