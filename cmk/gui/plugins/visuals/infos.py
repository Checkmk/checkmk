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

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    TextUnicode,
    Integer,
)

from cmk.gui.plugins.visuals import (
    VisualInfo,
    visual_info_registry,
)


@visual_info_registry.register
class VisualInfoHost(VisualInfo):
    @property
    def ident(self):
        return "host"

    @property
    def title(self):
        return _("Host")

    @property
    def title_plural(self):
        return _("Hosts")

    @property
    def single_spec(self):
        return [('host', TextUnicode(title=_('Hostname'),))]

    @property
    def multiple_site_filters(self):
        return ["hostgroup"]

    @property
    def sort_index(self):
        return 10


@visual_info_registry.register
class VisualInfoService(VisualInfo):
    @property
    def ident(self):
        return "service"

    @property
    def title(self):
        return _("Service")

    @property
    def title_plural(self):
        return _("Services")

    @property
    def single_spec(self):
        return [('service', TextUnicode(title=_('Service Description'),))]

    @property
    def multiple_site_filters(self):
        return ["servicegroup"]

    @property
    def sort_index(self):
        return 10


@visual_info_registry.register
class VisualInfoHostgroup(VisualInfo):
    @property
    def ident(self):
        return "hostgroup"

    @property
    def title(self):
        return _("Host Group")

    @property
    def title_plural(self):
        return _("Host Groups")

    @property
    def single_spec(self):
        return [('hostgroup', TextUnicode(title=_('Host Group Name'),))]

    @property
    def single_site(self):
        return False

    @property
    def sort_index(self):
        return 10


@visual_info_registry.register
class VisualInfoServicegroup(VisualInfo):
    @property
    def ident(self):
        return "servicegroup"

    @property
    def title(self):
        return _("Service Group")

    @property
    def title_plural(self):
        return _("Service Groups")

    @property
    def single_spec(self):
        return [
            ('servicegroup', TextUnicode(title=_('Service Group Name'),)),
        ]

    @property
    def single_site(self):
        return False

    @property
    def sort_index(self):
        return 10


@visual_info_registry.register
class VisualInfoLog(VisualInfo):
    @property
    def ident(self):
        return "log"

    @property
    def title(self):
        return _('Log Entry')

    @property
    def title_plural(self):
        return _('Log Entries')

    @property
    def single_spec(self):
        return


@visual_info_registry.register
class VisualInfoComment(VisualInfo):
    @property
    def ident(self):
        return "comment"

    @property
    def title(self):
        return _('Comment')

    @property
    def title_plural(self):
        return _('Comments')

    @property
    def single_spec(self):
        return [
            ('comment_id', Integer(title=_('Comment ID'),)),
        ]


@visual_info_registry.register
class VisualInfoDowntime(VisualInfo):
    @property
    def ident(self):
        return "downtime"

    @property
    def title(self):
        return _('Downtime')

    @property
    def title_plural(self):
        return _('Downtimes')

    @property
    def single_spec(self):
        return [
            ('downtime_id', Integer(title=_('Downtime ID'),)),
        ]


@visual_info_registry.register
class VisualInfoContact(VisualInfo):
    @property
    def ident(self):
        return "contact"

    @property
    def title(self):
        return _('Contact')

    @property
    def title_plural(self):
        return _('Contacts')

    @property
    def single_spec(self):
        return [
            ('log_contact_name', TextUnicode(title=_('Contact Name'),)),
        ]


@visual_info_registry.register
class VisualInfoCommand(VisualInfo):
    @property
    def ident(self):
        return "command"

    @property
    def title(self):
        return _('Command')

    @property
    def title_plural(self):
        return _('Commands')

    @property
    def single_spec(self):
        return [
            ('command_name', TextUnicode(title=_('Command Name'),)),
        ]


@visual_info_registry.register
class VisualInfoBIAggregation(VisualInfo):
    @property
    def ident(self):
        return "aggr"

    @property
    def title(self):
        return _('BI Aggregation')

    @property
    def title_plural(self):
        return _('BI Aggregations')

    @property
    def single_spec(self):
        return [
            ('aggr_name', TextUnicode(title=_('Aggregation Name'),)),
        ]

    @property
    def sort_index(self):
        return 20


@visual_info_registry.register
class VisualInfoBIAggregationGroup(VisualInfo):
    @property
    def ident(self):
        return "aggr_group"

    @property
    def title(self):
        return _('BI Aggregation Group')

    @property
    def title_plural(self):
        return _('BI Aggregation Groups')

    @property
    def single_spec(self):
        return [
            ('aggr_group', TextUnicode(title=_('Aggregation group'),)),
        ]

    @property
    def sort_index(self):
        return 20


@visual_info_registry.register
class VisualInfoDiscovery(VisualInfo):
    @property
    def ident(self):
        return "discovery"

    @property
    def title(self):
        return _('Discovery Output')

    @property
    def title_plural(self):
        return _('Discovery Outputs')

    @property
    def single_spec(self):
        return None


@visual_info_registry.register
class VisualInfoEvent(VisualInfo):
    @property
    def ident(self):
        return "event"

    @property
    def title(self):
        return _('Event Console Event')

    @property
    def title_plural(self):
        return _('Event Console Events')

    @property
    def single_spec(self):
        return [
            ('event_id', Integer(title=_('Event ID'),)),
        ]


@visual_info_registry.register
class VisualInfoEventHistory(VisualInfo):
    @property
    def ident(self):
        return "history"

    @property
    def title(self):
        return _('Historic Event Console Event')

    @property
    def title_plural(self):
        return _('Historic Event Console Events')

    @property
    def single_spec(self):
        return [
            ('event_id', Integer(title=_('Event ID'),)),
            ('history_line', Integer(title=_('History Line Number'),)),
        ]


@visual_info_registry.register
class VisualInfoCrash(VisualInfo):
    @property
    def ident(self):
        return "crash"

    @property
    def title(self):
        return _('Crash report')

    @property
    def title_plural(self):
        return _('Crash reports')

    @property
    def single_spec(self):
        return [
            ('crash_id', TextUnicode(title=_('Crash ID'),)),
        ]
