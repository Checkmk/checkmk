#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Verify or find out a hosts agent related configuration"""

import json
from typing import List, Optional, Type

from six import ensure_str

import cmk.gui.pages
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.exceptions import MKAuthException, MKGeneralException, MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.valuespec import (
    TextAscii,
    DropdownChoice,
    Integer,
    Float,
    Dictionary,
    Password,
    HostAddress,
    FixedValue,
    DictionaryEntry,
)
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    make_form_submit_link,
)
from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.wato.pages.hosts import ModeEditHost, page_menu_host_entries

from cmk.gui.plugins.wato import (
    WatoMode,
    ActionResult,
    mode_registry,
    monitoring_macro_help,
    flash,
    mode_url,
    redirect,
)


@mode_registry.register
class ModeDiagHost(WatoMode):
    @classmethod
    def name(cls):
        return "diag_host"

    @classmethod
    def permissions(cls):
        return ["hosts", "diag_host"]

    @classmethod
    def parent_mode(cls) -> Optional[Type[WatoMode]]:
        return ModeEditHost

    @classmethod
    def diag_host_tests(cls):
        return [
            ('ping', _('Ping')),
            ('agent', _('Agent')),
            ('snmpv1', _('SNMPv1')),
            ('snmpv2', _('SNMPv2c')),
            ('snmpv2_nobulk', _('SNMPv2c (without Bulkwalk)')),
            ('snmpv3', _('SNMPv3')),
            ('traceroute', _('Traceroute')),
        ]

    def _from_vars(self):
        self._hostname = html.request.get_ascii_input_mandatory("host")
        self._host = watolib.Folder.current().host(self._hostname)
        self._host.need_permission("read")

        if self._host.is_cluster():
            raise MKGeneralException(_('This page does not support cluster hosts.'))

    def title(self):
        return _('Test connection to host') + " " + self._hostname

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="actions",
                    title=_("Actions"),
                    topics=[
                        PageMenuTopic(
                            title=_("Host properties"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Save & go to host properties"),
                                    icon_name="save",
                                    item=make_form_submit_link("diag_host", "_save"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Options"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Test"),
                                    icon_name="save",
                                    item=make_form_submit_link("diag_host", "_try"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
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
            ],
            breadcrumb=breadcrumb,
        )

    def action(self) -> ActionResult:
        if not html.check_transaction():
            return None

        if html.request.var('_try'):
            try:
                self._validate_diag_html_vars()
            except MKUserError as e:
                html.add_user_error(e.varname, e)
            return None

        if html.request.var('_save'):
            # Save the ipaddress and/or community
            vs_host = self._vs_host()
            new = vs_host.from_html_vars('vs_host')
            vs_host.validate_value(new, 'vs_host')

            # If both snmp types have credentials set - snmpv3 takes precedence
            return_message = []
            if "ipaddress" in new:
                return_message.append(_("IP address"))
            if "snmp_v3_credentials" in new:
                if "snmp_community" in new:
                    return_message.append(_("SNMPv3 credentials (SNMPv2 community was discarded)"))
                else:
                    return_message.append(_("SNMPv3 credentials"))
                new["snmp_community"] = new["snmp_v3_credentials"]
            elif "snmp_community" in new:
                return_message.append(_("SNMP credentials"))

            self._host.update_attributes(new)
            flash(_("Updated attributes: ") + ", ".join(return_message))
            return redirect(
                mode_url(
                    "edit_host",
                    host=self._hostname,
                    folder=watolib.Folder.current().path(),
                ))
        return None

    def _validate_diag_html_vars(self):
        vs_host = self._vs_host()
        host_vars = vs_host.from_html_vars("vs_host")
        vs_host.validate_value(host_vars, "vs_host")

        vs_rules = self._vs_rules()
        rule_vars = vs_rules.from_html_vars("vs_rules")
        vs_rules.validate_value(rule_vars, "vs_rules")

    def page(self):
        html.open_div(class_="diag_host")
        html.open_table()
        html.open_tr()
        html.open_td()

        html.begin_form('diag_host', method="POST")
        html.prevent_password_auto_completion()

        forms.header(_('Host Properties'))

        forms.section(legend=False)

        # The diagnose page shows both snmp variants at the same time
        # We need to analyse the preconfigured community and set either the
        # snmp_community or the snmp_v3_credentials
        vs_dict = {}
        for key, value in self._host.attributes().items():
            if key == "snmp_community" and isinstance(value, tuple):
                vs_dict["snmp_v3_credentials"] = value
                continue
            vs_dict[key] = value

        vs_host = self._vs_host()
        vs_host.render_input("vs_host", vs_dict)
        html.help(vs_host.help())

        forms.end()

        html.open_div(style="margin-bottom:10px")
        html.close_div()

        forms.header(_('Options'))

        value = {}
        forms.section(legend=False)
        vs_rules = self._vs_rules()
        vs_rules.render_input("vs_rules", value)
        html.help(vs_rules.help())
        forms.end()

        # When clicking "Save & Test" on the "Edit host" page, this will be set
        # to immediately execute the tests using the just saved settings
        if html.request.has_var("_start_on_load"):
            html.final_javascript("cmk.page_menu.form_submit('diag_host', '_try');")

        html.hidden_fields()
        html.end_form()

        html.close_td()
        html.open_td(style="padding-left:10px;")

        self._show_diagnose_output()

    def _show_diagnose_output(self):
        if not html.request.var('_try'):
            html.show_message(
                _('You can diagnose the connection to a specific host using this dialog. '
                  'You can either test whether your current configuration is still working '
                  'or investigate in which ways a host can be reached. Simply configure the '
                  'connection options you like to try on the right side of the screen and '
                  'press the "Test" button. The results will be displayed here.'))
            return

        if html.has_user_errors():
            html.show_user_errors()
            return

        # TODO: Insert any vs_host valuespec validation
        #       These tests can be called with invalid valuespec settings...
        # TODO: Replace hard coded icon paths with dynamic ones to old or new theme
        for ident, title in ModeDiagHost.diag_host_tests():
            html.h3(title)
            html.open_table(class_=["data", "test"])
            html.open_tr(class_=["data", "odd0"])

            html.open_td(class_="icons")
            html.open_div()
            html.icon("reload", id_="%s_img" % ident)
            html.open_a(href="")
            html.icon("reload",
                      title=_('Retry this test'),
                      cssclass="retry",
                      id_="%s_retry" % ident)
            html.close_a()
            html.close_div()
            html.close_td()

            html.open_td()
            html.div('', class_="log", id="%s_log" % ident)
            html.close_td()

            html.close_tr()
            html.close_table()
            html.javascript('cmk.host_diagnose.start_test(%s, %s, %s)' %
                            (json.dumps(ident), json.dumps(self._hostname),
                             json.dumps(html.transaction_manager.fresh_transid())))

    def _vs_host(self):
        return Dictionary(
            required_keys=['hostname'],
            elements=[
                ('hostname', FixedValue(
                    self._hostname,
                    title=_('Hostname'),
                )),
                ('ipaddress',
                 HostAddress(
                     title=_("IPv4 Address"),
                     allow_empty=False,
                     allow_ipv6_address=False,
                 )),
                ('snmp_community', Password(
                    title=_("SNMPv1/2 community"),
                    allow_empty=False,
                )),
                ('snmp_v3_credentials',
                 cmk.gui.plugins.wato.SNMPCredentials(
                     default_value=None,
                     only_v3=True,
                 )),
            ],
        )

    def _vs_rules(self):
        if config.user.may('wato.add_or_modify_executables'):
            ds_option: List[DictionaryEntry] = [(
                'datasource_program',
                TextAscii(
                    title=_("Individual program call (<a href=\"%s\">Rules</a>)") %
                    watolib.folder_preserving_link([('mode', 'edit_ruleset'),
                                                    ('varname', 'datasource_programs')]),
                    help=
                    _("For agent based checks Check_MK allows you to specify an alternative "
                      "program that should be called by Check_MK instead of connecting the agent "
                      "via TCP. That program must output the agent's data on standard output in "
                      "the same format the agent would do. This is for example useful for monitoring "
                      "via SSH.") + monitoring_macro_help() + " " +
                    _("This option can only be used with the permission \"Can add or modify executables\"."
                     ),
                ))]
        else:
            ds_option = []

        return Dictionary(
            optional_keys = False,
            elements = [
                ('agent_port', Integer(
                    minvalue = 1,
                    maxvalue = 65535,
                    default_value = 6556,
                    title = _("Checkmk Agent Port (<a href=\"%s\">Rules</a>)") %
                        watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'agent_ports')]),
                    help = _("This variable allows to specify the TCP port to "
                             "be used to connect to the agent on a per-host-basis.")
                )),
                ('tcp_connect_timeout', Float(
                    minvalue = 1.0,
                    default_value = 5.0,
                    unit = _("sec"),
                    display_format = "%.0f",  # show values consistent to
                    size = 2,                 # SNMP-Timeout
                    title = _("TCP Connection Timeout (<a href=\"%s\">Rules</a>)") % \
                        watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'tcp_connect_timeouts')]),
                    help = _("This variable allows to specify a timeout for the "
                            "TCP connection to the Check_MK agent on a per-host-basis."
                            "If the agent does not respond within this time, it is considered to be unreachable.")
                )),
                ('snmp_timeout', Integer(
                    title = _("SNMP-Timeout (<a href=\"%s\">Rules</a>)") % \
                        watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'snmp_timing')]),
                    help = _("After a request is sent to the remote SNMP agent we will wait up to this "
                             "number of seconds until assuming the answer get lost and retrying."),
                    default_value = 1,
                    minvalue = 1,
                    maxvalue = 60,
                    unit = _("sec"),
                )),
                ('snmp_retries', Integer(
                    title = _("SNMP-Retries (<a href=\"%s\">Rules</a>)") % \
                        watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'snmp_timing')]),
                    default_value = 5,
                    minvalue = 0,
                    maxvalue = 50,
                )),
            ] + ds_option,
        )


@page_registry.register_page("wato_ajax_diag_host")
class ModeAjaxDiagHost(AjaxPage):
    def page(self):
        watolib.init_wato_datastructures(with_wato_lock=True)

        if not config.user.may('wato.diag_host'):
            raise MKAuthException(_('You are not permitted to perform this action.'))

        if not html.check_transaction():
            raise MKAuthException(_("Invalid transaction"))

        request = self.webapi_request()

        hostname = request.get("host")
        if not hostname:
            raise MKGeneralException(_('The hostname is missing.'))

        host = watolib.Host.host(hostname)

        if not host:
            raise MKGeneralException(_('The given host does not exist.'))
        if host.is_cluster():
            raise MKGeneralException(_('This view does not support cluster hosts.'))

        host.need_permission("read")

        _test = request.get('_test')
        if not _test:
            raise MKGeneralException(_('The test is missing.'))

        # Execute a specific test
        if _test not in dict(ModeDiagHost.diag_host_tests()).keys():
            raise MKGeneralException(_('Invalid test.'))

        # TODO: Use ModeDiagHost._vs_rules() for processing/validation?
        args: List[str] = [u""] * 13
        for idx, what in enumerate([
                'ipaddress',
                'snmp_community',
                'agent_port',
                'snmp_timeout',
                'snmp_retries',
                'tcp_connect_timeout',
        ]):
            args[idx] = request.get(what, u"")

        if config.user.may('wato.add_or_modify_executables'):
            args[6] = request.get("datasource_program", "")

        if request.get("snmpv3_use"):
            snmpv3_use = {
                u"0": u"noAuthNoPriv",
                u"1": u"authNoPriv",
                u"2": u"authPriv",
            }.get(request.get("snmpv3_use", u""), u"")

            args[7] = snmpv3_use
            if snmpv3_use != u"noAuthNoPriv":
                snmpv3_auth_proto = {
                    str(DropdownChoice.option_id("md5")): u"md5",
                    str(DropdownChoice.option_id("sha")): u"sha"
                }.get(request.get("snmpv3_auth_proto", u""), u"")

                args[8] = snmpv3_auth_proto
                args[9] = request.get("snmpv3_security_name", u"")
                args[10] = request.get("snmpv3_security_password", u"")

                if snmpv3_use == "authPriv":
                    snmpv3_privacy_proto = {
                        str(DropdownChoice.option_id("DES")): u"DES",
                        str(DropdownChoice.option_id("AES")): u"AES"
                    }.get(request.get("snmpv3_privacy_proto", u""), u"")

                    args[11] = snmpv3_privacy_proto

                    args[12] = request.get("snmpv3_privacy_password", u"")
            else:
                args[9] = request.get("snmpv3_security_name", u"")

        result = watolib.check_mk_automation(host.site_id(), "diag-host", [hostname, _test] + args)
        return {
            "next_transid": html.transaction_manager.fresh_transid(),
            "status_code": result[0],
            "output": ensure_str(result[1], errors="replace"),
        }
