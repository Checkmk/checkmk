#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"

import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from fnmatch import fnmatch
from functools import partial
from pathlib import Path
from typing import Literal, override

import cmk.ccc.version as cmk_version
import cmk.utils.paths
from cmk.discover_plugins import discover_families, PluginGroup
from cmk.graphing_engine import MetricName
from cmk.gui import sites
from cmk.gui.color import render_color_icon
from cmk.gui.config import Config
from cmk.gui.graphing import (
    evaluated_metrics,
    EvaluatedMetric,
    get_metric_spec,
    get_temperature_unit,
    metrics_from_api,
    registered_metric_ids_and_titles,
    registered_metrics,
    registered_translations,
    RegisteredMetric,
)
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import HTMLGenerator
from cmk.gui.http import Request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.painter_options import (
    paint_age,
    paint_age_or_never,
    PainterOption,
    PainterOptionRegistry,
    PainterOptions,
)
from cmk.gui.theme import Theme
from cmk.gui.type_defs import PainterParameters, Row, VisualLinkSpec
from cmk.gui.utils.host_relations import RELATIONS_CUSTOM_VARIABLE
from cmk.gui.utils.popups import MethodAjax
from cmk.gui.utils.temperature_unit import TemperatureUnit
from cmk.gui.valuespec import (
    Checkbox,
    DateFormat,
    Dictionary,
    DictionaryElements,
    DropdownChoice,
    DropdownChoiceEntries,
    Integer,
    ListChoice,
    ListChoiceChoices,
    TextInput,
    ValueSpec,
)
from cmk.gui.view_utils import (
    CellSpec,
    CSSClass,
    determine_must_escape,
    format_plugin_output,
    get_labels,
    render_labels,
    render_tag_groups,
    replace_action_url_macros,
)
from cmk.gui.visual_link import render_link_to_view
from cmk.livestatus_client import SiteConfigurations
from cmk.ruleset_matcher.labels import Labels
from cmk.ruleset_matcher.tags import TagConfig
from cmk.utils import man_pages
from cmk.utils.render import approx_age
from cmk.utils.statename import short_host_state_name, short_service_state_name
from cmk.web.utils import escaping
from cmk.web.utils.html import HTML
from cmk.web.utils.icons import IconNames, StaticIcon
from cmk.web.utils.speaklater import LazyString
from cmk.web.utils.urls import HTTPVariable

from .base import Cell, InternalPainter, PainterConfig, PainterContext
from .helpers import (
    format_labels_for_csv_export,
    get_label_sources,
    get_perfdata_nth_value,
    get_tag_groups,
    is_stale,
    paint_host_list,
    paint_nagiosflag,
    paint_stalified,
    render_cache_info,
    RenderLink,
    tag_choices_for_group,
)
from .registry import PainterRegistry


def register(
    painter_option_registry: PainterOptionRegistry, painter_registry: PainterRegistry
) -> None:
    painter_option_registry.register(PainterOptionTimestampFormat())
    painter_option_registry.register(PainterOptionTimestampDate())
    painter_option_registry.register(PainterOptionMatrixOmitUniform())
    painter_option_registry.register(PainterOptionShowInternalGraphAndMetricIds())
    painter_registry.register(make_site_icon_painter())
    painter_registry.register(make_sitename_plain_painter())
    painter_registry.register(make_sitealias_painter())
    painter_registry.register(make_service_state_painter())
    painter_registry.register(make_svc_plugin_output_painter())
    painter_registry.register(make_svc_long_plugin_output_painter())
    painter_registry.register(make_svc_perf_data_painter())
    painter_registry.register(make_svc_metrics_painter())
    for num in range(1, 11):
        painter_registry.register(make_svc_perf_val_painter(num))
    painter_registry.register(make_svc_check_command_painter())
    painter_registry.register(make_svc_check_command_expanded_painter())
    painter_registry.register(make_svc_notes_url_painter())
    painter_registry.register(make_svc_contacts_painter())
    painter_registry.register(make_svc_contact_groups_painter())
    painter_registry.register(make_service_description_painter())
    painter_registry.register(make_service_display_name_painter())
    painter_registry.register(make_svc_state_age_painter())
    painter_registry.register(make_svc_check_age_painter())
    painter_registry.register(make_svc_check_cache_info_painter())
    painter_registry.register(make_svc_next_check_painter())
    painter_registry.register(make_svc_last_time_ok_painter())
    painter_registry.register(make_svc_next_notification_painter())
    painter_registry.register(make_svc_notification_postponement_reason_painter())
    painter_registry.register(make_svc_last_notification_painter())
    painter_registry.register(make_svc_notification_number_painter())
    painter_registry.register(make_svc_check_latency_painter())
    painter_registry.register(make_svc_check_duration_painter())
    painter_registry.register(make_svc_attempt_painter())
    painter_registry.register(make_svc_normal_interval_painter())
    painter_registry.register(make_svc_retry_interval_painter())
    painter_registry.register(make_svc_check_interval_painter())
    painter_registry.register(make_svc_check_type_painter())
    painter_registry.register(make_svc_in_downtime_painter())
    painter_registry.register(make_svc_in_notifper_painter())
    painter_registry.register(make_svc_notifper_painter())
    painter_registry.register(make_svc_check_period_painter())
    painter_registry.register(make_svc_flapping_painter())
    painter_registry.register(make_svc_notifications_enabled_painter())
    painter_registry.register(make_svc_is_active_painter())
    painter_registry.register(make_svc_group_memberlist_painter())
    painter_registry.register(make_check_manpage_painter())
    painter_registry.register(make_svc_comments_painter())
    painter_registry.register(make_svc_acknowledged_painter())
    painter_registry.register(make_svc_custom_notes_painter())
    painter_registry.register(make_svc_staleness_painter())
    painter_registry.register(make_svc_is_stale_painter())
    painter_registry.register(make_svc_custom_vars_painter())
    painter_registry.register(make_service_custom_variable_painter())
    painter_registry.register(make_host_custom_variable_painter())
    painter_registry.register(make_host_state_painter())
    painter_registry.register(make_host_state_onechar_painter())
    painter_registry.register(make_host_plugin_output_painter())
    painter_registry.register(make_host_perf_data_painter())
    painter_registry.register(make_host_check_command_painter())
    painter_registry.register(make_host_check_command_expanded_painter())
    painter_registry.register(make_host_notes_url_painter())
    painter_registry.register(make_host_state_age_painter())
    painter_registry.register(make_host_check_age_painter())
    painter_registry.register(make_host_next_check_painter())
    painter_registry.register(make_host_next_notification_painter())
    painter_registry.register(make_host_notification_postponement_reason_painter())
    painter_registry.register(make_host_last_notification_painter())
    painter_registry.register(make_host_check_latency_painter())
    painter_registry.register(make_host_check_duration_painter())
    painter_registry.register(make_host_attempt_painter())
    painter_registry.register(make_host_normal_interval_painter())
    painter_registry.register(make_host_retry_interval_painter())
    painter_registry.register(make_host_check_interval_painter())
    painter_registry.register(make_host_check_type_painter())
    painter_registry.register(make_host_in_notifper_painter())
    painter_registry.register(make_host_notifper_painter())
    painter_registry.register(make_host_notification_number_painter())
    painter_registry.register(make_host_flapping_painter())
    painter_registry.register(make_host_is_active_painter())
    painter_registry.register(make_host_notifications_enabled_painter())
    painter_registry.register(make_host_black_painter())
    painter_registry.register(make_host_with_state_painter())
    painter_registry.register(make_host_painter())
    painter_registry.register(make_alias_painter())
    painter_registry.register(make_host_address_painter())
    painter_registry.register(make_host_ipv4_address_painter())
    painter_registry.register(make_host_ipv6_address_painter())
    painter_registry.register(make_host_addresses_painter())
    painter_registry.register(make_host_addresses_additional_painter())
    painter_registry.register(make_host_address_family_painter())
    painter_registry.register(make_host_address_families_painter())
    painter_registry.register(make_num_services_painter())
    painter_registry.register(make_num_services_ok_painter())
    painter_registry.register(make_num_problems_painter())
    painter_registry.register(make_num_services_warn_painter())
    painter_registry.register(make_num_services_crit_painter())
    painter_registry.register(make_num_services_unknown_painter())
    painter_registry.register(make_num_services_pending_painter())
    painter_registry.register(make_host_services_painter())
    painter_registry.register(make_host_parents_painter())
    painter_registry.register(make_host_childs_painter())
    painter_registry.register(make_host_group_memberlist_painter())
    painter_registry.register(make_host_contacts_painter())
    painter_registry.register(make_host_contact_groups_painter())
    painter_registry.register(make_host_custom_notes_painter())
    painter_registry.register(make_host_comments_painter())
    painter_registry.register(make_host_in_downtime_painter())
    painter_registry.register(make_host_acknowledged_painter())
    painter_registry.register(make_host_staleness_painter())
    painter_registry.register(make_host_is_stale_painter())
    painter_registry.register(make_host_custom_vars_painter())
    painter_registry.register(make_service_discovery_state_painter())
    painter_registry.register(make_service_discovery_check_painter())
    painter_registry.register(make_service_discovery_service_painter())
    painter_registry.register(make_hostgroup_hosts_painter())
    painter_registry.register(make_hg_num_services_painter())
    painter_registry.register(make_hg_num_services_ok_painter())
    painter_registry.register(make_hg_num_services_warn_painter())
    painter_registry.register(make_hg_num_services_crit_painter())
    painter_registry.register(make_hg_num_services_unknown_painter())
    painter_registry.register(make_hg_num_services_pending_painter())
    painter_registry.register(make_hg_num_hosts_up_painter())
    painter_registry.register(make_hg_num_hosts_down_painter())
    painter_registry.register(make_hg_num_hosts_unreach_painter())
    painter_registry.register(make_hg_num_hosts_pending_painter())
    painter_registry.register(make_hg_name_painter())
    painter_registry.register(make_hg_alias_painter())
    painter_registry.register(make_sg_services_painter())
    painter_registry.register(make_sg_num_services_painter())
    painter_registry.register(make_sg_num_services_ok_painter())
    painter_registry.register(make_sg_num_services_warn_painter())
    painter_registry.register(make_sg_num_services_crit_painter())
    painter_registry.register(make_sg_num_services_unknown_painter())
    painter_registry.register(make_sg_num_services_pending_painter())
    painter_registry.register(make_sg_name_painter())
    painter_registry.register(make_sg_alias_painter())
    painter_registry.register(make_comment_id_painter())
    painter_registry.register(make_comment_author_painter())
    painter_registry.register(make_comment_comment_painter())
    painter_registry.register(make_comment_what_painter())
    painter_registry.register(make_comment_time_painter())
    painter_registry.register(make_comment_expires_painter())
    painter_registry.register(make_comment_entry_type_painter())
    painter_registry.register(make_downtime_id_painter())
    painter_registry.register(make_downtime_author_painter())
    painter_registry.register(make_downtime_comment_painter())
    painter_registry.register(make_downtime_fixed_painter())
    painter_registry.register(make_downtime_origin_painter())
    painter_registry.register(make_downtime_what_painter())
    painter_registry.register(make_downtime_type_painter())
    painter_registry.register(make_downtime_entry_time_painter())
    painter_registry.register(make_downtime_start_time_painter())
    painter_registry.register(make_downtime_end_time_painter())
    painter_registry.register(make_downtime_duration_painter())
    painter_registry.register(make_log_details_history_painter())
    painter_registry.register(make_log_message_painter())
    painter_registry.register(make_log_plugin_output_painter())
    painter_registry.register(make_log_what_painter())
    painter_registry.register(make_log_attempt_painter())
    painter_registry.register(make_log_state_type_painter())
    painter_registry.register(make_log_state_info_painter())
    painter_registry.register(make_log_type_painter())
    painter_registry.register(make_log_contact_name_painter())
    painter_registry.register(make_log_command_painter())
    painter_registry.register(make_log_icon_painter())
    painter_registry.register(make_log_options_painter())
    painter_registry.register(make_log_comment_painter())
    painter_registry.register(make_log_time_painter())
    painter_registry.register(make_log_lineno_painter())
    painter_registry.register(make_log_date_painter())
    painter_registry.register(make_log_state_painter())
    painter_registry.register(make_alert_stats_ok_painter())
    painter_registry.register(make_alert_stats_warn_painter())
    painter_registry.register(make_alert_stats_crit_painter())
    painter_registry.register(make_alert_stats_unknown_painter())
    painter_registry.register(make_alert_stats_problem_painter())
    painter_registry.register(make_host_tags_painter())
    painter_registry.register(make_host_tags_with_titles_painter())
    painter_registry.register(make_service_tags_painter())
    painter_registry.register(make_service_tags_with_titles_painter())
    painter_registry.register(make_host_labels_painter())
    painter_registry.register(make_service_labels_painter())
    painter_registry.register(make_host_docker_node_painter())
    painter_registry.register(make_host_specific_metric_painter())
    painter_registry.register(make_service_specific_metric_painter())
    painter_registry.register(make_host_kubernetes_cluster_painter())
    painter_registry.register(make_host_kubernetes_namespace_painter())
    painter_registry.register(make_host_kubernetes_deployment_painter())
    painter_registry.register(make_host_kubernetes_daemonset_painter())
    painter_registry.register(make_host_kubernetes_statefulset_painter())
    painter_registry.register(make_host_kubernetes_node_painter())


#   .--Painter Options-----------------------------------------------------.
#   |                   ____       _       _                               |
#   |                  |  _ \ __ _(_)_ __ | |_ ___ _ __                    |
#   |                  | |_) / _` | | '_ \| __/ _ \ '__|                   |
#   |                  |  __/ (_| | | | | | ||  __/ |                      |
#   |                  |_|   \__,_|_|_| |_|\__\___|_|                      |
#   |                                                                      |
#   |                   ___        _   _                                   |
#   |                  / _ \ _ __ | |_(_) ___  _ __  ___                   |
#   |                 | | | | '_ \| __| |/ _ \| '_ \/ __|                  |
#   |                 | |_| | |_) | |_| | (_) | | | \__ \                  |
#   |                  \___/| .__/ \__|_|\___/|_| |_|___/                  |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   | Painter options influence how painters render their data. Painter    |
#   | options are stored together with "refresh" and "columns" as "View    |
#   | options".                                                            |
#   '----------------------------------------------------------------------'


class PainterOptionShowInternalGraphAndMetricIds(PainterOption):
    def __init__(self) -> None:
        super().__init__(
            ident="show_internal_graph_and_metric_ids",
            valuespec=Checkbox(
                title=_("Show internal graph and metric IDs"),
                default_value=False,
            ),
        )


class PainterOptionTimestampFormat(PainterOption):
    def __init__(self) -> None:
        super().__init__(ident="ts_format")

    @override
    def valuespec(self, config: Config) -> ValueSpec:
        return DropdownChoice(
            title=_("Timestamp format"),
            default_value=config.default_ts_format,
            encode_value=False,
            choices=[
                ("mixed", _("Mixed")),
                ("abs", _("Absolute")),
                ("rel", _("Relative")),
                ("both", _("Both")),
                ("epoch", _("Unix timestamp (epoch)")),
            ],
        )


class PainterOptionTimestampDate(PainterOption):
    def __init__(self) -> None:
        super().__init__(ident="ts_date", valuespec=DateFormat())


class PainterOptionMatrixOmitUniform(PainterOption):
    def __init__(self) -> None:
        super().__init__(
            ident="matrix_omit_uniform",
            valuespec=DropdownChoice(
                title=_("Find differences..."),
                choices=[
                    (False, _("Always show all rows")),
                    (True, _("Omit rows where all columns are identical")),
                ],
            ),
        )


# .
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


# This helper function returns the value of the given custom var
def paint_custom_var(
    what: str, key: CSSClass, row: Row, choices: Sequence[tuple[int, str]] | None = None
) -> CellSpec:
    if choices is None:
        choices = []

    if what:
        what += "_"

    custom_vars = dict(
        zip(row[what + "custom_variable_names"], row[what + "custom_variable_values"])
    )

    if key in custom_vars:
        custom_val = custom_vars[key]
        if choices:
            custom_val = dict(choices).get(int(custom_val), custom_val)
        return key, custom_val

    return key, ""


def _paint_future_time(
    timestamp: int,
    *,
    request: Request,
    painter_options: PainterOptions,
) -> CellSpec:
    # NOTE: Nagios uses 0 to represent "never again" while the CMC uses a time far into the future
    # (year 2262 or 0x7fffffffffffffff nanoseconds after 1970, but we leave some headroom below).
    # Although this is inconsistent, the latter is arguably more correct. In any case, the usage of
    # magic numbers is a quite a hack...
    if not 0 < timestamp < 0x200000000:
        return "", "-"
    return paint_age(
        timestamp,
        True,
        0,
        request=request,
        painter_options=painter_options,
        what="future",
    )


def _paint_day(timestamp: int) -> CellSpec:
    return "", time.strftime("%A, %Y-%m-%d", time.localtime(timestamp))


# .
#   .--Site----------------------------------------------------------------.
#   |                           ____  _ _                                  |
#   |                          / ___|(_) |_ ___                            |
#   |                          \___ \| | __/ _ \                           |
#   |                           ___) | | ||  __/                           |
#   |                          |____/|_|\__\___|                           |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Column painters showing information about a site.                   |
#   '----------------------------------------------------------------------'


def _render_site_icon(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    if row.get("site") and context.config.use_siteicons:
        return None, HTMLWriter.render_img("icons/site-%s-24.png" % row["site"], class_="siteicon")
    return None, ""


def make_site_icon_painter() -> InternalPainter:
    return InternalPainter(
        ident="site_icon",
        title=_l("Site icon"),
        short_title="",
        columns=["site"],
        sorter="site",
        render=_render_site_icon,
    )


def _render_sitename_plain(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["site"])


def make_sitename_plain_painter() -> InternalPainter:
    return InternalPainter(
        ident="sitename_plain",
        title=_l("Site ID"),
        short_title=_l("Site"),
        columns=["site"],
        sorter="site",
        render=_render_sitename_plain,
    )


def _render_sitealias(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return (None, context.config.sites[row["site"]]["alias"])


def make_sitealias_painter() -> InternalPainter:
    return InternalPainter(
        ident="sitealias", title=_l("Site alias"), columns=["site"], render=_render_sitealias
    )


# .
#   .--Services------------------------------------------------------------.
#   |                ____                  _                               |
#   |               / ___|  ___ _ ____   _(_) ___ ___  ___                 |
#   |               \___ \ / _ \ '__\ \ / / |/ __/ _ \/ __|                |
#   |                ___) |  __/ |   \ V /| | (_|  __/\__ \                |
#   |               |____/ \___|_|    \_/ |_|\___\___||___/                |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Painters for services                                                |
#   '----------------------------------------------------------------------'


def service_state_short(row: Row) -> tuple[str, str]:
    if row["service_has_been_checked"] == 1:
        return str(row["service_state"]), short_service_state_name(row["service_state"], "")
    return "p", short_service_state_name(-1, "")


def _paint_service_state_short(row: Row, *, staleness_threshold: float) -> CellSpec:
    state, name = service_state_short(row)
    if is_stale(row, staleness_threshold):
        state = state + " stale"
    return "state svcstate state%s" % state, HTMLWriter.render_span(
        name, class_=["state_rounded_fill"]
    )


def host_state_short(row: Row) -> tuple[str, str]:
    if row["host_has_been_checked"] == 1:
        state = str(row["host_state"])
        # A state of 3 is sent by livestatus in cases where no normal state
        # information is avaiable, e.g. for "DOWNTIMESTOPPED (UP)"
        name = short_host_state_name(row["host_state"], "")
    else:
        state = "p"
        name = _("PEND")
    return state, name


def _paint_host_state_short(
    row: Row, short: bool = False, *, staleness_threshold: float
) -> CellSpec:
    state, name = host_state_short(row)
    if is_stale(row, staleness_threshold):
        state = state + " stale"

    if short:
        name = name[0]

    return "state hstate hstate%s" % state, HTMLWriter.render_span(
        name, class_=["state_rounded_fill"]
    )


def _render_service_state(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_service_state_short(row, staleness_threshold=context.config.staleness_threshold)


def make_service_state_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_state",
        title=_l("Service state"),
        short_title=_l("State"),
        columns=["service_has_been_checked", "service_state"],
        sorter="svcstate",
        title_classes=["center"],
        render=_render_service_state,
    )


def _render_svc_plugin_output(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_stalified(
        row,
        format_plugin_output(
            row["service_plugin_output"],
            request=context.request,
            must_escape=determine_must_escape(context.config.sites, row),
            row=row,
        ),
        context.config.staleness_threshold,
    )


def make_svc_plugin_output_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_plugin_output",
        title=_l("Summary"),
        list_title=_l("Summary (previously named: Status details or plug-in output)"),
        columns=["service_plugin_output", "service_custom_variables", "service_check_command"],
        sorter="svcoutput",
        render=_render_svc_plugin_output,
    )


def _parameters_svc_long_plugin_output(_context: PainterContext) -> Dictionary:
    return Dictionary(
        elements=[
            (
                "max_len",
                Integer(
                    title=_("Maximum number of characters to show"),
                    help=_(
                        "Truncate content at this amount of characters. "
                        "A zero value means not to truncate."
                    ),
                    default_value=0,
                    minvalue=0,
                ),
            ),
        ]
    )


def _render_svc_long_plugin_output(
    row: Row, cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    if (params := cell.painter_parameters()) is None:
        params = {}

    max_len = params.get("max_len", 0)
    long_output = row["service_long_plugin_output"]
    long_output_len = len(long_output)

    if 0 < max_len < long_output_len:
        long_output = long_output[:max_len] + "..."

    content = format_plugin_output(
        long_output,
        request=context.request,
        row=row,
        newlineishs_to_brs=True,
        must_escape=determine_must_escape(context.config.sites, row),
    )

    # has to be placed after format_plugin_output() to keep links save from
    # escaping
    if (
        max_long_output_size := sites.states().get(row["site"], {}).get("max_long_output_size", 0)
    ) and long_output_len > max_long_output_size:
        setting_link_tag = context.url_renderer.link_from_filename(
            "global_settings.py",
            html_text="(%s)" % _("Increase limit"),
            query_args=[("varname", "max_long_output_size")],
        )
        content = (
            _("Lost data due to truncation of long output to ")
            + f"{int(max_long_output_size / 1000)}kB "
            + setting_link_tag
            + HTMLWriter.render_b("WARN", class_="stmark state1")
            + HTMLWriter.render_br()
            + content
        )

    return paint_stalified(row, content, context.config.staleness_threshold)


def make_svc_long_plugin_output_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_long_plugin_output",
        title=_l("Details"),
        list_title=_l("Details (previously named: long output)"),
        columns=["service_long_plugin_output", "service_custom_variables"],
        parameters=_parameters_svc_long_plugin_output,
        render=_render_svc_long_plugin_output,
    )


def _render_svc_perf_data(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_stalified(row, row["service_perf_data"], context.config.staleness_threshold)


def make_svc_perf_data_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_perf_data",
        title=_l("Service metrics (source code)"),
        short_title=_l("Metrics"),
        columns=["service_perf_data"],
        render=_render_svc_perf_data,
    )


def _rendered_value(metric: EvaluatedMetric) -> str:
    value = metric.performance_data.value
    return "" if value is None else metric.formatter.render(value)


def _metric_row(
    metric_name: MetricName,
    metric: EvaluatedMetric,
    host_name: str,
    service_description: str,
    show_metric_id: bool,
) -> HTML:
    optional_metric_id = ""
    if show_metric_id:
        optional_metric_id = f" (Metric ID: {metric_name})"
    cells = (
        HTMLWriter.render_td(render_color_icon(metric.color), class_="color")
        + HTMLWriter.render_td(f"{metric.title}{optional_metric_id}:")
        + HTMLWriter.render_td(_rendered_value(metric), class_="value")
    )
    if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.COMMUNITY:
        cells += HTMLWriter.render_td(
            HTMLGenerator.render_popup_trigger(
                HTMLGenerator.render_static_icon(
                    StaticIcon(IconNames.menu),
                    title=_("Use this metric for a forecast graph"),
                    css_classes=["iconbutton"],
                ),
                ident="add_metric_to_graph_" + host_name + ";" + str(service_description),
                method=MethodAjax(
                    endpoint="add_metric_to_graph",
                    url_vars=[
                        ("host", host_name),
                        ("service", service_description),
                        ("metric", metric_name),
                    ],
                ),
            )
        )
    return HTMLWriter.render_tr(cells)


def _metrics_table(
    evaluated: Mapping[MetricName, EvaluatedMetric],
    host_name: str,
    service_description: str,
    show_metric_id: bool,
) -> HTML:
    return HTMLWriter.render_table(
        HTML.empty().join(
            _metric_row(metric_name, metric, host_name, service_description, show_metric_id)
            for metric_name, metric in sorted(evaluated.items(), key=lambda t: t[1].title)
        ),
        class_="metricstable",
    )


def _render_svc_metrics(
    row: Row, _cell: Cell, user: LoggedInUser, context: PainterContext
) -> CellSpec:
    evaluated = evaluated_metrics(
        row["service_perf_data"],
        row["service_check_command"],
        registered_metrics=registered_metrics(),
        registered_translations=registered_translations(),
        temperature_unit=get_temperature_unit(user, context.config.default_temperature_unit),
        debug=context.config.debug,
    )

    if row["service_perf_data"] and not evaluated:
        return "", _("Failed to parse metrics string: %(perf_data)s") % {
            "perf_data": row["service_perf_data"]
        }

    return "", _metrics_table(
        evaluated,
        row["host_name"],
        row["service_description"],
        show_metric_id=context.painter_options.get("show_internal_graph_and_metric_ids"),
    )


def make_svc_metrics_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_metrics",
        title=_l("Service metrics"),
        short_title=_l("Metrics"),
        columns=["service_check_command", "service_perf_data"],
        printable=False,
        painter_options=["show_internal_graph_and_metric_ids"],
        render=_render_svc_metrics,
    )


def _render_svc_perf_val(
    num: int, row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_stalified(
        row, get_perfdata_nth_value(row, num - 1), context.config.staleness_threshold
    )


def make_svc_perf_val_painter(num: int) -> InternalPainter:
    return InternalPainter(
        ident=f"svc_perf_val{num:02d}",
        title=_l("Service metrics - value number %(nr)2d") % {"nr": num},
        short_title=_l("Val. %(nr)d") % {"nr": num},
        columns=["service_perf_data"],
        render=partial(_render_svc_perf_val, num),
    )


def _render_svc_check_command(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["service_check_command"])


def make_svc_check_command_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_check_command",
        title=_l("Service check command"),
        short_title=_l("Check command"),
        columns=["service_check_command"],
        render=_render_svc_check_command,
    )


def _render_svc_check_command_expanded(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["service_check_command_expanded"])


def make_svc_check_command_expanded_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_check_command_expanded",
        title=_l("Service check command expanded"),
        short_title=_l("Check command expanded"),
        columns=["service_check_command_expanded"],
        render=_render_svc_check_command_expanded,
    )


def _render_svc_notes_u_r_l(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    raw_url = row.get("service_notes_url")
    if not raw_url:
        return None, HTML.empty()

    url = replace_action_url_macros(raw_url, "service", row)
    content = context.url_renderer.link_direct(url, html_text=url, target="_blank")
    return None, content


def make_svc_notes_url_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_notes_url",
        title=_l("Notes (URL) for services"),
        short_title=_l("Notes URL"),
        columns=["host_address", "service_notes_url"],
        render=_render_svc_notes_u_r_l,
    )


def _render_svc_contacts(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, ", ".join(row["service_contacts"]))


def make_svc_contacts_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_contacts",
        title=_l("Service contacts"),
        short_title=_l("Contacts"),
        columns=["service_contacts"],
        render=_render_svc_contacts,
    )


def _render_svc_contact_groups(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, ", ".join(row["service_contact_groups"]))


def make_svc_contact_groups_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_contact_groups",
        title=_l("Service contact groups"),
        short_title=_l("Contact groups"),
        columns=["service_contact_groups"],
        render=_render_svc_contact_groups,
    )


def _render_service_description(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["service_description"])


def make_service_description_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_description",
        title=_l("Service name"),
        short_title=_l("Service"),
        columns=["service_description"],
        sorter="svcdescr",
        render=_render_service_description,
    )


def _render_service_display_name(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["service_display_name"])


def make_service_display_name_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_display_name",
        title=_l("Service alternative display name"),
        short_title=_l("Display name"),
        columns=["service_display_name"],
        sorter="svcdispname",
        render=_render_service_display_name,
    )


def _render_svc_state_age(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age(
        row["service_last_state_change"],
        row["service_has_been_checked"] == 1,
        60 * 10,
        request=context.request,
        painter_options=context.painter_options,
    )


def make_svc_state_age_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_state_age",
        title=_l("Age of the current service state"),
        short_title=_l("Age"),
        columns=["service_has_been_checked", "service_last_state_change"],
        sorter="stateage",
        painter_options=["ts_format", "ts_date"],
        render=_render_svc_state_age,
    )


def _paint_checked(
    what: str,
    row: Row,
    *,
    staleness_threshold: float,
    request: Request,
    painter_options: PainterOptions,
) -> CellSpec:
    age = row[what + "_last_check"]
    if what == "service":
        cached_at = row["service_cached_at"]
        if cached_at:
            age = cached_at

    css, td = paint_age(
        age,
        row[what + "_has_been_checked"] == 1,
        0,
        request=request,
        painter_options=painter_options,
    )
    assert css is not None
    if is_stale(row, staleness_threshold):
        css += " staletime"
    return css, td


def _render_svc_check_age(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_checked(
        "service",
        row,
        staleness_threshold=context.config.staleness_threshold,
        request=context.request,
        painter_options=context.painter_options,
    )


def make_svc_check_age_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_check_age",
        title=_l("Time since the last check of the service"),
        short_title=_l("Checked"),
        columns=["service_has_been_checked", "service_last_check", "service_cached_at"],
        painter_options=["ts_format", "ts_date"],
        render=_render_svc_check_age,
    )


def _render_svc_check_cache_info(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    if not row["service_cached_at"]:
        return "", ""
    return "", render_cache_info("service", row)


def make_svc_check_cache_info_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_check_cache_info",
        title=_l("Cached agent data"),
        short_title=_l("Cached"),
        columns=["service_last_check", "service_cached_at", "service_cache_interval"],
        painter_options=["ts_format", "ts_date"],
        render=_render_svc_check_cache_info,
    )


def _render_svc_next_check(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_future_time(
        row["service_next_check"],
        request=context.request,
        painter_options=context.painter_options,
    )


def make_svc_next_check_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_next_check",
        title=_l("Time of the next scheduled service check"),
        short_title=_l("Next check"),
        columns=["service_next_check"],
        render=_render_svc_next_check,
    )


def _render_svc_last_time_ok(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age_or_never(
        row["service_last_time_ok"],
        row["service_has_been_checked"] == 1,
        60 * 10,
        request=context.request,
        painter_options=context.painter_options,
    )


def make_svc_last_time_ok_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_last_time_ok",
        title=_l("Last time the service was OK"),
        short_title=_l("Last OK"),
        columns=["service_last_time_ok", "service_has_been_checked"],
        render=_render_svc_last_time_ok,
    )


def _render_svc_next_notification(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_future_time(
        row["service_next_notification"],
        request=context.request,
        painter_options=context.painter_options,
    )


def make_svc_next_notification_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_next_notification",
        title=_l("Time of the next service notification"),
        short_title=_l("Next notification"),
        columns=["service_next_notification"],
        render=_render_svc_next_notification,
    )


def _paint_notification_postponement_reason(what: str, row: Row) -> CellSpec:
    # Needs to be in sync with the possible reasons. Can not be translated otherwise.
    reasons = {
        "delayed notification": _("Delay notification"),
        "periodic notification": _("Periodic notification"),
        "currently in downtime": _("In downtime"),
        "host of this service is currently in downtime": _("Host is in downtime"),
        "problem acknowledged and periodic notifications are enabled": _(
            "Problem is acknowledged, but is configured to be periodic"
        ),
        "notifications are disabled, but periodic notifications are enabled": _(
            "Notifications are disabled, but is configured to be periodic"
        ),
        "not in notification period": _("Is not in notification period"),
        "host of this service is not up": _("Host is down"),
        "last host check not recent enough": _("Last host check is not recent enough"),
        "last service check not recent enough": _("Last service check is not recent enough"),
        "all parents are down": _("All parents are down"),
        "at least one parent is up, but no check is recent enough": _(
            "Last service check is not recent enough"
        ),
        None: "",  # column is not available if the Nagios core is used
    }

    reason: str = row[what + "_notification_postponement_reason"]
    return ("", reasons.get(reason, reason))


def _render_svc_notification_postponement_reason(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _paint_notification_postponement_reason("service", row)


def make_svc_notification_postponement_reason_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_notification_postponement_reason",
        title=_l("Notification postponement reason"),
        short_title=_l("Notif. postponed"),
        columns=["service_notification_postponement_reason"],
        render=_render_svc_notification_postponement_reason,
    )


def _render_svc_last_notification(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age(
        row["service_last_notification"],
        row["service_last_notification"],
        0,
        request=context.request,
        painter_options=context.painter_options,
    )


def make_svc_last_notification_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_last_notification",
        title=_l("Time of the last service notification"),
        short_title=_l("last notification"),
        columns=["service_last_notification"],
        painter_options=["ts_format", "ts_date"],
        render=_render_svc_last_notification,
    )


def _render_svc_notification_number(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    # Keep in sync with HACK in cmk/base/events.py
    current: str = str(row["service_current_notification_number"])
    return ("", "1" if current == "0" else current)


def make_svc_notification_number_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_notification_number",
        title=_l("Service notification number"),
        short_title=_l("N#"),
        columns=["service_current_notification_number"],
        render=_render_svc_notification_number,
    )


def _render_svc_check_latency(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", approx_age(row["service_latency"]))


def make_svc_check_latency_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_check_latency",
        title=_l("Service check latency"),
        short_title=_l("Latency"),
        columns=["service_latency"],
        render=_render_svc_check_latency,
    )


def _render_svc_check_duration(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", approx_age(row["service_execution_time"]))


def make_svc_check_duration_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_check_duration",
        title=_l("Service check duration"),
        short_title=_l("Duration"),
        columns=["service_execution_time"],
        render=_render_svc_check_duration,
    )


def _render_svc_attempt(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, "%d/%d" % (row["service_current_attempt"], row["service_max_check_attempts"]))


def make_svc_attempt_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_attempt",
        title=_l("Current check attempt"),
        short_title=_l("Att."),
        columns=["service_current_attempt", "service_max_check_attempts"],
        render=_render_svc_attempt,
    )


def _render_svc_normal_interval(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("number", approx_age(row["service_check_interval"] * 60.0))


def make_svc_normal_interval_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_normal_interval",
        title=_l("Service normal check interval"),
        short_title=_l("Check int."),
        columns=["service_check_interval"],
        render=_render_svc_normal_interval,
    )


def _render_svc_retry_interval(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("number", approx_age(row["service_retry_interval"] * 60.0))


def make_svc_retry_interval_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_retry_interval",
        title=_l("Service retry check interval"),
        short_title=_l("Retry"),
        columns=["service_retry_interval"],
        render=_render_svc_retry_interval,
    )


def _render_svc_check_interval(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (
        None,
        "%s / %s"
        % (
            approx_age(row["service_check_interval"] * 60.0),
            approx_age(row["service_retry_interval"] * 60.0),
        ),
    )


def make_svc_check_interval_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_check_interval",
        title=_l("Service normal/retry check interval"),
        short_title=_l("Interval"),
        columns=["service_check_interval", "service_retry_interval"],
        render=_render_svc_check_interval,
    )


def _render_svc_check_type(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, _("ACTIVE") if row["service_check_type"] == 0 else _("PASSIVE"))


def make_svc_check_type_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_check_type",
        title=_l("Service check type"),
        short_title=_l("Type"),
        columns=["service_check_type"],
        render=_render_svc_check_type,
    )


def _render_svc_in_downtime(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "service_scheduled_downtime_depth", True)


def make_svc_in_downtime_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_in_downtime",
        title=_l("Currently in downtime"),
        short_title=_l("Dt."),
        columns=["service_scheduled_downtime_depth"],
        render=_render_svc_in_downtime,
    )


def _render_svc_in_notifper(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "service_in_notification_period", False)


def make_svc_in_notifper_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_in_notifper",
        title=_l("In notification period"),
        short_title=_l("in notif. p."),
        columns=["service_in_notification_period"],
        render=_render_svc_in_notifper,
    )


def _render_svc_notifper(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["service_notification_period"])


def make_svc_notifper_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_notifper",
        title=_l("Service notification period"),
        short_title=_l("notif."),
        columns=["service_notification_period"],
        render=_render_svc_notifper,
    )


def _render_svc_check_period(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["service_check_period"])


def make_svc_check_period_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_check_period",
        title=_l("Service check period"),
        short_title=_l("check."),
        columns=["service_check_period"],
        render=_render_svc_check_period,
    )


def _render_svc_flapping(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "service_is_flapping", True)


def make_svc_flapping_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_flapping",
        title=_l("Service is flapping"),
        short_title=_l("Flap"),
        columns=["service_is_flapping"],
        render=_render_svc_flapping,
    )


def _render_svc_notifications_enabled(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "service_notifications_enabled", False)


def make_svc_notifications_enabled_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_notifications_enabled",
        title=_l("Service notifications enabled"),
        short_title=_l("Notif."),
        columns=["service_notifications_enabled"],
        render=_render_svc_notifications_enabled,
    )


def _render_svc_is_active(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "service_active_checks_enabled", False)


def make_svc_is_active_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_is_active",
        title=_l("Service is active"),
        short_title=_l("Active"),
        columns=["service_active_checks_enabled"],
        render=_render_svc_is_active,
    )


def _render_svc_group_memberlist(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    links = []

    for group in row["service_groups"]:
        link = context.url_renderer.link_from_filename(
            "view.py",
            html_text=group,
            query_args=[
                ("view_name", "servicegroup"),
                ("servicegroup", group),
            ],
        )
        links.append(link)
    return "", HTML.without_escaping(", ").join(links)


def _export_for_csv_svc_group_memberlist(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str:
    return ", ".join(row["service_groups"])


def _export_for_json_svc_group_memberlist(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    return row["service_groups"]


def make_svc_group_memberlist_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_group_memberlist",
        title=_l("Service groups the service is member of"),
        short_title=_l("Groups"),
        columns=["service_groups"],
        render=_render_svc_group_memberlist,
        export_for_csv=_export_for_csv_svc_group_memberlist,
        export_for_json=_export_for_json_svc_group_memberlist,
    )


def _render_check_manpage(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    command = row["service_check_command"]

    if not command.startswith(("check_mk-", "check-mk", "check_mk_active-cmk_inv")):
        return "", ""

    if command == "check-mk":
        checktype = "check-mk"
    elif command == "check-mk-inventory":
        checktype = "check-mk-inventory"
    elif "check_mk_active-cmk_inv" in command:
        checktype = "check_cmk_inv"
    elif command.startswith("check_mk-mgmt_"):
        checktype = command[14:]
    else:
        checktype = command[9:]

    man_page_path_map = man_pages.make_man_page_path_map(
        discover_families(raise_errors=False), PluginGroup.CHECKMAN.value
    )
    # some checks are run as commandlines (e.g. checks configured via the "Integrate nagios plugins" rule).
    name = checktype.split()[0]

    try:
        page = man_pages.parse_man_page(name, man_page_path_map[name])
    except KeyError:
        return "", ""

    description = HTML.without_escaping(
        escaping.escape_attribute(page.description)
        .replace("{", "<b>")
        .replace("}", "</b>")
        .replace("&lt;br&gt;", "<br>")
        .replace("\n\n", "\n<br>\n")
    )
    return "", description


def make_check_manpage_painter() -> InternalPainter:
    return InternalPainter(
        ident="check_manpage",
        title=_l("Check manual (for Checkmk based checks)"),
        short_title=_l("Manual"),
        columns=["service_check_command"],
        render=_render_check_manpage,
    )


def _paint_comments(prefix: str, row: Row) -> CellSpec:
    comments = row[prefix + "comments_with_info"]
    text = HTML.without_escaping(", ").join(
        [
            HTMLWriter.render_i(a)
            + escaping.escape_to_html_permissive(": %s" % c, escape_links=False)
            for _id, a, c in comments
        ]
    )
    return "", text


def _render_svc_comments(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _paint_comments("service_", row)


def make_svc_comments_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_comments",
        title=_l("Service Comments"),
        short_title=_l("Comments"),
        columns=["service_comments_with_info"],
        render=_render_svc_comments,
    )


def _render_svc_acknowledged(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "service_acknowledged", False)


def make_svc_acknowledged_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_acknowledged",
        title=_l("Service problem acknowledged"),
        short_title=_l("Ack"),
        columns=["service_acknowledged"],
        render=_render_svc_acknowledged,
    )


def match_path_entries_with_item(dirs: Iterable[Path], item: str) -> Iterable[Path]:
    yield from (
        sub_path
        for directory in dirs
        if directory.is_dir()
        for sub_path in directory.iterdir()
        if not sub_path.name.startswith(".") and fnmatch(item, sub_path.name)
    )


def _paint_custom_notes(what: str, row: Row, *, site_configs: SiteConfigurations) -> CellSpec:
    host = row["host_name"]
    svc = row.get("service_description")
    if what == "service":
        dirs = match_path_entries_with_item(
            [cmk.utils.paths.default_config_dir / "notes/services"], host
        )
        item = svc
    else:
        dirs = [cmk.utils.paths.default_config_dir / "notes/hosts"]
        item = host

    assert isinstance(item, str)
    files = sorted(match_path_entries_with_item(dirs, item), reverse=True)
    contents = []

    def replace_tags(text: str) -> str:
        sitename = row["site"]
        url_prefix = site_configs[sitename]["url_prefix"]
        return (
            text.replace("$URL_PREFIX$", url_prefix)
            .replace("$SITE$", sitename)
            .replace("$HOSTNAME$", host)
            .replace("$HOSTNAME_LOWER$", host.lower())
            .replace("$HOSTNAME_UPPER$", host.upper())
            .replace("$HOSTNAME_TITLE$", host[0].upper() + host[1:].lower())
            .replace("$HOSTADDRESS$", row["host_address"])
            .replace("$SERVICEOUTPUT$", row.get("service_plugin_output", ""))
            .replace("$HOSTOUTPUT$", row.get("host_plugin_output", ""))
            .replace("$SERVICEDESC$", row.get("service_description", ""))
        )

    for f in files:
        contents.append(replace_tags(f.read_text(encoding="utf8").strip()))
    # These notes can only be created if you have site user access.
    # And yes that feature is used: SUP-15290
    return "", HTML.without_escaping("<hr>".join(contents))


def _render_svc_custom_notes(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_custom_notes("service", row, site_configs=context.config.sites)


def make_svc_custom_notes_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_custom_notes",
        title=_l("Custom services notes"),
        short_title=_l("Notes"),
        columns=["host_name", "host_address", "service_description", "service_plugin_output"],
        render=_render_svc_custom_notes,
    )


def _render_svc_staleness(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", "%0.2f" % row.get("service_staleness", 0))


def make_svc_staleness_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_staleness",
        title=_l("Service staleness value"),
        short_title=_l("Staleness"),
        columns=["service_staleness"],
        render=_render_svc_staleness,
    )


def _paint_is_stale(row: Row, staleness_threshold: float) -> CellSpec:
    if is_stale(row, staleness_threshold):
        return "badflag", HTMLWriter.render_span(_("yes"))
    return "goodflag", _("no")


def _render_svc_is_stale(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_is_stale(row, context.config.staleness_threshold)


def make_svc_is_stale_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_is_stale",
        title=_l("Service is stale"),
        short_title=_l("Stale"),
        columns=["service_staleness"],
        sorter="svc_staleness",
        render=_render_svc_is_stale,
    )


def _paint_custom_vars(what: str, row: Row, blacklist: list | None = None) -> CellSpec:
    if blacklist is None:
        blacklist = []

    items = sorted(row[what + "_custom_variables"].items())
    rows = []
    for varname, value in items:
        if varname not in blacklist:
            rows.append(
                HTMLWriter.render_tr(HTMLWriter.render_td(varname) + HTMLWriter.render_td(value))
            )
    return "", HTMLWriter.render_table(HTML.empty().join(rows))


def _export_custom_vars(what: str, row: Row, blacklist: list | None = None) -> str:
    if blacklist is None:
        blacklist = []

    items = sorted(row[what + "_custom_variables"].items())
    rows = []
    for varname, value in items:
        if varname not in blacklist:
            if value:
                rows.append(f"{varname}: {value}")
            else:
                rows.append(f"{varname}")
    return ", ".join(rows)


def _group_by_service_custom_variables(
    row: Row, _cell: Cell, _context: PainterContext
) -> tuple[tuple[str, str], ...]:
    return tuple(row["service_custom_variables"].items())


def _render_service_custom_variables(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _paint_custom_vars("service", row)


def _export_for_csv_service_custom_variables(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str:
    return _export_custom_vars("service", row)


def _export_for_json_service_custom_variables(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str:
    return _export_custom_vars("service", row)


def make_svc_custom_vars_painter() -> InternalPainter:
    return InternalPainter(
        ident="svc_custom_vars",
        title=_l("Service custom attributes"),
        columns=["service_custom_variables"],
        group_by=_group_by_service_custom_variables,
        render=_render_service_custom_variables,
        export_for_csv=_export_for_csv_service_custom_variables,
        export_for_json=_export_for_json_service_custom_variables,
    )


type _CustomAttributeChoices = Callable[[PainterConfig], DropdownChoiceEntries]


def _service_custom_attribute_choices(config: PainterConfig) -> DropdownChoiceEntries:
    return sorted(config.service_custom_attribute_titles.items(), key=lambda x: x[1])


def _host_custom_attribute_choices(config: PainterConfig) -> DropdownChoiceEntries:
    return sorted(config.host_custom_attribute_titles.items(), key=lambda x: x[1])


def _title_custom_variable(
    attribute_choices: _CustomAttributeChoices,
    default_title: LazyString,
    cell: Cell,
    context: PainterContext,
) -> str:
    if (params := cell.painter_parameters()) is None:
        # Happens in view editor when adding a painter
        return str(default_title)

    try:
        attributes: dict = dict(attribute_choices(context.config))
        return attributes[params["ident"]]
    except KeyError:
        return str(default_title)


def _export_title_custom_variable(name: str, cell: Cell) -> str:
    if (params := cell.painter_parameters()) is None:
        return name
    return f"{name}_{params['ident']}"


def _parameters_custom_variable(
    attribute_choices: _CustomAttributeChoices, context: PainterContext
) -> Dictionary:
    return Dictionary(
        elements=[
            (
                "ident",
                DropdownChoice(
                    choices=lambda: attribute_choices(context.config),
                    title=_("ID"),
                ),
            ),
        ],
        title=_("Options"),
        optional_keys=[],
    )


def _render_custom_variable(
    object_type: str, row: Row, cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    if (params := cell.painter_parameters()) is None:
        params = {}
    return paint_custom_var(object_type, params.get("ident", "").upper(), row)


def _group_by_host_custom_variable(
    row: Row, cell: Cell, _context: PainterContext
) -> str | tuple[str, ...]:
    if (parameters := cell.painter_parameters()) is None:
        return ""

    custom_variable_name = parameters["ident"]
    try:
        index = row["host_custom_variable_names"].index(custom_variable_name.upper())
    except ValueError:
        # group all hosts without this custom variable into a single group.
        # this group does not have a headline.
        return ""
    return row["host_custom_variable_values"][index]


_SERVICE_CUSTOM_VARIABLE_TITLE = _l("Service custom attribute")


def _render_service_custom_variable(
    row: Row, cell: Cell, user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _render_custom_variable("service", row, cell, user, context)


def _title_service_custom_variable(cell: Cell, context: PainterContext) -> str:
    return _title_custom_variable(
        _service_custom_attribute_choices, _SERVICE_CUSTOM_VARIABLE_TITLE, cell, context
    )


def _export_title_service_custom_variable(cell: Cell) -> str:
    return _export_title_custom_variable("service_custom_variable", cell)


def _parameters_service_custom_variable(context: PainterContext) -> Dictionary:
    return _parameters_custom_variable(_service_custom_attribute_choices, context)


def make_service_custom_variable_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_custom_variable",
        title=_SERVICE_CUSTOM_VARIABLE_TITLE,
        list_title=_SERVICE_CUSTOM_VARIABLE_TITLE,
        columns=["service_custom_variable_names", "service_custom_variable_values"],
        cell_title=_title_service_custom_variable,
        cell_short_title=_title_service_custom_variable,
        export_title=_export_title_service_custom_variable,
        parameters=_parameters_service_custom_variable,
        render=_render_service_custom_variable,
    )


_HOST_CUSTOM_VARIABLE_TITLE = _l("Host custom attribute")


def _render_host_custom_variable(
    row: Row, cell: Cell, user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _render_custom_variable("host", row, cell, user, context)


def _title_host_custom_variable(cell: Cell, context: PainterContext) -> str:
    return _title_custom_variable(
        _host_custom_attribute_choices, _HOST_CUSTOM_VARIABLE_TITLE, cell, context
    )


def _export_title_host_custom_variable(cell: Cell) -> str:
    return _export_title_custom_variable("host_custom_variable", cell)


def _parameters_host_custom_variable(context: PainterContext) -> Dictionary:
    return _parameters_custom_variable(_host_custom_attribute_choices, context)


def make_host_custom_variable_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_custom_variable",
        title=_HOST_CUSTOM_VARIABLE_TITLE,
        list_title=_HOST_CUSTOM_VARIABLE_TITLE,
        columns=["host_custom_variable_names", "host_custom_variable_values"],
        cell_title=_title_host_custom_variable,
        cell_short_title=_title_host_custom_variable,
        export_title=_export_title_host_custom_variable,
        parameters=_parameters_host_custom_variable,
        group_by=_group_by_host_custom_variable,
        render=_render_host_custom_variable,
    )


# .
#   .--Hosts---------------------------------------------------------------.
#   |                       _   _           _                              |
#   |                      | | | | ___  ___| |_ ___                        |
#   |                      | |_| |/ _ \/ __| __/ __|                       |
#   |                      |  _  | (_) \__ \ |_\__ \                       |
#   |                      |_| |_|\___/|___/\__|___/                       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Painters for hosts                                                   |
#   '----------------------------------------------------------------------'


def _render_host_state(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_host_state_short(row, staleness_threshold=context.config.staleness_threshold)


def make_host_state_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_state",
        title=_l("Host state"),
        short_title=_l("State"),
        columns=["host_has_been_checked", "host_state"],
        sorter="hoststate",
        title_classes=["center"],
        render=_render_host_state,
    )


def _render_host_state_onechar(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_host_state_short(
        row, short=True, staleness_threshold=context.config.staleness_threshold
    )


def make_host_state_onechar_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_state_onechar",
        title=_l("Host state (first character)"),
        short_title=_l("S."),
        columns=["host_has_been_checked", "host_state"],
        sorter="hoststate",
        render=_render_host_state_onechar,
    )


def _render_host_plugin_output(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return (
        None,
        format_plugin_output(
            row["host_plugin_output"],
            request=context.request,
            must_escape=determine_must_escape(context.config.sites, row),
            row=row,
        ),
    )


def make_host_plugin_output_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_plugin_output",
        title=_l("Summary"),
        list_title=_l("Summary (previously named: Status details or plug-in output)"),
        columns=["host_plugin_output", "host_custom_variables"],
        render=_render_host_plugin_output,
    )


def _render_host_perf_data(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["host_perf_data"])


def make_host_perf_data_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_perf_data",
        title=_l("Host metrics"),
        short_title=_l("Metrics"),
        columns=["host_perf_data"],
        render=_render_host_perf_data,
    )


def _render_host_check_command(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["host_check_command"])


def make_host_check_command_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_check_command",
        title=_l("Host check command"),
        short_title=_l("Check command"),
        columns=["host_check_command"],
        render=_render_host_check_command,
    )


def _render_host_check_command_expanded(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["host_check_command_expanded"])


def make_host_check_command_expanded_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_check_command_expanded",
        title=_l("Host check command expanded"),
        short_title=_l("Check command expanded"),
        columns=["host_check_command_expanded"],
        render=_render_host_check_command_expanded,
    )


def _render_host_notes_u_r_l(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    raw_url = row.get("host_notes_url")
    if not raw_url:
        return None, HTML.empty()

    url = replace_action_url_macros(raw_url, "host", row)
    content = context.url_renderer.link_direct(url, html_text=url, target="_blank")
    return None, content


def make_host_notes_url_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_notes_url",
        title=_l("Notes (URL) for hosts"),
        short_title=_l("Notes URL"),
        columns=["host_address", "host_notes_url"],
        render=_render_host_notes_u_r_l,
    )


def _render_host_state_age(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age(
        row["host_last_state_change"],
        row["host_has_been_checked"] == 1,
        60 * 10,
        request=context.request,
        painter_options=context.painter_options,
    )


def make_host_state_age_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_state_age",
        title=_l("Age of the current host state"),
        short_title=_l("Age"),
        columns=["host_has_been_checked", "host_last_state_change"],
        painter_options=["ts_format", "ts_date"],
        render=_render_host_state_age,
    )


def _render_host_check_age(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_checked(
        "host",
        row,
        staleness_threshold=context.config.staleness_threshold,
        request=context.request,
        painter_options=context.painter_options,
    )


def make_host_check_age_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_check_age",
        title=_l("Time since the last check of the host"),
        short_title=_l("Checked"),
        columns=["host_has_been_checked", "host_last_check"],
        painter_options=["ts_format", "ts_date"],
        render=_render_host_check_age,
    )


def _render_host_next_check(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_future_time(
        row["host_next_check"],
        request=context.request,
        painter_options=context.painter_options,
    )


def make_host_next_check_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_next_check",
        title=_l("Time of the next scheduled host check"),
        short_title=_l("Next check"),
        columns=["host_next_check"],
        render=_render_host_next_check,
    )


def _render_host_next_notification(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_future_time(
        row["host_next_notification"],
        request=context.request,
        painter_options=context.painter_options,
    )


def make_host_next_notification_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_next_notification",
        title=_l("Time of the next host notification"),
        short_title=_l("Next notification"),
        columns=["host_next_notification"],
        render=_render_host_next_notification,
    )


def _render_host_notification_postponement_reason(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _paint_notification_postponement_reason("host", row)


def make_host_notification_postponement_reason_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_notification_postponement_reason",
        title=_l("Notification postponement reason"),
        short_title=_l("Notif. postponed"),
        columns=["host_notification_postponement_reason"],
        render=_render_host_notification_postponement_reason,
    )


def _render_host_last_notification(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age(
        row["host_last_notification"],
        row["host_last_notification"],
        0,
        request=context.request,
        painter_options=context.painter_options,
    )


def make_host_last_notification_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_last_notification",
        title=_l("Time of the last host notification"),
        short_title=_l("last notification"),
        columns=["host_last_notification"],
        painter_options=["ts_format", "ts_date"],
        render=_render_host_last_notification,
    )


def _render_host_check_latency(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", approx_age(row["host_latency"]))


def make_host_check_latency_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_check_latency",
        title=_l("Host check latency"),
        short_title=_l("Latency"),
        columns=["host_latency"],
        render=_render_host_check_latency,
    )


def _render_host_check_duration(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", approx_age(row["host_execution_time"]))


def make_host_check_duration_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_check_duration",
        title=_l("Host check duration"),
        short_title=_l("Duration"),
        columns=["host_execution_time"],
        render=_render_host_check_duration,
    )


def _render_host_attempt(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, "%d/%d" % (row["host_current_attempt"], row["host_max_check_attempts"]))


def make_host_attempt_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_attempt",
        title=_l("Current host check attempt"),
        short_title=_l("Att."),
        columns=["host_current_attempt", "host_max_check_attempts"],
        render=_render_host_attempt,
    )


def _render_host_normal_interval(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, approx_age(row["host_check_interval"] * 60.0))


def make_host_normal_interval_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_normal_interval",
        title=_l("Normal check interval"),
        short_title=_l("Check int."),
        columns=["host_check_interval"],
        render=_render_host_normal_interval,
    )


def _render_host_retry_interval(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, approx_age(row["host_retry_interval"] * 60.0))


def make_host_retry_interval_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_retry_interval",
        title=_l("Retry check interval"),
        short_title=_l("Retry"),
        columns=["host_retry_interval"],
        render=_render_host_retry_interval,
    )


def _render_host_check_interval(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (
        None,
        "%s / %s"
        % (
            approx_age(row["host_check_interval"] * 60.0),
            approx_age(row["host_retry_interval"] * 60.0),
        ),
    )


def make_host_check_interval_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_check_interval",
        title=_l("Normal/retry check interval"),
        short_title=_l("Interval"),
        columns=["host_check_interval", "host_retry_interval"],
        render=_render_host_check_interval,
    )


def _render_host_check_type(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["host_check_type"] == 0 and "ACTIVE" or "PASSIVE")


def make_host_check_type_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_check_type",
        title=_l("Host check type"),
        short_title=_l("Type"),
        columns=["host_check_type"],
        render=_render_host_check_type,
    )


def _render_host_in_notifper(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "host_in_notification_period", False)


def make_host_in_notifper_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_in_notifper",
        title=_l("Host in notif. period"),
        short_title=_l("in notif. p."),
        columns=["host_in_notification_period"],
        render=_render_host_in_notifper,
    )


def _render_host_notifper(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["host_notification_period"])


def make_host_notifper_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_notifper",
        title=_l("Host notification period"),
        short_title=_l("notif."),
        columns=["host_notification_period"],
        render=_render_host_notifper,
    )


def _render_host_notification_number(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", str(row["host_current_notification_number"]))


def make_host_notification_number_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_notification_number",
        title=_l("Host notification number"),
        short_title=_l("N#"),
        columns=["host_current_notification_number"],
        render=_render_host_notification_number,
    )


def _render_host_flapping(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "host_is_flapping", True)


def make_host_flapping_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_flapping",
        title=_l("Host is flapping"),
        short_title=_l("Flap"),
        columns=["host_is_flapping"],
        render=_render_host_flapping,
    )


def _render_host_is_active(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "host_active_checks_enabled", False)


def make_host_is_active_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_is_active",
        title=_l("Host is active"),
        short_title=_l("Active"),
        columns=["host_active_checks_enabled"],
        render=_render_host_is_active,
    )


def _render_host_notifications_enabled(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "host_notifications_enabled", False)


def make_host_notifications_enabled_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_notifications_enabled",
        title=_l("Host notifications enabled"),
        short_title=_l("Notif."),
        columns=["host_notifications_enabled"],
        render=_render_host_notifications_enabled,
    )


def _render_host_black(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    state = row["host_state"]
    if state != 0:
        return "nobr", HTMLWriter.render_div(row["host_name"], class_="hostdown")
    return "nobr", row["host_name"]


def make_host_black_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_black",
        title=_l("Host name, red background if down or unreachable (deprecated)"),
        short_title=_l("Host"),
        columns=["site", "host_name", "host_state"],
        sorter="site_host",
        render=_render_host_black,
    )


def _render_host_with_state(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    state = row["host_state"] if row["host_has_been_checked"] else "p"
    if state != 0:
        return "state hstate hstate%s" % state, HTMLWriter.render_span(row["host_name"])
    return "nobr", row["host_name"]


def make_host_with_state_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_with_state",
        title=_l("Host name, marked red if down (deprecated)"),
        short_title=_l("Host"),
        columns=["site", "host_name", "host_state", "host_has_been_checked"],
        sorter="site_host",
        render=_render_host_with_state,
    )


def _parameters_host(_context: PainterContext) -> Dictionary:
    elements: DictionaryElements = [
        (
            "color_choices",
            ListChoice(
                choices=[
                    ("colorize_up", _("Colorize background if host is up")),
                    ("colorize_down", _("Colorize background if host is down")),
                    ("colorize_unreachable", _("Colorize background if host unreachable")),
                    ("colorize_pending", _("Colorize background if host is pending")),
                    ("colorize_downtime", _("Colorize background if host is downtime")),
                ],
                title=_("Coloring"),
                help=_(
                    "Here, you can configure the background color for specific states. "
                    "The coloring for host in downtime overrules all other coloring."
                ),
            ),
        )
    ]

    return Dictionary(elements=elements, title=_("Options"), optional_keys=[])


def _render_host(row: Row, cell: Cell, _user: LoggedInUser, _context: PainterContext) -> CellSpec:
    if (params := cell.painter_parameters()) is None:
        params = {}

    color_choices = params.get("color_choices", [])

    state = row["host_state"] if row["host_has_been_checked"] else "p"

    css = ["nobr"]
    if "colorize_downtime" in color_choices and row["host_scheduled_downtime_depth"] > 0:
        css.extend(["hstate", "hstated"])

    # Also apply other css classes, even if its already in downtime
    for key, option_state in [
        ("colorize_up", 0),
        ("colorize_down", 1),
        ("colorize_unreachable", 2),
        ("colorize_pending", "p"),
    ]:
        if key in color_choices and state == option_state:
            if "hstate" not in css:
                css.append("hstate")
            css.append("hstate%s" % option_state)
            break

    return " ".join(css), HTMLWriter.render_span(
        row["host_name"], class_=["state_rounded_fill", "host"]
    )


def make_host_painter() -> InternalPainter:
    return InternalPainter(
        ident="host",
        title=_l("Host name"),
        short_title=_l("Host"),
        columns=[
            "host_name",
            "host_state",
            "host_has_been_checked",
            "host_scheduled_downtime_depth",
        ],
        sorter="site_host",
        parameters=_parameters_host,
        render=_render_host,
    )


def _render_alias(row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext) -> CellSpec:
    return ("", row["host_alias"])


def make_alias_painter() -> InternalPainter:
    return InternalPainter(
        ident="alias",
        title=_l("Host alias"),
        short_title=_l("Alias"),
        columns=["host_alias"],
        render=_render_alias,
    )


def _render_host_address(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", row["host_address"])


def make_host_address_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_address",
        title=_l("Host address (primary)"),
        short_title=_l("IP address"),
        columns=["host_address"],
        render=_render_host_address,
    )


def _render_host_ipv4_address(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_custom_var("host", "ADDRESS_4", row)


def make_host_ipv4_address_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_ipv4_address",
        title=_l("Host address (IPv4)"),
        short_title=_l("IPv4 address"),
        columns=["host_custom_variable_names", "host_custom_variable_values"],
        render=_render_host_ipv4_address,
    )


def _render_host_ipv6_address(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_custom_var("host", "ADDRESS_6", row)


def make_host_ipv6_address_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_ipv6_address",
        title=_l("Host address (IPv6)"),
        short_title=_l("IPv6 address"),
        columns=["host_custom_variable_names", "host_custom_variable_values"],
        render=_render_host_ipv6_address,
    )


def _render_host_addresses(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    custom_vars = dict(zip(row["host_custom_variable_names"], row["host_custom_variable_values"]))

    if custom_vars.get("ADDRESS_FAMILY", "4") == "4":
        primary = custom_vars.get("ADDRESS_4", "")
        secondary = custom_vars.get("ADDRESS_6", "")
    else:
        primary = custom_vars.get("ADDRESS_6", "")
        secondary = custom_vars.get("ADDRESS_4", "")

    if secondary:
        secondary = " (%s)" % secondary
    return "", primary + secondary


def make_host_addresses_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_addresses",
        title=_l("Host addresses (IPv4/IPv6)"),
        short_title=_l("IP addresses"),
        columns=["host_address", "host_custom_variable_names", "host_custom_variable_values"],
        render=_render_host_addresses,
    )


def _render_host_addresses_additional(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    custom_vars = dict(zip(row["host_custom_variable_names"], row["host_custom_variable_values"]))

    ipv4_addresses = custom_vars.get("ADDRESSES_4", "").strip()
    ipv6_addresses = custom_vars.get("ADDRESSES_6", "").strip()

    addresses = []
    if ipv4_addresses:
        addresses += ipv4_addresses.split(" ")
    if ipv6_addresses:
        addresses += ipv6_addresses.split(" ")

    return "", ", ".join(addresses)


def make_host_addresses_additional_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_addresses_additional",
        title=_l("Host addresses (additional)"),
        short_title=_l("Add. addresses"),
        columns=["host_custom_variable_names", "host_custom_variable_values"],
        render=_render_host_addresses_additional,
    )


def _render_host_address_family(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_custom_var("host", "ADDRESS_FAMILY", row)


def make_host_address_family_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_address_family",
        title=_l("Host address family (primary)"),
        short_title=_l("Address family"),
        columns=["host_custom_variable_names", "host_custom_variable_values"],
        render=_render_host_address_family,
    )


def _render_host_address_families(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    custom_vars = dict(zip(row["host_custom_variable_names"], row["host_custom_variable_values"]))

    primary = custom_vars.get("ADDRESS_FAMILY", "4")

    families = [primary]
    if primary == "6" and custom_vars.get("ADDRESS_4"):
        families.append("4")
    elif primary == "4" and custom_vars.get("ADDRESS_6"):
        families.append("6")

    return "", ", ".join(families)


def make_host_address_families_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_address_families",
        title=_l("Host address families"),
        short_title=_l("Address families"),
        columns=["host_custom_variable_names", "host_custom_variable_values"],
        render=_render_host_address_families,
    )


def paint_svc_count(id_: int | str, count: int) -> CellSpec:
    if count > 0:
        return "count svcstate state%s" % id_, str(count)
    return "count svcstate", "0"


def paint_host_count(id_: int | None, count: int) -> CellSpec:
    if count > 0:
        if id_ is not None:
            return "count hstate hstate%s" % id_, str(count)
        # pending
        return "count hstate hstatep", str(count)
    return "count hstate", "0"


def _render_num_services(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, str(row["host_num_services"]))


def make_num_services_painter() -> InternalPainter:
    return InternalPainter(
        ident="num_services",
        title=_l("Number of services"),
        short_title="",
        columns=["host_num_services"],
        title_classes=["right"],
        render=_render_num_services,
    )


def _render_num_services_ok(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(0, row["host_num_services_ok"])


def make_num_services_ok_painter() -> InternalPainter:
    return InternalPainter(
        ident="num_services_ok",
        title=_l("Number of services in state OK"),
        short_title=_l("OK"),
        columns=["host_num_services_ok"],
        title_classes=["right"],
        render=_render_num_services_ok,
    )


def _render_num_problems(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(
        "s",
        row["host_num_services"] - row["host_num_services_ok"] - row["host_num_services_pending"],
    )


def make_num_problems_painter() -> InternalPainter:
    return InternalPainter(
        ident="num_problems",
        title=_l("Number of problems"),
        short_title=_l("Prob."),
        columns=["host_num_services", "host_num_services_ok", "host_num_services_pending"],
        title_classes=["right"],
        render=_render_num_problems,
    )


def _render_num_services_warn(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(1, row["host_num_services_warn"])


def make_num_services_warn_painter() -> InternalPainter:
    return InternalPainter(
        ident="num_services_warn",
        title=_l("Number of services in state WARN"),
        short_title=_l("Wa"),
        columns=["host_num_services_warn"],
        title_classes=["right"],
        render=_render_num_services_warn,
    )


def _render_num_services_crit(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(2, row["host_num_services_crit"])


def make_num_services_crit_painter() -> InternalPainter:
    return InternalPainter(
        ident="num_services_crit",
        title=_l("Number of services in state CRIT"),
        short_title=_l("Cr"),
        columns=["host_num_services_crit"],
        title_classes=["right"],
        render=_render_num_services_crit,
    )


def _render_num_services_unknown(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(3, row["host_num_services_unknown"])


def make_num_services_unknown_painter() -> InternalPainter:
    return InternalPainter(
        ident="num_services_unknown",
        title=_l("Number of services in state UNKNOWN"),
        short_title=_l("Un"),
        columns=["host_num_services_unknown"],
        title_classes=["right"],
        render=_render_num_services_unknown,
    )


def _render_num_services_pending(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count("p", row["host_num_services_pending"])


def make_num_services_pending_painter() -> InternalPainter:
    return InternalPainter(
        ident="num_services_pending",
        title=_l("Number of services in state PENDING"),
        short_title=_l("Pd"),
        columns=["host_num_services_pending"],
        title_classes=["right"],
        render=_render_num_services_pending,
    )


def _paint_service_list(row: Row, columnname: str, *, renderer: RenderLink) -> CellSpec:
    def sort_key(entry: tuple[str, int, int] | tuple[str, str, int, int]) -> tuple[str, ...]:
        if columnname.startswith("servicegroup") and isinstance(entry[1], str):
            return entry[0].lower(), entry[1].lower()
        return (entry[0].lower(),)

    h = HTML.empty()
    for entry in sorted(row[columnname], key=sort_key):
        if columnname.startswith("servicegroup"):
            host, svc, state, checked = entry
            text = host + " ~ " + svc
        else:
            svc, state, checked = entry
            host = row["host_name"]
            text = svc

        link = renderer.link_from_filename(
            "view.py",
            html_text=text,
            query_args=[
                ("view_name", "service"),
                ("site", row["site"]),
                ("host", host),
                ("service", svc),
            ],
        )

        css = "state%d" % state if checked else "statep"

        h += HTMLWriter.render_div(HTMLWriter.render_span(link), class_=css)

    return "", HTMLWriter.render_div(h, class_="objectlist")


def _parameters_host_services(_context: PainterContext) -> Dictionary:
    choices: ListChoiceChoices = [
        (0, _("OK")),
        (1, _("WARN")),
        (2, _("CRIT")),
        (3, _("UNKN")),
        ("p", _("PEND")),
    ]
    elements: DictionaryElements = [
        (
            "render_states",
            ListChoice(
                choices=choices,
                toggle_all=True,
                default_value=[0, 1, 2, 3, "p"],
                title=_("Only show services in this states"),
                help=_(
                    "Here, you can configure which services are displayed depending on "
                    "their state. This is a filter at display level not query level."
                ),
            ),
        )
    ]

    return Dictionary(elements=elements, title=_("Options"))


def _render_host_services(
    row: Row, cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    if (params := cell.painter_parameters()) is None:
        params = {}

    render_states = params.get("render_states", [0, 1, 2, 3, "p"])
    render_pend = [1]
    if "p" in render_states:
        render_pend.append(0)

    filtered_services = []
    for svc, state, checked in row["host_services_with_state"]:
        if state in render_states and checked in render_pend:
            filtered_services.append([svc, state, checked])

    row["host_services_with_state_filtered"] = filtered_services

    return _paint_service_list(
        row, "host_services_with_state_filtered", renderer=context.url_renderer
    )


def make_host_services_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_services",
        title=_l("Services colored according to state"),
        short_title=_l("Services"),
        columns=["host_name", "host_services_with_state"],
        parameters=_parameters_host_services,
        render=_render_host_services,
    )


def _render_host_parents(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_host_list(row["site"], row["host_parents"], request=context.request)


def make_host_parents_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_parents",
        title=_l("Host's parents"),
        short_title=_l("Parents"),
        columns=["host_parents"],
        use_painter_link=False,
        render=_render_host_parents,
    )


def _render_host_childs(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_host_list(row["site"], row["host_childs"], request=context.request)


def make_host_childs_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_childs",
        title=_l("Host's children"),
        short_title=_l("children"),
        columns=["host_childs"],
        use_painter_link=False,
        render=_render_host_childs,
    )


def _group_by_host_group_memberlist(
    row: Row, _cell: Cell, _context: PainterContext
) -> tuple[str, ...]:
    return tuple(row["host_groups"])


def _render_host_group_memberlist(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    links = []
    for group in row["host_groups"]:
        link = context.url_renderer.link_from_filename(
            "view.py",
            html_text=group,
            query_args=[
                ("view_name", "hostgroup"),
                ("hostgroup", group),
            ],
        )
        links.append(link)
    return "", HTML.without_escaping(", ").join(links)


def _export_for_csv_host_group_memberlist(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str:
    return ", ".join(row["host_groups"])


def _export_for_json_host_group_memberlist(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> object:
    return row["host_groups"]


def make_host_group_memberlist_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_group_memberlist",
        title=_l("Host groups the host is member of"),
        short_title=_l("Groups"),
        columns=["host_groups"],
        use_painter_link=False,
        group_by=_group_by_host_group_memberlist,
        render=_render_host_group_memberlist,
        export_for_csv=_export_for_csv_host_group_memberlist,
        export_for_json=_export_for_json_host_group_memberlist,
    )


def _render_host_contacts(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, ", ".join(row["host_contacts"]))


def make_host_contacts_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_contacts",
        title=_l("Host contacts"),
        short_title=_l("Contacts"),
        columns=["host_contacts"],
        render=_render_host_contacts,
    )


def _render_host_contact_groups(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, ", ".join(row["host_contact_groups"]))


def make_host_contact_groups_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_contact_groups",
        title=_l("Host contact groups"),
        short_title=_l("Contact groups"),
        columns=["host_contact_groups"],
        render=_render_host_contact_groups,
    )


def _render_host_custom_notes(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_custom_notes("hosts", row, site_configs=context.config.sites)


def make_host_custom_notes_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_custom_notes",
        title=_l("Custom host notes"),
        short_title=_l("Notes"),
        columns=["host_name", "host_address", "host_plugin_output"],
        render=_render_host_custom_notes,
    )


def _render_host_comments(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _paint_comments("host_", row)


def make_host_comments_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_comments",
        title=_l("Host comments"),
        short_title=_l("Comments"),
        columns=["host_comments_with_info"],
        render=_render_host_comments,
    )


def _render_host_in_downtime(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "host_scheduled_downtime_depth", True)


def make_host_in_downtime_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_in_downtime",
        title=_l("Host in downtime"),
        short_title=_l("Downtime"),
        columns=["host_scheduled_downtime_depth"],
        render=_render_host_in_downtime,
    )


def _render_host_acknowledged(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_nagiosflag(row, "host_acknowledged", False)


def make_host_acknowledged_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_acknowledged",
        title=_l("Host problem acknowledged"),
        short_title=_l("Ack"),
        columns=["host_acknowledged"],
        render=_render_host_acknowledged,
    )


def _render_host_staleness(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", "%0.2f" % row.get("host_staleness", 0))


def make_host_staleness_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_staleness",
        title=_l("Host staleness value"),
        short_title=_l("Staleness"),
        columns=["host_staleness"],
        render=_render_host_staleness,
    )


def _render_host_is_stale(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_is_stale(row, context.config.staleness_threshold)


def make_host_is_stale_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_is_stale",
        title=_l("Host is stale"),
        short_title=_l("Stale"),
        columns=["host_staleness"],
        sorter="svc_staleness",
        render=_render_host_is_stale,
    )


_HOST_CUSTOM_VARIABLES_BLACKLIST: list[str] = [
    "FILENAME",
    "TAGS",
    "ADDRESS_4",
    "ADDRESS_6",
    "ADDRESS_FAMILY",
    "NODEIPS",
    "NODEIPS_4",
    "NODEIPS_6",
    RELATIONS_CUSTOM_VARIABLE,
]


def _group_by_host_custom_variables(
    row: Row, _cell: Cell, _context: PainterContext
) -> tuple[tuple[str, str], ...]:
    return tuple(
        item
        for item in row["host_custom_variables"].items()
        if item[0] not in _HOST_CUSTOM_VARIABLES_BLACKLIST
    )


def _render_host_custom_variables(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _paint_custom_vars("host", row, _HOST_CUSTOM_VARIABLES_BLACKLIST)


def _export_for_csv_host_custom_variables(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str:
    return _export_custom_vars("host", row, _HOST_CUSTOM_VARIABLES_BLACKLIST)


def _export_for_json_host_custom_variables(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> str:
    return _export_custom_vars("host", row, _HOST_CUSTOM_VARIABLES_BLACKLIST)


def make_host_custom_vars_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_custom_vars",
        title=_l("Host custom attributes"),
        columns=["host_custom_variables"],
        group_by=_group_by_host_custom_variables,
        render=_render_host_custom_variables,
        export_for_csv=_export_for_csv_host_custom_variables,
        export_for_json=_export_for_json_host_custom_variables,
    )


def _paint_discovery_output(
    field: str,
    row: Row,
    *,
    renderer: RenderLink,
    theme: Theme,
) -> CellSpec:
    value: str = row[field]
    if field == "discovery_state":
        ruleset_url = "wato.py?mode=edit_ruleset&varname=ignored_services"
        discovery_url = "wato.py?mode=inventory&host=%s&mode=inventory" % row["host_name"]

        return (
            None,
            {
                "ignored": HTMLGenerator.render_icon_button(
                    ruleset_url,
                    _("Disabled (configured away by admin)"),
                    StaticIcon(IconNames.rulesets),
                    theme=theme,
                )
                + HTML.with_escaping(_("Disabled (configured away by admin)")),
                "vanished": HTMLGenerator.render_icon_button(
                    discovery_url,
                    _("Vanished (checked, but no longer exists)"),
                    StaticIcon(IconNames.services),
                    theme=theme,
                )
                + HTML.with_escaping(_("Vanished (checked, but no longer exists)")),
                "unmonitored": HTMLGenerator.render_icon_button(
                    discovery_url,
                    _("Available (missing)"),
                    StaticIcon(IconNames.services),
                    theme=theme,
                )
                + HTML.with_escaping(_("Available (missing)")),
            }.get(value, value),
        )
    if not (field == "discovery_service" and row["discovery_state"] == "vanished"):
        return None, value

    href = renderer.link_from_filename(
        "view.py",
        html_text=value,
        query_args=[
            ("view_name", "service"),
            ("site", row["site"]),
            ("host", row["host_name"]),
            ("service", value),
        ],
    )
    return None, HTMLWriter.render_div(href)


def _render_service_discovery_state(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_discovery_output(
        "discovery_state", row, renderer=context.url_renderer, theme=context.theme
    )


def make_service_discovery_state_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_discovery_state",
        title=_l("Service discovery: State"),
        short_title=_l("State"),
        columns=["discovery_state"],
        render=_render_service_discovery_state,
    )


def _render_service_discovery_check(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_discovery_output(
        "discovery_check", row, renderer=context.url_renderer, theme=context.theme
    )


def make_service_discovery_check_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_discovery_check",
        title=_l("Service discovery: Check type"),
        short_title=_l("Check type"),
        columns=["discovery_state", "discovery_check", "discovery_service"],
        render=_render_service_discovery_check,
    )


def _render_service_discovery_service(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_discovery_output(
        "discovery_service", row, renderer=context.url_renderer, theme=context.theme
    )


def make_service_discovery_service_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_discovery_service",
        title=_l("Service discovery: Service name"),
        short_title=_l("Service name"),
        columns=["discovery_state", "discovery_check", "discovery_service"],
        render=_render_service_discovery_service,
    )


#    _   _           _
#   | | | | ___  ___| |_ __ _ _ __ ___  _   _ _ __  ___
#   | |_| |/ _ \/ __| __/ _` | '__/ _ \| | | | '_ \/ __|
#   |  _  | (_) \__ \ || (_| | | | (_) | |_| | |_) \__ \
#   |_| |_|\___/|___/\__\__, |_|  \___/ \__,_| .__/|___/
#                       |___/                |_|
def _render_hostgroup_hosts(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    divs = []
    for host, state, checked in row["hostgroup_members_with_state"]:
        link = context.url_renderer.link_from_filename(
            "view.py",
            html_text=host,
            query_args=[
                ("view_name", "host"),
                ("site", row["site"]),
                ("host", host),
            ],
        )
        css = "hstate%d" % state if checked else "hstatep"
        divs.append(HTMLWriter.render_div(link, class_=css))
    return "", HTMLWriter.render_div(HTML.empty().join(divs), class_="objectlist")


def make_hostgroup_hosts_painter() -> InternalPainter:
    return InternalPainter(
        ident="hostgroup_hosts",
        title=_l("Hosts colored according to state (host group)"),
        short_title=_l("Hosts"),
        columns=["hostgroup_members_with_state"],
        render=_render_hostgroup_hosts,
    )


def _render_hg_num_services(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, str(row["hostgroup_num_services"]))


def make_hg_num_services_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_num_services",
        title=_l("Number of services (host group)"),
        short_title="",
        columns=["hostgroup_num_services"],
        render=_render_hg_num_services,
    )


def _render_hg_num_services_ok(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(0, row["hostgroup_num_services_ok"])


def make_hg_num_services_ok_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_num_services_ok",
        title=_l("Number of services in state OK (host group)"),
        short_title=_l("O"),
        columns=["hostgroup_num_services_ok"],
        title_classes=["right"],
        render=_render_hg_num_services_ok,
    )


def _render_hg_num_services_warn(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(1, row["hostgroup_num_services_warn"])


def make_hg_num_services_warn_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_num_services_warn",
        title=_l("Number of services in state WARN (host group)"),
        short_title=_l("W"),
        columns=["hostgroup_num_services_warn"],
        title_classes=["right"],
        render=_render_hg_num_services_warn,
    )


def _render_hg_num_services_crit(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(2, row["hostgroup_num_services_crit"])


def make_hg_num_services_crit_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_num_services_crit",
        title=_l("Number of services in state CRIT (host group)"),
        short_title=_l("C"),
        columns=["hostgroup_num_services_crit"],
        title_classes=["right"],
        render=_render_hg_num_services_crit,
    )


def _render_hg_num_services_unknown(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(3, row["hostgroup_num_services_unknown"])


def make_hg_num_services_unknown_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_num_services_unknown",
        title=_l("Number of services in state UNKNOWN (host group)"),
        short_title=_l("U"),
        columns=["hostgroup_num_services_unknown"],
        title_classes=["right"],
        render=_render_hg_num_services_unknown,
    )


def _render_hg_num_services_pending(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count("p", row["hostgroup_num_services_pending"])


def make_hg_num_services_pending_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_num_services_pending",
        title=_l("Number of services in state PENDING (host group)"),
        short_title=_l("P"),
        columns=["hostgroup_num_services_pending"],
        title_classes=["right"],
        render=_render_hg_num_services_pending,
    )


def _render_hg_num_hosts_up(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_host_count(0, row["hostgroup_num_hosts_up"])


def make_hg_num_hosts_up_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_num_hosts_up",
        title=_l("Number of hosts in state UP (host group)"),
        short_title=_l("Up"),
        columns=["hostgroup_num_hosts_up"],
        title_classes=["right"],
        render=_render_hg_num_hosts_up,
    )


def _render_hg_num_hosts_down(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_host_count(1, row["hostgroup_num_hosts_down"])


def make_hg_num_hosts_down_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_num_hosts_down",
        title=_l("Number of hosts in state DOWN (host group)"),
        short_title=_l("Dw"),
        columns=["hostgroup_num_hosts_down"],
        title_classes=["right"],
        render=_render_hg_num_hosts_down,
    )


def _render_hg_num_hosts_unreach(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_host_count(2, row["hostgroup_num_hosts_unreach"])


def make_hg_num_hosts_unreach_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_num_hosts_unreach",
        title=_l("Number of hosts in state UNREACH (host group)"),
        short_title=_l("Un"),
        columns=["hostgroup_num_hosts_unreach"],
        title_classes=["right"],
        render=_render_hg_num_hosts_unreach,
    )


def _render_hg_num_hosts_pending(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_host_count(None, row["hostgroup_num_hosts_pending"])


def make_hg_num_hosts_pending_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_num_hosts_pending",
        title=_l("Number of hosts in state PENDING (host group)"),
        short_title=_l("Pd"),
        columns=["hostgroup_num_hosts_pending"],
        title_classes=["right"],
        render=_render_hg_num_hosts_pending,
    )


def _render_hg_name(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["hostgroup_name"])


def make_hg_name_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_name",
        title=_l("Host group name"),
        short_title=_l("Name"),
        columns=["hostgroup_name"],
        render=_render_hg_name,
    )


def _render_hg_alias(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["hostgroup_alias"])


def make_hg_alias_painter() -> InternalPainter:
    return InternalPainter(
        ident="hg_alias",
        title=_l("Host group alias"),
        short_title=_l("Alias"),
        columns=["hostgroup_alias"],
        render=_render_hg_alias,
    )


#    ____                  _
#   / ___|  ___ _ ____   _(_) ___ ___  __ _ _ __ ___  _   _ _ __  ___
#   \___ \ / _ \ '__\ \ / / |/ __/ _ \/ _` | '__/ _ \| | | | '_ \/ __|
#    ___) |  __/ |   \ V /| | (_|  __/ (_| | | | (_) | |_| | |_) \__ \
#   |____/ \___|_|    \_/ |_|\___\___|\__, |_|  \___/ \__,_| .__/|___/
#                                     |___/                |_|


def _render_sg_services(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _paint_service_list(
        row, "servicegroup_members_with_state", renderer=context.url_renderer
    )


def make_sg_services_painter() -> InternalPainter:
    return InternalPainter(
        ident="sg_services",
        title=_l("Services colored according to state (service group)"),
        short_title=_l("Services"),
        columns=["servicegroup_members_with_state"],
        render=_render_sg_services,
    )


def _render_sg_num_services(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, str(row["servicegroup_num_services"]))


def make_sg_num_services_painter() -> InternalPainter:
    return InternalPainter(
        ident="sg_num_services",
        title=_l("Number of services (service group)"),
        short_title="",
        columns=["servicegroup_num_services"],
        render=_render_sg_num_services,
    )


def _render_sg_num_services_ok(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(0, row["servicegroup_num_services_ok"])


def make_sg_num_services_ok_painter() -> InternalPainter:
    return InternalPainter(
        ident="sg_num_services_ok",
        title=_l("Number of services in state OK (service group)"),
        short_title=_l("O"),
        columns=["servicegroup_num_services_ok"],
        render=_render_sg_num_services_ok,
    )


def _render_sg_num_services_warn(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(1, row["servicegroup_num_services_warn"])


def make_sg_num_services_warn_painter() -> InternalPainter:
    return InternalPainter(
        ident="sg_num_services_warn",
        title=_l("Number of services in state WARN (service group)"),
        short_title=_l("W"),
        columns=["servicegroup_num_services_warn"],
        render=_render_sg_num_services_warn,
    )


def _render_sg_num_services_crit(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(2, row["servicegroup_num_services_crit"])


def make_sg_num_services_crit_painter() -> InternalPainter:
    return InternalPainter(
        ident="sg_num_services_crit",
        title=_l("Number of services in state CRIT (service group)"),
        short_title=_l("C"),
        columns=["servicegroup_num_services_crit"],
        render=_render_sg_num_services_crit,
    )


def _render_sg_num_services_unknown(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(3, row["servicegroup_num_services_unknown"])


def make_sg_num_services_unknown_painter() -> InternalPainter:
    return InternalPainter(
        ident="sg_num_services_unknown",
        title=_l("Number of services in state UNKNOWN (service group)"),
        short_title=_l("U"),
        columns=["servicegroup_num_services_unknown"],
        render=_render_sg_num_services_unknown,
    )


def _render_sg_num_services_pending(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count("p", row["servicegroup_num_services_pending"])


def make_sg_num_services_pending_painter() -> InternalPainter:
    return InternalPainter(
        ident="sg_num_services_pending",
        title=_l("Number of services in state PENDING (service group)"),
        short_title=_l("P"),
        columns=["servicegroup_num_services_pending"],
        render=_render_sg_num_services_pending,
    )


def _render_sg_name(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["servicegroup_name"])


def make_sg_name_painter() -> InternalPainter:
    return InternalPainter(
        ident="sg_name",
        title=_l("Service group name"),
        short_title=_l("Name"),
        columns=["servicegroup_name"],
        render=_render_sg_name,
    )


def _render_sg_alias(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["servicegroup_alias"])


def make_sg_alias_painter() -> InternalPainter:
    return InternalPainter(
        ident="sg_alias",
        title=_l("Service group alias"),
        short_title=_l("Alias"),
        columns=["servicegroup_alias"],
        render=_render_sg_alias,
    )


#     ____                                     _
#    / ___|___  _ __ ___  _ __ ___   ___ _ __ | |_ ___
#   | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \| __/ __|
#   | |__| (_) | | | | | | | | | | |  __/ | | | |_\__ \
#    \____\___/|_| |_| |_|_| |_| |_|\___|_| |_|\__|___/
#


def _render_comment_id(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, str(row["comment_id"]))


def make_comment_id_painter() -> InternalPainter:
    return InternalPainter(
        ident="comment_id",
        title=_l("Comment ID"),
        short_title=_l("ID"),
        columns=["comment_id"],
        render=_render_comment_id,
    )


def _render_comment_author(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["comment_author"])


def make_comment_author_painter() -> InternalPainter:
    return InternalPainter(
        ident="comment_author",
        title=_l("Comment author"),
        short_title=_l("Author"),
        columns=["comment_author"],
        render=_render_comment_author,
    )


def _render_comment_comment(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return (
        None,
        format_plugin_output(
            row["comment_comment"],
            request=context.request,
            must_escape=determine_must_escape(context.config.sites, row),
            row=row,
        ),
    )


def make_comment_comment_painter() -> InternalPainter:
    return InternalPainter(
        ident="comment_comment",
        title=_l("Comment text"),
        columns=["comment_comment"],
        render=_render_comment_comment,
    )


def _render_comment_what(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["comment_type"] == 1 and _("Host") or _("Service"))


def make_comment_what_painter() -> InternalPainter:
    return InternalPainter(
        ident="comment_what",
        title=_l("Comment type (host/service)"),
        short_title=_l("Type"),
        columns=["comment_type"],
        render=_render_comment_what,
    )


def _render_comment_time(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age(
        row["comment_entry_time"],
        True,
        3600,
        request=context.request,
        painter_options=context.painter_options,
    )


def make_comment_time_painter() -> InternalPainter:
    return InternalPainter(
        ident="comment_time",
        title=_l("Comment entry time"),
        short_title=_l("Time"),
        columns=["comment_entry_time"],
        painter_options=["ts_format", "ts_date"],
        render=_render_comment_time,
    )


def _render_comment_expires(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age(
        row["comment_expire_time"],
        row["comment_expire_time"] != 0,
        3600,
        request=context.request,
        painter_options=context.painter_options,
        what="future",
    )


def make_comment_expires_painter() -> InternalPainter:
    return InternalPainter(
        ident="comment_expires",
        title=_l("Comment expiry time"),
        short_title=_l("Expires"),
        columns=["comment_expire_time"],
        painter_options=["ts_format", "ts_date"],
        render=_render_comment_expires,
    )


def _render_comment_entry_type(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    t = row["comment_entry_type"]
    linkview = None
    if t == 1:
        icon = StaticIcon(IconNames.comment)
        help_txt = _("Comment")
    elif t == 2:
        icon = StaticIcon(IconNames.downtime)
        help_txt = _("Downtime")
        linkview = "downtimes_of_service" if row["service_description"] else "downtimes_of_host"

    elif t == 3:
        icon = StaticIcon(IconNames.flapping)
        help_txt = _("Flapping")
    elif t == 4:
        icon = StaticIcon(IconNames.ack)
        help_txt = _("Acknowledgment")
    else:
        return "", ""
    code: str | HTML = HTMLGenerator.render_static_icon(icon, title=help_txt)
    if linkview:
        code = render_link_to_view(
            code,
            row,
            VisualLinkSpec("views", linkview),
            context.user_permissions,
            request=context.request,
        )
    return "icons", code


def make_comment_entry_type_painter() -> InternalPainter:
    return InternalPainter(
        ident="comment_entry_type",
        title=_l("Comment entry type (user/downtime/flapping/ack)"),
        short_title=_l("E.Type"),
        columns=["comment_entry_type", "host_name", "service_description"],
        render=_render_comment_entry_type,
    )


#    ____                      _   _
#   |  _ \  _____      ___ __ | |_(_)_ __ ___   ___  ___
#   | | | |/ _ \ \ /\ / / '_ \| __| | '_ ` _ \ / _ \/ __|
#   | |_| | (_) \ V  V /| | | | |_| | | | | | |  __/\__ \
#   |____/ \___/ \_/\_/ |_| |_|\__|_|_| |_| |_|\___||___/
#


def _render_downtime_id(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, "%d" % row["downtime_id"])


def make_downtime_id_painter() -> InternalPainter:
    return InternalPainter(
        ident="downtime_id",
        title=_l("Downtime ID"),
        short_title=_l("ID"),
        columns=["downtime_id"],
        render=_render_downtime_id,
    )


def _render_downtime_author(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["downtime_author"])


def make_downtime_author_painter() -> InternalPainter:
    return InternalPainter(
        ident="downtime_author",
        title=_l("Downtime author"),
        short_title=_l("Author"),
        columns=["downtime_author"],
        render=_render_downtime_author,
    )


def _render_downtime_comment(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return (
        None,
        format_plugin_output(
            row["downtime_comment"],
            request=context.request,
            must_escape=determine_must_escape(context.config.sites, row),
            row=row,
        ),
    )


def make_downtime_comment_painter() -> InternalPainter:
    return InternalPainter(
        ident="downtime_comment",
        title=_l("Downtime comment"),
        short_title=_l("Comment"),
        columns=["downtime_comment"],
        render=_render_downtime_comment,
    )


def _render_downtime_fixed(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["downtime_fixed"] == 0 and _("flexible") or _("fixed"))


def make_downtime_fixed_painter() -> InternalPainter:
    return InternalPainter(
        ident="downtime_fixed",
        title=_l("Downtime start mode"),
        short_title=_l("Mode"),
        columns=["downtime_fixed"],
        render=_render_downtime_fixed,
    )


def _render_downtime_origin(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["downtime_origin"] == 1 and _("configuration") or _("command"))


def make_downtime_origin_painter() -> InternalPainter:
    return InternalPainter(
        ident="downtime_origin",
        title=_l("Downtime origin"),
        short_title=_l("Origin"),
        columns=["downtime_origin"],
        render=_render_downtime_origin,
    )


def _render_downtime_what(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["downtime_is_service"] and _("Service") or _("Host"))


def make_downtime_what_painter() -> InternalPainter:
    return InternalPainter(
        ident="downtime_what",
        title=_l("Downtime for host/service"),
        short_title=_l("for"),
        columns=["downtime_is_service"],
        render=_render_downtime_what,
    )


def _render_downtime_type(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return (None, row["is_pending"] == 0 and _("active") or _("pending"))


def make_downtime_type_painter() -> InternalPainter:
    return InternalPainter(
        ident="downtime_type",
        title=_l("Downtime active or pending"),
        short_title=_l("act/pend"),
        columns=["is_pending"],
        render=_render_downtime_type,
    )


def _render_downtime_entry_time(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age(
        row["downtime_entry_time"],
        True,
        3600,
        request=context.request,
        painter_options=context.painter_options,
    )


def make_downtime_entry_time_painter() -> InternalPainter:
    return InternalPainter(
        ident="downtime_entry_time",
        title=_l("Downtime entry time"),
        short_title=_l("Entry"),
        columns=["downtime_entry_time"],
        painter_options=["ts_format", "ts_date"],
        render=_render_downtime_entry_time,
    )


def _render_downtime_start_time(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age(
        row["downtime_start_time"],
        True,
        3600,
        request=context.request,
        painter_options=context.painter_options,
        what="both",
    )


def make_downtime_start_time_painter() -> InternalPainter:
    return InternalPainter(
        ident="downtime_start_time",
        title=_l("Downtime start time"),
        short_title=_l("Start"),
        columns=["downtime_start_time"],
        painter_options=["ts_format", "ts_date"],
        render=_render_downtime_start_time,
    )


def _render_downtime_end_time(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age(
        row["downtime_end_time"],
        True,
        3600,
        request=context.request,
        painter_options=context.painter_options,
        what="both",
    )


def make_downtime_end_time_painter() -> InternalPainter:
    return InternalPainter(
        ident="downtime_end_time",
        title=_l("Downtime end time"),
        short_title=_l("End"),
        columns=["downtime_end_time"],
        painter_options=["ts_format", "ts_date"],
        render=_render_downtime_end_time,
    )


def _render_downtime_duration(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    if row["downtime_fixed"] == 0:
        return "number", "%02d:%02d:00" % divmod(int(row["downtime_duration"] / 60.0), 60)
    return "", ""


def make_downtime_duration_painter() -> InternalPainter:
    return InternalPainter(
        ident="downtime_duration",
        title=_l("Downtime duration (if flexible)"),
        short_title=_l("Flex. duration"),
        columns=["downtime_duration", "downtime_fixed"],
        render=_render_downtime_duration,
    )


#    _
#   | |    ___   __ _
#   | |   / _ \ / _` |
#   | |__| (_) | (_| |
#   |_____\___/ \__, |
#               |___/


def _parameters_log_details_history(_context: PainterContext) -> Dictionary:
    return Dictionary(
        elements=[
            (
                "max_len",
                Integer(
                    title=_("Maximum number of characters to show"),
                    help=_(
                        "Truncate content at this amount of characters. "
                        "A zero value means not to truncate."
                    ),
                    default_value=0,
                    minvalue=0,
                ),
            ),
        ],
    )


def _render_log_details_history(
    row: Row, cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    if (params := cell.painter_parameters()) is None:
        params = {}

    max_len = params.get("max_len", 0)
    long_output = row["log_long_plugin_output"]
    long_output_len = len(long_output)

    if 0 < max_len < len(long_output):
        long_output = long_output[:max_len] + "..."

    # See werk #15523.
    is_ps_check = row["service_check_command"] == "check_mk-ps"
    # We can only display tables if they are complete.
    non_displayable_html = "<table>" in long_output and not long_output.endswith("</table>")
    # Only hand over relevant row to ensure correct escaping options in
    # case of ps_check. Otherwise "ESCAPE_PLUGIN_OUTPUT" would be used in
    # format_plugin_output()
    row_to_format = (
        {"log_long_plugin_output": long_output} if is_ps_check and non_displayable_html else row
    )
    content = format_plugin_output(
        long_output,
        request=context.request,
        row=row_to_format,
        must_escape=determine_must_escape(context.config.sites, row),
        newlineishs_to_brs=True,
    )

    if is_ps_check:
        content = HTML.without_escaping(str(content).replace("&bsol%3B", "\\"))

    # has to be placed after format_plugin_output() to keep links save from
    # escaping
    host_custom_variables: dict = row.get("host_custom_variables", {})
    custom_vars = row.get("service_custom_variables", host_custom_variables)
    escape_plugin_output = custom_vars.get("ESCAPE_PLUGIN_OUTPUT", "1") == "0"
    if long_output_len > max_len and escape_plugin_output and non_displayable_html:
        setting_link_tag = context.url_renderer.link_from_filename(
            "global_settings.py",
            html_text="(%s)" % _("Increase limit for future entries"),
            query_args=[("varname", "max_long_output_size")],
        )
        content = (
            _("HTML output cannot be rendered because of truncated data. ")
            + setting_link_tag
            + HTMLWriter.render_b("WARN", class_="stmark state1")
            + HTMLWriter.render_br()
            + content
        )

    return paint_stalified(row, content, context.config.staleness_threshold)


def make_log_details_history_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_details_history",
        title=_l("Log: Details"),
        columns=[
            "log_long_plugin_output",
            "service_check_command",
            "service_custom_variables",
            "host_custom_variables",
        ],
        parameters=_parameters_log_details_history,
        render=_render_log_details_history,
    )


def _render_log_message(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", row["log_message"])


def make_log_message_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_message",
        title=_l("Log: complete message"),
        short_title=_l("Message"),
        columns=["log_message"],
        render=_render_log_message,
    )


def _render_log_plugin_output(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    if output := _decode_item_log_plugin_output(row, column="log_plugin_output"):
        return "", format_plugin_output(
            output,
            request=context.request,
            must_escape=determine_must_escape(context.config.sites, row),
            row=row,
        )

    if comment := _decode_item_log_plugin_output(row, column="log_comment"):
        return "", comment

    log_type = row["log_type"]
    lst = row["log_state_type"]
    if "FLAPPING" in log_type:
        what = _("host") if "HOST" in log_type else _("service")
        if lst == "STOPPED":
            return "", _("The %(what)s stopped flapping") % {"what": what}
        return "", _("The %(what)s started flapping") % {"what": what}
    if lst:
        return "", (lst + " - " + log_type)
    return "", ""


def make_log_plugin_output_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_plugin_output",
        title=_l("Log: Summary"),
        short_title=_l("Summary"),
        columns=["log_plugin_output", "log_type", "log_state_type", "log_comment"],
        render=_render_log_plugin_output,
    )


def _decode_item_log_plugin_output(
    row: Row, *, column: Literal["log_plugin_output", "log_comment"]
) -> str:
    # TODO: decode all escaped characters coming from monitoring history.
    return row.get(column, "").replace("%3B", ";")


def _render_log_what(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    lt = row["log_type"]
    if "HOST" in lt:
        return "", _("Host")
    if "SERVICE" in lt or "SVC" in lt:
        return "", _("Service")
    return "", _("Program")


def make_log_what_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_what",
        title=_l("Log: host or service"),
        short_title=_l("Host/service"),
        columns=["log_type"],
        render=_render_log_what,
    )


def _render_log_attempt(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", str(row["log_attempt"]))


def make_log_attempt_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_attempt",
        title=_l("Log: number of check attempt"),
        short_title=_l("Att."),
        columns=["log_attempt"],
        render=_render_log_attempt,
    )


def _render_log_state_type(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", row["log_state_type"])


def make_log_state_type_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_state_type",
        title=_l('Log: state type (DEPRECATED: Use "state information")'),
        short_title=_l("Type"),
        columns=["log_state_type"],
        render=_render_log_state_type,
    )


def _render_log_state_info(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    info = row["log_state_info"]

    # be compatible to <1.7 remote sites and show log_state_type content as fallback
    if not info:
        info = row["log_state_type"]

    return ("", info)


def make_log_state_info_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_state_info",
        title=_l("Log: State information"),
        short_title=_l("State info"),
        columns=["log_state_info", "log_state_type"],
        render=_render_log_state_info,
    )


def _render_log_type(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("nowrap", row["log_type"])


def make_log_type_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_type",
        title=_l("Log: event"),
        short_title=_l("Event"),
        columns=["log_type"],
        render=_render_log_type,
    )


def _render_log_contact_name(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    target_view_name = context.url_renderer.get_filename(
        filename="contactnotifications",
        mobile_filename="mobile_contactnotifications",
    )
    links = [
        context.url_renderer.link_from_filename(
            "view.py",
            html_text=contact,
            query_args=[
                ("view_name", target_view_name),
                ("log_contact_name", contact),
            ],
            mobile_filename="mobile_view.py",
        )
        for contact in row["log_contact_name"].split(",")
    ]
    return "nowrap", HTML.without_escaping(", ").join(links)


def make_log_contact_name_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_contact_name",
        title=_l("Log: contact name"),
        short_title=_l("Contact"),
        columns=["log_contact_name"],
        render=_render_log_contact_name,
    )


def _render_log_command(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("nowrap", row["log_command_name"])


def make_log_command_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_command",
        title=_l("Log: command/plug-in"),
        short_title=_l("Command"),
        columns=["log_command_name"],
        render=_render_log_command,
    )


def _render_log_icon(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    img: StaticIcon | None = None
    log_type = row["log_type"]
    log_state = row["log_state"]

    if log_type == "SERVICE ALERT":
        img = {
            0: StaticIcon(IconNames.alert_ok),
            1: StaticIcon(IconNames.alert_warn),
            2: StaticIcon(IconNames.alert_crit),
            3: StaticIcon(IconNames.alert_unknown),
        }.get(row["log_state"])
        title = _("Service alert")

    elif log_type == "HOST ALERT":
        img = {
            0: StaticIcon(IconNames.alert_up),
            1: StaticIcon(IconNames.alert_down),
            2: StaticIcon(IconNames.alert_unreach),
        }.get(row["log_state"])
        title = _("Host alert")

    elif log_type.endswith("ALERT HANDLER STARTED"):
        img = StaticIcon(IconNames.alert_alert_handler_started)
        title = _("Alert handler started")

    elif log_type.endswith("ALERT HANDLER STOPPED"):
        if log_state == 0:
            img = StaticIcon(IconNames.alert_alert_handler_stopped)
            title = _("Alert handler stopped")
        else:
            img = StaticIcon(IconNames.alert_alert_handler_failed)
            title = _("Alert handler failed")

    elif "DOWNTIME" in log_type:
        if row["log_state_type"] in ["END", "STOPPED"]:
            img = StaticIcon(IconNames.alert_downtimestop)
            title = _("Downtime stopped")
        else:
            img = StaticIcon(IconNames.alert_downtime)
            title = _("Downtime")

    elif log_type.endswith("NOTIFICATION"):
        if row["log_command_name"] == "check-mk-notify":
            img = StaticIcon(IconNames.alert_cmk_notify)
            title = _("Core produced a notification")
        else:
            img = StaticIcon(IconNames.alert_notify)
            title = _("User notification")

    elif log_type.endswith("NOTIFICATION RESULT"):
        img = StaticIcon(IconNames.alert_notify_result)
        title = _("Final notification result")

    elif log_type.endswith("NOTIFICATION PROGRESS"):
        img = StaticIcon(IconNames.alert_notify_progress)
        title = _("The notification is being processed")

    elif log_type == "EXTERNAL COMMAND":
        img = StaticIcon(IconNames.alert_command)
        title = _("External command")

    elif "restarting..." in log_type:
        img = StaticIcon(IconNames.alert_restart)
        title = _("Core restarted")

    elif "Reloading configuration" in log_type:
        img = StaticIcon(IconNames.alert_reload)
        title = _("Core configuration reloaded")

    elif "starting..." in log_type:
        img = StaticIcon(IconNames.alert_start)
        title = _("Core started")

    elif "shutdown..." in log_type or "shutting down" in log_type:
        img = StaticIcon(IconNames.alert_stop)
        title = _("Core stopped")

    elif " FLAPPING " in log_type:
        img = StaticIcon(IconNames.alert_flapping)
        title = _("Flapping")

    elif "ACKNOWLEDGE ALERT" in log_type:
        if row["log_state_type"] == "STARTED":
            img = StaticIcon(IconNames.alert_ack)
            title = _("Acknowledged")
        else:
            img = StaticIcon(IconNames.alert_ackstop)
            title = _("Stopped acknowledgment")

    if img:
        return "icon", HTMLGenerator.render_static_icon(img, title=title)  # type: ignore[possibly-undefined]
    return "icon", ""


def make_log_icon_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_icon",
        title=_l("Log: event icon"),
        short_title="",
        columns=["log_type", "log_state", "log_state_type", "log_command_name"],
        render=_render_log_icon,
    )


def _render_log_options(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", row["log_options"])


def make_log_options_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_options",
        title=_l("Log: informational part of message"),
        short_title=_l("Info"),
        columns=["log_options"],
        render=_render_log_options,
    )


def _render_log_comment(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    msg = row["log_options"]
    if ";" in msg:
        parts = msg.split(";")
        if len(parts) > 6:
            return ("", parts[-1])
    return ("", "")


def make_log_comment_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_comment",
        title=_l("Log: comment"),
        short_title=_l("Comment"),
        columns=["log_options"],
        render=_render_log_comment,
    )


def _render_log_time(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return paint_age(
        row["log_time"],
        True,
        3600 * 24,
        request=context.request,
        painter_options=context.painter_options,
    )


def make_log_time_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_time",
        title=_l("Log: entry time"),
        short_title=_l("Time"),
        columns=["log_time"],
        painter_options=["ts_format", "ts_date"],
        render=_render_log_time,
    )


def _render_log_lineno(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("number", str(row["log_lineno"]))


def make_log_lineno_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_lineno",
        title=_l("Log: line number in log file"),
        short_title=_l("Line"),
        columns=["log_lineno"],
        render=_render_log_lineno,
    )


def _group_by_log_date(row: Row, _cell: Cell, _context: PainterContext) -> str:
    return str(_paint_day(row["log_time"])[1])


def _render_log_date(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return _paint_day(row["log_time"])


def make_log_date_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_date",
        title=_l("Log: day of entry"),
        short_title=_l("Date"),
        columns=["log_time"],
        group_by=_group_by_log_date,
        render=_render_log_date,
    )


def _render_log_state(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    state = row["log_state"]

    # Notification result/progress lines don't hold real states. They hold notification plugin
    # exit results (0: ok, 1: temp issue, 2: perm issue). We display them as service states.
    if (
        row["log_service_description"]
        or row["log_type"].endswith("NOTIFICATION RESULT")
        or row["log_type"].endswith("NOTIFICATION PROGRESS")
    ):
        return _paint_service_state_short(
            {"service_has_been_checked": 1, "service_state": state},
            staleness_threshold=context.config.staleness_threshold,
        )
    return _paint_host_state_short(
        {"host_has_been_checked": 1, "host_state": state},
        staleness_threshold=context.config.staleness_threshold,
    )


def make_log_state_painter() -> InternalPainter:
    return InternalPainter(
        ident="log_state",
        title=_l("Log: state of host/service at log time"),
        short_title=_l("State"),
        columns=["log_state", "log_state_type", "log_service_description", "log_type"],
        title_classes=["center"],
        render=_render_log_state,
    )


# Alert statistics


def _render_alert_stats_ok(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return ("", str(row["log_alerts_ok"]))


def make_alert_stats_ok_painter() -> InternalPainter:
    return InternalPainter(
        ident="alert_stats_ok",
        title=_l("Alert statistics: Number of recoveries"),
        short_title=_l("OK"),
        columns=["log_alerts_ok"],
        title_classes=["right"],
        render=_render_alert_stats_ok,
    )


def _render_alert_stats_warn(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(1, row["log_alerts_warn"])


def make_alert_stats_warn_painter() -> InternalPainter:
    return InternalPainter(
        ident="alert_stats_warn",
        title=_l("Alert statistics: Number of warnings"),
        short_title=_l("WARN"),
        columns=["log_alerts_warn"],
        title_classes=["right"],
        render=_render_alert_stats_warn,
    )


def _render_alert_stats_crit(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(2, row["log_alerts_crit"])


def make_alert_stats_crit_painter() -> InternalPainter:
    return InternalPainter(
        ident="alert_stats_crit",
        title=_l("Alert statistics: Number of critical alerts"),
        short_title=_l("CRIT"),
        columns=["log_alerts_crit"],
        title_classes=["right"],
        render=_render_alert_stats_crit,
    )


def _render_alert_stats_unknown(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count(3, row["log_alerts_unknown"])


def make_alert_stats_unknown_painter() -> InternalPainter:
    return InternalPainter(
        ident="alert_stats_unknown",
        title=_l("Alert statistics: Number of unknown alerts"),
        short_title=_l("UNKN"),
        columns=["log_alerts_unknown"],
        title_classes=["right"],
        render=_render_alert_stats_unknown,
    )


def _render_alert_stats_problem(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return paint_svc_count("s", row["log_alerts_problem"])


def make_alert_stats_problem_painter() -> InternalPainter:
    return InternalPainter(
        ident="alert_stats_problem",
        title=_l("Alert statistics: Number of problem alerts"),
        short_title=_l("Problems"),
        columns=["log_alerts_problem"],
        title_classes=["right"],
        render=_render_alert_stats_problem,
    )


#
# TAGS
#


def _render_host_tags(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return "", render_tag_groups(
        get_tag_groups(row, "host"), "host", with_links=True, request=context.request
    )


def make_host_tags_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_tags",
        title=_l("Host tags"),
        columns=["host_tags"],
        sorter="host",
        render=_render_host_tags,
    )


def _tag_entries(object_type: str, row: Row, tags: TagConfig) -> list[tuple[str, str]]:
    entries = []
    aux_titles = _aux_tag_titles(tags)
    for tag_group_id, tag_id in get_tag_groups(row, object_type).items():
        tag_group = tags.get_tag_group(tag_group_id)
        if tag_group:
            choices = tag_choices_for_group(tag_group)
            entries.append((tag_group.title, choices.get(tag_id, tag_id)))
            continue

        aux_tag_title = aux_titles.get(tag_group_id)
        if aux_tag_title:
            entries.append((aux_tag_title, aux_tag_title))
            continue

        entries.append((tag_group_id, tag_id))
    return entries


def _render_tags_with_titles(
    object_type: str, row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    entries = _tag_entries(object_type, row, context.config.tags)
    return "", HTMLWriter.render_br().join(
        [
            escaping.escape_to_html_permissive("%s: %s" % e, escape_links=False)
            for e in sorted(entries)
        ]
    )


@request_memoize()
def _aux_tag_titles(tag_config: TagConfig) -> dict[str, str]:
    return dict(tag_config.aux_tag_list.get_choices())


def _render_host_tags_with_titles(
    row: Row, cell: Cell, user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _render_tags_with_titles("host", row, cell, user, context)


def make_host_tags_with_titles_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_tags_with_titles",
        title=_l("Host tags (with titles)"),
        columns=["host_tags"],
        sorter="host",
        render=_render_host_tags_with_titles,
    )


def _render_service_tags(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return "", render_tag_groups(
        get_tag_groups(row, "service"), "service", with_links=True, request=context.request
    )


def make_service_tags_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_tags",
        title=_l("Service tags"),
        columns=["service_tags"],
        sorter="service_tags",
        render=_render_service_tags,
    )


def _render_service_tags_with_titles(
    row: Row, cell: Cell, user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return _render_tags_with_titles("service", row, cell, user, context)


def make_service_tags_with_titles_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_tags_with_titles",
        title=_l("Service tags (with titles)"),
        columns=["service_tags"],
        sorter="service_tags",
        render=_render_service_tags_with_titles,
    )


def _compute_data_host_labels(row: Row, _context: PainterContext) -> Labels:
    return get_labels(row, "host")


def _render_host_labels(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return "", render_labels(
        _compute_data_host_labels(row, context),
        "host",
        with_links=True,
        label_sources=get_label_sources(row, "host"),
        request=context.request,
    )


def _export_for_python_host_labels(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> Labels:
    return _compute_data_host_labels(row, context)


def _export_for_csv_host_labels(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> str | HTML:
    return format_labels_for_csv_export(_compute_data_host_labels(row, context))


def _export_for_json_host_labels(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> Labels:
    return _compute_data_host_labels(row, context)


def make_host_labels_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_labels",
        title=_l("Host labels"),
        columns=["host_labels", "host_label_sources"],
        sorter="host_labels",
        render=_render_host_labels,
        compute_data=_compute_data_host_labels,
        export_for_python=_export_for_python_host_labels,
        export_for_csv=_export_for_csv_host_labels,
        export_for_json=_export_for_json_host_labels,
    )


def _compute_data_service_labels(row: Row, _context: PainterContext) -> Labels:
    return get_labels(row, "service")


def _render_service_labels(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    return "", render_labels(
        _compute_data_service_labels(row, context),
        "service",
        with_links=True,
        label_sources=get_label_sources(row, "service"),
        request=context.request,
    )


def _export_for_python_service_labels(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> Labels:
    return _compute_data_service_labels(row, context)


def _export_for_csv_service_labels(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> str | HTML:
    return format_labels_for_csv_export(_compute_data_service_labels(row, context))


def _export_for_json_service_labels(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> Labels:
    return _compute_data_service_labels(row, context)


def make_service_labels_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_labels",
        title=_l("Service labels"),
        columns=["service_labels", "service_label_sources"],
        sorter="service_labels",
        render=_render_service_labels,
        compute_data=_compute_data_service_labels,
        export_for_python=_export_for_python_service_labels,
        export_for_csv=_export_for_csv_service_labels,
        export_for_json=_export_for_json_service_labels,
    )


def _render_host_docker_node(
    row: Row, _cell: Cell, _user: LoggedInUser, context: PainterContext
) -> CellSpec:
    if row.get("host_labels", {}).get("cmk/docker_object") != "container":
        return "", ""

    docker_nodes = _get_docker_container_status_outputs()
    output = docker_nodes.get(row["host_name"])
    # Output with node: "Container running on node mynode2"
    # Output without node: "Container running"
    if output is None or "node" not in output:
        return "", ""

    node = output.split()[-1]
    content = context.url_renderer.link_from_filename(
        "view.py",
        query_args=[
            ("view_name", "host"),
            ("host", node),
        ],
        html_text=node,
    )
    return "", content


def make_host_docker_node_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_docker_node",
        title=_l("Docker node"),
        short_title=_l("Node"),
        columns=["host_labels", "host_label_sources"],
        render=_render_host_docker_node,
    )


@request_memoize()
def _get_docker_container_status_outputs() -> dict[str, str]:
    """Returns a map of all known hosts with their docker nodes

    It is important to cache this query per request and also try to use the
    liveproxyd query cached.
    """
    query: str = (
        "GET services\n"
        "Columns: host_name service_plugin_output\n"
        "Filter: check_command = check_mk-docker_container_status\n"
    )
    return {row[0]: row[1] for row in sites.live().query(query)}


_SPECIFIC_METRIC_DEFAULT_TITLE = _l("Show single metric")


def _title_specific_metric(cell: Cell, _context: PainterContext) -> str:
    if not (parameters := cell.painter_parameters()):
        # Used in Edit-View
        return str(_SPECIFIC_METRIC_DEFAULT_TITLE)
    return _title_with_parameters(parameters, metrics_from_api)


def _title_with_parameters(
    parameters: PainterParameters,
    registered_metrics: Mapping[str, RegisteredMetric],
) -> str:
    try:
        return get_metric_spec(parameters["metric"], registered_metrics).title
    except KeyError:
        return _("Metric not found")


@request_memoize()
def metric_choices() -> list[tuple[str, str]]:
    return sorted(
        (
            (metric_id, metric_title)
            for metric_id, metric_title in registered_metric_ids_and_titles(metrics_from_api)
        ),
        key=lambda x: x[1],
    )


def _parameters_specific_metric(_context: PainterContext) -> Dictionary:
    return Dictionary(
        elements=[
            (
                "metric",
                DropdownChoice(
                    title=_("Show metric"),
                    choices=metric_choices(),
                    help=_("If available, the following metric will be shown"),
                ),
            ),
            ("column_title", TextInput(title=_("Custom title"))),
        ],
        optional_keys=["column_title"],
    )


def _render_specific_metric(
    cell: Cell,
    perf_data_entries: str,
    check_command: str,
    temperature_unit: TemperatureUnit,
    debug: bool,
) -> tuple[str, str]:
    parameters = cell.painter_parameters()
    assert parameters is not None
    show_metric = parameters["metric"]

    evaluated = evaluated_metrics(
        perf_data_entries,
        check_command,
        registered_metrics=registered_metrics(),
        registered_translations=registered_translations(),
        temperature_unit=temperature_unit,
        debug=debug,
    )

    if (metric := evaluated.get(MetricName(show_metric))) is None:
        return "", ""

    return "", _rendered_value(metric)


def _render_host_specific_metric(
    row: Row, cell: Cell, user: LoggedInUser, context: PainterContext
) -> CellSpec:
    perf_data_entries = row["host_perf_data"]
    check_command = row["host_check_command"]
    return _render_specific_metric(
        cell,
        perf_data_entries,
        check_command,
        get_temperature_unit(user, context.config.default_temperature_unit),
        context.config.debug,
    )


def make_host_specific_metric_painter() -> InternalPainter:
    return InternalPainter(
        ident="host_specific_metric",
        title=_SPECIFIC_METRIC_DEFAULT_TITLE,
        list_title=_l("Metric"),
        columns=["host_perf_data", "host_check_command"],
        cell_title=_title_specific_metric,
        cell_short_title=_title_specific_metric,
        parameters=_parameters_specific_metric,
        render=_render_host_specific_metric,
    )


def _render_service_specific_metric(
    row: Row, cell: Cell, user: LoggedInUser, context: PainterContext
) -> CellSpec:
    perf_data_entries = row["service_perf_data"]
    check_command = row["service_check_command"]
    return _render_specific_metric(
        cell,
        perf_data_entries,
        check_command,
        get_temperature_unit(user, context.config.default_temperature_unit),
        context.config.debug,
    )


def make_service_specific_metric_painter() -> InternalPainter:
    return InternalPainter(
        ident="service_specific_metric",
        title=_SPECIFIC_METRIC_DEFAULT_TITLE,
        list_title=_l("Metric"),
        columns=["service_perf_data", "service_check_command"],
        cell_title=_title_specific_metric,
        cell_short_title=_title_specific_metric,
        parameters=_parameters_specific_metric,
        render=_render_service_specific_metric,
    )


def _render_host_kubernetes(
    object_type: str,
    constraints: Sequence[str],
    row: Row,
    _cell: Cell,
    _user: LoggedInUser,
    context: PainterContext,
) -> CellSpec:
    labels = row.get("host_labels", {})
    if labels.get("cmk/kubernetes/object") != object_type:
        return "", ""

    links: list[HTTPVariable] = []
    for link_key in constraints:
        if (link_value := labels.get(f"cmk/kubernetes/{link_key}")) is None:
            # a requested filter can not be set, so better don't show anything
            return "", ""

        links.append((f"kubernetes_{link_key}", link_value))

    links.extend(
        [
            # name of the dashboard we are linking to
            ("name", f"kubernetes_{object_type}"),
            ("host", row["host_name"]),
            ("site", row["site"]),
        ]
    )

    if (object_name := labels.get(f"cmk/kubernetes/{object_type}")) is None:
        return "", ""

    content = context.url_renderer.link_from_filename(
        "dashboard.py", html_text=object_name, query_args=links
    )
    return "", content


def _make_host_kubernetes_painter(
    *, object_type: str, constraints: Sequence[str], title: LazyString, short_title: LazyString
) -> InternalPainter:
    return InternalPainter(
        ident=f"host_kubernetes_{object_type}",
        title=title,
        short_title=short_title,
        columns=["host_labels", "host_name", "site"],
        render=partial(_render_host_kubernetes, object_type, constraints),
    )


def make_host_kubernetes_cluster_painter() -> InternalPainter:
    return _make_host_kubernetes_painter(
        object_type="cluster",
        constraints=["cluster"],
        title=_l("Kubernetes cluster"),
        short_title=_l("Cluster"),
    )


def make_host_kubernetes_namespace_painter() -> InternalPainter:
    return _make_host_kubernetes_painter(
        object_type="namespace",
        constraints=["namespace", "cluster-host", "cluster"],
        title=_l("Kubernetes Namespace"),
        short_title=_l("Namespace"),
    )


def make_host_kubernetes_deployment_painter() -> InternalPainter:
    return _make_host_kubernetes_painter(
        object_type="deployment",
        constraints=["deployment", "namespace", "cluster-host", "cluster"],
        title=_l("Kubernetes deployment"),
        short_title=_l("Deployment"),
    )


def make_host_kubernetes_daemonset_painter() -> InternalPainter:
    return _make_host_kubernetes_painter(
        object_type="daemonset",
        constraints=["daemonset", "namespace", "cluster-host", "cluster"],
        title=_l("Kubernetes DaemonSet"),
        short_title=_l("DaemonSet"),
    )


def make_host_kubernetes_statefulset_painter() -> InternalPainter:
    return _make_host_kubernetes_painter(
        object_type="statefulset",
        constraints=["statefulset", "namespace", "cluster-host", "cluster"],
        title=_l("Kubernetes StatefulSet"),
        short_title=_l("StatefulSet"),
    )


def make_host_kubernetes_node_painter() -> InternalPainter:
    return _make_host_kubernetes_painter(
        object_type="node",
        constraints=["node", "cluster"],
        title=_l("Kubernetes node"),
        short_title=_l("Node"),
    )
