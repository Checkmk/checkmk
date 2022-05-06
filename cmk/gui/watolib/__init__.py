#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable, Sequence, Tuple, Type

import urllib3 as _urllib3

import cmk.gui.gui_background_job as _gui_background_job
import cmk.gui.hooks as _hooks
import cmk.gui.mkeventd as _mkeventd
import cmk.gui.pages as _pages
import cmk.gui.userdb as _userdb
import cmk.gui.watolib.auth_php as _auth_php
import cmk.gui.watolib.automation_commands as _automation_commands
import cmk.gui.watolib.config_domains as _config_domains
import cmk.gui.weblib as _webling
from cmk.gui.config import register_post_config_load_hook as _register_post_config_load_hook
from cmk.gui.permissions import permission_section_registry as _permission_section_registry
from cmk.gui.plugins.watolib.utils import config_domain_registry as _config_domain_registry
from cmk.gui.utils import load_web_plugins as _load_web_plugins

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


def _register_hooks():
    # TODO: Should we not execute this hook also when folders are modified?
    args: Sequence[Tuple[str, Callable]] = (
        ("userdb-job", _auth_php._on_userdb_job),
        ("users-saved", lambda users: _auth_php._create_auth_file("users-saved", users)),
        ("roles-saved", lambda x: _auth_php._create_auth_file("roles-saved")),
        ("contactgroups-saved", lambda x: _auth_php._create_auth_file("contactgroups-saved")),
        ("activate-changes", lambda x: _auth_php._create_auth_file("activate-changes")),
    )
    for name, func in args:
        _hooks.register_builtin(name, func)


def _register_pages():
    for name, func in (
        ("tree_openclose", _webling.ajax_tree_openclose),
        ("ajax_set_rowselection", _webling.ajax_set_rowselection),
    ):
        _pages.register(name)(func)


def _register_permission_section_registry():
    clss = (_mkeventd.PermissionSectionEventConsole,)
    for cls in clss:
        _permission_section_registry.register(cls)


def _register_post_config_load():
    for cls in (
        _userdb._fix_user_connections,
        _userdb.update_config_based_user_attributes,
    ):
        _register_post_config_load_hook(cls)


def load_watolib_plugins():
    _load_web_plugins("watolib", globals())


# TODO(ml):  The code is still poorly organized as we register classes here that are
# not defined under watolib.

_register_automation_commands()
_register_gui_background_jobs()
_register_hooks()
_register_config_domains()
_register_pages()
_register_permission_section_registry()
