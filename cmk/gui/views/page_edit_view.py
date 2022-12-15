#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Provides the view editor dialog"""

import ast
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, Literal, NamedTuple, overload

from cmk.utils.type_defs import UserId

from cmk.gui import visuals
from cmk.gui.dashboard import ViewDashletConfig
from cmk.gui.exceptions import MKGeneralException, MKInternalError, MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage, PageResult
from cmk.gui.plugins.visuals.utils import visual_info_registry, visual_type_registry
from cmk.gui.type_defs import (
    ColumnName,
    ColumnTypes,
    PainterName,
    PainterParameters,
    PainterSpec,
    SingleInfos,
    SorterSpec,
    ViewSpec,
    VisualLinkSpec,
)
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.valuespec import (
    CascadingDropdown,
    CascadingDropdownChoice,
    Dictionary,
    DropdownChoice,
    DropdownChoiceEntries,
    DropdownChoiceEntry,
    FixedValue,
    Integer,
    ListChoice,
    ListOf,
    TextInput,
    Transform,
    Tuple,
    ValueSpec,
)

from .data_source import ABCDataSource, data_source_registry
from .layout import layout_registry
from .painter.v0.base import Cell, Painter, painter_registry, PainterRegistry
from .sorter import ParameterizedSorter, Sorter, sorter_registry, SorterRegistry
from .store import get_all_views
from .view_choices import view_choices


def page_edit_view() -> None:
    def get_view_infos(view: ViewSpec) -> SingleInfos:
        """Return list of available datasources (used to render filters)"""
        # In create mode "datasource" is mandatory, in other mode it's not
        ds_name = view.get("datasource", request.get_ascii_input_mandatory("datasource", ""))
        try:
            return data_source_registry[ds_name]().infos
        except KeyError:
            raise MKUserError("datasource", _("Invalid data source: %s") % ds_name)

    visuals.page_edit_visual(
        "views",
        get_all_views(),
        custom_field_handler=render_view_config,
        create_handler=create_view_from_valuespec,
        info_handler=get_view_infos,
    )


def view_editor_options():
    return [
        ("mobile", _("Show this view in the Mobile GUI")),
        ("mustsearch", _("Show data only on search")),
        ("force_checkboxes", _("Always show the checkboxes")),
        ("user_sortable", _("Make view sortable by user")),
        ("play_sounds", _("Play alarm sounds")),
    ]


def view_editor_general_properties(ds_name: str) -> Dictionary:
    return Dictionary(
        title=_("View Properties"),
        render="form",
        optional_keys=False,
        elements=[
            (
                "datasource",
                FixedValue(
                    value=ds_name,
                    title=_("Datasource"),
                    totext=data_source_registry[ds_name]().title,
                    help=_("The datasource of a view cannot be changed."),
                ),
            ),
            (
                "options",
                ListChoice(
                    title=_("Options"),
                    choices=view_editor_options(),
                    default_value=["user_sortable"],
                ),
            ),
            (
                "browser_reload",
                Integer(
                    title=_("Automatic page reload"),
                    unit=_("seconds"),
                    minvalue=0,
                    help=_('Set to "0" to disable the automatic reload.'),
                ),
            ),
            (
                "layout",
                DropdownChoice(
                    title=_("Basic Layout"),
                    choices=layout_registry.get_choices(),
                    default_value="table",
                    sorted=True,
                ),
            ),
            (
                "num_columns",
                Integer(
                    title=_("Number of Columns"),
                    default_value=1,
                    minvalue=1,
                    maxvalue=50,
                ),
            ),
            (
                "column_headers",
                DropdownChoice(
                    title=_("Column Headers"),
                    choices=[
                        ("off", _("off")),
                        ("pergroup", _("once per group")),
                        ("repeat", _("repeat every 20'th row")),
                    ],
                    default_value="pergroup",
                ),
            ),
        ],
    )


def view_editor_column_spec(ident: str, ds_name: str) -> Dictionary:
    choices = [_get_common_vs_column_choice(ds_name)]
    if join_vs_column_choice := _get_join_vs_column_choice(ds_name):
        choices.append(join_vs_column_choice)

    return _view_editor_spec(
        ds_name=ds_name,
        ident=ident,
        title=_("Columns"),
        vs_column=CascadingDropdown(choices=choices),
        allow_empty=False,
        empty_text=_("Please add at least one column to your view."),
    )


def view_editor_grouping_spec(ident: str, ds_name: str) -> Dictionary:
    return _view_editor_spec(
        ds_name=ds_name,
        ident=ident,
        title=_("Grouping"),
        vs_column=CascadingDropdown(choices=[_get_common_vs_column_choice(ds_name)]),
        allow_empty=True,
        empty_text=None,
    )


class _VSColumnChoice(NamedTuple):
    column_type: ColumnTypes
    title: str
    vs: Tuple


def _get_common_vs_column_choice(ds_name: str) -> _VSColumnChoice:
    painters = painters_of_datasource(ds_name)
    return _VSColumnChoice(
        column_type="column",
        title=_("Column"),
        vs=Tuple(
            elements=[
                _get_vs_column_dropdown(ds_name, "painter", painters),
            ]
            + _get_vs_link_or_tooltip_elements(painters),
        ),
    )


def _get_join_vs_column_choice(ds_name: str) -> None | _VSColumnChoice:
    if not (join_painters := join_painters_of_datasource(ds_name)):
        return None

    return _VSColumnChoice(
        column_type="join_column",
        title=_("Joined column"),
        vs=Tuple(
            help=_(
                "A joined column can display information about specific services for "
                "host objects in a view showing host objects. You need to specify the "
                "service description of the service you like to show the data for."
            ),
            elements=[
                _get_vs_column_dropdown(ds_name, "join_painter", join_painters),
                TextInput(
                    title=_("of Service"),
                    allow_empty=False,
                ),
                TextInput(title=_("Title")),
            ]
            + _get_vs_link_or_tooltip_elements(join_painters),
        ),
    )


def _get_vs_column_dropdown(
    ds_name: str, painter_type: str, painters: Mapping[str, Painter]
) -> ValueSpec:
    return CascadingDropdown(
        title=_("Column"),
        choices=_painter_choices_with_params(painters),
        no_preselect_title="",
        render_sub_vs_page_name="ajax_cascading_render_painer_parameters",
        render_sub_vs_request_vars={
            "ds_name": ds_name,
            "painter_type": painter_type,
        },
    )


def _get_vs_link_or_tooltip_elements(painters: Mapping[str, Painter]) -> list[ValueSpec]:
    return [
        CascadingDropdown(
            title=_("Link"),
            choices=_column_link_choices(),
            orientation="horizontal",
        ),
        DropdownChoice(
            title=_("Tooltip"),
            choices=[(None, "")] + list(_painter_choices(painters)),
        ),
    ]


_RawColumnPainterSpec = tuple[
    PainterName | tuple[PainterName, PainterParameters],
    VisualLinkSpec | None,
    ColumnName | None,
]


_RawJoinColumnPainterSpec = tuple[
    PainterName | tuple[PainterName, PainterParameters],
    ColumnName,
    str,
    VisualLinkSpec | None,
    ColumnName | None,
]


def _view_editor_spec(
    *,
    ident: str,
    ds_name: str,
    title: str,
    vs_column: ValueSpec,
    allow_empty: bool,
    empty_text: str | None,
) -> Dictionary:
    # Note: for ident == "grouping" we always have "column" type,
    # ie. there aren't any "join_column"s.

    def _from_vs(
        value: (
            tuple[Literal["column"], _RawColumnPainterSpec]
            | tuple[Literal["join_column"], _RawJoinColumnPainterSpec]
        )
    ) -> PainterSpec:
        column_type, inner_value = value

        if isinstance(name_or_parameters := inner_value[0], tuple):
            name, parameters = name_or_parameters
        else:
            name = name_or_parameters
            parameters = None

        link_spec = inner_value[-2]
        tooltip = inner_value[-1]

        if column_type == "column":
            return PainterSpec(
                _column_type=column_type,
                name=name,
                parameters=parameters,
                link_spec=link_spec,
                tooltip=tooltip,
            )

        if (
            column_type == "join_column"
            and isinstance(join_index := inner_value[1], str)
            and isinstance(column_title := inner_value[2], str)
        ):
            return PainterSpec(
                _column_type=column_type,
                name=name,
                parameters=parameters,
                join_index=join_index,
                column_title=column_title,
                link_spec=link_spec,
                tooltip=tooltip,
            )

        raise ValueError()

    def _to_vs(
        painter_spec: PainterSpec | None,
    ) -> (
        tuple[Literal["column"], _RawColumnPainterSpec]
        | tuple[Literal["join_column"], _RawJoinColumnPainterSpec]
        | None
    ):
        if painter_spec is None:
            return None

        if painter_spec.column_type == "column" and painter_spec.join_index is None:
            return (
                painter_spec.column_type,
                (
                    _get_name_or_params(painter_spec),
                    painter_spec.link_spec,
                    painter_spec.tooltip,
                ),
            )

        if (
            painter_spec.column_type == "join_column"
            and isinstance(painter_spec.join_index, str)
            and isinstance(painter_spec.column_title, str)
        ):
            return (
                painter_spec.column_type,
                (
                    _get_name_or_params(painter_spec),
                    painter_spec.join_index,
                    painter_spec.column_title,
                    painter_spec.link_spec,
                    painter_spec.tooltip,
                ),
            )

        raise ValueError()

    def _get_name_or_params(
        painter_spec: PainterSpec,
    ) -> PainterName | tuple[PainterName, PainterParameters]:
        if painter_spec.parameters is None:
            return painter_spec.name
        return (painter_spec.name, painter_spec.parameters)

    vs_column = Transform(
        valuespec=vs_column,
        from_valuespec=_from_vs,
        to_valuespec=_to_vs,
    )

    return Dictionary(
        title=title,
        render="form",
        optional_keys=False,
        elements=[
            (
                ident,
                ListOf(
                    valuespec=vs_column,
                    title=title,
                    add_label=_("Add column"),
                    allow_empty=allow_empty,
                    empty_text=empty_text,
                ),
            ),
        ],
    )


def _column_link_choices() -> list[CascadingDropdownChoice]:
    return [
        (None, _("Do not add a link")),
        (
            "views",
            _("Link to view") + ":",
            DropdownChoice(
                choices=view_choices,
                sorted=True,
            ),
        ),
        (
            "dashboards",
            _("Link to dashboard") + ":",
            DropdownChoice(
                choices=visual_type_registry["dashboards"]().choices,
                sorted=True,
            ),
        ),
    ]


def view_editor_sorter_specs(
    ident: str, ds_name: str, painters: Sequence[PainterSpec]
) -> Dictionary:
    def _sorter_choices(
        ds_name: str, painters: Sequence[PainterSpec]
    ) -> Iterator[DropdownChoiceEntry | CascadingDropdownChoice]:
        datasource: ABCDataSource = data_source_registry[ds_name]()
        unsupported_columns: list[ColumnName] = datasource.unsupported_columns

        for name, p in sorters_of_datasource(ds_name).items():
            if any(column in p.columns for column in unsupported_columns):
                continue
            # Sorters may provide a third element: That Dictionary will be displayed after the
            # sorter was choosen in the CascadingDropdown.
            if isinstance(p, ParameterizedSorter) and (parameters := p.vs_parameters(painters)):
                yield name, get_sorter_plugin_title_for_choices(p), parameters
            else:
                yield name, get_sorter_plugin_title_for_choices(p)

    return Dictionary(
        title=_("Sorting"),
        render="form",
        optional_keys=False,
        elements=[
            (
                "sorters",
                ListOf(
                    valuespec=Tuple(
                        elements=[
                            CascadingDropdown(
                                title=_("Column"),
                                choices=list(_sorter_choices(ds_name, painters)),
                                sorted=True,
                                no_preselect_title="",
                            ),
                            DropdownChoice(
                                title=_("Order"),
                                choices=[(False, _("Ascending")), (True, _("Descending"))],
                            ),
                        ],
                        orientation="horizontal",
                    ),
                    title=_("Sorting"),
                    add_label=_("Add sorter"),
                ),
            ),
        ],
    )


class PageAjaxCascadingRenderPainterParameters(AjaxPage):
    def page(self) -> PageResult:
        api_request = request.get_request()

        if api_request["painter_type"] == "painter":
            painters = painters_of_datasource(api_request["ds_name"])
        elif api_request["painter_type"] == "join_painter":
            painters = join_painters_of_datasource(api_request["ds_name"])
        else:
            raise NotImplementedError()

        vs = CascadingDropdown(choices=_painter_choices_with_params(painters))
        sub_vs = self._get_sub_vs(vs, ast.literal_eval(api_request["choice_id"]))
        value = ast.literal_eval(api_request["encoded_value"])

        with output_funnel.plugged():
            vs.show_sub_valuespec(api_request["varprefix"], sub_vs, value)
            return {"html_code": output_funnel.drain()}

    def _get_sub_vs(self, vs: CascadingDropdown, choice_id: object) -> ValueSpec:
        for val, _title, sub_vs in vs.choices():
            if val == choice_id:
                if sub_vs is None:
                    raise MKGeneralException("Choice does not have a ValueSpec")
                return sub_vs
        raise MKGeneralException("Invaild choice")


def render_view_config(
    view_spec: ViewDashletConfig | ViewSpec, general_properties: bool = True
) -> None:
    value = _transform_view_to_valuespec_value(view_spec)

    # TODO: This and the modification of the view_spec should not be here. Find a better place
    ds_name: str = view_spec.get("datasource", request.get_ascii_input_mandatory("datasource", ""))
    if not ds_name:
        raise MKInternalError(_("No datasource defined."))
    if ds_name not in data_source_registry:
        raise MKInternalError(_("The given datasource is not supported."))

    value["datasource"] = ds_name

    if general_properties:
        view_editor_general_properties(ds_name).render_input("view", value.get("view"))

    vs_columns = view_editor_column_spec("columns", ds_name)
    vs_columns.render_input("columns", value["columns"])

    vs_sorting = view_editor_sorter_specs("sorting", ds_name, value["columns"]["columns"])
    vs_sorting.render_input("sorting", value["sorting"])

    vs_grouping = view_editor_grouping_spec("grouping", ds_name)
    vs_grouping.render_input("grouping", value["grouping"])


# Is used to change the view structure to be compatible to
# the valuespec This needs to perform the inverted steps of the
# _transform_valuespec_value_to_view() function. FIXME: One day we should
# rewrite this to make no transform needed anymore
def _transform_view_to_valuespec_value(view: ViewDashletConfig | ViewSpec) -> dict[str, Any]:
    value: dict[str, Any] = {**view}
    value["view"] = {}  # Several global variables are put into a sub-dict
    # Only copy our known keys. Reporting element, etc. might have their own keys as well
    for key in ["datasource", "browser_reload", "layout", "num_columns", "column_headers"]:
        if key in value:
            value["view"][key] = value[key]

    if not value.get("topic"):
        value["topic"] = "other"

    value["view"]["options"] = []
    for key, _title in view_editor_options():
        if value.get(key):
            value["view"]["options"].append(key)

    value["visibility"] = {}
    for key in ["hidden", "hidebutton", "public"]:
        if value.get(key):
            value["visibility"][key] = value[key]

    value["grouping"] = {"grouping": value.get("group_painters", [])}

    value["sorting"] = {
        "sorters": [sorter_spec.to_raw() for sorter_spec in value.get("sorters", {})]
    }

    value["columns"] = {"columns": value.get("painters", [])}
    return value


def _transform_valuespec_value_to_view(ident, attrs):
    # Transform some valuespec specific options to legacy view format.
    # We do not want to change the view data structure at the moment.

    if ident == "view":
        options = attrs.pop("options", [])
        if options:
            for option, _title in view_editor_options():
                attrs[option] = option in options

        return attrs

    if ident == "sorting":
        return {"sorters": [SorterSpec(*s) for s in attrs["sorters"]]}

    if ident == "grouping":
        return {"group_painters": attrs["grouping"]}

    if ident == "columns":
        return {"painters": attrs["columns"]}

    return {ident: attrs}


# Extract properties of view from HTML variables and construct
# view object, to be used for saving or displaying
#
# old_view is the old view dict which might be loaded from storage.
# view is the new dict object to be updated.
def create_view_from_valuespec(old_view, view):
    ds_name = old_view.get("datasource", request.var("datasource"))
    view["datasource"] = ds_name

    def update_view(ident, vs):
        attrs = vs.from_html_vars(ident)
        vs.validate_value(attrs, ident)
        view.update(_transform_valuespec_value_to_view(ident, attrs))

    update_view("view", view_editor_general_properties(ds_name))
    update_view("columns", view_editor_column_spec("columns", ds_name))
    update_view("grouping", view_editor_grouping_spec("grouping", ds_name))
    update_view("sorting", view_editor_sorter_specs("sorting", ds_name, view["painters"]))
    return view


def _painter_choices(painters: Mapping[str, Painter]) -> DropdownChoiceEntries:
    return [(c[0], c[1]) for c in _painter_choices_with_params(painters)]


def _painter_choices_with_params(painters: Mapping[str, Painter]) -> list[CascadingDropdownChoice]:
    return sorted(
        (
            (
                name,
                _get_painter_plugin_title_for_choices(painter),
                painter.parameters if painter.parameters else None,
            )
            for name, painter in painters.items()
        ),
        key=lambda x: x[1],
    )


def _get_painter_plugin_title_for_choices(plugin: Painter) -> str:
    dummy_cell = Cell(PainterSpec(plugin.ident), None)
    return f"{_get_info_title(plugin)}: {plugin.list_title(dummy_cell)}"


def get_sorter_plugin_title_for_choices(plugin: Sorter) -> str:
    dummy_cell = Cell(PainterSpec(plugin.ident), None)
    title: str
    if callable(plugin.title):
        title = plugin.title(dummy_cell)
    else:
        title = plugin.title
    return f"{_get_info_title(plugin)}: {title}"


def _dummy_view_spec() -> ViewSpec:
    # Just some dummy view to make the query() method callable. We'll review this for a cleanup.
    return ViewSpec(
        {
            "browser_reload": 30,
            "column_headers": "pergroup",
            "datasource": "hosts",
            "description": "",
            "group_painters": [],
            "hidden": False,
            "hidebutton": False,
            "layout": "table",
            "mustsearch": False,
            "name": "allhosts",
            "num_columns": 3,
            "owner": UserId.builtin(),
            "painters": [],
            "play_sounds": False,
            "public": True,
            "sorters": [],
            "title": "",
            "topic": "overview",
            "sort_index": 20,
            "icon": "folder",
            "user_sortable": True,
            "single_infos": [],
            "context": {},
            "link_from": {},
            "add_context_to_title": True,
            "is_show_more": False,
        }
    )


def _get_info_title(plugin: Painter | Sorter) -> str:
    # TODO: Cleanup the special case for sites. How? Add an info for it?
    if plugin.columns == ["site"]:
        return _("Site")

    return "/".join(
        [
            str(visual_info_registry[info_name]().title_plural)
            for info_name in sorted(infos_needed_by_plugin(plugin))
        ]
    )


def infos_needed_by_plugin(plugin: Painter | Sorter, add_columns: list | None = None) -> set[str]:
    if add_columns is None:
        add_columns = []

    return {c.split("_", 1)[0] for c in plugin.columns if c != "site" and c not in add_columns}


def sorters_of_datasource(ds_name: str) -> Mapping[str, Sorter]:
    return _allowed_for_datasource(sorter_registry, ds_name)


def painters_of_datasource(ds_name: str) -> Mapping[str, Painter]:
    return _allowed_for_datasource(painter_registry, ds_name)


def join_painters_of_datasource(ds_name: str) -> Mapping[str, Painter]:
    datasource = data_source_registry[ds_name]()
    if datasource.join is None:
        return {}  # no joining with this datasource

    # Get the painters allowed for the join "source" and "target"
    painters = painters_of_datasource(ds_name)
    join_painters_unfiltered = _allowed_for_datasource(painter_registry, datasource.join[0])

    # Filter out painters associated with the "join source" datasource
    join_painters: dict[str, Painter] = {}
    for key, val in join_painters_unfiltered.items():
        if key not in painters:
            join_painters[key] = val

    return join_painters


@overload
def _allowed_for_datasource(collection: PainterRegistry, ds_name: str) -> Mapping[str, Painter]:
    ...


@overload
def _allowed_for_datasource(collection: SorterRegistry, ds_name: str) -> Mapping[str, Sorter]:
    ...


# Filters a list of sorters or painters and decides which of
# those are available for a certain data source
def _allowed_for_datasource(
    collection: PainterRegistry | SorterRegistry,
    ds_name: str,
) -> Mapping[str, Sorter | Painter]:
    datasource: ABCDataSource = data_source_registry[ds_name]()
    infos_available: set[str] = set(datasource.infos)
    add_columns: list[ColumnName] = datasource.add_columns
    unsupported_columns: list[ColumnName] = datasource.unsupported_columns

    allowed: dict[str, Sorter | Painter] = {}
    for name, plugin_class in collection.items():
        plugin = plugin_class()
        if any(column in plugin.columns for column in unsupported_columns):
            continue
        infos_needed = infos_needed_by_plugin(plugin, add_columns)
        if len(infos_needed.difference(infos_available)) == 0:
            allowed[name] = plugin

    return allowed
