#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Display a table view"""

import functools
from itertools import chain
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set
from typing import Tuple as _Tuple
from typing import Union

import livestatus
from livestatus import SiteId

import cmk.utils.version as cmk_version
from cmk.utils.cpu_tracking import CPUTracker, Snapshot
from cmk.utils.site import omd_site
from cmk.utils.structured_data import StructuredDataNode
from cmk.utils.type_defs import UserId

import cmk.gui.log as log
import cmk.gui.visuals as visuals
from cmk.gui.config import active_config
from cmk.gui.ctx_stack import g
from cmk.gui.data_source import data_source_registry
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKMissingDataError, MKUserError
from cmk.gui.exporter import exporter_registry
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.inventory import (
    get_short_inventory_filepath,
    load_filtered_and_merged_tree,
    LoadStructuredDataError,
)
from cmk.gui.logged_in import user
from cmk.gui.page_menu import make_external_link, PageMenuEntry, PageMenuTopic
from cmk.gui.painter_options import PainterOptions
from cmk.gui.plugins.views.utils import Cell, JoinCell, load_used_options
from cmk.gui.plugins.visuals.utils import Filter, get_livestatus_filter_headers
from cmk.gui.sorter import SorterEntry
from cmk.gui.type_defs import ColumnName, Row, Rows, SorterSpec, ViewSpec
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.view import View
from cmk.gui.view_renderer import ABCViewRenderer, GUIViewRenderer
from cmk.gui.view_store import get_all_views, get_permitted_views

from . import availability


def page_show_view() -> None:
    """Central entry point for the initial HTML page rendering of a view"""
    with CPUTracker() as page_view_tracker:
        view_name = request.get_ascii_input_mandatory("view_name", "")
        view_spec = visuals.get_permissioned_visual(
            view_name,
            request.get_validated_type_input(UserId, "owner"),
            "view",
            get_permitted_views(),
            get_all_views(),
        )
        _patch_view_context(view_spec)

        datasource = data_source_registry[view_spec["datasource"]]()
        context = visuals.active_context_from_request(datasource.infos, view_spec["context"])

        view = View(view_name, view_spec, context)
        view.row_limit = get_limit()

        view.only_sites = visuals.get_only_sites_from_context(context)

        view.user_sorters = get_user_sorters()
        view.want_checkboxes = get_want_checkboxes()

        # Gather the page context which is needed for the "add to visual" popup menu
        # to add e.g. views to dashboards or reports
        visuals.set_page_context(context)

        # Need to be loaded before processing the painter_options below.
        # TODO: Make this dependency explicit
        display_options.load_from_html(request, html)

        painter_options = PainterOptions.get_instance()
        painter_options.load(view.name)
        painter_options.update_from_url(
            view.name, load_used_options(view.spec, view.group_cells + view.row_cells)
        )
        process_view(GUIViewRenderer(view, show_buttons=True))

    _may_create_slow_view_log_entry(page_view_tracker, view)


def _may_create_slow_view_log_entry(page_view_tracker: CPUTracker, view: View) -> None:
    duration_threshold = active_config.slow_views_duration_threshold
    if page_view_tracker.duration.process.elapsed < duration_threshold:
        return

    logger = log.logger.getChild("slow-views")
    logger.debug(
        (
            "View name: %s, User: %s, Row limit: %s, Limit type: %s, URL variables: %s"
            ", View context: %s, Unfiltered rows: %s, Filtered rows: %s, Rows after limit: %s"
            ", Duration fetching rows: %s, Duration filtering rows: %s, Duration rendering view: %s"
            ", Rendering page exceeds %ss: %s"
        ),
        view.name,
        user.id,
        view.row_limit,
        # as in get_limit()
        request.var("limit", "soft"),
        ["%s=%s" % (k, v) for k, v in request.itervars() if k != "selection" and v != ""],
        view.context,
        view.process_tracking.amount_unfiltered_rows,
        view.process_tracking.amount_filtered_rows,
        view.process_tracking.amount_rows_after_limit,
        _format_snapshot_duration(view.process_tracking.duration_fetch_rows),
        _format_snapshot_duration(view.process_tracking.duration_filter_rows),
        _format_snapshot_duration(view.process_tracking.duration_view_render),
        duration_threshold,
        _format_snapshot_duration(page_view_tracker.duration),
    )


def _format_snapshot_duration(snapshot: Snapshot) -> str:
    return "%.2fs" % snapshot.process.elapsed


def _patch_view_context(view_spec: ViewSpec) -> None:
    """Apply some hacks that are needed because for some edge cases in the view / visuals / context
    imlementation"""
    # FIXME TODO HACK to make grouping single contextes possible on host/service infos
    # Is hopefully cleaned up soon.
    # This is also somehow connected to the datasource.link_filters hack hat has been created for
    # linking hosts / services with groups
    if view_spec["datasource"] in ["hosts", "services"]:
        if request.has_var("hostgroup") and not request.has_var("opthost_group"):
            request.set_var("opthost_group", request.get_str_input_mandatory("hostgroup"))
        if request.has_var("servicegroup") and not request.has_var("optservice_group"):
            request.set_var("optservice_group", request.get_str_input_mandatory("servicegroup"))

    # TODO: Another hack :( Just like the above one: When opening the view "ec_events_of_host",
    # which is of single context "host" using a host name of a unrelated event, the list of
    # events is always empty since the single context filter "host" is sending a "host_name = ..."
    # filter to livestatus which is not matching a "unrelated event". Instead the filter event_host
    # needs to be used.
    # But this may only be done for the unrelated events view. The "ec_events_of_monhost" view still
    # needs the filter. :-/
    # Another idea: We could change these views to non single context views, but then we would not
    # be able to show the buttons to other host related views, which is also bad. So better stick
    # with the current mode.
    if _is_ec_unrelated_host_view(view_spec):
        # Set the value for the event host filter
        if not request.has_var("event_host") and request.has_var("host"):
            request.set_var("event_host", request.get_str_input_mandatory("host"))


def process_view(view_renderer: ABCViewRenderer) -> None:
    """Rendering all kind of views"""
    if request.var("mode") == "availability":
        _process_availability_view(view_renderer)
    else:
        _process_regular_view(view_renderer)


def _process_regular_view(view_renderer: ABCViewRenderer) -> None:
    all_active_filters = _get_all_active_filters(view_renderer.view)
    with livestatus.intercept_queries() as queries:
        unfiltered_amount_of_rows, rows = _get_view_rows(
            view_renderer.view,
            all_active_filters,
            only_count=False,
        )

    if html.output_format != "html":
        _export_view(view_renderer.view, rows)
        return

    _add_rest_api_menu_entries(view_renderer, queries)
    _show_view(view_renderer, unfiltered_amount_of_rows, rows)


def _add_rest_api_menu_entries(view_renderer, queries: List[str]):  # type:ignore[no-untyped-def]
    from cmk.utils.livestatus_helpers.queries import Query

    from cmk.gui.plugins.openapi.utils import create_url

    entries: List[PageMenuEntry] = []
    for text_query in set(queries):
        if "\nStats:" in text_query:
            continue
        try:
            query = Query.from_string(text_query)
        except ValueError:
            continue
        try:
            url = create_url(omd_site(), query)
        except ValueError:
            continue
        table = query.table.__tablename__
        entries.append(
            PageMenuEntry(
                title=_("Query %s resource") % (table,),
                icon_name="filter",
                item=make_external_link(url),
            )
        )
    view_renderer.append_menu_topic(
        dropdown="export",
        topic=PageMenuTopic(
            title="REST API",
            entries=entries,
        ),
    )


def _process_availability_view(view_renderer: ABCViewRenderer) -> None:
    view = view_renderer.view
    all_active_filters = _get_all_active_filters(view)

    # Fork to availability view. We just need the filter headers, since we do not query the normal
    # hosts and service table, but "statehist". This is *not* true for BI availability, though (see
    # later)
    if "aggr" not in view.datasource.infos or request.var("timeline_aggr"):
        filterheaders = "".join(get_livestatus_filter_headers(view.context, all_active_filters))
        # all 'amount_*', 'duration_fetch_rows' and 'duration_filter_rows' will be set in:
        show_view_func = functools.partial(
            availability.show_availability_page,
            view=view,
            filterheaders=filterheaders,
        )

    else:
        _unfiltered_amount_of_rows, rows = _get_view_rows(
            view, all_active_filters, only_count=False
        )
        # 'amount_rows_after_limit' will be set in:
        show_view_func = functools.partial(
            availability.show_bi_availability,
            view=view,
            aggr_rows=rows,
        )

    with CPUTracker() as view_render_tracker:
        show_view_func()
    view.process_tracking.duration_view_render = view_render_tracker.duration


# TODO: Use livestatus Stats: instead of fetching rows?
def get_row_count(view: View) -> int:
    """Returns the number of rows shown by a view"""

    all_active_filters = _get_all_active_filters(view)
    # Check that all needed information for configured single contexts are available
    if view.missing_single_infos:
        raise MKUserError(
            None,
            _(
                "Missing context information: %s. You can either add this as a fixed "
                "setting, or call the with the missing HTTP variables."
            )
            % (", ".join(view.missing_single_infos)),
        )

    _unfiltered_amount_of_rows, rows = _get_view_rows(view, all_active_filters, only_count=True)
    return len(rows)


def _get_view_rows(
    view: View, all_active_filters: List[Filter], only_count: bool = False
) -> _Tuple[int, Rows]:
    with CPUTracker() as fetch_rows_tracker:
        rows, unfiltered_amount_of_rows = _fetch_view_rows(view, all_active_filters, only_count)

    # Sorting - use view sorters and URL supplied sorters
    _sort_data(view, rows, view.sorters)

    with CPUTracker() as filter_rows_tracker:
        # Apply non-Livestatus filters
        for filter_ in all_active_filters:
            try:
                rows = filter_.filter_table(view.context, rows)
            except MKMissingDataError as e:
                view.add_warning_message(str(e))

    view.process_tracking.amount_unfiltered_rows = unfiltered_amount_of_rows
    view.process_tracking.amount_filtered_rows = len(rows)
    view.process_tracking.duration_fetch_rows = fetch_rows_tracker.duration
    view.process_tracking.duration_filter_rows = filter_rows_tracker.duration

    return unfiltered_amount_of_rows, rows


def _fetch_view_rows(
    view: View, all_active_filters: List[Filter], only_count: bool
) -> _Tuple[Rows, int]:
    """Fetches the view rows from livestatus

    Besides gathering the information from livestatus it also joins the rows with other information.
    For the moment this is:

    - Livestatus table joining (e.g. Adding service row info to host rows (For join painters))
    - Add HW/SW inventory data when needed
    - Add SLA data when needed
    """
    filterheaders = "".join(get_livestatus_filter_headers(view.context, all_active_filters))
    headers = filterheaders + view.spec.get("add_headers", "")

    # Fetch data. Some views show data only after pressing [Search]
    if (
        only_count
        or (not view.spec.get("mustsearch"))
        or request.var("filled_in") in ["filter", "actions", "confirm", "painteroptions"]
    ):
        columns = _get_needed_regular_columns(
            all_active_filters,
            view,
        )
        # We test for limit here and not inside view.row_limit, because view.row_limit is used
        # for rendering limits.
        query_row_limit = None if view.datasource.ignore_limit else view.row_limit
        row_data: Union[Rows, _Tuple[Rows, int]] = view.datasource.table.query(
            view.datasource,
            view.row_cells,
            columns,
            view.context,
            headers,
            view.only_sites,
            query_row_limit,
            all_active_filters,
        )

        if isinstance(row_data, tuple):
            rows, unfiltered_amount_of_rows = row_data
        else:
            rows = row_data
            unfiltered_amount_of_rows = len(row_data)

        # Now add join information, if there are join columns
        if view.join_cells:
            _do_table_join(view, rows, filterheaders, view.sorters)

        # If any painter, sorter or filter needs the information about the host's
        # inventory, then we load it and attach it as column "host_inventory"
        if _is_inventory_data_needed(view, all_active_filters):
            _add_inventory_data(rows)

        if not cmk_version.is_raw_edition():
            _add_sla_data(view, rows)

        return rows, unfiltered_amount_of_rows
    return [], 0


def _show_view(view_renderer: ABCViewRenderer, unfiltered_amount_of_rows: int, rows: Rows) -> None:
    view = view_renderer.view

    # Load from hard painter options > view > hard coded default
    painter_options = PainterOptions.get_instance()
    num_columns = painter_options.get("num_columns", view.spec.get("num_columns", 1))
    browser_reload = painter_options.get("refresh", view.spec.get("browser_reload", None))

    force_checkboxes = view.spec.get("force_checkboxes", False)
    show_checkboxes = force_checkboxes or request.var("show_checkboxes", "0") == "1"

    show_filters = visuals.filters_of_visual(
        view.spec, view.datasource.infos, link_filters=view.datasource.link_filters
    )

    # Set browser reload
    if browser_reload and display_options.enabled(display_options.R):
        html.browser_reload = browser_reload

    if active_config.enable_sounds and active_config.sounds:
        for row in rows:
            save_state_for_playing_alarm_sounds(row)

    # Until now no single byte of HTML code has been output.
    # Now let's render the view
    with CPUTracker() as view_render_tracker:
        view_renderer.render(
            rows, show_checkboxes, num_columns, show_filters, unfiltered_amount_of_rows
        )
    view.process_tracking.duration_view_render = view_render_tracker.duration


def _get_all_active_filters(view: View) -> "List[Filter]":
    # Always allow the users to specify all allowed filters using the URL
    use_filters = list(visuals.filters_allowed_for_infos(view.datasource.infos).values())

    # See process_view() for more information about this hack
    if _is_ec_unrelated_host_view(view.spec):
        # Remove the original host name filter
        use_filters = [f for f in use_filters if f.ident != "host"]

    use_filters = [f for f in use_filters if f.available()]

    for filt in use_filters:
        # TODO: Clean this up! E.g. make the Filter class implement a default method
        if hasattr(filt, "derived_columns"):
            filt.derived_columns(view.row_cells)  # type: ignore[attr-defined]

    return use_filters


def _export_view(view: View, rows: Rows) -> None:
    """Shows the views data in one of the supported machine readable formats"""
    layout = view.layout
    if html.output_format == "csv" and layout.has_individual_csv_export:
        layout.csv_export(rows, view.spec, view.group_cells, view.row_cells)
        return

    exporter = exporter_registry.get(html.output_format)
    if not exporter:
        raise MKUserError(
            "output_format", _("Output format '%s' not supported") % html.output_format
        )

    exporter.handler(view, rows)


def _is_ec_unrelated_host_view(view_spec: ViewSpec) -> bool:
    # The "name" is not set in view report elements
    return (
        view_spec["datasource"] in ["mkeventd_events", "mkeventd_history"]
        and "host" in view_spec["single_infos"]
        and view_spec.get("name") != "ec_events_of_monhost"
    )


def _get_needed_regular_columns(
    all_active_filters: Iterable[Filter],
    view: View,
) -> List[ColumnName]:
    """Compute the list of all columns we need to query via Livestatus

    Those are: (1) columns used by the sorters in use, (2) columns use by column- and group-painters
    in use and - note - (3) columns used to satisfy external references (filters) of views we link
    to. The last bit is the trickiest. Also compute this list of view options use by the painters
    """
    # BI availability needs aggr_tree
    # TODO: wtf? a full reset of the list? Move this far away to a special place!
    if request.var("mode") == "availability" and "aggr" in view.datasource.infos:
        return ["aggr_tree", "aggr_name", "aggr_group"]

    columns = columns_of_cells(view.group_cells + view.row_cells)

    # Columns needed for sorters
    # TODO: Move sorter parsing and logic to something like Cells()
    for entry in view.sorters:
        columns.update(entry.sorter.columns)

    # Add key columns, needed for executing commands
    columns.update(view.datasource.keys)

    # Add idkey columns, needed for identifying the row
    columns.update(view.datasource.id_keys)

    # Add columns requested by filters for post-livestatus filtering
    columns.update(
        chain.from_iterable(
            filter.columns_for_filter_table(view.context) for filter in all_active_filters
        )
    )

    # Remove (implicit) site column
    try:
        columns.remove("site")
    except KeyError:
        pass

    # In the moment the context buttons are shown, the link_from mechanism is used
    # to decide to which other views/dashboards the context buttons should link to.
    # This decision is partially made on attributes of the object currently shown.
    # E.g. on a "single host" page the host labels are needed for the decision.
    # This is currently realized explicitly until we need a more flexible mechanism.
    if display_options.enabled(display_options.B) and "host" in view.datasource.infos:
        columns.add("host_labels")

    return list(columns)


def _get_needed_join_columns(
    join_cells: List[JoinCell], sorters: List[SorterEntry]
) -> List[ColumnName]:
    join_columns = columns_of_cells(join_cells)

    # Columns needed for sorters
    # TODO: Move sorter parsing and logic to something like Cells()
    for entry in sorters:
        join_columns.update(entry.sorter.columns)

    # Remove (implicit) site column
    try:
        join_columns.remove("site")
    except KeyError:
        pass

    return list(join_columns)


def _is_inventory_data_needed(view: View, all_active_filters: "List[Filter]") -> bool:

    group_cells: List[Cell] = view.group_cells
    cells: List[Cell] = view.row_cells
    sorters: List[SorterEntry] = view.sorters

    for cell in cells:
        if cell.has_tooltip():
            if cell.tooltip_painter_name().startswith("inv_"):
                return True

    for entry in sorters:
        if entry.sorter.load_inv:
            return True

    for cell in group_cells + cells:
        if cell.painter().load_inv:
            return True

    for filt in all_active_filters:
        if filt.need_inventory(view.context.get(filt.ident, {})):
            return True

    return False


def _add_inventory_data(rows: Rows) -> None:
    corrupted_inventory_files = []
    for row in rows:
        if "host_name" not in row:
            continue

        try:
            row["host_inventory"] = load_filtered_and_merged_tree(row)
        except LoadStructuredDataError:
            # The inventory row may be joined with other rows (perf-o-meter, ...).
            # Therefore we initialize the corrupt inventory tree with an empty tree
            # in order to display all other rows.
            row["host_inventory"] = StructuredDataNode()
            corrupted_inventory_files.append(str(get_short_inventory_filepath(row["host_name"])))

            if corrupted_inventory_files:
                user_errors.add(
                    MKUserError(
                        "load_structured_data_tree",
                        _(
                            "Cannot load HW/SW inventory trees %s. Please remove the corrupted files."
                        )
                        % ", ".join(sorted(corrupted_inventory_files)),
                    )
                )


def _add_sla_data(view: View, rows: Rows) -> None:
    import cmk.gui.cee.sla as sla  # pylint: disable=no-name-in-module,import-outside-toplevel

    sla_params = []
    for cell in view.row_cells:
        if cell.painter_name() in ["sla_specific", "sla_fixed"]:
            sla_params.append(cell.painter_parameters())
    if sla_params:
        sla_configurations_container = sla.SLAConfigurationsContainerFactory.create_from_cells(
            sla_params, rows
        )
        sla.SLAProcessor(sla_configurations_container).add_sla_data_to_rows(rows)


def columns_of_cells(cells: Sequence[Cell]) -> Set[ColumnName]:
    columns: Set[ColumnName] = set()
    for cell in cells:
        columns.update(cell.needed_columns())
    return columns


JoinMasterKey = _Tuple[SiteId, str]
JoinSlaveKey = str


def _do_table_join(
    view: View, master_rows: Rows, master_filters: str, sorters: List[SorterEntry]
) -> None:
    assert view.datasource.join is not None
    join_table, join_master_column = view.datasource.join
    slave_ds = data_source_registry[join_table]()
    assert slave_ds.join_key is not None
    join_slave_column = slave_ds.join_key
    join_cells = view.join_cells
    join_columns = _get_needed_join_columns(join_cells, sorters)

    # Create additional filters
    join_filters = []
    for cell in join_cells:
        join_filters.append(cell.livestatus_filter(join_slave_column))

    join_filters.append("Or: %d" % len(join_filters))
    headers = "%s%s\n" % (master_filters, "\n".join(join_filters))
    row_data = slave_ds.table.query(
        view.datasource,
        view.row_cells,
        columns=list(set([join_master_column, join_slave_column] + join_columns)),
        context=view.context,
        headers=headers,
        only_sites=view.only_sites,
        limit=None,
        all_active_filters=[],
    )

    if isinstance(row_data, tuple):
        rows, _unfiltered_amount_of_rows = row_data
    else:
        rows = row_data

    per_master_entry: Dict[JoinMasterKey, Dict[JoinSlaveKey, Row]] = {}
    current_key: Optional[JoinMasterKey] = None
    current_entry: Optional[Dict[JoinSlaveKey, Row]] = None
    for row in rows:
        master_key = (row["site"], row[join_master_column])
        if master_key != current_key:
            current_key = master_key
            current_entry = {}
            per_master_entry[current_key] = current_entry
        assert current_entry is not None
        current_entry[row[join_slave_column]] = row

    # Add this information into master table in artificial column "JOIN"
    for row in master_rows:
        key = (row["site"], row[join_master_column])
        joininfo = per_master_entry.get(key, {})
        row["JOIN"] = joininfo


def save_state_for_playing_alarm_sounds(row: "Row") -> None:
    if not active_config.enable_sounds or not active_config.sounds:
        return

    # TODO: Move this to a generic place. What about -1?
    host_state_map = {0: "up", 1: "down", 2: "unreachable"}
    service_state_map = {0: "up", 1: "warning", 2: "critical", 3: "unknown"}

    for state_map, state in [
        (host_state_map, row.get("host_hard_state", row.get("host_state"))),
        (service_state_map, row.get("service_last_hard_state", row.get("service_state"))),
    ]:
        if state is None:
            continue

        try:
            state_name = state_map[int(state)]
        except KeyError:
            continue

        g.setdefault("alarm_sound_states", set()).add(state_name)


def _parse_url_sorters(sort: Optional[str]) -> list[SorterSpec]:
    sorters: list[SorterSpec] = []
    if not sort:
        return sorters
    for s in sort.split(","):
        if "~" in s:
            sorter, join_index = s.split("~", 1)
        else:
            sorter, join_index = s, None

        negate = False
        if sorter.startswith("-"):
            negate = True
            sorter = sorter[1:]

        sorters.append(SorterSpec(sorter, negate, join_index))
    return sorters


def get_user_sorters() -> List[SorterSpec]:
    """Returns a list of optionally set sort parameters from HTTP request"""
    return _parse_url_sorters(request.var("sort"))


def get_want_checkboxes() -> bool:
    """Whether or not the user requested checkboxes to be shown"""
    return request.get_integer_input_mandatory("show_checkboxes", 0) == 1


def get_limit() -> Optional[int]:
    """How many data rows may the user query?"""
    limitvar = request.var("limit", "soft")
    if limitvar == "hard" and user.may("general.ignore_soft_limit"):
        return active_config.hard_query_limit
    if limitvar == "none" and user.may("general.ignore_hard_limit"):
        return None
    return active_config.soft_query_limit


def _link_to_folder_by_path(path: str) -> str:
    """Return an URL to a certain WATO folder when we just know its path"""
    return makeuri_contextless(
        request,
        [("mode", "folder"), ("folder", path)],
        filename="wato.py",
    )


def _sort_data(view: View, data: "Rows", sorters: List[SorterEntry]) -> None:
    """Sort data according to list of sorters."""
    if not sorters:
        return

    # Handle case where join columns are not present for all rows
    def safe_compare(compfunc: Callable[[Row, Row], int], row1: Row, row2: Row) -> int:
        if row1 is None and row2 is None:
            return 0
        if row1 is None:
            return -1
        if row2 is None:
            return 1
        return compfunc(row1, row2)

    def multisort(e1: Row, e2: Row) -> int:
        for entry in sorters:
            neg = -1 if entry.negate else 1

            if entry.join_key:  # Sorter for join column, use JOIN info
                c = neg * safe_compare(
                    entry.sorter.cmp, e1["JOIN"].get(entry.join_key), e2["JOIN"].get(entry.join_key)
                )
            else:
                c = neg * entry.sorter.cmp(e1, e2)

            if c != 0:
                return c
        return 0  # equal

    data.sort(key=functools.cmp_to_key(multisort))
