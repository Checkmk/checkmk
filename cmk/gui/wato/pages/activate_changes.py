#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for activating pending changes. Does also replication with
remote sites in distributed Setup."""

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="unreachable"
# mypy: disable-error-code="no-untyped-call"

import ast
import enum
import json
import os
from collections.abc import Collection, Iterator, Sequence
from pathlib import Path
from typing import Literal, override

from livestatus import SiteConfiguration, SiteConfigurations

import cmk.gui.watolib.changes as _changes
from cmk.ccc.archive import CheckmkTarArchive
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition, edition, edition_has_enforced_licensing
from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import HTTPRedirect, MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_checkbox_selection_topic,
    make_javascript_action,
    make_javascript_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
    show_confirm_cancel_dialog,
)
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.sites import SiteStatus
from cmk.gui.table import Foldable, init_rowselect, table_element
from cmk.gui.type_defs import ActionResult, IconNames, PermissionName, ReadOnlySpec, StaticIcon
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.utils.selection_id import SelectionId
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri, makeuri_contextless
from cmk.gui.valuespec import Checkbox, Dictionary, DictionaryEntry, TextAreaUnicode
from cmk.gui.watolib import activate_changes, backup_snapshots, read_only
from cmk.gui.watolib.activate_changes import (
    affects_all_sites,
    ConfigWarnings,
    get_status_for_site,
    has_been_activated,
    is_foreign_change,
    prevent_discard_changes,
    verify_remote_site_config,
)
from cmk.gui.watolib.automation_commands import AutomationCommand, AutomationCommandRegistry
from cmk.gui.watolib.automations import MKAutomationException
from cmk.gui.watolib.config_domain_name import ABCConfigDomain, DomainRequest, DomainRequests
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, folder_tree, Host
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.gui.watolib.objref import ObjectRef, ObjectRefType
from cmk.utils import paths, render
from cmk.utils.licensing.registry import get_licensing_user_effect
from cmk.utils.licensing.usage import get_license_usage_report_validity, LicenseUsageReportValidity
from cmk.utils.setup_search_index import request_index_rebuild

from .sites import sort_sites


def register(
    page_registry: PageRegistry,
    mode_registry: ModeRegistry,
    automation_command_registry: AutomationCommandRegistry,
) -> None:
    page_registry.register(PageEndpoint("ajax_start_activation", PageAjaxStartActivation()))
    page_registry.register(PageEndpoint("ajax_activation_state", PageAjaxActivationState()))
    mode_registry.register(ModeActivateChanges)
    mode_registry.register(ModeRevertChanges)
    automation_command_registry.register(AutomationActivateChanges)


class ActivationState(enum.Enum):
    WARNING = 1  # same int values as for Check results to be able to reuse CSS mappings
    ERROR = 2


def _show_activation_state_messages(title: str, message: str, state: ActivationState) -> None:
    html.open_div(id="activation_state_message_container")

    html.open_div(class_="state_bar state%s" % state.value)
    html.open_span()
    match state:
        case ActivationState.WARNING:
            html.static_icon(StaticIcon(IconNames.host_svc_problems_dark))
        case ActivationState.ERROR:
            html.static_icon(StaticIcon(IconNames.host_svc_problems))
    html.close_span()
    html.close_div()  # activation_state

    html.open_div(class_="message_container")
    html.h2(title)
    html.open_div()
    html.span(message)
    html.close_div()
    html.close_div()  # activation_state_message

    html.close_div()  # activation_state_message_container


def _extract_snapshot(snapshot_file: str) -> None:
    filepath = Path(backup_snapshots.snapshot_dir + snapshot_file)
    if not isinstance(backup_snapshots.backup_domains, dict):
        raise NotImplementedError()
    with CheckmkTarArchive.from_path(filepath, streaming=False, compression="*") as opened_file:
        backup_snapshots.extract_snapshot(opened_file, backup_snapshots.backup_domains)


def _get_snapshots() -> list[str]:
    snapshots: list[str] = []
    try:
        for f in os.listdir(backup_snapshots.snapshot_dir):
            if os.path.isfile(backup_snapshots.snapshot_dir + f):
                snapshots.append(f)
        snapshots.sort(reverse=True)
    except OSError:
        pass
    return snapshots


def _get_last_wato_snapshot_file(*, debug: bool) -> None | str:
    for snapshot_file in _get_snapshots():
        status = backup_snapshots.get_snapshot_status(
            snapshot=snapshot_file,
            debug=debug,
        )
        if status["type"] == "automatic" and not status["broken"]:
            return snapshot_file
    return None


class ModeRevertChanges(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "revert_changes"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["discard"]

    def __init__(self) -> None:
        super().__init__()
        self._changes = activate_changes.ActivateChanges()
        self._changes.load(list(active_config.sites))

    def title(self) -> str:
        return _("Revert changes")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_setup()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def _page_menu_entries_setup(self) -> Iterator[PageMenuEntry]:
        if user.may("wato.sites"):
            yield PageMenuEntry(
                title=_("Sites"),
                icon_name=StaticIcon(IconNames.sites),
                item=make_simple_link(
                    makeuri_contextless(
                        request,
                        [("mode", "sites")],
                    )
                ),
            )

        if user.may("wato.auditlog"):
            yield PageMenuEntry(
                title=_("Audit log"),
                icon_name=StaticIcon(IconNames.auditlog),
                item=make_simple_link(folder_preserving_link([("mode", "auditlog")])),
            )

    def _may_discard_changes(self, read_only_config: ReadOnlySpec, *, debug: bool) -> bool:
        if not user.may("wato.activate"):
            return False

        if not user.may("wato.discard"):
            return False

        if read_only.is_enabled(read_only_config) and not read_only.may_override(read_only_config):
            return False

        if not _get_last_wato_snapshot_file(debug=debug):
            return False

        return True

    def action(self, config: Config) -> ActionResult:
        if request.var("_action") != "discard":
            return None

        if not transactions.check_transaction():
            return None

        if not self._may_discard_changes(config.wato_read_only, debug=config.debug):
            return None

        if not self._changes.has_changes():
            return None

        # Now remove all currently pending changes by simply restoring the last automatically
        # taken snapshot. Then activate the configuration. This should revert all pending changes.
        file_to_restore = _get_last_wato_snapshot_file(debug=config.debug)

        if not file_to_restore:
            raise MKUserError(None, _("There is no Setup snapshot to be restored."))

        msg = _("Discarded pending changes (restored %s)") % file_to_restore

        # All sites and domains can be affected by a restore: Better restart everything.
        _changes.add_change(
            action_name="changes-discarded",
            text=msg,
            user_id=user.id,
            domains=ABCConfigDomain.enabled_domains(),
            need_restart=True,
            use_git=config.wato_use_git,
        )

        _extract_snapshot(file_to_restore)
        activate_changes.execute_activate_changes(
            [d.get_domain_request([]) for d in ABCConfigDomain.enabled_domains()],
            is_remote_site=is_distributed_setup_remote_site(config.sites),
        )

        for site_id in activation_sites(config.sites):
            self._changes.confirm_site_changes(site_id)

        request_index_rebuild()

        flash(_("Pending changes reverted."))
        return HTTPRedirect(makeuri_contextless(request, [("mode", ModeActivateChanges.name())]))

    def page(self, config: Config) -> None:
        if not self._changes.has_changes():
            html.open_div(class_="wato")
            html.show_message(_("No pending changes."))
            html.footer()
            return

        confirm_url = makeactionuri(request, transactions, [("_action", "discard")])
        cancel_url = makeuri_contextless(
            request,
            [("mode", ModeActivateChanges.name())],
        )
        message = html.render_div(
            (
                html.render_span(_("Info:"), class_="underline")
                + _(
                    " This also includes any changes made since the last activation that did not "
                    "require manual activation (marked with "
                )
                + html.render_static_icon(StaticIcon(IconNames.info_circle))
                + ")"
            ),
            class_="confirm_info",
        )

        show_confirm_cancel_dialog(
            _("Revert changes?"),
            confirm_url,
            cancel_url,
            message,
            confirm_text=_("Revert changes"),
            post_confirm_waiting_text=_("Reverting pending changes."),
        )

        _change_table(
            list(activation_sites(config.sites)), self._changes.changes, _("Revert changes")
        )


def _change_table(
    activation_site_ids: Sequence[SiteId], changes: list[tuple[str, dict]], title: str
) -> None:
    with table_element(
        "changes",
        title=title,
        sortable=False,
        searchable=False,
        css="changes",
        limit=None,
        empty_text=_("Currently there are no changes to activate."),
        foldable=Foldable.FOLDABLE_STATELESS,
    ) as table:
        for _change_id, change in reversed(changes):
            css = []
            if is_foreign_change(change):
                css.append("foreign")
            if not user.may("wato.activateforeign"):
                css.append("not_permitted")

            table.row(css=[" ".join(css)])

            table.cell("", css=["buttons"])
            rendered = render_object_ref_as_icon(change["object"])
            if rendered:
                html.write_html(rendered)

            if has_been_activated(change):
                html.static_icon(
                    StaticIcon(IconNames.info_circle), title=_("This change is already activated")
                )

            table.cell(_("Time"), render.date_and_time(change["time"]), css=["narrow nobr"])
            table.cell(_("User"), css=["narrow nobr"])
            html.write_text_permissive(change["user_id"] if change["user_id"] else "")
            if is_foreign_change(change):
                html.static_icon(
                    StaticIcon(IconNames.foreign_changes),
                    title=_("This change has been made by another user"),
                )

            icon_code = (
                html.render_static_icon(
                    StaticIcon(IconNames.no_revert),
                    title=_(
                        "Change is not revertible. Activate this change to unblock the reverting of pending changes."
                    ),
                )
                if prevent_discard_changes(change)
                else HTML.empty()
            )

            # Text is already escaped (see ActivateChangesWriter._add_change_to_site). We have
            # to handle this in a special way because of the SiteChanges file format. Would be
            # cleaner to transport the text type (like AuditLogStore is doing it).
            table.cell(_("Change"), icon_code + HTML.without_escaping(change["text"]))

            table.cell(_("Affected sites"), css=["affected_sites"])
            if affects_all_sites(activation_site_ids, change):
                html.write_text_permissive("<i>%s</i>" % _("All sites"))
            else:
                html.write_text_permissive(", ".join(sorted(change["affected_sites"])))


class ModeActivateChanges(WatoMode):
    VAR_ORIGIN = "origin"
    VAR_SPECIAL_AGENT_NAME = "special_agent_name"

    @classmethod
    def name(cls) -> str:
        return "changelog"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return []

    def __init__(self) -> None:
        super().__init__()
        self._changes = activate_changes.ActivateChanges()
        self._changes.load(list(active_config.sites))
        self._license_usage_report_validity = get_license_usage_report_validity()
        self._quick_setup_origin = request.get_ascii_input(self.VAR_ORIGIN) == "quick_setup"

    def title(self) -> str:
        return _("Activate pending changes")

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        self._select_sites_with_pending_changes(config.sites)
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="changes",
                    title=_("Changes"),
                    topics=[
                        PageMenuTopic(
                            title=_("On all sites"),
                            entries=list(
                                self._page_menu_entries_all_sites(
                                    activation_site_ids := list(
                                        activation_sites(active_config.sites)
                                    ),
                                    config.wato_read_only,
                                    debug=config.debug,
                                )
                            ),
                        ),
                        PageMenuTopic(
                            title=_("On selected sites"),
                            entries=list(
                                self._page_menu_entries_selected_sites(
                                    config.wato_read_only, activation_site_ids
                                )
                            ),
                        ),
                        make_checkbox_selection_topic(
                            selection_key=self.name(),
                            is_enabled=self._changes.has_pending_changes(),
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_setup()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def _page_menu_entries_setup(self) -> Iterator[PageMenuEntry]:
        if user.may("wato.sites"):
            yield PageMenuEntry(
                title=_("Sites"),
                icon_name=StaticIcon(IconNames.sites),
                item=make_simple_link(
                    makeuri_contextless(
                        request,
                        [("mode", "sites")],
                    )
                ),
            )

        if user.may("wato.auditlog"):
            yield PageMenuEntry(
                title=_("Audit log"),
                icon_name=StaticIcon(IconNames.auditlog),
                item=make_simple_link(folder_preserving_link([("mode", "auditlog")])),
            )

    def _page_menu_entries_all_sites(
        self, activation_site_ids: Sequence[SiteId], read_only_config: ReadOnlySpec, *, debug: bool
    ) -> Iterator[PageMenuEntry]:
        if not self._may_discard_changes(read_only_config, activation_site_ids, debug=debug):
            return

        enabled = False
        disabled_tooltip: str | None = None
        if self._changes.has_changes():
            if not _get_last_wato_snapshot_file(debug=debug):
                enabled = False
                disabled_tooltip = _("No snapshot to restore available.")
            elif self._changes.discard_changes_forbidden(activation_site_ids):
                enabled = False
                disabled_tooltip = _(
                    "Blocked due to non-revertible change. Activate those changes to unblock reverting."
                )
            elif any(
                (change["user_id"] != user.id for _, change in self._changes.pending_changes)
            ) and not user.may("wato.discardforeign"):
                enabled = False
                disabled_tooltip = _("This user doesn't have permission to revert these changes")
            else:
                enabled = True

        yield PageMenuEntry(
            title=_("Revert changes"),
            icon_name=StaticIcon(IconNames.revert),
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", ModeRevertChanges.name())],
                )
            ),
            name="discard_changes",
            is_enabled=enabled,
            disabled_tooltip=disabled_tooltip,
        )

    def _page_menu_entries_selected_sites(
        self, read_only_config: ReadOnlySpec, activation_site_ids: Sequence[SiteId]
    ) -> Iterator[PageMenuEntry]:
        if not self._may_activate_changes(read_only_config, activation_site_ids):
            return

        yield PageMenuEntry(
            title=_("Activate on selected sites"),
            icon_name=StaticIcon(
                IconNames.save,
                emblem="refresh",
            ),
            item=make_javascript_link('cmk.activation.activate_changes("selected")'),
            name="activate_selected",
            is_shortcut=True,
            is_suggested=True,
            is_enabled=self._changes.has_pending_changes(),
        )

    def _may_discard_changes(
        self, read_only_config: ReadOnlySpec, activation_site_ids: Sequence[SiteId], *, debug: bool
    ) -> bool:
        if not user.may("wato.discard"):
            return False

        if not user.may("wato.discardforeign") and self._changes.has_foreign_changes_on_any_site(
            activation_site_ids
        ):
            return False

        if not self._may_activate_changes(read_only_config, activation_site_ids):
            return False

        if not _get_last_wato_snapshot_file(debug=debug):
            return False

        return True

    def _license_allows_activation(self) -> bool:
        if edition(paths.omd_root) in (Edition.ULTIMATEMT, Edition.ULTIMATE):
            # TODO: move to CCE handler to avoid is_ultimate_edition check
            license_usage_report_valid = (
                self._license_usage_report_validity
                != LicenseUsageReportValidity.older_than_five_days
            )
            block_effect = get_licensing_user_effect(
                licensing_settings_link=makeuri_contextless(
                    request, [("mode", "licensing")], filename="wato.py"
                ),
            )
            return block_effect.block is None and license_usage_report_valid
        return True

    def _may_activate_changes(
        self, read_only_config: ReadOnlySpec, activation_site_ids: Sequence[SiteId]
    ) -> bool:
        if not user.may("wato.activate"):
            return False

        if not user.may("wato.activateforeign") and self._changes.has_foreign_changes_on_any_site(
            activation_site_ids
        ):
            return False

        if read_only.is_enabled(read_only_config) and not read_only.may_override(read_only_config):
            return False

        return self._license_allows_activation()

    def page(self, config: Config) -> None:
        self._quick_setup_activation_msg()
        self._activation_msg()
        self._activation_form(
            comment_mode=config.wato_activate_changes_comment_mode,
            activation_site_ids=list(activation_sites(config.sites)),
        )

        self._show_license_validity()

        self._activation_status(activation_site_configs := activation_sites(config.sites))

        if self._changes.has_pending_changes():
            _change_table(
                list(activation_site_configs),
                self._changes.pending_changes,
                _("Pending changes"),
            )

    def _quick_setup_activation_msg(self) -> None:
        if not (self._quick_setup_origin and self._changes.has_pending_changes()):
            return

        message = html.render_div(
            (
                html.render_div(
                    _('Activate the changes by clicking the "Activate on selected sites" button.')
                )
                + html.render_div(_("This action will affect all pending changes you have made."))
            ),
            class_="confirm_info",
        )

        confirm_url = "javascript:" + make_javascript_action(
            'cmk.activation.activate_changes("selected")'
        )

        show_confirm_cancel_dialog(
            title=_("Activate pending changes"),
            confirm_url=confirm_url,
            confirm_text=_("Activate on selected sites"),
            message=message,
            show_cancel_button=False,
        )

    def _activation_msg(self) -> None:
        html.open_div(id_="async_progress_msg")
        if message := self._get_initial_message():
            html.show_message(message)
        html.close_div()

    def _get_initial_message(self) -> str | None:
        if len(self._changes.pending_changes) == 0:
            return None
        if not request.has_var("_finished"):
            return None
        return _("Activation has finished.")

    def _activation_form(
        self,
        comment_mode: Literal["enforce", "optional", "disabled"],
        activation_site_ids: Sequence[SiteId],
    ) -> None:
        if not user.may("wato.activate"):
            html.show_warning(_("You are not permitted to activate configuration changes."))
            return

        if not self._changes.pending_changes:
            return

        if not user.may("wato.activateforeign") and self._changes.has_foreign_changes_on_any_site(
            activation_site_ids
        ):
            html.show_warning(_("Sorry, you are not allowed to activate changes of other users."))
            return

        valuespec = _vs_activation(self.title(), comment_mode, self._changes.has_foreign_changes())

        with html.form_context("activate", method="POST", action=""):
            html.hidden_field(
                "activate_until", self._changes.get_last_change_id(), id_="activate_until"
            )

            if valuespec:
                title = valuespec.title()
                assert title is not None
                forms.header(title)
                valuespec.render_input("activate", {})
                valuespec.set_focus("activate")
                html.help(valuespec.help())

            if self._changes.has_foreign_changes():
                if user.may("wato.activateforeign"):
                    html.show_warning(
                        _(
                            "There are some changes made by your colleagues that you will activate if you proceed. You need to enable the checkbox above to confirm the activation of these changes."
                        )
                    )
                else:
                    html.show_warning(
                        _(
                            "There are some changes made by your colleagues that you cannot activate because you are not permitted to. You can only activate your changes on the sites that are not affected by these changes. <br>If you need to activate your changes on all sites, please contact a permitted user to do it for you."
                        )
                    )

            forms.end()
            html.hidden_field("selection_id", SelectionId.from_request(request))
            html.hidden_fields()
        init_rowselect(self.name())

    def _show_license_validity(self) -> None:
        if block_effect := get_licensing_user_effect(
            licensing_settings_link=makeuri_contextless(
                request, [("mode", "licensing")], filename="wato.py"
            ),
        ).block:
            _show_activation_state_messages(
                _("Activation not possible because of the following licensing issues:"),
                block_effect.message_html,
                ActivationState.ERROR,
            )
            return

        if edition_has_enforced_licensing(edition(paths.omd_root)):
            if (
                self._license_usage_report_validity
                == LicenseUsageReportValidity.older_than_five_days
            ):
                _show_activation_state_messages(
                    "",
                    _(
                        "The license usage history is older than five days. In order to have a"
                        " reliable average of the number of services the license usage report must"
                        " contain a significant number of license usage samples. Please execute"
                        " the following command as site user 'cmk-update-license-usage --force' in"
                        " order to solve this situation."
                    ),
                    ActivationState.WARNING,
                )
            elif (
                self._license_usage_report_validity
                == LicenseUsageReportValidity.older_than_three_days
            ):
                _show_activation_state_messages(
                    "",
                    _("The license usage history was updated at least three days ago."),
                    ActivationState.WARNING,
                )

    def _activation_status(self, activation_sites: SiteConfigurations) -> None:
        with table_element(
            "site-status",
            title=_("Activation status"),
            searchable=False,
            sortable=False,
            css="activation",
            foldable=Foldable.FOLDABLE_STATELESS,
        ) as table:
            for site_id, site in sort_sites(activation_sites):
                table.row()

                site_status = get_status_for_site(site_id, site)
                status = site_status.get("state", "unknown")

                is_online = self._changes.site_is_online(status)
                is_logged_in = self._changes.site_is_logged_in(site_id, site)
                can_activate_all = self._can_activate_all(site_id)

                # Disable actions for offline sites and not logged in sites
                if not is_online or not is_logged_in:
                    can_activate_all = False

                need_restart = self._changes.is_activate_needed(site_id)
                need_sync = self._changes.is_sync_needed(site_id, site)
                need_action = need_restart or need_sync
                nr_changes = len(
                    list(
                        change
                        for change in self._changes.changes_of_site(site_id)
                        if not has_been_activated(change)
                    )
                )

                # Activation checkbox
                table.cell("", css=["buttons"])
                if can_activate_all and nr_changes:
                    html.checkbox("site_%s" % site_id, need_action, cssclass="site_checkbox")

                # Iconbuttons
                table.cell(_("Actions"), css=["buttons"])

                if user.may("wato.sites"):
                    edit_url = folder_preserving_link([("mode", "edit_site"), ("site", site_id)])
                    html.icon_button(
                        edit_url, _("Edit the properties of this site"), StaticIcon(IconNames.edit)
                    )

                # State
                if can_activate_all and need_sync:
                    html.icon_button(
                        url="javascript:void(0)",
                        id_="activate_%s" % site_id,
                        cssclass="activate_site",
                        title=_("This site is not update and needs a replication. Start it now."),
                        icon=StaticIcon(IconNames.need_replicate),
                        onclick='cmk.activation.activate_changes("site", "%s")' % site_id,
                    )

                if can_activate_all and need_restart:
                    html.icon_button(
                        url="javascript:void(0)",
                        id_="activate_%s" % site_id,
                        cssclass="activate_site",
                        title=_(
                            "This site needs a restart for activating the changes. Start it now."
                        ),
                        icon=StaticIcon(IconNames.need_restart),
                        onclick='cmk.activation.activate_changes("site", "%s")' % site_id,
                    )

                if can_activate_all and not need_action:
                    html.static_icon(
                        StaticIcon(IconNames.checkmark), title=_("This site is up-to-date.")
                    )

                site_url = site.get("multisiteurl")
                if site_url:
                    html.icon_button(
                        site_url,
                        _("Open this site's local web user interface"),
                        StaticIcon(IconNames.url),
                        target="_blank",
                    )

                table.cell(_("Site"), site.get("alias", site_id), css=["narrow nobr"])

                # Livestatus
                table.cell(_("Status"), css=["narrow nobr"])
                html.status_label(
                    content=status, status=status, title=_("This site is %s") % status
                )

                # Livestatus-/Checkmk-Version
                table.cell(
                    _("Version"), site_status.get("livestatus_version", ""), css=["narrow nobr"]
                )

                table.cell(_("Changes"), "%d" % nr_changes, css=["number narrow nobr"])

                table.cell(_("Progress"), css=["repprogress"])
                html.open_div(id_="site_%s_status" % site_id, class_=["msg"])
                html.close_div()
                html.open_div(id_="site_%s_progress" % site_id, class_=["progress"])
                html.close_div()

                table.cell(_("Details"), css=["details"])
                html.open_div(id_="site_%s_details" % site_id)

                self._display_site_activation_status_details(
                    need_action, is_logged_in, site_id, site_status, status
                )

                html.close_div()

    def _display_site_activation_status_details(
        self,
        need_action: bool,
        is_logged_in: bool,
        site_id: SiteId,
        site_status: SiteStatus,
        status: str,
    ) -> None:
        if status == "dead":
            html.write_text_permissive(str(site_status["exception"]))
            return

        last_state = self._changes.last_activation_state(site_id)

        if not is_logged_in:
            html.write_text_permissive(_("Is not logged in.") + " ")

        if not last_state:
            html.write_text_permissive(_("Has never been activated"))
        elif need_action and last_state["_state"] == activate_changes.STATE_SUCCESS:
            html.write_text_permissive(_("Activation needed"))
        else:
            html.javascript(
                "cmk.activation.update_site_activation_state(%s);" % json.dumps(last_state)
            )

    def _can_activate_all(self, site_id: SiteId) -> bool:
        return not self._changes.site_has_foreign_changes(site_id) or user.may(
            "wato.activateforeign"
        )

    def _get_selected_sites(self, site_configs: SiteConfigurations) -> list[str]:
        return [
            "site_%s" % site_id
            for site_id, site in sort_sites(activation_sites(site_configs))
            if len(self._changes.changes_of_site(site_id))
            and self._can_activate_all(site_id)
            and self._is_active_site(
                site_id=site_id,
                site=site,
                status=get_status_for_site(site_id, site).get("state", "unknown"),
            )
        ]

    def _select_sites_with_pending_changes(self, site_configs: SiteConfigurations) -> None:
        selected_sites: list[str] = self._get_selected_sites(site_configs)
        user.set_rowselection(SelectionId.from_request(request), self.name(), selected_sites, "set")

    def _is_active_site(self, site_id: SiteId, site: SiteConfiguration, status: str) -> bool:
        return self._changes.site_is_online(status) and self._changes.site_is_logged_in(
            site_id, site
        )


def render_object_ref_as_icon(object_ref: ObjectRef | None) -> HTML | None:
    if object_ref is None:
        return None

    url, title = _get_object_reference(object_ref)
    if not url:
        return None

    icons = {
        ObjectRefType.Host: StaticIcon(IconNames.host),
        ObjectRefType.Folder: StaticIcon(IconNames.folder),
        ObjectRefType.User: StaticIcon(IconNames.users),
        ObjectRefType.Rule: StaticIcon(IconNames.rule),
        ObjectRefType.Ruleset: StaticIcon(IconNames.rulesets),
    }

    return HTMLWriter.render_a(
        content=html.render_static_icon(
            icons.get(object_ref.object_type, StaticIcon(IconNames.link)),
            title=f"{object_ref.object_type.name}: {title}" if title else None,
        ),
        href=url,
    )


def render_object_ref(object_ref: ObjectRef | None) -> str | HTML | None:
    url, title = _get_object_reference(object_ref)
    if title and not url:
        return title
    if not title:
        return None
    return HTMLWriter.render_a(title, href=url)


# TODO: Move this to some generic place
def _get_object_reference(object_ref: ObjectRef | None) -> tuple[str | None, str | None]:
    if object_ref is None:
        return None, None

    if object_ref.object_type is ObjectRefType.Host:
        host = Host.host(HostName(object_ref.ident))
        if host:
            return host.edit_url(), host.name()
        return None, object_ref.ident

    if object_ref.object_type is ObjectRefType.Folder:
        tree = folder_tree()
        if tree.folder_exists(object_ref.ident):
            folder = tree.folder(object_ref.ident)
            return folder.url(), folder.title()
        return None, object_ref.ident

    if object_ref.object_type is ObjectRefType.User:
        url = makeuri_contextless(
            request,
            [
                ("mode", "edit_user"),
                ("edit", object_ref.ident),
            ],
            filename="wato.py",
        )
        return url, object_ref.ident

    if object_ref.object_type is ObjectRefType.Rule:
        url = makeuri_contextless(
            request,
            [
                ("mode", "edit_rule"),
                ("varname", object_ref.labels["ruleset"]),
                ("rule_id", object_ref.ident),
            ],
            filename="wato.py",
        )
        return url, object_ref.ident

    if object_ref.object_type is ObjectRefType.Ruleset:
        url = makeuri_contextless(
            request,
            [
                ("mode", "edit_ruleset"),
                ("varname", object_ref.ident),
            ],
            filename="wato.py",
        )
        return url, object_ref.ident

    return None, object_ref.ident


def _vs_activation(
    title: str, comment_mode: Literal["enforce", "optional", "disabled"], has_foreign_changes: bool
) -> Dictionary | None:
    elements: list[DictionaryEntry] = []

    if comment_mode != "disabled":
        is_optional = comment_mode != "enforce"
        elements.append(
            (
                "comment",
                TextAreaUnicode(
                    title=_("Comment (optional)") if is_optional else _("Comment"),
                    cols=40,
                    try_max_width=True,
                    rows=1,
                    help=_(
                        "You can provide an optional comment for the current activation. "
                        "This can be useful to document the reason why the changes you "
                        "activate have been made."
                    ),
                    allow_empty=is_optional,
                ),
            )
        )

    if has_foreign_changes and user.may("wato.activateforeign"):
        elements.append(
            (
                "foreign",
                Checkbox(
                    title=_("Activate foreign changes"),
                    label=_("Activate changes of other users"),
                ),
            )
        )

    if not elements:
        return None

    return Dictionary(
        title=title,
        elements=elements,
        optional_keys=[],
        render="form_part",
    )


class PageAjaxStartActivation(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        check_csrf_token()
        user.need_permission("wato.activate")

        api_request = ctx.request.get_request()
        activate_until = api_request.get("activate_until")
        if not activate_until:
            raise MKUserError("activate_until", _('Missing parameter "%s".') % "activate_until")

        manager = activate_changes.ActivateChangesManager()
        manager.changes.load(list(ctx.config.sites))
        affected_sites_request = api_request.get("sites", "").strip()
        if not affected_sites_request:
            affected_sites = manager.changes.dirty_and_active_activation_sites(
                activation_sites(ctx.config.sites)
            )
        else:
            affected_sites = [SiteId(s) for s in affected_sites_request.split(",")]

        comment: str | None = api_request.get("comment", "").strip()

        activate_foreign = api_request.get("activate_foreign", "0") == "1"

        valuespec = _vs_activation(
            "", ctx.config.wato_activate_changes_comment_mode, manager.changes.has_foreign_changes()
        )
        if valuespec:
            valuespec.validate_value(
                {
                    "comment": comment,
                    "foreign": activate_foreign,
                },
                "activate",
            )

        if comment == "":
            comment = None

        activation_id = manager.start(
            sites=affected_sites,
            all_site_configs=ctx.config.sites,
            activate_until=activate_until,
            comment=comment,
            activate_foreign=activate_foreign,
            user_permission_config=UserPermissionSerializableConfig.from_global_config(ctx.config),
            source="GUI",
            max_snapshots=ctx.config.wato_max_snapshots,
            use_git=ctx.config.wato_use_git,
            debug=ctx.config.debug,
        )

        return {
            "activation_id": activation_id,
        }


class PageAjaxActivationState(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        user.need_permission("wato.activate")

        api_request = ctx.request.get_request()

        activation_id = api_request.get("activation_id")
        if not activation_id:
            raise MKUserError("activation_id", _('Missing parameter "%s".') % "activation_id")

        manager = activate_changes.ActivateChangesManager()
        manager.changes.load(list(ctx.config.sites))
        manager.load_activation(activation_id)

        return manager.get_state()


class AutomationActivateChanges(AutomationCommand[DomainRequests]):
    def command_name(self) -> str:
        return "activate-changes"

    def get_request(self, config: Config, request: Request) -> DomainRequests:
        verify_remote_site_config(
            config.sites, SiteId(request.get_ascii_input_mandatory("site_id"))
        )
        domains = request.get_ascii_input_mandatory("domains")
        try:
            return [DomainRequest(**x) for x in ast.literal_eval(domains)]
        except SyntaxError:
            raise MKAutomationException(_("Invalid request: %r") % domains)

    def execute(self, api_request: DomainRequests) -> ConfigWarnings:
        return activate_changes.execute_activate_changes(api_request, is_remote_site=True)
