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
"""Editor for global settings in main.mk and modes for these global
settings"""

import abc

import cmk
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.valuespec import Checkbox, Transform

from cmk.gui.plugins.watolib.utils import (
    config_variable_group_registry,
    config_variable_registry,
    ConfigDomain,
)
from cmk.gui.plugins.wato.utils import mode_registry, get_search_expression
from cmk.gui.plugins.wato.utils.base_modes import WatoMode
from cmk.gui.plugins.wato.utils.html_elements import search_form, wato_confirm
from cmk.gui.plugins.wato.utils.context_buttons import global_buttons

from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKGeneralException, MKAuthException, MKUserError
from cmk.gui.log import logger
from cmk.gui.htmllib import HTML


class GlobalSettingsMode(WatoMode):
    def __init__(self):
        self._search = None
        self._show_only_modified = False

        super(GlobalSettingsMode, self).__init__()

        self._default_values = ConfigDomain.get_all_default_globals()
        self._global_settings = {}
        self._current_settings = {}

    def _from_vars(self):
        self._search = get_search_expression()
        self._show_only_modified = html.request.has_var("show_only_modified")

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
        search_form(_("Search for settings:"))
        search = self._search

        html.open_div(class_="filter_buttons")
        if self._show_only_modified:
            html.buttonlink(html.makeuri([], delvars=["show_only_modified"]),
                            _("Show all settings"))
        else:
            html.buttonlink(html.makeuri([("show_only_modified", "1")]),
                            _("Show only modified settings"))
        html.close_div()

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
                    else:
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
                    title=html.strip_tags(help_text))

                if varname in self._current_settings:
                    value = self._current_settings[varname]
                elif varname in self._global_settings:
                    value = self._global_settings[varname]
                else:
                    value = default_value

                try:
                    to_text = valuespec.value_to_text(value)
                except Exception:
                    logger.exception("error converting %r to text" % (value,))
                    to_text = html.render_error(_("Failed to render value: %r") % value)

                # Is this a simple (single) value or not? change styling in these cases...
                simple = True
                if '\n' in to_text or '<td>' in to_text:
                    simple = False
                forms.section(title, simple=simple)

                if varname in self._current_settings:
                    modified_cls = "modified"
                    title = _("This option has been modified.")
                elif varname in self._global_settings:
                    modified_cls = "modified globally"
                    title = _("This option has been modified in global settings.")
                else:
                    modified_cls = None
                    title = None

                if is_a_checkbox(valuespec):
                    html.open_div(class_=["toggle_switch_container", modified_cls])
                    html.toggle_switch(
                        enabled=value,
                        help_txt=_("Immediately toggle this setting"),
                        href=html.makeactionuri([("_action", "toggle"), ("_varname", varname)]),
                        class_=modified_cls,
                        title=title,
                    )
                    html.close_div()

                else:
                    html.a(HTML(to_text), href=edit_url, class_=modified_cls, title=title)

            if header_is_painted:
                forms.end()
        if not at_least_one_painted and search:
            html.message(_('Did not find any global setting matching your search.'))
        html.close_div()


class EditGlobalSettingMode(WatoMode):
    @abc.abstractmethod
    def _back_mode(self):
        raise NotImplementedError()

    def _from_vars(self):
        self._varname = html.get_ascii_input("varname")
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

    def action(self):
        if html.request.var("_reset"):
            if not is_a_checkbox(self._valuespec):
                c = wato_confirm(
                    _("Resetting configuration variable"),
                    _("Do you really want to reset this configuration variable "
                      "back to its default value?"))
                if c is False:
                    return ""
                elif c is None:
                    return None
            elif not html.check_transaction():
                return

            try:
                del self._current_settings[self._varname]
            except KeyError:
                pass

            msg = _("Resetted configuration variable %s to its default.") % self._varname
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

        return self._back_mode()

    def _save(self):
        watolib.save_global_settings(self._current_settings)

    @abc.abstractmethod
    def _affected_sites(self):
        raise NotImplementedError()

    def page(self):
        is_configured = self._varname in self._current_settings
        is_configured_globally = self._varname in self._global_settings

        default_values = watolib.ConfigDomain.get_all_default_globals()

        defvalue = default_values[self._varname]
        value = self._current_settings.get(self._varname,
                                           self._global_settings.get(self._varname, defvalue))

        html.begin_form("value_editor", method="POST")
        forms.header(self._valuespec.title())
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
        html.write_html(self._valuespec.value_to_text(defvalue))

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
        html.button("save", _("Save"))
        if self._config_variable.allow_reset() and is_configured:
            curvalue = self._current_settings[self._varname]
            html.button(
                "_reset",
                _("Remove explicit setting") if curvalue == defvalue else _("Reset to default"))
        html.hidden_fields()
        html.end_form()

    def _show_global_setting(self):
        pass


@mode_registry.register
class ModeEditGlobals(GlobalSettingsMode):
    @classmethod
    def name(cls):
        return "globalvars"

    @classmethod
    def permissions(cls):
        return ["global"]

    def __init__(self):
        super(ModeEditGlobals, self).__init__()

        self._current_settings = watolib.load_configuration_settings()

    def title(self):
        if self._search:
            return _("Global Settings matching '%s'") % html.render_text(self._search)
        return _("Global Settings")

    def buttons(self):
        global_buttons()

        if config.user.may("wato.set_read_only"):
            html.context_button(_("Read only mode"),
                                watolib.folder_preserving_link([("mode", "read_only")]),
                                "read_only")

        if cmk.is_managed_edition():
            cmk.gui.cme.plugins.wato.managed.cme_global_settings_buttons()

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
        elif c is False:
            return ""

    def page(self):
        self._show_configuration_variables(self._groups())


@mode_registry.register
class ModeEditGlobalSetting(EditGlobalSettingMode):
    @classmethod
    def name(cls):
        return "edit_configvar"

    @classmethod
    def permissions(cls):
        return ["global"]

    def title(self):
        return _("Global configuration settings for Check_MK")

    def buttons(self):
        html.context_button(_("Abort"), watolib.folder_preserving_link([("mode", "globalvars")]),
                            "abort")

    def _back_mode(self):
        return "globalvars"

    def _affected_sites(self):
        return None  # All sites


@mode_registry.register
class ModeEditSiteGlobalSetting(EditGlobalSettingMode):
    @classmethod
    def name(cls):
        return "edit_site_configvar"

    @classmethod
    def permissions(cls):
        return ["global"]

    def _back_mode(self):
        return "edit_site_globals"

    def _from_vars(self):
        super(ModeEditSiteGlobalSetting, self)._from_vars()

        self._site_id = html.request.var("site")
        if self._site_id:
            self._configured_sites = watolib.SiteManagementFactory().factory().load_sites()
            try:
                site = self._configured_sites[self._site_id]
            except KeyError:
                raise MKUserError("site", _("Invalid site"))

        self._current_settings = site.setdefault("globals", {})
        self._global_settings = watolib.load_configuration_settings()

    def title(self):
        return _("Site-specific global configuration for %s") % self._site_id

    def buttons(self):
        html.context_button(
            _("Abort"),
            watolib.folder_preserving_link([("mode", "edit_site_globals"),
                                            ("site", self._site_id)]), "abort")

    def _affected_sites(self):
        return [self._site_id]

    def _save(self):
        watolib.SiteManagementFactory().factory().save_sites(self._configured_sites, activate=False)
        if self._site_id == config.omd_site():
            watolib.save_site_global_settings(self._current_settings)

    def _show_global_setting(self):
        forms.section(_("Global setting"))
        html.write_html(self._valuespec.value_to_text(self._global_settings[self._varname]))


def is_a_checkbox(vs):
    """Checks if a valuespec is a Checkbox"""
    if isinstance(vs, Checkbox):
        return True
    elif isinstance(vs, Transform):
        return is_a_checkbox(vs._valuespec)
    return False
