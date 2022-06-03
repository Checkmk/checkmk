#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Page user can change several aspects of it's own profile"""

import time
import abc
import json
from typing import Iterator, List, Optional, Union
from cmk.utils.type_defs import UserId

import cmk.gui.i18n
import cmk.gui.sites
import cmk.gui.userdb as userdb
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
import cmk.gui.login as login

from cmk.gui.breadcrumb import make_simple_page_breadcrumb
from cmk.gui.main_menu import mega_menu_registry
from cmk.gui.type_defs import MegaMenu, TopicMenuItem, TopicMenuTopic
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.config import SiteId, SiteConfiguration
from cmk.gui.plugins.userdb.htpasswd import hash_password
from cmk.gui.plugins.userdb.utils import get_user_attributes_by_topic
from cmk.gui.plugins.wato.utils.base_modes import redirect
from cmk.gui.exceptions import (MKUserError, MKGeneralException, MKAuthException, FinalizeRequest)
from cmk.gui.i18n import _, _l, _u
from cmk.gui.globals import html, request
from cmk.gui.pages import page_registry, AjaxPage, AjaxPageResult, Page
from cmk.gui.page_menu import (
    PageMenu,
    PageMenuDropdown,
    PageMenuTopic,
    PageMenuEntry,
    make_simple_link,
    make_simple_form_page_menu,
)

from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.utils.flashed_messages import flash, get_flashed_messages
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.activate_changes import ACTIVATION_TIME_PROFILE_SYNC
from cmk.gui.wato.pages.users import select_language

from cmk.gui.watolib.global_settings import rulebased_notifications_enabled
from cmk.gui.watolib.user_profile import push_user_profiles_to_site_transitional_wrapper


def _get_current_theme_titel() -> str:
    return [titel for theme_id, titel in config.theme_choices() if theme_id == html.get_theme()][0]


def _get_sidebar_position() -> str:
    assert config.user.id is not None
    sidebar_position = userdb.load_custom_attr(config.user.id, 'ui_sidebar_position', lambda x: None
                                               if x == "None" else "left")

    return sidebar_position or "right"


def _sidebar_position_title(stored_value: str) -> str:
    return _("Left") if stored_value == "left" else _("Right")


def _sidebar_position_id(stored_value: str) -> str:
    return "left" if stored_value == "left" else "right"


def _user_menu_topics() -> List[TopicMenuTopic]:
    quick_items = [
        TopicMenuItem(
            name="ui_theme",
            title=_("Interface theme"),
            url="javascript:cmk.sidebar.toggle_user_attribute(\"ajax_ui_theme.py\")",
            target="",
            sort_index=10,
            icon="color_mode",
            button_title=_get_current_theme_titel(),
        ),
        TopicMenuItem(
            name="sidebar_position",
            title=_("Sidebar position"),
            url="javascript:cmk.sidebar.toggle_user_attribute(\"ajax_sidebar_position.py\")",
            target="",
            sort_index=20,
            icon="sidebar_position",
            button_title=_sidebar_position_title(_get_sidebar_position()),
        ),
    ]

    items = [
        TopicMenuItem(
            name="change_password",
            title=_("Change password"),
            url="user_change_pw.py",
            sort_index=10,
            icon="topic_change_password",
        ),
        TopicMenuItem(
            name="user_profile",
            title=_("Edit profile"),
            url="user_profile.py",
            sort_index=20,
            icon="topic_profile",
        ),
        TopicMenuItem(
            name="logout",
            title=_("Logout"),
            url="logout.py",
            sort_index=30,
            icon="sidebar_logout",
        ),
    ]

    if rulebased_notifications_enabled() and config.user.may('general.edit_notifications'):
        items.insert(
            1,
            TopicMenuItem(
                name="notification_rules",
                title=_("Notification rules"),
                url="wato.py?mode=user_notifications_p",
                sort_index=30,
                icon="topic_events",
            ))

    return [
        TopicMenuTopic(
            name="user",
            title=_("Quick toggle"),
            # TODO(rb): set correct icon
            icon="topic_profile",
            items=quick_items,
        ),
        TopicMenuTopic(
            name="user",
            title=_("Profile"),
            icon="topic_profile",
            items=items,
        )
    ]


mega_menu_registry.register(
    MegaMenu(name="user",
             title=_l("User"),
             icon="main_user",
             sort_index=20,
             topics=_user_menu_topics,
             info_line=lambda: f"{config.user.id} ({config.user.baserole_id})"))


@page_registry.register_page("ajax_ui_theme")
class ModeAjaxCycleThemes(AjaxPage):
    """AJAX handler for quick access option 'Interface theme" in user menu"""
    def page(self) -> AjaxPageResult:
        check_csrf_token()
        themes = [theme for theme, _title in cmk.gui.config.theme_choices()]
        current_theme = html.get_theme()
        try:
            theme_index = themes.index(current_theme)
        except ValueError:
            raise MKUserError(None, _("Could not determine current theme."))

        if len(themes) == theme_index + 1:
            new_theme = themes[0]
        else:
            new_theme = themes[theme_index + 1]

        _set_user_attribute("ui_theme", new_theme)
        return {}


@page_registry.register_page("ajax_sidebar_position")
class ModeAjaxCycleSidebarPosition(AjaxPage):
    """AJAX handler for quick access option 'Sidebar position" in user menu"""
    def page(self) -> AjaxPageResult:
        check_csrf_token()
        _set_user_attribute(
            "ui_sidebar_position",
            None if _sidebar_position_id(_get_sidebar_position()) == "left" else "left")
        return {}


@page_registry.register_page("ajax_set_dashboard_start_url")
class ModeAjaxSetStartURL(AjaxPage):
    """AJAX handler to set the start URL of a user to a dashboard"""
    def page(self) -> AjaxPageResult:
        check_csrf_token()
        try:
            name = html.request.get_str_input_mandatory("name")
            url = makeuri_contextless(request, [("name", name)], "dashboard.py")
            cmk.gui.utils.validate_start_url(url, "")
            _set_user_attribute("start_url", repr(url))
        except Exception:
            raise MKUserError(None, _("Failed to set start URL"))
        return {}


def _set_user_attribute(key: str, value: Optional[str]):
    assert config.user.id is not None
    user_id = config.user.id

    if value is None:
        userdb.remove_custom_attr(user_id, key)
    else:
        userdb.save_custom_attr(user_id, key, value)


def user_profile_async_replication_page(back_url: str) -> None:
    sites = list(config.user.authorized_login_sites().keys())
    user_profile_async_replication_dialog(sites=sites, back_url=back_url)

    html.footer()


def user_profile_async_replication_dialog(sites: List[SiteId], back_url: str) -> None:
    html.p(
        _('In order to activate your changes available on all remote sites, your user profile needs '
          'to be replicated to the remote sites. This is done on this page now. Each site '
          'is being represented by a single image which is first shown gray and then fills '
          'to green during synchronisation.'))

    html.h3(_('Replication States'))
    html.open_div(id_="profile_repl")
    num_replsites = 0
    for site_id in sites:
        site = config.sites[site_id]
        if "secret" not in site:
            status_txt = _('Not logged in.')
            start_sync = False
            icon = 'repl_locked'
        else:
            status_txt = _('Waiting for replication to start')
            start_sync = True
            icon = 'repl_pending'

        html.open_div(class_="site", id_="site-%s" % site_id)
        html.div("", title=status_txt, class_=["icon", "repl_status", icon])
        if start_sync:
            changes_manager = watolib.ActivateChanges()
            changes_manager.load()
            estimated_duration = changes_manager.get_activation_time(site_id,
                                                                     ACTIVATION_TIME_PROFILE_SYNC,
                                                                     2.0)
            html.javascript('cmk.profile_replication.start(%s, %d, %s);' %
                            (json.dumps(site_id), int(estimated_duration * 1000.0),
                             json.dumps(_('Replication in progress'))))
            num_replsites += 1
        else:
            _add_profile_replication_change(site_id, status_txt)
        html.span(site.get('alias', site_id))

        html.close_div()

    html.javascript('cmk.profile_replication.prepare(%d, %s);\n' %
                    (num_replsites, json.dumps(back_url)))

    html.close_div()


def _add_profile_replication_change(site_id: SiteId, result: Union[bool, str]) -> None:
    """Add pending change entry to make sync possible later for admins"""
    add_change("edit-users",
               _('Profile changed (sync failed: %s)') % result,
               sites=[site_id],
               need_restart=False)


class ABCUserProfilePage(Page):
    @abc.abstractmethod
    def _page_title(self) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def _action(self) -> None:
        raise NotImplementedError()

    @abc.abstractmethod
    def _show_form(self) -> None:
        raise NotImplementedError()

    def __init__(self, permission: str) -> None:
        super().__init__()
        self._verify_requirements(permission)

    @staticmethod
    def _verify_requirements(permission: str) -> None:
        if not config.user.id:
            raise MKUserError(None, _('Not logged in.'))

        if not config.user.may(permission):
            raise MKAuthException(_("You are not allowed to edit your user profile."))

        if not config.wato_enabled:
            raise MKAuthException(_('User profiles can not be edited (WATO is disabled).'))

    def _page_menu(self, breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(_("Profile"),
                                          breadcrumb,
                                          form_name="profile",
                                          button_name="_save")
        menu.dropdowns.insert(1, page_menu_dropdown_user_related(html.myfile))
        return menu

    def page(self) -> None:
        title = self._page_title()
        breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_user(), title)
        html.header(title, breadcrumb, self._page_menu(breadcrumb))

        if html.request.has_var('_save') and html.check_transaction():
            try:
                self._action()
            except MKUserError as e:
                html.add_user_error(e.varname, e)

        for message in get_flashed_messages():
            html.show_message(message)

        if html.has_user_errors():
            html.show_user_errors()

        self._show_form()


@page_registry.register_page("user_profile_replicate")
class UserProfileReplicate(Page):
    def __init__(self) -> None:
        super().__init__()

        if not config.user.id:
            raise MKUserError(None, _('Not logged in.'))

        if (not config.user.may("general.change_password") and
                not config.user.may("general.edit_profile")):
            raise MKAuthException(_("You are not allowed to edit your user profile."))

        if not config.wato_enabled:
            raise MKAuthException(_('User profiles can not be edited (WATO is disabled).'))

    def _page_menu(self, breadcrumb) -> PageMenu:
        menu = make_simple_form_page_menu(_("Profile"),
                                          breadcrumb,
                                          form_name="profile",
                                          button_name="_save")
        menu.dropdowns.insert(1, page_menu_dropdown_user_related(html.myfile))
        return menu

    def page(self) -> None:
        title = _('Replicate user profile')
        breadcrumb = make_simple_page_breadcrumb(mega_menu_registry.menu_user(), title)
        html.header(title, breadcrumb, self._page_menu(breadcrumb))

        for message in get_flashed_messages():
            html.show_message(message)

        # Now, if in distributed environment where users can login to remote sites, set the trigger for
        # pushing the new user profile to the remote sites asynchronously
        user_profile_async_replication_page(back_url=html.get_url_input("back", "user_profile.py"))


@page_registry.register_page("user_change_pw")
class UserChangePasswordPage(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Change password")

    def __init__(self) -> None:
        super().__init__("general.change_password")

    def _action(self) -> None:
        assert config.user.id is not None

        users = userdb.load_users(lock=True)
        user = users[config.user.id]

        cur_password = html.request.get_str_input_mandatory('cur_password')
        password = html.request.get_str_input_mandatory('password')
        password2 = html.request.get_str_input_mandatory('password2', '')

        # Force change pw mode
        if not cur_password:
            raise MKUserError("cur_password", _("You need to provide your current password."))

        if not password:
            raise MKUserError("password", _("You need to change your password."))

        if cur_password == password:
            raise MKUserError("password", _("The new password must differ from your current one."))

        if userdb.check_credentials(config.user.id, cur_password) is False:
            raise MKUserError("cur_password", _("Your old password is wrong."))

        if password2 and password != password2:
            raise MKUserError("password2", _("The both new passwords do not match."))

        watolib.verify_password_policy(password)
        user['password'] = hash_password(password)
        user['last_pw_change'] = int(time.time())

        # In case the user was enforced to change it's password, remove the flag
        try:
            del user['enforce_pw_change']
        except KeyError:
            pass

        # Increase serial to invalidate old authentication cookies
        if 'serial' not in user:
            user['serial'] = 1
        else:
            user['serial'] += 1

        userdb.save_users(users)

        flash(_("Successfully changed password."))

        # Set the new cookie to prevent logout for the current user
        login.update_auth_cookie(config.user.id)

        # In distributed setups with remote sites where the user can login, start the
        # user profile replication now which will redirect the user to the destination
        # page after completion. Otherwise directly open up the destination page.
        origtarget = html.request.get_str_input_mandatory('_origtarget', 'user_change_pw.py')
        if config.user.authorized_login_sites():
            raise redirect(
                makeuri_contextless(request, [("back", origtarget)],
                                    filename="user_profile_replicate.py"))
        raise redirect(origtarget)

    def _show_form(self) -> None:
        assert config.user.id is not None

        users = userdb.load_users()

        change_reason = html.request.get_ascii_input('reason')

        if change_reason == 'expired':
            html.p(_('Your password is too old, you need to choose a new password.'))
        elif change_reason == 'enforced':
            html.p(_('You are required to change your password before proceeding.'))

        user = users.get(config.user.id)
        if user is None:
            html.show_warning(_("Sorry, your user account does not exist."))
            html.footer()
            return

        locked_attributes = userdb.locked_attributes(user.get('connector'))
        if "password" in locked_attributes:
            raise MKUserError(
                "cur_password",
                _("You can not change your password, because it is "
                  "managed by another system."))

        html.begin_form("profile", method="POST")
        html.prevent_password_auto_completion()
        html.open_div(class_="wato")
        forms.header(self._page_title())

        forms.section(_("Current Password"))
        html.password_input('cur_password', autocomplete="new-password")

        forms.section(_("New Password"))
        html.password_input('password', autocomplete="new-password")

        forms.section(_("New Password Confirmation"))
        html.password_input('password2', autocomplete="new-password")

        forms.end()
        html.close_div()
        html.hidden_fields()
        html.end_form()
        html.footer()


@page_registry.register_page("user_profile")
class UserProfile(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Edit profile")

    def __init__(self) -> None:
        super().__init__("general.edit_profile")

    def _action(self) -> None:
        assert config.user.id is not None

        users = userdb.load_users(lock=True)
        user = users[config.user.id]

        language = html.request.get_ascii_input_mandatory('language', "")
        # Set the users language if requested to set it explicitly
        if language != "_default_":
            user['language'] = language
            config.user.language = language
            html.set_language_cookie(language)

        else:
            if 'language' in user:
                del user['language']
            config.user.reset_language()

        # load the new language
        cmk.gui.i18n.localize(config.user.language)

        if config.user.may('general.edit_notifications') and user.get("notifications_enabled"):
            value = forms.get_input(watolib.get_vs_flexible_notifications(), "notification_method")
            user["notification_method"] = value

        # Custom attributes
        if config.user.may('general.edit_user_attributes'):
            for name, attr in userdb.get_user_attributes():
                if not attr.user_editable():
                    continue

                if attr.permission() and not config.user.may(attr.permission()):
                    continue

                vs = attr.valuespec()
                value = vs.from_html_vars('ua_' + name)
                vs.validate_value(value, "ua_" + name)
                user[name] = value

        userdb.save_users(users)

        flash(_("Successfully updated user profile."))

        # In distributed setups with remote sites where the user can login, start the
        # user profile replication now which will redirect the user to the destination
        # page after completion. Otherwise directly open up the destination page.
        if config.user.authorized_login_sites():
            back_url = "user_profile_replicate.py?back=user_profile.py"
        else:
            back_url = "user_profile.py"

        # Ensure theme changes are applied without additional user interaction
        html.reload_whole_page(back_url)
        html.footer()

        raise FinalizeRequest(code=200)

    def _show_form(self) -> None:
        assert config.user.id is not None

        users = userdb.load_users()

        user = users.get(config.user.id)
        if user is None:
            html.show_warning(_("Sorry, your user account does not exist."))
            html.footer()
            return

        html.begin_form("profile", method="POST")
        html.prevent_password_auto_completion()
        html.open_div(class_="wato")
        forms.header(_("Personal settings"))

        forms.section(_("Name"), simple=True)
        html.write_text(user.get("alias", config.user.id))

        select_language(user)

        # Let the user configure how he wants to be notified
        rulebased_notifications = rulebased_notifications_enabled()
        if (not rulebased_notifications and config.user.may('general.edit_notifications') and
                user.get("notifications_enabled")):
            forms.section(_("Notifications"))
            html.help(
                _("Here you can configure how you want to be notified about host and service problems and "
                  "other monitoring events."))
            watolib.get_vs_flexible_notifications().render_input("notification_method",
                                                                 user.get("notification_method"))

        if config.user.may('general.edit_user_attributes'):
            custom_user_attr_topics = get_user_attributes_by_topic()
            _show_custom_user_attr(user, custom_user_attr_topics.get("personal", []))
            forms.header(_("User interface settings"))
            _show_custom_user_attr(user, custom_user_attr_topics.get("interface", []))

        forms.end()
        html.close_div()
        html.hidden_fields()
        html.end_form()
        html.footer()


def _show_custom_user_attr(user, custom_attr):
    for name, attr in custom_attr:
        if attr.user_editable():
            vs = attr.valuespec()
            forms.section(_u(vs.title()))
            value = user.get(name, vs.default_value())
            if not attr.permission() or config.user.may(attr.permission()):
                vs.render_input("ua_" + name, value)
                html.help(_u(vs.help()))
            else:
                html.write(vs.value_to_text(value))


@page_registry.register_page("wato_ajax_profile_repl")
class ModeAjaxProfileReplication(AjaxPage):
    """AJAX handler for asynchronous replication of user profiles (changed passwords)"""
    def page(self):
        check_csrf_token()
        ajax_request = self.webapi_request()

        site_id_val = ajax_request.get("site")
        if not site_id_val:
            raise MKUserError(None, "The site_id is missing")
        site_id = site_id_val
        if site_id not in config.sitenames():
            raise MKUserError(None, _("The requested site does not exist"))

        status = cmk.gui.sites.states().get(site_id,
                                            cmk.gui.sites.SiteStatus({})).get("state", "unknown")
        if status == "dead":
            raise MKGeneralException(_('The site is marked as dead. Not trying to replicate.'))

        site = config.site(site_id)
        assert config.user.id is not None
        result = self._synchronize_profile(site_id, site, config.user.id)

        if result is not True:
            assert result is not False
            _add_profile_replication_change(site_id, result)
            raise MKGeneralException(result)

        return _("Replication completed successfully.")

    def _synchronize_profile(self, site_id: SiteId, site: SiteConfiguration,
                             user_id: UserId) -> Union[bool, str]:
        users = userdb.load_users(lock=False)
        if user_id not in users:
            raise MKUserError(None, _('The requested user does not exist'))

        start = time.time()
        result = push_user_profiles_to_site_transitional_wrapper(site, {user_id: users[user_id]})

        duration = time.time() - start
        watolib.ActivateChanges().update_activation_time(site_id, ACTIVATION_TIME_PROFILE_SYNC,
                                                         duration)
        return result


def page_menu_dropdown_user_related(page_name: str) -> PageMenuDropdown:
    return PageMenuDropdown(
        name="related",
        title=_("Related"),
        topics=[
            PageMenuTopic(
                title=_("User"),
                entries=list(_page_menu_entries_related(page_name)),
            ),
        ],
    )


def _page_menu_entries_related(page_name: str) -> Iterator[PageMenuEntry]:
    if page_name != "user_change_pw":
        yield PageMenuEntry(
            title=_("Change password"),
            icon_name="topic_change_password",
            item=make_simple_link("user_change_pw.py"),
        )

    if page_name != "user_profile":
        yield PageMenuEntry(
            title=_("Edit profile"),
            icon_name="topic_profile",
            item=make_simple_link("user_profile.py"),
        )

    if page_name != "user_notifications_p" and rulebased_notifications_enabled(
    ) and config.user.may('general.edit_notifications'):
        yield PageMenuEntry(
            title=_("Notification rules"),
            icon_name="topic_events",
            item=make_simple_link("wato.py?mode=user_notifications_p"),
        )
