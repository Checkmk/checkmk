#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import abc
import os
import time

import cmk.utils.paths
import cmk.utils.render
import cmk.utils.man_pages as man_pages
from cmk.utils.defines import short_service_state_name, short_host_state_name

import cmk.gui.config as config
import cmk.gui.metrics as metrics
import cmk.gui.sites as sites
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html, current_app
from cmk.gui.valuespec import (
    Timerange,
    TextAscii,
    DropdownChoice,
    DateFormat,
    Dictionary,
    ListChoice,
)

from cmk.gui.plugins.views.icons import (
    get_icons,
    iconpainter_columns,
)

from cmk.gui.plugins.views import (
    painter_registry,
    Painter,
    painter_option_registry,
    PainterOption,
    PainterOptions,
    transform_action_url,
    is_stale,
    paint_stalified,
    paint_host_list,
    format_plugin_output,
    display_options,
    link_to_view,
    get_perfdata_nth_value,
    get_graph_timerange_from_painter_options,
    paint_age,
    paint_nagiosflag,
    replace_action_url_macros,
    render_cache_info,
    render_tag_groups,
    get_tag_groups,
    render_labels,
    get_labels,
    get_label_sources,
)

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


@painter_option_registry.register
class PainterOptionPNPTimerange(PainterOption):
    @property
    def ident(self):
        return "pnp_timerange"

    @property
    def valuespec(self):
        return Timerange(
            title=_("Graph time range"),
            default_value=None,
            include_time=True,
        )


@painter_option_registry.register
class PainterOptionTimestampFormat(PainterOption):
    @property
    def ident(self):
        return "ts_format"

    @property
    def valuespec(self):
        return DropdownChoice(
            title=_("Time stamp format"),
            default_value=config.default_ts_format,
            choices=[
                ("mixed", _("Mixed")),
                ("abs", _("Absolute")),
                ("rel", _("Relative")),
                ("both", _("Both")),
                ("epoch", _("Unix Timestamp (Epoch)")),
            ],
        )


@painter_option_registry.register
class PainterOptionTimestampDate(PainterOption):
    @property
    def ident(self):
        return "ts_date"

    @property
    def valuespec(self):
        return DateFormat()


@painter_option_registry.register
class PainterOptionMatrixOmitUniform(PainterOption):
    @property
    def ident(self):
        return "matrix_omit_uniform"

    @property
    def valuespec(self):
        return DropdownChoice(title=_("Find differences..."),
                              choices=[
                                  (False, _("Always show all rows")),
                                  (True, _("Omit rows where all columns are identical")),
                              ])


#.
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   '----------------------------------------------------------------------'


# This helper function returns the value of the given custom var
def paint_custom_var(what, key, row, choices=None):
    if choices is None:
        choices = []

    if what:
        what += '_'

    custom_vars = dict(
        zip(row[what + "custom_variable_names"], row[what + "custom_variable_values"]))

    if key in custom_vars:
        custom_val = custom_vars[key]
        if choices:
            custom_val = dict(choices).get(int(custom_val), custom_val)
        return key, html.attrencode(custom_val)

    return key, ""


def paint_future_time(timestamp):
    if timestamp <= 0:
        return "", "-"
    return paint_age(timestamp, True, 0, what='future')


def paint_day(timestamp):
    return "", time.strftime("%A, %Y-%m-%d", time.localtime(timestamp))


# Paint column with various icons. The icons use
# a plugin based mechanism so it is possible to
# register own icon "handlers".
# what: either "host" or "service"
# row: the data row of the host or service
def paint_icons(what, row):
    # EC: In case of unrelated events also skip rendering this painter. All the icons
    # that display a host state are useless in this case. Maybe we make this decision
    # individually for the single icons one day.
    if not row["host_name"] or row.get("event_is_unrelated"):
        return "", ""  # Host probably does not exist

    toplevel_icons = get_icons(what, row, toplevel=True)

    # In case of non HTML output, just return the top level icon names
    # as space separated string
    if html.output_format != 'html':
        return 'icons', ' '.join([i[1] for i in toplevel_icons])

    output = ''
    for icon in toplevel_icons:
        if len(icon) == 4:
            icon_name, title, url_spec = icon[1:]
            if url_spec:
                url, target_frame = transform_action_url(url_spec)
                url = replace_action_url_macros(url, what, row)

                onclick = ''
                if url.startswith('onclick:'):
                    onclick = url[8:]
                    url = 'javascript:void(0)'

                output += html.render_icon_button(url,
                                                  title,
                                                  icon_name,
                                                  onclick=onclick,
                                                  target=target_frame)
            else:
                output += html.render_icon(icon_name, title)
        else:
            output += icon[1]

    return "icons", output


# TODO: Refactor to one icon base class
@painter_registry.register
class PainterServiceIcons(Painter):
    @property
    def ident(self):
        return "service_icons"

    @property
    def title(self):
        return _("Service icons")

    @property
    def short_title(self):
        return _("Icons")

    @property
    def columns(self):
        return iconpainter_columns("service", toplevel=None)

    @property
    def printable(self):
        return False

    def group_by(self, row):
        return ("",)  # Do not account for in grouping

    def render(self, row, cell):
        return paint_icons("service", row)


@painter_registry.register
class PainterHostIcons(Painter):
    @property
    def ident(self):
        return "host_icons"

    @property
    def title(self):
        return _("Host icons")

    @property
    def short_title(self):
        return _("Icons")

    @property
    def columns(self):
        return iconpainter_columns("host", toplevel=None)

    @property
    def printable(self):
        return False

    def group_by(self, row):
        return ("",)  # Do not account for in grouping

    def render(self, row, cell):
        return paint_icons("host", row)


#.
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


@painter_registry.register
class PainterSiteIcon(Painter):
    @property
    def ident(self):
        return "site_icon"

    @property
    def title(self):
        return _("Site icon")

    @property
    def short_title(self):
        return u""

    @property
    def columns(self):
        return ['site']

    @property
    def sorter(self):
        return 'site'

    def render(self, row, cell):
        if row.get("site") and config.use_siteicons:
            return None, "<img class=siteicon src=\"icons/site-%s-24.png\">" % row["site"]
        return None, ""


@painter_registry.register
class PainterSitenamePlain(Painter):
    @property
    def ident(self):
        return "sitename_plain"

    @property
    def title(self):
        return _("Site ID")

    @property
    def short_title(self):
        return _("Site")

    @property
    def columns(self):
        return ['site']

    @property
    def sorter(self):
        return 'site'

    def render(self, row, cell):
        return (None, row["site"])


@painter_registry.register
class PainterSitealias(Painter):
    @property
    def ident(self):
        return "sitealias"

    @property
    def title(self):
        return _("Site alias")

    @property
    def columns(self):
        return ['site']

    def render(self, row, cell):
        return (None, html.attrencode(config.site(row["site"])["alias"]))


#.
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


def paint_service_state_short(row):
    if row["service_has_been_checked"] == 1:
        state = str(row["service_state"])
        name = short_service_state_name(row["service_state"], "")
    else:
        state = "p"
        name = short_service_state_name(-1, "")

    if is_stale(row):
        state = str(state) + " stale"

    return "state svcstate state%s" % state, name


def paint_host_state_short(row, short=False):
    if row["host_has_been_checked"] == 1:
        state = row["host_state"]
        # A state of 3 is sent by livestatus in cases where no normal state
        # information is avaiable, e.g. for "DOWNTIMESTOPPED (UP)"
        name = short_host_state_name(row["host_state"], "")
    else:
        state = "p"
        name = _("PEND")

    if is_stale(row):
        state = str(state) + " stale"

    if short:
        name = name[0]

    return "state hstate hstate%s" % state, name


@painter_registry.register
class PainterServiceState(Painter):
    @property
    def ident(self):
        return "service_state"

    @property
    def title(self):
        return _("Service state")

    @property
    def short_title(self):
        return _("State")

    @property
    def columns(self):
        return ['service_has_been_checked', 'service_state']

    @property
    def sorter(self):
        return 'svcstate'

    def render(self, row, cell):
        return paint_service_state_short(row)


@painter_registry.register
class PainterSvcPluginOutput(Painter):
    @property
    def ident(self):
        return "svc_plugin_output"

    @property
    def title(self):
        return _("Output of check plugin")

    @property
    def short_title(self):
        return _("Status detail")

    @property
    def columns(self):
        return ['service_plugin_output', 'service_custom_variables']

    @property
    def sorter(self):
        return 'svcoutput'

    def render(self, row, cell):
        return paint_stalified(row, format_plugin_output(row["service_plugin_output"], row))


@painter_registry.register
class PainterSvcLongPluginOutput(Painter):
    @property
    def ident(self):
        return "svc_long_plugin_output"

    @property
    def title(self):
        return _("Long output of check plugin (multiline)")

    @property
    def short_title(self):
        return _("Status detail")

    @property
    def columns(self):
        return ['service_long_plugin_output', 'service_custom_variables']

    def render(self, row, cell):
        return paint_stalified(
            row,
            format_plugin_output(row["service_long_plugin_output"],
                                 row).replace('\\n', '<br>').replace('\n', '<br>'))


@painter_registry.register
class PainterSvcPerfData(Painter):
    @property
    def ident(self):
        return "svc_perf_data"

    @property
    def title(self):
        return _("Service performance data (source code)")

    @property
    def short_title(self):
        return _("Perfdata")

    @property
    def columns(self):
        return ['service_perf_data']

    def render(self, row, cell):
        return paint_stalified(row, row["service_perf_data"])


@painter_registry.register
class PainterSvcMetrics(Painter):
    @property
    def ident(self):
        return "svc_metrics"

    @property
    def title(self):
        return _("Service Metrics")

    @property
    def short_title(self):
        return _("Metrics")

    @property
    def columns(self):
        return ['service_check_command', 'service_perf_data']

    @property
    def printable(self):
        return False

    def render(self, row, cell):
        translated_metrics = metrics.translate_perf_data(row["service_perf_data"],
                                                         row["service_check_command"])

        if row["service_perf_data"] and not translated_metrics:
            return "", _("Failed to parse performance data string: %s") % row["service_perf_data"]

        return "", metrics.render_metrics_table(translated_metrics, row["host_name"],
                                                row["service_description"])


# TODO: Use a parameterized painter for this instead of 10 painter classes
class PainterSvcPerfVal(Painter):
    _num = 0

    @property
    def ident(self):
        return "svc_perf_val%02d" % self._num

    @property
    def title(self):
        return _("Service performance data - value number %2d") % self._num

    @property
    def short_title(self):
        return _("Val. %d") % self._num

    @property
    def columns(self):
        return ['service_perf_data']

    def render(self, row, cell):
        return paint_stalified(row, get_perfdata_nth_value(row, self._num - 1))


@painter_registry.register
class PainterSvcPerfVal01(PainterSvcPerfVal):
    _num = 1


@painter_registry.register
class PainterSvcPerfVal02(PainterSvcPerfVal):
    _num = 2


@painter_registry.register
class PainterSvcPerfVal03(PainterSvcPerfVal):
    _num = 3


@painter_registry.register
class PainterSvcPerfVal04(PainterSvcPerfVal):
    _num = 4


@painter_registry.register
class PainterSvcPerfVal05(PainterSvcPerfVal):
    _num = 5


@painter_registry.register
class PainterSvcPerfVal06(PainterSvcPerfVal):
    _num = 6


@painter_registry.register
class PainterSvcPerfVal07(PainterSvcPerfVal):
    _num = 7


@painter_registry.register
class PainterSvcPerfVal08(PainterSvcPerfVal):
    _num = 8


@painter_registry.register
class PainterSvcPerfVal09(PainterSvcPerfVal):
    _num = 9


@painter_registry.register
class PainterSvcPerfVal10(PainterSvcPerfVal):
    _num = 10


@painter_registry.register
class PainterSvcCheckCommand(Painter):
    @property
    def ident(self):
        return "svc_check_command"

    @property
    def title(self):
        return _("Service check command")

    @property
    def short_title(self):
        return _("Check command")

    @property
    def columns(self):
        return ['service_check_command']

    def render(self, row, cell):
        return (None, html.attrencode(row["service_check_command"]))


@painter_registry.register
class PainterSvcCheckCommandExpanded(Painter):
    @property
    def ident(self):
        return "svc_check_command_expanded"

    @property
    def title(self):
        return _("Service check command expanded")

    @property
    def short_title(self):
        return _("Check command expanded")

    @property
    def columns(self):
        return ['service_check_command_expanded']

    def render(self, row, cell):
        return html.attrencode(row["service_check_command_expanded"])


@painter_registry.register
class PainterSvcContacts(Painter):
    @property
    def ident(self):
        return "svc_contacts"

    @property
    def title(self):
        return _("Service contacts")

    @property
    def short_title(self):
        return _("Contacts")

    @property
    def columns(self):
        return ['service_contacts']

    def render(self, row, cell):
        return (None, ", ".join(row["service_contacts"]))


@painter_registry.register
class PainterSvcContactGroups(Painter):
    @property
    def ident(self):
        return "svc_contact_groups"

    @property
    def title(self):
        return _("Service contact groups")

    @property
    def short_title(self):
        return _("Contact groups")

    @property
    def columns(self):
        return ['service_contact_groups']

    def render(self, row, cell):
        return (None, ", ".join(row["service_contact_groups"]))


@painter_registry.register
class PainterServiceDescription(Painter):
    @property
    def ident(self):
        return "service_description"

    @property
    def title(self):
        return _("Service description")

    @property
    def short_title(self):
        return _("Service")

    @property
    def columns(self):
        return ['service_description']

    @property
    def sorter(self):
        return 'svcdescr'

    def render(self, row, cell):
        return (None, row["service_description"])


@painter_registry.register
class PainterServiceDisplayName(Painter):
    @property
    def ident(self):
        return "service_display_name"

    @property
    def title(self):
        return _("Service alternative display name")

    @property
    def short_title(self):
        return _("Display name")

    @property
    def columns(self):
        return ['service_display_name']

    @property
    def sorter(self):
        return 'svcdispname'

    def render(self, row, cell):
        return (None, row["service_display_name"])


@painter_registry.register
class PainterSvcStateAge(Painter):
    @property
    def ident(self):
        return "svc_state_age"

    @property
    def title(self):
        return _("The age of the current service state")

    @property
    def short_title(self):
        return _("Age")

    @property
    def columns(self):
        return ['service_has_been_checked', 'service_last_state_change']

    @property
    def sorter(self):
        return 'stateage'

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["service_last_state_change"], row["service_has_been_checked"] == 1,
                         60 * 10)


def paint_checked(what, row):
    age = row[what + "_last_check"]
    if what == "service":
        cached_at = row["service_cached_at"]
        if cached_at:
            age = cached_at

    css, td = paint_age(age, row[what + "_has_been_checked"] == 1, 0)
    if is_stale(row):
        css += " staletime"
    return css, td


@painter_registry.register
class PainterSvcCheckAge(Painter):
    @property
    def ident(self):
        return "svc_check_age"

    @property
    def title(self):
        return _("The time since the last check of the service")

    @property
    def short_title(self):
        return _("Checked")

    @property
    def columns(self):
        return ['service_has_been_checked', 'service_last_check', 'service_cached_at']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_checked("service", row)


@painter_registry.register
class PainterSvcCheckCacheInfo(Painter):
    @property
    def ident(self):
        return "svc_check_cache_info"

    @property
    def title(self):
        return _("Cached agent data")

    @property
    def short_title(self):
        return _("Cached")

    @property
    def columns(self):
        return ['service_last_check', 'service_cached_at', 'service_cache_interval']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        if not row["service_cached_at"]:
            return "", ""
        return "", render_cache_info("service", row)


@painter_registry.register
class PainterSvcNextCheck(Painter):
    @property
    def ident(self):
        return "svc_next_check"

    @property
    def title(self):
        return _("The time of the next scheduled service check")

    @property
    def short_title(self):
        return _("Next check")

    @property
    def columns(self):
        return ['service_next_check']

    def render(self, row, cell):
        return paint_future_time(row["service_next_check"])


@painter_registry.register
class PainterSvcLastTimeOk(Painter):
    @property
    def ident(self):
        return "svc_last_time_ok"

    @property
    def title(self):
        return _("The last time the service was OK")

    @property
    def short_title(self):
        return _("Last OK")

    @property
    def columns(self):
        return ['service_last_time_ok', 'service_has_been_checked']

    def render(self, row, cell):
        return paint_age(row["service_last_time_ok"], row["service_has_been_checked"] == 1, 60 * 10)


@painter_registry.register
class PainterSvcNextNotification(Painter):
    @property
    def ident(self):
        return "svc_next_notification"

    @property
    def title(self):
        return _("The time of the next service notification")

    @property
    def short_title(self):
        return _("Next notification")

    @property
    def columns(self):
        return ['service_next_notification']

    def render(self, row, cell):
        return paint_future_time(row["service_next_notification"])


def paint_notification_postponement_reason(what, row):
    # Needs to be in sync with the possible reasons. Can not be translated otherwise.
    reasons = {
        "delayed notification": _("Delay notification"),
        "periodic notification": _("Periodic notification"),
        "currently in downtime": _("In downtime"),
        "host of this service is currently in downtime": _("Host is in downtime"),
        "problem acknowledged and periodic notifications are enabled":
            _("Problem is acknowledged, but is configured to be periodic"),
        "notifications are disabled, but periodic notifications are enabled":
            _("Notifications are disabled, but is configured to be periodic"),
        "not in notification period": _("Is not in notification period"),
        "host of this service is not up": _("Host is down"),
        "last host check not recent enough": _("Last host check is not recent enough"),
        "last service check not recent enough": _("Last service check is not recent enough"),
        "all parents are down": _("All parents are down"),
        "at least one parent is up, but no check is recent enough":
            _("Last service check is not recent enough"),
    }

    return ("",
            reasons.get(row[what + "_notification_postponement_reason"],
                        row[what + "_notification_postponement_reason"]))


@painter_registry.register
class PainterSvcNotificationPostponementReason(Painter):
    @property
    def ident(self):
        return "svc_notification_postponement_reason"

    @property
    def title(self):
        return _("Notification postponement reason")

    @property
    def short_title(self):
        return _("Notif. postponed")

    @property
    def columns(self):
        return ['service_notification_postponement_reason']

    def render(self, row, cell):
        return paint_notification_postponement_reason("service", row)


@painter_registry.register
class PainterSvcLastNotification(Painter):
    @property
    def ident(self):
        return "svc_last_notification"

    @property
    def title(self):
        return _("The time of the last service notification")

    @property
    def short_title(self):
        return _("last notification")

    @property
    def columns(self):
        return ['service_last_notification']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["service_last_notification"], row["service_last_notification"], 0)


@painter_registry.register
class PainterSvcNotificationNumber(Painter):
    @property
    def ident(self):
        return "svc_notification_number"

    @property
    def title(self):
        return _("Service notification number")

    @property
    def short_title(self):
        return _("N#")

    @property
    def columns(self):
        return ['service_current_notification_number']

    def render(self, row, cell):
        return ("", str(row["service_current_notification_number"]))


@painter_registry.register
class PainterSvcCheckLatency(Painter):
    @property
    def ident(self):
        return "svc_check_latency"

    @property
    def title(self):
        return _("Service check latency")

    @property
    def short_title(self):
        return _("Latency")

    @property
    def columns(self):
        return ['service_latency']

    def render(self, row, cell):
        return ("", cmk.utils.render.approx_age(row["service_latency"]))


@painter_registry.register
class PainterSvcCheckDuration(Painter):
    @property
    def ident(self):
        return "svc_check_duration"

    @property
    def title(self):
        return _("Service check duration")

    @property
    def short_title(self):
        return _("Duration")

    @property
    def columns(self):
        return ['service_execution_time']

    def render(self, row, cell):
        return ("", cmk.utils.render.approx_age(row["service_execution_time"]))


@painter_registry.register
class PainterSvcAttempt(Painter):
    @property
    def ident(self):
        return "svc_attempt"

    @property
    def title(self):
        return _("Current check attempt")

    @property
    def short_title(self):
        return _("Att.")

    @property
    def columns(self):
        return ['service_current_attempt', 'service_max_check_attempts']

    def render(self, row, cell):
        return (None, "%d/%d" % (row["service_current_attempt"], row["service_max_check_attempts"]))


@painter_registry.register
class PainterSvcNormalInterval(Painter):
    @property
    def ident(self):
        return "svc_normal_interval"

    @property
    def title(self):
        return _("Service normal check interval")

    @property
    def short_title(self):
        return _("Check int.")

    @property
    def columns(self):
        return ['service_check_interval']

    def render(self, row, cell):
        return ("number", cmk.utils.render.approx_age(row["service_check_interval"] * 60.0))


@painter_registry.register
class PainterSvcRetryInterval(Painter):
    @property
    def ident(self):
        return "svc_retry_interval"

    @property
    def title(self):
        return _("Service retry check interval")

    @property
    def short_title(self):
        return _("Retry")

    @property
    def columns(self):
        return ['service_retry_interval']

    def render(self, row, cell):
        return ("number", cmk.utils.render.approx_age(row["service_retry_interval"] * 60.0))


@painter_registry.register
class PainterSvcCheckInterval(Painter):
    @property
    def ident(self):
        return "svc_check_interval"

    @property
    def title(self):
        return _("Service normal/retry check interval")

    @property
    def short_title(self):
        return _("Interval")

    @property
    def columns(self):
        return ['service_check_interval', 'service_retry_interval']

    def render(self, row, cell):
        return (
            None,
            "%s / %s" % (cmk.utils.render.approx_age(row["service_check_interval"] * 60.0),
                         cmk.utils.render.approx_age(row["service_retry_interval"] * 60.0)),
        )


@painter_registry.register
class PainterSvcCheckType(Painter):
    @property
    def ident(self):
        return "svc_check_type"

    @property
    def title(self):
        return _("Service check type")

    @property
    def short_title(self):
        return _("Type")

    @property
    def columns(self):
        return ['service_check_type']

    def render(self, row, cell):
        return (None, _("ACTIVE") if row["service_check_type"] == 0 else _("PASSIVE"))


@painter_registry.register
class PainterSvcInDowntime(Painter):
    @property
    def ident(self):
        return "svc_in_downtime"

    @property
    def title(self):
        return _("Currently in downtime")

    @property
    def short_title(self):
        return _("Dt.")

    @property
    def columns(self):
        return ['service_scheduled_downtime_depth']

    def render(self, row, cell):
        return paint_nagiosflag(row, "service_scheduled_downtime_depth", True)


@painter_registry.register
class PainterSvcInNotifper(Painter):
    @property
    def ident(self):
        return "svc_in_notifper"

    @property
    def title(self):
        return _("In notification period")

    @property
    def short_title(self):
        return _("in notif. p.")

    @property
    def columns(self):
        return ['service_in_notification_period']

    def render(self, row, cell):
        return paint_nagiosflag(row, "service_in_notification_period", False)


@painter_registry.register
class PainterSvcNotifper(Painter):
    @property
    def ident(self):
        return "svc_notifper"

    @property
    def title(self):
        return _("Service notification period")

    @property
    def short_title(self):
        return _("notif.")

    @property
    def columns(self):
        return ['service_notification_period']

    def render(self, row, cell):
        return (None, row["service_notification_period"])


@painter_registry.register
class PainterSvcCheckPeriod(Painter):
    @property
    def ident(self):
        return "svc_check_period"

    @property
    def title(self):
        return _("Service check period")

    @property
    def short_title(self):
        return _("check.")

    @property
    def columns(self):
        return ['service_check_period']

    def render(self, row, cell):
        return (None, row["service_check_period"])


@painter_registry.register
class PainterSvcFlapping(Painter):
    @property
    def ident(self):
        return "svc_flapping"

    @property
    def title(self):
        return _("Service is flapping")

    @property
    def short_title(self):
        return _("Flap")

    @property
    def columns(self):
        return ['service_is_flapping']

    def render(self, row, cell):
        return paint_nagiosflag(row, "service_is_flapping", True)


@painter_registry.register
class PainterSvcNotificationsEnabled(Painter):
    @property
    def ident(self):
        return "svc_notifications_enabled"

    @property
    def title(self):
        return _("Service notifications enabled")

    @property
    def short_title(self):
        return _("Notif.")

    @property
    def columns(self):
        return ['service_notifications_enabled']

    def render(self, row, cell):
        return paint_nagiosflag(row, "service_notifications_enabled", False)


@painter_registry.register
class PainterSvcIsActive(Painter):
    @property
    def ident(self):
        return "svc_is_active"

    @property
    def title(self):
        return _("Service is active")

    @property
    def short_title(self):
        return _("Active")

    @property
    def columns(self):
        return ['service_active_checks_enabled']

    def render(self, row, cell):
        return paint_nagiosflag(row, "service_active_checks_enabled", None)


@painter_registry.register
class PainterSvcGroupMemberlist(Painter):
    @property
    def ident(self):
        return "svc_group_memberlist"

    @property
    def title(self):
        return _("Service groups the service is member of")

    @property
    def short_title(self):
        return _("Groups")

    @property
    def columns(self):
        return ['service_groups']

    def render(self, row, cell):
        links = []
        for group in row["service_groups"]:
            link = "view.py?view_name=servicegroup&servicegroup=" + group
            links.append(html.render_a(group, link))
        return "", HTML(", ").join(links)


def paint_time_graph(row, cell):
    if metrics.cmk_graphs_possible(row["site"]):
        import cmk.gui.cee.plugins.views.graphs  # pylint: disable=redefined-outer-name
        return cmk.gui.cee.plugins.views.graphs.paint_time_graph_cmk(row, cell)
    return paint_time_graph_pnp(row)


def paint_time_graph_pnp(row):
    sitename = row["site"]
    host = row["host_name"]
    service = row.get("service_description", "_HOST_")

    container_id = "%s_%s_%s_graph" % (sitename, host, service)
    url_prefix = config.site(sitename)["url_prefix"]
    pnp_url = url_prefix + "pnp4nagios/"
    if display_options.enabled(display_options.X):
        with_link = 'true'
    else:
        with_link = 'false'

    painter_options = PainterOptions.get_instance()
    pnp_timerange = painter_options.get("pnp_timerange")

    pnpview = '1'
    from_ts, to_ts = 'null', 'null'
    if pnp_timerange is not None:
        if pnp_timerange[0] != 'pnp_view':
            from_ts, to_ts = get_graph_timerange_from_painter_options()
        else:
            pnpview = pnp_timerange[1]

    pnp_theme = html.get_theme()
    if pnp_theme == "classic":
        pnp_theme = "multisite"

    return (
        "pnpgraph", "<div id=\"%s\"></div>"
        "<script>cmk.graph_integration.render_graphs('%s', '%s', '%s', '%s', '%s', '%s', '%s', %s, '%s', %s, %s, '%s')</script>"
        % (container_id, container_id, sitename, host, service, pnpview, config.url_prefix() +
           "check_mk/", pnp_url, with_link, _('Add this graph to...'), from_ts, to_ts, pnp_theme))


def time_graph_params():
    if not metrics.cmk_graphs_possible():
        return  # The method is only available in CEE

    import cmk.gui.cee.plugins.views.graphs  # pylint: disable=redefined-outer-name
    return cmk.gui.cee.plugins.views.graphs.cmk_time_graph_params()


@painter_registry.register
class PainterSvcPnpgraph(Painter):
    @property
    def ident(self):
        return "svc_pnpgraph"

    @property
    def title(self):
        return _("Service Graphs")

    @property
    def columns(self):
        return [
            'host_name',
            'service_description',
            'service_perf_data',
            'service_metrics',
            'service_check_command',
        ]

    @property
    def printable(self):
        return 'time_graph'

    @property
    def painter_options(self):
        return ['pnp_timerange']

    @property
    def parameters(self):
        return time_graph_params()

    def render(self, row, cell):
        return paint_time_graph(row, cell)


@painter_registry.register
class PainterCheckManpage(Painter):
    @property
    def ident(self):
        return "check_manpage"

    @property
    def title(self):
        return _("Check manual (for Check_MK based checks)")

    @property
    def short_title(self):
        return _("Manual")

    @property
    def columns(self):
        return ['service_check_command']

    def render(self, row, cell):
        command = row["service_check_command"]
        if not command.startswith("check_mk-"):
            return "", ""
        checktype = command[9:]

        page = man_pages.load_man_page(checktype)
        if page is None:
            return "", _("Man page %s not found.") % checktype

        description = page["header"]["description"]
        return "", description.replace("<", "&lt;") \
                              .replace(">", "&gt;") \
                              .replace("{", "<b>") \
                              .replace("}", "</b>") \
                              .replace("&lt;br&gt;", "<br>")


def paint_comments(prefix, row):
    comments = row[prefix + "comments_with_info"]
    text = ", ".join(["<i>%s</i>: %s" % (a, html.attrencode(c)) for _id, a, c in comments])
    return "", text


@painter_registry.register
class PainterSvcComments(Painter):
    @property
    def ident(self):
        return "svc_comments"

    @property
    def title(self):
        return _("Service Comments")

    @property
    def short_title(self):
        return _("Comments")

    @property
    def columns(self):
        return ['service_comments_with_info']

    def render(self, row, cell):
        return paint_comments("service_", row)


@painter_registry.register
class PainterSvcAcknowledged(Painter):
    @property
    def ident(self):
        return "svc_acknowledged"

    @property
    def title(self):
        return _("Service problem acknowledged")

    @property
    def short_title(self):
        return _("Ack")

    @property
    def columns(self):
        return ['service_acknowledged']

    def render(self, row, cell):
        return paint_nagiosflag(row, "service_acknowledged", False)


def notes_matching_pattern_entries(dirs, item):
    from fnmatch import fnmatch
    matching = []
    for directory in dirs:
        if os.path.isdir(directory):
            entries = sorted([d for d in os.listdir(directory) if d[0] != '.'], reverse=True)
            for pattern in entries:
                if pattern[0] == '.':
                    continue
                if fnmatch(item, pattern):
                    matching.append(directory + "/" + pattern)
    return matching


def paint_custom_notes(what, row):
    host = row["host_name"]
    svc = row.get("service_description")
    if what == "service":
        notes_dir = cmk.utils.paths.default_config_dir + "/notes/services"
        dirs = notes_matching_pattern_entries([notes_dir], host)
        item = svc
    else:
        dirs = [cmk.utils.paths.default_config_dir + "/notes/hosts"]
        item = host

    files = sorted(notes_matching_pattern_entries(dirs, item), reverse=True)
    contents = []

    def replace_tags(text):
        sitename = row["site"]
        url_prefix = config.site(sitename)["url_prefix"]
        return text\
            .replace('$URL_PREFIX$',     url_prefix)\
            .replace('$SITE$',           sitename)\
            .replace('$HOSTNAME$',       host)\
            .replace('$HOSTNAME_LOWER$', host.lower())\
            .replace('$HOSTNAME_UPPER$', host.upper())\
            .replace('$HOSTNAME_TITLE$', host[0].upper() + host[1:].lower())\
            .replace('$HOSTADDRESS$',    row["host_address"])\
            .replace('$SERVICEOUTPUT$',  row.get("service_plugin_output", ""))\
            .replace('$HOSTOUTPUT$',     row.get("host_plugin_output", ""))\
            .replace('$SERVICEDESC$',    row.get("service_description", ""))

    for f in files:
        contents.append(replace_tags(unicode(file(f).read(), "utf-8").strip()))
    return "", "<hr>".join(contents)


@painter_registry.register
class PainterSvcCustomNotes(Painter):
    @property
    def ident(self):
        return "svc_custom_notes"

    @property
    def title(self):
        return _("Custom services notes")

    @property
    def short_title(self):
        return _("Notes")

    @property
    def columns(self):
        return ['host_name', 'host_address', 'service_description', 'service_plugin_output']

    def render(self, row, cell):
        return paint_custom_notes("service", row)


@painter_registry.register
class PainterSvcStaleness(Painter):
    @property
    def ident(self):
        return "svc_staleness"

    @property
    def title(self):
        return _("Service staleness value")

    @property
    def short_title(self):
        return _("Staleness")

    @property
    def columns(self):
        return ['service_staleness']

    def render(self, row, cell):
        return ('', '%0.2f' % row.get('service_staleness', 0))


def paint_is_stale(row):
    if is_stale(row):
        return "badflag", _('yes')
    return "goodflag", _('no')


@painter_registry.register
class PainterSvcIsStale(Painter):
    @property
    def ident(self):
        return "svc_is_stale"

    @property
    def title(self):
        return _("Service is stale")

    @property
    def short_title(self):
        return _("Stale")

    @property
    def columns(self):
        return ['service_staleness']

    @property
    def sorter(self):
        return 'svc_staleness'

    def render(self, row, cell):
        return paint_is_stale(row)


@painter_registry.register
class PainterSvcServicelevel(Painter):
    @property
    def ident(self):
        return "svc_servicelevel"

    @property
    def title(self):
        return _("Service service level")

    @property
    def short_title(self):
        return _("Service Level")

    @property
    def columns(self):
        return ['service_custom_variable_names', 'service_custom_variable_values']

    @property
    def sorter(self):
        return 'servicelevel'

    def render(self, row, cell):
        return paint_custom_var('service', 'EC_SL', row, config.mkeventd_service_levels)


def paint_custom_vars(what, row, blacklist=None):
    if blacklist is None:
        blacklist = []

    items = sorted(row[what + "_custom_variables"].items())
    rows = []
    for varname, value in items:
        if varname not in blacklist:
            rows.append(html.render_tr(html.render_td(varname) + html.render_td(value)))
    return '', "%s" % html.render_table(HTML().join(rows))


@painter_registry.register
class PainterServiceCustomVariables(Painter):
    @property
    def ident(self):
        return "svc_custom_vars"

    @property
    def title(self):
        return _("Service custom attributes")

    @property
    def columns(self):
        return ['service_custom_variables']

    def group_by(self, row):
        return tuple(row["service_custom_variables"].items())

    def render(self, row, cell):
        return paint_custom_vars('service', row)


class ABCPainterCustomVariable(Painter):
    __metaclass__ = abc.ABCMeta

    @property
    def title(self):
        return self._dynamic_title

    @property
    def short_title(self):
        return self._dynamic_title

    def _dynamic_title(self, params=None):
        if params is None:
            # Happens in view editor when adding a painter
            return self._default_title

        try:
            return config.custom_service_attributes[params["ident"]]["title"]
        except KeyError:
            return self._default_title

    @abc.abstractproperty
    def _default_title(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def _object_type(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def _custom_attribute_choices(self):
        raise NotImplementedError()

    @property
    def parameters(self):
        return Dictionary(
            elements=[
                ("ident", DropdownChoice(
                    choices=self._custom_attribute_choices,
                    title=_("ID"),
                )),
            ],
            title=_("Options"),
            optional_keys=[],
        )

    def render(self, row, cell):
        params = cell.painter_parameters()
        return paint_custom_var(self._object_type, params["ident"].upper(), row)


@painter_registry.register
class PainterServiceCustomVariable(ABCPainterCustomVariable):
    @property
    def ident(self):
        return "service_custom_variable"

    @property
    def columns(self):
        return ['service_custom_variable_names', 'service_custom_variable_values']

    @property
    def _default_title(self):
        return _("Service custom attribute")

    @property
    def _object_type(self):
        return "service"

    def _custom_attribute_choices(self):
        choices = []
        for ident, attr_spec in config.custom_service_attributes.items():
            choices.append((ident, attr_spec["title"]))
        return sorted(choices, key=lambda x: x[1])


@painter_registry.register
class PainterHostCustomVariable(ABCPainterCustomVariable):
    @property
    def ident(self):
        return "host_custom_variable"

    @property
    def columns(self):
        return ['host_custom_variable_names', 'host_custom_variable_values']

    @property
    def _default_title(self):
        return _("Host custom attribute")

    @property
    def _object_type(self):
        return "host"

    def _custom_attribute_choices(self):
        choices = []
        for attr_spec in config.wato_host_attrs:
            choices.append((attr_spec["name"], attr_spec["title"]))
        return sorted(choices, key=lambda x: x[1])


#.
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


@painter_registry.register
class PainterHostState(Painter):
    @property
    def ident(self):
        return "host_state"

    @property
    def title(self):
        return _("Host state")

    @property
    def short_title(self):
        return _("state")

    @property
    def columns(self):
        return ['host_has_been_checked', 'host_state']

    @property
    def sorter(self):
        return 'hoststate'

    def render(self, row, cell):
        return paint_host_state_short(row)


@painter_registry.register
class PainterHostStateOnechar(Painter):
    @property
    def ident(self):
        return "host_state_onechar"

    @property
    def title(self):
        return _("Host state (first character)")

    @property
    def short_title(self):
        return _("S.")

    @property
    def columns(self):
        return ['host_has_been_checked', 'host_state']

    @property
    def sorter(self):
        return 'hoststate'

    def render(self, row, cell):
        return paint_host_state_short(row, short=True)


@painter_registry.register
class PainterHostPluginOutput(Painter):
    @property
    def ident(self):
        return "host_plugin_output"

    @property
    def title(self):
        return _("Output of host check plugin")

    @property
    def short_title(self):
        return _("Status detail")

    @property
    def columns(self):
        return ['host_plugin_output', 'host_custom_variables']

    def render(self, row, cell):
        return (None, format_plugin_output(row["host_plugin_output"], row))


@painter_registry.register
class PainterHostPerfData(Painter):
    @property
    def ident(self):
        return "host_perf_data"

    @property
    def title(self):
        return _("Host performance data")

    @property
    def short_title(self):
        return _("Performance data")

    @property
    def columns(self):
        return ['host_perf_data']

    def render(self, row, cell):
        return (None, row["host_perf_data"])


@painter_registry.register
class PainterHostCheckCommand(Painter):
    @property
    def ident(self):
        return "host_check_command"

    @property
    def title(self):
        return _("Host check command")

    @property
    def short_title(self):
        return _("Check command")

    @property
    def columns(self):
        return ['host_check_command']

    def render(self, row, cell):
        return (None, row["host_check_command"])


@painter_registry.register
class PainterHostCheckCommandExpanded(Painter):
    @property
    def ident(self):
        return "host_check_command_expanded"

    @property
    def title(self):
        return _("Host check command expanded")

    @property
    def short_title(self):
        return _("Check command expanded")

    @property
    def columns(self):
        return ['host_check_command_expanded']

    def render(self, row, cell):
        return (None, row["host_check_command_expanded"])


@painter_registry.register
class PainterHostStateAge(Painter):
    @property
    def ident(self):
        return "host_state_age"

    @property
    def title(self):
        return _("The age of the current host state")

    @property
    def short_title(self):
        return _("Age")

    @property
    def columns(self):
        return ['host_has_been_checked', 'host_last_state_change']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["host_last_state_change"], row["host_has_been_checked"] == 1, 60 * 10)


@painter_registry.register
class PainterHostCheckAge(Painter):
    @property
    def ident(self):
        return "host_check_age"

    @property
    def title(self):
        return _("The time since the last check of the host")

    @property
    def short_title(self):
        return _("Checked")

    @property
    def columns(self):
        return ['host_has_been_checked', 'host_last_check']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_checked("host", row)


@painter_registry.register
class PainterHostNextCheck(Painter):
    @property
    def ident(self):
        return "host_next_check"

    @property
    def title(self):
        return _("The time of the next scheduled host check")

    @property
    def short_title(self):
        return _("Next check")

    @property
    def columns(self):
        return ['host_next_check']

    def render(self, row, cell):
        return paint_future_time(row["host_next_check"])


@painter_registry.register
class PainterHostNextNotification(Painter):
    @property
    def ident(self):
        return "host_next_notification"

    @property
    def title(self):
        return _("The time of the next host notification")

    @property
    def short_title(self):
        return _("Next notification")

    @property
    def columns(self):
        return ['host_next_notification']

    def render(self, row, cell):
        return paint_future_time(row["host_next_notification"])


@painter_registry.register
class PainterHostNotificationPostponementReason(Painter):
    @property
    def ident(self):
        return "host_notification_postponement_reason"

    @property
    def title(self):
        return _("Notification postponement reason")

    @property
    def short_title(self):
        return _("Notif. postponed")

    @property
    def columns(self):
        return ['host_notification_postponement_reason']

    def render(self, row, cell):
        return paint_notification_postponement_reason("host", row)


@painter_registry.register
class PainterHostLastNotification(Painter):
    @property
    def ident(self):
        return "host_last_notification"

    @property
    def title(self):
        return _("The time of the last host notification")

    @property
    def short_title(self):
        return _("last notification")

    @property
    def columns(self):
        return ['host_last_notification']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["host_last_notification"], row["host_last_notification"], 0)


@painter_registry.register
class PainterHostCheckLatency(Painter):
    @property
    def ident(self):
        return "host_check_latency"

    @property
    def title(self):
        return _("Host check latency")

    @property
    def short_title(self):
        return _("Latency")

    @property
    def columns(self):
        return ['host_latency']

    def render(self, row, cell):
        return ("", cmk.utils.render.approx_age(row["host_latency"]))


@painter_registry.register
class PainterHostCheckDuration(Painter):
    @property
    def ident(self):
        return "host_check_duration"

    @property
    def title(self):
        return _("Host check duration")

    @property
    def short_title(self):
        return _("Duration")

    @property
    def columns(self):
        return ['host_execution_time']

    def render(self, row, cell):
        return ("", cmk.utils.render.approx_age(row["host_execution_time"]))


@painter_registry.register
class PainterHostAttempt(Painter):
    @property
    def ident(self):
        return "host_attempt"

    @property
    def title(self):
        return _("Current host check attempt")

    @property
    def short_title(self):
        return _("Att.")

    @property
    def columns(self):
        return ['host_current_attempt', 'host_max_check_attempts']

    def render(self, row, cell):
        return (None, "%d/%d" % (row["host_current_attempt"], row["host_max_check_attempts"]))


@painter_registry.register
class PainterHostNormalInterval(Painter):
    @property
    def ident(self):
        return "host_normal_interval"

    @property
    def title(self):
        return _("Normal check interval")

    @property
    def short_title(self):
        return _("Check int.")

    @property
    def columns(self):
        return ['host_check_interval']

    def render(self, row, cell):
        return (None, cmk.utils.render.approx_age(row["host_check_interval"] * 60.0))


@painter_registry.register
class PainterHostRetryInterval(Painter):
    @property
    def ident(self):
        return "host_retry_interval"

    @property
    def title(self):
        return _("Retry check interval")

    @property
    def short_title(self):
        return _("Retry")

    @property
    def columns(self):
        return ['host_retry_interval']

    def render(self, row, cell):
        return (None, cmk.utils.render.approx_age(row["host_retry_interval"] * 60.0))


@painter_registry.register
class PainterHostCheckInterval(Painter):
    @property
    def ident(self):
        return "host_check_interval"

    @property
    def title(self):
        return _("Normal/retry check interval")

    @property
    def short_title(self):
        return _("Interval")

    @property
    def columns(self):
        return ['host_check_interval', 'host_retry_interval']

    def render(self, row, cell):
        return (
            None,
            "%s / %s" % (cmk.utils.render.approx_age(row["host_check_interval"] * 60.0),
                         cmk.utils.render.approx_age(row["host_retry_interval"] * 60.0)),
        )


@painter_registry.register
class PainterHostCheckType(Painter):
    @property
    def ident(self):
        return "host_check_type"

    @property
    def title(self):
        return _("Host check type")

    @property
    def short_title(self):
        return _("Type")

    @property
    def columns(self):
        return ['host_check_type']

    def render(self, row, cell):
        return (None, row["host_check_type"] == 0 and "ACTIVE" or "PASSIVE")


@painter_registry.register
class PainterHostInNotifper(Painter):
    @property
    def ident(self):
        return "host_in_notifper"

    @property
    def title(self):
        return _("Host in notif. period")

    @property
    def short_title(self):
        return _("in notif. p.")

    @property
    def columns(self):
        return ['host_in_notification_period']

    def render(self, row, cell):
        return paint_nagiosflag(row, "host_in_notification_period", False)


@painter_registry.register
class PainterHostNotifper(Painter):
    @property
    def ident(self):
        return "host_notifper"

    @property
    def title(self):
        return _("Host notification period")

    @property
    def short_title(self):
        return _("notif.")

    @property
    def columns(self):
        return ['host_notification_period']

    def render(self, row, cell):
        return (None, row["host_notification_period"])


@painter_registry.register
class PainterHostNotificationNumber(Painter):
    @property
    def ident(self):
        return "host_notification_number"

    @property
    def title(self):
        return _("Host notification number")

    @property
    def short_title(self):
        return _("N#")

    @property
    def columns(self):
        return ['host_current_notification_number']

    def render(self, row, cell):
        return ("", str(row["host_current_notification_number"]))


@painter_registry.register
class PainterHostFlapping(Painter):
    @property
    def ident(self):
        return "host_flapping"

    @property
    def title(self):
        return _("Host is flapping")

    @property
    def short_title(self):
        return _("Flap")

    @property
    def columns(self):
        return ['host_is_flapping']

    def render(self, row, cell):
        return paint_nagiosflag(row, "host_is_flapping", True)


@painter_registry.register
class PainterHostIsActive(Painter):
    @property
    def ident(self):
        return "host_is_active"

    @property
    def title(self):
        return _("Host is active")

    @property
    def short_title(self):
        return _("Active")

    @property
    def columns(self):
        return ['host_active_checks_enabled']

    def render(self, row, cell):
        return paint_nagiosflag(row, "host_active_checks_enabled", None)


@painter_registry.register
class PainterHostNotificationsEnabled(Painter):
    @property
    def ident(self):
        return "host_notifications_enabled"

    @property
    def title(self):
        return _("Host notifications enabled")

    @property
    def short_title(self):
        return _("Notif.")

    @property
    def columns(self):
        return ['host_notifications_enabled']

    def render(self, row, cell):
        return paint_nagiosflag(row, "host_notifications_enabled", False)


@painter_registry.register
class PainterHostPnpgraph(Painter):
    @property
    def ident(self):
        return "host_pnpgraph"

    @property
    def title(self):
        return _("Host graph")

    @property
    def short_title(self):
        return _("Graph")

    @property
    def columns(self):
        return ['host_name', 'host_perf_data', 'host_metrics', 'host_check_command']

    @property
    def printable(self):
        return 'time_graph'

    @property
    def painter_options(self):
        return ['pnp_timerange']

    @property
    def parameters(self):
        return time_graph_params()

    def render(self, row, cell):
        return paint_time_graph(row, cell)


@painter_registry.register
class PainterHostBlack(Painter):
    @property
    def ident(self):
        return "host_black"

    @property
    def title(self):
        return _("Hostname, red background if down or unreachable (Deprecated)")

    @property
    def short_title(self):
        return _("Host")

    @property
    def columns(self):
        return ['site', 'host_name', 'host_state']

    @property
    def sorter(self):
        return 'site_host'

    def render(self, row, cell):
        state = row["host_state"]
        if state != 0:
            return "nobr", "<div class=hostdown>%s</div>" % row["host_name"]
        return "nobr", row["host_name"]


@painter_registry.register
class PainterHostWithState(Painter):
    @property
    def ident(self):
        return "host_with_state"

    @property
    def title(self):
        return _("Hostname, marked red if down (Deprecated)")

    @property
    def short_title(self):
        return _("Host")

    @property
    def columns(self):
        return ['site', 'host_name', 'host_state', 'host_has_been_checked']

    @property
    def sorter(self):
        return 'site_host'

    def render(self, row, cell):
        if row["host_has_been_checked"]:
            state = row["host_state"]
        else:
            state = "p"
        if state != 0:
            return "state hstate hstate%s" % state, row["host_name"]
        return "nobr", row["host_name"]


@painter_registry.register
class PainterHost(Painter):
    @property
    def ident(self):
        return "host"

    @property
    def title(self):
        return _("Hostname")

    @property
    def short_title(self):
        return _("Host")

    @property
    def columns(self):
        return ['host_name', 'host_state', 'host_has_been_checked', 'host_scheduled_downtime_depth']

    @property
    def sorter(self):
        return 'site_host'

    @property
    def parameters(self):
        elements = [
            ("color_choices",
             ListChoice(choices=[
                 ("colorize_up", _("Colorize background if host is up")),
                 ("colorize_down", _("Colorize background if host is down")),
                 ("colorize_unreachable", _("Colorize background if host unreachable")),
                 ("colorize_pending", _("Colorize background if host is pending")),
                 ("colorize_downtime", _("Colorize background if host is downtime"))
             ],
                        title=_("Coloring"),
                        help=_("Here you can configure the background color for specific states. "
                               "The coloring for host in dowtime overrules all other coloring.")))
        ]

        return Dictionary(elements=elements, title=_("Options"), optional_keys=[])

    def render(self, row, cell):
        params = cell.painter_parameters()
        color_choices = params["color_choices"]

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

        return " ".join(css), row["host_name"]


@painter_registry.register
class PainterAlias(Painter):
    @property
    def ident(self):
        return "alias"

    @property
    def title(self):
        return _("Host alias")

    @property
    def short_title(self):
        return _("Alias")

    @property
    def columns(self):
        return ['host_alias']

    def render(self, row, cell):
        return ("", html.attrencode(row["host_alias"]))


@painter_registry.register
class PainterHostAddress(Painter):
    @property
    def ident(self):
        return "host_address"

    @property
    def title(self):
        return _("Host address (Primary)")

    @property
    def short_title(self):
        return _("IP address")

    @property
    def columns(self):
        return ['host_address']

    def render(self, row, cell):
        return ("", row["host_address"])


@painter_registry.register
class PainterHostIpv4Address(Painter):
    @property
    def ident(self):
        return "host_ipv4_address"

    @property
    def title(self):
        return _("Host address (IPv4)")

    @property
    def short_title(self):
        return _("IPv4 address")

    @property
    def columns(self):
        return ['host_custom_variable_names', 'host_custom_variable_values']

    def render(self, row, cell):
        return paint_custom_var('host', 'ADDRESS_4', row)


@painter_registry.register
class PainterHostIpv6Address(Painter):
    @property
    def ident(self):
        return "host_ipv6_address"

    @property
    def title(self):
        return _("Host address (IPv6)")

    @property
    def short_title(self):
        return _("IPv6 address")

    @property
    def columns(self):
        return ['host_custom_variable_names', 'host_custom_variable_values']

    def render(self, row, cell):
        return paint_custom_var('host', 'ADDRESS_6', row)


@painter_registry.register
class PainterHostAddresses(Painter):
    @property
    def ident(self):
        return "host_addresses"

    @property
    def title(self):
        return _("Host addresses (IPv4/IPv6)")

    @property
    def short_title(self):
        return _("IP addresses")

    @property
    def columns(self):
        return ['host_address', 'host_custom_variable_names', 'host_custom_variable_values']

    def render(self, row, cell):
        custom_vars = dict(
            zip(row["host_custom_variable_names"], row["host_custom_variable_values"]))

        if custom_vars.get("ADDRESS_FAMILY", "4") == "4":
            primary = custom_vars.get("ADDRESS_4", "")
            secondary = custom_vars.get("ADDRESS_6", "")
        else:
            primary = custom_vars.get("ADDRESS_6", "")
            secondary = custom_vars.get("ADDRESS_4", "")

        if secondary:
            secondary = " (%s)" % secondary
        return "", primary + secondary


@painter_registry.register
class PainterHostAddressesAdditional(Painter):
    @property
    def ident(self):
        return "host_addresses_additional"

    @property
    def title(self):
        return _("Host addresses (additional)")

    @property
    def short_title(self):
        return _("Add. addresses")

    @property
    def columns(self):
        return ["host_custom_variable_names", "host_custom_variable_values"]

    def render(self, row, cell):
        custom_vars = dict(
            zip(row["host_custom_variable_names"], row["host_custom_variable_values"]))

        ipv4_addresses = custom_vars.get("ADDRESSES_4", "").strip()
        ipv6_addresses = custom_vars.get("ADDRESSES_6", "").strip()

        addresses = []
        if ipv4_addresses:
            addresses += ipv4_addresses.split(" ")
        if ipv6_addresses:
            addresses += ipv6_addresses.split(" ")

        return "", ", ".join(addresses)


@painter_registry.register
class PainterHostAddressFamily(Painter):
    @property
    def ident(self):
        return "host_address_family"

    @property
    def title(self):
        return _("Host address family (Primary)")

    @property
    def short_title(self):
        return _("Address family")

    @property
    def columns(self):
        return ['host_custom_variable_names', 'host_custom_variable_values']

    def render(self, row, cell):
        return paint_custom_var('host', 'ADDRESS_FAMILY', row)


@painter_registry.register
class PainterHostAddressFamilies(Painter):
    @property
    def ident(self):
        return "host_address_families"

    @property
    def title(self):
        return _("Host address families")

    @property
    def short_title(self):
        return _("Address families")

    @property
    def columns(self):
        return ['host_custom_variable_names', 'host_custom_variable_values']

    def render(self, row, cell):
        custom_vars = dict(
            zip(row["host_custom_variable_names"], row["host_custom_variable_values"]))

        primary = custom_vars.get("ADDRESS_FAMILY", "4")

        families = [primary]
        if primary == "6" and custom_vars.get("ADDRESS_4"):
            families.append("4")
        elif primary == "4" and custom_vars.get("ADDRESS_6"):
            families.append("6")

        return "", ", ".join(families)


def paint_svc_count(id_, count):
    if count > 0:
        return "count svcstate state%s" % id_, str(count)
    return "count svcstate statex", "0"


def paint_host_count(id_, count):
    if count > 0:
        if id_ is not None:
            return "count hstate hstate%s" % id_, str(count)
        # pending
        return "count hstate hstatep", str(count)

    return "count hstate hstatex", "0"


@painter_registry.register
class PainterNumServices(Painter):
    @property
    def ident(self):
        return "num_services"

    @property
    def title(self):
        return _("Number of services")

    @property
    def short_title(self):
        return u""

    @property
    def columns(self):
        return ['host_num_services']

    def render(self, row, cell):
        return (None, str(row["host_num_services"]))


@painter_registry.register
class PainterNumServicesOk(Painter):
    @property
    def ident(self):
        return "num_services_ok"

    @property
    def title(self):
        return _("Number of services in state OK")

    @property
    def short_title(self):
        return _("OK")

    @property
    def columns(self):
        return ['host_num_services_ok']

    def render(self, row, cell):
        return paint_svc_count(0, row["host_num_services_ok"])


@painter_registry.register
class PainterNumProblems(Painter):
    @property
    def ident(self):
        return "num_problems"

    @property
    def title(self):
        return _("Number of problems")

    @property
    def short_title(self):
        return _("Pro.")

    @property
    def columns(self):
        return ['host_num_services', 'host_num_services_ok', 'host_num_services_pending']

    def render(self, row, cell):
        return paint_svc_count(
            's', row["host_num_services"] - row["host_num_services_ok"] -
            row["host_num_services_pending"])


@painter_registry.register
class PainterNumServicesWarn(Painter):
    @property
    def ident(self):
        return "num_services_warn"

    @property
    def title(self):
        return _("Number of services in state WARN")

    @property
    def short_title(self):
        return _("Wa")

    @property
    def columns(self):
        return ['host_num_services_warn']

    def render(self, row, cell):
        return paint_svc_count(1, row["host_num_services_warn"])


@painter_registry.register
class PainterNumServicesCrit(Painter):
    @property
    def ident(self):
        return "num_services_crit"

    @property
    def title(self):
        return _("Number of services in state CRIT")

    @property
    def short_title(self):
        return _("Cr")

    @property
    def columns(self):
        return ['host_num_services_crit']

    def render(self, row, cell):
        return paint_svc_count(2, row["host_num_services_crit"])


@painter_registry.register
class PainterNumServicesUnknown(Painter):
    @property
    def ident(self):
        return "num_services_unknown"

    @property
    def title(self):
        return _("Number of services in state UNKNOWN")

    @property
    def short_title(self):
        return _("Un")

    @property
    def columns(self):
        return ['host_num_services_unknown']

    def render(self, row, cell):
        return paint_svc_count(3, row["host_num_services_unknown"])


@painter_registry.register
class PainterNumServicesPending(Painter):
    @property
    def ident(self):
        return "num_services_pending"

    @property
    def title(self):
        return _("Number of services in state PENDING")

    @property
    def short_title(self):
        return _("Pd")

    @property
    def columns(self):
        return ['host_num_services_pending']

    def render(self, row, cell):
        return paint_svc_count("p", row["host_num_services_pending"])


def paint_service_list(row, columnname):
    def sort_key(entry):
        if columnname.startswith("servicegroup"):
            return entry[0].lower(), entry[1].lower()
        return entry[0].lower()

    h = ""
    for entry in sorted(row[columnname], key=sort_key):
        if columnname.startswith("servicegroup"):
            host, svc, state, checked = entry
            text = host + " ~ " + svc
        else:
            svc, state, checked = entry
            host = row["host_name"]
            text = svc
        link = "view.py?view_name=service&site=%s&host=%s&service=%s" % (html.urlencode(
            row["site"]), html.urlencode(host), html.urlencode(svc))
        if checked:
            css = "state%d" % state
        else:
            css = "statep"

        h += html.render_div(html.render_a(text, link), class_=css)

    return "", html.render_div(h, class_="objectlist")


@painter_registry.register
class PainterHostServices(Painter):
    @property
    def ident(self):
        return "host_services"

    @property
    def title(self):
        return _("Services colored according to state")

    @property
    def short_title(self):
        return _("Services")

    @property
    def columns(self):
        return ['host_name', 'host_services_with_state']

    def render(self, row, cell):
        return paint_service_list(row, "host_services_with_state")


@painter_registry.register
class PainterHostParents(Painter):
    @property
    def ident(self):
        return "host_parents"

    @property
    def title(self):
        return _("Host's parents")

    @property
    def short_title(self):
        return _("Parents")

    @property
    def columns(self):
        return ['host_parents']

    def render(self, row, cell):
        return paint_host_list(row["site"], row["host_parents"])


@painter_registry.register
class PainterHostChilds(Painter):
    @property
    def ident(self):
        return "host_childs"

    @property
    def title(self):
        return _("Host's children")

    @property
    def short_title(self):
        return _("children")

    @property
    def columns(self):
        return ['host_childs']

    def render(self, row, cell):
        return paint_host_list(row["site"], row["host_childs"])


@painter_registry.register
class PainterHostGroupMemberlist(Painter):
    @property
    def ident(self):
        return "host_group_memberlist"

    @property
    def title(self):
        return _("Host groups the host is member of")

    @property
    def short_title(self):
        return _("Groups")

    @property
    def columns(self):
        return ['host_groups']

    def group_by(self, row):
        return tuple(row["host_groups"])

    def render(self, row, cell):
        links = []
        for group in row["host_groups"]:
            link = "view.py?view_name=hostgroup&hostgroup=" + group
            if html.request.var("display_options"):
                link += "&display_options=%s" % html.attrencode(html.request.var("display_options"))
            links.append(html.render_a(group, link))
        return "", HTML(", ").join(links)


@painter_registry.register
class PainterHostContacts(Painter):
    @property
    def ident(self):
        return "host_contacts"

    @property
    def title(self):
        return _("Host contacts")

    @property
    def short_title(self):
        return _("Contacts")

    @property
    def columns(self):
        return ['host_contacts']

    def render(self, row, cell):
        return (None, ", ".join(row["host_contacts"]))


@painter_registry.register
class PainterHostContactGroups(Painter):
    @property
    def ident(self):
        return "host_contact_groups"

    @property
    def title(self):
        return _("Host contact groups")

    @property
    def short_title(self):
        return _("Contact groups")

    @property
    def columns(self):
        return ['host_contact_groups']

    def render(self, row, cell):
        return (None, ", ".join(row["host_contact_groups"]))


@painter_registry.register
class PainterHostCustomNotes(Painter):
    @property
    def ident(self):
        return "host_custom_notes"

    @property
    def title(self):
        return _("Custom host notes")

    @property
    def short_title(self):
        return _("Notes")

    @property
    def columns(self):
        return ['host_name', 'host_address', 'host_plugin_output']

    def render(self, row, cell):
        return paint_custom_notes("hosts", row)


@painter_registry.register
class PainterHostComments(Painter):
    @property
    def ident(self):
        return "host_comments"

    @property
    def title(self):
        return _("Host comments")

    @property
    def short_title(self):
        return _("Comments")

    @property
    def columns(self):
        return ['host_comments_with_info']

    def render(self, row, cell):
        return paint_comments("host_", row)


@painter_registry.register
class PainterHostInDowntime(Painter):
    @property
    def ident(self):
        return "host_in_downtime"

    @property
    def title(self):
        return _("Host in downtime")

    @property
    def short_title(self):
        return _("Downtime")

    @property
    def columns(self):
        return ['host_scheduled_downtime_depth']

    def render(self, row, cell):
        return paint_nagiosflag(row, "host_scheduled_downtime_depth", True)


@painter_registry.register
class PainterHostAcknowledged(Painter):
    @property
    def ident(self):
        return "host_acknowledged"

    @property
    def title(self):
        return _("Host problem acknowledged")

    @property
    def short_title(self):
        return _("Ack")

    @property
    def columns(self):
        return ['host_acknowledged']

    def render(self, row, cell):
        return paint_nagiosflag(row, "host_acknowledged", False)


@painter_registry.register
class PainterHostStaleness(Painter):
    @property
    def ident(self):
        return "host_staleness"

    @property
    def title(self):
        return _("Host staleness value")

    @property
    def short_title(self):
        return _("Staleness")

    @property
    def columns(self):
        return ['host_staleness']

    def render(self, row, cell):
        return ('', '%0.2f' % row.get('host_staleness', 0))


@painter_registry.register
class PainterHostIsStale(Painter):
    @property
    def ident(self):
        return "host_is_stale"

    @property
    def title(self):
        return _("Host is stale")

    @property
    def short_title(self):
        return _("Stale")

    @property
    def columns(self):
        return ['host_staleness']

    @property
    def sorter(self):
        return 'svc_staleness'

    def render(self, row, cell):
        return paint_is_stale(row)


@painter_registry.register
class PainterHostServicelevel(Painter):
    @property
    def ident(self):
        return "host_servicelevel"

    @property
    def title(self):
        return _("Host service level")

    @property
    def short_title(self):
        return _("Service Level")

    @property
    def columns(self):
        return ['host_custom_variable_names', 'host_custom_variable_values']

    @property
    def sorter(self):
        return 'servicelevel'

    def render(self, row, cell):
        return paint_custom_var('host', 'EC_SL', row, config.mkeventd_service_levels)


@painter_registry.register
class PainterHostCustomVariables(Painter):
    @property
    def ident(self):
        return "host_custom_vars"

    @property
    def title(self):
        return _("Host custom attributes")

    @property
    def columns(self):
        return ['host_custom_variables']

    def group_by(self, row):
        return tuple(row["host_custom_variables"].items())

    def render(self, row, cell):
        return paint_custom_vars('host', row, [
            'FILENAME',
            'TAGS',
            'ADDRESS_4',
            'ADDRESS_6',
            'ADDRESS_FAMILY',
            'NODEIPS',
            'NODEIPS_4',
            'NODEIPS_6',
        ])


def paint_discovery_output(field, row):
    value = row[field]
    if field == "discovery_state":
        ruleset_url = "wato.py?mode=edit_ruleset&varname=ignored_services"
        discovery_url = "wato.py?mode=inventory&host=%s&mode=inventory" % row["host_name"]

        return None, {
            "ignored": html.render_icon_button(ruleset_url, 'Disabled (configured away by admin)',
                                               'rulesets') + "Disabled (configured away by admin)",
            "vanished": html.render_icon_button(
                discovery_url, 'Vanished (checked, but no longer exist)', 'services') +
                        "Vanished (checked, but no longer exist)",
            "unmonitored": html.render_icon_button(discovery_url, 'Available (missing)', 'services')
                           + "Available (missing)"
        }.get(value, value)
    elif field == "discovery_service" and row["discovery_state"] == "vanished":
        link = "view.py?view_name=service&site=%s&host=%s&service=%s" % (html.urlencode(
            row["site"]), html.urlencode(row["host_name"]), html.urlencode(value))
        return None, html.render_div(html.render_a(value, link))
    return None, value


@painter_registry.register
class PainterServiceDiscoveryState(Painter):
    @property
    def ident(self):
        return "service_discovery_state"

    @property
    def title(self):
        return _("Service discovery: State")

    @property
    def short_title(self):
        return _("State")

    @property
    def columns(self):
        return ['discovery_state']

    def render(self, row, cell):
        return paint_discovery_output("discovery_state", row)


@painter_registry.register
class PainterServiceDiscoveryCheck(Painter):
    @property
    def ident(self):
        return "service_discovery_check"

    @property
    def title(self):
        return _("Service discovery: Check type")

    @property
    def short_title(self):
        return _("Check type")

    @property
    def columns(self):
        return ['discovery_state', 'discovery_check', 'discovery_service']

    def render(self, row, cell):
        return paint_discovery_output("discovery_check", row)


@painter_registry.register
class PainterServiceDiscoveryService(Painter):
    @property
    def ident(self):
        return "service_discovery_service"

    @property
    def title(self):
        return _("Service discovery: Service description")

    @property
    def short_title(self):
        return _("Service description")

    @property
    def columns(self):
        return ['discovery_state', 'discovery_check', 'discovery_service']

    def render(self, row, cell):
        return paint_discovery_output("discovery_service", row)


#    _   _           _
#   | | | | ___  ___| |_ __ _ _ __ ___  _   _ _ __  ___
#   | |_| |/ _ \/ __| __/ _` | '__/ _ \| | | | '_ \/ __|
#   |  _  | (_) \__ \ || (_| | | | (_) | |_| | |_) \__ \
#   |_| |_|\___/|___/\__\__, |_|  \___/ \__,_| .__/|___/
#                       |___/                |_|
#
@painter_registry.register
class PainterHostgroupHosts(Painter):
    @property
    def ident(self):
        return "hostgroup_hosts"

    @property
    def title(self):
        return _("Hosts colored according to state (Host Group)")

    @property
    def short_title(self):
        return _("Hosts")

    @property
    def columns(self):
        return ['hostgroup_members_with_state']

    def render(self, row, cell):
        h = ""
        for host, state, checked in row["hostgroup_members_with_state"]:
            link = "view.py?view_name=host&site=%s&host=%s" % (html.urlencode(
                row["site"]), html.urlencode(host))
            if checked:
                css = "hstate%d" % state
            else:
                css = "hstatep"
            h += html.render_div(html.render_a(host, link), class_=css)
        return "", html.render_div(h, class_="objectlist")


@painter_registry.register
class PainterHgNumServices(Painter):
    @property
    def ident(self):
        return "hg_num_services"

    @property
    def title(self):
        return _("Number of services (Host Group)")

    @property
    def short_title(self):
        return u""

    @property
    def columns(self):
        return ['hostgroup_num_services']

    def render(self, row, cell):
        return (None, str(row["hostgroup_num_services"]))


@painter_registry.register
class PainterHgNumServicesOk(Painter):
    @property
    def ident(self):
        return "hg_num_services_ok"

    @property
    def title(self):
        return _("Number of services in state OK (Host Group)")

    @property
    def short_title(self):
        return _("O")

    @property
    def columns(self):
        return ['hostgroup_num_services_ok']

    def render(self, row, cell):
        return paint_svc_count(0, row["hostgroup_num_services_ok"])


@painter_registry.register
class PainterHgNumServicesWarn(Painter):
    @property
    def ident(self):
        return "hg_num_services_warn"

    @property
    def title(self):
        return _("Number of services in state WARN (Host Group)")

    @property
    def short_title(self):
        return _("W")

    @property
    def columns(self):
        return ['hostgroup_num_services_warn']

    def render(self, row, cell):
        return paint_svc_count(1, row["hostgroup_num_services_warn"])


@painter_registry.register
class PainterHgNumServicesCrit(Painter):
    @property
    def ident(self):
        return "hg_num_services_crit"

    @property
    def title(self):
        return _("Number of services in state CRIT (Host Group)")

    @property
    def short_title(self):
        return _("C")

    @property
    def columns(self):
        return ['hostgroup_num_services_crit']

    def render(self, row, cell):
        return paint_svc_count(2, row["hostgroup_num_services_crit"])


@painter_registry.register
class PainterHgNumServicesUnknown(Painter):
    @property
    def ident(self):
        return "hg_num_services_unknown"

    @property
    def title(self):
        return _("Number of services in state UNKNOWN (Host Group)")

    @property
    def short_title(self):
        return _("U")

    @property
    def columns(self):
        return ['hostgroup_num_services_unknown']

    def render(self, row, cell):
        return paint_svc_count(3, row["hostgroup_num_services_unknown"])


@painter_registry.register
class PainterHgNumServicesPending(Painter):
    @property
    def ident(self):
        return "hg_num_services_pending"

    @property
    def title(self):
        return _("Number of services in state PENDING (Host Group)")

    @property
    def short_title(self):
        return _("P")

    @property
    def columns(self):
        return ['hostgroup_num_services_pending']

    def render(self, row, cell):
        return paint_svc_count("p", row["hostgroup_num_services_pending"])


@painter_registry.register
class PainterHgNumHostsUp(Painter):
    @property
    def ident(self):
        return "hg_num_hosts_up"

    @property
    def title(self):
        return _("Number of hosts in state UP (Host Group)")

    @property
    def short_title(self):
        return _("Up")

    @property
    def columns(self):
        return ['hostgroup_num_hosts_up']

    def render(self, row, cell):
        return paint_host_count(0, row["hostgroup_num_hosts_up"])


@painter_registry.register
class PainterHgNumHostsDown(Painter):
    @property
    def ident(self):
        return "hg_num_hosts_down"

    @property
    def title(self):
        return _("Number of hosts in state DOWN (Host Group)")

    @property
    def short_title(self):
        return _("Dw")

    @property
    def columns(self):
        return ['hostgroup_num_hosts_down']

    def render(self, row, cell):
        return paint_host_count(1, row["hostgroup_num_hosts_down"])


@painter_registry.register
class PainterHgNumHostsUnreach(Painter):
    @property
    def ident(self):
        return "hg_num_hosts_unreach"

    @property
    def title(self):
        return _("Number of hosts in state UNREACH (Host Group)")

    @property
    def short_title(self):
        return _("Un")

    @property
    def columns(self):
        return ['hostgroup_num_hosts_unreach']

    def render(self, row, cell):
        return paint_host_count(2, row["hostgroup_num_hosts_unreach"])


@painter_registry.register
class PainterHgNumHostsPending(Painter):
    @property
    def ident(self):
        return "hg_num_hosts_pending"

    @property
    def title(self):
        return _("Number of hosts in state PENDING (Host Group)")

    @property
    def short_title(self):
        return _("Pd")

    @property
    def columns(self):
        return ['hostgroup_num_hosts_pending']

    def render(self, row, cell):
        return paint_host_count(None, row["hostgroup_num_hosts_pending"])


@painter_registry.register
class PainterHgName(Painter):
    @property
    def ident(self):
        return "hg_name"

    @property
    def title(self):
        return _("Hostgroup name")

    @property
    def short_title(self):
        return _("Name")

    @property
    def columns(self):
        return ['hostgroup_name']

    def render(self, row, cell):
        return (None, row["hostgroup_name"])


@painter_registry.register
class PainterHgAlias(Painter):
    @property
    def ident(self):
        return "hg_alias"

    @property
    def title(self):
        return _("Hostgroup alias")

    @property
    def short_title(self):
        return _("Alias")

    @property
    def columns(self):
        return ['hostgroup_alias']

    def render(self, row, cell):
        return (None, html.attrencode(row["hostgroup_alias"]))


#    ____                  _
#   / ___|  ___ _ ____   _(_) ___ ___  __ _ _ __ ___  _   _ _ __  ___
#   \___ \ / _ \ '__\ \ / / |/ __/ _ \/ _` | '__/ _ \| | | | '_ \/ __|
#    ___) |  __/ |   \ V /| | (_|  __/ (_| | | | (_) | |_| | |_) \__ \
#   |____/ \___|_|    \_/ |_|\___\___|\__, |_|  \___/ \__,_| .__/|___/
#                                     |___/                |_|


@painter_registry.register
class PainterSgServices(Painter):
    @property
    def ident(self):
        return "sg_services"

    @property
    def title(self):
        return _("Services colored according to state (Service Group)")

    @property
    def short_title(self):
        return _("Services")

    @property
    def columns(self):
        return ['servicegroup_members_with_state']

    def render(self, row, cell):
        return paint_service_list(row, "servicegroup_members_with_state")


@painter_registry.register
class PainterSgNumServices(Painter):
    @property
    def ident(self):
        return "sg_num_services"

    @property
    def title(self):
        return _("Number of services (Service Group)")

    @property
    def short_title(self):
        return u""

    @property
    def columns(self):
        return ['servicegroup_num_services']

    def render(self, row, cell):
        return (None, str(row["servicegroup_num_services"]))


@painter_registry.register
class PainterSgNumServicesOk(Painter):
    @property
    def ident(self):
        return "sg_num_services_ok"

    @property
    def title(self):
        return _("Number of services in state OK (Service Group)")

    @property
    def short_title(self):
        return _("O")

    @property
    def columns(self):
        return ['servicegroup_num_services_ok']

    def render(self, row, cell):
        return paint_svc_count(0, row["servicegroup_num_services_ok"])


@painter_registry.register
class PainterSgNumServicesWarn(Painter):
    @property
    def ident(self):
        return "sg_num_services_warn"

    @property
    def title(self):
        return _("Number of services in state WARN (Service Group)")

    @property
    def short_title(self):
        return _("W")

    @property
    def columns(self):
        return ['servicegroup_num_services_warn']

    def render(self, row, cell):
        return paint_svc_count(1, row["servicegroup_num_services_warn"])


@painter_registry.register
class PainterSgNumServicesCrit(Painter):
    @property
    def ident(self):
        return "sg_num_services_crit"

    @property
    def title(self):
        return _("Number of services in state CRIT (Service Group)")

    @property
    def short_title(self):
        return _("C")

    @property
    def columns(self):
        return ['servicegroup_num_services_crit']

    def render(self, row, cell):
        return paint_svc_count(2, row["servicegroup_num_services_crit"])


@painter_registry.register
class PainterSgNumServicesUnknown(Painter):
    @property
    def ident(self):
        return "sg_num_services_unknown"

    @property
    def title(self):
        return _("Number of services in state UNKNOWN (Service Group)")

    @property
    def short_title(self):
        return _("U")

    @property
    def columns(self):
        return ['servicegroup_num_services_unknown']

    def render(self, row, cell):
        return paint_svc_count(3, row["servicegroup_num_services_unknown"])


@painter_registry.register
class PainterSgNumServicesPending(Painter):
    @property
    def ident(self):
        return "sg_num_services_pending"

    @property
    def title(self):
        return _("Number of services in state PENDING (Service Group)")

    @property
    def short_title(self):
        return _("P")

    @property
    def columns(self):
        return ['servicegroup_num_services_pending']

    def render(self, row, cell):
        return paint_svc_count("p", row["servicegroup_num_services_pending"])


@painter_registry.register
class PainterSgName(Painter):
    @property
    def ident(self):
        return "sg_name"

    @property
    def title(self):
        return _("Servicegroup name")

    @property
    def short_title(self):
        return _("Name")

    @property
    def columns(self):
        return ['servicegroup_name']

    def render(self, row, cell):
        return (None, row["servicegroup_name"])


@painter_registry.register
class PainterSgAlias(Painter):
    @property
    def ident(self):
        return "sg_alias"

    @property
    def title(self):
        return _("Servicegroup alias")

    @property
    def short_title(self):
        return _("Alias")

    @property
    def columns(self):
        return ['servicegroup_alias']

    def render(self, row, cell):
        return (None, html.attrencode(row["servicegroup_alias"]))


#     ____                                     _
#    / ___|___  _ __ ___  _ __ ___   ___ _ __ | |_ ___
#   | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \| __/ __|
#   | |__| (_) | | | | | | | | | | |  __/ | | | |_\__ \
#    \____\___/|_| |_| |_|_| |_| |_|\___|_| |_|\__|___/
#


@painter_registry.register
class PainterCommentId(Painter):
    @property
    def ident(self):
        return "comment_id"

    @property
    def title(self):
        return _("Comment id")

    @property
    def short_title(self):
        return _("ID")

    @property
    def columns(self):
        return ['comment_id']

    def render(self, row, cell):
        return (None, str(row["comment_id"]))


@painter_registry.register
class PainterCommentAuthor(Painter):
    @property
    def ident(self):
        return "comment_author"

    @property
    def title(self):
        return _("Comment author")

    @property
    def short_title(self):
        return _("Author")

    @property
    def columns(self):
        return ['comment_author']

    def render(self, row, cell):
        return (None, row["comment_author"])


@painter_registry.register
class PainterCommentComment(Painter):
    @property
    def ident(self):
        return "comment_comment"

    @property
    def title(self):
        return _("Comment text")

    @property
    def columns(self):
        return ['comment_comment']

    def render(self, row, cell):
        return (None, format_plugin_output(row["comment_comment"], row))


@painter_registry.register
class PainterCommentWhat(Painter):
    @property
    def ident(self):
        return "comment_what"

    @property
    def title(self):
        return _("Comment type (host/service)")

    @property
    def short_title(self):
        return _("Type")

    @property
    def columns(self):
        return ['comment_type']

    def render(self, row, cell):
        return (None, row["comment_type"] == 1 and _("Host") or _("Service"))


@painter_registry.register
class PainterCommentTime(Painter):
    @property
    def ident(self):
        return "comment_time"

    @property
    def title(self):
        return _("Comment entry time")

    @property
    def short_title(self):
        return _("Time")

    @property
    def columns(self):
        return ['comment_entry_time']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["comment_entry_time"], True, 3600)


@painter_registry.register
class PainterCommentExpires(Painter):
    @property
    def ident(self):
        return "comment_expires"

    @property
    def title(self):
        return _("Comment expiry time")

    @property
    def short_title(self):
        return _("Expires")

    @property
    def columns(self):
        return ['comment_expire_time']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["comment_expire_time"],
                         row["comment_expire_time"] != 0,
                         3600,
                         what='future')


@painter_registry.register
class PainterCommentEntryType(Painter):
    @property
    def ident(self):
        return "comment_entry_type"

    @property
    def title(self):
        return _("Comment entry type (user/downtime/flapping/ack)")

    @property
    def short_title(self):
        return _("E.Type")

    @property
    def columns(self):
        return ['comment_entry_type', 'host_name', 'service_description']

    def render(self, row, cell):
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
        code = html.render_icon(icon, help_txt)
        if linkview:
            code = link_to_view(code, row, linkview)
        return "icons", code


#    ____                      _   _
#   |  _ \  _____      ___ __ | |_(_)_ __ ___   ___  ___
#   | | | |/ _ \ \ /\ / / '_ \| __| | '_ ` _ \ / _ \/ __|
#   | |_| | (_) \ V  V /| | | | |_| | | | | | |  __/\__ \
#   |____/ \___/ \_/\_/ |_| |_|\__|_|_| |_| |_|\___||___/
#


@painter_registry.register
class PainterDowntimeId(Painter):
    @property
    def ident(self):
        return "downtime_id"

    @property
    def title(self):
        return _("Downtime id")

    @property
    def short_title(self):
        return _("ID")

    @property
    def columns(self):
        return ['downtime_id']

    def render(self, row, cell):
        return (None, "%d" % row["downtime_id"])


@painter_registry.register
class PainterDowntimeAuthor(Painter):
    @property
    def ident(self):
        return "downtime_author"

    @property
    def title(self):
        return _("Downtime author")

    @property
    def short_title(self):
        return _("Author")

    @property
    def columns(self):
        return ['downtime_author']

    def render(self, row, cell):
        return (None, row["downtime_author"])


@painter_registry.register
class PainterDowntimeComment(Painter):
    @property
    def ident(self):
        return "downtime_comment"

    @property
    def title(self):
        return _("Downtime comment")

    @property
    def short_title(self):
        return _("Comment")

    @property
    def columns(self):
        return ['downtime_comment']

    def render(self, row, cell):
        return (None, format_plugin_output(row["downtime_comment"], row))


@painter_registry.register
class PainterDowntimeFixed(Painter):
    @property
    def ident(self):
        return "downtime_fixed"

    @property
    def title(self):
        return _("Downtime start mode")

    @property
    def short_title(self):
        return _("Mode")

    @property
    def columns(self):
        return ['downtime_fixed']

    def render(self, row, cell):
        return (None, row["downtime_fixed"] == 0 and _("flexible") or _("fixed"))


@painter_registry.register
class PainterDowntimeOrigin(Painter):
    @property
    def ident(self):
        return "downtime_origin"

    @property
    def title(self):
        return _("Downtime origin")

    @property
    def short_title(self):
        return _("Origin")

    @property
    def columns(self):
        return ['downtime_origin']

    def render(self, row, cell):
        return (None, row["downtime_origin"] == 1 and _("configuration") or _("command"))


@painter_registry.register
class PainterDowntimeRecurring(Painter):
    @property
    def ident(self):
        return "downtime_recurring"

    @property
    def title(self):
        return _("Downtime recurring interval")

    @property
    def short_title(self):
        return _("Recurring")

    @property
    def columns(self):
        return ['downtime_recurring']

    def render(self, row, cell):
        try:
            from cmk.gui.cee.plugins.wato.cmc import recurring_downtimes_types
        except ImportError:
            return "", _("(not supported)")

        r = row["downtime_recurring"]
        if not r:
            return "", _("no")
        return "", recurring_downtimes_types().get(r, _("(unknown: %d)") % r)


@painter_registry.register
class PainterDowntimeWhat(Painter):
    @property
    def ident(self):
        return "downtime_what"

    @property
    def title(self):
        return _("Downtime for host/service")

    @property
    def short_title(self):
        return _("for")

    @property
    def columns(self):
        return ['downtime_is_service']

    def render(self, row, cell):
        return (None, row["downtime_is_service"] and _("Service") or _("Host"))


@painter_registry.register
class PainterDowntimeType(Painter):
    @property
    def ident(self):
        return "downtime_type"

    @property
    def title(self):
        return _("Downtime active or pending")

    @property
    def short_title(self):
        return _("act/pend")

    @property
    def columns(self):
        return ['downtime_type']

    def render(self, row, cell):
        return (None, row["downtime_type"] == 0 and _("active") or _("pending"))


@painter_registry.register
class PainterDowntimeEntryTime(Painter):
    @property
    def ident(self):
        return "downtime_entry_time"

    @property
    def title(self):
        return _("Downtime entry time")

    @property
    def short_title(self):
        return _("Entry")

    @property
    def columns(self):
        return ['downtime_entry_time']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["downtime_entry_time"], True, 3600)


@painter_registry.register
class PainterDowntimeStartTime(Painter):
    @property
    def ident(self):
        return "downtime_start_time"

    @property
    def title(self):
        return _("Downtime start time")

    @property
    def short_title(self):
        return _("Start")

    @property
    def columns(self):
        return ['downtime_start_time']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["downtime_start_time"], True, 3600, what="both")


@painter_registry.register
class PainterDowntimeEndTime(Painter):
    @property
    def ident(self):
        return "downtime_end_time"

    @property
    def title(self):
        return _("Downtime end time")

    @property
    def short_title(self):
        return _("End")

    @property
    def columns(self):
        return ['downtime_end_time']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["downtime_end_time"], True, 3600, what="both")


@painter_registry.register
class PainterDowntimeDuration(Painter):
    @property
    def ident(self):
        return "downtime_duration"

    @property
    def title(self):
        return _("Downtime duration (if flexible)")

    @property
    def short_title(self):
        return _("Flex. Duration")

    @property
    def columns(self):
        return ['downtime_duration', 'downtime_fixed']

    def render(self, row, cell):
        if row["downtime_fixed"] == 0:
            return "number", "%02d:%02d:00" % divmod(row["downtime_duration"] / 60, 60)
        return "", ""


#    _
#   | |    ___   __ _
#   | |   / _ \ / _` |
#   | |__| (_) | (_| |
#   |_____\___/ \__, |
#               |___/


@painter_registry.register
class PainterLogMessage(Painter):
    @property
    def ident(self):
        return "log_message"

    @property
    def title(self):
        return _("Log: complete message")

    @property
    def short_title(self):
        return _("Message")

    @property
    def columns(self):
        return ['log_message']

    def render(self, row, cell):
        return ("", html.attrencode(row["log_message"]))


@painter_registry.register
class PainterLogPluginOutput(Painter):
    @property
    def ident(self):
        return "log_plugin_output"

    @property
    def title(self):
        return _("Log: Output")

    @property
    def short_title(self):
        return _("Output")

    @property
    def columns(self):
        return [
            'log_plugin_output', 'log_type', 'log_state_type', 'log_comment', 'custom_variables'
        ]

    def render(self, row, cell):
        output = row["log_plugin_output"]
        comment = row["log_comment"]

        if output:
            return "", format_plugin_output(output, row)

        elif comment:
            return "", html.attrencode(comment)

        else:
            log_type = row["log_type"]
            lst = row["log_state_type"]
            if "FLAPPING" in log_type:
                if "HOST" in log_type:
                    what = _("host")
                else:
                    what = _("service")
                if lst == "STOPPED":
                    return "", _("The %s stopped flapping") % what
                return "", _("The %s started flapping") % what

            elif lst:
                return "", (lst + " - " + log_type)
            else:
                return "", ""


@painter_registry.register
class PainterLogWhat(Painter):
    @property
    def ident(self):
        return "log_what"

    @property
    def title(self):
        return _("Log: host or service")

    @property
    def short_title(self):
        return _("Host/Service")

    @property
    def columns(self):
        return ['log_type']

    def render(self, row, cell):
        lt = row["log_type"]
        if "HOST" in lt:
            return "", _("Host")
        elif "SERVICE" in lt or "SVC" in lt:
            return "", _("Service")
        return "", _("Program")


@painter_registry.register
class PainterLogAttempt(Painter):
    @property
    def ident(self):
        return "log_attempt"

    @property
    def title(self):
        return _("Log: number of check attempt")

    @property
    def short_title(self):
        return _("Att.")

    @property
    def columns(self):
        return ['log_attempt']

    def render(self, row, cell):
        return ("", str(row["log_attempt"]))


@painter_registry.register
class PainterLogStateType(Painter):
    @property
    def ident(self):
        return "log_state_type"

    @property
    def title(self):
        return _("Log: type of state (hard/soft/stopped/started)")

    @property
    def short_title(self):
        return _("Type")

    @property
    def columns(self):
        return ['log_state_type']

    def render(self, row, cell):
        return ("", row["log_state_type"])


@painter_registry.register
class PainterLogType(Painter):
    @property
    def ident(self):
        return "log_type"

    @property
    def title(self):
        return _("Log: event")

    @property
    def short_title(self):
        return _("Event")

    @property
    def columns(self):
        return ['log_type']

    def render(self, row, cell):
        return ("nowrap", row["log_type"])


@painter_registry.register
class PainterLogContactName(Painter):
    @property
    def ident(self):
        return "log_contact_name"

    @property
    def title(self):
        return _("Log: contact name")

    @property
    def short_title(self):
        return _("Contact")

    @property
    def columns(self):
        return ['log_contact_name']

    def render(self, row, cell):
        return ("nowrap", row["log_contact_name"])


@painter_registry.register
class PainterLogCommand(Painter):
    @property
    def ident(self):
        return "log_command"

    @property
    def title(self):
        return _("Log: command/plugin")

    @property
    def short_title(self):
        return _("Command")

    @property
    def columns(self):
        return ['log_command_name']

    def render(self, row, cell):
        return ("nowrap", row["log_command_name"])


@painter_registry.register
class PainterLogIcon(Painter):
    @property
    def ident(self):
        return "log_icon"

    @property
    def title(self):
        return _("Log: event icon")

    @property
    def short_title(self):
        return u""

    @property
    def columns(self):
        return ['log_type', 'log_state', 'log_state_type', 'log_command_name']

    def render(self, row, cell):
        img = None
        log_type = row["log_type"]
        log_state = row["log_state"]

        if log_type == "SERVICE ALERT":
            img = {0: "ok", 1: "warn", 2: "crit", 3: "unknown"}.get(row["log_state"])
            title = _("Service Alert")

        elif log_type == "HOST ALERT":
            img = {0: "up", 1: "down", 2: "unreach"}.get(row["log_state"])
            title = _("Host Alert")

        elif log_type.endswith("ALERT HANDLER STARTED"):
            img = "alert_handler_started"
            title = _("Alert Handler Started")

        elif log_type.endswith("ALERT HANDLER STOPPED"):
            if log_state == 0:
                img = "alert_handler_stopped"
                title = _("Alert handler Stopped")
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
            return "icon", html.render_icon("alert_" + img, title=title)
        return "icon", ""


@painter_registry.register
class PainterLogOptions(Painter):
    @property
    def ident(self):
        return "log_options"

    @property
    def title(self):
        return _("Log: informational part of message")

    @property
    def short_title(self):
        return _("Info")

    @property
    def columns(self):
        return ['log_options']

    def render(self, row, cell):
        return ("", html.attrencode(row["log_options"]))


@painter_registry.register
class PainterLogComment(Painter):
    @property
    def ident(self):
        return "log_comment"

    @property
    def title(self):
        return _("Log: comment")

    @property
    def short_title(self):
        return _("Comment")

    @property
    def columns(self):
        return ['log_options']

    def render(self, row, cell):
        msg = row['log_options']
        if ';' in msg:
            parts = msg.split(';')
            if len(parts) > 6:
                return ("", html.attrencode(parts[-1]))
        return ("", "")


@painter_registry.register
class PainterLogTime(Painter):
    @property
    def ident(self):
        return "log_time"

    @property
    def title(self):
        return _("Log: entry time")

    @property
    def short_title(self):
        return _("Time")

    @property
    def columns(self):
        return ['log_time']

    @property
    def painter_options(self):
        return ['ts_format', 'ts_date']

    def render(self, row, cell):
        return paint_age(row["log_time"], True, 3600 * 24)


@painter_registry.register
class PainterLogLineno(Painter):
    @property
    def ident(self):
        return "log_lineno"

    @property
    def title(self):
        return _("Log: line number in log file")

    @property
    def short_title(self):
        return _("Line")

    @property
    def columns(self):
        return ['log_lineno']

    def render(self, row, cell):
        return ("number", str(row["log_lineno"]))


@painter_registry.register
class PainterLogDate(Painter):
    @property
    def ident(self):
        return "log_date"

    @property
    def title(self):
        return _("Log: day of entry")

    @property
    def short_title(self):
        return _("Date")

    @property
    def columns(self):
        return ['log_time']

    def group_by(self, row):
        return paint_day(row["log_time"])[1]

    def render(self, row, cell):
        return paint_day(row["log_time"])


@painter_registry.register
class PainterLogState(Painter):
    @property
    def ident(self):
        return "log_state"

    @property
    def title(self):
        return _("Log: state of host/service at log time")

    @property
    def short_title(self):
        return _("State")

    @property
    def columns(self):
        return ['log_state', 'log_state_type', 'log_service_description', 'log_type']

    def render(self, row, cell):
        state = row["log_state"]

        # Notification result/progress lines don't hold real states. They hold notification plugin
        # exit results (0: ok, 1: temp issue, 2: perm issue). We display them as service states.
        if row["log_service_description"] \
           or row["log_type"].endswith("NOTIFICATION RESULT") \
           or row["log_type"].endswith("NOTIFICATION PROGRESS"):
            return paint_service_state_short({
                "service_has_been_checked": 1,
                "service_state": state
            })
        return paint_host_state_short({"host_has_been_checked": 1, "host_state": state})


# Alert statistics


@painter_registry.register
class PainterAlertStatsOk(Painter):
    @property
    def ident(self):
        return "alert_stats_ok"

    @property
    def title(self):
        return _("Alert Statistics: Number of recoveries")

    @property
    def short_title(self):
        return _("OK")

    @property
    def columns(self):
        return ['log_alerts_ok']

    def render(self, row, cell):
        return ("", str(row["log_alerts_ok"]))


@painter_registry.register
class PainterAlertStatsWarn(Painter):
    @property
    def ident(self):
        return "alert_stats_warn"

    @property
    def title(self):
        return _("Alert Statistics: Number of warnings")

    @property
    def short_title(self):
        return _("WARN")

    @property
    def columns(self):
        return ['log_alerts_warn']

    def render(self, row, cell):
        return paint_svc_count(1, row["log_alerts_warn"])


@painter_registry.register
class PainterAlertStatsCrit(Painter):
    @property
    def ident(self):
        return "alert_stats_crit"

    @property
    def title(self):
        return _("Alert Statistics: Number of critical alerts")

    @property
    def short_title(self):
        return _("CRIT")

    @property
    def columns(self):
        return ['log_alerts_crit']

    def render(self, row, cell):
        return paint_svc_count(2, row["log_alerts_crit"])


@painter_registry.register
class PainterAlertStatsUnknown(Painter):
    @property
    def ident(self):
        return "alert_stats_unknown"

    @property
    def title(self):
        return _("Alert Statistics: Number of unknown alerts")

    @property
    def short_title(self):
        return _("UNKN")

    @property
    def columns(self):
        return ['log_alerts_unknown']

    def render(self, row, cell):
        return paint_svc_count(3, row["log_alerts_unknown"])


@painter_registry.register
class PainterAlertStatsProblem(Painter):
    @property
    def ident(self):
        return "alert_stats_problem"

    @property
    def title(self):
        return _("Alert Statistics: Number of problem alerts")

    @property
    def short_title(self):
        return _("PROB")

    @property
    def columns(self):
        return ['log_alerts_problem']

    def render(self, row, cell):
        return paint_svc_count('s', row["log_alerts_problem"])


#
# TAGS
#


@painter_registry.register
class PainterHostTags(Painter):
    @property
    def ident(self):
        return "host_tags"

    @property
    def title(self):
        return _("Host tags")

    @property
    def short_title(self):
        return _("Tags")

    @property
    def columns(self):
        return ["host_tags"]

    @property
    def sorter(self):
        return "host"

    def render(self, row, cell):
        return "", render_tag_groups(get_tag_groups(row, "host"), "host", with_links=True)


class ABCPainterTagsWithTitles(Painter):
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def object_type(self):
        raise NotImplementedError()

    def render(self, row, cell):
        entries = self._get_entries(row)
        return "", "<br>".join(["%s: %s" % e for e in sorted(entries)])

    def _get_entries(self, row):
        entries = []
        for tag_group_id, tag_id in get_tag_groups(row, self.object_type).items():
            tag_group = config.tags.get_tag_group(tag_group_id)
            if tag_group:
                entries.append(
                    (tag_group.title, dict(tag_group.get_tag_choices()).get(tag_id, tag_id)))
                continue

            aux_tag_title = dict(config.tags.aux_tag_list.get_choices()).get(tag_group_id)
            if aux_tag_title:
                entries.append((aux_tag_title, aux_tag_title))
                continue

            entries.append((tag_group_id, tag_id))
        return entries


@painter_registry.register
class PainterHostTagsWithTitles(ABCPainterTagsWithTitles):
    @property
    def object_type(self):
        return "host"

    @property
    def ident(self):
        return "host_tags_with_titles"

    @property
    def title(self):
        return _("Host tags (with titles)")

    @property
    def short_title(self):
        return _("Tags")

    @property
    def columns(self):
        return ["host_tags"]

    @property
    def sorter(self):
        return "host"


@painter_registry.register
class PainterServiceTags(Painter):
    @property
    def ident(self):
        return "service_tags"

    @property
    def title(self):
        return _("Tags")

    @property
    def short_title(self):
        return _("Tags")

    @property
    def columns(self):
        return ["service_tags"]

    @property
    def sorter(self):
        return "service_tags"

    def render(self, row, cell):
        return "", render_tag_groups(get_tag_groups(row, "service"), "service", with_links=True)


@painter_registry.register
class PainterServiceTagsWithTitles(ABCPainterTagsWithTitles):
    @property
    def object_type(self):
        return "service"

    @property
    def ident(self):
        return "service_tags_with_titles"

    @property
    def title(self):
        return _("Tags (with titles)")

    @property
    def short_title(self):
        return _("Tags")

    @property
    def columns(self):
        return ["service_tags"]

    @property
    def sorter(self):
        return "service_tags"


@painter_registry.register
class PainterHostLabels(Painter):
    @property
    def ident(self):
        return "host_labels"

    @property
    def title(self):
        return _("Labels")

    @property
    def short_title(self):
        return _("Labels")

    @property
    def columns(self):
        return ["host_labels", "host_label_sources"]

    @property
    def sorter(self):
        return "host_labels"

    def render(self, row, cell):
        return "", render_labels(get_labels(row, "host"),
                                 "host",
                                 with_links=True,
                                 label_sources=get_label_sources(row, "host"))


@painter_registry.register
class PainterServiceLabels(Painter):
    @property
    def ident(self):
        return "service_labels"

    @property
    def title(self):
        return _("Labels")

    @property
    def short_title(self):
        return _("Labels")

    @property
    def columns(self):
        return ["service_labels", "service_label_sources"]

    @property
    def sorter(self):
        return "service_labels"

    def render(self, row, cell):
        return "", render_labels(get_labels(row, "service"),
                                 "service",
                                 with_links=True,
                                 label_sources=get_label_sources(row, "service"))


@painter_registry.register
class PainterHostDockerNode(Painter):
    @property
    def ident(self):
        return "host_docker_node"

    @property
    def title(self):
        return _("Docker node")

    @property
    def short_title(self):
        return _("Node")

    @property
    def columns(self):
        return ["host_labels", "host_label_sources"]

    def render(self, row, cell):
        source_hosts = [
            k[21:]
            for k in get_labels(row, "host").iterkeys()
            if k.startswith("cmk/piggyback_source_")
        ]

        if not source_hosts:
            return "", ""

        # We need the labels of the piggyback hosts to know which of them is
        # the docker node. We can not do livestatus queries per host/row here.
        # For this reason we perform a single query for all hosts of the users
        # sites which is then cached to prevent additional queries.
        host_labels = _get_host_labels()

        docker_nodes = [
            h for h in source_hosts if host_labels.get(h, {}).get("cmk/docker_object") == "node"
        ]

        content = []
        for host_name in docker_nodes:
            url = html.makeuri_contextless(
                [
                    ("view_name", "host"),
                    ("host", host_name),
                ],
                filename="view.py",
            )
            content.append(html.render_a(host_name, href=url))
        return "", HTML(", ").join(content)


def _get_host_labels():
    """Returns a map of all known hosts with their host labels

    It is important to cache this query per request and also try to use the
    liveproxyd query cached.
    """
    cache_id = "host_labels"
    if cache_id in current_app.g:
        return current_app.g[cache_id]

    query = "GET hosts\nColumns: name labels\nCache: reload\n"
    host_labels = {name: labels for name, labels in sites.live().query(query)}

    current_app.g[cache_id] = host_labels
    return host_labels


class AbstractPainterSpecificMetric(Painter):
    @property
    def ident(self):
        raise NotImplementedError()

    @property
    def title(self):
        return lambda p=None: self.title_with_parameters(p)

    @property
    def short_title(self):
        return lambda p=None: self.title_with_parameters(p)

    def title_with_parameters(self, parameters):
        try:
            if not parameters:
                # Used in Edit-View
                return "Show single metric"
            return metrics.metric_info[parameters["metric"]]["title"]
        except KeyError:
            return _("Metric not found")

    @property
    def columns(self):
        raise NotImplementedError()

    @property
    def parameters(self):
        cache_id = "painter_specific_metric_choices"
        if cache_id in current_app.g:
            choices = current_app.g[cache_id]
        else:
            choices = []
            for key, value in metrics.metric_info.iteritems():
                choices.append((key, value.get("title")))
            choices.sort(key=lambda x: x[1])
            current_app.g[cache_id] = choices

        return Dictionary(elements=[
            ("metric",
             DropdownChoice(title=_("Show metric"),
                            choices=choices,
                            help=_("If available, the following metric will be shown"))),
            ("column_title", TextAscii(title=_("Custom title"))),
        ],
                          optional_keys=["column_title"])

    def _render(self, row, cell, perf_data_entries, check_command):
        show_metric = cell.painter_parameters()["metric"]
        translated_metrics = metrics.translate_perf_data(perf_data_entries,
                                                         check_command=check_command)

        if show_metric not in translated_metrics:
            return "", ""

        return "", translated_metrics[show_metric]["unit"]["render"](
            translated_metrics[show_metric]["value"])


@painter_registry.register
class PainterHostSpecificMetric(AbstractPainterSpecificMetric):
    @property
    def ident(self):
        return "host_specific_metric"

    @property
    def columns(self):
        return ["host_perf_data", "host_check_command"]

    def render(self, row, cell):
        perf_data_entries = row["host_perf_data"]
        check_command = row["host_check_command"]
        return self._render(row, cell, perf_data_entries, check_command)


@painter_registry.register
class PainterServiceSpecificMetric(AbstractPainterSpecificMetric):
    @property
    def ident(self):
        return "service_specific_metric"

    @property
    def columns(self):
        return ["service_perf_data", "service_check_command"]

    def render(self, row, cell):
        perf_data_entries = row["service_perf_data"]
        check_command = row["service_check_command"]
        return self._render(row, cell, perf_data_entries, check_command)
