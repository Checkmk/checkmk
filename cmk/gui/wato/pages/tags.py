#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Manage the variable config.wato_host_tags -> The set of tags to be assigned
to hosts and that is the basis of the rules."""

import abc
from typing import List, Optional, Set, Type, Union

import cmk.utils.tags

import cmk.gui.forms as forms
import cmk.gui.watolib.changes as _changes
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import load_config
from cmk.gui.exceptions import FinalizeRequest, MKGeneralException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _u
from cmk.gui.page_menu import (
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.plugins.wato.utils import (
    flash,
    make_confirm_link,
    mode_registry,
    mode_url,
    redirect,
    WatoMode,
)
from cmk.gui.plugins.wato.utils.html_elements import wato_html_head
from cmk.gui.plugins.wato.utils.main_menu import MainMenu, MenuItem
from cmk.gui.table import Table, table_element
from cmk.gui.type_defs import ActionResult
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import (
    Dictionary,
    FixedValue,
    Foldable,
    ID,
    ListChoice,
    ListOf,
    OptionalDropdownChoice,
    TextInput,
    Transform,
    Tuple,
)
from cmk.gui.watolib.host_attributes import host_attribute, undeclare_host_tag_attribute
from cmk.gui.watolib.hosts_and_folders import (
    CREFolder,
    CREHost,
    Folder,
    folder_preserving_link,
    make_action_link,
)
from cmk.gui.watolib.rulesets import Ruleset
from cmk.gui.watolib.tags import (
    ABCOperation,
    change_host_tags_in_folders,
    identify_modified_tags,
    OperationRemoveAuxTag,
    OperationRemoveTagGroup,
    OperationReplaceGroupedTags,
    TagCleanupMode,
    TagConfigFile,
)


class ABCTagMode(WatoMode, abc.ABC):
    def __init__(self) -> None:
        super().__init__()
        self._tag_config_file = TagConfigFile()
        self._load_effective_config()

    def _save_tags_and_update_hosts(self, tag_config):
        self._tag_config_file.save(tag_config)
        load_config()
        Folder.invalidate_caches()
        Folder.root_folder().rewrite_hosts_files()

    def _load_effective_config(self):
        self._builtin_config = cmk.utils.tags.BuiltinTagConfig()

        self._tag_config = cmk.utils.tags.TagConfig.from_config(
            self._tag_config_file.load_for_reading()
        )

        self._effective_config = cmk.utils.tags.TagConfig.from_config(
            self._tag_config.get_dict_format()
        )
        self._effective_config += self._builtin_config

    def _get_tags_using_aux_tag(
        self, aux_tag: cmk.utils.tags.AuxTag
    ) -> Set[cmk.utils.tags.GroupedTag]:
        return {
            tag  #
            for tag_group in self._effective_config.tag_groups
            for tag in tag_group.tags
            if aux_tag.id in tag.aux_tag_ids
        }


@mode_registry.register
class ModeTags(ABCTagMode):
    @classmethod
    def name(cls):
        return "tags"

    @classmethod
    def permissions(cls):
        return ["hosttags"]

    def title(self):
        return _("Tag groups")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="tags",
                    title=_("Tags"),
                    topics=[
                        PageMenuTopic(
                            title=_("Add tags"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Add tag group"),
                                    icon_name="new",
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "edit_tag")])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                                PageMenuEntry(
                                    title=_("Add aux tag"),
                                    icon_name={"icon": "tag", "emblem": "add"},
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "edit_auxtag")])
                                    ),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Analyze"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Tag usage"),
                                    icon_name={
                                        "icon": "tag",
                                        "emblem": "search",
                                    },
                                    item=make_simple_link(
                                        folder_preserving_link([("mode", "tag_usage")])
                                    ),
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
            return redirect(mode_url("tags"))

        if request.has_var("_delete"):
            return self._delete_tag_group()

        if request.has_var("_del_aux"):
            return self._delete_aux_tag()

        if request.var("_move"):
            return self._move_tag_group()

        return redirect(mode_url("tags"))

    def _delete_tag_group(self) -> ActionResult:
        del_id = request.get_item_input("_delete", dict(self._tag_config.get_tag_group_choices()))[
            1
        ]

        if not request.has_var("_repair") and self._is_cleaning_up_user_tag_group_to_builtin(
            del_id
        ):
            message: Union[bool, str] = (
                _('Transformed the user tag group "%s" to builtin.') % del_id
            )
        else:
            message = _rename_tags_after_confirmation(
                self.breadcrumb(), OperationRemoveTagGroup(del_id)
            )
            if message is False:
                return FinalizeRequest(code=200)

        if message:
            self._tag_config.remove_tag_group(del_id)
            try:
                self._tag_config.validate_config()
            except MKGeneralException as e:
                raise MKUserError(None, "%s" % e)
            self._save_tags_and_update_hosts(self._tag_config.get_dict_format())
            _changes.add_change("edit-tags", _("Removed tag group %s (%s)") % (message, del_id))
            if isinstance(message, str):
                flash(message)
        return redirect(mode_url("tags"))

    def _is_cleaning_up_user_tag_group_to_builtin(self, del_id):
        """The "Agent type" tag group was user defined in previous versions

        Have a look at cmk/gui/watolib/tags.py (_migrate_old_sample_config_tag_groups)
        for further information

        In case a user wants to remove such a "agent" tag group do not perform the
        usual validations since this is not a real delete operation because it just
        replaces a custom group with a builtin one.
        """
        if del_id != "agent":
            return False

        builtin_tg = self._builtin_config.get_tag_group("agent")
        if builtin_tg is None:
            return False

        user_tg = self._tag_config.get_tag_group("agent")
        if user_tg is None:
            return False

        # When the tag choices are matching the builtin tag group choices
        # simply allow removal without confirm
        return builtin_tg.get_tag_ids() == user_tg.get_tag_ids()

    def _delete_aux_tag(self) -> ActionResult:
        del_id = request.get_item_input(
            "_del_aux", dict(self._tag_config.aux_tag_list.get_choices())
        )[1]

        # Make sure that this aux tag is not begin used by any tag group
        for group in self._tag_config.tag_groups:
            for grouped_tag in group.tags:
                if del_id in grouped_tag.aux_tag_ids:
                    raise MKUserError(
                        None,
                        _(
                            "You cannot delete this auxiliary tag. "
                            "It is being used in the tag group <b>%s</b>."
                        )
                        % group.title,
                    )

        message = _rename_tags_after_confirmation(self.breadcrumb(), OperationRemoveAuxTag(del_id))
        if message is False:
            return FinalizeRequest(code=200)

        if message:
            self._tag_config.aux_tag_list.remove(del_id)
            try:
                self._tag_config.validate_config()
            except MKGeneralException as e:
                raise MKUserError(None, "%s" % e)
            self._save_tags_and_update_hosts(self._tag_config.get_dict_format())
            _changes.add_change("edit-tags", _("Removed auxiliary tag %s (%s)") % (message, del_id))
            if isinstance(message, str):
                flash(message)
        return redirect(mode_url("tags"))

    # Mypy wants the explicit return, pylint does not like it.
    def _move_tag_group(self) -> ActionResult:  # pylint: disable=useless-return
        move_nr = request.get_integer_input_mandatory("_move")
        move_to = request.get_integer_input_mandatory("_index")

        moved = self._tag_config.tag_groups.pop(move_nr)
        self._tag_config.tag_groups.insert(move_to, moved)

        try:
            self._tag_config.validate_config()
        except MKGeneralException as e:
            raise MKUserError(None, "%s" % e)
        self._tag_config_file.save(self._tag_config.get_dict_format())
        self._load_effective_config()
        _changes.add_change("edit-tags", _("Changed order of tag groups"))
        return None

    def page(self):
        if not self._tag_config.tag_groups and not self._tag_config.get_aux_tags():
            MainMenu(
                [
                    MenuItem(
                        "edit_tag",
                        _("Create new tag group"),
                        "new",
                        "hosttags",
                        _(
                            "Each tag group will create one dropdown choice in the host configuration."
                        ),
                    ),
                    MenuItem(
                        "edit_auxtag",
                        _("Create new auxiliary tag"),
                        "new",
                        "hosttags",
                        _(
                            "You can have these tags automatically added if certain primary tags are set."
                        ),
                    ),
                ]
            ).show()
            return

        self._show_customized_builtin_warning()

        self._render_tag_group_list()
        self._render_aux_tag_list()

    def _show_customized_builtin_warning(self):
        customized = [
            tg.id
            for tg in self._effective_config.tag_groups
            if self._builtin_config.tag_group_exists(tg.id)
            and self._tag_config.tag_group_exists(tg.id)
        ]

        if not customized:
            return

        html.show_warning(
            _(
                "You have customized the tag group(s) <tt>%s</tt> in your tag configuration. "
                "In current Checkmk versions these are <i>builtin</i> tag groups which "
                "can not be customized anymore. Your customized tag group will work for "
                "the moment, but needs to be migrated until 1.7. With 1.7 it won't work "
                "anymore."
            )
            % ", ".join(customized)
        )

    def _render_tag_group_list(self):
        with table_element(
            "tags",
            _("Tag groups"),
            help=(
                _(
                    "Tags are the basis of Check_MK's rule based configuration. "
                    "If the first step you define arbitrary tag groups. A host "
                    "has assigned exactly one tag out of each group. These tags can "
                    "later be used for defining parameters for hosts and services, "
                    "such as <i>disable notifications for all hosts with the tags "
                    "<b>Network device</b> and <b>Test</b></i>."
                )
            ),
            empty_text=_("You haven't defined any tag groups yet."),
            searchable=False,
            sortable=False,
        ) as table:

            for nr, tag_group in enumerate(self._effective_config.tag_groups):
                table.row()
                table.cell(_("Actions"), css=["buttons"])
                self._show_tag_icons(tag_group, nr)

                table.cell(_("ID"), tag_group.id)
                table.cell(_("Title"), tag_group.title)
                table.cell(_("Topic"), tag_group.topic or _("Tags"))
                table.cell(_("Demonstration"), sortable=False)
                if tag_group.help:
                    html.help(tag_group.help)
                html.begin_form("tag_%s" % tag_group.id)
                tag_group_attribute = host_attribute("tag_%s" % tag_group.id)
                tag_group_attribute.render_input("", tag_group_attribute.default_value())
                html.end_form()

    def _show_tag_icons(self, tag_group, nr):
        # Tag groups were made builtin with ~1.4. Previously users could modify
        # these groups.  These users now have the modified tag groups in their
        # user configuration and should be able to cleanup this using the GUI
        # for the moment. Make the buttons available to the users.
        if self._builtin_config.tag_group_exists(
            tag_group.id
        ) and not self._tag_config.tag_group_exists(tag_group.id):
            html.i("(%s)" % _("builtin"))
            return

        edit_url = folder_preserving_link([("mode", "edit_tag"), ("edit", tag_group.id)])
        html.icon_button(edit_url, _("Edit this tag group"), "edit")

        html.element_dragger_url("tr", base_url=make_action_link([("mode", "tags"), ("_move", nr)]))

        delete_url = make_confirm_link(
            url=make_action_link([("mode", "tags"), ("_delete", tag_group.id)]),
            message=_("Do you really want to delete the tag group '%s'?") % tag_group.id,
        )
        html.icon_button(delete_url, _("Delete this tag group"), "delete")

    def _render_aux_tag_list(self) -> None:
        with table_element(
            "auxtags",
            _("Auxiliary tags"),
            help=_(
                "Auxiliary tags can be attached to other tags. That way "
                "you can for example have all hosts with the tag <tt>cmk-agent</tt> "
                "get also the tag <tt>tcp</tt>. This makes the configuration of "
                "your hosts easier."
            ),
            empty_text=_("You haven't defined any auxiliary tags."),
            searchable=False,
        ) as table:

            for aux_tag in self._effective_config.aux_tag_list.get_tags():
                table.row()
                table.cell(_("Actions"), css=["buttons"])
                self._show_aux_tag_icons(aux_tag)

                table.cell(_("ID"), aux_tag.id)

                table.cell(_("Title"), _u(aux_tag.title))
                table.cell(_("Topic"), _u(aux_tag.topic) if aux_tag.topic else _("Tags"))
                table.cell(
                    _("Tags using this auxiliary tag"),
                    ", ".join(
                        sorted(
                            tag.id
                            for tag in self._get_tags_using_aux_tag(aux_tag)
                            if tag.id is not None
                        )
                    ),
                )

    def _show_aux_tag_icons(self, aux_tag: cmk.utils.tags.AuxTag) -> None:
        if aux_tag.id in self._builtin_config.aux_tag_list.get_tag_ids():
            html.i("(%s)" % _("builtin"))
            return

        edit_url = folder_preserving_link([("mode", "edit_auxtag"), ("edit", aux_tag.id)])
        delete_url = make_confirm_link(
            url=make_action_link([("mode", "tags"), ("_del_aux", aux_tag.id)]),
            message=_("Do you really want to delete the auxiliary tag '%s'?") % aux_tag.id,
        )
        html.icon_button(edit_url, _("Edit this auxiliary tag"), "edit")
        html.icon_button(delete_url, _("Delete this auxiliary tag"), "delete")


class ABCEditTagMode(ABCTagMode, abc.ABC):
    @classmethod
    def permissions(cls):
        return ["hosttags"]

    def __init__(self) -> None:
        super().__init__()
        self._id = self._get_id()
        self._new = self._is_new_tag()

    @abc.abstractmethod
    def _get_id(self):
        raise NotImplementedError()

    def _is_new_tag(self):
        return request.var("edit") is None

    def _basic_elements(self, id_title):
        if self._new:
            vs_id = ID(
                title=id_title,
                size=60,
                allow_empty=False,
                help=_("This ID is used as it's unique identifier. It cannot be changed later."),
            )
        else:
            vs_id = FixedValue(
                value=self._id,
                title=id_title,
            )

        return [
            ("id", vs_id),
            (
                "title",
                TextInput(
                    title=_("Title"),
                    size=60,
                    allow_empty=False,
                ),
            ),
            ("topic", self._get_topic_valuespec()),
            (
                "help",
                TextInput(
                    title=_("Help"),
                    size=60,
                ),
            ),
        ]

    def _get_topic_valuespec(self):
        return OptionalDropdownChoice(
            title=_("Topic") + "<sup>*</sup>",
            choices=list(self._effective_config.get_topic_choices()),
            explicit=TextInput(),
            otherlabel=_("Create new topic"),
            default_value=None,
            help=_(
                "Different tags can be grouped in topics to make the visualization and "
                "selections in the GUI more comfortable."
            ),
        )


@mode_registry.register
class ModeTagUsage(ABCTagMode):
    @classmethod
    def name(cls) -> str:
        return "tag_usage"

    @classmethod
    def permissions(cls) -> List[str]:
        return ["hosttags"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeTags

    def title(self) -> str:
        return _("Tag usage")

    def page(self) -> None:
        self._show_tag_list()
        self._show_aux_tag_list()

    def _show_tag_list(self) -> None:
        with table_element("tag_usage", _("Tags")) as table:
            for tag_group in self._effective_config.tag_groups:
                for tag in tag_group.tags:
                    self._show_tag_row(table, tag_group, tag)

    def _show_tag_row(
        self, table: Table, tag_group: cmk.utils.tags.TagGroup, tag: cmk.utils.tags.GroupedTag
    ) -> None:
        table.row()

        table.cell(_("Actions"), css=["buttons"])
        self._show_tag_group_icons(tag_group)

        table.cell(_("Tag group"), _u(tag_group.choice_title))
        # TODO: This check shouldn't be necessary if we get our types right.
        if tag.title is None or tag_group.id is None:
            raise Exception("uninitialized tag/tag group")
        table.cell(_("Tag"), _u(tag.title))

        operation = OperationReplaceGroupedTags(
            tag_group.id, remove_tag_ids=[tag.id], replace_tag_ids={}
        )
        affected_folders, affected_hosts, affected_rulesets = change_host_tags_in_folders(
            operation, TagCleanupMode.CHECK, Folder.root_folder()
        )

        table.cell(_("Explicitly set on folders"))
        if affected_folders:
            _show_affected_folders(affected_folders)

        table.cell(_("Explicitly set on hosts"))
        if affected_hosts:
            _show_affected_hosts(affected_hosts)

        table.cell(_("Used in rulesets"))
        if affected_rulesets:
            _show_affected_rulesets(affected_rulesets)

    def _show_tag_group_icons(self, tag_group: cmk.utils.tags.TagGroup) -> None:
        # Tag groups were made builtin with ~1.4. Previously users could modify
        # these groups.  These users now have the modified tag groups in their
        # user configuration and should be able to cleanup this using the GUI
        # for the moment. Make the buttons available to the users.
        if self._builtin_config.tag_group_exists(
            tag_group.id
        ) and not self._tag_config.tag_group_exists(tag_group.id):
            html.i("(%s)" % _("builtin"))
            return

        edit_url = folder_preserving_link([("mode", "edit_tag"), ("edit", tag_group.id)])
        html.icon_button(edit_url, _("Edit this tag group"), "edit")

    def _show_aux_tag_list(self) -> None:
        with table_element("aux_tag_usage", _("Auxiliary tags")) as table:
            for aux_tag in self._effective_config.aux_tag_list.get_tags():
                self._show_aux_tag_row(table, aux_tag)

    def _show_aux_tag_row(self, table: Table, aux_tag: cmk.utils.tags.AuxTag) -> None:
        table.row()

        table.cell(_("Actions"), css=["buttons"])
        self._show_aux_tag_icons(aux_tag)

        table.cell(_("Tag"), _u(aux_tag.choice_title))
        table.cell(_("Used by tags"))
        _show_aux_tag_used_by_tags(self._get_tags_using_aux_tag(aux_tag))

        # TODO: This check shouldn't be necessary if we get our types right.
        if aux_tag.id is None:
            raise Exception("uninitialized tag")
        operation = OperationRemoveAuxTag(aux_tag.id)
        affected_folders, affected_hosts, affected_rulesets = change_host_tags_in_folders(
            operation, TagCleanupMode.CHECK, Folder.root_folder()
        )

        table.cell(_("Explicitly set on folders"))
        if affected_folders:
            _show_affected_folders(affected_folders)

        table.cell(_("Explicitly set on hosts"))
        if affected_hosts:
            _show_affected_hosts(affected_hosts)

        table.cell(_("Used in rulesets"))
        if affected_rulesets:
            _show_affected_rulesets(affected_rulesets)

    def _show_aux_tag_icons(self, aux_tag: cmk.utils.tags.AuxTag) -> None:
        if aux_tag.id in self._builtin_config.aux_tag_list.get_tag_ids():
            html.i("(%s)" % _("builtin"))
            return

        edit_url = folder_preserving_link([("mode", "edit_auxtag"), ("edit", aux_tag.id)])
        html.icon_button(edit_url, _("Edit this auxiliary tag"), "edit")


@mode_registry.register
class ModeEditAuxtag(ABCEditTagMode):
    @classmethod
    def name(cls):
        return "edit_auxtag"

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeTags

    def __init__(self) -> None:
        super().__init__()

        if self._new:
            self._aux_tag = cmk.utils.tags.AuxTag(tag_id="", title="", topic=None)
        else:
            self._aux_tag = self._tag_config.aux_tag_list.get_aux_tag(self._id)

    def _get_id(self):
        if not request.has_var("edit"):
            return None

        return request.get_item_input("edit", dict(self._tag_config.aux_tag_list.get_choices()))[1]

    def title(self):
        if self._new:
            return _("Add auxiliary tag")
        return _("Edit auxiliary tag")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Tag"), breadcrumb, form_name="aux_tag", button_name="_save"
        )

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(mode_url("tags"))

        vs = self._valuespec()
        aux_tag_spec = vs.from_html_vars("aux_tag")
        vs.validate_value(aux_tag_spec, "aux_tag")

        self._aux_tag = cmk.utils.tags.AuxTag.from_config(aux_tag_spec)
        self._aux_tag.validate()

        changed_hosttags_config = cmk.utils.tags.TagConfig.from_config(
            self._tag_config_file.load_for_reading()
        )

        if self._new:
            changed_hosttags_config.aux_tag_list.append(self._aux_tag)
        else:
            changed_hosttags_config.aux_tag_list.update(self._id, self._aux_tag)
        try:
            changed_hosttags_config.validate_config()
        except MKGeneralException as e:
            raise MKUserError(None, "%s" % e)

        self._tag_config_file.save(changed_hosttags_config.get_dict_format())

        return redirect(mode_url("tags"))

    def page(self):
        html.begin_form("aux_tag")

        self._valuespec().render_input("aux_tag", self._aux_tag.get_dict_format())

        forms.end()
        html.show_localization_hint()
        html.hidden_fields()
        html.end_form()

    def _valuespec(self):
        return Dictionary(
            title=_("Basic settings"),
            elements=self._basic_elements(_("Tag ID")),
            render="form",
            form_narrow=True,
            optional_keys=[],
        )


@mode_registry.register
class ModeEditTagGroup(ABCEditTagMode):
    @classmethod
    def name(cls):
        return "edit_tag"

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeTags

    def __init__(self) -> None:
        super().__init__()

        tg = self._tag_config.get_tag_group(self._id)
        self._untainted_tag_group = (
            cmk.utils.tags.TagGroup(group_id="", title="", topic=None, help=None, tags=[])
            if tg is None
            else tg
        )

        tg = self._tag_config.get_tag_group(self._id)
        self._tag_group = (
            cmk.utils.tags.TagGroup(group_id="", title="", topic=None, help=None, tags=[])
            if tg is None
            else tg
        )

    def _get_id(self):
        return request.var("edit", request.var("tag_id"))

    def title(self):
        if self._new:
            return _("Add tag group")
        return _("Edit tag group")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return make_simple_form_page_menu(
            _("Tag group"), breadcrumb, form_name="tag_group", button_name="_save"
        )

    def action(self) -> ActionResult:
        if not transactions.check_transaction():
            return redirect(mode_url("tags"))

        vs = self._valuespec()
        tag_group_spec = vs.from_html_vars("tag_group")
        vs.validate_value(tag_group_spec, "tag_group")

        # Create new object with existing host tags
        changed_hosttags_config = cmk.utils.tags.TagConfig.from_config(
            self._tag_config_file.load_for_modification()
        )
        changed_tag_group = cmk.utils.tags.TagGroup.from_config(tag_group_spec)
        self._tag_group = changed_tag_group

        if self._new:
            # Inserts and verifies changed tag group
            changed_hosttags_config.insert_tag_group(changed_tag_group)
            try:
                changed_hosttags_config.validate_config()
            except MKGeneralException as e:
                raise MKUserError(None, "%s" % e)
            self._save_tags_and_update_hosts(changed_hosttags_config.get_dict_format())
            _changes.add_change(
                "edit-hosttags", _("Created new host tag group '%s'") % changed_tag_group.id
            )
            flash(_("Created new host tag group '%s'") % changed_tag_group.title)
            return redirect(mode_url("tags"))

        # Updates and verifies changed tag group
        changed_hosttags_config.update_tag_group(changed_tag_group)
        try:
            changed_hosttags_config.validate_config()
        except MKGeneralException as e:
            raise MKUserError(None, "%s" % e)

        remove_tag_ids, replace_tag_ids = identify_modified_tags(
            changed_tag_group, self._untainted_tag_group
        )
        tg_id = self._tag_group.id
        if tg_id is None:
            raise Exception("tag group ID not set")
        operation = OperationReplaceGroupedTags(tg_id, remove_tag_ids, replace_tag_ids)

        # Now check, if any folders, hosts or rules are affected
        message = _rename_tags_after_confirmation(self.breadcrumb(), operation)
        if message is False:
            return FinalizeRequest(code=200)

        self._save_tags_and_update_hosts(changed_hosttags_config.get_dict_format())
        _changes.add_change(
            "edit-hosttags", _("Edited host tag group %s (%s)") % (message, self._id)
        )
        if isinstance(message, str):
            flash(message)

        return redirect(mode_url("tags"))

    def page(self):
        html.begin_form("tag_group", method="POST")

        self._valuespec().render_input("tag_group", self._tag_group.get_dict_format())

        forms.end()
        html.show_localization_hint()

        html.hidden_fields()
        html.end_form()

    def _valuespec(self):
        basic_elements = self._basic_elements(_("Tag group ID"))
        tag_choice_elements = self._tag_choices_elements()

        return Dictionary(
            elements=basic_elements + tag_choice_elements,
            headers=[
                (_("Basic settings"), [k for k, _vs in basic_elements]),
                (_("Tag choices"), [k for k, _vs in tag_choice_elements]),
            ],
            render="form",
            form_narrow=True,
            optional_keys=[],
        )

    def _tag_choices_elements(self):
        return [
            ("tags", self._tag_choices_valuespec()),
        ]

    def _tag_choices_valuespec(self):
        # We want the compact tuple style visualization which is not
        # supported by the Dictionary valuespec. Transform!
        return Transform(
            valuespec=ListOf(
                valuespec=Tuple(
                    elements=[
                        Transform(
                            valuespec=TextInput(
                                title=_("Tag ID"),
                                size=40,
                                regex="^[-a-z0-9A-Z_]*$",
                                regex_error=_(
                                    "Invalid tag ID. Only the characters a-z, A-Z, "
                                    "0-9, _ and - are allowed."
                                ),
                                allow_empty=True,
                            ),
                            forth=lambda x: "" if x is None else x,
                            back=lambda x: None if not x else x,
                        ),
                        TextInput(
                            title=_("Title") + "*",
                            allow_empty=False,
                            size=60,
                        ),
                        Foldable(
                            valuespec=ListChoice(
                                title=_("Auxiliary tags"),
                                choices=self._effective_config.aux_tag_list.get_choices(),
                            ),
                        ),
                    ],
                    show_titles=True,
                    orientation="horizontal",
                ),
                add_label=_("Add tag choice"),
                sort_by=1,  # sort by description
                help=_(
                    "The first choice of a tag group will be its default value. "
                    "If a tag group has only one choice, it will be displayed "
                    "as a checkbox and set or not set the only tag. If it has "
                    "more choices you may leave at most one tag id empty. A host "
                    "with that choice will not get any tag of this group.<br><br>"
                    "The tag ID must contain only of letters, digits and "
                    "underscores.<br><br><b>Renaming tags ID:</b> if you want "
                    "to rename the ID of a tag, then please make sure that you do not "
                    "change its title at the same time! Otherwise WATO will not "
                    "be able to detect the renaming and cannot exchange the tags "
                    "in all folders, hosts and rules accordingly."
                ),
            ),
            forth=lambda x: [(c["id"], c["title"], c["aux_tags"]) for c in x],
            back=lambda x: [dict(zip(["id", "title", "aux_tags"], c)) for c in x],
        )


def _rename_tags_after_confirmation(
    breadcrumb: Breadcrumb, operation: ABCOperation
) -> Union[bool, str]:
    """Handle renaming and deletion of tags

    Find affected hosts, folders and rules. Remove or fix those rules according
    the users' wishes.

    Returns:
        True: Proceed, no "question" dialog shown
        False: "Question dialog" shown
        str: Action done after "question" dialog
    """
    repair_mode = request.var("_repair")
    if repair_mode is not None:
        try:
            mode = TagCleanupMode(repair_mode)
        except ValueError:
            raise MKUserError("_repair", "Invalid mode")

        if mode == TagCleanupMode.ABORT:
            raise MKUserError("id_0", _("Aborting change."))

        # make attribute unknown to system, important for save() operations
        if isinstance(operation, OperationRemoveTagGroup):
            undeclare_host_tag_attribute(operation.tag_group_id)

        affected_folders, affected_hosts, affected_rulesets = change_host_tags_in_folders(
            operation, mode, Folder.root_folder()
        )

        return _("Modified folders: %d, modified hosts: %d, modified rulesets: %d") % (
            len(affected_folders),
            len(affected_hosts),
            len(affected_rulesets),
        )

    message = HTML()
    affected_folders, affected_hosts, affected_rulesets = change_host_tags_in_folders(
        operation, TagCleanupMode.CHECK, Folder.root_folder()
    )

    if affected_folders:
        with output_funnel.plugged():
            html.write_text(
                _(
                    "Affected folders with an explicit reference to this tag "
                    "group and that are affected by the change"
                )
                + ":"
            )
            _show_affected_folders(affected_folders)
            message += HTML(output_funnel.drain())

    if affected_hosts:
        with output_funnel.plugged():
            html.write_text(
                _(
                    "Hosts where this tag group is explicitely set "
                    "and that are effected by the change"
                )
                + ":"
            )
            _show_affected_hosts(affected_hosts)
            message += HTML(output_funnel.drain())

    if affected_rulesets:
        with output_funnel.plugged():
            html.write_text(
                _("Rulesets that contain rules with references to the changed tags") + ":"
            )
            _show_affected_rulesets(affected_rulesets)
            message += HTML(output_funnel.drain())

    if message:
        wato_html_head(title=operation.confirm_title(), breadcrumb=breadcrumb)
        html.open_div(class_="really")
        html.h3(_("Your modifications affect some objects"))
        html.write_text(message)
        html.br()
        html.write_text(
            _(
                "Setup can repair things for you. It can rename tags in folders, host and rules. "
                "Removed tag groups will be removed from hosts and folders, removed tags will be "
                "replaced with the default value for the tag group (for hosts and folders). What "
                "rules concern, you have to decide how to proceed."
            )
        )
        html.begin_form("confirm", method="POST")

        if affected_rulesets and _is_removing_tags(operation):
            html.br()
            html.b(
                _(
                    "Some tags that are used in rules have been removed by you. What "
                    "shall we do with that rules?"
                )
            )
            html.open_ul()
            html.radiobutton(
                "_repair", "remove", True, _("Just remove the affected tags from the rules.")
            )
            html.br()
            html.radiobutton(
                "_repair",
                "delete",
                False,
                _(
                    "Delete rules containing tags that have been removed, if tag is used in a positive sense. Just remove that tag if it's used negated."
                ),
            )
        else:
            html.open_ul()
            html.radiobutton("_repair", "repair", True, _("Fix affected folders, hosts and rules."))

        html.br()
        html.radiobutton("_repair", "abort", False, _("Abort your modifications."))
        html.close_ul()

        html.button("_do_confirm", _("Proceed"), "")
        html.hidden_fields(add_action_vars=True)
        html.end_form()
        html.close_div()
        return False

    return True


def _show_aux_tag_used_by_tags(tags: Set[cmk.utils.tags.GroupedTag]) -> None:
    if not tags:
        return

    html.open_ul()
    html.open_li()
    builtin_config = cmk.utils.tags.BuiltinTagConfig()
    for index, tag in enumerate(sorted(tags, key=lambda t: t.choice_title)):
        if index > 0:
            html.write_text(", ")

        # Builtin tag groups can not be edited
        if builtin_config.tag_group_exists(tag.group.id):
            html.write_text(_u(tag.choice_title))
        else:
            edit_url = folder_preserving_link([("mode", "edit_tag"), ("edit", tag.group.id)])
            html.a(_u(tag.choice_title), href=edit_url)
    html.close_li()
    html.close_ul()


def _show_affected_folders(affected_folders: List[CREFolder]) -> None:
    html.open_ul()
    for folder in affected_folders:
        html.open_li()
        html.a(folder.alias_path(), href=folder.edit_url())
        html.close_li()
    html.close_ul()


def _show_affected_hosts(affected_hosts: List[CREHost]) -> None:
    html.open_ul()
    html.open_li()
    for nr, host in enumerate(affected_hosts):
        if nr > 20:
            html.write_text(_("... (%d more)") % (len(affected_hosts) - 20))
            break

        if nr > 0:
            html.write_text(", ")

        html.a(host.name(), href=host.edit_url())
    html.close_li()
    html.close_ul()


def _show_affected_rulesets(affected_rulesets: List[Ruleset]) -> None:
    html.open_ul()
    for ruleset in affected_rulesets:
        html.open_li()
        html.a(
            ruleset.title(),
            href=folder_preserving_link([("mode", "edit_ruleset"), ("varname", ruleset.name)]),
        )
        html.close_li()
    html.close_ul()


def _is_removing_tags(operation: ABCOperation) -> bool:
    if isinstance(operation, (OperationRemoveAuxTag, OperationRemoveTagGroup)):
        return True

    if isinstance(operation, OperationReplaceGroupedTags) and operation.remove_tag_ids:
        return True

    return False
