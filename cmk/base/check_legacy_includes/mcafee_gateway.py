#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file


def inventory_mcafee_gateway_generic(info):
    return [(None, {})]


#   .--web-----------------------------------------------------------------.
#   |                                      _                               |
#   |                        __      _____| |__                            |
#   |                        \ \ /\ / / _ \ '_ \                           |
#   |                         \ V  V /  __/ |_) |                          |
#   |                          \_/\_/ \___|_.__/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# There are a few different fields in the related MIB:
# Statistics, HTTP, HTTPs, FTP, Miscellaneous
# Future extensions: each field one check
# mcafee_webgateway_http, mcafee_webgateway_https, mcafee_webgateway_ftp


def scan_mcafee_webgateway(oid):
    return "mcafee web gateway" in oid(".1.3.6.1.2.1.1.1.0").lower()


# .
#   .--email---------------------------------------------------------------.
#   |                                           _ _                        |
#   |                       ___ _ __ ___   __ _(_) |                       |
#   |                      / _ \ '_ ` _ \ / _` | | |                       |
#   |                     |  __/ | | | | | (_| | | |                       |
#   |                      \___|_| |_| |_|\__,_|_|_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


# migrated to cmk/base/plugins/agent_based/utils/mcafee_gateway.py
def scan_mcafee_emailgateway(oid):
    return "mcafee email gateway" in oid(".1.3.6.1.2.1.1.1.0").lower()
