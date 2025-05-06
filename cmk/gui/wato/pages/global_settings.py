#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Editor for global settings in main.mk and modes for these global
settings"""

import abc
from collections.abc import Callable, Collection, Iterable, Iterator, Sequence
from copy import deepcopy
from typing import Any, Final

from cmk.ccc.exceptions import MKGeneralException

import cmk.gui.watolib.changes as _changes
from cmk.gui import forms
from cmk.gui.breadcrumb import Breadcrumb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKAuthException, MKUserError
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
from cmk.gui.site_config import configured_sites
from cmk.gui.type_defs import ActionResult, GlobalSettings, PermissionName
from cmk.gui.utils import escaping
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.utils.flashed_messages import flash
from cmk.gui.utils.html import HTML
from cmk.gui.utils.transaction_manager import transactions
from cmk.gui.utils.urls import makeactionuri, makeuri_contextless
from cmk.gui.valuespec import Checkbox, Transform, ValueSpec
from cmk.gui.wato.piggyback_hub import CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_variable_group_registry,
    config_variable_registry,
    ConfigVariable,
    ConfigVariableGroup,
)
from cmk.gui.watolib.config_domains import (
    ConfigDomainCACertificates,
    ConfigDomainCore,
    finalize_all_settings_per_site,
)
from cmk.gui.watolib.global_settings import load_configuration_settings, save_global_settings
from cmk.gui.watolib.hosts_and_folders import folder_preserving_link
from cmk.gui.watolib.mode import mode_url, ModeRegistry, redirect, WatoMode
from cmk.gui.watolib.piggyback_hub import validate_piggyback_hub_config
from cmk.gui.watolib.search import (
    ABCMatchItemGenerator,
    MatchItem,
    MatchItemGeneratorRegistry,
    MatchItems,
)


def register(
    mode_registry: ModeRegistry,
    match_item_generator_registry: MatchItemGeneratorRegistry,
) -> None:
    mode_registry.register(DefaultModeEditGlobals)
    mode_registry.register(DefaultModeEditGlobalSetting)
    match_item_generator_registry.register(
        MatchItemGeneratorSettings(
            "global_settings",
            _("Global settings"),
            DefaultModeEditGlobals,
        )
    )


class ABCGlobalSettingsMode(WatoMode):
    def __init__(self) -> None:
        self._search: None | str = None
        self._show_only_modified = False

        super().__init__()

        self._default_values = ABCConfigDomain.get_all_default_globals()
        self._global_settings: GlobalSettings = {}
        self._current_settings: dict[str, Any] = {}

    def _from_vars(self):
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

        if not (domain := config_variable.domain()).enabled():
            return False

        if isinstance(domain, ConfigDomainCore) and varname not in self._default_values:
            if active_config.debug:
                raise MKGeneralException(
                    "The configuration variable <tt>%s</tt> is unknown to "
                    "your local Checkmk installation" % varname
                )
            return False

        if not config_variable.in_global_settings():
            return False

        return True

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
            icon_name="toggle_on" if self._show_only_modified else "toggle_off",
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

    def iter_all_configuration_variables(
        self,
    ) -> Iterable[tuple[ConfigVariableGroup, Iterable[ConfigVariable]]]:
        yield from (
            (
                group,
                (
                    config_variable
                    for config_variable in group.config_variables()
                    if self._should_show_config_variable(config_variable)
                ),
            )
            for group in sorted(self._groups(), key=lambda g: g.sort_index())
        )

    def _show_configuration_variables(self) -> None:
        search = self._search

        at_least_one_painted = False
        html.open_div(class_="globalvars")
        global_config = get_global_config()
        for group, config_variables in self.iter_all_configuration_variables():
            header_is_painted = False  # needed for omitting empty groups

            for config_variable in config_variables:
                varname = config_variable.ident()
                valuespec = config_variable.valuespec()

                if not global_config.global_settings.is_activated(varname):
                    continue

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
                    forms.header(group.title(), isopen=bool(search) or self._show_only_modified)
                    if warning := group.warning():
                        forms.warning_message(warning)
                    header_is_painted = True

                default_value = self._default_values[varname]

                edit_url = folder_preserving_link(
                    [
                        ("mode", self.edit_mode_name),
                        ("varname", varname),
                        ("site", request.var("site", "")),
                    ]
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
                    modified_cls = ["modified"]
                    value_title: str | None = _("This option has been modified.")
                elif varname in self._global_settings:
                    modified_cls = ["modified globally"]
                    value_title = _("This option has been modified in global settings.")
                else:
                    modified_cls = []
                    value_title = None

                if is_a_checkbox(valuespec):
                    html.open_div(
                        class_=["toggle_switch_container"]
                        + modified_cls
                        + (["on"] if value else [])
                    )
                    html.toggle_switch(
                        enabled=value,
                        help_txt=(value_title + " " if value_title else "")
                        + _("Click to toggle this setting"),
                        href=makeactionuri(
                            request, transactions, [("_action", "toggle"), ("_varname", varname)]
                        ),
                        class_=[*modified_cls, "large"],
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
            self._config_variable = config_variable_registry[self._varname]
            self._valuespec = self._config_variable.valuespec()
        except KeyError:
            raise MKUserError(
                "varname", _('The global setting "%s" does not exist.') % self._varname
            )

        if not self._may_edit_configvar(self._varname):
            raise MKAuthException(_("You are not permitted to edit this global setting."))

        self._current_settings = dict(load_configuration_settings())
        self._global_settings: GlobalSettings = {}

    def _may_edit_configvar(self, varname):
        if not get_global_config().global_settings.is_activated(varname):
            return False
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
                    title=_("Reset configuration variable to default value"),
                    confirm_button=_("Reset"),
                ),
                is_enabled=reset_possible,
                is_shortcut=True,
                is_suggested=True,
            )
        )

        return menu

    def action(self) -> ActionResult:
        check_csrf_token()

        current = self._current_settings.get(self._varname)
        new_value = None
        if request.var("_reset"):
            if not transactions.check_transaction():
                return None

            if self._varname == CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT:
                default_settings = ABCConfigDomain.get_all_default_globals()
                self._validate_update_piggyback_hub_config(
                    default_settings[self._varname], default_settings
                )

            try:
                del self._current_settings[self._varname]
            except KeyError:
                pass

            msg = HTML.with_escaping(
                _("Resetted configuration variable %s to its default.") % self._varname
            )
        else:
            new_value = self._valuespec.from_html_vars("ve")
            self._valuespec.validate_value(new_value, "ve")

            if self._varname == CONFIG_VARIABLE_PIGGYBACK_HUB_IDENT:
                self._validate_update_piggyback_hub_config(
                    new_value, ABCConfigDomain.get_all_default_globals()
                )

            self._current_settings[self._varname] = new_value
            msg = HTML.without_escaping(
                _("Changed global configuration variable %s to %s.")
                % (
                    escaping.escape_attribute(self._varname),
                    self._valuespec.value_to_html(new_value),
                )
            )

        self._save()
        if new_value and self._varname == "trusted_certificate_authorities":
            ConfigDomainCACertificates.log_changes(current, new_value)

        _changes.add_change(
            action_name="edit-configvar",
            text=msg,
            user_id=user.id,
            sites=self._affected_sites(),
            domains=[(domain := self._config_variable.domain())],
            need_restart=self._config_variable.need_restart(),
            need_apache_reload=self._config_variable.need_apache_reload(),
            domain_settings={
                domain.ident(): {"need_apache_reload": self._config_variable.need_apache_reload()}
            },
            use_git=active_config.wato_use_git,
        )

        return redirect(self._back_url())

    def _validate_update_piggyback_hub_config(
        self, new_value: bool, default_settings: GlobalSettings
    ) -> None:
        site_specific_settings = {
            site_id: deepcopy(site_conf.get("globals", {}))
            for site_id, site_conf in configured_sites().items()
        }
        global_settings = dict(deepcopy(self._global_settings))
        if (sites := self._affected_sites()) is not None:
            for site_id in sites:
                site_specific_settings[site_id][self._varname] = new_value
        else:
            global_settings[self._varname] = new_value

        validate_piggyback_hub_config(
            finalize_all_settings_per_site(
                default_settings, global_settings, site_specific_settings
            )
        )

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

    def _vue_field_id(self):
        # Note: this _underscore is critical because of the hidden vars special behaviour
        # Non _ vars are always added as hidden vars into a form
        return "_vue_global_settings"

    def page(self) -> None:
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
            html.write_text_permissive(self._valuespec.value_to_html(defvalue))

            forms.section(_("Current state"))
            if is_configured_globally:
                html.write_text_permissive(
                    _('This variable is configured in <a href="%s">global settings</a>.')
                    % ("wato.py?mode=edit_configvar&varname=%s" % self._varname)
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
                    html.write_text_permissive(self._valuespec.value_to_html(curvalue))

            forms.end()
            html.hidden_fields()

    def _show_global_setting(self):
        pass


class ModeEditGlobals(ABCGlobalSettingsMode):
    @classmethod
    def name(cls) -> str:
        return "globalvars"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["global"]

    def __init__(
        self,
        page_menu_dropdowns_postprocess: Callable[
            [Sequence[PageMenuDropdown]], list[PageMenuDropdown]
        ],
    ) -> None:
        super().__init__()
        self._current_settings = dict(load_configuration_settings())
        self._page_menu_dropdowns_postprocess = page_menu_dropdowns_postprocess

    def title(self) -> str:
        if self._search:
            return _("Global settings matching '%s'") % self._search
        return _("Global settings")

    def page_menu(self, breadcrumb: Breadcrumb) -> PageMenu:
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
            icon_name="sites",
            item=make_simple_link("wato.py?mode=sites"),
        )

    def action(self) -> ActionResult:
        varname = request.var("_varname")
        if not varname:
            return None

        action = request.var("_action")

        config_variable = config_variable_registry[varname]
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
            action_name="edit-configvar",
            text=msg,
            user_id=user.id,
            domains=[(domain := config_variable.domain())],
            need_restart=config_variable.need_restart(),
            need_apache_reload=config_variable.need_apache_reload(),
            domain_settings={
                domain.ident(): {"need_apache_reload": config_variable.need_apache_reload()}
            },
            use_git=active_config.wato_use_git,
        )

        if action == "_reset":
            flash(msg)
        return redirect(mode_url("globalvars"))

    def page(self) -> None:
        self._show_configuration_variables()


class DefaultModeEditGlobals(ModeEditGlobals):
    def __init__(self) -> None:
        super().__init__(list)


class ModeEditGlobalSetting(ABCEditGlobalSettingMode):
    @classmethod
    def name(cls) -> str:
        return "edit_configvar"

    @staticmethod
    def static_permissions() -> Collection[PermissionName]:
        return ["global"]

    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return ModeEditGlobals

    def title(self) -> str:
        return _("Edit global setting")

    def _affected_sites(self):
        return None  # All sites

    def _back_url(self) -> str:
        return ModeEditGlobals.mode_url()


class DefaultModeEditGlobalSetting(ModeEditGlobalSetting):
    @classmethod
    def parent_mode(cls) -> type[WatoMode] | None:
        return DefaultModeEditGlobals


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
        mode_class: type[ABCGlobalSettingsMode],
    ) -> None:
        super().__init__(name)
        self._topic: Final[str] = topic
        self._mode_class: Final[type[ABCGlobalSettingsMode]] = mode_class

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
