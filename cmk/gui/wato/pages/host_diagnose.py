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
"""Verify or find out a hosts agent related configuration"""

import json

import cmk.gui.pages
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
from cmk.gui.exceptions import MKAuthException, MKGeneralException, MKUserError
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.wato.utils.context_buttons import host_status_button
from cmk.gui.pages import page_registry, AjaxPage

from cmk.gui.valuespec import (
    TextAscii,
    DropdownChoice,
    Integer,
    Float,
    Dictionary,
    Password,
    HostAddress,
    FixedValue,
)

from cmk.gui.plugins.wato import (
    WatoMode,
    mode_registry,
    monitoring_macro_help,
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
        self._hostname = html.request.var("host")
        if not self._hostname:
            raise MKGeneralException(_('The hostname is missing.'))

        self._host = watolib.Folder.current().host(self._hostname)
        self._host.need_permission("read")

        if self._host.is_cluster():
            raise MKGeneralException(_('This page does not support cluster hosts.'))

    def title(self):
        return _('Diagnostic of host') + " " + self._hostname

    def buttons(self):
        html.context_button(_("Folder"), watolib.folder_preserving_link([("mode", "folder")]),
                            "back")
        host_status_button(self._hostname, "hoststatus")
        html.context_button(_("Properties"), self._host.edit_url(), "edit")
        if config.user.may('wato.rulesets'):
            html.context_button(_("Parameters"), self._host.params_url(), "rulesets")
        html.context_button(_("Services"), self._host.services_url(), "services")

    def action(self):
        if not html.check_transaction():
            return

        if html.request.var('_try'):
            try:
                self._validate_diag_html_vars()
            except MKUserError as e:
                html.add_user_error(e.varname, e)
            return

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
            return_message = _("Updated attributes: ") + ", ".join(return_message)

            self._host.update_attributes(new)
            html.request.del_vars()
            html.request.set_var("host", self._hostname)
            html.request.set_var("folder", watolib.Folder.current().path())
            return "edit_host", return_message

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
        html.button("_save", _("Save & Exit"))
        html.close_div()

        forms.header(_('Options'))

        value = {}
        forms.section(legend=False)
        vs_rules = self._vs_rules()
        vs_rules.render_input("vs_rules", value)
        html.help(vs_rules.help())
        forms.end()

        html.button("_try", _("Test"))

        html.hidden_fields()
        html.end_form()

        html.close_td()
        html.open_td(style="padding-left:10px;")

        self._show_diagnose_output()

    def _show_diagnose_output(self):
        if not html.request.var('_try'):
            html.message(
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
            html.icon(title=None, icon="reload", id_="%s_img" % ident)
            html.open_a(href="")
            html.icon(title=_('Retry this test'),
                      icon="reload",
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
        return Dictionary(required_keys=['hostname'],
                          elements=[
                              ('hostname',
                               FixedValue(self._hostname, title=_('Hostname'), allow_empty=False)),
                              ('ipaddress',
                               HostAddress(
                                   title=_("IPv4 Address"),
                                   allow_empty=False,
                                   allow_ipv6_address=False,
                               )),
                              ('snmp_community',
                               Password(title=_("SNMPv1/2 community"), allow_empty=False)),
                              ('snmp_v3_credentials',
                               cmk.gui.plugins.wato.SNMPCredentials(default_value=None,
                                                                    only_v3=True)),
                          ])

    def _vs_rules(self):
        if config.user.may('wato.add_or_modify_executables'):
            ds_option = [
                ('datasource_program', TextAscii(
                    title = _("Datasource Program (<a href=\"%s\">Rules</a>)") % \
                        watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'datasource_programs')]),
                    help = _("For agent based checks Check_MK allows you to specify an alternative "
                             "program that should be called by Check_MK instead of connecting the agent "
                             "via TCP. That program must output the agent's data on standard output in "
                             "the same format the agent would do. This is for example useful for monitoring "
                             "via SSH.") + monitoring_macro_help() + " "
                         + _("This option can only be used with the permission \"Can add or modify executables\"."),
                ))
            ]
        else:
            ds_option = []

        return Dictionary(
            optional_keys = False,
            elements = [
                ('agent_port', Integer(
                    allow_empty = False,
                    minvalue = 1,
                    maxvalue = 65535,
                    default_value = 6556,
                    title = _("Check_MK Agent Port (<a href=\"%s\">Rules</a>)") % \
                        watolib.folder_preserving_link([('mode', 'edit_ruleset'), ('varname', 'agent_ports')]),
                    help = _("This variable allows to specify the TCP port to "
                             "be used to connect to the agent on a per-host-basis.")
                )),
                ('tcp_connect_timeout', Float(
                    allow_empty = False,
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
                    allow_empty = False,
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
                    allow_empty = False,
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
        args = [""] * 13
        for idx, what in enumerate([
                'ipaddress',
                'snmp_community',
                'agent_port',
                'snmp_timeout',
                'snmp_retries',
                'tcp_connect_timeout',
        ]):
            args[idx] = request.get(what, "")

        if config.user.may('wato.add_or_modify_executables'):
            args[6] = request.get("datasource_program", "")

        if request.get("snmpv3_use"):
            snmpv3_use = {
                "0": "noAuthNoPriv",
                "1": "authNoPriv",
                "2": "authPriv",
            }.get(request.get("snmpv3_use"))
            args[7] = snmpv3_use
            if snmpv3_use != "noAuthNoPriv":
                snmpv3_auth_proto = {
                    DropdownChoice.option_id("md5"): "md5",
                    DropdownChoice.option_id("sha"): "sha"
                }.get(request.get("snmpv3_auth_proto"))
                args[8] = snmpv3_auth_proto
                args[9] = request.get("snmpv3_security_name")
                args[10] = request.get("snmpv3_security_password")
                if snmpv3_use == "authPriv":
                    snmpv3_privacy_proto = {
                        DropdownChoice.option_id("DES"): "DES",
                        DropdownChoice.option_id("AES"): "AES"
                    }.get(request.get("snmpv3_privacy_proto"))
                    args[11] = snmpv3_privacy_proto
                    args[12] = request.get("snmpv3_privacy_password")
            else:
                args[9] = request.get("snmpv3_security_name")

        result = watolib.check_mk_automation(host.site_id(), "diag-host", [hostname, _test] + args)
        return {
            "next_transid": html.transaction_manager.fresh_transid(),
            "status_code": result[0],
            "output": result[1],
        }
