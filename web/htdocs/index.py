#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
from mod_python import apache, util, Cookie
import sys, os, pprint
from lib import *
import livestatus
import defaults, config, htmllib, login, userdb, hooks, default_permissions

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

def read_get_vars(req):
    req.vars = {}
    req.listvars = {} # for variables with more than one occurrance
    fields = util.FieldStorage(req, keep_blank_values = 1)
    for field in fields.list:
        varname = field.name
        value = field.value
        # Multiple occurrance of a variable? Store in extra list dict
        if varname in req.vars:
            if varname in req.listvars:
                req.listvars[varname].append(value)
            else:
                req.listvars[varname] = [ req.vars[varname], value ]
        # In the single-value-store the last occurrance of a variable
        # has precedence. That makes appending variables to the current
        # URL simpler.
        req.vars[varname] = value

def read_cookies(req):
    req.cookies = Cookie.get_cookies(req)

def connect_to_livestatus(html):
    html.site_status = {}
    # site_status keeps a dictionary for each site with the following
    # keys:
    # "state"              --> "online", "disabled", "down", "unreach", "dead" or "waiting"
    # "exception"          --> An error exception in case of down, unreach, dead or waiting
    # "status_host_state"  --> host state of status host (0, 1, 2 or None)
    # "livestatus_version" --> Version of sites livestatus if "online"
    # "program_version"    --> Version of Nagios if "online"

    # If there is only one site (non-multisite), than
    # user cannot enable/disable.
    if config.is_multisite():
        # do not contact those sites the user has disabled.
        # Also honor HTML-variables for switching off sites
        # right now. This is generally done by the variable
        # _site_switch=sitename1:on,sitename2:off,...
        switch_var = html.var("_site_switch")
        if switch_var:
            for info in switch_var.split(","):
                sitename, onoff = info.split(":")
                d = config.user_siteconf.get(sitename, {})
                if onoff == "on":
                    d["disabled"] = False
                else:
                    d["disabled"] = True
                config.user_siteconf[sitename] = d
            config.save_site_config()

        # Make lists of enabled and disabled sites
        enabled_sites = {}
        disabled_sites = {}

        for sitename, site in config.allsites().items():
            siteconf = config.user_siteconf.get(sitename, {})
            if siteconf.get("disabled", False):
                html.site_status[sitename] = { "state" : "disabled", "site" : site }
                disabled_sites[sitename] = site
            else:
                html.site_status[sitename] = { "state" : "dead", "site" : site }
                enabled_sites[sitename] = site

        html.live = livestatus.MultiSiteConnection(enabled_sites, disabled_sites)

        # Fetch status of sites by querying the version of Nagios and livestatus
        html.live.set_prepend_site(True)
        for sitename, v1, v2, ps, num_hosts, num_services in html.live.query(
              "GET status\n"
              "Columns: livestatus_version program_version program_start num_hosts num_services"):
            html.site_status[sitename].update({
                "state" : "online",
                "livestatus_version": v1,
                "program_version" : v2,
                "program_start" : ps,
                "num_hosts" : num_hosts,
                "num_services" : num_services,
            })
        html.live.set_prepend_site(False)

        # Get exceptions in case of dead sites
        for sitename, deadinfo in html.live.dead_sites().items():
            html.site_status[sitename]["exception"] = deadinfo["exception"]
            shs = deadinfo.get("status_host_state")
            html.site_status[sitename]["status_host_state"] = shs
            if shs == None:
                statename = "dead"
            else:
                statename = { 1:"down", 2:"unreach", 3:"waiting", }.get(shs, "unknown")
            html.site_status[sitename]["state"] = statename

    else:
        html.live = livestatus.SingleSiteConnection("unix:" + defaults.livestatus_unix_socket)
        html.live.set_timeout(10) # default timeout is 10 seconds
        html.site_status = { '': { "state" : "dead", "site" : config.site('') } }
        v1, v2, ps = html.live.query_row("GET status\nColumns: livestatus_version program_version program_start")
        html.site_status[''].update({ "state" : "online", "livestatus_version": v1, "program_version" : v2, "program_start" : ps })

    # If Multisite is retricted to data user is a nagios contact for,
    # we need to set an AuthUser: header for livestatus
    use_livestatus_auth = True
    if html.output_format == 'html':
        if config.may("general.see_all") and not config.user.get("force_authuser"):
            use_livestatus_auth = False
    else:
        if config.may("general.see_all") and not config.user.get("force_authuser_webservice"):
            use_livestatus_auth = False

    if use_livestatus_auth == True:
        html.live.set_auth_user('read',   config.user_id)
        html.live.set_auth_user('action', config.user_id)


    # May the user see all objects in BI aggregations or only some?
    if not config.may("bi.see_all"):
        html.live.set_auth_user('bi', config.user_id)

    # Default auth domain is read. Please set to None to switch off authorization
    html.live.set_auth_domain('read')

# Call the load_plugins() function in all modules
def load_all_plugins():
    for module in [ hooks, userdb, views, sidebar, dashboard, wato, bi, mobile ]:
        try:
            module.load_plugins # just check if this function exists
            module.load_plugins()
        except AttributeError:
            pass
        except Exception:
            raise
__builtin__.load_all_plugins = load_all_plugins

# Main entry point for all HTTP-requests (called directly by mod_apache)
def handler(req, profiling = True):
    req.content_type = "text/html; charset=UTF-8"
    req.header_sent = False

    # All URIs end in .py. We strip away the .py and get the
    # name of the page.
    req.myfile = req.uri.split("/")[-1][:-3]

    # Create an object that contains all data about the request and
    # helper functions for creating valid HTML. Parse URI and
    # store results in the request object for later usage.
    html = htmllib.html(req)
    html.id = {} # create unique ID for this request
    __builtin__.html = html
    req.uriinfo = htmllib.uriinfo(req)

    response_code = apache.OK
    try:
        # Do not parse variables again if profiling (and second run is done)
        if profiling:
            read_get_vars(req)
            read_cookies(req)

        # Ajax-Functions want no HTML output in case of an error but
        # just a plain server result code of 500
        fail_silently = html.has_var("_ajaxid")

        # Webservice functions may decide to get a normal result code
        # but a text with an error message in case of an error
        plain_error = html.has_var("_plain_error")

        config.load_config() # load multisite.mk
        if html.var("debug"): # Debug flag may be set via URL
            config.debug = True
        html.set_buffering(config.buffered_http_stream)

        # profiling can be enabled in multisite.mk
        if profiling and config.profile:
            import cProfile # , pstats, sys, StringIO, tempfile
            # the profiler looses the memory about all modules. We need to park
            # the request object in the apache module. This seems to be persistent.
            # Ubuntu: install python-profiler when using this feature
            apache._profiling_req = req
            profilefile = defaults.var_dir + "/web/multisite.profile"
            retcode = cProfile.run("import index; from mod_python import apache; index.handler(apache._profiling_req, False)", profilefile)
            file(profilefile + ".py", "w").write("#!/usr/bin/python\nimport pstats\nstats = pstats.Stats(%r)\nstats.sort_stats('time').print_stats()\n" % profilefile)
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
        if req.myfile == "index" and html.mobile:
            req.myfile = "mobile"

        # Get page handler
        handler = pagehandlers.get(req.myfile, page_not_found)

        # First initialization of the default permissions. Needs to be done before the auth_file
        # (auth.php) ist written (it's done during showing the login page for the first time).
        # Must be loaded before the "automation" call to have the general.* permissions available
        # during automation action processing (e.g. hooks triggered by restart)
        default_permissions.load()

        # Special handling for automation.py. Sorry, this must be hardcoded
        # here. Automation calls bybass the normal authentication stuff
        if req.myfile == "automation":
            try:
                handler()
            except Exception, e:
                html.write(str(e))
            release_all_locks()
            return apache.OK

        # Prepare output format
        output_format = html.var("output_format", "html")
        html.set_output_format(output_format)

        # Is the user set by the webserver? otherwise use the cookie based auth
        if not req.user or type(req.user) != str:
            config.auth_type = 'cookie'
            # When not authed tell the browser to ask for the password
            req.user = login.check_auth()
            if req.user == '':
                if fail_silently:
                    # While api call don't show the login dialog
                    raise MKUnauthenticatedException(_('You are not authenticated.'))

                # Initialize the i18n for the login dialog. This might be overridden
                # later after user login
                load_language(html.var("lang", config.get_language()))

                # After auth check the regular page can be shown
                result = login.page_login(plain_error)
                if type(result) == tuple:
                    # This is the redirect to the requested page directly after successful login
                    req.user = result[0]
                    req.uri  = result[1]
                    req.myfile = req.uri.split("/")[-1][:-3]
                    handler = pagehandlers.get(req.myfile, page_not_found)
                else:
                    release_all_locks()
                    return result

        # Call userdb page hooks which are executed on a regular base to e.g. syncronize
        # information withough explicit user triggered actions
        userdb.hook_page()

        # Set all permissions, read site config, and similar stuff
        config.login(html.req.user)

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

        # General access allowed. Now connect to livestatus
        connect_to_livestatus(html)

        handler()

    except MKUserError, e:
        if plain_error:
            html.write(_("User error") + ": %s\n" % e)
        elif not fail_silently:
            html.header("Invalid User Input")
            html.show_error(unicode(e))
            html.footer()

    except MKAuthException, e:
        if plain_error:
            html.write(_("Authentication error") + ": %s\n" % e)
        elif not fail_silently:
            html.header(_("Permission denied"))
            html.show_error(unicode(e))
            html.footer()

    except MKUnauthenticatedException, e:
        if plain_error:
            html.write(_("Missing authentication credentials") + ": %s\n" % e)
        elif not fail_silently:
            html.header(_("Not authenticated"))
            html.show_error(unicode(e))
            html.footer()
        response_code = apache.HTTP_UNAUTHORIZED

    except MKConfigError, e:
        if plain_error:
            html.write(_("Configuration error") + ": %s\n" % e)
        elif not fail_silently:
            html.header(_("Configuration Error"))
            html.show_error(unicode(e))
            html.footer()
        apache.log_error(_("Configuration error: %s") % (e,), apache.APLOG_ERR)

    except MKGeneralException, e:
        if plain_error:
            html.write(_("General error") + ": %s\n" % e)
        elif not fail_silently:
            html.header(_("Error"))
            html.show_error(unicode(e))
            html.footer()
        # apache.log_error(_("Error: %s") % (e,), apache.APLOG_ERR)

    except livestatus.MKLivestatusNotFoundError, e:
        if plain_error:
            html.write(_("Livestatus-data not found") + ": %s\n" % e)
        elif not fail_silently:
            html.header(_("Data not found"))
            html.show_error(_("The following query produced no output:\n<pre>\n%s</pre>\n") % \
                    e.query)
            html.footer()
        response_code = apache.HTTP_NOT_FOUND

    except livestatus.MKLivestatusException, e:
        if plain_error:
            html.write(_("Livestatus problem") + ": %s\n" % e)
        elif not fail_silently:
            html.header(_("Livestatus problem"))
            html.show_error(_("Livestatus problem: %s") % e)
            html.footer()
        else:
            response_code = apache.HTTP_BAD_GATEWAY

    except (apache.SERVER_RETURN,
            (apache.SERVER_RETURN, apache.HTTP_UNAUTHORIZED),
            (apache.SERVER_RETURN, apache.HTTP_MOVED_TEMPORARILY)):
        release_all_locks()
        html.live = None
        raise

    except Exception, e:
        html.unplug()
        if plain_error:
            html.write(_("Internal error") + ": %s\n" % e)
        elif not fail_silently:
            html.header(_("Internal error"))
            if config.debug:
                html.show_error("%s: %s<pre>%s</pre>" %
                    (_('Internal error') + ':', e, format_exception()))
            else:
                url = html.makeuri([("debug", "1")])
                html.show_error("%s: %s (<a href=\"%s\">%s</a>)" % (_('Internal error') + ':', e, url, _('Retry with debug mode')))
                apache.log_error("%s %s" % (_('Internal error') + ':', e), apache.APLOG_ERR)
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
