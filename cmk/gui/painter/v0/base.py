#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

import abc
import os
import re
import traceback
from collections.abc import Callable, Mapping, Sequence
from html import unescape
from typing import Any, Literal

from cmk.ccc.exceptions import MKGeneralException

import cmk.utils.paths

from cmk.gui import visuals
from cmk.gui.config import active_config, Config
from cmk.gui.display_options import display_options
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, request, response
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter_options import PainterOptions
from cmk.gui.theme import Theme
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import (
    ColumnName,
    ColumnSpec,
    HTTPVariables,
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
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri
from cmk.gui.valuespec import ValueSpec
from cmk.gui.view_utils import CellSpec, CSVExportError, JSONExportError, PythonExportError

from ..v1.painter_lib import experimental_painter_registry, Formatters, PainterConfiguration
from ..v1.painter_lib import Painter as V1Painter
from .helpers import RenderLink

ExportCellContent = str | dict[str, Any]
PDFCellContent = str | tuple[Literal["icon"], str]
PDFCellSpec = tuple[Sequence[str], PDFCellContent]


# TODO: Return value of render() could be cleaned up e.g. to a named tuple with an
# optional CSS class. A lot of painters don't specify CSS classes.
# TODO: Since we have the reporting also working with the painters it could be useful
# to make the render function return structured data which can then be rendered for
# HTML and PDF.
# TODO: A lot of painter classes simply display plain livestatus column values. These
# could be replaced with some simpler generic definition.
class Painter(abc.ABC):
    """A painter computes HTML code based on information from a data row and
    creates a CSS class for one display column.

    Please note, that there is no
    1:1 relation between data columns and display columns. A painter can
    make use of more than one data columns. One example is the current
    service state. It uses the columns "service_state" and "has_been_checked".
    """

    def __init__(
        self,
        *,
        config: Config,
        request: Request,
        painter_options: PainterOptions,
        theme: Theme,
        url_renderer: RenderLink,
    ):
        self.config = config
        self.request = request
        self._painter_options = painter_options
        self.theme = theme
        self.url_renderer = url_renderer

    def to_v1_painter(self) -> V1Painter[object]:
        """Convert an instance of an old painter to a v1 Painter."""

        def get_row(rows: Rows, config: PainterConfiguration) -> Sequence[Any]:
            return rows

        # Needed because of old calling conventions. Doesn't have any effect.
        empty_cell = EmptyCell(None, None, None)

        def format_html(
            row: Row, _painter_configuration: PainterConfiguration, user: LoggedInUser
        ) -> CellSpec:
            return self.render(row, empty_cell, user)

        def format_json(
            row: Row, _painter_configuration: PainterConfiguration, user: LoggedInUser
        ) -> object:
            return self.export_for_json(row, empty_cell, user)

        def format_csv(
            row: Row, _painter_configuration: PainterConfiguration, user: LoggedInUser
        ) -> str:
            result = self.export_for_csv(row, empty_cell, user)
            if isinstance(result, HTML):
                # ??? Typing doesn't fit.
                return str(result)
            return result

        return V1Painter[Any](
            ident=self.ident,
            computer=get_row,
            formatters=Formatters[Any](
                html=format_html,
                json=format_json,
                csv=format_csv,
            ),
            title=self.title(empty_cell),
            short_title=self.short_title(empty_cell),
            columns=self.columns,
            list_title=self.list_title(empty_cell),
            painter_options=self.painter_options,
            title_classes=self.title_classes(),
        )

    @staticmethod
    def uuid_col(cell: Cell) -> str:
        # This method is only overwritten in two subclasses and does not even
        # use `self`.  This is all very fishy.
        return ""

    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a painter. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @abc.abstractmethod
    def title(self, cell: Cell) -> str:
        """Used as display string for the painter in the GUI (e.g. views using this painter)"""
        raise NotImplementedError()

    def title_classes(self) -> list[str]:
        """Additional css classes used to render the title"""
        return []

    @property
    @abc.abstractmethod
    def columns(self) -> Sequence[ColumnName]:
        """Livestatus columns needed for this painter"""
        raise NotImplementedError()

    def dynamic_columns(self, cell: Cell) -> list[ColumnName]:
        """Return list of dynamically generated column as specified by Cell

        Some columns for the Livestatus query need to be generated at
        execution time, knowing user configuration. Using the Cell object
        generated the required column names."""
        return []

    def derive(self, rows: Rows, cell: Cell, dynamic_columns: Sequence[ColumnName]) -> None:
        """Post process query according to cell

        This function processes data immediately after it is handled back
        from the Livestatus Datasource. It gets access to the entire
        returned table and sequentially to each of the cells configured.

        rows: List of Dictionaries
             Data table of the returning query. Every element is a
             dictionary which keys are the column names. Derive function
             should mutate in place each row. When processing data or
             generating new columns.
        cell: Cell
            Used to retrieve configuration parameters
        dynamic_columns: Sequence[ColumnName]
            The exact dynamic columns generated by the painter before the
            query. As they might be required to find them again within the
            data."""

    def short_title(self, cell: Cell) -> str:
        """Used as display string for the painter e.g. as table header
        Falls back to the full title if no short title is given"""
        return self.title(cell)

    def tooltip_title(self, cell: Cell) -> str:
        """Used as string for the painter title in table header tooltips
        Falls back to the full title if no tooltip title is given"""
        return self.title(cell)

    def export_title(self, cell: Cell) -> str:
        """Used for exporting views in JSON/CSV/python format"""
        return self.ident

    def list_title(self, cell: Cell) -> str:
        """Override this to define a custom title for the painter in the view editor
        Falls back to the full title if no short title is given"""
        return self.title(cell)

    def group_by(
        self,
        row: Row,
        cell: Cell,
    ) -> None | str | tuple[str, ...] | tuple[tuple[str, str], ...]:
        """When a value is returned, this is used instead of the value produced by self.paint()"""
        return None

    @property
    def parameters(self) -> ValueSpec | None:
        """Returns either the valuespec of the painter parameters or None"""
        return None

    @property
    def painter_options(self) -> list[str]:
        """Returns a list of painter option names that affect this painter"""
        return []

    @property
    def printable(self) -> bool | str:
        """
        True       : Is printable in PDF
        False      : Is not printable at all
        "<string>" : ID of a painter_printer (Reporting module)
        """
        return True

    @property
    def use_painter_link(self) -> bool:
        """Allow the view spec to define a view / dashboard to link to"""
        return True

    @property
    def sorter(self) -> SorterName | None:
        """Returns the optional name of the sorter for this painter"""
        return None

    # TODO: Cleanup this hack
    @property
    def load_inv(self) -> bool:
        """Whether or not to load the HW/SW Inventory for this column"""
        return False

    # TODO At the moment we use render as fallback but in the future every
    # painter should implement explicit
    #   - _compute_data
    #   - render
    #   - export methods
    # As soon as this is done all four methods will be abstract.

    # See first implementations: PainterInventoryTree, PainterHostLabels, ...

    # TODO For PDF we implement an additional method.

    def _compute_data(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        return self.render(row, cell, user)[1]

    @abc.abstractmethod
    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        """Renders the painter for the given row
        The paint function gets one argument: A data row, which is a python
        dictionary representing one data object (host, service, ...). Its
        keys are the column names, its values the actual values from livestatus
        (typed: numbers are float or int, not string)

        The paint function must return a pair of two strings:
            - A CSS class for the TD of the column and
            - a Text string or HTML code for painting the column

        That class is optional and set to "" in most cases. Currently CSS
        styles are not modular and all defined in check_mk.css. This will
        change in future."""
        raise NotImplementedError()

    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        """Render the content of the painter for Pyton export based on the given row.

        If the data of a painter can not be exported as Python, then this method
        raises a 'PythonExportError'.
        """
        return self._compute_data(row, cell, user)

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        """Render the content of the painter for CSV export based on the given row.

        If the data of a painter can not be exported as CSV (like trees), then this method
        raises a 'CSVExportError'.
        """
        if isinstance(data := self._compute_data(row, cell, user), str | HTML):
            return data
        raise ValueError("Data must be of type 'str' or 'HTML' but is %r" % type(data))

    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> object:
        """Render the content of the painter for JSON export based on the given row.

        If the data of a painter can not be exported as JSON, then this method
        raises a 'JSONExportError'.
        """
        return self._compute_data(row, cell, user)


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
        registered_painters: Mapping[str, type[Painter]] | None,
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

    def _link_view(self, permitted_views: Mapping[ViewName, ViewSpec]) -> ViewSpec | None:
        if self._link_spec is None:
            return None

        try:
            return permitted_views[self._link_spec.name]
        except KeyError:
            return None

    def painter(self) -> Painter:
        painter_options_inst = PainterOptions.get_instance()
        try:
            return PainterAdapter(
                experimental_painter_registry[self.painter_name()],
                config=active_config,
                request=request,
                painter_options=painter_options_inst,
                theme=theme,
                url_renderer=RenderLink(request, response, display_options),
            )
        except KeyError:
            assert self._registered_painters is not None
            return self._registered_painters[self.painter_name()](
                config=active_config,
                request=request,
                painter_options=painter_options_inst,
                theme=theme,
                url_renderer=RenderLink(request, response, display_options),
            )

    def painter_name(self) -> PainterName:
        assert self._painter_name is not None
        return self._painter_name

    def export_title(self) -> str:
        if self._custom_title:
            return re.sub(r"[^\w]", "_", self._custom_title.lower())
        return self.painter().export_title(self)

    def painter_options(self) -> list[str]:
        return self.painter().painter_options

    def painter_parameters(self) -> PainterParameters | None:
        """The parameters configured in the view for this painter. In case the
        painter has params, it defaults to the valuespec default value and
        in case the painter has no params, it returns None."""
        if not (vs_painter_params := self.painter().parameters):
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
        return painter.tooltip_title(self)

    def _get_short_title(self, painter: Painter) -> str:
        return painter.short_title(self)

    def _get_long_title(self, painter: Painter) -> str:
        return painter.title(self)

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

    def tooltip_painter(self) -> Painter:
        assert self._tooltip_painter_name is not None
        assert self._registered_painters is not None
        return self._registered_painters[self._tooltip_painter_name](
            config=active_config,
            request=request,
            painter_options=PainterOptions.get_instance(),
            theme=theme,
            url_renderer=RenderLink(request, response, display_options),
        )

    def paint_as_header(self) -> None:
        # Optional: Sort link in title cell
        # Use explicit defined sorter or implicit the sorter with the painter name
        # Important for links:
        # - Add the display options (Keeping the same display options as current)
        # - Link to _self (Always link to the current frame)
        classes: list[str] = []
        onclick = ""
        title = ""
        if display_options.enabled(display_options.L) and self._sort_url_parameter:
            params: HTTPVariables = [
                ("sort", self._sort_url_parameter),
                ("_show_filter_form", 0),
            ]
            if display_options.title_options:
                params.append(("display_options", display_options.title_options))

            classes += ["sort"]
            onclick = "location.href='%s'" % makeuri(request, addvars=params, remove_prefix="sort")
            title = _("Sort by %s") % self.tooltip_title()
        classes += self.painter().title_classes()

        html.open_th(class_=classes, onclick=onclick, title=title)
        html.write_text_permissive(self.title())
        html.close_th()

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
            logger.exception("Failed to render painter '%s' (Row: %r)", self._painter_name, row)
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
                ColumnSpec(self.tooltip_painter_name()), None, self._registered_painters
            )
            _tooltip_tdclass, tooltip_content = tooltip_cell.render_content(row, user=user)
            assert not isinstance(tooltip_content, Mapping)
            tooltip_text = escaping.strip_tags_for_tooltip(tooltip_content)
            if tooltip_text:
                content = HTMLWriter.render_span(content, title=tooltip_text)

        return tdclass, content

    def _use_painter_link(self) -> bool:
        return self.painter().use_painter_link

    # Same as self.render() for HTML output: Gets a painter and a data
    # row and creates the text for being painted.
    def render_for_pdf(
        self, row: Row, time_range: tuple[int, int], user: LoggedInUser
    ) -> PDFCellSpec:
        # TODO: Move this somewhere else!
        def find_htdocs_image_path(filename):
            themes = theme.icon_themes()
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
                return css_classes.split(), ""
            assert isinstance(rendered_txt, str | HTML)

            txt = rendered_txt.strip()
            content: PDFCellContent = ""

            # Handle <img...>. Our PDF writer cannot draw arbitrary
            # images, but all that we need for showing simple icons.
            # Current limitation: *one* image
            assert not isinstance(txt, tuple)
            if (isinstance(txt, str) and txt.lower().startswith("<img")) or (
                isinstance(txt, HTML) and txt.lower().startswith(HTML.without_escaping("<img"))
            ):
                img_filename = re.sub(".*src=[\"']([^'\"]*)[\"'].*", "\\1", str(txt))
                img_path = find_htdocs_image_path(img_filename)
                if img_path:
                    content = ("icon", img_path)
                else:
                    content = img_filename

            if not content:
                if isinstance(txt, HTML):
                    content = escaping.strip_tags(unescape(str(txt)))
                elif not isinstance(txt, tuple):
                    content = escaping.strip_tags(unescape(txt))

            return css_classes.split(), content
        except Exception:
            raise MKGeneralException(
                f'Failed to paint "{self.painter_name()}": {traceback.format_exc()}'
            )

    def render_for_python_export(self, row: Row, user: LoggedInUser) -> object:
        if request.var("output_format") not in ["python", "python_export"]:
            return "NOT_PYTHON_EXPORTABLE"

        if not row:
            return ""

        try:
            content = self.painter().export_for_python(row, self, user)
        except PythonExportError:
            return "NOT_PYTHON_EXPORTABLE"

        if isinstance(content, str | HTML):
            # TODO At the moment we have to keep this str/HTML handling because export_for_python
            # falls back to render. As soon as all painters have explicit export_for_* methods,
            # we can remove this...
            return self._render_html_content(content)

        return content

    def render_for_csv_export(self, row: Row, user: LoggedInUser) -> str | HTML:
        if request.var("output_format") not in ["csv", "csv_export"]:
            return "NOT_CSV_EXPORTABLE"

        if not row:
            return ""

        try:
            content = self.painter().export_for_csv(row, self, user)
        except CSVExportError:
            return "NOT_CSV_EXPORTABLE"

        return self._render_html_content(content)

    def render_for_json_export(self, row: Row, user: LoggedInUser) -> object:
        if request.var("output_format") not in ["json", "json_export"]:
            return "NOT_JSON_EXPORTABLE"

        if not row:
            return ""

        try:
            content = self.painter().export_for_json(row, self, user)
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

        return txt

    def render_content(self, row: Row, user: LoggedInUser) -> CellSpec:
        if not row:
            return "", ""  # nothing to paint

        painter = self.painter()
        return painter.render(row, self, user)

    def paint(
        self,
        row: Row,
        link_renderer: Callable[[str | HTML, Row, VisualLinkSpec], str | HTML] | None,
        user: LoggedInUser,
        colspan: int | None = None,
    ) -> bool:
        tdclass, content = self.render(row, link_renderer, user)
        assert isinstance(content, str | HTML)
        html.td(content, class_=tdclass, colspan=colspan)
        return content != ""


class JoinCell(Cell):
    def __init__(
        self,
        column_spec: ColumnSpec,
        sort_url_parameter: str | None,
        registered_painters: Mapping[str, type[Painter]],
    ) -> None:
        super().__init__(column_spec, sort_url_parameter, registered_painters)
        if (join_value := column_spec.join_value) is None:
            raise ValueError()

        self.join_value = join_value

    def title(self, use_short: bool = True) -> str:
        return self._custom_title or self.join_value

    def tooltip_title(self) -> str:
        return self.title()

    def export_title(self) -> str:
        serv_painter = re.sub(r"[^\w]", "_", self.title().lower())
        return f"{self._painter_name}.{serv_painter}"


def join_row(row: Row, cell: Cell) -> Row:
    return row.get("JOIN", {}).get(cell.join_value) if isinstance(cell, JoinCell) else row


class EmptyCell(Cell):
    def render(
        self,
        row: Row,
        link_renderer: Callable[[str | HTML, Row, VisualLinkSpec], str | HTML] | None,
        user: LoggedInUser,
    ) -> tuple[str, str]:
        return "", ""

    def paint(
        self,
        row: Row,
        link_renderer: Callable[[str | HTML, Row, VisualLinkSpec], str | HTML] | None,
        user: LoggedInUser,
        colspan: int | None = None,
    ) -> bool:
        return False


class PainterAdapter(Painter):
    """Adapt a "new" Painter to work in code expecting an "old" one.

    "new" means Painters deriving from cmk.gui.painter.v1.painter_lib.Painter
    "old" means Painters deriving from cmk.gui.painter.v0.base.Painter

    Args:
        painter: a "new" Painter instance

    """

    def __init__(
        self,
        painter: V1Painter,
        *,
        config: Config,
        request: Request,
        painter_options: PainterOptions,
        theme: Theme,
        url_renderer: RenderLink,
    ):
        super().__init__(
            config=config,
            request=request,
            painter_options=painter_options,
            theme=theme,
            url_renderer=url_renderer,
        )
        self._painter = painter

    @property
    def ident(self) -> str:
        return self._painter.ident

    def title(self, cell: Cell) -> str:
        return str(self._painter.title)

    def short_title(self, cell: Cell) -> str:
        return str(self._painter.short_title)

    @property
    def columns(self) -> Sequence[ColumnName]:
        return self._painter.columns

    def dynamic_columns(self, cell: Cell) -> list[ColumnName]:
        # TODO: the dynamic columns/derive functionality is added, once we migrate painters using it
        if self._painter.dynamic_columns is None or (params := cell.painter_parameters()) is None:
            return []
        return list(self._painter.dynamic_columns(params))

    @property
    def painter_options(self) -> list[str]:
        """Returns a list of painter option names that affect this painter"""
        return self._painter.painter_options or []

    def title_classes(self) -> list[str]:
        return self._painter.title_classes or []

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        config = PainterConfiguration(
            parameters=cell.painter_parameters(), columns=self._painter.columns
        )
        return self._painter.formatters.html(
            list(self._painter.computer([row], config))[0],
            config,
            user,
        )
