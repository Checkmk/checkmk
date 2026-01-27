#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="unreachable"
# mypy: disable-error-code="no-untyped-call"


"""Modes for managing timeperiod definitions for the core"""

import logging
import time
from collections.abc import Collection
from datetime import date, datetime, timedelta
from typing import Any, cast

import recurring_ical_events
from icalendar import Calendar, Event
from icalendar.prop import vDDDTypes

from cmk.gui import forms, watolib
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.default_name import unique_default_name_suggestion
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, IconNames, PermissionName, StaticIcon
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import DocReference, make_confirm_delete_link
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    DictionaryModel,
    FileUpload,
    FileUploadModel,
    FixedValue,
    Integer,
    ListChoice,
    ListOf,
    ListOfTimeRanges,
    TextInput,
    Tuple,
    ValueSpec,
)
from cmk.gui.watolib import groups
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, make_action_link
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.timeperiods import load_timeperiods
from cmk.utils import dateutils
from cmk.utils.timeperiod import (
    is_builtin_timeperiod,
    timeperiod_spec_alias,
    TimeperiodName,
    TimeperiodSpec,
)

logger = logging.getLogger(__name__)

TimeperiodUsage = tuple[str, str]


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeTimeperiods)
    mode_registry.register(ModeTimeperiodImportICal)
    mode_registry.register(ModeEditTimeperiod)


class ICalEvent(Event):
    def __init__(self, event: Event):
        super().__init__(**event)
        self.time_ranges: list[tuple[str, str]] = []

    def _as_datetime(self, key: str) -> datetime:
        if key not in self:
            raise ValueError(f"Event obj doesn't have the key {key}")

        vddd: vDDDTypes = self[key]
        dt = vddd.dt

        if isinstance(dt, datetime):
            return dt.astimezone()

        if isinstance(dt, date):
            return datetime.combine(dt, datetime.min.time()).astimezone()

        raise ValueError(f"Error getting datetime obj for the key: {key}")

    @property
    def dtstart_dt(self) -> datetime:
        return self._as_datetime("DTSTART")

    @property
    def dtstart_str(self) -> str:
        return self.dtstart_dt.strftime("%Y-%m-%d")

    @property
    def _dtend(self) -> datetime:
        return self._as_datetime("DTEND")

    @property
    def _description(self) -> str:
        if "DESCRIPTION" not in self:
            return ""
        return self.decoded("DESCRIPTION").decode("UTF-8")

    @property
    def summary(self) -> str:
        if "SUMMARY" not in self:
            return self._description
        return self.decoded("SUMMARY").decode("UTF-8")

    @property
    def _duration(self) -> timedelta:
        if "DURATION" in self:
            dur: vDDDTypes = self["DURATION"]
            if isinstance(dur.dt, timedelta):
                return dur.dt

        return self._dtend - self.dtstart_dt

    @property
    def _timerange_to(self) -> str:
        duration = self._duration
        if duration.days >= 1 and duration.seconds == 0 and duration.microseconds == 0:
            return "24:00"

        return (self.dtstart_dt + self._duration).strftime("%H:%M")

    @property
    def timerange(self) -> tuple[str, str]:
        return self.dtstart_dt.strftime("%H:%M"), self._timerange_to

    @property
    def timeranges(self) -> set[tuple[str, str]]:
        self.time_ranges.append(self.timerange)
        if ("00:00", "24:00") in self.time_ranges:
            return {("00:00", "24:00")}
        return set(self.time_ranges)

    def add_timerange(self, new_timerange: tuple[str, str]) -> None:
        self.time_ranges.append(new_timerange)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({super().__repr__()})"

    def to_timeperiod_exception(self) -> dict[str, TimeperiodUsage]:
        """An event can take several days. Moreover, it does not necessarily have to take up the whole day.
        This method returns a dict that relates each of the days involved to the corresponding time slot.

        Examples:
        From 2024-08-01 00:00
        To 2024-08-02 00:00:00
        Output {'2024-08-01': ("00:00", "24:00")}

        From 2024-08-01 12:00:00
        To 2024-08-03 12:00:00
        Output {'2024-08-01': ("12:00", "24:00"), '2024-08-02': ("00:00", "24:00"), '2024-8-03': ("00:00", "12:00")}

        From 2024-08-01 09:00
        To 2024-08-01 18:00
        Output {'2024-08-01': ("09:00", "18:00")}

        """
        start_date = self.dtstart_dt
        event_lenght = self._duration
        end_date = start_date + event_lenght
        end_date_str = end_date.strftime("%Y-%m-%d")

        result: dict[str, tuple[str, str]] = {}
        current_day = start_date
        current_time_start = start_date.strftime("%H:%M")
        current_time_end = "24:00"

        while current_day.date() <= end_date.date():
            current_day_str = current_day.strftime("%Y-%m-%d")
            if current_day_str == end_date_str and (end_date.hour == 0 and end_date.minute == 0):
                break

            if current_day_str == end_date_str:
                current_time_end = end_date.strftime("%H:%M")

            result[current_day_str] = (current_time_start, current_time_end)
            current_day += timedelta(days=1)
            current_time_start = "00:00"

        return result


class ModeTimeperiods(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "timeperiods"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["timeperiods"]

    def __init__(self) -> None:
        super().__init__()
        self._timeperiods = load_timeperiods()

    def title(self) -> str:
        return _("Time periods")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
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
                                    icon_name=StaticIcon(IconNames.new),
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "edit_timeperiod")])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                                PageMenuEntry(
                                    title=_("Import iCalendar"),
                                    icon_name=StaticIcon(IconNames.ical),
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
        menu.add_doc_reference(_("Time periods"), DocReference.TIMEPERIODS)
        return menu

    def action(self, config: Config) -> ActionResult:
        delname = request.var("_delete")
        if not delname:
            return redirect(mode_url("timeperiods"))

        if not transactions.check_transaction():
            return redirect(mode_url("timeperiods"))

        try:
            watolib.timeperiods.delete_timeperiod(
                TimeperiodName(delname),
                user_id=user.id,
                pprint_value=config.wato_pprint_config,
                use_git=config.wato_use_git,
            )
            self._timeperiods = load_timeperiods()

        except watolib.timeperiods.TimePeriodBuiltInError:
            raise MKUserError("_delete", _("Built-in time periods cannot be modified"))

        except watolib.timeperiods.TimePeriodInUseError as exception:
            message = "<b>{}</b><br>{}:<ul>".format(
                _("You cannot delete this time period."),
                _("It is still in use by"),
            )
            for title, link in exception.usages:
                message += f'<li><a href="{link}">{title}</a></li>\n'
            message += "</ul>"
            raise MKUserError(None, message)

        return redirect(mode_url("timeperiods"))

    def page(self, config: Config) -> None:
        with table_element(
            "timeperiods", empty_text=_("There are no time periods defined yet.")
        ) as table:
            for name, timeperiod in sorted(self._timeperiods.items()):
                table.row()

                table.cell(_("Actions"), css=["buttons"])
                alias = timeperiod_spec_alias(timeperiod)
                if is_builtin_timeperiod(name):
                    html.i(_("(built-in)"))
                else:
                    self._action_buttons(name, alias)

                table.cell(_("Name"), name)
                table.cell(_("Alias"), alias)

    def _action_buttons(self, name: str, alias: str) -> None:
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
        delete_url = make_confirm_delete_link(
            url=make_action_link(
                [
                    ("mode", "timeperiods"),
                    ("_delete", name),
                ]
            ),
            title=_("Delete time period"),
            suffix=alias,
            message=_("Name: %s") % name,
        )

        html.icon_button(edit_url, _("Properties"), StaticIcon(IconNames.edit))
        html.icon_button(clone_url, _("Create a copy"), StaticIcon(IconNames.clone))
        html.icon_button(delete_url, _("Delete"), StaticIcon(IconNames.delete))


# Displays a dialog for uploading an ical file which will then
# be used to generate timeperiod exceptions etc. and then finally
# open the edit_timeperiod page to create a new timeperiod using
# these information
class ModeTimeperiodImportICal(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "import_ical"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["timeperiods"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeTimeperiods

    def title(self) -> str:
        if request.var("upload"):
            return _("Add time period")
        return _("Import iCalendar File to create a time period")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        if not request.var("upload"):
            return make_simple_form_page_menu(
                _("iCalendar"),
                breadcrumb,
                form_name="import_ical",
                button_name="upload",
                save_title=_("Import"),
            )
        return ModeEditTimeperiod().page_menu(config, breadcrumb)

    def _vs_ical(self) -> Dictionary:
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
                        allowed_extensions=[".ics"],
                        mime_types=["text/calendar"],
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
            ],
        )

    def _validate_ical_file(self, value: FileUploadModel, varprefix: str) -> None:
        assert isinstance(value, tuple)  # Hmmm...
        filename, _ty, content = value
        if not filename.endswith(".ics"):
            raise MKUserError(
                varprefix,
                _(
                    "The given file does not seem to be a valid iCalendar file. "
                    "It needs to have the file extension <tt>.ics</tt>."
                ),
            )

        if not content.startswith(b"BEGIN:VCALENDAR") or not content.endswith(
            (b"END:VCALENDAR", b"END:VCALENDAR\n", b"END:VCALENDAR\r\n")
        ):
            raise MKUserError(varprefix, _("The file does not seem to be a valid iCalendar file."))

    def page(self, config: Config) -> None:
        if not request.var("upload"):
            self._show_import_ical_page()
        else:
            self._show_add_timeperiod_page(config)

    def _show_import_ical_page(self) -> None:
        html.p(
            _(
                "This page can be used to generate a new time period definition based "
                "on the appointments of an iCalendar (<tt>*.ics</tt>) file. This import "
                "is normally used to import events as exceptions. Time ranges and "
                "recurring events are supported, however, currently the total number of "
                "75 exceptions cannot be exceeded."
            )
        )

        with html.form_context("import_ical", method="POST"):
            self._vs_ical().render_input("ical", {})
            forms.end()
            html.hidden_fields()

    def _show_add_timeperiod_page(self, config: Config) -> None:
        # If an ICalendar file is uploaded, we process the htmlvars here, to avoid
        # "Request URI too long exceptions"
        vs_ical = self._vs_ical()
        ical = vs_ical.from_html_vars("ical")
        vs_ical.validate_value(ical, "ical")

        filename, _ty, content = ical["file"]
        cal_obj: Calendar = Calendar.from_ical(content)  # type: ignore[assignment]

        exception_map: dict[str, list[TimeperiodUsage]] = {}
        now = datetime.now()
        for e in recurring_ical_events.of(cal_obj).between(
            now, now + timedelta(days=365 * ical["horizon"])
        ):
            ice = ICalEvent(e)
            if ice.dtstart_dt is None:
                continue

            exceptions = ice.to_timeperiod_exception()
            for dt, timerange in exceptions.items():
                if existing_event := exception_map.get(dt):
                    existing_event.append(timerange)
                    continue
                exception_map[dt] = [timerange]

        # If a time period exception has the full day, we can ignore the others (if available)
        for timeranges in exception_map.values():
            if ("00:00", "24:00") in timeranges:
                timeranges[:] = [("00:00", "24:00")]

        get_vars = {
            "timeperiod_p_alias": str(
                cal_obj.get("X-WR-CALDESC", cal_obj.get("X-WR-CALNAME", filename))
            ),
        }

        for day in dateutils.weekday_ids():
            get_vars["%s_0_from" % day] = ""
            get_vars["%s_0_until" % day] = ""

        get_vars["timeperiod_p_exceptions_count"] = "%d" % len(exception_map)

        index = 1
        for dtstart_str, timeranges in sorted(exception_map.items()):
            get_vars["timeperiod_p_exceptions_%d_0" % index] = dtstart_str
            get_vars["timeperiod_p_exceptions_indexof_%d" % index] = "%d" % index
            get_vars["timeperiod_p_exceptions_%d_1_count" % index] = "%d" % len(
                timeranges
            )  # "1"  # "%d" % len(ical["times"])
            for n, (timerange_from, timerange_to) in enumerate(timeranges, 1):
                get_vars["timeperiod_p_exceptions_%d_1_%d_from" % (index, n)] = timerange_from
                get_vars["timeperiod_p_exceptions_%d_1_%d_until" % (index, n)] = timerange_to
                get_vars["timeperiod_p_exceptions_%d_1_indexof_%d" % (index, n)] = "%d" % index

            index += 1

        for var, val in get_vars.items():
            request.set_var(var, val)

        request.set_var("mode", "edit_timeperiod")

        ModeEditTimeperiod().page(config)


class ModeEditTimeperiod(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "edit_timeperiod"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["timeperiods"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeTimeperiods

    def _from_vars(self) -> None:
        self._timeperiods = load_timeperiods()
        self._name = (
            None if (n := request.var("edit")) is None else TimeperiodName(n)
        )  # missing -> new group
        if self._name is None:
            clone_name = None if (c := request.var("clone")) is None else TimeperiodName(c)
            if request.var("mode") == "import_ical":
                self._timeperiod: TimeperiodSpec = {"alias": request.var("timeperiod_p_alias", "")}
            elif clone_name:
                self._name = clone_name
                self._timeperiod = self._get_timeperiod(self._name)
            else:
                self._timeperiod = {"alias": ""}
        else:
            if is_builtin_timeperiod(self._name):
                raise MKUserError("edit", _("Built-in time periods cannot be modified"))
            self._timeperiod = self._get_timeperiod(self._name)

    def _get_timeperiod(self, name: TimeperiodName) -> TimeperiodSpec:
        try:
            return self._timeperiods[name]
        except KeyError:
            raise MKUserError(None, _("This time period does not exist."))

    def title(self) -> str:
        return _("Add time period") if self._name is None else _("Edit time period")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Time period"), breadcrumb, form_name="timeperiod", button_name="_save"
        )

    def _valuespec(self) -> Dictionary:
        if self._name is None:
            # Cannot use ID() here because old versions of the GUI allowed time periods to start
            # with numbers and so on. The ID() valuespec does not allow it.
            name_element: ValueSpec = TextInput(
                title=_("Internal ID"),
                regex=watolib.timeperiods.TIMEPERIOD_ID_PATTERN,
                regex_error=_(
                    "Invalid time period name. Only the characters a-z, A-Z, 0-9, "
                    "_ and - are allowed."
                ),
                allow_empty=False,
                size=80,
            )
        else:
            name_element = FixedValue(value=self._name)

        elements = [
            ("name", name_element),
            (
                "alias",
                TextInput(
                    title=_("Alias"),
                    help=_("An alias or description of the time period"),
                    allow_empty=False,
                    size=80,
                ),
            ),
            ("weekdays", self._vs_weekdays()),
            ("exceptions", self._vs_exceptions()),
        ]

        # Show the exclude option in the gui, only when there are choices.
        exclude = self._vs_exclude(choices := self._other_timeperiod_choices())
        if choices:
            elements.append(("exclude", exclude))

        return Dictionary(
            title=_("Time period"),
            elements=elements,
            render="form",
            optional_keys=False,
            validate=self._validate_id_and_alias,
        )

    def _validate_id_and_alias(self, value: DictionaryModel, varprefix: str) -> None:
        self._validate_id(value["name"], "%s_p_name" % varprefix)
        self._validate_alias(value["name"], value["alias"], "%s_p_alias" % varprefix)

    def _validate_id(self, value: str, varprefix: str) -> None:
        if self._name is None and value in self._timeperiods:
            raise MKUserError(
                varprefix, _("This name is already being used by another time period.")
            )

    def _validate_alias(self, name: str, alias: str, varprefix: str) -> None:
        unique, message = groups.is_alias_used("timeperiods", name, alias)
        if not unique:
            assert message is not None
            raise MKUserError(varprefix, message)

    def _vs_weekdays(self) -> CascadingDropdown:
        return CascadingDropdown(
            title=_("Active time range"),
            help=_(
                "For each weekday you can set up no, one or several "
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

    def _weekday_elements(self) -> list[tuple[dateutils.Weekday, ListOf]]:
        elements = []
        for tp_id, tp_title in dateutils.weekdays_by_name():
            elements.append((tp_id, ListOfTimeRanges(title=tp_title)))
        return elements

    def _vs_exceptions(self) -> ListOf:
        return ListOf(
            valuespec=Tuple(
                orientation="horizontal",
                show_titles=False,
                elements=[
                    TextInput(
                        regex="^[-a-z0-9A-Z /]*$",
                        regex_error=_("This is not a valid Nagios time period day specification."),
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

    def _validate_timeperiod_exception(self, value: str, varprefix: str) -> None:
        if value in dateutils.weekday_ids():
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
                    varprefix, _("You need to provide time period exceptions in YYYY-MM-DD format")
                )

    def _vs_exclude(self, choices: list[tuple[str, str]]) -> ListChoice:
        return ListChoice(
            choices=choices,
            title=_("Exclude"),
            help=_(
                "You can use other time period definitions to exclude the times "
                "defined in the other time periods from this current time period."
            ),
        )

    def _other_timeperiod_choices(self) -> list[tuple[str, str]]:
        """List of timeperiods that can be used for exclusions

        We offer the list of all other time periods - but only those that do not exclude the current
        time period (in order to avoid cycles)

        Don't allow the built-in time period '24X7'.

        """
        other_tps = []

        for tpname, tp in self._timeperiods.items():
            if tpname == "24X7":
                continue

            if not self._timeperiod_excludes(tpname):
                other_tps.append((tpname, timeperiod_spec_alias(tp, tpname)))

        return sorted(other_tps, key=lambda a: a[1].lower())

    def _timeperiod_excludes(self, tpa_name: TimeperiodName) -> bool:
        """Check, if timeperiod tpa excludes or is tpb"""
        if tpa_name == self._name:
            return True

        tpa = self._timeperiods[tpa_name]
        for ex in tpa.get("exclude", []):
            if ex == self._name:
                return True

            assert isinstance(ex, str)
            if self._timeperiod_excludes(ex):
                return True

        return False

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return None

        vs = self._valuespec()  # returns a Dictionary object
        vs_spec = vs.from_html_vars("timeperiod")
        vs.validate_value(vs_spec, "timeperiod")
        self._timeperiod = self._from_valuespec(vs_spec)

        if self._name is None:
            self._name = vs_spec["name"]
            watolib.timeperiods.create_timeperiod(
                self._name,
                self._timeperiod,
                user_id=user.id,
                pprint_value=config.wato_pprint_config,
                use_git=config.wato_use_git,
            )
        else:
            watolib.timeperiods.modify_timeperiod(
                self._name,
                self._timeperiod,
                user_id=user.id,
                pprint_value=config.wato_pprint_config,
                use_git=config.wato_use_git,
            )

        self._timeperiods = load_timeperiods()
        return redirect(mode_url("timeperiods"))

    def page(self, config: Config) -> None:
        with html.form_context("timeperiod", method="POST"):
            self._valuespec().render_input("timeperiod", self._to_valuespec(self._timeperiod))
            forms.end()
            html.hidden_fields()

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
    def _to_valuespec(self, tp_spec: TimeperiodSpec) -> dict:
        if not tp_spec:
            return {}

        exceptions = []
        for exception_name, time_ranges in tp_spec.items():
            if exception_name not in dateutils.weekday_ids() + ["alias", "exclude"]:
                exceptions.append(
                    (
                        exception_name,
                        self._time_ranges_to_valuespec(cast(list[tuple[str, str]], time_ranges)),
                    )
                )

        vs_spec = {
            "name": self._name
            or (unique_default_name_suggestion("time_period", list(self._timeperiods.keys()))),
            "alias": timeperiod_spec_alias(tp_spec),
            "weekdays": self._weekdays_to_valuespec(tp_spec),
            "exclude": tp_spec.get("exclude", []),
            "exceptions": sorted(exceptions),
        }

        return vs_spec

    def _weekdays_to_valuespec(self, tp_spec: TimeperiodSpec) -> tuple:
        if self._has_same_time_specs_during_whole_week(tp_spec):
            return ("whole_week", self._time_ranges_to_valuespec(tp_spec.get("monday", [])))

        return (
            "day_specific",
            {
                day: self._time_ranges_to_valuespec(tp_spec.get(day, []))
                for day in dateutils.weekday_ids()
            },
        )

    def _has_same_time_specs_during_whole_week(self, tp_spec: TimeperiodSpec) -> bool:
        """Put the time ranges of all weekdays into a set to reduce the duplicates to see whether
        or not all days have the same time spec and return True if they have the same."""
        unified_time_ranges = {tuple(tp_spec.get(day, [])) for day in dateutils.weekday_ids()}
        return len(unified_time_ranges) == 1

    def _time_ranges_to_valuespec(
        self, time_ranges: list[tuple[str, str]]
    ) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        return [self._time_range_to_valuespec(r) for r in time_ranges]

    def _time_range_to_valuespec(
        self, time_range: tuple[str, str]
    ) -> tuple[tuple[int, int], tuple[int, int]]:
        """Convert a time range specification to valuespec format
        e.g. ("00:30", "10:17") -> ((0,30),(10,17))"""
        start, end = time_range
        return (self._time_to_valuespec(start), self._time_to_valuespec(end))

    def _time_to_valuespec(self, time_str: str) -> tuple[int, int]:
        """Convert a time specification to valuespec format
        e.g. "00:30" -> (0, 30)"""
        hour, minute = time_str.split(":")
        return (int(hour), int(minute))

    def _from_valuespec(self, vs_spec: DictionaryModel) -> TimeperiodSpec:
        tp_spec: dict[str, Any] = {
            "alias": vs_spec["alias"],
        }

        if "exclude" in vs_spec:
            tp_spec["exclude"] = vs_spec["exclude"]

        tp_spec.update(self._exceptions_from_valuespec(vs_spec))
        tp_spec.update(self._time_exceptions_from_valuespec(vs_spec))
        return cast(TimeperiodSpec, tp_spec)

    def _exceptions_from_valuespec(self, vs_spec: DictionaryModel) -> dict[str, Any]:
        tp_spec = {}
        for exception_name, time_ranges in vs_spec["exceptions"]:
            if time_ranges:
                tp_spec[exception_name] = self._time_ranges_from_valuespec(time_ranges)
        return tp_spec

    def _time_exceptions_from_valuespec(self, vs_spec: DictionaryModel) -> dict[str, Any]:
        # TODO: time exceptions is either a list of tuples or a dictionary for
        period_type, exceptions_details = vs_spec["weekdays"]

        if period_type not in ["whole_week", "day_specific"]:
            raise NotImplementedError()

        # produce a data structure equal to the "day_specific" structure
        if period_type == "whole_week":
            time_exceptions = {day: exceptions_details for day in dateutils.weekday_ids()}
        else:  # specific days
            time_exceptions = exceptions_details

        return {
            day: self._time_ranges_from_valuespec(time_ranges)
            for day, time_ranges in time_exceptions.items()
            if time_ranges
        }

    def _time_ranges_from_valuespec(
        self, time_ranges: list[tuple[tuple[int, int], tuple[int, int]] | None]
    ) -> list[tuple[str, str]]:
        return [self._time_range_from_valuespec(r) for r in time_ranges if r is not None]

    def _time_range_from_valuespec(
        self, value: tuple[tuple[int, int], tuple[int, int]]
    ) -> tuple[str, str]:
        """Convert a time range specification from valuespec format"""
        start, end = value
        return (self._format_valuespec_time(start), self._format_valuespec_time(end))

    def _format_valuespec_time(self, value: tuple[int, int]) -> str:
        """Convert a time specification from valuespec format"""
        return "%02d:%02d" % value
