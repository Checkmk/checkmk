#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="type-arg"


import os
import re
import traceback
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from html import unescape
from typing import Any, Literal, override

import cmk.utils.paths
from cmk.ccc.exceptions import MKGeneralException
from cmk.gui import visuals
from cmk.gui.config import Config, RequestCacheConfig
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter_options import PainterOptions
from cmk.gui.theme import Theme
from cmk.gui.type_defs import (
    ColumnName,
    ColumnSpec,
    GraphTimerange,
    PainterName,
    PainterParameters,
    PermittedViewSpecs,
    Row,
    Rows,
    SorterName,
    ViewName,
    ViewSpec,
    VisualLinkSpec,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import ValueSpec
from cmk.gui.view_utils import (
    CellSpec,
    CSVExportError,
    JSONExportError,
    PythonExportError,
)
from cmk.livestatus_client import SiteConfigurations
from cmk.ruleset_matcher.tags import TagConfig
from cmk.web.utils import escaping
from cmk.web.utils.escaping import replace_anchor_tags_with_urls, replace_br_with_newlines
from cmk.web.utils.html import HTML
from cmk.web.utils.request_cache import RequestCache
from cmk.web.utils.speaklater import LazyString, LazyText

from .helpers import RenderLink

ExportCellContent = str | dict[str, Any]
PDFCellContent = str | tuple[Literal["icon"], str]
PDFCellSpec = tuple[Sequence[str], PDFCellContent]


@dataclass(frozen=True, kw_only=True)
class PainterConfig:
    staleness_threshold: float
    debug: bool
    sites: SiteConfigurations
    use_siteicons: bool
    default_temperature_unit: str
    graph_timeranges: Sequence[GraphTimerange]
    tags: TagConfig
    service_custom_attribute_titles: Mapping[str, str]
    host_custom_attribute_titles: Mapping[str, str]
    escape_plugin_output: bool
    mkeventd_service_levels: Sequence[tuple[int, str]]
    wato_enabled: bool
    mkeventd_enabled: bool
    multisite_draw_ruleicon: bool

    @classmethod
    def from_config(cls, config: Config) -> PainterConfig:
        return cls(
            staleness_threshold=config.staleness_threshold,
            debug=config.debug,
            sites=config.sites,
            use_siteicons=config.use_siteicons,
            default_temperature_unit=config.default_temperature_unit,
            graph_timeranges=config.graph_timeranges,
            tags=config.tags,
            service_custom_attribute_titles={
                ident: spec["title"] for ident, spec in config.custom_service_attributes.items()
            },
            host_custom_attribute_titles={
                spec["name"]: spec["title"] for spec in config.wato_host_attrs
            },
            escape_plugin_output=config.escape_plugin_output,
            mkeventd_service_levels=config.mkeventd_service_levels,
            wato_enabled=config.wato_enabled,
            mkeventd_enabled=config.mkeventd_enabled,
            multisite_draw_ruleicon=config.multisite_draw_ruleicon,
        )


@dataclass(frozen=True, kw_only=True)
class PainterContext:
    config: PainterConfig
    request: Request
    painter_options: PainterOptions
    theme: Theme
    url_renderer: RenderLink
    user_permissions: UserPermissions


type RowFunction[T] = Callable[[Row, Cell, LoggedInUser, PainterContext], T]
type CellTitle = Callable[[Cell, PainterContext], str]
type GroupValue = None | str | tuple[str, ...] | tuple[tuple[str, str], ...]


type StaticText = str | LazyString | LazyText


class InternalPainter:
    def __init__(
        self,
        *,
        ident: str | LazyText,
        title: StaticText,
        short_title: StaticText | None = None,
        list_title: StaticText | None = None,
        tooltip_title: StaticText | None = None,
        columns: Sequence[ColumnName] | Callable[[], Sequence[ColumnName]] = (),
        groupable: bool = True,
        sorter: SorterName | None = None,
        printable: bool | str = True,
        painter_options: Sequence[str] = (),
        load_inv: bool = False,
        use_painter_link: bool = True,
        title_classes: Sequence[str] = (),
        cell_title: CellTitle | None = None,
        cell_short_title: CellTitle | None = None,
        cell_list_title: CellTitle | None = None,
        cell_tooltip_title: CellTitle | None = None,
        export_title: Callable[[Cell], str] | None = None,
        dynamic_columns: Callable[[Cell], list[ColumnName]] | None = None,
        uuid_col: Callable[[Cell], str] | None = None,
        parameters: ValueSpec | Callable[[PainterContext], ValueSpec | None] | None = None,
        group_by: Callable[[Row, Cell, PainterContext], GroupValue] | None = None,
        derive: Callable[[Rows, Cell, Sequence[ColumnName], LoggedInUser, PainterContext], None]
        | None = None,
        render: RowFunction[CellSpec],
        compute_data: Callable[[Row, PainterContext], object] | None = None,
        export_for_python: RowFunction[object] | None = None,
        export_for_csv: RowFunction[str | HTML] | None = None,
        export_for_json: RowFunction[object] | None = None,
    ) -> None:
        self._ident = ident
        self._title = title
        self._short_title = short_title
        self._list_title = list_title
        self._tooltip_title = tooltip_title
        self._columns = columns
        self._groupable = groupable
        self._sorter = sorter
        self._printable = printable
        self._painter_options = painter_options
        self._load_inv = load_inv
        self._use_painter_link = use_painter_link
        self._title_classes = title_classes
        self._cell_title = cell_title
        self._cell_short_title = cell_short_title
        self._cell_list_title = cell_list_title
        self._cell_tooltip_title = cell_tooltip_title
        self._export_title = export_title
        self._dynamic_columns = dynamic_columns
        self._uuid_col = uuid_col
        self._parameters = parameters
        self._group_by = group_by
        self._derive = derive
        self._render = render
        self._compute_data_function = compute_data
        self._export_for_python = export_for_python
        self._export_for_csv = export_for_csv
        self._export_for_json = export_for_json

    @property
    def ident(self) -> str:
        return str(self._ident)

    @property
    def static_title(self) -> str | LazyString | LazyText:
        return self._title

    def title(self, cell: Cell, context: PainterContext) -> str:
        if self._cell_title is None:
            return str(self._title)
        return self._cell_title(cell, context)

    def short_title(self, cell: Cell, context: PainterContext) -> str:
        if self._cell_short_title is not None:
            return self._cell_short_title(cell, context)
        if self._short_title is None:
            return self.title(cell, context)
        return str(self._short_title)

    def list_title(self, cell: Cell, context: PainterContext) -> str:
        if self._cell_list_title is not None:
            return self._cell_list_title(cell, context)
        if self._list_title is None:
            return self.title(cell, context)
        return str(self._list_title)

    def tooltip_title(self, cell: Cell, context: PainterContext) -> str:
        if self._cell_tooltip_title is not None:
            return self._cell_tooltip_title(cell, context)
        if self._tooltip_title is None:
            return self.title(cell, context)
        return str(self._tooltip_title)

    def export_title(self, cell: Cell) -> str:
        if self._export_title is None:
            return self.ident
        return self._export_title(cell)

    def title_classes(self) -> Sequence[str]:
        return self._title_classes

    @property
    def columns(self) -> Sequence[ColumnName]:
        if isinstance(self._columns, Sequence):
            return self._columns
        return self._columns()

    def dynamic_columns(self, cell: Cell) -> list[ColumnName]:
        if self._dynamic_columns is None:
            return []
        return self._dynamic_columns(cell)

    def derive(
        self,
        rows: Rows,
        cell: Cell,
        dynamic_columns: Sequence[ColumnName],
        acting_user: LoggedInUser,
        context: PainterContext,
    ) -> None:
        if self._derive is not None:
            self._derive(rows, cell, dynamic_columns, acting_user, context)

    def group_by(self, row: Row, cell: Cell, context: PainterContext) -> GroupValue:
        if not self._groupable:
            return ("",)
        if self._group_by is None:
            return None
        return self._group_by(row, cell, context)

    def parameters(self, context: PainterContext) -> ValueSpec | None:
        if self._parameters is None or isinstance(self._parameters, ValueSpec):
            return self._parameters
        return self._parameters(context)

    def uuid_col(self, cell: Cell) -> str:
        if self._uuid_col is None:
            return ""
        return self._uuid_col(cell)

    @property
    def painter_options(self) -> Sequence[str]:
        return self._painter_options

    @property
    def printable(self) -> bool | str:
        return self._printable

    @property
    def use_painter_link(self) -> bool:
        return self._use_painter_link

    @property
    def sorter(self) -> SorterName | None:
        return self._sorter

    @property
    def load_inv(self) -> bool:
        return self._load_inv

    def render(
        self, row: Row, cell: Cell, acting_user: LoggedInUser, context: PainterContext
    ) -> CellSpec:
        return self._render(row, cell, acting_user, context)

    def _compute_data(
        self, row: Row, cell: Cell, acting_user: LoggedInUser, context: PainterContext
    ) -> object:
        if self._compute_data_function is None:
            return self.render(row, cell, acting_user, context)[1]
        return self._compute_data_function(row, context)

    def export_for_python(
        self, row: Row, cell: Cell, acting_user: LoggedInUser, context: PainterContext
    ) -> object:
        if self._export_for_python is None:
            return self._compute_data(row, cell, acting_user, context)
        return self._export_for_python(row, cell, acting_user, context)

    def export_for_csv(
        self, row: Row, cell: Cell, acting_user: LoggedInUser, context: PainterContext
    ) -> str | HTML:
        if self._export_for_csv is not None:
            return self._export_for_csv(row, cell, acting_user, context)
        if isinstance(data := self._compute_data(row, cell, acting_user, context), str | HTML):
            return data
        raise ValueError("Data must be of type 'str' or 'HTML' but is %r" % type(data))

    def export_for_json(
        self, row: Row, cell: Cell, acting_user: LoggedInUser, context: PainterContext
    ) -> object:
        if self._export_for_json is None:
            return self._compute_data(row, cell, acting_user, context)
        return self._export_for_json(row, cell, acting_user, context)


# .
#   .--Cells---------------------------------------------------------------.
#   |                           ____     _ _                               |
#   |                          / ___|___| | |___                           |
#   |                         | |   / _ \ | / __|                          |
#   |                         | |__|  __/ | \__ \                          |
#   |                          \____\___|_|_|___/                          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | View cell handling classes. Each cell instanciates a multisite       |
#   | painter to render a table cell.                                      |
#   '----------------------------------------------------------------------'


def columns_of_cells(cells: Sequence[Cell], permitted_views: PermittedViewSpecs) -> set[ColumnName]:
    columns: set[ColumnName] = set()
    for cell in cells:
        columns.update(cell.needed_columns(permitted_views))
    return columns


class Cell:
    """A cell is an instance of a painter in a view (-> a cell or a grouping cell)"""

    def __init__(
        self,
        column_spec: ColumnSpec | None,
        sort_url_parameter: str | None,
        registered_painters: Mapping[str, InternalPainter] | None,
        painter_context: PainterContext | None,
        request_cache: RequestCache[RequestCacheConfig] | None,
    ) -> None:
        self._painter_name: PainterName | None
        self._painter_params: PainterParameters | None
        self._registered_painters = registered_painters

        if column_spec:
            self._painter_name = column_spec.name
            self._painter_params = column_spec.parameters
            self._custom_title = (
                column_spec.parameters.get("column_title") or column_spec.column_title
            )
            self._link_spec = column_spec.link_spec
            assert registered_painters is not None
            self._tooltip_painter_name = (
                column_spec.tooltip if column_spec.tooltip in registered_painters else None
            )
        else:
            self._painter_name = None
            self._painter_params = None
            self._custom_title = None
            self._link_spec = None
            self._tooltip_painter_name = None

        self._sort_url_parameter = sort_url_parameter
        self._painter_context = painter_context
        self._request_cache = request_cache

    @property
    def request_cache(self) -> RequestCache[RequestCacheConfig]:
        """The cache of the request rendering the cell

        Cells only asked for painter titles, like the EmptyCell and those of the view editor, have
        none, so a painter reads it only when rendering or exporting a row.
        """
        if self._request_cache is None:
            raise TypeError("Cell has no request cache: it is only meant for painter titles")
        return self._request_cache

    def needed_columns(self, permitted_views: Mapping[ViewName, ViewSpec]) -> set[ColumnName]:
        """Get a list of columns we need to fetch in order to render this cell"""

        columns = set(self.painter().columns)

        link_view = self._link_view(permitted_views)
        if link_view:
            # TODO: Clean this up here
            for filt in [
                visuals.get_filter(fn)
                for fn in visuals.get_single_info_keys(link_view["single_infos"])
            ]:
                columns.update(filt.link_columns)

        if self.has_tooltip():
            columns.update(self.tooltip_painter().columns)

        return columns

    def has_link_spec(self) -> bool:
        """Whether the column has a user-configured "Link to view / dashboard"."""
        return self._link_spec is not None

    def _link_view(self, permitted_views: Mapping[ViewName, ViewSpec]) -> ViewSpec | None:
        if self._link_spec is None:
            return None

        try:
            return permitted_views[self._link_spec.name]
        except KeyError:
            return None

    def painter(self) -> InternalPainter:
        assert self._registered_painters is not None
        return self._registered_painters[self.painter_name()]

    def painter_context(self) -> PainterContext:
        if self._painter_context is None:
            raise TypeError("Cell has no painter context: it is only a placeholder")
        return self._painter_context

    def painter_name(self) -> PainterName:
        assert self._painter_name is not None
        return self._painter_name

    def export_title(self) -> str:
        if self._custom_title:
            return re.sub(r"[^\w]", "_", self._custom_title.lower())
        return self.painter().export_title(self)

    def painter_options(self) -> Sequence[str]:
        return self.painter().painter_options

    def painter_parameters(self) -> PainterParameters | None:
        """The parameters configured in the view for this painter. In case the
        painter has params, it defaults to the valuespec default value and
        in case the painter has no params, it returns None."""
        if not (vs_painter_params := self.painter().parameters(self.painter_context())):
            return None
        return self._painter_params if self._painter_params else vs_painter_params.default_value()

    def has_painter_params(self) -> bool:
        return self._painter_params not in (None, {})

    def title(self, use_short: bool = True) -> str:
        if self._custom_title:
            return self._custom_title

        painter = self.painter()
        if use_short:
            return self._get_short_title(painter)
        return self._get_long_title(painter)

    def tooltip_title(self) -> str:
        if self._custom_title:
            return self._custom_title

        painter = self.painter()
        return painter.tooltip_title(self, self.painter_context())

    def _get_short_title(self, painter: InternalPainter) -> str:
        return painter.short_title(self, self.painter_context())

    def _get_long_title(self, painter: InternalPainter) -> str:
        return painter.title(self, self.painter_context())

    # Can either be:
    # True       : Is printable in PDF
    # False      : Is not printable at all
    # "<string>" : ID of a painter_printer (Reporting module)
    def printable(self) -> bool | str:
        return self.painter().printable

    def has_tooltip(self) -> bool:
        return self._tooltip_painter_name is not None

    def tooltip_painter_name(self) -> str:
        assert self._tooltip_painter_name is not None
        return self._tooltip_painter_name

    def tooltip_painter(self) -> InternalPainter:
        assert self._tooltip_painter_name is not None
        assert self._registered_painters is not None
        return self._registered_painters[self._tooltip_painter_name]

    def paint_as_header(self, writer: HTMLWriter) -> None:
        classes: list[str] = []
        onclick = ""
        title = ""
        if self._sort_url_parameter and (
            sort_url := self.painter_context().url_renderer.sort_url(self._sort_url_parameter)
        ):
            classes += ["sort"]
            onclick = "location.href='%s'" % sort_url
            title = _("Sort by %(title)s") % {"title": self.tooltip_title()}
        classes += self.painter().title_classes()

        writer.open_th(class_=classes, onclick=onclick, title=title)
        writer.write_text_permissive(self.title())
        writer.close_th()

    def render(
        self,
        row: Row,
        link_renderer: Callable[[str | HTML, Row, VisualLinkSpec], str | HTML] | None,
        user: LoggedInUser,
    ) -> tuple[str, str | HTML]:
        row = join_row(row, self)

        try:
            tdclass, content = self.render_content(row, user=user)
            assert isinstance(content, str | HTML)
        except Exception:
            logger.exception(
                "Failed to render painter '%(painter_name)s' (Row: %(row)r)",
                {"painter_name": self._painter_name, "row": row},
            )
            raise

        if tdclass is None:
            tdclass = ""

        if tdclass == "" and content == "":
            return "", ""

        # Add the optional link to another view
        if content and self._link_spec is not None and self._use_painter_link() and link_renderer:
            content = link_renderer(content, row, self._link_spec)

        # Add the optional mouseover tooltip
        if content and self.has_tooltip():
            assert isinstance(content, str | HTML)
            tooltip_cell = Cell(
                ColumnSpec(self.tooltip_painter_name()),
                None,
                self._registered_painters,
                self._painter_context,
                self._request_cache,
            )
            _tooltip_tdclass, tooltip_content = tooltip_cell.render_content(row, user=user)
            assert not isinstance(tooltip_content, Mapping)
            tooltip_text = escaping.strip_tags_for_tooltip(tooltip_content)
            if tooltip_text:
                content = HTMLWriter.render_span(content, title=tooltip_text, class_="tooltip")

        return tdclass, content

    def _use_painter_link(self) -> bool:
        return self.painter().use_painter_link

    # Same as self.render() for HTML output: Gets a painter and a data
    # row and creates the text for being painted.
    def render_for_pdf(
        self,
        row: Row,
        time_range: tuple[int, int],  # noqa: ARG002
        user: LoggedInUser,
    ) -> PDFCellSpec:
        # TODO: Move this somewhere else!
        def find_htdocs_image_path(filename: str) -> str | None:
            themes = self.painter_context().theme.icon_themes()
            for file_path in [
                cmk.utils.paths.local_web_dir / "htdocs" / filename,
                cmk.utils.paths.web_dir / "htdocs" / filename,
            ]:
                for path_in_theme in (str(file_path).replace(t, "facelift") for t in themes):
                    if os.path.exists(path_in_theme):
                        return path_in_theme
            return None

        try:
            row = join_row(row, self)
            css_classes, rendered_txt = self.render_content(row, user=user)
            if css_classes is None:
                css_classes = ""
            if rendered_txt is None:
                return css_classes.split(), ""  # type: ignore[unreachable]
            assert isinstance(rendered_txt, str | HTML)

            txt = rendered_txt.strip()
            content: PDFCellContent = ""

            # Handle <img...>. Our PDF writer cannot draw arbitrary
            # images, but all that we need for showing simple icons.
            # Current limitation: *one* image
            if (isinstance(txt, str) and txt.lower().startswith("<img")) or (
                isinstance(txt, HTML) and txt.lower().startswith(HTML.without_escaping("<img"))
            ):
                img_filename = re.sub(".*src=[\"']([^'\"]*)[\"'].*", "\\1", str(txt))
                img_path = find_htdocs_image_path(img_filename)
                content = ("icon", img_path) if img_path else img_filename

            if not content:
                if isinstance(txt, HTML):
                    html_str = unescape(str(txt))
                    html_str = replace_anchor_tags_with_urls(html_str)
                    html_str = replace_br_with_newlines(html_str)
                    content = escaping.strip_tags(html_str)
                else:
                    content = escaping.strip_tags(unescape(txt))

            return css_classes.split(), content
        except Exception:
            raise MKGeneralException(
                f'Failed to paint "{self.painter_name()}": {traceback.format_exc()}'
            )

    def render_for_python_export(self, row: Row, user: LoggedInUser) -> object:
        if self.painter_context().request.var("output_format") not in ["python", "python_export"]:
            return "NOT_PYTHON_EXPORTABLE"

        if not row:
            return ""

        try:
            content = self.painter().export_for_python(row, self, user, self.painter_context())
        except PythonExportError:
            return "NOT_PYTHON_EXPORTABLE"

        if isinstance(content, str | HTML):
            # TODO At the moment we have to keep this str/HTML handling because export_for_python
            # falls back to render. As soon as all painters have explicit export_for_* methods,
            # we can remove this...
            return self._render_html_content(content)

        return content

    def render_for_csv_export(self, row: Row, user: LoggedInUser) -> str | HTML:
        if self.painter_context().request.var("output_format") not in ["csv", "csv_export"]:
            return "NOT_CSV_EXPORTABLE"

        if not row:
            return ""

        try:
            content = self.painter().export_for_csv(row, self, user, self.painter_context())
        except CSVExportError:
            return "NOT_CSV_EXPORTABLE"

        return self._render_html_content(content)

    def render_for_json_export(self, row: Row, user: LoggedInUser) -> object:
        if self.painter_context().request.var("output_format") not in ["json", "json_export"]:
            return "NOT_JSON_EXPORTABLE"

        if not row:
            return ""

        try:
            content = self.painter().export_for_json(row, self, user, self.painter_context())
        except JSONExportError:
            return "NOT_JSON_EXPORTABLE"

        if isinstance(content, str | HTML):
            # TODO At the moment we have to keep this str/HTML handling because export_for_json
            # falls back to render. As soon as all painters have explicit export_for_* methods,
            # we can remove this...
            return self._render_html_content(content)

        return content

    def _render_html_content(self, content: str | HTML) -> str:
        txt: str = str(content).strip()

        # Similar to the PDF rendering hack above, but this time we extract the title from our icons
        # and add them to the CSV export instead of stripping the whole HTML tag.
        # Current limitation: *one* image
        if txt.lower().startswith("<img"):
            txt = re.sub(".*title=[\"']([^'\"]*)[\"'].*", "\\1", str(txt))

        txt = replace_anchor_tags_with_urls(txt)
        txt = replace_br_with_newlines(txt)
        return escaping.strip_tags(txt)

    def render_content(self, row: Row, user: LoggedInUser) -> CellSpec:
        if not row:
            return "", ""  # nothing to paint

        painter = self.painter()
        return painter.render(row, self, user, self.painter_context())

    def paint(
        self,
        row: Row,
        link_renderer: Callable[[str | HTML, Row, VisualLinkSpec], str | HTML] | None,
        user: LoggedInUser,
        writer: HTMLWriter,
        colspan: int | None = None,
    ) -> bool:
        tdclass, content = self.render(row, link_renderer, user)
        assert isinstance(content, str | HTML)
        writer.td(content, class_=tdclass, colspan=colspan)
        return content != ""


class JoinCell(Cell):
    def __init__(
        self,
        column_spec: ColumnSpec,
        sort_url_parameter: str | None,
        registered_painters: Mapping[str, InternalPainter],
        painter_context: PainterContext,
        request_cache: RequestCache[RequestCacheConfig],
    ) -> None:
        super().__init__(
            column_spec, sort_url_parameter, registered_painters, painter_context, request_cache
        )
        if (join_value := column_spec.join_value) is None:
            raise ValueError

        self.join_value = join_value

    @override
    def title(self, use_short: bool = True) -> str:
        return self._custom_title or self.join_value

    @override
    def tooltip_title(self) -> str:
        return self.title()

    @override
    def export_title(self) -> str:
        serv_painter = re.sub(r"[^\w]", "_", self.title().lower())
        return f"{self._painter_name}.{serv_painter}"


def join_row(row: Row, cell: Cell) -> Row:
    return row.get("JOIN", {}).get(cell.join_value) if isinstance(cell, JoinCell) else row


class EmptyCell(Cell):
    def __init__(self) -> None:
        super().__init__(None, None, None, None, None)

    @override
    def render(
        self,
        row: Row,
        link_renderer: Callable[[str | HTML, Row, VisualLinkSpec], str | HTML] | None,
        user: LoggedInUser,
    ) -> tuple[str, str]:
        return "", ""

    @override
    def paint(
        self,
        row: Row,
        link_renderer: Callable[[str | HTML, Row, VisualLinkSpec], str | HTML] | None,
        user: LoggedInUser,
        writer: HTMLWriter,
        colspan: int | None = None,
    ) -> bool:
        return False
