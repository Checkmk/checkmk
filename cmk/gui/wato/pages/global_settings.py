#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Editor for global settings in main.mk and modes for these global
settings"""

import abc
from typing import Optional, Union, Iterator, Type

import cmk.utils.version as cmk_version
import cmk.gui.config as config
import cmk.gui.escaping as escaping
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.valuespec import Checkbox, Transform

from cmk.gui.plugins.watolib.utils import (
    config_variable_group_registry,
    config_variable_registry,
    ABCConfigDomain,
)
from cmk.gui.plugins.wato.utils import mode_registry, get_search_expression
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.plugins.wato.utils.html_elements import wato_confirm

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKGeneralException, MKAuthException, MKUserError
from cmk.gui.log import logger
from cmk.gui.htmllib import HTML
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    PageMenuCheckbox,
    PageMenuSearch,
    make_simple_link,
    make_form_submit_link,
    make_simple_form_page_menu,
    make_display_options_dropdown,
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
        self._show_only_modified = html.request.get_integer_input_mandatory(
            "_show_only_modified", 0) == 1

    def _groups(self, show_all=False):
        groups = []

        for group_class in config_variable_group_registry.values():
            group = group_class()
            add = False
            for config_variable_class in group.config_variables():
                config_variable = config_variable_class()
                if not show_all and (not config_variable.in_global_settings() or
                                     not config_variable.domain().in_global_settings):
                    continue  # do not edit via global settings

                add = True
                break

            if add:
                groups.append(group)

        return groups

    def _edit_mode(self):
        return "edit_configvar"

    def _show_configuration_variables(self, groups):
        search = self._search

        at_least_one_painted = False
        html.open_div(class_="globalvars")
        for group in sorted(groups, key=lambda g: g.sort_index()):
            header_is_painted = False  # needed for omitting empty groups

            for config_variable_class in group.config_variables():
                config_variable = config_variable_class()
                varname = config_variable.ident()
                valuespec = config_variable.valuespec()

                if not config_variable.domain().enabled():
                    continue

                if config_variable.domain(
                ) == watolib.ConfigDomainCore and varname not in self._default_values:
                    if config.debug:
                        raise MKGeneralException(
                            "The configuration variable <tt>%s</tt> is unknown to "
                            "your local Check_MK installation" % varname)
                    continue

                if not config_variable.in_global_settings():
                    continue

                if self._show_only_modified and varname not in self._current_settings:
                    continue

                help_text = valuespec.help() or ''
                title_text = valuespec.title()

                if search and search not in group.title().lower() \
                        and search not in config_variable.domain().ident.lower() \
                          and search not in varname \
                          and search not in help_text.lower() \
                          and search not in title_text.lower():
                    continue  # skip variable when search is performed and nothing matches
                at_least_one_painted = True

                if not header_is_painted:
                    # always open headers when searching
                    forms.header(group.title(), isopen=search or self._show_only_modified)
                    header_is_painted = True

                default_value = self._default_values[varname]

                edit_url = watolib.folder_preserving_link([("mode", self._edit_mode()),
                                                           ("varname", varname),
                                                           ("site", html.request.var("site", ""))])
                title = html.render_a(
                    title_text,
                    href=edit_url,
                    class_="modified" if varname in self._current_settings else None,
                    title=escaping.strip_tags(help_text))

                if varname in self._current_settings:
                    value = self._current_settings[varname]
                elif varname in self._global_settings:
                    value = self._global_settings[varname]
                else:
                    value = default_value

                try:
                    to_text = valuespec.value_to_text(value)
                except Exception:
                    logger.exception("error converting %r to text", value)
                    to_text = html.render_error(_("Failed to render value: %r") % value)

                # Is this a simple (single) value or not? change styling in these cases...
                simple = True
                if '\n' in to_text or '<td>' in to_text:
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
                    html.open_div(class_=["toggle_switch_container", modified_cls])
                    html.toggle_switch(
                        enabled=value,
                        help_txt=_("Immediately toggle this setting"),
                        href=html.makeactionuri([("_action", "toggle"), ("_varname", varname)]),
                        class_=modified_cls,
                        title=value_title,
                    )
                    html.close_div()

                else:
                    html.a(HTML(to_text), href=edit_url, class_=modified_cls, title=value_title)

            if header_is_painted:
                forms.end()
        if not at_least_one_painted and search:
            html.show_message(_('Did not find any global setting matching your search.'))
        html.close_div()


class ABCEditGlobalSettingMode(WatoMode):
    def _from_vars(self):
        self._varname = html.request.get_ascii_input_mandatory("varname")
        try:
            self._config_variable = config_variable_registry[self._varname]()
            self._valuespec = self._config_variable.valuespec()
        except KeyError:
            raise MKUserError("varname",
                              _("The global setting \"%s\" does not exist.") % self._varname)

        if not self._may_edit_configvar(self._varname):
            raise MKAuthException(_("You are not permitted to edit this global setting."))

        self._current_settings = watolib.load_configuration_settings()
        self._global_settings = {}

    def _may_edit_configvar(self, varname):
        if varname in ["actions"]:
            return config.user.may("wato.add_or_modify_executables")
        return True

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(breadcrumb, form_name="value_editor", button_name="save")

        reset_possible = self._config_variable.allow_reset() and self._is_configured()
        default_values = watolib.ABCConfigDomain.get_all_default_globals()
        defvalue = default_values[self._varname]
        value = self._current_settings.get(self._varname,
                                           self._global_settings.get(self._varname, defvalue))
        menu.dropdowns[0].topics[0].entries.append(
            PageMenuEntry(
                title=_("Remove explicit setting") if value == defvalue else _("Reset to default"),
                icon_name="reset",
                item=make_form_submit_link(form_name="value_editor", button_name="_reset"),
                is_enabled=reset_possible,
            ))

        return menu

    def action(self):
        if html.request.var("_reset"):
            if not is_a_checkbox(self._valuespec):
                c = wato_confirm(
                    _("Resetting configuration variable"),
                    _("Do you really want to reset this configuration variable "
                      "back to its default value?"))
                if c is False:
                    return ""
                if c is None:
                    return None
            elif not html.check_transaction():
                return

            try:
                del self._current_settings[self._varname]
            except KeyError:
                pass

            msg: Union[
                HTML, str] = _("Resetted configuration variable %s to its default.") % self._varname
        else:
            new_value = self._valuespec.from_html_vars("ve")
            self._valuespec.validate_value(new_value, "ve")
            self._current_settings[self._varname] = new_value
            msg = _("Changed global configuration variable %s to %s.") \
                  % (self._varname, self._valuespec.value_to_text(new_value))
            # FIXME: THIS HTML(...) is needed because we do not know what we get from value_to_text!!
            msg = HTML(msg)

        self._save()
        watolib.add_change("edit-configvar",
                           msg,
                           sites=self._affected_sites(),
                           domains=[self._config_variable.domain()],
                           need_restart=self._config_variable.need_restart())

        page_menu = self.parent_mode()
        assert page_menu is not None
        return page_menu.name()

    def _save(self):
        watolib.save_global_settings(self._current_settings)

    @abc.abstractmethod
    def _affected_sites(self):
        raise NotImplementedError()

    def _is_configured(self) -> bool:
        return self._varname in self._current_settings

    def page(self):
        is_configured = self._is_configured()
        is_configured_globally = self._varname in self._global_settings

        default_values = watolib.ABCConfigDomain.get_all_default_globals()

        defvalue = default_values[self._varname]
        value = self._current_settings.get(self._varname,
                                           self._global_settings.get(self._varname, defvalue))

        html.begin_form("value_editor", method="POST")
        title = self._valuespec.title()
        assert isinstance(title, str)
        forms.header(title)
        if not config.wato_hide_varnames:
            forms.section(_("Configuration variable:"))
            html.tt(self._varname)

        forms.section(_("Current setting"))
        self._valuespec.render_input("ve", value)
        self._valuespec.set_focus("ve")
        html.help(self._valuespec.help())

        if is_configured_globally:
            self._show_global_setting()

        forms.section(_("Factory setting"))
        html.write_html(HTML(self._valuespec.value_to_text(defvalue)))

        forms.section(_("Current state"))
        if is_configured_globally:
            html.write_text(
                _("This variable is configured in <a href=\"%s\">global settings</a>.") %
                ("wato.py?mode=edit_configvar&varname=%s" % self._varname))
        elif not is_configured:
            html.write_text(_("This variable is at factory settings."))
        else:
            curvalue = self._current_settings[self._varname]
            if is_configured_globally and curvalue == self._global_settings[self._varname]:
                html.write_text(_("Site setting and global setting are identical."))
            elif curvalue == defvalue:
                html.write_text(_("Your setting and factory settings are identical."))
            else:
                html.write(self._valuespec.value_to_text(curvalue))

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
        self._current_settings = watolib.load_configuration_settings()

    def title(self):
        if self._search:
            return _("Global settings matching '%s'") % html.render_text(self._search)
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
            ),)

        menu = PageMenu(
            dropdowns=dropdowns,
            breadcrumb=breadcrumb,
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
            0, PageMenuTopic(
                title=_("Details"),
                entries=list(self._page_menu_entries_details()),
            ))

        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Filter settings"),
                entries=list(self._page_menu_entries_filter()),
            ))

    def _page_menu_entries_details(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title=_("Show only modified settings"),
            icon_name="trans",
            item=PageMenuCheckbox(
                is_checked=self._show_only_modified,
                check_url=html.makeuri([("_show_only_modified", "1")]),
                uncheck_url=html.makeuri([("_show_only_modified", "0")]),
            ),
        )

    def _page_menu_entries_filter(self) -> Iterator[PageMenuEntry]:
        yield PageMenuEntry(
            title="",
            icon_name="trans",
            item=PageMenuSearch(),
        )

    def action(self):
        varname = html.request.var("_varname")
        if not varname:
            return

        action = html.request.var("_action")

        config_variable = config_variable_registry[varname]()
        def_value = self._default_values[varname]

        if action == "reset" and not is_a_checkbox(config_variable.valuespec()):
            c = wato_confirm(
                _("Resetting configuration variable"),
                _("Do you really want to reset the configuration variable <b>%s</b> "
                  "back to the default value of <b><tt>%s</tt></b>?") %
                (varname, config_variable.valuespec().value_to_text(def_value)))
        else:
            if not html.check_transaction():
                return
            c = True  # no confirmation for direct toggle

        if c:
            if varname in self._current_settings:
                self._current_settings[varname] = not self._current_settings[varname]
            else:
                self._current_settings[varname] = not def_value
            msg = _("Changed Configuration variable %s to %s.") % (
                varname, "on" if self._current_settings[varname] else "off")
            watolib.save_global_settings(self._current_settings)

            watolib.add_change("edit-configvar",
                               msg,
                               domains=[config_variable.domain()],
                               need_restart=config_variable.need_restart())

            if action == "_reset":
                return "globalvars", msg
            return "globalvars"
        if c is False:
            return ""

    def page(self):
        self._show_configuration_variables(self._groups())


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


def is_a_checkbox(vs):
    """Checks if a valuespec is a Checkbox"""
    if isinstance(vs, Checkbox):
        return True
    if isinstance(vs, Transform):
        return is_a_checkbox(vs._valuespec)
    return False
