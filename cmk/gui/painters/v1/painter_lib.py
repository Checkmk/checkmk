#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass, field
from typing import Any, Callable, Generic, Optional, Sequence, TypeVar

import cmk.utils
from cmk.utils.type_defs import TimeRange

from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import ColumnName, PainterParameters, Rows
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.view_utils import CellSpec

T = TypeVar("T")


@dataclass(frozen=True)
class PainterConfiguration:
    columns: Sequence[ColumnName]
    parameters: Optional[PainterParameters]  # configured via valuespec
    painter_options: Optional[PainterOptions] = None
    time_range: Optional[TimeRange] = None  # provided from external view/dashlet
    dynamic_columns: Optional[Callable[["PainterConfiguration"], Sequence[ColumnName]]] = None


def strip_css_from_cell_spec(
    html_formatter: Callable[[T, PainterConfiguration], CellSpec]
) -> Callable[[T, PainterConfiguration], str]:
    def css_remover(painter_data: T, painter_configuration: PainterConfiguration) -> str:
        return str(html_formatter(painter_data, painter_configuration)[1])

    return css_remover


class Formatters(Generic[T]):
    def __init__(
        self,
        html: Callable[[T, PainterConfiguration], CellSpec],
        csv: Optional[Callable[[T, PainterConfiguration], str]] = None,
        json: Optional[Callable[[T, PainterConfiguration], object]] = None,
    ) -> None:
        self.html = html
        self.csv = csv or strip_css_from_cell_spec(html)
        self.json = json or strip_css_from_cell_spec(html)


@dataclass(frozen=True, kw_only=True)
class Painter(Generic[T]):
    ident: str
    computer: Callable[[Rows, PainterConfiguration], Sequence[T]]
    formatters: Formatters[T]
    title: str | LazyString
    short_title: str | LazyString
    columns: Sequence[ColumnName] = field(default_factory=list)
    list_title: Optional[str | LazyString] = None
    group_key: Callable[[T, PainterConfiguration], Any] = lambda x, y: None
    painter_options: Optional[list[str]] = None
    title_classes: Optional[list[str]] = None
    # dynamic_columns/derive will be reviewed later on
    dynamic_columns: Optional[Callable[[PainterParameters], Sequence[ColumnName]]] = None
    derive: Optional[Callable[[Rows, PainterParameters, list[ColumnName]], None]] = None
    postprocess_query: Optional[
        Callable[[Rows, PainterParameters, Sequence[ColumnName]], Rows]
    ] = None

    def export_title(self) -> str:
        return self.ident


class ExperimentalPainterRegistry(cmk.utils.plugin_registry.Registry[Painter]):
    def plugin_name(self, instance):
        return instance.ident


experimental_painter_registry = ExperimentalPainterRegistry()
