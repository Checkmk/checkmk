#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Utility module for common code between the CMK base and other parts
of Check_MK. The GUI is e.g. accessing this module for gathering things
from the configuration.
"""


from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher, RulesetMatchObject
from cmk.utils.type_defs import (
    CheckPluginName,
    CheckPluginNameStr,
    HostName,
    Item,
    Labels,
    ServiceName,
)

import cmk.base.config as config

_config_loaded = False


# TODO: This should be solved in the config module / ConfigCache object
def _load_config() -> None:
    global _config_loaded
    if not _config_loaded:
        config.load(validate_hosts=False)
        _config_loaded = True


def reset_config() -> None:
    global _config_loaded
    _config_loaded = False


def service_description(
    hostname: HostName, check_plugin_name: CheckPluginNameStr, item: Item
) -> str:
    _load_config()
    return config.service_description(hostname, CheckPluginName(check_plugin_name), item)


def get_ruleset_matcher() -> RulesetMatcher:
    """Return a helper object to perform matching on Checkmk rulesets"""
    _load_config()
    return config.get_config_cache().ruleset_matcher


def ruleset_match_object_of_service(
    hostname: HostName, svc_desc: ServiceName
) -> RulesetMatchObject:
    """Construct the object that is needed to match service rulesets"""
    _load_config()
    config_cache = config.get_config_cache()
    return config_cache.ruleset_match_object_of_service(hostname, svc_desc)


def ruleset_match_object_for_checkgroup_parameters(
    hostname: HostName, item: Item, svc_desc: ServiceName
) -> RulesetMatchObject:
    """Construct the object that is needed to match checkgroup parameter rulesets"""
    _load_config()
    config_cache = config.get_config_cache()
    return config_cache.ruleset_match_object_for_checkgroup_parameters(hostname, item, svc_desc)


def get_host_labels(hostname: HostName) -> Labels:
    _load_config()
    config_cache = config.get_config_cache()
    return config_cache.get_host_config(hostname).labels
