#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from typing import Dict, List, Sequence
from typing import Tuple as _Tuple

from livestatus import SiteId

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.agent_registration import get_uuid_link_manager, UUIDLinkManager
from cmk.utils.bi.bi_packs import BIHostRenamer
from cmk.utils.object_diff import make_diff_text
from cmk.utils.type_defs import HostName

from cmk.gui import userdb
from cmk.gui.bi import get_cached_bi_packs
from cmk.gui.exceptions import MKAuthException
from cmk.gui.i18n import _
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.check_mk_automations import rename_hosts
from cmk.gui.watolib.hosts_and_folders import call_hook_hosts_changed, CREFolder, Folder, Host
from cmk.gui.watolib.notifications import load_notification_rules, save_notification_rules
from cmk.gui.watolib.rulesets import FolderRulesets
from cmk.gui.watolib.utils import rename_host_in_list

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

    def update_interface(message: str) -> None:
        if job_interface is None:
            return
        job_interface.send_progress_update(message)

    actions = []
    all_hosts = Host.all()

    # 1. Fix WATO configuration itself ----------------
    auth_problems = []
    successful_renamings = []
    update_interface(_("Renaming WATO configuration..."))
    for folder, oldname, newname in renamings:
        try:
            this_host_actions = []
            update_interface(_("Renaming host(s) in folders..."))
            this_host_actions += _rename_host_in_folder(folder, oldname, newname)
            update_interface(_("Renaming host(s) in cluster nodes..."))
            this_host_actions += _rename_host_as_cluster_node(all_hosts, oldname, newname)
            update_interface(_("Renaming host(s) in parents..."))
            this_host_actions += _rename_host_in_parents(oldname, newname)
            update_interface(_("Renaming host(s) in rulesets..."))
            this_host_actions += _rename_host_in_rulesets(folder, oldname, newname)
            update_interface(_("Renaming host(s) in BI aggregations..."))
            this_host_actions += _rename_host_in_bi(oldname, newname)
            actions += this_host_actions
            successful_renamings.append((folder, oldname, newname))
        except MKAuthException as e:
            auth_problems.append((oldname, e))

    # 2. Checkmk stuff ------------------------------------------------
    update_interface(_("Renaming host(s) in base configuration, rrd, history files, etc."))
    update_interface(_("This might take some time and involves a core restart..."))
    action_counts = _rename_hosts_in_check_mk(successful_renamings)

    # 3. Notification settings ----------------------------------------------
    # Notification rules - both global and users' ones
    update_interface(_("Renaming host(s) in notification rules..."))
    for folder, oldname, newname in successful_renamings:
        actions += _rename_host_in_event_rules(oldname, newname)
        actions += _rename_host_in_multisite(oldname, newname)

    # 4. Update UUID links
    update_interface(_("Renaming host(s): Update UUID links..."))
    actions += _rename_host_in_uuid_link_manager(
        get_uuid_link_manager(),
        [(oldname, newname) for _folder, oldname, newname in successful_renamings],
    )

    for action in actions:
        action_counts.setdefault(action, 0)
        action_counts[action] += 1

    update_interface(_("Calling final hooks"))
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


def _rename_host_in_parents(oldname, newname):
    parents = _rename_host_as_parent(oldname, newname)
    return ["parents"] * len(parents)


def _rename_host_in_rulesets(folder, oldname, newname):
    # Rules that explicitely name that host (no regexes)
    changed_rulesets = []

    def rename_host_in_folder_rules(folder):
        rulesets = FolderRulesets(folder)
        rulesets.load()

        changed_folder_rulesets = []
        for varname, ruleset in rulesets.get_rulesets().items():
            for _rule_folder, _rulenr, rule in ruleset.get_rules():
                orig_rule = rule.clone(preserve_id=True)
                if rule.replace_explicit_host_condition(oldname, newname):
                    changed_folder_rulesets.append(varname)

                    log_audit(
                        "edit-rule",
                        _('Renamed host condition from "%s" to "%s"') % (oldname, newname),
                        diff_text=make_diff_text(orig_rule.to_log(), rule.to_log()),
                        object_ref=rule.object_ref(),
                    )

        if changed_folder_rulesets:
            add_change(
                "edit-ruleset",
                _("Renamed host in %d rulesets of folder %s")
                % (len(changed_folder_rulesets), folder.title()),
                object_ref=folder.object_ref(),
                sites=folder.all_site_ids(),
            )
            rulesets.save()

        changed_rulesets.extend(changed_folder_rulesets)

        for subfolder in folder.subfolders():
            rename_host_in_folder_rules(subfolder)

    rename_host_in_folder_rules(Folder.root_folder())
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
    renamings: List[_Tuple[CREFolder, HostName, HostName]]
) -> Dict[str, int]:
    action_counts: Dict[str, int] = {}
    for site_id, name_pairs in _group_renamings_by_site(renamings).items():
        message = _("Renamed host %s") % ", ".join(
            [_("%s into %s") % (oldname, newname) for (oldname, newname) in name_pairs]
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


def _rename_host_in_event_rules(oldname, newname):  # pylint: disable=too-many-branches
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
        userdb.save_users(users, datetime.now())

    return actions


def _rename_host_in_multisite(oldname, newname):
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


def _rename_host_as_parent(oldname, newname, in_folder=None):
    if in_folder is None:
        in_folder = Folder.root_folder()

    parents = []
    for somehost in in_folder.hosts().values():
        if somehost.has_explicit_attribute("parents"):
            if somehost.rename_parent(oldname, newname):
                parents.append(somehost.name())

    if in_folder.has_explicit_attribute("parents"):
        if in_folder.rename_parent(oldname, newname):
            parents.append(in_folder.name())

    for subfolder in in_folder.subfolders():
        parents += _rename_host_as_parent(oldname, newname, subfolder)

    return parents


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


def _rename_host_in_uuid_link_manager(
    uuid_link_manager: UUIDLinkManager,
    successful_renamings: Sequence[_Tuple[HostName, HostName]],
) -> Sequence[_Tuple[HostName, HostName]]:
    return uuid_link_manager.rename(successful_renamings)
