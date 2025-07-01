#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime
import time
from collections.abc import Iterator, Sequence
from typing import Any, cast

import livestatus

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId

from cmk.gui import sites
from cmk.gui.breadcrumb import (
    Breadcrumb,
    BreadcrumbItem,
    make_current_page_breadcrumb_item,
    make_simple_page_breadcrumb,
)
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import (
    make_display_options_dropdown,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import PageEndpoint, PageRegistry
from cmk.gui.table import table_element
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri, makeuri, makeuri_contextless
from cmk.gui.view_breadcrumbs import make_host_breadcrumb

#   .--HTML Output---------------------------------------------------------.
#   |     _   _ _____ __  __ _        ___        _               _         |
#   |    | | | |_   _|  \/  | |      / _ \ _   _| |_ _ __  _   _| |_       |
#   |    | |_| | | | | |\/| | |     | | | | | | | __| '_ \| | | | __|      |
#   |    |  _  | | | | |  | | |___  | |_| | |_| | |_| |_) | |_| | |_       |
#   |    |_| |_| |_| |_|  |_|_____|  \___/ \__,_|\__| .__/ \__,_|\__|      |
#   |                                               |_|                    |
#   +----------------------------------------------------------------------+
#   |  Toplevel code for show the actual HTML page                         |
#   '----------------------------------------------------------------------'


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageEndpoint("logwatch", page_show))


def page_show(config: Config) -> None:
    site = request.get_validated_type_input(SiteId, "site")  # optional site hint
    host_name = request.get_validated_type_input_mandatory(HostName, "host", deflt=HostName(""))
    file_name = request.get_str_input_mandatory("file", "")

    # Fix problem when URL is missing certain illegal characters
    try:
        file_name = form_file_to_ext(
            find_matching_logfile(site, host_name, form_file_to_int(file_name))
        )
    except livestatus.MKLivestatusNotFoundError:
        pass  # host_name log dir does not exist

    if not host_name:
        show_log_list(debug=config.debug)
        return

    if file_name:
        show_file(site, host_name, file_name, debug=config.debug)
    else:
        show_host_log_list(site, host_name, debug=config.debug)


def show_log_list(*, debug: bool) -> None:
    """Shows a list of all problematic logfiles grouped by host"""
    title = _("All problematic log files")
    breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_monitoring(), title)
    make_header(html, title, breadcrumb, _log_list_page_menu(breadcrumb))

    if request.has_var("_ack") and not request.var("_do_actions") == _("No"):
        do_log_ack(site=None, host_name=None, file_name=None)
        return

    for site, host_name, logs in all_logs():
        if not logs:
            continue

        all_logs_empty = not any(
            parse_file(site, host_name, file_name, hidecontext=False, debug=debug)
            for file_name in logs
        )

        if all_logs_empty:
            continue  # Logfile vanished

        html.h3(
            HTMLWriter.render_a(
                host_name,
                href=makeuri(
                    request,
                    [("site", site), ("host", host_name)],
                ),
            ),
            class_="table",
        )
        list_logs(site, host_name, logs, debug=debug)
    html.footer()


def _log_list_page_menu(breadcrumb: Breadcrumb) -> PageMenu:
    return PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="logs",
                title=_("Logs"),
                topics=[
                    PageMenuTopic(
                        title=_("Acknowledge"),
                        entries=list(_page_menu_entry_acknowledge()),
                    ),
                ],
            ),
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Setup"),
                        entries=[
                            PageMenuEntry(
                                title=_("Analyze patterns"),
                                icon_name="analyze",
                                item=make_simple_link(
                                    makeuri_contextless(
                                        request,
                                        [("mode", "pattern_editor")],
                                        filename="wato.py",
                                    )
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
    )


def services_url(site: SiteId | None, host_name: HostName) -> str:
    return makeuri_contextless(
        request,
        [("view_name", "host"), ("site", site), ("host", host_name)],
        filename="view.py",
    )


def analyse_url(
    site: SiteId | None, host_name: HostName, file_name: str = "", match: str = ""
) -> str:
    return makeuri_contextless(
        request,
        [
            ("mode", "pattern_editor"),
            ("site", site),
            ("host", host_name),
            ("file", file_name),
            ("match", match),
        ],
        filename="wato.py",
    )


def show_host_log_list(site: SiteId | None, host_name: HostName, *, debug: bool) -> None:
    """Shows all problematic logfiles of a host"""
    title = _("Logfiles of host %s") % host_name
    breadcrumb = _host_log_list_breadcrumb(host_name, title)
    make_header(html, title, breadcrumb, _host_log_list_page_menu(breadcrumb, site, host_name))

    if request.has_var("_ack") and not request.var("_do_actions") == _("No"):
        do_log_ack(site, host_name, file_name=None)
        return

    html.open_table(class_=["data"])
    list_logs(site, host_name, logfiles_of_host(site, host_name), debug=debug)
    html.close_table()

    html.footer()


def _host_log_list_breadcrumb(host_name: HostName, title: str) -> Breadcrumb:
    breadcrumb = make_host_breadcrumb(host_name)
    breadcrumb.append(make_current_page_breadcrumb_item(title))
    return breadcrumb


def _host_log_list_page_menu(
    breadcrumb: Breadcrumb, site_id: SiteId | None, host_name: HostName
) -> PageMenu:
    return PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="logs",
                title=_("Logs"),
                topics=[
                    PageMenuTopic(
                        title=_("Current log files"),
                        entries=list(_page_menu_entry_acknowledge(site_id, host_name)),
                    ),
                    PageMenuTopic(
                        title=_("Log files"),
                        entries=[
                            PageMenuEntry(
                                title=_("All log files"),
                                icon_name="logwatch",
                                item=make_simple_link(
                                    makeuri(
                                        request,
                                        [("site", ""), ("host", ""), ("file", "")],
                                    )
                                ),
                            ),
                        ],
                    ),
                ],
            ),
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Monitoring"),
                        entries=[
                            PageMenuEntry(
                                title=_("Services of host"),
                                icon_name="services",
                                item=make_simple_link(services_url(site_id, host_name)),
                            ),
                        ],
                    ),
                    PageMenuTopic(
                        title=_("Setup"),
                        entries=[
                            PageMenuEntry(
                                title=_("Analyze host patterns"),
                                icon_name="analyze",
                                item=make_simple_link(analyse_url(site_id, host_name)),
                            ),
                        ],
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
    )


def list_logs(
    site: SiteId | None, host_name: HostName, logfile_names: Sequence[str], *, debug: bool
) -> None:
    """Displays a table of logfiles"""
    with table_element(empty_text=_("No logs found for this host.")) as table:
        for file_name in logfile_names:
            table.row()
            file_display = form_file_to_ext(file_name)
            uri = makeuri(request, [("site", site), ("host", host_name), ("file", file_display)])
            logfile_link = HTMLWriter.render_a(file_display, href=uri)

            try:
                log_chunks = parse_file(site, host_name, file_name, hidecontext=False, debug=debug)
                if not log_chunks:
                    continue  # Logfile vanished

                worst_log = get_worst_chunk(log_chunks)
                last_log = get_last_chunk(log_chunks)
                state = worst_log["level"]
                state_name = form_level(state)

                table.cell(_("Level"), state_name, css=["state%d" % state])
                table.cell(_("Logfile"), logfile_link)
                table.cell(_("Last Entry"), form_datetime(last_log["datetime"]))
                table.cell(_("Entries"), len(log_chunks), css=["number"])

            except Exception:
                if debug:
                    raise
                table.cell(_("Level"), "")
                table.cell(_("Logfile"), logfile_link)
                table.cell(_("Last Entry"), "")
                table.cell(_("Entries"), _("Corrupted"))


def show_file(site: SiteId | None, host_name: HostName, file_name: str, *, debug: bool) -> None:
    int_filename = form_file_to_int(file_name)

    title = _("Logfiles of Host %s: %s") % (host_name, int_filename)
    breadcrumb = _show_file_breadcrumb(host_name, title)
    make_header(
        html,
        title,
        breadcrumb,
        _show_file_page_menu(breadcrumb, site, host_name, int_filename),
    )

    if request.has_var("_ack") and not request.var("_do_actions") == _("No"):
        do_log_ack(site, host_name, file_name)
        return

    try:
        log_chunks = parse_file(
            site,
            host_name,
            int_filename,
            hidecontext=request.var("_hidecontext", "no") == "yes",
            debug=debug,
        )
    except Exception as e:
        if debug:
            raise
        html.show_error(_("Unable to show logfile: <b>%s</b>") % e)
        html.footer()
        return

    if log_chunks is None:
        html.show_error(_("The logfile does not exist on site."))
        html.footer()
        return

    if log_chunks == []:
        html.show_message(_("This logfile contains no unacknowledged messages."))
        html.footer()
        return

    html.open_div(id_="logwatch")
    for log in log_chunks:
        html.open_table(class_="groupheader")
        html.open_tr()
        html.td(form_level(log["level"]), class_=form_level(log["level"]))
        html.td(form_datetime(log["datetime"]), class_="date")
        html.close_tr()
        html.close_table()

        html.open_table(class_=["section"])
        for line in log["lines"]:
            html.open_tr(class_=line["class"])
            html.open_td(class_="lines")
            html.icon_button(
                analyse_url(site, host_name, int_filename, line["line"]),
                _("Analyze this line"),
                "analyze",
            )
            html.write_text_permissive(line["line"].replace(" ", "&nbsp;").replace("\1", "<br>"))
            html.close_td()
            html.close_tr()

        html.close_table()

    html.close_div()
    html.footer()


def _show_file_breadcrumb(host_name: HostName, title: str) -> Breadcrumb:
    breadcrumb = make_host_breadcrumb(host_name)
    breadcrumb.append(
        BreadcrumbItem(
            title=_("Log files of host %s") % host_name,
            url=makeuri(request, [("file", "")]),
        )
    )
    breadcrumb.append(make_current_page_breadcrumb_item(title))
    return breadcrumb


def _show_file_page_menu(
    breadcrumb: Breadcrumb, site_id: SiteId | None, host_name: HostName, int_filename: str
) -> PageMenu:
    menu = PageMenu(
        dropdowns=[
            PageMenuDropdown(
                name="logs",
                title=_("Logs"),
                topics=[
                    PageMenuTopic(
                        title=_("This log file"),
                        entries=list(
                            _page_menu_entry_acknowledge(site_id, host_name, int_filename)
                        ),
                    ),
                    PageMenuTopic(
                        title=_("Log files"),
                        entries=[
                            PageMenuEntry(
                                title=_("Log files of host %s") % host_name,
                                icon_name="logwatch",
                                item=make_simple_link(makeuri(request, [("file", "")])),
                            ),
                            PageMenuEntry(
                                title=_("All log files"),
                                icon_name="logwatch",
                                item=make_simple_link(
                                    makeuri(
                                        request,
                                        [("site", ""), ("host", ""), ("file", "")],
                                    )
                                ),
                            ),
                        ],
                    ),
                ],
            ),
            PageMenuDropdown(
                name="related",
                title=_("Related"),
                topics=[
                    PageMenuTopic(
                        title=_("Monitoring"),
                        entries=[
                            PageMenuEntry(
                                title=_("Services of host"),
                                icon_name="services",
                                item=make_simple_link(services_url(site_id, host_name)),
                            ),
                        ],
                    ),
                    PageMenuTopic(
                        title=_("Setup"),
                        entries=[
                            PageMenuEntry(
                                title=_("Analyze host patterns"),
                                icon_name="analyze",
                                item=make_simple_link(analyse_url(site_id, host_name)),
                            ),
                        ],
                    ),
                ],
            ),
        ],
        breadcrumb=breadcrumb,
    )
    _extend_display_dropdown(menu)
    return menu


def _extend_display_dropdown(menu: PageMenu) -> None:
    display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())
    context_hidden = request.var("_hidecontext", "no") == "yes"
    display_dropdown.topics.insert(
        0,
        PageMenuTopic(
            title=_("Context"),
            entries=[
                PageMenuEntry(
                    title=_("Show context"),
                    icon_name="toggle_off" if context_hidden else "toggle_on",
                    item=make_simple_link(
                        makeactionuri(
                            request,
                            transactions,
                            [
                                (
                                    ("_show_backlog", "no")
                                    if context_hidden
                                    else ("_hidecontext", "yes")
                                ),
                            ],
                        )
                    ),
                ),
            ],
        ),
    )


# .
#   .--Acknowledge---------------------------------------------------------.
#   |       _        _                        _          _                 |
#   |      / \   ___| | ___ __   _____      _| | ___  __| | __ _  ___      |
#   |     / _ \ / __| |/ / '_ \ / _ \ \ /\ / / |/ _ \/ _` |/ _` |/ _ \     |
#   |    / ___ \ (__|   <| | | | (_) \ V  V /| |  __/ (_| | (_| |  __/     |
#   |   /_/   \_\___|_|\_\_| |_|\___/ \_/\_/ |_|\___|\__,_|\__, |\___|     |
#   |                                                      |___/           |
#   +----------------------------------------------------------------------+
#   |  Code for acknowleding (i.e. deleting) log files                     |
#   '----------------------------------------------------------------------'


def _page_menu_entry_acknowledge(
    site: SiteId | None = None,
    host_name: HostName | None = None,
    int_filename: str | None = None,
) -> Iterator[PageMenuEntry]:
    if not user.may("general.act") or (host_name and not may_see(site, host_name)):
        return

    if int_filename:
        label = _("Clear log")
    else:
        label = _("Clear logs")

    urivars: HTTPVariables = [("_ack", "1")]
    if int_filename:
        urivars.append(("file", form_file_to_ext(int_filename)))

    ack_msg = _get_ack_msg(host_name, form_file_to_ext(int_filename) if int_filename else None)

    yield PageMenuEntry(
        title=label,
        icon_name="delete",
        item=make_simple_link(
            make_confirm_delete_link(
                url=makeactionuri(request, transactions, urivars),
                title=_("Clear logs by deleting all stored messages"),
                message=_("This affects %s") % ack_msg,
                confirm_button=_("Clear & Delete"),
            )
        ),
        is_shortcut=True,
        is_suggested=True,
    )


def do_log_ack(site: SiteId | None, host_name: HostName | None, file_name: str | None) -> None:
    sites.live().set_auth_domain("action")

    logs_to_ack: list = []
    if not host_name and not file_name:  # all logs on all hosts
        for this_site, this_host, logs in all_logs():
            for int_filename in logs:
                file_display = form_file_to_ext(int_filename)
                logs_to_ack.append((this_site, this_host, int_filename, file_display))

    elif host_name and not file_name:  # all logs on one host
        for int_filename in logfiles_of_host(site, host_name):
            file_display = form_file_to_ext(int_filename)
            logs_to_ack.append((site, host_name, int_filename, file_display))

    elif host_name and file_name:  # one log on one host
        int_filename = form_file_to_int(file_name)
        logs_to_ack = [(site, host_name, int_filename, form_file_to_ext(int_filename))]

    elif file_name is not None:
        for this_site, this_host, logs in all_logs():
            file_display = form_file_to_ext(file_name)
            if file_name in logs:
                logs_to_ack.append((this_site, this_host, file_name, file_display))

    ack_msg = _get_ack_msg(host_name, file_name)
    ack = request.var("_ack")

    if not user.may("general.act"):
        html.h1(_("Permission denied"), class_=["error"])
        html.div(_("You are not allowed to acknowledge %s") % ack_msg, class_=["error"])
        html.footer()
        return

    # filter invalid values
    if ack != "1":
        raise MKUserError("_ack", _("Invalid value for ack parameter."))

    for this_site, this_host, int_filename, display_name in logs_to_ack:
        try:
            acknowledge_logfile(this_site, this_host, int_filename, display_name)
        except Exception as e:
            html.show_error(
                _("The log file <tt>%s</tt> of host <tt>%s</tt> could not be deleted: %s.")
                % (display_name, this_host, e)
            )
            html.footer()
            return

    html.show_message(
        "<b>{}</b><p>{}</p>".format(
            _("Acknowledged %s") % ack_msg,
            _("Acknowledged all messages in %s.") % ack_msg,
        )
    )
    html.footer()


def _get_ack_msg(host_name: HostName | None, file_name: str | None) -> str:
    if not host_name and not file_name:  # all logs on all hosts
        return _("all logfiles on all hosts")

    if host_name and not file_name:  # all logs on one host
        return _("all logfiles of host %s") % host_name

    if host_name and file_name:  # one log on one host
        return _("the log file %s on host %s") % (file_name, host_name)

    return _("log file %s on all hosts") % file_name


def acknowledge_logfile(
    site: SiteId, host_name: HostName, int_filename: str, display_name: str
) -> None:
    if not may_see(site, host_name):
        raise MKAuthException(_("Permission denied."))

    command = f"MK_LOGWATCH_ACKNOWLEDGE;{host_name};{int_filename}"
    sites.live().command("[%d] %s" % (int(time.time()), command), site)


# .
#   .--Parsing-------------------------------------------------------------.
#   |                  ____                _                               |
#   |                 |  _ \ __ _ _ __ ___(_)_ __   __ _                   |
#   |                 | |_) / _` | '__/ __| | '_ \ / _` |                  |
#   |                 |  __/ (_| | |  \__ \ | | | | (_| |                  |
#   |                 |_|   \__,_|_|  |___/_|_| |_|\__, |                  |
#   |                                              |___/                   |
#   +----------------------------------------------------------------------+
#   |  Parsing the contents of a logfile                                   |
#   '----------------------------------------------------------------------'


def parse_file(
    site: SiteId | None,
    host_name: HostName,
    file_name: str,
    *,
    hidecontext: bool,
    debug: bool,
) -> list[dict[str, Any]] | None:
    log_chunks: list[dict[str, Any]] = []
    try:
        chunk: dict[str, Any] | None = None
        lines = get_logfile_lines(site, host_name, file_name)
        if lines is None:
            return None
        # skip hash line. this doesn't exist in older files
        while lines and lines[0].startswith("#"):
            lines = lines[1:]

        for line in lines:
            line = line.strip()
            if line == "":
                continue

            if line[:3] == "<<<":  # new chunk begins
                log_lines: list[dict[str, Any]] = []
                chunk = {"lines": log_lines}
                log_chunks.append(chunk)

                # New header line
                date, logtime, level = line[3:-3].split(" ")

                # Save level as integer to make it better comparable
                if level == "CRIT":
                    chunk["level"] = 2
                elif level == "WARN":
                    chunk["level"] = 1
                elif level == "OK":
                    chunk["level"] = 0
                else:
                    chunk["level"] = 0

                # Gather datetime object
                # Python versions below 2.5 don't provide datetime.datetime.strptime.
                # Use the following instead:
                # chunk['datetime'] = datetime.datetime.strptime(date + ' ' + logtime, "%Y-%m-%d %H:%M:%S")
                chunk["datetime"] = datetime.datetime(
                    *time.strptime(date + " " + logtime, "%Y-%m-%d %H:%M:%S")[0:5]
                )

            elif chunk:  # else: not in a chunk?!
                # Data line
                line_display = line[2:]

                # Classify the line for styling
                if line[0] == "W":
                    line_level = 1
                    line_class = "WARN"

                elif line[0] == "u":
                    line_level = 1
                    line_class = "WARN"

                elif line[0] == "C":
                    line_level = 2
                    line_class = "CRIT"

                elif line[0] == "O":
                    line_level = 0
                    line_class = "OK"

                elif not hidecontext:
                    line_level = 0
                    line_class = "context"

                else:
                    continue  # ignore this line

                log_lines.append({"level": line_level, "class": line_class, "line": line_display})
    except Exception as e:
        if debug:
            raise
        raise MKGeneralException(_("Cannot parse log file %s: %s") % (file_name, e))

    return log_chunks


def get_worst_chunk(log_chunks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    worst_level = 0
    worst_log = log_chunks[0]

    for chunk in log_chunks:
        for line in chunk["lines"]:
            if line["level"] >= worst_level:
                worst_level = line["level"]
                worst_log = chunk

    return worst_log


def get_last_chunk(log_chunks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    last_log = None
    last_datetime = None

    for chunk in log_chunks:
        if not last_datetime or chunk["datetime"] > last_datetime:
            last_datetime = chunk["datetime"]
            last_log = chunk

    if last_log is None:
        raise ValueError("No last log found, this should not happen.")

    return last_log


# .
#   .--Constants-----------------------------------------------------------.
#   |              ____                _              _                    |
#   |             / ___|___  _ __  ___| |_ __ _ _ __ | |_ ___              |
#   |            | |   / _ \| '_ \/ __| __/ _` | '_ \| __/ __|             |
#   |            | |__| (_) | | | \__ \ || (_| | | | | |_\__ \             |
#   |             \____\___/|_| |_|___/\__\__,_|_| |_|\__|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Definition of various constants - also used by Setup                  |
#   '----------------------------------------------------------------------'

nagios_illegal_chars = "`;~!$%^&*|'\"<>?,()="


def logwatch_level_name(level: str) -> str:
    return {
        "O": "OK",
        "W": "WARN",
        "C": "CRIT",
        "I": "IGNORE",
    }[level]


def level_name(level: str) -> str:
    if level == "W":
        return "WARN"
    if level == "C":
        return "CRIT"
    if level == "O":
        return "OK"
    return "OK"


def level_state(level: str) -> int:
    if level == "W":
        return 1
    if level == "C":
        return 2
    if level == "O":
        return 0
    return 0


# .
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Various helper functions                                            |
#   '----------------------------------------------------------------------'


def form_level(level: int) -> str:
    levels = ["OK", "WARN", "CRIT", "UNKNOWN"]
    return levels[level]


def form_file_to_int(f: str) -> str:
    return f.replace("/", "\\")


def form_file_to_ext(f: str) -> str:
    return f.replace("\\", "/")


def form_datetime(dt: datetime.datetime, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return dt.strftime(fmt)


# .
#   .--Access--------------------------------------------------------------.
#   |                       _                                              |
#   |                      / \   ___ ___ ___  ___ ___                      |
#   |                     / _ \ / __/ __/ _ \/ __/ __|                     |
#   |                    / ___ \ (_| (_|  __/\__ \__ \                     |
#   |                   /_/   \_\___\___\___||___/___/                     |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Code for fetching data and for acknowledging. Now all via Live-     |
#   |  status.                                                             |
#   '----------------------------------------------------------------------'


def logfiles_of_host(site: SiteId | None, host_name: HostName) -> list[str]:
    if site:  # Honor site hint if available
        sites.live().set_only_sites([site])
    file_names: list[str] = sites.live().query_value(
        "GET hosts\n"
        "Columns: mk_logwatch_files\n"
        "Filter: name = %s\n" % livestatus.lqencode(host_name)
    )
    if site:  # Honor site hint if available
        sites.live().set_only_sites(None)
    return file_names


def get_logfile_lines(site: SiteId | None, host_name: HostName, file_name: str) -> list[str] | None:
    if site:  # Honor site hint if available
        sites.live().set_only_sites([site])
    query = "GET hosts\nColumns: mk_logwatch_file:file:{}/{}\nFilter: name = {}\n".format(
        livestatus.lqencode(host_name),
        livestatus.lqencode(file_name.replace("\\", "\\\\").replace(" ", "\\s")),
        livestatus.lqencode(host_name),
    )
    file_content = sites.live().query_value(query)
    if site:  # Honor site hint if available
        sites.live().set_only_sites(None)
    if file_content is None:
        return None
    return [line.decode("utf-8") for line in file_content.splitlines()]


def all_logs() -> list[tuple[SiteId, HostName, list[str]]]:
    sites.live().set_prepend_site(True)
    rows = sites.live().query("GET hosts\nColumns: name mk_logwatch_files\n")
    sites.live().set_prepend_site(False)
    return cast(list[tuple[SiteId, HostName, list[str]]], rows)


def may_see(site: SiteId | None, host_name: HostName) -> bool:
    if user.may("general.see_all"):
        return True

    try:
        if site:
            sites.live().set_only_sites([site])
        # Note: This query won't work in a distributed setup and no site given as argument
        # livestatus connection is setup with AuthUser
        num_hosts: int = sites.live().query_value(
            "GET hosts\nStats: state >= 0\nFilter: name = %s\n" % livestatus.lqencode(host_name)
        )
        return num_hosts > 0
    finally:
        sites.live().set_only_sites(None)


# Tackle problem, where some characters are missing in the service
# description
def find_matching_logfile(site: SiteId | None, host_name: HostName, file_name: str) -> str:
    existing_files = logfiles_of_host(site, host_name)
    if file_name in existing_files:
        return file_name  # Most common case

    for logfile_name in existing_files:
        if remove_illegal_service_characters(logfile_name) == file_name:
            return logfile_name

    # Not found? Fall back to original name. Logfile might be cleared.
    return file_name


def remove_illegal_service_characters(file_name: str) -> str:
    return "".join([c for c in file_name if c not in nagios_illegal_chars])
