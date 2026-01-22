#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

import cmk.ccc.plugin_registry
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import ColumnName, PainterParameters, Rows
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.view_utils import CellSpec

T = TypeVar("T")


@dataclass(frozen=True)
class PainterConfiguration:
    columns: Sequence[ColumnName]
    parameters: PainterParameters | None  # configured via valuespec
    painter_options: PainterOptions | None = None
    time_range: tuple[int, int] | None = None  # provided from external view/dashlet
    dynamic_columns: Callable[["PainterConfiguration"], Sequence[ColumnName]] | None = None


def strip_css_from_cell_spec(
    html_formatter: Callable[[T, PainterConfiguration, LoggedInUser], CellSpec], user: LoggedInUser
) -> Callable[[T, PainterConfiguration], str]:
    def css_remover(painter_data: T, painter_configuration: PainterConfiguration) -> str:
        return str(html_formatter(painter_data, painter_configuration, user)[1])

    return css_remover


class Formatters(Generic[T]):
    def __init__(
        self,
        html: Callable[[T, PainterConfiguration, LoggedInUser], CellSpec],
        csv: Callable[[T, PainterConfiguration, LoggedInUser], str] | None = None,
        json: Callable[[T, PainterConfiguration, LoggedInUser], object] | None = None,
        user: LoggedInUser = user,
    ) -> None:
        self.html = html
        self.csv = csv or strip_css_from_cell_spec(html, user)
        self.json = json or strip_css_from_cell_spec(html, user)


@dataclass(frozen=True, kw_only=True)
class Painter(Generic[T]):
    """Base class for "new" Painters.

    This hierarchy is incompatible with old Painters, so it is necessary to wrap these classes with

        cmk.gui.painters.v0.base.PainterAdapter

    in order to make it work in existing code.

    """

    ident: str
    computer: Callable[[Rows, PainterConfiguration], Sequence[T]]
    """Function which generates the data from one or more rows into a sequence of entries.

    These may be `int` or `str`, but more complex aggregate types like NamedTuple, etc are also
    possible."""

    formatters: Formatters[T]
    """Class which collects functions (html, css, json) which represent the output content-type
    and will take the result of the compute method above and generates output from that."""

    title: str | LazyString
    short_title: str | LazyString
    columns: Sequence[ColumnName] = field(default_factory=list)
    list_title: str | LazyString | None = None
    group_key: Callable[[T, PainterConfiguration], Any] = lambda x, y: None
    painter_options: list[str] | None = None
    title_classes: list[str] | None = None
    # dynamic_columns/derive will be reviewed later on
    dynamic_columns: Callable[[PainterParameters], Sequence[ColumnName]] | None = None
    derive: Callable[[Rows, PainterParameters, list[ColumnName]], None] | None = None
    postprocess_query: None | (Callable[[Rows, PainterParameters, Sequence[ColumnName]], Rows]) = (
        None
    )

    def export_title(self) -> str:
        return self.ident


class ExperimentalPainterRegistry(cmk.ccc.plugin_registry.Registry[Painter]):
    def plugin_name(self, instance: Painter[object]) -> str:
        return instance.ident


experimental_painter_registry = ExperimentalPainterRegistry()
