#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Import top level modules into the application to make them able to register with the application."""
# flake8: noqa
# pylint: disable=unused-import

import cmk.gui.default_permissions
import cmk.gui.main
import cmk.gui.sidebar
import cmk.gui.main_menu
import cmk.gui.cron
import cmk.gui.login
import cmk.gui.weblib
import cmk.gui.help
import cmk.gui.hooks

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
