#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for activating pending changes. Does also replication with
remote sites in distributed WATO."""

import ast
import tarfile
import os
import json
from livestatus import SiteId, SiteConfiguration
from typing import Dict, NamedTuple, List, Optional, Iterator, Tuple, Union

from six import ensure_str

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
import cmk.gui.weblib as weblib
from cmk.gui.table import table_element, init_rowselect
import cmk.utils.render as render

from cmk.gui.plugins.wato.utils import mode_registry, sort_sites
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.type_defs import ActionResult
from cmk.gui.watolib.changes import ObjectRef, ObjectRefType
import cmk.gui.watolib.read_only as read_only
import cmk.gui.watolib.snapshots
import cmk.gui.watolib.changes
import cmk.gui.watolib.activate_changes
from cmk.gui.watolib.search import build_index_background

from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.globals import html, request as global_request, display_options
from cmk.gui.i18n import _
from cmk.gui.exceptions import MKUserError, FinalizeRequest
from cmk.gui.valuespec import Checkbox, Dictionary, TextAreaUnicode
from cmk.gui.valuespec import DictionaryEntry
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    make_checkbox_selection_topic,
    make_simple_link,
    make_javascript_link,
)
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.html import HTML


@mode_registry.register
class ModeActivateChanges(WatoMode, watolib.ActivateChanges):
    @classmethod
    def name(cls):
        return "changelog"

    @classmethod
    def permissions(cls):
        return []

    def __init__(self):
        self._value = {}
        super(ModeActivateChanges, self).__init__()
        super(ModeActivateChanges, self).load()

    def title(self):
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
        if config.user.may("wato.sites"):
            yield PageMenuEntry(
                title=_("Sites"),
                icon_name="sites",
                item=make_simple_link(makeuri_contextless(
                    global_request,
                    [("mode", "sites")],
                )),
            )

        if config.user.may("wato.auditlog"):
            yield PageMenuEntry(
                title=_("Audit log"),
                icon_name="auditlog",
                item=make_simple_link(watolib.folder_preserving_link([("mode", "auditlog")])),
            )

    def _page_menu_entries_all_sites(self) -> Iterator[PageMenuEntry]:
        if not self._may_activate_changes():
            return

        yield PageMenuEntry(
            title=_("Discard all pending changes"),
            icon_name="delete",
            item=make_simple_link(html.makeactionuri([("_action", "discard")])),
            name="discard_changes",
            is_enabled=self.has_changes() and self._get_last_wato_snapshot_file(),
        )

    def _page_menu_entries_selected_sites(self) -> Iterator[PageMenuEntry]:
        if not self._may_activate_changes():
            return

        if self._may_activate_changes():
            yield PageMenuEntry(
                title=_("Activate on selected sites"),
                icon_name={
                    "icon": "save",
                    "emblem": "refresh",
                },
                item=make_javascript_link("cmk.activation.activate_changes(\"selected\")"),
                name="activate_selected",
                is_shortcut=True,
                is_suggested=True,
                is_enabled=self.has_changes(),
            )

    def _may_discard_changes(self) -> bool:
        if not self._may_activate_changes():
            return False

        if not self._get_last_wato_snapshot_file():
            return False

        return True

    def _may_activate_changes(self) -> bool:
        if not config.user.may("wato.activate"):
            return False

        if not config.user.may("wato.activateforeign") and self._has_foreign_changes_on_any_site():
            return False

        if read_only.is_enabled() and not read_only.may_override():
            return False

        return True

    def action(self) -> ActionResult:
        if html.request.var("_action") != "discard":
            return None

        if not html.check_transaction():
            return None

        if not self._may_discard_changes():
            return None

        if not self.has_changes():
            return None

        # Now remove all currently pending changes by simply restoring the last automatically
        # taken snapshot. Then activate the configuration. This should revert all pending changes.
        file_to_restore = self._get_last_wato_snapshot_file()

        if not file_to_restore:
            raise MKUserError(None, _('There is no WATO snapshot to be restored.'))

        msg = _("Discarded pending changes (Restored %s)") % file_to_restore

        # All sites and domains can be affected by a restore: Better restart everything.
        watolib.add_change("changes-discarded",
                           msg,
                           domains=watolib.ABCConfigDomain.enabled_domains(),
                           need_restart=True)

        self._extract_snapshot(file_to_restore)
        cmk.gui.watolib.activate_changes.execute_activate_changes(
            [d.ident() for d in watolib.ABCConfigDomain.enabled_domains()])

        for site_id in config.activation_sites():
            self.confirm_site_changes(site_id)

        build_index_background()

        html.header(self.title(),
                    breadcrumb=self.breadcrumb(),
                    show_body_start=display_options.enabled(display_options.H),
                    show_top_heading=display_options.enabled(display_options.T))
        html.open_div(class_="wato")

        html.show_message(_("Successfully discarded all pending changes."))
        html.javascript("hide_changes_buttons();")
        html.footer()
        return FinalizeRequest(code=200)

    def _extract_snapshot(self, snapshot_file):
        self._extract_from_file(cmk.gui.watolib.snapshots.snapshot_dir + snapshot_file,
                                watolib.backup_domains)

    def _extract_from_file(self, filename: str,
                           elements: Dict[str, cmk.gui.watolib.snapshots.DomainSpec]) -> None:
        if not isinstance(elements, dict):
            raise NotImplementedError()

        cmk.gui.watolib.snapshots.extract_snapshot(tarfile.open(filename, "r"), elements)

    # TODO: Remove once new changes mechanism has been implemented
    def _get_last_wato_snapshot_file(self):
        for snapshot_file in self._get_snapshots():
            status = cmk.gui.watolib.snapshots.get_snapshot_status(snapshot_file)
            if status['type'] == 'automatic' and not status['broken']:
                return snapshot_file

    # TODO: Remove once new changes mechanism has been implemented
    def _get_snapshots(self):
        snapshots = []
        try:
            for f in os.listdir(cmk.gui.watolib.snapshots.snapshot_dir):
                if os.path.isfile(cmk.gui.watolib.snapshots.snapshot_dir + f):
                    snapshots.append(f)
            snapshots.sort(reverse=True)
        except OSError:
            pass
        return snapshots

    def page(self):
        self._activation_msg()
        self._activation_form()

        html.h3(_("Activation status"))
        self._activation_status()

        if self.has_changes():
            html.open_h3(class_="pending_changes_header")
            html.write_text(_("Pending changes"))
            html.div("", id_="row_info")
            html.close_h3()
            self._change_table()

    def _activation_msg(self):
        html.open_div(id_="async_progress_msg")
        html.show_message(self._get_initial_message())
        html.close_div()

    def _get_initial_message(self) -> str:
        changes = sum(len(self._changes_of_site(site_id)) for site_id in config.activation_sites())
        if changes == 0:
            if html.request.has_var("_finished"):
                return _("Activation has finished.")
            return _("Currently there are no changes to activate.")
        if changes == 1:
            return _("Currently there is one change to activate.")
        return _("Currently there are %d changes to activate.") % changes

    def _activation_form(self):
        if not config.user.may("wato.activate"):
            html.show_warning(_("You are not permitted to activate configuration changes."))
            return

        if not self._changes:
            return

        if not config.user.may("wato.activateforeign") \
           and self._has_foreign_changes_on_any_site():
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
            if config.user.may("wato.activateforeign"):
                html.show_warning(
                    _("There are some changes made by your colleagues that you will "
                      "activate if you proceed. You need to enable the checkbox above "
                      "to confirm the activation of these changes."))
            else:
                html.show_warning(
                    _("There are some changes made by your colleagues that you can not "
                      "activate because you are not permitted to. You can only activate "
                      "the changes on the sites that are not affected by these changes. "
                      "<br>"
                      "If you need to activate your changes on all sites, please contact "
                      "a permitted user to do it for you."))

        forms.end()
        html.hidden_field("selection_id", weblib.selection_id())
        html.hidden_fields()
        html.end_form()
        init_rowselect(self.name())

    def _change_table(self):
        with table_element("changes",
                           sortable=False,
                           searchable=False,
                           css="changes",
                           limit=None,
                           empty_text=_("Currently there are no changes to activate.")) as table:
            for _change_id, change in reversed(self._changes):
                css = []
                if self._is_foreign(change):
                    css.append("foreign")
                if not config.user.may("wato.activateforeign"):
                    css.append("not_permitted")

                table.row(css=" ".join(css))

                table.cell("", css="buttons")
                rendered = render_object_ref_as_icon(change["object"])
                if rendered:
                    html.write(rendered)

                table.cell(_("Time"), render.date_and_time(change["time"]), css="narrow nobr")
                table.cell(_("User"), css="narrow nobr")
                html.write_text(change["user_id"] if change["user_id"] else "")
                if self._is_foreign(change):
                    html.icon("foreign_changes", _("This change has been made by another user"))

                table.cell(_("Change"), change["text"])

                table.cell(_("Affected sites"), css="affected_sites")
                if self._affects_all_sites(change):
                    html.write_text("<i>%s</i>" % _("All sites"))
                else:
                    html.write_text(", ".join(sorted(change["affected_sites"])))

    def _activation_status(self):
        with table_element("site-status", searchable=False, sortable=False,
                           css="activation") as table:

            for site_id, site in sort_sites(config.activation_sites()):
                table.row()

                site_status, status = self._get_site_status(site_id, site)

                is_online = self._site_is_online(status)
                is_logged_in = self._site_is_logged_in(site_id, site)
                can_activate_all = self._can_activate_all(site_id)

                # Disable actions for offline sites and not logged in sites
                if not is_online or not is_logged_in:
                    can_activate_all = False

                need_restart = self._is_activate_needed(site_id)
                need_sync = self.is_sync_needed(site_id)
                need_action = need_restart or need_sync
                nr_changes = len(self._changes_of_site(site_id))

                # Activation checkbox
                table.cell("", css="buttons")
                if can_activate_all and nr_changes:
                    html.checkbox("site_%s" % site_id, need_action, cssclass="site_checkbox")

                # Iconbuttons
                table.cell(_("Actions"), css="buttons")

                if config.user.may("wato.sites"):
                    edit_url = watolib.folder_preserving_link([("mode", "edit_site"),
                                                               ("site", site_id)])
                    html.icon_button(edit_url, _("Edit the properties of this site"), "edit")

                # State
                if can_activate_all and need_sync:
                    html.icon_button(
                        url="javascript:void(0)",
                        id_="activate_%s" % site_id,
                        cssclass="activate_site",
                        title=_("This site is not update and needs a replication. Start it now."),
                        icon="need_replicate",
                        onclick="cmk.activation.activate_changes(\"site\", \"%s\")" % site_id)

                if can_activate_all and need_restart:
                    html.icon_button(
                        url="javascript:void(0)",
                        id_="activate_%s" % site_id,
                        cssclass="activate_site",
                        title=_(
                            "This site needs a restart for activating the changes. Start it now."),
                        icon="need_restart",
                        onclick="cmk.activation.activate_changes(\"site\", \"%s\")" % site_id)

                if can_activate_all and not need_action:
                    html.icon("siteuptodate", _("This site is up-to-date."))

                site_url = site.get("multisiteurl")
                if site_url:
                    html.icon_button(site_url,
                                     _("Open this site's local web user interface"),
                                     "url",
                                     target="_blank")

                table.text_cell(_("Site"), site.get("alias", site_id), css="narrow nobr")

                # Livestatus
                table.cell(_("Status"), css="narrow nobr")
                html.status_label(content=status,
                                  status=status,
                                  title=_("This site is %s") % status)

                # Livestatus-/Checkmk-Version
                table.cell(_("Version"),
                           site_status.get("livestatus_version", ""),
                           css="narrow nobr")

                table.cell(_("Changes"), "%d" % nr_changes, css="number narrow nobr")

                table.cell(_("Progress"), css="repprogress")
                html.open_div(id_="site_%s_status" % site_id, class_=["msg"])
                html.close_div()
                html.open_div(id_="site_%s_progress" % site_id, class_=["progress"])
                html.close_div()

                table.cell(_("Details"), css="details")
                html.open_div(id_="site_%s_details" % site_id)

                last_state = self._last_activation_state(site_id)

                if not is_logged_in:
                    html.write_text(_("Is not logged in.") + " ")

                if not last_state:
                    html.write_text(_("Has never been activated"))
                elif (need_action and
                      last_state["_state"] == cmk.gui.watolib.activate_changes.STATE_SUCCESS):
                    html.write_text(_("Activation needed"))
                else:
                    html.javascript("cmk.activation.update_site_activation_state(%s);" %
                                    json.dumps(last_state))

                html.close_div()

    def _can_activate_all(self, site_id: SiteId) -> bool:
        return not self._site_has_foreign_changes(site_id) or config.user.may(
            "wato.activateforeign")

    def _get_selected_sites(self) -> List[SiteId]:
        return [
            "site_%s" % site_id
            for site_id, site in sort_sites(config.activation_sites())
            if len(self._changes_of_site(site_id)) and self._can_activate_all(site_id) and
            self._is_active_site(
                site_id=site_id,
                site=site,
                status=self._get_site_status(site_id, site)[1],
            )
        ]

    def _select_sites_with_pending_changes(self) -> None:
        selected_sites: List[SiteId] = self._get_selected_sites()
        config.user.set_rowselection(weblib.selection_id(), self.name(), selected_sites, "set")

    def _is_active_site(self, site_id: SiteId, site: SiteConfiguration, status: str) -> bool:
        return self._site_is_online(status) and self._site_is_logged_in(site_id, site)


def render_object_ref_as_icon(object_ref: Optional[ObjectRef]) -> Optional[HTML]:
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

    return html.render_a(
        content=html.render_icon(
            icons.get(object_ref.object_type, "link"),
            title="%s: %s" % (object_ref.object_type.name, title) if title else None,
        ),
        href=url,
    )


def render_object_ref(object_ref: Optional[ObjectRef]) -> Union[str, HTML, None]:
    url, title = _get_object_reference(object_ref)
    if title and not url:
        return title
    if not title:
        return None
    return html.render_a(title, href=url)


# TODO: Move this to some generic place
def _get_object_reference(object_ref: Optional[ObjectRef]) -> Tuple[Optional[str], Optional[str]]:
    if object_ref is None:
        return None, None

    if object_ref.object_type is ObjectRefType.Host:
        host = watolib.Host.host(object_ref.ident)
        if host:
            return host.edit_url(), host.name()
        return None, object_ref.ident

    if object_ref.object_type is ObjectRefType.Folder:
        if watolib.Folder.folder_exists(object_ref.ident):
            folder = watolib.Folder.folder(object_ref.ident)
            return folder.url(), folder.title()
        return None, object_ref.ident

    if object_ref.object_type is ObjectRefType.User:
        url = makeuri_contextless(global_request, [
            ("mode", "edit_user"),
            ("edit", object_ref.ident),
        ],
                                  filename="wato.py")
        return url, object_ref.ident

    if object_ref.object_type is ObjectRefType.Rule:
        url = makeuri_contextless(global_request, [
            ("mode", "edit_rule"),
            ("varname", object_ref.labels["ruleset"]),
            ("rule_id", object_ref.ident),
        ],
                                  filename="wato.py")
        return url, object_ref.ident

    if object_ref.object_type is ObjectRefType.Ruleset:
        url = makeuri_contextless(global_request, [
            ("mode", "edit_ruleset"),
            ("varname", object_ref.ident),
        ],
                                  filename="wato.py")
        return url, object_ref.ident

    return None, object_ref.ident


def _vs_activation(title: str, has_foreign_changes: bool) -> Optional[Dictionary]:
    elements: List[DictionaryEntry] = []

    if config.wato_activate_changes_comment_mode != "disabled":
        is_optional = config.wato_activate_changes_comment_mode != "enforce"
        elements.append(
            ("comment",
             TextAreaUnicode(
                 title=_("Comment (optional)") if is_optional else _("Comment"),
                 cols=40,
                 try_max_width=True,
                 rows=1,
                 help=_("You can provide an optional comment for the current activation. "
                        "This can be useful to document the reason why the changes you "
                        "activate have been made."),
                 allow_empty=is_optional,
             )))

    if has_foreign_changes and config.user.may("wato.activateforeign"):
        elements.append(("foreign",
                         Checkbox(
                             title=_("Activate foreign changes"),
                             label=_("Activate changes of other users"),
                         )))

    if not elements:
        return None

    return Dictionary(
        title=title,
        elements=elements,
        optional_keys=[],
        render="form_part",
    )


@page_registry.register_page("ajax_start_activation")
class ModeAjaxStartActivation(AjaxPage):
    def page(self):
        check_csrf_token()
        config.user.need_permission("wato.activate")

        request = self.webapi_request()

        activate_until = request.get("activate_until")
        if not activate_until:
            raise MKUserError("activate_until", _("Missing parameter \"%s\".") % "activate_until")

        manager = watolib.ActivateChangesManager()
        manager.load()

        affected_sites_request = ensure_str(request.get("sites", "").strip())
        if not affected_sites_request:
            affected_sites = manager.dirty_and_active_activation_sites()
        else:
            affected_sites = affected_sites_request.split(",")

        comment: Optional[str] = request.get("comment", "").strip()

        activate_foreign = request.get("activate_foreign", "0") == "1"

        valuespec = _vs_activation("", manager.has_foreign_changes())
        if valuespec:
            valuespec.validate_value({
                "comment": comment,
                "foreign": activate_foreign,
            }, "activate")

        if comment == "":
            comment = None

        activation_id = manager.start(
            sites=affected_sites,
            activate_until=ensure_str(activate_until),
            comment=None if comment is None else ensure_str(comment),
            activate_foreign=activate_foreign,
        )

        return {
            "activation_id": activation_id,
        }


@page_registry.register_page("ajax_activation_state")
class ModeAjaxActivationState(AjaxPage):
    def page(self):
        config.user.need_permission("wato.activate")

        request = self.webapi_request()

        activation_id = request.get("activation_id")
        if not activation_id:
            raise MKUserError("activation_id", _("Missing parameter \"%s\".") % "activation_id")

        manager = watolib.ActivateChangesManager()
        manager.load()
        manager.load_activation(activation_id)

        return manager.get_state()


ActivateChangesRequest = NamedTuple("ActivateChangesRequest", [("site_id", str),
                                                               ("domains", List[str])])


@watolib.automation_command_registry.register
class AutomationActivateChanges(watolib.AutomationCommand):
    def command_name(self):
        return "activate-changes"

    def get_request(self):
        site_id = html.request.get_ascii_input_mandatory("site_id")
        cmk.gui.watolib.activate_changes.verify_remote_site_config(site_id)

        try:
            domains = ast.literal_eval(html.request.get_ascii_input_mandatory("domains"))
        except SyntaxError:
            raise watolib.MKAutomationException(
                _("Invalid request: %r") % html.request.get_ascii_input_mandatory("domains"))

        return ActivateChangesRequest(site_id=site_id, domains=domains)

    def execute(self, request):
        return cmk.gui.watolib.activate_changes.execute_activate_changes(request.domains)
