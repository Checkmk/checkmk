#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mange custom attributes of users and hosts"""

import abc
import re
from collections.abc import Collection, Iterable
from datetime import datetime
from typing import Generic, TypeVar

import cmk.gui.watolib.changes as _changes
from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.table import table_element
from cmk.gui.type_defs import (
    ActionResult,
    Choices,
    CustomAttrSpec,
    CustomHostAttrSpec,
    CustomUserAttrSpec,
    PermissionName,
)
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import make_confirm_delete_link, makeactionuri, makeuri, makeuri_contextless
from cmk.gui.watolib.custom_attributes import (
    load_custom_attrs_from_mk_file,
    save_custom_attrs_to_mk_file,
    update_host_custom_attrs,
    update_user_custom_attrs,
)
from cmk.gui.watolib.host_attributes import host_attribute_topic_registry
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.users import remove_custom_attribute_from_all_users, user_features_registry


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeEditCustomUserAttr)
    mode_registry.register(ModeEditCustomHostAttr)
    mode_registry.register(ModeCustomUserAttrs)
    mode_registry.register(ModeCustomHostAttrs)


def custom_attr_types() -> Choices:
    return [
        ("TextAscii", _("Simple Text")),
    ]


_T_CustomAttrSpec = TypeVar("_T_CustomAttrSpec", bound=CustomAttrSpec)


# TODO: Refactor to be valuespec based
class ModeEditCustomAttr(WatoMode, abc.ABC, Generic[_T_CustomAttrSpec]):
    def _from_vars(self):
        self._name = request.get_ascii_input("edit")  # missing -> new custom attr
        self._new = self._name is None

        # TODO: Inappropriate Intimacy: custom host attributes should not now about
        #       custom user attributes and vice versa. The only reason they now about
        #       each other now is that they are stored in one file.
        self._all_attrs = load_custom_attrs_from_mk_file(lock=transactions.is_transaction())

        if not self._new:
            matching_attrs = [a for a in self._attrs if a["name"] == self._name]
            if not matching_attrs:
                raise MKUserError(None, _("The attribute does not exist."))
            self._attr: _T_CustomAttrSpec = matching_attrs[0]
        else:
            self._attr = self._default_value

    @property
    @abc.abstractmethod
    def _type(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def _attrs(self) -> list[_T_CustomAttrSpec]: ...

    @property
    @abc.abstractmethod
    def _topics(self) -> Choices:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def _default_value(self) -> _T_CustomAttrSpec: ...

    @property
    @abc.abstractmethod
    def _macro_help(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def _macro_label(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def _update_config(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _show_in_table_option(self) -> None:
        """Option to show the custom attribute in overview tables of the setup menu."""
        raise NotImplementedError()

    def _render_table_option(self, section_title: str, label: str, help_text: str) -> None:
        """Helper method to implement _show_in_table_option."""
        forms.section(section_title)
        html.help(help_text)
        html.checkbox("show_in_table", self._attr["show_in_table"] or False, label=label)

    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Attribute"), breadcrumb, form_name="attr", button_name="_save"
        )

    def _add_extra_attrs_from_html_vars(self) -> None:
        pass

    def _add_extra_form_sections(self) -> None:
        pass

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return None

        title = request.get_str_input_mandatory("title").strip()
        if not title:
            raise MKUserError("title", _("Please specify a title."))

        for this_attr in self._attrs:
            if title == this_attr["title"] and self._name != this_attr["name"]:
                raise MKUserError(
                    "alias",
                    _("This alias is already used by the attribute %s.") % this_attr["name"],
                )

        topic = request.get_str_input_mandatory("topic", "").strip()
        help_txt = request.get_str_input_mandatory("help", "").strip()
        show_in_table = html.get_checkbox("show_in_table")
        add_custom_macro = html.get_checkbox("add_custom_macro")

        if self._new:
            self._name = request.get_ascii_input_mandatory("name", "").strip()
            if not self._name:
                raise MKUserError("name", _("Please specify a name for the new attribute."))
            if " " in self._name:
                raise MKUserError("name", _("Sorry, spaces are not allowed in attribute names."))
            if not re.match("^[-a-z0-9A-Z_]*$", self._name):
                raise MKUserError(
                    "name",
                    _(
                        "Invalid attribute name. Only the characters a-z, A-Z, 0-9, _ and - are allowed."
                    ),
                )
            if [a for a in self._attrs if a["name"] == self._name]:
                raise MKUserError("name", _("Sorry, there is already an attribute with that name."))

            ty = request.get_ascii_input_mandatory("type", "").strip()
            if ty not in [t[0] for t in custom_attr_types()]:
                raise MKUserError("type", _("The choosen attribute type is invalid."))

            self._attr["name"] = self._name
            self._attr["type"] = "TextAscii"
            self._attr["title"] = title
            self._attr["topic"] = topic
            self._attr["help"] = help_txt
            self._attr["show_in_table"] = show_in_table
            self._attr["add_custom_macro"] = add_custom_macro

            self._attrs.append(self._attr)

            _changes.add_change(
                action_name="edit-%sattr" % self._type,
                text=_("Create new %s attribute %s") % (self._type, self._name),
                user_id=user.id,
                use_git=active_config.wato_use_git,
            )
        else:
            _changes.add_change(
                action_name="edit-%sattr" % self._type,
                text=_("Modified %s attribute %s") % (self._type, self._name),
                user_id=user.id,
                use_git=active_config.wato_use_git,
            )
            self._attr["title"] = title
            self._attr["topic"] = topic
            self._attr["help"] = help_txt
            self._attr["show_in_table"] = show_in_table
            self._attr["add_custom_macro"] = add_custom_macro

        self._add_extra_attrs_from_html_vars()

        save_custom_attrs_to_mk_file(self._all_attrs)
        self._update_config()

        return redirect(mode_url(self._type + "_attrs"))

    def page(self) -> None:
        # TODO: remove subclass specific things specifict things (everything with _type == 'user')
        with html.form_context("attr"):
            forms.header(_("Properties"))
            forms.section(_("Name"), simple=not self._new, is_required=True)
            html.help(
                _(
                    "The name of the attribute is used as an internal key. It cannot be "
                    "changed later."
                )
            )
            if self._new:
                html.text_input("name", self._attr["name"], size=61)
                html.set_focus("name")
            else:
                html.write_text_permissive(self._name)
                html.set_focus("title")

            forms.section(_("Title") + "<sup>*</sup>", is_required=True)
            html.help(_("The title is used to label this attribute."))
            html.text_input("title", self._attr["title"], size=61)

            forms.section(_("Topic"))
            html.help(_("The attribute is added to this section in the edit dialog."))
            html.dropdown("topic", self._topics, deflt=self._attr["topic"])

            forms.section(_("Help text") + "<sup>*</sup>")
            html.help(_("You might want to add some helpful description for the attribute."))
            html.text_area("help", self._attr["help"])

            forms.section(_("Data type"))
            html.help(_("The type of information to be stored in this attribute."))
            if self._new:
                html.dropdown("type", custom_attr_types(), deflt=self._attr["type"])
            else:
                html.write_text_permissive(dict(custom_attr_types())[self._attr["type"]])

            self._add_extra_form_sections()
            self._show_in_table_option()

            forms.section(_("Add to monitoring configuration"))
            html.help(self._macro_help)
            html.checkbox(
                "add_custom_macro",
                self._attr["add_custom_macro"] or False,
                label=self._macro_label,
            )

            forms.end()
            html.show_localization_hint()
            html.hidden_fields()


class ModeEditCustomUserAttr(ModeEditCustomAttr[CustomUserAttrSpec]):
    @classmethod
    def name(cls) -> str:
        return "edit_user_attr"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["users", "custom_attributes"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeCustomUserAttrs

    @property
    def _type(self) -> str:
        return "user"

    @property
    def _attrs(self) -> list[CustomUserAttrSpec]:
        return self._all_attrs["user"]

    @property
    def _topics(self) -> Choices:
        return [
            ("ident", _("Identity")),
            ("security", _("Security")),
            ("notify", _("Notifications")),
            ("personal", _("Personal settings")),
        ]

    @property
    def _default_value(self) -> CustomUserAttrSpec:
        return CustomUserAttrSpec(
            {
                "type": "TextAscii",
                "name": "",
                "title": "",
                "topic": "personal",
                "help": "",
                "show_in_table": False,
                "add_custom_macro": False,
                "user_editable": True,
            }
        )

    @property
    def _macro_help(self) -> str:
        return _(
            "The attribute can be added to the contact definiton in order to use it for notifications."
        )

    @property
    def _macro_label(self) -> str:
        return _("Make this variable available in notifications")

    def _update_config(self) -> None:
        update_user_custom_attrs(datetime.now())

    def _show_in_table_option(self) -> None:
        self._render_table_option(
            _("Show in user table"),
            _("Show this attribute in the user table of the setup menu"),
            _(
                "This attribute is only visibile in the edit user "
                "page by default. This option displays it in the user "
                "overview table of the setup menu as well."
            ),
        )

    def _add_extra_attrs_from_html_vars(self) -> None:
        self._attr["user_editable"] = html.get_checkbox("user_editable")

    def _add_extra_form_sections(self) -> None:
        forms.section(_("Editable by Users"))
        html.help(_("It is possible to let users edit their custom attributes."))
        html.checkbox(
            "user_editable",
            self._attr.get("user_editable", True) or False,
            label=_("Users can change this attribute in their personal settings"),
        )

    def title(self) -> str:
        if self._new:
            return _("Add user attribute")
        return _("Edit user attribute")


class ModeEditCustomHostAttr(ModeEditCustomAttr[CustomHostAttrSpec]):
    @classmethod
    def name(cls) -> str:
        return "edit_host_attr"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "manage_hosts", "custom_attributes"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeCustomHostAttrs

    @property
    def _type(self) -> str:
        return "host"

    @property
    def _attrs(self) -> list[CustomHostAttrSpec]:
        return self._all_attrs["host"]

    @property
    def _topics(self) -> Choices:
        return host_attribute_topic_registry.get_choices()

    @property
    def _default_value(self) -> CustomHostAttrSpec:
        return CustomHostAttrSpec(
            {
                "type": "TextAscii",
                "name": "",
                "title": "",
                "topic": "custom_attributes",
                "help": "",
                "show_in_table": False,
                "add_custom_macro": False,
            }
        )

    @property
    def _macro_help(self) -> str:
        return _(
            "The attribute can be added to the host definition in order to use it as custom host attribute "
            "(sometimes called monitoring macro) in different places, for example as in check commands or "
            "notifications. You can also only display this attribute in the status GUI when enabling this "
            "option."
        )

    @property
    def _macro_label(self) -> str:
        return _(
            "Make this custom attribute available to check commands, notifications and the status GUI"
        )

    def _update_config(self) -> None:
        update_host_custom_attrs(pprint_value=active_config.wato_pprint_config)

    def _show_in_table_option(self) -> None:
        self._render_table_option(
            _("Show in host tables"),
            _("Show this attribute in host tables of the setup menu"),
            _(
                "This attribute is only visibile in the edit host and folder "
                "pages by default. This option displays it in host overview "
                "tables of the setup menu as well."
            ),
        )

    def title(self) -> str:
        if self._new:
            return _("Add host attribute")
        return _("Edit host attribute")


class ModeCustomAttrs(WatoMode, abc.ABC, Generic[_T_CustomAttrSpec]):
    def __init__(self) -> None:
        super().__init__()
        # TODO: Inappropriate Intimacy: custom host attributes should not now about
        #       custom user attributes and vice versa. The only reason they now about
        #       each other now is that they are stored in one file.
        self._all_attrs = load_custom_attrs_from_mk_file(lock=transactions.is_transaction())

    @property
    @abc.abstractmethod
    def _type(self) -> str:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def _attrs(self) -> list[_T_CustomAttrSpec]: ...

    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def _update_config(self):
        raise NotImplementedError()

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="attributes",
                    title=_("Attributes"),
                    topics=[
                        PageMenuTopic(
                            title=_("Create"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add attribute"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        folder_preserving_link(
                                            [("mode", "edit_%s_attr" % self._type)]
                                        )
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="related",
                    title=_("Related"),
                    topics=[
                        PageMenuTopic(
                            title=_("Setup"),
                            entries=list(self._page_menu_entries_related()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

    @abc.abstractmethod
    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        raise NotImplementedError()

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            request.del_var("_transid")
            return redirect(makeuri(request=request, addvars=list(request.itervars())))

        if not request.var("_delete"):
            request.del_var("_transid")
            return redirect(makeuri(request=request, addvars=list(request.itervars())))

        delname = request.get_ascii_input_mandatory("_delete")
        for index, attr in enumerate(self._attrs):
            if attr["name"] == delname:
                self._attrs.pop(index)
        save_custom_attrs_to_mk_file(self._all_attrs)
        remove_custom_attribute_from_all_users(delname, user_features_registry.features().sites)
        self._update_config()
        _changes.add_change(
            action_name="edit-%sattrs" % self._type,
            text=_("Deleted attribute %s") % (delname),
            user_id=user.id,
            use_git=active_config.wato_use_git,
        )
        return redirect(self.mode_url())

    def page(self) -> None:
        if not self._attrs:
            html.div(_("No custom attributes are defined yet."), class_="info")
            return

        with table_element(self._type + "attrs") as table:
            for nr, custom_attr in enumerate(sorted(self._attrs, key=lambda x: x["title"])):
                table.row()
                table.cell("#", css=["narrow nowrap"])
                html.write_text_permissive(nr)

                table.cell(_("Actions"), css=["buttons"])
                edit_url = folder_preserving_link(
                    [("mode", "edit_%s_attr" % self._type), ("edit", custom_attr["name"])]
                )
                delete_url = make_confirm_delete_link(
                    url=makeactionuri(request, transactions, [("_delete", custom_attr["name"])]),
                    title=_("Delete custom attribute #%d") % nr,
                    suffix=custom_attr["title"],
                    message=_("Name: %s") % custom_attr["name"],
                )
                html.icon_button(edit_url, _("Properties"), "edit")
                html.icon_button(delete_url, _("Delete"), "delete")

                table.cell(_("Name"), custom_attr["name"])
                table.cell(_("Title"), custom_attr["title"])
                table.cell(_("Type"), dict(custom_attr_types())[custom_attr["type"]])


class ModeCustomUserAttrs(ModeCustomAttrs[CustomUserAttrSpec]):
    @classmethod
    def name(cls) -> str:
        return "user_attrs"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["users", "custom_attributes"]

    @property
    def _type(self) -> str:
        return "user"

    @property
    def _attrs(self) -> list[CustomUserAttrSpec]:
        return self._all_attrs["user"]

    def _update_config(self) -> None:
        update_user_custom_attrs(datetime.now())

    def title(self) -> str:
        return _("Custom user attributes")

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Users"),
            icon_name="users",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", "users")],
                    filename="wato.py",
                )
            ),
        )


class ModeCustomHostAttrs(ModeCustomAttrs[CustomHostAttrSpec]):
    @classmethod
    def name(cls) -> str:
        return "host_attrs"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "manage_hosts", "custom_attributes"]

    @property
    def _type(self) -> str:
        return "host"

    @property
    def _attrs(self) -> list[CustomHostAttrSpec]:
        return self._all_attrs["host"]

    def _update_config(self) -> None:
        update_host_custom_attrs(pprint_value=active_config.wato_pprint_config)

    def title(self) -> str:
        return _("Custom host attributes")

    def get_attributes(self):
        return self._attrs

    def _page_menu_entries_related(self) -> Iterable[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Hosts"),
            icon_name="folder",
            item=make_simple_link(
                makeuri_contextless(
                    request,
                    [("mode", "folder")],
                    filename="wato.py",
                )
            ),
        )
