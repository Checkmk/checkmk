#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: flake8 has no way to ignore just e.g. F401 for the whole file! :-P
# flake8: noqa
# pylint: disable=unused-import

import urllib3 as _urllib3

import cmk.utils.version as _cmk_version

import cmk.gui.hooks as hooks
import cmk.gui.mkeventd as mkeventd
import cmk.gui.userdb as userdb
import cmk.gui.watolib.auth_php
import cmk.gui.watolib.changes
import cmk.gui.watolib.git
import cmk.gui.watolib.timeperiods
import cmk.gui.weblib
from cmk.gui.watolib.automation_commands import automation_command_registry, AutomationCommand
from cmk.gui.watolib.config_domains import (
    ConfigDomainCACertificates,
    ConfigDomainCore,
    ConfigDomainEventConsole,
    ConfigDomainGUI,
    ConfigDomainLiveproxy,
    ConfigDomainOMD,
)
from cmk.gui.watolib.sites import CEESiteManagement, LivestatusViaTCP, SiteManagementFactory

if _cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
_urllib3.disable_warnings(_urllib3.exceptions.InsecureRequestWarning)


def load_watolib_plugins():
    cmk.gui.utils.load_web_plugins("watolib", globals())
