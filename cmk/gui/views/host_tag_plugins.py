#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Dynamic registration of host tag painters and sorters based on the site configuration"""

from cmk.gui.config import active_config
from cmk.gui.i18n import _

from .painter.v0.base import Painter, painter_registry
from .painter.v0.helpers import get_tag_groups
from .sorter import Sorter, sorter_registry


def register_tag_plugins() -> None:
    if getattr(register_tag_plugins, "_config_hash", None) == _calc_config_hash():
        return  # No re-register needed :-)
    _register_host_tag_painters()
    _register_host_tag_sorters()
    setattr(register_tag_plugins, "_config_hash", _calc_config_hash())


def _calc_config_hash() -> int:
    return hash(repr(active_config.tags.get_dict_format()))


def _register_host_tag_painters() -> None:
    # first remove all old painters to reflect delted painters during runtime
    for key in list(painter_registry.keys()):
        if key.startswith("host_tag_"):
            painter_registry.unregister(key)

    for tag_group in active_config.tags.tag_groups:
        if tag_group.topic:
            long_title = tag_group.topic + " / " + tag_group.title
        else:
            long_title = tag_group.title

        ident = "host_tag_" + tag_group.id
        spec = {
            "title": _("Host tag:") + " " + long_title,
            "short": tag_group.title,
            "columns": ["host_tags"],
        }
        cls = type(
            "HostTagPainter%s" % str(tag_group.id).title(),
            (Painter,),
            {
                "_ident": ident,
                "_spec": spec,
                "_tag_group_id": tag_group.id,
                "ident": property(lambda self: self._ident),
                "title": lambda self, cell: self._spec["title"],
                "short_title": lambda self, cell: self._spec["short"],
                "columns": property(lambda self: self._spec["columns"]),
                "render": lambda self, row, cell: _paint_host_tag(row, self._tag_group_id),
                # Use title of the tag value for grouping, not the complete
                # dictionary of custom variables!
                "group_by": lambda self, row, _cell: _paint_host_tag(row, self._tag_group_id)[1],
            },
        )
        painter_registry.register(cls)


def _paint_host_tag(row, tgid):
    return "", _get_tag_group_value(row, "host", tgid)


def _register_host_tag_sorters() -> None:
    for tag_group in active_config.tags.tag_groups:
        ident = "host_tag_" + str(tag_group.id)
        cls = type(
            "LegacySorter%s" % str(ident).title(),
            (Sorter,),
            {
                "_ident": ident,
                "_spec": {"_tag_group_id": tag_group.id},
                "ident": property(lambda s: s._ident),
                "title": _("Host tag:") + " " + tag_group.title,
                "columns": ["host_tags"],
                "load_inv": False,
                "cmp": lambda self, r1, r2, p: _cmp_host_tag(r1, r2, self._spec["_tag_group_id"]),
            },
        )
        sorter_registry.register(cls)


def _cmp_host_tag(r1, r2, tgid):
    host_tag_1 = _get_tag_group_value(r1, "host", tgid)
    host_tag_2 = _get_tag_group_value(r2, "host", tgid)
    return (host_tag_1 > host_tag_2) - (host_tag_1 < host_tag_2)


def _get_tag_group_value(row, what, tag_group_id) -> str:  # type:ignore[no-untyped-def]
    tag_id = get_tag_groups(row, "host").get(tag_group_id)

    tag_group = active_config.tags.get_tag_group(tag_group_id)
    if tag_group:
        label = dict(tag_group.get_tag_choices()).get(tag_id, _("N/A"))
    else:
        label = tag_id or _("N/A")

    return label or _("N/A")
