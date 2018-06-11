#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk_base.config import monitoring_core


# TODO: The "config" literal should really be centralized somehow.
def _cmc_file(options):
    return options["cmc-file"] if options and "cmc-file" in options else "config"


def _create_config_hook(options):
    if monitoring_core == "cmc":
        from cmk_base.cee.core_cmc import create_config_hook as cch
        create_config_hook = lambda: cch(_cmc_file(options))
    else:
        from cmk_base.core_nagios import create_config_hook
    return create_config_hook


def _precompile_hook():
    if monitoring_core == "cmc":
        from cmk_base.cee.core_cmc import precompile_hook
    else:
        from cmk_base.core_nagios import precompile_hook
    return precompile_hook


# TODO: Change this naive dict representation of a core object into a real class!
def create_core(options=None):
    return {"create_config": _create_config_hook(options), "precompile": _precompile_hook()}
