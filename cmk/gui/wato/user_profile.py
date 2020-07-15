#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Page user can change several aspects of it's own profile"""

import time
import abc
from typing import List, Union
from cmk.utils.type_defs import UserId

import cmk.gui.i18n
import cmk.gui.sites
import cmk.gui.userdb as userdb
import cmk.gui.config as config
import cmk.gui.watolib as watolib
import cmk.gui.forms as forms
import cmk.gui.login as login
from cmk.gui.breadcrumb import Breadcrumb, BreadcrumbItem
from cmk.gui.plugins.main_menu.mega_menus import (
    make_main_menu_breadcrumb,
    MegaMenuUser,
)
from cmk.gui.config import SiteId, SiteConfiguration
from cmk.gui.plugins.userdb.htpasswd import hash_password
from cmk.gui.exceptions import HTTPRedirect, MKUserError, MKGeneralException, MKAuthException
from cmk.gui.i18n import _, _u
from cmk.gui.globals import html
from cmk.gui.pages import page_registry, AjaxPage, Page

from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.activate_changes import ACTIVATION_TIME_PROFILE_SYNC
from cmk.gui.wato.pages.users import select_language

from cmk.gui.watolib.global_settings import rulebased_notifications_enabled
from cmk.gui.watolib.user_profile import push_user_profiles_to_site_transitional_wrapper


def user_profile_async_replication_page() -> None:
    html.header(_('Replicate new User Profile'))

    html.begin_context_buttons()
    html.context_button(_('User Profile'), 'user_profile.py', 'back')
    html.end_context_buttons()

    sites = list(config.user.authorized_login_sites().keys())
    user_profile_async_replication_dialog(sites=sites)

    html.footer()


def user_profile_async_replication_dialog(sites: List[SiteId]) -> None:
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
            html.javascript(
                'cmk.profile_replication.start(\'%s\', %d, \'%s\');' %
                (site_id, int(estimated_duration * 1000.0), _('Replication in progress')))
            num_replsites += 1
        else:
            _add_profile_replication_change(site_id, status_txt)
        html.span(site.get('alias', site_id))

        html.close_div()

    html.javascript('cmk.profile_replication.prepare(%d);\n' % num_replsites)

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
    def _action(self) -> bool:
        raise NotImplementedError()

    @abc.abstractmethod
    def _show_form(self, profile_changed: bool) -> None:
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

    def page(self) -> None:
        watolib.init_wato_datastructures(with_wato_lock=True)

        profile_changed = False
        if html.request.has_var('_save') and html.check_transaction():
            try:
                profile_changed = self._action()
            except MKUserError as e:
                html.add_user_error(e.varname, e)

        # Now, if in distributed environment where users can login to remote sites, set the trigger for
        # pushing the new user profile to the remote sites asynchronously
        if profile_changed and config.user.authorized_login_sites():
            user_profile_async_replication_page()
            return

        self._show_form(profile_changed)


@page_registry.register_page("user_change_pw")
class UserChangePasswordPage(ABCUserProfilePage):
    def _page_title(self) -> str:
        return _("Change password")

    def __init__(self) -> None:
        super().__init__("general.change_password")

    def _action(self) -> bool:
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

        if userdb.hook_login(config.user.id, cur_password) is False:
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

        # Set the new cookie to prevent logout for the current user
        login.set_auth_cookie(config.user.id)

        return True

    def _show_form(self, profile_changed: bool) -> None:
        assert config.user.id is not None

        users = userdb.load_users()

        breadcrumb = make_main_menu_breadcrumb(MegaMenuUser) + Breadcrumb(
            [BreadcrumbItem(title=self._page_title(), url=html.makeuri([]))])
        html.header(self._page_title(), breadcrumb)

        change_reason = html.request.get_ascii_input('reason')

        if change_reason == 'expired':
            html.p(_('Your password is too old, you need to choose a new password.'))
        elif change_reason == 'enforced':
            html.p(_('You are required to change your password before proceeding.'))

        if profile_changed:
            html.show_message(_("Your password has been changed."))
            if change_reason:
                raise HTTPRedirect(html.request.get_str_input_mandatory('_origtarget', 'index.py'))

        if html.has_user_errors():
            html.show_user_errors()

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
        html.button("_save", _("Save"))
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

    def _action(self) -> bool:
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

        return True

    def _show_form(self, profile_changed: bool) -> None:
        assert config.user.id is not None

        users = userdb.load_users()

        breadcrumb = make_main_menu_breadcrumb(MegaMenuUser) + Breadcrumb(
            [BreadcrumbItem(title=self._page_title(), url=html.makeuri([]))])
        html.header(self._page_title(), breadcrumb)

        self._show_context_buttons()

        if profile_changed:
            html.reload_sidebar()
            html.show_message(_("Successfully updated user profile."))
            # Ensure theme changes are applied without additional user interaction
            html.immediate_browser_redirect(0.5, html.makeuri([]))

        if html.has_user_errors():
            html.show_user_errors()

        user = users.get(config.user.id)
        if user is None:
            html.show_warning(_("Sorry, your user account does not exist."))
            html.footer()
            return

        html.begin_form("profile", method="POST")
        html.prevent_password_auto_completion()
        html.open_div(class_="wato")
        forms.header(self._page_title())

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
            for name, attr in userdb.get_user_attributes():
                if attr.user_editable():
                    vs = attr.valuespec()
                    forms.section(_u(vs.title()))
                    value = user.get(name, vs.default_value())
                    if not attr.permission() or config.user.may(attr.permission()):
                        vs.render_input("ua_" + name, value)
                        html.help(_u(vs.help()))
                    else:
                        html.write(vs.value_to_text(value))

        forms.end()
        html.button("_save", _("Save"))
        html.close_div()
        html.hidden_fields()
        html.end_form()
        html.footer()

    def _show_context_buttons(self) -> None:
        rulebased_notifications = rulebased_notifications_enabled()
        if rulebased_notifications and config.user.may('general.edit_notifications'):
            html.begin_context_buttons()
            url = "wato.py?mode=user_notifications_p"
            html.context_button(_("Notifications"), url, "notifications")
            html.end_context_buttons()


@page_registry.register_page("wato_ajax_profile_repl")
class ModeAjaxProfileReplication(AjaxPage):
    """AJAX handler for asynchronous replication of user profiles (changed passwords)"""
    def page(self):
        request = self.webapi_request()

        site_id_val = request.get("site")
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
