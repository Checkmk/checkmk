#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Editor for global settings in main.mk and modes for these global
settings"""

import abc
from typing import Final, Iterable, Iterator, Optional, Tuple, Type

import cmk.utils.version as cmk_version

import cmk.gui.forms as forms
import cmk.gui.utils.escaping as escaping
import cmk.gui.watolib as watolib
import cmk.gui.watolib.changes as _changes
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKGeneralException, MKUserError
from cmk.gui.htmllib.context import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_confirmed_form_submit_link,
    make_display_options_dropdown,
    make_simple_form_page_menu,
    make_simple_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuSearch,
    PageMenuTopic,
)
from cmk.gui.plugins.wato.utils import get_search_expression, mode_registry
from cmk.gui.plugins.wato.utils.base_modes import mode_url, redirect, WatoMode
from cmk.gui.plugins.watolib.utils import (
    ABCConfigDomain,
    config_variable_group_registry,
    config_variable_registry,
    ConfigVariable,
    ConfigVariableGroup,
)
from cmk.gui.type_defs import ActionResult
from cmk.gui.utils.escaping import escape_to_html
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri, makeuri_contextless
from cmk.gui.valuespec import Checkbox, Transform
from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    match_item_generator_registry,
    MatchItem,
    MatchItems,
)


class ABCGlobalSettingsMode(WatoMode):
    def __init__(self):
        self._search = None
        self._show_only_modified = False

        super().__init__()

        self._default_values = ABCConfigDomain.get_all_default_globals()
        self._global_settings = {}
        self._current_settings = {}

    def _from_vars(self):
        self._search = get_search_expression()
        self._show_only_modified = (
            request.get_integer_input_mandatory("_show_only_modified", 0) == 1
        )

    @staticmethod
    def _get_groups(show_all: bool) -> Iterable[ConfigVariableGroup]:
        groups = []

        for group_class in config_variable_group_registry.values():
            group = group_class()
            add = False
            for config_variable_class in group.config_variables():
                config_variable = config_variable_class()
                if not show_all and (
                    not config_variable.in_global_settings()
                    or not config_variable.domain().in_global_settings
                ):
                    continue  # do not edit via global settings

                add = True
                break

            if add:
                groups.append(group)

        return groups

    def _groups(self) -> Iterable[ConfigVariableGroup]:
        return self._get_groups(show_all=False)

    @property
    def edit_mode_name(self) -> str:
        return "edit_configvar"

    def _should_show_config_variable(self, config_variable: ConfigVariable) -> bool:
        varname = config_variable.ident()

        if not config_variable.domain().enabled():
            return False

        if (
            config_variable.domain() == watolib.ConfigDomainCore
            and varname not in self._default_values
        ):
            if active_config.debug:
                raise MKGeneralException(
                    "The configuration variable <tt>%s</tt> is unknown to "
                    "your local Check_MK installation" % varname
                )
            return False

        if not config_variable.in_global_settings():
            return False

        return True

    def iter_all_configuration_variables(
        self,
    ) -> Iterable[Tuple[ConfigVariableGroup, Iterable[ConfigVariable]]]:
        yield from (
            (
                group,
                (
                    config_variable
                    for config_variable_class in group.config_variables()
                    for config_variable in [config_variable_class()]
                    if self._should_show_config_variable(config_variable)
                ),
            )
            for group in sorted(self._groups(), key=lambda g: g.sort_index())
        )

    def _show_configuration_variables(self) -> None:
        search = self._search

        at_least_one_painted = False
        html.open_div(class_="globalvars")
        for group, config_variables in self.iter_all_configuration_variables():
            header_is_painted = False  # needed for omitting empty groups

            for config_variable in config_variables:
                varname = config_variable.ident()
                valuespec = config_variable.valuespec()

                if self._show_only_modified and varname not in self._current_settings:
                    continue

                help_text = valuespec.help() or ""
                title_text = valuespec.title() or ""

                if (
                    search
                    and search not in group.title().lower()
                    and search not in config_variable.domain().ident().lower()
                    and search not in varname
                    and search not in help_text.lower()
                    and search not in title_text.lower()
                ):
                    continue  # skip variable when search is performed and nothing matches
                at_least_one_painted = True

                if not header_is_painted:
                    # always open headers when searching
                    forms.header(group.title(), isopen=search or self._show_only_modified)
                    header_is_painted = True

                default_value = self._default_values[varname]

                edit_url = folder_preserving_link(
                    [
                        ("mode", self.edit_mode_name),
                        ("varname", varname),
                        ("site", request.var("site", "")),
                    ]
                )
                title = html.render_a(
                    title_text,
                    href=edit_url,
                    class_="modified" if varname in self._current_settings else None,
                    title=escaping.strip_tags(help_text),
                )

                if varname in self._current_settings:
                    value = self._current_settings[varname]
                elif varname in self._global_settings:
                    value = self._global_settings[varname]
                else:
                    value = default_value

                try:
                    to_text = valuespec.value_to_html(value)
                except Exception:
                    logger.exception("error converting %r to text", value)
                    to_text = html.render_error(_("Failed to render value: %r") % value)

                # Is this a simple (single) value or not? change styling in these cases...
                simple = True
                if "\n" in to_text or "<td>" in to_text:
                    simple = False
                forms.section(title, simple=simple)

                if varname in self._current_settings:
                    modified_cls: Optional[str] = "modified"
                    value_title: Optional[str] = _("This option has been modified.")
                elif varname in self._global_settings:
                    modified_cls = "modified globally"
                    value_title = _("This option has been modified in global settings.")
                else:
                    modified_cls = None
                    value_title = None

                if is_a_checkbox(valuespec):
                    html.open_div(
                        class_=["toggle_switch_container", modified_cls, "on" if value else None]
                    )
                    html.toggle_switch(
                        enabled=value,
                        help_txt=_("Immediately toggle this setting"),
                        href=makeactionuri(
                            request, transactions, [("_action", "toggle"), ("_varname", varname)]
                        ),
                        class_=modified_cls,
                        title=value_title,
                    )
                    html.close_div()

                else:
                    html.a(to_text, href=edit_url, class_=modified_cls, title=value_title)

            if header_is_painted:
                forms.end()
        if not at_least_one_painted and search:
            html.show_message(_("Did not find any global setting matching your search."))
        html.close_div()


class ABCEditGlobalSettingMode(WatoMode):
    def _from_vars(self):
        self._varname = request.get_ascii_input_mandatory("varname")
        try:
            self._config_variable = config_variable_registry[self._varname]()
            self._valuespec = self._config_variable.valuespec()
        except KeyError:
            raise MKUserError(
                "varname", _('The global setting "%s" does not exist.') % self._varname
            )

        if not self._may_edit_configvar(self._varname):
            raise MKAuthException(_("You are not permitted to edit this global setting."))

        self._current_settings = load_configuration_settings()
        self._global_settings = {}

    def _may_edit_configvar(self, varname):
        if varname in ["actions"]:
            return user.may("wato.add_or_modify_executables")
        return True

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(
            _("Setting"), breadcrumb, form_name="value_editor", button_name="_save"
        )

        reset_possible = self._config_variable.allow_reset() and self._is_configured()
        default_values = ABCConfigDomain.get_all_default_globals()
        defvalue = default_values[self._varname]
        value = self._current_settings.get(
            self._varname, self._global_settings.get(self._varname, defvalue)
        )
        menu.dropdowns[0].topics[0].entries.append(
            PageMenuEntry(
                title=_("Remove explicit setting") if value == defvalue else _("Reset to default"),
                icon_name="reset",
                item=make_confirmed_form_submit_link(
                    form_name="value_editor",
                    button_name="_reset",
                    message=_(
                        "Do you really want to reset this configuration variable "
                        "back to its default value?"
                    ),
                ),
                is_enabled=reset_possible,
                is_shortcut=True,
                is_suggested=True,
            )
        )

        return menu

    def action(self) -> ActionResult:
        if request.var("_reset"):
            if not transactions.check_transaction():
                return None

            try:
                del self._current_settings[self._varname]
            except KeyError:
                pass

            msg = escape_to_html(
                _("Resetted configuration variable %s to its default.") % self._varname
            )
        else:
            new_value = self._valuespec.from_html_vars("ve")
            self._valuespec.validate_value(new_value, "ve")
            self._current_settings[self._varname] = new_value
            msg = HTML(
                _("Changed global configuration variable %s to %s.")
                % (
                    escaping.escape_attribute(self._varname),
                    self._valuespec.value_to_html(new_value),
                )
            )

        self._save()
        _changes.add_change(
            "edit-configvar",
            msg,
            sites=self._affected_sites(),
            domains=[self._config_variable.domain()],
            need_restart=self._config_variable.need_restart(),
        )

        return redirect(self._back_url())

    @abc.abstractmethod
    def _back_url(self) -> str:
        raise NotImplementedError()

    def _save(self):
        save_global_settings(self._current_settings)

    @abc.abstractmethod
    def _affected_sites(self):
        raise NotImplementedError()

    def _is_configured(self) -> bool:
        return self._varname in self._current_settings

    def page(self) -> None:
        is_configured = self._is_configured()
        is_configured_globally = self._varname in self._global_settings

        default_values = ABCConfigDomain.get_all_default_globals()

        defvalue = default_values[self._varname]
        value = self._current_settings.get(
            self._varname, self._global_settings.get(self._varname, defvalue)
        )

        hint = self._config_variable.hint()
        if hint:
            html.show_warning(hint)

        html.begin_form("value_editor", method="POST")
        title = self._valuespec.title()
        assert isinstance(title, str)
        forms.header(title)
        if not active_config.wato_hide_varnames:
            forms.section(_("Configuration variable:"))
            html.tt(self._varname)

        forms.section(_("Current setting"))
        self._valuespec.render_input("ve", value)
        self._valuespec.set_focus("ve")
        html.help(self._valuespec.help())

        if is_configured_globally:
            self._show_global_setting()

        forms.section(_("Factory setting"))
        html.write_text(self._valuespec.value_to_html(defvalue))

        forms.section(_("Current state"))
        if is_configured_globally:
            html.write_text(
                _('This variable is configured in <a href="%s">global settings</a>.')
                % ("wato.py?mode=edit_configvar&varname=%s" % self._varname)
            )
        elif not is_configured:
            html.write_text(_("This variable is at factory settings."))
        else:
            curvalue = self._current_settings[self._varname]
            if is_configured_globally and curvalue == self._global_settings[self._varname]:
                html.write_text(_("Site setting and global setting are identical."))
            elif curvalue == defvalue:
                html.write_text(_("Your setting and factory settings are identical."))
            else:
                html.write_text(self._valuespec.value_to_html(curvalue))

        forms.end()
        html.hidden_fields()
        html.end_form()

    def _show_global_setting(self):
        pass


@mode_registry.register
class ModeEditGlobals(ABCGlobalSettingsMode):
    @classmethod
    def name(cls):
        return "globalvars"

    @classmethod
    def permissions(cls):
        return ["global"]

    def __init__(self):
        super().__init__()
        self._current_settings = load_configuration_settings()

    def title(self):
        if self._search:
            return _("Global settings matching '%s'") % escape_to_html(self._search)
        return _("Global settings")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        dropdowns = []

        if cmk_version.is_managed_edition():
            import cmk.gui.cme.plugins.wato.managed  # pylint: disable=no-name-in-module,import-outside-toplevel

            dropdowns.append(cmk.gui.cme.plugins.wato.managed.cme_global_settings_dropdown())

        dropdowns.append(
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
        )

        menu = PageMenu(
            dropdowns=dropdowns,
            breadcrumb=breadcrumb,
            inpage_search=PageMenuSearch(),
        )

        self._extend_display_dropdown(menu)
        return menu

    def _page_menu_entries_related(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Sites"),
            icon_name="sites",
            item=make_simple_link("wato.py?mode=sites"),
        )

    def _extend_display_dropdown(self, menu: PageMenu) -> None:
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())
        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Details"),
                entries=list(self._page_menu_entries_details()),
            ),
        )

    def _page_menu_entries_details(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Show all settings"),
            icon_name="checked_checkbox" if self._show_only_modified else "checkbox",
            item=make_simple_link(
                makeactionuri(
                    request,
                    transactions,
                    [
                        ("_show_only_modified", "0" if self._show_only_modified else "1"),
                    ],
                )
            ),
        )

    def action(self) -> ActionResult:
        varname = request.var("_varname")
        if not varname:
            return None

        action = request.var("_action")

        config_variable = config_variable_registry[varname]()
        def_value = self._default_values[varname]

        if not transactions.check_transaction():
            return None

        if varname in self._current_settings:
            self._current_settings[varname] = not self._current_settings[varname]
        else:
            self._current_settings[varname] = not def_value
        msg = _("Changed Configuration variable %s to %s.") % (
            varname,
            "on" if self._current_settings[varname] else "off",
        )
        save_global_settings(self._current_settings)

        _changes.add_change(
            "edit-configvar",
            msg,
            domains=[config_variable.domain()],
            need_restart=config_variable.need_restart(),
        )

        if action == "_reset":
            flash(msg)
        return redirect(mode_url("globalvars"))

    def page(self):
        self._show_configuration_variables()


@mode_registry.register
class ModeEditGlobalSetting(ABCEditGlobalSettingMode):
    @classmethod
    def name(cls):
        return "edit_configvar"

    @classmethod
    def permissions(cls):
        return ["global"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeEditGlobals

    def title(self):
        return _("Edit global setting")

    def _affected_sites(self):
        return None  # All sites

    def _back_url(self) -> str:
        return ModeEditGlobals.mode_url()


def is_a_checkbox(vs):
    """Checks if a valuespec is a Checkbox"""
    if isinstance(vs, Checkbox):
        return True
    if isinstance(vs, Transform):
        return is_a_checkbox(vs._valuespec)
    return False


class MatchItemGeneratorSettings(ABCMatchItemGenerator):
    def __init__(
        self,
        name: str,
        topic: str,
        # we cannot pass an instance here because we would get
        # RuntimeError("Working outside of request context.")
        # when registering below due to
        # ABCGlobalSettingsMode.__init__ --> _from_vars --> get_search_expression)
        mode_class: Type[ABCGlobalSettingsMode],
    ) -> None:
        super().__init__(name)
        self._topic: Final[str] = topic
        self._mode_class: Final[Type[ABCGlobalSettingsMode]] = mode_class

    def _config_variable_to_match_item(
        self,
        config_variable: ConfigVariable,
        edit_mode_name: str,
    ) -> MatchItem:
        title = config_variable.valuespec().title() or _("Untitled setting")
        ident = config_variable.ident()
        return MatchItem(
            title=title,
            topic=self._topic,
            url=makeuri_contextless(
                request,
                [("mode", edit_mode_name), ("varname", ident)],
                filename="wato.py",
            ),
            match_texts=[title, ident],
        )

    def generate_match_items(self) -> MatchItems:
        mode = self._mode_class()
        yield from (
            self._config_variable_to_match_item(config_variable, mode.edit_mode_name)
            for _group, config_variables in mode.iter_all_configuration_variables()
            for config_variable in config_variables
        )

    @staticmethod
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    def is_localization_dependent(self) -> bool:
        return True


match_item_generator_registry.register(
    MatchItemGeneratorSettings(
        "global_settings",
        _("Global settings"),
        ModeEditGlobals,
    )
)
