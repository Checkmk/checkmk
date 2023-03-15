#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Sequence

import urllib3 as _urllib3

import cmk.gui.background_job as _background_job
import cmk.gui.hooks as _hooks
import cmk.gui.pages as _pages
import cmk.gui.userdb as _userdb
import cmk.gui.watolib.auth_php as _auth_php
import cmk.gui.watolib.automation_commands as _automation_commands
import cmk.gui.watolib.builtin_attributes as builtin_attributes
import cmk.gui.watolib.config_domains as _config_domains
import cmk.gui.watolib.groups as groups
import cmk.gui.weblib as _webling
from cmk.gui.config import register_post_config_load_hook as _register_post_config_load_hook
from cmk.gui.cron import register_job as _register_job
from cmk.gui.inventory import (
    execute_inventory_housekeeping_job as _execute_inventory_housekeeping_job,
)
from cmk.gui.plugins.watolib.utils import config_domain_registry as _config_domain_registry
from cmk.gui.utils import load_web_plugins as _load_web_plugins
from cmk.gui.watolib import autodiscovery as _autodiscovery
from cmk.gui.watolib import automatic_host_removal as _automatic_host_removal
from cmk.gui.watolib._host_attributes import register as _register_host_attributes
from cmk.gui.watolib.activate_changes import (
    execute_activation_cleanup_background_job as _execute_activation_cleanup_background_job,
)
from cmk.gui.watolib.host_attributes import ABCHostAttribute
from cmk.gui.watolib.host_attributes import host_attribute_registry as _host_attributes_registry
from cmk.gui.watolib.host_rename import (
    AutomationRenameHostsUUIDLink as _AutomationRenameHostsUUIDLink,
)
from cmk.gui.watolib.hosts_and_folders import (
    rebuild_folder_lookup_cache as _rebuild_folder_lookup_cache,
)
from cmk.gui.watolib.network_scan import execute_network_scan_job as _execute_network_scan_job

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
_urllib3.disable_warnings(_urllib3.exceptions.InsecureRequestWarning)


def _register_automation_commands() -> None:
    clss: Sequence[type[_automation_commands.AutomationCommand]] = (
        _automation_commands.AutomationPing,
        _automatic_host_removal.AutomationHostsForAutoRemoval,
        _AutomationRenameHostsUUIDLink,
    )
    for cls in clss:
        _automation_commands.automation_command_registry.register(cls)


def _register_gui_background_jobs() -> None:
    clss: Sequence[type[_background_job.BackgroundJob]] = (
        _config_domains.OMDConfigChangeBackgroundJob,
        _automatic_host_removal.HostRemovalBackgroundJob,
        _autodiscovery.AutodiscoveryBackgroundJob,
    )
    for cls in clss:
        _background_job.job_registry.register(cls)


def _register_config_domains() -> None:
    clss: Sequence[type[_config_domains.ABCConfigDomain]] = (
        _config_domains.ConfigDomainCore,
        _config_domains.ConfigDomainGUI,
        _config_domains.ConfigDomainLiveproxy,
        _config_domains.ConfigDomainCACertificates,
        _config_domains.ConfigDomainOMD,
    )
    for cls in clss:
        _config_domain_registry.register(cls)


def _register_host_attribute():
    clss: Sequence[type[ABCHostAttribute]] = [
        builtin_attributes.HostAttributeAlias,
        builtin_attributes.HostAttributeIPv4Address,
        builtin_attributes.HostAttributeIPv6Address,
        builtin_attributes.HostAttributeAdditionalIPv4Addresses,
        builtin_attributes.HostAttributeAdditionalIPv6Addresses,
        builtin_attributes.HostAttributeSNMPCommunity,
        builtin_attributes.HostAttributeParents,
        builtin_attributes.HostAttributeNetworkScan,
        builtin_attributes.HostAttributeNetworkScanResult,
        builtin_attributes.HostAttributeManagementAddress,
        builtin_attributes.HostAttributeManagementProtocol,
        builtin_attributes.HostAttributeManagementSNMPCommunity,
        builtin_attributes.HostAttributeManagementIPMICredentials,
        builtin_attributes.HostAttributeSite,
        builtin_attributes.HostAttributeLockedBy,
        builtin_attributes.HostAttributeLockedAttributes,
        builtin_attributes.HostAttributeMetaData,
        builtin_attributes.HostAttributeDiscoveryFailed,
        builtin_attributes.HostAttributeLabels,
        groups.HostAttributeContactGroups,
    ]
    for cls in clss:
        _host_attributes_registry.register(cls)


def _register_hooks():
    # TODO: Should we not execute this hook also when folders are modified?
    args: Sequence[tuple[str, Callable]] = (
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


def _register_post_config_load():
    for cls in (
        _userdb._fix_user_connections,
        _userdb.update_config_based_user_attributes,
    ):
        _register_post_config_load_hook(cls)


def _register_cronjobs() -> None:
    _register_job(_execute_activation_cleanup_background_job)
    _register_job(_background_job.execute_housekeeping_job)
    _register_job(_execute_inventory_housekeeping_job)
    _register_job(_execute_network_scan_job)
    _register_job(_userdb.execute_userdb_job)
    _register_job(_userdb.execute_user_profile_cleanup_job)
    _register_job(_rebuild_folder_lookup_cache)
    _register_job(_automatic_host_removal.execute_host_removal_background_job)
    _register_job(_autodiscovery.execute_autodiscovery)


def load_watolib_plugins():
    _load_web_plugins("watolib", globals())


# TODO(ml):  The code is still poorly organized as we register classes here that are
# not defined under watolib.

_register_automation_commands()
_register_gui_background_jobs()
_register_hooks()
_register_config_domains()
_register_host_attributes()
_register_host_attribute()
_register_pages()
_register_post_config_load()
_register_cronjobs()
