#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Dynamic host tag painters and sorters based on the site configuration"""

from collections.abc import Sequence

from cmk.utils.tags import TagGroup, TagGroupID

from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.painter.v0 import Painter
from cmk.gui.painter.v0.helpers import get_tag_groups
from cmk.gui.type_defs import Row
from cmk.gui.view_utils import CellSpec


class HashableTagGroups:
    def __init__(self, tag_groups: Sequence[TagGroup]) -> None:
        self.tag_groups = tag_groups

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, HashableTagGroups):
            return False
        return hash(self) == hash(other)

    def __hash__(self) -> int:
        return hash(tuple(self.tag_groups))


@request_memoize()
def host_tag_config_based_painters(
    hashed_tag_groups: HashableTagGroups,
) -> dict[str, type[Painter]]:
    return {
        (ident := "host_tag_" + tag_group.id): type(
            "HostTagPainter%s" % str(tag_group.id).title(),
            (Painter,),
            {
                "_ident": ident,
                "_spec": {
                    "title": _("Host tag:")
                    + " "
                    + (
                        f"{tag_group.topic}  / {tag_group.title}"
                        if tag_group.topic
                        else tag_group.title
                    ),
                    "short": tag_group.title,
                    "columns": ["host_tags"],
                },
                "_tag_group_id": tag_group.id,
                "ident": property(lambda self: self._ident),
                "title": lambda self, cell: self._spec["title"],
                "short_title": lambda self, cell: self._spec["short"],
                "columns": property(lambda self: self._spec["columns"]),
                "render": lambda self, row, cell, user, tag_group=tag_group: _paint_host_tag(
                    row, self._tag_group_id, tag_group=tag_group
                ),
                # Use title of the tag value for grouping, not the complete
                # dictionary of custom variables!
                "group_by": lambda self, row, _cell, tag_group=tag_group: _paint_host_tag(
                    row, self._tag_group_id, tag_group=tag_group
                )[1],
            },
        )
        for tag_group in hashed_tag_groups.tag_groups
    }


def _paint_host_tag(row: Row, tgid: TagGroupID, *, tag_group: TagGroup) -> CellSpec:
    return "", _get_tag_group_value(row, "host", tgid, tag_group=tag_group)


def _get_tag_group_value(
    row: Row, what: str, tag_group_id: TagGroupID, *, tag_group: TagGroup
) -> str:
    tag_id = get_tag_groups(row, what).get(tag_group_id)
    return dict(tag_group.get_tag_choices()).get(tag_id, _("N/A"))
