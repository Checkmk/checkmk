#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os

from typing import List, Dict, Tuple as _Tuple, Union
from livestatus import SiteId

import cmk.utils.store as store
import cmk.gui.config as config
import cmk.gui.watolib as watolib

from cmk.utils.type_defs import HostName
from cmk.utils.bi.bi_packs import BIHostRenamer

from cmk.gui.i18n import _
from cmk.gui.bi import get_cached_bi_packs

from cmk.gui import userdb
from cmk.gui.exceptions import MKAuthException
from cmk.gui.watolib.utils import rename_host_in_list
from cmk.gui.watolib.notifications import load_notification_rules, save_notification_rules
from cmk.gui.watolib.changes import log_audit, add_change, make_diff_text
from cmk.gui.watolib.hosts_and_folders import (
    CREFolder,
    Folder,
    Host,
    call_hook_hosts_changed,
)
from cmk.gui.watolib.automations import check_mk_automation

try:
    import cmk.gui.cee.plugins.wato.alert_handling as alert_handling  # type: ignore[import]
except ImportError:
    alert_handling = None  # type: ignore[assignment]


def perform_rename_hosts(renamings, job_interface=None):
    """Rename hosts mechanism

    Args:
        renamings:
            tuple consisting of folder, oldname, newname

        job_interface:
            only relevant for WATO interaction, allows to update the interface with the current
            update info
    """
    def update_interface(message):
        if job_interface is None:
            return
        job_interface.send_progress_update(_(message))

    actions = []
    all_hosts = Host.all()

    # 1. Fix WATO configuration itself ----------------
    auth_problems = []
    successful_renamings = []
    update_interface("Renaming WATO configuration...")
    for folder, oldname, newname in renamings:
        try:
            this_host_actions = []
            update_interface("Renaming host(s) in folders...")
            this_host_actions += _rename_host_in_folder(folder, oldname, newname)
            update_interface("Renaming host(s) in cluster nodes...")
            this_host_actions += _rename_host_as_cluster_node(all_hosts, oldname, newname)
            update_interface("Renaming host(s) in parents...")
            this_host_actions += _rename_parents(oldname, newname)
            update_interface("Renaming host(s) in rulesets...")
            this_host_actions += _rename_host_in_rulesets(folder, oldname, newname)
            update_interface("Renaming host(s) in BI aggregations...")
            this_host_actions += _rename_host_in_bi(oldname, newname)
            actions += this_host_actions
            successful_renamings.append((folder, oldname, newname))
        except MKAuthException as e:
            auth_problems.append((oldname, e))

    # 2. Checkmk stuff ------------------------------------------------
    update_interface("Renaming host(s) in base configuration, rrd, history files, etc.")
    update_interface("This might take some time and involves a core restart...")
    action_counts = _rename_hosts_in_check_mk(successful_renamings)

    # 3. Notification settings ----------------------------------------------
    # Notification rules - both global and users' ones
    update_interface("Renaming host(s) in notification rules...")
    for folder, oldname, newname in successful_renamings:
        actions += _rename_host_in_event_rules(oldname, newname)
        actions += _rename_host_in_multisite(oldname, newname)

    for action in actions:
        action_counts.setdefault(action, 0)
        action_counts[action] += 1

    update_interface("Calling final hooks")
    call_hook_hosts_changed(Folder.root_folder())
    return action_counts, auth_problems


def _rename_host_in_folder(folder, oldname, newname):
    folder.rename_host(oldname, newname)
    return ["folder"]


def _rename_host_as_cluster_node(all_hosts, oldname, newname):
    clusters = []
    for somehost in all_hosts.values():
        if somehost.is_cluster():
            if somehost.rename_cluster_node(oldname, newname):
                clusters.append(somehost.name())
    if clusters:
        return ["cluster_nodes"] * len(clusters)
    return []


def _rename_parents(
    oldname: HostName,
    newname: HostName,
) -> List[str]:
    parent_renamed: List[str]
    folder_parent_renamed: List[CREFolder]
    parent_renamed, folder_parent_renamed = _rename_host_in_parents(oldname, newname)
    # Needed because hosts.mk in folders with parent as effective attribute
    # would not be updated
    for folder in folder_parent_renamed:
        folder.rewrite_hosts_files()

    return parent_renamed


def _rename_host_in_parents(
    oldname: HostName,
    newname: HostName,
) -> _Tuple[List[str], List[CREFolder]]:
    folder_parent_renamed: List[CREFolder] = []
    parents, folder_parent_renamed = _rename_host_as_parent(
        oldname,
        newname,
        folder_parent_renamed,
        Folder.root_folder(),
    )
    return ["parents"] * len(parents), folder_parent_renamed


def _rename_host_in_rulesets(folder, oldname, newname):
    # Rules that explicitely name that host (no regexes)
    changed_rulesets = []

    def rename_host_in_folder_rules(folder):
        rulesets = watolib.FolderRulesets(folder)
        rulesets.load()

        changed_folder_rulesets = []
        for varname, ruleset in rulesets.get_rulesets().items():
            for _rule_folder, _rulenr, rule in ruleset.get_rules():
                orig_rule = rule.clone(preserve_id=True)
                if rule.replace_explicit_host_condition(oldname, newname):
                    changed_folder_rulesets.append(varname)

                    log_audit("edit-rule",
                              _("Renamed host condition from \"%s\" to \"%s\"") %
                              (oldname, newname),
                              diff_text=make_diff_text(orig_rule.to_log(), rule.to_log()),
                              object_ref=rule.object_ref())

        if changed_folder_rulesets:
            add_change("edit-ruleset",
                       _("Renamed host in %d rulesets of folder %s") %
                       (len(changed_folder_rulesets), folder.title()),
                       object_ref=folder.object_ref(),
                       sites=folder.all_site_ids())
            rulesets.save()

        changed_rulesets.extend(changed_folder_rulesets)

        for subfolder in folder.subfolders():
            rename_host_in_folder_rules(subfolder)

    rename_host_in_folder_rules(watolib.Folder.root_folder())
    if changed_rulesets:
        actions = []
        unique = set(changed_rulesets)
        for varname in unique:
            actions += ["wato_rules"] * changed_rulesets.count(varname)
        return actions
    return []


def _rename_host_in_bi(oldname, newname):
    return BIHostRenamer().rename_host(oldname, newname, get_cached_bi_packs())


def _rename_hosts_in_check_mk(
        renamings: List[_Tuple[CREFolder, HostName, HostName]]) -> Dict[str, int]:
    action_counts: Dict[str, int] = {}
    for site_id, name_pairs in _group_renamings_by_site(renamings).items():
        message = _("Renamed host %s") % ", ".join(
            [_("%s into %s") % (oldname, newname) for (oldname, newname) in name_pairs])

        # Restart is done by remote automation (below), so don't do it during rename/sync
        # The sync is automatically done by the remote automation call
        add_change("renamed-hosts", message, sites=[site_id], need_restart=False)

        new_counts = check_mk_automation(site_id,
                                         "rename-hosts", [],
                                         name_pairs,
                                         non_blocking_http=True)

        _merge_action_counts(action_counts, new_counts)
    return action_counts


def _rename_host_in_event_rules(oldname, newname):
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
        if user.get("notification_rules"):
            rules = user["notification_rules"]
            num_changed = rename_in_event_rules(rules)
            if num_changed:
                actions += ["notify_user"] * num_changed
                some_user_changed = True

    rules = load_notification_rules()
    num_changed = rename_in_event_rules(rules)
    if num_changed:
        actions += ["notify_global"] * num_changed
        save_notification_rules(rules)

    if alert_handling:
        rules = alert_handling.load_alert_handler_rules()
        if rules:
            num_changed = rename_in_event_rules(rules)
            if num_changed:
                actions += ["alert_rules"] * num_changed
                alert_handling.save_alert_handler_rules(rules)

    # Notification channels of flexible notifications also can have host conditions
    for user in users.values():
        method = user.get("notification_method")
        if method and isinstance(method, tuple) and method[0] == "flexible":
            channels_changed = 0
            for channel in method[1]:
                if channel.get("only_hosts"):
                    num_changed = rename_host_in_list(channel["only_hosts"], oldname, newname)
                    if num_changed:
                        channels_changed += 1
                        some_user_changed = True
            if channels_changed:
                actions += ["notify_flexible"] * channels_changed

    if some_user_changed:
        userdb.save_users(users)

    return actions


def _rename_host_in_multisite(oldname, newname):
    # State of Multisite ---------------------------------------
    # Favorites of users and maybe other settings. We simply walk through
    # all directories rather then through the user database. That way we
    # are sure that also currently non-existant users are being found and
    # also only users that really have a profile.
    users_changed = 0
    total_changed = 0
    for userid in os.listdir(config.config_dir):
        if userid[0] == '.':
            continue
        if not os.path.isdir(config.config_dir + "/" + userid):
            continue

        favpath = config.config_dir + "/" + userid + "/favorites.mk"
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
    folder_parent_renamed: List[CREFolder],
    in_folder: CREFolder,
) -> _Tuple[List[Union[HostName, str]], List[CREFolder]]:

    parents = []
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
            oldname, newname, folder_parent_renamed, subfolder)
        parents += subfolder_parents

    return parents, folder_parent_renamed


def _merge_action_counts(action_counts, new_counts):
    for key, count in new_counts.items():
        action_counts.setdefault(key, 0)
        action_counts[key] += count


def _group_renamings_by_site(renamings):
    renamings_per_site: Dict[SiteId, List[_Tuple[HostName, HostName]]] = {}
    for folder, oldname, newname in renamings:
        host = folder.host(newname)  # already renamed here!
        site_id = host.site_id()
        renamings_per_site.setdefault(site_id, []).append((oldname, newname))
    return renamings_per_site
