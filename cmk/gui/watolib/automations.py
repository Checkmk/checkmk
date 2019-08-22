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
"""This code section deals with the interaction of Check_MK base code. It is
used for doing inventory, showing the services of a host, deletion of a host
and similar things."""

import ast
import re
import subprocess
import time
import requests
import urllib3

import cmk.utils

import cmk.gui.config as config
import cmk.gui.hooks as hooks
from cmk.gui.htmllib import Encoder
from cmk.gui.i18n import _
from cmk.gui.log import logger
from cmk.gui.globals import html
from cmk.gui.watolib.sites import SiteManagementFactory
from cmk.gui.watolib.utils import mk_repr
from cmk.gui.exceptions import (
    MKGeneralException,
    MKUserError,
)

# Disable python warnings in background job output or logs like "Unverified
# HTTPS request is being made". We warn the user using analyze configuration.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class MKAutomationException(MKGeneralException):
    pass


def check_mk_automation(siteid,
                        command,
                        args=None,
                        indata="",
                        stdin_data=None,
                        timeout=None,
                        sync=True):
    if args is None:
        args = []

    if not siteid or config.site_is_local(siteid):
        return check_mk_local_automation(command, args, indata, stdin_data, timeout)
    return check_mk_remote_automation(siteid, command, args, indata, stdin_data, timeout, sync)


def check_mk_local_automation(command, args=None, indata="", stdin_data=None, timeout=None):
    if args is None:
        args = []

    auto_logger = logger.getChild("automations")

    if timeout:
        args = ["--timeout", "%d" % timeout] + args

    cmd = ['check_mk', '--automation', command, '--'] + args
    if command in ['restart', 'reload']:
        call_hook_pre_activate_changes()

    cmd = [cmk.utils.make_utf8(a) for a in cmd]
    try:
        # This debug output makes problems when doing bulk inventory, because
        # it garbles the non-HTML response output
        # if config.debug:
        #     html.write("<div class=message>Running <tt>%s</tt></div>\n" % subprocess.list2cmdline(cmd))
        auto_logger.info("RUN: %s" % subprocess.list2cmdline(cmd))
        p = subprocess.Popen(cmd,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             close_fds=True)
    except Exception as e:
        raise MKGeneralException("Cannot execute <tt>%s</tt>: %s" %
                                 (subprocess.list2cmdline(cmd), e))

    if stdin_data is not None:
        auto_logger.info("STDIN: %r" % stdin_data)
        p.stdin.write(stdin_data)
    else:
        auto_logger.info("STDIN: %r" % indata)
        p.stdin.write(repr(indata))

    p.stdin.close()
    outdata = p.stdout.read()
    exitcode = p.wait()
    auto_logger.info("FINISHED: %d" % exitcode)
    auto_logger.debug("OUTPUT: %r" % outdata)
    if exitcode != 0:
        auto_logger.error("Error running %r (exit code %d)" %
                          (subprocess.list2cmdline(cmd), exitcode))

        if config.debug:
            raise MKGeneralException(
                "Error running <tt>%s</tt> (exit code %d): <pre>%s</pre>" %
                (subprocess.list2cmdline(cmd), exitcode, _hilite_errors(outdata)))
        else:
            raise MKGeneralException(_hilite_errors(outdata))

    # On successful "restart" command execute the activate changes hook
    if command in ['restart', 'reload']:
        call_hook_activate_changes()

    try:
        return ast.literal_eval(outdata)
    except SyntaxError as e:
        raise MKGeneralException(
            "Error running <tt>%s</tt>. Invalid output from webservice (%s): <pre>%s</pre>" %
            (subprocess.list2cmdline(cmd), e, outdata))


def _hilite_errors(outdata):
    return re.sub("\nError: *([^\n]*)", "\n<div class=err><b>Error:</b> \\1</div>", outdata)


def check_mk_remote_automation(site_id,
                               command,
                               args,
                               indata,
                               stdin_data=None,
                               timeout=None,
                               sync=True):
    site = config.site(site_id)
    if "secret" not in site:
        raise MKGeneralException(
            _("Cannot connect to site \"%s\": The site is not logged in") %
            site.get("alias", site_id))

    if not site.get("replication"):
        raise MKGeneralException(
            _("Cannot connect to site \"%s\": The replication is disabled") %
            site.get("alias", site_id))

    if sync:
        sync_changes_before_remote_automation(site_id)

    # Now do the actual remote command
    response = do_remote_automation(
        config.site(site_id),
        "checkmk-automation",
        [
            ("automation", command),  # The Check_MK automation command
            ("arguments", mk_repr(args)),  # The arguments for the command
            ("indata", mk_repr(indata)),  # The input data
            ("stdin_data", mk_repr(stdin_data)),  # The input data for stdin
            ("timeout", mk_repr(timeout)),  # The timeout
        ])
    return response


# If the site is not up-to-date, synchronize it first.
def sync_changes_before_remote_automation(site_id):
    # TODO: Cleanup this local import
    import cmk.gui.watolib.activate_changes  # pylint: disable=redefined-outer-name
    manager = cmk.gui.watolib.activate_changes.ActivateChangesManager()
    manager.load()

    if not manager.is_sync_needed(site_id):
        return

    logger.info("Syncing %s", site_id)

    manager.start([site_id], activate_foreign=True, prevent_activate=True)

    # Wait maximum 30 seconds for sync to finish
    timeout = 30
    while manager.is_running() and timeout > 0.0:
        time.sleep(0.5)
        timeout -= 0.5

    state = manager.get_site_state(site_id)
    if state and state["_state"] != "success":
        logger.error(_("Remote automation tried to sync pending changes but failed: %s"),
                     state.get("_status_details"))


# This hook is executed when one applies the pending configuration changes
# from wato but BEFORE the nagios restart is executed.
#
# It can be used to create custom input files for nagios/Check_MK.
#
# The registered hooks are called with a dictionary as parameter which
# holds all available with the hostnames as keys and the attributes of
# the hosts as values.
def call_hook_pre_activate_changes():
    if hooks.registered('pre-activate-changes'):
        # TODO: Cleanup this local import
        import cmk.gui.watolib.hosts_and_folders  # pylint: disable=redefined-outer-name
        hooks.call("pre-activate-changes", cmk.gui.watolib.hosts_and_folders.collect_all_hosts())


# This hook is executed when one applies the pending configuration changes
# from wato.
#
# But it is only excecuted when there is at least one function
# registered for this host.
#
# The registered hooks are called with a dictionary as parameter which
# holds all available with the hostnames as keys and the attributes of
# the hosts as values.
def call_hook_activate_changes():
    if hooks.registered('activate-changes'):
        # TODO: Cleanup this local import
        import cmk.gui.watolib.hosts_and_folders  # pylint: disable=redefined-outer-name
        hooks.call("activate-changes", cmk.gui.watolib.hosts_and_folders.collect_all_hosts())


def do_remote_automation(site, command, vars_, timeout=None):
    base_url = site["multisiteurl"]
    secret = site.get("secret")
    if not secret:
        raise MKAutomationException(_("You are not logged into the remote site."))

    url = base_url + "automation.py?" + \
        Encoder().urlencode_vars([
               ("command", command),
               ("secret",  secret),
               ("debug",   config.debug and '1' or '')
        ])

    response = get_url(url, site.get('insecure', False), data=dict(vars_), timeout=timeout)

    if not response:
        raise MKAutomationException(_("Empty output from remote site."))

    try:
        response = ast.literal_eval(response)
    except SyntaxError:
        # The remote site will send non-Python data in case of an error.
        raise MKAutomationException("%s: <pre>%s</pre>" % (_("Got invalid data"), response))

    return response


def get_url_raw(url, insecure, auth=None, data=None, files=None, timeout=None):
    response = requests.post(
        url,
        data=data,
        verify=not insecure,
        auth=auth,
        files=files,
        timeout=timeout,
    )

    response.encoding = "utf-8"  # Always decode with utf-8

    if response.status_code == 401:
        raise MKUserError("_passwd", _("Authentication failed. Invalid login/password."))

    elif response.status_code == 503 and "Site Not Started" in response.text:
        raise MKUserError(None, _("Site is not running"))

    elif response.status_code != 200:
        raise MKUserError(None, _("HTTP Error - %d: %s") % (response.status_code, response.text))

    return response


def get_url(url, insecure, auth=None, data=None, files=None, timeout=None):
    return get_url_raw(url, insecure, auth, data, files, timeout).text


def get_url_json(url, insecure, auth=None, data=None, files=None, timeout=None):
    return get_url_raw(url, insecure, auth, data, files, timeout).json()


def do_site_login(site_id, name, password):
    sites = SiteManagementFactory().factory().load_sites()
    site = sites[site_id]
    if not name:
        raise MKUserError("_name", _("Please specify your administrator login on the remote site."))
    if not password:
        raise MKUserError("_passwd", _("Please specify your password."))

    # Trying basic auth AND form based auth to ensure the site login works.
    # Adding _ajaxid makes the web service fail silently with an HTTP code and
    # not output HTML code for an error screen.
    url = site["multisiteurl"] + 'login.py'
    post_data = {
        '_login': '1',
        '_username': name,
        '_password': password,
        '_origtarget': 'automation_login.py?_version=%s&_edition_short=%s' %
                       (cmk.__version__, cmk.edition_short()),
        '_plain_error': '1',
    }
    response = get_url(url, site.get('insecure', False), auth=(name, password),
                       data=post_data).strip()
    if '<html>' in response.lower():
        message = _("Authentication to web service failed.<br>Message:<br>%s") % \
            html.strip_tags(html.strip_scripts(response))
        if config.debug:
            message += "<br>" + _("Automation URL:") + " <tt>%s</tt><br>" % url
        raise MKAutomationException(message)
    elif not response:
        raise MKAutomationException(_("Empty response from web service"))
    else:
        try:
            eval_response = ast.literal_eval(response)
        except SyntaxError:
            raise MKAutomationException(response)
        if isinstance(eval_response, dict):
            if cmk.is_managed_edition() and eval_response["edition_short"] != "cme":
                raise MKUserError(
                    None,
                    _("The Check_MK Managed Services Edition can only "
                      "be connected with other sites using the CME."))
            return eval_response["login_secret"]
        return eval_response
