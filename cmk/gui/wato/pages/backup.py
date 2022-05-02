#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pages for managing backup and restore of WATO"""

from typing import Optional, Type

import cmk.utils.paths
from cmk.utils.site import omd_site

import cmk.gui.backup as backup
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, page_registry
from cmk.gui.plugins.wato.utils import mode_registry, SiteBackupJobs, WatoMode
from cmk.gui.valuespec import Checkbox
from cmk.gui.watolib.audit_log import log_audit


class SiteBackupTargets(backup.Targets):
    def __init__(self):
        super().__init__(backup.site_config_path())


@mode_registry.register
class ModeBackup(backup.PageBackup, WatoMode):
    @classmethod
    def name(cls):
        return "backup"

    @classmethod
    def permissions(cls):
        return ["backups"]

    def title(self):
        return _("Site backup")

    def jobs(self):
        return SiteBackupJobs()

    def keys(self):
        return SiteBackupKeypairStore()

    def home_button(self):
        pass


@mode_registry.register
class ModeBackupTargets(backup.PageBackupTargets, WatoMode):
    @classmethod
    def name(cls):
        return "backup_targets"

    @classmethod
    def permissions(cls):
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeBackup

    def title(self):
        return _("Site backup targets")

    def targets(self):
        return SiteBackupTargets()

    def jobs(self):
        return SiteBackupJobs()

    def page(self):
        self.targets().show_list()
        backup.SystemBackupTargetsReadOnly().show_list(
            editable=False, title=_("System global targets")
        )


@mode_registry.register
class ModeEditBackupTarget(backup.PageEditBackupTarget, WatoMode):
    @classmethod
    def name(cls):
        return "edit_backup_target"

    @classmethod
    def permissions(cls):
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeBackupTargets

    def targets(self):
        return SiteBackupTargets()


@mode_registry.register
class ModeEditBackupJob(backup.PageEditBackupJob, WatoMode):
    @classmethod
    def name(cls):
        return "edit_backup_job"

    @classmethod
    def permissions(cls):
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeBackup

    def jobs(self):
        return SiteBackupJobs()

    def targets(self):
        return SiteBackupTargets()

    def backup_target_choices(self):
        choices = self.targets().choices()

        # Only add system wide defined targets that don't conflict with
        # the site specific backup targets
        choice_dict = dict(choices)
        for key, title in backup.SystemBackupTargetsReadOnly().choices():
            if key not in choice_dict:
                choices.append((key, _("%s (system wide)") % title))

        return sorted(choices, key=lambda x_y: x_y[1].title())

    def _validate_target(self, value, varprefix):
        targets = self.targets()
        try:
            targets.get(value)
        except KeyError:
            backup.SystemBackupTargetsReadOnly().validate_target(value, varprefix)
            return

        targets.validate_target(value, varprefix)

    def keys(self):
        return SiteBackupKeypairStore()

    def custom_job_attributes(self):
        return [
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
        ]


@mode_registry.register
class ModeBackupJobState(backup.PageBackupJobState, WatoMode):
    @classmethod
    def name(cls):
        return "backup_job_state"

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeBackup

    @classmethod
    def permissions(cls):
        return ["backups"]

    def jobs(self):
        return SiteBackupJobs()


@page_registry.register_page("ajax_backup_job_state")
class ModeAjaxBackupJobState(AjaxPage):
    # TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    def handle_page(self):
        self._handle_exc(self.page)

    def page(self):
        user.need_permission("wato.backups")
        if request.var("job") == "restore":
            page: backup.PageAbstractBackupJobState = backup.PageBackupRestoreState()
        else:
            page = ModeBackupJobState()
        page.show_job_details()


class SiteBackupKeypairStore(backup.BackupKeypairStore):
    def __init__(self):
        super().__init__(cmk.utils.paths.default_config_dir + "/backup_keys.mk", "keys")


@mode_registry.register
class ModeBackupKeyManagement(SiteBackupKeypairStore, backup.PageBackupKeyManagement, WatoMode):
    @classmethod
    def name(cls):
        return "backup_keys"

    @classmethod
    def permissions(cls):
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeBackup

    def jobs(self):
        return SiteBackupJobs()


@mode_registry.register
class ModeBackupEditKey(SiteBackupKeypairStore, backup.PageBackupEditKey, WatoMode):
    @classmethod
    def name(cls):
        return "backup_edit_key"

    @classmethod
    def permissions(cls):
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeBackupKeyManagement


@mode_registry.register
class ModeBackupUploadKey(SiteBackupKeypairStore, backup.PageBackupUploadKey, WatoMode):
    @classmethod
    def name(cls):
        return "backup_upload_key"

    @classmethod
    def permissions(cls):
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeBackupKeyManagement

    def _upload_key(self, key_file, value):
        log_audit("upload-backup-key", _("Uploaded backup key '%s'") % value["alias"])
        super()._upload_key(key_file, value)


@mode_registry.register
class ModeBackupDownloadKey(SiteBackupKeypairStore, backup.PageBackupDownloadKey, WatoMode):
    @classmethod
    def name(cls):
        return "backup_download_key"

    @classmethod
    def permissions(cls):
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeBackupKeyManagement

    def _file_name(self, key_id, key):
        return "Check_MK-%s-%s-backup_key-%s.pem" % (backup.hostname(), omd_site(), key_id)


@mode_registry.register
class ModeBackupRestore(backup.PageBackupRestore, WatoMode):
    @classmethod
    def name(cls):
        return "backup_restore"

    @classmethod
    def permissions(cls):
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeBackup

    def title(self):
        if not self._target:
            return _("Site restore")
        return _("Restore from target: %s") % self._target.title()

    def targets(self):
        return SiteBackupTargets()

    def keys(self):
        return SiteBackupKeypairStore()

    def _get_target(self, target_ident):
        try:
            return self.targets().get(target_ident)
        except KeyError:
            return backup.SystemBackupTargetsReadOnly().get(target_ident)

    def _show_target_list(self) -> None:
        super()._show_target_list()
        backup.SystemBackupTargetsReadOnly().show_list(
            editable=False, title=_("System global targets")
        )

    def _show_backup_list(self) -> None:
        assert self._target is not None
        self._target.show_backup_list(only_type="Check_MK")
