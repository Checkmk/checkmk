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

import grp, pprint, os, errno, gettext, marshal, re, fcntl, __builtin__

#Workarround when the file is included outsite multisite
try:
    import defaults
except:
    pass


core_state_names = { -1: _("NODATA"), 0: _("OK"), 1: _("WARNING"), 2: _("CRITICAL"), 3: _("UNKNOWN")}
nagios_short_state_names = { -1: _("PEND"), 0: _("OK"), 1: _("WARN"), 2: _("CRIT"), 3: _("UNKN") }
nagios_short_host_state_names = { 0: _("UP"), 1: _("DOWN"), 2: _("UNREACH") }

# never used directly in the code. Just some wrapper to make all of our
# exceptions handleable with one call
class MKException(Exception):
    # Do not use the Exception() __str__, because it uses str()
    # to convert the message. We want to keep unicode strings untouched
    def __str__(self):
        return self.message

class MKGeneralException(MKException):
    plain_title = _("General error")
    title       = _("Error")
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason

class MKAuthException(MKException):
    title       = _("Permission denied")
    plain_title = _("Authentication error")
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason

class MKUnauthenticatedException(MKGeneralException):
    title       = _("Not authenticated")
    plain_title = _("Missing authentication credentials")

class MKConfigError(MKException):
    title       = _("Configuration error")
    plain_title = _("Configuration error")

class MKUserError(MKException):
    title       = _("Invalid User Input")
    plain_title = _("User error")
    def __init__(self, varname, message):
        self.varname = varname
        Exception.__init__(self, message)

class MKInternalError(MKException):
    pass

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
    try:
        data = pprint.pformat(content)
    except UnicodeDecodeError:
        # When writing a dict with unicode keys and normal strings with garbled
        # umlaut encoding pprint.pformat() fails with UnicodeDecodeError().
        # example:
        #   pprint.pformat({'Z\xc3\xa4ug': 'on',  'Z\xe4ug': 'on', u'Z\xc3\xa4ugx': 'on'})
        # Catch the exception and use repr() instead
        data = repr(content)
    create_user_file(path, "w").write(data + "\n")

def savefloat(f):
    try:
        return float(f)
    except:
        return 0.0

# sorted() is not available in all Python versions
try:
    sorted
except:
    def sorted(l):
        a = l[:]
        a.sort()
        return a

# We should use /dev/random here for cryptographic safety. But
# that involves the great problem that the system might hang
# because of loss of entropy. So we hope /dev/urandom is enough.
# Furthermore we filter out non-printable characters. The byte
# 0x00 for example does not make it through HTTP and the URL.
def get_random_string(size):
    secret = ""
    urandom = file("/dev/urandom")
    while len(secret) < size:
        c = urandom.read(1)
        if ord(c) >= 48 and ord(c) <= 90:
            secret += c
    return secret

# Generates a unique id
def gen_id():
    try:
        return file('/proc/sys/kernel/random/uuid').read().strip()
    except IOError:
        # On platforms where the above file does not exist we try to
        # use the python uuid module which seems to be a good fallback
        # for those systems. Well, if got python < 2.5 you are lost for now.
        import uuid
        return str(uuid.uuid4())

# Load all files below share/check_mk/web/plugins/WHAT into a
# specified context (global variables). Also honors the
# local-hierarchy for OMD
def load_web_plugins(forwhat, globalvars):
    plugins_path = defaults.web_dir + "/plugins/" + forwhat
    if os.path.exists(plugins_path):
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
    languages = set([ (None, _('English')) ])

    for lang_dir in get_language_dirs():
        try:
            languages.update([ (val, get_language_alias(val))
                for val in os.listdir(lang_dir) if not '.' in val ])
        except OSError:
            # Catch "OSError: [Errno 2] No such file or
            # directory:" when directory not exists
            pass

    return list(languages)

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

# Localization of user supplied texts
def _u(text):
    import config
    ldict = config.user_localizations.get(text)
    if ldict:
        return ldict.get(current_language, text)
    else:
        return text

__builtin__._u = _u

def pnp_cleanup(s):
    return s \
        .replace(' ', '_') \
        .replace(':', '_') \
        .replace('/', '_') \
        .replace('\\', '_')

# Quote string for use as arguments on the shell
def quote_shell_string(s):
        return "'" + s.replace("'", "'\"'\"'") + "'"

ok_marker      = '<b class="stmark state0">OK</b>'
warn_marker    = '<b class="stmark state1">WARN</b>'
crit_marker    = '<b class="stmark state2">CRIT</b>'
unknown_marker = '<b class="stmark state3">UNKN</b>'

def paint_host_list(site, hosts):
    h = ""
    first = True
    for host in hosts:
        if first:
            first = False
        else:
            h += ", "
        link = "view.py?view_name=hoststatus&site=%s&host=%s" % (html.urlencode(site), html.urlencode(host))
        if html.var("display_options"):
            link += "&display_options=%s" % html.var("display_options")
        h += "<a href=\"%s\">%s</a></div>" % (link, host)
    return "", h

def format_plugin_output(output, row = None):
    import config
    if config.escape_plugin_output:
        output = html.attrencode(output)

    output = output.replace("(!)", warn_marker) \
              .replace("(!!)", crit_marker) \
              .replace("(?)", unknown_marker) \
              .replace("(.)", ok_marker)

    if row and "[running on" in output:
        a = output.index("[running on")
        e = output.index("]", a)
        hosts = output[a+12:e].replace(" ","").split(",")
        css, h = paint_host_list(row["site"], hosts)
        output = output[:a] + "running on " + h + output[e+1:]

    if config.escape_plugin_output:
        output = re.sub("http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                         lambda p: '<a href="%s"><img class=pluginurl align=absmiddle title="%s" src="images/pluginurl.png"></a>' %
                            (p.group(0).replace('&quot;', ''), p.group(0).replace('&quot;', '')), output)

    return output

def format_exception():
    import traceback
    return traceback.format_exc()

# Escape/strip unwanted chars from (user provided) strings to
# use them in livestatus queries. Prevent injections of livestatus
# protocol related chars or strings
def lqencode(s):
    # It is not enough to strip off \n\n, because one might submit "\n \n",
    # which is also interpreted as termination of the last query and beginning
    # of the next query.
    return s.replace('\n', '')

def saveint(x):
    try:
        return int(x)
    except:
        return 0

def tryint(x):
    try:
        return int(x)
    except:
        return x

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
    g_aquired_locks.append((path, fd))
    g_locked_paths.append(path)

def release_lock(path):
    if path not in g_locked_paths:
        return # no unlocking needed
    for lock_path, fd in g_aquired_locks:
        if lock_path == path:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            g_aquired_locks.remove((lock_path, fd))
    g_locked_paths.remove(path)

def have_lock(path):
    return path in g_locked_paths

def release_all_locks():
    global g_aquired_locks, g_locked_paths
    for path, fd in g_aquired_locks:
        os.close(fd)
    g_aquired_locks = []
    g_locked_paths = []


regex_cache = {}
def regex(r):
    rx = regex_cache.get(r)
    if rx:
        return rx
    try:
        rx = re.compile(r)
    except Exception, e:
        raise MKConfigError(_("Invalid regular expression '%s': %s") % (r, e))
    regex_cache[r] = rx
    return rx

def escape_regex_chars(text):
    escaped = ""
    for c in text:
        if c in '().^$[]{}+*\\':
            escaped += '\\'
        escaped += c
    return escaped


# Splits a word into sequences of numbers and non-numbers.
# Creates a tuple from these where the number are converted
# into int datatype. That way a naturual sort can be
# implemented.
def num_split(s):
    if not s:
        return ()
    elif s[0].isdigit():
        first_num = regex("[^0-9]").split(s)[0]
        return ( int(first_num), ) + num_split(s[len(first_num):])
    else:
        first_word = regex("[0-9]").split(s)[0]
        return ( first_word.lower(), ) + num_split(s[len(first_word):])

def number_human_readable(n, precision=1, unit="B"):
    base = 1024.0
    if unit == "Bit":
        base = 1000.0

    n = float(n)
    f = "%." + str(precision) + "f"
    if abs(n) > base * base * base:
        return (f + "G%s") % (n / (base * base * base), unit)
    elif abs(n) > base * base:
        return (f + "M%s") % (n / (base * base), unit)
    elif abs(n) > base:
        return (f + "k%s") % (n / base, unit)
    else:
        return (f + "%s") % (n, unit)

def age_human_readable(secs, min_only=False):
    if secs < 0:
        return "- " + age_human_readable(-secs, min_only)
    elif secs > 0 and secs < 0.0001: # us
        return "%.1f us" % (secs * 1000000)
    elif secs > 0 and secs < 1: # ms
        return "%.2f ms" % (secs * 1000)
    elif min_only:
        mins = secs / 60.0
        return "%.1f %s" % (mins, _("min"))
    elif secs < 10:
        return "%.2f %s" % (secs, _("sec"))
    elif secs < 60:
        return "%.1f %s" % (secs, _("sec"))
    elif secs < 240:
        return "%d %s" % (secs, _("sec"))
    mins = secs / 60
    if mins < 360:
        return "%d %s" % (mins, _("min"))
    hours = mins / 60
    if hours < 48:
        return "%d %s" % (hours, _("hours"))
    days = hours / 24
    return "%d %s" % (days, _("days"))

def bytes_human_readable(b, base=1024.0, bytefrac=True, unit="B"):
    base = float(base)
    # Handle negative bytes correctly
    prefix = ''
    if b < 0:
        prefix = '-'
        b *= -1

    if b >= base * base * base * base:
        return '%s%.2f T%s' % (prefix, b / base / base / base / base, unit)
    elif b >= base * base * base:
        return '%s%.2f G%s' % (prefix, b / base / base / base, unit)
    elif b >= base * base:
        return '%s%.2f M%s' % (prefix, b / base / base, unit)
    elif b >= base:
        return '%s%.2f k%s' % (prefix, b / base, unit)
    elif bytefrac:
        return '%s%.2f %s' % (prefix, b, unit)
    else: # Omit byte fractions
        return '%s%.0f %s' % (prefix, b, unit)




__builtin__.default_user_localizations = {
     u'Agent type':                          { "de": u"Art des Agenten", },
     u'Business critical':                   { "de": u"Geschäftskritisch", },
     u'Check_MK Agent (Server)':             { "de": u"Check_MK Agent (Server)", },
     u'Criticality':                         { "de": u"Kritikalität", },
     u'DMZ (low latency, secure access)':    { "de": u"DMZ (geringe Latenz, hohe Sicherheit", },
     u'Do not monitor this host':            { "de": u"Diesen Host nicht überwachen", },
     u'Dual: Check_MK Agent + SNMP':         { "de": u"Dual: Check_MK Agent + SNMP", },
     u'Legacy SNMP device (using V1)':       { "de": u"Alte SNMP-Geräte (mit Version 1)", },
     u'Local network (low latency)':         { "de": u"Lokales Netzwerk (geringe Latenz)", },
     u'Networking Segment':                  { "de": u"Netzwerksegment", },
     u'No Agent':                            { "de": u"Kein Agent", },
     u'Productive system':                   { "de": u"Produktivsystem", },
     u'Test system':                         { "de": u"Testsystem", },
     u'WAN (high latency)':                  { "de": u"WAN (hohe Latenz)", },
     u'monitor via Check_MK Agent':          { "de": u"Überwachung via Check_MK Agent", },
     u'monitor via SNMP':                    { "de": u"Überwachung via SNMP", },
     u'SNMP (Networking device, Appliance)': { "de": u"SNMP (Netzwerkgerät, Appliance)", },
}

try:
    import ast
    literal_eval = ast.literal_eval
except ImportError:
    # python <2.5 compatibility
    try:
        from compiler import parse
        import compiler.ast
        def literal_eval(node_or_string):
            _safe_names = {'none': none, 'true': true, 'false': false}

            if isinstance(node_or_string, basestring):
                node_or_string = parse(node_or_string, mode='eval')
            if isinstance(node_or_string, compiler.ast.expression):
                node_or_string = node_or_string.node

            def _convert(node):
                if isinstance(node, compiler.ast.const) and isinstance(node.value,
                        (basestring, int, float, long, complex)):
                     return node.value
                elif isinstance(node, compiler.ast.tuple):
                    return tuple(map(_convert, node.nodes))
                elif isinstance(node, compiler.ast.list):
                    return list(map(_convert, node.nodes))
                elif isinstance(node, compiler.ast.dict):
                    return dict((_convert(k), _convert(v)) for k, v
                                in node.items)
                elif isinstance(node, compiler.ast.name):
                    if node.name in _safe_names:
                        return _safe_names[node.name]
                elif isinstance(node, compiler.ast.unarysub):
                    return -_convert(node.expr)
                raise valueerror('malformed string')

            return _convert(node_or_string)
    except:
        literal_eval = none
