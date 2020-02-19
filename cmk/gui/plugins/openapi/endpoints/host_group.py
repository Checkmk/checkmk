#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional  # pylint: disable=unused-import

from cmk.gui.watolib.groups import load_host_group_information, edit_group
from cmk.gui.wsgi.types import RFC7662, HostGroup  # pylint: disable=unused-import


def create(ident, body, user=None, token_info=None):
    raise Exception


def post(ident, body, user=None, token_info=None):
    # type: (str, HostGroup, Optional[str], Optional[RFC7662]) -> HostGroup
    edit_group(ident, 'host', body)
    return get(ident)


def get(ident, user=None, token_info=None):
    # type: (str, Optional[str], Optional[RFC7662]) -> HostGroup
    groups = load_host_group_information()
    return groups[ident]
