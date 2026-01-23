#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Verify or find out a hosts agent related configuration"""

# mypy: disable-error-code="exhaustive-match"

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

import base64
import json
from collections.abc import Collection
from typing import NotRequired, override, TypedDict

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    make_form_submit_link,
    PageMenu,
    PageMenuDropdown,
    PageMenuEntry,
    PageMenuTopic,
)
from cmk.gui.pages import AjaxPage, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.type_defs import ActionResult, IconNames, PermissionName, StaticIcon
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.encrypter import Encrypter
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.user_errors import user_errors
from cmk.gui.valuespec import Dictionary, DropdownChoice, FixedValue, Float, Integer, Password
from cmk.gui.valuespec import HostAddress as VSHostAddress
from cmk.gui.wato.pages.hosts import ModeEditHost, page_menu_host_entries
from cmk.gui.watolib.attributes import SNMPCredentials as VSSNMPCredentials
from cmk.gui.watolib.automations import make_automation_config
from cmk.gui.watolib.check_mk_automations import diag_host
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import folder_from_request, folder_preserving_link, Host
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.rulesets import AllRulesets
from cmk.snmplib import SNMPCredentials  # astrein: disable=cmk-module-layer-violation

SNMPv3NoAuthNoPriv = tuple[str, str]
SNMPv3AuthNoPriv = tuple[str, str, str, str]
SNMPv3AuthPriv = tuple[str, str, str, str, str, str]


class HostSpec(TypedDict):
    hostname: HostName
    ipaddress: NotRequired[HostAddress]
    snmp_community: NotRequired[SNMPCredentials]
    snmp_v3_credentials: NotRequired[SNMPv3NoAuthNoPriv | SNMPv3AuthNoPriv | SNMPv3AuthPriv]


def register(page_registry: PageRegistry, mode_registry: ModeRegistry) -> None:
    page_registry.register(PageEndpoint("wato_ajax_diag_host", PageAjaxDiagHost()))
    mode_registry.register(ModeDiagHost)


class ModeDiagHost(WatoMode):
    @classmethod
    def name(cls) -> str:
        return "diag_host"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "diag_host"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditHost

    @classmethod
    def diag_host_tests(cls) -> list[tuple[str, str]]:
        return [
            ("ping", _("Ping")),
            ("agent", _("Agent")),
            ("snmpv1", _("SNMPv1")),
            ("snmpv2", _("SNMPv2c")),
            ("snmpv2_nobulk", _("SNMPv2c (without bulk walk)")),
            ("snmpv3", _("SNMPv3")),
            ("traceroute", _("Traceroute")),
        ]

    def _from_vars(self) -> None:
        self._hostname = request.get_validated_type_input_mandatory(HostName, "host")
        self._host = folder_from_request(request.var("folder"), self._hostname).load_host(
            self._hostname
        )
        self._host.permissions.need_permission("read")

        if self._host.is_cluster():
            raise MKGeneralException(_("This page does not support cluster hosts."))

        if "cmk/relay_monitored" in self._host.labels():
            raise MKGeneralException(_("This page does not support relay monitored hosts."))

    def title(self) -> str:
        return _("Test connection to host") + " " + self._hostname

    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
                PageMenuDropdown(
                    name="actions",
                    title=_("Test"),
                    topics=[
                        PageMenuTopic(
                            title=_("Options"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Run tests"),
                                    icon_name=StaticIcon(IconNames.connection_tests),
                                    item=make_form_submit_link("diag_host", "_save"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                        PageMenuTopic(
                            title=_("Host properties"),
                            entries=[
                                PageMenuEntry(
                                    title=_("Save & go to host properties"),
                                    icon_name=StaticIcon(IconNames.save),
                                    item=make_form_submit_link("diag_host", "go_to_properties"),
                                    is_shortcut=True,
                                    is_suggested=True,
                                ),
                            ],
                        ),
                    ],
                ),
                PageMenuDropdown(
                    name="host",
                    title=_("Host"),
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

    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        if not transactions.check_transaction():
            return None

        if request.var("_save"):
            try:
                self._validate_diag_html_vars()
            except MKUserError as e:
                user_errors.add(e)
            return None

        if request.var("go_to_properties"):
            # Save the ipaddress and/or community
            vs_host = self._vs_host()
            new = vs_host.from_html_vars("vs_host")
            vs_host.validate_value(new, "vs_host")

            return_message = []
            attributes = HostAttributes()

            if "ipaddress" in new:
                return_message.append(_("IP address"))
                attributes["ipaddress"] = new["ipaddress"]

            # If both SNMP types have credentials set - SNMPv3 takes precedence
            if "snmp_v3_credentials" in new:
                if "snmp_community" in new:
                    return_message.append(_("SNMPv3 credentials (SNMPv2 community was discarded)"))
                else:
                    return_message.append(_("SNMPv3 credentials"))
                attributes["snmp_community"] = new["snmp_v3_credentials"]
            elif "snmp_community" in new:
                return_message.append(_("SNMP credentials"))
                attributes["snmp_community"] = new["snmp_community"]

            self._host.update_attributes(
                attributes, pprint_value=config.wato_pprint_config, use_git=config.wato_use_git
            )

            flash(_("Updated attributes: ") + ", ".join(return_message))
            return redirect(
                mode_url(
                    "edit_host",
                    host=self._hostname,
                    folder=folder_from_request(
                        request.var("folder"), request.get_ascii_input("host")
                    ).path(),
                )
            )
        return None

    def _validate_diag_html_vars(self) -> None:
        vs_host = self._vs_host()
        host_vars = vs_host.from_html_vars("vs_host")
        vs_host.validate_value(host_vars, "vs_host")

        vs_rules = self._vs_rules()
        rule_vars = vs_rules.from_html_vars("vs_rules")
        vs_rules.validate_value(rule_vars, "vs_rules")

    def page(self, config: Config) -> None:
        html.open_div(class_="diag_host")
        html.open_table()
        html.open_tr()
        html.open_td()
        all_rulesets = AllRulesets.load_all_rulesets()
        agent_ports_ruleset = all_rulesets.get("agent_ports")
        tcp_connect_timeouts_ruleset = all_rulesets.get("tcp_connect_timeouts")
        snmp_timing_ruleset = all_rulesets.get("snmp_timing")
        agent_port: int | None = None
        match agent_ports_ruleset.analyse_ruleset(
            hostname=self._hostname,
            svc_desc_or_item=None,
            svc_desc=None,
            service_labels={},
            debug=config.debug,
        ):
            case int() as agent_port, _:
                pass

        tcp_connect_timeout: float | None = None
        match tcp_connect_timeouts_ruleset.analyse_ruleset(
            hostname=self._hostname,
            svc_desc_or_item=None,
            svc_desc=None,
            service_labels={},
            debug=config.debug,
        ):
            case float() as tcp_connect_timeout, _:
                pass

        snmp_timing: dict[str, int] = {}
        match snmp_timing_ruleset.analyse_ruleset(
            hostname=self._hostname,
            svc_desc_or_item=None,
            svc_desc=None,
            service_labels={},
            debug=config.debug,
        ):
            case dict() as snmp_timing, _:
                pass

        with html.form_context("diag_host", method="POST"):
            html.prevent_password_auto_completion()

            forms.header(_("Host Properties"))

            forms.section(legend=False)

            # The diagnose page shows both SNMP variants at the same time
            # We need to analyse the preconfigured community and set either the
            # snmp_community or the snmp_v3_credentials
            vs_dict: dict[str, object] = {}
            for key, value in self._host.attributes.items():
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

            forms.header(_("Options"))

            value = {}
            forms.section(legend=False)
            vs_rules = self._vs_rules(
                agent_port=agent_port,
                tcp_connect_timeout=tcp_connect_timeout,
                snmp_timeout=snmp_timing.get("timeout"),
                snmp_retries=snmp_timing.get("retries"),
            )
            vs_rules.render_input("vs_rules", value)
            html.help(vs_rules.help())
            forms.end()

            # When clicking "Save & Test" on the "Edit host" page, this will be set
            # to immediately execute the tests using the just saved settings
            if request.has_var("_start_on_load"):
                html.final_javascript("cmk.page_menu.form_submit('diag_host', '_save');")

            html.hidden_fields()

        html.close_td()
        html.open_td(style="padding-left:10px;")

        self._show_diagnose_output()

    def _show_diagnose_output(self) -> None:
        if not request.var("_save"):
            html.show_message(
                _(
                    "You can diagnose the connection to a specific host using this dialog. "
                    "You can either test whether your current configuration is still working "
                    "or investigate in which ways a host can be reached. Simply configure the "
                    "connection options you like to try on the right side of the screen and "
                    'press the "Test" button. The results will be displayed here.'
                )
            )
            return

        if user_errors:
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
            html.static_icon(StaticIcon(IconNames.reload), id_="%s_img" % ident)
            html.open_a(href="")
            html.static_icon(
                StaticIcon(IconNames.reload),
                title=_("Retry this test"),
                css_classes=["retry"],
                id_="%s_retry" % ident,
            )
            html.close_a()
            html.close_div()
            html.close_td()

            html.open_td()
            html.div("", class_="log", id="%s_log" % ident)
            html.close_td()

            html.close_tr()
            html.close_table()
            html.javascript(
                "cmk.host_diagnose.start_test(%s, %s, %s)"
                % (
                    json.dumps(ident),
                    json.dumps(self._hostname),
                    json.dumps(transactions.fresh_transid()),
                )
            )

    def _vs_host(self) -> Dictionary:
        return Dictionary(
            required_keys=["hostname"],
            elements=[
                (
                    "hostname",
                    FixedValue(
                        value=self._hostname,
                        title=_("Host name"),
                    ),
                ),
                (
                    "ipaddress",
                    VSHostAddress(
                        title=_("IPv4 address"),
                        allow_empty=False,
                        allow_ipv6_address=False,
                    ),
                ),
                (
                    "snmp_community",
                    Password(
                        title=_("SNMPv1/2 community"),
                        allow_empty=False,
                    ),
                ),
                (
                    "snmp_v3_credentials",
                    VSSNMPCredentials(
                        default_value=None,
                        only_v3=True,
                    ),
                ),
            ],
        )

    def _vs_rules(
        self,
        agent_port: int | None = None,
        tcp_connect_timeout: float | None = None,
        snmp_timeout: int | None = None,
        snmp_retries: int | None = None,
    ) -> Dictionary:
        return Dictionary(
            optional_keys=False,
            elements=[
                (
                    "agent_port",
                    Integer(
                        minvalue=1,
                        maxvalue=65535,
                        default_value=agent_port if agent_port is not None else 6556,
                        title=_('Checkmk Agent Port (<a href="%s">Rules</a>)')
                        % folder_preserving_link(
                            [
                                ("mode", "edit_ruleset"),
                                ("varname", "agent_ports"),
                            ]
                        ),
                        help=_(
                            "This variable allows to specify the TCP port to "
                            "be used to connect to the agent on a per-host-basis."
                        ),
                    ),
                ),
                (
                    "tcp_connect_timeout",
                    Float(
                        minvalue=1.0,
                        default_value=tcp_connect_timeout
                        if tcp_connect_timeout is not None
                        else 5.0,
                        unit=_("sec"),
                        display_format="%.0f",  # show values consistent to
                        size=2,  # SNMP-Timeout
                        title=_('TCP connection timeout (<a href="%s">Rules</a>)')
                        % folder_preserving_link(
                            [
                                ("mode", "edit_ruleset"),
                                ("varname", "tcp_connect_timeouts"),
                            ]
                        ),
                        help=_(
                            "This variable allows to specify a timeout for the "
                            "TCP connection to the Checkmk agent on a per-host-basis. "
                            "If the agent does not respond within this time, it is considered to be unreachable."
                        ),
                    ),
                ),
                (
                    "snmp_timeout",
                    Integer(
                        title=_('SNMP-Timeout (<a href="%s">Rules</a>)')
                        % folder_preserving_link(
                            [
                                ("mode", "edit_ruleset"),
                                ("varname", "snmp_timing"),
                            ]
                        ),
                        help=_(
                            "After a request is sent to the remote SNMP agent, the service will wait up to "
                            "the provided timeout limit before assuming that the answer got lost and retrying."
                        ),
                        default_value=snmp_timeout if snmp_timeout is not None else 1,
                        minvalue=1,
                        maxvalue=60,
                        unit=_("sec"),
                    ),
                ),
                (
                    "snmp_retries",
                    Integer(
                        title=_('SNMP-Retries (<a href="%s">Rules</a>)')
                        % folder_preserving_link(
                            [
                                ("mode", "edit_ruleset"),
                                ("varname", "snmp_timing"),
                            ]
                        ),
                        default_value=snmp_retries if snmp_retries is not None else 5,
                        minvalue=0,
                        maxvalue=50,
                    ),
                ),
            ],
        )


class PageAjaxDiagHost(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        check_csrf_token()
        if not user.may("wato.diag_host"):
            raise MKAuthException(_("You are not permitted to perform this action."))

        if not transactions.check_transaction():
            raise MKAuthException(_("Invalid transaction"))

        api_request = ctx.request.get_request()

        hostname = api_request.get("host")
        if not hostname:
            raise MKGeneralException(_("The host name is missing."))

        host = Host.host(hostname)

        if not host:
            raise MKGeneralException(_("The given host does not exist."))
        if host.is_cluster():
            raise MKGeneralException(_("This view does not support cluster hosts."))

        host.permissions.need_permission("read")

        _test = api_request.get("_test")
        if not _test:
            raise MKGeneralException(_("The test is missing."))

        # Execute a specific test
        if _test not in dict(ModeDiagHost.diag_host_tests()):
            raise MKGeneralException(_("Invalid test."))

        # TODO: Use ModeDiagHost._vs_rules() for processing/validation?
        args: list[str] = [""] * 13
        for idx, what in enumerate(
            [
                "ipaddress",
                "snmp_community",
                "agent_port",
                "snmp_timeout",
                "snmp_retries",
                "tcp_connect_timeout",
            ]
        ):
            args[idx] = api_request.get(what, "")

        if api_request.get("snmpv3_use"):
            snmpv3_use = {
                "0": "noAuthNoPriv",
                "1": "authNoPriv",
                "2": "authPriv",
            }.get(api_request.get("snmpv3_use", ""), "")

            args[7] = snmpv3_use
            if snmpv3_use != "noAuthNoPriv":
                snmpv3_auth_proto = {
                    str(DropdownChoice.option_id("md5")): "md5",
                    str(DropdownChoice.option_id("sha")): "sha",
                    str(DropdownChoice.option_id("SHA-224")): "SHA-224",
                    str(DropdownChoice.option_id("SHA-256")): "SHA-256",
                    str(DropdownChoice.option_id("SHA-384")): "SHA-384",
                    str(DropdownChoice.option_id("SHA-512")): "SHA-512",
                }.get(api_request.get("snmpv3_auth_proto", ""), "")

                args[8] = snmpv3_auth_proto
                args[9] = api_request.get("snmpv3_security_name", "")
                args[10] = _decrypt_passwd(api_request.get("snmpv3_security_password", ""))

                if snmpv3_use == "authPriv":
                    snmpv3_privacy_proto = {
                        str(DropdownChoice.option_id("DES")): "DES",
                        str(DropdownChoice.option_id("AES")): "AES",
                        str(DropdownChoice.option_id("AES-192")): "AES-192",
                        str(DropdownChoice.option_id("AES-256")): "AES-256",
                    }.get(api_request.get("snmpv3_privacy_proto", ""), "")

                    args[11] = snmpv3_privacy_proto

                    args[12] = _decrypt_passwd(api_request.get("snmpv3_privacy_password", ""))
            else:
                args[9] = api_request.get("snmpv3_security_name", "")

        result = diag_host(
            make_automation_config(ctx.config.sites[host.site_id()]),
            hostname,
            _test,
            ctx.config.debug,
            *args,
        )
        return {
            "next_transid": transactions.fresh_transid(),
            "status_code": result.return_code,
            "output": result.response,
        }


def _decrypt_passwd(encrypted_passwd: str) -> str:
    try:
        return Encrypter.decrypt(base64.b64decode(encrypted_passwd.encode("ascii")))
    except Exception:
        raise MKUserError(None, _("Decryption of SNMPv3 password failed."))
