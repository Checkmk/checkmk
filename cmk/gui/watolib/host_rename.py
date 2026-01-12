#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import auto, StrEnum
from typing import Any

from pydantic import BaseModel

from livestatus import SiteId

from cmk.ccc import store
from cmk.ccc.plugin_registry import Registry

import cmk.utils.paths
from cmk.utils.agent_registration import get_uuid_link_manager
from cmk.utils.hostaddress import HostName
from cmk.utils.notify_types import EventRule
from cmk.utils.object_diff import make_diff_text

from cmk.gui import userdb
from cmk.gui.background_job import BackgroundJob, BackgroundProcessInterface
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.site_config import get_site_config, site_is_local
from cmk.gui.utils.urls import makeuri

from ..config import active_config
from .audit_log import log_audit
from .automation_commands import AutomationCommand
from .automations import AnnotatedHostName, do_remote_automation
from .changes import add_change
from .check_mk_automations import rename_hosts
from .hosts_and_folders import call_hook_hosts_changed, Folder, folder_tree, Host
from .notifications import NotificationRuleConfigFile
from .rulesets import FolderRulesets, Rule
from .utils import rename_host_in_list


class RenamePhase(StrEnum):
    SETUP = auto()
    POST_CMK_BASE = auto()


@dataclass(frozen=True)
class RenameHostHook:
    phase: RenamePhase
    title: str
    func: Callable[[HostName, HostName], list[str]]


class RenameHostHookRegistry(Registry[RenameHostHook]):
    def plugin_name(self, instance: RenameHostHook) -> str:
        return instance.title

    def hooks_by_phase(self, phase: RenamePhase) -> list[RenameHostHook]:
        return [h for h in self.values() if h.phase == phase]


rename_host_hook_registry = RenameHostHookRegistry()


@dataclass(frozen=True)
class RenameHostInRuleValue:
    ruleset_name: str
    func: Callable[[HostName, HostName, Rule], bool]  # returns true on change


class RenameHostInRuleValueRegistry(Registry[RenameHostInRuleValue]):
    def plugin_name(self, instance: RenameHostInRuleValue) -> str:
        return instance.ruleset_name


rename_host_in_rule_value_registry = RenameHostInRuleValueRegistry()


def perform_rename_hosts(
    renamings: Iterable[tuple[Folder, HostName, HostName]],
    job_interface: BackgroundProcessInterface,
) -> tuple[dict[str, int], list[tuple[HostName, MKAuthException]]]:
    def update_interface(message: str) -> None:
        job_interface.send_progress_update(message)

    actions: list[str] = []

    # 1. Fix Setup configuration itself ----------------
    auth_problems = []
    successful_renamings = []
    update_interface(_("Renaming Setup configuration..."))

    setup_actions: dict[tuple[Folder, HostName, HostName], list[str]] = {}
    for renaming in renamings:
        folder, oldname, newname = renaming
        try:
            update_interface(_("Renaming host(s) in folders..."))
            setup_actions[renaming] = _rename_host_in_folder(folder, oldname, newname)
        except MKAuthException as e:
            auth_problems.append((oldname, e))

    # Precompute cluster host list for node renaming due to expensive Host.all()
    # call. This currently also needs to be done after the host renaming as the
    # folder_tree cache_invalidation still misses some caches.
    cluster_hosts = [host for host in Host.all().values() if host.is_cluster()]

    for renaming, this_host_actions in setup_actions.items():
        folder, oldname, newname = renaming
        try:
            update_interface(_("Renaming host(s) in cluster nodes..."))
            this_host_actions.extend(_rename_host_as_cluster_node(cluster_hosts, oldname, newname))
            update_interface(_("Renaming host(s) in parents..."))
            this_host_actions.extend(_rename_parents(oldname, newname))
            update_interface(_("Renaming host(s) in rule sets..."))
            this_host_actions.extend(_rename_host_in_rulesets(oldname, newname))

            for hook in rename_host_hook_registry.hooks_by_phase(RenamePhase.SETUP):
                update_interface(_("Renaming host(s) in %s...") % hook.title)
                actions += hook.func(oldname, newname)

            actions += this_host_actions
            successful_renamings.append((folder, oldname, newname))
        except MKAuthException as e:
            auth_problems.append((oldname, e))

    # 2. Checkmk stuff ------------------------------------------------
    update_interface(_("Renaming host(s) in base configuration, rrd, history files, etc."))
    update_interface(_("This might take some time and involves a core restart..."))
    renamings_by_site = group_renamings_by_site(successful_renamings)
    action_counts = _rename_hosts_in_check_mk(renamings_by_site)

    # 3. Notification settings ----------------------------------------------
    # Notification rules - both global and users' ones
    update_interface(_("Renaming host(s) in notification rules..."))
    for folder, oldname, newname in successful_renamings:
        actions += _rename_host_in_event_rules(oldname, newname)
        actions += _rename_host_in_multisite(oldname, newname)

    # 4. Trigger updates in decoupled (e.g. edition specific) features
    for hook in rename_host_hook_registry.hooks_by_phase(RenamePhase.POST_CMK_BASE):
        update_interface(_("Renaming host(s) in %s...") % hook.title)
        actions += hook.func(oldname, newname)

    # 5. Update UUID links
    update_interface(_("Renaming host(s): Update UUID links..."))
    actions += _rename_host_in_uuid_link_manager(renamings_by_site)

    for action in actions:
        action_counts.setdefault(action, 0)
        action_counts[action] += 1

    update_interface(_("Calling final hooks"))
    call_hook_hosts_changed(folder_tree().root_folder())

    return action_counts, auth_problems


def _rename_host_in_folder(folder: Folder, oldname: HostName, newname: HostName) -> list[str]:
    folder.rename_host(oldname, newname)
    folder_tree().invalidate_caches()
    return ["folder"]


def _rename_host_as_cluster_node(
    cluster_hosts: list[Host], oldname: HostName, newname: HostName
) -> list[str]:
    renamed_cluster_nodes = 0
    for cluster_host in cluster_hosts:
        if cluster_host.rename_cluster_node(oldname, newname):
            renamed_cluster_nodes += 1
    return ["cluster_nodes"] * renamed_cluster_nodes


def _rename_parents(
    oldname: HostName,
    newname: HostName,
) -> list[str]:
    parent_renamed: list[str]
    folder_parent_renamed: list[Folder]
    parent_renamed, folder_parent_renamed = _rename_host_in_parents(oldname, newname)
    # Needed because hosts.mk in folders with parent as effective attribute
    # would not be updated
    for folder in folder_parent_renamed:
        folder.recursively_save_hosts()

    return parent_renamed


def _rename_host_in_parents(
    oldname: HostName,
    newname: HostName,
) -> tuple[list[str], list[Folder]]:
    folder_parent_renamed: list[Folder] = []
    parents, folder_parent_renamed = _rename_host_as_parent(
        oldname,
        newname,
        folder_parent_renamed,
        folder_tree().root_folder(),
    )
    return ["parents"] * len(parents), folder_parent_renamed


def _rename_host_in_rulesets(oldname: HostName, newname: HostName) -> list[str]:
    # Rules that explicitely name that host (no regexes)
    changed_rulesets = []

    def rename_host_in_folder_rules(folder: Folder) -> None:
        rulesets = FolderRulesets.load_folder_rulesets(folder)

        changed_folder_rulesets = []
        for varname, ruleset in rulesets.get_rulesets().items():
            rename_host_in_rule_value_hook = rename_host_in_rule_value_registry.get(varname)
            for _rule_folder, _rulenr, rule in ruleset.get_rules():
                orig_rule = rule.clone(preserve_id=True)
                changed_rule = False
                if rule.replace_explicit_host_condition(oldname, newname):
                    changed_rule = True
                if rename_host_in_rule_value_hook:
                    if rename_host_in_rule_value_hook.func(oldname, newname, rule):
                        changed_rule = True

                if changed_rule:
                    changed_folder_rulesets.append(varname)

                    log_audit(
                        "edit-rule",
                        f'Renamed host condition from "{oldname}" to "{newname}"',
                        diff_text=make_diff_text(orig_rule.to_log(), rule.to_log()),
                        object_ref=rule.object_ref(),
                    )

        if changed_folder_rulesets:
            add_change(
                "edit-ruleset",
                _l("Renamed host in %d rulesets of folder %s")
                % (len(changed_folder_rulesets), folder.title()),
                object_ref=folder.object_ref(),
                sites=folder.all_site_ids(),
            )
            rulesets.save_folder()

        changed_rulesets.extend(changed_folder_rulesets)

        for subfolder in folder.subfolders():
            rename_host_in_folder_rules(subfolder)

    rename_host_in_folder_rules(folder_tree().root_folder())
    if changed_rulesets:
        actions = []
        unique = set(changed_rulesets)
        for varname in unique:
            actions += ["wato_rules"] * changed_rulesets.count(varname)
        return actions
    return []


def _rename_hosts_in_check_mk(
    renamings_by_site: Mapping[SiteId, Sequence[tuple[HostName, HostName]]],
) -> dict[str, int]:
    action_counts: dict[str, int] = {}
    for site_id, name_pairs in renamings_by_site.items():
        message = _l("Renamed host %s") % ", ".join(
            [f"{oldname} into {newname}" for (oldname, newname) in name_pairs]
        )

        # Restart is done by remote automation (below), so don't do it during rename/sync
        # The sync is automatically done by the remote automation call
        add_change(
            "renamed-hosts",
            message,
            sites=[site_id],
            need_restart=False,
            prevent_discard_changes=True,
        )

        new_counts = rename_hosts(
            site_id,
            name_pairs,
        ).action_counts

        _merge_action_counts(action_counts, new_counts)
    return action_counts


def _rename_host_in_event_rules(oldname: HostName, newname: HostName) -> list[str]:
    actions = []

    users = userdb.load_users(lock=True)
    some_user_changed = False
    for user_ in users.values():
        if unrules := user_.get("notification_rules"):
            if num_changed := rename_in_event_rules(unrules, oldname, newname):
                actions += ["notify_user"] * num_changed
                some_user_changed = True

    nrules = NotificationRuleConfigFile().load_for_modification()
    if num_changed := rename_in_event_rules(nrules, oldname, newname):
        actions += ["notify_global"] * num_changed
        NotificationRuleConfigFile().save(nrules)

    if some_user_changed:
        userdb.save_users(users, datetime.now())

    return actions


def rename_in_event_rules(
    rules: list[dict[str, Any]] | list[EventRule], oldname: HostName, newname: HostName
) -> int:
    num_changed = 0
    for rule in rules:
        if rule.get("match_hosts"):
            if rename_host_in_list(rule["match_hosts"], oldname, newname):
                num_changed += 1
        if rule.get("match_exclude_hosts"):
            if rename_host_in_list(rule["match_exclude_hosts"], oldname, newname):
                num_changed += 1
    return num_changed


def _rename_host_in_multisite(oldname: HostName, newname: HostName) -> list[str]:
    # State of Multisite ---------------------------------------
    # Favorites of users and maybe other settings. We simply walk through
    # all directories rather then through the user database. That way we
    # are sure that also currently non-existant users are being found and
    # also only users that really have a profile.
    users_changed = 0
    total_changed = 0
    for profile_path in cmk.utils.paths.profile_dir.iterdir():
        if not profile_path.is_dir():
            continue

        favpath = profile_path / "favorites.mk"
        num_changed = 0
        favorites = store.load_object_from_file(favpath, default=[], lock=True)
        for nr, entry in enumerate(favorites):
            if entry == oldname:
                favorites[nr] = newname
                num_changed += 1
            elif entry.startswith(oldname + ";"):
                favorites[nr] = newname + ";" + entry.split(";")[1]
                num_changed += 1

        if num_changed:
            store.save_object_to_file(favpath, favorites)
            users_changed += 1
            total_changed += num_changed
        store.release_lock(favpath)

    if users_changed:
        return ["favorites"] * total_changed
    return []


def _rename_host_as_parent(
    oldname: HostName,
    newname: HostName,
    folder_parent_renamed: list[Folder],
    in_folder: Folder,
) -> tuple[list[HostName | str], list[Folder]]:
    parents: list[HostName | str] = []
    for somehost in in_folder.hosts().values():
        if "parents" in somehost.attributes:
            if somehost.rename_parent(oldname, newname):
                parents.append(somehost.name())

    if "parents" in in_folder.attributes:
        if in_folder.rename_parent(oldname, newname):
            if in_folder not in folder_parent_renamed:
                folder_parent_renamed.append(in_folder)
            parents.append(in_folder.name())

    for subfolder in in_folder.subfolders():
        subfolder_parents, folder_parent_renamed = _rename_host_as_parent(
            oldname, newname, folder_parent_renamed, subfolder
        )
        parents += subfolder_parents

    return parents, folder_parent_renamed


def _merge_action_counts(action_counts: dict[str, int], new_counts: Mapping[str, int]) -> None:
    for key, count in new_counts.items():
        action_counts.setdefault(key, 0)
        action_counts[key] += count


def group_renamings_by_site(
    renamings: Iterable[tuple[Folder, HostName, HostName]],
) -> dict[SiteId, list[tuple[HostName, HostName]]]:
    renamings_per_site: dict[SiteId, list[tuple[HostName, HostName]]] = {}
    for folder, oldname, newname in renamings:
        if not (host := folder.host(newname)):  # already renamed here!
            continue
        site_id = host.site_id()
        renamings_per_site.setdefault(site_id, []).append((oldname, newname))
    return renamings_per_site


def _rename_host_in_uuid_link_manager(
    renamings_by_site: Mapping[SiteId, Sequence[tuple[HostName, HostName]]],
) -> list[str]:
    n_relinked = 0
    for site_id, renamings in renamings_by_site.items():
        if site_is_local(active_config, site_id):
            n_relinked += len(get_uuid_link_manager().rename(renamings))
        else:
            n_relinked += int(
                str(
                    do_remote_automation(
                        get_site_config(active_config, site_id),
                        "rename-hosts-uuid-link",
                        [
                            (
                                "renamings",
                                json.dumps(renamings),
                            )
                        ],
                    )
                )
            )
    return ["uuid_link"] * n_relinked


class _RenameHostsUUIDLinkRequest(BaseModel):
    renamings: Sequence[tuple[AnnotatedHostName, AnnotatedHostName]]


class AutomationRenameHostsUUIDLink(AutomationCommand[_RenameHostsUUIDLinkRequest]):
    def command_name(self) -> str:
        return "rename-hosts-uuid-link"

    def execute(self, api_request: _RenameHostsUUIDLinkRequest) -> int:
        return len(get_uuid_link_manager().rename(api_request.renamings))

    def get_request(self) -> _RenameHostsUUIDLinkRequest:
        return _RenameHostsUUIDLinkRequest(renamings=json.loads(request.get_request()["renamings"]))


class RenameHostsBackgroundJob(BackgroundJob):
    job_prefix = "rename-hosts"

    @classmethod
    def gui_title(cls) -> str:
        return _("Host renaming")

    @classmethod
    def status_checks(cls) -> tuple[bool, bool]:
        instance = cls.__new__(cls)
        super(RenameHostsBackgroundJob, instance).__init__(instance.job_prefix)
        return instance.exists(), instance.is_active()

    def __init__(self) -> None:
        super().__init__(self.job_prefix)

    def _back_url(self) -> str:
        return makeuri(request, [])


class RenameHostBackgroundJob(RenameHostsBackgroundJob):
    def __init__(self, host: Host) -> None:
        super().__init__()
        self._host = host

    def _back_url(self):
        return self._host.folder().url()
