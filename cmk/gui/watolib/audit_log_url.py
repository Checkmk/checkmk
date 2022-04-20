#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.globals import request
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.watolib.objref import ObjectRef


def make_object_audit_log_url(object_ref: ObjectRef) -> str:
    return makeuri_contextless(
        request,
        [
            ("mode", "auditlog"),
            ("options_object_type", DropdownChoice.option_id(object_ref.object_type)),
            ("options_object_ident", object_ref.ident),
        ],
        filename="wato.py",
    )
