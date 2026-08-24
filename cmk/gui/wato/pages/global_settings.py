#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="type-arg"
# mypy: disable-error-code="unreachable"

"""Editor for global settings in main.mk and modes for these global
settings"""

import abc
import contextlib
from collections.abc import Callable, Collection, Iterable, Iterator, Sequence
from copy import deepcopy
from typing import Any, Final, override

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition
from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config, Config
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.form_specs import (
    DisplayMode,
    get_visitor,
    IncomingData,
    localize,
    parse_data_from_field_id,
    RawDiskData,
    read_data_from_frontend,
    render_form_spec,
    VisitorOptions,
)
from cmk.gui.form_specs.unstable.legacy_converter import resolve_help_text, resolve_title
from cmk.gui.global_config import get_global_config
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.page_menu import (
    get_search_expression,
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
from cmk.gui.pages import PageContext
from cmk.gui.search.matchers import (
    ABCMatchItemGenerator,
    MatchItem,
    MatchItemGeneratorRegistry,
    MatchItems,
)
from cmk.gui.site_config import has_distributed_setup_remote_sites
from cmk.gui.type_defs import ActionResult, GlobalSettings, IconNames, PermissionName, StaticIcon
from cmk.gui.user_sites import activation_sites
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.valuespec import Checkbox, Transform, ValueSpec
from cmk.gui.wato.piggyback_hub import CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_group_registry,
    config_variable_registry,
    ConfigVariable,
    ConfigVariableGroup,
    GlobalSettingsContext,
)
from cmk.gui.watolib.config_domains import (
    ConfigDomainCACertificates,
    ConfigDomainCore,
    finalize_all_settings_per_site,
)
from cmk.gui.watolib.global_settings import (
    add_global_settings_change,
    load_configuration_settings,
    save_global_settings,
    STATIC_PERMISSIONS_GLOBAL_SETTINGS,
)
from cmk.gui.watolib.hosts_and_folders import (
    folder_preserving_link,
    FolderTree,
    make_folder_tree,
)
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.piggyback_hub import validate_piggyback_hub_config
from cmk.gui.watolib.sidebar_reload import sidebar_reload_change_hook
from cmk.gui.watolib.utils import site_neutral_path
from cmk.livestatus_client import SiteConfigurations
from cmk.rulesets.v1.form_specs import BooleanChoice, FormSpec
from cmk.utils.object_diff import make_diff, make_diff_text
from cmk.utils.paths import log_dir, var_dir
from cmk.web.utils import escaping
from cmk.web.utils.flashed_messages import flash
from cmk.web.utils.html import HTML
from cmk.web.utils.urls import makeactionuri, makeuri_contextless


def _masked_value_for_log(
    config_variable: ConfigVariable, context: GlobalSettingsContext, value: object
) -> object:
    value_model = config_variable.value_model(context)
    if isinstance(value_model, FormSpec):
        visitor = get_visitor(
            value_model,
            VisitorOptions(migrate_values=True, mask_values=True),
        )
        return visitor.to_disk(RawDiskData(value))
    return value_model.mask(value)


def _global_settings_diff_text(
    config_variable: ConfigVariable,
    context: GlobalSettingsContext,
    old_settings: GlobalSettings,
    new_settings: GlobalSettings,
) -> str:
    old_masked = {
        varname: _masked_value_for_log(config_variable, context, value)
        for varname, value in old_settings.items()
    }
    new_masked = {
        varname: _masked_value_for_log(config_variable, context, value)
        for varname, value in new_settings.items()
    }

    unmasked_diff = make_diff(old_settings, new_settings)
    masked_diff = make_diff(old_masked, new_masked)

    if unmasked_diff == masked_diff:
        return make_diff_text(old_masked, new_masked)

    return (masked_diff + "\n" if masked_diff else "") + _("Redacted secrets changed.")


def register(
    edition: Edition,
    mode_registry: ModeRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
) -> None:
    mode_registry.register(DefaultModeEditGlobals)
    mode_registry.register(DefaultModeEditGlobalSetting)
    match_item_generator_registry.register(
        MatchItemGeneratorSettings(
            "global_settings",
            _("Global settings"),
            lambda: DefaultModeEditGlobals(
                edition, PageContext(config=active_config, request=request)
            ),
        )
    )


class ABCGlobalSettingsMode(WatoMode):
    def __init__(self, edition: Edition, ctx: PageContext) -> None:
        self._search: None | str = None
        self._show_only_modified = False

        super().__init__(edition, ctx)

        self._default_values = ABCConfigDomain.get_all_default_globals()
        self._global_settings: GlobalSettings = {}
        self._current_settings: dict[str, Any] = {}

    @override
    def _from_vars(self) -> None:
        self._search = get_search_expression()
        self._show_only_modified = (
            request.get_integer_input_mandatory("_show_only_modified", 0) == 1
        )

    @staticmethod
    def _get_groups(show_all: bool) -> Iterable[ConfigVariableGroup]:
        groups = []

        for group in config_variable_group_registry.values():
            add = False
            for config_variable in group.config_variables():
                if not show_all and (
                    not config_variable.in_global_settings()
                    or not config_variable.primary_domain().in_global_settings
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

    def _should_show_config_variable(self, config_variable: ConfigVariable, *, debug: bool) -> bool:
        varname = config_variable.ident()

        if not (domain := config_variable.primary_domain()).enabled():
            return False

        if isinstance(domain, ConfigDomainCore) and varname not in self._default_values:
            if debug:
                raise MKGeneralException(
                    "The configuration variable <tt>%s</tt> is unknown to "
                    "your local Checkmk installation" % varname
                )
            return False

        return config_variable.in_global_settings()

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
            title=_("Show only modified settings"),
            icon_name=StaticIcon(IconNames.toggle_on)
            if self._show_only_modified
            else StaticIcon(IconNames.toggle_off),
            item=make_simple_link(
                makeactionuri(
                    request,
                    transactions.get(),
                    [
                        ("_show_only_modified", "0" if self._show_only_modified else "1"),
                    ],
                )
            ),
        )

    def iter_all_configuration_variables(
        self, *, debug: bool
    ) -> Iterable[tuple[ConfigVariableGroup, Iterable[ConfigVariable]]]:
        yield from (
            (
                group,
                (
                    config_variable
                    for config_variable in group.config_variables()
                    if self._should_show_config_variable(config_variable, debug=debug)
                ),
            )
            for group in sorted(self._groups(), key=lambda g: g.sort_index())
        )

    def _show_configuration_variables(self, config: Config) -> None:
        search = self._search

        at_least_one_painted = False
        html.open_div(class_="globalvars")
        global_config = get_global_config()
        for group, config_variables in self.iter_all_configuration_variables(debug=config.debug):
            header_is_painted = False  # needed for omitting empty groups

            for config_variable in config_variables:
                varname = config_variable.ident()
                context = self.make_global_settings_context(config)
                value_model = config_variable.value_model(context)
                help_text: str | HTML
                if isinstance(value_model, FormSpec):
                    help_text = localize(resolve_help_text(value_model))
                    title_text = localize(resolve_title(value_model))
                else:
                    help_text = value_model.help() or ""
                    title_text = value_model.title() or ""

                if not global_config.global_settings.is_activated(varname):
                    continue

                if self._show_only_modified and varname not in self._current_settings:
                    continue

                if (
                    search
                    and search not in group.title().lower()
                    and search not in config_variable.primary_domain().ident().lower()
                    and search not in varname
                    and search not in help_text.lower()
                    and search not in title_text.lower()
                ):
                    continue  # skip variable when search is performed and nothing matches
                at_least_one_painted = True

                if not header_is_painted:
                    # always open headers when searching
                    forms.header(group.title(), isopen=bool(search) or self._show_only_modified)
                    if warning := group.warning():
                        forms.warning_message(warning)
                    header_is_painted = True

                default_value = self._default_values[varname]

                edit_url = folder_preserving_link(
                    request,
                    [
                        ("mode", self.edit_mode_name),
                        ("varname", varname),
                        ("site", request.var("site", "")),
                    ],
                )
                title = HTMLWriter.render_a(
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

                if varname in self._current_settings:
                    modified_cls = ["modified"]
                    value_title: str | None = _("This option has been modified.")
                elif varname in self._global_settings:
                    modified_cls = ["modified globally"]
                    value_title = _("This option has been modified in the global settings.")
                else:
                    modified_cls = []
                    value_title = None

                if isinstance(value_model, BooleanChoice):
                    forms.section(title, simple=True)
                    _show_toggle_switch(varname, bool(value), modified_cls, value_title)
                    continue

                if isinstance(value_model, FormSpec):
                    forms.section(title, simple=True)
                    html.open_a(href=edit_url, class_=modified_cls, title=value_title)
                    render_form_spec(
                        value_model,
                        f"_vue_gs_{varname}",
                        RawDiskData(value),
                        do_validate=False,
                        display_mode=DisplayMode.READONLY,
                    )
                    html.close_a()
                    continue

                try:
                    to_text = value_model.value_to_html(value)
                except Exception:
                    logger.exception("error converting %(value)r to text", {"value": value})
                    to_text = html.render_error(
                        _("Failed to render value: %(value)r") % {"value": value}
                    )

                # Is this a simple (single) value or not? change styling in these cases...
                simple = True
                if "\n" in to_text or "<td>" in to_text:
                    simple = False
                forms.section(title, simple=simple)

                if is_a_checkbox(value_model):
                    _show_toggle_switch(varname, value, modified_cls, value_title)

                else:
                    html.a(to_text, href=edit_url, class_=modified_cls, title=value_title)

            if header_is_painted:
                forms.end()
        if not at_least_one_painted and search:
            html.show_message(_("Did not find any global setting matching your search."))
        html.close_div()

    @abc.abstractmethod
    def make_global_settings_context(self, config: Config) -> GlobalSettingsContext: ...


class ABCEditGlobalSettingMode(WatoMode):
    def __init__(self, edition: Edition, ctx: PageContext) -> None:
        super().__init__(edition, ctx)
        # Don't call this in _from_vars. make_global_settings_context might rely on the object
        # being fully initialized.
        context = self.make_global_settings_context(active_config)
        self._value_model: ValueSpec | FormSpec[Any] = self._config_variable.value_model(context)

    @override
    def _from_vars(self) -> None:
        self._varname = request.get_ascii_input_mandatory("varname")
        try:
            self._config_variable = config_variable_registry[self._varname]
        except KeyError:
            raise MKUserError(
                "varname",
                _('The global setting "%(varname)s" does not exist.') % {"varname": self._varname},
            )

        if not self._may_edit_configvar(self._varname):
            raise MKAuthException(_("You are not permitted to edit this global setting."))

        self._current_settings = dict(load_configuration_settings())
        self._global_settings: GlobalSettings = {}

    def _may_edit_configvar(self, varname: str) -> bool:
        if not get_global_config().global_settings.is_activated(varname):
            return False
        if varname in ["actions"]:
            return user.may("wato.add_or_modify_executables")
        return True

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
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
                icon_name=StaticIcon(IconNames.reset),
                item=make_confirmed_form_submit_link(
                    form_name="value_editor",
                    button_name="_reset",
                    title=_("Reset configuration variable to default value"),
                    confirm_button=_("Reset"),
                ),
                is_enabled=reset_possible,
                is_shortcut=True,
                is_suggested=True,
            )
        )

        return menu

    @override
    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        current = self._current_settings.get(self._varname)
        old_settings: GlobalSettings = (
            {self._varname: current} if self._varname in self._current_settings else {}
        )
        new_value: Any = None
        if request.var("_reset"):
            if not transactions.check_transaction(request):
                return None

            if self._varname == CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT:
                default_settings = ABCConfigDomain.get_all_default_globals()
                self._validate_update_piggyback_hub_config(
                    default_settings[self._varname],
                    default_settings,
                    config.sites,
                )

            with contextlib.suppress(KeyError):
                del self._current_settings[self._varname]

            msg = HTML.with_escaping(
                _("Resetted configuration variable %(varname)s to its default.")
                % {"varname": self._varname}
            )
            new_settings: GlobalSettings = {}
        else:
            new_value = self._parse_submitted_value()

            if self._varname == CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT:
                self._validate_update_piggyback_hub_config(
                    new_value, ABCConfigDomain.get_all_default_globals(), config.sites
                )

            self._current_settings[self._varname] = new_value
            msg = HTML.with_escaping(
                _("Changed global configuration variable %(varname)s.") % {"varname": self._varname}
            )
            new_settings = {self._varname: new_value}

        self._save(
            make_folder_tree(config),
            pprint_value=config.wato_pprint_config,
            use_git=config.wato_use_git,
            liveproxyd_enabled=config.liveproxyd_enabled,
        )
        if new_value and self._varname == "trusted_certificate_authorities":
            ConfigDomainCACertificates.log_changes(current, new_value)

        add_global_settings_change(
            self._config_variable,
            text=msg,
            sites=self._affected_sites(),
            pending_changes=_pending_changes(
                config.sites,
                use_git=config.wato_use_git,
                local_site=omd_site(),
                user_id=user.id,
            ),
            diff_text=_global_settings_diff_text(
                self._config_variable,
                self.make_global_settings_context(config),
                old_settings,
                new_settings,
            ),
        )

        if (
            self.name() == "edit_site_configvar"
            and not has_distributed_setup_remote_sites(config.sites)
            and not self._current_settings
        ):
            return redirect(mode_url("sites"))

        return redirect(self._back_url())

    def _validate_update_piggyback_hub_config(
        self, new_value: bool, default_settings: GlobalSettings, site_configs: SiteConfigurations
    ) -> None:
        site_specific_settings = {
            site_id: deepcopy(site_conf.get("globals", {}))
            for site_id, site_conf in site_configs.items()
        }
        global_settings = dict(deepcopy(self._global_settings))
        if (sites := self._affected_sites()) is not None:
            for site_id in sites:
                site_specific_settings[site_id][self._varname] = new_value
        else:
            global_settings[self._varname] = new_value

        validate_piggyback_hub_config(
            site_configs,
            finalize_all_settings_per_site(
                default_settings, global_settings, site_specific_settings
            ),
        )

    @abc.abstractmethod
    def _back_url(self) -> str:
        raise NotImplementedError

    def _save(
        self, tree: FolderTree, *, pprint_value: bool, use_git: bool, liveproxyd_enabled: bool
    ) -> None:
        save_global_settings(self._current_settings)

    @abc.abstractmethod
    def _affected_sites(self) -> Sequence[SiteId] | None:
        raise NotImplementedError

    def _is_configured(self) -> bool:
        return self._varname in self._current_settings

    def _vue_field_id(self) -> str:
        # Note: this _underscore is critical because of the hidden vars special behaviour
        # Non _ vars are always added as hidden vars into a form
        return "_vue_global_settings"

    def _title(self) -> str:
        if isinstance(self._value_model, FormSpec):
            return localize(resolve_title(self._value_model))
        title = self._value_model.title()
        assert isinstance(title, str)
        return title

    def _parse_submitted_value(self) -> object:
        if isinstance(self._value_model, FormSpec):
            return parse_data_from_field_id(self._value_model, self._vue_field_id())
        new_value = self._value_model.from_html_vars("ve")
        self._value_model.validate_value(new_value, "ve")
        return new_value

    def _render_editable_value(self, value: object) -> None:
        if isinstance(self._value_model, FormSpec):
            if request.has_var(self._vue_field_id()):
                value_incoming: IncomingData = read_data_from_frontend(self._vue_field_id())
            else:
                value_incoming = RawDiskData(value)
            render_form_spec(
                self._value_model, self._vue_field_id(), value_incoming, do_validate=True
            )
            return
        self._value_model.render_input("ve", value)
        self._value_model.set_focus("ve")
        html.help(self._value_model.help())

    def _render_readonly_value(self, field_id: str, value: object) -> None:
        if isinstance(self._value_model, FormSpec):
            render_form_spec(
                self._value_model,
                field_id,
                RawDiskData(value),
                do_validate=False,
                display_mode=DisplayMode.READONLY,
            )
            return
        html.write_text_permissive(self._value_model.value_to_html(value))

    @override
    def page(self, config: Config) -> None:
        is_configured = self._is_configured()
        is_configured_globally = self._varname in self._global_settings

        default_values = ABCConfigDomain.get_all_default_globals()

        defvalue = default_values[self._varname]
        value = self._current_settings.get(
            self._varname, self._global_settings.get(self._varname, defvalue)
        )
        domain_hint = self._config_variable.domain_hint()

        if domain_hint:
            html.show_warning(domain_hint)
        hint = self._config_variable.hint()
        if hint:
            html.show_warning(hint)

        with html.form_context("value_editor", method="POST"):
            forms.header(self._title())
            if not config.wato_hide_varnames:
                forms.section(_("Configuration variable:"))
                html.tt(self._varname)

            forms.section(_("Current setting"))
            self._render_editable_value(value)

            if is_configured_globally:
                self._show_global_setting()

            forms.section(_("Factory setting"))
            self._render_readonly_value("_vue_global_settings_factory", defvalue)

            forms.section(_("Current state"))
            if is_configured_globally:
                html.write_text_permissive(
                    _('This variable is configured in <a href="%(url)s">Global settings</a>.')
                    % {"url": "wato.py?mode=edit_configvar&varname=%s" % self._varname}
                )
            elif not is_configured:
                html.write_text_permissive(_("This variable is at factory settings."))
            else:
                curvalue = self._current_settings[self._varname]
                if is_configured_globally and curvalue == self._global_settings[self._varname]:
                    html.write_text_permissive(_("Site setting and global setting are identical."))
                elif curvalue == defvalue:
                    html.write_text_permissive(
                        _("Your setting and factory settings are identical.")
                    )
                else:
                    self._render_readonly_value("_vue_global_settings_current", curvalue)

            forms.end()
            html.hidden_fields()

    def _show_global_setting(self) -> None:
        pass

    @abc.abstractmethod
    def make_global_settings_context(self, config: Config) -> GlobalSettingsContext: ...


class ModeEditGlobals(ABCGlobalSettingsMode):
    @classmethod
    @override
    def name(cls) -> str:
        return "globalvars"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return STATIC_PERMISSIONS_GLOBAL_SETTINGS

    def __init__(
        self,
        edition: Edition,
        ctx: PageContext,
        page_menu_dropdowns_postprocess: Callable[
            [Sequence[PageMenuDropdown]], list[PageMenuDropdown]
        ],
    ) -> None:
        super().__init__(edition, ctx)
        self._current_settings = dict(load_configuration_settings())
        self._page_menu_dropdowns_postprocess = page_menu_dropdowns_postprocess

    @override
    def title(self) -> str:
        if self._search:
            return _("Global settings matching '%(search)s'") % {"search": self._search}
        return _("Global settings")

    @override
    def page_menu(self, config: Config, breadcrumb: Breadcrumb) -> PageMenu:
        dropdowns = []

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

        dropdowns = self._page_menu_dropdowns_postprocess(dropdowns)

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
            icon_name=StaticIcon(IconNames.sites),
            item=make_simple_link("wato.py?mode=sites"),
        )

    @override
    def action(self, config: Config) -> ActionResult:
        check_csrf_token()

        varname = request.var("_varname")
        if not varname:
            return None

        action = request.var("_action")

        config_variable = config_variable_registry[varname]
        def_value = self._default_values[varname]

        if not transactions.check_transaction(request):
            return None

        old_settings: GlobalSettings = (
            {varname: self._current_settings[varname]} if varname in self._current_settings else {}
        )
        if varname in self._current_settings:
            self._current_settings[varname] = not self._current_settings[varname]
        else:
            self._current_settings[varname] = not def_value
        msg = _("Changed global configuration variable %(varname)s.") % {"varname": varname}
        save_global_settings(self._current_settings)

        add_global_settings_change(
            config_variable,
            text=msg,
            sites=None,
            pending_changes=_pending_changes(
                config.sites,
                use_git=config.wato_use_git,
                local_site=omd_site(),
                user_id=user.id,
            ),
            diff_text=_global_settings_diff_text(
                config_variable,
                self.make_global_settings_context(config),
                old_settings,
                {varname: self._current_settings[varname]},
            ),
        )

        if action == "_reset":
            flash(msg)
        return redirect(mode_url("globalvars"))

    @override
    def page(self, config: Config) -> None:
        self._show_configuration_variables(config)

    @override
    def make_global_settings_context(self, config: Config) -> GlobalSettingsContext:
        return make_global_settings_context(self._edition, omd_site(), config)


class DefaultModeEditGlobals(ModeEditGlobals):
    def __init__(self, edition: Edition, ctx: PageContext) -> None:
        super().__init__(edition, ctx, list)


class ModeEditGlobalSetting(ABCEditGlobalSettingMode):
    @classmethod
    @override
    def name(cls) -> str:
        return "edit_configvar"

    @staticmethod
    @override
    def static_permissions() -> Collection[PermissionName]:
        return STATIC_PERMISSIONS_GLOBAL_SETTINGS

    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditGlobals

    @override
    def title(self) -> str:
        return _("Edit global setting")

    @override
    def _affected_sites(self) -> Sequence[SiteId] | None:
        return None  # All sites

    @override
    def _back_url(self) -> str:
        return ModeEditGlobals.mode_url()

    @override
    def make_global_settings_context(self, config: Config) -> GlobalSettingsContext:
        return make_global_settings_context(self._edition, omd_site(), config)


class DefaultModeEditGlobalSetting(ModeEditGlobalSetting):
    @classmethod
    @override
    def parent_mode(cls) -> type[WatoMode] | None:
        return DefaultModeEditGlobals


def _show_toggle_switch(
    varname: str, value: bool, modified_cls: list[str], value_title: str | None
) -> None:
    html.open_div(class_=["toggle_switch_container"] + modified_cls + (["on"] if value else []))
    html.toggle_switch(
        enabled=value,
        help_txt=(value_title + " " if value_title else "") + _("Click to toggle this setting"),
        href=makeactionuri(
            request,
            transactions.get(),
            [("_action", "toggle"), ("_varname", varname)],
        ),
        class_=[*modified_cls, "large"],
    )
    html.close_div()


def is_a_checkbox(vs: ValueSpec) -> bool:
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
        create_mode: Callable[[], ABCGlobalSettingsMode],
    ) -> None:
        super().__init__(name, provider="setup")
        self._topic: Final[str] = topic
        self._create_mode: Final = create_mode

    def _config_variable_to_match_item(
        self,
        config_variable: ConfigVariable,
        edit_mode_name: str,
        global_settings_context: GlobalSettingsContext,
    ) -> MatchItem:
        value_model = config_variable.value_model(global_settings_context)
        if isinstance(value_model, FormSpec):
            title = localize(resolve_title(value_model)) or _("Untitled setting")
        else:
            title = value_model.title() or _("Untitled setting")
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

    @override
    def generate_match_items(self, user_permissions: UserPermissions) -> MatchItems:
        mode = self._create_mode()
        yield from (
            self._config_variable_to_match_item(
                config_variable,
                mode.edit_mode_name,
                mode.make_global_settings_context(active_config),
            )
            for _group, config_variables in mode.iter_all_configuration_variables(
                debug=active_config.debug
            )
            for config_variable in config_variables
        )

    @staticmethod
    @override
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    @override
    def is_localization_dependent(self) -> bool:
        return True


def make_global_settings_context(
    edition: Edition, target_site_id: SiteId, config: Config
) -> GlobalSettingsContext:
    return GlobalSettingsContext(
        target_site_id=target_site_id,
        edition_of_local_site=edition,
        site_neutral_log_dir=site_neutral_path(log_dir),
        site_neutral_var_dir=site_neutral_path(var_dir),
        configured_sites=config.sites,
        configured_graph_timeranges=config.graph_timeranges,
    )


def _pending_changes(
    sites: SiteConfigurations,
    *,
    use_git: bool,
    local_site: SiteId,
    user_id: UserId | None,
) -> PendingChanges:
    return PendingChanges(
        activation_sites=activation_sites(sites),
        local_site=local_site,
        acting_user=user_id,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=use_git),
            sidebar_reload_change_hook,
            index_update_change_hook,
        ),
    )
