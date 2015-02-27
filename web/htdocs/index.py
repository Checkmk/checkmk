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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.


# Prepare builtin-scope for localization function _()
import __builtin__
__builtin__._ = lambda x: x
__builtin__.current_language = None

# Load modules
from mod_python import apache
import sys, os, pprint
from lib import *
import livestatus
import defaults, config, login, userdb, hooks, visuals, default_permissions

if os.path.exists(os.path.dirname(os.path.abspath(__file__)) + '/reporting.py'):
    import reporting
else:
    reporting = None

from html_mod_python import *

# Load page handlers
pagehandlers = {}
pagehandlers_dir = defaults.web_dir + "/plugins/pages"
for fn in os.listdir(pagehandlers_dir):
    if fn.endswith(".py"):
        execfile(pagehandlers_dir + "/" + fn)

# prepare local-structure within OMD sites
if defaults.omd_root:
    local_module_path = defaults.omd_root + "/local/share/check_mk/web/htdocs"
    local_locale_path = defaults.omd_root + "/local/share/check_mk/locale"
    if local_module_path not in sys.path:
        sys.path[0:0] = [ local_module_path, defaults.web_dir + "/htdocs" ]
    local_pagehandlers_dir = defaults.omd_root + "/local/share/check_mk/web/plugins/pages"
    if os.path.exists(local_pagehandlers_dir):
        for fn in os.listdir(local_pagehandlers_dir):
            if fn.endswith(".py"):
                execfile(local_pagehandlers_dir + "/" + fn)


# Call the load_plugins() function in all modules
def load_all_plugins():
    for module in [ hooks, userdb, visuals, views, metrics, sidebar, dashboard,
                    wato, bi, mobile, notify, webapi, reporting, cron ]:
        try:
            module.load_plugins # just check if this function exists
        except AttributeError:
            pass
        else:
            module.load_plugins()


__builtin__.load_all_plugins = load_all_plugins

# Main entry point for all HTTP-requests (called directly by mod_apache)
def handler(req, fields = None, profiling = True):
    req.content_type = "text/html; charset=UTF-8"
    req.header_sent = False

    # Create an object that contains all data about the request and
    # helper functions for creating valid HTML. Parse URI and
    # store results in the request object for later usage.
    html = html_mod_python(req, fields)
    html.enable_debug = config.debug
    html.id = {} # create unique ID for this request
    __builtin__.html = html
    response_code = apache.OK

    try:

        # Ajax-Functions want no HTML output in case of an error but
        # just a plain server result code of 500
        fail_silently = html.has_var("_ajaxid")

        # Webservice functions may decide to get a normal result code
        # but a text with an error message in case of an error
        plain_error = html.has_var("_plain_error")

        config.load_config() # load multisite.mk
        if html.var("debug"): # Debug flag may be set via URL
            config.debug = True

        if html.var("screenshotmode") or config.screenshotmode: # Omit fancy background, make it white
            html.screenshotmode = True

        html.enable_debug = config.debug
        html.set_buffering(config.buffered_http_stream)

        # profiling can be enabled in multisite.mk
        if profiling and config.profile:
            import cProfile # , pstats, sys, StringIO, tempfile
            # the profiler looses the memory about all modules. We need to hand over
            # the request object in the apache module.
            # Ubuntu: install python-profiler when using this feature
            profilefile = defaults.var_dir + "/web/multisite.profile"
            retcode = cProfile.runctx(
                "import index; "
                "index.handler(profile_req, profile_fields, False)",
                {'profile_req': req, 'profile_fields': html.fields}, {}, profilefile)
            file(profilefile + ".py", "w").write(
                "#!/usr/bin/python\n"
                "import pstats\n"
                "stats = pstats.Stats(%r)\n"
                "stats.sort_stats('time').print_stats()\n" % profilefile)
            os.chmod(profilefile + ".py", 0755)
            release_all_locks()
            return apache.OK

        # Make sure all plugins are avaiable as early as possible. At least
        # we need the plugins (i.e. the permissions declared in these) at the
        # time before the first login for generating auth.php.
        load_all_plugins()

        # Detect mobile devices
        if html.has_var("mobile"):
            html.mobile = not not html.var("mobile")
        else:
            user_agent = html.req.headers_in.get('User-Agent', '')
            html.mobile = mobile.is_mobile(user_agent)

        # Redirect to mobile GUI if we are a mobile device and
        # the URL is /
        if html.myfile == "index" and html.mobile:
            html.myfile = "mobile"

        # Get page handler.
        handler = pagehandlers.get(html.myfile, page_not_found)

        # First initialization of the default permissions. Needs to be done before the auth_file
        # (auth.php) ist written (it's done during showing the login page for the first time).
        # Must be loaded before the "automation" call to have the general.* permissions available
        # during automation action processing (e.g. hooks triggered by restart)
        default_permissions.load()

        # Some pages do skip authentication. This is done by adding
        # noauth: to the page hander, e.g. "noauth:run_cron" : ...
        if handler == page_not_found:
            handler = pagehandlers.get("noauth:" + html.myfile, page_not_found)
            if handler != page_not_found:
                try:
                    # Call userdb page hooks which are executed on a regular base to e.g. syncronize
                    # information withough explicit user triggered actions
                    userdb.hook_page()

                    handler()
                except Exception, e:
                    html.write(str(e))
                    if config.debug:
                        html.write(html.attrencode(format_exception()))
                release_all_locks()
                return apache.OK

        # Prepare output format
        output_format = html.var("output_format", "html")
        html.set_output_format(output_format)

        # Is the user set by the webserver? otherwise use the cookie based auth
        if not html.user or type(html.user) != str:
            config.auth_type = 'cookie'
            # When not authed tell the browser to ask for the password
            html.user = login.check_auth()
            if html.user == '':
                if fail_silently:
                    # While api call don't show the login dialog
                    raise MKUnauthenticatedException(_('You are not authenticated.'))

                # Redirect to the login-dialog with the current url as original target
                # Never render the login form directly when accessing urls like "index.py"
                # or "dashboard.py". This results in strange problems.
                if html.myfile != 'login':
                    html.http_redirect(defaults.url_prefix + 'check_mk/login.py?_origtarget=%s' %
                                                html.urlencode(html.makeuri([])))

                # Initialize the i18n for the login dialog. This might be overridden
                # later after user login
                load_language(html.var("lang", config.get_language()))

                # This either displays the login page or validates the information submitted
                # to the login form. After successful login a http redirect to the originally
                # requested page is performed.
                login.page_login(plain_error)
                release_all_locks()
                return apache.OK

        # Call userdb page hooks which are executed on a regular base to e.g. syncronize
        # information withough explicit user triggered actions
        userdb.hook_page()

        # Set all permissions, read site config, and similar stuff
        config.login(html.user)
        html.load_help_visible()

        # Initialize the multiste i18n. This will be replaced by
        # language settings stored in the user profile after the user
        # has been initialized
        load_language(html.var("lang", config.get_language()))

        # All plugins might have to be reloaded due to a language change
        load_all_plugins()

        # Reload default permissions (maybe reload due to language change)
        default_permissions.load()

        # User allowed to login at all?
        if not config.may("general.use"):
            reason = _("You are not authorized to use Check_MK Multisite. Sorry. "
                       "You are logged in as <b>%s</b>.") % config.user_id
            if len(config.user_role_ids):
                reason += _("Your roles are <b>%s</b>. " % ", ".join(config.user_role_ids))
            else:
                reason += _("<b>You do not have any roles.</b> ")
            reason += _("If you think this is an error, "
                        "please ask your administrator to check the permissions configuration.")

            if config.auth_type == 'cookie':
                reason += _('<p>You have been logged out. Please reload the page to re-authenticate.</p>')
                login.del_auth_cookie()

            raise MKAuthException(reason)

        handler()

    except (MKUserError, MKAuthException, MKUnauthenticatedException, MKConfigError, MKGeneralException,
            livestatus.MKLivestatusNotFoundError, livestatus.MKLivestatusException), e:
        ty = type(e)
        if ty == livestatus.MKLivestatusNotFoundError:
            title       = _("Data not found")
            plain_title = _("Livestatus-data not found")
        elif isinstance(e, livestatus.MKLivestatusException):
            title       = _("Livestatus problem")
            plain_title = _("Livestatus problem")
        else:
            title       = e.title
            plain_title = e.plain_title

        if plain_error:
            html.write("%s: %s\n" % (plain_title, e))
        elif not fail_silently:
            html.header(title)
            html.show_error(e)
            html.footer()

        # Some exception need to set a specific HTTP status code
        if ty == MKUnauthenticatedException:
            response_code = apache.HTTP_UNAUTHORIZED
        elif ty == livestatus.MKLivestatusNotFoundError:
            response_code = apache.HTTP_NOT_FOUND
        elif ty == livestatus.MKLivestatusException:
            response_code = apache.HTTP_BAD_GATEWAY

        if ty in [MKConfigError, MKGeneralException]:
            html.log(_("%s: %s") % (plain_title, e))

    except (apache.SERVER_RETURN,
            (apache.SERVER_RETURN, apache.HTTP_UNAUTHORIZED),
            (apache.SERVER_RETURN, apache.HTTP_MOVED_TEMPORARILY)):
        release_all_locks()
        html.live = None
        raise

    except Exception, e:
        html.unplug()
        msg = "%s %s: %s" % (req.uri, _('Internal error'), e)
        if type(msg) == unicode:
            msg = msg.encode('utf-8')
        apache.log_error(msg, apache.APLOG_ERR) # log in all cases
        if plain_error:
            html.write(_("Internal error") + ": %s\n" % html.attrencode(e))
        elif not fail_silently:
            html.header(_("Internal error"))
            html.show_exception(e)
            html.footer()
        response_code = apache.OK

    release_all_locks()
    html.live = None # disconnects from livestatus
    return response_code

def page_not_found():
    if html.has_var("_plain_error"):
        html.write(_("Page not found"))
    else:
        html.header(_("Page not found"))
        html.show_error(_("This page was not found. Sorry."))
    html.footer()
