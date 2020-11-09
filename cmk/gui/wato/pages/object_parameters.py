#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Mode for displaying and modifying the rule based host and service
parameters. This is a host/service overview page over all things that can be
modified via rules."""

from typing import List, Tuple as _Tuple, Optional, Type, Iterator

from six import ensure_str

import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
import cmk.gui.view_utils
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import Tuple
from cmk.gui.watolib.rulesets import Ruleset, Rule
from cmk.gui.watolib.hosts_and_folders import CREFolder
from cmk.gui.watolib.rulespecs import (
    rulespec_group_registry,
    rulespec_registry,
)
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
)
from cmk.gui.wato.pages.hosts import ModeEditHost, page_menu_host_entries
from cmk.gui.plugins.wato.utils.context_buttons import make_service_status_link

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
)


@mode_registry.register
class ModeObjectParameters(WatoMode):
    _PARAMETERS_UNKNOWN: List = []
    _PARAMETERS_OMIT: List = []

    @classmethod
    def name(cls):
        return "object_parameters"

    @classmethod
    def permissions(cls):
        return ["hosts", "rulesets"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeEditHost

    def _from_vars(self):
        self._hostname = html.request.get_ascii_input_mandatory("host")
        self._host = watolib.Folder.current().host(self._hostname)
        if self._host is None:
            raise MKUserError("host", _('The given host does not exist.'))
        self._host.need_permission("read")

        # TODO: Validate?
        self._service = html.request.get_unicode_input("service")

    def title(self):
        title = _("Parameters of") + " " + self._hostname
        if self._service:
            title += " / " + self._service
        return title

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="hosts",
                    title=_("Hosts"),
                    topics=[
                        PageMenuTopic(
                            title=_("For this host"),
                            entries=list(page_menu_host_entries(self.name(), self._host)),
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="services",
                    title=_("Services"),
                    topics=[
                        PageMenuTopic(
                            title=_("For this service"),
                            entries=list(self._page_menu_service_entries()),
                        ),
                    ],
                ),
            ],
            breadcrumb=breadcrumb,
        )

    def _page_menu_service_entries(self) -> Iterator[PageMenuEntry]:
        if self._service:
            yield make_service_status_link(self._host.name(), self._service)

    def page(self):
        all_rulesets = watolib.AllRulesets()
        all_rulesets.load()

        # Object type specific detail information
        if self._service:
            self._show_service_info(all_rulesets)
        else:
            self._show_host_info()

        last_maingroup = None
        for groupname in sorted(rulespec_group_registry.get_host_rulespec_group_names()):
            maingroup = groupname.split("/")[0]
            for rulespec in sorted(rulespec_registry.get_by_group(groupname),
                                   key=lambda x: x.title or ""):
                if (rulespec.item_type == 'service') == (not self._service):
                    continue  # This rule is not for hosts/services

                # Open form for that group here, if we know that we have at least one rule
                if last_maingroup != maingroup:
                    last_maingroup = maingroup
                    rulegroup = watolib.get_rulegroup(maingroup)
                    forms.header(rulegroup.title,
                                 isopen=maingroup == "monconf",
                                 narrow=True,
                                 css="rulesettings")
                    html.help(rulegroup.help)

                self._output_analysed_ruleset(all_rulesets,
                                              rulespec,
                                              svc_desc_or_item=self._service,
                                              svc_desc=self._service)

        forms.end()

    def _show_host_info(self):
        host_info = watolib.check_mk_automation(self._host.site_id(), "analyse-host",
                                                [self._hostname])
        if not host_info:
            return

        forms.header(_("Host information"), isopen=True, narrow=True, css="rulesettings")
        self._show_labels(host_info["labels"], "host", host_info["label_sources"])

    def _show_service_info(self, all_rulesets):
        assert self._service is not None

        serviceinfo = watolib.check_mk_automation(self._host.site_id(), "analyse-service",
                                                  [self._hostname, self._service])
        if not serviceinfo:
            return

        forms.header(_("Check origin and parameters"), isopen=True, narrow=True, css="rulesettings")
        origin = serviceinfo["origin"]
        origin_txt = {
            "active": _("Active check"),
            "static": _("Manual check"),
            "auto": _("Inventorized check"),
            "classic": _("Classical check"),
        }[origin]
        self._render_rule_reason(_("Type of check"), None, "", "", False, origin_txt)

        # First case: discovered checks. They come from var/check_mk/autochecks/HOST.
        if origin == "auto":
            checkgroup = serviceinfo["checkgroup"]
            checktype = serviceinfo["checktype"]
            if not checkgroup:
                self._render_rule_reason(_("Parameters"), None, "", "", True,
                                         _("This check is not configurable via WATO"))

            # Logwatch needs a special handling, since it is not configured
            # via checkgroup_parameters but via "logwatch_rules" in a special
            # WATO module.
            elif checkgroup == "logwatch":
                rulespec = rulespec_registry["logwatch_rules"]
                self._output_analysed_ruleset(all_rulesets,
                                              rulespec,
                                              svc_desc_or_item=serviceinfo["item"],
                                              svc_desc=self._service,
                                              known_settings=serviceinfo["parameters"])

            else:
                # Note: some discovered checks have a check group but
                # *no* ruleset for discovered checks. One example is "ps".
                # That can be configured as a manual check or created by
                # inventory. But in the later case all parameters are set
                # by the inventory. This will be changed in a later version,
                # but we need to address it anyway.
                grouprule = "checkgroup_parameters:" + checkgroup
                if grouprule not in rulespec_registry:
                    try:
                        rulespec = rulespec_registry["static_checks:" + checkgroup]
                    except KeyError:
                        self._render_rule_reason(_("Parameters"), None, "", "", True,
                                                 _("This check is not configurable via WATO"))
                        return

                    url = watolib.folder_preserving_link([('mode', 'edit_ruleset'),
                                                          ('varname',
                                                           "static_checks:" + checkgroup),
                                                          ('host', self._hostname)])
                    assert isinstance(rulespec.valuespec, Tuple)
                    self._render_rule_reason(
                        _("Parameters"), url, _("Determined by discovery"), None, False,
                        rulespec.valuespec._elements[2].value_to_text(serviceinfo["parameters"]))

                else:
                    rulespec = rulespec_registry[grouprule]
                    self._output_analysed_ruleset(all_rulesets,
                                                  rulespec,
                                                  svc_desc_or_item=serviceinfo["item"],
                                                  svc_desc=self._service,
                                                  known_settings=serviceinfo["parameters"])

        elif origin == "static":
            checkgroup = serviceinfo["checkgroup"]
            checktype = serviceinfo["checktype"]
            if not checkgroup:
                html.write_text(_("This check is not configurable via WATO"))
            else:
                rulespec = rulespec_registry["static_checks:" + checkgroup]
                itemspec = rulespec.item_spec
                if itemspec:
                    item_text = itemspec.value_to_text(serviceinfo["item"])
                    assert rulespec.item_spec is not None
                    title = rulespec.item_spec.title()
                else:
                    item_text = serviceinfo["item"]
                    title = _("Item")
                self._render_rule_reason(title, None, "", "", False, item_text)
                self._output_analysed_ruleset(all_rulesets,
                                              rulespec,
                                              svc_desc_or_item=serviceinfo["item"],
                                              svc_desc=self._service,
                                              known_settings=self._PARAMETERS_OMIT)
                assert isinstance(rulespec.valuespec, Tuple)
                html.write(rulespec.valuespec._elements[2].value_to_text(serviceinfo["parameters"]))
                html.close_td()
                html.close_tr()
                html.close_table()

        elif origin == "active":
            checktype = serviceinfo["checktype"]
            rulespec = rulespec_registry["active_checks:" + checktype]
            self._output_analysed_ruleset(all_rulesets,
                                          rulespec,
                                          svc_desc_or_item=None,
                                          svc_desc=None,
                                          known_settings=serviceinfo["parameters"])

        elif origin == "classic":
            ruleset = all_rulesets.get("custom_checks")
            origin_rule_result = self._get_custom_check_origin_rule(ruleset, self._hostname,
                                                                    self._service)
            if origin_rule_result is None:
                raise MKUserError(
                    None,
                    _("Failed to determine origin rule of %s / %s") %
                    (self._hostname, self._service))
            rule_folder, rule_index, _rule = origin_rule_result

            url = watolib.folder_preserving_link([('mode', 'edit_ruleset'),
                                                  ('varname', "custom_checks"),
                                                  ('host', self._hostname)])
            forms.section(html.render_a(_("Command Line"), href=url))
            url = watolib.folder_preserving_link([('mode', 'edit_rule'),
                                                  ('varname', "custom_checks"),
                                                  ('rule_folder', rule_folder.path()),
                                                  ('rulenr', rule_index), ('host', self._hostname)])

            html.open_table(class_="setting")
            html.open_tr()

            html.open_td(class_="reason")
            html.a("%s %d %s %s" % (_("Rule"), rule_index + 1, _("in"), rule_folder.title()),
                   href=url)
            html.close_td()
            html.open_td(class_=["settingvalue", "used"])
            if "command_line" in serviceinfo:
                html.tt(serviceinfo["command_line"])
            else:
                html.write_text(_("(no command line, passive check)"))
            html.close_td()

            html.close_tr()
            html.close_table()

        self._show_labels(serviceinfo.get("labels", {}), "service",
                          serviceinfo.get("label_sources", {}))

    def _get_custom_check_origin_rule(self, ruleset: Ruleset, hostname: str,
                                      svc_desc: str) -> Optional[_Tuple[CREFolder, int, Rule]]:
        # We could use the outcome of _setting instead of the outcome of
        # the automation call in the future
        _setting, rules = ruleset.analyse_ruleset(self._hostname,
                                                  svc_desc_or_item=None,
                                                  svc_desc=None)

        for rule_folder, rule_index, rule in rules:
            if rule.is_disabled():
                continue
            if rule.value["service_description"] != self._service:
                continue

            return rule_folder, rule_index, rule

        return None

    def _show_labels(self, labels, object_type, label_sources):
        forms.section(_("Effective labels"))
        html.open_table(class_="setting")
        html.open_tr()

        html.open_td(class_="reason")
        html.i(_("Explicit, ruleset, discovered"))
        html.close_td()
        html.open_td(class_=["settingvalue", "used"])
        html.write(
            cmk.gui.view_utils.render_labels(labels,
                                             object_type,
                                             with_links=False,
                                             label_sources=label_sources))
        html.close_td()

        html.close_tr()
        html.close_table()

    def _render_rule_reason(self, title, title_url, reason, reason_url, is_default, setting):
        if title_url:
            title = html.render_a(title, href=title_url)
        forms.section(title)

        if reason:
            reason = html.render_a(reason, href=reason_url)

        html.open_table(class_="setting")
        html.open_tr()
        if is_default:
            html.td(html.render_i(reason), class_="reason")
            html.td(setting, class_=["settingvalue", "unused"])
        else:
            html.td(reason, class_="reason")
            html.td(setting, class_=["settingvalue", "used"])
        html.close_tr()
        html.close_table()

    def _output_analysed_ruleset(self,
                                 all_rulesets,
                                 rulespec,
                                 svc_desc_or_item,
                                 svc_desc,
                                 known_settings=None):
        if known_settings is None:
            known_settings = self._PARAMETERS_UNKNOWN

        def rule_url(rule):
            return watolib.folder_preserving_link([
                ('mode', 'edit_rule'),
                ('varname', varname),
                ('rule_folder', rule.folder.path()),
                ('rulenr', rule.index()),
                ('host', self._hostname),
                ('item', ensure_str(watolib.mk_repr(svc_desc_or_item)) if svc_desc_or_item else ''),
                ('service', ensure_str(watolib.mk_repr(svc_desc)) if svc_desc else ''),
            ])

        varname = rulespec.name
        valuespec = rulespec.valuespec

        url = watolib.folder_preserving_link([
            ('mode', 'edit_ruleset'),
            ('varname', varname),
            ('host', self._hostname),
            ('item', ensure_str(watolib.mk_repr(svc_desc_or_item))),
            ('service', ensure_str(watolib.mk_repr(svc_desc))),
        ])

        forms.section(html.render_a(rulespec.title, url))

        ruleset = all_rulesets.get(varname)
        setting, rules = ruleset.analyse_ruleset(self._hostname, svc_desc_or_item, svc_desc)

        html.open_table(class_="setting")
        html.open_tr()
        html.open_td(class_="reason")

        # Show reason for the determined value
        if len(rules) == 1:
            rule_folder, rule_index, rule = rules[0]
            url = rule_url(rule)
            html.a(_("Rule %d in %s") % (rule_index + 1, rule_folder.title()), href=rule_url(rule))

        elif len(rules) > 1:
            html.a("%d %s" % (len(rules), _("Rules")), href=url)

        else:
            html.i(_("Default Value"))
        html.close_td()

        # Show the resulting value or factory setting
        html.open_td(class_=["settingvalue", "used" if len(rules) > 0 else "unused"])

        if isinstance(known_settings, dict) and "tp_computed_params" in known_settings:
            computed_at = known_settings["tp_computed_params"]["computed_at"]
            html.write_text(
                _("Timespecific parameters computed at %s") %
                cmk.utils.render.date_and_time(computed_at))
            html.br()
            known_settings = known_settings["tp_computed_params"]["params"]

        # In some cases we now the settings from a check_mk automation
        if known_settings is self._PARAMETERS_OMIT:
            return

        # Special handling for logwatch: The check parameter is always None. The actual
        # patterns are configured in logwatch_rules. We do not have access to the actual
        # patterns here but just to the useless "None". In order not to complicate things
        # we simply display nothing here.
        if varname == "logwatch_rules":
            pass

        elif known_settings is not self._PARAMETERS_UNKNOWN:
            try:
                html.write(valuespec.value_to_text(known_settings))
            except Exception as e:
                if config.debug:
                    raise
                html.write_text(_("Invalid parameter %r: %s") % (known_settings, e))

        else:
            # For match type "dict" it can be the case the rule define some of the keys
            # while other keys are taken from the factory defaults. We need to show the
            # complete outcoming value here.
            if rules and ruleset.match_type() == "dict":
                if rulespec.factory_default is not watolib.Rulespec.NO_FACTORY_DEFAULT \
                    and rulespec.factory_default is not watolib.Rulespec.FACTORY_DEFAULT_UNUSED:
                    fd = rulespec.factory_default.copy()
                    fd.update(setting)
                    setting = fd

            if valuespec and not rules:  # show the default value
                if rulespec.factory_default is watolib.Rulespec.FACTORY_DEFAULT_UNUSED:
                    # Some rulesets are ineffective if they are empty
                    html.write_text(_("(unused)"))

                elif rulespec.factory_default is not watolib.Rulespec.NO_FACTORY_DEFAULT:
                    # If there is a factory default then show that one
                    setting = rulespec.factory_default
                    html.write(valuespec.value_to_text(setting))

                elif ruleset.match_type() in ("all", "list"):
                    # Rulesets that build lists are empty if no rule matches
                    html.write_text(_("(no entry)"))

                else:
                    # Else we use the default value of the valuespec
                    html.write(valuespec.value_to_text(valuespec.default_value()))

            # We have a setting
            elif valuespec:
                if ruleset.match_type() == "all":
                    html.write(", ".join(valuespec.value_to_text(s) for s in setting))
                else:
                    html.write(valuespec.value_to_text(setting))

            # Binary rule, no valuespec, outcome is True or False
            else:
                icon_name = "rule_%s%s" % ("yes" if setting else "no", "_off" if not rules else '')
                html.icon(icon_name, title=_("yes") if setting else _("no"))
        html.close_td()
        html.close_tr()
        html.close_table()
