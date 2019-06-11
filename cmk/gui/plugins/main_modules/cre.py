#!/usr/bin/python
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
"""Import top level modules into the application to make them able to register with the application."""
# pylint: disable=unused-import

import cmk.gui.main
import cmk.gui.sidebar
import cmk.gui.cron
import cmk.gui.login
import cmk.gui.weblib
import cmk.gui.help
import cmk.gui.hooks
import cmk.gui.default_permissions

import cmk.gui.visuals
import cmk.gui.views
import cmk.gui.inventory
import cmk.gui.bi
import cmk.gui.metrics
import cmk.gui.mobile
import cmk.gui.prediction
import cmk.gui.logwatch
import cmk.gui.dashboard

import cmk.gui.wato
import cmk.gui.userdb
import cmk.gui.notify
import cmk.gui.webapi
import cmk.gui.crash_reporting
import cmk.gui.werks
import cmk.gui.notifications
import cmk.gui.valuespec

import cmk.gui.node_visualization
