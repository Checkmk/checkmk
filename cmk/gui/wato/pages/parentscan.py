#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for automatic scan of parents."""

from collections.abc import Collection
from dataclasses import dataclass
from typing import cast, Literal

from cmk.utils.paths import profile_dir

from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_form_submit_link,
    make_simple_form_page_menu,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.wato.pages.folders import ModeFolder
from cmk.gui.watolib.hosts_and_folders import (
    disk_or_search_base_folder_from_request,
    disk_or_search_folder_from_request,
    Folder,
    Host,
    SearchFolder,
)
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.gui.watolib.parent_scan import (
    ParentScanBackgroundJob,
    ParentScanSettings,
    start_parent_scan,
    WhereChoices,
)

from ._bulk_actions import get_hosts_from_checkboxes

# select: 'noexplicit' -> no explicit parents
#         'no'         -> no implicit parents
#         'ignore'     -> not important
SelectChoices = Literal["noexplicit", "no", "ignore"]


@dataclass(frozen=True)
class GUIParentScanSettings(ParentScanSettings):
    select: SelectChoices
    recurse: bool


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeParentScan)


class ModeParentScan(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "parentscan"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "parentscan"]

    def title(self) -> str:
        return _("Parent scan")

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeFolder

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(_("Parent scan"), breadcrumb)
        menu.dropdowns.insert(
            0,
            PageMenuDropdown(
                name="parent_scan",
                title=_("Action"),
                topics=[
                    PageMenuTopic(
                        title=_("Parent scan"),
                        entries=[
                            PageMenuEntry(
                                title=_("Start"),
                                icon_name="background_jobs",
                                item=make_form_submit_link("parentscan", "_start"),
                                is_shortcut=True,
                                is_suggested=True,
                                css_classes=["submit"],
                            ),
                        ],
                    ),
                ],
            ),
        )

        return menu

    def _from_vars(self) -> None:
        self._start = bool(request.var("_start"))
        # 'all' not set -> only scan checked hosts in current folder, no recursion
        # otherwise: all host in this folder, maybe recursively
        self._all = bool(request.var("all"))
        self._complete_folder = self._all

        # Ignored during initial form display
        self._settings = GUIParentScanSettings(
            recurse=html.get_checkbox("recurse") or False,
            select=cast(
                SelectChoices,
                request.get_ascii_input_mandatory(
                    "select",
                    "noexplicit",
                    allowed_values={"noexplicit", "no", "ignore"},
                ),
            ),
            where=cast(
                WhereChoices,
                request.get_ascii_input_mandatory(
                    "where",
                    "subfolder",
                    allowed_values={"nowhere", "here", "subfolder", "there"},
                ),
            ),
            alias=request.get_str_input_mandatory("alias", "").strip(),
            timeout=request.get_integer_input_mandatory("timeout", 8),
            probes=request.get_integer_input_mandatory("probes", 2),
            max_ttl=request.get_integer_input_mandatory("max_ttl", 10),
            force_explicit=html.get_checkbox("force_explicit") or False,
            ping_probes=request.get_integer_input_mandatory("ping_probes", 5),
            gateway_folder_path=None,
        )
        self._job = ParentScanBackgroundJob()
        self._folder = disk_or_search_folder_from_request(
            request.var("folder"), request.get_ascii_input("host")
        )

    def action(self) -> ActionResult:
        check_csrf_token()

        try:
            transactions.check_transaction()

            user.save_file("parentscan", self._settings)

            start_parent_scan(self._get_selected_hosts(), self._job, self._settings)
        except Exception as e:
            if active_config.debug:
                raise
            logger.exception("Failed to start parent scan")
            raise MKUserError(
                None,
                _("Failed to start parent scan: %s") % ("%s" % e).replace("\n", "\n<br>"),
            )

        raise HTTPRedirect(self._job.detail_url())

    def _get_selected_hosts(self) -> list[Host]:
        if not request.var("all"):
            return [
                host
                for host in get_hosts_from_checkboxes(self._folder)
                if self._include_host(host, self._settings.select)
            ]
        return self._recurse_hosts(
            self._folder,
            self._settings.recurse,
            self._settings.select,
        )

    def _include_host(self, host: Host, select: SelectChoices) -> bool:
        if select == "noexplicit" and "parents" in host.attributes:
            return False
        if select == "no":
            if host.effective_attributes().get("parents"):
                return False
        return True

    def _recurse_hosts(
        self, folder: Folder | SearchFolder, recurse: bool, select: SelectChoices
    ) -> list[Host]:
        entries = []
        for host in folder.hosts().values():
            if self._include_host(host, select):
                entries.append(host)

        if recurse:
            assert isinstance(folder, Folder)
            for subfolder in folder.subfolders():
                entries += self._recurse_hosts(subfolder, recurse, select)
        return entries

    def page(self) -> None:
        if self._job.is_active():
            html.show_message(
                _('Parent scan currently running in <a href="%s">background</a>.')
                % self._job.detail_url()
            )
            return

        self._show_start_form()

    # TODO: Refactor to be valuespec based
    def _show_start_form(self) -> None:
        with html.form_context("parentscan", method="POST"):
            self._show_start_form_inner()

    def _show_start_form_inner(self) -> None:
        html.hidden_fields()

        # Mode of action
        if not self._complete_folder:
            num_selected = len(get_hosts_from_checkboxes(self._folder))
            html.icon("toggle_details")
            html.write_text(_("You have selected <b>%d</b> hosts for parent scan. ") % num_selected)
        html.help(
            _(
                "The parent scan will try to detect the last gateway "
                "on layer 3 (IP) before a host. This will be done by "
                "calling <tt>traceroute</tt>. If a gateway is found by "
                "that way and its IP address belongs to one of your "
                "monitored hosts, that host will be used as the hosts "
                "parent. If no such host exists, an artifical ping-only "
                "gateway host will be created if you have not disabled "
                "this feature."
            )
        )

        forms.header(_("Settings for Parent Scan"))

        try:
            parent_scan_settings = GUIParentScanSettings(
                **user.load_file(
                    "parentscan",
                    {
                        "where": "subfolder",
                        "alias": _("Created by parent scan"),
                        "recurse": True,
                        "select": "noexplicit",
                        "timeout": 8,
                        "probes": 2,
                        "ping_probes": 5,
                        "max_ttl": 10,
                        "force_explicit": False,
                        "gateway_folder_path": None,
                    },
                )
            )
        except Exception:
            user_file = f"{profile_dir}/{user.id}/parentscan.mk"
            raise MKUserError(
                None,
                _("Error reading parent scan settings. Please delete the file ''%s' and try again.")
                % user_file,
            )

        self._settings = parent_scan_settings

        # Selection
        forms.section(_("Selection"))
        if self._complete_folder:
            html.checkbox("recurse", self._settings.recurse, label=_("Include all subfolders"))
            html.br()
        html.radiobutton(
            "select",
            "noexplicit",
            self._settings.select == "noexplicit",
            _("Skip hosts with explicit parent definitions (even if empty)") + "<br>",
        )
        html.radiobutton(
            "select",
            "no",
            self._settings.select == "no",
            _("Skip hosts hosts with non-empty parents (also if inherited)") + "<br>",
        )
        html.radiobutton(
            "select",
            "ignore",
            self._settings.select == "ignore",
            _("Scan all hosts") + "<br>",
        )

        # Performance
        forms.section(_("Performance"))
        html.open_table()
        html.open_tr()
        html.open_td()
        html.write_text(_("Timeout for responses") + ":")
        html.close_td()
        html.open_td()
        html.text_input("timeout", str(self._settings.timeout), size=2, cssclass="number")
        html.write_text(_("sec"))
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Number of probes per hop") + ":")
        html.close_td()
        html.open_td()
        html.text_input("probes", str(self._settings.probes), size=2, cssclass="number")
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Maximum distance (TTL) to gateway") + ":")
        html.close_td()
        html.open_td()
        html.text_input("max_ttl", str(self._settings.max_ttl), size=2, cssclass="number")
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Number of PING probes") + ":")
        html.help(
            _(
                "After a gateway has been found, Checkmk checks if it is reachable "
                "via PING. If not, it is skipped and the next gateway nearer to the "
                "monitoring core is being tried. You can disable this check by setting "
                "the number of PING probes to 0."
            )
        )
        html.close_td()
        html.open_td()
        html.text_input("ping_probes", str(self._settings.ping_probes), size=2, cssclass="number")
        html.close_td()
        html.close_tr()
        html.close_table()

        # Configuring parent
        forms.section(_("Configuration"))
        html.checkbox(
            "force_explicit",
            deflt=self._settings.force_explicit,
            label=_(
                "Force explicit setting for parents even if setting matches that of the folder"
            ),
        )

        # Gateway creation
        forms.section(_("Creation of gateway hosts"))
        html.write_text(_("Create gateway hosts in"))
        html.open_ul()

        disk_folder = disk_or_search_base_folder_from_request(
            request.var("folder"), request.get_ascii_input("host")
        )
        html.radiobutton(
            "where",
            "subfolder",
            self._settings.where == "subfolder",
            _("in the subfolder <b>%s/Parents</b>") % disk_folder.title(),
        )

        html.br()
        html.radiobutton(
            "where",
            "here",
            self._settings.where == "here",
            _("directly in the folder <b>%s</b>") % disk_folder.title(),
        )
        html.br()
        html.radiobutton(
            "where",
            "there",
            self._settings.where == "there",
            _("in the same folder as the host"),
        )
        html.br()
        html.radiobutton(
            "where",
            "nowhere",
            self._settings.where == "nowhere",
            _("do not create gateway hosts"),
        )
        html.close_ul()
        html.write_text(_("Alias for created gateway hosts") + ": ")
        html.text_input("alias", default_value=self._settings.alias)

        forms.end()

        html.hidden_fields()
