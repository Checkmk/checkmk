#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Utility module for common code between the CMK base and other parts
of Check_MK. The GUI is e.g. accessing this module for gathering things
from the configuration.
"""

from cmk.utils.hostaddress import HostName
from cmk.utils.labels import Labels
from cmk.utils.paths import checks_dir, local_checks_dir
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher
from cmk.utils.servicename import Item

from cmk.checkengine.checking import CheckPluginName

from cmk.base import config
from cmk.base.api.agent_based.register import (
    AgentBasedPlugins,
    extract_known_discovery_rulesets,
)

_config: config.LoadedConfigFragment | None = None
_plugins: AgentBasedPlugins | None = None


# TODO: This should be solved in the config module / ConfigCache object
def _load_config() -> config.LoadedConfigFragment:
    global _config
    if _config is None:
        # not sure if we need the plugins here (probably not)
        # but this whole module is soon to be removed anyway
        plugins = _load_checks()
        _config = config.load(extract_known_discovery_rulesets(plugins), validate_hosts=False)
    return _config


# TODO: This should be solved in the config module / ConfigCache object
def _load_checks() -> AgentBasedPlugins:
    global _plugins
    if _plugins is None:
        _plugins, _errors = config.load_all_plugins(
            local_checks_dir=local_checks_dir, checks_dir=checks_dir
        )
    return _plugins


def reset_config() -> None:
    global _config
    _config = None


def logwatch_service_description(
    hostname: HostName,
    item: Item,
) -> str:
    # Note: We actually only need the logwatch plug-in here, but to be
    # *absolutely* sure we get the real thing, we need to load all plug-ins
    # (users might shadow/redefine the logwatch plug-in in unexpected places)
    # Failing to load the right plug-in would result in a wrong service description,
    # in turn leading to wrong service labels and ruleset matches.
    plugin_name = CheckPluginName("logwatch")
    plugin = _load_checks().check_plugins[plugin_name]
    return config.service_description(
        get_ruleset_matcher(),
        hostname,
        plugin.name,
        service_name_template=plugin.service_name,
        item=item,
    )


def get_ruleset_matcher() -> RulesetMatcher:
    """Return a helper object to perform matching on Checkmk rulesets"""
    return _load_config().config_cache.ruleset_matcher


def get_host_labels(hostname: HostName) -> Labels:
    return get_ruleset_matcher().labels_of_host(hostname)
