#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import functools
import os
import traceback
import six

import livestatus

import cmk.gui.crash_reporting as crash_reporting
import cmk.utils.paths
import cmk.utils.profile
import cmk.utils.store

from cmk.gui import config, login, pages, modules, http, htmllib
from cmk.gui.exceptions import (
    MKUserError,
    MKConfigError,
    MKGeneralException,
    MKAuthException,
    MKUnauthenticatedException,
    FinalizeRequest,
    HTTPRedirect,
)
from cmk.gui.globals import html, request, RequestContext, AppContext
from cmk.gui.i18n import _
from cmk.gui.log import logger

# TODO
#  * derive all exceptions from werkzeug's http exceptions.


def _auth(func):
    # Ensure the user is authenticated. This call is wrapping all the different
    # authentication modes the Check_MK GUI supports and initializes the logged
    # in user objects.
    @functools.wraps(func)
    def _call_auth():
        if not login.authenticate(request):
            return _handle_not_authenticated()

        # This may raise an exception with error messages, which will then be displayed to the user.
        _ensure_general_access()

        # Initialize the multisite cmk.gui.i18n. This will be replaced by
        # language settings stored in the user profile after the user
        # has been initialized
        _localize_request()

        # Update the UI theme with the attribute configured by the user
        html.set_theme(config.user.get_attribute("ui_theme"))

        func()

        return html.response

    return _call_auth


def _noauth(func):
    #
    # We don't have to set up anything because we assume this is only used for special calls. We
    # however have to make sure all errors get written out in plaintext, without HTML.
    #
    # Currently these are:
    #  * noauth:run_cron
    #  * noauth:deploy_agent
    #  * noauth:ajax_graph_images
    #  * noauth:automation
    #
    @functools.wraps(func)
    def _call_noauth():
        try:
            func()
        except Exception as e:
            html.write_text("%s" % e)
            if config.debug:
                html.write_text(traceback.format_exc())

        return html.response

    return _call_noauth


def get_and_wrap_page(script_name):
    """Get the page handler and wrap authentication logic when needed.

    For all "noauth" page handlers the wrapping part is skipped. In the `_auth` wrapper
    everything needed to make a logged-in request is listed.
    """
    _handler = pages.get_page_handler(script_name)
    if _handler is None:
        # Some pages do skip authentication. This is done by adding
        # noauth: to the page handler, e.g. "noauth:run_cron" : ...
        # TODO: Eliminate those "noauth:" pages. Eventually replace it by call using
        #       the now existing default automation user.
        _handler = pages.get_page_handler("noauth:" + script_name)
        if _handler is not None:
            return _noauth(_handler)

    if _handler is None:
        return _page_not_found

    return _auth(_handler)


def _plain_error():
    """Webservice functions may decide to get a normal result code
    but a text with an error message in case of an error"""
    return html.request.has_var("_plain_error") or html.myfile == "webapi"


def _profiling_enabled():
    if config.profile is False:
        return False  # Not enabled

    if config.profile == "enable_by_var" and not html.request.has_var("_profile"):
        return False  # Not enabled by HTTP variable

    return True


def _fail_silently():
    """Ajax-Functions want no HTML output in case of an error but
    just a plain server result code of 500"""
    return html.request.has_var("_ajaxid")


def _page_not_found():
    # TODO: This is a page handler. It should not be located in generic application
    # object. Move it to another place
    if html.request.has_var("_plain_error"):
        html.write(_("Page not found"))
    else:
        html.header(_("Page not found"))
        html.show_error(_("This page was not found. Sorry."))
    html.footer()

    return html.response


def _ensure_general_access():
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


def _handle_not_authenticated():
    if _fail_silently():
        # While api call don't show the login dialog
        raise MKUnauthenticatedException(_('You are not authenticated.'))

    # Redirect to the login-dialog with the current url as original target
    # Never render the login form directly when accessing urls like "index.py"
    # or "dashboard.py". This results in strange problems.
    if html.myfile != 'login':
        raise HTTPRedirect('%scheck_mk/login.py?_origtarget=%s' %
                           (config.url_prefix(), html.urlencode(html.makeuri([]))))
    # This either displays the login page or validates the information submitted
    # to the login form. After successful login a http redirect to the originally
    # requested page is performed.
    login_page = login.LoginPage()
    login_page.set_no_html_output(_plain_error())
    login_page.handle_page()

    return html.response


def _load_all_plugins():
    # Optimization: in case of the graph ajax call only check the metrics module. This
    # improves the performance for these requests.
    # TODO: CLEANUP: Move this to the pagehandlers if this concept works out.
    # werkzeug.wrappers.Request.script_root would be helpful here, but we don't have that yet.
    only_modules = ["metrics"] if html.myfile == "ajax_graph" else None
    modules.load_all_plugins(only_modules=only_modules)


def _localize_request():
    previous_language = cmk.gui.i18n.get_current_language()
    user_language = html.request.get_ascii_input("lang", config.user.language)

    html.set_language_cookie(user_language)
    cmk.gui.i18n.localize(user_language)

    # All plugins might have to be reloaded due to a language change. Only trigger
    # a second plugin loading when the user is really using a custom localized GUI.
    # Otherwise the load_all_plugins() at the beginning of the request is sufficient.
    if cmk.gui.i18n.get_current_language() != previous_language:
        _load_all_plugins()


def _render_exception(e, title=""):
    if title:
        title = "%s: " % title

    if _plain_error():
        html.set_output_format("text")
        html.write("%s%s\n" % (title, e))

    elif not _fail_silently():
        html.header(title)
        html.show_error(e)
        html.footer()

    return html.response


def profiling_middleware(func):
    """Wrap an WSGI app in a profiling context manager"""
    def profiler(environ, start_response):
        with cmk.utils.profile.Profile(
                enabled=_profiling_enabled(),
                profile_file=os.path.join(cmk.utils.paths.var_dir, "multisite.profile"),
        ):
            return func(environ, start_response)

    return profiler


class CheckmkApp(object):
    """The Check_MK GUI WSGI entry point"""
    def __init__(self):
        # TODO: Just inline profiling_middleware, getting rid of this useless meta-Kung-Fu.
        self.wsgi_app = profiling_middleware(self._wsgi_app)

    def __call__(self, environ, start_response):
        req = http.Request(environ)
        with AppContext(self), RequestContext(req=req, html_obj=htmllib.html(req)):
            config.initialize()
            html.init_modes()
            return self.wsgi_app(environ, start_response)

    def _wsgi_app(self, environ, start_response):
        """Is called by the WSGI server to serve the current page"""
        with cmk.utils.store.cleanup_locks():
            return _process_request(environ, start_response)


def _process_request(environ, start_response):  # pylint: disable=too-many-branches
    try:
        config.initialize()
        html.init_modes()

        # Make sure all plugins are available as early as possible. At least
        # we need the plugins (i.e. the permissions declared in these) at the
        # time before the first login for generating auth.php.
        _load_all_plugins()

        page_handler = get_and_wrap_page(html.myfile)
        response = page_handler()
        # If page_handler didn't raise we assume everything is OK.
        response.status_code = six.moves.http_client.OK
    except HTTPRedirect as e:
        # This can't be a new Response as it can have already cookies set/deleted by the pages.
        # We can't return the response because the Exception has been raised instead.
        # TODO: Remove all HTTPRedirect exceptions from all pages. Making the Exception a subclass
        #       of Response may also work as it can then be directly returned from here.
        response = html.response
        response.status_code = e.status
        response.headers["Location"] = e.url

    except FinalizeRequest as e:
        # This doesn't seem to serve much purpose anymore.
        # TODO: Remove all FinalizeRequest exceptions from all pages and replace it with a `return`.
        #       It may be necessary to rewire the control-flow a bit as this exception could have
        #       been used to short-circuit some code and jump directly to the response. This
        #       needs to be changed as well.
        response = html.response
        response.status_code = e.status

    except livestatus.MKLivestatusNotFoundError as e:
        response = _render_exception(e, title=_("Data not found"))

    except MKUserError as e:
        response = _render_exception(e, title=_("Invalid user Input"))

    except MKAuthException as e:
        response = _render_exception(e, title=_("Permission denied"))

    except livestatus.MKLivestatusException as e:
        response = _render_exception(e, title=_("Livestatus problem"))
        response.status_code = six.moves.http_client.BAD_GATEWAY

    except MKUnauthenticatedException as e:
        response = _render_exception(e, title=_("Not authenticated"))
        response.status_code = six.moves.http_client.UNAUTHORIZED

    except MKConfigError as e:
        response = _render_exception(e, title=_("Configuration error"))
        logger.error("MKConfigError: %s", e)

    except MKGeneralException as e:
        response = _render_exception(e, title=_("General error"))
        logger.error("MKGeneralException: %s", e)

    except Exception:
        crash_reporting.handle_exception_as_gui_crash_report(_plain_error(), _fail_silently())
        # This needs to be cleaned up.
        response = html.response

    return response(environ, start_response)
