#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module implements generic functionality of the Checkmk backup
system. It is used to configure the site and system backup.
"""

from __future__ import annotations

import abc
import contextlib
import errno
import os
import shutil
import signal
import socket
import subprocess
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from io import TextIOWrapper
from pathlib import Path
from typing import assert_never, cast, Final, Generic, TypeVar

import cmk.ccc.version as cmk_version
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import omd_site

from cmk.utils import render
from cmk.utils.backup.config import Config as RawConfig
from cmk.utils.backup.job import JobConfig, JobState, ScheduleConfig
from cmk.utils.backup.targets import TargetId
from cmk.utils.backup.targets.aws_s3_bucket import S3Bucket, S3Params, S3Target
from cmk.utils.backup.targets.azure_blob_storage import (
    BlobStorage,
    BlobStorageParams,
    BlobStorageTarget,
)
from cmk.utils.backup.targets.config import TargetConfig
from cmk.utils.backup.targets.local import LocalTarget, LocalTargetParams
from cmk.utils.backup.targets.protocol import Target as TargetProtocol
from cmk.utils.backup.targets.remote_interface import (
    RemoteTarget,
    RemoteTargetParams,
    TRemoteParams,
    TRemoteStorage,
)
from cmk.utils.backup.type_defs import SiteBackupInfo
from cmk.utils.backup.utils import BACKUP_INFO_FILENAME
from cmk.utils.certs import CertManagementEvent
from cmk.utils.paths import omd_root
from cmk.utils.schedule import next_scheduled_time

from cmk.gui import forms, key_mgmt
from cmk.gui.breadcrumb import Breadcrumb, make_simple_page_breadcrumb
from cmk.gui.exceptions import FinalizeRequest, HTTPRedirect, MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import ActionResult, Key
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import (
    DocReference,
    make_confirm_delete_link,
    make_confirm_link,
    makeactionuri,
    makeactionuri_contextless,
    makeuri_contextless,
)
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import (
    AbsoluteDirname,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DictionaryElements,
    DropdownChoice,
    FixedValue,
    ID,
    ListOf,
    Password,
    SchedulePeriod,
    TextInput,
    Timeofday,
    ValueSpecText,
)
from cmk.gui.wato import IndividualOrStoredPassword

from cmk.crypto.password import Password as PasswordType
from cmk.crypto.pem import PEMDecodingError


def register() -> None:
    target_type_registry.register(BackupTargetLocal)
    target_type_registry.register(BackupTargetAWSS3Bucket)
    target_type_registry.register(BackupTargetAzureBlobStorage)


# .
#   .--Config--------------------------------------------------------------.
#   |                     ____             __ _                            |
#   |                    / ___|___  _ __  / _(_) __ _                      |
#   |                   | |   / _ \| '_ \| |_| |/ _` |                     |
#   |                   | |__| (_) | | | |  _| | (_| |                     |
#   |                    \____\___/|_| |_|_| |_|\__, |                     |
#   |                                           |___/                      |
#   +----------------------------------------------------------------------+
#   | Handling of the backup configuration files. This is used to handle   |
#   | either the global system config for the appliance and the site       |
#   | specific configuration of the site backup.                           |
#   '----------------------------------------------------------------------'


_OUTER_TEXT_FIELD_SIZE = 80


def mkbackup_path() -> Path:
    return omd_root / "bin/mkbackup"


def hostname() -> str:
    return socket.gethostname()


class Config:
    def __init__(self, config: RawConfig) -> None:
        self._config = config
        self._cronjob_path = omd_root / "etc/cron.d/mkbackup"

    @classmethod
    def load(cls) -> Config:
        return cls(RawConfig.load())

    @property
    def jobs(self) -> dict[str, Job]:
        return {
            job_id: Job(
                job_id,
                job_config,
            )
            for job_id, job_config in self._config.site.jobs.items()
        }

    @property
    def site_targets(self) -> dict[TargetId, Target]:
        return {
            target_id: Target(
                target_id,
                target_config,
            )
            for target_id, target_config in self._config.site.targets.items()
        }

    @property
    def cma_system_targets(self) -> dict[TargetId, Target]:
        return {
            target_id: Target(
                target_id,
                target_config,
            )
            for target_id, target_config in self._config.cma_system.targets.items()
        }

    @property
    def all_targets(self) -> dict[TargetId, Target]:
        return {
            target_id: Target(
                target_id,
                target_config,
            )
            for target_id, target_config in self._config.all_targets.items()
        }

    def add_target(self, target: Target) -> None:
        self._config.site.targets[target.ident] = target.config
        self._config.save()

    def delete_target(self, target_id: TargetId) -> None:
        del self._config.site.targets[target_id]
        self._config.save()

    def add_job(self, job: Job) -> None:
        self._config.site.jobs[job.ident] = job.config
        self._config.save()
        self._save_cronjobs()

    def delete_job(self, job_id: str) -> None:
        del self._config.site.jobs[job_id]
        self._config.save()
        self._save_cronjobs()

    def _save_cronjobs(self) -> None:
        with Path(self._cronjob_path).open("w", encoding="utf-8") as f:
            self._write_cronjob_header(f)
            for job in self.jobs.values():
                cron_config = job.cron_config()
                if cron_config:
                    f.write("%s\n" % "\n".join(cron_config))

        self._apply_cron_config()

    def _write_cronjob_header(self, f: TextIOWrapper) -> None:
        f.write("# Written by mkbackup configuration\n")

    def _apply_cron_config(self) -> None:
        completed_process = subprocess.run(
            ["omd", "restart", "crontab"],
            close_fds=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            stdin=subprocess.DEVNULL,
            check=False,
        )
        if completed_process.returncode:
            raise MKGeneralException(
                _("Failed to apply the cronjob config: %s") % completed_process.stdout
            )


# .
#   .--Jobs----------------------------------------------------------------.
#   |                            _       _                                 |
#   |                           | | ___ | |__  ___                         |
#   |                        _  | |/ _ \| '_ \/ __|                        |
#   |                       | |_| | (_) | |_) \__ \                        |
#   |                        \___/ \___/|_.__/|___/                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Backup job handling. A backup job is the entity to describe a single |
#   | backup process which has it's own state, can be executed manually    |
#   | and also scheduled to be executed in a predefined interval.          |
#   '----------------------------------------------------------------------'


# Abstract class for backup jobs (Job) and restore job (RestoreJob)
class MKBackupJob(abc.ABC):
    @classmethod
    def state_name(cls, state: str | None) -> str:
        return {
            "started": _("Started"),
            "running": _("Currently running"),
            "finished": _("Ended"),
            None: _("Never executed"),
        }[state]

    @abc.abstractmethod
    def state_file_path(self) -> Path: ...

    def cleanup(self) -> None:
        self.state_file_path().unlink(missing_ok=True)

    def state(self) -> JobState:
        try:
            state = JobState.parse_file(self.state_file_path())
        except FileNotFoundError:
            state = JobState(
                state=None,
                started=None,
                output="",
            )
        except Exception as e:
            raise MKGeneralException(
                _('Failed to parse state file "%s": %s') % (self.state_file_path(), e)
            )

        # Fix data structure when the process has been killed
        if state.state == "running" and not os.path.exists("/proc/%d" % state.pid):  # type: ignore[str-format]
            assert state.started is not None
            state.state = "finished"
            state.finished = max(state.started, self.state_file_path().stat().st_mtime)
            state.success = False

        return state

    def was_started(self) -> bool:
        return self.state_file_path().exists()

    def is_running(self) -> bool:
        if not self.was_started():
            return False

        state = self.state()
        return state.state in ["started", "running"] and os.path.exists("/proc/%d" % state.pid)  # type: ignore[str-format]

    def start(self, **env_updates: str) -> None:
        completed_process = subprocess.run(
            self._start_command(),
            close_fds=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            encoding="utf-8",
            env={
                # we always need os.environ, otherwise, mkbackup won't start in the site context
                **os.environ,
                **env_updates,
            },
            check=False,
        )
        if completed_process.returncode != 0:
            raise MKGeneralException(_("Failed to start the job: %s") % completed_process.stdout)

    @abc.abstractmethod
    def _start_command(self) -> Sequence[str | Path]: ...

    def stop(self) -> None:
        state = self.state()
        assert state.pid is not None
        pgid = os.getpgid(state.pid)

        try:
            os.killpg(pgid, signal.SIGTERM)
        except OSError as e:
            if e.errno == errno.ESRCH:
                pass
            else:
                raise

        wait = 5.0  # sec
        while os.path.exists("/proc/%d" % state.pid) and wait > 0:
            time.sleep(0.5)
            wait -= 0.5

        # When still running after 5 seconds, enforce
        if wait == 0:
            try:
                os.killpg(pgid, signal.SIGKILL)
            except OSError as e:
                if e.errno == errno.ESRCH:
                    pass
                else:
                    raise


class Job(MKBackupJob):
    def __init__(self, ident: str, config: JobConfig) -> None:
        self.ident: Final = ident
        self.config: Final = config

    @property
    def title(self) -> str:
        return self.config["title"]

    def target_ident(self) -> TargetId:
        return self.config["target"]

    def key_ident(self) -> str | None:
        return self.config["encrypt"]

    def is_encrypted(self) -> bool:
        return self.config["encrypt"] is not None

    def state_file_path(self) -> Path:
        return omd_root / "var/check_mk/backup" / ("%s.state" % self.ident)

    def _start_command(self) -> Sequence[str | Path]:
        return [mkbackup_path(), "backup", "--background", self.ident]

    def schedule(self) -> ScheduleConfig | None:
        return self.config["schedule"]

    def cron_config(self) -> list[str]:
        if not (schedule := self.config["schedule"]) or schedule["disabled"]:
            return []
        userspec = self._cron_userspec()
        cmdline = self._cron_cmdline()
        return [f"{timespec} {userspec}{cmdline}" for timespec in self._cron_timespecs(schedule)]

    @staticmethod
    def _cron_timespecs(schedule: ScheduleConfig) -> Sequence[str]:
        period = schedule["period"]
        times = schedule["timeofday"]

        if period == "day":
            dayspec = "* * *"

        elif period[0] == "week":
            # 0-6
            dayspec = "* * %d" % (period[1] + 1,)

        elif period[0] == "month_begin":
            # 1-28
            dayspec = "%d * *" % period[1]

        else:
            assert_never(period)

        # times: list of two element tuples (hours, minutes)
        timespecs = []
        for hour, minute in times:
            timespecs.append("%d %d %s" % (minute, hour, dayspec))

        return timespecs

    def _cron_userspec(self) -> str:
        if os.environ.get("OMD_SITE"):
            return ""
        return "root "

    def _cron_cmdline(self) -> str:
        return "mkbackup backup %s >/dev/null" % self.ident


class PageBackup:
    def title(self) -> str:
        return _("Site backup")

    def __init__(self, key_store: key_mgmt.KeypairStore) -> None:
        super().__init__()
        self.key_store = key_store

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="backups",
                    title=_("Backups"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_setup()),
                        ),
                        PageMenuTopic(
                            title=_("Restore from backup"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Restore"),
                                    icon_name={
                                        "icon": "backup",
                                        "emblem": "refresh",
                                    },
                                    item=make_simple_link(
                                        makeuri_contextless(request, [("mode", "backup_restore")])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )
        menu.add_doc_reference(_("Backups"), DocReference.BACKUPS)
        return menu

    def _page_menu_entries_setup(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Backup targets"),
            icon_name="backup_targets",
            item=make_simple_link(makeuri_contextless(request, [("mode", "backup_targets")])),
            is_shortcut=True,
            is_suggested=True,
        )
        yield PageMenuEntry(
            title=_("Backup encryption keys"),
            icon_name="signature_key",
            item=make_simple_link(makeuri_contextless(request, [("mode", "backup_keys")])),
            is_shortcut=True,
            is_suggested=True,
        )
        yield PageMenuEntry(
            title=_("Add job"),
            icon_name="new",
            item=make_simple_link(makeuri_contextless(request, [("mode", "edit_backup_job")])),
            is_shortcut=True,
            is_suggested=True,
        )

    def action(self) -> ActionResult:
        if (ident := request.var("_job")) is None:
            raise MKUserError("_job", _("Missing job ID."))

        try:
            job = Config.load().jobs[ident]
        except KeyError:
            raise MKUserError("_job", _("This backup job does not exist."))

        action = request.var("_action")

        if not transactions.check_transaction():
            return HTTPRedirect(makeuri_contextless(request, [("mode", "backup")]))

        if action == "delete":
            self._delete_job(job)

        elif action == "start":
            self._start_job(job)

        elif action == "stop":
            self._stop_job(job)

        return HTTPRedirect(makeuri_contextless(request, [("mode", "backup")]))

    def _delete_job(self, job: Job) -> None:
        if job.is_running():
            raise MKUserError("_job", _("This job is currently running."))

        job.cleanup()

        with contextlib.suppress(KeyError):
            Config.load().delete_job(job.ident)

        flash(_("The job has been deleted."))

    def _start_job(self, job: Job) -> None:
        job.start()
        flash(_("The backup has been started."))

    def _stop_job(self, job: Job) -> None:
        job.stop()
        flash(_("The backup has been stopped."))

    def page(self) -> None:
        show_key_download_warning(self.key_store.load())
        self._show_job_list()

    def _show_job_list(self) -> None:
        html.h3(_("Jobs"))
        with table_element(sortable=False, searchable=False) as table:
            for nr, job in enumerate(sorted(Config.load().jobs.values(), key=lambda j: j.ident)):
                table.row()
                table.cell("#", css=["narrow nowrap"])
                html.write_text_permissive(nr)
                table.cell(_("Actions"), css=["buttons"])
                state = job.state()
                job_state = state.state
                delete_url = make_confirm_delete_link(
                    url=makeactionuri_contextless(
                        request,
                        transactions,
                        [
                            ("mode", "backup"),
                            ("_action", "delete"),
                            ("_job", job.ident),
                        ],
                    ),
                    title=_("Delete job #%d") % nr,
                    suffix=job.title,
                    message=_("ID: %s") % job.ident,
                )
                edit_url = makeuri_contextless(
                    request,
                    [("mode", "edit_backup_job"), ("job", job.ident)],
                )
                state_url = makeuri_contextless(
                    request,
                    [("mode", "backup_job_state"), ("job", job.ident)],
                )

                if not job.is_running():
                    html.icon_button(edit_url, _("Edit this backup job"), "edit")
                    html.icon_button(delete_url, _("Delete this backup job"), "delete")

                if job_state is not None:
                    html.icon_button(
                        state_url,
                        _("Show current / last state of this backup job"),
                        "backup_state",
                    )

                if not job.is_running():
                    start_url = makeactionuri_contextless(
                        request,
                        transactions,
                        [
                            ("mode", "backup"),
                            ("_action", "start"),
                            ("_job", job.ident),
                        ],
                    )

                    html.icon_button(start_url, _("Manually start this backup"), "backup_start")
                else:
                    stop_url = makeactionuri_contextless(
                        request,
                        transactions,
                        [
                            ("mode", "backup"),
                            ("_action", "stop"),
                            ("_job", job.ident),
                        ],
                    )

                    html.icon_button(stop_url, _("Stop this backup job"), "backup_stop")

                table.cell(_("ID"), job.ident)
                table.cell(_("Name"), job.title)

                css = "state0"
                state_txt = job.state_name(job_state)
                if job_state == "finished":
                    if not state.success:
                        css = "state2"
                        state_txt = _("Failed")
                    else:
                        state_txt = _("Finished")
                elif job_state is None:
                    css = ""

                table.cell(_("State"), css=[css])
                html.write_html(HTMLWriter.render_span(state_txt))

                table.cell(_("Runtime"))
                if state.started:
                    html.write_text_permissive(
                        _("Started at %s") % render.date_and_time(state.started)
                    )
                    duration = time.time() - state.started
                    if job_state == "finished":
                        assert state.finished is not None
                        html.write_text_permissive(
                            ", Finished at %s" % render.date_and_time(state.finished)
                        )
                        duration = state.finished - state.started

                    if state.size is not None:
                        size_txt = " Size: %s," % render.fmt_bytes(state.size)
                    else:
                        size_txt = ""

                    assert state.bytes_per_second is not None
                    html.write_text_permissive(
                        _(" (Duration: %s,%s IO: %s/s)")
                        % (
                            render.timespan(duration),
                            size_txt,
                            render.fmt_bytes(state.bytes_per_second),
                        )
                    )

                table.cell(_("Next run"))
                schedule = job.schedule()
                if not schedule:
                    html.write_text_permissive(_("Only execute manually"))

                elif schedule["disabled"]:
                    html.write_text_permissive(_("Disabled"))

                elif schedule["timeofday"]:
                    # find the next time of all configured times
                    times = []
                    for timespec in schedule["timeofday"]:
                        times.append(next_scheduled_time(schedule["period"], timespec))

                    html.write_text_permissive(
                        time.strftime("%Y-%m-%d %H:%M", time.localtime(min(times)))
                    )


class PageEditBackupJob:
    def __init__(self, key_store: key_mgmt.KeypairStore) -> None:
        super().__init__()
        self.key_store = key_store
        job_ident = request.get_str_input("job")

        if job_ident is not None:
            try:
                job = Config.load().jobs[job_ident]
            except KeyError:
                raise MKUserError("target", _("This backup job does not exist."))

            if job.is_running():
                raise MKUserError("_job", _("This job is currently running."))

            self._new = False
            self._ident: str | None = job_ident
            self._job_cfg: JobConfig | dict[str, object] = job.config
            self._title = _("Edit backup job: %s") % job.title
        else:
            self._new = True
            self._ident = None
            self._job_cfg = {}
            self._title = _("Add backup job")

    def title(self) -> str:
        return self._title

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Job"), breadcrumb, form_name="edit_job", button_name="_save"
        )

    def vs_backup_schedule(self) -> Alternative:
        return Alternative(
            title=_("Schedule"),
            elements=[
                FixedValue(
                    value=None,
                    title=_("Execute manually"),
                    totext=_("Only execute manually"),
                ),
                Dictionary(
                    title=_("Schedule execution"),
                    elements=[
                        (
                            "disabled",
                            Checkbox(
                                title=_("Disable"),
                                label=_("Currently disable scheduled execution of this job"),
                            ),
                        ),
                        ("period", SchedulePeriod(from_end=False)),
                        (
                            "timeofday",
                            ListOf(
                                valuespec=Timeofday(
                                    default_value=(0, 0),
                                    allow_empty=False,
                                ),
                                title=_("Time of day to start the backup at"),
                                movable=False,
                                default_value=[(0, 0)],
                                add_label=_("Add new time"),
                                empty_text=_("Please specify at least one time."),
                                allow_empty=False,
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ],
        )

    def vs_backup_job(self, config: Config) -> Dictionary:
        if self._new:
            ident_attr: list[tuple[str, TextInput | FixedValue]] = [
                (
                    "ident",
                    ID(
                        title=_("Unique ID"),
                        help=_(
                            "The ID of the job must be a unique text. It will be used as an internal key "
                            "when objects refer to the job."
                        ),
                        allow_empty=False,
                        size=_OUTER_TEXT_FIELD_SIZE,
                        validate=lambda ident, varprefix: self._validate_backup_job_ident(
                            config,
                            ident,
                            varprefix,
                        ),
                    ),
                )
            ]
        else:
            ident_attr = [
                (
                    "ident",
                    FixedValue(value=self._ident, title=_("Unique ID")),
                )
            ]

        return Dictionary(
            title=_("Backup job"),
            elements=ident_attr
            + [
                (
                    "title",
                    TextInput(
                        title=_("Title"),
                        allow_empty=False,
                        size=_OUTER_TEXT_FIELD_SIZE,
                    ),
                ),
                (
                    "target",
                    DropdownChoice(
                        title=_("Target"),
                        choices=self.backup_target_choices(config),
                        validate=lambda target_id, varprefix: self._validate_target(
                            config,
                            target_id,
                            varprefix,
                        ),
                        invalid_choice="complain",
                    ),
                ),
                ("schedule", self.vs_backup_schedule()),
                (
                    "compress",
                    Checkbox(
                        title=_("Compression"),
                        help=_(
                            "Enable gzip compression of the backed up files. The tar archives "
                            "created by the backup are gzipped during backup."
                        ),
                        label=_("Compress the backed up files"),
                    ),
                ),
                (
                    "encrypt",
                    Alternative(
                        title=_("Encryption"),
                        help=_(
                            "Enable encryption of the backed up files. The tar archives "
                            "created by the backup are encrypted using the specified key "
                            "during backup. You will need the private key and the "
                            "passphrase to decrypt the backup."
                        ),
                        elements=[
                            FixedValue(
                                value=None,
                                title=_("Do not encrypt the backup"),
                                totext="",
                            ),
                            DropdownChoice(
                                title=_("Encrypt the backup using the key:"),
                                choices=self.backup_key_choices,
                                invalid_choice="complain",
                            ),
                        ],
                    ),
                ),
                (
                    "no_history",
                    Checkbox(
                        title=_("Do not backup historical data"),
                        help=_(
                            "You may use this option to create a much smaller partial backup of the site."
                        ),
                        label=_(
                            "Do not backup metric data (RRD files), the monitoring history and log files"
                        ),
                    ),
                ),
            ],
            optional_keys=[],
            render="form",
        )

    def _validate_target(
        self,
        config: Config,
        target_id: TargetId | None,
        varprefix: str,
    ) -> None:
        if not target_id:
            raise MKUserError(varprefix, _("You need to provide an ID"))
        config.all_targets[target_id].validate(varprefix)

    def _validate_backup_job_ident(self, config: Config, value: str, varprefix: str) -> None:
        if value == "restore":
            raise MKUserError(varprefix, _("You need to choose another ID."))

        if value in config.jobs:
            raise MKUserError(varprefix, _("This ID is already used by another backup job."))

    def backup_key_choices(self) -> Sequence[tuple[str, str]]:
        return self.key_store.choices()

    def backup_target_choices(self, config: Config) -> Sequence[tuple[TargetId, str]]:
        return [
            (
                target.ident,
                target.title,
            )
            for target in sorted(
                config.all_targets.values(),
                key=lambda t: t.ident,
            )
        ]

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return HTTPRedirect(makeuri_contextless(request, [("mode", "backup")]))

        backup_config = Config.load()
        vs = self.vs_backup_job(backup_config)

        job_config = vs.from_html_vars("edit_job")
        vs.validate_value(job_config, "edit_job")

        if "ident" in job_config:
            self._ident = job_config.pop("ident")
        self._job_cfg = cast(JobConfig, job_config)
        if self._ident is None:
            raise MKGeneralException("Cannot create or modify job without identifier")

        backup_config.add_job(
            Job(
                self._ident,
                self._job_cfg,
            )
        )

        return HTTPRedirect(makeuri_contextless(request, [("mode", "backup")]))

    def page(self) -> None:
        with html.form_context("edit_job", method="POST"):
            html.prevent_password_auto_completion()

            vs = self.vs_backup_job(Config.load())

            vs.render_input("edit_job", dict(self._job_cfg))
            vs.set_focus("edit_job")
            forms.end()

            html.hidden_fields()


_TBackupJob = TypeVar("_TBackupJob", bound=MKBackupJob)


class PageAbstractMKBackupJobState(abc.ABC, Generic[_TBackupJob]):
    @property
    @abc.abstractmethod
    def ident(self) -> str: ...

    @property
    @abc.abstractmethod
    def job(self) -> _TBackupJob: ...

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(dropdowns=[], breadcrumb=breadcrumb)

    def page(self) -> None:
        html.open_div(id_="job_details")
        self.show_job_details()
        html.close_div()
        html.javascript(
            "cmk.backup.refresh_job_details('{}', '{}', {})".format(
                self._update_url(), self.ident, "true"
            )
        )

    def _update_url(self) -> str:
        return "ajax_backup_job_state.py?job=%s" % self.ident

    def show_job_details(self) -> None:
        state = self.job.state()

        html.open_table(class_=["data", "backup_job"])

        if state.state is None:
            css = []
            state_txt = self.job.state_name(state.state)
        elif state.state != "finished":
            css = ["state0"]
            state_txt = self.job.state_name(state.state)
        elif state.success:
            css = ["state0"]
            state_txt = _("Finished")
        else:
            css = ["state2"]
            state_txt = _("Failed")

        html.open_tr(class_=["data", "even0"])
        html.td(_("State"), class_=["left", "legend"])
        html.td(state_txt, class_=["state"] + css)
        html.close_tr()

        html.open_tr(class_=["data", "odd0"])
        html.td(_("Runtime"), class_="left")
        html.open_td()
        if state.started:
            html.write_text_permissive(_("Started at %s") % render.date_and_time(state.started))
            duration = time.time() - state.started
            if state.state == "finished":
                assert state.finished is not None
                html.write_text_permissive(", Finished at %s" % render.date_and_time(state.started))
                duration = state.finished - state.started

            html.write_text_permissive(_(" (Duration: %s)") % render.timespan(duration))
        html.close_td()
        html.close_tr()

        html.open_tr(class_=["data", "even0"])
        html.td(_("Output"), class_=["left", "legend"])
        html.open_td()
        html.open_div(class_="log_output", style="height: 400px;", id_="progress_log")
        html.pre(state.output)
        html.close_div()
        html.close_td()
        html.close_tr()

        html.close_table()


class PageBackupJobState(PageAbstractMKBackupJobState[Job]):
    def __init__(self) -> None:
        super().__init__()
        self._from_vars()

    @property
    def ident(self) -> str:
        return self._ident

    @property
    def job(self) -> Job:
        return self._job

    def title(self) -> str:
        return _("Job state: %s") % self.job.title

    def _from_vars(self) -> None:
        if (job_ident := request.var("job")) is None:
            raise MKUserError("job", _("You need to specify a backup job."))
        try:
            tmp = Config.load().jobs[job_ident]
        except KeyError:
            raise MKUserError("job", _("This backup job does not exist."))
        self._job = tmp
        self._ident = job_ident


# .
#   .--Target Types--------------------------------------------------------.
#   |      _____                    _     _____                            |
#   |     |_   _|_ _ _ __ __ _  ___| |_  |_   _|   _ _ __   ___  ___       |
#   |       | |/ _` | '__/ _` |/ _ \ __|   | || | | | '_ \ / _ \/ __|      |
#   |       | | (_| | | | (_| |  __/ |_    | || |_| | |_) |  __/\__ \      |
#   |       |_|\__,_|_|  \__, |\___|\__|   |_| \__, | .__/ \___||___/      |
#   |                    |___/                 |___/|_|                    |
#   +----------------------------------------------------------------------+
#   | A target type implements the handling of different protocols to use  |
#   | for storing the backup.                                              |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class _Backups:
    backups: Mapping[str, SiteBackupInfo]
    timed_out: bool

    def get(self, ident: str) -> SiteBackupInfo:
        try:
            return self.backups[ident]
        except KeyError as ex:
            if self.timed_out:
                raise MKGeneralException(
                    "Unable to find backup. This may be because "
                    "the listing of remote backups timed out. "
                    "There may be too many files present at the "
                    "remote target."
                )
            else:
                raise ex


class ABCBackupTargetType(abc.ABC):
    @abc.abstractmethod
    def __init__(self, params: Mapping[str, object]) -> None: ...

    @property
    @abc.abstractmethod
    def parameters(self) -> Mapping[str, object]: ...

    @property
    @abc.abstractmethod
    def target(self) -> TargetProtocol: ...

    @staticmethod
    @abc.abstractmethod
    def ident() -> str: ...

    @staticmethod
    @abc.abstractmethod
    def title() -> str: ...

    @classmethod
    def valuespec(cls) -> Dictionary:
        return Dictionary(
            elements=cls.dictionary_elements(),
            optional_keys=[],
            validate=lambda params, varprefix: cls(params).validate(varprefix),
        )

    @classmethod
    @abc.abstractmethod
    def dictionary_elements(cls) -> DictionaryElements: ...

    @abc.abstractmethod
    def validate(self, varprefix: str) -> None: ...

    def backups(self) -> _Backups:
        _check_if_target_ready(self.target)
        backups: dict[str, SiteBackupInfo] = {}
        time0 = time.time()
        for ident, info in self.target.list_backups():
            backups[ident] = info
            if time.time() - time0 > request.request_timeout - 20:
                return _Backups(backups, timed_out=True)
        return _Backups(backups, timed_out=False)

    @abc.abstractmethod
    def remove_backup(self, backup_ident: str) -> None: ...

    def render(self) -> ValueSpecText:
        return self.valuespec().value_to_html(dict(self.parameters))


class TargetTypeRegistry(Registry[type[ABCBackupTargetType]]):
    def plugin_name(self, instance: type[ABCBackupTargetType]) -> str:
        return instance.ident()


target_type_registry = TargetTypeRegistry()


class BackupTargetLocal(ABCBackupTargetType):
    def __init__(self, params: LocalTargetParams) -> None:
        self._params = params
        self._local_target = LocalTarget(TargetId(""), params)

    @property
    def parameters(self) -> LocalTargetParams:
        return self._params

    @property
    def target(self) -> LocalTarget:
        return self._local_target

    @staticmethod
    def ident() -> str:
        return "local"

    @staticmethod
    def title() -> str:
        return _("Local path")

    @classmethod
    def dictionary_elements(cls) -> DictionaryElements:
        yield from _local_directory_configuration_elements(77)

    def validate(self, varprefix: str) -> None:
        _validate_local_target(
            self.target,
            varprefix,
        )

    def remove_backup(self, backup_ident: str) -> None:
        _check_if_target_ready(self.target)
        shutil.rmtree("{}/{}".format(self.parameters["path"], backup_ident))


class ABCBackupTargetRemote(ABCBackupTargetType, Generic[TRemoteParams, TRemoteStorage]):
    # align text fields with one valuespec nesting level with _OUTER_TEXT_FIELD_SIZE on the right
    _INNER_TEXT_FIELD_SIZE = 74
    # align password fields with one valuespec nesting level with _OUTER_TEXT_FIELD_SIZE on the
    # right
    _INNER_PASSWORD_FIELD_SIZE = 61

    def __init__(self, params: RemoteTargetParams) -> None:
        self._params = params
        self._target = self._instantiate_target(params)

    @property
    def parameters(self) -> RemoteTargetParams:
        return self._params

    @property
    def target(self) -> RemoteTarget[TRemoteParams, TRemoteStorage]:
        return self._target

    @classmethod
    def dictionary_elements(cls) -> DictionaryElements:
        yield (
            "remote",
            Dictionary(
                title=_("Remote configuration"),
                elements=cls._remote_dictionary_elements(),
                optional_keys=[],
            ),
        )
        yield (
            "temp_folder",
            Dictionary(
                elements=_local_directory_configuration_elements(cls._INNER_TEXT_FIELD_SIZE),
                title=_("Temporary local destination"),
                help=_(
                    "This directory will be used for temporarily storing backups before "
                    "uploading and after downloading. You can for example use the <tt>/tmp</tt> "
                    "directory. Please note that Checkmk will not clean up this directory."
                ),
                optional_keys=[],
            ),
        )

    def remove_backup(self, backup_ident: str) -> None:
        backup_info = self.backups().get(backup_ident)
        for remote_key in (
            Path(backup_ident) / BACKUP_INFO_FILENAME,
            Path(backup_ident) / backup_info.filename,
        ):
            try:
                self.target.remote_storage.remove(remote_key)
            except Exception as e:
                raise MKGeneralException(
                    f"Removal of {remote_key} in remote storage failed. Original error: {e}"
                )

    def validate(self, varprefix: str) -> None:
        _validate_remote_target(self.target, varprefix)

    @staticmethod
    @abc.abstractmethod
    def _instantiate_target(
        params: RemoteTargetParams,
    ) -> RemoteTarget[TRemoteParams, TRemoteStorage]: ...

    @classmethod
    @abc.abstractmethod
    def _remote_dictionary_elements(cls) -> DictionaryElements: ...


class BackupTargetAWSS3Bucket(ABCBackupTargetRemote[S3Params, S3Bucket]):
    @staticmethod
    def ident() -> str:
        return "aws_s3_bucket"

    @classmethod
    def title(cls) -> str:
        return _("AWS S3 Bucket")

    @staticmethod
    def _instantiate_target(params: RemoteTargetParams[S3Params]) -> S3Target:
        return S3Target(TargetId(""), params)

    @classmethod
    def _remote_dictionary_elements(cls) -> DictionaryElements:
        yield (
            "access_key",
            TextInput(
                title=_("Access key"),
                help=_("The access key for your AWS account"),
                allow_empty=False,
                size=cls._INNER_TEXT_FIELD_SIZE,
            ),
        )
        yield (
            "secret",
            IndividualOrStoredPassword(
                title=_("Secret key"),
                help=_("The secret key for your AWS account"),
                allow_empty=False,
                size=cls._INNER_PASSWORD_FIELD_SIZE,
            ),
        )
        yield (
            "bucket",
            TextInput(
                title=_("Bucket name"),
                allow_empty=False,
                size=cls._INNER_TEXT_FIELD_SIZE,
            ),
        )


class BackupTargetAzureBlobStorage(ABCBackupTargetRemote[BlobStorageParams, BlobStorage]):
    @staticmethod
    def ident() -> str:
        return "azure_blob_storage"

    @classmethod
    def title(cls) -> str:
        return _("Azure Blob Storage")

    @staticmethod
    def _instantiate_target(
        params: RemoteTargetParams[BlobStorageParams],
    ) -> BlobStorageTarget:
        return BlobStorageTarget(TargetId(""), params)

    @classmethod
    def _remote_dictionary_elements(cls) -> DictionaryElements:
        yield (
            "storage_account_name",
            TextInput(
                title=_("Storage account name"),
                allow_empty=False,
                size=cls._INNER_TEXT_FIELD_SIZE,
            ),
        )
        yield (
            "container",
            TextInput(
                title=_("Container name"),
                allow_empty=False,
                size=cls._INNER_TEXT_FIELD_SIZE,
            ),
        )
        yield (
            "credentials",
            CascadingDropdown(
                title=_("Credentials"),
                choices=[
                    (
                        "shared_key",
                        _("Storage account shared key"),
                        IndividualOrStoredPassword(
                            title=_("Shared key"),
                            allow_empty=False,
                            size=cls._INNER_PASSWORD_FIELD_SIZE,
                        ),
                    ),
                    # Do not use cls._INNER_TEXT_FIELD_SIZE / cls._INNER_PASSWORD_FIELD_SIZE below,
                    # since we are now at valuespec nesting level 2.
                    (
                        "active_directory",
                        _("Active Directory credentials"),
                        Dictionary(
                            elements=[
                                (
                                    "client_id",
                                    TextInput(
                                        title=_("Application (client) ID"),
                                        allow_empty=False,
                                        size=71,
                                    ),
                                ),
                                (
                                    "tenant_id",
                                    TextInput(
                                        title=_("Directory (tenant) ID"),
                                        allow_empty=False,
                                        size=71,
                                    ),
                                ),
                                (
                                    "client_secret",
                                    IndividualOrStoredPassword(
                                        title=_("Client secret"),
                                        allow_empty=False,
                                        size=58,
                                    ),
                                ),
                            ],
                            optional_keys=[],
                        ),
                    ),
                ],
            ),
        )


def _local_directory_configuration_elements(
    directory_field_size: int,
) -> DictionaryElements:
    yield (
        "path",
        AbsoluteDirname(
            title=_("Directory to save the backup to"),
            help=_(
                "This can be a local directory of your choice. You can also use this "
                "option if you want to save your backup to a network share using "
                "NFS, Samba or similar. But you will have to care about mounting the "
                "network share on your own."
            ),
            allow_empty=False,
            size=directory_field_size,
        ),
    )
    yield (
        "is_mountpoint",
        Checkbox(
            title=_("Mountpoint"),
            label=_("Is mountpoint"),
            help=_(
                "When this is checked, the backup ensures that the configured path "
                "is a mountpoint. If there is no active mount on the path, the backup "
                "fails with an error message."
            ),
            default_value=True,
        ),
    )


def _check_if_target_ready(target: TargetProtocol, varprefix: str | None = None) -> None:
    try:
        target.check_ready()
    except MKGeneralException as e:
        raise MKUserError(varprefix, str(e))


def _validate_local_target(local_target: LocalTarget, varprefix: str) -> None:
    _check_if_target_ready(local_target, varprefix=varprefix)
    _validate_local_write_access(local_target.path, varprefix)


def _validate_local_write_access(path: Path, varprefix: str) -> None:
    with _write_access_test_file(path) as test_file_path:
        try:
            test_file_path.write_bytes(b"")
        except OSError:
            if cmk_version.is_cma():
                raise MKUserError(
                    varprefix,
                    _(
                        "Failed to write to the configured directory. The target directory needs "
                        "to be writable."
                    ),
                )
            raise MKUserError(
                varprefix,
                _(
                    "Failed to write to the configured directory. The site user needs to be able to "
                    "write the target directory. The recommended way is to make it writable by the "
                    'group "omd".'
                ),
            )


def _validate_remote_target(
    remote_target: RemoteTarget[TRemoteParams, TRemoteStorage],
    varprefix: str,
) -> None:
    _check_if_target_ready(remote_target, varprefix=varprefix)
    _validate_local_write_access(remote_target.local_target.path, varprefix)

    with _write_access_test_file(remote_target.local_target.path) as local_test_file_path:
        local_test_file_path.write_bytes(b"")
        remote_key = Path(local_test_file_path.name)
        try:
            remote_target.remote_storage.upload(local_test_file_path, remote_key)
        except Exception as e:
            raise MKUserError(
                varprefix,
                _("File upload test for remote storage failed. Original error message: %s") % e,
            )
        try:
            remote_target.remote_storage.download(remote_key, remote_target.local_target.path)
        except Exception as e:
            raise MKUserError(
                varprefix,
                _("File download test for remote storage failed. Original error message: %s") % e,
            )
        try:
            remote_target.remote_storage.remove(remote_key)
        except Exception as e:
            raise MKUserError(
                varprefix,
                _("File removal test for remote storage failed. Original error message: %s") % e,
            )


@contextlib.contextmanager
def _write_access_test_file(path: Path) -> Iterator[Path]:
    test_file_path = path / (f"write_test_{int(time.time())}")
    try:
        yield test_file_path
    finally:
        test_file_path.unlink(missing_ok=True)


# .
#   .--Targets-------------------------------------------------------------.
#   |                  _____                    _                          |
#   |                 |_   _|_ _ _ __ __ _  ___| |_ ___                    |
#   |                   | |/ _` | '__/ _` |/ _ \ __/ __|                   |
#   |                   | | (_| | | | (_| |  __/ |_\__ \                   |
#   |                   |_|\__,_|_|  \__, |\___|\__|___/                   |
#   |                                |___/                                 |
#   +----------------------------------------------------------------------+
#   | Specifying backup targets, the user tells the backup system which    |
#   | destinations can be used for the backups. Each destination has it's  |
#   | own protocol and specific parameters to specify how to backup.       |
#   '----------------------------------------------------------------------'


class Target:
    def __init__(self, ident: TargetId, config: TargetConfig) -> None:
        self.ident: Final = ident
        self.config: Final = config

    @property
    def title(self) -> str:
        return self.config["title"]

    def _target_type(self) -> ABCBackupTargetType:
        target_type_ident, target_params = self.config["remote"]
        try:
            target_type = target_type_registry[target_type_ident]
        except KeyError:
            raise MKUserError(
                None,
                _("Unknown target type: %s. Available types: %s.")
                % (
                    target_type_ident,
                    ", ".join(target_type_registry),
                ),
            )
        return target_type(target_params)

    def backups(self) -> _Backups:
        return self._target_type().backups()

    def remove_backup(self, backup_ident: str) -> None:
        self._target_type().remove_backup(backup_ident)

    def validate(self, varprefix: str) -> None:
        self._target_type().validate(varprefix)

    def render_destination(self) -> ValueSpecText:
        return self._target_type().render()

    def render_type(self) -> str:
        return self._target_type().title()


def _show_site_and_system_targets(config: Config) -> None:
    _show_target_list(config.site_targets.values(), False)
    if cmk_version.is_cma():
        _show_target_list(config.cma_system_targets.values(), True)


def _show_target_list(targets: Iterable[Target], targets_are_cma: bool) -> None:
    html.h2(_("System global targets") if targets_are_cma else _("Targets"))
    if targets_are_cma:
        html.p(
            _(
                "These backup targets can not be edited here. You need to "
                "open the device backup management."
            )
        )

    with table_element(sortable=False, searchable=False) as table:
        for nr, target in enumerate(sorted(targets, key=lambda t: t.ident)):
            table.row()
            table.cell("#", css=["narrow nowrap"])
            html.write_text_permissive(nr)
            table.cell(_("Actions"), css=["buttons"])
            restore_url = makeuri_contextless(
                request,
                [("mode", "backup_restore"), ("target", target.ident)],
            )
            html.icon_button(
                restore_url,
                _("Restore from this backup target"),
                {
                    "icon": "backup",
                    "emblem": "refresh",
                },
            )

            if not targets_are_cma:
                delete_url = make_confirm_delete_link(
                    url=makeactionuri_contextless(
                        request,
                        transactions,
                        [("mode", "backup_targets"), ("target", target.ident)],
                    ),
                    title=_("Delete target #%d") % nr,
                    suffix=target.title,
                    message=_("ID: %s") % target.ident,
                )
                edit_url = makeuri_contextless(
                    request,
                    [("mode", "edit_backup_target"), ("target", target.ident)],
                )

                html.icon_button(edit_url, _("Edit this backup target"), "edit")
                html.icon_button(delete_url, _("Delete this backup target"), "delete")

            table.cell(_("ID"), target.ident, css=["narrow nowrap"])
            table.cell(_("Title"), target.title, css=["narrow nowrap"])
            table.cell(_("Type"), target.render_type())
            table.cell(_("Destination"), target.render_destination())


class PageBackupTargets:
    def title(self) -> str:
        return _("Site backup targets")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="targets",
                    title=_("Targets"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add target"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add target"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        makeuri_contextless(
                                            request,
                                            [("mode", "edit_backup_target")],
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return HTTPRedirect(makeuri_contextless(request, [("mode", "backup_targets")]))

        if not (ident := request.var("target")):
            raise MKUserError("target", _("This backup target does not exist."))

        config = Config.load()

        try:
            target = config.site_targets[TargetId(ident)]
        except KeyError:
            raise MKUserError("target", _("This backup target does not exist."))

        self._verify_not_used(config, target.ident)

        with contextlib.suppress(KeyError):
            config.delete_target(target.ident)

        flash(_("The target has been deleted."))
        return HTTPRedirect(makeuri_contextless(request, [("mode", "backup_targets")]))

    def _verify_not_used(self, config: Config, target_id: TargetId) -> None:
        if jobs := [job for job in config.jobs.values() if job.target_ident() == target_id]:
            raise MKUserError(
                "target",
                _("You can not delete this target because it is used by these backup jobs: %s")
                % ", ".join(job.title for job in jobs),
            )

    def page(self) -> None:
        _show_site_and_system_targets(Config.load())


class PageEditBackupTarget:
    def __init__(self) -> None:
        super().__init__()
        target_ident = request.var("target")

        if target_ident is not None:
            target_ident = TargetId(target_ident)
            try:
                target = Config.load().site_targets[target_ident]
            except KeyError:
                raise MKUserError("target", _("This backup target does not exist."))

            self._new = False
            self._ident: TargetId | None = target_ident
            self._target_cfg: TargetConfig | dict[str, object] = target.config
            self._title = _("Edit backup target: %s") % target.title
        else:
            self._new = True
            self._ident = None
            self._target_cfg = {}
            self._title = _("Add backup target")

    def title(self) -> str:
        return self._title

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Target"), breadcrumb, form_name="edit_target", button_name="_save"
        )

    def vs_backup_target(self, config: Config) -> Dictionary:
        if self._new:
            ident_attr: list[tuple[str, TextInput | FixedValue]] = [
                (
                    "ident",
                    ID(
                        title=_("Unique ID"),
                        help=_(
                            "The ID of the target must be a unique text. It will be used as an internal key "
                            "when objects refer to the target."
                        ),
                        allow_empty=False,
                        size=_OUTER_TEXT_FIELD_SIZE,
                        validate=lambda ident, varprefix: self.validate_backup_target_ident(
                            config,
                            ident,
                            varprefix,
                        ),
                    ),
                ),
            ]
        else:
            ident_attr = [
                (
                    "ident",
                    FixedValue(
                        value=self._ident,
                        title=_("Unique ID"),
                    ),
                ),
            ]

        return Dictionary(
            title=_("Backup target"),
            elements=ident_attr
            + [
                (
                    "title",
                    TextInput(
                        title=_("Title"),
                        allow_empty=False,
                        size=_OUTER_TEXT_FIELD_SIZE,
                    ),
                ),
                (
                    "remote",
                    CascadingDropdown(
                        title=_("Destination"),
                        choices=[
                            (
                                target_type.ident(),
                                target_type.title(),
                                target_type.valuespec(),
                            )
                            for target_type in target_type_registry.values()
                        ],
                    ),
                ),
            ],
            optional_keys=[],
            render="form",
        )

    def validate_backup_target_ident(self, config: Config, value: str, varprefix: str) -> None:
        if TargetId(value) in config.site_targets:
            raise MKUserError(varprefix, _("This ID is already used by another backup target."))

    def action(self) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return HTTPRedirect(makeuri_contextless(request, [("mode", "backup_targets")]))

        backup_config = Config.load()
        vs = self.vs_backup_target(backup_config)

        target_config = vs.from_html_vars("edit_target")
        vs.validate_value(target_config, "edit_target")

        if "ident" in target_config:
            self._ident = TargetId(target_config.pop("ident"))
        self._target_cfg = cast(TargetConfig, target_config)

        if self._ident is None:
            raise MKGeneralException("Cannot create or modify job without identifier")

        backup_config.add_target(
            Target(
                self._ident,
                self._target_cfg,
            )
        )

        return HTTPRedirect(makeuri_contextless(request, [("mode", "backup_targets")]))

    def page(self) -> None:
        with html.form_context("edit_target", method="POST"):
            html.prevent_password_auto_completion()

            vs = self.vs_backup_target(Config.load())

            vs.render_input("edit_target", dict(self._target_cfg))
            vs.set_focus("edit_target")
            forms.end()

            html.hidden_fields()


# .
#   .--Key Management------------------------------------------------------.
#   |             _  __            __  __                 _                |
#   |            | |/ /___ _   _  |  \/  | __ _ _ __ ___ | |_              |
#   |            | ' // _ \ | | | | |\/| |/ _` | '_ ` _ \| __|             |
#   |            | . \  __/ |_| | | |  | | (_| | | | | | | |_              |
#   |            |_|\_\___|\__, | |_|  |_|\__, |_| |_| |_|\__|             |
#   |                      |___/          |___/                            |
#   +----------------------------------------------------------------------+
#   | Managing of the keys that are used for signing the agents            |
#   '----------------------------------------------------------------------'


class BackupKeypairStore(key_mgmt.KeypairStore):
    pass


class PageBackupKeyManagement(key_mgmt.PageKeyManagement):
    edit_mode = "backup_edit_key"
    upload_mode = "backup_upload_key"
    download_mode = "backup_download_key"

    def title(self) -> str:
        return _("Keys for backups")

    def page(self) -> None:
        show_key_download_warning(self.key_store.load())
        super().page()

    def _key_in_use(self, key_id: int, key: Key) -> bool:
        for job in Config.load().jobs.values():
            if (job_key_id := job.key_ident()) and str(key_id) == job_key_id:
                return True
        return False

    def _table_title(self) -> str:
        return self.title()

    def _delete_confirm_msg(self) -> str:
        return _(
            "<b>Beware:</b> Deleting this key "
            "means that you will not be able to encrypt or sign backups with the key. "
            "Already created backups which have been encrypted, can not be decrypted "
            "without access to this key. So please be sure that you either have a "
            "backup or don't need this key anymore."
        )

    def _delete_confirm_title(self, nr: int) -> str:
        return _("Delete backup key #%d") % nr

    @property
    def component_name(self) -> CertManagementEvent.ComponentType:
        return "backup encryption keys"


class PageBackupEditKey(key_mgmt.PageEditKey):
    back_mode = "backup_keys"

    def title(self) -> str:
        return _("Create backup key")

    def _passphrase_help(self) -> str:
        return _(
            "The backup key will be stored encrypted using this passphrase on your "
            "disk. The passphrase will not be stored anywhere. The backup will use "
            "the public key part of the key to sign or encrypt the backups. If you "
            "encrypt a backup, you will need the private key part together with the "
            "passphrase to decrypt the backup."
        )

    @property
    def component_name(self) -> CertManagementEvent.ComponentType:
        return "backup encryption keys"


class PageBackupUploadKey(key_mgmt.PageUploadKey):
    back_mode = "backup_keys"

    def title(self) -> str:
        return _("Upload backup key")

    def _passphrase_help(self) -> str:
        return _(
            "The backup key will be stored encrypted using this passphrase on your "
            "disk. The passphrase will not be stored anywhere. The backup will use "
            "the public key part of the key to sign or encrypt the backups. If you "
            "encrypt a backup, you will need the private key part together with the "
            "passphrase to decrypt the backup."
        )

    @property
    def component_name(self) -> CertManagementEvent.ComponentType:
        return "backup encryption keys"


class PageBackupDownloadKey(key_mgmt.PageDownloadKey):
    back_mode = "backup_keys"

    def title(self) -> str:
        return _("Download backup key")

    def _send_download(self, keys: dict[int, Key], key_id: int) -> None:
        super()._send_download(keys, key_id)
        keys[key_id].not_downloaded = False
        self.key_store.save(keys)

    def _file_name(self, key_id: int, key: Key) -> str:
        return f"Check_MK-{hostname()}-{omd_site()}-backup_key-{key_id}.pem"


def show_key_download_warning(keys: dict[int, Key]) -> None:
    to_load = [k.alias for k in keys.values() if k.not_downloaded]
    if to_load:
        html.show_warning(
            _(
                "To be able to restore your encrypted backups, you need to "
                "download and keep the backup encryption keys in a safe place. "
                "If you lose your keys or the keys passphrases, your backup "
                "can not be restored.<br>"
                "The following keys have not been downloaded yet: %s"
            )
            % ", ".join(to_load)
        )


# .
#   .--Restore-------------------------------------------------------------.
#   |                  ____           _                                    |
#   |                 |  _ \ ___  ___| |_ ___  _ __ ___                    |
#   |                 | |_) / _ \/ __| __/ _ \| '__/ _ \                   |
#   |                 |  _ <  __/\__ \ || (_) | | |  __/                   |
#   |                 |_| \_\___||___/\__\___/|_|  \___|                   |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Listing backups of targets and controlling the the restore procedure |
#   '----------------------------------------------------------------------'


class RestoreJob(MKBackupJob):
    def __init__(
        self,
        target_ident: TargetId | None,
        backup_ident: str | None,
        passphrase: PasswordType | None = None,
    ) -> None:
        super().__init__()
        self._target_ident = target_ident
        self._backup_ident = backup_ident
        self._passphrase = passphrase

    def title(self) -> str:
        return _("Restore")

    def state_file_path(self) -> Path:
        return Path("/tmp/restore-%s.state" % os.environ["OMD_SITE"])  # nosec B108 # BNS:13b2c8

    def complete(self) -> None:
        self.cleanup()

    def _start_command(self) -> Sequence[str | Path]:
        assert self._target_ident is not None
        assert self._backup_ident is not None
        return [
            mkbackup_path(),
            "restore",
            "--background",
            self._target_ident,
            self._backup_ident,
        ]

    def start(self, **env_updates: str) -> None:
        if self._passphrase:
            env_updates["MKBACKUP_PASSPHRASE"] = self._passphrase.raw
        super().start(**env_updates)


class PageBackupRestore:
    def __init__(self, key_store: key_mgmt.KeypairStore) -> None:
        super().__init__()
        self.key_store = key_store
        self._load_target()
        if self._target:
            self._backups = self._target.backups()
        else:
            self._backups = _Backups({}, timed_out=False)

    def _load_target(self) -> None:
        ident = request.var("target")
        if ident is None:
            self._target_ident = None
            self._target = None
            return

        self._target_ident = TargetId(ident)

        try:
            self._target = self._get_target(self._target_ident)
        except KeyError:
            raise MKUserError("target_p_target", _("This backup target does not exist."))

    def _get_target(self, target_ident: TargetId) -> Target:
        return Config.load().all_targets[target_ident]

    def title(self) -> str:
        if not self._target:
            return _("Site restore")
        return _("Restore from target: %s") % self._target.title

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="restore",
                    title=_("Restore"),
                    topics=[
                        PageMenuTopic(
                            title=_("Restore job"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Stop"),
                                    icon_name="backup_stop",
                                    item=make_simple_link(
                                        make_confirm_delete_link(
                                            url=makeactionuri(
                                                request,
                                                transactions,
                                                [("_action", "stop")],
                                            ),
                                            title=_("Stop restore of backup"),
                                            message=_(
                                                "<b>Beware:</b> This will leave your environment in an undefined state."
                                            ),
                                            confirm_button=_("Stop"),
                                            cancel_button=_("Cancel"),
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                    is_enabled=self._restore_is_running(),
                                ),
                                PageMenuEntry(
                                    title=_("Complete the restore"),
                                    icon_name="save",
                                    item=make_simple_link(
                                        makeactionuri(
                                            request,
                                            transactions,
                                            [("_action", "complete")],
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                    is_enabled=self._restore_was_started(),
                                ),
                            ],
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        action = request.var("_action")
        backup_ident = request.var("_backup")

        if action is None:
            return None  # Only choosen the target

        if not transactions.check_transaction():
            return HTTPRedirect(makeuri_contextless(request, [("mode", "backup_restore")]))

        if action == "delete":
            self._delete_backup(backup_ident)

        elif action == "complete":
            self._complete_restore(backup_ident)

        elif action == "start":
            return self._start_restore(backup_ident)

        elif action == "stop":
            self._stop_restore(backup_ident)

        return HTTPRedirect(makeuri_contextless(request, [("mode", "backup_restore")]))

    def _delete_backup(self, backup_ident: str | None) -> None:
        if self._restore_is_running():
            raise MKUserError(
                None,
                _(
                    "A restore is currently running. You can only delete "
                    "backups while no restore is running."
                ),
            )

        if self._target is None:
            raise Exception("no backup target")
        if backup_ident not in self._backups.backups:
            if self._backups.timed_out:
                raise MKGeneralException(
                    "Unable to find backup to delete. "
                    "This may be because the listing of remote backups timed out. "
                    "There may be too many files present at the remote target."
                )
            raise MKUserError(None, _("This backup does not exist."))

        assert backup_ident is not None

        self._target.remove_backup(backup_ident)
        flash(_("The backup has been deleted."))

    def _restore_was_started(self) -> bool:
        return RestoreJob(self._target_ident, None).was_started()

    def _restore_is_running(self) -> bool:
        return RestoreJob(self._target_ident, None).is_running()

    def _start_restore(self, backup_ident: str | None) -> ActionResult:
        if self._target is None:
            raise Exception("no backup target")
        assert backup_ident is not None
        backup_info = self._backups.get(backup_ident)
        if (key_digest := backup_info.config["encrypt"]) is not None:
            return self._start_encrypted_restore(backup_ident, key_digest)
        return self._start_unencrypted_restore(backup_ident)

    def _complete_restore(self, backup_ident: str | None) -> None:
        RestoreJob(self._target_ident, None).complete()

    def _start_encrypted_restore(self, backup_ident: str, key_digest: str) -> ActionResult:
        try:
            _key_id, key = self.key_store.get_key_by_digest(key_digest)
        except KeyError:
            raise MKUserError(
                None,
                _(
                    "The key with the fingerprint %s which is needed to decrypt "
                    "the backup is misssing."
                )
                % key_digest,
            )

        if html.form_submitted("key"):
            try:
                value = self._vs_key().from_html_vars("_key")
                if request.has_var("_key_p_passphrase"):
                    self._vs_key().validate_value(value, "_key")
                    passphrase = PasswordType(value["passphrase"])

                    # Validate the passphrase
                    try:
                        key.to_certificate_with_private_key(passphrase)
                    except (PEMDecodingError, ValueError):
                        raise MKUserError("_key_p_passphrase", _("Invalid passphrase"))

                    transactions.check_transaction()  # invalidate transid
                    RestoreJob(self._target_ident, backup_ident, passphrase).start()
                    flash(_("The restore has been started."))
                    return HTTPRedirect(makeuri_contextless(request, [("mode", "backup_restore")]))
            except MKUserError as e:
                user_errors.add(e)

        # Special handling for Checkmk / CMA differences
        title = _("Insert passphrase")
        breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_setup(), title)
        make_header(html, title, breadcrumb, PageMenu(dropdowns=[], breadcrumb=breadcrumb))

        html.show_user_errors()
        html.p(
            _(
                "To be able to decrypt and restore the encrypted backup, you need to enter the "
                "passphrase of the encryption key."
            )
        )
        with html.form_context("key", method="GET"):
            html.hidden_field("_action", "start")
            html.hidden_field("_backup", backup_ident)
            html.prevent_password_auto_completion()
            self._vs_key().render_input("_key", {})
            html.button("upload", _("Start restore"))
            self._vs_key().set_focus("_key")
            html.hidden_fields()
        html.footer()
        return FinalizeRequest(code=200)

    def _vs_key(self) -> Dictionary:
        return Dictionary(
            title=_("Properties"),
            elements=[
                (
                    "passphrase",
                    Password(
                        title=_("Passphrase"),
                        allow_empty=False,
                        is_stored_plain=False,
                    ),
                ),
            ],
            optional_keys=False,
            render="form",
        )

    def _start_unencrypted_restore(self, backup_ident: str) -> ActionResult:
        RestoreJob(self._target_ident, backup_ident).start()
        flash(_("The restore has been started."))
        return HTTPRedirect(makeuri_contextless(request, [("mode", "backup_restore")]))

    def _stop_restore(self, backup_ident: str | None) -> None:
        RestoreJob(self._target_ident, backup_ident).stop()
        flash(_("The restore has been stopped."))

    def page(self) -> None:
        if self._restore_was_started():
            self._show_restore_progress()

        elif self._target:
            self._show_backup_list()

        else:
            self._show_target_list()

    def _show_target_list(self) -> None:
        html.p(_("Please choose a target to perform the restore from."))
        _show_site_and_system_targets(Config.load())

    def _show_backup_list(self) -> None:
        assert self._target is not None
        if self._backups.timed_out:
            html.show_warning(
                "The following list is not complete "
                "as the listing of remote backups timed "
                "out. There may be too many files present "
                "at the remote target. To make sure all "
                "backups are listed, remove unneeded files "
                "at the remote target."
            )
        with table_element(sortable=False, searchable=False) as table:
            for backup_ident, info in sorted(self._backups.backups.items()):
                table.row()
                table.cell(_("Actions"), css=["buttons"])

                from_info = f"{info.hostname} (Site: {info.site_id}, Version: {info.site_version})"
                delete_url = make_confirm_delete_link(
                    url=makeactionuri(
                        request,
                        transactions,
                        [("_action", "delete"), ("_backup", backup_ident)],
                    ),
                    title=_("Delete backup"),
                    message=_("From: %s") % from_info,
                    suffix=backup_ident,
                )

                html.icon_button(delete_url, _("Delete this backup"), "delete")

                start_url = make_confirm_link(
                    url=makeactionuri(
                        request,
                        transactions,
                        [("_action", "start"), ("_backup", backup_ident)],
                    ),
                    title=_("Start restore of backup"),
                    suffix=backup_ident,
                    message=_("From: %s") % from_info,
                    confirm_button=_("Start"),
                    cancel_button=_("Cancel"),
                )

                html.icon_button(
                    start_url,
                    _("Start restore of this backup"),
                    {
                        "icon": "backup",
                        "emblem": "refresh",
                    },
                )

                table.cell(_("Backup-ID"), backup_ident)
                table.cell(_("From"), from_info)
                table.cell(_("Finished"), render.date_and_time(info.finished))
                table.cell(_("Size"), render.fmt_bytes(info.size))
                table.cell(_("Encrypted"))
                if (encrypt := info.config["encrypt"]) is not None:
                    html.write_text_permissive(encrypt)
                else:
                    html.write_text_permissive(_("No"))

    def _show_restore_progress(self) -> None:
        PageBackupRestoreState().page()


class PageBackupRestoreState(PageAbstractMKBackupJobState[RestoreJob]):
    def __init__(self) -> None:
        super().__init__()
        self._job = RestoreJob(None, None)  # TODO: target_ident and backup_ident needed?
        self._ident = "restore"

    @property
    def ident(self) -> str:
        return self._ident

    @property
    def job(self) -> RestoreJob:
        return self._job
