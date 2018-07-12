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

import abc

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.wato.base_modes import WatoMode
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKGeneralException, MKAuthException
from cmk.gui.log import logger
from cmk.gui.htmllib import HTML

from cmk.gui.wato.html_elements import (
    search_form,
    wato_confirm,
)

from cmk.gui.watolib import (
    configvar_order,
    is_a_checkbox,
    get_search_expression,
    may_edit_configvar,
    add_change,
)

class GlobalSettingsMode(WatoMode):
    def __init__(self):
        self._search = None
        self._show_only_modified = False

        super(GlobalSettingsMode, self).__init__()

        self._default_values   = watolib.ConfigDomain.get_all_default_globals()
        self._global_settings  = {}
        self._current_settings = {}


    def _from_vars(self):
        self._search = get_search_expression()
        self._show_only_modified = html.has_var("show_only_modified")


    def _group_names(self, show_all=False):
        group_names = []

        for group_name, group_vars in watolib.configvar_groups().items():
            add = False
            for domain, varname, valuespec in group_vars:
                if not show_all and (not watolib.configvars()[varname][4]
                                     or not domain.in_global_settings):
                    continue # do not edit via global settings

                add = True
                break

            if add:
                group_names.append(group_name)

        return sorted(group_names, key=lambda a: configvar_order().get(a, 999))


    def _edit_mode(self):
        return "edit_configvar"


    def _show_configuration_variables(self, group_names):
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
        for group_name in group_names:
            header_is_painted = False # needed for omitting empty groups

            for domain, varname, valuespec in watolib.configvar_groups()[group_name]:
                if domain == watolib.ConfigDomainCore and varname not in self._default_values:
                    if config.debug:
                        raise MKGeneralException("The configuration variable <tt>%s</tt> is unknown to "
                                              "your local Check_MK installation" % varname)
                    else:
                        continue

                if not watolib.configvar_show_in_global_settings(varname):
                    continue

                if self._show_only_modified and varname not in self._current_settings:
                    continue

                help_text  = valuespec.help() or ''
                title_text = valuespec.title()

                if search and search not in group_name.lower() \
                        and search not in domain.ident.lower() \
                          and search not in varname \
                          and search not in help_text.lower() \
                          and search not in title_text.lower():
                    continue # skip variable when search is performed and nothing matches
                at_least_one_painted = True

                if not header_is_painted:
                    # always open headers when searching
                    forms.header(group_name, isopen=search or self._show_only_modified)
                    header_is_painted = True

                default_value = self._default_values[varname]

                edit_url = watolib.folder_preserving_link([("mode", self._edit_mode()),
                                                   ("varname", varname),
                                                   ("site", html.var("site", ""))])
                title = html.render_a(title_text,
                    href=edit_url,
                    class_="modified" if varname in self._current_settings else None,
                    title=html.strip_tags(help_text)
                )

                if varname in self._current_settings:
                    value = self._current_settings[varname]
                elif varname in self._global_settings:
                    value = self._global_settings[varname]
                else:
                    value = default_value

                try:
                    to_text = valuespec.value_to_text(value)
                except Exception, e:
                    logger.exception()
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
                        help=_("Immediately toggle this setting"),
                        href=html.makeactionuri([("_action", "toggle"), ("_varname", varname)]),
                        class_=modified_cls,
                        title=title,
                    )
                    html.close_div()

                else:
                    html.a(HTML(to_text),
                        href=edit_url,
                        class_=modified_cls,
                        title=title
                    )

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
        self._varname = html.var("varname")
        try:
            self._domain, self._valuespec, self._need_restart, \
            self._allow_reset, in_global_settings = watolib.configvars()[self._varname]
        except KeyError:
            raise MKGeneralException(_("The global setting \"%s\" does not exist.") % self._varname)

        if not may_edit_configvar(self._varname):
            raise MKAuthException(_("You are not permitted to edit this global setting."))

        self._current_settings = watolib.load_configuration_settings()
        self._global_settings  = {}


    def action(self):
        if html.var("_reset"):
            if not is_a_checkbox(self._valuespec):
                c = wato_confirm(
                    _("Resetting configuration variable"),
                    _("Do you really want to reset this configuration variable "
                      "back to its default value?"))
                if c == False:
                    return ""
                elif c == None:
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
        add_change("edit-configvar", msg, sites=self._affected_sites(), domains=[self._domain], need_restart=self._need_restart)

        return self._back_mode()


    def _save(self):
        watolib.save_global_settings(self._current_settings)


    @abc.abstractmethod
    def _affected_sites(self):
        raise NotImplementedError()


    def page(self):
        is_configured = self._varname in self._current_settings
        is_configured_globally = self._varname in self._global_settings

        default_values  = watolib.ConfigDomain.get_all_default_globals()

        defvalue = default_values[self._varname]
        value    = self._current_settings.get(self._varname, self._global_settings.get(self._varname, defvalue))

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
            html.write_text(_("This variable is configured in <a href=\"%s\">global settings</a>.") %
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
        if self._allow_reset and is_configured:
            curvalue = self._current_settings[self._varname]
            html.button("_reset", _("Remove explicit setting") if curvalue == defvalue else _("Reset to default"))
        html.hidden_fields()
        html.end_form()


    def _show_global_setting(self):
        pass
