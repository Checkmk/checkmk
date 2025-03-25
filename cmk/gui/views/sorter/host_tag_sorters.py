#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Dynamic sorters based on the site configuration"""

from collections.abc import Mapping
from functools import partial

from cmk.utils.tags import TagGroupID

from cmk.gui.config import Config
from cmk.gui.hooks import request_memoize
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.painter.v0.helpers import get_tag_groups
from cmk.gui.painter.v0.host_tag_painters import HashableTagGroups
from cmk.gui.type_defs import Row

from .base import Sorter


@request_memoize()
def host_tag_config_based_sorters(hashable_tag_groups: HashableTagGroups) -> dict[str, Sorter]:
    return {
        (ident := f"host_tag_{tag_group.id}"): Sorter(
            ident=ident,
            title=_("Host tag:") + " " + tag_group.title,
            columns=["host_tags"],
            load_inv=False,
            sort_function=partial(_cmp_host_tag, tag_group_id=tag_group.id),
        )
        for tag_group in hashable_tag_groups.tag_groups
    }


def _cmp_host_tag(
    r1: Row,
    r2: Row,
    *,
    parameters: Mapping[str, object] | None,
    config: Config,
    request: Request,
    tag_group_id: TagGroupID,
) -> int:
    host_tag_1 = _get_tag_group_value(r1, "host", tag_group_id, config=config)
    host_tag_2 = _get_tag_group_value(r2, "host", tag_group_id, config=config)
    return (host_tag_1 > host_tag_2) - (host_tag_1 < host_tag_2)


def _get_tag_group_value(row: Row, what: str, tag_group_id: TagGroupID, *, config: Config) -> str:
    tag_id = get_tag_groups(row, what).get(tag_group_id)

    tag_group = config.tags.get_tag_group(tag_group_id)
    if tag_group:
        label = dict(tag_group.get_tag_choices()).get(tag_id, _("N/A"))
    else:
        label = tag_id or _("N/A")

    return label or _("N/A")
