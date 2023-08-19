#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for activating pending changes. Does also replication with
remote sites in distributed Setup."""

import ast
import enum
import json
import os
import tarfile
from collections.abc import Collection, Iterator, Sequence
from dataclasses import asdict
from typing import NamedTuple

from six import ensure_str

from livestatus import SiteConfiguration, SiteId

import cmk.utils.render as render
from cmk.utils.hostaddress import HostName
from cmk.utils.licensing.registry import get_licensing_user_effect
from cmk.utils.licensing.usage import get_license_usage_report_validity, LicenseUsageReportValidity
from cmk.utils.setup_search_index import request_index_rebuild
from cmk.utils.version import edition, Edition

import cmk.gui.forms as forms
import cmk.gui.watolib.changes as _changes
import cmk.gui.watolib.read_only as read_only
import cmk.gui.weblib as weblib
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import FinalizeRequest, MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_checkbox_selection_topic,
    make_javascript_link,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import AjaxPage, PageRegistry, PageResult
from cmk.gui.plugins.wato.utils import sort_sites
from cmk.gui.sites import SiteStatus
from cmk.gui.table import Foldable, init_rowselect, table_element
from cmk.gui.type_defs import ActionResult, PermissionName
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri, makeuri_contextless
from cmk.gui.valuespec import Checkbox, Dictionary, DictionaryEntry, TextAreaUnicode
from cmk.gui.watolib import activate_changes, backup_snapshots
from cmk.gui.watolib.automation_commands import automation_command_registry, AutomationCommand
from cmk.gui.watolib.automations import MKAutomationException
from cmk.gui.watolib.config_domain_name import ABCConfigDomain, DomainRequest, DomainRequests
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link, folder_tree, Host
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.gui.watolib.objref import ObjectRef, ObjectRefType


def register(page_registry: PageRegistry, mode_registry: ModeRegistry) -> None:
    page_registry.register_page("ajax_start_activation")(PageAjaxStartActivation)
    page_registry.register_page("ajax_activation_state")(PageAjaxActivationState)
    mode_registry.register(ModeActivateChanges)


class ActivationState(enum.Enum):
    WARNING = 1  # same int values as for Check results to be able to reuse CSS mappings
    ERROR = 2


def _show_activation_state_messages(
    title: str, messages: Sequence[str], state: ActivationState
) -> None:
    html.open_div(id="activation_state_message_container")

    html.open_div(class_="state_bar state%s" % state.value)
    html.open_span()
    match state:
        case ActivationState.WARNING:
            html.icon("host_svc_problems_dark")
        case ActivationState.ERROR:
            html.icon("host_svc_problems")
    html.close_span()
    html.close_div()  # activation_state

    html.open_div(class_="message_container")
    html.h2(title)
    html.open_div()
    for msg in messages:
        html.span(msg)
    html.close_div()
    html.close_div()  # activation_state_message

    html.close_div()  # activation_state_message_container


class ModeActivateChanges(WatoMode, activate_changes.ActivateChanges):
    @classmethod
    def name(cls) -> str:
        return "changelog"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return []

    def __init__(self) -> None:
        self._value: dict = {}
        super().__init__()
        super().load()
        self._license_usage_report_validity = get_license_usage_report_validity()

    def title(self) -> str:
        return _("Activate pending changes")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        self._select_sites_with_pending_changes()
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="changes",
                    title=_("Changes"),
                    topics=[
                        PageMenuTopic(
                            title=_("On all sites"),
                            entries=list(self._page_menu_entries_all_sites()),
                        ),
                        PageMenuTopic(
                            title=_("On selected sites"),
                            entries=list(self._page_menu_entries_selected_sites()),
                        ),
                        make_checkbox_selection_topic(
                            selection_key=self.name(),
                            is_enabled=self.has_changes(),
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
                icon_name="sites",
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
                icon_name="auditlog",
                item=make_simple_link(folder_preserving_link([("mode", "auditlog")])),
            )

    def _page_menu_entries_all_sites(self) -> Iterator[PageMenuEntry]:
        if not self._may_discard_changes():
            return

        yield PageMenuEntry(
            title=_("Revert all pending changes"),
            icon_name="revert",
            item=make_simple_link(makeactionuri(request, transactions, [("_action", "discard")])),
            name="discard_changes",
            is_enabled=self.has_changes()
            and not self.discard_changes_forbidden()
            and self._get_last_wato_snapshot_file(),
            disabled_tooltip=_(
                "Blocked due to non-revertible change. Activate those changes to unblock reverting."
            ),
        )

    def _page_menu_entries_selected_sites(self) -> Iterator[PageMenuEntry]:
        if not self._may_activate_changes():
            return

        yield PageMenuEntry(
            title=_("Activate on selected sites"),
            icon_name={
                "icon": "save",
                "emblem": "refresh",
            },
            item=make_javascript_link('cmk.activation.activate_changes("selected")'),
            name="activate_selected",
            is_shortcut=True,
            is_suggested=True,
            is_enabled=self.has_changes(),
        )

    def _may_discard_changes(self) -> bool:
        if not user.may("wato.discard"):
            return False

        if not user.may("wato.discardforeign") and self._has_foreign_changes_on_any_site():
            return False

        if not self._may_activate_changes():
            return False

        if not self._get_last_wato_snapshot_file():
            return False

        return True

    def _license_allows_activation(self):
        if edition() is Edition.CCE:
            # TODO: move to CCE handler to avoid is_cloud_edition check
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

    def _may_activate_changes(self) -> bool:
        if not user.may("wato.activate"):
            return False

        if not user.may("wato.activateforeign") and self._has_foreign_changes_on_any_site():
            return False

        if read_only.is_enabled() and not read_only.may_override():
            return False

        return self._license_allows_activation()

    def action(self) -> ActionResult:
        if request.var("_action") != "discard":
            return None

        if not transactions.check_transaction():
            return None

        if not self._may_discard_changes():
            return None

        if not self.has_changes():
            return None

        if not self._license_allows_activation():
            return None

        # Now remove all currently pending changes by simply restoring the last automatically
        # taken snapshot. Then activate the configuration. This should revert all pending changes.
        file_to_restore = self._get_last_wato_snapshot_file()

        if not file_to_restore:
            raise MKUserError(None, _("There is no Setup snapshot to be restored."))

        msg = _("Discarded pending changes (Restored %s)") % file_to_restore

        # All sites and domains can be affected by a restore: Better restart everything.
        _changes.add_change(
            "changes-discarded",
            msg,
            domains=ABCConfigDomain.enabled_domains(),
            need_restart=True,
        )

        self._extract_snapshot(file_to_restore)
        activate_changes.execute_activate_changes(
            [d.get_domain_request([]) for d in ABCConfigDomain.enabled_domains()]
        )

        for site_id in activation_sites():
            self.confirm_site_changes(site_id)

        request_index_rebuild()

        make_header(
            html,
            self.title(),
            breadcrumb=self.breadcrumb(),
            show_body_start=display_options.enabled(display_options.H),
            show_top_heading=display_options.enabled(display_options.T),
        )
        html.open_div(class_="wato")

        html.show_message(_("Successfully discarded all pending changes."))
        html.javascript("hide_changes_buttons();")
        html.footer()
        return FinalizeRequest(code=200)

    def _extract_snapshot(self, snapshot_file):
        self._extract_from_file(
            backup_snapshots.snapshot_dir + snapshot_file, backup_snapshots.backup_domains
        )

    def _extract_from_file(
        self, filename: str, elements: dict[str, backup_snapshots.DomainSpec]
    ) -> None:
        if not isinstance(elements, dict):
            raise NotImplementedError()

        with tarfile.open(filename, "r") as opened_file:
            backup_snapshots.extract_snapshot(opened_file, elements)

    def _get_last_wato_snapshot_file(self):
        for snapshot_file in self._get_snapshots():
            status = backup_snapshots.get_snapshot_status(snapshot_file)
            if status["type"] == "automatic" and not status["broken"]:
                return snapshot_file
        return None

    def _get_snapshots(self) -> list[str]:
        snapshots: list[str] = []
        try:
            for f in os.listdir(backup_snapshots.snapshot_dir):
                if os.path.isfile(backup_snapshots.snapshot_dir + f):
                    snapshots.append(f)
            snapshots.sort(reverse=True)
        except OSError:
            pass
        return snapshots

    def page(self) -> None:
        self._activation_msg()
        self._activation_form()

        self._show_license_validity()

        self._activation_status()

        if self.has_changes():
            self._change_table()

    def _activation_msg(self):
        html.open_div(id_="async_progress_msg")
        if message := self._get_initial_message():
            html.show_message(message)
        html.close_div()

    def _get_amount_changes(self) -> int:
        return sum(len(self._changes_of_site(site_id)) for site_id in activation_sites())

    def _get_initial_message(self) -> str | None:
        if self._get_amount_changes() != 0:
            return None
        if not request.has_var("_finished"):
            return None
        return _("Activation has finished.")

    def _activation_form(self):
        if not user.may("wato.activate"):
            html.show_warning(_("You are not permitted to activate configuration changes."))
            return

        if not self._changes:
            return

        if not user.may("wato.activateforeign") and self._has_foreign_changes_on_any_site():
            html.show_warning(_("Sorry, you are not allowed to activate changes of other users."))
            return

        valuespec = _vs_activation(self.title(), self.has_foreign_changes())

        html.begin_form("activate", method="POST", action="")
        html.hidden_field("activate_until", self._get_last_change_id(), id_="activate_until")

        if valuespec:
            title = valuespec.title()
            assert title is not None
            forms.header(title)
            valuespec.render_input("activate", self._value)
            valuespec.set_focus("activate")
            html.help(valuespec.help())

        if self.has_foreign_changes():
            if user.may("wato.activateforeign"):
                html.show_warning(
                    _(
                        "There are some changes made by your colleagues that you will "
                        "activate if you proceed. You need to enable the checkbox above "
                        "to confirm the activation of these changes."
                    )
                )
            else:
                html.show_warning(
                    _(
                        "There are some changes made by your colleagues that you can not "
                        "activate because you are not permitted to. You can only activate "
                        "the changes on the sites that are not affected by these changes. "
                        "<br>"
                        "If you need to activate your changes on all sites, please contact "
                        "a permitted user to do it for you."
                    )
                )

        forms.end()
        html.hidden_field("selection_id", weblib.selection_id())
        html.hidden_fields()
        html.end_form()
        init_rowselect(self.name())

    def _change_table(self):
        with table_element(
            "changes",
            title=_("Pending changes (%s)") % self._get_amount_changes(),
            sortable=False,
            searchable=False,
            css="changes",
            limit=None,
            empty_text=_("Currently there are no changes to activate."),
            foldable=Foldable.FOLDABLE_STATELESS,
        ) as table:
            for _change_id, change in reversed(self._changes):
                css = []
                if self._is_foreign(change):
                    css.append("foreign")
                if not user.may("wato.activateforeign"):
                    css.append("not_permitted")

                table.row(css=[" ".join(css)])

                table.cell("", css=["buttons"])
                rendered = render_object_ref_as_icon(change["object"])
                if rendered:
                    html.write_html(rendered)

                table.cell(_("Time"), render.date_and_time(change["time"]), css=["narrow nobr"])
                table.cell(_("User"), css=["narrow nobr"])
                html.write_text(change["user_id"] if change["user_id"] else "")
                if self._is_foreign(change):
                    html.icon("foreign_changes", _("This change has been made by another user"))

                icon_code = (
                    html.render_icon(
                        "no_revert",
                        _(
                            "Change is not revertible. Activate this change to unblock the reverting of pending changes."
                        ),
                    )
                    if self._prevent_discard_changes(change)
                    else ""
                )

                # Text is already escaped (see ActivateChangesWriter._add_change_to_site). We have
                # to handle this in a special way because of the SiteChanges file format. Would be
                # cleaner to transport the text type (like AuditLogStore is doing it).
                table.cell(_("Change"), HTML(icon_code + change["text"]))

                table.cell(_("Affected sites"), css=["affected_sites"])
                if self._affects_all_sites(change):
                    html.write_text("<i>%s</i>" % _("All sites"))
                else:
                    html.write_text(", ".join(sorted(change["affected_sites"])))

    def _show_license_validity(self) -> None:
        errors = []
        warnings = []

        if block_effect := get_licensing_user_effect(
            licensing_settings_link=makeuri_contextless(
                request, [("mode", "licensing")], filename="wato.py"
            ),
        ).block:
            errors.append(block_effect.message_html)

        if edition() is Edition.CCE:
            # TODO move to CCE handler to avoid is_cloud_edition check
            if (
                self._license_usage_report_validity
                == LicenseUsageReportValidity.older_than_five_days
            ):
                errors.append(_("The license usage history is older than five days."))
            elif (
                self._license_usage_report_validity
                == LicenseUsageReportValidity.older_than_three_days
            ):
                warnings.append(
                    _(
                        "The license usage history was updated at least three days ago."
                        "<br>Note: If it cannot be updated within five days activate changes"
                        " will be blocked."
                    )
                )
        if errors:
            error_title = _("Activation not possible because of the following licensing issues:")
            _show_activation_state_messages(error_title, errors, ActivationState.ERROR)

            return
        if warnings:
            _show_activation_state_messages("", warnings, ActivationState.WARNING)

    def _activation_status(self):
        with table_element(
            "site-status",
            title=_("Activation status"),
            searchable=False,
            sortable=False,
            css="activation",
            foldable=Foldable.FOLDABLE_STATELESS,
        ) as table:
            for site_id, site in sort_sites(activation_sites()):
                table.row()

                site_status, status = self._get_site_status(site_id, site)

                is_online = self._site_is_online(status)
                is_logged_in = self._site_is_logged_in(site_id, site)
                can_activate_all = self._can_activate_all(site_id)

                # Disable actions for offline sites and not logged in sites
                if not is_online or not is_logged_in:
                    can_activate_all = False

                need_restart = self.is_activate_needed(site_id)
                need_sync = self.is_sync_needed(site_id)
                need_action = need_restart or need_sync
                nr_changes = len(self._changes_of_site(site_id))

                # Activation checkbox
                table.cell("", css=["buttons"])
                if can_activate_all and nr_changes:
                    html.checkbox("site_%s" % site_id, need_action, cssclass="site_checkbox")

                # Iconbuttons
                table.cell(_("Actions"), css=["buttons"])

                if user.may("wato.sites"):
                    edit_url = folder_preserving_link([("mode", "edit_site"), ("site", site_id)])
                    html.icon_button(edit_url, _("Edit the properties of this site"), "edit")

                # State
                if can_activate_all and need_sync:
                    html.icon_button(
                        url="javascript:void(0)",
                        id_="activate_%s" % site_id,
                        cssclass="activate_site",
                        title=_("This site is not update and needs a replication. Start it now."),
                        icon="need_replicate",
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
                        icon="need_restart",
                        onclick='cmk.activation.activate_changes("site", "%s")' % site_id,
                    )

                if can_activate_all and not need_action:
                    html.icon("siteuptodate", _("This site is up-to-date."))

                site_url = site.get("multisiteurl")
                if site_url:
                    html.icon_button(
                        site_url,
                        _("Open this site's local web user interface"),
                        "url",
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
            html.write_text(str(site_status["exception"]))
            return

        last_state = self._last_activation_state(site_id)

        if not is_logged_in:
            html.write_text(_("Is not logged in.") + " ")

        if not last_state:
            html.write_text(_("Has never been activated"))
        elif need_action and last_state["_state"] == activate_changes.STATE_SUCCESS:
            html.write_text(_("Activation needed"))
        else:
            html.javascript(
                "cmk.activation.update_site_activation_state(%s);" % json.dumps(last_state)
            )

    def _can_activate_all(self, site_id: SiteId) -> bool:
        return not self._site_has_foreign_changes(site_id) or user.may("wato.activateforeign")

    def _get_selected_sites(self) -> list[SiteId | str]:
        return [
            "site_%s" % site_id
            for site_id, site in sort_sites(activation_sites())
            if len(self._changes_of_site(site_id))
            and self._can_activate_all(site_id)
            and self._is_active_site(
                site_id=site_id,
                site=site,
                status=self._get_site_status(site_id, site)[1],
            )
        ]

    def _select_sites_with_pending_changes(self) -> None:
        selected_sites: list[SiteId | str] = self._get_selected_sites()
        user.set_rowselection(weblib.selection_id(), self.name(), selected_sites, "set")

    def _is_active_site(self, site_id: SiteId, site: SiteConfiguration, status: str) -> bool:
        return self._site_is_online(status) and self._site_is_logged_in(site_id, site)


def render_object_ref_as_icon(object_ref: ObjectRef | None) -> HTML | None:
    if object_ref is None:
        return None

    url, title = _get_object_reference(object_ref)
    if not url:
        return None

    icons = {
        ObjectRefType.Host: "host",
        ObjectRefType.Folder: "folder",
        ObjectRefType.User: "users",
        ObjectRefType.Rule: "rule",
        ObjectRefType.Ruleset: "rulesets",
    }

    return HTMLWriter.render_a(
        content=html.render_icon(
            icons.get(object_ref.object_type, "link"),
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


def _vs_activation(title: str, has_foreign_changes: bool) -> Dictionary | None:
    elements: list[DictionaryEntry] = []

    if active_config.wato_activate_changes_comment_mode != "disabled":
        is_optional = active_config.wato_activate_changes_comment_mode != "enforce"
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
    def page(self) -> PageResult:
        check_csrf_token()
        user.need_permission("wato.activate")

        api_request = self.webapi_request()
        # ? type of activate_until is unclear
        activate_until = api_request.get("activate_until")
        if not activate_until:
            raise MKUserError("activate_until", _('Missing parameter "%s".') % "activate_until")

        manager = activate_changes.ActivateChangesManager()
        manager.load()
        # ? type of api_request is unclear
        affected_sites_request = ensure_str(  # pylint: disable= six-ensure-str-bin-call
            api_request.get("sites", "").strip()
        )
        if not affected_sites_request:
            affected_sites = manager.dirty_and_active_activation_sites()
        else:
            affected_sites = [SiteId(s) for s in affected_sites_request.split(",")]

        comment: str | None = api_request.get("comment", "").strip()

        activate_foreign = api_request.get("activate_foreign", "0") == "1"

        valuespec = _vs_activation("", manager.has_foreign_changes())
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
            activate_until=ensure_str(activate_until),  # pylint: disable= six-ensure-str-bin-call
            comment=comment,
            activate_foreign=activate_foreign,
        )

        return {
            "activation_id": activation_id,
        }


class PageAjaxActivationState(AjaxPage):
    def page(self) -> PageResult:
        user.need_permission("wato.activate")

        api_request = self.webapi_request()

        activation_id = api_request.get("activation_id")
        if not activation_id:
            raise MKUserError("activation_id", _('Missing parameter "%s".') % "activation_id")

        manager = activate_changes.ActivateChangesManager()
        manager.load()
        manager.load_activation(activation_id)

        return manager.get_state()


class ActivateChangesRequest(NamedTuple):
    site_id: SiteId
    domains: DomainRequests


@automation_command_registry.register
class AutomationActivateChanges(AutomationCommand):
    def command_name(self):
        return "activate-changes"

    def get_request(self):
        site_id = SiteId(request.get_ascii_input_mandatory("site_id"))
        activate_changes.verify_remote_site_config(site_id)

        try:
            serialized_domain_requests = ast.literal_eval(
                request.get_ascii_input_mandatory("domains")
            )
            if serialized_domain_requests and isinstance(serialized_domain_requests[0], str):
                serialized_domain_requests = [
                    asdict(DomainRequest(x)) for x in serialized_domain_requests
                ]
        except SyntaxError:
            raise MKAutomationException(
                _("Invalid request: %r") % request.get_ascii_input_mandatory("domains")
            )

        return ActivateChangesRequest(site_id=site_id, domains=serialized_domain_requests)

    def execute(self, api_request):
        return activate_changes.execute_activate_changes(
            activate_changes.parse_serialized_domain_requests(api_request.domains)
        )
