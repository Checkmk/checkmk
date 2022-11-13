#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import urllib.parse
from enum import Enum
from functools import lru_cache
from typing import Literal, Mapping, Optional, Sequence, Tuple, Union

from typing_extensions import assert_never

from cmk.gui.exceptions import MKNotFound
from cmk.gui.http import Request
from cmk.gui.logged_in import user
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.utils.escaping import escape_text
from cmk.gui.utils.transaction_manager import TransactionManager

QueryVars = Mapping[str, Sequence[str]]

_ALWAYS_SAFE = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZ" b"abcdefghijklmnopqrstuvwxyz" b"0123456789" b"_.-~" b" "
)
_ALWAYS_SAFE_BYTES = bytes(_ALWAYS_SAFE)
_QUOTED = {b: chr(b) if b in _ALWAYS_SAFE else "%{:02X}".format(b) for b in range(256)}


def quote(string: str) -> str:
    """More performant version of urllib.parse equivalent to the call quote(string, safe=' ')."""
    if not string:
        return string
    bs = string.encode("utf-8", "strict")
    if not bs.rstrip(_ALWAYS_SAFE_BYTES):
        return bs.decode()
    return "".join([_QUOTED[char] for char in bs])


@lru_cache(maxsize=4096)
def quote_plus(string: str) -> str:
    """More performant version of urllib.parse equivalent to the call quote_plus(string)."""
    if " " not in string:
        return quote(string)
    return quote(string).replace(" ", "+")


def _quote_pair(varname: str, value: Union[None, int, str]) -> str:
    assert isinstance(varname, str)
    if isinstance(value, int):
        return "%s=%s" % (quote_plus(varname), quote_plus(str(value)))
    if value is None:
        # TODO: This is not ideal and should better be cleaned up somehow. Shouldn't
        # variables with None values simply be skipped? We currently can not find the
        # call sites easily. This may be cleaned up once we establish typing. Until then
        # we need to be compatible with the previous behavior.
        return "%s=" % quote_plus(varname)
    return "%s=%s" % (quote_plus(varname), quote_plus(value))


# TODO: Inspect call sites to this function: Most of them can be replaced with makeuri_contextless
def urlencode_vars(vars_: HTTPVariables) -> str:
    """Convert a mapping object or a sequence of two-element tuples to a “percent-encoded” string"""
    return "&".join([_quote_pair(var, val) for var, val in sorted(vars_)])


# TODO: Inspect call sites to this function: Most of them can be replaced with makeuri_contextless
def urlencode(value: Optional[str]) -> str:
    """Replace special characters in string using the %xx escape."""
    return "" if value is None else quote_plus(value)


def _file_name_from_path(
    path: str,
    on_error: Literal["raise", "ignore"] = "ignore",
    default: str = "index",
) -> str:
    """Derive a "file name" from the path.

    These no longer map to real file names, but rather to the page handlers attached to the names.

    Args:
        path:
            The path, without query string, and without server portion.

    Returns:
        The "file name" as a string.

    Examples:

        Sensible values.

            >>> _file_name_from_path("/NO_SITE/check_mk/should_match.py")
            'should_match'

            >>> _file_name_from_path("/NO_SITE/check_mk/")
            'index'

            >>> _file_name_from_path("/NO_SITE/check_mk/should_match.py/NO_SITE/check_mk/blubb.py", on_error="ignore")
            'index'

            >>> _file_name_from_path("/NO_SITE/check_mk/should_match.py/NO_SITE/check_mk/blubb.py", on_error="ignore", default="not_found")
            'not_found'

            >>> _file_name_from_path("/NO_SITE/check_mk/should_match.py/NO_SITE/check_mk/blubb.py", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKNotFound: Not found

            >>> _file_name_from_path("/NO_SITE/check_mk/foo/bar", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKNotFound: Not found

            >>> _file_name_from_path("/NO_SITE/check_mk/.py", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKNotFound: Not found

        Not so sensible values. Not sure where this would occur, but tests were in place which
        required this.

            >>> _file_name_from_path("/NO_SITE/check_mk/should_match.py/", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKNotFound: Not found

        `file_name_and_query_vars_from_url` expects relative URLs, so we sadly need to support
        those as well.

            >>> _file_name_from_path("wato.py")
            'wato'

        This works as expected.

            >>> _file_name_from_path(".py", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKNotFound: Not found
    """
    parts = path.split("/")
    if len(parts) in (1, 4) and len(parts[-1]) > 3 and parts[-1].endswith(".py"):
        # If it is a relative url or a URL like /site/check_mk/file.py and the filename is not just
        # the extension (like /site/check_mk/.py) then we have a filename.
        result = parts[-1][:-3]
    elif len(parts) < 5 and not parts[-1]:
        # If we have a "normal" url and not an excessive amount of paths (probably a duplication)
        # and the last part is empty, we have an "index" URL.
        result = "index"
    else:
        if on_error == "raise":  # pylint: disable=no-else-raise
            raise MKNotFound("Not found")
        elif on_error == "ignore":
            result = default
        else:
            assert_never(on_error)
            raise RuntimeError("To make pylint happy")

    return result


def requested_file_name(
    request: Request, on_error: Literal["raise", "ignore"] = "ignore", default: str = "index"
) -> str:
    """Convenience wrapper around _file_name_from_path

    Args:
        request:
            A Werkzeug or Flask request wrapper.

    Returns:
        The "file name".

    Examples:

        >>> from unittest.mock import Mock
        >>> requested_file_name(Mock(path="/dev/check_mk/foo_bar.py"))
        'foo_bar'

        >>> requested_file_name(Mock(path="/dev/check_mk/foo_bar.py/"), on_error="raise")
        Traceback (most recent call last):
        ...
        cmk.gui.exceptions.MKNotFound: Not found

        >>> requested_file_name(Mock(path="/dev/check_mk/foo_bar.py/foo"), on_error="raise")
        Traceback (most recent call last):
        ...
        cmk.gui.exceptions.MKNotFound: Not found

    """
    return _file_name_from_path(request.path, on_error=on_error, default=default)


def requested_file_with_query(request: Request) -> str:
    """Returns a string containing the requested file name and query to be used in hyperlinks"""
    file_name = requested_file_name(request)
    query = request.query_string.decode(request.charset)
    return f"{file_name}.py?{query}"


def makeuri(
    request: Request,
    addvars: HTTPVariables,
    filename: Optional[str] = None,
    remove_prefix: Optional[str] = None,
    delvars: Optional[Sequence[str]] = None,
) -> str:
    new_vars = [nv[0] for nv in addvars]
    vars_: HTTPVariables = [
        (v, val)
        for v, val in request.itervars()
        if v[0] != "_" and v not in new_vars and not (delvars and v in delvars)
    ]
    if remove_prefix is not None:
        vars_ = [i for i in vars_ if not i[0].startswith(remove_prefix)]
    vars_ = vars_ + addvars
    if filename is None:
        filename = urlencode(requested_file_name(request)) + ".py"
    if vars_:
        return filename + "?" + urlencode_vars(vars_)
    return filename


def makeuri_contextless(
    request: Request,
    vars_: HTTPVariables,
    filename: Optional[str] = None,
) -> str:
    if not filename:
        filename = requested_file_name(request) + ".py"
    if vars_:
        return filename + "?" + urlencode_vars(vars_)
    return filename


def makeactionuri(
    request: Request,
    transaction_manager: TransactionManager,
    addvars: HTTPVariables,
    filename: Optional[str] = None,
    delvars: Optional[Sequence[str]] = None,
) -> str:
    return makeuri(
        request,
        addvars + [("_transid", transaction_manager.get())],
        filename=filename,
        delvars=delvars,
    )


def makeactionuri_contextless(
    request: Request,
    transaction_manager: TransactionManager,
    addvars: HTTPVariables,
    filename: Optional[str] = None,
) -> str:
    return makeuri_contextless(
        request,
        addvars + [("_transid", transaction_manager.get())],
        filename=filename,
    )


def makeuri_contextless_rulespec_group(
    request: Request,
    group_name: str,
) -> str:
    return makeuri_contextless(
        request,
        [("group", group_name), ("mode", "rulesets")],
        filename="wato.py",
    )


def make_confirm_link(*, url: str, message: str) -> str:
    return "javascript:cmk.forms.confirm_link(%s, %s),cmk.popup_menu.close_popup()" % (
        json.dumps(quote_plus(url)),
        json.dumps(escape_text(message)),
    )


def file_name_and_query_vars_from_url(url: str) -> Tuple[str, QueryVars]:
    """Deconstruct a (potentially relative) URL.

    Args:
        url:
            A URL path without the server portion, but optionally including the `query string`.

    Returns:
        A tuple of "file name" and a parsed query string dict.

    Examples:

        With path and query string (relative)

            >>> file_name_and_query_vars_from_url("wato.py?foo=bar")
            ('wato', {'foo': ['bar']})

        With path and query string (absolute)

            >>> file_name_and_query_vars_from_url("/dev/check_mk/wato.py?foo=bar")
            ('wato', {'foo': ['bar']})

        Without path

            >>> file_name_and_query_vars_from_url("?foo=bar")
            ('index', {'foo': ['bar']})

        Without path and without query string

            >>> file_name_and_query_vars_from_url("")
            ('index', {})

    """
    split_result = urllib.parse.urlsplit(url)
    return _file_name_from_path(split_result.path), urllib.parse.parse_qs(split_result.query)


class DocReference(Enum):
    """All references to the documentation - e.g. "[intro_setup#install|Welcome]" - must be listed
    in DocReference. The string must consist of the page name and if an anchor exists the anchor
    name joined by a '#'. E.g. INTRO_SETUP_INSTALL = "intro_setup#install"""

    ACTIVE_CHECKS = "active_checks"
    ACTIVE_CHECKS_MRPE = "active_checks#mrpe"
    AGENT_LINUX = "agent_linux"
    AGENT_WINDOWS = "agent_windows"
    ALERT_HANDLERS = "alert_handlers"
    BI = "bi"  # Business Intelligence
    DASHBOARD_HOST_PROBLEMS = "dashboards#host_problems"
    DCD = "dcd"  # dynamic host configuration
    DEVEL_CHECK_PLUGINS = "devel_check_plugins"
    DISTRIBUTED_MONITORING = "distributed_monitoring"
    GRAPHING_RRDS = "graphing#rrds"
    # TODO: Check whether these anchors on the intro page exist and fix/remove broken ones.
    INTRO_CREATING_FOLDERS = "intro#Creating folders"
    INTRO_FOLDERS = "intro#folders"
    INTRO_LINUX = "intro#linux"
    INTRO_SERVICES = "intro#services"
    INTRO_WELCOME = "intro_welcome"
    LDAP = "ldap"
    PIGGYBACK = "piggyback"
    REGEXES = "regexes"
    REST_API = "rest_api"
    WATO_HOSTS = "wato_hosts"
    WATO_SERVICES = "wato_services"
    WATO_SERVICES_ENFORCED_SERVICES = "wato_services#enforced_services"
    WATO_USER_2FA = "wato_user#2fa"


def doc_reference_url(doc_ref: Optional[DocReference] = None) -> str:
    base = user.get_docs_base_url()
    if doc_ref is None:
        return base
    if "#" not in doc_ref.value:
        return f"{base}/{doc_ref.value}.html"
    return f"{base}/{doc_ref.value.replace('#', '.html#', 1)}"
