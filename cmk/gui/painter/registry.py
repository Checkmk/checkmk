#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Sequence
from typing import Any, overload, override

from cmk.ccc.plugin_registry import Registry
from cmk.ruleset_matcher.tags import TagGroup

from .base import InternalPainter
from .host_tag_painters import HashableTagGroups, host_tag_config_based_painters
from .legacy import LegacyPainterAdapter, Painter


class PainterRegistry(Registry[InternalPainter]):
    @override
    def plugin_name(self, instance: InternalPainter) -> str:
        return instance.ident

    @overload
    def register(self, instance: InternalPainter) -> InternalPainter: ...

    @overload
    def register(self, instance: type[Painter]) -> type[Painter]: ...

    @overload
    def register(self, instance: type[InternalPainter]) -> type[InternalPainter]: ...

    @override
    def register(
        self, instance: InternalPainter | type[Painter] | type[InternalPainter]
    ) -> InternalPainter | type[Painter] | type[InternalPainter]:
        if isinstance(instance, InternalPainter):
            return super().register(instance)
        if issubclass(instance, InternalPainter):
            super().register(instance())
            return instance
        super().register(LegacyPainterAdapter(instance))
        return instance


painter_registry = PainterRegistry()


def all_painters(tag_groups: Sequence[TagGroup]) -> dict[str, InternalPainter]:
    return dict(painter_registry.items()) | host_tag_config_based_painters(
        HashableTagGroups(tag_groups)
    )


# Kept for pre 1.6 compatibility.
def register_painter(ident: str, spec: dict[str, Any]) -> None:
    paint_function = spec["paint"]
    cls = type(
        "LegacyPainter%s" % ident.title(),
        (InternalPainter,),
        {
            "_ident": ident,
            "_spec": spec,
            "ident": property(lambda s: s._ident),  # noqa: SLF001
            "title": lambda s, cell, context: s._spec["title"],  # noqa: ARG005, SLF001
            "short_title": lambda s, cell, context: s._spec.get("short", s.title),  # noqa: ARG005, SLF001
            "tooltip_title": lambda s, cell, context: s._spec.get("tooltip_title", s.title),  # noqa: ARG005, SLF001
            "columns": property(lambda s: s._spec["columns"]),  # noqa: SLF001
            "render": lambda self, row, cell, user, context: paint_function(row),  # noqa: ARG005
            "export_for_python": (
                lambda self, row, cell, user, context: (  # noqa: ARG005
                    spec["export_for_python"](row, cell)
                    if "export_for_python" in spec
                    else paint_function(row)[1]
                )
            ),
            "export_for_csv": (
                lambda self, row, cell, user, context: (  # noqa: ARG005
                    spec["export_for_csv"](row, cell)
                    if "export_for_csv" in spec
                    else paint_function(row)[1]
                )
            ),
            "export_for_json": (
                lambda self, row, cell, user, context: (  # noqa: ARG005
                    spec["export_for_json"](row, cell)
                    if "export_for_json" in spec
                    else paint_function(row)[1]
                )
            ),
            "group_by": lambda self, row, cell, context: self._spec.get("groupby"),  # noqa: ARG005
            "parameters": lambda s, context: s._spec.get("params"),  # noqa: ARG005, SLF001
            "painter_options": property(lambda s: s._spec.get("options", [])),  # noqa: SLF001
            "printable": property(lambda s: s._spec.get("printable", True)),  # noqa: SLF001
            "sorter": property(lambda s: s._spec.get("sorter", None)),  # noqa: SLF001
            "load_inv": property(lambda s: s._spec.get("load_inv", False)),  # noqa: SLF001
        },
    )
    painter_registry.register(cls())
