#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="unreachable"

"""Provides the view editor dialog"""

from __future__ import annotations

import ast
import datetime as dt
import string
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, Literal, NamedTuple, overload, override, TypedDict

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.config import active_config
from cmk.gui.dashboard.type_defs import ViewDashletConfig
from cmk.gui.data_source import ABCDataSource, data_source_registry
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKInternalError, MKUserError
from cmk.gui.http import request, response
from cmk.gui.i18n import _
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.painter.v0 import all_painters, Cell, Painter
from cmk.gui.painter.v0.helpers import RenderLink
from cmk.gui.painter_options import PainterOptions
from cmk.gui.permissions import permission_registry
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import (
    ColumnName,
    ColumnSpec,
    ColumnTypes,
    DynamicIconName,
    InventoryJoinMacrosSpec,
    PainterName,
    PainterParameters,
    SingleInfos,
    SorterSpec,
    ViewSpec,
    VisualLinkSpec,
    VisualName,
    VisualTypeName,
)
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
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
    Migrate,
    OptionalDropdownChoice,
    TextInput,
    TextOrRegExp,
    Transform,
    Tuple,
    ValueSpec,
)
from cmk.gui.views.inventory import (
    inv_display_hints,
    OrderedColumnDisplayHintsOfView,
    TableWithView,
)
from cmk.gui.visuals.info import visual_info_registry
from cmk.gui.visuals.type import visual_type_registry
from cmk.inventory.structured_data import SDPath

from .layout import layout_registry
from .sorter import all_sorters, ParameterizedSorter, Sorter
from .store import get_all_views
from .view_choices import view_choices


def page_edit_view(ctx: PageContext) -> None:
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
        UserPermissions.from_config(ctx.config, permission_registry),
        custom_field_handler=render_view_config,
        create_handler=create_view_from_valuespec,
        info_handler=get_view_infos,
    )


def view_editor_options() -> list[
    tuple[Literal["mobile", "mustsearch", "force_checkboxes", "user_sortable", "play_sounds"], str]
]:
    return [
        ("mobile", _("Show this view in the Mobile GUI")),
        ("mustsearch", _("Show data only on search")),
        ("force_checkboxes", _("Always show the checkboxes")),
        ("user_sortable", _("Make view sortable by user")),
        ("play_sounds", _("Play alarm sounds")),
    ]


def view_editor_general_properties(ds_name: str) -> Dictionary:
    return Dictionary(
        title=_("View properties"),
        render="form",
        optional_keys=False,
        elements=[
            (
                "datasource",
                FixedValue(
                    value=ds_name,
                    title=_("Data source"),
                    totext=data_source_registry[ds_name]().title,
                    help=_("The data source of a view cannot be changed."),
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
                "row_limit",
                OptionalDropdownChoice(
                    title=_("Row limit"),
                    choices=[
                        (0, _("Use global hard/soft limit behavior")),
                    ],
                    explicit=Integer(
                        default_value=10,
                        minvalue=1,
                        maxvalue=1000,
                    ),
                    otherlabel=_("Set custom row limit"),
                ),
            ),
            (
                "layout",
                DropdownChoice(
                    title=_("Basic layout"),
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
                Migrate(
                    DropdownChoice(
                        title=_("Column Headers"),
                        choices=[
                            ("off", _("off")),
                            ("pergroup", _("once per group")),
                        ],
                        default_value="pergroup",
                    ),
                    migrate=_migrate_column_headers_repeat_to_pergroup,
                ),
            ),
        ],
    )


def _migrate_column_headers_repeat_to_pergroup(setting: str) -> str:
    """In 2.5 we removed the 'repeat' option for column headers
    because we don't need it now that we have sticky headers.
    This function ensures previous settings are migrated properly. Can be removed in 2.6."""
    if setting == "repeat":
        return "pergroup"
    return setting


def view_inventory_join_macros(
    ds_name: str, all_column_display_hints: Sequence[OrderedColumnDisplayHintsOfView]
) -> Dictionary:
    def _validate_macro_of_datasource(macro: str, varprefix: str) -> None:
        allowed_macros_chars = string.ascii_uppercase + string.digits + "_"
        if (
            not (macro.startswith("$") and macro.endswith("$"))
            or len(macro) <= 2
            or any(c not in allowed_macros_chars for c in macro[1:-1])
        ):
            raise MKUserError(
                varprefix,
                _(
                    "A macro must begin and end with '$' and is allowed to contain only"
                    " ASCII upper letters, digits and underscores."
                ),
            )

    return Dictionary(
        title=_("Macros for joining service data or inventory tables"),
        render="form",
        optional_keys=False,
        elements=[
            (
                "macros",
                ListOf(
                    Tuple(
                        elements=[
                            DropdownChoice(
                                title=_("Use value from"),
                                choices=[
                                    col_info
                                    for col_hints in all_column_display_hints
                                    for col_info in _get_inventory_column_infos(col_hints)
                                ],
                            ),
                            TextInput(
                                title=_("as macro named"),
                                validate=_validate_macro_of_datasource,
                                allow_empty=False,
                            ),
                        ]
                    ),
                    title=_("Macros"),
                    add_label=_("Add new macro"),
                    magic="##col##",
                ),
            ),
        ],
    )


def view_editor_column_spec(
    ident: str, ds_name: str, user_permissions: UserPermissions
) -> Dictionary:
    choices = [
        _get_common_vs_column_choice(ds_name, user_permissions, add_custom_column_title=True)
    ]
    if join_vs_column_choice := _get_join_vs_column_choice(ds_name, user_permissions):
        choices.append(join_vs_column_choice)

    if join_inv_vs_column_choice := _get_join_inv_vs_column_choice(ds_name, user_permissions):
        choices.append(join_inv_vs_column_choice)

    return _view_editor_spec(
        ds_name=ds_name,
        ident=ident,
        title=_("Columns"),
        vs_column=CascadingDropdown(choices=choices),
        allow_empty=False,
        empty_text=_("Please add at least one column to your view."),
    )


def view_editor_grouping_spec(
    ident: str, ds_name: str, user_permissions: UserPermissions
) -> Dictionary:
    return _view_editor_spec(
        ds_name=ds_name,
        ident=ident,
        title=_("Grouping"),
        vs_column=CascadingDropdown(
            choices=[
                _get_common_vs_column_choice(
                    ds_name, user_permissions, add_custom_column_title=False
                )
            ]
        ),
        allow_empty=True,
        empty_text=None,
    )


class _VSColumnChoice(NamedTuple):
    column_type: ColumnTypes
    title: str
    vs: Dictionary


def _get_common_vs_column_choice(
    ds_name: str,
    user_permissions: UserPermissions,
    add_custom_column_title: bool,
) -> _VSColumnChoice:
    painters = painters_of_datasource(ds_name, user_permissions)

    elements = [_get_vs_column_dropdown(ds_name, "painter", painters, user_permissions)]
    if add_custom_column_title:
        elements.append(_get_vs_column_title())
    elements.extend(_get_vs_link_or_tooltip_elements(painters, user_permissions))

    return _VSColumnChoice(
        column_type="column",
        title=_("Column"),
        vs=Dictionary(
            elements=elements,
            optional_keys=["link_spec", "tooltip"],
        ),
    )


def _get_vs_column_title() -> tuple[str, TextInput]:
    return ("column_title", TextInput(title=_("Title")))


def _get_join_vs_column_choice(
    ds_name: str, user_permissions: UserPermissions
) -> None | _VSColumnChoice:
    if not (join_painters := join_painters_of_datasource(ds_name, user_permissions)):
        return None

    return _VSColumnChoice(
        column_type="join_column",
        title=_("Joined column"),
        vs=Dictionary(
            help=_(
                "A joined column can display information about specific services for "
                "host objects in a view showing host objects. You need to specify the "
                "service name of the service you like to show the data for."
            ),
            elements=[
                _get_vs_column_dropdown(ds_name, "join_painter", join_painters, user_permissions),
                (
                    "join_value",
                    TextOrRegExp(
                        title=_("of Service"),
                        allow_empty=False,
                        help=_(
                            "If multiple entries are found, the first one of the sorted entries"
                            " is used. If you use macros within inventory based views these"
                            " macros are replaced <tt>before</tt> the regex evaluation."
                            "<br>Note: If a service name contains special characters like"
                            " <tt>%s</tt> you have to escape them in order to get reliable"
                            " results. Macros don't need to be escaped. If a macro could not be"
                            " found then it stays as it is."
                        )
                        % ", ".join([f"'{c}'" for c in "[]\\().?{}|*^$+"]),
                    ),
                ),
                _get_vs_column_title(),
            ]
            + _get_vs_link_or_tooltip_elements(join_painters, user_permissions),
            optional_keys=["link_spec", "tooltip"],
        ),
    )


def _get_join_inv_vs_column_choice(
    ds_name: str, user_permissions: UserPermissions
) -> _VSColumnChoice | None:
    if not _is_inventory_datasource(ds_name):
        return None

    elements: list[tuple[str, ValueSpec]] = [
        (
            "painter_spec",
            CascadingDropdown(
                title=_("Column"),
                label=_("From inventory table"),
                choices=[
                    (
                        table_info.table_view_name,
                        table_info.title,
                        Dictionary(
                            elements=[
                                (
                                    "column_to_display",
                                    DropdownChoice(
                                        title=_("Display the column"),
                                        choices=column_infos,
                                    ),
                                ),
                                (
                                    "columns_to_match",
                                    ListOf(
                                        Tuple(
                                            elements=[
                                                DropdownChoice(
                                                    title=_("The column"),
                                                    choices=column_infos,
                                                ),
                                                TextInput(
                                                    title=_("must match"),
                                                    allow_empty=False,
                                                ),
                                            ],
                                            orientation="horizontal",
                                            help=_(
                                                "Here you have to use macros which are defined"
                                                " above below <tt>Macros for joining service data"
                                                " or inventory tables</tt>. The joining of"
                                                " different inventory tables is based on these"
                                                " macros."
                                            ),
                                        ),
                                        title=_("Columns to match"),
                                        add_label=_("Add new match criteria"),
                                        allow_empty=False,
                                        magic="#@inv@#",
                                    ),
                                ),
                                ("path_to_table", FixedValue(table_info.path, totext="")),
                            ],
                            optional_keys=[],
                        ),
                    )
                    for table_info, column_infos in _get_inventory_column_infos_by_table(ds_name)
                ],
            ),
        ),
        _get_vs_column_title(),
    ]

    return _VSColumnChoice(
        column_type="join_inv_column",
        title=_("Joined inventory column"),
        vs=Dictionary(
            elements=elements + _get_vs_link_or_tooltip_elements({}, user_permissions),
            optional_keys=["link_spec", "tooltip"],
        ),
    )


class InventoryTableInfo(NamedTuple):
    table_view_name: str
    path: SDPath
    title: str


class InventoryColumnInfo(NamedTuple):
    column_name: str
    title: str


def _get_inventory_column_infos_by_table(
    ds_name: str,
) -> Iterator[tuple[InventoryTableInfo, Sequence[InventoryColumnInfo]]]:
    for node_hint in inv_display_hints:
        if not isinstance(node_hint.table, TableWithView):
            continue

        if node_hint.table.name in ("", ds_name):
            # No view, no choices; Also skip in case of same data source:
            # columns are already avail in "normal" column.
            continue

        yield (
            InventoryTableInfo(
                table_view_name=node_hint.table.name,
                path=node_hint.path,
                title=node_hint.long_title,
            ),
            _get_inventory_column_infos(node_hint.table.columns),
        )


def _get_inventory_column_infos(
    column_display_hints: OrderedColumnDisplayHintsOfView,
) -> Sequence[InventoryColumnInfo]:
    registered_painters = all_painters(active_config.tags.tag_groups)
    return [
        InventoryColumnInfo(
            column_name=column_name,
            title=str(column_hint.title),
        )
        for column_name, column_hint in column_display_hints.items()
        if column_hint.name and registered_painters.get(column_hint.name)
    ]


def _get_vs_column_dropdown(
    ds_name: str,
    painter_type: str,
    painters: Mapping[str, Painter],
    user_permissions: UserPermissions,
) -> tuple[str, ValueSpec]:
    return (
        "painter_spec",
        CascadingDropdown(
            title=_("Column"),
            choices=_painter_choices_with_params(painters, user_permissions),
            no_preselect_title="",
            render_sub_vs_page_name="ajax_cascading_render_painer_parameters",
            render_sub_vs_request_vars={
                "ds_name": ds_name,
                "painter_type": painter_type,
            },
        ),
    )


def _get_vs_link_or_tooltip_elements(
    painters: Mapping[str, Painter],
    user_permissions: UserPermissions,
) -> list[tuple[str, ValueSpec]]:
    return [
        (
            "link_spec",
            CascadingDropdown(
                title=_("Link"),
                choices=_column_link_choices(user_permissions),
                orientation="horizontal",
            ),
        ),
        (
            "tooltip",
            DropdownChoice(
                title=_("Tooltip"),
                choices=_painter_choices(painters, user_permissions),
            ),
        ),
    ]


class _RawVSColumnSpecOptional(TypedDict, total=False):
    link_spec: tuple[VisualTypeName, VisualName]
    tooltip: ColumnName


class _RawVSColumnSpec(_RawVSColumnSpecOptional):
    painter_spec: PainterName | tuple[PainterName, PainterParameters]
    column_title: str


class _RawVSJoinColumnSpec(_RawVSColumnSpec):
    join_value: ColumnName


class _RawVSJoinInvColumnSpec(_RawVSColumnSpecOptional):
    painter_spec: tuple[PainterName, PainterParameters]
    column_title: str


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
            tuple[Literal["column"], _RawVSColumnSpec]
            | tuple[Literal["join_column"], _RawVSJoinColumnSpec]
            | tuple[Literal["join_inv_column"], _RawVSJoinInvColumnSpec]
        ),
    ) -> ColumnSpec:
        if value[0] == "column":
            column_type, inner_value = value
            return ColumnSpec(
                _column_type=column_type,
                name=_get_name(inner_value),
                parameters=_get_params(inner_value),
                column_title=inner_value.get("column_title", ""),
                link_spec=_get_link_spec(inner_value),
                tooltip=inner_value.get("tooltip"),
            )

        if value[0] == "join_column":
            join_column_type, inner_value = value
            return ColumnSpec(
                _column_type=join_column_type,
                name=_get_name(inner_value),
                parameters=_get_params(inner_value),
                join_value=inner_value["join_value"],
                column_title=inner_value["column_title"],
                link_spec=_get_link_spec(inner_value),
                tooltip=inner_value.get("tooltip"),
            )

        if value[0] == "join_inv_column":
            return _from_vs_join_inv_column(*value)

        raise ValueError()

    def _from_vs_join_inv_column(
        column_type: Literal["join_inv_column"],
        inner_value: _RawVSJoinInvColumnSpec,
    ) -> ColumnSpec:
        # The column_spec.name must be created from the table view name ("name") and
        # "column_to_display" because the related painter is registered under this name.
        name, parameters = inner_value["painter_spec"]
        join_value = "_".join([name, parameters["column_to_display"]])
        return ColumnSpec(
            _column_type=column_type,
            name=join_value,
            parameters=PainterParameters(
                column_to_display=parameters["column_to_display"],
                columns_to_match=parameters["columns_to_match"],
                path_to_table=parameters["path_to_table"],
            ),
            join_value=join_value,
            column_title=inner_value["column_title"],
            link_spec=_get_link_spec(inner_value),
            tooltip=inner_value.get("tooltip"),
        )

    def _get_name(value: _RawVSColumnSpec) -> PainterName:
        return ps[0] if isinstance((ps := value["painter_spec"]), tuple) else ps

    def _get_params(value: _RawVSColumnSpec) -> PainterParameters:
        return ps[1] if isinstance((ps := value["painter_spec"]), tuple) else PainterParameters()

    def _get_link_spec(value: _RawVSColumnSpec | _RawVSJoinInvColumnSpec) -> VisualLinkSpec | None:
        return None if (ls := value.get("link_spec")) is None else VisualLinkSpec.from_raw(ls)

    def _to_vs(
        column_spec: ColumnSpec | None,
    ) -> (
        tuple[Literal["column"], _RawVSColumnSpec]
        | tuple[Literal["join_column"], _RawVSJoinColumnSpec]
        | tuple[Literal["join_inv_column"], _RawVSJoinInvColumnSpec]
        | None
    ):
        if column_spec is None:
            return None

        if (column_type := column_spec.column_type) == "column":
            raw_vs = _RawVSColumnSpec(
                painter_spec=_get_painter_spec(column_spec),
                column_title=column_spec.column_title or "",
            )
            if column_spec.link_spec:
                raw_vs["link_spec"] = column_spec.link_spec.to_raw()
            if column_spec.tooltip:
                raw_vs["tooltip"] = column_spec.tooltip
            return column_type, raw_vs

        if column_type == "join_column" and column_spec.join_value:
            raw_vs = _RawVSJoinColumnSpec(
                painter_spec=_get_painter_spec(column_spec),
                join_value=column_spec.join_value,
                column_title=column_spec.column_title or "",
            )
            if column_spec.link_spec:
                raw_vs["link_spec"] = column_spec.link_spec.to_raw()
            if column_spec.tooltip:
                raw_vs["tooltip"] = column_spec.tooltip
            return column_type, raw_vs

        if column_type == "join_inv_column":
            # See related function "_from_vs" regarding "painter_spec":
            raw_inv_vs = _RawVSJoinInvColumnSpec(
                painter_spec=(
                    column_spec.name.removesuffix(
                        "_" + column_spec.parameters["column_to_display"]
                    ),
                    {
                        "column_to_display": column_spec.parameters["column_to_display"],
                        "columns_to_match": column_spec.parameters["columns_to_match"],
                        "path_to_table": column_spec.parameters["path_to_table"],
                    },
                ),
                column_title=column_spec.column_title or "",
            )
            if column_spec.link_spec:
                raw_inv_vs["link_spec"] = column_spec.link_spec.to_raw()
            if column_spec.tooltip:
                raw_inv_vs["tooltip"] = column_spec.tooltip
            return column_type, raw_inv_vs

        raise ValueError()

    def _get_painter_spec(
        column_spec: ColumnSpec,
    ) -> PainterName | tuple[PainterName, PainterParameters]:
        if column_spec.parameters is None:
            return column_spec.name
        return (column_spec.name, column_spec.parameters)

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


def _column_link_choices(user_permissions: UserPermissions) -> list[CascadingDropdownChoice]:
    visual_type = visual_type_registry["dashboards"]()
    return [
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
                choices=visual_type.choices(visual_type.visuals(), user_permissions),
                sorted=True,
            ),
        ),
    ]


def view_editor_sorter_specs(
    ident: str, ds_name: str, painters: Sequence[ColumnSpec], user_permissions: UserPermissions
) -> Dictionary:
    def _sorter_choices(
        ds_name: str, painters: Sequence[ColumnSpec]
    ) -> Iterator[DropdownChoiceEntry | CascadingDropdownChoice]:
        datasource: ABCDataSource = data_source_registry[ds_name]()
        unsupported_columns: list[ColumnName] = datasource.unsupported_columns
        registered_painters = all_painters(active_config.tags.tag_groups)

        for name, p in sorters_of_datasource(ds_name, user_permissions).items():
            if any(column in p.columns for column in unsupported_columns):
                continue
            # Sorters may provide a third element: That Dictionary will be displayed after the
            # sorter was choosen in the CascadingDropdown.
            if isinstance(p, ParameterizedSorter):
                yield (
                    name,
                    get_sorter_plugin_title_for_choices(p, registered_painters, user_permissions),
                    p.vs_parameters(active_config, painters),
                )
            else:
                yield (
                    name,
                    get_sorter_plugin_title_for_choices(p, registered_painters, user_permissions),
                )

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
    @override
    def page(self, ctx: PageContext) -> PageResult:
        api_request = request.get_request()

        user_permissions = UserPermissions.from_config(ctx.config, permission_registry)
        if api_request["painter_type"] == "painter":
            painters = painters_of_datasource(api_request["ds_name"], user_permissions)
        elif api_request["painter_type"] == "join_painter":
            painters = join_painters_of_datasource(api_request["ds_name"], user_permissions)
        else:
            raise NotImplementedError()

        vs = CascadingDropdown(choices=_painter_choices_with_params(painters, user_permissions))
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


def render_view_config(view_spec: ViewSpec, general_properties: bool = True) -> None:
    value = _transform_view_to_valuespec_value(view_spec)

    # TODO: This and the modification of the view_spec should not be here. Find a better place
    ds_name: str = view_spec.get("datasource", request.get_ascii_input_mandatory("datasource", ""))
    if not ds_name:
        raise MKInternalError(_("No data source defined."))
    if ds_name not in data_source_registry:
        raise MKInternalError(_("The given data source is not supported."))

    value["datasource"] = ds_name

    if general_properties:
        view_editor_general_properties(ds_name).render_input("view", value.get("view"))

    if _is_inventory_datasource(ds_name):
        view_inventory_join_macros(
            ds_name,
            [h.table.columns for h in inv_display_hints if isinstance(h.table, TableWithView)],
        ).render_input("macros", value.get("inventory_join_macros"))

    user_permissions = UserPermissions.from_config(active_config, permission_registry)
    vs_columns = view_editor_column_spec("columns", ds_name, user_permissions)
    vs_columns.render_input("columns", value["columns"])

    vs_sorting = view_editor_sorter_specs(
        "sorting", ds_name, value["columns"]["columns"], user_permissions
    )
    vs_sorting.render_input("sorting", value["sorting"])

    vs_grouping = view_editor_grouping_spec("grouping", ds_name, user_permissions)
    vs_grouping.render_input("grouping", value["grouping"])


# Is used to change the view structure to be compatible to
# the valuespec This needs to perform the inverted steps of the
# _transform_valuespec_value_to_view() function. FIXME: One day we should
# rewrite this to make no transform needed anymore
def _transform_view_to_valuespec_value(view: ViewSpec) -> dict[str, Any]:
    value: dict[str, Any] = {**view}
    value["view"] = {}  # Several global variables are put into a sub-dict
    # Only copy our known keys. Reporting element, etc. might have their own keys as well
    for key in [
        "datasource",
        "browser_reload",
        "layout",
        "num_columns",
        "column_headers",
        "row_limit",
    ]:
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


def _update_view_with_valuespec_values(
    view: ViewSpec | ViewDashletConfig, ident: str, attrs: dict[str, Any]
) -> None:
    """Transform valuespec values into view structure"""
    if ident == "view":
        options = attrs.pop("options", [])
        if options:
            for option, _title in view_editor_options():
                view[option] = option in options

    if ident == "sorting":
        view["sorters"] = [SorterSpec(*s) for s in attrs["sorters"]]

    if ident == "grouping":
        view["group_painters"] = attrs["grouping"]

    if ident == "columns":
        view["painters"] = attrs["columns"]

    if ident == "macros":
        view["inventory_join_macros"] = InventoryJoinMacrosSpec({"macros": attrs["macros"]})


# Extract properties of view from HTML variables and construct
# view object, to be used for saving or displaying
#
# old_view is the old view dict which might be loaded from storage.
# view is the new dict object to be updated.
def create_view_from_valuespec[T: (ViewSpec, ViewDashletConfig)](old_view: T, view: T) -> T:
    ds_name = old_view.get("datasource") or request.get_ascii_input_mandatory("datasource")
    view["datasource"] = ds_name

    def update_view(ident: str, vs: Dictionary) -> None:
        attrs = vs.from_html_vars(ident)
        vs.validate_value(attrs, ident)
        _update_view_with_valuespec_values(view, ident, attrs)

    user_permissions = UserPermissions.from_config(active_config, permission_registry)
    update_view("view", view_editor_general_properties(ds_name))
    update_view("columns", view_editor_column_spec("columns", ds_name, user_permissions))
    update_view("grouping", view_editor_grouping_spec("grouping", ds_name, user_permissions))
    update_view(
        "sorting", view_editor_sorter_specs("sorting", ds_name, view["painters"], user_permissions)
    )

    if _is_inventory_datasource(ds_name):
        update_view(
            "macros",
            view_inventory_join_macros(
                ds_name,
                [h.table.columns for h in inv_display_hints if isinstance(h.table, TableWithView)],
            ),
        )

    view["modified_at"] = dt.datetime.now(dt.UTC).isoformat()

    return view


def _painter_choices(
    painters: Mapping[str, Painter], user_permissions: UserPermissions
) -> DropdownChoiceEntries:
    return [(c[0], c[1]) for c in _painter_choices_with_params(painters, user_permissions)]


def _painter_choices_with_params(
    painters: Mapping[str, Painter], user_permissions: UserPermissions
) -> list[CascadingDropdownChoice]:
    registered_painters = all_painters(active_config.tags.tag_groups)
    return sorted(
        (
            (
                name,
                _get_painter_plugin_title_for_choices(
                    painter, registered_painters, user_permissions
                ),
                painter.parameters if painter.parameters else None,
            )
            for name, painter in painters.items()
        ),
        key=lambda x: x[1],
    )


def _get_painter_plugin_title_for_choices(
    plugin: Painter,
    registered_painters: Mapping[str, type[Painter]],
    user_permissions: UserPermissions,
) -> str:
    dummy_cell = Cell(ColumnSpec(plugin.ident), None, registered_painters, user_permissions)
    return f"{_get_info_title(plugin)}: {plugin.list_title(dummy_cell)}"


def get_sorter_plugin_title_for_choices(
    plugin: Sorter,
    registered_painters: Mapping[str, type[Painter]],
    user_permissions: UserPermissions,
) -> str:
    dummy_cell = Cell(ColumnSpec(plugin.ident), None, registered_painters, user_permissions)
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
            "icon": DynamicIconName("folder"),
            "user_sortable": True,
            "single_infos": [],
            "context": {},
            "link_from": {},
            "add_context_to_title": True,
            "is_show_more": False,
            "packaged": False,
            "main_menu_search_terms": [],
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


def sorters_of_datasource(ds_name: str, user_permissions: UserPermissions) -> Mapping[str, Sorter]:
    return _allowed_for_datasource(all_sorters(active_config), ds_name, user_permissions)


def painters_of_datasource(
    ds_name: str, user_permissions: UserPermissions
) -> Mapping[str, Painter]:
    return _allowed_for_datasource(
        all_painters(active_config.tags.tag_groups), ds_name, user_permissions
    )


def join_painters_of_datasource(
    ds_name: str, user_permissions: UserPermissions
) -> Mapping[str, Painter]:
    datasource = data_source_registry[ds_name]()
    if datasource.join is None:
        return {}  # no joining with this datasource

    # Get the painters allowed for the join "source" and "target"
    painters = painters_of_datasource(ds_name, user_permissions)
    join_painters_unfiltered = _allowed_for_datasource(
        all_painters(active_config.tags.tag_groups), datasource.join[0], user_permissions
    )

    # Filter out painters associated with the "join source" datasource
    join_painters: dict[str, Painter] = {}
    for key, val in join_painters_unfiltered.items():
        if key not in painters:
            join_painters[key] = val

    return join_painters


@overload
def _allowed_for_datasource(
    collection: Mapping[str, type[Painter]], ds_name: str, user_permissions: UserPermissions
) -> Mapping[str, Painter]: ...


@overload
def _allowed_for_datasource(
    collection: Mapping[str, Sorter], ds_name: str, user_permissions: UserPermissions
) -> Mapping[str, Sorter]: ...


# Filters a list of sorters or painters and decides which of
# those are available for a certain data source
def _allowed_for_datasource(
    collection: Mapping[str, type[Painter]] | Mapping[str, Sorter],
    ds_name: str,
    user_permissions: UserPermissions,
) -> Mapping[str, Sorter | Painter]:
    datasource: ABCDataSource = data_source_registry[ds_name]()
    infos_available: set[str] = set(datasource.infos)
    add_columns: list[ColumnName] = datasource.add_columns
    unsupported_columns: list[ColumnName] = datasource.unsupported_columns

    allowed: dict[str, Sorter | Painter] = {}
    plugin: Sorter | Painter
    for name, instance in collection.items():
        if isinstance(instance, Sorter):
            plugin = instance
        elif issubclass(instance, Painter):
            plugin = instance(
                config=active_config,
                request=request,
                painter_options=PainterOptions.get_instance(),
                theme=theme,
                url_renderer=RenderLink(request, response, display_options),
                user_permissions=user_permissions,
            )
        else:
            raise TypeError(f"Unexpected instance type ({type(instance)}): {instance}")

        if any(column in plugin.columns for column in unsupported_columns):
            continue
        infos_needed = infos_needed_by_plugin(plugin, add_columns)
        if len(infos_needed.difference(infos_available)) == 0:
            allowed[name] = plugin

    return allowed


def _is_inventory_datasource(ds_name: str) -> bool:
    return ds_name.startswith("inv")
