#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Managing configuration activation of Checkmk

The major elements here are:

ActivateChangesManager   - Coordinates a single activation of Checkmk config changes for all
                           affected sites.
SnapshotManager          - Coordinates the collection and packing of snapshots
ABCSnapshotDataCollector - Copying or generating files to be put into snapshots
SnapshotCreator          - Packing the snapshots into snapshot archives
"""

from __future__ import annotations

import ast
import enum
import errno
import hashlib
import io
import logging
import multiprocessing
import os
import re
import shutil
import subprocess
import time
import traceback
from collections.abc import (
    Callable,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
)
from dataclasses import asdict, dataclass
from datetime import datetime
from itertools import filterfalse
from multiprocessing.pool import AsyncResult, ThreadPool
from pathlib import Path
from typing import Any, Literal, NamedTuple

from setproctitle import setthreadtitle
from typing_extensions import TypedDict

from livestatus import SiteConfiguration, SiteId

from cmk.utils import (
    agent_registration,
    paths,
    render,
    setup_search_index,
    store,
    version,
)
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.licensing.export import LicenseUsageExtensions
from cmk.utils.licensing.registry import get_licensing_user_effect, is_free
from cmk.utils.licensing.usage import save_extensions
from cmk.utils.site import omd_site
from cmk.utils.user import UserId
from cmk.utils.visuals import invalidate_visuals_cache

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

import cmk.gui.hooks as hooks
import cmk.gui.utils
import cmk.gui.utils.escaping as escaping
import cmk.gui.watolib.automations
import cmk.gui.watolib.config_domain_name as config_domain_name
import cmk.gui.watolib.git
import cmk.gui.watolib.sidebar_reload
import cmk.gui.watolib.utils
from cmk.gui import userdb
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundJobAlreadyRunning,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobStatusSpec,
)
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKInternalError, MKUserError
from cmk.gui.http import request as _request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.nodevis.utils import topology_dir
from cmk.gui.site_config import (
    enabled_sites,
    get_site_config,
    is_single_local_site,
    site_is_local,
)
from cmk.gui.sites import disconnect as sites_disconnect
from cmk.gui.sites import SiteStatus
from cmk.gui.sites import states as sites_states
from cmk.gui.type_defs import Users
from cmk.gui.user_sites import activation_sites
from cmk.gui.userdb import load_users, user_sync_default_config
from cmk.gui.userdb.htpasswd import HtpasswdUserConnector
from cmk.gui.userdb.store import load_users_uncached, save_users
from cmk.gui.utils.ntop import is_ntop_configured
from cmk.gui.utils.request_context import copy_request_context
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.watolib import backup_snapshots
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.config_domain_name import (
    ConfigDomainName,
    DomainRequest,
    DomainRequests,
    get_always_activate_domains,
    get_config_domain,
    SerializedSettings,
)
from cmk.gui.watolib.config_sync import (
    ABCSnapshotDataCollector,
    create_distributed_wato_files,
    get_site_globals,
    ReplicationPath,
    SnapshotSettings,
)
from cmk.gui.watolib.global_settings import save_site_global_settings
from cmk.gui.watolib.hosts_and_folders import (
    collect_all_hosts,
    folder_preserving_link,
    validate_all_hosts,
)
from cmk.gui.watolib.paths import wato_var_dir
from cmk.gui.watolib.site_changes import ChangeSpec, SiteChanges

from cmk import mkp_tool
from cmk.bi.type_defs import frozen_aggregations_dir
from cmk.discover_plugins import addons_plugins_local_path, plugins_local_path

# TODO: Make private
Phase = str  # TODO: Make dedicated type
PHASE_INITIALIZED = "initialized"  # Process has been initialized (not in thread yet)
PHASE_QUEUED = "queued"  # Process queued by site scheduler
PHASE_STARTED = "started"  # Process just started, nothing happened yet
PHASE_SYNC = "sync"  # About to sync
PHASE_ACTIVATE = "activate"  # sync done activating changes
PHASE_FINISHING = "finishing"  # Remote work done, finalizing local state
PHASE_DONE = "done"  # Done (with good or bad result)

# PHASE_DONE can have these different states:

State = str  # TODO: Make dedicated type
STATE_SUCCESS = "success"  # Everything is ok
STATE_ERROR = "error"  # Something went really wrong
STATE_WARNING = "warning"  # e.g. in case of core config warnings

# Available activation time keys

ACTIVATION_TIME_RESTART = "restart"
ACTIVATION_TIME_SYNC = "sync"
ACTIVATION_TIME_PROFILE_SYNC = "profile-sync"

ACTIVATION_TMP_BASE_DIR = str(cmk.utils.paths.tmp_dir / "wato/activation")
ACTIVATION_PERISTED_DIR = cmk.utils.paths.var_dir + "/wato/activation"

var_dir = cmk.utils.paths.var_dir + "/wato/"


GENERAL_DIR_EXCLUDE = "__pycache__"

# Directories and files to synchronize during replication
_replication_paths: list[ReplicationPath] = []

ConfigWarnings = dict[ConfigDomainName, list[str]]
ActivationId = str
SiteActivationState = dict[str, Any]
ActivationState = dict[str, SiteActivationState]
FileFilterFunc = Callable[[str], bool] | None
ActivationSource = Literal["GUI", "REST API", "INTERNAL"]


class MKLicensingError(Exception):
    pass


def get_free_message(format_html: bool = False) -> str:
    subject = _("Trial period ended: Distributed setup not allowed")
    body = _(
        "Your trial period has ended, and your license state is automatically converted to 'Free'. "
        "In this license state, a distributed setup is not allowed. In case you want to test "
        "distributed setups, please contact us at "
    )
    contact_link = "<a href='https://checkmk.com/contact'>https://checkmk.com/contact</a>"
    if format_html:
        return f"<b>{subject}</b><br>{body}{contact_link}"
    return "{}\n{}{}".format(subject, body, "https://checkmk.com/contact")


# TODO: find a way to make this more obvious/transparent in code
def add_replication_paths(repl_paths: list[ReplicationPath]) -> None:
    """Addition of any edition-specific replication paths (i.e. config files) that need
    to be synchronised in a distributed set-up.

    This addition is done dynamically by the various edition plugins.
    {enterprise,managed}/cmk/gui/{cee,cme}/plugins/wato
    """
    _replication_paths.extend(repl_paths)


def get_replication_paths() -> list[ReplicationPath]:
    """A list of replication paths common to all editions.

    NOTE: This list is enriched further by edition plugins. See
    'add_replication_paths'.
    """
    repl_paths: list[ReplicationPath] = [
        ReplicationPath(
            "dir",
            "check_mk",
            os.path.relpath(cmk.gui.watolib.utils.wato_root_dir(), cmk.utils.paths.omd_root),
            [],
        ),
        ReplicationPath(
            "dir",
            "multisite",
            os.path.relpath(cmk.gui.watolib.utils.multisite_dir(), cmk.utils.paths.omd_root),
            [],
        ),
        ReplicationPath(
            "file",
            "htpasswd",
            os.path.relpath(cmk.utils.paths.htpasswd_file, cmk.utils.paths.omd_root),
            [],
        ),
        ReplicationPath(
            "file",
            "auth.secret",
            os.path.relpath(cmk.utils.paths.auth_secret_file, cmk.utils.paths.omd_root),
            [],
        ),
        ReplicationPath(
            "file",
            "password_store.secret",
            os.path.relpath(cmk.utils.paths.password_store_secret_file, cmk.utils.paths.omd_root),
            [],
        ),
        ReplicationPath(
            "file",
            "auth.serials",
            os.path.relpath(
                "%s/auth.serials" % os.path.dirname(cmk.utils.paths.htpasswd_file),
                cmk.utils.paths.omd_root,
            ),
            [],
        ),
        ReplicationPath(
            "file",
            "stored_passwords",
            os.path.relpath(
                "%s/stored_passwords" % cmk.utils.paths.var_dir,
                cmk.utils.paths.omd_root,
            ),
            [],
        ),
        # Also replicate the user-settings of Multisite? While the replication
        # as such works pretty well, the count of pending changes will not
        # know.
        ReplicationPath(
            "dir",
            "usersettings",
            os.path.relpath(cmk.utils.paths.var_dir + "/web", cmk.utils.paths.omd_root),
            ["report-thumbnails", "session_info.mk"],
        ),
        ReplicationPath(
            "dir",
            "mkps",
            os.path.relpath(cmk.utils.paths.var_dir + "/packages", cmk.utils.paths.omd_root),
            [],
        ),
        ReplicationPath(
            "dir",
            "mkps_disabled",
            os.path.relpath(cmk.utils.paths.disabled_packages_dir, cmk.utils.paths.omd_root),
            [],
        ),
        ReplicationPath(  # add this explicitly, it is *not* below `local` despite the name.
            "dir",
            "mkps_avail",
            os.path.relpath(cmk.utils.paths.local_optional_packages_dir, cmk.utils.paths.omd_root),
            [],
        ),
        ReplicationPath(
            "dir",
            "local",
            "local",
            [],
        ),
        ReplicationPath(
            ty="file",
            ident="distributed_wato",
            site_path="etc/check_mk/conf.d/distributed_wato.mk",
            excludes=[],
        ),
        ReplicationPath(
            ty="dir",
            ident="omd",
            site_path="etc/omd",
            excludes=["site.conf", "instance_id"],
        ),
        ReplicationPath(
            ty="dir",
            ident="frozen_aggregations",
            site_path=os.path.relpath(frozen_aggregations_dir, cmk.utils.paths.omd_root),
            excludes=[],
        ),
        ReplicationPath(
            ty="dir",
            ident="topology",
            site_path=os.path.relpath(topology_dir, cmk.utils.paths.omd_root),
            excludes=[],
        ),
        ReplicationPath(
            ty="dir",
            ident="apache_proccess_tuning",
            site_path="etc/check_mk/apache.d/wato",
            excludes=[],
        ),
    ]

    # Include rule configuration into backup/restore/replication. Current
    # status is not backed up.
    if active_config.mkeventd_enabled:
        _rule_pack_dir = str(ec.rule_pack_dir().relative_to(cmk.utils.paths.omd_root))
        repl_paths.append(ReplicationPath("dir", "mkeventd", _rule_pack_dir, []))

        _mkp_rule_pack_dir = str(ec.mkp_rule_pack_dir().relative_to(cmk.utils.paths.omd_root))
        repl_paths.append(ReplicationPath("dir", "mkeventd_mkp", _mkp_rule_pack_dir, []))

    return repl_paths + _replication_paths


# If the site is not up-to-date, synchronize it first.
def sync_changes_before_remote_automation(site_id):
    manager = ActivateChangesManager()
    manager.load()

    if not manager.is_sync_needed(site_id):
        return

    logger.info("Syncing %s", site_id)

    manager.start(
        [site_id],
        activate_foreign=True,
        prevent_activate=True,
        source="INTERNAL",
    )

    # Wait maximum 30 seconds for sync to finish
    timeout = 30.0
    while manager.is_running() and timeout > 0.0:
        time.sleep(0.5)
        timeout -= 0.5

    state = manager.get_site_state(site_id)
    if state and state["_state"] != "success":
        logger.error(
            _("Remote automation tried to sync pending changes but failed: %s"),
            state.get("_status_details"),
        )


def _load_site_replication_status(site_id, lock=False):
    return store.load_object_from_file(
        _site_replication_status_path(site_id),
        default={},
        lock=lock,
    )


def _save_site_replication_status(site_id, repl_status):
    store.save_object_to_file(_site_replication_status_path(site_id), repl_status, pretty=False)


def _update_replication_status(site_id, vars_):
    """Updates one or more dict elements of a site in an atomic way."""
    store.mkdir(var_dir)

    repl_status = _load_site_replication_status(site_id, lock=True)
    try:
        repl_status.setdefault("times", {})
        repl_status.update(vars_)
    finally:
        _save_site_replication_status(site_id, repl_status)


def clear_site_replication_status(site_id):
    try:
        os.unlink(_site_replication_status_path(site_id))
    except FileNotFoundError:
        pass  # Not existant -> OK

    ActivateChanges().confirm_site_changes(site_id)


def _site_replication_status_path(site_id):
    return f"{var_dir}replication_status_{site_id}.mk"


def _load_replication_status(lock=False):
    return {
        site_id: _load_site_replication_status(site_id, lock=lock)
        for site_id in active_config.sites
    }


@dataclass
class PendingChangesInfo:
    number: int
    message: str | None

    def has_changes(self) -> bool:
        return self.number > 0

    @property
    def message_without_number(self) -> str | None:
        """Returns only the non-numeric (and non-"+") part of the pending changes message
        E.g.: self.message = "2 pending changes" -> "pending changes"
              self.message = "10+ Änderungen"    -> "Änderungen"
        The message cannot be split by the first space as for the Japanese locale there is no space
        between number and word"
        """
        if self.message is None:
            return None

        match = re.match(r"(\d+\+?)([^\d\+].*)", self.message)
        if match is None:
            raise MKInternalError(
                "pending_changes_str",
                _(
                    'The given str "%s" for the pending changes info does not match the required '
                    'pattern: "[number] change(s)"'
                )
                % self.message,
            )
        return match.groups()[1].strip()


@dataclass()
class ActivationStatus:
    site_id: SiteId
    activation_id: ActivationId
    phase: Phase
    time_started: float
    time_end: float
    time_updated: float
    expected_duration: float
    state: State
    status_text: str
    status_details: str | None


def get_activation_times(site_id):
    repl_status = _load_site_replication_status(site_id)
    return repl_status.get("times", {})


def _mark_queued(site_activation_state: SiteActivationState) -> None:
    _set_result(site_activation_state, PHASE_QUEUED, _("Queued"))


def _mark_running(site_activation_state: SiteActivationState) -> None:
    _set_result(site_activation_state, PHASE_STARTED, _("Started"))


def _is_currently_activating(site_rep_status) -> bool:  # type: ignore[no-untyped-def]
    current_activation_id = site_rep_status.get("current_activation")
    if not current_activation_id:
        return False

    # Is this activation still in progress?
    manager = ActivateChangesManager()

    try:
        manager.load_activation(current_activation_id)
    except MKUserError:
        return False  # Not existent anymore!

    if manager.is_running():
        return True

    return False


def _lock_activation(site_activation_state: SiteActivationState) -> bool:
    # This locks the site specific replication status file
    repl_status = _load_site_replication_status(site_activation_state["_site_id"], lock=True)
    got_lock = False
    try:
        if _is_currently_activating(repl_status):
            _set_result(
                site_activation_state,
                PHASE_DONE,
                _("Locked"),
                # Prevent key error for existing site_activation_states after update?!
                status_details=_(
                    "Activation blocked.<br>%s is currently activating "
                    "changes on this site.<br>Ongoing activation has been "
                    "executed from Checkmk %s."
                )
                % (
                    repl_status.get("current_user_id", "UNKNOWN"),
                    repl_status.get("current_source", "UNKNOWN"),
                ),
                state=STATE_WARNING,
            )
            return False

        got_lock = True
        _mark_queued(site_activation_state)
        return True
    finally:
        # This call unlocks the replication status file after setting "current_activation"
        # which will prevent other users from starting an activation for this site.
        # If the site was already locked, simply release the lock without further changes
        if got_lock:
            _update_replication_status(
                site_activation_state["_site_id"],
                {
                    "current_activation": site_activation_state["_activation_id"],
                    "current_source": site_activation_state["_source"],
                    "current_user_id": site_activation_state["_user_id"],
                },
            )
        else:
            store.release_lock(_site_replication_status_path(site_activation_state["_site_id"]))


def _unlock_activation(
    site_id: SiteId,
    activation_id: ActivationId,
    source: ActivationSource,
) -> None:
    _update_replication_status(
        site_id,
        {
            "last_activation": activation_id,
            "current_activation": None,
            "current_source": None,
            "current_user_id": None,
        },
    )


def update_activation_time(site_id: SiteId, time_key: str, duration: float) -> None:
    repl_status = _load_site_replication_status(site_id, lock=True)
    try:
        times = repl_status.setdefault("times", {})

        if time_key not in times:
            times[time_key] = duration
        else:
            times[time_key] = 0.8 * times[time_key] + 0.2 * duration
    finally:
        _save_site_replication_status(site_id, repl_status)


def _calc_status_details(
    time_started: float,
    time_ended: float,
    expected_duration: float,
    phase: Phase,
    status_details: str | None,
) -> str:
    # As long as the site is in queue, there is no time started
    if phase == PHASE_QUEUED:
        value = _("Queued for update")
    elif time_started is not None:
        value = _("Started at: %s.") % render.time_of_day(time_started)
    else:
        value = _("Not started.")

    if phase == PHASE_DONE:
        value += _(" Finished at: %s.") % render.time_of_day(time_ended)
    elif phase != PHASE_QUEUED:
        assert isinstance(time_started, (int, float))
        estimated_time_left = expected_duration - (time.time() - time_started)
        if estimated_time_left < 0:
            value += " " + _("Takes %.1f seconds longer than expected") % abs(estimated_time_left)
        else:
            value += " " + _("Approximately finishes in %.1f seconds") % estimated_time_left

    if status_details:
        value += "<br>%s" % status_details

    return value


def _set_result(
    current_state: SiteActivationState,
    phase: Phase,
    status_text: str,
    status_details: str | None = None,
    state: State = STATE_SUCCESS,
) -> None:
    """Stores the current state for displaying in the GUI

    Args:
        phase: Identity of the current phase
        status_text: Short label. Is used as text on the progress bar.
        status_details: HTML code that is rendered into the Details cell.
        state: String identifying the state of the activation. Is used as part of the
            progress bar CSS class ("state_[state]").
    """
    current_state["_phase"] = phase
    current_state["_status_text"] = status_text

    if phase != PHASE_INITIALIZED:
        current_state["_status_details"] = _calc_status_details(
            current_state["_time_started"],
            current_state["_time_ended"],
            current_state["_expected_duration"],
            phase,
            status_details,
        )

    current_state["_time_updated"] = time.time()
    if phase == PHASE_DONE:
        current_state["_time_ended"] = current_state["_time_updated"]
        current_state["_state"] = state

    _save_state(current_state["_activation_id"], current_state["_site_id"], current_state)


def _handle_activation_changes_exception(
    exc_logger: logging.Logger,
    exc_msg: str,
    site_activation_status: SiteActivationState,
) -> None:
    exc_logger.exception("error activating changes")
    # The text of following exception will be rendered in the GUI and the error message may
    # contain some remotely-fetched data (including HTML) so we are escaping it to avoid
    # executing arbitrary HTML code.
    # The escape function does not escape some simple tags used for formatting.
    # SUP-9840
    escaped_exception = escaping.escape_text(exc_msg)
    _set_result(
        site_activation_status,
        PHASE_DONE,
        _("Failed"),
        escaped_exception,
        state=STATE_ERROR,
    )


def _load_expected_duration(site_id: SiteId, activate_changes: ActivateChanges) -> float:
    times = get_activation_times(site_id)
    duration = 0.0

    if activate_changes.is_sync_needed(site_id):
        duration += times.get(ACTIVATION_TIME_SYNC, 0)

    if activate_changes.is_activate_needed(site_id):
        duration += times.get(ACTIVATION_TIME_RESTART, 0)

    # In case expected is 0, calculate with 10 seconds instead of failing
    if duration == 0.0:
        duration = 10.0

    return duration


def _set_sync_state(
    site_activation_state: SiteActivationState, status_details: str | None = None
) -> None:
    _set_result(
        site_activation_state,
        PHASE_SYNC,
        _("Synchronizing"),
        status_details=status_details,
    )


def _get_config_sync_state(
    site_id: SiteId, replication_paths: Sequence[ReplicationPath]
) -> tuple[ConfigSyncFileInfos, int]:
    """Get the config file states from the remote sites

    Calls the automation call "get-config-sync-state" on the remote site,
    which is handled by AutomationGetConfigSyncState."""
    site = get_site_config(site_id)
    response = cmk.gui.watolib.automations.do_remote_automation(
        site,
        "get-config-sync-state",
        [("replication_paths", repr([tuple(r) for r in replication_paths]))],
    )

    assert isinstance(response, tuple)
    return {k: ConfigSyncFileInfo(*v) for k, v in response[0].items()}, response[1]


def _synchronize_files(
    site_id: SiteId,
    files_to_sync: list[str],
    files_to_delete: list[str],
    remote_config_generation: int,
    site_config_dir: Path,
) -> None:
    """Pack the files in a simple tar archive and send it to the remote site

    We build a simple tar archive containing all files to be synchronized.  The list of file to
    be deleted and the current config generation is handed over using dedicated HTTP parameters.
    """

    sync_archive = _get_sync_archive(files_to_sync, site_config_dir)

    site = get_site_config(site_id)
    response = cmk.gui.watolib.automations.do_remote_automation(
        site,
        "receive-config-sync",
        [
            ("site_id", site_id),
            ("to_delete", repr(files_to_delete)),
            ("config_generation", "%d" % remote_config_generation),
        ],
        files={"sync_archive": io.BytesIO(sync_archive)},
    )

    if response is not True:
        raise MKGeneralException(_("Failed to synchronize with site: %s") % response)


@dataclass(frozen=True)
class SyncState:
    central_file_infos: ConfigSyncFileInfos
    remote_file_infos: ConfigSyncFileInfos
    remote_config_generation: int


def fetch_sync_state(
    replication_paths: list[ReplicationPath],
    site_activation_state: SiteActivationState,
    central_file_infos: ConfigSyncFileInfos,
) -> tuple[SyncState, SiteActivationState, float] | None:
    site_id = site_activation_state["_site_id"]
    site_logger = logger.getChild(f"site[{site_id}]")

    sync_start = time.time()
    try:
        _set_sync_state(site_activation_state)

        _set_sync_state(site_activation_state, _("Fetching sync state"))
        site_logger.debug(site_activation_state, "Starting config sync")

        remote_file_infos, remote_config_generation = _get_config_sync_state(
            site_id, replication_paths
        )
        site_logger.debug("Received %d file infos from remote", len(remote_file_infos))

        return (
            SyncState(
                central_file_infos=central_file_infos,
                remote_file_infos=remote_file_infos,
                remote_config_generation=remote_config_generation,
            ),
            site_activation_state,
            sync_start,
        )
    except Exception as e:
        duration = time.time() - sync_start
        update_activation_time(site_id, ACTIVATION_TIME_SYNC, duration)
        _handle_activation_changes_exception(site_logger, str(e), site_activation_state)
        return None


def calc_sync_delta(
    sync_state: SyncState,
    file_filter_func: FileFilterFunc,
    site_activation_state: SiteActivationState,
    sync_start: float,
) -> tuple[SyncDelta, SiteActivationState, float] | None:
    site_id = site_activation_state["_site_id"]
    site_logger = logger.getChild(f"site[{site_id}]")
    try:
        _set_sync_state(site_activation_state, _("Computing differences"))

        sync_delta = get_file_names_to_sync(site_id, site_logger, sync_state, file_filter_func)

        site_logger.debug("New files to be synchronized: %r", sync_delta.to_sync_new)
        site_logger.debug("Changed files to be synchronized: %r", sync_delta.to_sync_changed)
        site_logger.debug("Obsolete files to be deleted: %r", sync_delta.to_delete)

        return sync_delta, site_activation_state, sync_start
    except Exception as e:
        duration = time.time() - sync_start
        update_activation_time(site_id, ACTIVATION_TIME_SYNC, duration)
        _handle_activation_changes_exception(site_logger, str(e), site_activation_state)
        return None


def synchronize_files(
    sync_delta: SyncDelta,
    remote_config_generation: int,
    site_config_dir: Path,
    site_activation_state: SiteActivationState,
    sync_start: float,
) -> SiteActivationState | None:
    site_id = site_activation_state["_site_id"]
    site_logger = logger.getChild(f"site[{site_id}]")

    try:
        if (
            not sync_delta.to_sync_new
            and not sync_delta.to_sync_changed
            and not sync_delta.to_delete
        ):
            site_logger.debug("Finished config sync (Nothing to be done)")
            return site_activation_state

        _set_sync_state(
            site_activation_state,
            _("Transferring: %d new, %d changed and %d vanished files")
            % (
                len(sync_delta.to_sync_new),
                len(sync_delta.to_sync_changed),
                len(sync_delta.to_delete),
            ),
        )
        _synchronize_files(
            site_id,
            sync_delta.to_sync_new + sync_delta.to_sync_changed,
            sync_delta.to_delete,
            remote_config_generation,
            site_config_dir,
        )
        site_logger.debug("Finished config sync")
        return site_activation_state
    except Exception as e:
        _handle_activation_changes_exception(site_logger, str(e), site_activation_state)
        return None
    finally:
        duration = time.time() - sync_start
        update_activation_time(site_id, ACTIVATION_TIME_SYNC, duration)


def _set_done_result(
    configuration_warnings: ConfigWarnings, site_activation_state: SiteActivationState
) -> None:
    if any(configuration_warnings.values()):
        details = _render_warnings(configuration_warnings)
        _set_result(
            site_activation_state,
            PHASE_DONE,
            _("Activated"),
            details,
            state=STATE_WARNING,
        )
    else:
        _set_result(site_activation_state, PHASE_DONE, _("Success"), state=STATE_SUCCESS)


def _confirm_synchronized_changes(site_id: SiteId) -> None:
    with SiteChanges(site_id).mutable_view() as changes:
        for change in changes:
            change["need_sync"] = False


def _confirm_activated_changes(
    site_id: SiteId, site_changes_activate_until: Sequence[ChangeSpec]
) -> None:
    with SiteChanges(site_id).mutable_view() as changes:
        changes[: len(site_changes_activate_until)] = []


def _is_activate_needed(all_site_changes: Sequence[ChangeSpec]) -> bool:
    return any(c["need_restart"] for c in all_site_changes)


def _get_domains_needing_activation(
    omd_ident: ConfigDomainName, site_changes_activate_until: Sequence[ChangeSpec]
) -> DomainRequests:
    domain_settings: dict[ConfigDomainName, list[SerializedSettings]] = {}
    omd_domain_used: bool = False
    for change in site_changes_activate_until:
        if change["need_restart"]:
            for domain_name in change["domains"]:
                # ConfigDomainOMD needs a restart of the apache,
                # make sure it's executed at the end
                if domain_name == omd_ident:
                    omd_domain_used = True
                    omd_domain_change = change
                    continue
                domain_settings.setdefault(domain_name, []).append(
                    get_config_domain(domain_name).get_domain_settings(change)
                )

    domain_requests = sorted(
        (
            get_config_domain(domain_name).get_domain_request(settings_list)
            for (domain_name, settings_list) in domain_settings.items()
        ),
        key=lambda x: x.name,
    )

    if omd_domain_used:
        domain_requests.append(get_config_domain(omd_ident).get_domain_request([omd_domain_change]))

    return domain_requests


def _get_omd_domain_background_job_result(site_id: SiteId) -> Sequence[str]:
    """
    OMD domain needs restart of the whole site so the apache connection gets lost.
    A background job is started and we have to wait for the result
    """
    while True:
        try:
            raw_omd_response = cmk.gui.watolib.automations.do_remote_automation(
                get_site_config(site_id),
                "checkmk-remote-automation-get-status",
                [("request", repr("omd-config-change"))],
            )

            assert isinstance(raw_omd_response, tuple)
            omd_response = cmk.gui.watolib.automations.CheckmkAutomationGetStatusResponse(
                JobStatusSpec.model_validate(raw_omd_response[0]),
                raw_omd_response[1],
            )
            if not omd_response.job_status.is_active:
                return list(omd_response.job_status.loginfo["JobException"])
            time.sleep(0.5)
        except MKUserError as e:
            if not (e.message == "Site is not running" or e.message.startswith("HTTP Error - 502")):
                return [e.message]


def _call_activate_changes_automation(
    site_id: SiteId, site_changes_activate_until: Sequence[ChangeSpec]
) -> ConfigWarnings:
    omd_ident: ConfigDomainName = config_domain_name.OMD
    domain_requests = _get_domains_needing_activation(omd_ident, site_changes_activate_until)

    if site_is_local(site_id):
        return execute_activate_changes(domain_requests)

    serialized_requests = list(asdict(x) for x in domain_requests)
    try:
        response = cmk.gui.watolib.automations.do_remote_automation(
            get_site_config(site_id),
            "activate-changes",
            [("domains", repr(serialized_requests)), ("site_id", site_id)],
        )
    except cmk.gui.watolib.automations.MKAutomationException as e:
        if "Invalid automation command: activate-changes" in "%s" % e:
            raise MKGeneralException(
                "Activate changes failed (%s). The version of this site may be too old."
            )
        raise

    # If request.settings is empty no `omd-config-change` job is started
    assert isinstance(response, dict)
    if any(request.name == omd_ident and request.settings for request in domain_requests):
        response.setdefault(omd_ident, []).extend(_get_omd_domain_background_job_result(site_id))

    return response


def _do_activate(
    site_id: SiteId,
    site_changes_activate_until: Sequence[ChangeSpec],
    site_activation_state: SiteActivationState,
) -> ConfigWarnings:
    _set_result(site_activation_state, PHASE_ACTIVATE, _("Activating"))

    start = time.time()

    configuration_warnings = _call_activate_changes_automation(site_id, site_changes_activate_until)

    duration = time.time() - start
    update_activation_time(site_id, ACTIVATION_TIME_RESTART, duration)
    return configuration_warnings


def activate_remote_changes(
    activate_changes: ActivateChanges,
    prevent_activate: bool,
    site_activation_state: SiteActivationState,
) -> SiteActivationState | None:
    site_id = site_activation_state["_site_id"]
    site_logger = logger.getChild(f"site[{site_id}]")

    try:
        _set_result(site_activation_state, PHASE_FINISHING, _("Finalizing"))
        site_changes_activate_until = activate_changes.get_changes_to_activate(site_id)

        configuration_warnings = {}
        if prevent_activate:
            _confirm_synchronized_changes(site_id)
        else:
            if activate_changes.is_activate_needed_until(site_id):
                configuration_warnings = _do_activate(
                    site_id, site_changes_activate_until, site_activation_state
                )
            _confirm_activated_changes(site_id, site_changes_activate_until)

        _set_done_result(configuration_warnings, site_activation_state)
        return site_activation_state
    except Exception as e:
        _handle_activation_changes_exception(site_logger, str(e), site_activation_state)
        return None


class ActivateChanges:
    def __init__(self) -> None:
        self._repstatus: dict = {}

        # Changes grouped by site
        self._changes_by_site: dict = {}

        # Changes grouped by site up until a specific activation id
        self._changes_by_site_until: dict = {}

        # A list of changes ordered by time and grouped by the change.
        # Each change contains a list of affected sites.
        self._all_changes: list[tuple[str, dict]] = []
        self._pending_changes: list[tuple[str, dict]] = []
        super().__init__()

    def load(self):
        self._repstatus = _load_replication_status()
        self._load_changes()

    def _load_changes(self):
        self._changes_by_site = {}

        active_changes: dict[str, dict[str, Any]] = {}
        pending_changes: dict[str, dict[str, Any]] = {}

        # Astroid 2.x bug prevents us from using NewType https://github.com/PyCQA/pylint/issues/2296
        # pylint: disable=not-an-iterable
        for site_id in activation_sites():
            site_changes = SiteChanges(site_id).read()
            self._changes_by_site[site_id] = site_changes

            if not site_changes:
                continue

            # Assume changes can be recorded multiple times and deduplicate them.
            for change in site_changes:
                change_id = change["id"]
                target_bucket = active_changes if has_been_activated(change) else pending_changes
                if change_id not in target_bucket:
                    target_bucket[change_id] = change.copy()

                affected_sites = target_bucket[change_id].setdefault("affected_sites", [])
                affected_sites.append(site_id)

        self._pending_changes = sorted(pending_changes.items(), key=lambda k_v: k_v[1]["time"])
        self._all_changes = sorted(
            list(pending_changes.items()) + list(active_changes.items()),
            key=lambda k_v: k_v[1]["time"],
        )

    def load_changes_until(self, activation_id: ActivationId, sites: Iterable[SiteId]) -> None:
        manager = load_activate_change_manager_with_id(activation_id)
        change_id = manager.activate_until()

        # Find the last activated change and return all changes till this entry
        # (including the one we were searching for)
        self._changes_by_site_until = {}
        for site_id in sites:
            changes = []
            for change in self._changes_by_site[site_id]:
                changes.append(change)
                if change["id"] == change_id:
                    break

            self._changes_by_site_until[site_id] = changes

    def confirm_site_changes(self, site_id):
        SiteChanges(site_id).clear()
        cmk.gui.watolib.sidebar_reload.need_sidebar_reload()

    @staticmethod
    def _get_number_of_pending_changes() -> int:
        changes_counter = 0
        # Astroid 2.x bug prevents us from using NewType https://github.com/PyCQA/pylint/issues/2296
        # pylint: disable=not-an-iterable
        for site_id in activation_sites():
            changes = SiteChanges(site_id).read()
            changes_counter += len(
                list(change for change in changes if not has_been_activated(change))
            )
        return changes_counter

    @staticmethod
    def _make_changes_message(number_of_changes: int) -> str | None:
        if number_of_changes > 10:
            return _("10+ changes")
        if number_of_changes == 1:
            return _("1 change")
        if number_of_changes > 1:
            return _("%d changes") % number_of_changes
        return None

    def get_changes_estimate(self) -> str | None:
        number_of_changes = self._get_number_of_pending_changes()
        return self._make_changes_message(number_of_changes)

    def get_pending_changes_info(self) -> PendingChangesInfo:
        number_of_changes = self._get_number_of_pending_changes()
        message = self._make_changes_message(number_of_changes)
        return PendingChangesInfo(number=number_of_changes, message=message)

    def discard_changes_forbidden(self):
        for site_id in set(activation_sites()):
            for change in SiteChanges(site_id).read():
                if change.get("prevent_discard_changes", False):
                    return True
        return False

    def grouped_changes(self):
        return self._pending_changes

    def _changes_of_site(self, site_id):
        return self._changes_by_site[site_id]

    def dirty_and_active_activation_sites(self) -> list[SiteId]:
        """Returns the list of sites that should be used when activating all affected sites"""
        return self.filter_not_activatable_sites(self.dirty_sites())

    def filter_not_activatable_sites(
        self, sites: list[tuple[SiteId, SiteConfiguration]]
    ) -> list[SiteId]:
        dirty = []
        for site_id, site in sites:
            status = self._get_site_status(site_id, site)[1]
            is_online = self._site_is_online(status)
            is_logged_in = self._site_is_logged_in(site_id, site)

            if is_online and is_logged_in:
                dirty.append(site_id)
        return dirty

    def dirty_sites(self) -> list[tuple[SiteId, SiteConfiguration]]:
        """Returns the list of sites that have changes (including offline sites)"""
        return [s for s in activation_sites().items() if self._changes_of_site(s[0])]

    def _site_is_logged_in(self, site_id, site):
        return site_is_local(site_id) or "secret" in site

    def _site_is_online(self, status: str) -> bool:
        return status in ["online", "disabled"]

    def _get_site_status(self, site_id: SiteId, site: SiteConfiguration) -> tuple[SiteStatus, str]:
        if site.get("disabled"):
            site_status = SiteStatus({})
            status = "disabled"
        else:
            site_status = sites_states().get(site_id, SiteStatus({}))
            status = site_status.get("state", "unknown")

        return site_status, status

    def _site_has_foreign_changes(self, site_id):
        changes = self._changes_of_site(site_id)
        return bool([c for c in changes if is_foreign_change(c) and not has_been_activated(c)])

    def _is_sync_needed_specific_changes(
        self, site_id: SiteId, changes_to_check: Sequence[ChangeSpec]
    ) -> bool:
        if site_is_local(site_id):
            return False

        return any(c["need_sync"] for c in changes_to_check)

    def is_sync_needed(self, site_id: SiteId) -> bool:
        return self._is_sync_needed_specific_changes(site_id, self._changes_of_site(site_id))

    def is_sync_needed_until(self, site_id: SiteId) -> bool:
        return self._is_sync_needed_specific_changes(site_id, self._changes_by_site_until[site_id])

    def _is_activate_needed_specific_changes(self, changes_to_check: Sequence[ChangeSpec]) -> bool:
        return any(c["need_restart"] for c in changes_to_check)

    def is_activate_needed(self, site_id: SiteId) -> bool:
        return self._is_activate_needed_specific_changes(self._changes_of_site(site_id))

    def is_activate_needed_until(self, site_id: SiteId) -> bool:
        return self._is_activate_needed_specific_changes(self._changes_by_site_until[site_id])

    def _last_activation_state(self, site_id: SiteId):  # type: ignore[no-untyped-def]
        """This function returns the last known persisted activation state"""
        return store.load_object_from_file(
            ActivateChangesManager.persisted_site_state_path(site_id), default={}
        )

    def _get_last_change_id(self) -> str:
        return self._pending_changes[-1][1]["id"]

    def has_changes(self) -> bool:
        return bool(self._all_changes)

    def has_pending_changes(self) -> bool:
        return bool(self._pending_changes)

    def has_foreign_changes(self) -> bool:
        return any(
            change
            for _change_id, change in self._pending_changes
            if is_foreign_change(change) and not has_been_activated(change)
        )

    def _has_foreign_changes_on_any_site(self) -> bool:
        return any(
            change
            for _change_id, change in self._pending_changes
            if is_foreign_change(change)
            and not has_been_activated(change)
            and affects_all_sites(change)
        )

    def get_activation_time(self, site_id, ty, deflt=None):
        return get_activation_times(site_id).get(ty, deflt)

    def get_changes_to_activate(self, site_id: SiteId) -> Sequence[ChangeSpec]:
        return self._changes_by_site_until[site_id]


def has_been_activated(change) -> bool:  # type:ignore[no-untyped-def]
    return change.get("has_been_activated", False)


def prevent_discard_changes(change) -> bool:  # type:ignore[no-untyped-def]
    return change.get("prevent_discard_changes", False)


def is_foreign_change(change) -> bool:  # type:ignore[no-untyped-def]
    return change["user_id"] and change["user_id"] != user.id


def affects_all_sites(change) -> bool:  # type:ignore[no-untyped-def]
    return not set(change["affected_sites"]).symmetric_difference(set(activation_sites()))


class ActivateChangesManager(ActivateChanges):
    """Manages the activation of pending configuration changes

    A single object cares about one activation for all affected sites.

    It is used to execute an activation using ActivateChangesManager.start().  During execution it
    persists it's activation information. This makes it possible to gather the activation state
    asynchronously.

    Prepares the snapshots for synchronization and handles all the objects that manage the
    activation for the single sites.
    """

    # These keys will be persisted in <activation_id>/info.mk
    info_keys = (
        "_sites",
        "_activate_until",
        "_comment",
        "_activate_foreign",
        "_activation_id",
        "_time_started",
        "_persisted_changes",
    )

    def __init__(self) -> None:
        self._sites: list[SiteId] = []
        self._site_snapshot_settings: dict[SiteId, SnapshotSettings] = {}
        self._activate_until: str | None = None
        self._comment: str | None = None
        self._activate_foreign = False
        self._activation_id: str | None = None
        self._prevent_activate = False
        self._persisted_changes: list[dict[str, Any]] = []

        store.makedirs(ACTIVATION_PERISTED_DIR)
        super().__init__()

    @property
    def activation_id(self) -> str:
        return self._new_activation_id() if self._activation_id is None else self._activation_id

    @property
    def sites(self) -> Sequence[SiteId]:
        return self._sites

    @property
    def activate_foreign(self) -> bool:
        return self._activate_foreign

    @property
    def time_started(self) -> float:
        return self._time_started

    @property
    def persisted_changes(self) -> Sequence[ActivationChange]:
        return [ActivationChange(**change) for change in self._persisted_changes]

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
    def start(
        self,
        sites: list[SiteId],
        source: ActivationSource,
        activate_until: str | None = None,
        comment: str | None = None,
        activate_foreign: bool = False,
        prevent_activate: bool = False,
    ) -> ActivationId:
        """Start activation of changes.

        For each site one background process will be launched, handling the activation of one
        particular site. Handling of remote sites is done transparently through the use of
        SyncSnapshots.

        Args:
            sites:
                The sites for which activation should be started.

            source:
                The source of the activation. Possible sources: "GUI", "REST API", "INTERNAL"

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
        _raise_for_license_block()

        self._activate_foreign = activate_foreign

        self._sites = self._get_sites(sites)
        self._source = source
        self._activation_id = self._new_activation_id()

        self._site_snapshot_settings = self._get_site_snapshot_settings(
            self._activation_id, self._sites
        )
        self._activate_until = (
            self._get_last_change_id() if activate_until is None else activate_until
        )
        self._comment = comment
        self._time_started = time.time()
        self._prevent_activate = prevent_activate
        self._set_persisted_changes()

        self._verify_valid_host_config()
        self._save_activation()

        # Always do housekeeping. We chose to only delete activations older than one minute, as we
        # don't want to accidentally "clean up" our soon-to-be started activations.
        execute_activation_cleanup_background_job(maximum_age=60)

        self._pre_activate_changes()
        self._create_snapshots()
        self._save_activation()

        self._start_activation()

        return self._activation_id

    def _verify_valid_host_config(self):
        defective_hosts = validate_all_hosts([], force_all=True)
        if defective_hosts:
            raise MKUserError(
                None,
                _("You cannot activate changes while some hosts have an invalid configuration: ")
                + ", ".join(
                    [
                        '<a href="%s">%s</a>'
                        % (
                            folder_preserving_link([("mode", "edit_host"), ("host", hn)]),
                            hn,
                        )
                        for hn in defective_hosts
                    ]
                ),
            )

    def activate_until(self):
        return self._activate_until

    def wait_for_completion(self, timeout: float | None = None) -> bool:
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
    def running_sites(self) -> list[SiteId]:
        running = []
        for site_id in self._sites:
            if self._activation_running(site_id):
                running.append(site_id)

        return running

    def _new_activation_id(self) -> ActivationId:
        return cmk.gui.utils.gen_id()

    def _get_sites(self, sites: list[SiteId]) -> list[SiteId]:
        for site_id in sites:
            # suppression needed because of pylint bug, see https://github.com/PyCQA/pylint/issues/2296
            if site_id not in activation_sites():  # pylint: disable=unsupported-membership-test
                raise MKUserError("sites", _('The site "%s" does not exist.') % site_id)

        return sites

    def _info_path(self, activation_id: str) -> str:
        if not re.match(r"^[\d\-a-fA-F]+$", activation_id):
            raise MKUserError(
                None,
                _("Invalid activation_id"),
            )
        return f"{ACTIVATION_TMP_BASE_DIR}/{activation_id}/info.mk"

    def activations(self) -> Iterator[tuple[str, dict[str, Any]]]:
        for activation_id in get_activation_ids():
            yield activation_id, self._load_activation_info(activation_id)

    def _site_snapshot_file(self, site_id: SiteId) -> str:
        return "{}/{}/site_{}_sync.tar.gz".format(
            ACTIVATION_TMP_BASE_DIR,
            self._activation_id,
            site_id,
        )

    def _load_activation_info(self, activation_id: str) -> dict[str, Any]:
        info_path = self._info_path(activation_id)
        if not os.path.exists(info_path):
            raise MKUserError(
                None,
                f"Unknown activation process: {activation_id!r} not found",
            )
        return store.load_object_from_file(info_path, default={})

    def _set_persisted_changes(self) -> None:
        """Sets the persisted_changes, which are a subset of self._changes."""
        if not self._persisted_changes:
            for _activation_id, change in self._pending_changes:
                self._persisted_changes.append(
                    asdict(
                        ActivationChange(
                            **{
                                k: v
                                for k, v in change.items()
                                if k in ("id", "action_name", "text", "user_id", "time")
                            }
                        )
                    )
                )

    def _save_activation(self) -> None:
        if self._activation_id is None:
            raise MKUserError(None, _("activation ID is not set"))

        store.makedirs(os.path.dirname(self._info_path(self._activation_id)))
        to_file = {key: getattr(self, key) for key in self.info_keys}
        store.save_object_to_file(self._info_path(self._activation_id), to_file)

    # Give hooks chance to do some pre-activation things (and maybe stop
    # the activation)
    def _pre_activate_changes(self):
        try:
            if hooks.registered("pre-distribute-changes"):
                hooks.call("pre-distribute-changes", collect_all_hosts())
        except Exception as e:
            logger.exception("error calling pre-distribute-changes hook")
            if active_config.debug:
                raise
            raise MKUserError(None, _("Can not start activation: %s") % e)

    def _create_snapshots(self):
        """Creates the needed SyncSnapshots for each applicable site.

        Some conflict prevention is being done. This function checks for the presence of
        newer changes than the ones to be activated.

        """
        with store.lock_checkmk_configuration():
            if not self._pending_changes:
                raise MKUserError(None, _("Currently there are no changes to activate."))

            if self._get_last_change_id() != self._activate_until:
                raise MKUserError(
                    None,
                    _(
                        "Another change has been made in the meantime. Please review it "
                        "to ensure you also want to activate it now and start the "
                        "activation again."
                    ),
                )

            backup_snapshot_proc = multiprocessing.Process(
                target=backup_snapshots.create_snapshot, args=(self._comment,)
            )
            backup_snapshot_proc.start()

            if self._activation_id is None:
                raise Exception("activation ID is not set")

            logger.debug("Start creating config sync snapshots")
            start = time.time()
            work_dir = os.path.join(ACTIVATION_TMP_BASE_DIR, self._activation_id)

            # Do not create a snapshot for the local site. All files are already in place
            site_snapshot_settings = self._site_snapshot_settings.copy()
            try:
                del site_snapshot_settings[omd_site()]
            except KeyError:
                pass

            snapshot_manager = SnapshotManager.factory(
                work_dir, site_snapshot_settings, version.edition()
            )
            snapshot_manager.generate_snapshots()
            logger.debug("Config sync snapshot creation took %.4f", time.time() - start)

            logger.debug("Waiting for backup snapshot creation to complete")
            backup_snapshot_proc.join()

        logger.debug("Finished all snapshots")

    def _get_site_snapshot_settings(
        self, activation_id: ActivationId, sites: list[SiteId]
    ) -> dict[SiteId, SnapshotSettings]:
        snapshot_settings = {}

        for site_id in sites:
            self._check_snapshot_creation_permissions(site_id)

            site_config = active_config.sites[site_id]
            work_dir = cmk.utils.paths.site_config_dir / activation_id / site_id

            snapshot_components = _get_replication_components(site_config)

            # Generate a quick reference_by_name for each component
            component_names = {c[1] for c in snapshot_components}

            snapshot_settings[site_id] = SnapshotSettings(
                snapshot_path=self._site_snapshot_file(site_id),
                work_dir=str(work_dir),
                snapshot_components=snapshot_components,
                component_names=component_names,
                site_config=site_config,
            )

        return snapshot_settings

    def _check_snapshot_creation_permissions(self, site_id):
        if self._site_has_foreign_changes(site_id) and not self._activate_foreign:
            if not user.may("wato.activateforeign"):
                raise MKUserError(
                    None,
                    _(
                        "There are some changes made by your colleagues that you can not "
                        "activate because you are not permitted to. You can only activate "
                        "the changes on the sites that are not affected by these changes. "
                        "<br>"
                        "If you need to activate your changes on all sites, please contact "
                        "a permitted user to do it for you."
                    ),
                )

            raise MKUserError(
                None,
                _(
                    "There are some changes made by your colleagues and you did not "
                    "confirm to activate these changes. In order to proceed, you will "
                    "have to confirm the activation or ask you colleagues to activate "
                    "these changes in their own."
                ),
            )

    def _start_activation(self) -> None:
        self._log_activation()
        assert self._activation_id is not None
        job = ActivateChangesSchedulerBackgroundJob(
            self._activation_id,
            self._site_snapshot_settings,
            self._prevent_activate,
            self._source,
        )
        job.start(job.schedule_sites)

    def _log_activation(self):
        log_msg = "Starting activation (Sites: %s)" % ",".join(self._sites)
        log_audit("activate-changes", log_msg)

        if self._comment:
            log_audit("activate-changes", "Comment: %s" % self._comment)

    def get_state(self) -> ActivationState:
        return {"sites": {site_id: self.get_site_state(site_id) for site_id in self._sites}}  #

    def get_site_state(self, site_id):
        if self._activation_id is None:
            raise Exception("activation ID is not set")
        return store.load_object_from_file(
            ActivateChangesManager.site_state_path(self._activation_id, site_id),
            default={},
        )

    @staticmethod
    def persisted_site_state_path(site_id: SiteId) -> str:
        return os.path.join(
            ACTIVATION_PERISTED_DIR,
            ActivateChangesManager.site_filename(site_id),
        )

    @staticmethod
    def site_state_path(activation_id: ActivationId, site_id: SiteId) -> str:
        return os.path.join(
            ACTIVATION_TMP_BASE_DIR,
            activation_id,
            ActivateChangesManager.site_filename(site_id),
        )

    @staticmethod
    def site_filename(site_id):
        return "site_%s.mk" % site_id


def make_cre_snapshot_manager(
    work_dir: str,
    site_snapshot_settings: dict[SiteId, SnapshotSettings],
    edition: version.Edition,
) -> SnapshotManager:
    return SnapshotManager(
        work_dir,
        site_snapshot_settings,
        CRESnapshotDataCollector(site_snapshot_settings),
        reuse_identical_snapshots=True,
        generate_in_subprocess=False,
    )


class SnapshotManager:
    factory: Callable[[str, dict[SiteId, SnapshotSettings], version.Edition], SnapshotManager] = (
        make_cre_snapshot_manager
    )

    def __init__(
        self,
        activation_work_dir: str,
        site_snapshot_settings: dict[SiteId, SnapshotSettings],
        data_collector: ABCSnapshotDataCollector,
        reuse_identical_snapshots: bool,
        generate_in_subprocess: bool,
    ) -> None:
        super().__init__()
        self._activation_work_dir = activation_work_dir
        self._site_snapshot_settings = site_snapshot_settings
        self._data_collector = data_collector
        self._reuse_identical_snapshots = reuse_identical_snapshots
        self._generate_in_subproces = generate_in_subprocess

        # Stores site and folder specific information to speed-up the snapshot generation
        self._logger = logger.getChild(self.__class__.__name__)

    def generate_snapshots(self) -> None:
        if not self._site_snapshot_settings:
            # Nothing to do
            return

        # 1. Collect files to "var/check_mk/site_configs" directory
        self._data_collector.prepare_snapshot_files()

        # 2. Allow hooks to further modify the reference data for the remote site
        hooks.call("post-snapshot-creation", self._site_snapshot_settings)


def _clone_site_config_directory(
    site_logger: logging.Logger,
    site_id: str,
    snapshot_settings: SnapshotSettings,
    origin_site_work_dir: str,
) -> None:
    site_logger.debug("Processing site %s", site_id)

    if os.path.exists(snapshot_settings.work_dir):
        shutil.rmtree(snapshot_settings.work_dir)

    completed_process = subprocess.run(
        ["cp", "-al", origin_site_work_dir, snapshot_settings.work_dir],
        shell=False,
        close_fds=True,
        check=False,
    )

    assert completed_process.returncode == 0
    site_logger.debug("Finished site")


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

        for site_id, snapshot_settings in sorted(
            self._site_snapshot_settings.items(), key=lambda x: x[0]
        ):
            site_globals = get_site_globals(site_id, snapshot_settings.site_config)

            save_site_global_settings(site_globals, custom_site_path=snapshot_settings.work_dir)

            create_distributed_wato_files(Path(snapshot_settings.work_dir), site_id, is_remote=True)

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

        for component in self.get_generic_components():
            # Generic components (i.e. any component that does not have "ident"
            # = "sitespecific") are collected to be snapshotted. Site-specific
            # components as well as distributed wato components are done later on
            # in the process.

            # Note that at this stage, components that have been deselected
            # from site synchronisation by the user must not be pre-filtered,
            # otherwise these settings would cascade randomly from the first site
            # to the other sites.

            # These components are deselected in the snapshot settings of the
            # site, which is the basis of the actual synchronisation.

            # Examples of components that can be excluded:
            # - event console ("mkeventd", "mkeventd_mkp")
            # - MKPs ("local", "mkps")

            source_path = cmk.utils.paths.omd_root / component.site_path
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
            # shutil.copytree(source_path, str(target_path.parent) + "/", copy_function=os.link)

            completed_process = subprocess.run(
                ["cp", "-al", str(source_path), str(target_path.parent) + "/"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                shell=False,
                close_fds=True,
                check=False,
            )
            if completed_process.returncode:
                self._logger.error(
                    "Failed to clone files from %s to %s: %s",
                    source_path,
                    str(target_path),
                    completed_process.stdout,
                )
                raise MKGeneralException("Failed to create site config directory")

        self._logger.debug("Finished site")

    def _clone_site_config_directories(
        self, origin_site_id: SiteId, site_ids: list[SiteId]
    ) -> None:
        clone_args = [
            (
                self._logger.getChild(f"site[{site_id}]"),
                site_id,
                self._site_snapshot_settings[site_id],
                self._site_snapshot_settings[origin_site_id].work_dir,
            )
            for site_id in site_ids
        ]

        num_threads = 5  # based on rudimentary tests, performance improvement drops off after
        with multiprocessing.pool.ThreadPool(processes=num_threads) as copy_pool:
            copy_pool.starmap(_clone_site_config_directory, clone_args)

    def get_generic_components(self) -> list[ReplicationPath]:
        return get_replication_paths()

    def get_site_components(
        self, snapshot_settings: SnapshotSettings
    ) -> tuple[list[ReplicationPath], list[ReplicationPath]]:
        generic_site_components = []
        custom_site_components = []

        for component in snapshot_settings.snapshot_components:
            if component.ident == "sitespecific":
                # Only the site specific global files are individually handled in the non CME snapshot
                custom_site_components.append(component)
            else:
                generic_site_components.append(component)

        return generic_site_components, custom_site_components


class ActivationCleanupBackgroundJob(BackgroundJob):
    job_prefix = "activation_cleanup"

    @classmethod
    def gui_title(cls):
        return _("Activation cleanup")

    def __init__(self, maximum_age: int = 300) -> None:
        """
        Args:

            maximum_age:
                How old the activations need to be (in seconds), for them to be considered
                for deletion.

                Some examples:
                    * When the value is 0, this means *every* non-running activation it finds,
                      regardless of its age, will be considered for deletion.
                    * When the value is 60, every non-running activation started at least 60
                      seconds ago will be considered for deletion. Newer activations will not be
                      considered.

                The default value is 300 (seconds), which are exactly 5 minutes.

        """
        super().__init__(
            self.job_prefix,
            InitialStatusArgs(
                title=self.gui_title(),
                lock_wato=False,
                stoppable=False,
                user=str(user.id) if user.id else None,
            ),
        )
        self.maximum_age = maximum_age

    def do_execute(self, job_interface: BackgroundProcessInterface) -> None:
        self._do_housekeeping()
        job_interface.send_result_message(_("Activation cleanup finished"))

    def _do_housekeeping(self) -> None:
        """Cleanup non-running activation directories"""
        with store.lock_checkmk_configuration():
            for activation_id in self._existing_activation_ids():
                self._logger.info("Check activation: %s", activation_id)
                delete = False
                manager = ActivateChangesManager()

                # Try to detect whether the activation is still in progress. In case the
                # activation information can not be read, it is likely that the activation has
                # just finished while we were iterating the activations.
                # In case loading fails continue with the next activations
                try:
                    delete = True

                    try:
                        manager.load_activation(activation_id)
                        # This may mean, has not been started or has already completed.
                        delete = not manager.is_running()
                    except MKUserError:
                        # "Unknown activation process", is normal after activation -> Delete, but no
                        # error message logging
                        self._logger.debug("Is not running")
                except Exception as e:
                    self._logger.warning(
                        "  Failed to load activation (%s), trying to delete...",
                        e,
                        exc_info=True,
                    )

                self._logger.info("  -> %s", "Delete" if delete else "Keep")
                if not delete:
                    continue

                # Because the heuristic to detect if an activation is or isn't running is not
                # very reliable (stated politely) we need to make sure that we don't accidentally
                # delete activations WHICH HAVE NOT BEEN STARTED YET. To make sure this is not the
                # case we wait for some time and only delete sufficiently old activations.
                for base_dir in (
                    str(cmk.utils.paths.site_config_dir),
                    ACTIVATION_TMP_BASE_DIR,
                ):
                    activation_dir = os.path.join(base_dir, activation_id)
                    if not os.path.isdir(activation_dir):
                        continue

                    # TODO:
                    #   This checks creation time, which is kind of silly. More interesting would be
                    #   to consider completion time.
                    dir_stat = os.stat(activation_dir)
                    if time.time() - dir_stat.st_mtime < self.maximum_age:
                        continue

                    try:
                        shutil.rmtree(activation_dir)
                    except Exception:
                        self._logger.error(
                            "  Failed to delete the activation directory '%s'" % activation_dir,
                            exc_info=True,
                        )

    def _existing_activation_ids(self):
        files = set()

        for base_dir in (
            str(cmk.utils.paths.site_config_dir),
            ACTIVATION_TMP_BASE_DIR,
        ):
            try:
                files.update(os.listdir(base_dir))
            except FileNotFoundError:
                pass

        ids = []
        for activation_id in files:
            if len(activation_id) == 36 and activation_id[8] == "-" and activation_id[13] == "-":
                ids.append(activation_id)
        return ids


def execute_activation_cleanup_background_job(maximum_age: int | None = None) -> None:
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log."""
    if maximum_age is not None:
        job = ActivationCleanupBackgroundJob(maximum_age=maximum_age)
    else:
        job = ActivationCleanupBackgroundJob()

    if job.is_active():
        logger.debug("Another activation cleanup job is already running: Skipping this time")
        return

    try:
        job.start(job.do_execute)
    except BackgroundJobAlreadyRunning:
        logger.debug("Another activation cleanup job is already running: Skipping this time")


def _handle_distributed_sites_in_free(
    site_snapshot_settings: Mapping[SiteId, SnapshotSettings], time_started: float
) -> bool:
    distributed_sites_in_free = [
        site_id for site_id in site_snapshot_settings if site_id != omd_site()
    ]
    for start_site_id in distributed_sites_in_free:
        _handle_activation_changes_exception(
            logger.getChild(f"site[{start_site_id}]"),
            get_free_message(),
            {"_site_id": start_site_id, "_time_started": time_started},
        )
    return any(distributed_sites_in_free)


def _initialize_site_activation_state(
    site_id: SiteId,
    activation_id: ActivationId,
    activate_changes: ActivateChanges,
    time_started: float,
    source: ActivationSource,
) -> SiteActivationState:
    site_activation_state = {
        "_site_id": site_id,
        "_activation_id": activation_id,
        "_phase": None,
        "_state": None,
        "_status_text": None,
        "_status_details": None,
        "_time_started": time_started,
        "_time_updated": None,
        "_time_ended": None,
        "_expected_duration": _load_expected_duration(site_id, activate_changes),
        "_pid": os.getpid(),
        "_user_id": user.id,
        "_source": source,
    }
    return site_activation_state


class ReplicationPathType(enum.StrEnum):
    FILE = enum.auto()
    DIR = enum.auto()


def _get_config_sync_file_infos_per_inode(
    replication_paths: Sequence[ReplicationPath],
) -> Mapping[int, ConfigSyncFileInfo]:
    inode_sync_states = {}

    for replication_path in replication_paths:
        replication_path_full = os.path.join(cmk.utils.paths.omd_root, replication_path.site_path)

        if not os.path.exists(replication_path_full):
            continue

        if replication_path.ty == ReplicationPathType.FILE:
            inode_sync_states[os.stat(replication_path_full).st_ino] = _get_config_sync_file_info(
                replication_path_full
            )
        elif replication_path.ty == ReplicationPathType.DIR:
            _get_replication_dir_config_sync_file_infos_per_inode(
                inode_sync_states, replication_path_full, replication_path.excludes
            )
        else:
            raise NotImplementedError()

    return inode_sync_states


def _get_replication_dir_config_sync_file_infos_per_inode(
    inode_sync_states: MutableMapping[int, ConfigSyncFileInfo],
    replication_path: str,
    replication_path_excludes: Sequence[str],
) -> None:
    # Use os functionality instead of pathlib since it is faster
    for root, dir_names, file_names in os.walk(replication_path):
        root_name = os.path.basename(root)
        if root_name == GENERAL_DIR_EXCLUDE or root_name in replication_path_excludes:
            continue

        for dir_name in dir_names:
            dir_path = os.path.join(root, dir_name)
            if (
                os.path.exists(dir_path)
                and os.path.islink(dir_path)
                and not dir_name == GENERAL_DIR_EXCLUDE
            ):
                inode_sync_states[os.stat(dir_path).st_ino] = _get_config_sync_file_info(dir_path)

        for file_name in file_names:
            file_path = os.path.join(root, file_name)
            if os.path.exists(file_path):
                inode_sync_states[os.stat(file_path).st_ino] = _get_config_sync_file_info(file_path)


def _prepare_for_activation_tasks(
    activate_changes: ActivateChanges,
    activation_id: ActivationId,
    site_snapshot_settings: Mapping[SiteId, SnapshotSettings],
    time_started: float,
    source: ActivationSource,
) -> tuple[Mapping[SiteId, ConfigSyncFileInfos], Mapping[SiteId, SiteActivationState]]:
    config_sync_file_infos_per_inode = _get_config_sync_file_infos_per_inode(
        get_replication_paths()
    )
    central_file_infos_per_site = {}
    site_activation_states_per_site = {}
    for site_id, snapshot_settings in sorted(site_snapshot_settings.items(), key=lambda e: e[0]):
        site_activation_state = _initialize_site_activation_state(
            site_id, activation_id, activate_changes, time_started, source
        )
        try:
            if not _lock_activation(site_activation_state):
                continue
            _mark_running(site_activation_state)

            log_audit("activate-changes", "Started activation of site %s" % site_id)
            site_activation_states_per_site[site_id] = site_activation_state

            if activate_changes.is_sync_needed(site_id):
                central_file_infos_per_site[site_id] = _get_site_central_file_infos(
                    site_id, snapshot_settings, config_sync_file_infos_per_inode
                )
        except Exception as e:
            _handle_activation_changes_exception(
                logger.getChild(f"site[{site_id}]"), str(e), site_activation_state
            )
            _cleanup_activation(site_id, activation_id, source)
    return central_file_infos_per_site, site_activation_states_per_site


def _get_site_central_file_infos(
    site_id: SiteId,
    snapshot_settings: SnapshotSettings,
    config_sync_file_infos_per_inode: Mapping[int, ConfigSyncFileInfo],
) -> ConfigSyncFileInfos:
    # In case we experience performance issues here, we could postpone the hashing of the
    # central files to only be done ad-hoc in get_file_names_to_sync when the other attributes
    # are not enough to detect a differing file.

    site_config_dir = Path(snapshot_settings.work_dir)
    central_file_infos = _get_config_sync_file_infos(
        snapshot_settings.snapshot_components,
        site_config_dir,
        config_sync_file_infos_per_inode,
    )

    logger.getChild(f"site[{site_id}]").debug(
        "Got %d file infos from %s", len(central_file_infos), site_config_dir
    )
    return central_file_infos


class ActiveTasks(TypedDict):
    fetch_sync_state: MutableMapping[SiteId, AsyncResult]
    calc_sync_delta: MutableMapping[SiteId, AsyncResult]
    synchronize_files: MutableMapping[SiteId, AsyncResult]
    activate_remote_changes: MutableMapping[SiteId, AsyncResult]


def _error_callback(error: BaseException) -> None:
    # for exceptions that could not be handled within the function, e.g. calling with incorrect
    # number of arguments
    logger.error(str(error))


def sync_and_activate(
    activation_id: str,
    site_snapshot_settings: Mapping[SiteId, SnapshotSettings],
    file_filter_func: FileFilterFunc,
    source: ActivationSource,
    prevent_activate: bool = False,
) -> None:
    """
    Realizes the incremental config sync from the central to the remote site

    1. Gather the replication paths handled by the central site.

        We want the state of these files from the remote site to be able to compare the state
        of the central sites site_config directory with it. Warning: In mixed version setups
        it would not be enough to use the replication paths known by the remote site.
        We really need the central sites definitions.

    2. Send them over to the remote site and request the current state of the mentioned files
    3. Compare the response with the site_config directory of the site
    4. Collect needed files and send them over to the remote site (+ remote config hash)
    5. Raise when something failed on the remote site while applying the sent files
    """
    site_activation_states: Mapping[SiteId, SiteActivationState] = {}
    try:
        time_started = time.time()

        setthreadtitle("cmk-activate-changes")

        # Cleanup existing livestatus connections (may be opened later when needed)
        sites_disconnect()

        activate_changes = ActivateChanges()
        activate_changes.load()
        activate_changes.load_changes_until(activation_id, site_snapshot_settings.keys())

        if is_free():
            if _handle_distributed_sites_in_free(site_snapshot_settings, time_started):
                return

        (
            site_central_file_infos,
            site_activation_states,
        ) = _prepare_for_activation_tasks(
            activate_changes,
            activation_id,
            site_snapshot_settings,
            time_started,
            source,
        )

        task_pool = ThreadPool(processes=len(site_snapshot_settings))

        active_tasks = ActiveTasks(
            fetch_sync_state={},
            calc_sync_delta={},
            synchronize_files={},
            activate_remote_changes={},
        )

        for site_id, site_activation_state in site_activation_states.items():
            if activate_changes.is_sync_needed(site_id):
                async_result = task_pool.apply_async(
                    func=copy_request_context(fetch_sync_state),
                    args=(
                        site_snapshot_settings[site_id].snapshot_components,
                        site_activation_state,
                        site_central_file_infos[site_id],
                    ),
                    error_callback=_error_callback,
                )
                active_tasks["fetch_sync_state"][site_id] = async_result
            else:
                async_result = task_pool.apply_async(
                    func=copy_request_context(activate_remote_changes),
                    args=(activate_changes, prevent_activate, site_activation_state),
                    error_callback=_error_callback,
                )
                active_tasks["activate_remote_changes"][site_id] = async_result

        remote_config_generation_per_site: dict[SiteId, int] = {}
        # we want to mostly parallelize the activation steps, but if one site takes longer,
        # it should not hold up the other sites
        # -> monitor active tasks to handle results as soon as one finishes and start a task for
        # the next step
        while (
            len(active_tasks["fetch_sync_state"]) > 0
            or len(active_tasks["calc_sync_delta"]) > 0
            or len(active_tasks["synchronize_files"]) > 0
            or len(active_tasks["activate_remote_changes"]) > 0
        ):
            time.sleep(0.1)
            _handle_active_tasks(
                active_tasks,
                activate_changes,
                file_filter_func,
                prevent_activate,
                remote_config_generation_per_site,
                site_snapshot_settings,
                task_pool,
            )

    except Exception:
        logger.exception("error activating changes")
    finally:
        for activation_site_id in site_activation_states:
            _cleanup_activation(activation_site_id, activation_id, source)


def _cleanup_activation(
    site_id: SiteId, activation_id: ActivationId, source: ActivationSource
) -> None:
    _unlock_activation(site_id, activation_id, source)
    # Create a copy of last result in the persisted dir
    shutil.copy(
        ActivateChangesManager.site_state_path(activation_id, site_id),
        ActivateChangesManager.persisted_site_state_path(site_id),
    )


def _handle_active_tasks(
    active_tasks: ActiveTasks,
    activate_changes: ActivateChanges,
    file_filter_func: FileFilterFunc,
    prevent_activate: bool,
    remote_config_generation_per_site: MutableMapping[SiteId, int],
    site_snapshot_settings: Mapping[SiteId, SnapshotSettings],
    task_pool: ThreadPool,
) -> None:
    for site_id, async_result in list(active_tasks["fetch_sync_state"].items()):
        if not async_result.ready():
            return

        active_tasks["fetch_sync_state"].pop(site_id)
        if (fetch_sync_state_results := async_result.get()) is None:
            return  # exception handling happens in thread

        sync_state, activation_state, sync_start_time = fetch_sync_state_results
        remote_config_generation_per_site[site_id] = sync_state.remote_config_generation

        active_tasks["calc_sync_delta"][site_id] = task_pool.apply_async(
            func=copy_request_context(calc_sync_delta),
            args=(sync_state, file_filter_func, activation_state, sync_start_time),
            error_callback=_error_callback,
        )

    for site_id, async_result in list(active_tasks["calc_sync_delta"].items()):
        if not async_result.ready():
            return

        active_tasks["calc_sync_delta"].pop(site_id)
        if (calc_sync_delta_result := async_result.get()) is None:
            return  # exception handling happens in thread

        sync_delta, activation_state, sync_start_time = calc_sync_delta_result
        active_tasks["synchronize_files"][site_id] = task_pool.apply_async(
            func=copy_request_context(synchronize_files),
            args=(
                sync_delta,
                remote_config_generation_per_site[site_id],
                Path(site_snapshot_settings[site_id].work_dir),
                activation_state,
                sync_start_time,
            ),
            error_callback=_error_callback,
        )

    for site_id, async_result in list(active_tasks["synchronize_files"].items()):
        if not async_result.ready():
            return

        active_tasks["synchronize_files"].pop(site_id)
        if (activation_state := async_result.get()) is None:
            return  # exception handling happens in thread

        active_tasks["activate_remote_changes"][site_id] = task_pool.apply_async(
            func=copy_request_context(activate_remote_changes),
            args=(activate_changes, prevent_activate, activation_state),
            error_callback=_error_callback,
        )

    for site_id, async_result in list(active_tasks["activate_remote_changes"].items()):
        if not async_result.ready():
            return

        active_tasks["activate_remote_changes"].pop(site_id)


class ActivateChangesSchedulerBackgroundJob(BackgroundJob):
    job_prefix = "activate-changes-scheduler"
    housekeeping_max_age_sec = 86400 * 30
    housekeeping_max_count = 10
    file_filter_func: Callable[[str], bool] | None = None

    @classmethod
    def gui_title(cls):
        return _("Activate Changes Scheduler")

    def __init__(
        self,
        activation_id: str,
        site_snapshot_settings: dict[SiteId, SnapshotSettings],
        prevent_activate: bool,
        source: ActivationSource,
    ) -> None:
        super().__init__(
            f"{self.job_prefix}-{activation_id}",
            InitialStatusArgs(
                deletable=False,
                stoppable=False,
                user=str(user.id) if user.id else None,
            ),
        )
        self._activation_id = activation_id
        self._site_snapshot_settings = site_snapshot_settings
        self._prevent_activate = prevent_activate
        self._source = source

    def schedule_sites(self, job_interface: BackgroundProcessInterface) -> None:
        job_interface.send_progress_update(
            _("Activate Changes Scheduler started"), with_timestamp=True
        )

        job_interface.send_progress_update(
            _("Going to update %d sites") % len(self._site_snapshot_settings),
            with_timestamp=True,
        )

        sync_and_activate(
            self._activation_id,
            self._site_snapshot_settings,
            ActivateChangesSchedulerBackgroundJob.file_filter_func,
            self._source,
            self._prevent_activate,
        )
        job_interface.send_result_message(_("Activate changes finished"))


def _render_warnings(configuration_warnings: ConfigWarnings) -> str:
    html_code = "<div class=warning>"
    html_code += "<b>%s</b>" % _("Warnings:")
    html_code += "<ul>"
    for domain, warnings in sorted(configuration_warnings.items()):
        for warning in warnings:
            html_code += "<li>{}: {}</li>".format(
                escaping.escape_attribute(domain),
                escaping.escape_attribute(warning),
            )
    html_code += "</ul>"
    html_code += "</div>"
    return html_code


def _save_state(activation_id: ActivationId, site_id: SiteId, state: SiteActivationState) -> None:
    state_path = ActivateChangesManager.site_state_path(activation_id, site_id)
    store.save_object_to_file(state_path, state)


def parse_serialized_domain_requests(
    serialized_requests: Iterable[SerializedSettings],
) -> DomainRequests:
    return [DomainRequest(**x) for x in serialized_requests]


def execute_activate_changes(domain_requests: DomainRequests) -> ConfigWarnings:
    domain_names = [x.name for x in domain_requests]

    all_domain_requests = [
        domain.get_domain_request([])
        for domain in get_always_activate_domains()
        if domain.ident() not in domain_names
    ]
    all_domain_requests.extend(domain_requests)
    all_domain_requests.sort(key=lambda x: x.name)

    results: ConfigWarnings = {}
    for domain_request in all_domain_requests:
        warnings = get_config_domain(domain_request.name)().activate(domain_request.settings)
        results[domain_request.name] = warnings or []

    _add_extensions_for_license_usage()
    _update_links_for_agent_receiver()

    return results


def _add_extensions_for_license_usage():
    save_extensions(
        LicenseUsageExtensions(
            ntop=is_ntop_configured(),
        )
    )


def _update_links_for_agent_receiver() -> None:
    uuid_link_manager = agent_registration.get_uuid_link_manager()
    uuid_link_manager.update_links(collect_all_hosts())


def confirm_all_local_changes() -> None:
    ActivateChanges().confirm_site_changes(omd_site())


def has_pending_changes() -> bool:
    return ActivateChanges().get_pending_changes_info().has_changes()


def get_pending_changes_tooltip() -> str:
    changes_info = ActivateChanges().get_pending_changes_info()
    if changes_info.has_changes():
        n_changes = changes_info.number
        return (
            (
                _("Currently, there is one pending change not yet activated.")
                if n_changes == 1
                else _("Currently, there are %s not yet activated.") % n_changes
            )
            + "\n"
            + _("Click here for details.")
        )
    return _("Click here to see the activation status per site.")


def get_number_of_pending_changes() -> int:
    changes = ActivateChanges()
    changes.load()
    return len(changes.grouped_changes())


def get_pending_changes() -> dict[str, ActivationChange]:
    changes = ActivateChanges()
    changes.load()
    return {
        change_id: ActivationChange(
            id=ac["id"],
            user_id=ac["user_id"],
            action_name=ac["action_name"],
            text=ac["text"],
            time=ac["time"],
        )
        for change_id, ac in changes.grouped_changes()
    }


def _need_to_update_mkps_after_sync() -> bool:
    if not (central_version := _request.headers.get("x-checkmk-version")):
        raise ValueError("Request header x-checkmk-version is missing")
    logger.debug("Local version: %s, Central version: %s", version.__version__, central_version)
    return version.__version__ != central_version


def _need_to_update_config_after_sync() -> bool:
    if not (central_version := _request.headers.get("x-checkmk-version")):
        raise ValueError("Request header x-checkmk-version is missing")
    this_v = version.Version.from_str(version.__version__)
    other_v = version.Version.from_str(central_version)
    if this_v.base is None or other_v.base is None:
        logger.debug(
            "Unable to determine base version of master daily build (%s, %s): "
            "Assume no cmk-update-config needed",
            this_v.base,
            other_v.base,
        )
        # We can not decide which is the current base version of the master daily builds.
        # For this reason we always treat them to be compatbile.
        return False
    return (this_v.base.major, this_v.base.minor) != (
        other_v.base.major,
        other_v.base.minor,
    )


def _execute_cmk_update_config() -> None:
    completed_process = subprocess.run(
        ["cmk-update-config", "--site-may-run", "--conflict", "abort"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        encoding="utf-8",
        check=False,
    )
    logger.log(
        logging.DEBUG if completed_process.returncode == 0 else logging.WARNING,
        "'cmk-update-config' finished. Exit code: %s, Output: %s",
        completed_process.returncode,
        completed_process.stdout,
    )

    if completed_process.returncode:
        raise MKGeneralException(_("Configuration update failed\n%s") % completed_process.stdout)


def _execute_update_passwords() -> None:
    cmd = ["cmk", "--automation", "update-passwords-merged-file"]
    msg_template = f"{' '.join(cmd)!r} finished. Exit code: %s, Output: %s"
    try:
        out = subprocess.check_output(cmd, encoding="utf-8")
        logger.log(logging.DEBUG, msg_template, 0, out)
    except subprocess.CalledProcessError as e:
        logger.log(logging.WARNING, msg_template, e.returncode, e.output)
        raise MKGeneralException(_("Collection of passwords failed\n%s") % e.output)


def _execute_post_config_sync_actions(site_id: SiteId) -> None:
    try:
        # When receiving configuration from a central site that uses a previous major
        # version, the config migration logic has to be executed to make the local
        # configuration compatible with the local Checkmk version.
        if _need_to_update_mkps_after_sync():
            logger.debug("Updating active packages")
            local_path = plugins_local_path()
            addons_path = addons_plugins_local_path()
            if local_path is not None and addons_path is not None:
                uninstalled, installed = mkp_tool.update_active_packages(
                    mkp_tool.Installer(paths.installed_packages_dir),
                    mkp_tool.PathConfig(
                        cmk_plugins_dir=local_path,
                        cmk_addons_plugins_dir=addons_path,
                        agent_based_plugins_dir=paths.local_agent_based_plugins_dir,
                        agents_dir=paths.local_agents_dir,
                        alert_handlers_dir=paths.local_alert_handlers_dir,
                        bin_dir=paths.local_bin_dir,
                        check_manpages_dir=paths.local_legacy_check_manpages_dir,
                        checks_dir=paths.local_checks_dir,
                        doc_dir=paths.local_doc_dir,
                        gui_plugins_dir=paths.local_gui_plugins_dir,
                        installed_packages_dir=paths.installed_packages_dir,
                        inventory_dir=paths.local_inventory_dir,
                        lib_dir=paths.local_lib_dir,
                        locale_dir=paths.local_locale_dir,
                        local_root=paths.local_root,
                        mib_dir=paths.local_mib_dir,
                        mkp_rule_pack_dir=ec.mkp_rule_pack_dir(),
                        notifications_dir=paths.local_notifications_dir,
                        pnp_templates_dir=paths.local_pnp_templates_dir,
                        manifests_dir=paths.tmp_dir,
                        web_dir=paths.local_web_dir,
                    ),
                    mkp_tool.PackageStore(
                        enabled_dir=paths.local_enabled_packages_dir,
                        local_dir=paths.local_optional_packages_dir,
                        shipped_dir=paths.optional_packages_dir,
                    ),
                    {
                        mkp_tool.PackagePart.EC_RULE_PACKS: mkp_tool.PackageOperationCallbacks(
                            install=ec.install_packaged_rule_packs,
                            release=ec.release_packaged_rule_packs,
                            uninstall=ec.uninstall_packaged_rule_packs,
                        )
                    },
                    version.__version__,
                    parse_version=version.parse_check_mk_version,
                )
                mkp_tool.make_post_package_change_actions(
                    on_any_change=(
                        mkp_tool.reload_apache,
                        invalidate_visuals_cache,
                        setup_search_index.request_index_rebuild,
                    )
                )([*uninstalled, *installed])
        if _need_to_update_config_after_sync():
            logger.debug("Executing cmk-update-config")
            _execute_cmk_update_config()

        _execute_update_passwords()

        # The local configuration has just been replaced. The pending changes are not
        # relevant anymore. Confirm all of them to cleanup the inconsistency.
        logger.debug("Confirming pending changes")
        confirm_all_local_changes()

        hooks.call("snapshot-pushed")
    except Exception:
        raise MKGeneralException(
            _(
                'Failed to deploy configuration: "%s". '
                "Please note that the site configuration has been synchronized "
                "partially."
            )
            % traceback.format_exc()
        )

    log_audit(
        "replication",
        "Synchronized configuration from central site (local site ID is %s.)" % site_id,
    )


def verify_remote_site_config(site_id: SiteId) -> None:
    our_id = omd_site()

    if not is_single_local_site():
        raise MKGeneralException(
            _(
                "Configuration error. You treat us as "
                "a <b>remote</b>, but we have an own distributed Setup configuration!"
            )
        )

    if our_id is not None and our_id != site_id:
        raise MKGeneralException(
            _("Site ID mismatch. Our ID is '%s', but you are saying we are '%s'.")
            % (our_id, site_id)
        )

    # Make sure there are no local changes we would lose!
    changes = cmk.gui.watolib.activate_changes.ActivateChanges()
    changes.load()
    pending = list(reversed(changes.grouped_changes()))
    if pending:
        message = _(
            "There are %d pending changes that would get lost. The most recent are: "
        ) % len(pending)
        message += ", ".join(change["text"] for _change_id, change in pending[:10])

        raise MKGeneralException(message)


def _get_replication_components(
    site_config: SiteConfiguration,
) -> list[ReplicationPath]:
    """Gives a list of ReplicationPath instances.

    These represent the folders which need to be sent to remote sites. Whether a specific subset
    of paths need to be sent is being determined by the site-specific `site_config`.

    Note:
        "Replication path" or "replication component" or "snapshot component" are the same concept.

    Args:
        site_config:
            The site configuration. Specifically the following keys on it are used:

                 - `replicate_ec`:
                 - `replicate_mkps`

    Returns:
        A list of ReplicationPath instances, specifying which paths shall be packaged for this
        particular site.

    """
    repl_paths = get_replication_paths()[:]

    # Remove Event Console settings, if this site does not want it (might
    # be removed in some future day)
    if not site_config.get("replicate_ec"):
        repl_paths = [e for e in repl_paths if e.ident not in ["mkeventd", "mkeventd_mkp"]]

    # Remove extensions if site does not want them
    if not site_config.get("replicate_mkps"):
        repl_paths = [
            e for e in repl_paths if e.ident not in ["local", "mkps", "mkps_disabled", "mkps_avail"]
        ]

    return repl_paths


def get_file_names_to_sync(
    site_id: SiteId,
    site_logger: logging.Logger,
    sync_state: SyncState,
    file_filter_func: FileFilterFunc,
) -> SyncDelta:
    """Compare the response with the site_config directory of the site

    Comparing both file lists and returning all files for synchronization that

    a) Do not exist on the remote site
    b) Differ from the central site
    c) Exist on the remote site but not on the central site as
    """

    # New files
    central_files = set(sync_state.central_file_infos.keys())
    remote_files_set = set(sync_state.remote_file_infos.keys())
    remote_site_config = get_site_config(site_id)
    remote_files = (
        _filter_remote_files(remote_files_set)
        if remote_site_config.get("user_sync")
        else remote_files_set
    )
    to_sync_new = list(central_files - remote_files)

    # Add differing files
    to_sync_changed = []
    for existing in central_files.intersection(remote_files):
        if sync_state.central_file_infos[existing] != sync_state.remote_file_infos[existing]:
            site_logger.debug(
                "Sync needed %s: %r <> %r",
                existing,
                sync_state.central_file_infos[existing],
                sync_state.remote_file_infos[existing],
            )
            to_sync_changed.append(existing)

    # Files to be deleted
    to_delete = list(remote_files - central_files)

    if file_filter_func is not None:
        to_sync_new = list(filterfalse(file_filter_func, to_sync_new))
        to_sync_changed = list(filterfalse(file_filter_func, to_sync_changed))
        to_delete = list(filterfalse(file_filter_func, to_delete))
    return SyncDelta(to_sync_new=to_sync_new, to_sync_changed=to_sync_changed, to_delete=to_delete)


def _filter_remote_files(remote_files: set[str]) -> set[str]:
    """
    Exclude the remote files of users not known to the central site from
    removal.

    This is important if a remote site uses LDAP connectors that the central
    site does not use. The central site would not know about the users on the
    remote site and would delete the unknown users on every sync.
    """
    remote_files_to_keep: set[str] = set()
    users_known_to_central: dict[UserId, bool] = {}
    for file in remote_files:
        if not file.startswith("var/check_mk/web"):
            remote_files_to_keep.add(file)
            continue

        file_parts = file.split("/")
        if len(file_parts) == 4:
            remote_files_to_keep.add(file)
            continue

        user_id = UserId(file_parts[3])

        if user_id not in users_known_to_central:
            users_known_to_central[user_id] = userdb.user_exists(user_id)

        if users_known_to_central[user_id]:
            remote_files_to_keep.add(file)

    return remote_files_to_keep


def _get_sync_archive(to_sync: list[str], base_dir: Path) -> bytes:
    # Use native tar instead of python tarfile for performance reasons
    completed_process = subprocess.run(
        [
            "tar",
            "-c",
            "-C",
            str(base_dir),
            "-f",
            "-",
            "--null",
            "-T",
            "-",
            "--preserve-permissions",
        ],
        input=b"\0".join(f.encode() for f in to_sync),
        capture_output=True,
        close_fds=True,
        shell=False,
        check=False,
    )

    # Since we don't stream the archive to the remote site (we could probably do this) it should be
    # no problem to buffer it in memory for the moment

    if completed_process.returncode:
        raise MKGeneralException(
            _("Failed to create sync archive [%d]: %s")
            % (completed_process.returncode, completed_process.stderr.decode())
        )

    return completed_process.stdout


def _unpack_sync_archive(sync_archive: bytes, base_dir: Path) -> None:
    completed_process = subprocess.run(
        [
            "tar",
            "-x",
            "-C",
            str(base_dir),
            "-f",
            "-",
            "-U",
            "--recursive-unlink",
            "--preserve-permissions",
        ],
        input=sync_archive,
        capture_output=True,
        close_fds=True,
        shell=False,
        check=False,
    )

    if completed_process.returncode:
        raise MKGeneralException(
            _("Failed to create sync archive [%d]: %s")
            % (completed_process.returncode, completed_process.stderr.decode())
        )


class ConfigSyncFileInfo(NamedTuple):
    st_mode: int
    st_size: int
    link_target: str | None
    file_hash: str | None


# Would've used some kind of named tuple here, but the serialization and deserialization is a pain.
# Using some simpler data structure for transport now to reduce the pain.
# GetConfigSyncStateResponse = NamedTuple("GetConfigSyncStateResponse", [
#    ("file_infos", dict[str, ConfigSyncFileInfo]),
#    ("config_generation", int),
# ])
GetConfigSyncStateResponse = tuple[dict[str, tuple[int, int, str | None, str | None]], int]

ConfigSyncFileInfos = dict[str, ConfigSyncFileInfo]


@dataclass(frozen=True)
class SyncDelta:
    to_sync_new: list[str]
    to_sync_changed: list[str]
    to_delete: list[str]


class AutomationGetConfigSyncState(AutomationCommand):
    """Called on remote site from a central site to get the current config sync state

    The central site hands over the list of replication paths it will try to synchronize later.  The
    remote site computes the list of replication files and sends it back together with the current
    configuration generation ID. The config generation ID is increased on every Setup modification
    and ensures that nothing is changed between the two config sync steps.
    """

    def command_name(self):
        return "get-config-sync-state"

    def get_request(self) -> list[ReplicationPath]:
        return [
            ReplicationPath(*e)
            for e in ast.literal_eval(_request.get_ascii_input_mandatory("replication_paths"))
        ]

    def execute(self, api_request: list[ReplicationPath]) -> GetConfigSyncStateResponse:
        with store.lock_checkmk_configuration():
            file_infos = _get_config_sync_file_infos(api_request, base_dir=cmk.utils.paths.omd_root)
            transport_file_infos = {
                k: (v.st_mode, v.st_size, v.link_target, v.file_hash) for k, v in file_infos.items()
            }
            return (transport_file_infos, _get_current_config_generation())


def _get_config_sync_paths(
    root_path: str,
    dir_names: Sequence[str],
    file_names: Sequence[str],
    general_dir_exclude: str,
    replication_path_excludes: Sequence[str],
) -> Sequence[str]:
    valid_entries = []

    for dir_name in dir_names:
        dir_path = os.path.join(root_path, dir_name)
        if (
            os.path.islink(dir_path)
            and not dir_name == general_dir_exclude
            and dir_name not in replication_path_excludes
        ):
            valid_entries.append(dir_path)

    for file_name in file_names:
        file_path = os.path.join(root_path, file_name)
        if (
            os.path.basename(os.path.dirname(file_path)) not in replication_path_excludes
            and file_name not in replication_path_excludes
        ):
            valid_entries.append(file_path)

    return valid_entries


def _get_config_sync_file_infos(
    replication_paths: list[ReplicationPath],
    base_dir: Path,
    config_sync_file_infos_per_inode: Mapping[int, ConfigSyncFileInfo] | None = None,
) -> ConfigSyncFileInfos:
    """Scans the given replication paths for the information needed for the config sync

    It produces a dictionary of sync file infos. One entry is created for each file.  Directories
    are not added to the dictionary unless it is a symlink.
    Since files to be synced for different site are copied as hardlink, the sync file infos can be
    precomputed and the relevant info then identified via the files inode
    """
    if config_sync_file_infos_per_inode is None:
        config_sync_file_infos_per_inode = {}

    infos = {}
    for replication_path in replication_paths:
        replication_path_full = str(base_dir.joinpath(replication_path.site_path))

        if not os.path.exists(replication_path_full):
            continue  # Only report back existing things

        if replication_path.ty == ReplicationPathType.FILE:
            infos[replication_path.site_path] = _get_config_sync_file_info(replication_path_full)

        elif replication_path.ty == ReplicationPathType.DIR:
            _get_replication_dir_config_sync_file_infos(
                infos,
                config_sync_file_infos_per_inode,
                base_dir,
                replication_path_full,
                replication_path.excludes,
            )
        else:
            raise NotImplementedError()
    return infos


def _get_replication_dir_config_sync_file_infos(
    infos: MutableMapping[str, ConfigSyncFileInfo],
    config_sync_file_infos_per_inode: Mapping[int, ConfigSyncFileInfo],
    base_dir: Path,
    replication_path: str,
    replication_path_excludes: Sequence[str],
) -> None:
    # Use os functionality instead of pathlib since it is faster
    for root, dir_names, file_names in os.walk(replication_path):
        root_name = os.path.basename(root)

        if root_name == GENERAL_DIR_EXCLUDE or root_name in replication_path_excludes:
            continue

        config_sync_paths = _get_config_sync_paths(
            root, dir_names, file_names, GENERAL_DIR_EXCLUDE, replication_path_excludes
        )
        for config_sync_path in config_sync_paths:
            valid_site_path = os.path.relpath(config_sync_path, base_dir)
            try:
                if sync_file_info := config_sync_file_infos_per_inode.get(
                    os.stat(config_sync_path).st_ino, None
                ):
                    infos[valid_site_path] = sync_file_info
                else:
                    infos[valid_site_path] = _get_config_sync_file_info(config_sync_path)
            except FileNotFoundError:  # e.g. broken symlinks
                infos[valid_site_path] = _get_config_sync_file_info(config_sync_path)


def _get_config_sync_file_info(file_path: str) -> ConfigSyncFileInfo:
    stat = os.lstat(file_path)
    is_symlink = os.path.islink(file_path)
    return ConfigSyncFileInfo(
        stat.st_mode,
        stat.st_size,
        os.readlink(str(file_path)) if is_symlink else None,
        _create_config_sync_file_hash(file_path) if not is_symlink else None,
    )


def _create_config_sync_file_hash(file_path: str) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()


def update_config_generation() -> None:
    """Increase the config generation ID

    This ID is used to detect whether something else has been changed in the configuration between
    two points in time. Therefore, all places that change the configuration must call this function
    at least once.
    """
    store.save_object_to_file(
        _config_generation_path(), _get_current_config_generation(lock=True) + 1
    )


def _get_current_config_generation(lock: bool = False) -> int:
    return store.load_object_from_file(_config_generation_path(), default=0, lock=lock)


def _config_generation_path() -> Path:
    return wato_var_dir() / "config-generation.mk"


class ReceiveConfigSyncRequest(NamedTuple):
    site_id: SiteId
    sync_archive: bytes
    to_delete: list[str]
    config_generation: int


class AutomationReceiveConfigSync(AutomationCommand):
    """Called on remote site from a central site to update the Checkmk configuration

    The central site hands over a tar archive with the files to be written and a list of
    files to be deleted. The configuration generation is used to validate that no modification has
    been made between the two sync steps (get-config-sync-state and this autmoation).
    """

    def command_name(self) -> str:
        return "receive-config-sync"

    def get_request(self) -> ReceiveConfigSyncRequest:
        site_id = SiteId(_request.get_ascii_input_mandatory("site_id"))
        verify_remote_site_config(site_id)

        return ReceiveConfigSyncRequest(
            site_id,
            _request.uploaded_file("sync_archive")[2],
            ast.literal_eval(_request.get_str_input_mandatory("to_delete")),
            _request.get_integer_input_mandatory("config_generation"),
        )

    def execute(self, api_request: ReceiveConfigSyncRequest) -> bool:
        with store.lock_checkmk_configuration():
            if api_request.config_generation != _get_current_config_generation():
                raise MKGeneralException(
                    _(
                        "The configuration was changed during activation. "
                        "Terminating this activation to ensure configuration integrity. "
                        "Please try again."
                    )
                )

            logger.debug("Updating configuration from sync snapshot")
            self._update_config_on_remote_site(api_request.sync_archive, api_request.to_delete)

            logger.debug("Executing post sync actions")
            _execute_post_config_sync_actions(api_request.site_id)

            logger.debug("Done")
            return True

    def _update_config_on_remote_site(self, sync_archive: bytes, to_delete: list[str]) -> None:
        """Use the given tar archive and list of files to be deleted to update the local files"""
        base_dir = cmk.utils.paths.omd_root
        base_folder_path = f"{cmk.utils.paths.check_mk_config_dir}/wato"

        default_sync_config = user_sync_default_config(omd_site())
        current_users = {}
        keep_local_users = False
        active_connectors = []
        if isinstance(default_sync_config, tuple) and default_sync_config[0] == "list":
            keep_local_users = True
            current_users = load_users()
            active_connectors = default_sync_config[1]

        try:
            # to_delete should not include any files mentioned in the sync_archive
            for site_path in to_delete:
                site_file = base_dir.joinpath(site_path)
                try:
                    site_file.unlink()
                except FileNotFoundError:
                    # errno.ENOENT - File already removed. Fine
                    pass
                except NotADirectoryError:
                    # errno.ENOTDIR - dir with files was replaced by e.g. symlink
                    pass

                finally:
                    # Delete folder if empty
                    parent = os.path.dirname(site_file)
                    if (
                        parent.startswith(base_folder_path)  # It's below the base folder
                        and parent != base_folder_path  # It's not the base folder
                        and not os.listdir(parent)  # It's empty
                    ):
                        os.rmdir(parent)
            _unpack_sync_archive(sync_archive, base_dir)
        finally:
            if keep_local_users:
                _reintegrate_site_local_users(current_users, active_connectors)


def _reintegrate_site_local_users(old_users: Users, active_connectors: list[str]) -> None:
    """
    Fixes missing user files after a new snapshot got applied
    The remote site already ignores ~/var/check_mk/web folders which are only known
    to the remote site. Remaining files to fix:
    - contacts.mk  # written in save_users()
    - users.mk     # written in save_users()
    - auth.serials # written in save_users(), serial is taken from user_profile
    """

    # Only read the data of these updated users -> load_users_uncached
    # It would be a bad idea to exchange any loaded users in a running request
    new_users = load_users_uncached()

    local_site_users: Users = {}
    for username, settings in old_users.items():
        if username in new_users:
            # User is known in central site
            continue
        connector = settings.get("connector")
        if connector in (None, HtpasswdUserConnector.type()):
            # User has an incompatible connector type
            continue
        if connector in active_connectors:
            # This user is only known on the remote site, keep it
            local_site_users[username] = settings
    new_users.update(local_site_users)
    save_users(new_users, datetime.now())


@dataclass
class ActivationChange:
    id: str
    user_id: UserId
    action_name: str
    text: str
    time: float


@dataclass
class ActivationRestAPIResponseExtensions:
    activation_id: str
    sites: Sequence[SiteId]
    is_running: bool
    force_foreign_changes: bool
    time_started: float
    changes: Sequence[ActivationChange]


def get_activation_ids() -> list[str]:
    """
    Returns:
        A list of activation ids found in the tmp activation directory
    """

    if os.path.exists(ACTIVATION_TMP_BASE_DIR):
        return os.listdir(ACTIVATION_TMP_BASE_DIR)
    return []


def load_activate_change_manager_with_id(activation_id: str) -> ActivateChangesManager:
    """Load activation from file and setattr on an ActivateChangeManager instance.

    Args:
        activation_id: A string id representing a recent activation.

    Returns:
        An ActivateChangesManager instance with the attributes of a recent activation.

    """
    manager = ActivateChangesManager()
    manager.load_activation(activation_id)
    return manager


def activation_attributes_for_rest_api_response(
    manager: ActivateChangesManager,
) -> ActivationRestAPIResponseExtensions:
    """Creates and returns an ActivationRestAPIResponseExtensions instance

    Args:
        manager: An instance of an ActivateChangesManager

    Returns:
        An ActivateRestAPIResponseExtensions instance.

    """
    return ActivationRestAPIResponseExtensions(
        activation_id=manager.activation_id,
        sites=manager.sites,
        is_running=manager.is_running(),
        force_foreign_changes=manager.activate_foreign,
        time_started=manager.time_started,
        changes=manager.persisted_changes,
    )


def get_restapi_response_for_activation_id(
    activation_id: str,
) -> ActivationRestAPIResponseExtensions:
    """Get the Rest API response for a given activation_id

    Args:
        activation_id: A string id representing a recent activation.

    Returns:
        An ActivationRestAPIResponseExtensions instance

    """
    return activation_attributes_for_rest_api_response(
        load_activate_change_manager_with_id(activation_id)
    )


def _raise_for_license_block() -> None:
    if block_effect := get_licensing_user_effect(
        licensing_settings_link=makeuri_contextless(
            _request, [("mode", "licensing")], filename="wato.py"
        ),
    ).block:
        raise MKLicensingError(block_effect.message_raw)


def activate_changes_start(
    sites: list[SiteId],
    source: ActivationSource,
    comment: str | None = None,
    force_foreign_changes: bool = False,
) -> ActivationRestAPIResponseExtensions:
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
        An ActivationRestAPIResponseExtensions instance.

    """

    changes = ActivateChanges()
    changes.load()

    _raise_for_license_block()

    if changes.has_foreign_changes():
        if not user.may("wato.activateforeign"):
            raise MKAuthException(_("You are not allowed to activate changes of other users."))
        if not force_foreign_changes:
            raise MKAuthException(
                _(
                    "There are changes from other users and foreign changes are "
                    "not allowed in this API call."
                )
            )

    known_sites = enabled_sites().keys()
    for site in sites:
        if site not in known_sites:
            raise MKUserError(
                None, _("Unknown site %s") % escaping.escape_attribute(site), status=400
            )

    manager = ActivateChangesManager()
    manager.load()

    if manager.is_running():
        raise MKUserError(None, _("There is an activation already running."), status=423)

    if not manager.has_pending_changes():
        raise MKUserError(None, _("Currently there are no changes to activate."), status=422)

    if not sites:
        dirty_sites = manager.dirty_sites()
        if not dirty_sites:
            raise MKUserError(None, _("Currently there are no changes to activate."), status=422)

        sites = manager.filter_not_activatable_sites(dirty_sites)
        if not sites:
            raise MKUserError(
                None,
                _(
                    "There are changes to activate, but no site can be "
                    "activated (The sites %s have changes, but may be "
                    "offline or not logged in)."
                )
                % ", ".join([site_id for site_id, _site in dirty_sites]),
                status=409,
            )

    manager.start(sites, comment=comment, activate_foreign=force_foreign_changes, source=source)
    return activation_attributes_for_rest_api_response(manager)


def activate_changes_wait(
    activation_id: ActivationId, timeout: float | int | None = None
) -> ActivationState | None:
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
    manager.load_activation(activation_id)
    if manager.wait_for_completion(timeout=timeout):
        return manager.get_state()
    return None
