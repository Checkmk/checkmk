#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Pages for managing backup and restore of WATO"""

import cmk.utils.paths

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.backup as backup
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.wato.utils.context_buttons import home_button
from cmk.gui.valuespec import Checkbox
from cmk.gui.pages import page_registry, AjaxPage

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
    SiteBackupJobs,
)


class SiteBackupTargets(backup.Targets):
    def __init__(self):
        super(SiteBackupTargets, self).__init__(backup.site_config_path())


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
        home_button()


@mode_registry.register
class ModeBackupTargets(backup.PageBackupTargets, WatoMode):
    @classmethod
    def name(cls):
        return "backup_targets"

    @classmethod
    def permissions(cls):
        return ["backups"]

    def title(self):
        return _("Site backup targets")

    def targets(self):
        return SiteBackupTargets()

    def jobs(self):
        return SiteBackupJobs()

    def page(self):
        self.targets().show_list()
        backup.SystemBackupTargetsReadOnly().show_list(editable=False,
                                                       title=_("System global targets"))


@mode_registry.register
class ModeEditBackupTarget(backup.PageEditBackupTarget, WatoMode):
    @classmethod
    def name(cls):
        return "edit_backup_target"

    @classmethod
    def permissions(cls):
        return ["backups"]

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
            ("no_history",
             Checkbox(
                 title=_("Do not backup historical data"),
                 help=_(
                     "You may use this option to create a much smaller partial backup of the site."
                 ),
                 label=_(
                     "Do not backup metric data (RRD files), the monitoring history and log files"),
             )),
        ]


@mode_registry.register
class ModeBackupJobState(backup.PageBackupJobState, WatoMode):
    @classmethod
    def name(cls):
        return "backup_job_state"

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
        self.page()

    def page(self):
        config.user.need_permission("wato.backups")
        if html.request.var("job") == "restore":
            page = backup.PageBackupRestoreState()
        else:
            page = ModeBackupJobState()
        page.show_job_details()


class SiteBackupKeypairStore(backup.BackupKeypairStore):
    def __init__(self):
        super(SiteBackupKeypairStore,
              self).__init__(cmk.utils.paths.default_config_dir + "/backup_keys.mk", "keys")


@mode_registry.register
class ModeBackupKeyManagement(SiteBackupKeypairStore, backup.PageBackupKeyManagement, WatoMode):
    @classmethod
    def name(cls):
        return "backup_keys"

    @classmethod
    def permissions(cls):
        return ["backups"]

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


@mode_registry.register
class ModeBackupUploadKey(SiteBackupKeypairStore, backup.PageBackupUploadKey, WatoMode):
    @classmethod
    def name(cls):
        return "backup_upload_key"

    @classmethod
    def permissions(cls):
        return ["backups"]

    def _upload_key(self, key_file, value):
        watolib.log_audit(None, "upload-backup-key", _("Uploaded backup key '%s'") % value["alias"])
        super(ModeBackupUploadKey, self)._upload_key(key_file, value)


@mode_registry.register
class ModeBackupDownloadKey(SiteBackupKeypairStore, backup.PageBackupDownloadKey, WatoMode):
    @classmethod
    def name(cls):
        return "backup_download_key"

    @classmethod
    def permissions(cls):
        return ["backups"]

    def _file_name(self, key_id, key):
        return "Check_MK-%s-%s-backup_key-%s.pem" % (backup.hostname(), config.omd_site(), key_id)


@mode_registry.register
class ModeBackupRestore(backup.PageBackupRestore, WatoMode):
    @classmethod
    def name(cls):
        return "backup_restore"

    @classmethod
    def permissions(cls):
        return ["backups"]

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

    def _show_target_list(self):
        super(ModeBackupRestore, self)._show_target_list()
        backup.SystemBackupTargetsReadOnly().show_list(editable=False,
                                                       title=_("System global targets"))

    def _show_backup_list(self):
        self._target.show_backup_list("Check_MK")
