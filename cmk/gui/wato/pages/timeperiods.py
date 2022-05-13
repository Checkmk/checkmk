#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Modes for managing timeperiod definitions for the core"""

import time
from typing import Any, Dict, List
from typing import Optional as _Optional
from typing import Tuple as _Tuple
from typing import Type

import cmk.utils.defines as defines
import cmk.utils.version as cmk_version
from cmk.utils.type_defs import EventRule, timeperiod_spec_alias, UserId

import cmk.gui.forms as forms
import cmk.gui.plugins.wato.utils
import cmk.gui.userdb as userdb
import cmk.gui.wato.mkeventdstore as mkeventdstore
import cmk.gui.watolib as watolib
import cmk.gui.watolib.changes as _changes
import cmk.gui.watolib.groups as groups
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request, UploadedFile
from cmk.gui.i18n import _
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.plugins.wato.utils import (
    make_confirm_link,
    mode_registry,
    mode_url,
    redirect,
    WatoMode,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    FileUpload,
    FixedValue,
    Integer,
    ListChoice,
    ListOf,
    ListOfTimeRanges,
    Optional,
    TextInput,
    Tuple,
    ValueSpec,
)
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link
from cmk.gui.watolib.notifications import load_notification_rules
from cmk.gui.watolib.rulesets import AllRulesets

TimeperiodUsage = _Tuple[str, str]

try:
    import cmk.gui.cee.plugins.wato.alert_handling as alert_handling
except ImportError:
    alert_handling = None  # type: ignore[assignment]


@mode_registry.register
class ModeTimeperiods(WatoMode):
    @classmethod
    def name(cls):
        return "timeperiods"

    @classmethod
    def permissions(cls):
        return ["timeperiods"]

    def __init__(self):
        super().__init__()
        self._timeperiods = watolib.timeperiods.load_timeperiods()

    def title(self):
        return _("Time periods")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="timeperiods",
                    title=_("Time periods"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add time period"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add time period"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "edit_timeperiod")])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                                PageMenuEntry(
                                    title=_("Import iCalendar"),
                                    icon_name="ical",
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "import_ical")])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

    def action(self) -> ActionResult:
        delname = request.var("_delete")
        if not delname:
            return redirect(mode_url("timeperiods"))

        if not transactions.check_transaction():
            return redirect(mode_url("timeperiods"))

        if delname in watolib.timeperiods.builtin_timeperiods():
            raise MKUserError("_delete", _("Builtin timeperiods can not be modified"))

        usages = self._find_usages_of_timeperiod(delname)
        if usages:
            message = "<b>%s</b><br>%s:<ul>" % (
                _("You cannot delete this timeperiod."),
                _("It is still in use by"),
            )
            for title, link in usages:
                message += '<li><a href="%s">%s</a></li>\n' % (link, title)
            message += "</ul>"
            raise MKUserError(None, message)

        del self._timeperiods[delname]
        watolib.timeperiods.save_timeperiods(self._timeperiods)
        _changes.add_change("edit-timeperiods", _("Deleted timeperiod %s") % delname)
        return redirect(mode_url("timeperiods"))

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
    def _find_usages_of_timeperiod(self, tpname: str) -> List[TimeperiodUsage]:
        used_in: List[TimeperiodUsage] = []
        used_in += self._find_usages_in_host_and_service_rules(tpname)
        used_in += self._find_usages_in_users(tpname)
        used_in += self._find_usages_in_other_timeperiods(tpname)
        used_in += self._find_usages_in_notification_rules(tpname)
        used_in += self._find_usages_in_alert_handler_rules(tpname)
        used_in += self._find_usages_in_ec_rules(tpname)
        used_in += self._find_usages_in_time_specific_parameters(tpname)
        return used_in

    def _find_usages_in_host_and_service_rules(self, tpname: str) -> List[TimeperiodUsage]:
        used_in: List[TimeperiodUsage] = []
        rulesets = AllRulesets()
        rulesets.load()
        for varname, ruleset in rulesets.get_rulesets().items():
            if not isinstance(ruleset.valuespec(), watolib.timeperiods.TimeperiodSelection):
                continue

            for _folder, _rulenr, rule in ruleset.get_rules():
                if rule.value == tpname:
                    used_in.append(
                        (
                            "%s: %s" % (_("Ruleset"), ruleset.title()),
                            folder_preserving_link(
                                [("mode", "edit_ruleset"), ("varname", varname)]
                            ),
                        )
                    )
                    break
        return used_in

    def _find_usages_in_users(self, tpname: str) -> List[TimeperiodUsage]:
        used_in: List[TimeperiodUsage] = []
        for userid, user in userdb.load_users().items():
            tp = user.get("notification_period")
            if tp == tpname:
                used_in.append(
                    (
                        "%s: %s" % (_("User"), userid),
                        folder_preserving_link([("mode", "edit_user"), ("edit", userid)]),
                    )
                )

            for index, rule in enumerate(user.get("notification_rules", [])):
                used_in += self._find_usages_in_notification_rule(
                    tpname, index, rule, user_id=userid
                )
        return used_in

    def _find_usages_in_other_timeperiods(self, tpname: str) -> List[TimeperiodUsage]:
        used_in: List[TimeperiodUsage] = []
        for tpn, tp in watolib.timeperiods.load_timeperiods().items():
            if tpname in tp.get("exclude", []):
                used_in.append(
                    (
                        "%s: %s (%s)"
                        % (_("Timeperiod"), timeperiod_spec_alias(tp, tpn), _("excluded")),
                        folder_preserving_link([("mode", "edit_timeperiod"), ("edit", tpn)]),
                    )
                )
        return used_in

    def _find_usages_in_notification_rules(self, tpname: str) -> List[TimeperiodUsage]:
        used_in: List[TimeperiodUsage] = []
        for index, rule in enumerate(load_notification_rules()):
            used_in += self._find_usages_in_notification_rule(tpname, index, rule)
        return used_in

    def _find_usages_in_notification_rule(
        self, tpname: str, index: int, rule: EventRule, user_id: _Optional[UserId] = None
    ) -> List[TimeperiodUsage]:
        used_in: List[TimeperiodUsage] = []
        if self._used_in_tp_condition(rule, tpname) or self._used_in_bulking(rule, tpname):
            url = folder_preserving_link(
                [
                    ("mode", "notification_rule"),
                    ("edit", index),
                    ("user", user_id),
                ]
            )
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

    def _find_usages_in_alert_handler_rules(self, tpname: str) -> List[TimeperiodUsage]:
        used_in: List[TimeperiodUsage] = []
        if cmk_version.is_raw_edition():
            return used_in
        for index, rule in enumerate(alert_handling.load_alert_handler_rules()):
            if rule.get("match_timeperiod") == tpname:
                url = folder_preserving_link(
                    [
                        ("mode", "alert_handler_rule"),
                        ("edit", index),
                    ]
                )
                used_in.append((_("Alert handler rule"), url))
        return used_in

    def _find_usages_in_ec_rules(self, tpname: str) -> List[TimeperiodUsage]:
        used_in: List[TimeperiodUsage] = []
        rule_packs = mkeventdstore.load_mkeventd_rules()
        for rule_pack in rule_packs:
            for rule_index, rule in enumerate(rule_pack["rules"]):
                if rule.get("match_timeperiod") == tpname:
                    url = folder_preserving_link(
                        [
                            ("mode", "mkeventd_edit_rule"),
                            ("edit", rule_index),
                            ("rule_pack", rule_pack["id"]),
                        ]
                    )
                    used_in.append((_("Event console rule"), url))
        return used_in

    def _find_usages_in_time_specific_parameters(self, tpname: str) -> List[TimeperiodUsage]:
        used_in: List[TimeperiodUsage] = []
        rulesets = AllRulesets()
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
                    edit_url = folder_preserving_link(
                        [
                            ("mode", "edit_rule"),
                            ("back_mode", "timeperiods"),
                            ("varname", ruleset.name),
                            ("rulenr", rule_index),
                            ("rule_folder", rule_folder.path()),
                        ]
                    )
                    used_in.append((_("Time specific check parameter #%d") % (index + 1), edit_url))
        return used_in

    def page(self):
        with table_element(
            "timeperiods", empty_text=_("There are no timeperiods defined yet.")
        ) as table:
            for name, timeperiod in sorted(self._timeperiods.items()):
                table.row()

                table.cell(_("Actions"), css="buttons")
                if name in watolib.timeperiods.builtin_timeperiods():
                    html.i(_("(builtin)"))
                else:
                    self._action_buttons(name)

                table.cell(_("Name"), name)
                table.cell(_("Alias"), timeperiod_spec_alias(timeperiod))

    def _action_buttons(self, name):
        edit_url = folder_preserving_link(
            [
                ("mode", "edit_timeperiod"),
                ("edit", name),
            ]
        )
        clone_url = folder_preserving_link(
            [
                ("mode", "edit_timeperiod"),
                ("clone", name),
            ]
        )
        delete_url = make_confirm_link(
            url=make_action_link(
                [
                    ("mode", "timeperiods"),
                    ("_delete", name),
                ]
            ),
            message=_("Do you really want to delete the time period '%s'?") % name,
        )

        html.icon_button(edit_url, _("Properties"), "edit")
        html.icon_button(clone_url, _("Create a copy"), "clone")
        html.icon_button(delete_url, _("Delete"), "delete")


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

    @classmethod
    def parent_mode(cls) -> _Optional[Type[WatoMode]]:
        return ModeTimeperiods

    def title(self):
        if html.request.var("upload"):
            return _("Add time period")
        return _("Import iCalendar File to create a time period")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        if not html.request.var("upload"):
            return make_simple_form_page_menu(
                _("iCalendar"),
                breadcrumb,
                form_name="import_ical",
                button_name="upload",
                save_title=_("Import"),
            )
        return ModeEditTimeperiod().page_menu(breadcrumb)

    def _vs_ical(self):
        return Dictionary(
            title=_("Import iCalendar File"),
            render="form",
            optional_keys=False,
            elements=[
                (
                    "file",
                    FileUpload(
                        title=_("iCalendar File"),
                        help=_("Select an iCalendar file (<tt>*.ics</tt>) from your PC"),
                        validate=self._validate_ical_file,
                    ),
                ),
                (
                    "horizon",
                    Integer(
                        title=_("Time horizon for repeated events"),
                        help=_(
                            "When the iCalendar file contains definitions of repeating events, these repeating "
                            "events will be resolved to single events for the number of years you specify here."
                        ),
                        minvalue=0,
                        maxvalue=50,
                        default_value=10,
                        unit=_("years"),
                    ),
                ),
                (
                    "times",
                    Optional(
                        valuespec=ListOfTimeRanges(
                            default_value=[None],
                        ),
                        title=_("Use specific times"),
                        label=_("Use specific times instead of whole day"),
                        help=_(
                            "When you specify explicit time definitions here, these will be added to each "
                            "date which is added to the resulting time period. By default the whole day is "
                            "used."
                        ),
                    ),
                ),
            ],
        )

    def _validate_ical_file(self, value: UploadedFile, varprefix: str) -> None:
        filename, _ty, content = value
        if not filename.endswith(".ics"):
            raise MKUserError(
                varprefix,
                _(
                    "The given file does not seem to be a valid iCalendar file. "
                    "It needs to have the file extension <tt>.ics</tt>."
                ),
            )

        if not content.startswith(b"BEGIN:VCALENDAR\r\n"):
            raise MKUserError(
                varprefix, _("The file does not seem to be a valid iCalendar file.AAA")
            )

        if not content.endswith(b"END:VCALENDAR\r\n"):
            raise MKUserError(
                varprefix, _("The file does not seem to be a valid iCalendar file.BBB")
            )

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
    def _parse_ical(self, ical_blob: str, horizon=10):
        ical: Dict[str, Any] = {"raw_events": []}

        def get_params(key: str) -> Dict[str, str]:
            return {k: v for p in key.split(";")[1:] for k, v in [p.split("=", 1)]}

        def parse_date(params, val):
            # First noprmalize the date value to make it easier parsable later
            if "T" not in val and params.get("VALUE") == "DATE":
                val += "T000000"  # add 00:00:00 to date specification

            return list(time.strptime(val, "%Y%m%dT%H%M%S"))

        # FIXME: The code below is incorrect, the contentlines have to be unfolded before parsing, see RFC 5545!
        # First extract the relevant information from the file
        in_event = False
        event: Dict[str, Any] = {}
        for l in ical_blob.split("\n"):
            line = l.strip()
            if not line:
                continue
            try:
                key, val = line.split(":", 1)
            except ValueError:
                raise Exception("Failed to parse line: %r" % line)

            if key == "X-WR-CALNAME":
                ical["name"] = val
            elif key == "X-WR-CALDESC":
                ical["descr"] = val

            elif line == "BEGIN:VEVENT":
                in_event = True
                event = {}  # create new event

            elif line == "END:VEVENT":
                # Finish the current event
                ical["raw_events"].append(event)
                in_event = False

            elif in_event:
                if key.startswith("DTSTART"):
                    params = get_params(key)
                    event["start"] = parse_date(params, val)

                elif key.startswith("DTEND"):
                    params = get_params(key)
                    event["end"] = parse_date(params, val)

                elif key == "RRULE":
                    event["recurrence"] = {
                        k: v for p in val.split(";") for k, v in [p.split("=", 1)]
                    }

                elif key == "SUMMARY":
                    event["name"] = val

        def next_occurrence(start, now, freq) -> time.struct_time:
            # convert struct_time to list to be able to modify it,
            # then set it to the next occurence
            t = start[:]

            if freq == "YEARLY":
                t[0] = now[0] + 1  # add 1 year
            elif freq == "MONTHLY":
                if now[1] + 1 > 12:
                    t[0] = now[0] + 1
                    t[1] = now[1] + 1 - 12
                else:
                    t[0] = now[0]
                    t[1] = now[1] + 1
            else:
                raise Exception('The frequency "%s" is currently not supported' % freq)
            return time.struct_time(t)

        def resolve_multiple_days(event, cur_start_time: time.struct_time):
            end = time.struct_time(event["end"])
            if time.strftime("%Y-%m-%d", cur_start_time) == time.strftime("%Y-%m-%d", end):
                # Simple case: a single day event
                return [
                    {
                        "name": event["name"],
                        "date": time.strftime("%Y-%m-%d", cur_start_time),
                    }
                ]

            # Resolve multiple days
            resolved, cur_timestamp, day = [], time.mktime(cur_start_time), 1
            while cur_timestamp < time.mktime(end):
                resolved.append(
                    {
                        "name": "%s %s" % (event["name"], _(" (day %d)") % day),
                        "date": time.strftime("%Y-%m-%d", time.localtime(cur_timestamp)),
                    }
                )
                cur_timestamp += 86400
                day += 1

            return resolved

        # TODO(ml): We should just use datetime to manipulate the time instead
        #           of messing around with lists and tuples.
        # Now resolve recurring events starting from 01.01 of current year
        # Non-recurring events are simply copied
        resolved = []
        now = time.strptime(str(time.localtime().tm_year - 1), "%Y")
        last = time.struct_time((horizon + 1, *now[1:]))
        for event in ical["raw_events"]:
            if "recurrence" in event and time.struct_time(event["start"]) < now:
                rule = event["recurrence"]
                freq = rule["FREQ"]
                cur = now
                while cur < last:
                    cur = next_occurrence(event["start"], cur, freq)
                    resolved += resolve_multiple_days(event, cur)
            else:
                resolved += resolve_multiple_days(event, time.struct_time(event["start"]))

        ical["events"] = sorted(resolved, key=lambda x: x["date"])

        return ical

    def page(self) -> None:
        if not html.request.var("upload"):
            self._show_import_ical_page()
        else:
            self._show_add_timeperiod_page()

    def _show_import_ical_page(self) -> None:
        html.p(
            _(
                "This page can be used to generate a new timeperiod definition based "
                "on the appointments of an iCalendar (<tt>*.ics</tt>) file. This import is normally used "
                "to import events like holidays, therefore only single whole day appointments are "
                "handled by this import."
            )
        )

        html.begin_form("import_ical", method="POST")
        self._vs_ical().render_input("ical", {})
        forms.end()
        html.hidden_fields()
        html.end_form()

    def _show_add_timeperiod_page(self) -> None:
        # If an ICalendar file is uploaded, we process the htmlvars here, to avoid
        # "Request URI too long exceptions"
        vs_ical = self._vs_ical()
        ical = vs_ical.from_html_vars("ical")
        vs_ical.validate_value(ical, "ical")

        filename, _ty, content = ical["file"]

        try:
            # TODO(ml): If we could open the file in text mode, we would not
            #           need to `decode()` here.
            data = self._parse_ical(content.decode("utf-8"), ical["horizon"])
        except Exception as e:
            if active_config.debug:
                raise
            raise MKUserError("ical_file", _("Failed to parse file: %s") % e)

        get_vars = {
            "timeperiod_p_alias": data.get("descr", data.get("name", filename)),
        }

        for day in defines.weekday_ids():
            get_vars["%s_0_from" % day] = ""
            get_vars["%s_0_until" % day] = ""

        # Default to whole day
        if not ical["times"]:
            ical["times"] = [((0, 0), (24, 0))]

        get_vars["timeperiod_p_exceptions_count"] = "%d" % len(data["events"])
        for index, event in enumerate(data["events"]):
            index += 1
            get_vars["timeperiod_p_exceptions_%d_0" % index] = event["date"]
            get_vars["timeperiod_p_exceptions_indexof_%d" % index] = "%d" % index

            get_vars["timeperiod_p_exceptions_%d_1_count" % index] = "%d" % len(ical["times"])
            for n, time_spec in enumerate(ical["times"]):
                n += 1
                start_time = ":".join("%02d" % x for x in time_spec[0])
                end_time = ":".join("%02d" % x for x in time_spec[1])
                get_vars["timeperiod_p_exceptions_%d_1_%d_from" % (index, n)] = start_time
                get_vars["timeperiod_p_exceptions_%d_1_%d_until" % (index, n)] = end_time
                get_vars["timeperiod_p_exceptions_%d_1_indexof_%d" % (index, n)] = "%d" % index

        for var, val in get_vars.items():
            html.request.set_var(var, val)

        html.request.set_var("mode", "edit_timeperiod")

        ModeEditTimeperiod().page()


@mode_registry.register
class ModeEditTimeperiod(WatoMode):
    @classmethod
    def name(cls):
        return "edit_timeperiod"

    @classmethod
    def permissions(cls):
        return ["timeperiods"]

    @classmethod
    def parent_mode(cls) -> _Optional[Type[WatoMode]]:
        return ModeTimeperiods

    def _from_vars(self):
        self._timeperiods = watolib.timeperiods.load_timeperiods()
        self._name = request.var("edit")  # missing -> new group
        # TODO: Nuke the field below? It effectively hides facts about _name for mypy.
        self._new = self._name is None

        if self._name in watolib.timeperiods.builtin_timeperiods():
            raise MKUserError("edit", _("Builtin timeperiods can not be modified"))
        if self._new:
            clone_name = request.var("clone")
            if request.var("mode") == "import_ical":
                self._timeperiod = {}
            elif clone_name:
                self._name = clone_name

                self._timeperiod = self._get_timeperiod(self._name)
            else:
                # initialize with 24x7 config
                self._timeperiod = {day: [("00:00", "24:00")] for day in defines.weekday_ids()}
        else:
            self._timeperiod = self._get_timeperiod(self._name)

    def _get_timeperiod(self, name):
        try:
            return self._timeperiods[name]
        except KeyError:
            raise MKUserError(None, _("This timeperiod does not exist."))

    def title(self):
        if self._new:
            return _("Add time period")
        return _("Edit time period")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Time period"), breadcrumb, form_name="timeperiod", button_name="_save"
        )

    def _valuespec(self):
        if self._new:
            # Cannot use ID() here because old versions of the GUI allowed time periods to start
            # with numbers and so on. The ID() valuespec does not allow it.
            name_element: ValueSpec = TextInput(
                title=_("Internal ID"),
                regex=r"^[-a-z0-9A-Z_]*$",
                regex_error=_(
                    "Invalid timeperiod name. Only the characters a-z, A-Z, 0-9, "
                    "_ and - are allowed."
                ),
                allow_empty=False,
                size=80,
            )
        else:
            name_element = FixedValue(value=self._name)

        return Dictionary(
            title=_("Time period"),
            elements=[
                ("name", name_element),
                (
                    "alias",
                    TextInput(
                        title=_("Alias"),
                        help=_("An alias or description of the timeperiod"),
                        allow_empty=False,
                        size=80,
                    ),
                ),
                ("weekdays", self._vs_weekdays()),
                ("exceptions", self._vs_exceptions()),
                ("exclude", self._vs_exclude()),
            ],
            render="form",
            optional_keys=False,
            validate=self._validate_id_and_alias,
        )

    def _validate_id_and_alias(self, value, varprefix):
        self._validate_id(value["name"], "%s_p_name" % varprefix)
        self._validate_alias(value["name"], value["alias"], "%s_p_alias" % varprefix)

    def _validate_id(self, value, varprefix):
        if self._name is None and value in self._timeperiods:
            raise MKUserError(
                varprefix, _("This name is already being used by another timeperiod.")
            )

    def _validate_alias(self, name, alias, varprefix):
        unique, message = groups.is_alias_used("timeperiods", name, alias)
        if not unique:
            assert message is not None
            raise MKUserError(varprefix, message)

    def _vs_weekdays(self):
        return CascadingDropdown(
            title=_("Active time range"),
            help=_(
                "For each weekday you can setup no, one or several "
                "time ranges in the format <tt>23:39</tt>, in which the time period "
                "should be active."
            ),
            choices=[
                ("whole_week", _("Same times for all weekdays"), ListOfTimeRanges()),
                (
                    "day_specific",
                    _("Weekday specific times"),
                    Dictionary(
                        elements=self._weekday_elements(),
                        optional_keys=False,
                        indent=False,
                    ),
                ),
            ],
        )

    def _weekday_elements(self):
        elements = []
        for tp_id, tp_title in cmk.utils.defines.weekdays_by_name():
            elements.append((tp_id, ListOfTimeRanges(title=tp_title)))
        return elements

    def _vs_exceptions(self):
        return ListOf(
            valuespec=Tuple(
                orientation="horizontal",
                show_titles=False,
                elements=[
                    TextInput(
                        regex="^[-a-z0-9A-Z /]*$",
                        regex_error=_("This is not a valid Nagios timeperiod day specification."),
                        allow_empty=False,
                        validate=self._validate_timeperiod_exception,
                    ),
                    ListOfTimeRanges(),
                ],
            ),
            title=_("Exceptions (from weekdays)"),
            help=_(
                "Here you can specify exceptional time ranges for certain "
                "dates in the form YYYY-MM-DD which are used to define more "
                "specific definitions to override the times configured for the matching "
                "weekday."
            ),
            movable=False,
            add_label=_("Add Exception"),
        )

    def _validate_timeperiod_exception(self, value, varprefix):
        if value in defines.weekday_ids():
            raise MKUserError(
                varprefix, _("You cannot use weekday names (%s) in exceptions") % value
            )

        if value in ["name", "alias", "timeperiod_name", "register", "use", "exclude"]:
            raise MKUserError(varprefix, _("<tt>%s</tt> is a reserved keyword."))

        cfg = ConfigDomainOMD().default_globals()
        if cfg["site_core"] == "cmc":
            try:
                time.strptime(value, "%Y-%m-%d")
            except ValueError:
                raise MKUserError(
                    varprefix, _("You need to provide timeperiod exceptions in YYYY-MM-DD format")
                )

    def _vs_exclude(self):
        return ListChoice(
            choices=self._other_timeperiod_choices(),
            title=_("Exclude"),
            help=_(
                "You can use other timeperiod definitions to exclude the times "
                "defined in the other timeperiods from this current timeperiod."
            ),
        )

    def _other_timeperiod_choices(self):
        """List of timeperiods that can be used for exclusions

        We offer the list of all other timeperiods - but only those that do not exclude the current
        timeperiod (in order to avoid cycles)"""
        other_tps = []

        for tpname, tp in self._timeperiods.items():
            if not self._timeperiod_excludes(tpname):
                other_tps.append((tpname, timeperiod_spec_alias(tp, tpname)))

        return sorted(other_tps, key=lambda a: a[1].lower())

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

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return None

        vs = self._valuespec()  # returns a Dictionary object
        vs_spec = vs.from_html_vars("timeperiod")
        vs.validate_value(vs_spec, "timeperiod")
        self._timeperiod = self._from_valuespec(vs_spec)

        if self._new:
            self._name = vs_spec["name"]
            _changes.add_change("edit-timeperiods", _("Created new time period %s") % self._name)
        else:
            _changes.add_change("edit-timeperiods", _("Modified time period %s") % self._name)

        assert self._name is not None
        self._timeperiods[self._name] = self._timeperiod
        watolib.timeperiods.save_timeperiods(self._timeperiods)
        return redirect(mode_url("timeperiods"))

    def page(self):
        html.begin_form("timeperiod", method="POST")
        self._valuespec().render_input("timeperiod", self._to_valuespec(self._timeperiod))
        forms.end()
        html.hidden_fields()
        html.end_form()

    # The timeperiod data structure for the Checkmk config looks like follows.
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
            if exception_name not in defines.weekday_ids() + ["alias", "exclude"]:
                exceptions.append((exception_name, self._time_ranges_to_valuespec(time_ranges)))

        vs_spec = {
            "name": self._name
            or (unique_default_name_suggestion("time_period", list(self._timeperiods.keys()))),
            "alias": timeperiod_spec_alias(tp_spec),
            "weekdays": self._weekdays_to_valuespec(tp_spec),
            "exclude": tp_spec.get("exclude", []),
            "exceptions": sorted(exceptions),
        }

        return vs_spec

    def _weekdays_to_valuespec(self, tp_spec):
        if self._has_same_time_specs_during_whole_week(tp_spec):
            return ("whole_week", self._time_ranges_to_valuespec(tp_spec.get("monday", [])))

        return (
            "day_specific",
            {
                day: self._time_ranges_to_valuespec(tp_spec.get(day, []))
                for day in defines.weekday_ids()
            },
        )

    def _has_same_time_specs_during_whole_week(self, tp_spec):
        """Put the time ranges of all weekdays into a set to reduce the duplicates to see whether
        or not all days have the same time spec and return True if they have the same."""
        unified_time_ranges = set(tuple(tp_spec.get(day, [])) for day in defines.weekday_ids())
        return len(unified_time_ranges) == 1

    def _time_ranges_to_valuespec(self, time_ranges):
        return [self._time_range_to_valuespec(r) for r in time_ranges]

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
        tp_spec.update(self._time_exceptions_from_valuespec(vs_spec))
        return tp_spec

    def _exceptions_from_valuespec(self, vs_spec):
        tp_spec = {}
        for exception_name, time_ranges in vs_spec["exceptions"]:
            if time_ranges:
                tp_spec[exception_name] = self._time_ranges_from_valuespec(time_ranges)
        return tp_spec

    def _time_exceptions_from_valuespec(self, vs_spec):
        # TODO: time exceptions is either a list of tuples or a dictionary for
        period_type, exceptions_details = vs_spec["weekdays"]

        if period_type not in ["whole_week", "day_specific"]:
            raise NotImplementedError()

        # produce a data structure equal to the "day_specific" structure
        if period_type == "whole_week":
            time_exceptions = {day: exceptions_details for day in defines.weekday_ids()}
        else:  # specific days
            time_exceptions = exceptions_details

        return {
            day: self._time_ranges_from_valuespec(time_exceptions[day])
            for day, time_ranges in time_exceptions.items()
            if time_ranges
        }

    def _time_ranges_from_valuespec(self, time_ranges):
        return [self._time_range_from_valuespec(r) for r in time_ranges if r is not None]

    def _time_range_from_valuespec(self, value):
        """Convert a time range specification from valuespec format"""
        return tuple(map(self._format_valuespec_time, value))

    def _format_valuespec_time(self, value):
        """Convert a time specification from valuespec format"""
        return "%02d:%02d" % value
