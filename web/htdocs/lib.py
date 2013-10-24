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

import grp, defaults, pprint, os, errno, gettext, marshal, fcntl, __builtin__


nagios_state_names = { -1: "NODATA", 0: "OK", 1: "WARNING", 2: "CRITICAL", 3: "UNKNOWN", 4: "DEPENDENT" }
nagios_short_state_names = { -1: "PEND", 0: "OK", 1: "WARN", 2: "CRIT", 3: "UNKN", 4: "DEP" }
nagios_short_host_state_names = { 0: "UP", 1: "DOWN", 2: "UNREACH" }

class MKGeneralException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason

class MKAuthException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason

class MKUnauthenticatedException(MKGeneralException):
    pass

class MKConfigError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)

class MKUserError(Exception):
    def __init__(self, varname, msg):
        self.varname = varname
        self.message = msg
        Exception.__init__(self, msg)

class MKInternalError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)


# Create directory owned by common group of Nagios and webserver,
# and make it writable for the group
def make_nagios_directory(path):
    if not os.path.exists(path):
        parent_dir, lastpart = path.rstrip('/').rsplit('/', 1)
        make_nagios_directory(parent_dir)
        try:
            os.mkdir(path)
            gid = grp.getgrnam(defaults.www_group).gr_gid
            os.chown(path, -1, gid)
            os.chmod(path, 0770)
        except Exception, e:
            raise MKConfigError("Your web server cannot create the directory <tt>%s</tt>, "
                    "or cannot set the group to <tt>%s</tt> or cannot set the permissions to <tt>0770</tt>. "
                    "Please make sure that:<ul><li>the base directory is writable by the web server.</li>"
                    "<li>Both Nagios and the web server are in the group <tt>%s</tt>.</ul>Reason: %s" % (
                        path, defaults.www_group, defaults.www_group, e))

# Same as make_nagios_directory but also creates parent directories
# Logic has been copied from os.makedirs()
def make_nagios_directories(name):
    head, tail = os.path.split(name)
    if not tail:
        head, tail = os.path.split(head)
    if head and tail and not os.path.exists(head):
        try:
            make_nagios_directories(head)
        except os.OSError, e:
            # be happy if someone already created the path
            if e.errno != errno.EEXIST:
                raise
        if tail == ".":           # xxx/newdir/. exists if xxx/newdir exists
            return
    make_nagios_directory(name)

def create_user_file(path, mode):
    f = file(path, mode, 0)
    gid = grp.getgrnam(defaults.www_group).gr_gid
    # Tackle user problem: If the file is owned by nagios, the web
    # user can write it but cannot chown the group. In that case we
    # assume that the group is correct and ignore the error
    try:
        os.chown(path, -1, gid)
        os.chmod(path, 0660)
    except:
        pass
    return f

def write_settings_file(path, content):
    create_user_file(path, "w").write(pprint.pformat(content) + "\n")

def savefloat(f):
    try:
        return float(f)
    except:
        return 0.0



# Load all files below share/check_mk/web/plugins/WHAT into a
# specified context (global variables). Also honors the
# local-hierarchy for OMD
def load_web_plugins(forwhat, globalvars):
    plugins_path = defaults.web_dir + "/plugins/" + forwhat

    fns = os.listdir(plugins_path)
    fns.sort()
    for fn in fns:
        file_path = plugins_path + "/" + fn
        if fn.endswith(".py"):
            if not os.path.exists(file_path + "c"):
                execfile(file_path, globalvars)
        elif fn.endswith(".pyc"):
            code_bytes = file(file_path).read()[8:]
            code = marshal.loads(code_bytes)
            exec code in globalvars

    if defaults.omd_root:
        local_plugins_path = defaults.omd_root + "/local/share/check_mk/web/plugins/" + forwhat
        if local_plugins_path != plugins_path: # honor ./setup.sh in site
            if os.path.exists(local_plugins_path):
                fns = os.listdir(local_plugins_path)
                fns.sort()
                for fn in fns:
                    file_path = local_plugins_path + "/" + fn
                    if fn.endswith(".py"):
                        execfile(file_path, globalvars)
                    elif fn.endswith(".pyc"):
                        code_bytes = file(file_path).read()[8:]
                        code = marshal.loads(code_bytes)
                        exec code in globalvars

def get_language_dirs():
    dirs = [ defaults.locale_dir ]
    if defaults.omd_root:
        dirs.append(defaults.omd_root + "/local/share/check_mk/locale")
    return dirs

def get_language_alias(lang):
    alias = lang
    for lang_dir in get_language_dirs():
        try:
            alias = file('%s/%s/alias' % (lang_dir, lang), 'r').read().strip()
        except (OSError, IOError):
            pass
    return alias

def get_languages():
    # Add the hard coded english language to the language list
    # It must be choosable even if the administrator changed the default
    # language to a custom value
    languages = [ (None, _('English')) ]

    for lang_dir in get_language_dirs():
        try:
            languages += [ (val, get_language_alias(val))
                for val in os.listdir(lang_dir) if not '.' in val ]
        except OSError:
            # Catch "OSError: [Errno 2] No such file or
            # directory:" when directory not exists
            pass

    return languages

def load_language(lang):
    # Make current language globally known to all of our modules
    __builtin__.current_language = lang

    if lang:
        locale_base = defaults.locale_dir

        # OMD users can put their localization into a local path into the site
        if defaults.omd_root:
            local_locale_path = defaults.omd_root + "/local/share/check_mk/locale"
            po_path = '/%s/LC_MESSAGES/multisite.mo' % lang
            # Use file in OMD local strucuture when existing
            if os.path.exists(local_locale_path + po_path):
                locale_base = local_locale_path

        try:
            i18n = gettext.translation('multisite', locale_base, languages = [ lang ], codeset = 'UTF-8')
            i18n.install(unicode = True)
        except IOError, e:
            # Fallback to non localized multisite
            # I'd prefer to fallback to multisite default language but can not import config module here
            __builtin__.current_language = None
    else:
        # Replace the _() function to disable i18n again
        __builtin__._ = lambda x: x

def pnp_cleanup(s):
    return s \
        .replace(' ', '_') \
        .replace(':', '_') \
        .replace('/', '_') \
        .replace('\\', '_')

warn_marker    = '<b class="stmark state1">WARN</b>'
crit_marker    = '<b class="stmark state2">CRIT</b>'
unknown_marker = '<b class="stmark state3">UNKN</b>'

def paint_host_list(site, hosts):
    from htmllib import urlencode
    h = ""
    first = True
    for host in hosts:
        if first:
            first = False
        else:
            h += ", "
        link = "view.py?view_name=hoststatus&site=%s&host=%s" % (urlencode(site), urlencode(host))
        if html.var("display_options"):
            link += "&display_options=%s" % html.var("display_options")
        h += "<a href=\"%s\">%s</a></div>" % (link, host)
    return "", h

def format_plugin_output(output, row = None):
    from htmllib import attrencode
    output = attrencode(output).replace("(!)", warn_marker) \
              .replace("(!!)", crit_marker) \
              .replace("(?)", unknown_marker)
    if row and "[running on" in output:
        a = output.index("[running on")
        e = output.index("]", a)
        hosts = output[a+12:e].replace(" ","").split(",")
        css, h = paint_host_list(row["site"], hosts)
        output = output[:a] + "running on " + h + output[e+1:]

    return output

def format_exception():
    import traceback, StringIO, sys
    txt = StringIO.StringIO()
    t, v, tb = sys.exc_info()
    traceback.print_exception(t, v, tb, None, txt)
    return txt.getvalue()

def saveint(x):
    try:
        return int(x)
    except:
        return 0

def set_is_disjoint(a, b):
    for elem in a:
        if elem in b:
            return False
    return True

# Functions for locking files. All locks must be freed if a request
# has terminated (in good or in bad manner). Currently only exclusive
# locks are implemented and they always will wait for ever.
g_aquired_locks = []
g_locked_paths = []
def aquire_lock(path):
    if path in g_locked_paths:
        return # No recursive locking
    fd = os.open(path, os.O_RDONLY)
    fcntl.flock(fd, fcntl.LOCK_EX)
    g_aquired_locks.append(fd)
    g_locked_paths.append(path)

def release_all_locks():
    global g_aquired_locks, g_locked_paths
    for fd in g_aquired_locks:
        os.close(fd)
    g_aquired_locks = []
    g_locked_paths = []


