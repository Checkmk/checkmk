#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="comparison-overlap"
# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="unreachable"
# mypy: disable-error-code="possibly-undefined"
# mypy: disable-error-code="redundant-expr"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

"""Manage configuration activation of Checkmk"""

from __future__ import annotations

import ast
import hashlib
import io
import logging
import os
import re
import shutil
import subprocess
import time
import traceback
from collections import Counter
from collections.abc import (
    Callable,
    Collection,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
)
from contextlib import contextmanager, suppress
from dataclasses import asdict, dataclass
from datetime import datetime
from html import unescape
from itertools import filterfalse
from multiprocessing.pool import AsyncResult, ThreadPool
from pathlib import Path
from typing import Any, assert_never, Literal, NamedTuple, NotRequired, TypedDict
from urllib.parse import urlparse

from pydantic import BaseModel
from setproctitle import setthreadtitle

from livestatus import BrokerConnections, SiteConfiguration, SiteConfigurations

import cmk.bi.filesystem
import cmk.ec.export as ec  # astrein: disable=cmk-module-layer-violation
import cmk.gui.utils
import cmk.gui.watolib.automations
import cmk.gui.watolib.git
import cmk.gui.watolib.sidebar_reload
import cmk.gui.watolib.utils
from cmk import mkp_tool, trace
from cmk.ccc import store, version
from cmk.ccc.archive import CheckmkTarArchive
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.crypto.certificate import PersistedCertificateWithPrivateKey
from cmk.discover_plugins import addons_plugins_local_path, plugins_local_path
from cmk.gui import hooks, userdb
from cmk.gui.background_job import (
    BackgroundJob,
    BackgroundProcessInterface,
    InitialStatusArgs,
    JobStatusSpec,
    JobTarget,
)
from cmk.gui.config import active_config, Config
from cmk.gui.crash_handler import crash_dump_message, handle_exception_as_gui_crash_report
from cmk.gui.exceptions import MKAuthException, MKInternalError, MKUserError
from cmk.gui.http import Request
from cmk.gui.http import request as _request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.nodevis.utils import topology_dir
from cmk.gui.permissions import permission_registry
from cmk.gui.site_config import (
    is_distributed_setup_remote_site,
    is_single_local_site,
    site_is_local,
)
from cmk.gui.sites import SiteStatus
from cmk.gui.sites import states as sites_states
from cmk.gui.type_defs import GlobalSettings, Users
from cmk.gui.user_sites import activation_sites
from cmk.gui.userdb import get_user_attributes, load_users, user_sync_default_config, UserAttribute
from cmk.gui.userdb.htpasswd import HtpasswdUserConnector
from cmk.gui.userdb.store import load_users_uncached, save_users
from cmk.gui.utils import escaping
from cmk.gui.utils.ntop import is_ntop_configured
from cmk.gui.utils.request_context import copy_request_context
from cmk.gui.utils.roles import (
    UserPermissions,
    UserPermissionSerializableConfig,
)
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.watolib import backup_snapshots
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    make_automation_config,
    remote_automation_config_from_site_config,
)
from cmk.gui.watolib.broker_certificates import (
    broker_certificate_sync_registry,
    BrokerCertificateSync,
    clean_remote_sites_certs,
)
from cmk.gui.watolib.broker_connections import BrokerConnectionsConfigFile
from cmk.gui.watolib.config_domain_name import (
    ConfigDomainName,
    DomainRequests,
    get_always_activate_domains,
    get_config_domain,
    SerializedSettings,
)
from cmk.gui.watolib.config_domain_name import OMD as OMDDomainName
from cmk.gui.watolib.config_sync import (
    create_rabbitmq_new_definitions_file,
    replication_path_registry,
    ReplicationPath,
    ReplicationPathRegistry,
    ReplicationPathType,
    SnapshotSettings,
)
from cmk.gui.watolib.global_settings import load_configuration_settings
from cmk.gui.watolib.hosts_and_folders import (
    collect_all_hosts,
    folder_preserving_link,
    folder_tree,
    FolderTree,
    validate_all_hosts,
)
from cmk.gui.watolib.paths import wato_var_dir
from cmk.gui.watolib.piggyback_hub import has_piggyback_hub_relevant_changes
from cmk.gui.watolib.site_changes import ChangeSpec, SiteChanges
from cmk.gui.watolib.snapshots import SnapshotManager
from cmk.messaging import rabbitmq
from cmk.utils import agent_registration, paths, render, setup_search_index
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.utils.licensing.export import LicenseUsageExtensions
from cmk.utils.licensing.registry import get_licensing_user_effect, is_free
from cmk.utils.licensing.usage import save_extensions
from cmk.utils.paths import configuration_lockfile
from cmk.utils.visuals import invalidate_visuals_cache

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
ACTIVATION_PERISTED_DIR = str(cmk.utils.paths.var_dir / "wato/activation")

var_dir = cmk.utils.paths.var_dir / "wato"


GENERAL_DIR_EXCLUDE = "__pycache__"

ConfigWarnings = dict[ConfigDomainName, list[str]]
ActivationId = str
SiteActivationState = dict[str, Any]
ActivationState = dict[str, SiteActivationState]
FileFilterFunc = Callable[[str], bool] | None
ActivationSource = Literal["GUI", "REST API", "INTERNAL"]

tracer = trace.get_tracer()


class SiteReplicationStatus(TypedDict, total=False):
    last_activation: ActivationId | None
    current_activation: ActivationId | None
    current_source: ActivationSource | None
    current_user_id: UserId | None
    times: dict[str, float]


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


def register(replication_path_registry_: ReplicationPathRegistry) -> None:
    for repl_path in [
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="check_mk",
            site_path=os.path.relpath(
                str(cmk.gui.watolib.utils.wato_root_dir()), cmk.utils.paths.omd_root
            ),
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="multisite",
            site_path=os.path.relpath(
                str(cmk.gui.watolib.utils.multisite_dir()), cmk.utils.paths.omd_root
            ),
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="htpasswd",
            site_path=os.path.relpath(str(cmk.utils.paths.htpasswd_file), cmk.utils.paths.omd_root),
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="password_store.secret",
            site_path=os.path.relpath(
                cmk.utils.paths.password_store_secret_file, cmk.utils.paths.omd_root
            ),
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="auth.serials",
            site_path=os.path.relpath(
                str(cmk.utils.paths.htpasswd_file.with_name("auth.serials")),
                cmk.utils.paths.omd_root,
            ),
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="stored_passwords",
            site_path=os.path.relpath(
                str(cmk.utils.paths.var_dir / "stored_passwords"), cmk.utils.paths.omd_root
            ),
        ),
        # Also replicate the user-settings of Multisite? While the replication
        # as such works pretty well, the count of pending changes will not
        # know.
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="usersettings",
            site_path=os.path.relpath(
                str(cmk.utils.paths.var_dir / "web"), cmk.utils.paths.omd_root
            ),
            excludes_exact_match=["last_login.mk", "report-thumbnails", "session_info.mk"],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkps",
            site_path=os.path.relpath(
                str(cmk.utils.paths.var_dir / "packages"), cmk.utils.paths.omd_root
            ),
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="mkps_disabled",
            site_path=os.path.relpath(
                cmk.utils.paths.disabled_packages_dir, cmk.utils.paths.omd_root
            ),
        ),
        ReplicationPath.make(  # add this explicitly, it is *not* below `local` despite the name.
            ty=ReplicationPathType.DIR,
            ident="mkps_avail",
            site_path=os.path.relpath(
                cmk.utils.paths.local_optional_packages_dir, cmk.utils.paths.omd_root
            ),
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="local",
            site_path="local",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.FILE,
            ident="distributed_wato",
            site_path="etc/check_mk/conf.d/distributed_wato.mk",
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="omd",
            site_path="etc/omd",
            excludes_exact_match=["site.conf", "instance_id"],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="rabbitmq",
            site_path=rabbitmq.DEFINITIONS_PATH,
            excludes_exact_match=[
                rabbitmq.DEFAULT_DEFINITIONS_FILE_NAME,
                rabbitmq.ACTIVE_DEFINITIONS_FILE_NAME,
            ],
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="frozen_aggregations",
            site_path=os.path.relpath(
                cmk.bi.filesystem.get_default_site_filesystem().var.frozen_aggregations,
                cmk.utils.paths.omd_root,
            ),
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="topology",
            site_path=os.path.relpath(topology_dir, cmk.utils.paths.omd_root),
        ),
        ReplicationPath.make(
            ty=ReplicationPathType.DIR,
            ident="apache_proccess_tuning",
            site_path="etc/check_mk/apache.d/wato",
        ),
    ]:
        replication_path_registry.register(repl_path)


# If the site is not up-to-date, synchronize it first.
def sync_changes_before_remote_automation(site_id: SiteId, debug: bool) -> None:
    manager = ActivateChangesManager()
    # TODO: So far we used active_config.sites. Would it be enough to use [site_id]?
    manager.changes.load(list(active_config.sites))

    if not manager.changes.is_sync_needed(site_id, active_config.sites[site_id]):
        return

    logger.info("Syncing %s", site_id)

    manager.start(
        sites=[site_id],
        activate_foreign=True,
        prevent_activate=True,
        source="INTERNAL",
        all_site_configs=active_config.sites,
        user_permission_config=UserPermissionSerializableConfig.from_global_config(active_config),
        max_snapshots=active_config.wato_max_snapshots,
        use_git=active_config.wato_use_git,
        debug=debug,
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


def _load_site_replication_status(site_id: SiteId, lock: bool = False) -> SiteReplicationStatus:
    return store.load_object_from_file(
        _site_replication_status_path(site_id),
        default={},
        lock=lock,
    )


def _save_site_replication_status(site_id: SiteId, repl_status: SiteReplicationStatus) -> None:
    store.save_object_to_file(
        _site_replication_status_path(site_id), repl_status, pprint_value=False
    )


def _update_replication_status(site_id: SiteId, vars_: SiteReplicationStatus) -> None:
    """Updates one or more dict elements of a site in an atomic way."""
    var_dir.mkdir(mode=0o770, exist_ok=True)

    repl_status = _load_site_replication_status(site_id, lock=True)
    try:
        repl_status.setdefault("times", {})
        repl_status.update(vars_)
    finally:
        _save_site_replication_status(site_id, repl_status)


def clear_site_replication_status(site_id: SiteId) -> None:
    try:
        _site_replication_status_path(site_id).unlink()
    except FileNotFoundError:
        pass  # Not existant -> OK

    ActivateChanges.confirm_site_changes(site_id)


def _site_replication_status_path(site_id: SiteId) -> Path:
    return var_dir / f"replication_status_{site_id}.mk"


@dataclass
class PendingChangesInfo:
    number: int
    message: str | None

    def has_changes(self) -> bool:
        return self.number > 0

    @property
    def readable_number(self) -> str | int:
        if self.number > 10:
            return "10+"

        return self.number

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


def get_activation_times(site_id: SiteId) -> dict[str, float]:
    repl_status = _load_site_replication_status(site_id)
    return repl_status.get("times", {})


def _mark_queued(site_activation_state: SiteActivationState) -> None:
    _set_result(site_activation_state, PHASE_QUEUED, _("Queued"))


def _mark_running(site_activation_state: SiteActivationState) -> None:
    _set_result(site_activation_state, PHASE_STARTED, _("Started"))


def _is_currently_activating(site_rep_status: SiteReplicationStatus) -> bool:
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
        assert isinstance(time_started, int | float)
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
    exc_logger: logging.Logger, exception: Exception, site_activation_status: SiteActivationState
) -> None:
    if isinstance(exception, MKGeneralException | MKUserError):
        exc_logger.exception("error activating changes")
        message = str(exception)
    else:
        crash = handle_exception_as_gui_crash_report(fail_silently=True)
        message = crash_dump_message(crash, user.may("general.see_crash_reports"))
    # The text of following exception will be rendered in the GUI and the error message may
    # contain some remotely-fetched data (including HTML) so we are escaping it to avoid
    # executing arbitrary HTML code.
    # The escape function does not escape some simple tags used for formatting.
    # SUP-9840
    escaped_details = escaping.escape_text(message)
    _set_result(
        site_activation_status,
        PHASE_DONE,
        _("Failed"),
        escaped_details,
        state=STATE_ERROR,
    )


def _load_expected_duration(
    site_id: SiteId, site_config: SiteConfiguration, activate_changes: ActivateChanges
) -> float:
    times = get_activation_times(site_id)
    duration = 0.0

    if activate_changes.is_sync_needed(site_id, site_config):
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
        site_activation_state, PHASE_SYNC, _("Synchronizing"), status_details=status_details
    )


def _get_config_sync_state(
    automation_config: RemoteAutomationConfig,
    replication_paths: Sequence[ReplicationPath],
    *,
    debug: bool,
) -> tuple[ConfigSyncFileInfos, int]:
    """Get the config file states from the remote sites

    Calls the automation call "get-config-sync-state" on the remote site,
    which is handled by AutomationGetConfigSyncState."""
    response = cmk.gui.watolib.automations.do_remote_automation(
        automation_config,
        "get-config-sync-state",
        [("replication_paths", repr([r.serialize() for r in replication_paths]))],
        debug=debug,
    )

    assert isinstance(response, tuple)
    return {k: ConfigSyncFileInfo(*v) for k, v in response[0].items()}, response[1]


def _synchronize_files(
    site_id: SiteId,
    automation_config: RemoteAutomationConfig,
    files_to_sync: list[str],
    files_to_delete: list[str],
    remote_config_generation: int,
    site_config_dir: Path,
    *,
    debug: bool,
) -> None:
    """Pack the files in a simple tar archive and send it to the remote site

    We build a simple tar archive containing all files to be synchronized.  The list of file to
    be deleted and the current config generation is handed over using dedicated HTTP parameters.
    """

    sync_archive = _get_sync_archive(files_to_sync, site_config_dir)

    response = cmk.gui.watolib.automations.do_remote_automation(
        automation_config,
        "receive-config-sync",
        [
            ("site_id", site_id),
            ("to_delete", repr(files_to_delete)),
            ("config_generation", "%d" % remote_config_generation),
        ],
        files={"sync_archive": io.BytesIO(sync_archive)},
        debug=debug,
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
    origin_span: trace.Span,
    automation_config: RemoteAutomationConfig,
    debug: bool,
) -> tuple[SyncState, SiteActivationState, float] | None:
    site_id = site_activation_state["_site_id"]
    site_logger = logger.getChild(f"site[{site_id}]")
    with tracer.span(
        f"fetch_sync_state[{site_id}]",
        context=trace.set_span_in_context(origin_span),
    ):
        sync_start = time.time()
        try:
            _set_sync_state(site_activation_state)

            _set_sync_state(site_activation_state, _("Fetching sync state"))
            site_logger.debug("Starting config sync (%r)", site_activation_state)

            remote_file_infos, remote_config_generation = _get_config_sync_state(
                automation_config,
                replication_paths,
                debug=debug,
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
            _handle_activation_changes_exception(site_logger, e, site_activation_state)
            return None


def calc_sync_delta(
    sync_state: SyncState,
    file_sync_enabled: bool,
    file_filter_func: FileFilterFunc,
    site_activation_state: SiteActivationState,
    sync_start: float,
    origin_span: trace.Span,
) -> tuple[SyncDelta, SiteActivationState, float] | None:
    site_id = site_activation_state["_site_id"]
    site_logger = logger.getChild(f"site[{site_id}]")
    with tracer.span(
        f"calc_sync_delta[{site_id}]",
        context=trace.set_span_in_context(origin_span),
    ):
        try:
            _set_sync_state(site_activation_state, _("Computing differences"))

            sync_delta = get_file_names_to_sync(
                site_logger,
                sync_state,
                file_sync_enabled,
                file_filter_func,
            )

            site_logger.debug("New files to be synchronized: %r", sync_delta.to_sync_new)
            site_logger.debug("Changed files to be synchronized: %r", sync_delta.to_sync_changed)
            site_logger.debug("Obsolete files to be deleted: %r", sync_delta.to_delete)

            return sync_delta, site_activation_state, sync_start
        except Exception as e:
            duration = time.time() - sync_start
            update_activation_time(site_id, ACTIVATION_TIME_SYNC, duration)
            _handle_activation_changes_exception(site_logger, e, site_activation_state)
            return None


def synchronize_files(
    sync_delta: SyncDelta,
    remote_config_generation: int,
    site_config_dir: Path,
    site_activation_state: SiteActivationState,
    sync_start: float,
    origin_span: trace.Span,
    automation_config: RemoteAutomationConfig,
    debug: bool,
) -> SiteActivationState | None:
    site_id = site_activation_state["_site_id"]
    site_logger = logger.getChild(f"site[{site_id}]")

    with tracer.span(
        f"synchronize_files[{site_id}]",
        context=trace.set_span_in_context(origin_span),
    ):
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
                automation_config,
                sync_delta.to_sync_new + sync_delta.to_sync_changed,
                sync_delta.to_delete,
                remote_config_generation,
                site_config_dir,
                debug=debug,
            )
            site_logger.debug("Finished config sync")
            return site_activation_state
        except Exception as e:
            _handle_activation_changes_exception(site_logger, e, site_activation_state)
            return None
        finally:
            duration = time.time() - sync_start
            update_activation_time(site_id, ACTIVATION_TIME_SYNC, duration)


def _set_done_result(
    configuration_warnings: ConfigWarnings, site_activation_state: SiteActivationState
) -> None:
    if any(configuration_warnings.values()):
        details = _render_warnings(configuration_warnings)
        _set_result(site_activation_state, PHASE_DONE, _("Activated"), details, state=STATE_WARNING)
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


def _get_domains_needing_activation(
    site_changes_activate_until: Sequence[ChangeSpec],
) -> DomainRequests:
    domain_settings: dict[ConfigDomainName, list[SerializedSettings]] = {}
    omd_domain_setting_changes: list[SerializedSettings] = []
    for change in site_changes_activate_until:
        if change["need_restart"]:
            for domain_name in change["domains"]:
                settings = get_config_domain(domain_name).get_domain_settings(change)
                # ConfigDomainOMD needs a restart of the apache,
                # make sure it's executed at the end
                if domain_name == OMDDomainName:
                    omd_domain_setting_changes.append(settings)
                    continue
                domain_settings.setdefault(domain_name, []).append(settings)

    domain_requests = sorted(
        (
            get_config_domain(domain_name).get_domain_request(settings_list)
            for (domain_name, settings_list) in domain_settings.items()
        ),
        key=lambda x: x.name,
    )

    if omd_domain_setting_changes:
        domain_requests.append(
            get_config_domain(OMDDomainName).get_domain_request(omd_domain_setting_changes)
        )

    return domain_requests


def _get_omd_domain_background_job_result(
    automation_config: RemoteAutomationConfig,
    *,
    debug: bool,
) -> Sequence[str]:
    """
    OMD domain needs restart of the whole site so the apache connection gets lost.
    A background job is started and we have to wait for the result
    """
    while True:
        try:
            raw_omd_response = cmk.gui.watolib.automations.do_remote_automation(
                automation_config,
                "checkmk-remote-automation-get-status",
                [("request", repr("omd-config-change"))],
                debug=debug,
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
    site_id: SiteId,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    site_changes_activate_until: Sequence[ChangeSpec],
    *,
    debug: bool,
    is_remote_site: bool,
) -> ConfigWarnings:
    domain_requests = _get_domains_needing_activation(site_changes_activate_until)

    if isinstance(automation_config, LocalAutomationConfig):
        return execute_activate_changes(domain_requests, is_remote_site=is_remote_site)

    serialized_requests = list(asdict(x) for x in domain_requests)
    try:
        response = cmk.gui.watolib.automations.do_remote_automation(
            automation_config,
            "activate-changes",
            [("domains", repr(serialized_requests)), ("site_id", site_id)],
            debug=debug,
        )
    except cmk.gui.watolib.automations.MKAutomationException as e:
        if "Invalid automation command: activate-changes" in "%s" % e:
            raise MKGeneralException(
                "Activate changes failed (%s). The version of this site may be too old."
            )
        raise

    # If request.settings is empty no `omd-config-change` job is started
    assert isinstance(response, dict)
    if any(request.name == OMDDomainName and request.settings for request in domain_requests):
        response.setdefault(OMDDomainName, []).extend(
            _get_omd_domain_background_job_result(automation_config, debug=debug)
        )

    return response


def _do_activate(
    site_id: SiteId,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    site_changes_activate_until: Sequence[ChangeSpec],
    site_activation_state: SiteActivationState,
    *,
    debug: bool,
    is_remote_site: bool,
) -> ConfigWarnings:
    _set_result(site_activation_state, PHASE_ACTIVATE, _("Activating"))

    start = time.time()

    configuration_warnings = _call_activate_changes_automation(
        site_id,
        automation_config,
        site_changes_activate_until,
        debug=debug,
        is_remote_site=is_remote_site,
    )

    duration = time.time() - start
    update_activation_time(site_id, ACTIVATION_TIME_RESTART, duration)
    return configuration_warnings


def activate_site_changes(
    activate_changes: ActivateChanges,
    prevent_activate: bool,
    site_activation_state: SiteActivationState,
    origin_span: trace.Span,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    debug: bool,
    is_remote_site: bool,
) -> SiteActivationState | None:
    site_id = site_activation_state["_site_id"]
    site_logger = logger.getChild(f"site[{site_id}]")
    with tracer.span(
        f"activate_site_changes[{site_id}]",
        context=trace.set_span_in_context(origin_span),
    ):
        try:
            _set_result(site_activation_state, PHASE_FINISHING, _("Finalizing"))
            site_changes_activate_until = activate_changes.get_changes_to_activate(site_id)

            configuration_warnings = {}
            if prevent_activate:
                _confirm_synchronized_changes(site_id)
            else:
                if activate_changes.is_activate_needed_until(site_id):
                    configuration_warnings = _do_activate(
                        site_id,
                        automation_config,
                        site_changes_activate_until,
                        site_activation_state,
                        debug=debug,
                        is_remote_site=is_remote_site,
                    )
                _confirm_activated_changes(site_id, site_changes_activate_until)

            _set_done_result(configuration_warnings, site_activation_state)
            return site_activation_state
        except Exception as e:
            _handle_activation_changes_exception(site_logger, e, site_activation_state)
            return None


class ActivationSitesSummary(TypedDict):
    siteId: str
    siteName: str
    version: str
    changes: int
    onlineStatus: Literal[
        "online",
        "disabled",
        "down",
        "unreach",
        "dead",
        "waiting",
        "missing",
        "unknown",
    ]
    loggedIn: bool
    # We can't easily use the StatusPerSite dataclass instead of dict[str, Any] as the type for
    # lastActivationStatus because that causes a serialization error when converting to JSON
    # in the ajax_sidebar_get_sites_and_changes call.
    # TODO: Use either TypedDict or dataclass types all over to easily combine them, and
    #   share these types with the frontend with cmk-shared-typing: CMK-28459
    lastActivationStatus: NotRequired[dict[str, Any]]


class PendingChangesSummary(TypedDict):
    changeId: str
    changeText: str
    user: str
    time: float
    whichSites: list[str]


class ActivationChangesSummary(TypedDict):
    sites: list[ActivationSitesSummary]
    pendingChanges: list[PendingChangesSummary]


class ActivateChanges:
    def __init__(self) -> None:
        # Changes grouped by site
        self._changes_by_site: dict[SiteId, Sequence[ChangeSpec]] = {}

        # Changes grouped by site up until a specific activation id
        self._changes_by_site_until: dict[SiteId, list[ChangeSpec]] = {}

        # A list of changes ordered by time and grouped by the change.
        # Each change contains a list of affected sites.
        self._all_changes: list[tuple[str, ChangeSpec]] = []
        self._pending_changes: list[tuple[str, ChangeSpec]] = []
        super().__init__()

    def load(self, sites: Sequence[SiteId]) -> None:
        self._changes_by_site = {}

        active_changes: dict[str, ChangeSpec] = {}
        pending_changes: dict[str, ChangeSpec] = {}

        for site_id in sites:
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

    @staticmethod
    def confirm_site_changes(site_id: SiteId) -> None:
        SiteChanges(site_id).clear()
        cmk.gui.watolib.sidebar_reload.need_sidebar_reload()

    @staticmethod
    def get_number_of_pending_changes(
        sites: Sequence[SiteId], count_limit: int | None = None
    ) -> int:
        changes_counter = 0
        for site_id in sites:
            changes = SiteChanges(site_id).read()
            changes_counter += len(
                list(change for change in changes if not has_been_activated(change))
            )
            if count_limit is not None and changes_counter > count_limit:
                return changes_counter
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

    @staticmethod
    def get_pending_changes_info(
        sites: Sequence[SiteId], count_limit: int | None = None
    ) -> PendingChangesInfo:
        number_of_changes = ActivateChanges.get_number_of_pending_changes(
            sites, count_limit=count_limit
        )
        message = ActivateChanges._make_changes_message(number_of_changes)
        return PendingChangesInfo(number=number_of_changes, message=message)

    def discard_changes_forbidden(self, sites: Sequence[SiteId]) -> bool:
        for site_id in sites:
            for change in SiteChanges(site_id).read():
                if change.get("prevent_discard_changes", False):
                    return True
        return False

    def grouped_changes(self) -> list[tuple[str, ChangeSpec]]:
        return self._pending_changes

    def changes_of_site(self, site_id: SiteId) -> Sequence[ChangeSpec]:
        return self._changes_by_site[site_id]

    def dirty_and_active_activation_sites(
        self, sites: Mapping[SiteId, SiteConfiguration]
    ) -> list[SiteId]:
        """Returns the list of sites that should be used when activating all affected sites"""
        return self.filter_not_activatable_sites(self.dirty_sites(sites))

    def filter_not_activatable_sites(
        self, sites: list[tuple[SiteId, SiteConfiguration]]
    ) -> list[SiteId]:
        dirty = []
        for site_id, site in sites:
            status = get_status_for_site(site_id, site).get("state", "unknown")
            is_online = self.site_is_online(status)
            is_logged_in = self.site_is_logged_in(site_id, site)

            if is_online and is_logged_in:
                dirty.append(site_id)
        return dirty

    def dirty_sites(
        self, sites: Mapping[SiteId, SiteConfiguration]
    ) -> list[tuple[SiteId, SiteConfiguration]]:
        """Returns the list of sites that have changes (including offline sites)"""
        return [s for s in sites.items() if self.changes_of_site(s[0])]

    def site_is_logged_in(self, site_id: SiteId, site: SiteConfiguration) -> bool:
        return site_is_local(site) or "secret" in site

    def site_is_online(self, status: str) -> bool:
        return status in ["online", "disabled"]

    def site_has_foreign_changes(self, site_id: SiteId) -> bool:
        changes = self.changes_of_site(site_id)
        return bool([c for c in changes if is_foreign_change(c) and not has_been_activated(c)])

    def _is_sync_needed_specific_changes(
        self,
        site_id: SiteId,
        site_config: SiteConfiguration,
        changes_to_check: Sequence[ChangeSpec],
    ) -> bool:
        if site_is_local(site_config):
            return False

        return any(c["need_sync"] for c in changes_to_check)

    def is_sync_needed(self, site_id: SiteId, site_config: SiteConfiguration) -> bool:
        return self._is_sync_needed_specific_changes(
            site_id, site_config, self.changes_of_site(site_id)
        )

    def _is_activate_needed_specific_changes(self, changes_to_check: Sequence[ChangeSpec]) -> bool:
        return any(c["need_restart"] for c in changes_to_check)

    def is_activate_needed(self, site_id: SiteId) -> bool:
        return self._is_activate_needed_specific_changes(self.changes_of_site(site_id))

    def is_activate_needed_until(self, site_id: SiteId) -> bool:
        return self._is_activate_needed_specific_changes(self._changes_by_site_until[site_id])

    def last_activation_state(self, site_id: SiteId) -> SiteActivationState:
        """This function returns the last known persisted activation state"""
        return store.load_object_from_file(
            Path(ActivateChangesManager.persisted_site_state_path(site_id)), default={}
        )

    def get_last_change_id(self) -> str:
        return self._pending_changes[-1][1]["id"]

    def has_changes(self) -> bool:
        return bool(self._all_changes)

    @property
    def changes(self) -> list[tuple[str, ChangeSpec]]:
        return self._all_changes

    def has_pending_changes(self) -> bool:
        return bool(self._pending_changes)

    @property
    def pending_changes(self) -> list[tuple[str, ChangeSpec]]:
        return self._pending_changes

    def has_foreign_changes(self) -> bool:
        return any(
            change
            for _change_id, change in self._pending_changes
            if is_foreign_change(change) and not has_been_activated(change)
        )

    def has_foreign_changes_on_any_site(self, activation_site_ids: Sequence[SiteId]) -> bool:
        return any(
            change
            for _change_id, change in self._pending_changes
            if is_foreign_change(change)
            and not has_been_activated(change)
            and affects_all_sites(activation_site_ids, change)
        )

    def get_activation_time(self, site_id: SiteId, ty: str) -> float | None:
        return get_activation_times(site_id).get(ty)

    def get_changes_to_activate(self, site_id: SiteId) -> Sequence[ChangeSpec]:
        return self._changes_by_site_until[site_id]

    def get_all_data_required_for_activation_popout(
        self, sites: SiteConfigurations
    ) -> ActivationChangesSummary:
        self.load(list(activation_sites(sites)))

        def _get_site_version(site_id: SiteId) -> str:
            site_status = get_status_for_site(site_id, sites[site_id])
            site_version = (
                site_status.get("livestatus_version", "") if not site_status.get("disabled") else ""
            )
            if site_version and "-" in site_version:
                site_version = site_version.split("-", 1)[0]
            return site_version

        def _get_last_activation_status(site_id: SiteId) -> StatusPerSite | None:
            """Get the last persisted activation status for a site, if any"""
            last_state = self.last_activation_state(site_id)
            if last_state and "_state" in last_state and "_phase" in last_state:
                raw_status_details = last_state.get("_status_details")
                # Apply the same HTML stripping and unescaping as
                # in activation_attributes_for_rest_api_response:
                clean_status_details = (
                    re.sub(r"<.*?>", "", unescape(raw_status_details))
                    if raw_status_details is not None
                    else ""
                )

                return StatusPerSite(
                    site=site_id,
                    phase=last_state["_phase"],
                    state=last_state["_state"],
                    status_text=last_state.get("_status_text", ""),
                    status_details=clean_status_details,
                    start_time=last_state.get("_time_started", 0),
                    end_time=last_state.get("_time_ended", 0),
                )
            return None

        def _build_site_summary(site_id: SiteId, site: SiteConfiguration) -> ActivationSitesSummary:
            base_summary = ActivationSitesSummary(
                siteId=site["id"],
                siteName=site["alias"],
                version=_get_site_version(site_id),
                changes=0
                if site["id"] not in site_change_counter
                else site_change_counter[site["id"]],
                onlineStatus=get_status_for_site(site_id, site).get("state", "unknown"),
                loggedIn=self.site_is_logged_in(site_id, site),
            )
            if last_status := _get_last_activation_status(site_id):
                base_summary["lastActivationStatus"] = asdict(last_status)
            return base_summary

        site_change_counter: Counter = Counter()
        pending_changes: list[PendingChangesSummary] = []
        for _changeid, change in self._all_changes:
            if not has_been_activated(change):
                for site in change["affected_sites"]:
                    site_change_counter[site] += 1

                pending_changes.append(
                    PendingChangesSummary(
                        changeId=change["id"],
                        changeText=unescape(change["text"]),
                        user=change["user_id"],
                        time=change["time"],
                        whichSites=["All sites"]
                        if affects_all_sites(list(activation_sites(sites)), change)
                        else change["affected_sites"],
                    )
                )

        return ActivationChangesSummary(
            sites=[
                _build_site_summary(site_id, site)
                for site_id, site in activation_sites(sites).items()
            ],
            pendingChanges=pending_changes,
        )


def has_been_activated(change: ChangeSpec) -> bool:
    return change.get("has_been_activated", False)


def prevent_discard_changes(change: ChangeSpec) -> bool:
    return change.get("prevent_discard_changes", False)


def is_foreign_change(change: ChangeSpec) -> bool:
    return change["user_id"] and change["user_id"] != user.id


def affects_all_sites(sites: Sequence[SiteId], change: ChangeSpec) -> bool:
    return not set(change["affected_sites"]).symmetric_difference(set(sites))


def _add_peer_to_peer_connections(
    replicated_sites_configs: Mapping[SiteId, SiteConfiguration],
    connection_info: list[rabbitmq.Connection],
    peer_to_peer_connections: BrokerConnections,
) -> None:
    for _connection_id, connection in peer_to_peer_connections.items():
        source_site = connection.connecter.site_id
        destination_site = connection.connectee.site_id

        connection_info.append(
            rabbitmq.Connection(
                connectee=rabbitmq.Connectee(
                    site_id=destination_site,
                    site_server=urlparse(
                        replicated_sites_configs[destination_site]["multisiteurl"]
                    ).hostname
                    or "",
                    rabbitmq_port=replicated_sites_configs[destination_site].get(
                        "message_broker_port", 5672
                    ),
                ),
                connecter=rabbitmq.Connecter(
                    site_id=source_site,
                ),
            )
        )


def get_all_replicated_sites(
    activation_site_configs: SiteConfigurations,
) -> Mapping[SiteId, SiteConfiguration]:
    return {
        site_id: site_config
        for site_id, site_config in activation_site_configs.items()
        if site_config.get("replication")
    }


def default_rabbitmq_definitions(
    replicated_sites_configs: Mapping[SiteId, SiteConfiguration],
    peer_to_peer_connections: BrokerConnections,
) -> Mapping[str, rabbitmq.Definitions]:
    connection_info = [
        rabbitmq.Connection(
            connectee=rabbitmq.Connectee(
                site_id=site_id,
                site_server=urlparse(site_config["multisiteurl"]).hostname or "",
                rabbitmq_port=site_config.get("message_broker_port", 5672),
            ),
            connecter=rabbitmq.Connecter(
                site_id=omd_site(),
            ),
        )
        for site_id, site_config in replicated_sites_configs.items()
    ]

    _add_peer_to_peer_connections(
        replicated_sites_configs, connection_info, peer_to_peer_connections
    )
    return rabbitmq.compute_distributed_definitions(connection_info)


@contextmanager
def _debug_log_message(msg: str) -> Iterator[None]:
    logger.debug(msg)
    start = time.time()
    yield
    logger.debug(f"{msg} ... done (%ss)", round(time.time() - start, 2))


class ActivateChangesManager:
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
        self.changes = ActivateChanges()
        self._sites: Sequence[SiteId] = []
        self._site_snapshot_settings: dict[SiteId, SnapshotSettings] = {}
        self._activate_until: str | None = None
        self._comment: str | None = None
        self._activate_foreign = False
        self._activation_id: str | None = None
        self._time_started = 0.0
        self._prevent_activate = False
        self._persisted_changes: list[dict[str, Any]] = []

        Path(ACTIVATION_PERISTED_DIR).mkdir(mode=0o770, parents=True, exist_ok=True)
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
    @tracer.instrument("activate_changes")
    def start(
        self,
        sites: Sequence[SiteId],
        source: ActivationSource,
        *,
        all_site_configs: SiteConfigurations,
        user_permission_config: UserPermissionSerializableConfig,
        max_snapshots: int,
        use_git: bool,
        debug: bool,
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

        self._verify_requested_sites(sites, list(activation_sites(all_site_configs)))
        self._sites = sites

        self._source = source
        self._activation_id = self._new_activation_id()
        trace.get_current_span().set_attribute("cmk.activate.id", self._activation_id)

        activation_features = activation_features_registry[str(version.edition(paths.omd_root))]

        with _debug_log_message("Compute rabbitmq definitions"):
            rabbitmq_definitions = activation_features.get_rabbitmq_definitions(
                get_all_replicated_sites(activation_sites(all_site_configs)),
                BrokerConnectionsConfigFile().load_for_reading(),
            )

        with _debug_log_message("Preparing site snapshot settings"):
            self._site_snapshot_settings = self._get_site_snapshot_settings(
                self._activation_id,
                {site_id: all_site_configs[site_id] for site_id in self._sites},
                rabbitmq_definitions,
            )
        self._activate_until = (
            self.changes.get_last_change_id() if activate_until is None else activate_until
        )
        self._comment = comment
        self._time_started = time.time()
        self._prevent_activate = prevent_activate
        self._set_persisted_changes()

        with _debug_log_message("Verifying host config"):
            self._verify_valid_host_config(tree := folder_tree())
        self._save_activation()

        with _debug_log_message("Calling pre-activate changes"):
            self._pre_activate_changes(debug=debug)

        with _debug_log_message("Creating snapshots"):
            self._create_snapshots(
                activation_features.snapshot_manager_factory,
                max_snapshots=max_snapshots,
                debug=debug,
                use_git=use_git,
            )
        self._save_activation()

        with _debug_log_message("Starting activation"):
            self._start_activation(
                all_site_configs, user_permission_config, debug=debug, use_git=use_git
            )

        with _debug_log_message("Update and activate central rabbitmq changes"):
            create_rabbitmq_new_definitions_file(paths.omd_root, rabbitmq_definitions[omd_site()])
            rabbitmq.update_and_activate_rabbitmq_definitions(paths.omd_root, logger)

        # rabbitmq must be running on the central site if one of the remote sites
        # has piggyback-hub running
        if rabbitmq.rabbitmqctl_running() and has_piggyback_hub_relevant_changes(
            [change for _, change in self.changes.pending_changes]
        ):
            with (
                tracer.span("distribute_piggyback_hub_configs"),
                _debug_log_message("Starting piggyback hub config distribution"),
            ):
                activation_features.distribute_piggyback_hub_configs(
                    load_configuration_settings(),
                    all_site_configs,
                    {
                        site_id
                        for site_id, _site_config in self.changes.dirty_sites(
                            activation_sites(all_site_configs)
                        )
                    },
                    {
                        host_name: host.site_id()
                        for host_name, host in tree.root_folder().all_hosts_recursively().items()
                    },
                )

        return self._activation_id

    def _verify_valid_host_config(self, tree: FolderTree) -> None:
        defective_hosts = validate_all_hosts(tree, [], force_all=True)
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

    def activate_until(self) -> str | None:
        return self._activate_until

    def is_running(self) -> bool:
        if self._activation_id is None:
            # activation not initialized in ActivateChangesManager yet, not running
            return False

        if not ActivateChangesSchedulerBackgroundJob(self._activation_id).is_active():
            return False

        return bool(self.running_sites())

    def _activation_running(self, site_id: SiteId) -> bool:
        site_state = self.get_site_state(site_id)

        # The site_state file may be missing/empty, if the operation has started recently.
        # However, if the file is still missing after a considerable amount
        # of time, we consider this site activation as dead
        seconds_since_start = time.time() - self._time_started
        if site_state == {} and seconds_since_start > Request.request_timeout - 10:
            return False

        if site_state == {} or site_state["_phase"] == PHASE_INITIALIZED:
            # Just been initialized. Treat as running as it has not been
            # started and could not lock the site stat file yet.
            return True

        if site_state["_phase"] in PHASE_DONE:
            return False

        return True

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

    def _verify_requested_sites(
        self, requested_sites: Sequence[SiteId], activation_site_ids: Sequence[SiteId]
    ) -> None:
        for site_id in requested_sites:
            if site_id not in activation_site_ids:
                raise MKUserError("sites", _('The site "%s" does not exist.') % site_id)

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
        return f"{ACTIVATION_TMP_BASE_DIR}/{self._activation_id}/site_{site_id}_sync.tar.gz"

    def _load_activation_info(self, activation_id: str) -> dict[str, Any]:
        info_path = self._info_path(activation_id)
        if not os.path.exists(info_path):
            raise MKUserError(
                None,
                f"Unknown activation process: {activation_id!r} not found",
            )
        return store.load_object_from_file(Path(info_path), default={})

    def _set_persisted_changes(self) -> None:
        """Sets the persisted_changes, which are a subset of self._changes."""
        if not self._persisted_changes:
            for _activation_id, change in self.changes.pending_changes:
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

        Path(self._info_path(self._activation_id)).parent.mkdir(
            mode=0o770, parents=True, exist_ok=True
        )
        to_file = {key: getattr(self, key) for key in self.info_keys}
        store.save_object_to_file(Path(self._info_path(self._activation_id)), to_file)

    # Give hooks chance to do some pre-activation things (and maybe stop
    # the activation)
    def _pre_activate_changes(self, *, debug: bool) -> None:
        try:
            if hooks.registered("pre-distribute-changes"):
                hooks.call("pre-distribute-changes", collect_all_hosts())
        except Exception as e:
            logger.exception("error calling pre-distribute-changes hook")
            if debug:
                raise
            raise MKUserError(None, _("Can not start activation: %s") % e)

    @tracer.instrument("create_snapshots")
    def _create_snapshots(
        self,
        snapshot_manager_factory: Callable[[str, dict[SiteId, SnapshotSettings]], SnapshotManager],
        *,
        max_snapshots: int,
        debug: bool,
        use_git: bool,
    ) -> None:
        """Creates the needed SyncSnapshots for each applicable site.

        Some conflict prevention is being done. This function checks for the presence of
        newer changes than the ones to be activated.

        """
        with store.lock_checkmk_configuration(configuration_lockfile):
            if not self.changes.pending_changes:
                raise MKUserError(None, _("Currently there are no changes to activate."))

            if self.changes.get_last_change_id() != self._activate_until:
                raise MKUserError(
                    None,
                    _(
                        "Another change has been made in the meantime. Please review it "
                        "to ensure you also want to activate it now and start the "
                        "activation again."
                    ),
                )

            if self._activation_id is None:
                raise Exception("activation ID is not set")

            with backup_snapshots.create_snapshot_in_concurrent_thread(
                comment=self._comment,
                created_by=user.id,
                secret=backup_snapshots.snapshot_secret(),
                max_snapshots=max_snapshots,
                use_git=use_git,
                debug=debug,
                parent_span_context=trace.get_current_span().get_span_context(),
            ) as future_backup_snapshot_creation:
                logger.debug("Start creating config sync snapshots")
                start = time.time()
                work_dir = os.path.join(ACTIVATION_TMP_BASE_DIR, self._activation_id)

                # Do not create a snapshot for the local site. All files are already in place
                site_snapshot_settings = self._site_snapshot_settings.copy()
                try:
                    del site_snapshot_settings[omd_site()]
                except KeyError:
                    pass

                snapshot_manager = snapshot_manager_factory(work_dir, site_snapshot_settings)
                snapshot_manager.generate_snapshots()
                logger.debug("Config sync snapshot creation took %.4f", time.time() - start)

                logger.debug("Waiting for backup snapshot creation to complete")

                if (
                    exception_in_backup_snapshot_creation
                    := future_backup_snapshot_creation.exception()
                ):
                    raise MKGeneralException(
                        "Failed to create backup snapshot"
                    ) from exception_in_backup_snapshot_creation

        logger.debug("Finished all snapshots")

    def _get_site_snapshot_settings(
        self,
        activation_id: ActivationId,
        site_configs: Mapping[SiteId, SiteConfiguration],
        rabbitmq_definitions: Mapping[str, rabbitmq.Definitions],
    ) -> dict[SiteId, SnapshotSettings]:
        snapshot_settings = {}

        for site_id, site_config in site_configs.items():
            self._check_snapshot_creation_permissions(site_id)

            work_dir = cmk.utils.paths.site_config_dir / activation_id / site_id

            snapshot_components = _get_replication_components(site_config)

            # Generate a quick reference_by_name for each component
            component_names = {c.ident for c in snapshot_components}

            snapshot_settings[site_id] = SnapshotSettings(
                snapshot_path=self._site_snapshot_file(site_id),
                work_dir=str(work_dir),
                snapshot_components=snapshot_components,
                component_names=component_names,
                site_config=site_config,
                rabbitmq_definition=rabbitmq_definitions[site_id],
            )

        return snapshot_settings

    def _check_snapshot_creation_permissions(self, site_id: SiteId) -> None:
        if self.changes.site_has_foreign_changes(site_id) and not self._activate_foreign:
            if not user.may("wato.activateforeign"):
                raise MKUserError(
                    None,
                    _(
                        "There are some changes made by your colleagues that you cannot "
                        "activate because you are not permitted to. You can only activate "
                        "your changes on the sites that are not affected by these changes. "
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
                    "have to confirm the activation or ask your colleagues to activate "
                    "these changes on their own."
                ),
            )

    @tracer.instrument("start_activation")
    def _start_activation(
        self,
        all_site_configs: SiteConfigurations,
        user_permission_config: UserPermissionSerializableConfig,
        *,
        debug: bool,
        use_git: bool,
    ) -> None:
        self._log_activation(use_git=use_git)
        assert self._activation_id is not None
        job = ActivateChangesSchedulerBackgroundJob(self._activation_id)
        result = job.start(
            JobTarget(
                callable=activate_changes_scheduler_job_entry_point,
                args=ActivateChangesSchedulerJobArgs(
                    activation_id=self._activation_id,
                    site_snapshot_settings=self._site_snapshot_settings,
                    prevent_activate=self._prevent_activate,
                    source=self._source,
                    all_site_configs=all_site_configs,
                    user_permission_config=user_permission_config,
                    debug=debug,
                    use_git=use_git,
                ),
            ),
            InitialStatusArgs(
                title=job.gui_title(),
                deletable=False,
                stoppable=False,
                user=str(user.id) if user.id else None,
            ),
        )
        if result.is_error():
            raise result.error

    def _log_activation(self, *, use_git: bool) -> None:
        log_msg = "Starting activation (Sites: %s)" % ",".join(self._sites)
        log_audit(
            action="activate-changes",
            message=log_msg,
            user_id=user.id,
            use_git=use_git,
        )

        if self._comment:
            log_audit(
                action="activate-changes",
                message="Comment: %s" % self._comment,
                user_id=user.id,
                use_git=use_git,
            )

    def get_state(self) -> ActivationState:
        return {"sites": {site_id: self.get_site_state(site_id) for site_id in self._sites}}  #

    def get_site_state(self, site_id: SiteId) -> SiteActivationState:
        if self._activation_id is None:
            raise Exception("activation ID is not set")
        return store.load_object_from_file(
            Path(ActivateChangesManager.site_state_path(self._activation_id, site_id)), default={}
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
    def site_filename(site_id: SiteId) -> str:
        return "site_%s.mk" % site_id


class ActivationCleanupJob:
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
        self.maximum_age = maximum_age

    def shall_start(self) -> bool:
        """Some basic preliminary check to decide quickly whether to start the job"""
        return bool(self._existing_activation_ids())

    def do_execute(self) -> None:
        """Cleanup non-running activation directories"""
        with store.lock_checkmk_configuration(configuration_lockfile):
            for activation_id in self._existing_activation_ids():
                logger.info("Check activation: %s", activation_id)
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
                        logger.debug("Is not running")
                except Exception as e:
                    logger.warning(
                        "  Failed to load activation (%s), trying to delete...", e, exc_info=True
                    )

                if not delete:
                    logger.info("  -> Keep (is running)")
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
                        logger.info("  -> Keep (not a directory)")
                        continue

                    # TODO:
                    #   This checks creation time, which is kind of silly. More interesting would be
                    #   to consider completion time.
                    dir_stat = os.stat(activation_dir)
                    if time.time() - dir_stat.st_mtime < self.maximum_age:
                        logger.info(
                            "  -> Keep (created %d seconds ago)", time.time() - dir_stat.st_mtime
                        )
                        continue

                    try:
                        logger.info("  -> Delete")
                        shutil.rmtree(activation_dir)
                    except Exception:
                        logger.error(
                            "  Failed to delete the activation directory '%s'",
                            activation_dir,
                            exc_info=True,
                        )

        logger.info("Activation cleanup finished")

    def _existing_activation_ids(self) -> list[str]:
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


def execute_activation_cleanup_job(config: Config) -> None:
    """This function is called by the GUI cron job once a minute.

    Errors are logged to var/log/web.log."""
    job = ActivationCleanupJob(maximum_age=60)

    if not job.shall_start():
        logger.debug("Job shall not start")
        return

    job.do_execute()


def _handle_distributed_sites_in_free(
    site_snapshot_settings: Mapping[SiteId, SnapshotSettings], time_started: float
) -> bool:
    distributed_sites_in_free = [
        site_id for site_id in site_snapshot_settings if site_id != omd_site()
    ]
    for start_site_id in distributed_sites_in_free:
        exc = MKUserError(None, get_free_message())
        _handle_activation_changes_exception(
            logger.getChild(f"site[{start_site_id}]"),
            exc,
            {"_site_id": start_site_id, "_time_started": time_started},
        )
    return any(distributed_sites_in_free)


def _initialize_site_activation_state(
    site_id: SiteId,
    site_config: SiteConfiguration,
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
        "_expected_duration": _load_expected_duration(site_id, site_config, activate_changes),
        "_pid": os.getpid(),
        "_user_id": user.id,
        "_source": source,
    }
    return site_activation_state


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
                inode_sync_states, replication_path_full, replication_path.is_excluded
            )
        else:
            raise NotImplementedError()

    return inode_sync_states


def _get_replication_dir_config_sync_file_infos_per_inode(
    inode_sync_states: MutableMapping[int, ConfigSyncFileInfo],
    replication_path: str,
    replication_path_excluder: Callable[[str], bool],
) -> None:
    # Use os functionality instead of pathlib since it is faster
    for root, dir_names, file_names in os.walk(replication_path):
        root_name = os.path.basename(root)
        if root_name == GENERAL_DIR_EXCLUDE or replication_path_excluder(root_name):
            continue

        for dir_name in dir_names:
            dir_path = os.path.join(root, dir_name)
            try:
                if os.path.islink(dir_path) and not dir_name == GENERAL_DIR_EXCLUDE:
                    inode_sync_states[os.stat(dir_path).st_ino] = _get_config_sync_file_info(
                        dir_path
                    )
            except FileNotFoundError:
                pass  # Ignore directories vanishing during processing

        for file_name in file_names:
            file_path = os.path.join(root, file_name)
            try:
                inode_sync_states[os.stat(file_path).st_ino] = _get_config_sync_file_info(file_path)
            except FileNotFoundError:
                pass  # Ignore files vanishing during processing


def _prepare_for_activation_tasks(
    activate_changes: ActivateChanges,
    activation_id: ActivationId,
    site_snapshot_settings: Mapping[SiteId, SnapshotSettings],
    time_started: float,
    source: ActivationSource,
    *,
    use_git: bool,
) -> tuple[Mapping[SiteId, ConfigSyncFileInfos], Mapping[SiteId, SiteActivationState]]:
    # All activations need to fail if the initialization failed
    initialization_failure: Exception | None = None
    try:
        config_sync_file_infos_per_inode = _get_config_sync_file_infos_per_inode(
            list(replication_path_registry.values())
        )
    except Exception as e:
        initialization_failure = e

    central_file_infos_per_site = {}
    site_activation_states_per_site = {}
    for site_id, snapshot_settings in sorted(site_snapshot_settings.items(), key=lambda e: e[0]):
        site_activation_state = _initialize_site_activation_state(
            site_id,
            snapshot_settings.site_config,
            activation_id,
            activate_changes,
            time_started,
            source,
        )
        try:
            if not _lock_activation(site_activation_state):
                continue

            if initialization_failure:
                raise initialization_failure

            _mark_running(site_activation_state)

            log_audit(
                action="activate-changes",
                message="Started activation of site %s" % site_id,
                user_id=user.id,
                use_git=use_git,
            )
            site_activation_states_per_site[site_id] = site_activation_state

            if activate_changes.is_sync_needed(site_id, snapshot_settings.site_config):
                central_file_infos_per_site[site_id] = _get_site_central_file_infos(
                    site_id, snapshot_settings, config_sync_file_infos_per_inode
                )
        except Exception as e:
            _handle_activation_changes_exception(
                logger.getChild(f"site[{site_id}]"), e, site_activation_state
            )
            _finalize_activation(site_id, activation_id, source)
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
    activate_site_changes: MutableMapping[SiteId, AsyncResult]


def _error_callback(error: BaseException) -> None:
    # for exceptions that could not be handled within the function, e.g. calling with incorrect
    # number of arguments
    logger.error(str(error))


@tracer.instrument("_sync_and_activate")
def _sync_and_activate(
    activation_id: str,
    site_snapshot_settings: Mapping[SiteId, SnapshotSettings],
    file_filter_func: FileFilterFunc,
    source: ActivationSource,
    all_site_configs: SiteConfigurations,
    *,
    debug: bool,
    prevent_activate: bool,
    use_git: bool,
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

        activate_changes = ActivateChanges()
        activate_changes.load(list(all_site_configs))
        activate_changes.load_changes_until(activation_id, site_snapshot_settings.keys())

        if is_free():
            if _handle_distributed_sites_in_free(site_snapshot_settings, time_started):
                return

        (site_central_file_infos, site_activation_states) = _prepare_for_activation_tasks(
            activate_changes,
            activation_id,
            site_snapshot_settings,
            time_started,
            source,
            use_git=use_git,
        )

        task_pool = ThreadPool(processes=len(site_snapshot_settings))

        site_activation_states = _create_broker_certificates_for_remote_sites(
            omd_site(),
            site_activation_states,
            site_snapshot_settings,
            task_pool,
            broker_certificate_sync_registry["broker_certificate_sync"],
            debug=debug,
        )
        clean_remote_sites_certs(
            kept_sites=list(get_all_replicated_sites(activation_sites(all_site_configs)))
        )

        active_tasks = ActiveTasks(
            fetch_sync_state={},
            calc_sync_delta={},
            synchronize_files={},
            activate_site_changes={},
        )

        automation_configs = {
            site_id: make_automation_config(settings.site_config)
            for site_id, settings in site_snapshot_settings.items()
        }

        for site_id, site_activation_state in site_activation_states.items():
            automation_config = automation_configs[site_id]

            if activate_changes.is_sync_needed(
                site_id, site_snapshot_settings[site_id].site_config
            ):
                assert isinstance(automation_config, RemoteAutomationConfig)
                async_result_fetch_sync_state = task_pool.apply_async(
                    func=copy_request_context(fetch_sync_state),
                    args=(
                        site_snapshot_settings[site_id].snapshot_components,
                        site_activation_state,
                        site_central_file_infos[site_id],
                        trace.get_current_span(),
                        automation_config,
                        debug,
                    ),
                    error_callback=_error_callback,
                )
                active_tasks["fetch_sync_state"][site_id] = async_result_fetch_sync_state
            else:
                async_result_activate_site_changes = task_pool.apply_async(
                    func=copy_request_context(activate_site_changes),
                    args=(
                        activate_changes,
                        prevent_activate,
                        site_activation_state,
                        trace.get_current_span(),
                        automation_config,
                        debug,
                        is_distributed_setup_remote_site(all_site_configs),
                    ),
                    error_callback=_error_callback,
                )
                active_tasks["activate_site_changes"][site_id] = async_result_activate_site_changes

        remote_config_generation_per_site: dict[SiteId, int] = {}
        # we want to mostly parallelize the activation steps, but if one site takes longer,
        # it should not hold up the other sites
        # -> monitor active tasks to handle results as soon as one finishes and start a task for
        # the next step
        while (
            len(active_tasks["fetch_sync_state"]) > 0
            or len(active_tasks["calc_sync_delta"]) > 0
            or len(active_tasks["synchronize_files"]) > 0
            or len(active_tasks["activate_site_changes"]) > 0
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
                automation_configs,
                debug=debug,
            )

    except Exception:
        handle_exception_as_gui_crash_report(fail_silently=True)
    finally:
        for activation_site_id in site_activation_states:
            _finalize_activation(activation_site_id, activation_id, source)


def create_broker_certificates(
    broker_cert_sync: BrokerCertificateSync,
    central_ca_bundle: PersistedCertificateWithPrivateKey,
    customer_ca_bundle: PersistedCertificateWithPrivateKey | None,
    settings: SiteConfiguration,
    site_activation_state: SiteActivationState,
    origin_span: trace.Span,
    debug: bool,
) -> SiteActivationState | None:
    site_id = site_activation_state["_site_id"]
    site_logger = logger.getChild(f"site[{site_id}]")

    with tracer.span(
        f"create_broker_certificates[{site_id}]",
        context=trace.set_span_in_context(origin_span),
    ):
        sync_start = time.time()
        try:
            _set_sync_state(site_activation_state, _("Syncing broker certificates"))
            broker_cert_sync.create_broker_certificates(
                remote_automation_config_from_site_config(settings),
                central_ca_bundle,
                customer_ca_bundle,
                debug=debug,
            )
            return site_activation_state
        except Exception as e:
            duration = time.time() - sync_start
            update_activation_time(site_id, ACTIVATION_TIME_SYNC, duration)
            _handle_activation_changes_exception(site_logger, e, site_activation_state)
            return None


def _create_broker_certificates_for_remote_sites(
    myself: SiteId,
    site_activation_states: Mapping[SiteId, SiteActivationState],
    site_snapshot_settings: Mapping[SiteId, SnapshotSettings],
    task_pool: ThreadPool,
    broker_sync: BrokerCertificateSync,
    *,
    debug: bool,
) -> Mapping[SiteId, SiteActivationState]:
    site_activation_states_certs_synced = dict(site_activation_states)

    if not (
        required_sites := broker_sync.get_site_to_sync(
            myself,
            [
                (site_id, settings.site_config)
                for site_id, settings in site_snapshot_settings.items()
            ],
        )
    ):
        return site_activation_states_certs_synced

    central_ca = broker_sync.load_central_ca()
    map_args = []
    for customer, sites in required_sites.items():
        customer_ca = broker_sync.load_or_create_customer_ca(customer)
        for site_id, settings in sites:
            map_args.append(
                (
                    broker_sync,
                    central_ca,
                    customer_ca,
                    settings,
                    site_activation_states[site_id],
                    trace.get_current_span(),
                    debug,
                )
            )
            site_activation_states_certs_synced.pop(site_id)

    logger.debug("Start pool broker certificates creation")
    for result in task_pool.starmap(
        copy_request_context(func=create_broker_certificates),
        map_args,
    ):
        if result is None:
            continue
        site_activation_states_certs_synced[result["_site_id"]] = result
    logger.debug("Broker certificates for remote sites created")

    broker_sync.update_trusted_cas()
    return site_activation_states_certs_synced


def _finalize_activation(
    site_id: SiteId, activation_id: ActivationId, source: ActivationSource
) -> None:
    _unlock_activation(site_id, activation_id, source)
    with suppress(FileNotFoundError):
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
    automation_configs: Mapping[SiteId, LocalAutomationConfig | RemoteAutomationConfig],
    *,
    debug: bool,
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
            args=(
                sync_state,
                bool(site_snapshot_settings[site_id].site_config.get("sync_files")),
                file_filter_func,
                activation_state,
                sync_start_time,
                trace.get_current_span(),
            ),
            error_callback=_error_callback,
        )

    for site_id, async_result in list(active_tasks["calc_sync_delta"].items()):
        if not async_result.ready():
            return

        active_tasks["calc_sync_delta"].pop(site_id)
        if (calc_sync_delta_result := async_result.get()) is None:
            return  # exception handling happens in thread

        automation_config = automation_configs[site_id]
        assert isinstance(automation_config, RemoteAutomationConfig)

        sync_delta, activation_state, sync_start_time = calc_sync_delta_result
        active_tasks["synchronize_files"][site_id] = task_pool.apply_async(
            func=copy_request_context(synchronize_files),
            args=(
                sync_delta,
                remote_config_generation_per_site[site_id],
                Path(site_snapshot_settings[site_id].work_dir),
                activation_state,
                sync_start_time,
                trace.get_current_span(),
                automation_config,
                debug,
            ),
            error_callback=_error_callback,
        )

    for site_id, async_result in list(active_tasks["synchronize_files"].items()):
        if not async_result.ready():
            return

        active_tasks["synchronize_files"].pop(site_id)
        if (activation_state := async_result.get()) is None:
            return  # exception handling happens in thread

        # Sync finished, now start the activation
        active_tasks["activate_site_changes"][site_id] = task_pool.apply_async(
            func=copy_request_context(activate_site_changes),
            args=(
                activate_changes,
                prevent_activate,
                activation_state,
                trace.get_current_span(),
                automation_configs[site_id],
                debug,
                True,
            ),
            error_callback=_error_callback,
        )

    for site_id, async_result in list(active_tasks["activate_site_changes"].items()):
        if not async_result.ready():
            return

        active_tasks["activate_site_changes"].pop(site_id)


class ActivateChangesSchedulerJobArgs(BaseModel, frozen=True):
    activation_id: str
    site_snapshot_settings: Mapping[SiteId, SnapshotSettings]
    prevent_activate: bool
    source: ActivationSource
    all_site_configs: SiteConfigurations
    user_permission_config: UserPermissionSerializableConfig
    debug: bool
    use_git: bool


def activate_changes_scheduler_job_entry_point(
    job_interface: BackgroundProcessInterface, args: ActivateChangesSchedulerJobArgs
) -> None:
    ActivateChangesSchedulerBackgroundJob(args.activation_id).schedule_sites(
        job_interface,
        args.site_snapshot_settings,
        args.prevent_activate,
        args.source,
        args.all_site_configs,
        args.user_permission_config,
        args.debug,
        args.use_git,
    )


class ActivateChangesSchedulerBackgroundJob(BackgroundJob):
    job_prefix = "activate-changes-scheduler"
    housekeeping_max_age_sec = 86400 * 30
    housekeeping_max_count = 20

    @classmethod
    def gui_title(cls) -> str:
        return _("Activate changes scheduler")

    def __init__(self, activation_id: str) -> None:
        super().__init__(f"{self.job_prefix}-{activation_id}")
        self._activation_id = activation_id

    def schedule_sites(
        self,
        job_interface: BackgroundProcessInterface,
        site_snapshot_settings: Mapping[SiteId, SnapshotSettings],
        prevent_activate: bool,
        source: ActivationSource,
        all_site_configs: SiteConfigurations,
        user_permission_config: UserPermissionSerializableConfig,
        debug: bool,
        use_git: bool,
    ) -> None:
        with job_interface.gui_context(
            UserPermissions.from_serialized_config(user_permission_config, permission_registry)
        ):
            job_interface.send_progress_update(
                _("Activate changes scheduler started"), with_timestamp=True
            )

            job_interface.send_progress_update(
                _("Going to update %d sites") % len(site_snapshot_settings),
                with_timestamp=True,
            )

            _sync_and_activate(
                self._activation_id,
                site_snapshot_settings,
                activation_features_registry[
                    str(version.edition(paths.omd_root))
                ].sync_file_filter_func,
                source,
                all_site_configs,
                debug=debug,
                prevent_activate=prevent_activate,
                use_git=use_git,
            )
            job_interface.send_result_message(_("Activate changes finished"))


def _render_warnings(configuration_warnings: ConfigWarnings) -> str:
    html_code = "<div class=warning>"
    html_code += "<b>%s</b>" % _("Warnings:")
    html_code += "<ul>"
    for domain, warnings in sorted(configuration_warnings.items()):
        for warning in warnings:
            html_code += f"<li>{escaping.escape_attribute(domain)}: {escaping.escape_attribute(warning)}</li>"
    html_code += "</ul>"
    html_code += "</div>"
    return html_code


def _save_state(activation_id: ActivationId, site_id: SiteId, state: SiteActivationState) -> None:
    store.save_object_to_file(
        Path(ActivateChangesManager.site_state_path(activation_id, site_id)), state
    )


@tracer.instrument("execute_activate_changes")
def execute_activate_changes(
    domain_requests: DomainRequests, is_remote_site: bool
) -> ConfigWarnings:
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
        with tracer.span(
            f"activate[{domain_request.name}]",
            attributes={
                "cmk.activate_changes.domain.name": domain_request.name,
                "cmk.activate_changes.domain.settings": repr(domain_request.settings),
            },
        ):
            warnings = get_config_domain(domain_request.name).activate(domain_request.settings)
            results[domain_request.name] = warnings or []

    _add_extensions_for_license_usage()
    _update_links_for_agent_receiver()
    # Only the remote sites are dealt with here, since the central site is dealt with separately.
    # The rabbitmq definition of the central site has to be updated anytime the definition of a
    # remote site is activated, not only when the central site is activated.
    if is_remote_site:
        _activate_local_rabbitmq_changes()

    return results


@tracer.instrument("_activate_local_rabbitmq_changes")
def _activate_local_rabbitmq_changes() -> None:
    rabbitmq.update_and_activate_rabbitmq_definitions(paths.omd_root, logger)


def _add_extensions_for_license_usage() -> None:
    save_extensions(
        LicenseUsageExtensions(
            ntop=is_ntop_configured(),
        )
    )


def _update_links_for_agent_receiver() -> None:
    uuid_link_manager = agent_registration.UUIDLinkManager(
        received_outputs_dir=paths.received_outputs_dir,
        data_source_dir=paths.data_source_push_agent_dir,
        r4r_discoverable_dir=paths.r4r_discoverable_dir,
        uuid_lookup_dir=paths.uuid_lookup_dir,
    )

    uuid_link_manager.update_links(collect_all_hosts())


def get_pending_changes_tooltip(changes_info: PendingChangesInfo) -> str:
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


def get_pending_changes(sites: Sequence[SiteId]) -> dict[str, ActivationChange]:
    changes = ActivateChanges()
    changes.load(sites)
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
    return (this_v.base.major, this_v.base.minor) != (other_v.base.major, other_v.base.minor)


def _execute_update_mkps(
    path_config: mkp_tool.PathConfig,
) -> tuple[Sequence[mkp_tool.Manifest], Sequence[mkp_tool.Manifest]]:
    logger.debug("Updating active packages")

    uninstalled, installed = mkp_tool.update_active_packages(
        mkp_tool.Installer(paths.installed_packages_dir),
        path_config,
        mkp_tool.PackageStore(
            enabled_dir=paths.local_enabled_packages_dir,
            local_dir=paths.local_optional_packages_dir,
            shipped_dir=paths.optional_packages_dir,
        ),
        ec.mkp_callbacks(paths.omd_root),
        version.__version__,
        parse_version=version.parse_check_mk_version,
    )
    return uninstalled, installed


def make_path_config() -> mkp_tool.PathConfig | None:
    if (local_path := plugins_local_path()) is None:
        return None
    if (addons_path := addons_plugins_local_path()) is None:
        return None
    ec_paths = ec.create_paths(paths.omd_root)
    return mkp_tool.PathConfig(
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
        inventory_dir=paths.local_inventory_dir,
        lib_dir=paths.local_lib_dir,
        locale_dir=paths.local_locale_dir,
        local_root=paths.local_root,
        mib_dir=ec_paths.local_mibs_dir.value,
        mkp_rule_pack_dir=ec_paths.mkp_rule_pack_dir.value,
        notifications_dir=paths.local_notifications_dir,
        pnp_templates_dir=paths.local_pnp_templates_dir,
        web_dir=paths.local_web_dir,
    )


def _execute_changed_local_files_actions() -> None:
    # I'm not changing this for fear of repercussions, but
    # NOTE: Users might be deploying a fix to a check function via MKP (for example).
    # In that case, we'd have to re*start* the core.
    mkp_tool.reload_services_affected_by_mkp_changes()
    invalidate_visuals_cache()
    setup_search_index.request_index_rebuild()


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


def _has_local_file_changes(sync_archive: bytes, to_delete: list[str]) -> bool:
    if any(p.startswith(f"{paths.LOCAL_SEGMENT}/") for p in to_delete):
        return True  # no need to check the archive.

    with CheckmkTarArchive.from_bytes(sync_archive, compression="*") as safe_tar:
        return any(m.name.startswith(f"{paths.LOCAL_SEGMENT}/") for m in safe_tar)


def _execute_post_config_sync_actions(
    site_id: SiteId, *, local_files_changed: bool, use_git: bool
) -> None:
    try:
        # When receiving configuration from a central site that uses a previous major
        # version, the config migration logic has to be executed to make the local
        # configuration compatible with the local Checkmk version.
        if _need_to_update_mkps_after_sync() and (path_config := make_path_config()):
            uninstalled, installed = _execute_update_mkps(path_config)
            mkps_changed = bool(uninstalled or installed)
        else:
            installed = ()
            mkps_changed = False

        if local_files_changed or mkps_changed:
            _execute_changed_local_files_actions()

        if _need_to_update_config_after_sync():
            logger.debug("Executing cmk-update-config")
            _execute_cmk_update_config()
        elif installed:
            cmd = ["cmk-migrate-extension-rulesets", *(m.name for m in installed)]
            logger.debug("Executing `%s`", " ".join(cmd))
            try:
                for line in subprocess.check_output(cmd, text=True).splitlines():
                    logger.debug("  %s", line.strip())
            except subprocess.CalledProcessError as e:
                logger.warning("Error while running migration script: %s", e)

        _execute_update_passwords()

        # The local configuration has just been replaced. The pending changes are not
        # relevant anymore. Confirm all of them to cleanup the inconsistency.
        logger.debug("Confirming pending changes")
        ActivateChanges.confirm_site_changes(omd_site())

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
        action="replication",
        message="Synchronized configuration from central site (local site ID is %s.)" % site_id,
        user_id=user.id,
        use_git=use_git,
    )


def verify_remote_site_config(sites: Mapping[SiteId, SiteConfiguration], site_id: SiteId) -> None:
    our_id = omd_site()

    if not is_single_local_site(sites):
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
    changes.load(list(sites))
    pending = list(reversed(changes.grouped_changes()))
    if pending:
        message = _(
            "There are %d pending changes that would get lost. The most recent are: "
        ) % len(pending)
        message += ", ".join(change["text"] for _change_id, change in pending[:10])

        raise MKGeneralException(message)


def _get_replication_components(site_config: SiteConfiguration) -> list[ReplicationPath]:
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
    repl_paths = list(replication_path_registry.values())

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
    site_logger: logging.Logger,
    sync_state: SyncState,
    file_sync_enabled: bool,
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
    to_sync_new = list(central_files - remote_files_set)

    # Add differing files
    to_sync_changed = []
    for existing in central_files.intersection(remote_files_set):
        if sync_state.central_file_infos[existing] != sync_state.remote_file_infos[existing]:
            site_logger.debug(
                "Sync needed %s: %r <> %r",
                existing,
                sync_state.central_file_infos[existing],
                sync_state.remote_file_infos[existing],
            )
            to_sync_changed.append(existing)

    # Files to be deleted
    to_delete = list(
        (_filter_remote_files(remote_files_set) if file_sync_enabled else remote_files_set)
        - central_files
    )

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
            _("Failed to extract sync archive [%d]: %s")
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


class AutomationGetConfigSyncState(AutomationCommand[list[ReplicationPath]]):
    """Called on remote site from a central site to get the current config sync state

    The central site hands over the list of replication paths it will try to synchronize later.  The
    remote site computes the list of replication files and sends it back together with the current
    configuration generation ID. The config generation ID is increased on every Setup modification
    and ensures that nothing is changed between the two config sync steps.
    """

    def command_name(self) -> str:
        return "get-config-sync-state"

    def get_request(self, config: Config, request: Request) -> list[ReplicationPath]:
        return [
            ReplicationPath.deserialize(e)
            for e in ast.literal_eval(_request.get_ascii_input_mandatory("replication_paths"))
        ]

    def execute(self, api_request: list[ReplicationPath]) -> GetConfigSyncStateResponse:
        with store.lock_checkmk_configuration(configuration_lockfile):
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
    replication_path_excluder: Callable[[str], bool],
) -> Sequence[str]:
    valid_entries = []

    for dir_name in dir_names:
        dir_path = os.path.join(root_path, dir_name)
        if (
            os.path.islink(dir_path)
            and not dir_name == general_dir_exclude
            and not replication_path_excluder(dir_name)
        ):
            valid_entries.append(dir_path)

    for file_name in file_names:
        file_path = os.path.join(root_path, file_name)
        if not (
            replication_path_excluder(os.path.basename(os.path.dirname(file_path)))
            or replication_path_excluder(file_name)
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

        match replication_path.ty:
            case ReplicationPathType.FILE:
                infos[replication_path.site_path] = _get_config_sync_file_info(
                    replication_path_full
                )

            case ReplicationPathType.DIR:
                _get_replication_dir_config_sync_file_infos(
                    infos,
                    config_sync_file_infos_per_inode,
                    base_dir,
                    replication_path_full,
                    replication_path.is_excluded,
                )
            case _:
                assert_never(replication_path.ty)
    return infos


def _get_replication_dir_config_sync_file_infos(
    infos: MutableMapping[str, ConfigSyncFileInfo],
    config_sync_file_infos_per_inode: Mapping[int, ConfigSyncFileInfo],
    base_dir: Path,
    replication_path: str,
    replication_path_excluder: Callable[[str], bool],
) -> None:
    # Use os functionality instead of pathlib since it is faster
    for root, dir_names, file_names in os.walk(replication_path):
        root_name = os.path.basename(root)

        if root_name == GENERAL_DIR_EXCLUDE or replication_path_excluder(root_name):
            continue

        config_sync_paths = _get_config_sync_paths(
            root, dir_names, file_names, GENERAL_DIR_EXCLUDE, replication_path_excluder
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
    use_git: bool
    site_config: SiteConfiguration
    user_attributes: Sequence[tuple[str, UserAttribute]]


class AutomationReceiveConfigSync(AutomationCommand[ReceiveConfigSyncRequest]):
    """Called on remote site from a central site to update the Checkmk configuration

    The central site hands over a tar archive with the files to be written and a list of
    files to be deleted. The configuration generation is used to validate that no modification has
    been made between the two sync steps (get-config-sync-state and this autmoation).
    """

    def command_name(self) -> str:
        return "receive-config-sync"

    def get_request(self, config: Config, request: Request) -> ReceiveConfigSyncRequest:
        site_id = SiteId(request.get_ascii_input_mandatory("site_id"))
        verify_remote_site_config(config.sites, site_id)

        return ReceiveConfigSyncRequest(
            site_id,
            request.uploaded_file("sync_archive")[2],
            ast.literal_eval(request.get_str_input_mandatory("to_delete")),
            request.get_integer_input_mandatory("config_generation"),
            config.wato_use_git,
            config.sites[site_id],
            get_user_attributes(config.wato_user_attrs),
        )

    def execute(self, api_request: ReceiveConfigSyncRequest) -> bool:
        with store.lock_checkmk_configuration(configuration_lockfile):
            if api_request.config_generation != _get_current_config_generation():
                raise MKGeneralException(
                    _(
                        "The configuration was changed during activation. "
                        "Terminating this activation to ensure configuration integrity. "
                        "Please try again."
                    )
                )

            logger.debug("Updating configuration from sync snapshot")
            self._update_config_on_remote_site(
                api_request.sync_archive,
                api_request.to_delete,
                api_request.site_id,
                api_request.site_config,
                api_request.user_attributes,
            )

            logger.debug("Executing post sync actions")
            _execute_post_config_sync_actions(
                api_request.site_id,
                local_files_changed=_has_local_file_changes(
                    api_request.sync_archive, api_request.to_delete
                ),
                use_git=api_request.use_git,
            )

            logger.debug("Done")
            return True

    def _update_config_on_remote_site(
        self,
        sync_archive: bytes,
        to_delete: list[str],
        site_id: SiteId,
        site_config: SiteConfiguration,
        user_attributes: Sequence[tuple[str, UserAttribute]],
    ) -> None:
        """Use the given tar archive and list of files to be deleted to update the local files"""
        base_dir = cmk.utils.paths.omd_root
        base_folder_path = str(cmk.utils.paths.check_mk_config_dir / "wato")

        default_sync_config = user_sync_default_config(site_config, site_id)
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
                _reintegrate_site_local_users(current_users, active_connectors, user_attributes)


def _reintegrate_site_local_users(
    old_users: Users,
    active_connectors: list[str],
    user_attributes: Sequence[tuple[str, UserAttribute]],
) -> None:
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
    save_users(
        new_users,
        user_attributes,
        active_config.user_connections,
        now=datetime.now(),
        pprint_value=active_config.wato_pprint_config,
        call_users_saved_hook=True,
    )


@dataclass
class ActivationChange:
    id: str
    user_id: UserId
    action_name: str
    text: str
    time: float


@dataclass
class StatusPerSite:
    site: SiteId
    phase: Literal["initialized", "queued", "started", "sync", "activate", "finishing", "done"]
    state: Literal["success", "error", "warning"]
    status_text: str
    status_details: str
    start_time: float
    end_time: float


@dataclass
class ActivationRestAPIResponseExtensions:
    activation_id: str
    sites: Sequence[SiteId]
    is_running: bool
    force_foreign_changes: bool
    time_started: float
    changes: Sequence[ActivationChange]
    status_per_site: Sequence[StatusPerSite]


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
        status_per_site=[
            StatusPerSite(
                site=SiteId(site),
                phase=status_dict["_phase"],
                state=status_dict["_state"],
                status_text=status_dict["_status_text"],
                status_details=re.sub(r"<.*?>", "", unescape(status_dict["_status_details"])),
                start_time=status_dict["_time_started"],
                end_time=status_dict["_time_ended"],
            )
            for site, status_dict in manager.get_state()["sites"].items()
            if status_dict
        ],
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


def get_status_for_site(site_id: SiteId, site: SiteConfiguration) -> SiteStatus:
    return (
        SiteStatus({"state": "disabled"})
        if site.get("disabled")
        else sites_states().get(site_id, SiteStatus({}))
    )


def _check_sites_that_cannot_be_activated(
    site_configurations: SiteConfigurations,
) -> None:
    """Run checks on the given site configurations these sites cannot be activated.
    They may have a status that is not 'online' or they could be remote sites that
    are not logged in.
    """
    sites_that_cannot_be_activated = SiteConfigurations(
        {
            site_id: site
            for site_id, site in site_configurations.items()
            if (
                not (site_is_local(site) or "secret" in site)
                or get_status_for_site(site_id, site).get("state", "unknown")
                not in ["online", "disabled"]
            )
        }
    )

    manager = ActivateChangesManager()
    manager.changes.load(list(sites_that_cannot_be_activated))

    if dirty_sites := manager.changes.dirty_sites(activation_sites(sites_that_cannot_be_activated)):
        """There are changes to activate, but sites cannot currently be activated."""
        err_msg = (
            "sites %s have" % ", ".join(site_id for site_id, _site in dirty_sites)
            if len(dirty_sites) > 1
            else "site %s has" % dirty_sites[0][0]
        )

        raise MKUserError(
            None,
            _(
                "There are changes to activate, but no site can be "
                "activated (The %s changes, but may be "
                "offline or not logged in)."
            )
            % err_msg,
            status=409,
        )


def _check_sites_that_can_be_activated(
    site_configurations: SiteConfigurations,
    force_foreign_changes: bool,
) -> tuple[ActivateChangesManager, SiteConfigurations]:
    """Run checks on the given site configurations These sites are either remote sites that
    are logged in or the local site and they will have an online status ."""
    sites_that_can_be_activated = SiteConfigurations(
        {
            site_id: site
            for site_id, site in site_configurations.items()
            if (
                (site_is_local(site) or "secret" in site)
                and get_status_for_site(site_id, site).get("state", "unknown")
                in ["online", "disabled"]
            )
        }
    )

    manager = ActivateChangesManager()
    manager.changes.load(list(sites_that_can_be_activated))

    if manager.changes.has_foreign_changes():
        if not user.may("wato.activateforeign"):
            raise MKAuthException(_("You are not allowed to activate changes of other users."))
        if not force_foreign_changes:
            raise MKAuthException(
                _(
                    "There are changes from other users and foreign changes are "
                    "not allowed in this API call."
                )
            )

    if manager.is_running():
        raise MKUserError(None, _("There is an activation already running."), status=423)

    if not manager.changes.has_pending_changes():
        raise MKUserError(None, _("Currently there are no changes to activate."), status=422)

    if not manager.changes.dirty_sites(activation_sites(sites_that_can_be_activated)):
        raise MKUserError(None, _("Currently there are no changes to activate."), status=422)

    return manager, sites_that_can_be_activated


def activate_changes_start(
    *,
    sites: Sequence[SiteId],
    all_site_configs: SiteConfigurations,
    user_permission_config: UserPermissionSerializableConfig,
    source: ActivationSource,
    comment: str | None,
    max_snapshots: int,
    force_foreign_changes: bool,
    use_git: bool,
    debug: bool,
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

    _raise_for_license_block()

    for site_id in sites:
        if site_id not in all_site_configs:
            raise MKUserError(
                None, _("Unknown site %s") % escaping.escape_attribute(site_id), status=400
            )

    sites_to_activate = SiteConfigurations(
        {
            site_id: site
            for site_id, site in all_site_configs.items()
            if not sites or site_id in sites
        }
    )
    _check_sites_that_cannot_be_activated(sites_to_activate)
    manager, sites_that_can_be_activated = _check_sites_that_can_be_activated(
        sites_to_activate, force_foreign_changes
    )

    manager.start(
        sites=list(sites_that_can_be_activated),
        comment=comment,
        activate_foreign=force_foreign_changes,
        source=source,
        all_site_configs=sites_that_can_be_activated,
        user_permission_config=user_permission_config,
        max_snapshots=max_snapshots,
        use_git=use_git,
        debug=debug,
    )
    return activation_attributes_for_rest_api_response(manager)


@dataclass(frozen=True)
class ActivationFeatures:
    edition: version.Edition
    sync_file_filter_func: Callable[[str], bool] | None
    snapshot_manager_factory: Callable[[str, dict[SiteId, SnapshotSettings]], SnapshotManager]
    get_rabbitmq_definitions: Callable[
        [Mapping[SiteId, SiteConfiguration], BrokerConnections], Mapping[str, rabbitmq.Definitions]
    ]
    distribute_piggyback_hub_configs: Callable[
        [
            GlobalSettings,
            Mapping[SiteId, SiteConfiguration],
            Collection[SiteId],
            Mapping[HostName, SiteId],
        ],
        None,
    ]


class ActivationFeaturesRegistry(Registry[ActivationFeatures]):
    def plugin_name(self, instance: ActivationFeatures) -> str:
        return str(instance.edition)


activation_features_registry = ActivationFeaturesRegistry()
