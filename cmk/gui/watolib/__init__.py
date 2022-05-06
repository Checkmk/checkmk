#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: flake8 has no way to ignore just e.g. F401 for the whole file! :-P
# flake8: noqa
# pylint: disable=unused-import

from typing import Sequence, Type

import urllib3 as _urllib3

import cmk.utils.version as _cmk_version

import cmk.gui.gui_background_job as _gui_background_job
import cmk.gui.mkeventd as mkeventd
import cmk.gui.userdb as userdb
import cmk.gui.watolib.auth_php
import cmk.gui.watolib.automation_commands as _automation_commands
import cmk.gui.watolib.config_domains as _config_domains
import cmk.gui.watolib.sites
import cmk.gui.weblib
from cmk.gui.plugins.watolib.utils import config_domain_registry as _config_domain_registry
from cmk.gui.utils import load_web_plugins as _load_web_plugins

if _cmk_version.is_managed_edition():
    import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
_urllib3.disable_warnings(_urllib3.exceptions.InsecureRequestWarning)


def _register_automation_commands() -> None:
    clss = (_automation_commands.AutomationPing,)
    for cls in clss:
        _automation_commands.automation_command_registry.register(cls)


def _register_gui_background_jobs() -> None:
    cls = _config_domains.OMDConfigChangeBackgroundJob
    _gui_background_job.job_registry.register(cls)


def _register_config_domains() -> None:
    clss: Sequence[Type[_config_domains.ABCConfigDomain]] = (
        _config_domains.ConfigDomainCore,
        _config_domains.ConfigDomainGUI,
        _config_domains.ConfigDomainLiveproxy,
        _config_domains.ConfigDomainEventConsole,
        _config_domains.ConfigDomainCACertificates,
        _config_domains.ConfigDomainOMD,
    )
    for cls in clss:
        _config_domain_registry.register(cls)


def load_watolib_plugins():
    _load_web_plugins("watolib", globals())


_register_automation_commands()
_register_gui_background_jobs()
_register_config_domains()
