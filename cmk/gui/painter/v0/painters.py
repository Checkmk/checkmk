#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import time
from collections.abc import Iterable, Mapping, Sequence
from fnmatch import fnmatch
from pathlib import Path
from typing import Literal

import cmk.ccc.version as cmk_version

import cmk.utils.paths
from cmk.utils import man_pages
from cmk.utils.labels import Labels
from cmk.utils.render import approx_age
from cmk.utils.statename import short_host_state_name, short_service_state_name

from cmk.gui import sites
from cmk.gui.config import active_config, Config
from cmk.gui.graphing._color import render_color_icon
from cmk.gui.graphing._from_api import metrics_from_api, RegisteredMetric
from cmk.gui.graphing._metrics import get_metric_spec, registered_metric_ids_and_titles
from cmk.gui.graphing._translated_metrics import (
    parse_perf_data,
    translate_metrics,
    TranslatedMetric,
)
from cmk.gui.graphing._unit import user_specific_unit
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.painter_options import (
    paint_age,
    paint_age_or_never,
    PainterOption,
    PainterOptionRegistry,
    PainterOptions,
)
from cmk.gui.site_config import get_site_config
from cmk.gui.theme import Theme
from cmk.gui.type_defs import (
    ColumnName,
    HTTPVariables,
    PainterParameters,
    Row,
    SorterName,
    VisualLinkSpec,
)
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.popups import MethodAjax
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
    format_plugin_output,
    get_labels,
    render_labels,
    render_tag_groups,
)
from cmk.gui.visual_link import render_link_to_view

from cmk.discover_plugins import discover_families, PluginGroup

from ..v1.helpers import get_perfdata_nth_value, is_stale, paint_stalified
from .base import Cell, Painter
from .helpers import (
    format_labels_for_csv_export,
    get_label_sources,
    get_tag_groups,
    paint_host_list,
    paint_nagiosflag,
    render_cache_info,
    RenderLink,
    replace_action_url_macros,
)
from .registry import PainterRegistry


def register(
    painter_option_registry: PainterOptionRegistry, painter_registry: PainterRegistry
) -> None:
    painter_option_registry.register(PainterOptionTimestampFormat)
    painter_option_registry.register(PainterOptionTimestampDate)
    painter_option_registry.register(PainterOptionMatrixOmitUniform)
    painter_option_registry.register(PainterOptionShowInternalGraphAndMetricIds)
    painter_registry.register(PainterSiteIcon)
    painter_registry.register(PainterSitenamePlain)
    painter_registry.register(PainterSitealias)
    painter_registry.register(PainterServiceState)
    painter_registry.register(PainterSvcPluginOutput)
    painter_registry.register(PainterSvcLongPluginOutput)
    painter_registry.register(PainterSvcPerfData)
    painter_registry.register(PainterSvcMetrics)
    painter_registry.register(PainterSvcPerfVal01)
    painter_registry.register(PainterSvcPerfVal02)
    painter_registry.register(PainterSvcPerfVal03)
    painter_registry.register(PainterSvcPerfVal04)
    painter_registry.register(PainterSvcPerfVal05)
    painter_registry.register(PainterSvcPerfVal06)
    painter_registry.register(PainterSvcPerfVal07)
    painter_registry.register(PainterSvcPerfVal08)
    painter_registry.register(PainterSvcPerfVal09)
    painter_registry.register(PainterSvcPerfVal10)
    painter_registry.register(PainterSvcCheckCommand)
    painter_registry.register(PainterSvcCheckCommandExpanded)
    painter_registry.register(PainterSvcNotesURL)
    painter_registry.register(PainterSvcContacts)
    painter_registry.register(PainterSvcContactGroups)
    painter_registry.register(PainterServiceDescription)
    painter_registry.register(PainterServiceDisplayName)
    painter_registry.register(PainterSvcStateAge)
    painter_registry.register(PainterSvcCheckAge)
    painter_registry.register(PainterSvcCheckCacheInfo)
    painter_registry.register(PainterSvcNextCheck)
    painter_registry.register(PainterSvcLastTimeOk)
    painter_registry.register(PainterSvcNextNotification)
    painter_registry.register(PainterSvcNotificationPostponementReason)
    painter_registry.register(PainterSvcLastNotification)
    painter_registry.register(PainterSvcNotificationNumber)
    painter_registry.register(PainterSvcCheckLatency)
    painter_registry.register(PainterSvcCheckDuration)
    painter_registry.register(PainterSvcAttempt)
    painter_registry.register(PainterSvcNormalInterval)
    painter_registry.register(PainterSvcRetryInterval)
    painter_registry.register(PainterSvcCheckInterval)
    painter_registry.register(PainterSvcCheckType)
    painter_registry.register(PainterSvcInDowntime)
    painter_registry.register(PainterSvcInNotifper)
    painter_registry.register(PainterSvcNotifper)
    painter_registry.register(PainterSvcCheckPeriod)
    painter_registry.register(PainterSvcFlapping)
    painter_registry.register(PainterSvcNotificationsEnabled)
    painter_registry.register(PainterSvcIsActive)
    painter_registry.register(PainterSvcGroupMemberlist)
    painter_registry.register(PainterCheckManpage)
    painter_registry.register(PainterSvcComments)
    painter_registry.register(PainterSvcAcknowledged)
    painter_registry.register(PainterSvcCustomNotes)
    painter_registry.register(PainterSvcStaleness)
    painter_registry.register(PainterSvcIsStale)
    painter_registry.register(PainterServiceCustomVariables)
    painter_registry.register(PainterServiceCustomVariable)
    painter_registry.register(PainterHostCustomVariable)
    painter_registry.register(PainterHostState)
    painter_registry.register(PainterHostStateOnechar)
    painter_registry.register(PainterHostPluginOutput)
    painter_registry.register(PainterHostPerfData)
    painter_registry.register(PainterHostCheckCommand)
    painter_registry.register(PainterHostCheckCommandExpanded)
    painter_registry.register(PainterHostNotesURL)
    painter_registry.register(PainterHostStateAge)
    painter_registry.register(PainterHostCheckAge)
    painter_registry.register(PainterHostNextCheck)
    painter_registry.register(PainterHostNextNotification)
    painter_registry.register(PainterHostNotificationPostponementReason)
    painter_registry.register(PainterHostLastNotification)
    painter_registry.register(PainterHostCheckLatency)
    painter_registry.register(PainterHostCheckDuration)
    painter_registry.register(PainterHostAttempt)
    painter_registry.register(PainterHostNormalInterval)
    painter_registry.register(PainterHostRetryInterval)
    painter_registry.register(PainterHostCheckInterval)
    painter_registry.register(PainterHostCheckType)
    painter_registry.register(PainterHostInNotifper)
    painter_registry.register(PainterHostNotifper)
    painter_registry.register(PainterHostNotificationNumber)
    painter_registry.register(PainterHostFlapping)
    painter_registry.register(PainterHostIsActive)
    painter_registry.register(PainterHostNotificationsEnabled)
    painter_registry.register(PainterHostBlack)
    painter_registry.register(PainterHostWithState)
    painter_registry.register(PainterHost)
    painter_registry.register(PainterAlias)
    painter_registry.register(PainterHostAddress)
    painter_registry.register(PainterHostIpv4Address)
    painter_registry.register(PainterHostIpv6Address)
    painter_registry.register(PainterHostAddresses)
    painter_registry.register(PainterHostAddressesAdditional)
    painter_registry.register(PainterHostAddressFamily)
    painter_registry.register(PainterHostAddressFamilies)
    painter_registry.register(PainterNumServices)
    painter_registry.register(PainterNumServicesOk)
    painter_registry.register(PainterNumProblems)
    painter_registry.register(PainterNumServicesWarn)
    painter_registry.register(PainterNumServicesCrit)
    painter_registry.register(PainterNumServicesUnknown)
    painter_registry.register(PainterNumServicesPending)
    painter_registry.register(PainterHostServices)
    painter_registry.register(PainterHostParents)
    painter_registry.register(PainterHostChilds)
    painter_registry.register(PainterHostGroupMemberlist)
    painter_registry.register(PainterHostContacts)
    painter_registry.register(PainterHostContactGroups)
    painter_registry.register(PainterHostCustomNotes)
    painter_registry.register(PainterHostComments)
    painter_registry.register(PainterHostInDowntime)
    painter_registry.register(PainterHostAcknowledged)
    painter_registry.register(PainterHostStaleness)
    painter_registry.register(PainterHostIsStale)
    painter_registry.register(PainterHostCustomVariables)
    painter_registry.register(PainterServiceDiscoveryState)
    painter_registry.register(PainterServiceDiscoveryCheck)
    painter_registry.register(PainterServiceDiscoveryService)
    painter_registry.register(PainterHostgroupHosts)
    painter_registry.register(PainterHgNumServices)
    painter_registry.register(PainterHgNumServicesOk)
    painter_registry.register(PainterHgNumServicesWarn)
    painter_registry.register(PainterHgNumServicesCrit)
    painter_registry.register(PainterHgNumServicesUnknown)
    painter_registry.register(PainterHgNumServicesPending)
    painter_registry.register(PainterHgNumHostsUp)
    painter_registry.register(PainterHgNumHostsDown)
    painter_registry.register(PainterHgNumHostsUnreach)
    painter_registry.register(PainterHgNumHostsPending)
    painter_registry.register(PainterHgName)
    painter_registry.register(PainterHgAlias)
    painter_registry.register(PainterSgServices)
    painter_registry.register(PainterSgNumServices)
    painter_registry.register(PainterSgNumServicesOk)
    painter_registry.register(PainterSgNumServicesWarn)
    painter_registry.register(PainterSgNumServicesCrit)
    painter_registry.register(PainterSgNumServicesUnknown)
    painter_registry.register(PainterSgNumServicesPending)
    painter_registry.register(PainterSgName)
    painter_registry.register(PainterSgAlias)
    painter_registry.register(PainterCommentId)
    painter_registry.register(PainterCommentAuthor)
    painter_registry.register(PainterCommentComment)
    painter_registry.register(PainterCommentWhat)
    painter_registry.register(PainterCommentTime)
    painter_registry.register(PainterCommentExpires)
    painter_registry.register(PainterCommentEntryType)
    painter_registry.register(PainterDowntimeId)
    painter_registry.register(PainterDowntimeAuthor)
    painter_registry.register(PainterDowntimeComment)
    painter_registry.register(PainterDowntimeFixed)
    painter_registry.register(PainterDowntimeOrigin)
    painter_registry.register(PainterDowntimeWhat)
    painter_registry.register(PainterDowntimeType)
    painter_registry.register(PainterDowntimeEntryTime)
    painter_registry.register(PainterDowntimeStartTime)
    painter_registry.register(PainterDowntimeEndTime)
    painter_registry.register(PainterDowntimeDuration)
    painter_registry.register(PainterLogDetailsHistory)
    painter_registry.register(PainterLogMessage)
    painter_registry.register(PainterLogPluginOutput)
    painter_registry.register(PainterLogWhat)
    painter_registry.register(PainterLogAttempt)
    painter_registry.register(PainterLogStateType)
    painter_registry.register(PainterLogStateInfo)
    painter_registry.register(PainterLogType)
    painter_registry.register(PainterLogContactName)
    painter_registry.register(PainterLogCommand)
    painter_registry.register(PainterLogIcon)
    painter_registry.register(PainterLogOptions)
    painter_registry.register(PainterLogComment)
    painter_registry.register(PainterLogTime)
    painter_registry.register(PainterLogLineno)
    painter_registry.register(PainterLogDate)
    painter_registry.register(PainterLogState)
    painter_registry.register(PainterAlertStatsOk)
    painter_registry.register(PainterAlertStatsWarn)
    painter_registry.register(PainterAlertStatsCrit)
    painter_registry.register(PainterAlertStatsUnknown)
    painter_registry.register(PainterAlertStatsProblem)
    painter_registry.register(PainterHostTags)
    painter_registry.register(PainterHostTagsWithTitles)
    painter_registry.register(PainterServiceTags)
    painter_registry.register(PainterServiceTagsWithTitles)
    painter_registry.register(PainterHostLabels)
    painter_registry.register(PainterServiceLabels)
    painter_registry.register(PainterHostDockerNode)
    painter_registry.register(PainterHostSpecificMetric)
    painter_registry.register(PainterServiceSpecificMetric)
    painter_registry.register(PainterHostKubernetesCluster)
    painter_registry.register(PainterHostKubernetesNamespace)
    painter_registry.register(PainterHostKubernetesDeployment)
    painter_registry.register(PainterHostKubernetesDaemonset)
    painter_registry.register(PainterHostKubernetesStatefulset)
    painter_registry.register(PainterHostKubernetesNode)


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
    @property
    def ident(self) -> str:
        return "show_internal_graph_and_metric_ids"

    @property
    def valuespec(self) -> ValueSpec:
        return Checkbox(
            title=_("Show internal graph and metric IDs"),
            default_value=False,
        )


class PainterOptionTimestampFormat(PainterOption):
    @property
    def ident(self) -> str:
        return "ts_format"

    @property
    def valuespec(self) -> DropdownChoice:
        return DropdownChoice(
            title=_("Time stamp format"),
            default_value=self.config.default_ts_format,
            encode_value=False,
            choices=[
                ("mixed", _("Mixed")),
                ("abs", _("Absolute")),
                ("rel", _("Relative")),
                ("both", _("Both")),
                ("epoch", _("Unix Timestamp (Epoch)")),
            ],
        )


class PainterOptionTimestampDate(PainterOption):
    @property
    def ident(self) -> str:
        return "ts_date"

    @property
    def valuespec(self) -> DropdownChoice:
        return DateFormat()


class PainterOptionMatrixOmitUniform(PainterOption):
    @property
    def ident(self) -> str:
        return "matrix_omit_uniform"

    @property
    def valuespec(self) -> DropdownChoice:
        return DropdownChoice(
            title=_("Find differences..."),
            choices=[
                (False, _("Always show all rows")),
                (True, _("Omit rows where all columns are identical")),
            ],
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
def paint_custom_var(what: str, key: CSSClass, row: Row, choices: list | None = None) -> CellSpec:
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
    if not (0 < timestamp < 0x200000000):
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


class PainterSiteIcon(Painter):
    @property
    def ident(self) -> str:
        return "site_icon"

    def title(self, cell: Cell) -> str:
        return _("Site icon")

    def short_title(self, cell: Cell) -> str:
        return ""

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["site"]

    @property
    def sorter(self) -> SorterName:
        return "site"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if row.get("site") and self.config.use_siteicons:
            return None, HTMLWriter.render_img(
                "icons/site-%s-24.png" % row["site"], class_="siteicon"
            )
        return None, ""


class PainterSitenamePlain(Painter):
    @property
    def ident(self) -> str:
        return "sitename_plain"

    def title(self, cell: Cell) -> str:
        return _("Site ID")

    def short_title(self, cell: Cell) -> str:
        return _("Site")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["site"]

    @property
    def sorter(self) -> SorterName:
        return "site"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["site"])


class PainterSitealias(Painter):
    @property
    def ident(self) -> str:
        return "sitealias"

    def title(self, cell: Cell) -> str:
        return _("Site alias")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["site"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, get_site_config(self.config, row["site"])["alias"])


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


def _paint_service_state_short(row: Row, *, config: Config) -> CellSpec:
    state, name = service_state_short(row)
    if is_stale(row, config=config):
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


def _paint_host_state_short(row: Row, short: bool = False, *, config: Config) -> CellSpec:
    state, name = host_state_short(row)
    if is_stale(row, config=config):
        state = state + " stale"

    if short:
        name = name[0]

    return "state hstate hstate%s" % state, HTMLWriter.render_span(
        name, class_=["state_rounded_fill"]
    )


class PainterServiceState(Painter):
    @property
    def ident(self) -> str:
        return "service_state"

    def title(self, cell: Cell) -> str:
        return _("Service state")

    def short_title(self, cell: Cell) -> str:
        return _("State")

    def title_classes(self) -> list[str]:
        return ["center"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_has_been_checked", "service_state"]

    @property
    def sorter(self) -> SorterName:
        return "svcstate"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_service_state_short(row, config=self.config)


class PainterSvcPluginOutput(Painter):
    @property
    def ident(self) -> str:
        return "svc_plugin_output"

    def title(self, cell: Cell) -> str:
        return _("Summary")

    def list_title(self, cell: Cell) -> str:
        return _("Summary (Previously named: Status details or plug-in output)")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_plugin_output", "service_custom_variables", "service_check_command"]

    @property
    def sorter(self) -> SorterName:
        return "svcoutput"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_stalified(
            row,
            format_plugin_output(row["service_plugin_output"], request=self.request, row=row),
            config=self.config,
        )


class PainterSvcLongPluginOutput(Painter):
    @property
    def ident(self) -> str:
        return "svc_long_plugin_output"

    def title(self, cell: Cell) -> str:
        return _("Details")

    def list_title(self, cell: Cell) -> str:
        return _("Details (Previously named: long output)")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_long_plugin_output", "service_custom_variables"]

    @property
    def parameters(self) -> Dictionary:
        return Dictionary(
            elements=[
                (
                    "max_len",
                    Integer(
                        title=_("Maximum number of characters to show"),
                        help=_(
                            "Truncate content at this amount of characters."
                            "A zero value mean not to truncate"
                        ),
                        default_value=0,
                        minvalue=0,
                    ),
                ),
            ]
        )

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if (params := cell.painter_parameters()) is None:
            params = {}

        max_len = params.get("max_len", 0)
        long_output = row["service_long_plugin_output"]
        long_output_len = len(long_output)

        if 0 < max_len < long_output_len:
            long_output = long_output[:max_len] + "..."

        content = format_plugin_output(
            long_output, request=self.request, row=row, newlineishs_to_brs=True
        )

        # has to be placed after format_plugin_output() to keep links save from
        # escaping
        if (
            max_long_output_size := sites.states()
            .get(row["site"], {})
            .get("max_long_output_size", 0)
        ) and long_output_len > max_long_output_size:
            setting_link_tag = self.url_renderer.link_from_filename(
                "wato.py",
                html_text="(%s)" % _("Increase limit"),
                query_args=[
                    ("mode", "edit_configvar"),
                    ("varname", "max_long_output_size"),
                ],
            )
            content = (
                _("Lost data due to truncation of long output to ")
                + f"{int(max_long_output_size / 1000)}kB "
                + setting_link_tag
                + html.render_b("WARN", class_="stmark state1")
                + html.render_br()
                + content
            )

        return paint_stalified(row, content, config=self.config)


class PainterSvcPerfData(Painter):
    @property
    def ident(self) -> str:
        return "svc_perf_data"

    def title(self, cell: Cell) -> str:
        return _("Service performance data (source code)")

    def short_title(self, cell: Cell) -> str:
        return _("Perfdata")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_perf_data"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_stalified(row, row["service_perf_data"], config=self.config)


class PainterSvcMetrics(Painter):
    @property
    def ident(self) -> str:
        return "svc_metrics"

    def title(self, cell: Cell) -> str:
        return _("Service metrics")

    def short_title(self, cell: Cell) -> str:
        return _("Metrics")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_check_command", "service_perf_data"]

    @property
    def painter_options(self):
        return ["show_internal_graph_and_metric_ids"]

    @property
    def printable(self) -> bool:
        return False

    def render(self, row: Row, cell: Cell) -> CellSpec:
        perf_data, check_command = parse_perf_data(
            row["service_perf_data"], row["service_check_command"], config=self.config
        )
        translated_metrics = translate_metrics(
            perf_data,
            check_command,
            metrics_from_api,
        )

        if row["service_perf_data"] and not translated_metrics:
            return "", _("Failed to parse performance data string: %s") % row["service_perf_data"]

        with output_funnel.plugged():
            self._show_metrics_table(
                translated_metrics,
                row["host_name"],
                row["service_description"],
                show_metric_id=self._painter_options.get("show_internal_graph_and_metric_ids"),
                theme=self.theme,
            )
            return "", HTML.without_escaping(output_funnel.drain())

    def _show_metrics_table(
        self,
        translated_metrics: Mapping[str, TranslatedMetric],
        host_name: str,
        service_description: str,
        show_metric_id: bool,
        *,
        theme: Theme,
    ) -> None:
        html.open_table(class_="metricstable")
        for metric_name, translated_metric in sorted(
            translated_metrics.items(), key=lambda t: t[1].title
        ):
            optional_metric_id = ""
            if show_metric_id:
                optional_metric_id = f" (Metric ID: {metric_name})"
            html.open_tr()
            html.td(render_color_icon(translated_metric.color), class_="color")
            html.td(f"{translated_metric.title}{optional_metric_id}:")
            html.td(
                user_specific_unit(
                    translated_metric.unit_spec,
                    user,
                    active_config,
                ).formatter.render(translated_metric.value),
                class_="value",
            )
            if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.CRE:
                html.td(
                    html.render_popup_trigger(
                        html.render_icon(
                            "menu",
                            title=_("Add this metric to dedicated graph"),
                            cssclass="iconbutton",
                            theme=theme,
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
            html.close_tr()
        html.close_table()


# TODO: Use a parameterized painter for this instead of 10 painter classes
class PainterSvcPerfVal(Painter):
    _num = 0

    @property
    def ident(self) -> str:
        return "svc_perf_val%02d" % self._num

    def title(self, cell: Cell) -> str:
        return _("Service performance data - value number %2d") % self._num

    def short_title(self, cell: Cell) -> str:
        return _("Val. %d") % self._num

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_perf_data"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_stalified(row, get_perfdata_nth_value(row, self._num - 1), config=self.config)


class PainterSvcPerfVal01(PainterSvcPerfVal):
    _num = 1


class PainterSvcPerfVal02(PainterSvcPerfVal):
    _num = 2


class PainterSvcPerfVal03(PainterSvcPerfVal):
    _num = 3


class PainterSvcPerfVal04(PainterSvcPerfVal):
    _num = 4


class PainterSvcPerfVal05(PainterSvcPerfVal):
    _num = 5


class PainterSvcPerfVal06(PainterSvcPerfVal):
    _num = 6


class PainterSvcPerfVal07(PainterSvcPerfVal):
    _num = 7


class PainterSvcPerfVal08(PainterSvcPerfVal):
    _num = 8


class PainterSvcPerfVal09(PainterSvcPerfVal):
    _num = 9


class PainterSvcPerfVal10(PainterSvcPerfVal):
    _num = 10


class PainterSvcCheckCommand(Painter):
    @property
    def ident(self) -> str:
        return "svc_check_command"

    def title(self, cell: Cell) -> str:
        return _("Service check command")

    def short_title(self, cell: Cell) -> str:
        return _("Check command")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_check_command"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["service_check_command"])


class PainterSvcCheckCommandExpanded(Painter):
    @property
    def ident(self) -> str:
        return "svc_check_command_expanded"

    def title(self, cell: Cell) -> str:
        return _("Service check command expanded")

    def short_title(self, cell: Cell) -> str:
        return _("Check command expanded")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_check_command_expanded"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["service_check_command_expanded"])


class PainterSvcNotesURL(Painter):
    @property
    def ident(self) -> str:
        return "svc_notes_url"

    def title(self, cell: Cell) -> str:
        return _("Notes (URL) for Services")

    def short_title(self, cell: Cell) -> str:
        return _("Notes URL")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_notes_url"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        raw_url = row.get("service_notes_url")
        if not raw_url:
            return None, HTML.empty()

        url = replace_action_url_macros(raw_url, "service", row)
        content = self.url_renderer.link_direct(url, html_text=url, target="_blank")
        return None, content


class PainterSvcContacts(Painter):
    @property
    def ident(self) -> str:
        return "svc_contacts"

    def title(self, cell: Cell) -> str:
        return _("Service contacts")

    def short_title(self, cell: Cell) -> str:
        return _("Contacts")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_contacts"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, ", ".join(row["service_contacts"]))


class PainterSvcContactGroups(Painter):
    @property
    def ident(self) -> str:
        return "svc_contact_groups"

    def title(self, cell: Cell) -> str:
        return _("Service contact groups")

    def short_title(self, cell: Cell) -> str:
        return _("Contact groups")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_contact_groups"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, ", ".join(row["service_contact_groups"]))


class PainterServiceDescription(Painter):
    @property
    def ident(self) -> str:
        return "service_description"

    def title(self, cell: Cell) -> str:
        return _("Service name")

    def short_title(self, cell: Cell) -> str:
        return _("Service")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_description"]

    @property
    def sorter(self) -> SorterName:
        return "svcdescr"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["service_description"])


class PainterServiceDisplayName(Painter):
    @property
    def ident(self) -> str:
        return "service_display_name"

    def title(self, cell: Cell) -> str:
        return _("Service alternative display name")

    def short_title(self, cell: Cell) -> str:
        return _("Display name")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_display_name"]

    @property
    def sorter(self) -> SorterName:
        return "svcdispname"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["service_display_name"])


class PainterSvcStateAge(Painter):
    @property
    def ident(self) -> str:
        return "svc_state_age"

    def title(self, cell: Cell) -> str:
        return _("Age of the current service state")

    def short_title(self, cell: Cell) -> str:
        return _("Age")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_has_been_checked", "service_last_state_change"]

    @property
    def sorter(self) -> SorterName:
        return "stateage"

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["service_last_state_change"],
            row["service_has_been_checked"] == 1,
            60 * 10,
            request=self.request,
            painter_options=self._painter_options,
        )


def _paint_checked(
    what: str, row: Row, *, config: Config, request: Request, painter_options: PainterOptions
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
    if is_stale(row, config=config):
        css += " staletime"
    return css, td


class PainterSvcCheckAge(Painter):
    @property
    def ident(self) -> str:
        return "svc_check_age"

    def title(self, cell: Cell) -> str:
        return _("Time since the last check of the service")

    def short_title(self, cell: Cell) -> str:
        return _("Checked")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_has_been_checked", "service_last_check", "service_cached_at"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_checked(
            "service",
            row,
            config=self.config,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterSvcCheckCacheInfo(Painter):
    @property
    def ident(self) -> str:
        return "svc_check_cache_info"

    def title(self, cell: Cell) -> str:
        return _("Cached agent data")

    def short_title(self, cell: Cell) -> str:
        return _("Cached")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_last_check", "service_cached_at", "service_cache_interval"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if not row["service_cached_at"]:
            return "", ""
        return "", render_cache_info("service", row)


class PainterSvcNextCheck(Painter):
    @property
    def ident(self) -> str:
        return "svc_next_check"

    def title(self, cell: Cell) -> str:
        return _("Time of the next scheduled service check")

    def short_title(self, cell: Cell) -> str:
        return _("Next check")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_next_check"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_future_time(
            row["service_next_check"],
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterSvcLastTimeOk(Painter):
    @property
    def ident(self) -> str:
        return "svc_last_time_ok"

    def title(self, cell: Cell) -> str:
        return _("Last time the service was OK")

    def short_title(self, cell: Cell) -> str:
        return _("Last OK")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_last_time_ok", "service_has_been_checked"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age_or_never(
            row["service_last_time_ok"],
            row["service_has_been_checked"] == 1,
            60 * 10,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterSvcNextNotification(Painter):
    @property
    def ident(self) -> str:
        return "svc_next_notification"

    def title(self, cell: Cell) -> str:
        return _("Time of the next service notification")

    def short_title(self, cell: Cell) -> str:
        return _("Next notification")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_next_notification"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_future_time(
            row["service_next_notification"],
            request=self.request,
            painter_options=self._painter_options,
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

    return (
        "",
        reasons.get(
            row[what + "_notification_postponement_reason"],
            row[what + "_notification_postponement_reason"],
        ),
    )


class PainterSvcNotificationPostponementReason(Painter):
    @property
    def ident(self) -> str:
        return "svc_notification_postponement_reason"

    def title(self, cell: Cell) -> str:
        return _("Notification postponement reason")

    def short_title(self, cell: Cell) -> str:
        return _("Notif. postponed")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_notification_postponement_reason"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_notification_postponement_reason("service", row)


class PainterSvcLastNotification(Painter):
    @property
    def ident(self) -> str:
        return "svc_last_notification"

    def title(self, cell: Cell) -> str:
        return _("Time of the last service notification")

    def short_title(self, cell: Cell) -> str:
        return _("last notification")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_last_notification"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["service_last_notification"],
            row["service_last_notification"],
            0,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterSvcNotificationNumber(Painter):
    @property
    def ident(self) -> str:
        return "svc_notification_number"

    def title(self, cell: Cell) -> str:
        return _("Service notification number")

    def short_title(self, cell: Cell) -> str:
        return _("N#")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_current_notification_number"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        # Keep in sync with HACK in cmk/base/events.py
        current: str = str(row["service_current_notification_number"])
        return ("", "1" if current == "0" else current)


class PainterSvcCheckLatency(Painter):
    @property
    def ident(self) -> str:
        return "svc_check_latency"

    def title(self, cell: Cell) -> str:
        return _("Service check latency")

    def short_title(self, cell: Cell) -> str:
        return _("Latency")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_latency"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", approx_age(row["service_latency"]))


class PainterSvcCheckDuration(Painter):
    @property
    def ident(self) -> str:
        return "svc_check_duration"

    def title(self, cell: Cell) -> str:
        return _("Service check duration")

    def short_title(self, cell: Cell) -> str:
        return _("Duration")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_execution_time"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", approx_age(row["service_execution_time"]))


class PainterSvcAttempt(Painter):
    @property
    def ident(self) -> str:
        return "svc_attempt"

    def title(self, cell: Cell) -> str:
        return _("Current check attempt")

    def short_title(self, cell: Cell) -> str:
        return _("Att.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_current_attempt", "service_max_check_attempts"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, "%d/%d" % (row["service_current_attempt"], row["service_max_check_attempts"]))


class PainterSvcNormalInterval(Painter):
    @property
    def ident(self) -> str:
        return "svc_normal_interval"

    def title(self, cell: Cell) -> str:
        return _("Service normal check interval")

    def short_title(self, cell: Cell) -> str:
        return _("Check int.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_check_interval"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("number", approx_age(row["service_check_interval"] * 60.0))


class PainterSvcRetryInterval(Painter):
    @property
    def ident(self) -> str:
        return "svc_retry_interval"

    def title(self, cell: Cell) -> str:
        return _("Service retry check interval")

    def short_title(self, cell: Cell) -> str:
        return _("Retry")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_retry_interval"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("number", approx_age(row["service_retry_interval"] * 60.0))


class PainterSvcCheckInterval(Painter):
    @property
    def ident(self) -> str:
        return "svc_check_interval"

    def title(self, cell: Cell) -> str:
        return _("Service normal/retry check interval")

    def short_title(self, cell: Cell) -> str:
        return _("Interval")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_check_interval", "service_retry_interval"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (
            None,
            "%s / %s"
            % (
                approx_age(row["service_check_interval"] * 60.0),
                approx_age(row["service_retry_interval"] * 60.0),
            ),
        )


class PainterSvcCheckType(Painter):
    @property
    def ident(self) -> str:
        return "svc_check_type"

    def title(self, cell: Cell) -> str:
        return _("Service check type")

    def short_title(self, cell: Cell) -> str:
        return _("Type")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_check_type"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, _("ACTIVE") if row["service_check_type"] == 0 else _("PASSIVE"))


class PainterSvcInDowntime(Painter):
    @property
    def ident(self) -> str:
        return "svc_in_downtime"

    def title(self, cell: Cell) -> str:
        return _("Currently in downtime")

    def short_title(self, cell: Cell) -> str:
        return _("Dt.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_scheduled_downtime_depth"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "service_scheduled_downtime_depth", True)


class PainterSvcInNotifper(Painter):
    @property
    def ident(self) -> str:
        return "svc_in_notifper"

    def title(self, cell: Cell) -> str:
        return _("In notification period")

    def short_title(self, cell: Cell) -> str:
        return _("in notif. p.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_in_notification_period"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "service_in_notification_period", False)


class PainterSvcNotifper(Painter):
    @property
    def ident(self) -> str:
        return "svc_notifper"

    def title(self, cell: Cell) -> str:
        return _("Service notification period")

    def short_title(self, cell: Cell) -> str:
        return _("notif.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_notification_period"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["service_notification_period"])


class PainterSvcCheckPeriod(Painter):
    @property
    def ident(self) -> str:
        return "svc_check_period"

    def title(self, cell: Cell) -> str:
        return _("Service check period")

    def short_title(self, cell: Cell) -> str:
        return _("check.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_check_period"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["service_check_period"])


class PainterSvcFlapping(Painter):
    @property
    def ident(self) -> str:
        return "svc_flapping"

    def title(self, cell: Cell) -> str:
        return _("Service is flapping")

    def short_title(self, cell: Cell) -> str:
        return _("Flap")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_is_flapping"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "service_is_flapping", True)


class PainterSvcNotificationsEnabled(Painter):
    @property
    def ident(self) -> str:
        return "svc_notifications_enabled"

    def title(self, cell: Cell) -> str:
        return _("Service notifications enabled")

    def short_title(self, cell: Cell) -> str:
        return _("Notif.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_notifications_enabled"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "service_notifications_enabled", False)


class PainterSvcIsActive(Painter):
    @property
    def ident(self) -> str:
        return "svc_is_active"

    def title(self, cell: Cell) -> str:
        return _("Service is active")

    def short_title(self, cell: Cell) -> str:
        return _("Active")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_active_checks_enabled"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "service_active_checks_enabled", False)


class PainterSvcGroupMemberlist(Painter):
    @property
    def ident(self) -> str:
        return "svc_group_memberlist"

    def title(self, cell: Cell) -> str:
        return _("Service groups the service is member of")

    def short_title(self, cell: Cell) -> str:
        return _("Groups")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_groups"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        links = []

        for group in row["service_groups"]:
            link = self.url_renderer.link_from_filename(
                "view.py",
                html_text=group,
                query_args=[
                    ("view_name", "servicegroup"),
                    ("servicegroup", group),
                ],
            )
            links.append(link)
        return "", HTML.without_escaping(", ").join(links)


class PainterCheckManpage(Painter):
    @property
    def ident(self) -> str:
        return "check_manpage"

    def title(self, cell: Cell) -> str:
        return _("Check manual (for Checkmk based checks)")

    def short_title(self, cell: Cell) -> str:
        return _("Manual")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_check_command"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
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


class PainterSvcComments(Painter):
    @property
    def ident(self) -> str:
        return "svc_comments"

    def title(self, cell: Cell) -> str:
        return _("Service Comments")

    def short_title(self, cell: Cell) -> str:
        return _("Comments")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_comments_with_info"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_comments("service_", row)


class PainterSvcAcknowledged(Painter):
    @property
    def ident(self) -> str:
        return "svc_acknowledged"

    def title(self, cell: Cell) -> str:
        return _("Service problem acknowledged")

    def short_title(self, cell: Cell) -> str:
        return _("Ack")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_acknowledged"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "service_acknowledged", False)


def match_path_entries_with_item(dirs: Iterable[Path], item: str) -> Iterable[Path]:
    yield from (
        sub_path
        for directory in dirs
        if directory.is_dir()
        for sub_path in directory.iterdir()
        if not sub_path.name.startswith(".") and fnmatch(item, sub_path.name)
    )


def _paint_custom_notes(what: str, row: Row, *, config: Config) -> CellSpec:
    host = row["host_name"]
    svc = row.get("service_description")
    if what == "service":
        notes_dir = cmk.utils.paths.default_config_dir + "/notes/services"
        dirs = match_path_entries_with_item([Path(notes_dir)], host)
        item = svc
    else:
        dirs = [Path(cmk.utils.paths.default_config_dir) / "notes/hosts"]
        item = host

    assert isinstance(item, str)
    files = sorted(match_path_entries_with_item(dirs, item), reverse=True)
    contents = []

    def replace_tags(text: str) -> str:
        sitename = row["site"]
        url_prefix = get_site_config(config, sitename)["url_prefix"]
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


class PainterSvcCustomNotes(Painter):
    @property
    def ident(self) -> str:
        return "svc_custom_notes"

    def title(self, cell: Cell) -> str:
        return _("Custom services notes")

    def short_title(self, cell: Cell) -> str:
        return _("Notes")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_name", "host_address", "service_description", "service_plugin_output"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_custom_notes("service", row, config=self.config)


class PainterSvcStaleness(Painter):
    @property
    def ident(self) -> str:
        return "svc_staleness"

    def title(self, cell: Cell) -> str:
        return _("Service staleness value")

    def short_title(self, cell: Cell) -> str:
        return _("Staleness")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_staleness"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", "%0.2f" % row.get("service_staleness", 0))


def _paint_is_stale(row: Row, *, config: Config) -> CellSpec:
    if is_stale(row, config=config):
        return "badflag", HTMLWriter.render_span(_("yes"))
    return "goodflag", _("no")


class PainterSvcIsStale(Painter):
    @property
    def ident(self) -> str:
        return "svc_is_stale"

    def title(self, cell: Cell) -> str:
        return _("Service is stale")

    def short_title(self, cell: Cell) -> str:
        return _("Stale")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_staleness"]

    @property
    def sorter(self) -> SorterName:
        return "svc_staleness"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_is_stale(row, config=self.config)


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


class PainterServiceCustomVariables(Painter):
    @property
    def ident(self) -> str:
        return "svc_custom_vars"

    def title(self, cell: Cell) -> str:
        return _("Service custom attributes")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_custom_variables"]

    def group_by(self, row: Row, cell: Cell) -> tuple[tuple[str, str], ...]:
        return tuple(row["service_custom_variables"].items())

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_custom_vars("service", row)

    def export_for_csv(self, row: Row, cell: Cell) -> str:
        return _export_custom_vars("service", row)

    def export_for_json(self, row: Row, cell: Cell) -> str:
        return _export_custom_vars("service", row)


class ABCPainterCustomVariable(Painter, abc.ABC):
    def title(self, cell: Cell) -> str:
        return self._dynamic_title(cell.painter_parameters())

    def short_title(self, cell: Cell) -> str:
        return self._dynamic_title(cell.painter_parameters())

    def export_title(self, cell: Cell) -> str:
        if (params := cell.painter_parameters()) is None:
            return self.ident
        return f"{self.ident}_{params['ident']}"

    def _dynamic_title(self, params: PainterParameters | None = None) -> str:
        if params is None:
            # Happens in view editor when adding a painter
            return self._default_title

        try:
            attributes: dict = dict(self._custom_attribute_choices())
            return attributes[params["ident"]]
        except KeyError:
            return self._default_title

    def list_title(self, cell: Cell) -> str:
        return self._default_title

    @property
    @abc.abstractmethod
    def _default_title(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def _object_type(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def _custom_attribute_choices(self) -> DropdownChoiceEntries:
        raise NotImplementedError()

    @property
    def parameters(self) -> Dictionary:
        return Dictionary(
            elements=[
                (
                    "ident",
                    DropdownChoice(
                        choices=self._custom_attribute_choices,
                        title=_("ID"),
                    ),
                ),
            ],
            title=_("Options"),
            optional_keys=[],
        )

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if (params := cell.painter_parameters()) is None:
            params = {}
        return paint_custom_var(self._object_type, params.get("ident", "").upper(), row)


class PainterServiceCustomVariable(ABCPainterCustomVariable):
    @property
    def ident(self) -> str:
        return "service_custom_variable"

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_custom_variable_names", "service_custom_variable_values"]

    @property
    def _default_title(self) -> str:
        return _("Service custom attribute")

    @property
    def _object_type(self) -> str:
        return "service"

    def _custom_attribute_choices(self) -> DropdownChoiceEntries:
        choices = []
        for ident, attr_spec in self.config.custom_service_attributes.items():
            choices.append((ident, attr_spec["title"]))
        return sorted(choices, key=lambda x: x[1])


class PainterHostCustomVariable(ABCPainterCustomVariable):
    @property
    def ident(self) -> str:
        return "host_custom_variable"

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def group_by(self, row: Row, cell: Cell) -> str | tuple[str, ...]:
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

    @property
    def _default_title(self) -> str:
        return _("Host custom attribute")

    @property
    def _object_type(self) -> str:
        return "host"

    def _custom_attribute_choices(self) -> DropdownChoiceEntries:
        choices = []
        for attr_spec in self.config.wato_host_attrs:
            choices.append((attr_spec["name"], attr_spec["title"]))
        return sorted(choices, key=lambda x: x[1])


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


class PainterHostState(Painter):
    @property
    def ident(self) -> str:
        return "host_state"

    def title(self, cell: Cell) -> str:
        return _("Host state")

    def short_title(self, cell: Cell) -> str:
        return _("State")

    def title_classes(self) -> list[str]:
        return ["center"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_has_been_checked", "host_state"]

    @property
    def sorter(self) -> SorterName:
        return "hoststate"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_host_state_short(row, config=self.config)


class PainterHostStateOnechar(Painter):
    @property
    def ident(self) -> str:
        return "host_state_onechar"

    def title(self, cell: Cell) -> str:
        return _("Host state (first character)")

    def short_title(self, cell: Cell) -> str:
        return _("S.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_has_been_checked", "host_state"]

    @property
    def sorter(self) -> SorterName:
        return "hoststate"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_host_state_short(row, short=True, config=self.config)


class PainterHostPluginOutput(Painter):
    @property
    def ident(self) -> str:
        return "host_plugin_output"

    def title(self, cell: Cell) -> str:
        return _("Summary")

    def list_title(self, cell):
        return _("Summary (Previously named: Status details or plug-in output)")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_plugin_output", "host_custom_variables"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (
            None,
            format_plugin_output(row["host_plugin_output"], request=self.request, row=row),
        )


class PainterHostPerfData(Painter):
    @property
    def ident(self) -> str:
        return "host_perf_data"

    def title(self, cell: Cell) -> str:
        return _("Host performance data")

    def short_title(self, cell: Cell) -> str:
        return _("Performance data")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_perf_data"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["host_perf_data"])


class PainterHostCheckCommand(Painter):
    @property
    def ident(self) -> str:
        return "host_check_command"

    def title(self, cell: Cell) -> str:
        return _("Host check command")

    def short_title(self, cell: Cell) -> str:
        return _("Check command")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_check_command"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["host_check_command"])


class PainterHostCheckCommandExpanded(Painter):
    @property
    def ident(self) -> str:
        return "host_check_command_expanded"

    def title(self, cell: Cell) -> str:
        return _("Host check command expanded")

    def short_title(self, cell: Cell) -> str:
        return _("Check command expanded")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_check_command_expanded"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["host_check_command_expanded"])


class PainterHostNotesURL(Painter):
    @property
    def ident(self) -> str:
        return "host_notes_url"

    def title(self, cell: Cell) -> str:
        return _("Notes (URL) for Hosts")

    def short_title(self, cell: Cell) -> str:
        return _("Notes URL")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_notes_url"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        raw_url = row.get("host_notes_url")
        if not raw_url:
            return None, HTML.empty()

        url = replace_action_url_macros(raw_url, "host", row)
        content = self.url_renderer.link_direct(url, html_text=url, target="_blank")
        return None, content


class PainterHostStateAge(Painter):
    @property
    def ident(self) -> str:
        return "host_state_age"

    def title(self, cell: Cell) -> str:
        return _("Age of the current host state")

    def short_title(self, cell: Cell) -> str:
        return _("Age")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_has_been_checked", "host_last_state_change"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["host_last_state_change"],
            row["host_has_been_checked"] == 1,
            60 * 10,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterHostCheckAge(Painter):
    @property
    def ident(self) -> str:
        return "host_check_age"

    def title(self, cell: Cell) -> str:
        return _("Time since the last check of the host")

    def short_title(self, cell: Cell) -> str:
        return _("Checked")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_has_been_checked", "host_last_check"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_checked(
            "host",
            row,
            config=self.config,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterHostNextCheck(Painter):
    @property
    def ident(self) -> str:
        return "host_next_check"

    def title(self, cell: Cell) -> str:
        return _("Time of the next scheduled host check")

    def short_title(self, cell: Cell) -> str:
        return _("Next check")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_next_check"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_future_time(
            row["host_next_check"],
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterHostNextNotification(Painter):
    @property
    def ident(self) -> str:
        return "host_next_notification"

    def title(self, cell: Cell) -> str:
        return _("Time of the next host notification")

    def short_title(self, cell: Cell) -> str:
        return _("Next notification")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_next_notification"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_future_time(
            row["host_next_notification"],
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterHostNotificationPostponementReason(Painter):
    @property
    def ident(self) -> str:
        return "host_notification_postponement_reason"

    def title(self, cell: Cell) -> str:
        return _("Notification postponement reason")

    def short_title(self, cell: Cell) -> str:
        return _("Notif. postponed")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_notification_postponement_reason"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_notification_postponement_reason("host", row)


class PainterHostLastNotification(Painter):
    @property
    def ident(self) -> str:
        return "host_last_notification"

    def title(self, cell: Cell) -> str:
        return _("Time of the last host notification")

    def short_title(self, cell: Cell) -> str:
        return _("last notification")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_last_notification"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["host_last_notification"],
            row["host_last_notification"],
            0,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterHostCheckLatency(Painter):
    @property
    def ident(self) -> str:
        return "host_check_latency"

    def title(self, cell: Cell) -> str:
        return _("Host check latency")

    def short_title(self, cell: Cell) -> str:
        return _("Latency")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_latency"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", approx_age(row["host_latency"]))


class PainterHostCheckDuration(Painter):
    @property
    def ident(self) -> str:
        return "host_check_duration"

    def title(self, cell: Cell) -> str:
        return _("Host check duration")

    def short_title(self, cell: Cell) -> str:
        return _("Duration")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_execution_time"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", approx_age(row["host_execution_time"]))


class PainterHostAttempt(Painter):
    @property
    def ident(self) -> str:
        return "host_attempt"

    def title(self, cell: Cell) -> str:
        return _("Current host check attempt")

    def short_title(self, cell: Cell) -> str:
        return _("Att.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_current_attempt", "host_max_check_attempts"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, "%d/%d" % (row["host_current_attempt"], row["host_max_check_attempts"]))


class PainterHostNormalInterval(Painter):
    @property
    def ident(self) -> str:
        return "host_normal_interval"

    def title(self, cell: Cell) -> str:
        return _("Normal check interval")

    def short_title(self, cell: Cell) -> str:
        return _("Check int.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_check_interval"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, approx_age(row["host_check_interval"] * 60.0))


class PainterHostRetryInterval(Painter):
    @property
    def ident(self) -> str:
        return "host_retry_interval"

    def title(self, cell: Cell) -> str:
        return _("Retry check interval")

    def short_title(self, cell: Cell) -> str:
        return _("Retry")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_retry_interval"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, approx_age(row["host_retry_interval"] * 60.0))


class PainterHostCheckInterval(Painter):
    @property
    def ident(self) -> str:
        return "host_check_interval"

    def title(self, cell: Cell) -> str:
        return _("Normal/retry check interval")

    def short_title(self, cell: Cell) -> str:
        return _("Interval")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_check_interval", "host_retry_interval"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (
            None,
            "%s / %s"
            % (
                approx_age(row["host_check_interval"] * 60.0),
                approx_age(row["host_retry_interval"] * 60.0),
            ),
        )


class PainterHostCheckType(Painter):
    @property
    def ident(self) -> str:
        return "host_check_type"

    def title(self, cell: Cell) -> str:
        return _("Host check type")

    def short_title(self, cell: Cell) -> str:
        return _("Type")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_check_type"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["host_check_type"] == 0 and "ACTIVE" or "PASSIVE")


class PainterHostInNotifper(Painter):
    @property
    def ident(self) -> str:
        return "host_in_notifper"

    def title(self, cell: Cell) -> str:
        return _("Host in notif. period")

    def short_title(self, cell: Cell) -> str:
        return _("in notif. p.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_in_notification_period"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "host_in_notification_period", False)


class PainterHostNotifper(Painter):
    @property
    def ident(self) -> str:
        return "host_notifper"

    def title(self, cell: Cell) -> str:
        return _("Host notification period")

    def short_title(self, cell: Cell) -> str:
        return _("notif.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_notification_period"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["host_notification_period"])


class PainterHostNotificationNumber(Painter):
    @property
    def ident(self) -> str:
        return "host_notification_number"

    def title(self, cell: Cell) -> str:
        return _("Host notification number")

    def short_title(self, cell: Cell) -> str:
        return _("N#")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_current_notification_number"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", str(row["host_current_notification_number"]))


class PainterHostFlapping(Painter):
    @property
    def ident(self) -> str:
        return "host_flapping"

    def title(self, cell: Cell) -> str:
        return _("Host is flapping")

    def short_title(self, cell: Cell) -> str:
        return _("Flap")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_is_flapping"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "host_is_flapping", True)


class PainterHostIsActive(Painter):
    @property
    def ident(self) -> str:
        return "host_is_active"

    def title(self, cell: Cell) -> str:
        return _("Host is active")

    def short_title(self, cell: Cell) -> str:
        return _("Active")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_active_checks_enabled"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "host_active_checks_enabled", False)


class PainterHostNotificationsEnabled(Painter):
    @property
    def ident(self) -> str:
        return "host_notifications_enabled"

    def title(self, cell: Cell) -> str:
        return _("Host notifications enabled")

    def short_title(self, cell: Cell) -> str:
        return _("Notif.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_notifications_enabled"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "host_notifications_enabled", False)


class PainterHostBlack(Painter):
    @property
    def ident(self) -> str:
        return "host_black"

    def title(self, cell: Cell) -> str:
        return _("Host name, red background if down or unreachable (deprecated)")

    def short_title(self, cell: Cell) -> str:
        return _("Host")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["site", "host_name", "host_state"]

    @property
    def sorter(self) -> SorterName:
        return "site_host"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        state = row["host_state"]
        if state != 0:
            return "nobr", HTMLWriter.render_div(row["host_name"], class_="hostdown")
        return "nobr", row["host_name"]


class PainterHostWithState(Painter):
    @property
    def ident(self) -> str:
        return "host_with_state"

    def title(self, cell: Cell) -> str:
        return _("Host name, marked red if down (deprecated)")

    def short_title(self, cell: Cell) -> str:
        return _("Host")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["site", "host_name", "host_state", "host_has_been_checked"]

    @property
    def sorter(self) -> SorterName:
        return "site_host"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if row["host_has_been_checked"]:
            state = row["host_state"]
        else:
            state = "p"
        if state != 0:
            return "state hstate hstate%s" % state, HTMLWriter.render_span(row["host_name"])
        return "nobr", row["host_name"]


class PainterHost(Painter):
    @property
    def ident(self) -> str:
        return "host"

    def title(self, cell: Cell) -> str:
        return _("Host name")

    def short_title(self, cell: Cell) -> str:
        return _("Host")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_name", "host_state", "host_has_been_checked", "host_scheduled_downtime_depth"]

    @property
    def sorter(self) -> SorterName:
        return "site_host"

    @property
    def parameters(self) -> Dictionary:
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
                        "Here you can configure the background color for specific states. "
                        "The coloring for host in downtime overrules all other coloring."
                    ),
                ),
            )
        ]

        return Dictionary(elements=elements, title=_("Options"), optional_keys=[])

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if (params := cell.painter_parameters()) is None:
            params = {}

        color_choices = params.get("color_choices", [])

        if row["host_has_been_checked"]:
            state = row["host_state"]
        else:
            state = "p"

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


class PainterAlias(Painter):
    @property
    def ident(self) -> str:
        return "alias"

    def title(self, cell: Cell) -> str:
        return _("Host alias")

    def short_title(self, cell: Cell) -> str:
        return _("Alias")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_alias"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", row["host_alias"])


class PainterHostAddress(Painter):
    @property
    def ident(self) -> str:
        return "host_address"

    def title(self, cell: Cell) -> str:
        return _("Host address (Primary)")

    def short_title(self, cell: Cell) -> str:
        return _("IP address")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_address"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", row["host_address"])


class PainterHostIpv4Address(Painter):
    @property
    def ident(self) -> str:
        return "host_ipv4_address"

    def title(self, cell: Cell) -> str:
        return _("Host address (IPv4)")

    def short_title(self, cell: Cell) -> str:
        return _("IPv4 address")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_custom_var("host", "ADDRESS_4", row)


class PainterHostIpv6Address(Painter):
    @property
    def ident(self) -> str:
        return "host_ipv6_address"

    def title(self, cell: Cell) -> str:
        return _("Host address (IPv6)")

    def short_title(self, cell: Cell) -> str:
        return _("IPv6 address")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_custom_var("host", "ADDRESS_6", row)


class PainterHostAddresses(Painter):
    @property
    def ident(self) -> str:
        return "host_addresses"

    def title(self, cell: Cell) -> str:
        return _("Host addresses (IPv4/IPv6)")

    def short_title(self, cell: Cell) -> str:
        return _("IP addresses")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_address", "host_custom_variable_names", "host_custom_variable_values"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        custom_vars = dict(
            zip(row["host_custom_variable_names"], row["host_custom_variable_values"])
        )

        if custom_vars.get("ADDRESS_FAMILY", "4") == "4":
            primary = custom_vars.get("ADDRESS_4", "")
            secondary = custom_vars.get("ADDRESS_6", "")
        else:
            primary = custom_vars.get("ADDRESS_6", "")
            secondary = custom_vars.get("ADDRESS_4", "")

        if secondary:
            secondary = " (%s)" % secondary
        return "", primary + secondary


class PainterHostAddressesAdditional(Painter):
    @property
    def ident(self) -> str:
        return "host_addresses_additional"

    def title(self, cell: Cell) -> str:
        return _("Host addresses (additional)")

    def short_title(self, cell: Cell) -> str:
        return _("Add. addresses")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        custom_vars = dict(
            zip(row["host_custom_variable_names"], row["host_custom_variable_values"])
        )

        ipv4_addresses = custom_vars.get("ADDRESSES_4", "").strip()
        ipv6_addresses = custom_vars.get("ADDRESSES_6", "").strip()

        addresses = []
        if ipv4_addresses:
            addresses += ipv4_addresses.split(" ")
        if ipv6_addresses:
            addresses += ipv6_addresses.split(" ")

        return "", ", ".join(addresses)


class PainterHostAddressFamily(Painter):
    @property
    def ident(self) -> str:
        return "host_address_family"

    def title(self, cell: Cell) -> str:
        return _("Host address family (Primary)")

    def short_title(self, cell: Cell) -> str:
        return _("Address family")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_custom_var("host", "ADDRESS_FAMILY", row)


class PainterHostAddressFamilies(Painter):
    @property
    def ident(self) -> str:
        return "host_address_families"

    def title(self, cell: Cell) -> str:
        return _("Host address families")

    def short_title(self, cell: Cell) -> str:
        return _("Address families")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        custom_vars = dict(
            zip(row["host_custom_variable_names"], row["host_custom_variable_values"])
        )

        primary = custom_vars.get("ADDRESS_FAMILY", "4")

        families = [primary]
        if primary == "6" and custom_vars.get("ADDRESS_4"):
            families.append("4")
        elif primary == "4" and custom_vars.get("ADDRESS_6"):
            families.append("6")

        return "", ", ".join(families)


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


class PainterNumServices(Painter):
    @property
    def ident(self) -> str:
        return "num_services"

    def title(self, cell: Cell) -> str:
        return _("Number of services")

    def short_title(self, cell: Cell) -> str:
        return ""

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_num_services"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, str(row["host_num_services"]))


class PainterNumServicesOk(Painter):
    @property
    def ident(self) -> str:
        return "num_services_ok"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state OK")

    def short_title(self, cell: Cell) -> str:
        return _("OK")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_num_services_ok"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(0, row["host_num_services_ok"])


class PainterNumProblems(Painter):
    @property
    def ident(self) -> str:
        return "num_problems"

    def title(self, cell: Cell) -> str:
        return _("Number of problems")

    def short_title(self, cell: Cell) -> str:
        return _("Prob.")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_num_services", "host_num_services_ok", "host_num_services_pending"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(
            "s",
            row["host_num_services"]
            - row["host_num_services_ok"]
            - row["host_num_services_pending"],
        )


class PainterNumServicesWarn(Painter):
    @property
    def ident(self) -> str:
        return "num_services_warn"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state WARN")

    def short_title(self, cell: Cell) -> str:
        return _("Wa")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_num_services_warn"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(1, row["host_num_services_warn"])


class PainterNumServicesCrit(Painter):
    @property
    def ident(self) -> str:
        return "num_services_crit"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state CRIT")

    def short_title(self, cell: Cell) -> str:
        return _("Cr")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_num_services_crit"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(2, row["host_num_services_crit"])


class PainterNumServicesUnknown(Painter):
    @property
    def ident(self) -> str:
        return "num_services_unknown"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state UNKNOWN")

    def short_title(self, cell: Cell) -> str:
        return _("Un")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_num_services_unknown"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(3, row["host_num_services_unknown"])


class PainterNumServicesPending(Painter):
    @property
    def ident(self) -> str:
        return "num_services_pending"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state PENDING")

    def short_title(self, cell: Cell) -> str:
        return _("Pd")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_num_services_pending"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count("p", row["host_num_services_pending"])


def _paint_service_list(row: Row, columnname: str, *, renderer: RenderLink) -> CellSpec:
    def sort_key(entry):
        if columnname.startswith("servicegroup"):
            return entry[0].lower(), entry[1].lower()
        return entry[0].lower()

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

        if checked:
            css = "state%d" % state
        else:
            css = "statep"

        h += HTMLWriter.render_div(HTMLWriter.render_span(link), class_=css)

    return "", HTMLWriter.render_div(h, class_="objectlist")


class PainterHostServices(Painter):
    @property
    def ident(self) -> str:
        return "host_services"

    def title(self, cell: Cell) -> str:
        return _("Services colored according to state")

    def short_title(self, cell: Cell) -> str:
        return _("Services")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_name", "host_services_with_state"]

    @property
    def parameters(self) -> Dictionary:
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
                        "Here you can configure which services are displayed depending on "
                        "their state. This is a filter at display level not query level."
                    ),
                ),
            )
        ]

        return Dictionary(elements=elements, title=_("Options"))

    def render(self, row: Row, cell: Cell) -> CellSpec:
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
            row, "host_services_with_state_filtered", renderer=self.url_renderer
        )


class PainterHostParents(Painter):
    @property
    def ident(self) -> str:
        return "host_parents"

    def title(self, cell: Cell) -> str:
        return _("Host's parents")

    def short_title(self, cell: Cell) -> str:
        return _("Parents")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_parents"]

    @property
    def use_painter_link(self) -> bool:
        return False  # This painter adds individual links for the single hosts

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_host_list(row["site"], row["host_parents"], request=self.request)


class PainterHostChilds(Painter):
    @property
    def ident(self) -> str:
        return "host_childs"

    def title(self, cell: Cell) -> str:
        return _("Host's children")

    def short_title(self, cell: Cell) -> str:
        return _("children")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_childs"]

    @property
    def use_painter_link(self) -> bool:
        return False  # This painter adds individual links for the single hosts

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_host_list(row["site"], row["host_childs"], request=self.request)


class PainterHostGroupMemberlist(Painter):
    @property
    def ident(self) -> str:
        return "host_group_memberlist"

    def title(self, cell: Cell) -> str:
        return _("Host groups the host is member of")

    def short_title(self, cell: Cell) -> str:
        return _("Groups")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_groups"]

    def group_by(self, row: Row, cell: Cell) -> tuple[str, ...]:
        return tuple(row["host_groups"])

    @property
    def use_painter_link(self) -> bool:
        return False  # This painter adds individual links for the single hosts

    def render(self, row: Row, cell: Cell) -> CellSpec:
        links = []
        for group in row["host_groups"]:
            link = self.url_renderer.link_from_filename(
                "view.py",
                html_text=group,
                query_args=[
                    ("view_name", "hostgroup"),
                    ("hostgroup", group),
                ],
            )
            links.append(link)
        return "", HTML.without_escaping(", ").join(links)


class PainterHostContacts(Painter):
    @property
    def ident(self) -> str:
        return "host_contacts"

    def title(self, cell: Cell) -> str:
        return _("Host contacts")

    def short_title(self, cell: Cell) -> str:
        return _("Contacts")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_contacts"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, ", ".join(row["host_contacts"]))


class PainterHostContactGroups(Painter):
    @property
    def ident(self) -> str:
        return "host_contact_groups"

    def title(self, cell: Cell) -> str:
        return _("Host contact groups")

    def short_title(self, cell: Cell) -> str:
        return _("Contact groups")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_contact_groups"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, ", ".join(row["host_contact_groups"]))


class PainterHostCustomNotes(Painter):
    @property
    def ident(self) -> str:
        return "host_custom_notes"

    def title(self, cell: Cell) -> str:
        return _("Custom host notes")

    def short_title(self, cell: Cell) -> str:
        return _("Notes")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_name", "host_address", "host_plugin_output"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_custom_notes("hosts", row, config=self.config)


class PainterHostComments(Painter):
    @property
    def ident(self) -> str:
        return "host_comments"

    def title(self, cell: Cell) -> str:
        return _("Host comments")

    def short_title(self, cell: Cell) -> str:
        return _("Comments")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_comments_with_info"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_comments("host_", row)


class PainterHostInDowntime(Painter):
    @property
    def ident(self) -> str:
        return "host_in_downtime"

    def title(self, cell: Cell) -> str:
        return _("Host in downtime")

    def short_title(self, cell: Cell) -> str:
        return _("Downtime")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_scheduled_downtime_depth"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "host_scheduled_downtime_depth", True)


class PainterHostAcknowledged(Painter):
    @property
    def ident(self) -> str:
        return "host_acknowledged"

    def title(self, cell: Cell) -> str:
        return _("Host problem acknowledged")

    def short_title(self, cell: Cell) -> str:
        return _("Ack")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_acknowledged"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_nagiosflag(row, "host_acknowledged", False)


class PainterHostStaleness(Painter):
    @property
    def ident(self) -> str:
        return "host_staleness"

    def title(self, cell: Cell) -> str:
        return _("Host staleness value")

    def short_title(self, cell: Cell) -> str:
        return _("Staleness")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_staleness"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", "%0.2f" % row.get("host_staleness", 0))


class PainterHostIsStale(Painter):
    @property
    def ident(self) -> str:
        return "host_is_stale"

    def title(self, cell: Cell) -> str:
        return _("Host is stale")

    def short_title(self, cell: Cell) -> str:
        return _("Stale")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_staleness"]

    @property
    def sorter(self) -> SorterName:
        return "svc_staleness"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_is_stale(row, config=self.config)


class PainterHostCustomVariables(Painter):
    BLACKLIST: list[str] = [
        "FILENAME",
        "TAGS",
        "ADDRESS_4",
        "ADDRESS_6",
        "ADDRESS_FAMILY",
        "NODEIPS",
        "NODEIPS_4",
        "NODEIPS_6",
    ]

    @property
    def ident(self) -> str:
        return "host_custom_vars"

    def title(self, cell: Cell) -> str:
        return _("Host custom attributes")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_custom_variables"]

    def group_by(self, row: Row, cell: Cell) -> tuple[tuple[str, str], ...]:
        return tuple(row["host_custom_variables"].items())

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_custom_vars("host", row, self.BLACKLIST)

    def export_for_csv(self, row: Row, cell: Cell) -> str:
        return _export_custom_vars("host", row, self.BLACKLIST)

    def export_for_json(self, row: Row, cell: Cell) -> str:
        return _export_custom_vars("host", row, self.BLACKLIST)


def _paint_discovery_output(
    field: str,
    row: Row,
    *,
    renderer: RenderLink,
    theme: Theme,
) -> CellSpec:
    value = row[field]
    if field == "discovery_state":
        ruleset_url = "wato.py?mode=edit_ruleset&varname=ignored_services"
        discovery_url = "wato.py?mode=inventory&host=%s&mode=inventory" % row["host_name"]

        return (
            None,
            {
                "ignored": html.render_icon_button(
                    ruleset_url,
                    _("Disabled (configured away by admin)"),
                    "rulesets",
                    theme=theme,
                )
                + HTML.with_escaping(_("Disabled (configured away by admin)")),
                "vanished": html.render_icon_button(
                    discovery_url,
                    _("Vanished (checked, but no longer exist)"),
                    "services",
                    theme=theme,
                )
                + HTML.with_escaping(_("Vanished (checked, but no longer exist)")),
                "unmonitored": html.render_icon_button(
                    discovery_url,
                    _("Available (missing)"),
                    "services",
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


class PainterServiceDiscoveryState(Painter):
    @property
    def ident(self) -> str:
        return "service_discovery_state"

    def title(self, cell: Cell) -> str:
        return _("Service discovery: State")

    def short_title(self, cell: Cell) -> str:
        return _("State")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["discovery_state"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_discovery_output(
            "discovery_state", row, renderer=self.url_renderer, theme=self.theme
        )


class PainterServiceDiscoveryCheck(Painter):
    @property
    def ident(self) -> str:
        return "service_discovery_check"

    def title(self, cell: Cell) -> str:
        return _("Service discovery: Check type")

    def short_title(self, cell: Cell) -> str:
        return _("Check type")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["discovery_state", "discovery_check", "discovery_service"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_discovery_output(
            "discovery_check", row, renderer=self.url_renderer, theme=self.theme
        )


class PainterServiceDiscoveryService(Painter):
    @property
    def ident(self) -> str:
        return "service_discovery_service"

    def title(self, cell: Cell) -> str:
        return _("Service discovery: Service name")

    def short_title(self, cell: Cell) -> str:
        return _("Service name")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["discovery_state", "discovery_check", "discovery_service"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_discovery_output(
            "discovery_service", row, renderer=self.url_renderer, theme=self.theme
        )


#    _   _           _
#   | | | | ___  ___| |_ __ _ _ __ ___  _   _ _ __  ___
#   | |_| |/ _ \/ __| __/ _` | '__/ _ \| | | | '_ \/ __|
#   |  _  | (_) \__ \ || (_| | | | (_) | |_| | |_) \__ \
#   |_| |_|\___/|___/\__\__, |_|  \___/ \__,_| .__/|___/
#                       |___/                |_|
#
class PainterHostgroupHosts(Painter):
    @property
    def ident(self) -> str:
        return "hostgroup_hosts"

    def title(self, cell: Cell) -> str:
        return _("Hosts colored according to state (host group)")

    def short_title(self, cell: Cell) -> str:
        return _("Hosts")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_members_with_state"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        divs = []
        for host, state, checked in row["hostgroup_members_with_state"]:
            link = self.url_renderer.link_from_filename(
                "view.py",
                html_text=host,
                query_args=[
                    ("view_name", "host"),
                    ("site", row["site"]),
                    ("host", host),
                ],
            )
            if checked:
                css = "hstate%d" % state
            else:
                css = "hstatep"
            divs.append(HTMLWriter.render_div(link, class_=css))
        return "", HTMLWriter.render_div(HTML.empty().join(divs), class_="objectlist")


class PainterHgNumServices(Painter):
    @property
    def ident(self) -> str:
        return "hg_num_services"

    def title(self, cell: Cell) -> str:
        return _("Number of services (host group)")

    def short_title(self, cell: Cell) -> str:
        return ""

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_num_services"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, str(row["hostgroup_num_services"]))


class PainterHgNumServicesOk(Painter):
    @property
    def ident(self) -> str:
        return "hg_num_services_ok"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state OK (host group)")

    def short_title(self, cell: Cell) -> str:
        return _("O")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_num_services_ok"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(0, row["hostgroup_num_services_ok"])


class PainterHgNumServicesWarn(Painter):
    @property
    def ident(self) -> str:
        return "hg_num_services_warn"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state WARN (host group)")

    def short_title(self, cell: Cell) -> str:
        return _("W")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_num_services_warn"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(1, row["hostgroup_num_services_warn"])


class PainterHgNumServicesCrit(Painter):
    @property
    def ident(self) -> str:
        return "hg_num_services_crit"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state CRIT (host group)")

    def short_title(self, cell: Cell) -> str:
        return _("C")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_num_services_crit"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(2, row["hostgroup_num_services_crit"])


class PainterHgNumServicesUnknown(Painter):
    @property
    def ident(self) -> str:
        return "hg_num_services_unknown"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state UNKNOWN (host group)")

    def short_title(self, cell: Cell) -> str:
        return _("U")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_num_services_unknown"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(3, row["hostgroup_num_services_unknown"])


class PainterHgNumServicesPending(Painter):
    @property
    def ident(self) -> str:
        return "hg_num_services_pending"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state PENDING (host group)")

    def short_title(self, cell: Cell) -> str:
        return _("P")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_num_services_pending"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count("p", row["hostgroup_num_services_pending"])


class PainterHgNumHostsUp(Painter):
    @property
    def ident(self) -> str:
        return "hg_num_hosts_up"

    def title(self, cell: Cell) -> str:
        return _("Number of hosts in state UP (host group)")

    def short_title(self, cell: Cell) -> str:
        return _("Up")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_num_hosts_up"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_host_count(0, row["hostgroup_num_hosts_up"])


class PainterHgNumHostsDown(Painter):
    @property
    def ident(self) -> str:
        return "hg_num_hosts_down"

    def title(self, cell: Cell) -> str:
        return _("Number of hosts in state DOWN (host group)")

    def short_title(self, cell: Cell) -> str:
        return _("Dw")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_num_hosts_down"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_host_count(1, row["hostgroup_num_hosts_down"])


class PainterHgNumHostsUnreach(Painter):
    @property
    def ident(self) -> str:
        return "hg_num_hosts_unreach"

    def title(self, cell: Cell) -> str:
        return _("Number of hosts in state UNREACH (host group)")

    def short_title(self, cell: Cell) -> str:
        return _("Un")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_num_hosts_unreach"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_host_count(2, row["hostgroup_num_hosts_unreach"])


class PainterHgNumHostsPending(Painter):
    @property
    def ident(self) -> str:
        return "hg_num_hosts_pending"

    def title(self, cell: Cell) -> str:
        return _("Number of hosts in state PENDING (host group)")

    def short_title(self, cell: Cell) -> str:
        return _("Pd")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_num_hosts_pending"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_host_count(None, row["hostgroup_num_hosts_pending"])


class PainterHgName(Painter):
    @property
    def ident(self) -> str:
        return "hg_name"

    def title(self, cell: Cell) -> str:
        return _("Host group name")

    def short_title(self, cell: Cell) -> str:
        return _("Name")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_name"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["hostgroup_name"])


class PainterHgAlias(Painter):
    @property
    def ident(self) -> str:
        return "hg_alias"

    def title(self, cell: Cell) -> str:
        return _("Host group alias")

    def short_title(self, cell: Cell) -> str:
        return _("Alias")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["hostgroup_alias"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["hostgroup_alias"])


#    ____                  _
#   / ___|  ___ _ ____   _(_) ___ ___  __ _ _ __ ___  _   _ _ __  ___
#   \___ \ / _ \ '__\ \ / / |/ __/ _ \/ _` | '__/ _ \| | | | '_ \/ __|
#    ___) |  __/ |   \ V /| | (_|  __/ (_| | | | (_) | |_| | |_) \__ \
#   |____/ \___|_|    \_/ |_|\___\___|\__, |_|  \___/ \__,_| .__/|___/
#                                     |___/                |_|


class PainterSgServices(Painter):
    @property
    def ident(self) -> str:
        return "sg_services"

    def title(self, cell: Cell) -> str:
        return _("Services colored according to state (service group)")

    def short_title(self, cell: Cell) -> str:
        return _("Services")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["servicegroup_members_with_state"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_service_list(
            row, "servicegroup_members_with_state", renderer=self.url_renderer
        )


class PainterSgNumServices(Painter):
    @property
    def ident(self) -> str:
        return "sg_num_services"

    def title(self, cell: Cell) -> str:
        return _("Number of services (service group)")

    def short_title(self, cell: Cell) -> str:
        return ""

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["servicegroup_num_services"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, str(row["servicegroup_num_services"]))


class PainterSgNumServicesOk(Painter):
    @property
    def ident(self) -> str:
        return "sg_num_services_ok"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state OK (service group)")

    def short_title(self, cell: Cell) -> str:
        return _("O")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["servicegroup_num_services_ok"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(0, row["servicegroup_num_services_ok"])


class PainterSgNumServicesWarn(Painter):
    @property
    def ident(self) -> str:
        return "sg_num_services_warn"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state WARN (service group)")

    def short_title(self, cell: Cell) -> str:
        return _("W")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["servicegroup_num_services_warn"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(1, row["servicegroup_num_services_warn"])


class PainterSgNumServicesCrit(Painter):
    @property
    def ident(self) -> str:
        return "sg_num_services_crit"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state CRIT (service group)")

    def short_title(self, cell: Cell) -> str:
        return _("C")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["servicegroup_num_services_crit"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(2, row["servicegroup_num_services_crit"])


class PainterSgNumServicesUnknown(Painter):
    @property
    def ident(self) -> str:
        return "sg_num_services_unknown"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state UNKNOWN (service group)")

    def short_title(self, cell: Cell) -> str:
        return _("U")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["servicegroup_num_services_unknown"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(3, row["servicegroup_num_services_unknown"])


class PainterSgNumServicesPending(Painter):
    @property
    def ident(self) -> str:
        return "sg_num_services_pending"

    def title(self, cell: Cell) -> str:
        return _("Number of services in state PENDING (service group)")

    def short_title(self, cell: Cell) -> str:
        return _("P")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["servicegroup_num_services_pending"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count("p", row["servicegroup_num_services_pending"])


class PainterSgName(Painter):
    @property
    def ident(self) -> str:
        return "sg_name"

    def title(self, cell: Cell) -> str:
        return _("Service group name")

    def short_title(self, cell: Cell) -> str:
        return _("Name")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["servicegroup_name"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["servicegroup_name"])


class PainterSgAlias(Painter):
    @property
    def ident(self) -> str:
        return "sg_alias"

    def title(self, cell: Cell) -> str:
        return _("Service group alias")

    def short_title(self, cell: Cell) -> str:
        return _("Alias")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["servicegroup_alias"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["servicegroup_alias"])


#     ____                                     _
#    / ___|___  _ __ ___  _ __ ___   ___ _ __ | |_ ___
#   | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \| __/ __|
#   | |__| (_) | | | | | | | | | | |  __/ | | | |_\__ \
#    \____\___/|_| |_| |_|_| |_| |_|\___|_| |_|\__|___/
#


class PainterCommentId(Painter):
    @property
    def ident(self) -> str:
        return "comment_id"

    def title(self, cell: Cell) -> str:
        return _("Comment id")

    def short_title(self, cell: Cell) -> str:
        return _("ID")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["comment_id"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, str(row["comment_id"]))


class PainterCommentAuthor(Painter):
    @property
    def ident(self) -> str:
        return "comment_author"

    def title(self, cell: Cell) -> str:
        return _("Comment author")

    def short_title(self, cell: Cell) -> str:
        return _("Author")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["comment_author"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["comment_author"])


class PainterCommentComment(Painter):
    @property
    def ident(self) -> str:
        return "comment_comment"

    def title(self, cell: Cell) -> str:
        return _("Comment text")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["comment_comment"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, format_plugin_output(row["comment_comment"], request=self.request, row=row))


class PainterCommentWhat(Painter):
    @property
    def ident(self) -> str:
        return "comment_what"

    def title(self, cell: Cell) -> str:
        return _("Comment type (host/service)")

    def short_title(self, cell: Cell) -> str:
        return _("Type")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["comment_type"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["comment_type"] == 1 and _("Host") or _("Service"))


class PainterCommentTime(Painter):
    @property
    def ident(self) -> str:
        return "comment_time"

    def title(self, cell: Cell) -> str:
        return _("Comment entry time")

    def short_title(self, cell: Cell) -> str:
        return _("Time")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["comment_entry_time"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["comment_entry_time"],
            True,
            3600,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterCommentExpires(Painter):
    @property
    def ident(self) -> str:
        return "comment_expires"

    def title(self, cell: Cell) -> str:
        return _("Comment expiry time")

    def short_title(self, cell: Cell) -> str:
        return _("Expires")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["comment_expire_time"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["comment_expire_time"],
            row["comment_expire_time"] != 0,
            3600,
            request=self.request,
            painter_options=self._painter_options,
            what="future",
        )


class PainterCommentEntryType(Painter):
    @property
    def ident(self) -> str:
        return "comment_entry_type"

    def title(self, cell: Cell) -> str:
        return _("Comment entry type (user/downtime/flapping/ack)")

    def short_title(self, cell: Cell) -> str:
        return _("E.Type")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["comment_entry_type", "host_name", "service_description"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        t = row["comment_entry_type"]
        linkview = None
        if t == 1:
            icon = "comment"
            help_txt = _("Comment")
        elif t == 2:
            icon = "downtime"
            help_txt = _("Downtime")
            if row["service_description"]:
                linkview = "downtimes_of_service"
            else:
                linkview = "downtimes_of_host"

        elif t == 3:
            icon = "flapping"
            help_txt = _("Flapping")
        elif t == 4:
            icon = "ack"
            help_txt = _("Acknowledgement")
        else:
            return "", ""
        code: str | HTML = html.render_icon(icon, help_txt, theme=self.theme)
        if linkview:
            code = render_link_to_view(
                code, row, VisualLinkSpec("views", linkview), request=self.request
            )
        return "icons", code


#    ____                      _   _
#   |  _ \  _____      ___ __ | |_(_)_ __ ___   ___  ___
#   | | | |/ _ \ \ /\ / / '_ \| __| | '_ ` _ \ / _ \/ __|
#   | |_| | (_) \ V  V /| | | | |_| | | | | | |  __/\__ \
#   |____/ \___/ \_/\_/ |_| |_|\__|_|_| |_| |_|\___||___/
#


class PainterDowntimeId(Painter):
    @property
    def ident(self) -> str:
        return "downtime_id"

    def title(self, cell: Cell) -> str:
        return _("Downtime id")

    def short_title(self, cell: Cell) -> str:
        return _("ID")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["downtime_id"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, "%d" % row["downtime_id"])


class PainterDowntimeAuthor(Painter):
    @property
    def ident(self) -> str:
        return "downtime_author"

    def title(self, cell: Cell) -> str:
        return _("Downtime author")

    def short_title(self, cell: Cell) -> str:
        return _("Author")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["downtime_author"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["downtime_author"])


class PainterDowntimeComment(Painter):
    @property
    def ident(self) -> str:
        return "downtime_comment"

    def title(self, cell: Cell) -> str:
        return _("Downtime comment")

    def short_title(self, cell: Cell) -> str:
        return _("Comment")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["downtime_comment"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, format_plugin_output(row["downtime_comment"], request=self.request, row=row))


class PainterDowntimeFixed(Painter):
    @property
    def ident(self) -> str:
        return "downtime_fixed"

    def title(self, cell: Cell) -> str:
        return _("Downtime start mode")

    def short_title(self, cell: Cell) -> str:
        return _("Mode")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["downtime_fixed"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["downtime_fixed"] == 0 and _("flexible") or _("fixed"))


class PainterDowntimeOrigin(Painter):
    @property
    def ident(self) -> str:
        return "downtime_origin"

    def title(self, cell: Cell) -> str:
        return _("Downtime origin")

    def short_title(self, cell: Cell) -> str:
        return _("Origin")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["downtime_origin"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["downtime_origin"] == 1 and _("configuration") or _("command"))


class PainterDowntimeWhat(Painter):
    @property
    def ident(self) -> str:
        return "downtime_what"

    def title(self, cell: Cell) -> str:
        return _("Downtime for host/service")

    def short_title(self, cell: Cell) -> str:
        return _("for")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["downtime_is_service"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["downtime_is_service"] and _("Service") or _("Host"))


class PainterDowntimeType(Painter):
    @property
    def ident(self) -> str:
        return "downtime_type"

    def title(self, cell: Cell) -> str:
        return _("Downtime active or pending")

    def short_title(self, cell: Cell) -> str:
        return _("act/pend")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["is_pending"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return (None, row["is_pending"] == 0 and _("active") or _("pending"))


class PainterDowntimeEntryTime(Painter):
    @property
    def ident(self) -> str:
        return "downtime_entry_time"

    def title(self, cell: Cell) -> str:
        return _("Downtime entry time")

    def short_title(self, cell: Cell) -> str:
        return _("Entry")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["downtime_entry_time"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["downtime_entry_time"],
            True,
            3600,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterDowntimeStartTime(Painter):
    @property
    def ident(self) -> str:
        return "downtime_start_time"

    def title(self, cell: Cell) -> str:
        return _("Downtime start time")

    def short_title(self, cell: Cell) -> str:
        return _("Start")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["downtime_start_time"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["downtime_start_time"],
            True,
            3600,
            request=self.request,
            painter_options=self._painter_options,
            what="both",
        )


class PainterDowntimeEndTime(Painter):
    @property
    def ident(self) -> str:
        return "downtime_end_time"

    def title(self, cell: Cell) -> str:
        return _("Downtime end time")

    def short_title(self, cell: Cell) -> str:
        return _("End")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["downtime_end_time"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["downtime_end_time"],
            True,
            3600,
            request=self.request,
            painter_options=self._painter_options,
            what="both",
        )


class PainterDowntimeDuration(Painter):
    @property
    def ident(self) -> str:
        return "downtime_duration"

    def title(self, cell: Cell) -> str:
        return _("Downtime duration (if flexible)")

    def short_title(self, cell: Cell) -> str:
        return _("Flex. Duration")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["downtime_duration", "downtime_fixed"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if row["downtime_fixed"] == 0:
            return "number", "%02d:%02d:00" % divmod(int(row["downtime_duration"] / 60.0), 60)
        return "", ""


#    _
#   | |    ___   __ _
#   | |   / _ \ / _` |
#   | |__| (_) | (_| |
#   |_____\___/ \__, |
#               |___/


class PainterLogDetailsHistory(Painter):
    @property
    def ident(self) -> str:
        return "log_details_history"

    def title(self, cell: Cell) -> str:
        return _("Log: Details")

    @property
    def columns(self) -> list[ColumnName]:
        return [
            "log_long_plugin_output",
            "service_check_command",
            "service_custom_variables",
            "host_custom_variables",
        ]

    @property
    def parameters(self) -> Dictionary:
        return Dictionary(
            elements=[
                (
                    "max_len",
                    Integer(
                        title=_("Maximum number of characters to show"),
                        help=_(
                            "Truncate content at this amount of characters."
                            "A zero value mean not to truncate"
                        ),
                        default_value=0,
                        minvalue=0,
                    ),
                ),
            ],
        )

    def render(self, row: Row, cell: Cell) -> CellSpec:
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
            request=self.request,
            row=row_to_format,
            newlineishs_to_brs=True,
        )

        if is_ps_check:
            content = HTML.without_escaping(str(content).replace("&bsol%3B", "\\"))

        # has to be placed after format_plugin_output() to keep links save from
        # escaping
        custom_vars = row.get("service_custom_variables", row.get("host_custom_variables", {}))
        escape_plugin_output = custom_vars.get("ESCAPE_PLUGIN_OUTPUT", "1") == "0"
        if long_output_len > max_len and escape_plugin_output and non_displayable_html:
            setting_link_tag = self.url_renderer.link_from_filename(
                "wato.py",
                html_text="(%s)" % _("Increase limit for future entries"),
                query_args=[
                    ("mode", "edit_configvar"),
                    ("varname", "max_long_output_size"),
                ],
            )
            content = (
                _("HTML output can not be rendered because of truncated data. ")
                + setting_link_tag
                + html.render_b("WARN", class_="stmark state1")
                + html.render_br()
                + content
            )

        return paint_stalified(row, content, config=self.config)


class PainterLogMessage(Painter):
    @property
    def ident(self) -> str:
        return "log_message"

    def title(self, cell: Cell) -> str:
        return _("Log: complete message")

    def short_title(self, cell: Cell) -> str:
        return _("Message")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_message"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", row["log_message"])


class PainterLogPluginOutput(Painter):
    @property
    def ident(self) -> str:
        return "log_plugin_output"

    def title(self, cell: Cell) -> str:
        return _("Log: Summary")

    def short_title(self, cell: Cell) -> str:
        return _("Summary")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_plugin_output", "log_type", "log_state_type", "log_comment"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        if output := self._decode_item(row, column="log_plugin_output"):
            return "", format_plugin_output(output, request=self.request, row=row)

        if comment := self._decode_item(row, column="log_comment"):
            return "", comment

        log_type = row["log_type"]
        lst = row["log_state_type"]
        if "FLAPPING" in log_type:
            what = _("host") if "HOST" in log_type else _("service")
            if lst == "STOPPED":
                return "", _("The %s stopped flapping") % what
            return "", _("The %s started flapping") % what
        if lst:
            return "", (lst + " - " + log_type)
        return "", ""

    @staticmethod
    def _decode_item(row: Row, *, column: Literal["log_plugin_output", "log_comment"]) -> str:
        """Decode escaped characters coming from Nagios history monitoring."""
        # TODO: decode all escaped characters coming from monitoring history.
        return row.get(column, "").replace("%3B", ";")


class PainterLogWhat(Painter):
    @property
    def ident(self) -> str:
        return "log_what"

    def title(self, cell: Cell) -> str:
        return _("Log: host or service")

    def short_title(self, cell: Cell) -> str:
        return _("Host/Service")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_type"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        lt = row["log_type"]
        if "HOST" in lt:
            return "", _("Host")
        if "SERVICE" in lt or "SVC" in lt:
            return "", _("Service")
        return "", _("Program")


class PainterLogAttempt(Painter):
    @property
    def ident(self) -> str:
        return "log_attempt"

    def title(self, cell: Cell) -> str:
        return _("Log: number of check attempt")

    def short_title(self, cell: Cell) -> str:
        return _("Att.")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_attempt"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", str(row["log_attempt"]))


class PainterLogStateType(Painter):
    @property
    def ident(self) -> str:
        return "log_state_type"

    def title(self, cell: Cell) -> str:
        return _('Log: state type (DEPRECATED: Use "state information")')

    def short_title(self, cell: Cell) -> str:
        return _("Type")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_state_type"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", row["log_state_type"])


class PainterLogStateInfo(Painter):
    @property
    def ident(self) -> str:
        return "log_state_info"

    def title(self, cell: Cell) -> str:
        return _("Log: State information")

    def short_title(self, cell: Cell) -> str:
        return _("State info")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_state_info", "log_state_type"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        info = row["log_state_info"]

        # be compatible to <1.7 remote sites and show log_state_type content as fallback
        if not info:
            info = row["log_state_type"]

        return ("", info)


class PainterLogType(Painter):
    @property
    def ident(self) -> str:
        return "log_type"

    def title(self, cell: Cell) -> str:
        return _("Log: event")

    def short_title(self, cell: Cell) -> str:
        return _("Event")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_type"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("nowrap", row["log_type"])


class PainterLogContactName(Painter):
    @property
    def ident(self) -> str:
        return "log_contact_name"

    def title(self, cell: Cell) -> str:
        return _("Log: contact name")

    def short_title(self, cell: Cell) -> str:
        return _("Contact")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_contact_name"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        target_view_name = self.url_renderer.get_filename(
            filename="contactnotifications",
            mobile_filename="mobile_contactnotifications",
        )
        links = [
            self.url_renderer.link_from_filename(
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


class PainterLogCommand(Painter):
    @property
    def ident(self) -> str:
        return "log_command"

    def title(self, cell: Cell) -> str:
        return _("Log: command/plug-in")

    def short_title(self, cell: Cell) -> str:
        return _("Command")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_command_name"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("nowrap", row["log_command_name"])


class PainterLogIcon(Painter):
    @property
    def ident(self) -> str:
        return "log_icon"

    def title(self, cell: Cell) -> str:
        return _("Log: event icon")

    def short_title(self, cell: Cell) -> str:
        return ""

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_type", "log_state", "log_state_type", "log_command_name"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        img = None
        log_type = row["log_type"]
        log_state = row["log_state"]

        if log_type == "SERVICE ALERT":
            img = {0: "ok", 1: "warn", 2: "crit", 3: "unknown"}.get(row["log_state"])
            title = _("Service alert")

        elif log_type == "HOST ALERT":
            img = {0: "up", 1: "down", 2: "unreach"}.get(row["log_state"])
            title = _("Host alert")

        elif log_type.endswith("ALERT HANDLER STARTED"):
            img = "alert_handler_started"
            title = _("Alert handler started")

        elif log_type.endswith("ALERT HANDLER STOPPED"):
            if log_state == 0:
                img = "alert_handler_stopped"
                title = _("Alert handler stopped")
            else:
                img = "alert_handler_failed"
                title = _("Alert handler failed")

        elif "DOWNTIME" in log_type:
            if row["log_state_type"] in ["END", "STOPPED"]:
                img = "downtimestop"
                title = _("Downtime stopped")
            else:
                img = "downtime"
                title = _("Downtime")

        elif log_type.endswith("NOTIFICATION"):
            if row["log_command_name"] == "check-mk-notify":
                img = "cmk_notify"
                title = _("Core produced a notification")
            else:
                img = "notify"
                title = _("User notification")

        elif log_type.endswith("NOTIFICATION RESULT"):
            img = "notify_result"
            title = _("Final notification result")

        elif log_type.endswith("NOTIFICATION PROGRESS"):
            img = "notify_progress"
            title = _("The notification is being processed")

        elif log_type == "EXTERNAL COMMAND":
            img = "command"
            title = _("External command")

        elif "restarting..." in log_type:
            img = "restart"
            title = _("Core restarted")

        elif "Reloading configuration" in log_type:
            img = "reload"
            title = _("Core configuration reloaded")

        elif "starting..." in log_type:
            img = "start"
            title = _("Core started")

        elif "shutdown..." in log_type or "shutting down" in log_type:
            img = "stop"
            title = _("Core stopped")

        elif " FLAPPING " in log_type:
            img = "flapping"
            title = _("Flapping")

        elif "ACKNOWLEDGE ALERT" in log_type:
            if row["log_state_type"] == "STARTED":
                img = "ack"
                title = _("Acknowledged")
            else:
                img = "ackstop"
                title = _("Stopped acknowledgement")

        if img:
            return "icon", html.render_icon("alert_" + img, title=title, theme=self.theme)
        return "icon", ""


class PainterLogOptions(Painter):
    @property
    def ident(self) -> str:
        return "log_options"

    def title(self, cell: Cell) -> str:
        return _("Log: informational part of message")

    def short_title(self, cell: Cell) -> str:
        return _("Info")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_options"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", row["log_options"])


class PainterLogComment(Painter):
    @property
    def ident(self) -> str:
        return "log_comment"

    def title(self, cell: Cell) -> str:
        return _("Log: comment")

    def short_title(self, cell: Cell) -> str:
        return _("Comment")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_options"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        msg = row["log_options"]
        if ";" in msg:
            parts = msg.split(";")
            if len(parts) > 6:
                return ("", parts[-1])
        return ("", "")


class PainterLogTime(Painter):
    @property
    def ident(self) -> str:
        return "log_time"

    def title(self, cell: Cell) -> str:
        return _("Log: entry time")

    def short_title(self, cell: Cell) -> str:
        return _("Time")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_time"]

    @property
    def painter_options(self) -> list[str]:
        return ["ts_format", "ts_date"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_age(
            row["log_time"],
            True,
            3600 * 24,
            request=self.request,
            painter_options=self._painter_options,
        )


class PainterLogLineno(Painter):
    @property
    def ident(self) -> str:
        return "log_lineno"

    def title(self, cell: Cell) -> str:
        return _("Log: line number in log file")

    def short_title(self, cell: Cell) -> str:
        return _("Line")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_lineno"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("number", str(row["log_lineno"]))


class PainterLogDate(Painter):
    @property
    def ident(self) -> str:
        return "log_date"

    def title(self, cell: Cell) -> str:
        return _("Log: day of entry")

    def short_title(self, cell: Cell) -> str:
        return _("Date")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_time"]

    def group_by(self, row: Row, cell: Cell) -> str:
        return str(_paint_day(row["log_time"])[1])

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_day(row["log_time"])


class PainterLogState(Painter):
    @property
    def ident(self) -> str:
        return "log_state"

    def title(self, cell: Cell) -> str:
        return _("Log: state of host/service at log time")

    def short_title(self, cell: Cell) -> str:
        return _("State")

    def title_classes(self) -> list[str]:
        return ["center"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_state", "log_state_type", "log_service_description", "log_type"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
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
                config=self.config,
            )
        return _paint_host_state_short(
            {"host_has_been_checked": 1, "host_state": state},
            config=self.config,
        )


# Alert statistics


class PainterAlertStatsOk(Painter):
    @property
    def ident(self) -> str:
        return "alert_stats_ok"

    def title(self, cell: Cell) -> str:
        return _("Alert statistics: Number of recoveries")

    def short_title(self, cell: Cell) -> str:
        return _("OK")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_alerts_ok"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", str(row["log_alerts_ok"]))


class PainterAlertStatsWarn(Painter):
    @property
    def ident(self) -> str:
        return "alert_stats_warn"

    def title(self, cell: Cell) -> str:
        return _("Alert statistics: Number of warnings")

    def short_title(self, cell: Cell) -> str:
        return _("WARN")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_alerts_warn"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(1, row["log_alerts_warn"])


class PainterAlertStatsCrit(Painter):
    @property
    def ident(self) -> str:
        return "alert_stats_crit"

    def title(self, cell: Cell) -> str:
        return _("Alert statistics: Number of critical alerts")

    def short_title(self, cell: Cell) -> str:
        return _("CRIT")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_alerts_crit"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(2, row["log_alerts_crit"])


class PainterAlertStatsUnknown(Painter):
    @property
    def ident(self) -> str:
        return "alert_stats_unknown"

    def title(self, cell: Cell) -> str:
        return _("Alert statistics: Number of unknown alerts")

    def short_title(self, cell: Cell) -> str:
        return _("UNKN")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_alerts_unknown"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count(3, row["log_alerts_unknown"])


class PainterAlertStatsProblem(Painter):
    @property
    def ident(self) -> str:
        return "alert_stats_problem"

    def title(self, cell: Cell) -> str:
        return _("Alert statistics: Number of problem alerts")

    def short_title(self, cell: Cell) -> str:
        return _("Problems")

    def title_classes(self) -> list[str]:
        return ["right"]

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["log_alerts_problem"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_svc_count("s", row["log_alerts_problem"])


#
# TAGS
#


class PainterHostTags(Painter):
    @property
    def ident(self) -> str:
        return "host_tags"

    def title(self, cell: Cell) -> str:
        return _("Host tags")

    def short_title(self, cell: Cell) -> str:
        return self.title(cell)

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_tags"]

    @property
    def sorter(self) -> SorterName:
        return "host"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return "", render_tag_groups(
            get_tag_groups(row, "host"), "host", with_links=True, request=self.request
        )


class ABCPainterTagsWithTitles(Painter, abc.ABC):
    @property
    @abc.abstractmethod
    def object_type(self):
        raise NotImplementedError()

    def render(self, row: Row, cell: Cell) -> CellSpec:
        entries = self._get_entries(row)
        return "", HTMLWriter.render_br().join(
            [
                escaping.escape_to_html_permissive("%s: %s" % e, escape_links=False)
                for e in sorted(entries)
            ]
        )

    def _get_entries(self, row):
        entries = []
        for tag_group_id, tag_id in get_tag_groups(row, self.object_type).items():
            tag_group = self.config.tags.get_tag_group(tag_group_id)
            if tag_group:
                entries.append(
                    (tag_group.title, dict(tag_group.get_tag_choices()).get(tag_id, tag_id))
                )
                continue

            aux_tag_title = dict(self.config.tags.aux_tag_list.get_choices()).get(tag_group_id)
            if aux_tag_title:
                entries.append((aux_tag_title, aux_tag_title))
                continue

            entries.append((tag_group_id, tag_id))
        return entries


class PainterHostTagsWithTitles(ABCPainterTagsWithTitles):
    @property
    def object_type(self) -> str:
        return "host"

    @property
    def ident(self) -> str:
        return "host_tags_with_titles"

    def title(self, cell: Cell) -> str:
        return _("Host tags (with titles)")

    def short_title(self, cell: Cell) -> str:
        return self.title(cell)

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_tags"]

    @property
    def sorter(self) -> SorterName:
        return "host"


class PainterServiceTags(Painter):
    @property
    def ident(self) -> str:
        return "service_tags"

    def title(self, cell: Cell) -> str:
        return _("Service tags")

    def short_title(self, cell: Cell) -> str:
        return self.title(cell)

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_tags"]

    @property
    def sorter(self) -> SorterName:
        return "service_tags"

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return "", render_tag_groups(
            get_tag_groups(row, "service"), "service", with_links=True, request=self.request
        )


class PainterServiceTagsWithTitles(ABCPainterTagsWithTitles):
    @property
    def object_type(self) -> str:
        return "service"

    @property
    def ident(self) -> str:
        return "service_tags_with_titles"

    def title(self, cell: Cell) -> str:
        return _("Service tags (with titles)")

    def short_title(self, cell: Cell) -> str:
        return self.title(cell)

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_tags"]

    @property
    def sorter(self) -> SorterName:
        return "service_tags"


class PainterHostLabels(Painter):
    @property
    def ident(self) -> str:
        return "host_labels"

    def title(self, cell: Cell) -> str:
        return _("Host labels")

    def short_title(self, cell: Cell) -> str:
        return self.title(cell)

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_labels", "host_label_sources"]

    @property
    def sorter(self) -> SorterName:
        return "host_labels"

    def _compute_data(self, row: Row, cell: Cell) -> Labels:
        return get_labels(row, "host")

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return "", render_labels(
            self._compute_data(row, cell),
            "host",
            with_links=True,
            label_sources=get_label_sources(row, "host"),
            request=self.request,
        )

    def export_for_python(self, row: Row, cell: Cell) -> Labels:
        return self._compute_data(row, cell)

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        return format_labels_for_csv_export(self._compute_data(row, cell))

    def export_for_json(self, row: Row, cell: Cell) -> Labels:
        return self._compute_data(row, cell)


class PainterServiceLabels(Painter):
    @property
    def ident(self) -> str:
        return "service_labels"

    def title(self, cell: Cell) -> str:
        return _("Service labels")

    def short_title(self, cell: Cell) -> str:
        return self.title(cell)

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_labels", "service_label_sources"]

    @property
    def sorter(self) -> SorterName:
        return "service_labels"

    def _compute_data(self, row: Row, cell: Cell) -> Labels:
        return get_labels(row, "service")

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return "", render_labels(
            self._compute_data(row, cell),
            "service",
            with_links=True,
            label_sources=get_label_sources(row, "service"),
            request=self.request,
        )

    def export_for_python(self, row: Row, cell: Cell) -> Labels:
        return self._compute_data(row, cell)

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        return format_labels_for_csv_export(self._compute_data(row, cell))

    def export_for_json(self, row: Row, cell: Cell) -> Labels:
        return self._compute_data(row, cell)


class PainterHostDockerNode(Painter):
    @property
    def ident(self) -> str:
        return "host_docker_node"

    def title(self, cell: Cell) -> str:
        return _("Docker node")

    def short_title(self, cell: Cell) -> str:
        return _("Node")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_labels", "host_label_sources"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        """We use the information stored in output of docker_container_status
        here. It's the most trusted source of the current node the container is
        running on."""
        if row.get("host_labels", {}).get("cmk/docker_object") != "container":
            return "", ""

        docker_nodes = _get_docker_container_status_outputs()
        output = docker_nodes.get(row["host_name"])
        # Output with node: "Container running on node mynode2"
        # Output without node: "Container running"
        if output is None or "node" not in output:
            return "", ""

        node = output.split()[-1]
        content = self.url_renderer.link_from_filename(
            "view.py",
            query_args=[
                ("view_name", "host"),
                ("host", node),
            ],
        )
        return "", content


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


class AbstractColumnSpecificMetric(Painter):
    @property
    def ident(self) -> str:
        raise NotImplementedError()

    def title(self, cell: Cell) -> str:
        return self._title_with_parameters(cell.painter_parameters(), metrics_from_api)

    def short_title(self, cell: Cell) -> str:
        return self._title_with_parameters(cell.painter_parameters(), metrics_from_api)

    def list_title(self, cell: Cell) -> str:
        return _("Metric")

    def _title_with_parameters(
        self,
        parameters: PainterParameters | None,
        registered_metrics: Mapping[str, RegisteredMetric],
    ) -> str:
        try:
            if not parameters:
                # Used in Edit-View
                return _("Show single metric")
            return get_metric_spec(parameters["metric"], registered_metrics).title
        except KeyError:
            return _("Metric not found")

    @property
    def columns(self) -> Sequence[ColumnName]:
        raise NotImplementedError()

    @property
    def parameters(self) -> Dictionary:
        return Dictionary(
            elements=[
                (
                    "metric",
                    DropdownChoice(
                        title=_("Show metric"),
                        choices=self._metric_choices(),
                        help=_("If available, the following metric will be shown"),
                    ),
                ),
                ("column_title", TextInput(title=_("Custom title"))),
            ],
            optional_keys=["column_title"],
        )

    @classmethod
    @request_memoize()
    def _metric_choices(cls) -> list[tuple[str, str]]:
        return sorted(
            (
                (metric_id, metric_title)
                for metric_id, metric_title in registered_metric_ids_and_titles(metrics_from_api)
            ),
            key=lambda x: x[1],
        )

    def _render(
        self, row: Row, cell: Cell, perf_data_entries: str, check_command: str
    ) -> tuple[str, str]:
        parameters = cell.painter_parameters()
        assert parameters is not None
        show_metric = parameters["metric"]

        perf_data, check_command = parse_perf_data(
            perf_data_entries, check_command, config=self.config
        )
        translated_metrics = translate_metrics(
            perf_data,
            check_command,
            metrics_from_api,
        )

        if show_metric not in translated_metrics:
            return "", ""

        translated_metric = translated_metrics[show_metric]

        return (
            "",
            user_specific_unit(
                translated_metric.unit_spec,
                user,
                active_config,
            ).formatter.render(translated_metric.value),
        )


class PainterHostSpecificMetric(AbstractColumnSpecificMetric):
    @property
    def ident(self) -> str:
        return "host_specific_metric"

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_perf_data", "host_check_command"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        perf_data_entries = row["host_perf_data"]
        check_command = row["host_check_command"]
        return self._render(row, cell, perf_data_entries, check_command)


class PainterServiceSpecificMetric(AbstractColumnSpecificMetric):
    @property
    def ident(self) -> str:
        return "service_specific_metric"

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["service_perf_data", "service_check_command"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        perf_data_entries = row["service_perf_data"]
        check_command = row["service_check_command"]
        return self._render(row, cell, perf_data_entries, check_command)


class _PainterHostKubernetes(Painter):
    """
    Link to kubernetes dashboard. The filters are set in a way that only hosts
    belonging to the kubernetes_object are shown.

    A host representing a kubernetes cluster will link to the kubernetes
    cluster dashboard. This dashboard should only display objects (=cmk hosts)
    belonging to cluster. So the link to the dashboard is augmented by a
    kubernetes_cluster filter.

    As nodes are not unique among multiple clusters, chains of multiple filters
    have to build for certain objects: in order to show only objects of a
    certain node, both node and cluster filter needs to be present.

    The cmk host names and the kubernetes names may differ: normally the cmk
    host names of kubernetes objects are prefixed with the cluster name. This
    painter will show the original kubernetes name, not the checkmk host name.
    """

    _kubernetes_object_type: str
    """
    The content of the corresponding label will be displayed by this painter.
    """
    _constraints: list[str]
    """
    Defines which filters should be added for building up the link.
    """

    @property
    def ident(self) -> str:
        return f"host_kubernetes_{self._kubernetes_object_type}"

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["host_labels", "host_name", "site"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        labels = row.get("host_labels", {})
        if labels.get("cmk/kubernetes/object") != self._kubernetes_object_type:
            return "", ""

        links: HTTPVariables = []
        for link_key in self._constraints:
            if (link_value := labels.get(f"cmk/kubernetes/{link_key}")) is None:
                # a requested filter can not be set, so better don't show anything
                return "", ""

            links.append((f"kubernetes_{link_key}", link_value))

        links.extend(
            [
                # name of the dashboard we are linking to
                ("name", f"kubernetes_{self._kubernetes_object_type}"),
                ("host", row["host_name"]),
                ("site", row["site"]),
            ]
        )

        if (object_name := labels.get(f"cmk/kubernetes/{self._kubernetes_object_type}")) is None:
            return "", ""

        content = self.url_renderer.link_from_filename(
            "dashboard.py", html_text=object_name, query_args=links
        )
        return "", content


class PainterHostKubernetesCluster(_PainterHostKubernetes):
    _kubernetes_object_type = "cluster"
    _constraints = ["cluster"]

    def title(self, cell: Cell) -> str:
        return _("Kubernetes Cluster")

    def short_title(self, cell: Cell) -> str:
        return _("Cluster")


class PainterHostKubernetesNamespace(_PainterHostKubernetes):
    _kubernetes_object_type = "namespace"
    _constraints = ["namespace", "cluster-host", "cluster"]

    def title(self, cell: Cell) -> str:
        return _("Kubernetes Namespace")

    def short_title(self, cell: Cell) -> str:
        return _("Namespace")


class PainterHostKubernetesDeployment(_PainterHostKubernetes):
    _kubernetes_object_type = "deployment"
    _constraints = ["deployment", "namespace", "cluster-host", "cluster"]

    def title(self, cell: Cell) -> str:
        return _("Kubernetes deployment")

    def short_title(self, cell: Cell) -> str:
        return _("Deployment")


class PainterHostKubernetesDaemonset(_PainterHostKubernetes):
    _kubernetes_object_type = "daemonset"
    _constraints = ["daemonset", "namespace", "cluster-host", "cluster"]

    def title(self, cell: Cell) -> str:
        return _("Kubernetes DaemonSet")

    def short_title(self, cell: Cell) -> str:
        return _("DaemonSet")


class PainterHostKubernetesStatefulset(_PainterHostKubernetes):
    _kubernetes_object_type = "statefulset"
    _constraints = ["statefulset", "namespace", "cluster-host", "cluster"]

    def title(self, cell: Cell) -> str:
        return _("Kubernetes StatefulSet")

    def short_title(self, cell: Cell) -> str:
        return _("StatefulSet")


class PainterHostKubernetesNode(_PainterHostKubernetes):
    _kubernetes_object_type = "node"
    _constraints = ["node", "cluster"]

    def title(self, cell: Cell) -> str:
        return _("Kubernetes Node")

    def short_title(self, cell: Cell) -> str:
        return _("Node")
