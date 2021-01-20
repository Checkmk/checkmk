#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Mapping, Optional, Sequence, Tuple
import urllib.parse
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.http import Request

from cmk.gui.utils.transaction_manager import TransactionManager
from cmk.gui.utils.url_encoder import URLEncoder
from cmk.gui.escaping import escape_text

QueryVars = Mapping[str, Sequence[str]]


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
        if v[0] != "_" and v not in new_vars and (not delvars or v not in delvars)
    ]
    if remove_prefix is not None:
        vars_ = [i for i in vars_ if not i[0].startswith(remove_prefix)]
    vars_ = vars_ + addvars
    if filename is None:
        filename = URLEncoder.urlencode(requested_file_name(request)) + ".py"
    if vars_:
        return filename + "?" + URLEncoder.urlencode_vars(vars_)
    return filename


def makeuri_contextless(
    request: Request,
    vars_: HTTPVariables,
    filename: Optional[str] = None,
) -> str:
    if not filename:
        filename = requested_file_name(request) + '.py'
    if vars_:
        return filename + "?" + URLEncoder.urlencode_vars(vars_)
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
        [('group', group_name), ('mode', 'rulesets')],
        filename='wato.py',
    )


def make_confirm_link(*, url: str, message: str) -> str:
    return "javascript:cmk.forms.confirm_link(%s, %s),cmk.popup_menu.close_popup()" % (
        json.dumps(url),
        json.dumps(escape_text(message)),
    )


def file_name_and_query_vars_from_url(url: str) -> Tuple[str, QueryVars]:
    split_result = urllib.parse.urlsplit(url)
    return _file_name_from_path(split_result.path), urllib.parse.parse_qs(split_result.query)
