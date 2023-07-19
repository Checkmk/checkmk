#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pages for managing backup and restore of WATO"""

from collections.abc import Collection

import cmk.utils.paths
from cmk.utils.crypto.password import Password

import cmk.gui.backup as backup
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, PageRegistry, PageResult
from cmk.gui.plugins.wato.utils import mode_registry, WatoMode
from cmk.gui.type_defs import PermissionName
from cmk.gui.watolib.audit_log import log_audit


def register(page_registry: PageRegistry) -> None:
    page_registry.register_page("ajax_backup_job_state")(PageAjaxBackupJobState)


@mode_registry.register
class ModeBackup(backup.PageBackup, WatoMode):
    @classmethod
    def name(cls) -> str:
        return "backup"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["backups"]

    def __init__(self) -> None:
        super().__init__(key_store=make_site_backup_keypair_store())

    def title(self) -> str:
        return _("Site backup")


@mode_registry.register
class ModeBackupTargets(backup.PageBackupTargets, WatoMode):
    @classmethod
    def name(cls) -> str:
        return "backup_targets"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeBackup


@mode_registry.register
class ModeEditBackupTarget(backup.PageEditBackupTarget, WatoMode):
    @classmethod
    def name(cls) -> str:
        return "edit_backup_target"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeBackupTargets


@mode_registry.register
class ModeEditBackupJob(backup.PageEditBackupJob, WatoMode):
    @classmethod
    def name(cls) -> str:
        return "edit_backup_job"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeBackup

    def __init__(self) -> None:
        super().__init__(key_store=make_site_backup_keypair_store())


@mode_registry.register
class ModeBackupJobState(backup.PageBackupJobState, WatoMode):
    @classmethod
    def name(cls) -> str:
        return "backup_job_state"

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeBackup

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["backups"]


class PageAjaxBackupJobState(AjaxPage):
    # TODO: Better use AjaxPage.handle_page() for standard AJAX call error handling. This
    # would need larger refactoring of the generic html.popup_trigger() mechanism.
    def handle_page(self) -> None:
        self._handle_exc(self.page)

    def page(self) -> PageResult:  # pylint: disable=useless-return
        user.need_permission("wato.backups")
        if request.var("job") == "restore":
            page: backup.PageAbstractMKBackupJobState = backup.PageBackupRestoreState()
        else:
            page = ModeBackupJobState()
        page.show_job_details()
        return None


def make_site_backup_keypair_store() -> backup.BackupKeypairStore:
    return backup.BackupKeypairStore(cmk.utils.paths.default_config_dir + "/backup_keys.mk", "keys")


@mode_registry.register
class ModeBackupKeyManagement(backup.PageBackupKeyManagement, WatoMode):
    @classmethod
    def name(cls) -> str:
        return "backup_keys"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeBackup

    def __init__(self) -> None:
        super().__init__(key_store=make_site_backup_keypair_store())


@mode_registry.register
class ModeBackupEditKey(backup.PageBackupEditKey, WatoMode):
    @classmethod
    def name(cls) -> str:
        return "backup_edit_key"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeBackupKeyManagement

    def __init__(self) -> None:
        super().__init__(key_store=make_site_backup_keypair_store())


@mode_registry.register
class ModeBackupUploadKey(backup.PageBackupUploadKey, WatoMode):
    @classmethod
    def name(cls) -> str:
        return "backup_upload_key"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeBackupKeyManagement

    def __init__(self) -> None:
        super().__init__(key_store=make_site_backup_keypair_store())

    def _upload_key(self, key_file: str, alias: str, passphrase: Password) -> None:
        log_audit("upload-backup-key", "Uploaded backup key '%s'" % alias)
        super()._upload_key(key_file, alias, passphrase)


@mode_registry.register
class ModeBackupDownloadKey(backup.PageBackupDownloadKey, WatoMode):
    @classmethod
    def name(cls) -> str:
        return "backup_download_key"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeBackupKeyManagement

    def __init__(self) -> None:
        super().__init__(key_store=make_site_backup_keypair_store())


@mode_registry.register
class ModeBackupRestore(backup.PageBackupRestore, WatoMode):
    @classmethod
    def name(cls) -> str:
        return "backup_restore"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["backups"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeBackup

    def __init__(self) -> None:
        super().__init__(key_store=make_site_backup_keypair_store())
