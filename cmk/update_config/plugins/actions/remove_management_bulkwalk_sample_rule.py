#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger
from typing import override

from cmk.ccc.site import omd_site
from cmk.gui.config import active_config
from cmk.gui.site_config import all_activation_sites
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import FolderTree, make_folder_tree
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
from cmk.gui.watolib.rulesets import AllRulesets, RulesetCollection, UseHostFolder
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.registry import update_action_registry, UpdateAction

RULESET_NAME = "management_bulkwalk_hosts"
SAMPLE_RULE_ID = "59d84cde-ee3a-4f8d-8bec-fce35a2b0d15"


def _has_management_board(attributes: HostAttributes) -> bool:
    return attributes.get("management_protocol") is not None


def _uses_management_board(tree: FolderTree) -> bool:
    return any(
        _has_management_board(folder.attributes)
        or any(_has_management_board(host.attributes) for host in folder.hosts().values())
        for folder in tree.all_folders().values()
    )


def remove_management_bulkwalk_sample_rule(
    tree: FolderTree,
    all_rulesets: RulesetCollection,
    pending_changes: PendingChanges,
    logger: Logger,
) -> bool:
    """Remove the formerly shipped rule of the deprecated rule set, if it has no effect

    Otherwise the deprecation check warns every admin about a rule they never created.
    It stays while any management board is configured, since an IPMI one may still be switched
    to SNMP and new rules can no longer be added."""
    if (ruleset := all_rulesets.get_rulesets().get(RULESET_NAME)) is None:
        return False
    try:
        rule = ruleset.get_rule_by_id(SAMPLE_RULE_ID)
    except KeyError:
        return False

    if not (
        rule.folder.is_root()
        and rule.value is True
        and not rule.conditions.to_config(UseHostFolder.NONE)
    ):
        logger.debug("The sample rule for management boards was changed. Nothing to do.")
        return False

    if _uses_management_board(tree):
        logger.debug("Management boards are configured. Keeping the sample rule.")
        return False

    logger.info(
        "Removing the unused sample rule: %(description)s",
        {"description": rule.rule_options.description},
    )
    ruleset.delete_rule(rule, create_change=False, pending_changes=pending_changes)
    return True


class RemoveManagementBulkwalkSampleRule(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        tree = make_folder_tree(active_config)
        all_rulesets = AllRulesets.load_all_rulesets(tree)
        pending_changes = PendingChanges(
            activation_sites=all_activation_sites(active_config.sites),
            local_site=omd_site(),
            acting_user=None,
            store=NoopPendingChangesStore(),
            hooks=(),
        )
        if remove_management_bulkwalk_sample_rule(tree, all_rulesets, pending_changes, logger):
            all_rulesets.save(
                pprint_value=active_config.wato_pprint_config, debug=active_config.debug
            )


update_action_registry.register(
    RemoveManagementBulkwalkSampleRule(
        name="remove_management_bulkwalk_sample_rule",
        title="Remove the unused sample rule for management boards",
        sort_index=40,  # after ruleset migration
        expiry_version=ExpiryVersion.CMK_310,
    )
)
