#!/usr/bin/env python
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

"""Modes for managing timeperiod definitions for the core"""

import re
import time

import cmk.defines as defines

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.userdb as userdb
import cmk.gui.table as table
import cmk.gui.forms as forms
import cmk.gui.plugins.wato.utils
import cmk.gui.wato.mkeventd
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    ID,
    FixedValue,
    Dictionary,
    Optional,
    Integer,
    FileUpload,
    TextAscii,
    TextUnicode,
    ListOf,
    Tuple,
    ValueSpec,
    TimeofdayRange,
    ListChoice,
    CascadingDropdown,
)

from cmk.gui.plugins.wato import (
    WatoMode,
    wato_confirm,
    global_buttons,
    mode_registry,
    make_action_link,
)


@mode_registry.register
class ModeTimeperiods(WatoMode):
    @classmethod
    def name(cls):
        return "timeperiods"


    @classmethod
    def permissions(cls):
        return ["timeperiods"]


    def __init__(self):
        super(ModeTimeperiods, self).__init__()
        self._timeperiods = watolib.load_timeperiods()


    def title(self):
        return _("Timeperiods")


    def buttons(self):
        global_buttons()
        html.context_button(_("New Timeperiod"), watolib.folder_preserving_link([("mode", "edit_timeperiod")]), "new")
        html.context_button(_("Import iCalendar"), watolib.folder_preserving_link([("mode", "import_ical")]), "ical")


    def action(self):
        delname = html.var("_delete")
        if delname and html.transaction_valid():
            usages = self._find_usages_of_timeperiod(delname)
            if usages:
                message = "<b>%s</b><br>%s:<ul>" % \
                            (_("You cannot delete this timeperiod."),
                             _("It is still in use by"))
                for title, link in usages:
                    message += '<li><a href="%s">%s</a></li>\n' % (link, title)
                message += "</ul>"
                raise MKUserError(None, message)

            c = wato_confirm(_("Confirm deletion of time period %s") % delname,
                  _("Do you really want to delete the time period '%s'? I've checked it: "
                    "it is not being used by any rule or user profile right now.") % delname)
            if c:
                del self._timeperiods[delname]
                watolib.save_timeperiods(self._timeperiods)
                watolib.add_change("edit-timeperiods", _("Deleted timeperiod %s") % delname)
            elif c == False:
                return ""


    # Check if a timeperiod is currently in use and cannot be deleted
    # Returns a list of two element tuples (title, url) that refer to the single occurrances.
    #
    # Possible usages:
    # - 1. rules: service/host-notification/check-period
    # - 2. user accounts (notification period)
    # - 3. excluded by other timeperiods
    # - 4. timeperiod condition in notification and alerting rules
    # - 5. bulk operation in notification rules
    # - 6. timeperiod condition in EC rules
    # - 7. rules: time specific parameters
    def _find_usages_of_timeperiod(self, tpname):
        used_in = []
        used_in += self._find_usages_in_host_and_service_rules(tpname)
        used_in += self._find_usages_in_users(tpname)
        used_in += self._find_usages_in_other_timeperiods(tpname)
        used_in += self._find_usages_in_notification_rules(tpname)
        used_in += self._find_usages_in_alert_handler_rules(tpname)
        used_in += self._find_usages_in_ec_rules(tpname)
        used_in += self._find_usages_in_time_specific_parameters(tpname)
        return used_in


    def _find_usages_in_host_and_service_rules(self, tpname):
        used_in = []
        rulesets = watolib.AllRulesets()
        rulesets.load()

        for varname, ruleset in rulesets.get_rulesets().items():
            if not isinstance(ruleset.valuespec(), watolib.TimeperiodSelection):
                continue

            for _folder, _rulenr, rule in ruleset.get_rules():
                if rule.value == tpname:
                    used_in.append(("%s: %s" % (_("Ruleset"), ruleset.title()),
                                   watolib.folder_preserving_link([("mode", "edit_ruleset"), ("varname", varname)])))
                    break

        return used_in


    def _find_usages_in_users(self, tpname):
        used_in = []
        for userid, user in userdb.load_users().items():
            tp = user.get("notification_period")
            if tp == tpname:
                used_in.append(("%s: %s" % (_("User"), userid),
                    watolib.folder_preserving_link([("mode", "edit_user"), ("edit", userid)])))

            for index, rule in enumerate(user.get("notification_rules", [])):
                used_in += self._find_usages_in_notification_rule(tpname, index, rule, user_id=userid)
        return used_in


    def _find_usages_in_other_timeperiods(self, tpname):
        used_in = []
        for tpn, tp in watolib.load_timeperiods().items():
            if tpname in tp.get("exclude", []):
                used_in.append(("%s: %s (%s)" % (_("Timeperiod"), tp.get("alias", tpn),
                        _("excluded")),
                        watolib.folder_preserving_link([("mode", "edit_timeperiod"), ("edit", tpn)])))
        return used_in


    def _find_usages_in_notification_rules(self, tpname):
        used_in = []
        for index, rule in enumerate(watolib.load_notification_rules()):
            used_in += self._find_usages_in_notification_rule(tpname, index, rule)
        return used_in


    def _find_usages_in_notification_rule(self, tpname, index, rule, user_id=None):
        used_in = []

        if self._used_in_tp_condition(rule, tpname) or self._used_in_bulking(rule, tpname):
            url = watolib.folder_preserving_link([("mode", "notification_rule"), ("edit", index), ("user", user_id)])
            if user_id:
                title = _("Notification rule of user '%s'") % user_id
            else:
                title = _("Notification rule")

            used_in.append((title, url))

        return used_in


    def _used_in_tp_condition(self, rule, tpname):
        return rule.get("match_timeperiod") == tpname


    def _used_in_bulking(self, rule, tpname):
        bulk = rule.get("bulk")
        if isinstance(bulk, tuple):
            method, params = bulk
            return method == "timeperiod" and params["timeperiod"] == tpname
        return False


    def _find_usages_in_alert_handler_rules(self, tpname):
        used_in = []

        if cmk.is_raw_edition():
            return used_in

        try:
            import cmk.gui.cee.plugins.wato.alert_handling as alert_handling
        except:
            alert_handling = None

        for index, rule in enumerate(alert_handling.load_alert_handler_rules()):
            if rule.get("match_timeperiod") == tpname:
                url = watolib.folder_preserving_link([("mode", "alert_handler_rule"), ("edit", index)])
                used_in.append((_("Alert handler rule"), url))
        return used_in


    def _find_usages_in_ec_rules(self, tpname):
        used_in = []
        rule_packs = cmk.gui.wato.mkeventd.load_mkeventd_rules()
        for rule_pack in rule_packs:
            for rule_index, rule in enumerate(rule_pack["rules"]):
                if rule.get("match_timeperiod") == tpname:
                    url = watolib.folder_preserving_link([("mode", "mkeventd_edit_rule"),
                                                          ("edit", rule_index),
                                                          ("rule_pack", rule_pack["id"])])
                    used_in.append((_("Event console rule"), url))
        return used_in


    def _find_usages_in_time_specific_parameters(self, tpname):
        used_in = []
        rulesets = watolib.AllRulesets()
        rulesets.load()
        for ruleset in rulesets.get_rulesets().values():
            vs = ruleset.valuespec()
            if not isinstance(vs, cmk.gui.plugins.wato.utils.TimeperiodValuespec):
                continue

            for rule_folder, rule_index, rule in ruleset.get_rules():
                if not vs.is_active(rule.value):
                    continue

                for index, (rule_tp_name, _value) in enumerate(rule.value["tp_values"]):
                    if rule_tp_name != tpname:
                        continue

                    edit_url = watolib.folder_preserving_link([
                        ("mode", "edit_rule"),
                        ("back_mode", "timeperiods"),
                        ("varname", ruleset.name),
                        ("rulenr", rule_index),
                        ("rule_folder", rule_folder.path()),
                    ])
                    used_in.append((_("Time specific check parameter #%d") % (index + 1), edit_url))

        return used_in


    def page(self):
        table.begin("timeperiods", empty_text = _("There are no timeperiods defined yet."))
        for name in sorted(self._timeperiods.keys()):
            table.row()

            timeperiod = self._timeperiods[name]
            edit_url     = watolib.folder_preserving_link([("mode", "edit_timeperiod"), ("edit", name)])
            clone_url    = watolib.folder_preserving_link([("mode", "edit_timeperiod"), ("clone", name)])
            delete_url   = make_action_link([("mode", "timeperiods"), ("_delete", name)])

            table.cell(_("Actions"), css="buttons")
            html.icon_button(edit_url, _("Properties"), "edit")
            html.icon_button(clone_url, _("Create a copy"), "clone")
            html.icon_button(delete_url, _("Delete"), "delete")

            table.text_cell(_("Name"), name)
            table.text_cell(_("Alias"), timeperiod.get("alias", ""))
        table.end()



# TODO: Deprecated and Replace with ListOf(TimeofdayRange(), ...)
class MultipleTimeRanges(ValueSpec):
    def __init__(self, **kwargs):
        ValueSpec.__init__(self, **kwargs)
        self._num_columns = kwargs.get("num_columns", 3)
        self._rangevs = TimeofdayRange()

    def canonical_value(self):
        return [ ((0,0), (24,0)), None, None ]

    def render_input(self, varprefix, value):
        for c in range(0, self._num_columns):
            if c:
                html.write(" &nbsp; ")
            if c < len(value):
                v = value[c]
            else:
                v = self._rangevs.canonical_value()
            self._rangevs.render_input(varprefix + "_%d" % c, v)

    def value_to_text(self, value):
        parts = []
        for v in value:
            parts.append(self._rangevs.value_to_text(v))
        return ", ".join(parts)

    def from_html_vars(self, varprefix):
        value = []
        for c in range(0, self._num_columns):
            v = self._rangevs.from_html_vars(varprefix + "_%d" % c)
            if v != None:
                value.append(v)
        return value

    def validate_value(self, value, varprefix):
        for c, v in enumerate(value):
            self._rangevs.validate_value(v, varprefix + "_%d" % c)
        ValueSpec.custom_validate(self, value, varprefix)


# Displays a dialog for uploading an ical file which will then
# be used to generate timeperiod exceptions etc. and then finally
# open the edit_timeperiod page to create a new timeperiod using
# these information
@mode_registry.register
class ModeTimeperiodImportICal(WatoMode):
    @classmethod
    def name(cls):
        return "import_ical"


    @classmethod
    def permissions(cls):
        return ["timeperiods"]


    def title(self):
        return _("Import iCalendar File to create a Timeperiod")


    def buttons(self):
        html.context_button(_("All Timeperiods"),
            watolib.folder_preserving_link([("mode", "timeperiods")]), "back")


    def _vs_ical(self):
        return Dictionary(
            title = _('Import iCalendar File'),
            render = "form",
            optional_keys = None,
            elements = [
                ('file', FileUpload(
                    title = _('iCalendar File'),
                    help = _("Select an iCalendar file (<tt>*.ics</tt>) from your PC"),
                    allow_empty = False,
                    custom_validate = self._validate_ical_file,
                )),
                ('horizon', Integer(
                    title = _('Time horizon for repeated events'),
                    help = _("When the iCalendar file contains definitions of repeating events, these repeating "
                             "events will be resolved to single events for the number of years you specify here."),
                    minvalue = 0,
                    maxvalue = 50,
                    default_value = 10,
                    unit = _('years'),
                    allow_empty = False,
                )),
                ('times', Optional(
                    MultipleTimeRanges(
                        default_value = [None, None, None],
                    ),
                    title = _('Use specific times'),
                    label = _('Use specific times instead of whole day'),
                    help = _("When you specify explicit time definitions here, these will be added to each "
                             "date which is added to the resulting time period. By default the whole day is "
                             "used."),
                )),
            ]
        )


    def _validate_ical_file(self, value, varprefix):
        filename, _ty, content = value
        if not filename.endswith('.ics'):
            raise MKUserError(varprefix, _('The given file does not seem to be a valid iCalendar file. '
                                           'It needs to have the file extension <tt>.ics</tt>.'))

        if not content.startswith('BEGIN:VCALENDAR'):
            raise MKUserError(varprefix, _('The file does not seem to be a valid iCalendar file.'))

        if not content.startswith('END:VCALENDAR'):
            raise MKUserError(varprefix, _('The file does not seem to be a valid iCalendar file.'))


    def action(self):
        if not html.check_transaction():
            return

        vs_ical = self._vs_ical()
        ical = vs_ical.from_html_vars("ical")
        vs_ical.validate_value(ical, "ical")

        filename, _ty, content = ical['file']

        try:
            data = self._parse_ical(content, ical['horizon'])
        except Exception, e:
            if config.debug:
                raise
            raise MKUserError('ical_file', _('Failed to parse file: %s') % e)

        html.set_var('alias', data.get('descr', data.get('name', filename)))

        for day in defines.weekday_ids():
            html.set_var('%s_0_from' % day, '')
            html.set_var('%s_0_until' % day, '')

        html.set_var('except_count', "%d" % len(data['events']))
        for index, event in enumerate(data['events']):
            index += 1
            html.set_var('except_%d_0' % index, event['date'])
            html.set_var('except_indexof_%d' % index, "%d" % index)

            if ical["times"]:
                for n, time_spec in enumerate(ical["times"]):
                    start_time = ":".join("%02d" % x for x in time_spec[0])
                    end_time   = ":".join("%02d" % x for x in time_spec[1])
                    html.set_var('except_%d_1_%d_from' % (index, n), start_time)
                    html.set_var('except_%d_1_%d_until' % (index, n), end_time)

        return "edit_timeperiod"


    # Returns a dictionary in the format:
    # {
    #   'name'   : '...',
    #   'descr'  : '...',
    #   'events' : [
    #       {
    #           'name': '...',
    #           'date': '...',
    #       },
    #   ],
    # }
    #
    # Relevant format specifications:
    #   http://tools.ietf.org/html/rfc2445
    #   http://tools.ietf.org/html/rfc5545
    # TODO: Let's use some sort of standard module in the future. Maybe we can then also handle
    # times instead of only full day events.
    def _parse_ical(self, ical_blob, horizon=10):
        ical = {'raw_events': []}

        def get_params(key):
            if ';' in key:
                return dict([ p.split('=', 1) for p in key.split(';')[1:] ])
            return {}

        def parse_date(params, val):
            # First noprmalize the date value to make it easier parsable later
            if 'T' not in val and params.get('VALUE') == 'DATE':
                val += 'T000000' # add 00:00:00 to date specification

            return list(time.strptime(val, '%Y%m%dT%H%M%S'))

        # First extract the relevant information from the file
        in_event = False
        event    = {}
        for l in ical_blob.split('\n'):
            line = l.strip()
            if not line:
                continue
            try:
                key, val = line.split(':', 1)
            except ValueError:
                raise Exception('Failed to parse line: %r' % line)

            if key == 'X-WR-CALNAME':
                ical['name'] = val
            elif key == 'X-WR-CALDESC':
                ical['descr'] = val

            elif line == 'BEGIN:VEVENT':
                in_event = True
                event = {} # create new event

            elif line == 'END:VEVENT':
                # Finish the current event
                ical['raw_events'].append(event)
                in_event = False

            elif in_event:
                if key.startswith('DTSTART'):
                    params = get_params(key)
                    event['start'] = parse_date(params, val)

                elif key.startswith('DTEND'):
                    params = get_params(key)
                    event['end'] = parse_date(params, val)

                elif key == 'RRULE':
                    event['recurrence'] = dict([ p.split('=', 1) for p in val.split(';') ])

                elif key == 'SUMMARY':
                    event['name'] = val

        def next_occurrence(start, now, freq):
            # convert struct_time to list to be able to modify it,
            # then set it to the next occurence
            t = start[:]

            if freq == 'YEARLY':
                t[0] = now[0]+1 # add 1 year
            elif freq == 'MONTHLY':
                if now[1] + 1 > 12:
                    t[0] = now[0]+1
                    t[1] = now[1] + 1 - 12
                else:
                    t[0] = now[0]
                    t[1] = now[1] + 1
            else:
                raise Exception('The frequency "%s" is currently not supported' % freq)
            return t

        def resolve_multiple_days(event, cur_start_time):
            if time.strftime('%Y-%m-%d', cur_start_time) \
                == time.strftime('%Y-%m-%d', event["end"]):
                # Simple case: a single day event
                return [{
                    'name'  : event['name'],
                    'date'  : time.strftime('%Y-%m-%d', cur_start_time),
                }]

            # Resolve multiple days
            resolved, cur_timestamp, day = [], time.mktime(cur_start_time), 1
            # day < 100 is just some plausibilty check. In case such an event
            # is needed eventually remove this
            while cur_timestamp < time.mktime(event["end"]) and day < 100:
                resolved.append({
                    "name" : "%s %s" % (event["name"], _(" (day %d)") % day),
                    "date" : time.strftime("%Y-%m-%d", time.localtime(cur_timestamp)),
                })
                cur_timestamp += 86400
                day += 1

            return resolved

        # Now resolve recurring events starting from 01.01 of current year
        # Non-recurring events are simply copied
        resolved = []
        now  = list(time.strptime(str(time.localtime().tm_year-1), "%Y"))
        last = now[:]
        last[0] += horizon+1 # update year to horizon
        for event in ical['raw_events']:
            if 'recurrence' in event and event['start'] < now:
                rule     = event['recurrence']
                freq     = rule['FREQ']
                cur      = now
                while cur < last:
                    cur = next_occurrence(event['start'], cur, freq)
                    resolved += resolve_multiple_days(event, cur)
            else:
                resolved += resolve_multiple_days(event, event["start"])

        ical['events'] = sorted(resolved)

        return ical


    def page(self):
        html.p(_('This page can be used to generate a new timeperiod definition based '
                 'on the appointments of an iCalendar (<tt>*.ics</tt>) file. This import is normally used '
                 'to import events like holidays, therefore only single whole day appointments are '
                 'handled by this import.'))

        html.begin_form("import_ical", method="POST")
        self._vs_ical().render_input("ical", {})
        forms.end()
        html.button("upload", _("Import"))
        html.hidden_fields()
        html.end_form()



@mode_registry.register
class ModeEditTimeperiod(WatoMode):
    @classmethod
    def name(cls):
        return "edit_timeperiod"


    @classmethod
    def permissions(cls):
        return ["timeperiods"]


    def _from_vars(self):
        self._timeperiods = watolib.load_timeperiods()
        self._name = html.var("edit") # missing -> new group
        self._new  = self._name == None

        if self._new:
            clone_name = html.var("clone")
            if clone_name:
                self._name = clone_name

                self._timeperiod = self._get_timeperiod(self._name)
            else:
                # initialize with 24x7 config
                self._timeperiod = {
                    day: [("00:00", "24:00")] for day in defines.weekday_ids()
                }
        else:
            self._timeperiod = self._get_timeperiod(self._name)


    def _get_timeperiod(self, name):
        try:
            return self._timeperiods[name]
        except KeyError:
            raise MKUserError(None, _("This timeperiod does not exist."))


    def title(self):
        if self._new:
            return _("Create new time period")
        else:
            return _("Edit time period")


    def buttons(self):
        html.context_button(_("All Timeperiods"), watolib.folder_preserving_link([("mode", "timeperiods")]), "back")


    def _valuespec(self):
        if self._new:
            # Cannot use ID() here because old versions of the GUI allowed time periods to start
            # with numbers and so on. The ID() valuespec does not allow it.
            name_element = TextAscii(
                title = _("Internal ID"),
                regex = r"^[-a-z0-9A-Z_]*$",
                regex_error = _("Invalid timeperiod name. Only the characters a-z, A-Z, 0-9, "
                                "_ and - are allowed."),
                allow_empty = False,
                size = 80,
                validate = self._validate_id,
            )
        else:
            name_element = FixedValue(
                self._name,
            )

        return Dictionary(
            title = _("Timeperiod"),
            elements = [
                ("name", name_element),
                ("alias", TextUnicode(
                    title = _("Alias"),
                    help = _("An alias or description of the timeperiod"),
                    allow_empty = False,
                    size = 80,
                    validate = self._validate_alias,
                )),
                ("weekdays", self._vs_weekdays()),
                ("exceptions", self._vs_exceptions()),
                ("exclude", self._vs_exclude()),
            ],
            render = "form",
            optional_keys = None,
        )


    def _validate_id(self, value, varprefix):
        if value in self._timeperiods:
            raise MKUserError(varprefix, _("This name is already being used by another timeperiod."))
        if value == "24X7":
            raise MKUserError(varprefix, _("The time period name 24X7 cannot be used. It is always autmatically defined."))


    def _validate_alias(self, value, varprefix):
        unique, message = watolib.is_alias_used("timeperiods", self._name, value)
        if not unique:
            raise MKUserError("alias", message)


    def _vs_weekdays(self):
        return CascadingDropdown(
            title = _("Active time range"),
            help = _("For each weekday you can setup no, one or several "
                     "time ranges in the format <tt>23:39</tt>, in which the time period "
                     "should be active."),
            choices = [
                ("whole_week", _("Same times for all weekdays"), MultipleTimeRanges(
                )),
                ("day_specific", _("Weekday specific times"), Dictionary(
                    elements = self._weekday_elements(),
                    optional_keys = None,
                    indent = False,
                )),
            ],
        )


    def _weekday_elements(self):
        elements = []
        for tp_id, tp_title in cmk.defines.weekdays_by_name():
            # TODO: Find way to render without line breaks between day and ranges
            elements.append((tp_id, MultipleTimeRanges(
                title=tp_title
            )))
            #elements.append((tp_id, ListOf(TimeofdayRange(),
            #    title = tp_title,
            #    movable = False,
            #    add_label = _("Add time range"),
            #    del_label = _("Delete time range"),
            #)))
        return elements


    def _vs_exceptions(self):
        return ListOf(
            Tuple(
                orientation = "horizontal",
                show_titles = False,
                elements = [
                    TextAscii(
                        regex = "^[-a-z0-9A-Z /]*$",
                        regex_error = _("This is not a valid Nagios timeperiod day specification."),
                        allow_empty = False,
                        validate = self._validate_timeperiod_exception,
                    ),
                    MultipleTimeRanges()
                ],
            ),
            title = _("Exceptions (from weekdays)"),
            help = _("Here you can specify exceptional time ranges for certain "
                     "dates in the form YYYY-MM-DD which are used to define more "
                     "specific definitions to override the times configured for the matching "
                     "weekday."),
            movable = False,
            add_label = _("Add Exception"),
        )


    def _validate_timeperiod_exception(self, value, varprefix):
        if value in defines.weekday_ids():
            raise MKUserError(varprefix, _("You cannot use weekday names (%s) in exceptions") % value)

        if value in [ "name", "alias", "timeperiod_name", "register", "use", "exclude" ]:
            raise MKUserError(varprefix, _("<tt>%s</tt> is a reserved keyword."))


    def _vs_exclude(self):
        return ListChoice(
            choices=self._other_timeperiod_choices(),
            title = _("Exclude"),
            help = _('You can use other timeperiod definitions to exclude the times '
                     'defined in the other timeperiods from this current timeperiod.'),
        )


    def _other_timeperiod_choices(self):
        """List of timeperiods that can be used for exclusions

        We offer the list of all other timeperiods - but only those that do not exclude the current
        timeperiod (in order to avoid cycles)"""
        other_tps = []
        for tpname, tp in self._timeperiods.items():
            if not self._timeperiod_excludes(tpname):
                other_tps.append((tpname, tp.get("alias") or tpname))
        return other_tps


    def _timeperiod_excludes(self, tpa_name):
        """Check, if timeperiod tpa excludes or is tpb"""
        if tpa_name == self._name:
            return True

        tpa = self._timeperiods[tpa_name]
        for ex in tpa.get("exclude", []):
            if ex == self._name:
                return True

            if self._timeperiod_excludes(ex):
                return True

        return False


    def action(self):
        if not html.check_transaction():
            return

        vs = self._valuespec()
        vs_spec = vs.from_html_vars("timeperiod")
        vs.validate_value(vs_spec, "timeperiod")
        self._timeperiod = self._from_valuespec(vs_spec)

        if self._new:
            self._name = vs_spec["name"]
            watolib.add_change("edit-timeperiods", _("Created new time period %s") % self._name)
        else:
            watolib.add_change("edit-timeperiods", _("Modified time period %s") % self._name)

        self._timeperiods[self._name] = self._timeperiod
        watolib.save_timeperiods(self._timeperiods)
        return "timeperiods"


    def page(self):
        html.begin_form("timeperiod", method="POST")
        self._valuespec().render_input("timeperiod", self._to_valuespec(self._timeperiod))
        forms.end()
        html.button("save", _("Save"))
        html.hidden_fields()
        html.end_form()


    # The timeperiod data structure for the Check_MK config looks like follows.
    # { 'alias': u'eeee',
    #   'monday': [('00:00', '22:00')],
    #   'tuesday': [('00:00', '24:00')],
    #   'wednesday': [('00:00', '24:00')],
    #   'thursday': [('00:00', '24:00')],
    #   'friday': [('00:00', '24:00')],
    #   'saturday': [('00:00', '24:00')],
    #   'sunday': [('00:00', '24:00')],
    #   'exclude': ['asde'],
    #   # These are the exceptions:
    #   '2018-01-28': [
    #       ('00:00', '10:00')
    #   ],
    # ]}}
    def _to_valuespec(self, tp_spec):
        if not tp_spec:
            return {}

        exceptions = []
        for exception_name, time_ranges in tp_spec.items():
            if exception_name not in defines.weekday_ids() + [ "alias", "exclude" ]:
                exceptions.append((exception_name, map(self._time_range_to_valuespec, time_ranges)))

        vs_spec = {
            "name": self._name,
            "alias": tp_spec.get("alias", ""),
            "weekdays": self._weekdays_to_valuespec(tp_spec),
            "exclude": tp_spec.get("exclude", []),
            "exceptions": sorted(exceptions),
        }

        return vs_spec


    def _weekdays_to_valuespec(self, tp_spec):
        if self._has_same_time_specs_during_whole_week(tp_spec):
            return ("whole_week", map(self._time_range_to_valuespec, tp_spec.get("monday", [])))

        return ("day_specific", { day: map(self._time_range_to_valuespec, tp_spec.get(day, []))
                                  for day in defines.weekday_ids() })


    def _has_same_time_specs_during_whole_week(self, tp_spec):
        """Put the time ranges of all weekdays into a set to reduce the duplicates to see whether
        or not all days have the same time spec and return True if they have the same."""
        unified_time_ranges = set([ tuple(tp_spec.get(day, []))
                                    for day in defines.weekday_ids() ])
        return len(unified_time_ranges) == 1


    def _time_range_to_valuespec(self, time_range):
        """Convert a time range specification to valuespec format
        e.g. ("00:30", "10:17") -> ((0,30),(10,17))"""
        return tuple(map(self._time_to_valuespec, time_range))


    def _time_to_valuespec(self, time_str):
        """Convert a time specification to valuespec format
        e.g. "00:30" -> (0, 30)"""
        return tuple(map(int, time_str.split(":")))


    def _from_valuespec(self, vs_spec):
        tp_spec = {
            "alias": vs_spec["alias"],
        }

        if vs_spec["exclude"]:
            tp_spec["exclude"] = vs_spec["exclude"]

        tp_spec.update(self._exceptions_from_valuespec(vs_spec))
        tp_spec.update(self._weekdays_from_valuespec(vs_spec))

        return tp_spec


    def _exceptions_from_valuespec(self, vs_spec):
        tp_spec = {}
        for exception_name, time_ranges in vs_spec["exceptions"]:
            if time_ranges:
                tp_spec[exception_name] = map(self._time_range_from_valuespec, time_ranges)
        return tp_spec


    def _weekdays_from_valuespec(self, vs_spec):
        weekday_ty, weekday_values = vs_spec["weekdays"]

        if weekday_ty == "whole_week":
            # produce a data structure equal to the "day_specific" structure
            weekday_values = { day: weekday_values for day in defines.weekday_ids() }

        elif weekday_ty != "day_specific":
            raise NotImplementedError()

        tp_spec = {}
        for day in defines.weekday_ids():
            time_specs = map(self._time_range_from_valuespec, weekday_values[day])
            if time_specs:
                tp_spec[day] = time_specs
        return tp_spec


    def _time_range_from_valuespec(self, value):
        """Convert a time range specification from valuespec format"""
        return tuple(map(self._time_from_valuespec, value))


    def _time_from_valuespec(self, value):
        """Convert a time specification from valuespec format"""
        return "%02d:%02d" % value
