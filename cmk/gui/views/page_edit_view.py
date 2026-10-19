#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="type-arg"

"""Provides the view editor dialog"""

import ast
import datetime as dt
import string
from collections.abc import Iterator, Mapping, Sequence, Set
from functools import partial
from typing import Any, Literal, NamedTuple, overload, override, TypedDict, TypeIs

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.config import active_config, Config
from cmk.gui.dashboard.type_defs import ViewDashletConfig
from cmk.gui.data_source import ABCDataSource, data_source_registry
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKInternalError, MKUserError
from cmk.gui.http import request, response
from cmk.gui.i18n import _, _l
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.painter import all_painters, Cell, InternalPainter, PainterConfig, PainterContext
from cmk.gui.painter.helpers import RenderLink
from cmk.gui.painter_options import PainterOptions
from cmk.gui.permissions import all_permissions
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import (
    ColumnName,
    ColumnSpec,
    ColumnTypes,
    ContextFilterConfig,
    ContextualLinkEntryConfig,
    ContextualLinkTargetType,
    FilterName,
    InfoName,
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
    AjaxDropdownChoice,
    CascadingDropdown,
    CascadingDropdownChoice,
    Checkbox,
    Dictionary,
    DictionaryModel,
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
from cmk.gui.visuals.filter import filter_registry
from cmk.gui.visuals.info import visual_info_registry
from cmk.gui.visuals.type import visual_type_registry
from cmk.inventory.trees import SDPath
from cmk.ruleset_matcher.tags import TagConfig
from cmk.web.utils.autocompleter_config import AutocompleterConfig, AutocompleterParams
from cmk.web.utils.icons import DynamicIconName

from .drilldown_filters import drilldown_filters, filled_single_infos
from .layout import layout_registry
from .sorter import all_sorters, ParameterizedSorter, Sorter
from .store import get_all_views, get_permitted_views
from .view_choices import view_choices

# Inherited: carries the clicked row's object; custom: the filters the user picks.
type _InheritedDrilldownChoice = Literal["drilldown_views", "drilldown_dashboards"]
_INHERITED_DRILLDOWN_TARGETS: Mapping[_InheritedDrilldownChoice, ContextualLinkTargetType] = {
    "drilldown_views": "views",
    "drilldown_dashboards": "dashboards",
}
_INHERITED_DRILLDOWN_CHOICES: Mapping[ContextualLinkTargetType, _InheritedDrilldownChoice] = {
    target: choice for choice, target in _INHERITED_DRILLDOWN_TARGETS.items()
}

type _CustomDrilldownChoice = Literal["custom_drilldown_views", "custom_drilldown_dashboards"]
_CUSTOM_DRILLDOWN_TARGETS: Mapping[_CustomDrilldownChoice, ContextualLinkTargetType] = {
    "custom_drilldown_views": "views",
    "custom_drilldown_dashboards": "dashboards",
}
_CUSTOM_DRILLDOWN_CHOICES: Mapping[ContextualLinkTargetType, _CustomDrilldownChoice] = {
    target: choice for choice, target in _CUSTOM_DRILLDOWN_TARGETS.items()
}
_DRILLDOWN_TITLES = {
    "drilldown_views": _l("Drill down to view (inherited)"),
    "drilldown_dashboards": _l("Drill down to dashboard (inherited)"),
    "custom_drilldown_views": _l("Drill down to view (custom)"),
    "custom_drilldown_dashboards": _l("Drill down to dashboard (custom)"),
}


def page_edit_view(ctx: PageContext) -> None:
    def get_view_infos(view: ViewSpec) -> SingleInfos:
        """Return list of available datasources (used to render filters)"""
        # In create mode "datasource" is mandatory, in other mode it's not
        ds_name = view.get("datasource", request.get_ascii_input_mandatory("datasource", ""))
        try:
            return data_source_registry[ds_name]().infos
        except KeyError:
            raise MKUserError(
                "datasource", _("Invalid data source: %(ds_name)s") % {"ds_name": ds_name}
            )

    visuals.page_edit_visual(
        "views",
        get_all_views(),
        ctx.user_permissions,
        ctx.config,
        custom_field_handler=partial(_render_editable_view_config, config=ctx.config),
        create_handler=partial(_create_editable_view, config=ctx.config),
        info_handler=get_view_infos,
    )


def _render_editable_view_config(view_spec: ViewSpec, *, config: Config) -> None:
    render_view_config(view_spec, allow_browser_reload=True, config=config)


def _create_editable_view(old_view: ViewSpec, view: ViewSpec, *, config: Config) -> ViewSpec:
    return create_view_from_valuespec(old_view, view, allow_browser_reload=True, config=config)


def view_editor_options() -> list[
    tuple[Literal["mobile", "mustsearch", "force_checkboxes", "user_sortable", "play_sounds"], str]
]:
    return [
        ("mobile", _("Show this view in the mobile GUI")),
        ("mustsearch", _("Show data only on search")),
        ("force_checkboxes", _("Always show the checkboxes")),
        ("user_sortable", _("Make view sortable by user")),
        ("play_sounds", _("Play alarm sounds")),
    ]


def view_editor_general_properties(ds_name: str, *, allow_browser_reload: bool) -> Dictionary:
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
            *(
                [
                    (
                        "browser_reload",
                        Integer(
                            title=_("Automatic page reload"),
                            unit=_("seconds"),
                            minvalue=0,
                            help=_('Set to "0" to disable the automatic reload.'),
                        ),
                    )
                ]
                if allow_browser_reload
                else []
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
                    default_value=0,
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
                    title=_("Number of columns"),
                    default_value=1,
                    minvalue=1,
                    maxvalue=50,
                ),
            ),
            (
                "column_headers",
                Migrate(
                    DropdownChoice(
                        title=_("Column headers"),
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
    ds_name: str,  # noqa: ARG001
    all_column_display_hints: Sequence[OrderedColumnDisplayHintsOfView],
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
                    valuespec=Tuple(
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
    ident: str, ds_name: str, painter_context: PainterContext, *, with_drilldown: bool = False
) -> Dictionary:
    """The columns of the view editor.

    With drill-down, each column's value is a pair of its spec and its drill-down link.
    """
    drilldown_choices = (
        _drilldown_link_choices(
            ds_name, painter_context.user_permissions, painter_context.config.tags
        )
        if with_drilldown
        else []
    )
    choices = [
        _get_common_vs_column_choice(
            ds_name,
            painter_context,
            add_custom_column_title=True,
            drilldown_choices=drilldown_choices,
        )
    ]
    if join_vs_column_choice := _get_join_vs_column_choice(
        ds_name, painter_context, drilldown_choices=drilldown_choices
    ):
        choices.append(join_vs_column_choice)

    if join_inv_vs_column_choice := _get_join_inv_vs_column_choice(
        ds_name, painter_context, drilldown_choices=drilldown_choices
    ):
        choices.append(join_inv_vs_column_choice)

    return _view_editor_spec(
        ds_name=ds_name,
        ident=ident,
        title=_("Columns"),
        vs_column=CascadingDropdown(choices=choices),
        allow_empty=False,
        empty_text=_("Please add at least one column to your view."),
        with_drilldown=with_drilldown,
    )


def view_editor_grouping_spec(
    ident: str, ds_name: str, painter_context: PainterContext
) -> Dictionary:
    return _view_editor_spec(
        ds_name=ds_name,
        ident=ident,
        title=_("Grouping"),
        vs_column=CascadingDropdown(
            choices=[
                _get_common_vs_column_choice(
                    ds_name, painter_context, add_custom_column_title=False
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
    painter_context: PainterContext,
    add_custom_column_title: bool,
    drilldown_choices: Sequence[CascadingDropdownChoice] = (),
) -> _VSColumnChoice:
    painters = painters_of_datasource(ds_name)

    elements = [_get_vs_column_dropdown(ds_name, "painter", painters, painter_context)]
    if add_custom_column_title:
        elements.append(_get_vs_column_title())
    elements.extend(_get_vs_link_or_tooltip_elements(painters, painter_context, drilldown_choices))

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
    ds_name: str,
    painter_context: PainterContext,
    drilldown_choices: Sequence[CascadingDropdownChoice] = (),
) -> None | _VSColumnChoice:
    if not (join_painters := join_painters_of_datasource(ds_name)):
        return None

    return _VSColumnChoice(
        column_type="join_column",
        title=_("Joined column"),
        vs=Dictionary(
            help=_(
                "A joined column can display information about specific services for "
                "host objects in a view showing host objects. You need to specify the "
                "service name of the service you want to show the data for."
            ),
            elements=[
                _get_vs_column_dropdown(ds_name, "join_painter", join_painters, painter_context),
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
                            " <tt>%(special_chars)s</tt> you have to escape them in order to get reliable"
                            " results. Macros don't need to be escaped. If a macro could not be"
                            " found then it stays as it is."
                        )
                        % {"special_chars": ", ".join([f"'{c}'" for c in "[]\\().?{}|*^$+"])},
                    ),
                ),
                _get_vs_column_title(),
            ]
            + _get_vs_link_or_tooltip_elements(join_painters, painter_context, drilldown_choices),
            optional_keys=["link_spec", "tooltip"],
        ),
    )


def _get_join_inv_vs_column_choice(
    ds_name: str,
    painter_context: PainterContext,
    drilldown_choices: Sequence[CascadingDropdownChoice] = (),
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
                                        valuespec=Tuple(
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
                                                "Here, you have to use macros which are defined"
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
            elements=elements
            + _get_vs_link_or_tooltip_elements({}, painter_context, drilldown_choices),
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
    painters: Mapping[str, InternalPainter],
    painter_context: PainterContext,
) -> tuple[str, ValueSpec]:
    return (
        "painter_spec",
        CascadingDropdown(
            title=_("Column"),
            choices=_painter_choices_with_params(painters, painter_context),
            no_preselect_title="",
            render_sub_vs_page_name="ajax_cascading_render_painer_parameters",
            render_sub_vs_request_vars={
                "ds_name": ds_name,
                "painter_type": painter_type,
            },
        ),
    )


def _get_vs_link_or_tooltip_elements(
    painters: Mapping[str, InternalPainter],
    painter_context: PainterContext,
    drilldown_choices: Sequence[CascadingDropdownChoice] = (),
) -> list[tuple[str, ValueSpec]]:
    return [
        (
            "link_spec",
            CascadingDropdown(
                title=_("Link"),
                choices=[
                    *_column_link_choices(painter_context.user_permissions),
                    *drilldown_choices,
                ],
                orientation="horizontal",
            ),
        ),
        (
            "tooltip",
            DropdownChoice(
                title=_("Tooltip"),
                choices=_painter_choices(painters, painter_context),
            ),
        ),
    ]


type _RawVSDrilldownFilter = FilterName | tuple[FilterName, str]


class _RawVSCustomDrilldown(TypedDict):
    target: VisualName
    filters: list[_RawVSDrilldownFilter]
    include_context: bool
    include_time_range: bool


type _RawVSLinkSpec = (
    tuple[VisualTypeName, VisualName]
    | tuple[_InheritedDrilldownChoice, VisualName]
    | tuple[_CustomDrilldownChoice, _RawVSCustomDrilldown]
)


class _RawVSColumnSpecOptional(TypedDict, total=False):
    link_spec: _RawVSLinkSpec
    tooltip: ColumnName


def _is_inherited_drilldown(
    link_spec: _RawVSLinkSpec,
) -> TypeIs[tuple[_InheritedDrilldownChoice, VisualName]]:
    return link_spec[0] in _INHERITED_DRILLDOWN_TARGETS


def _is_custom_drilldown(
    link_spec: _RawVSLinkSpec,
) -> TypeIs[tuple[_CustomDrilldownChoice, _RawVSCustomDrilldown]]:
    return link_spec[0] in _CUSTOM_DRILLDOWN_TARGETS


def _drilldown_link(link_spec: _RawVSLinkSpec | None) -> ContextualLinkEntryConfig | None:
    if link_spec is None:
        return None
    if _is_inherited_drilldown(link_spec):
        target_type, name = _INHERITED_DRILLDOWN_TARGETS[link_spec[0]], link_spec[1]
        # Like a new inherited link in the wizard, it carries the context and the time range.
        return ContextualLinkEntryConfig(
            title=name,
            location=(target_type, name),
            filters=[],
            include_context=True,
            include_time_range=True,
            show_filter_form=False,
        )
    if _is_custom_drilldown(link_spec):
        target_type, custom = _CUSTOM_DRILLDOWN_TARGETS[link_spec[0]], link_spec[1]
        # The editor offers no title, owner or filter form, so it saves the defaults.
        return ContextualLinkEntryConfig(
            title=custom["target"],
            location=(target_type, custom["target"]),
            filters=[
                ContextFilterConfig(filter_id=raw)
                if isinstance(raw, str)
                else ContextFilterConfig(filter_id=raw[0], key=raw[1])
                for raw in custom["filters"]
            ],
            include_context=custom["include_context"],
            include_time_range=custom["include_time_range"],
            show_filter_form=False,
        )
    return None


def _drilldown_link_spec(link: ContextualLinkEntryConfig) -> _RawVSLinkSpec:
    target_type, name = link["location"][0], link["location"][1]
    if not link["filters"]:
        return _INHERITED_DRILLDOWN_CHOICES[target_type], name
    return _CUSTOM_DRILLDOWN_CHOICES[target_type], _RawVSCustomDrilldown(
        target=name,
        filters=[
            (config["filter_id"], config["key"]) if "key" in config else config["filter_id"]
            for config in link["filters"]
        ],
        include_context=link["include_context"],
        include_time_range=link["include_time_range"],
    )


class _RawVSColumnSpec(_RawVSColumnSpecOptional):
    # None until a column is chosen, e.g. in the ListOf template for "Add column"
    painter_spec: PainterName | tuple[PainterName, PainterParameters] | None
    column_title: str


class _RawVSJoinColumnSpec(_RawVSColumnSpec):
    join_value: ColumnName


class _RawVSJoinInvColumnSpec(_RawVSColumnSpecOptional):
    painter_spec: tuple[PainterName, PainterParameters]
    column_title: str


type _RawVSColumn = (
    tuple[Literal["column"], _RawVSColumnSpec]
    | tuple[Literal["join_column"], _RawVSJoinColumnSpec]
    | tuple[Literal["join_inv_column"], _RawVSJoinInvColumnSpec]
)


def _view_editor_spec(
    *,
    ident: str,
    ds_name: str,  # noqa: ARG001
    title: str,
    vs_column: ValueSpec,
    allow_empty: bool,
    empty_text: str | None,
    with_drilldown: bool = False,
) -> Dictionary:
    # Note: for ident == "grouping" we always have "column" type,
    # ie. there aren't any "join_column"s.

    def _from_vs(value: _RawVSColumn) -> ColumnSpec | _RawVSColumn:
        if value[0] == "column":
            return _from_vs_column(value, join_value=None)

        if value[0] == "join_column":
            return _from_vs_column(value, join_value=value[1]["join_value"])

        if value[0] == "join_inv_column":
            return _from_vs_join_inv_column(*value)

        raise ValueError

    def _from_vs_column(
        value: (
            tuple[Literal["column"], _RawVSColumnSpec]
            | tuple[Literal["join_column"], _RawVSJoinColumnSpec]
        ),
        *,
        join_value: ColumnName | None,
    ) -> ColumnSpec | _RawVSColumn:
        column_type, inner_value = value
        # An unchosen painter stays raw, so that validation reports it at its dropdown
        if (painter_spec := inner_value["painter_spec"]) is None:
            return value
        name, parameters = _split_painter_spec(painter_spec)
        return ColumnSpec(
            _column_type=column_type,
            name=name,
            parameters=parameters,
            join_value=join_value,
            column_title=inner_value.get("column_title", ""),
            link_spec=_get_link_spec(inner_value),
            tooltip=inner_value.get("tooltip"),
        )

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

    def _split_painter_spec(
        painter_spec: PainterName | tuple[PainterName, PainterParameters],
    ) -> tuple[PainterName, PainterParameters]:
        if isinstance(painter_spec, tuple):
            return painter_spec
        return painter_spec, PainterParameters()

    def _get_link_spec(value: _RawVSColumnSpec | _RawVSJoinInvColumnSpec) -> VisualLinkSpec | None:
        if (
            (ls := value.get("link_spec")) is None
            or _is_inherited_drilldown(ls)
            or _is_custom_drilldown(ls)
        ):
            return None
        return VisualLinkSpec.from_raw(ls)

    def _to_vs(column_spec: ColumnSpec | _RawVSColumn | None) -> _RawVSColumn | None:
        if column_spec is None or isinstance(column_spec, tuple):
            return column_spec

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

        if column_type == "join_column":
            raw_vs = _RawVSJoinColumnSpec(
                painter_spec=_get_painter_spec(column_spec),
                join_value=column_spec.join_value or "",
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

        raise ValueError

    def _get_painter_spec(
        column_spec: ColumnSpec,
    ) -> tuple[PainterName, PainterParameters]:
        return (column_spec.name, column_spec.parameters)

    def _from_vs_with_drilldown(
        value: _RawVSColumn,
    ) -> tuple[ColumnSpec | _RawVSColumn, ContextualLinkEntryConfig | None]:
        return _from_vs(value), _drilldown_link(value[1].get("link_spec"))

    def _to_vs_with_drilldown(
        value: tuple[ColumnSpec | _RawVSColumn, ContextualLinkEntryConfig | None] | None,
    ) -> _RawVSColumn | None:
        if value is None:
            return None
        column_spec, link = value
        if (raw := _to_vs(column_spec)) is not None and link is not None:
            raw[1]["link_spec"] = _drilldown_link_spec(link)
        return raw

    vs_column = (
        Transform(
            valuespec=vs_column,
            from_valuespec=_from_vs_with_drilldown,
            to_valuespec=_to_vs_with_drilldown,
        )
        if with_drilldown
        else Transform(
            valuespec=vs_column,
            from_valuespec=_from_vs,
            to_valuespec=_to_vs,
        )
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


def _drilldown_link_choices(
    ds_name: str, user_permissions: UserPermissions, tags: TagConfig
) -> list[CascadingDropdownChoice]:
    """Inherited drill-downs need host or service rows, custom ones a filter the row can value."""
    data_source = data_source_registry[ds_name]()
    object_infos = {info for info in ("host", "service") if info in data_source.infos}
    choices: list[CascadingDropdownChoice] = []
    if object_infos:
        choices += [
            (
                choice,
                f"{_DRILLDOWN_TITLES[choice]}:",
                DropdownChoice(
                    choices=_fillable_targets(
                        target_type,
                        _permitted_target_single_infos(target_type, user_permissions),
                        object_infos,
                        user_permissions,
                    ),
                    sorted=True,
                ),
            )
            for choice, target_type in _INHERITED_DRILLDOWN_TARGETS.items()
        ]
    choices += [
        (
            choice,
            f"{_DRILLDOWN_TITLES[choice]}:",
            _custom_drilldown_valuespec(target_type, filters, tags, user_permissions),
        )
        for choice, target_type in _CUSTOM_DRILLDOWN_TARGETS.items()
        if (filters := drilldown_filters(data_source, target_type))
    ]
    return choices


def _fillable_targets(
    target_type: ContextualLinkTargetType,
    target_single_infos: Mapping[VisualName, SingleInfos],
    infos: Set[InfoName],
    user_permissions: UserPermissions,
) -> DropdownChoiceEntries:
    fillable = {
        name for name, single_infos in target_single_infos.items() if set(single_infos) <= infos
    }
    if target_type == "views":
        return [choice for choice in view_choices() if choice[0] in fillable]
    dashboard_type = visual_type_registry["dashboards"]()
    return [
        choice
        for choice in dashboard_type.choices(dashboard_type.visuals(), user_permissions)
        if choice[0] in fillable
    ]


def _permitted_target_single_infos(
    target_type: ContextualLinkTargetType, user_permissions: UserPermissions
) -> dict[VisualName, SingleInfos]:
    if target_type == "views":
        return {name: view["single_infos"] for name, view in get_permitted_views().items()}
    dashboard_type = visual_type_registry["dashboards"]()
    return {
        name: dashboard["single_infos"]
        for name, dashboard in dashboard_type.permitted_visuals(
            dashboard_type.visuals(), user_permissions
        ).items()
    }


def _custom_drilldown_valuespec(
    target_type: ContextualLinkTargetType,
    filters: Sequence[FilterName],
    tags: TagConfig,
    user_permissions: UserPermissions,
) -> Dictionary:
    target_single_infos = _permitted_target_single_infos(target_type, user_permissions)
    targets = _fillable_targets(
        target_type, target_single_infos, filled_single_infos(filters), user_permissions
    )
    return Dictionary(
        elements=[
            ("target", DropdownChoice(title=_("Target page"), choices=targets, sorted=True)),
            (
                "filters",
                ListOf(
                    valuespec=CascadingDropdown(
                        choices=[
                            (
                                filter_name,
                                _filter_title(filter_name),
                                _filter_key_valuespec(filter_name, tags),
                            )
                            for filter_name in filters
                        ],
                        orientation="horizontal",
                    ),
                    title=_("Filters of the clicked element"),
                    add_label=_("Add filter"),
                    # Distinct from the default placeholder of the enclosing column list.
                    magic="@!!",
                    allow_empty=False,
                    empty_text=_("Please add at least one filter."),
                    validate=_validate_filters,
                ),
            ),
            (
                "include_context",
                Checkbox(label=_("Include dashboard and widget filters"), default_value=True),
            ),
            (
                "include_time_range",
                Checkbox(label=_("Include current time range"), default_value=True),
            ),
        ],
        optional_keys=[],
        validate=partial(_validate_named_target, target_single_infos),
    )


def _validate_named_target(
    target_single_infos: Mapping[VisualName, SingleInfos], value: DictionaryModel, varprefix: str
) -> None:
    if value["include_context"]:
        return
    filter_names = [raw if isinstance(raw, str) else raw[0] for raw in value["filters"]]
    if not set(target_single_infos.get(value["target"], ())) <= filled_single_infos(filter_names):
        raise MKUserError(
            f"{varprefix}_p_filters",
            _(
                "The target page shows a single object. Without the dashboard and widget filters,"
                " add a filter that identifies it."
            ),
        )


def _filter_title(filter_name: FilterName) -> str:
    """Prefixed with its info's title, as in the filter menu."""
    filter_ = filter_registry[filter_name]
    return f"{visual_info_registry[filter_.info]().title}: {str(filter_.title).strip()}"


class _LabelKeyAutocompleterConfig(AutocompleterConfig):
    def __init__(self, *, object_type: Literal["host", "service"]) -> None:
        super().__init__(ident="label_key")
        self._object_type = object_type

    @property
    @override
    def params(self) -> AutocompleterParams:
        return {"object_type": self._object_type, **super().params}


def _filter_key_valuespec(filter_name: FilterName, tags: TagConfig) -> ValueSpec | None:
    """The label key, tag group or auxiliary tag a filter needs, if any."""
    match filter_name:
        case "host_labels" | "service_labels":
            return AjaxDropdownChoice(
                title=_("Label key"),
                autocompleter=_LabelKeyAutocompleterConfig(
                    object_type="host" if filter_name == "host_labels" else "service"
                ),
                validate=_validate_label_key,
            )
        # The service tag filter resolves its group through the tag config, like the host one.
        case "host_tags" | "service_tags":
            return DropdownChoice(title=_("Tag group"), choices=tags.get_tag_group_choices())
        case "host_auxtags":
            return DropdownChoice(title=_("Auxiliary tag"), choices=tags.aux_tag_list.get_choices())
        case _:
            return None


def _validate_label_key(value: str | None, varprefix: str) -> None:
    if not value:
        raise MKUserError(varprefix, _("Please enter a label key."))
    # A label is parsed as key:value, so a colon would end the key early.
    if ":" in value:
        raise MKUserError(varprefix, _("A label key must not contain a colon."))


def _validate_filters(value: Sequence[object], varprefix: str) -> None:
    if len(set(value)) != len(value):
        raise MKUserError(
            varprefix,
            _("Add each filter only once, and a label or tag filter only once per key."),
        )
    aux_tag_field_count = sum(
        1 for variable in filter_registry["host_auxtags"].htmlvars if not variable.endswith("_neg")
    )
    aux_tags = [raw for raw in value if isinstance(raw, tuple) and raw[0] == "host_auxtags"]
    if len(aux_tags) > aux_tag_field_count:
        raise MKUserError(
            varprefix, _("Add up to %(count)d auxiliary tags.") % {"count": aux_tag_field_count}
        )


def view_editor_sorter_specs(
    ident: str,  # noqa: ARG001
    ds_name: str,
    painters: Sequence[ColumnSpec],
    painter_context: PainterContext,
) -> Dictionary:
    def _sorter_choices(
        ds_name: str, painters: Sequence[ColumnSpec]
    ) -> Iterator[DropdownChoiceEntry | CascadingDropdownChoice]:
        datasource: ABCDataSource = data_source_registry[ds_name]()
        unsupported_columns: list[ColumnName] = datasource.unsupported_columns
        registered_painters = all_painters(active_config.tags.tag_groups)

        for name, p in sorters_of_datasource(ds_name).items():
            if any(column in p.columns for column in unsupported_columns):
                continue
            # Sorters may provide a third element: That Dictionary will be displayed after the
            # sorter was choosen in the CascadingDropdown.
            if isinstance(p, ParameterizedSorter):
                yield (
                    name,
                    get_sorter_plugin_title_for_choices(p, registered_painters, painter_context),
                    p.vs_parameters(active_config, painters),
                )
            else:
                yield (
                    name,
                    get_sorter_plugin_title_for_choices(p, registered_painters, painter_context),
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

        painter_context = PainterContext(
            config=PainterConfig.from_config(ctx.config),
            request=ctx.request,
            painter_options=PainterOptions.get_instance(),
            theme=theme,
            url_renderer=RenderLink(ctx.request, response, display_options),
            user_permissions=ctx.user_permissions,
        )
        if api_request["painter_type"] == "painter":
            painters = painters_of_datasource(api_request["ds_name"])
        elif api_request["painter_type"] == "join_painter":
            painters = join_painters_of_datasource(api_request["ds_name"])
        else:
            raise NotImplementedError

        vs = CascadingDropdown(choices=_painter_choices_with_params(painters, painter_context))
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


def _link_with_offered_filters(
    link: ContextualLinkEntryConfig | None, data_source: ABCDataSource
) -> ContextualLinkEntryConfig | None:
    """Without the filters no longer offered, None if none is left: the editor can't show them."""
    if link is None or not link["filters"]:
        return link
    offered = drilldown_filters(data_source, link["location"][0])
    if not (filters := [f for f in link["filters"] if f["filter_id"] in offered]):
        return None
    return {**link, "filters": filters}


def render_view_config(
    view_spec: ViewSpec,
    general_properties: bool = True,
    *,
    allow_browser_reload: bool,
    config: Config,
    column_links: Mapping[int, ContextualLinkEntryConfig] | None = None,
) -> None:
    """Render the view editor's fields; with column_links, a column may also drill down."""
    value = _transform_view_to_valuespec_value(view_spec)

    # TODO: This and the modification of the view_spec should not be here. Find a better place
    ds_name: str = view_spec.get("datasource", request.get_ascii_input_mandatory("datasource", ""))
    if not ds_name:
        raise MKInternalError(_("No data source defined."))
    if ds_name not in data_source_registry:
        raise MKInternalError(_("The given data source is not supported."))

    value["datasource"] = ds_name

    if general_properties:
        view_editor_general_properties(
            ds_name, allow_browser_reload=allow_browser_reload
        ).render_input("view", value.get("view"))

    if _is_inventory_datasource(ds_name):
        view_inventory_join_macros(
            ds_name,
            [h.table.columns for h in inv_display_hints if isinstance(h.table, TableWithView)],
        ).render_input("macros", value.get("inventory_join_macros"))

    painter_context = PainterContext(
        config=PainterConfig.from_config(config),
        request=request,
        painter_options=PainterOptions.get_instance(),
        theme=theme,
        url_renderer=RenderLink(request, response, display_options),
        user_permissions=UserPermissions.from_config(config, all_permissions()),
    )
    if column_links is None:
        vs_columns = view_editor_column_spec("columns", ds_name, painter_context)
        vs_columns.render_input("columns", value["columns"])
    else:
        vs_columns = view_editor_column_spec(
            "columns", ds_name, painter_context, with_drilldown=True
        )
        data_source = data_source_registry[ds_name]()
        vs_columns.render_input(
            "columns",
            {
                "columns": [
                    (column, _link_with_offered_filters(column_links.get(index), data_source))
                    for index, column in enumerate(value["columns"]["columns"])
                ]
            },
        )

    vs_sorting = view_editor_sorter_specs(
        "sorting", ds_name, value["columns"]["columns"], painter_context
    )
    vs_sorting.render_input("sorting", value["sorting"])

    vs_grouping = view_editor_grouping_spec("grouping", ds_name, painter_context)
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
        view.update(attrs)  # type: ignore[typeddict-item]

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
def create_view_from_valuespec[T: (ViewSpec, ViewDashletConfig)](
    old_view: T, view: T, *, allow_browser_reload: bool, config: Config
) -> T:
    view, _column_links = _create_view_from_valuespec(
        old_view,
        view,
        allow_browser_reload=allow_browser_reload,
        config=config,
        with_drilldown=False,
    )
    return view


def create_embedded_view_from_valuespec(
    old_view: ViewSpec, view: ViewSpec, *, allow_browser_reload: bool, config: Config
) -> tuple[ViewSpec, dict[int, ContextualLinkEntryConfig]]:
    """Like create_view_from_valuespec, where a column may also drill down.

    The drill-down links come by painter index, beside the view they have no place in.
    """
    return _create_view_from_valuespec(
        old_view,
        view,
        allow_browser_reload=allow_browser_reload,
        config=config,
        with_drilldown=True,
    )


def _create_view_from_valuespec[T: (ViewSpec, ViewDashletConfig)](
    old_view: T, view: T, *, allow_browser_reload: bool, config: Config, with_drilldown: bool
) -> tuple[T, dict[int, ContextualLinkEntryConfig]]:
    ds_name = old_view.get("datasource") or request.get_ascii_input_mandatory("datasource")
    view["datasource"] = ds_name

    def update_view(ident: str, vs: Dictionary) -> None:
        attrs = vs.from_html_vars(ident)
        vs.validate_value(attrs, ident)
        _update_view_with_valuespec_values(view, ident, attrs)

    painter_context = PainterContext(
        config=PainterConfig.from_config(config),
        request=request,
        painter_options=PainterOptions.get_instance(),
        theme=theme,
        url_renderer=RenderLink(request, response, display_options),
        user_permissions=UserPermissions.from_config(config, all_permissions()),
    )
    update_view(
        "view", view_editor_general_properties(ds_name, allow_browser_reload=allow_browser_reload)
    )

    vs_columns = view_editor_column_spec(
        "columns", ds_name, painter_context, with_drilldown=with_drilldown
    )
    columns = vs_columns.from_html_vars("columns")
    vs_columns.validate_value(columns, "columns")
    column_links: dict[int, ContextualLinkEntryConfig] = {}
    if with_drilldown:
        column_links = {
            index: link
            for index, (_column, link) in enumerate(columns["columns"])
            if link is not None
        }
        columns = {"columns": [column for column, _link in columns["columns"]]}
    _update_view_with_valuespec_values(view, "columns", columns)

    update_view("grouping", view_editor_grouping_spec("grouping", ds_name, painter_context))
    update_view(
        "sorting", view_editor_sorter_specs("sorting", ds_name, view["painters"], painter_context)
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

    return view, column_links


def _painter_choices(
    painters: Mapping[str, InternalPainter], painter_context: PainterContext
) -> DropdownChoiceEntries:
    return [(c[0], c[1]) for c in _painter_choices_with_params(painters, painter_context)]


def _painter_choices_with_params(
    painters: Mapping[str, InternalPainter], painter_context: PainterContext
) -> list[CascadingDropdownChoice]:
    registered_painters = all_painters(active_config.tags.tag_groups)
    return sorted(
        (
            (
                name,
                _get_painter_plugin_title_for_choices(
                    painter, registered_painters, painter_context
                ),
                painter.parameters(painter_context),
            )
            for name, painter in painters.items()
        ),
        key=lambda x: x[1],
    )


def _get_painter_plugin_title_for_choices(
    plugin: InternalPainter,
    registered_painters: Mapping[str, InternalPainter],
    painter_context: PainterContext,
) -> str:
    dummy_cell = Cell(ColumnSpec(plugin.ident), None, registered_painters, painter_context, None)
    return (
        f"{_get_info_title(plugin)}: {plugin.list_title(dummy_cell, dummy_cell.painter_context())}"
    )


def get_sorter_plugin_title_for_choices(
    plugin: Sorter,
    registered_painters: Mapping[str, InternalPainter],
    painter_context: PainterContext,
) -> str:
    dummy_cell = Cell(ColumnSpec(plugin.ident), None, registered_painters, painter_context, None)
    title: str
    title = plugin.title(dummy_cell) if callable(plugin.title) else plugin.title
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


def _get_info_title(plugin: InternalPainter | Sorter) -> str:
    # TODO: Cleanup the special case for sites. How? Add an info for it?
    if plugin.columns == ["site"]:
        return _("Site")

    return "/".join(
        [
            str(visual_info_registry[info_name]().title_plural)
            for info_name in sorted(infos_needed_by_plugin(plugin))
        ]
    )


def infos_needed_by_plugin(
    plugin: InternalPainter | Sorter, add_columns: list | None = None
) -> set[str]:
    if add_columns is None:
        add_columns = []

    return {c.split("_", 1)[0] for c in plugin.columns if c != "site" and c not in add_columns}


def sorters_of_datasource(ds_name: str) -> Mapping[str, Sorter]:
    return _allowed_for_datasource(all_sorters(active_config.tags.tag_groups), ds_name)


def painters_of_datasource(ds_name: str) -> Mapping[str, InternalPainter]:
    return _allowed_for_datasource(all_painters(active_config.tags.tag_groups), ds_name)


def join_painters_of_datasource(ds_name: str) -> Mapping[str, InternalPainter]:
    datasource = data_source_registry[ds_name]()
    if datasource.join is None:
        return {}  # no joining with this datasource

    # Get the painters allowed for the join "source" and "target"
    painters = painters_of_datasource(ds_name)
    join_painters_unfiltered = _allowed_for_datasource(
        all_painters(active_config.tags.tag_groups), datasource.join[0]
    )

    # Filter out painters associated with the "join source" datasource
    join_painters: dict[str, InternalPainter] = {}
    for key, val in join_painters_unfiltered.items():
        if key not in painters:
            join_painters[key] = val

    return join_painters


@overload
def _allowed_for_datasource(
    collection: Mapping[str, InternalPainter], ds_name: str
) -> Mapping[str, InternalPainter]: ...


@overload
def _allowed_for_datasource(
    collection: Mapping[str, Sorter], ds_name: str
) -> Mapping[str, Sorter]: ...


# Filters a list of sorters or painters and decides which of
# those are available for a certain data source
def _allowed_for_datasource(
    collection: Mapping[str, InternalPainter] | Mapping[str, Sorter],
    ds_name: str,
) -> Mapping[str, Sorter | InternalPainter]:
    datasource: ABCDataSource = data_source_registry[ds_name]()
    infos_available: set[str] = set(datasource.infos)
    add_columns: list[ColumnName] = datasource.add_columns
    unsupported_columns: list[ColumnName] = datasource.unsupported_columns

    allowed: dict[str, Sorter | InternalPainter] = {}
    for name, plugin in collection.items():
        if any(column in plugin.columns for column in unsupported_columns):
            continue
        infos_needed = infos_needed_by_plugin(plugin, add_columns)
        if len(infos_needed.difference(infos_available)) == 0:
            allowed[name] = plugin

    return allowed


def _is_inventory_datasource(ds_name: str) -> bool:
    return ds_name.startswith("inv")
