#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, Sequence
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.http import Request

from cmk.gui.utils.transaction_manager import TransactionManager
from cmk.gui.utils.url_encoder import URLEncoder


def requested_file_name(request: Request) -> str:
    parts = request.requested_file.rstrip("/").split("/")

    if len(parts) == 3 and parts[-1] == "check_mk":
        # Load index page when accessing /[site]/check_mk
        file_name = "index"

    elif parts[-1].endswith(".py"):
        # Regular pages end with .py - Stript it away to get the page name
        file_name = parts[-1][:-3]
        if file_name == "":
            file_name = "index"

    else:
        file_name = "index"

    return file_name


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


def makeuri_contextless_ruleset_group(
    request: Request,
    group_name: str,
):
    return makeuri_contextless(
        request,
        [('group', group_name), ('mode', 'rulesets')],
        filename='wato.py',
    )
