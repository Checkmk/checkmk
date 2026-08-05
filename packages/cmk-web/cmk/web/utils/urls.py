#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import html
import urllib.parse
from collections.abc import Collection, Mapping, Sequence
from functools import lru_cache
from typing import assert_never, Literal

from flask import session

import cmk.ccc.regex
from cmk.web.context import RequestProtocol
from cmk.web.exceptions import MKNotFound

HTTPVariable = tuple[str, str | int | None]


def make_contextless_url(filename: str, variables: Sequence[HTTPVariable]) -> str:
    """Build a ``filename?key=value&...`` URL independent of the current request.

    >>> make_contextless_url("werk.py", [("werk", 1234)])
    'werk.py?werk=1234'
    >>> make_contextless_url("wato.py", [])
    'wato.py'
    """
    encoded = [(key, str(value)) for key, value in variables if value is not None]
    if not encoded:
        return filename
    return filename + "?" + urllib.parse.urlencode(encoded)


def is_allowed_url(
    url: str, cross_domain: bool = False, schemes: Collection[str] | None = None
) -> bool:
    """Check if url is allowed

    >>> is_allowed_url("http://checkmk.com/")
    False
    >>> is_allowed_url("http://checkmk.com/", cross_domain=True, schemes=["http", "https"])
    True
    >>> is_allowed_url("/checkmk/", cross_domain=True, schemes=["http", "https"])
    True
    >>> is_allowed_url("//checkmk.com/", cross_domain=True)
    True
    >>> is_allowed_url("/foobar")
    True
    >>> is_allowed_url("//user:password@domain/", cross_domain=True)
    True
    >>> is_allowed_url("javascript:alert(1)")
    False
    >>> is_allowed_url("javascript:alert(1)", cross_domain=True, schemes=["javascript"])
    True
    >>> is_allowed_url('someXSSAttempt?"><script>alert(1)</script>')
    False
    """

    try:
        parsed = urllib.parse.urlparse(html.unescape(url))
    except ValueError:
        return False

    if not cross_domain and parsed.netloc != "":
        return False

    if schemes is None and parsed.scheme != "":
        return False
    if schemes is not None and parsed.scheme and parsed.scheme not in schemes:
        return False

    urlchar_regex = cmk.ccc.regex.regex(cmk.ccc.regex.URL_CHAR_REGEX)
    for part in parsed:
        if not part:
            continue
        if not urlchar_regex.match(part):
            return False

    return True


QueryVars = Mapping[str, Sequence[str]]

_ALWAYS_SAFE = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-~ ")
_ALWAYS_SAFE_BYTES = bytes(_ALWAYS_SAFE)
_QUOTED = {b: chr(b) if b in _ALWAYS_SAFE else f"%{b:02X}" for b in range(256)}


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


def _quote_pair(varname: str, value: None | int | str) -> str:
    assert isinstance(varname, str)
    if isinstance(value, int):
        return f"{quote_plus(varname)}={quote_plus(str(value))}"
    if value is None:
        # TODO: This is not ideal and should better be cleaned up somehow. Shouldn't
        # variables with None values simply be skipped? We currently can not find the
        # call sites easily. This may be cleaned up once we establish typing. Until then
        # we need to be compatible with the previous behavior.
        return "%s=" % quote_plus(varname)
    return f"{quote_plus(varname)}={quote_plus(value)}"


# TODO: Inspect call sites to this function: Most of them can be replaced with makeuri_contextless
def urlencode_vars(vars_: Sequence[tuple[str, int | str | None]]) -> str:
    """Convert a mapping object or a sequence of two-element tuples to a “percent-encoded” string"""
    return "&".join([_quote_pair(var, val) for var, val in sorted(vars_)])


# TODO: Inspect call sites to this function: Most of them can be replaced with makeuri_contextless
def urlencode(value: str | None) -> str:
    """Replace special characters in string using the %xx escape."""
    return "" if value is None else quote_plus(value)


_TRUTHY_QUERY_VALUES = frozenset({"1", "t", "true", "y", "yes", "on"})


def is_truthy_query_value(value: str | None) -> bool:
    """Whether a query-parameter value is one of the conventional truthy strings."""
    return value is not None and value.strip().lower() in _TRUTHY_QUERY_VALUES


def is_kiosk_request(request: RequestProtocol) -> bool:
    """Whether the request should render in chromeless 'kiosk' mode.

    Triggers when:
      * a truthy ``?kiosk=<value>`` was supplied, or
      * the requested page is a dashboard widget iframe endpoint
        (``widget_iframe_*``). These endpoints are always embedded inside a
        dashboard that already renders the main navigation; rendering it
        again inside each iframe would duplicate the chrome.
    """
    if is_truthy_query_value(request.var("kiosk")):
        return True
    file_name = requested_file_name(request)
    return file_name.startswith("widget_iframe_")


def add_kiosk_to_url(url: str) -> str:
    """Set kiosk=true on a URL, deduping any existing kiosk param and respecting fragments."""
    parts = urllib.parse.urlsplit(url)
    qs_map = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
    qs_map["kiosk"] = "true"
    query = urllib.parse.urlencode(list(qs_map.items()))
    return urllib.parse.urlunsplit(parts._replace(query=query))


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
            cmk.web.exceptions.MKNotFound: Not found

            >>> _file_name_from_path("/NO_SITE/check_mk/foo/bar", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.web.exceptions.MKNotFound: Not found

            >>> _file_name_from_path("/NO_SITE/check_mk/.py", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.web.exceptions.MKNotFound: Not found

        Not so sensible values. Not sure where this would occur, but tests were in place which
        required this.

            >>> _file_name_from_path("/NO_SITE/check_mk/should_match.py/", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.web.exceptions.MKNotFound: Not found

        `file_name_and_query_vars_from_url` expects relative URLs, so we sadly need to support
        those as well.

            >>> _file_name_from_path("wato.py")
            'wato'

        This works as expected.

            >>> _file_name_from_path(".py", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.web.exceptions.MKNotFound: Not found
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
    elif on_error == "raise":
        raise MKNotFound("Not found")
    elif on_error == "ignore":
        result = default
    else:
        assert_never(on_error)

    return result


def requested_file_name(
    request: RequestProtocol,
    on_error: Literal["raise", "ignore"] = "ignore",
    default: str = "index",
) -> str:
    """Derive the "file name" from the path of the given request.

    See ``_file_name_from_path`` for the path parsing itself, including what
    ``on_error`` and ``default`` do.
    """
    return _file_name_from_path(request.path, on_error=on_error, default=default)


def append_site_from_request(
    request: RequestProtocol, url_vars: Sequence[tuple[str, int | str | None]]
) -> Sequence[tuple[str, int | str | None]]:
    """Append the given request's site parameter to URL variables if present."""
    if site := request.var("site"):
        return [*url_vars, ("site", site)]
    return url_vars


def makeuri(
    request: RequestProtocol,
    addvars: Sequence[tuple[str, int | str | None]],
    filename: str | None = None,
    remove_prefix: str | None = None,
    delvars: Sequence[str] | None = None,
) -> str:
    new_vars = [nv[0] for nv in addvars]
    vars_: Sequence[tuple[str, int | str | None]] = [
        (v, val)
        for v, val in request.itervars()
        if v[0] != "_" and v not in new_vars and not (delvars and v in delvars)
    ]
    if remove_prefix is not None:
        vars_ = [i for i in vars_ if not i[0].startswith(remove_prefix)]
    vars_ = [*vars_, *addvars]
    if filename is None:
        filename = urlencode(requested_file_name(request)) + ".py"
    if vars_:
        return filename + "?" + urlencode_vars(vars_)
    return filename


def makeuri_contextless(
    request: RequestProtocol,
    vars_: Sequence[tuple[str, int | str | None]],
    filename: str | None = None,
) -> str:
    if not filename:
        filename = requested_file_name(request) + ".py"
    if vars_:
        return filename + "?" + urlencode_vars(vars_)
    return filename


def makeactionuri(
    request: RequestProtocol,
    transid: str,
    addvars: Sequence[tuple[str, int | str | None]],
    filename: str | None = None,
    delvars: Sequence[str] | None = None,
) -> str:
    session_vars: list[tuple[str, int | str | None]] = [("_transid", transid)]
    if session and hasattr(session, "session_info"):
        session_vars.append(("_csrf_token", session.session_info.csrf_token))

    return makeuri(request, [*addvars, *session_vars], filename=filename, delvars=delvars)


def makeactionuri_contextless(
    request: RequestProtocol,
    transid: str,
    addvars: Sequence[tuple[str, int | str | None]],
    filename: str | None = None,
) -> str:
    session_vars: list[tuple[str, int | str | None]] = [("_transid", transid)]
    if session and hasattr(session, "session_info"):
        session_vars.append(("_csrf_token", session.session_info.csrf_token))

    return makeuri_contextless(request, [*addvars, *session_vars], filename=filename)


def makeuri_contextless_rulespec_group(
    request: RequestProtocol,
    group_name: str,
) -> str:
    return makeuri_contextless(
        request,
        [("group", group_name), ("mode", "rulesets")],
        filename="wato.py",
    )


def file_name_and_query_vars_from_url(url: str) -> tuple[str, QueryVars]:
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
