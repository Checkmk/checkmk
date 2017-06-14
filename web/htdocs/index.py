#!/usr/bin/python
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

from mod_python import apache
import sys, os, pprint, __builtin__
import traceback

import i18n
import sites
import livestatus
import modules
import userdb
import config
import login
from lib import *
import log
from html_mod_python import html_mod_python, FinalizeRequest
import cmk.paths

# Main entry point for all HTTP-requests (called directly by mod_apache)
def handler(mod_python_req, fields = None, is_profiling = False):
    # Create an object that contains all data about the request and
    # helper functions for creating valid HTML. Parse URI and
    # store results in the request object for later usage.
    __builtin__.html = html_mod_python(mod_python_req, fields)

    response_code = apache.OK
    try:
        config.initialize()
        init_profiling(is_profiling)
        html.init_modes()

        # Make sure all plugins are avaiable as early as possible. At least
        # we need the plugins (i.e. the permissions declared in these) at the
        # time before the first login for generating auth.php.
        modules.load_all_plugins()

        # Get page handler.
        handler = modules.get_handler(html.myfile, page_not_found)

        # Some pages do skip authentication. This is done by adding
        # noauth: to the page hander, e.g. "noauth:run_cron" : ...
        # TODO: Eliminate those "noauth:" pages. Eventually replace it by call using
        #       the now existing default automation user.
        if handler == page_not_found:
            handler = modules.get_handler("noauth:" + html.myfile, page_not_found)
            if handler != page_not_found:
                try:
                    handler()
                except Exception, e:
                    html.write_text("%s" % e)
                    if config.debug:
                        html.write_text(traceback.format_exc())
                raise FinalizeRequest()

        # Ensure the user is authenticated. This call is wrapping all the different
        # authentication modes the Check_MK GUI supports and initializes the logged
        # in user objects.
        if not login.authenticate(mod_python_req):
            handle_not_authenticated()

        # Initialize the multiste i18n. This will be replaced by
        # language settings stored in the user profile after the user
        # has been initialized
        previous_language = i18n.get_current_language()
        i18n.localize(html.var("lang", config.user.language()))

        # All plugins might have to be reloaded due to a language change. Only trigger
        # a second plugin loading when the user is really using a custom localized GUI.
        # Otherwise the load_all_plugins() at the beginning of the request is sufficient.
        if i18n.get_current_language() != previous_language:
            modules.load_all_plugins()

        ensure_general_access()
        handler()

    except FinalizeRequest, e:
        response_code = e.status

    except (MKUserError, MKAuthException, MKUnauthenticatedException, MKConfigError, MKGeneralException,
            livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusException), e:

        html.unplug_all()

        ty = type(e)
        if ty == livestatus.MKLivestatusNotFoundError:
            title       = _("Data not found")
            plain_title = _("Livestatus-data not found")
        elif isinstance(e, livestatus.MKLivestatusException):
            title       = _("Livestatus problem")
            plain_title = _("Livestatus problem")
        else:
            title       = e.title()
            plain_title = e.plain_title()

        if plain_error():
            html.set_output_format("text")
            html.write("%s: %s\n" % (plain_title, e))
        elif not fail_silently():
            html.header(title)
            html.show_error(e)
            html.footer()


        # Some exception need to set a specific HTTP status code
        if ty == MKUnauthenticatedException:
            response_code = apache.HTTP_UNAUTHORIZED
        elif ty == livestatus.MKLivestatusException:
            response_code = apache.HTTP_BAD_GATEWAY

        if ty in [MKConfigError, MKGeneralException]:
            log.logger.error(_("%s: %s") % (plain_title, e))

    except (apache.SERVER_RETURN,
            (apache.SERVER_RETURN, apache.HTTP_UNAUTHORIZED),
            (apache.SERVER_RETURN, apache.HTTP_MOVED_TEMPORARILY)):
        raise

    except Exception, e:
        html.unplug_all()
        log_exception()
        if plain_error():
            html.set_output_format("text")
            html.write(_("Internal error") + ": %s\n" % e)
        elif not fail_silently():
            modules.get_handler("gui_crash")()
        response_code = apache.OK

    finally:
        try:
            finalize_request()
        except:
            log_exception()
            raise

    return response_code


def handle_not_authenticated():
    if fail_silently():
        # While api call don't show the login dialog
        raise MKUnauthenticatedException(_('You are not authenticated.'))

    # Redirect to the login-dialog with the current url as original target
    # Never render the login form directly when accessing urls like "index.py"
    # or "dashboard.py". This results in strange problems.
    if html.myfile != 'login':
        html.http_redirect('%scheck_mk/login.py?_origtarget=%s' %
                           (config.url_prefix(), html.urlencode(html.makeuri([]))))
    else:
        # This either displays the login page or validates the information submitted
        # to the login form. After successful login a http redirect to the originally
        # requested page is performed.
        login.page_login(plain_error())

    raise FinalizeRequest()


def ensure_general_access():
    if config.user.may("general.use"):
        return

    reason = [ _("You are not authorized to use the Check_MK GUI. Sorry. "
               "You are logged in as <b>%s</b>.") % config.user.id ]

    if config.user.role_ids:
        reason.append(_("Your roles are <b>%s</b>.") % ", ".join(config.user.role_ids))
    else:
        reason.append(_("<b>You do not have any roles.</b>"))

    reason.append(_("If you think this is an error, please ask your administrator "
                    "to check the permissions configuration."))

    if login.auth_type == 'cookie':
        reason.append(_("<p>You have been logged out. Please reload the page "
                        "to re-authenticate.</p>"))
        login.del_auth_cookie()

    raise MKAuthException(" ".join(reason))


def finalize_request():
    release_all_locks()
    userdb.finalize()
    sites.disconnect()
    html.finalize()


# Ajax-Functions want no HTML output in case of an error but
# just a plain server result code of 500
def fail_silently():
    return html.has_var("_ajaxid")


# Webservice functions may decide to get a normal result code
# but a text with an error message in case of an error
def plain_error():
    return html.has_var("_plain_error") or html.myfile == "webapi"


def page_not_found():
    if html.has_var("_plain_error"):
        html.write(_("Page not found"))
    else:
        html.header(_("Page not found"))
        html.show_error(_("This page was not found. Sorry."))
    html.footer()


# prepare local-structure within OMD sites
# TODO FIXME: Still needed?
def init_sys_path():
    local_module_path = cmk.paths.omd_root + "/local/share/check_mk/web/htdocs"
    if local_module_path not in sys.path:
        sys.path[0:0] = [ local_module_path, cmk.paths.web_dir + "/htdocs" ]


def init_profiling(is_profiling):
    if not is_profiling and config.profile:
        import cProfile

        # Ubuntu: install python-profiler when using this feature
        profile_file = cmk.paths.var_dir + "/multisite.profile"

        p = cProfile.Profile()
        p.runcall(handler, html.req, html.fields, True)
        p.dump_stats(profile_file)

        file(profile_file + ".py", "w").write(
            "#!/usr/bin/env python\n"
            "import pstats\n"
            "stats = pstats.Stats(%r)\n"
            "stats.sort_stats('time').print_stats()\n" % profile_file)
        os.chmod(profile_file + ".py", 0755)

        raise FinalizeRequest()


# Early initialization upon first start of the application by the server
def initialize():
    init_sys_path()
    log.init_logging()
    modules.init_modules()


# Run the global application initialization code here. It is called
# only once during the startup of the application server.
initialize()
