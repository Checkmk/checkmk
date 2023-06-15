#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime

from pydantic import BaseModel

from livestatus import SiteId

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.agent_registration import get_uuid_link_manager
from cmk.utils.hostaddress import HostName
from cmk.utils.object_diff import make_diff_text

from cmk.gui import background_job, userdb
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobAlreadyRunning,
    BackgroundProcessInterface,
    job_registry,
)
from cmk.gui.bi import get_cached_bi_packs
from cmk.gui.exceptions import MKAuthException
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.site_config import get_site_config, site_is_local
from cmk.gui.utils.urls import makeuri
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.check_mk_automations import rename_hosts
from cmk.gui.watolib.hosts_and_folders import (
    call_hook_hosts_changed,
    CREFolder,
    CREHost,
    folder_tree,
    Host,
)
from cmk.gui.watolib.notifications import load_notification_rules, save_notification_rules
from cmk.gui.watolib.rulesets import FolderRulesets
from cmk.gui.watolib.utils import rename_host_in_list

from cmk.bi.packs import BIHostRenamer

try:
    import cmk.gui.cee.plugins.wato.alert_handling as alert_handling
except ImportError:
    alert_handling = None  # type: ignore[assignment]


def perform_rename_hosts(
    renamings: Iterable[tuple[CREFolder, HostName, HostName]],
    job_interface: BackgroundProcessInterface | None = None,
) -> tuple[dict[str, int], list[tuple[HostName, MKAuthException]]]:
    """Rename hosts mechanism

    Args:
        renamings:
            tuple consisting of folder, oldname, newname

        job_interface:
            only relevant for Setup interaction, allows to update the interface with the current
            update info
    """

    def update_interface(message: str) -> None:
        if job_interface is None:
            return
        job_interface.send_progress_update(message)

    actions: list[str] = []
    all_hosts = list(Host.all().values())

    # 1. Fix Setup configuration itself ----------------
    auth_problems = []
    successful_renamings = []
    update_interface(_("Renaming Setup configuration..."))
    for folder, oldname, newname in renamings:
        try:
            this_host_actions = []
            update_interface(_("Renaming host(s) in folders..."))
            this_host_actions += _rename_host_in_folder(folder, oldname, newname)
            update_interface(_("Renaming host(s) in cluster nodes..."))
            this_host_actions += _rename_host_as_cluster_node(all_hosts, oldname, newname)
            update_interface(_("Renaming host(s) in parents..."))
            this_host_actions += _rename_parents(oldname, newname)
            update_interface(_("Renaming host(s) in rulesets..."))
            this_host_actions += _rename_host_in_rulesets(oldname, newname)
            update_interface(_("Renaming host(s) in BI aggregations..."))
            this_host_actions += _rename_host_in_bi(oldname, newname)
            actions += this_host_actions
            successful_renamings.append((folder, oldname, newname))
        except MKAuthException as e:
            auth_problems.append((oldname, e))

    # 2. Checkmk stuff ------------------------------------------------
    update_interface(_("Renaming host(s) in base configuration, rrd, history files, etc."))
    update_interface(_("This might take some time and involves a core restart..."))
    renamings_by_site = _group_renamings_by_site(successful_renamings)
    action_counts = _rename_hosts_in_check_mk(renamings_by_site)

    # 3. Notification settings ----------------------------------------------
    # Notification rules - both global and users' ones
    update_interface(_("Renaming host(s) in notification rules..."))
    for folder, oldname, newname in successful_renamings:
        actions += _rename_host_in_event_rules(oldname, newname)
        actions += _rename_host_in_multisite(oldname, newname)

    # 4. Update UUID links
    update_interface(_("Renaming host(s): Update UUID links..."))
    actions += _rename_host_in_uuid_link_manager(renamings_by_site)

    for action in actions:
        action_counts.setdefault(action, 0)
        action_counts[action] += 1

    update_interface(_("Calling final hooks"))
    call_hook_hosts_changed(folder_tree().root_folder())

    return action_counts, auth_problems


def _rename_host_in_folder(folder: CREFolder, oldname: HostName, newname: HostName) -> list[str]:
    folder.rename_host(oldname, newname)
    folder_tree().invalidate_caches()
    return ["folder"]


def _rename_host_as_cluster_node(
    all_hosts: Iterable[CREHost], oldname: HostName, newname: HostName
) -> list[str]:
    clusters = []
    for somehost in all_hosts:
        if somehost.is_cluster():
            if somehost.rename_cluster_node(oldname, newname):
                clusters.append(somehost.name())
    if clusters:
        return ["cluster_nodes"] * len(clusters)
    return []


def _rename_parents(
    oldname: HostName,
    newname: HostName,
) -> list[str]:
    parent_renamed: list[str]
    folder_parent_renamed: list[CREFolder]
    parent_renamed, folder_parent_renamed = _rename_host_in_parents(oldname, newname)
    # Needed because hosts.mk in folders with parent as effective attribute
    # would not be updated
    for folder in folder_parent_renamed:
        folder.rewrite_hosts_files()

    return parent_renamed


def _rename_host_in_parents(
    oldname: HostName,
    newname: HostName,
) -> tuple[list[str], list[CREFolder]]:
    folder_parent_renamed: list[CREFolder] = []
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

    def rename_host_in_folder_rules(folder: CREFolder) -> None:
        rulesets = FolderRulesets.load_folder_rulesets(folder)

        changed_folder_rulesets = []
        for varname, ruleset in rulesets.get_rulesets().items():
            for _rule_folder, _rulenr, rule in ruleset.get_rules():
                orig_rule = rule.clone(preserve_id=True)
                if rule.replace_explicit_host_condition(oldname, newname):
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


def _rename_host_in_bi(oldname: HostName, newname: HostName) -> list[str]:
    return BIHostRenamer().rename_host(oldname, newname, get_cached_bi_packs())


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
        add_change("renamed-hosts", message, sites=[site_id], need_restart=False)

        new_counts = rename_hosts(
            site_id,
            name_pairs,
        ).action_counts

        _merge_action_counts(action_counts, new_counts)
    return action_counts


def _rename_host_in_event_rules(oldname: HostName, newname: HostName) -> list[str]:
    actions = []

    def rename_in_event_rules(rules):
        num_changed = 0
        for rule in rules:
            for key in ["match_hosts", "match_exclude_hosts"]:
                if rule.get(key):
                    if rename_host_in_list(rule[key], oldname, newname):
                        num_changed += 1
        return num_changed

    users = userdb.load_users(lock=True)
    some_user_changed = False
    for user in users.values():
        if unrules := user.get("notification_rules"):
            if num_changed := rename_in_event_rules(unrules):
                actions += ["notify_user"] * num_changed
                some_user_changed = True

    nrules = load_notification_rules()
    if num_changed := rename_in_event_rules(nrules):
        actions += ["notify_global"] * num_changed
        save_notification_rules(nrules)

    if alert_handling:
        if arules := alert_handling.load_alert_handler_rules():
            if num_changed := rename_in_event_rules(arules):
                actions += ["alert_rules"] * num_changed
                alert_handling.save_alert_handler_rules(arules)

    if some_user_changed:
        userdb.save_users(users, datetime.now())

    return actions


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
    folder_parent_renamed: list[CREFolder],
    in_folder: CREFolder,
) -> tuple[list[HostName | str], list[CREFolder]]:
    parents: list[HostName | str] = []
    for somehost in in_folder.hosts().values():
        if somehost.has_explicit_attribute("parents"):
            if somehost.rename_parent(oldname, newname):
                parents.append(somehost.name())

    if in_folder.has_explicit_attribute("parents"):
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


def _group_renamings_by_site(
    renamings: Iterable[tuple[CREFolder, HostName, HostName]]
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
        if site_is_local(site_id):
            n_relinked += len(get_uuid_link_manager().rename(renamings))
        else:
            n_relinked += int(
                str(
                    do_remote_automation(
                        get_site_config(site_id),
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
    renamings: Sequence[tuple[HostName, HostName]]


class AutomationRenameHostsUUIDLink(AutomationCommand):
    def command_name(self) -> str:
        return "rename-hosts-uuid-link"

    def execute(self, api_request: _RenameHostsUUIDLinkRequest) -> int:
        return len(get_uuid_link_manager().rename(api_request.renamings))

    def get_request(self) -> _RenameHostsUUIDLinkRequest:
        return _RenameHostsUUIDLinkRequest(renamings=json.loads(request.get_request()["renamings"]))


@job_registry.register
class RenameHostsBackgroundJob(BackgroundJob):
    job_prefix = "rename-hosts"

    @classmethod
    def gui_title(cls) -> str:
        return _("Host renaming")

    @classmethod
    def status_checks(cls, title: str | None = None) -> tuple[bool, bool]:
        instance = cls.__new__(cls)
        super(RenameHostsBackgroundJob, instance).__init__(
            instance.job_prefix,
            background_job.InitialStatusArgs(
                title=title or instance.gui_title(),
                lock_wato=True,
                stoppable=False,
                estimated_duration=BackgroundJob(instance.job_prefix).get_status().duration,
            ),
        )
        return instance.exists(), instance.is_active()

    def __init__(self, title: str | None = None) -> None:
        super().__init__(
            self.job_prefix,
            background_job.InitialStatusArgs(
                title=title or self.gui_title(),
                lock_wato=True,
                stoppable=False,
                estimated_duration=BackgroundJob(self.job_prefix).get_status().duration,
            ),
        )

        if self.is_active():
            raise BackgroundJobAlreadyRunning(
                _("Another renaming operation is currently in progress")
            )

    def _back_url(self) -> str:
        return makeuri(request, [])


@job_registry.register
class RenameHostBackgroundJob(RenameHostsBackgroundJob):
    def __init__(self, host, title=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(title)
        self._host = host

    def _back_url(self):
        return self._host.folder().url()
