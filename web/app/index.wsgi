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

import httplib
import os
import traceback

import livestatus

import cmk.utils.paths
import cmk.utils.store as store
import cmk.utils.profile

import cmk.gui.i18n
import cmk.gui.config as config
import cmk.gui.modules as modules
import cmk.gui.pages as pages
import cmk.gui.login as login
import cmk.gui.log as log
import cmk.gui.htmllib
import cmk.gui.http
import cmk.gui.globals
from cmk.gui.log import logger
from cmk.gui.i18n import _
from cmk.gui.globals import AppContext, RequestContext, html

from cmk.gui.exceptions import (
    MKUserError,
    MKConfigError,
    MKGeneralException,
    MKAuthException,
    MKUnauthenticatedException,
    FinalizeRequest,
    HTTPRedirect,
)


class Application(object):
    """The Check_MK GUI WSGI entry point"""
    def __init__(self, environ, start_response):
        self._environ = environ
        self._start_response = start_response
        self._request = cmk.gui.http.Request(environ)
        self._response = cmk.gui.http.Response(is_secure=self._request.is_ssl_request)
        with AppContext(self), \
             RequestContext(cmk.gui.htmllib.html(self._request, self._response)):
            self._process_request()

    def _process_request(self):
        try:
            config.initialize()

            with cmk.utils.profile.Profile(enabled=self._profiling_enabled(),
                                           profile_file=os.path.join(cmk.utils.paths.var_dir,
                                                                     "multisite.profile")):
                self._handle_request()

        except HTTPRedirect as e:
            self._response.status_code = e.status
            self._response.headers["Location"] = e.url

        except FinalizeRequest as e:
            self._response.status_code = e.status

        except (livestatus.MKLivestatusNotFoundError, MKUserError, MKAuthException) as e:
            self._render_exception(e)

        except livestatus.MKLivestatusException as e:
            self._render_exception(e)
            self._response.status_code = httplib.BAD_GATEWAY

        except MKUnauthenticatedException as e:
            self._render_exception(e)
            self._response.status_code = httplib.UNAUTHORIZED

        except (MKConfigError, MKGeneralException) as e:
            self._render_exception(e)
            logger.error("%s: %s", e.plain_title(), e)

        except Exception as e:
            logger.exception("error processing WSGI request")
            if self._plain_error():
                html.set_output_format("text")
                html.write(_("Internal error") + ": %s\n" % e)
            elif not self._fail_silently():
                crash_handler = pages.get_page_handler("gui_crash")
                if not crash_handler:
                    raise
                crash_handler()

        finally:
            try:
                # TODO: Nuke this and use context managers only for locking!
                store.release_all_locks()
            except:
                logger.exception("error releasing locks after WSGI request")
                raise

    def _render_exception(self, e):
        if self._plain_error():
            html.set_output_format("text")
            html.write("%s: %s\n" % (e.plain_title(), e))
        elif not self._fail_silently():
            html.header(e.title())
            html.show_error(e)
            html.footer()

    def _handle_request(self):
        html.init_modes()

        # Make sure all plugins are avaiable as early as possible. At least
        # we need the plugins (i.e. the permissions declared in these) at the
        # time before the first login for generating auth.php.
        self._load_all_plugins()

        handler = pages.get_page_handler(html.myfile, self._page_not_found)

        # Some pages do skip authentication. This is done by adding
        # noauth: to the page hander, e.g. "noauth:run_cron" : ...
        # TODO: Eliminate those "noauth:" pages. Eventually replace it by call using
        #       the now existing default automation user.
        if handler == self._page_not_found:
            handler = pages.get_page_handler("noauth:" + html.myfile, self._page_not_found)
            if handler != self._page_not_found:
                try:
                    handler()
                except Exception as e:
                    self._show_exception_info(e)
                raise FinalizeRequest(httplib.OK)

        # Ensure the user is authenticated. This call is wrapping all the different
        # authentication modes the Check_MK GUI supports and initializes the logged
        # in user objects.
        if not login.authenticate(self._request):
            self._handle_not_authenticated()

        # Initialize the multiste cmk.gui.i18n. This will be replaced by
        # language settings stored in the user profile after the user
        # has been initialized
        self._localize_request()

        # Update the UI theme with the attribute configured by the user
        html.set_theme(config.user.get_attribute("ui_theme"))

        self._ensure_general_access()
        handler()

    def _load_all_plugins(self):
        # Optimization: in case of the graph ajax call only check the metrics module. This
        # improves the performance for these requests.
        # TODO: CLEANUP: Move this to the pagehandlers if this concept works out.
        # werkzeug.wrappers.Request.script_root would be helpful here, but we don't have that yet.
        only_modules = ["metrics"] if html.myfile == "ajax_graph" else None
        modules.load_all_plugins(only_modules=only_modules)

    def _show_exception_info(self, e):
        html.write_text("%s" % e)
        if config.debug:
            html.write_text(traceback.format_exc())

    def _handle_not_authenticated(self):
        if self._fail_silently():
            # While api call don't show the login dialog
            raise MKUnauthenticatedException(_('You are not authenticated.'))

        # Redirect to the login-dialog with the current url as original target
        # Never render the login form directly when accessing urls like "index.py"
        # or "dashboard.py". This results in strange problems.
        if html.myfile != 'login':
            raise HTTPRedirect('%scheck_mk/login.py?_origtarget=%s' %
                               (config.url_prefix(), html.urlencode(html.makeuri([]))))
        else:
            # This either displays the login page or validates the information submitted
            # to the login form. After successful login a http redirect to the originally
            # requested page is performed.
            login_page = login.LoginPage()
            login_page.set_no_html_output(self._plain_error())
            login_page.handle_page()

        raise FinalizeRequest(httplib.OK)

    def _localize_request(self):
        previous_language = cmk.gui.i18n.get_current_language()
        user_language = html.get_ascii_input("lang", config.user.language())

        html.set_language_cookie(user_language)
        cmk.gui.i18n.localize(user_language)

        # All plugins might have to be reloaded due to a language change. Only trigger
        # a second plugin loading when the user is really using a custom localized GUI.
        # Otherwise the load_all_plugins() at the beginning of the request is sufficient.
        if cmk.gui.i18n.get_current_language() != previous_language:
            self._load_all_plugins()

    def _fail_silently(self):
        """Ajax-Functions want no HTML output in case of an error but
        just a plain server result code of 500"""
        return html.request.has_var("_ajaxid")

    def _plain_error(self):
        """Webservice functions may decide to get a normal result code
        but a text with an error message in case of an error"""
        return html.request.has_var("_plain_error") or html.myfile == "webapi"

    def _profiling_enabled(self):
        if config.profile is False:
            return False  # Not enabled

        if config.profile == "enable_by_var" and not html.request.has_var("_profile"):
            return False  # Not enabled by HTTP variable

        return True

    # TODO: This is a page handler. It should not be located in generic application
    # object. Move it to another place
    def _page_not_found(self):
        if html.request.has_var("_plain_error"):
            html.write(_("Page not found"))
        else:
            html.header(_("Page not found"))
            html.show_error(_("This page was not found. Sorry."))
        html.footer()

    def _ensure_general_access(self):
        if config.user.may("general.use"):
            return

        reason = [
            _("You are not authorized to use the Check_MK GUI. Sorry. "
              "You are logged in as <b>%s</b>.") % config.user.id
        ]

        if config.user.role_ids:
            reason.append(_("Your roles are <b>%s</b>.") % ", ".join(config.user.role_ids))
        else:
            reason.append(_("<b>You do not have any roles.</b>"))

        reason.append(
            _("If you think this is an error, please ask your administrator "
              "to check the permissions configuration."))

        if login.auth_type == 'cookie':
            reason.append(
                _("<p>You have been logged out. Please reload the page "
                  "to re-authenticate.</p>"))
            login.del_auth_cookie()

        raise MKAuthException(" ".join(reason))

    def __iter__(self):
        """Is called by the WSGI server to serve the current page"""
        return self._response(self._environ, self._start_response)


# Early initialization upon first start of the application by the server
def _initialize():
    log.init_logging()
    modules.init_modules()


# Run the global application initialization code here. It is called
# only once during the startup of the application server.
_initialize()
