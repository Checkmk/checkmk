#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Managing configuration activation of Checkmk

The major elements here are:

ActivateChangesManager   - Coordinates a single activation of Checkmk config changes for all
                           affected sites.
SnapshotManager          - Coordinates the collection and packing of snapshots
ABCSnapshotDataCollector - Copying or generating files to be put into snapshots
SnapshotCreator          - Packing the snapshots into snapshot archives
ActivateChangesSite      - Executes the activation procedure for a single site.
"""

import io
import errno
import ast
import os
import shutil
import time
import abc
import multiprocessing
import traceback
import subprocess
import hashlib
from logging import Logger
from pathlib import Path
from typing import Dict, Set, List, Optional, Tuple, Union, NamedTuple, Any

import psutil  # type: ignore[import]
import werkzeug.urls
from six import ensure_binary, ensure_str

from livestatus import (
    SiteId,
    SiteConfiguration,
)

import cmk.utils
import cmk.utils.paths
import cmk.utils.version as cmk_version
import cmk.utils.daemon as daemon
import cmk.utils.store as store
import cmk.utils.render as render
from cmk.utils.werks import parse_check_mk_version

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui.type_defs import ConfigDomainName, HTTPVariables
import cmk.gui.utils
import cmk.gui.hooks as hooks
from cmk.gui.sites import (
    SiteStatus,
    states as sites_states,
    disconnect as sites_disconnect,
)
import cmk.gui.config as config
import cmk.gui.log as log
import cmk.gui.escaping as escaping
from cmk.gui.i18n import _
from cmk.gui.globals import g, request as _request
from cmk.gui.log import logger
from cmk.gui.exceptions import (
    MKGeneralException,
    RequestTimeout,
    MKUserError,
    MKAuthException,
)
import cmk.gui.gui_background_job as gui_background_job
from cmk.gui.plugins.userdb.utils import user_sync_default_config
from cmk.gui.plugins.watolib.utils import wato_fileheader

import cmk.gui.watolib.git
import cmk.gui.watolib.automations
import cmk.gui.watolib.utils
import cmk.gui.watolib.sidebar_reload
import cmk.gui.watolib.snapshots
from cmk.gui.watolib.config_sync import SnapshotCreator, ReplicationPath
from cmk.gui.watolib.wato_background_job import WatoBackgroundJob
from cmk.gui.watolib.config_sync import extract_from_buffer
from cmk.gui.watolib.global_settings import save_site_global_settings
from cmk.gui.watolib.automation_commands import automation_command_registry, AutomationCommand

from cmk.gui.watolib.changes import (
    SiteChanges,
    log_audit,
    activation_sites,
)
from cmk.gui.plugins.watolib import ABCConfigDomain

# TODO: Make private
PHASE_INITIALIZED = "initialized"  # Process has been initialized (not in thread yet)
PHASE_QUEUED = "queued"  # Process queued by site scheduler
PHASE_STARTED = "started"  # Process just started, nothing happened yet
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

SnapshotSettings = NamedTuple(
    "SnapshotSettings",
    [
        # TODO: Refactor to Path
        ("snapshot_path", str),
        # TODO: Refactor to Path
        ("work_dir", str),
        # TODO: Clarify naming (-> replication path or snapshot component?)
        ("snapshot_components", List[ReplicationPath]),
        ("component_names", Set[str]),
        ("site_config", SiteConfiguration),
        # TODO: Remove with 1.8
        ("create_pre_17_snapshot", bool),
    ])

# Directories and files to synchronize during replication
_replication_paths: List[ReplicationPath] = []

ReplicationPathPre16 = Union[Tuple[str, str, str, List[str]], Tuple[str, str, str]]
ReplicationPathCompat = Union[ReplicationPathPre16, ReplicationPath]
ConfigWarnings = Dict[ConfigDomainName, List[str]]
ActivationId = str
ActivationState = Dict[str, Dict[str, Any]]


def add_replication_paths(paths: List[ReplicationPathCompat]) -> None:

    clean_paths: List[ReplicationPath] = []

    for path in paths:
        # Be compatible to pre 1.7 tuple syntax and convert it to the
        # new internal strucure
        # TODO: Remove with 1.8
        if isinstance(path, tuple) and not isinstance(path, ReplicationPath):
            if len(path) not in [3, 4]:
                raise Exception("invalid replication path %r" % (path,))

            # add_replication_paths with tuples used absolute paths, make them relative to our
            # OMD_ROOT directory now
            site_path = os.path.relpath(path[2], cmk.utils.paths.omd_root)

            excludes: List[str] = []
            # mypy does not understand this
            if len(path) == 4:
                excludes = path[3]  # type: ignore[misc]

            clean_paths.append(ReplicationPath(path[0], path[1], site_path, excludes))
            continue

        clean_paths.append(path)

    _replication_paths.extend(clean_paths)


def get_replication_paths() -> List[ReplicationPath]:
    paths: List[ReplicationPath] = [
        ReplicationPath(
            "dir", "check_mk",
            os.path.relpath(cmk.gui.watolib.utils.wato_root_dir(), cmk.utils.paths.omd_root), []),
        ReplicationPath(
            "dir", "multisite",
            os.path.relpath(cmk.gui.watolib.utils.multisite_dir(), cmk.utils.paths.omd_root), []),
        ReplicationPath("file", "htpasswd",
                        os.path.relpath(cmk.utils.paths.htpasswd_file, cmk.utils.paths.omd_root),
                        []),
        ReplicationPath(
            "file", "auth.secret",
            os.path.relpath('%s/auth.secret' % os.path.dirname(cmk.utils.paths.htpasswd_file),
                            cmk.utils.paths.omd_root), []),
        ReplicationPath(
            "file", "auth.serials",
            os.path.relpath('%s/auth.serials' % os.path.dirname(cmk.utils.paths.htpasswd_file),
                            cmk.utils.paths.omd_root), []),
        # Also replicate the user-settings of Multisite? While the replication
        # as such works pretty well, the count of pending changes will not
        # know.
        ReplicationPath("dir", "usersettings",
                        os.path.relpath(cmk.utils.paths.var_dir + "/web", cmk.utils.paths.omd_root),
                        ["*/report-thumbnails"]),
        ReplicationPath(
            "dir", "mkps",
            os.path.relpath(cmk.utils.paths.var_dir + "/packages", cmk.utils.paths.omd_root), []),
        ReplicationPath(
            "dir", "local",
            os.path.relpath(cmk.utils.paths.omd_root + "/local", cmk.utils.paths.omd_root), []),
    ]

    # TODO: Move this to CEE specific code again
    if not cmk_version.is_raw_edition():
        paths += [
            ReplicationPath(
                "dir", "liveproxyd",
                os.path.relpath(cmk.gui.watolib.utils.liveproxyd_config_dir(),
                                cmk.utils.paths.omd_root), []),
        ]

    # Include rule configuration into backup/restore/replication. Current
    # status is not backed up.
    if config.mkeventd_enabled:
        _rule_pack_dir = str(ec.rule_pack_dir().relative_to(cmk.utils.paths.omd_root))
        paths.append(ReplicationPath("dir", "mkeventd", _rule_pack_dir, []))

        _mkp_rule_pack_dir = str(ec.mkp_rule_pack_dir().relative_to(cmk.utils.paths.omd_root))
        paths.append(ReplicationPath("dir", "mkeventd_mkp", _mkp_rule_pack_dir, []))

    # There are some edition specific paths available during unit tests when testing other
    # editions. Filter them out there, even when they are registered.
    filtered = _replication_paths[:]
    if not cmk_version.is_managed_edition():
        filtered = [
            p for p in filtered if p.ident not in {
                "customer_multisite", "customer_check_mk", "customer_gui_design", "gui_logo",
                "gui_logo_facelift", "gui_logo_dark"
            }
        ]

    return paths + filtered


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


def remove_site_config_directory(site_id: SiteId) -> None:
    work_dir = cmk.utils.paths.site_config_dir / site_id

    try:
        shutil.rmtree(str(work_dir))
    except OSError as e:
        if e.errno != errno.ENOENT:  # No such file or directory
            raise


class ActivateChanges:
    def __init__(self):
        self._repstatus = {}

        # Changes grouped by site
        self._changes_by_site = {}

        # A list of changes ordered by time and grouped by the change.
        # Each change contains a list of affected sites.
        self._changes = []

        super(ActivateChanges, self).__init__()

    def load(self):
        self._repstatus = _load_replication_status()
        self._load_changes()

    def _load_changes(self):
        self._changes_by_site = {}
        changes = {}

        for site_id in activation_sites():
            site_changes = SiteChanges(site_id).load()
            self._changes_by_site[site_id] = site_changes

            if not site_changes:
                continue

            # Assume changes can be recorded multiple times and deduplicate them.
            for change in site_changes:
                change_id = change["id"]

                if change_id not in changes:
                    changes[change_id] = change.copy()

                affected_sites = changes[change_id].setdefault("affected_sites", [])
                affected_sites.append(site_id)

        self._changes = sorted(changes.items(), key=lambda k_v: k_v[1]["time"])

    def confirm_site_changes(self, site_id):
        SiteChanges(site_id).clear()
        cmk.gui.watolib.sidebar_reload.need_sidebar_reload()

    def get_changes_estimate(self) -> Optional[str]:
        changes_counter = 0
        for site_id in activation_sites():
            changes_counter += len(SiteChanges(site_id).load())
            if changes_counter > 10:
                return _("10+ changes")
        if changes_counter == 1:
            return _("1 change")
        if changes_counter > 1:
            return _("%d changes") % changes_counter
        return None

    def grouped_changes(self):
        return self._changes

    def _changes_of_site(self, site_id):
        return self._changes_by_site[site_id]

    def dirty_and_active_activation_sites(self) -> List[SiteId]:
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

    def _site_is_online(self, status: str) -> bool:
        return status in ["online", "disabled"]

    def _get_site_status(self, site_id: SiteId, site: SiteConfiguration) -> Tuple[SiteStatus, str]:
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

    def _get_last_change_id(self) -> str:
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
    """Manages the activation of pending configuration changes

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

    # These keys will be persisted in <activation_id>/info.mk
    info_keys = (
        "_sites",
        "_activate_until",
        "_comment",
        "_activate_foreign",
        "_activation_id",
        "_time_started",
    )

    def __init__(self):
        self._sites: List[SiteId] = []
        self._site_snapshot_settings: Dict[SiteId, SnapshotSettings] = {}
        self._activate_until: Optional[str] = None
        self._comment: Optional[str] = None
        self._activate_foreign = False
        self._activation_id: Optional[str] = None
        self._prevent_activate = False
        store.makedirs(self.activation_persisted_dir)
        super(ActivateChangesManager, self).__init__()

    def load_activation(self, activation_id: ActivationId) -> None:
        self._activation_id = activation_id
        from_file = self._load_activation_info(activation_id)
        for key in self.info_keys:
            setattr(self, key, from_file[key])

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
    def start(self,
              sites: List[SiteId],
              activate_until: Optional[str] = None,
              comment: Optional[str] = None,
              activate_foreign: bool = False,
              prevent_activate: bool = False) -> ActivationId:
        """Start activation of changes.

        For each site one background process will be launched, handling the activation of one
        particular site. Handling of remote sites is done transparently through the use of
        SyncSnapshots.

        Args:
            sites:
                The sites for which activation should be started.

            activate_until:
                The most current change-id which shall be activated. If newer changes are present
                the activation is aborted.

            comment:
                A comment which will be persisted in the temporary info.mk file and stored with the
                newly created snapshot.

            activate_foreign:
                A boolean flag, indicating that even changes which do not originate from the
                user requesting the activation shall be activated. If this is not set and there
                are "foreign" changes, the activation will be aborted. In any case the user needs
                to have the `wato.activateforeign` permission.

            prevent_activate:
                Doesn't seem to be doing much. Remove?

        Returns:
            The activation-id under which to track the progress of this particular run.

        """
        self._activate_foreign = activate_foreign

        self._sites = self._get_sites(sites)
        self._site_snapshot_settings = self._get_site_snapshot_settings(self._sites)
        self._activate_until = (self._get_last_change_id()
                                if activate_until is None else activate_until)
        self._comment = comment
        self._activation_id = self._new_activation_id()
        self._time_started = time.time()
        self._prevent_activate = prevent_activate

        self._verify_valid_host_config()
        self._save_activation()

        self._pre_activate_changes()
        self._create_snapshots()
        self._save_activation()

        self._start_activation()

        return self._activation_id

    def _verify_valid_host_config(self):
        defective_hosts = cmk.gui.watolib.validate_all_hosts([], force_all=True)
        if defective_hosts:
            raise MKUserError(
                None,
                _("You cannot activate changes while some hosts have "
                  "an invalid configuration: ") + ", ".join([
                      '<a href="%s">%s</a>' %
                      (cmk.gui.watolib.folder_preserving_link([("mode", "edit_host"),
                                                               ("host", hn)]), hn)
                      for hn in defective_hosts
                  ]))

    def activate_until(self):
        return self._activate_until

    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """Wait for activation to be complete.

        Optionally a soft timeout can be given and waiting will stop. The return value will then
        be True if everything is completed and False if it isn't.

        Args:
            timeout: Optional timeout in seconds. If omitted the call will wait until completion.

        Returns:
            True if completed, False if still running.
        """
        start = time.time()
        while self.is_running():
            time.sleep(0.5)
            if timeout and start + timeout >= time.time():
                break

        completed = not self.is_running()
        return completed

    def is_running(self) -> bool:
        return bool(self.running_sites())

    def _activation_running(self, site_id: SiteId) -> bool:
        site_state = self.get_site_state(site_id)

        # The site_state file may be missing/empty, if the operation has started recently.
        # However, if the file is still missing after a considerable amount
        # of time, we consider this site activation as dead
        seconds_since_start = time.time() - self._time_started
        if site_state == {} and seconds_since_start > _request.request_timeout - 10:
            return False

        if site_state == {} or site_state["_phase"] == PHASE_INITIALIZED:
            # Just been initialized. Treat as running as it has not been
            # started and could not lock the site stat file yet.
            return True

        # Check whether or not the process is still there
        # The pid refers to
        # - the site scheduler PID as long as the site is in queue
        # - the site activate changes PID
        # - None, if the site was locked by another process
        if site_state["_pid"] is None:
            return False

        try:
            os.kill(site_state["_pid"], 0)
            return True
        except OSError as e:
            # ESRCH: no such process
            # EPERM: operation not permitted (another process reused this)
            # -> Both cases mean it is not running anymore
            if e.errno in [errno.EPERM, errno.ESRCH]:
                return False

            raise

    # Check whether or not at least one site thread is still working
    # (flock on the <activation_id>/site_<site_id>.mk file)
    def running_sites(self) -> List[SiteId]:
        running = []
        for site_id in self._sites:
            if self._activation_running(site_id):
                running.append(site_id)

        return running

    def _new_activation_id(self) -> ActivationId:
        return cmk.gui.utils.gen_id()

    def _get_sites(self, sites: List[SiteId]) -> List[SiteId]:
        for site_id in sites:
            if site_id not in activation_sites():
                raise MKUserError("sites", _("The site \"%s\" does not exist.") % site_id)

        return sites

    def _info_path(self, activation_id):
        return "%s/%s/info.mk" % (self.activation_tmp_base_dir, activation_id)

    def activations(self):
        for activation_id in os.listdir(self.activation_tmp_base_dir):
            yield activation_id, self._load_activation_info(activation_id)

    def _site_snapshot_file(self, site_id):
        return "%s/%s/site_%s_sync.tar.gz" % (self.activation_tmp_base_dir, self._activation_id,
                                              site_id)

    def _load_activation_info(self, activation_id):
        if not os.path.exists(self._info_path(activation_id)):
            raise MKUserError(None, "Unknown activation process")

        return store.load_object_from_file(self._info_path(activation_id), {})

    def _save_activation(self):
        store.makedirs(os.path.dirname(self._info_path(self._activation_id)))
        to_file = {key: getattr(self, key) for key in self.info_keys}
        return store.save_object_to_file(self._info_path(self._activation_id), to_file)

    # Give hooks chance to do some pre-activation things (and maybe stop
    # the activation)
    def _pre_activate_changes(self):
        try:
            if hooks.registered('pre-distribute-changes'):
                hooks.call("pre-distribute-changes", cmk.gui.watolib.collect_all_hosts())
        except Exception as e:
            logger.exception("error calling pre-distribute-changes hook")
            if config.debug:
                raise
            raise MKUserError(None, _("Can not start activation: %s") % e)

    def _create_snapshots(self):
        """Creates the needed SyncSnapshots for each applicable site.

        Some conflict prevention is being done. This function checks for the presence of
        newer changes than the ones to be activated.

        """
        with store.lock_checkmk_configuration():
            if not self._changes:
                raise MKUserError(None, _("Currently there are no changes to activate."))

            if self._get_last_change_id() != self._activate_until:
                raise MKUserError(
                    None,
                    _("Another change has been made in the meantime. Please review it "
                      "to ensure you also want to activate it now and start the "
                      "activation again."))

            backup_snapshot_proc = multiprocessing.Process(
                target=cmk.gui.watolib.snapshots.create_snapshot, args=(self._comment,))
            backup_snapshot_proc.start()

            if self._activation_id is None:
                raise Exception("activation ID is not set")

            logger.debug("Start creating config sync snapshots")
            start = time.time()
            work_dir = os.path.join(self.activation_tmp_base_dir, self._activation_id)

            # Do not create a snapshot for the local site. All files are already in place
            site_snapshot_settings = self._site_snapshot_settings.copy()
            try:
                del site_snapshot_settings[config.omd_site()]
            except KeyError:
                pass

            snapshot_manager = SnapshotManager.factory(work_dir, site_snapshot_settings)
            snapshot_manager.generate_snapshots()
            logger.debug("Config sync snapshot creation took %.4f", time.time() - start)

            logger.debug("Waiting for backup snapshot creation to complete")
            backup_snapshot_proc.join()

        logger.debug("Finished all snapshots")

    def _get_site_snapshot_settings(self, sites: List[SiteId]) -> Dict[SiteId, SnapshotSettings]:
        snapshot_settings = {}

        for site_id in sites:
            self._check_snapshot_creation_permissions(site_id)

            site_config = config.sites[site_id]
            work_dir = cmk.utils.paths.site_config_dir / site_id

            site_status = self._get_site_status(site_id, site_config)[0]
            is_pre_17_remote_site = _is_pre_17_remote_site(site_status)

            snapshot_components = _get_replication_components(str(work_dir), site_config,
                                                              is_pre_17_remote_site)

            # Generate a quick reference_by_name for each component
            component_names = {c[1] for c in snapshot_components}

            snapshot_settings[site_id] = SnapshotSettings(
                snapshot_path=self._site_snapshot_file(site_id),
                work_dir=str(work_dir),
                snapshot_components=snapshot_components,
                component_names=component_names,
                site_config=site_config,
                create_pre_17_snapshot=is_pre_17_remote_site,
            )

        return snapshot_settings

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

    def _start_activation(self) -> None:
        self._log_activation()
        assert self._activation_id is not None
        job = ActivateChangesSchedulerBackgroundJob(self._activation_id,
                                                    self._site_snapshot_settings,
                                                    self._prevent_activate)
        job.start()

    def _log_activation(self):
        log_msg = _("Starting activation (Sites: %s)") % ",".join(self._sites)
        log_audit(None, "activate-changes", log_msg)

        if self._comment:
            log_audit(None, "activate-changes", "%s: %s" % (_("Comment"), self._comment))

    def get_state(self) -> ActivationState:
        return {
            "sites": {
                site_id: self.get_site_state(site_id)  #
                for site_id in self._sites
            }
        }

    def get_site_state(self, site_id):
        return store.load_object_from_file(self.site_state_path(site_id), {})

    def site_state_path(self, site_id):
        if self._activation_id is None:
            raise Exception("activation ID is not set")
        return os.path.join(self.activation_tmp_base_dir, self._activation_id,
                            self.site_filename(site_id))

    @classmethod
    def site_filename(cls, site_id):
        return "site_%s.mk" % site_id


class SnapshotManager:
    @staticmethod
    def factory(work_dir: str, site_snapshot_settings: Dict[SiteId,
                                                            SnapshotSettings]) -> 'SnapshotManager':
        if cmk_version.is_managed_edition():
            import cmk.gui.cme.managed_snapshots as managed_snapshots  # pylint: disable=no-name-in-module
            return SnapshotManager(
                work_dir,
                site_snapshot_settings,
                managed_snapshots.CMESnapshotDataCollector(site_snapshot_settings),
                reuse_identical_snapshots=False,
                generate_in_suprocess=True,
            )

        return SnapshotManager(
            work_dir,
            site_snapshot_settings,
            CRESnapshotDataCollector(site_snapshot_settings),
            reuse_identical_snapshots=True,
            generate_in_suprocess=False,
        )

    def __init__(self, activation_work_dir: str, site_snapshot_settings: Dict[SiteId,
                                                                              SnapshotSettings],
                 data_collector: 'ABCSnapshotDataCollector', reuse_identical_snapshots: bool,
                 generate_in_suprocess: bool) -> None:
        super(SnapshotManager, self).__init__()
        self._activation_work_dir = activation_work_dir
        self._site_snapshot_settings = site_snapshot_settings
        self._data_collector = data_collector
        self._reuse_identical_snapshots = reuse_identical_snapshots
        self._generate_in_subproces = generate_in_suprocess

        # Stores site and folder specific information to speed-up the snapshot generation
        self._logger = logger.getChild(self.__class__.__name__)

    def _create_site_sync_snapshot(self, site_id: SiteId, snapshot_settings: SnapshotSettings,
                                   snapshot_creator: SnapshotCreator,
                                   data_collector: 'ABCSnapshotDataCollector') -> None:
        generic_site_components, custom_site_components = data_collector.get_site_components(
            snapshot_settings)

        # The CME produces individual snapshots in parallel subprocesses, the CEE mainly equal
        # snapshots for all sites (with some minor differences, like site specific global settings).
        # It creates a single snapshot and clones the result multiple times. Parallel creation of
        # the snapshots would not work for the CEE.
        if self._generate_in_subproces:
            generate_function = snapshot_creator.generate_snapshot_in_subprocess
        else:
            generate_function = snapshot_creator.generate_snapshot

        generate_function(snapshot_work_dir=snapshot_settings.work_dir,
                          target_filepath=snapshot_settings.snapshot_path,
                          generic_components=generic_site_components,
                          custom_components=custom_site_components,
                          reuse_identical_snapshots=self._reuse_identical_snapshots)

    def generate_snapshots(self) -> None:
        if not self._site_snapshot_settings:
            # Nothing to do
            return

        # 1. Collect files to "var/check_mk/site_configs" directory
        self._data_collector.prepare_snapshot_files()

        # 2. Create snapshot for synchronization (Only for pre 1.7 sites)
        generic_components = self._data_collector.get_generic_components()
        with SnapshotCreator(self._activation_work_dir, generic_components) as snapshot_creator:
            for site_id, snapshot_settings in sorted(self._site_snapshot_settings.items(),
                                                     key=lambda x: x[0]):
                if snapshot_settings.create_pre_17_snapshot:
                    self._create_site_sync_snapshot(site_id, snapshot_settings, snapshot_creator,
                                                    self._data_collector)


class ABCSnapshotDataCollector(metaclass=abc.ABCMeta):
    """Prepares files to be synchronized to the remote sites"""
    def __init__(self, site_snapshot_settings: Dict[SiteId, SnapshotSettings]) -> None:
        super(ABCSnapshotDataCollector, self).__init__()
        self._site_snapshot_settings = site_snapshot_settings
        self._logger = logger.getChild(self.__class__.__name__)

    @abc.abstractmethod
    def prepare_snapshot_files(self) -> None:
        """Site independent preparation of files to be used for the sync snapshots
        This will be called once before iterating over all sites.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_generic_components(self) -> List[ReplicationPath]:
        """Return the site independent snapshot components
        These will be collected by the SnapshotManager once when entering the context manager
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def get_site_components(
            self, snapshot_settings: SnapshotSettings
    ) -> Tuple[List[ReplicationPath], List[ReplicationPath]]:
        """Split the snapshot components into generic and site specific components

        The generic components have the advantage that they only need to be created once for all
        sites and can be shared between the sites to optimize processing."""
        raise NotImplementedError()


class CRESnapshotDataCollector(ABCSnapshotDataCollector):
    def prepare_snapshot_files(self):
        """Collect the files to be synchronized for all sites

        This is done by copying the things declared by the generic components together to a single
        site_config for one site. This will result in a directory containing only hard links to
        the original files.

        This directory is then cloned recursively for all sites, again with the result of having
        a single directory per site containing a lot of hard links to the original files.

        As last step the site individual files will be added.
        """
        # Choose one site to create the first site config for
        site_ids = list(self._site_snapshot_settings.keys())
        first_site = site_ids.pop(0)

        # Create first directory and clone it once for each destination site
        self._prepare_site_config_directory(first_site)
        self._clone_site_config_directories(first_site, site_ids)

        for site_id, snapshot_settings in sorted(self._site_snapshot_settings.items(),
                                                 key=lambda x: x[0]):

            site_globals = get_site_globals(site_id, snapshot_settings.site_config)

            # Generate site specific global settings file
            if snapshot_settings.create_pre_17_snapshot:
                create_site_globals_file(site_id, snapshot_settings.work_dir, site_globals)
            else:
                save_site_global_settings(site_globals, custom_site_path=snapshot_settings.work_dir)

            if not self._site_snapshot_settings[site_id].create_pre_17_snapshot:
                create_distributed_wato_files(Path(snapshot_settings.work_dir),
                                              site_id,
                                              is_remote=True)

    def _prepare_site_config_directory(self, site_id: SiteId) -> None:
        """
        Gather files to be synchronized to remote sites from etc hierarchy

        - Iterate all files declared by snapshot components
        - Synchronize site hierarchy with site_config directory
          - Remove files that do not exist anymore
          - Add hard links
        """
        self._logger.debug("Processing first site %s", site_id)
        snapshot_settings = self._site_snapshot_settings[site_id]

        # Currently we don't have an incremental sync on disk. The performance of some mkdir/link
        # calls should be good enough
        if os.path.exists(snapshot_settings.work_dir):
            shutil.rmtree(snapshot_settings.work_dir)

        for component in snapshot_settings.snapshot_components:
            if component.ident == "sitespecific":
                continue  # Will be created for each site individually later

            source_path = Path(cmk.utils.paths.omd_root).joinpath(component.site_path)
            target_path = Path(snapshot_settings.work_dir).joinpath(component.site_path)

            store.makedirs(target_path.parent)

            if not source_path.exists():
                # Not existing files things can simply be skipped, not existing files could also be
                # skipped, but we create them here to be 1:1 compatible with the pre 1.7 sync.
                if component.ty == "dir":
                    store.makedirs(target_path)

                continue

            # Recursively hard link files (rsync --link-dest or cp -al)
            # With Python 3 we could use "shutil.copytree(src, dst, copy_function=os.link)", but
            # please have a look at the performance before switching over...
            #shutil.copytree(source_path, str(target_path.parent) + "/", copy_function=os.link)
            p = subprocess.Popen(
                ["cp", "-al", str(source_path),
                 str(target_path.parent) + "/"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=open(os.devnull),
                shell=False,
                close_fds=True)
            stdout = p.communicate()[0]
            if p.returncode != 0:
                self._logger.error("Failed to clone files from %s to %s: %s", source_path,
                                   str(target_path), stdout)
                raise MKGeneralException("Failed to create site config directory")

        self._logger.debug("Finished site")

    def _clone_site_config_directories(self, origin_site_id: SiteId,
                                       site_ids: List[SiteId]) -> None:
        origin_site_work_dir = self._site_snapshot_settings[origin_site_id].work_dir

        for site_id in site_ids:
            self._logger.debug("Processing site %s", site_id)
            snapshot_settings = self._site_snapshot_settings[site_id]

            if os.path.exists(snapshot_settings.work_dir):
                shutil.rmtree(snapshot_settings.work_dir)

            p = subprocess.Popen(["cp", "-al", origin_site_work_dir, snapshot_settings.work_dir],
                                 shell=False,
                                 close_fds=True)
            p.wait()
            assert p.returncode == 0
            self._logger.debug("Finished site")

    def get_generic_components(self) -> List[ReplicationPath]:
        return get_replication_paths()

    def get_site_components(
            self, snapshot_settings: SnapshotSettings
    ) -> Tuple[List[ReplicationPath], List[ReplicationPath]]:
        generic_site_components = []
        custom_site_components = []

        for component in snapshot_settings.snapshot_components:
            if component.ident == "sitespecific":
                # Only the site specific global files are individually handled in the non CME snapshot
                custom_site_components.append(component)
            else:
                generic_site_components.append(component)

        return generic_site_components, custom_site_components


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

    def _do_housekeeping(self) -> None:
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


def execute_activation_cleanup_background_job() -> None:
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log. """
    job = ActivationCleanupBackgroundJob()
    if job.is_active():
        logger.debug("Another activation cleanup job is already running: Skipping this time")
        return

    job.set_function(job.do_execute)
    job.start()


@gui_background_job.job_registry.register
class ActivateChangesSchedulerBackgroundJob(WatoBackgroundJob):
    job_prefix = "activate-changes-scheduler"
    housekeeping_max_age_sec = 86400 * 30
    housekeeping_max_count = 10

    @classmethod
    def gui_title(cls):
        return _("Activate Changes Scheduler")

    def __init__(self, activation_id: str, site_snapshot_settings: Dict[SiteId, SnapshotSettings],
                 prevent_activate: bool) -> None:
        super(ActivateChangesSchedulerBackgroundJob,
              self).__init__("%s-%s" % (self.job_prefix, activation_id),
                             deletable=False,
                             stoppable=False)
        self._activation_id = activation_id
        self._site_snapshot_settings = site_snapshot_settings
        self._prevent_activate = prevent_activate
        self.set_function(self._schedule_sites)

    def _schedule_sites(self, job_interface):
        # Prepare queued jobs

        job_interface.send_progress_update(_("Activate Changes Scheduler started"),
                                           with_timestamp=True)
        queued_jobs = self._get_queued_jobs()

        job_interface.send_progress_update(_("Going to update %d sites") % len(queued_jobs),
                                           with_timestamp=True)

        running_jobs: List[ActivateChangesSite] = []
        max_jobs = self._get_maximum_concurrent_jobs()
        while queued_jobs or len(running_jobs) > 0:
            # Housekeeping, remove finished jobs
            for job in running_jobs[:]:
                if job.is_alive():
                    continue
                job_interface.send_progress_update(_("Finished site update: %s") % job.site_id,
                                                   with_timestamp=True)
                job.join()
                running_jobs.remove(job)

            time.sleep(0.1)

            # Continue if at max concurrent jobs
            if len(running_jobs) == max_jobs:
                continue

            # Start new jobs
            while queued_jobs:
                job = queued_jobs.pop(0)
                job_interface.send_progress_update(_("Starting site update: %s") % job.site_id,
                                                   with_timestamp=True)
                job.start()
                running_jobs.append(job)
                if len(running_jobs) == max_jobs:
                    break

        job_interface.send_result_message(_("Activate changes finished"))

    def _get_maximum_concurrent_jobs(self):
        if config.wato_activate_changes_concurrency == "auto":
            processes = self._max_processes_based_on_ram()
        else:  # (maximum, 23)
            processes = config.wato_activate_changes_concurrency[1]
        return max(5, processes)

    def _max_processes_based_on_ram(self):
        # This process will be forked mulitple times
        # Determine its current rss usage and compute a reasonable maximum value
        try:
            # We are going to fork this process
            process = psutil.Process(os.getpid())
            size = process.memory_info().rss
            return (0.9 * psutil.virtual_memory().available) // size
        except RequestTimeout:
            raise
        except Exception:
            return 1

    def _get_queued_jobs(self) -> 'List[ActivateChangesSite]':
        queued_jobs = []
        for site_id, snapshot_settings in sorted(self._site_snapshot_settings.items(),
                                                 key=lambda e: e[0]):
            site_job = ActivateChangesSite(site_id, snapshot_settings, self._activation_id,
                                           self._prevent_activate)
            site_job.load()
            if site_job.lock_activation():
                queued_jobs.append(site_job)
        return queued_jobs


class ActivateChangesSite(multiprocessing.Process, ActivateChanges):
    """Executes and monitors a single activation for one site"""
    def __init__(self,
                 site_id: SiteId,
                 snapshot_settings: SnapshotSettings,
                 activation_id: str,
                 prevent_activate: bool = False) -> None:
        super(ActivateChangesSite, self).__init__()
        self._site_id = site_id
        self._site_changes: List = []
        self._activation_id = activation_id
        self._snapshot_settings = snapshot_settings
        self.daemon = True
        self._prevent_activate = prevent_activate

        self._time_started: Optional[float] = None
        self._time_updated: Optional[float] = None
        self._time_ended: Optional[float] = None
        self._phase = None
        self._state = None
        self._status_text = None
        self._status_details: Optional[str] = None
        self._pid: Optional[int] = None
        self._expected_duration = 10.0
        self._logger = logger.getChild("site[%s]" % self._site_id)

        self._set_result(PHASE_INITIALIZED, _("Initialized"))

    @property
    def site_id(self):
        return self._site_id

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

        self._detach_from_parent()

        # Cleanup existing livestatus connections (may be opened later when needed)
        if g:
            sites_disconnect()

        self._close_apache_fds()

        # Reinitialize logging targets
        log.init_logging()  # NOTE: We run in a subprocess!

        try:
            self._do_run()
        except Exception:
            self._logger.exception("error running activate changes")

    def _detach_from_parent(self):
        # Detach from parent (apache) -> Remain running when apache is restarted
        os.setsid()

    def _close_apache_fds(self):
        # Cleanup resources of the apache
        for x in range(3, 256):
            try:
                os.close(x)
            except OSError as e:
                if e.errno == errno.EBADF:
                    pass
                else:
                    raise

    def _do_run(self):
        try:
            self._time_started = time.time()

            # Update PID
            # Initially the SiteScheduler set its own PID into the sites state file
            # The PID itself is used to detect whether the sites activation process is still running
            self._mark_running()

            log_audit(None, "activate-changes", _("Started activation of site %s") % self._site_id)

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
            self._logger.exception("error activating changes")
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

    def _set_done_result(self, configuration_warnings: ConfigWarnings) -> None:
        if any(configuration_warnings.values()):
            details = self._render_warnings(configuration_warnings)
            self._set_result(PHASE_DONE, _("Activated"), details, state=STATE_WARNING)
        else:
            self._set_result(PHASE_DONE, _("Success"), state=STATE_SUCCESS)

    def _render_warnings(self, configuration_warnings: ConfigWarnings) -> str:
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

    def lock_activation(self):
        # This locks the site specific replication status file
        repl_status = _load_site_replication_status(self._site_id, lock=True)
        got_lock = False
        try:
            if self._is_currently_activating(repl_status):
                self._set_result(
                    PHASE_DONE,
                    _("Locked"),
                    status_details=
                    _("The site is currently locked by another activation process. Please try again later"
                     ),
                    state=STATE_WARNING)
                return False

            got_lock = True
            self._mark_queued()
            return True
        finally:
            # This call unlocks the replication status file after setting "current_activation"
            # which will prevent other users from starting an activation for this site.
            # If the site was already locked, simply release the lock without further changes
            if got_lock:
                _update_replication_status(self._site_id,
                                           {"current_activation": self._activation_id})
            else:
                store.release_lock(_site_replication_status_path(self._site_id))

    def _is_currently_activating(self, site_rep_status):
        current_activation_id = site_rep_status.get("current_activation")
        if not current_activation_id:
            return False

        # Is this activation still in progress?
        manager = ActivateChangesManager()
        manager.load()

        try:
            manager.load_activation(current_activation_id)
        except MKUserError:
            return False  # Not existant anymore!

        if manager.is_running():
            return True

        return False

    def _mark_queued(self):
        # Is set by site scheduler
        self._pid = os.getpid()
        self._set_result(PHASE_QUEUED, _("Queued"))

    def _mark_running(self):
        # Is set by active site process
        self._pid = os.getpid()
        self._set_result(PHASE_STARTED, _("Started"))

    def _unlock_activation(self):
        _update_replication_status(self._site_id, {
            "last_activation": self._activation_id,
            "current_activation": None,
        })

    def _synchronize_site(self):
        """This is done on the central site to initiate the sync process"""
        self._set_sync_state()

        start = time.time()

        try:
            if self._snapshot_settings.create_pre_17_snapshot:
                self._synchronize_pre_17_site()
            else:
                self._synchronize_17_or_newer_site()
        finally:
            duration = time.time() - start
            self.update_activation_time(self._site_id, ACTIVATION_TIME_SYNC, duration)

    def _synchronize_17_or_newer_site(self) -> None:
        """Realizes the incremental config sync from the central to the remote site

        1. Gather the replication paths handled by the central site.

           We want the state of these files from the remote site to be able to compare the state of
           the central sites site_config directory with it. Warning: In mixed version setups it
           would not be enough to use the replication paths known by the remote site. We really need
           the central sites definitions.

        2. Send them over to the remote site and request the current state of the mentioned files
        3. Compare the response with the site_config directory of the site
        4. Collect needed files and send them over to the remote site (+ remote config hash)
        5. Raise when something failed on the remote site while applying the sent files
        """
        self._set_sync_state(_("Fetching sync state"))
        self._logger.debug("Starting config sync with >1.7 site")
        replication_paths = self._snapshot_settings.snapshot_components
        remote_file_infos, remote_config_generation = self._get_config_sync_state(replication_paths)
        self._logger.debug("Received %d file infos from remote", len(remote_file_infos))

        # In case we experience performance issues here, we could postpone the hashing of the
        # central files to only be done ad-hoc in _get_file_names_to_sync when the other attributes
        # are not enough to detect a differing file.
        site_config_dir = Path(self._snapshot_settings.work_dir)
        central_file_infos = _get_config_sync_file_infos(replication_paths, site_config_dir)
        self._logger.debug("Got %d file infos from %s", len(remote_file_infos), site_config_dir)

        self._set_sync_state(_("Computing differences"))
        to_sync_new, to_sync_changed, to_delete = _get_file_names_to_sync(
            self._logger, central_file_infos, remote_file_infos)

        self._logger.debug("New files to be synchronized: %r", to_sync_new)
        self._logger.debug("Changed files to be synchronized: %r", to_sync_changed)
        self._logger.debug("Obsolete files to be deleted: %r", to_delete)

        if not to_sync_new and not to_sync_changed and not to_delete:
            self._logger.debug("Finished config sync (Nothing to be done)")
            return

        self._set_sync_state(
            _("Transfering: %d new, %d changed and %d vanished files") %
            (len(to_sync_new), len(to_sync_changed), len(to_delete)))
        self._synchronize_files(to_sync_new + to_sync_changed, to_delete, remote_config_generation,
                                site_config_dir)
        self._logger.debug("Finished config sync")

    def _set_sync_state(self, status_details: Optional[str] = None) -> None:
        self._set_result(PHASE_SYNC, _("Synchronizing"), status_details=status_details)

    def _get_config_sync_state(
            self, replication_paths: List[ReplicationPath]
    ) -> 'Tuple[Dict[str, ConfigSyncFileInfo], int]':
        """Get the config file states from the remote sites

        Calls the automation call "get-config-sync-state" on the remote site,
        which is handled by AutomationGetConfigSyncState."""
        site = config.site(self._site_id)
        response = cmk.gui.watolib.automations.do_remote_automation(
            site,
            "get-config-sync-state",
            [("replication_paths", repr([tuple(r) for r in replication_paths]))],
        )

        return {k: ConfigSyncFileInfo(*v) for k, v in response[0].items()}, response[1]

    def _synchronize_files(self, files_to_sync: List[str], files_to_delete: List[str],
                           remote_config_generation: int, site_config_dir: Path) -> None:
        """Pack the files in a simple tar archive and send it to the remote site

        We build a simple tar archive containing all files to be synchronized.  The list of file to
        be deleted and the current config generation is handed over using dedicated HTTP parameters.
        """

        sync_archive = _get_sync_archive(files_to_sync, site_config_dir)

        site = config.site(self._site_id)
        response = cmk.gui.watolib.automations.do_remote_automation(
            site,
            "receive-config-sync",
            [
                ("site_id", self._site_id),
                ("sync_archive", sync_archive),
                ("to_delete", repr(files_to_delete)),
                ("config_generation", "%d" % remote_config_generation),
            ],
            files={
                "sync_archive": io.BytesIO(sync_archive),
            },
        )

        if response is not True:
            raise MKGeneralException(_("Failed to synchronize with site: %s") % response)

    # TODO: Compatibility for 1.6 -> 1.7 migration. Can be removed with 1.8.
    def _synchronize_pre_17_site(self) -> None:
        """This is done on the central site to initiate the sync process"""
        self._logger.debug("Starting config sync with pre 1.7 site")
        result = self._push_pre_17_snapshot_to_site()
        self._logger.debug("Finished config sync")

        # Pre 1.2.7i3 and sites return True on success and a string on error.
        # 1.2.7i3 and later return a list of warning messages on success.
        # [] means OK and no warnings. The error handling is unchanged.
        # Since 1.4.0i3 the old API (True -> success, <unicode>/<str> -> error)
        if isinstance(result, list):
            result = True

        if result is not True:
            raise MKGeneralException(_("Failed to synchronize with site: %s") % result)

    def _push_pre_17_snapshot_to_site(self) -> bool:
        """Calls a remote automation call push-snapshot which is handled by AutomationPushSnapshot()"""
        site = config.site(self._site_id)

        url = append_query_string(
            site["multisiteurl"] + "automation.py",
            [
                ("command", "push-snapshot"),
                ("secret", site["secret"]),
                ("siteid", site["id"]),
                ("debug", config.debug and "1" or ""),
            ],
        )

        response_text = self._upload_file(url, site.get('insecure', False))

        try:
            return ast.literal_eval(response_text)
        except SyntaxError:
            raise cmk.gui.watolib.automations.MKAutomationException(
                _("Garbled automation response: <pre>%s</pre>") %
                (escaping.escape_attribute(response_text)))

    def _upload_file(self, url, insecure):
        with open(self._snapshot_settings.snapshot_path, "rb") as f:
            return cmk.gui.watolib.automations.get_url(url, insecure, files={"snapshot": f})

    def _do_activate(self) -> ConfigWarnings:
        self._set_result(PHASE_ACTIVATE, _("Activating"))

        start = time.time()

        configuration_warnings = self._call_activate_changes_automation()

        duration = time.time() - start
        self.update_activation_time(self._site_id, ACTIVATION_TIME_RESTART, duration)
        return configuration_warnings

    def _call_activate_changes_automation(self) -> ConfigWarnings:
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
        # As long as the site is lying in queue, there is no time started
        if phase == PHASE_QUEUED:
            self._status_details = _("Queued for update")
        else:
            if self._time_started is None:
                raise Exception("start time not set")
            self._status_details = _("Started at: %s.") % render.time_of_day(self._time_started)

        if phase == PHASE_DONE:
            self._status_details += _(" Finished at: %s.") % render.time_of_day(self._time_ended)
        elif phase != PHASE_QUEUED:
            assert isinstance(self._time_started, (int, float))
            estimated_time_left = self._expected_duration - (time.time() - self._time_started)
            if estimated_time_left < 0:
                self._status_details += " " + _("Takes %.1f seconds longer than expected") % \
                                                                        abs(estimated_time_left)
            else:
                self._status_details += " " + _("Approximately finishes in %.1f seconds") % \
                                                                        estimated_time_left

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


def execute_activate_changes(domains: List[ConfigDomainName]) -> ConfigWarnings:
    activation_domains = set(domains).union(ABCConfigDomain.get_always_activate_domain_idents())

    results: ConfigWarnings = {}
    for domain in sorted(activation_domains):
        domain_class = ABCConfigDomain.get_class(domain)
        warnings = domain_class().activate()
        results[domain] = warnings or []

    return results


def confirm_all_local_changes() -> None:
    ActivateChanges().confirm_site_changes(config.omd_site())


def get_pending_changes_info() -> Optional[str]:
    changes = ActivateChanges()
    return changes.get_changes_estimate()


def get_number_of_pending_changes() -> int:
    changes = ActivateChanges()
    changes.load()
    return len(changes.grouped_changes())


def apply_pre_17_sync_snapshot(site_id: SiteId, tar_content: bytes, base_dir: Path,
                               components: List[ReplicationPath]) -> bool:
    """Apply the snapshot received from a central site to the local site"""
    extract_from_buffer(tar_content, base_dir, components)

    _save_pre_17_site_globals_on_slave_site(tar_content)

    # Create rule making this site only monitor our hosts
    create_distributed_wato_files(Path(cmk.utils.paths.omd_root), site_id, is_remote=True)

    _execute_post_config_sync_actions(site_id)
    return True


def _execute_post_config_sync_actions(site_id):
    try:
        # pending changes are lost
        confirm_all_local_changes()

        hooks.call("snapshot-pushed")
    except Exception:
        raise MKGeneralException(
            _("Failed to deploy configuration: \"%s\". "
              "Please note that the site configuration has been synchronized "
              "partially.") % traceback.format_exc())

    cmk.gui.watolib.changes.log_audit(None, "replication",
                                      _("Synchronized with master (my site id is %s.)") % site_id)


def verify_remote_site_config(site_id: SiteId) -> None:
    our_id = config.omd_site()

    if not config.is_single_local_site():
        raise MKGeneralException(
            _("Configuration error. You treat us as "
              "a <b>remote</b>, but we have an own distributed WATO configuration!"))

    if our_id is not None and our_id != site_id:
        raise MKGeneralException(
            _("Site ID mismatch. Our ID is '%s', but you are saying we are '%s'.") %
            (our_id, site_id))

    # Make sure there are no local changes we would lose!
    changes = cmk.gui.watolib.activate_changes.ActivateChanges()
    changes.load()
    pending = list(reversed(changes.grouped_changes()))
    if pending:
        message = _("There are %d pending changes that would get lost. The most recent are: "
                   ) % len(pending)
        message += ", ".join(change["text"] for _change_id, change in pending[:10])

        raise MKGeneralException(message)


def _save_pre_17_site_globals_on_slave_site(tarcontent: bytes) -> None:
    tmp_dir = cmk.utils.paths.tmp_dir + "/sitespecific-%s" % id(object)
    try:
        if not os.path.exists(tmp_dir):
            store.mkdir(tmp_dir)

        extract_from_buffer(
            tarcontent, Path(tmp_dir),
            [ReplicationPath("dir", "sitespecific", "site_globals/sitespecific.mk", [])])

        site_globals = store.load_object_from_file(tmp_dir + "site_globals/sitespecific.mk",
                                                   default={})
        save_site_global_settings(site_globals)
    finally:
        shutil.rmtree(tmp_dir)


def create_distributed_wato_files(base_dir: Path, site_id: SiteId, is_remote: bool) -> None:
    _create_distributed_wato_file_for_base(base_dir, site_id, is_remote)
    _create_distributed_wato_file_for_dcd(base_dir)


def _create_distributed_wato_file_for_base(base_dir: Path, site_id: SiteId,
                                           is_remote: bool) -> None:
    output = wato_fileheader()
    output += ("# This file has been created by the master site\n"
               "# push the configuration to us. It makes sure that\n"
               "# we only monitor hosts that are assigned to our site.\n\n")
    output += "distributed_wato_site = '%s'\n" % site_id
    output += "is_wato_slave_site = %r\n" % is_remote

    store.save_file(base_dir.joinpath("etc/check_mk/conf.d/distributed_wato.mk"), output)


def _create_distributed_wato_file_for_dcd(base_dir: Path) -> None:
    if cmk_version.is_raw_edition():
        return

    with base_dir.joinpath("etc/check_mk/dcd.d/wato/distributed.mk").open(mode="w",
                                                                          encoding="utf-8") as f:
        f.write(ensure_str(wato_fileheader()))
        f.write(u"dcd_is_wato_remote_site = True\n")


def create_site_globals_file(site_id: SiteId, tmp_dir: str,
                             site_globals: SiteConfiguration) -> None:
    site_globals_dir = os.path.join(tmp_dir, "site_globals")
    store.makedirs(site_globals_dir)
    store.save_object_to_file(os.path.join(site_globals_dir, "sitespecific.mk"), site_globals)


def get_site_globals(site_id: SiteId, site_config: SiteConfiguration) -> Dict:
    site_globals = site_config.get("globals", {}).copy()
    site_globals.update({
        "wato_enabled": not site_config.get("disable_wato", True),
        "userdb_automatic_sync": site_config.get("user_sync", user_sync_default_config(site_id)),
        "user_login": site_config.get("user_login", False),
    })
    return site_globals


def _is_pre_17_remote_site(site_status: SiteStatus) -> bool:
    """Decide which snapshot format is pushed to the given site

    The sync snapshot format was changed between 1.6 and 1.7. To support migrations with a
    new central site and an old remote site, we detect that case here and create the 1.6
    snapshots for the old sites.
    """
    version = site_status.get("livestatus_version")
    if not version:
        return False

    return parse_check_mk_version(version) < parse_check_mk_version("1.7.0i1")


def _get_replication_components(work_dir: str, site_config: SiteConfiguration,
                                is_pre_17_remote_site: bool) -> List[ReplicationPath]:
    """Gives a list of ReplicationPath instances.

    These represent the folders which need to be sent to remote sites. Whether a specific subset
    of paths need to be sent is being determined by the site-specific `site_config`.

    Note:
        "Replication path" or "replication component" or "snapshot component" are the same concept.

    Args:
        work_dir:
            Something no longer used apparently.

        site_config:
            The site configuration. Specifically the following keys on it are used:

                 - `replicate_ec`:
                 - `replicate_mkps`

        is_pre_17_remote_site:
            This is true if the site in question (as supplied in `site_config`) is of a version
            1.6.x or less.

    Returns:
        A list of ReplicationPath instances, specifying which paths shall be packaged for this
        particular site.

    """
    paths = get_replication_paths()[:]

    # Remove Event Console settings, if this site does not want it (might
    # be removed in some future day)
    if not site_config.get("replicate_ec"):
        paths = [e for e in paths if e.ident not in ["mkeventd", "mkeventd_mkp"]]

    # Remove extensions if site does not want them
    if not site_config.get("replicate_mkps"):
        paths = [e for e in paths if e.ident not in ["local", "mkps"]]

    # Add site-specific global settings
    if is_pre_17_remote_site:
        # When synchronizing with pre 1.7 sites, the sitespecific.mk from the config domain
        # directories must not be used. Instead of this, they are transfered using the
        # site_globals/sitespecific.mk (see below) and written on the remote site.
        paths = _add_pre_17_sitespecific_excludes(paths)

        paths.append(
            ReplicationPath(
                ty="file",
                ident="sitespecific",
                site_path="site_globals/sitespecific.mk",
                excludes=[],
            ))

    # Add distributed_wato.mk
    if not is_pre_17_remote_site:
        paths.append(
            ReplicationPath(
                ty="file",
                ident="distributed_wato",
                site_path="etc/check_mk/conf.d/distributed_wato.mk",
                excludes=[],
            ))

    return paths


def _add_pre_17_sitespecific_excludes(paths: List[ReplicationPath]) -> List[ReplicationPath]:
    add_domains = {"check_mk", "multisite", "liveproxyd", "mkeventd", "dcd", "mknotify"}
    new_paths = []
    for p in paths:
        if p.ident in add_domains:
            excludes = p.excludes[:] + ["sitespecific.mk"]
            if p.ident == "dcd":
                excludes.append("distributed.mk")

            p = ReplicationPath(
                ty=p.ty,
                ident=p.ident,
                site_path=p.site_path,
                excludes=excludes,
            )

        new_paths.append(p)
    return new_paths


def _get_file_names_to_sync(
        site_logger: Logger, central_file_infos: 'Dict[str, ConfigSyncFileInfo]',
        remote_file_infos: 'Dict[str, ConfigSyncFileInfo]'
) -> Tuple[List[str], List[str], List[str]]:
    """Compare the response with the site_config directory of the site

    Comparing both file lists and returning all files for synchronization that

    a) Do not exist on the remote site
    b) Differ from the central site
    c) Exist on the remote site but not on the central site as
    """

    # New files
    central_files = set(central_file_infos.keys())
    remote_files = set(remote_file_infos.keys())
    to_sync_new = list(central_files - remote_files)

    # Add differing files
    to_sync_changed = []
    for existing in central_files.intersection(remote_files):
        if central_file_infos[existing] != remote_file_infos[existing]:
            site_logger.debug("Sync needed %s: %r <> %r", existing, central_file_infos[existing],
                              remote_file_infos[existing])
            to_sync_changed.append(existing)

    # Files to be deleted
    to_delete = list(remote_files - central_files)

    return to_sync_new, to_sync_changed, to_delete


def _get_sync_archive(to_sync: List[str], base_dir: Path) -> bytes:
    # Use native tar instead of python tarfile for performance reasons
    p = subprocess.Popen(
        [
            "tar", "-c", "-C",
            str(base_dir), "-f", "-", "--null", "-T", "-", "--preserve-permissions"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        shell=False,
    )

    # Since we don't stream the archive to the remote site (we could probably do this) it should be
    # no problem to buffer it in memory for the moment
    archive, stderr = p.communicate(b"\0".join(ensure_binary(f) for f in to_sync))

    if p.returncode != 0:
        raise MKGeneralException(
            _("Failed to create sync archive [%d]: %s") % (p.returncode, ensure_str(stderr)))

    return archive


def _unpack_sync_archive(sync_archive: bytes, base_dir: Path) -> None:
    p = subprocess.Popen(
        [
            "tar", "-x", "-C",
            str(base_dir), "-f", "-", "-U", "--recursive-unlink", "--preserve-permissions"
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        close_fds=True,
        shell=False,
    )
    assert p.stdin is not None
    assert p.stdout is not None
    assert p.stderr is not None

    stderr = p.communicate(sync_archive)[1]
    if p.returncode != 0:
        raise MKGeneralException(
            _("Failed to create sync archive [%d]: %s") % (p.returncode, ensure_str(stderr)))


ConfigSyncFileInfo = NamedTuple("ConfigSyncFileInfo", [
    ("st_mode", int),
    ("st_size", int),
    ("link_target", Optional[str]),
    ("file_hash", Optional[str]),
])

# Would've used some kind of named tuple here, but the serialization and deserialization is a pain.
# Using some simpler data structure for transport now to reduce the pain.
#GetConfigSyncStateResponse = NamedTuple("GetConfigSyncStateResponse", [
#    ("file_infos", Dict[str, ConfigSyncFileInfo]),
#    ("config_generation", int),
#])
GetConfigSyncStateResponse = Tuple[Dict[str, Tuple[int, int, Optional[str], Optional[str]]], int]


@automation_command_registry.register
class AutomationGetConfigSyncState(AutomationCommand):
    """Called on remote site from a central site to get the current config sync state

    The central site hands over the list of replication paths it will try to synchronize later.  The
    remote site computes the list of replication files and sends it back together with the current
    configuration generation ID. The config generation ID is increased on every WATO modification
    and ensures that nothing is changed between the two config sync steps.
    """
    def command_name(self):
        return "get-config-sync-state"

    def get_request(self) -> List[ReplicationPath]:
        return [
            ReplicationPath(*e)
            for e in ast.literal_eval(_request.get_ascii_input_mandatory("replication_paths"))
        ]

    def execute(self, request: List[ReplicationPath]) -> GetConfigSyncStateResponse:
        with store.lock_checkmk_configuration():
            file_infos = _get_config_sync_file_infos(request,
                                                     base_dir=Path(cmk.utils.paths.omd_root))
            transport_file_infos = {
                k: (v.st_mode, v.st_size, v.link_target, v.file_hash)
                for k, v in file_infos.items()
            }
            return (transport_file_infos, _get_current_config_generation())


def _get_config_sync_file_infos(replication_paths: List[ReplicationPath],
                                base_dir: Path) -> Dict[str, ConfigSyncFileInfo]:
    """Scans the given replication paths for the information needed for the config sync

    It produces a dictionary of sync file infos. One entry is created for each file.  Directories
    are not added to the dictionary.
    """
    infos = {}

    for replication_path in replication_paths:
        path = base_dir.joinpath(replication_path.site_path)

        if not path.exists():
            continue  # Only report back existing things

        if replication_path.ty == "file":
            infos[replication_path.site_path] = _get_config_sync_file_info(path)

        elif replication_path.ty == "dir":
            for entry in path.glob("**/*"):
                if entry.is_dir() and not entry.is_symlink():
                    continue  # Do not add directories at all

                entry_site_path = entry.relative_to(base_dir)
                infos[str(entry_site_path)] = _get_config_sync_file_info(entry)

        else:
            raise NotImplementedError()
    return infos


def _get_config_sync_file_info(file_path: Path) -> ConfigSyncFileInfo:
    stat = file_path.lstat()
    is_symlink = file_path.is_symlink()
    return ConfigSyncFileInfo(
        stat.st_mode,
        stat.st_size,
        os.readlink(str(file_path)) if is_symlink else None,
        _create_config_sync_file_hash(file_path) if not is_symlink else None,
    )


def _create_config_sync_file_hash(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def update_config_generation():
    """Increase the config generation ID

    This ID is used to detect whether something else has been changed in the configuration between
    two points in time. Therefore, all places that change the configuration must call this function
    at least once.
    """
    store.save_object_to_file(_config_generation_path(),
                              _get_current_config_generation(lock=True) + 1)


def _get_current_config_generation(lock: bool = False) -> int:
    return store.load_object_from_file(_config_generation_path(), default=0, lock=lock)


def _config_generation_path():
    return Path(cmk.utils.paths.var_dir) / "wato" / "config-generation.mk"


ReceiveConfigSyncRequest = NamedTuple("ReceiveConfigSyncRequest", [
    ("site_id", SiteId),
    ("sync_archive", bytes),
    ("to_delete", List[str]),
    ("config_generation", int),
])


@automation_command_registry.register
class AutomationReceiveConfigSync(AutomationCommand):
    """Called on remote site from a central site to update the Checkmk configuration

    The central site hands over the a tar archive with the files to be written and a list of
    files to be deleted. The configuration generation is used to validate that no modification has
    been made between the two sync steps (get-config-sync-state and this autmoation).
    """
    def command_name(self):
        return "receive-config-sync"

    def get_request(self) -> ReceiveConfigSyncRequest:
        site_id = SiteId(_request.get_ascii_input_mandatory("site_id"))
        verify_remote_site_config(site_id)

        return ReceiveConfigSyncRequest(
            site_id,
            _request.uploaded_file("sync_archive")[2],
            ast.literal_eval(_request.get_ascii_input_mandatory("to_delete")),
            _request.get_integer_input_mandatory("config_generation"),
        )

    def execute(self, request: ReceiveConfigSyncRequest) -> bool:
        with store.lock_checkmk_configuration():
            if request.config_generation != _get_current_config_generation():
                raise MKGeneralException(
                    _("The configuration was changed during activation. "
                      "Terminating this activation to ensure configuration integrity. "
                      "Please try again."))

            self._update_config_on_remote_site(request.sync_archive, request.to_delete)

            _execute_post_config_sync_actions(request.site_id)
            return True

    def _update_config_on_remote_site(self, sync_archive: bytes, to_delete: List[str]) -> None:
        """Use the given tar archive and list of files to be deleted to update the local files"""
        base_dir = Path(cmk.utils.paths.omd_root)

        for site_path in to_delete:
            site_file = base_dir.joinpath(site_path)
            try:
                site_file.unlink()
            except OSError as e:
                # errno.ENOENT - File already removed. Fine
                # errno.ENOTDIR - dir with files was replaced by e.g. symlink
                if e.errno not in [errno.ENOENT, errno.ENOTDIR]:
                    raise

        _unpack_sync_archive(sync_archive, base_dir)


def activate_changes_start(
    sites: List[SiteId],
    comment: Optional[str] = None,
    force_foreign_changes: bool = False,
) -> ActivationId:
    """Start activation of configuration changes on specific or "dirty" sites.

    A "dirty" site is defined by having pending configuration changes to be activated.

    Args:
        sites:
            A list of site names which to activate.

        comment:
            A comment which shall be associated with this activation.

        force_foreign_changes:
            Will activate changes even if the user who made those changes is not the currently
            logged in user.

    Returns:

    """
    changes = ActivateChanges()
    changes.load()

    if changes.has_foreign_changes():
        if not config.user.may("wato.activateforeign"):
            raise MKAuthException(_("You are not allowed to activate changes of other users."))
        if not force_foreign_changes:
            raise MKAuthException(
                _("There are changes from other users and foreign changes are "
                  "not allowed in this API call."))

    known_sites = config.allsites().keys()
    for site in sites:
        if site not in known_sites:
            raise MKUserError(None, _("Unknown site %s") % escaping.escape_attribute(site))

    manager = ActivateChangesManager()
    manager.load()
    if manager.is_running():
        raise MKUserError(None, _("There is an activation already running."))

    if not manager.has_changes():
        raise MKUserError(None, _("Currently there are no changes to activate."))

    if not sites:
        sites = manager.dirty_and_active_activation_sites()

    return manager.start(sites, comment=comment, activate_foreign=force_foreign_changes)


def activate_changes_wait(activation_id: ActivationId,
                          timeout: Optional[Union[float, int]] = None) -> Optional[ActivationState]:
    """Wait for configuration changes to complete activating.

    Args:
        activation_id:
            The activation_id representing the activation to wait for.

        timeout:
            An optional timeout for the waiting time. If timeout is set to None, it will run
            until finished. A timeout set to 0 will time out immediately.

    Returns:
        The activation-state when finished, if not yet finished it will return None
    """
    manager = ActivateChangesManager()
    manager.load()
    manager.load_activation(activation_id)
    if manager.wait_for_completion(timeout=timeout):
        return manager.get_state()
    return None


def append_query_string(url: str, variables: HTTPVariables) -> str:
    """Append a query string to an URL.

    Non-str values are converted to str, None values are omitted in the result.

    Examples:

        None values are filtered out:

            >>> append_query_string("foo", [('b', 2), ('c', None), ('a', '1'),])
            'foo?a=1&b=2'

        Empty values are kept:

            >>> append_query_string("foo", [('c', ''), ('a', 1), ('b', '2'),])
            'foo?a=1&b=2&c='

    Args:
        url:
            The url to append the query string to.
        variables:
            The query string variables as a list of tuples.

    Returns:
        The url with the query string appended.

    """
    if variables:
        # Encoding would work even with byte-string keys, yet these are
        # excluded via our type signature.
        url += "?" + werkzeug.urls.url_encode(variables, sort=True)

    return url
