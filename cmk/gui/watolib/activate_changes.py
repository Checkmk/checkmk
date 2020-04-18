#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Managing configuration activation of Checkmk

The major elements here are:

ActivateChangesManager - Coordinates a single activation of Checkmk config changes for all affected
                         sites.
CRE/CMESnapshotCreator - Prepare the configuration to be synchronized to a site.
ActivateChangesSite    - Executes the activation procedure for a single site.
"""

import errno
import ast
import os
import shutil
import time
import abc
import multiprocessing
from typing import (  # pylint: disable=unused-import
    Dict, Set, List, Optional, Tuple, Union, NamedTuple, Type,
)
import six

from livestatus import (  # pylint: disable=unused-import
    SiteId, SiteConfiguration,
)

import cmk.utils
import cmk.utils.version as cmk_version
import cmk.utils.daemon as daemon
import cmk.utils.store as store
import cmk.utils.render as render

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

import cmk.gui.utils
import cmk.gui.hooks as hooks
from cmk.gui.sites import (  # pylint: disable=unused-import
    SiteStatus, states as sites_states, disconnect as sites_disconnect,
)
import cmk.gui.config as config
import cmk.gui.log as log
import cmk.gui.escaping as escaping
from cmk.gui.i18n import _
from cmk.gui.globals import g, html
from cmk.gui.log import logger
from cmk.gui.exceptions import (
    MKGeneralException,
    MKUserError,
)
import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.plugins.userdb.utils import user_sync_default_config

import cmk.gui.watolib.git
import cmk.gui.watolib.automations
import cmk.gui.watolib.utils
import cmk.gui.watolib.sidebar_reload
import cmk.gui.watolib.snapshots
from cmk.gui.watolib.config_sync import SnapshotCreator, ReplicationPath
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob

from cmk.gui.watolib.changes import (
    SiteChanges,
    log_audit,
    activation_sites,
)
from cmk.gui.plugins.watolib import ABCConfigDomain

# TODO: Make private
PHASE_INITIALIZED = "initialized"  # Thread object has been initialized (not in thread yet)
PHASE_STARTED = "started"  # Thread just started, nothing happened yet
PHASE_SYNC = "sync"  # About to sync
PHASE_ACTIVATE = "activate"  # sync done activating changes
PHASE_FINISHING = "finishing"  # Remote work done, finalizing local state
PHASE_DONE = "done"  # Done (with good or bad result)

# PHASE_DONE can have these different states:

STATE_SUCCESS = "success"  # Everything is ok
STATE_ERROR = "error"  # Something went really wrong
STATE_WARNING = "warning"  # e.g. in case of core config warnings

# Available activation time keys

ACTIVATION_TIME_RESTART = "restart"
ACTIVATION_TIME_SYNC = "sync"
ACTIVATION_TIME_PROFILE_SYNC = "profile-sync"

var_dir = cmk.utils.paths.var_dir + "/wato/"

SnapshotSettings = NamedTuple("SnapshotSettings", [
    ("snapshot_path", str),
    ("work_dir", str),
    ("snapshot_components", List[ReplicationPath]),
    ("component_names", Set[str]),
    ("site_config", SiteConfiguration),
])


def _replace_omd_root(new_root, rp):
    # type: (str, ReplicationPath) -> ReplicationPath
    return ReplicationPath(
        ty=rp.ty,
        ident=rp.ident,
        path=rp.path.replace(cmk.utils.paths.omd_root, new_root),
        excludes=rp.excludes,
    )


# Directories and files to synchronize during replication
_replication_paths = []  # type: List[ReplicationPath]

ReplicationPathPre16 = Union[Tuple[str, str, str, List[str]], Tuple[str, str, str]]
ReplicationPathCompat = Union[ReplicationPathPre16, ReplicationPath]


def add_replication_paths(paths):
    # type: (List[ReplicationPathCompat]) -> None

    clean_paths = []  # type: List[ReplicationPath]

    for path in paths:
        # Be compatible to pre 1.7 tuple syntax and convert it to the
        # new internal strucure
        # TODO: Remove with 1.8
        if isinstance(path, tuple) and not isinstance(path, ReplicationPath):
            if len(path) not in [3, 4]:
                raise Exception("invalid replication path %r" % (path,))

            # mypy does not understand this
            excludes = path[3] if len(path) == 4 else []  # type: ignore[misc]
            clean_paths.append(ReplicationPath(path[0], path[1], path[2], excludes))
            continue

        clean_paths.append(path)

    _replication_paths.extend(clean_paths)


def get_replication_paths():
    # type: () -> List[ReplicationPath]
    paths = [
        ReplicationPath("dir", "check_mk", cmk.gui.watolib.utils.wato_root_dir(),
                        ["sitespecific.mk"]),
        ReplicationPath("dir", "multisite", cmk.gui.watolib.utils.multisite_dir(),
                        ["sitespecific.mk"]),
        ReplicationPath("file", "htpasswd", cmk.utils.paths.htpasswd_file, []),
        ReplicationPath("file", "auth.secret",
                        '%s/auth.secret' % os.path.dirname(cmk.utils.paths.htpasswd_file), []),
        ReplicationPath("file", "auth.serials",
                        '%s/auth.serials' % os.path.dirname(cmk.utils.paths.htpasswd_file), []),
        # Also replicate the user-settings of Multisite? While the replication
        # as such works pretty well, the count of pending changes will not
        # know.
        ReplicationPath("dir", "usersettings", cmk.utils.paths.var_dir + "/web",
                        ["*/report-thumbnails"]),
        ReplicationPath("dir", "mkps", cmk.utils.paths.var_dir + "/packages", []),
        ReplicationPath("dir", "local", cmk.utils.paths.omd_root + "/local", []),
    ]  # type: List[ReplicationPath]

    # TODO: Move this to CEE specific code again
    if not cmk_version.is_raw_edition():
        paths += [
            ReplicationPath("dir", "liveproxyd", cmk.gui.watolib.utils.liveproxyd_config_dir(),
                            ["sitespecific.mk"]),
        ]

    # Include rule configuration into backup/restore/replication. Current
    # status is not backed up.
    if config.mkeventd_enabled:
        _rule_pack_dir = str(ec.rule_pack_dir())
        paths.append(ReplicationPath("dir", "mkeventd", _rule_pack_dir, ["sitespecific.mk"]))

        _mkp_rule_pack_dir = str(ec.mkp_rule_pack_dir())
        paths.append(ReplicationPath("dir", "mkeventd_mkp", _mkp_rule_pack_dir, []))

    return paths + _replication_paths


def _load_site_replication_status(site_id, lock=False):
    return store.load_object_from_file(
        _site_replication_status_path(site_id),
        default={},
        lock=lock,
    )


def _save_site_replication_status(site_id, repl_status):
    store.save_object_to_file(_site_replication_status_path(site_id), repl_status, pretty=False)
    _cleanup_legacy_replication_status()


def _update_replication_status(site_id, vars_):
    """Updates one or more dict elements of a site in an atomic way."""
    store.mkdir(var_dir)

    repl_status = _load_site_replication_status(site_id, lock=True)
    try:
        repl_status.setdefault("times", {})
        repl_status.update(vars_)
    finally:
        _save_site_replication_status(site_id, repl_status)


# This can be removed one day. It is only meant for cleaning up the pre 1.4.0
# global replication status file.
def _cleanup_legacy_replication_status():
    try:
        os.unlink(var_dir + "replication_status.mk")
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass  # Not existant -> OK
        else:
            raise


def clear_site_replication_status(site_id):
    try:
        os.unlink(_site_replication_status_path(site_id))
    except OSError as e:
        if e.errno == errno.ENOENT:
            pass  # Not existant -> OK
        else:
            raise

    ActivateChanges().confirm_site_changes(site_id)


def _site_replication_status_path(site_id):
    return "%sreplication_status_%s.mk" % (var_dir, site_id)


def _load_replication_status(lock=False):
    return {site_id: _load_site_replication_status(site_id, lock=lock) for site_id in config.sites}


class ActivateChanges(object):
    def __init__(self):
        self._repstatus = {}

        # Changes grouped by site
        self._changes_by_site = {}

        # A list of changes ordered by time and grouped by the change.
        # Each change contains a list of affected sites.
        self._changes = []

        super(ActivateChanges, self).__init__()

    def load(self):
        self._load_replication_status()
        self._load_changes_by_site()
        self._load_changes_by_id()

    def _load_replication_status(self):
        self._repstatus = _load_replication_status()

    def _load_changes_by_site(self):
        self._changes_by_site = {}
        for site_id in activation_sites():
            self._changes_by_site[site_id] = SiteChanges(site_id).load()

    def confirm_site_changes(self, site_id):
        SiteChanges(site_id).clear()
        cmk.gui.watolib.sidebar_reload.need_sidebar_reload()

    # Returns a list of changes ordered by time and grouped by the change.
    # Each change contains a list of affected sites.
    def _load_changes_by_id(self):
        changes = {}

        for site_id, site_changes in self._changes_by_site.items():
            if not site_changes:
                continue

            for change in site_changes:
                change_id = change["id"]

                if change_id not in changes:
                    changes[change_id] = change.copy()

                affected_sites = changes[change_id].setdefault("affected_sites", [])
                affected_sites.append(site_id)

        self._changes = sorted(changes.items(), key=lambda k_v: k_v[1]["time"])

    def get_changes_estimate(self):
        changes_counter = 0
        for site_id in activation_sites():
            changes_counter += len(SiteChanges(site_id).load())
            if changes_counter > 10:
                return _("10+ changes")
        if changes_counter == 1:
            return _("1 change")
        if changes_counter > 1:
            return _("%d changes") % changes_counter

    def grouped_changes(self):
        return self._changes

    def _changes_of_site(self, site_id):
        return self._changes_by_site[site_id]

    def dirty_and_active_activation_sites(self):
        # type: () -> List[SiteId]
        """Returns the list of sites that should be used when activating all affected sites"""
        dirty = []
        for site_id, site in activation_sites().items():
            status = self._get_site_status(site_id, site)[1]
            is_online = self._site_is_online(status)
            is_logged_in = self._site_is_logged_in(site_id, site)

            if is_online and is_logged_in and self._changes_of_site(site_id):
                dirty.append(site_id)
        return dirty

    def _site_is_logged_in(self, site_id, site):
        return config.site_is_local(site_id) or "secret" in site

    def _site_is_online(self, status):
        # type: (str) -> bool
        return status in ["online", "disabled"]

    def _get_site_status(self, site_id, site):
        # type: (SiteId, SiteConfiguration) -> Tuple[SiteStatus, str]
        if site.get("disabled"):
            site_status = SiteStatus({})
            status = "disabled"
        else:
            site_status = sites_states().get(site_id, SiteStatus({}))
            status = site_status.get("state", "unknown")

        return site_status, status

    def _site_has_foreign_changes(self, site_id):
        changes = self._changes_of_site(site_id)
        return bool([c for c in changes if self._is_foreign(c)])

    def is_sync_needed(self, site_id):
        if config.site_is_local(site_id):
            return False

        return any([c["need_sync"] for c in self._changes_of_site(site_id)])

    def _is_activate_needed(self, site_id):
        return any([c["need_restart"] for c in self._changes_of_site(site_id)])

    # This function returns the last known persisted activation state
    def _last_activation_state(self, site_id):
        manager = ActivateChangesManager()
        site_state_path = os.path.join(manager.activation_persisted_dir,
                                       manager.site_filename(site_id))
        return store.load_object_from_file(site_state_path, {})

    def _get_last_change_id(self):
        # type: () -> str
        return self._changes[-1][1]["id"]

    def has_changes(self):
        return bool(self._changes)

    def has_foreign_changes(self):
        return any(change for _change_id, change in self._changes if self._is_foreign(change))

    def _has_foreign_changes_on_any_site(self):
        return any(change for _change_id, change in self._changes
                   if self._is_foreign(change) and self._affects_all_sites(change))

    def _is_foreign(self, change):
        return change["user_id"] and change["user_id"] != config.user.id

    def _affects_all_sites(self, change):
        return not set(change["affected_sites"]).symmetric_difference(set(activation_sites()))

    def update_activation_time(self, site_id, ty, duration):
        repl_status = _load_site_replication_status(site_id, lock=True)
        try:
            times = repl_status.setdefault("times", {})

            if ty not in times:
                times[ty] = duration
            else:
                times[ty] = 0.8 * times[ty] + 0.2 * duration
        finally:
            _save_site_replication_status(site_id, repl_status)

    def get_activation_times(self, site_id):
        repl_status = _load_site_replication_status(site_id)
        return repl_status.get("times", {})

    def get_activation_time(self, site_id, ty, deflt=None):
        return self.get_activation_times(site_id).get(ty, deflt)


class ActivateChangesManager(ActivateChanges):
    """Mangages the activation of pending changes in Checkmk

    A single object cares about one activation for all affected sites.

    It is used to execute an activation using ActivateChangesManager.start().  During execution it
    persists it's activation information. This makes it possible to gather the activation state
    asynchronously.

    Prepares the snapshots for synchronization and handles all the ActivateChangesSite objects that
    manage the activation for the single sites.
    """
    # Temporary data
    activation_tmp_base_dir = cmk.utils.paths.tmp_dir + "/wato/activation"
    # Persisted data
    activation_persisted_dir = cmk.utils.paths.var_dir + "/wato/activation"

    def __init__(self):
        self._sites = []  # type: List[SiteId]
        self._activate_until = None  # type: Optional[str]
        self._comment = None  # type: Optional[str]
        self._activate_foreign = False
        self._activation_id = None  # type: Optional[str]
        self._snapshot_id = None  # TODO: Never set?!
        if not os.path.exists(self.activation_persisted_dir):
            os.makedirs(self.activation_persisted_dir)
        super(ActivateChangesManager, self).__init__()

    def load_activation(self, activation_id):
        self._activation_id = activation_id

        if not os.path.exists(self._info_path()):
            raise MKUserError(None, "Unknown activation process")

        self._load_activation()

    # Creates the snapshot and starts the single site sync processes. In case these
    # steps could not be started, exceptions are raised and have to be handled by
    # the caller.
    #
    # On success a separate thread is started that writes it's state to a state file
    # below "var/check_mk/wato/activation/<id>_general.state". The <id> is written to
    # the javascript code and can be used for fetching the activation state while
    # the activation is running.
    #
    # For each site a separate thread is started that controls the activation of the
    # configuration on that site. The state is checked by the general activation
    # thread.
    def start(
        self,
        sites,  # type: List[SiteId]
        activate_until=None,  # type: Optional[str]
        comment=None,  # type: Optional[str]
        activate_foreign=False,  # type: bool
        prevent_activate=False  # type: bool
    ):
        self._sites = self._get_sites(sites)
        self._activate_until = (self._get_last_change_id()
                                if activate_until is None else activate_until)
        self._comment = comment
        self._activate_foreign = activate_foreign
        self._activation_id = self._new_activation_id()
        self._time_started = time.time()
        self._snapshot_id = None
        self._prevent_activate = prevent_activate

        self._verify_valid_host_config()
        self._save_activation()

        self._pre_activate_changes()
        self._create_snapshots()
        self._save_activation()

        self._start_activation()

        return self._activation_id

    def _verify_valid_host_config(self):
        # TODO: Cleanup this local import
        import cmk.gui.watolib.hosts_and_folders  # pylint: disable=redefined-outer-name
        defective_hosts = cmk.gui.watolib.hosts_and_folders.validate_all_hosts([], force_all=True)
        if defective_hosts:
            raise MKUserError(
                None,
                _("You cannot activate changes while some hosts have "
                  "an invalid configuration: ") + ", ".join([
                      '<a href="%s">%s</a>' %
                      (cmk.gui.watolib.hosts_and_folders.folder_preserving_link(
                          [("mode", "edit_host"), ("host", hn)]), hn) for hn in defective_hosts
                  ]))

    def activate_until(self):
        return self._activate_until

    def wait_for_completion(self):
        while self.is_running():
            time.sleep(0.5)

    # Check whether or not at least one site thread is still working
    # (flock on the <activation_id>/site_<site_id>.mk file)
    def is_running(self):
        state = self.get_state()

        for site_id in self._sites:
            site_state = state["sites"][site_id]

            # The site_state file may be missing/empty, if the operation has started recently.
            # However, if the file is still missing after a considerable amount
            # of time, we consider this site activation as dead
            seconds_since_start = time.time() - self._time_started
            if site_state == {} and seconds_since_start > html.request.request_timeout - 10:
                continue

            if site_state == {} or site_state["_phase"] == PHASE_INITIALIZED:
                # Just been initialized. Treat as running as it has not been
                # started and could not lock the site stat file yet.
                return True  # -> running

            # Check whether or not the process is still there
            try:
                os.kill(site_state["_pid"], 0)
                return True  # -> running
            except OSError as e:
                # 3: not running
                # 1: operation not permitted (another process reused this)
                if e.errno in [3, 1]:
                    pass  # -> not running
                else:
                    raise

        return False  # No site reported running -> not running

    def _new_activation_id(self):
        return cmk.gui.utils.gen_id()

    def _get_sites(self, sites):
        for site_id in sites:
            if site_id not in activation_sites():
                raise MKUserError("sites", _("The site \"%s\" does not exist.") % site_id)

        return sites

    def _info_path(self):
        return "%s/%s/info.mk" % (self.activation_tmp_base_dir, self._activation_id)

    def _site_snapshot_file(self, site_id):
        return "%s/%s/site_%s_sync.tar.gz" % (self.activation_tmp_base_dir, self._activation_id,
                                              site_id)

    def _load_activation(self):
        self.__dict__.update(store.load_object_from_file(self._info_path(), {}))

    def _save_activation(self):
        try:
            os.makedirs(os.path.dirname(self._info_path()))
        except OSError as e:
            if e.errno == errno.EEXIST:
                pass
            else:
                raise

        return store.save_object_to_file(
            self._info_path(), {
                "_sites": self._sites,
                "_activate_until": self._activate_until,
                "_comment": self._comment,
                "_activate_foreign": self._activate_foreign,
                "_activation_id": self._activation_id,
                "_snapshot_id": self._snapshot_id,
                "_time_started": self._time_started,
            })

    # Give hooks chance to do some pre-activation things (and maybe stop
    # the activation)
    def _pre_activate_changes(self):
        # TODO: Cleanup this local import
        import cmk.gui.watolib.hosts_and_folders  # pylint: disable=redefined-outer-name
        try:
            if hooks.registered('pre-distribute-changes'):
                hooks.call("pre-distribute-changes",
                           cmk.gui.watolib.hosts_and_folders.collect_all_hosts())
        except Exception as e:
            logger.exception("error calling pre-distribute-changes hook")
            if config.debug:
                raise
            raise MKUserError(None, _("Can not start activation: %s") % e)

    def _create_snapshots(self):
        with store.lock_checkmk_configuration():
            if not self._changes:
                raise MKUserError(None, _("Currently there are no changes to activate."))

            if self._get_last_change_id() != self._activate_until:
                raise MKUserError(
                    None,
                    _("Another change has been made in the meantime. Please review it "
                      "to ensure you also want to activate it now and start the "
                      "activation again."))

            # Create (legacy) WATO config snapshot
            start = time.time()
            logger.debug("Snapshot creation started")
            # TODO: Remove/Refactor once new changes mechanism has been implemented
            #       This single function is responsible for the slow activate changes (python tar packaging..)
            snapshot_name = cmk.gui.watolib.snapshots.create_snapshot(self._comment)
            log_audit(None, "snapshot-created", _("Created snapshot %s") % snapshot_name)

            if self._activation_id is None:
                raise Exception("activation ID is not set")

            work_dir = os.path.join(self.activation_tmp_base_dir, self._activation_id)

            snapshot_manager = SnapshotManagerFactory().factory(work_dir,
                                                                self._site_snapshot_settings())
            snapshot_manager.generate_snapshots()

            logger.debug("Snapshot creation took %.4f", time.time() - start)

    def _site_snapshot_settings(self):
        # type: () -> Dict[SiteId, SnapshotSettings]
        snapshot_settings = {}

        site_configs = cmk.gui.watolib.sites.SiteManagementFactory().factory().load_sites()

        for site_id in self._sites:
            self._check_snapshot_creation_permissions(site_id)

            work_dir = self._get_site_tmp_dir(site_id)

            if cmk_version.is_managed_edition():
                # Change all default replication paths to be in the site specific temporary directory
                # These paths are then packed into the sync snapshot
                snapshot_components = [
                    _replace_omd_root(work_dir, repl_comp)
                    for repl_comp in self._get_replication_components(site_id)
                ]

                # Add site-specific global settings
                snapshot_components.append(
                    ReplicationPath(
                        ty="file",
                        ident="sitespecific",
                        path=os.path.join(work_dir, "site_globals", "sitespecific.mk"),
                        excludes=[],
                    ))

            else:
                snapshot_components = self._get_replication_components(site_id)

            # Generate a quick reference_by_name for each component
            component_names = {c[1] for c in snapshot_components}

            snapshot_settings[site_id] = SnapshotSettings(
                snapshot_path=self._site_snapshot_file(site_id),
                work_dir=work_dir,
                snapshot_components=snapshot_components,
                component_names=component_names,
                site_config=site_configs[site_id],
            )

        return snapshot_settings

    def _get_site_tmp_dir(self, site_id):
        if self._activation_id is None:
            raise Exception("activation ID is not set")
        return os.path.join(self.activation_tmp_base_dir, self._activation_id,
                            "sync-%s-specific-%.4f" % (site_id, time.time()))

    def _check_snapshot_creation_permissions(self, site_id):
        if self._site_has_foreign_changes(site_id) and not self._activate_foreign:
            if not config.user.may("wato.activateforeign"):
                raise MKUserError(
                    None,
                    _("There are some changes made by your colleagues that you can not "
                      "activate because you are not permitted to. You can only activate "
                      "the changes on the sites that are not affected by these changes. "
                      "<br>"
                      "If you need to activate your changes on all sites, please contact "
                      "a permitted user to do it for you."))

            raise MKUserError(
                None,
                _("There are some changes made by your colleagues and you did not "
                  "confirm to activate these changes. In order to proceed, you will "
                  "have to confirm the activation or ask you colleagues to activate "
                  "these changes in their own."))

    def _get_replication_components(self, site_id):
        # type: (SiteId) -> List[ReplicationPath]
        paths = get_replication_paths()[:]
        # Remove Event Console settings, if this site does not want it (might
        # be removed in some future day)
        if not config.sites[site_id].get("replicate_ec"):
            paths = [e for e in paths if e.ident not in ["mkeventd", "mkeventd_mkp"]]

        # Remove extensions if site does not want them
        if not config.sites[site_id].get("replicate_mkps"):
            paths = [e for e in paths if e.ident not in ["local", "mkps"]]

        return paths

    def _start_activation(self):
        self._log_activation()
        for site_id in self._sites:
            self._start_site_activation(site_id)

    def _start_site_activation(self, site_id):
        self._log_site_activation(site_id)

        # This is doing the first fork and the ActivateChangesSite() is doing the second
        # (to avoid zombie processes when sync processes exit)
        p = multiprocessing.Process(target=self._do_start_site_activation, args=(site_id,))
        p.start()
        p.join()

    def _do_start_site_activation(self, site_id):
        try:
            site_activation = ActivateChangesSite(site_id, self._activation_id,
                                                  self._site_snapshot_file(site_id),
                                                  self._prevent_activate)
            site_activation.load()
            site_activation.start()
            os._exit(0)
        except Exception:
            logger.exception("error starting site activation for site %s", site_id)

    def _log_activation(self):
        log_msg = _("Starting activation (Sites: %s)") % ",".join(self._sites)
        log_audit(None, "activate-changes", log_msg)

        if self._comment:
            log_audit(None, "activate-changes", "%s: %s" % (_("Comment"), self._comment))

    def _log_site_activation(self, site_id):
        log_audit(None, "activate-changes", _("Started activation of site %s") % site_id)

    def get_state(self):
        return {
            "sites": {
                site_id: self._load_site_state(site_id)  #
                for site_id in self._sites
            }
        }

    def get_site_state(self, site_id):
        return self._load_site_state(site_id)

    def _load_site_state(self, site_id):
        return store.load_object_from_file(self.site_state_path(site_id), {})

    def site_state_path(self, site_id):
        if self._activation_id is None:
            raise Exception("activation ID is not set")
        return os.path.join(self.activation_tmp_base_dir, self._activation_id,
                            self.site_filename(site_id))

    @classmethod
    def site_filename(cls, site_id):
        return "site_%s.mk" % site_id


class ABCSnapshotManager(six.with_metaclass(abc.ABCMeta, object)):
    def __init__(self, activation_work_dir, site_snapshot_settings):
        # type: (str, Dict[SiteId, SnapshotSettings]) -> None
        super(ABCSnapshotManager, self).__init__()
        self._activation_work_dir = activation_work_dir
        self._site_snapshot_settings = site_snapshot_settings

        # Stores site and folder specific information to speed-up the snapshot generation
        self._logger = logger.getChild(self.__class__.__name__)

    @abc.abstractmethod
    def generate_snapshots(self):
        # type: () -> None
        raise NotImplementedError()


class CRESnapshotManager(ABCSnapshotManager):
    def generate_snapshots(self):
        # type: () -> None
        with SnapshotCreator(self._activation_work_dir,
                             get_replication_paths()) as snapshot_creator:
            for site_id, snapshot_settings in self._site_snapshot_settings.items():
                self._create_site_sync_snapshot(site_id, snapshot_settings, snapshot_creator)

    def _create_site_sync_snapshot(self, site_id, snapshot_settings, snapshot_creator):
        # type: (SiteId, SnapshotSettings, SnapshotCreator) -> None
        create_site_globals_file(site_id, snapshot_settings.work_dir, snapshot_settings.site_config)

        # Add site-specific global settings
        site_specific_paths = [
            ReplicationPath(
                ty="file",
                ident="sitespecific",
                path=os.path.join(snapshot_settings.work_dir, "sitespecific.mk"),
                excludes=[],
            )
        ]  # type: List[ReplicationPath]

        snapshot_creator.generate_snapshot(target_filepath=snapshot_settings.snapshot_path,
                                           generic_components=snapshot_settings.snapshot_components,
                                           custom_components=site_specific_paths,
                                           reuse_identical_snapshots=True)

        shutil.rmtree(snapshot_settings.work_dir)


class SnapshotManagerFactory(object):
    @staticmethod
    def factory(work_dir, site_snapshot_settings):
        # type: (str, Dict[SiteId, SnapshotSettings]) -> ABCSnapshotManager
        if cmk_version.is_managed_edition():
            import cmk.gui.cme.managed_snapshots as managed_snapshots  # pylint: disable=no-name-in-module
            cls = managed_snapshots.CMESnapshotManager  # type: Type[ABCSnapshotManager]
        else:
            cls = CRESnapshotManager

        return cls(work_dir, site_snapshot_settings)


@gui_background_job.job_registry.register
class ActivationCleanupBackgroundJob(WatoBackgroundJob):
    job_prefix = "activation_cleanup"

    @classmethod
    def gui_title(cls):
        return _("Activation cleanup")

    def __init__(self):
        super(ActivationCleanupBackgroundJob, self).__init__(
            self.job_prefix,
            title=self.gui_title(),
            lock_wato=False,
            stoppable=False,
        )

    def do_execute(self, job_interface):
        self._do_housekeeping()
        job_interface.send_result_message(_("Activation cleanup finished"))

    def _do_housekeeping(self):
        # type: () -> None
        """Cleanup stale activations in case it is needed"""
        with store.lock_checkmk_configuration():
            for activation_id in self._existing_activation_ids():
                self._logger.info("Check activation: %s", activation_id)
                delete = False
                manager = ActivateChangesManager()
                manager.load()

                # Try to detect whether or not the activation is still in progress. In case the
                # activation information can not be read, it is likely that the activation has
                # just finished while we were iterating the activations.
                # In case loading fails continue with the next activations
                try:
                    delete = True

                    try:
                        manager.load_activation(activation_id)
                        delete = not manager.is_running()
                    except MKUserError:
                        # "Unknown activation process", is normal after activation -> Delete, but no
                        # error message logging
                        self._logger.debug("Is not running")
                except Exception as e:
                    self._logger.warning("  Failed to load activation (%s), trying to delete...",
                                         e,
                                         exc_info=True)

                self._logger.info("  -> %s", "Delete" if delete else "Keep")
                if not delete:
                    continue

                activation_dir = os.path.join(ActivateChangesManager.activation_tmp_base_dir,
                                              activation_id)
                try:
                    shutil.rmtree(activation_dir)
                except Exception:
                    self._logger.error("  Failed to delete the activation directory '%s'" %
                                       activation_dir,
                                       exc_info=True)

    def _existing_activation_ids(self):
        try:
            files = os.listdir(ActivateChangesManager.activation_tmp_base_dir)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise
            files = []

        ids = []
        for activation_id in files:
            if len(activation_id) == 36 and activation_id[8] == "-" and activation_id[13] == "-":
                ids.append(activation_id)
        return ids


def execute_activation_cleanup_background_job():
    # type: () -> None
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log. """
    job = ActivationCleanupBackgroundJob()
    if job.is_active():
        logger.debug("Another activation cleanup job is already running: Skipping this time")
        return

    job.set_function(job.do_execute)
    job.start()


class ActivateChangesSite(multiprocessing.Process, ActivateChanges):
    """Executes and monitors a single activation for one site"""
    def __init__(self, site_id, activation_id, site_snapshot_file, prevent_activate=False):
        super(ActivateChangesSite, self).__init__()

        self._site_id = site_id
        self._site_changes = []
        self._activation_id = activation_id
        self._snapshot_file = site_snapshot_file
        self.daemon = True
        self._prevent_activate = prevent_activate

        self._time_started = None  # type: Optional[float]
        self._time_updated = None
        self._time_ended = None
        self._phase = None
        self._state = None
        self._status_text = None
        self._status_details = None
        self._warnings = []
        self._pid = None
        self._expected_duration = 10.0

        self._set_result(PHASE_INITIALIZED, _("Initialized"))

    def load(self):
        super(ActivateChangesSite, self).load()
        self._load_this_sites_changes()
        self._load_expected_duration()

    def _load_this_sites_changes(self):
        all_changes = self._changes_of_site(self._site_id)

        change_id = self._activate_until_change_id()

        # Find the last activated change and return all changes till this entry
        # (including the one we were searching for)
        changes = []
        for change in all_changes:
            changes.append(change)
            if change["id"] == change_id:
                break

        self._site_changes = changes

    def run(self):
        # Ensure this process is not detected as apache process by the apache init script
        daemon.set_procname(b"cmk-activate-changes")

        # Detach from parent (apache) -> Remain running when apache is restarted
        os.setsid()

        # Cleanup existing livestatus connections (may be opened later when needed)
        if g:
            sites_disconnect()

        # Cleanup resources of the apache
        for x in range(3, 256):
            try:
                os.close(x)
            except OSError as e:
                if e.errno == errno.EBADF:
                    pass
                else:
                    raise

        # Reinitialize logging targets
        log.init_logging()  # NOTE: We run in a subprocess!

        try:
            self._do_run()
        except Exception:
            logger.exception("error running activate changes")

    def _do_run(self):
        try:
            self._time_started = time.time()
            self._lock_activation()

            if self.is_sync_needed(self._site_id):
                self._synchronize_site()

            self._set_result(PHASE_FINISHING, _("Finalizing"))
            configuration_warnings = {}
            if self._prevent_activate:
                self._confirm_synchronized_changes()
            else:
                if self._is_activate_needed(self._site_id):
                    configuration_warnings = self._do_activate()
                self._confirm_activated_changes()

            self._set_done_result(configuration_warnings)
        except Exception as e:
            logger.exception("error activating changes")
            self._set_result(PHASE_DONE, _("Failed"), _("Failed: %s") % e, state=STATE_ERROR)

        finally:
            self._unlock_activation()

            # Create a copy of last result in the persisted dir
            manager = ActivateChangesManager()
            manager.load()
            manager.load_activation(self._activation_id)
            source_path = manager.site_state_path(self._site_id)
            shutil.copy(source_path, manager.activation_persisted_dir)

    def _activate_until_change_id(self):
        manager = ActivateChangesManager()
        manager.load()
        manager.load_activation(self._activation_id)
        return manager.activate_until()

    def _set_done_result(self, configuration_warnings):
        if any(configuration_warnings.values()):
            self._warnings = configuration_warnings
            details = self._render_warnings(configuration_warnings)
            self._set_result(PHASE_DONE, _("Activated"), details, state=STATE_WARNING)
        else:
            self._set_result(PHASE_DONE, _("Success"), state=STATE_SUCCESS)

    def _render_warnings(self, configuration_warnings):
        html_code = u"<div class=warning>"
        html_code += "<b>%s</b>" % _("Warnings:")
        html_code += "<ul>"
        for domain, warnings in sorted(configuration_warnings.items()):
            for warning in warnings:
                html_code += "<li>%s: %s</li>" % \
                    (escaping.escape_attribute(domain), escaping.escape_attribute(warning))
        html_code += "</ul>"
        html_code += "</div>"
        return html_code

    def _lock_activation(self):
        # This locks the site specific replication status file
        repl_status = _load_site_replication_status(self._site_id, lock=True)
        try:
            if self._is_currently_activating(repl_status):
                raise MKGeneralException(
                    _("The site is currently locked by another activation process. Please try again later"
                     ))

            # This is needed to detect stale activation progress entries
            # (where activation thread is not running anymore)
            self._mark_running()
        finally:
            # This call unlocks the replication status file after setting "current_activation"
            # which will prevent other users from starting an activation for this site.
            _update_replication_status(self._site_id, {"current_activation": self._activation_id})

    def _is_currently_activating(self, rep_status):
        if not rep_status.get("current_activation"):
            return False

        #
        # Is this activation still in progress?
        #

        current_activation_id = rep_status.get(self._site_id, {}).get("current_activation")

        manager = ActivateChangesManager()
        manager.load()

        try:
            manager.load_activation(current_activation_id)
        except MKUserError:
            return False  # Not existant anymore!

        if manager.is_running():
            return True

        return False

    def _mark_running(self):
        self._pid = os.getpid()
        self._set_result(PHASE_STARTED, _("Started"))

    def _unlock_activation(self):
        _update_replication_status(self._site_id, {
            "last_activation": self._activation_id,
            "current_activation": None,
        })

    # This is done on the central site to initiate the sync process
    def _synchronize_site(self):
        self._set_result(PHASE_SYNC, _("Synchronizing"))

        start = time.time()

        result = self._push_snapshot_to_site()

        duration = time.time() - start
        self.update_activation_time(self._site_id, ACTIVATION_TIME_SYNC, duration)

        # Pre 1.2.7i3 and sites return True on success and a string on error.
        # 1.2.7i3 and later return a list of warning messages on success.
        # [] means OK and no warnings. The error handling is unchanged.
        # Since 1.4.0i3 the old API (True -> success, <unicode>/<str> -> error)
        if isinstance(result, list):
            result = True

        if result is not True:
            raise MKGeneralException(_("Failed to synchronize with site: %s") % result)

    def _push_snapshot_to_site(self):
        """Calls a remote automation call push-snapshot which is handled by AutomationPushSnapshot()"""
        site = config.site(self._site_id)

        url = html.makeuri_contextless(
            [
                ("command", "push-snapshot"),
                ("secret", site["secret"]),
                ("siteid", site["id"]),
                ("debug", config.debug and "1" or ""),
            ],
            filename=site["multisiteurl"] + "automation.py",
        )

        response_text = self._upload_file(url, site.get('insecure', False))

        try:
            return ast.literal_eval(response_text)
        except SyntaxError:
            raise cmk.gui.watolib.automations.MKAutomationException(
                _("Garbled automation response: <pre>%s</pre>") %
                (escaping.escape_attribute(response_text)))

    def _upload_file(self, url, insecure):
        return cmk.gui.watolib.automations.get_url(
            url, insecure, files={"snapshot": open(self._snapshot_file, "r")})

    def _cleanup_snapshot(self):
        try:
            os.unlink(self._snapshot_file)
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass  # Not existant -> OK
            else:
                raise

    def _do_activate(self):
        self._set_result(PHASE_ACTIVATE, _("Activating"))

        start = time.time()

        configuration_warnings = self._call_activate_changes_automation()

        duration = time.time() - start
        self.update_activation_time(self._site_id, ACTIVATION_TIME_RESTART, duration)
        return configuration_warnings

    def _call_activate_changes_automation(self):
        domains = self._get_domains_needing_activation()

        if config.site_is_local(self._site_id):
            return execute_activate_changes(domains)

        try:
            response = cmk.gui.watolib.automations.do_remote_automation(
                config.site(self._site_id), "activate-changes", [
                    ("domains", repr(domains)),
                    ("site_id", self._site_id),
                ])
        except cmk.gui.watolib.automations.MKAutomationException as e:
            if "Invalid automation command: activate-changes" in "%s" % e:
                raise MKGeneralException(
                    "Activate changes failed (%s). The version of this site may be too old.")
            raise

        return response

    def _get_domains_needing_activation(self):
        domains = set([])
        for change in self._site_changes:
            if change["need_restart"]:
                domains.update(change["domains"])
        return sorted(list(domains))

    def _confirm_activated_changes(self):
        site_changes = SiteChanges(self._site_id)
        changes = site_changes.load(lock=True)

        try:
            changes = changes[len(self._site_changes):]
        finally:
            site_changes.save(changes)

    def _confirm_synchronized_changes(self):
        site_changes = SiteChanges(self._site_id)
        changes = site_changes.load(lock=True)
        try:
            for change in changes:
                change["need_sync"] = False
        finally:
            site_changes.save(changes)

    def _set_result(self, phase, status_text, status_details=None, state=STATE_SUCCESS):
        self._phase = phase
        self._status_text = status_text

        if phase != PHASE_INITIALIZED:
            self._set_status_details(phase, status_details)

        self._time_updated = time.time()
        if phase == PHASE_DONE:
            self._time_ended = self._time_updated
            self._state = state

        self._save_state()

    def _set_status_details(self, phase, status_details):
        if self._time_started is None:
            raise Exception("start time not set")
        self._status_details = _("Started at: %s.") % render.time_of_day(self._time_started)

        if phase != PHASE_DONE:
            estimated_time_left = self._expected_duration - (time.time() - self._time_started)
            if estimated_time_left < 0:
                self._status_details += " " + _("Takes %.1f seconds longer than expected") % \
                                                                        abs(estimated_time_left)
            else:
                self._status_details += " " + _("Approximately finishes in %.1f seconds") % \
                                                                        estimated_time_left
        else:
            self._status_details += _(" Finished at: %s.") % render.time_of_day(self._time_ended)

        if status_details:
            self._status_details += "<br>%s" % status_details

    def _save_state(self):
        state_path = os.path.join(ActivateChangesManager.activation_tmp_base_dir,
                                  self._activation_id,
                                  ActivateChangesManager.site_filename(self._site_id))

        return store.save_object_to_file(
            state_path, {
                "_site_id": self._site_id,
                "_phase": self._phase,
                "_state": self._state,
                "_status_text": self._status_text,
                "_status_details": self._status_details,
                "_warnings": self._warnings,
                "_time_started": self._time_started,
                "_time_updated": self._time_updated,
                "_time_ended": self._time_ended,
                "_expected_duration": self._expected_duration,
                "_pid": self._pid,
            })

    def _load_expected_duration(self):
        times = self.get_activation_times(self._site_id)
        duration = 0.0

        if self.is_sync_needed(self._site_id):
            duration += times.get(ACTIVATION_TIME_SYNC, 0)

        if self._is_activate_needed(self._site_id):
            duration += times.get(ACTIVATION_TIME_RESTART, 0)

        # In case expected is 0, calculate with 10 seconds instead of failing
        if duration == 0.0:
            duration = 10.0

        self._expected_duration = duration


def execute_activate_changes(domains):
    domains = set(domains).union(ABCConfigDomain.get_always_activate_domain_idents())

    results = {}
    for domain in sorted(domains):
        domain_class = ABCConfigDomain.get_class(domain)
        warnings = domain_class().activate()
        results[domain] = warnings or []

    return results


def confirm_all_local_changes():
    ActivateChanges().confirm_site_changes(config.omd_site())


def get_pending_changes_info():
    changes = ActivateChanges()
    return changes.get_changes_estimate()


def get_number_of_pending_changes():
    changes = ActivateChanges()
    changes.load()
    return len(changes.grouped_changes())


def create_site_globals_file(site_id, tmp_dir, site_config):
    # type: (SiteId, str, SiteConfiguration) -> None
    store.makedirs(tmp_dir)

    site_globals = site_config.get("globals", {}).copy()
    site_globals.update({
        "wato_enabled": not site_config.get("disable_wato", True),
        "userdb_automatic_sync": site_config.get("user_sync", user_sync_default_config(site_id)),
    })

    store.save_object_to_file(tmp_dir + "/sitespecific.mk", site_globals)
