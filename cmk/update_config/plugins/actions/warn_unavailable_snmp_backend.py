#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from logging import Logger
from typing import Final, override

from cmk.ccc.version import Edition, edition
from cmk.gui.config import active_config
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.hosts_and_folders import make_folder_tree
from cmk.gui.watolib.rulesets import AllRulesets, RulesetCollection
from cmk.gui.watolib.sites import site_globals_editable, site_management_registry
from cmk.livestatus_client import SiteConfigurations
from cmk.update_config.lib import ExpiryVersion, format_warning
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils import paths

_GLOBAL_SETTING: Final = "snmp_backend_default"
_RULESET_NAME: Final = "snmp_backend_hosts"

# The legacy values selecting the inline backend are rewritten by the
# `migrate_snmp_backend_values` update action, which runs before this one.
_INLINE_VALUE: Final = "inline"


def warn_unavailable_snmp_backend(
    omd_edition: Edition,
    global_settings: GlobalSettings,
    configured_sites: SiteConfigurations,
    all_rulesets: RulesetCollection,
    logger: Logger,
) -> None:
    """Point out a configured inline SNMP backend that we cannot provide.

    The inline backend is not shipped in the Community Edition, and we no longer
    fall back to the classic backend silently: the affected hosts go CRIT. Tell
    the user about it during the update instead of at the next check cycle.
    """
    if omd_edition is not Edition.COMMUNITY:
        return

    configured_in = list(_inline_backend_locations(global_settings, configured_sites, all_rulesets))
    if not configured_in:
        return

    logger.warning(
        format_warning(
            f"The inline SNMP backend is configured in {' and '.join(configured_in)}, but it is "
            "not shipped in the Checkmk Community Edition. The 'Check_MK' service of the affected "
            "hosts will go CRIT. Please switch them to the classic backend."
        )
    )


def _inline_backend_locations(
    global_settings: GlobalSettings,
    configured_sites: SiteConfigurations,
    all_rulesets: RulesetCollection,
) -> Iterator[str]:
    if global_settings.get(_GLOBAL_SETTING) == _INLINE_VALUE:
        yield "the global setting 'Choose SNMP backend'"

    if sites := sorted(_sites_with_inline_backend(configured_sites)):
        listed = ", ".join(f"'{site_id}'" for site_id in sites)
        yield (
            f"the site specific global settings of "
            f"{'site' if len(sites) == 1 else 'the sites'} {listed}"
        )

    if n_rules := _count_inline_rules(all_rulesets):
        yield (
            f"{n_rules} rule{'' if n_rules == 1 else 's'} of 'Hosts using a specific SNMP Backend'"
        )


def _sites_with_inline_backend(configured_sites: SiteConfigurations) -> Iterator[str]:
    for site_id, site_spec in configured_sites.items():
        if not site_globals_editable(configured_sites, site_spec):
            continue
        if site_spec.get("globals", {}).get(_GLOBAL_SETTING) == _INLINE_VALUE:
            yield str(site_id)


def _count_inline_rules(all_rulesets: RulesetCollection) -> int:
    if not all_rulesets.exists(_RULESET_NAME):
        return 0
    return sum(
        1
        for _folder, _index, rule in all_rulesets.get(_RULESET_NAME).get_rules()
        if rule.value == _INLINE_VALUE
    )


class WarnUnavailableSNMPBackend(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        if is_distributed_setup_remote_site(active_config.sites):
            # the configuration is owned by the central site
            return

        warn_unavailable_snmp_backend(
            edition(paths.omd_root),
            load_configuration_settings(),
            site_management_registry["site_management"].load_sites(),
            AllRulesets.load_all_rulesets(make_folder_tree(active_config)),
            logger,
        )


update_action_registry.register(
    WarnUnavailableSNMPBackend(
        name="warn_unavailable_snmp_backend",
        title="Checking for an unavailable SNMP backend",
        sort_index=100,  # pure read-only check, no ordering constraints
        expiry_version=ExpiryVersion.CMK_310,
    )
)
