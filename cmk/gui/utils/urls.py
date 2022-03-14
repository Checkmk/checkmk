#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import urllib.parse
from functools import lru_cache
from typing import Mapping, Optional, Sequence, Tuple, Union

from cmk.gui.globals import user
from cmk.gui.http import Request
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


def _quote_pair(varname: str, value: Union[None, int, str]):
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


def _file_name_from_path(path: str) -> str:
    parts = path.rstrip("/").split("/")
    file_name = "index"
    if parts[-1].endswith(".py") and len(parts[-1]) > 3:
        # Regular pages end with .py - Strip it away to get the page name
        file_name = parts[-1][:-3]
    return file_name


def requested_file_name(request: Request) -> str:
    return _file_name_from_path(request.requested_file)


def requested_file_with_query(request: Request) -> str:
    """Returns a string containing the requested file name and query to be used in hyperlinks"""
    file_name, query = requested_file_name(request), request.query_string.decode(request.charset)
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
):
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
    split_result = urllib.parse.urlsplit(url)
    return _file_name_from_path(split_result.path), urllib.parse.parse_qs(split_result.query)


def manual_reference_url(
    article_name: Optional[str] = None, anchor_name: Optional[str] = None
) -> str:
    if article_name is None:
        return user.get_docs_base_url()
    anchor: str = "" if anchor_name is None else ("#" + anchor_name)
    return "%s/%s.html%s" % (user.get_docs_base_url(), article_name, anchor)
