#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Mode for displaying and modifying the rule based host and service
parameters. This is a host/service overview page over all things that can be
modified via rules."""

import functools
from collections.abc import Callable, Collection, Container, Iterator

from cmk.ccc.hostaddress import HostName

from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.servicename import Item

from cmk.automations.results import AnalyseServiceResult, ServiceInfo

import cmk.gui.view_utils
from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.page_menu import PageMenu, PageMenuDropdown, PageMenuEntry, PageMenuTopic
from cmk.gui.type_defs import PermissionName
from cmk.gui.utils.html import HTML
from cmk.gui.valuespec import Tuple, ValueSpecText
from cmk.gui.wato.pages.hosts import ModeEditHost, page_menu_host_entries
from cmk.gui.watolib.automations import (
    LocalAutomationConfig,
    make_automation_config,
    RemoteAutomationConfig,
)
from cmk.gui.watolib.check_mk_automations import analyse_host, analyse_service
from cmk.gui.watolib.hosts_and_folders import (
    Folder,
    folder_from_request,
    folder_preserving_link,
    Host,
)
from cmk.gui.watolib.mode import ModeRegistry, WatoMode
from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset
from cmk.gui.watolib.rulespecs import (
    AllowAll,
    get_rulegroup,
    get_rulespec_allow_list,
    Rulespec,
    rulespec_group_registry,
    rulespec_registry,
    RulespecAllowList,
)
from cmk.gui.watolib.utils import mk_repr

from ._status_links import make_service_status_link


def register(mode_registry: ModeRegistry) -> None:
    mode_registry.register(ModeObjectParameters)


NOTDISPLAYABLE = ["logwatch_ec_single"]


class ModeObjectParameters(WatoMode):
    _PARAMETERS_UNKNOWN: list = []
    _PARAMETERS_OMIT: list = []

    @classmethod
    def name(cls) -> str:
        return "object_parameters"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["hosts", "rulesets"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditHost

    def _from_vars(self):
        self._hostname = request.get_validated_type_input_mandatory(HostName, "host")
        host = folder_from_request(request.var("folder"), self._hostname).host(self._hostname)
        if host is None:
            raise MKUserError("host", _("The given host does not exist."))
        self._host: Host = host
        self._host.permissions.need_permission("read")

        # TODO: Validate?
        self._service = request.get_str_input("service")

    def title(self) -> str:
        title = _("Effective parameters of") + " " + self._hostname
        if self._service:
            title += " / " + self._service
        return title

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
        return PageMenu(
            dropdowns=[
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

    def page(self) -> None:
        all_rulesets = AllRulesets.load_all_rulesets()
        for_host: bool = not self._service

        # Object type specific detail information
        service_result: AnalyseServiceResult | None = None
        automation_config = make_automation_config(active_config.sites[self._host.site_id()])
        if for_host:
            self._show_host_info(automation_config=automation_config, debug=active_config.debug)
        else:
            assert self._service is not None
            service_result = analyse_service(
                automation_config,
                self._hostname,
                self._service,
                debug=active_config.debug,
            )
            self._show_service_info(
                all_rulesets=all_rulesets,
                service_result=service_result,
                debug=active_config.debug,
            )

        last_maingroup = None
        allow_list = get_rulespec_allow_list()
        irrelevant_rulesets = _get_irrelevant_rulesets(self._service)
        for groupname in sorted(rulespec_group_registry.get_host_rulespec_group_names(for_host)):
            maingroup = groupname.split("/")[0]
            for rulespec in sorted(
                rulespec_registry.get_by_group(groupname), key=lambda x: x.title or ""
            ):
                if rulespec.name in irrelevant_rulesets:
                    continue

                if not allow_list.is_visible(rulespec.name):
                    continue

                if (rulespec.item_type == "service") == (not self._service):
                    continue  # This rule is not for hosts/services

                # Open form for that group here, if we know that we have at least one rule
                if last_maingroup != maingroup:
                    last_maingroup = maingroup
                    rulegroup = get_rulegroup(maingroup)
                    forms.header(
                        rulegroup.title,
                        isopen=maingroup == "monconf",
                        narrow=True,
                        css="rulesettings",
                    )
                    html.help(rulegroup.help)

                self._output_analysed_ruleset(
                    all_rulesets,
                    rulespec,
                    svc_desc_or_item=self._service,
                    svc_desc=self._service,
                    service_result=service_result,
                    known_settings=None,
                    debug=active_config.debug,
                )

        forms.end()

    def _show_host_info(
        self, *, automation_config: LocalAutomationConfig | RemoteAutomationConfig, debug: bool
    ) -> None:
        host_info = analyse_host(
            automation_config,
            self._hostname,
            debug=debug,
        )
        forms.header(_("Host information"), isopen=True, narrow=True, css="rulesettings")
        self._show_labels(host_info.labels, "host", host_info.label_sources)

    def _show_service_info(
        self, all_rulesets: AllRulesets, service_result: AnalyseServiceResult, *, debug: bool
    ) -> None:
        assert self._service is not None
        serviceinfo = service_result.service_info
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
        self._render_rule_reason(_("Type of check"), "", "", "", False, origin_txt)

        handler = {
            "auto": self._handle_auto_origin,
            "static": self._handle_static_origin,
            "active": self._handle_active_origin,
            "classic": self._handle_classic_origin,
        }
        render_labels = functools.partial(
            self._show_labels, service_result.labels, "service", service_result.label_sources
        )
        rulespec_allow_list = get_rulespec_allow_list()
        handler[origin](
            serviceinfo,
            all_rulesets,
            rulespec_allow_list,
            service_result,
            render_labels,
            debug=debug,
        )
        return

    def _handle_auto_origin(
        self,
        serviceinfo: ServiceInfo,
        all_rulesets: AllRulesets,
        rulespec_allow_list: RulespecAllowList | AllowAll,
        service_result: AnalyseServiceResult,
        render_labels: Callable[[], None],
        *,
        debug: bool,
    ) -> None:
        # First case: discovered checks. They come from var/check_mk/autochecks/HOST.
        checkgroup = serviceinfo["checkgroup"]

        if (checktype := serviceinfo["checktype"]) in NOTDISPLAYABLE:
            reason = _("Check parameters for check type '%s' can not be displayed") % checktype
        else:
            reason = _("This check is not configurable via Setup")

        not_configurable_render = functools.partial(
            self._render_rule_reason,
            _("Parameters"),
            "",
            "",
            "",
            True,
            reason,
        )
        if not checkgroup or checkgroup == "None":
            not_configurable_render()
            render_labels()
            return

        if checkgroup == "logwatch":
            # Logwatch needs a special handling, since it is not configured
            # via checkgroup_parameters but via "logwatch_rules" in a special
            # Setup module.
            rulespec = rulespec_registry["logwatch_rules"]
            if rulespec_allow_list.is_visible(rulespec.name):
                self._output_analysed_ruleset(
                    all_rulesets,
                    rulespec,
                    svc_desc_or_item=serviceinfo["item"],
                    svc_desc=self._service,
                    known_settings=serviceinfo["parameters"],
                    service_result=service_result,
                    debug=debug,
                )
            else:
                not_configurable_render()
            render_labels()
            return

        # Note: some discovered checks have a check group but
        # *no* ruleset for discovered checks. One example is "ps".
        # That can be configured as a manual check or created by
        # inventory. But in the later case all parameters are set
        # by the inventory. This will be changed in a later version,
        # but we need to address it anyway.
        if RuleGroup.CheckgroupParameters(checkgroup) in rulespec_registry:
            rulespec = rulespec_registry["checkgroup_parameters:" + checkgroup]
            if rulespec_allow_list.is_visible(rulespec.name):
                self._output_analysed_ruleset(
                    all_rulesets,
                    rulespec,
                    svc_desc_or_item=serviceinfo["item"],
                    svc_desc=self._service,
                    known_settings=serviceinfo["parameters"],
                    service_result=service_result,
                    debug=debug,
                )
            else:
                not_configurable_render()
            render_labels()
            return

        if RuleGroup.StaticChecks(checkgroup) in rulespec_registry:
            not_configurable_render()
            return

        rulespec = rulespec_registry[RuleGroup.StaticChecks(checkgroup)]
        url = folder_preserving_link(
            [
                ("mode", "edit_ruleset"),
                ("varname", RuleGroup.StaticChecks(checkgroup)),
                ("host", self._hostname),
            ]
        )
        assert isinstance(rulespec.valuespec, Tuple)
        self._render_rule_reason(
            _("Parameters"),
            url,
            _("Determined by discovery"),
            "",
            False,
            rulespec.valuespec._elements[2].value_to_html(serviceinfo["parameters"]),
        )
        render_labels()

    def _handle_static_origin(
        self,
        serviceinfo: ServiceInfo,
        all_rulesets: AllRulesets,
        rulespec_allow_list: RulespecAllowList | AllowAll,
        service_result: AnalyseServiceResult,
        render_labels: Callable[[], None],
        *,
        debug: bool,
    ) -> None:
        checkgroup = serviceinfo["checkgroup"]
        rulespec = rulespec_registry.get("static_checks:" + checkgroup)
        if rulespec is None or (
            rulespec_allow_list is not None and not rulespec_allow_list.is_visible(rulespec.name)
        ):
            html.write_text_permissive(_("This check is not configurable via Setup"))
            return

        rulespec = rulespec_registry[RuleGroup.StaticChecks(checkgroup)]
        itemspec = rulespec.item_spec
        if itemspec:
            item_text: ValueSpecText | Item = itemspec.value_to_html(serviceinfo["item"])
            assert rulespec.item_spec is not None
            title = rulespec.item_spec.title() or ""
        else:
            item_text = serviceinfo["item"]
            title = _("Item")
        self._render_rule_reason(title, "", "", "", False, item_text)
        self._output_analysed_ruleset(
            all_rulesets,
            rulespec,
            svc_desc_or_item=serviceinfo["item"],
            svc_desc=self._service,
            known_settings=self._PARAMETERS_OMIT,
            service_result=service_result,
            debug=debug,
        )
        assert isinstance(rulespec.valuespec, Tuple)
        html.write_text_permissive(
            rulespec.valuespec._elements[2].value_to_html(serviceinfo["parameters"])
        )
        html.close_td()
        html.close_tr()
        html.close_table()
        render_labels()

    def _handle_active_origin(
        self,
        serviceinfo: ServiceInfo,
        all_rulesets: AllRulesets,
        rulespec_allow_list: RulespecAllowList | AllowAll,
        service_result: AnalyseServiceResult,
        render_labels: Callable[[], None],
        *,
        debug: bool,
    ) -> None:
        checktype = serviceinfo["checktype"]
        rulespec = rulespec_registry[
            (
                "periodic_discovery"
                if checktype == "check-mk-inventory"
                else RuleGroup.ActiveChecks(checktype)
            )
        ]
        if rulespec_allow_list.is_visible(rulespec.name):
            self._output_analysed_ruleset(
                all_rulesets,
                rulespec,
                svc_desc_or_item=None,
                svc_desc=None,
                known_settings=serviceinfo["parameters"],
                service_result=service_result,
                debug=debug,
            )
        self._show_labels(service_result.labels, "service", service_result.label_sources)

    def _handle_classic_origin(
        self,
        serviceinfo: ServiceInfo,
        all_rulesets: AllRulesets,
        _rulespec_allow_list: RulespecAllowList | AllowAll,
        service_result: AnalyseServiceResult,
        render_labels: Callable[[], None],
        *,
        debug: bool,
    ) -> None:
        ruleset = all_rulesets.get("custom_checks")
        assert self._service is not None
        origin_rule_result = self._get_custom_check_origin_rule(
            ruleset, self._hostname, self._service, service_result=service_result, debug=debug
        )
        if origin_rule_result is None:
            raise MKUserError(
                None,
                _("Failed to determine origin rule of %s / %s") % (self._hostname, self._service),
            )
        rule_folder, rule_index, rule = origin_rule_result

        url = folder_preserving_link(
            [("mode", "edit_ruleset"), ("varname", "custom_checks"), ("host", self._hostname)]
        )
        forms.section(HTMLWriter.render_a(_("Command Line"), href=url))
        url = folder_preserving_link(
            [
                ("mode", "edit_rule"),
                ("varname", "custom_checks"),
                ("rule_folder", rule_folder.path()),
                ("rule_id", rule.id),
                ("host", self._hostname),
            ]
        )

        html.open_table(class_="setting")
        html.open_tr()

        html.open_td(class_="reason")
        html.a("%s %d %s %s" % (_("Rule"), rule_index + 1, _("in"), rule_folder.title()), href=url)
        html.close_td()
        html.open_td(class_=["settingvalue", "used"])
        if "command_line" in serviceinfo:
            html.tt(serviceinfo["command_line"])
        else:
            html.write_text_permissive(_("(no command line, passive check)"))
        html.close_td()

        html.close_tr()
        html.close_table()
        render_labels()

    def _get_custom_check_origin_rule(
        self,
        ruleset: Ruleset,
        hostname: str,
        svc_desc: str,
        service_result: AnalyseServiceResult,
        *,
        debug: bool,
    ) -> tuple[Folder, int, Rule] | None:
        # We could use the outcome of _setting instead of the outcome of
        # the automation call in the future
        _setting, rules = ruleset.analyse_ruleset(
            self._hostname,
            svc_desc_or_item=None,
            svc_desc=None,
            service_labels=service_result.labels,
            debug=debug,
        )

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
        html.i(_("Explicit, rule set, discovered"))
        html.close_td()
        html.open_td(class_=["settingvalue", "used"])
        html.write_html(
            cmk.gui.view_utils.render_labels(
                labels, object_type, with_links=False, label_sources=label_sources, request=request
            )
        )
        html.close_td()

        html.close_tr()
        html.close_table()

    def _render_rule_reason(
        self,
        title: str,
        title_url: str,
        reason: str,
        reason_url: str,
        is_default: bool,
        setting: ValueSpecText | Item,
    ) -> None:
        forms.section(HTMLWriter.render_a(title, href=title_url) if title_url else title)

        reason_html: HTML | str = (
            HTMLWriter.render_a(reason, href=reason_url) if reason_url else reason
        )

        html.open_table(class_="setting")
        html.open_tr()
        if is_default:
            html.td(HTMLWriter.render_i(reason_html), class_="reason")
            html.td(setting, class_=["settingvalue", "unused"])
        else:
            html.td(reason_html, class_="reason")
            html.td(setting, class_=["settingvalue", "used"])
        html.close_tr()
        html.close_table()

    def _output_analysed_ruleset(
        self,
        all_rulesets: AllRulesets,
        rulespec: Rulespec,
        svc_desc_or_item: str | None,
        svc_desc: str | None,
        service_result: AnalyseServiceResult | None,
        known_settings: object | None,
        *,
        debug: bool,
    ) -> None:
        if known_settings is None:
            known_settings = self._PARAMETERS_UNKNOWN

        def rule_url(rule: Rule) -> str:
            return folder_preserving_link(
                [
                    ("mode", "edit_rule"),
                    ("varname", varname),
                    ("rule_folder", rule.folder.path()),
                    ("rule_id", rule.id),
                    ("host", self._hostname),
                    (
                        "item",
                        mk_repr(svc_desc_or_item).decode() if svc_desc_or_item else "",
                    ),
                    ("service", mk_repr(svc_desc).decode() if svc_desc else ""),
                ]
            )

        varname = rulespec.name
        valuespec = rulespec.valuespec

        url = folder_preserving_link(
            [
                ("mode", "edit_ruleset"),
                ("varname", varname),
                ("host", self._hostname),
                ("item", mk_repr(svc_desc_or_item).decode()),
                ("service", mk_repr(svc_desc).decode()),
            ]
        )

        forms.section(HTMLWriter.render_a(rulespec.title, url))

        ruleset = all_rulesets.get(varname)
        setting, rules = ruleset.analyse_ruleset(
            self._hostname,
            svc_desc_or_item,
            svc_desc,
            service_labels=service_result.labels if service_result else {},
            debug=debug,
        )

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
            html.span(_("Default value"))
        html.close_td()

        # Show the resulting value or factory setting
        html.open_td(class_=["settingvalue", "used" if len(rules) > 0 else "unused"])

        if isinstance(known_settings, dict) and "tp_computed_params" in known_settings:
            computed_at = known_settings["tp_computed_params"]["computed_at"]
            html.write_text_permissive(
                _("Time specific parameters computed at %s")
                % cmk.utils.render.date_and_time(computed_at)
            )
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
                html.write_text_permissive(valuespec.value_to_html(known_settings))
            except Exception as e:
                if active_config.debug:
                    raise
                html.write_text_permissive(_("Invalid parameter %r: %s") % (known_settings, e))

        elif not rules:  # show the default value
            if rulespec.factory_default is not Rulespec.NO_FACTORY_DEFAULT:
                # If there is a factory default then show that one
                setting = rulespec.factory_default
                html.write_text_permissive(valuespec.value_to_html(setting))

            elif ruleset.match_type() in ("all", "list"):
                # Rulesets that build lists are empty if no rule matches
                html.write_text_permissive(_("(no entry)"))

            else:
                # Else we use the default value of the valuespec
                html.write_text_permissive(valuespec.value_to_html(valuespec.default_value()))

        # We have a setting
        elif ruleset.match_type() == "all":
            if not isinstance(setting, list):
                raise ValueError(f"Expected list, got {setting}")
            html.write_html(
                HTML.without_escaping(", ").join(
                    [valuespec.value_to_html(value) for value in setting]
                )
            )
        else:
            html.write_text_permissive(valuespec.value_to_html(setting))

        html.close_td()
        html.close_tr()
        html.close_table()


def _get_irrelevant_rulesets(service: str | None) -> Container[str]:
    match service:
        case "Check_MK Discovery":
            return {
                # These two are not considered for the discovery service.
                # It has its own ruleset for normal interval, and that is also used
                # for the retry interval.
                RuleGroup.ExtraServiceConf("check_interval"),
                RuleGroup.ExtraServiceConf("retry_interval"),
            }
    return ()
