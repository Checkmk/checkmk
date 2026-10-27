#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup, Tag

from cmk.gui import hooks
from cmk.gui.config import Config
from cmk.gui.exceptions import HTTPRedirect
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.type_defs import ActionResult
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.watolib.mode import WatoMode

type TableRow = dict[str, Tag]


def page_context(config: Config) -> PageContext:
    return PageContext(
        config=config,
        request=request,
        transactions=transactions,
        session=session,
        user_permissions=UserPermissions.from_config(config, all_permissions()),
    )


def render_page[T](mode: WatoMode[T], config: Config) -> str:
    with output_funnel.plugged():
        mode.page(config)
        return "".join(output_funnel.drain())


def set_request_vars(**variables: str) -> None:
    for name, value in variables.items():
        request.set_var(name, value)


def submit(**variables: str) -> None:
    """Make the request look like a confirmed form submission of the logged-in user."""
    set_request_vars(**variables)
    transactions.ignore()
    request.set_var("_transid", "-1")
    request.set_var("_csrf_token", session.session_info.csrf_token)


def end_request() -> None:
    """Ends the request, e.g. the one showing a page before submitting its form

    Like after a real one, the next request no longer sees what it memoized, e.g. loaded
    configuration, but the changes made meanwhile."""
    hooks.call("request-end")


def _query_vars(url: str) -> dict[str, str]:
    return {name: values[0] for name, values in parse_qs(urlparse(url).query).items()}


def redirect_vars(result: ActionResult) -> dict[str, str]:
    assert isinstance(result, HTTPRedirect)
    return _query_vars(result.url)


def form_values(page: str, form_name: str) -> dict[str, str]:
    """The values a browser would submit for the form, as rendered, without any button."""
    form = BeautifulSoup(page, "html.parser").select_one(f"form[name={form_name}]")
    assert form is not None, f"form {form_name!r} not rendered"
    values: dict[str, str] = {}
    for field in form.select("input, select, textarea"):
        if not isinstance(name := field.get("name"), str) or field.has_attr("disabled"):
            continue
        if field.name == "select" and field.has_attr("multiple"):
            # Only the selected options are submitted, none at all if nothing is selected.
            selected = field.select("option[selected]")
            assert len(selected) <= 1, f"several values selected in {name!r}"
            if selected:
                values[name] = str(selected[0].get("value", ""))
        elif field.name == "select":
            option = field.select_one("option[selected]") or field.select_one("option")
            if option is not None:
                values[name] = str(option.get("value", ""))
        elif field.name == "textarea":
            values[name] = field.text
        elif field.get("type") in ("submit", "button", "image"):
            continue
        elif field.get("type") in ("checkbox", "radio"):
            if field.has_attr("checked"):
                values[name] = str(field.get("value", "on"))
        else:
            values[name] = str(field.get("value", ""))
    return values


def error_messages(page: str) -> list[str]:
    """The error messages the page shows, e.g. the one refusing a submitted form"""
    return [div.get_text() for div in BeautifulSoup(page, "html.parser").select("div.error")]


def data_table(page: str, title: str | None = None) -> Tag:
    """The titled table, or the first table of a page whose table has no title."""
    soup = BeautifulSoup(page, "html.parser")
    if title is None:
        table = soup.select_one("table.data")
    else:
        # Some titles carry an icon link, so compare the text rather than the string
        heading = soup.find(lambda tag: tag.name == "h3" and tag.get_text(strip=True) == title)
        assert isinstance(heading, Tag), f"table {title!r} not rendered"
        table = heading.find_next("table", class_="data")
    assert isinstance(table, Tag), f"table {title!r} not rendered"
    return table


def table_rows(page: str, title: str | None = None) -> list[TableRow]:
    """The data rows of the table, keyed by column header.

    Columns whose header is not unique, e.g. several without a title, are left out; check
    them through data_table. Empty spacer rows and detail rows spanning the whole table are
    skipped."""
    table = data_table(page, title)
    headers = [th.get_text(strip=True) for th in table.select("thead th")]
    unique = {header for header in headers if headers.count(header) == 1}
    rows = []
    for row in table.find_all("tr", class_="data", recursive=False):
        cells = row.find_all("td", recursive=False)
        if not cells or (len(cells) == 1 and cells[0].get("colspan") == str(len(headers))):
            continue
        rows.append(
            {header: cell for header, cell in zip(headers, cells, strict=True) if header in unique}
        )
    return rows


def link_vars(element: Tag) -> dict[str, str]:
    """The query variables of the first link in the element."""
    link = element.select_one("a[href]")
    assert link is not None, "no link rendered"
    return _query_vars(str(link["href"]))


def icon_titles(element: Tag) -> list[str]:
    """The tooltips of the icons, which carry their title in the Vue component data."""
    return [
        str(title)
        for icon in element.select("cmk-static-icon, cmk-dynamic-icon")
        if (title := json.loads(str(icon["data"])).get("title"))
    ]
