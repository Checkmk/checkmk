#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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
"""
Utility module for common code between the CMK base and other parts
of Check_MK. The GUI is e.g. accessing this module for gathering things
from the configuration.
"""

from typing import Dict, Text  # pylint: disable=unused-import
import cmk_base.config as config
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher, RulesetMatchObject  # pylint: disable=unused-import

_config_loaded = False


# TODO: This should be solved in the config module / ConfigCache object
def _load_config():
    global _config_loaded
    if not _config_loaded:
        config.load(validate_hosts=False)
        _config_loaded = True


def service_description(hostname, check_plugin_name, item):
    # type: (str, str, Text) -> Text
    _load_config()
    return config.service_description(hostname, check_plugin_name, item)


def get_ruleset_matcher():
    # type: () -> RulesetMatcher
    """Return a helper object to perform matching on Checkmk rulesets"""
    _load_config()
    return config.get_config_cache().ruleset_matcher


def ruleset_match_object_of_service(hostname, svc_desc):
    # type: (str, Text) -> RulesetMatchObject
    """Construct the object that is needed to match service rulesets"""
    _load_config()
    config_cache = config.get_config_cache()
    return config_cache.ruleset_match_object_of_service(hostname, svc_desc)


def ruleset_match_object_for_checkgroup_parameters(hostname, item, svc_desc):
    # type: (str, Text, Text) -> RulesetMatchObject
    """Construct the object that is needed to match checkgroup parameter rulesets"""
    _load_config()
    config_cache = config.get_config_cache()
    return config_cache.ruleset_match_object_for_checkgroup_parameters(hostname, item, svc_desc)


def get_host_labels(hostname):
    # type: (str) -> Dict[Text, Text]
    _load_config()
    config_cache = config.get_config_cache()
    return config_cache.get_host_config(hostname).labels
