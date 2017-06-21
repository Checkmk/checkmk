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

import math, grp, pprint, os, errno, marshal, re, fcntl, time
import traceback
from cmk.exceptions import MKException, MKGeneralException
from cmk.regex import regex
import cmk.store as store
import cmk.paths

from log import logger

class MKAuthException(MKException):
    def __init__(self, reason):
        self.reason = reason
        super(MKAuthException, self).__init__(reason)

    def __str__(self):
        return self.reason

    def title(self):
        return _("Permission denied")

    def plain_title(self):
        return _("Authentication error")


class MKUnauthenticatedException(MKGeneralException):
    def title(self):
        return _("Not authenticated")

    def plain_title(self):
        return _("Missing authentication credentials")


class MKConfigError(MKException):
    def title(self):
        return _("Configuration error")

    def plain_title(self):
        return self.title()


class MKUserError(MKException):
    def __init__(self, varname, message):
        self.varname = varname
        self.message = message
        super(MKUserError, self).__init__(varname, message)

    def __str__(self):
        return self.message

    def title(self):
        return _("Invalid User Input")

    def plain_title(self):
        return _("User error")


class MKInternalError(MKException):
    pass

# Create directory owned by common group of Nagios and webserver,
# and make it writable for the group
def make_nagios_directory(path):
    path = make_utf8(path)
    if not os.path.exists(path):
        parent_dir, lastpart = path.rstrip('/').rsplit('/', 1)
        make_nagios_directory(parent_dir)
        try:
            os.mkdir(path)
            os.chmod(path, 0770)
        except Exception, e:
            raise MKConfigError("Your web server cannot create the directory <tt>%s</tt>, "
                    "or cannot set the permissions to <tt>0770</tt>: %s" % (path, e))

# Same as make_nagios_directory but also creates parent directories
# Logic has been copied from os.makedirs()
def make_nagios_directories(name):
    name = make_utf8(name)
    head, tail = os.path.split(name)
    if not tail:
        head, tail = os.path.split(head)
    if head and tail and not os.path.exists(head):
        try:
            make_nagios_directories(head)
        except OSError, e:
            # be happy if someone already created the path
            if e.errno != errno.EEXIST:
                raise
        if tail == ".":           # xxx/newdir/. exists if xxx/newdir exists
            return
    make_nagios_directory(name)

# TODO: Deprecate this function! Don't use this anymore. Use the store.* functions!
def create_user_file(path, mode):
    path = make_utf8(path)
    f = file(path, mode, 0)
    os.chmod(path, 0660)
    return f


# TODO: Remove this helper function. Replace with explicit checks and covnersion
# in using code.
def savefloat(f):
    try:
        return float(f)
    except:
        return 0.0


def make_utf8(x):
    if type(x) == unicode:
        return x.encode('utf-8')
    else:
        return x


# We should use /dev/random here for cryptographic safety. But
# that involves the great problem that the system might hang
# because of loss of entropy. So we hope /dev/urandom is enough.
# Furthermore we filter out non-printable characters. The byte
# 0x00 for example does not make it through HTTP and the URL.
def get_random_string(size, from_ascii=48, to_ascii=90):
    secret = ""
    urandom = file("/dev/urandom")
    while len(secret) < size:
        c = urandom.read(1)
        if ord(c) >= from_ascii and ord(c) <= to_ascii:
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
# TODO: Couldn't we precompile all our plugins during packaging to make loading faster?
# TODO: Replace the execfile thing by some more pythonic plugin structure. But this would
#       be a large rewrite :-/
def load_web_plugins(forwhat, globalvars):
    for plugins_path in [ cmk.paths.web_dir + "/plugins/" + forwhat,
                          cmk.paths.local_web_dir + "/plugins/" + forwhat ]:
        if not os.path.exists(plugins_path):
            continue

        for fn in sorted(os.listdir(plugins_path)):
            file_path = plugins_path + "/" + fn

            if fn.endswith(".py") and not os.path.exists(file_path + "c"):
                execfile(file_path, globalvars)

            elif fn.endswith(".pyc"):
                code_bytes = file(file_path).read()[8:]
                code = marshal.loads(code_bytes)
                exec code in globalvars


def find_local_web_plugins():
    basedir = cmk.paths.local_web_dir + "/plugins/"

    try:
        plugin_dirs = os.listdir(basedir)
    except OSError, e:
        if e.errno == 2:
            return
        else:
            raise

    for plugins_dir in plugin_dirs:
        dir_path = basedir + plugins_dir
        yield dir_path # Changes in the directory like deletion of files!
        if os.path.isdir(dir_path):
            for file_name in os.listdir(dir_path):
                if file_name.endswith(".py") or file_name.endswith(".pyc"):
                    yield dir_path + "/" + file_name


last_web_plugins_update = 0
def local_web_plugins_have_changed():
    global last_web_plugins_update

    if html.is_cached("local_web_plugins_have_changed"):
        return html.get_cached("local_web_plugins_have_changed")

    this_time = 0.0
    for path in find_local_web_plugins():
        this_time = max(os.stat(path).st_mtime, this_time)
    last_time = last_web_plugins_update
    last_time = last_web_plugins_update
    last_web_plugins_update = this_time

    have_changed = this_time > last_time
    html.set_cache("local_web_plugins_have_changed", have_changed)
    return have_changed


def pnp_cleanup(s):
    return s \
        .replace(' ', '_') \
        .replace(':', '_') \
        .replace('/', '_') \
        .replace('\\', '_')

# Quote string for use as arguments on the shell
# TODO: Move to Check_MK library
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

# There is common code with modules/events.py:format_plugin_output(). Please check
# whether or not that function needs to be changed too
# TODO(lm): Find a common place to unify this functionality.
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
        # (?:&lt;A HREF=&quot;), (?: target=&quot;_blank&quot;&gt;)? and endswith(" </A>") is a special
        # handling for the HTML code produced by check_http when "clickable URL" option is active.
        output = re.sub("(?:&lt;A HREF=&quot;)?(http[s]?://[^\"'>\t\s\n,]+)(?: target=&quot;_blank&quot;&gt;)?",
                         lambda p: '<a href="%s"><img class=pluginurl align=absmiddle title="%s" src="images/pluginurl.png"></a>' %
                            (p.group(1).replace('&quot;', ''), p.group(1).replace('&quot;', '')), output)

        if output.endswith(" &lt;/A&gt;"):
            output = output[:-11]

    return output


def log_exception(msg=None):
    if msg is None:
        msg = _('Internal error')
    logger.error("%s %s: %s" % (html.request_uri(), msg, traceback.format_exc()))


# Escape/strip unwanted chars from (user provided) strings to
# use them in livestatus queries. Prevent injections of livestatus
# protocol related chars or strings
def lqencode(s):
    # It is not enough to strip off \n\n, because one might submit "\n \n",
    # which is also interpreted as termination of the last query and beginning
    # of the next query.
    return s.replace('\n', '')


# TODO: Remove this helper function. Replace with explicit checks and covnersion
# in using code.
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


aquire_lock       = store.aquire_lock
release_lock      = store.release_lock
have_lock         = store.have_lock
release_all_locks = store.release_all_locks

# Splits a word into sequences of numbers and non-numbers.
# Creates a tuple from these where the number are converted
# into int datatype. That way a naturual sort can be
# implemented.
def num_split(s):
    parts = []
    for part in re.split('(\d+)', s):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(part)

    return tuple(parts)


def cmp_service_name_equiv(r):
    if r == "Check_MK":
        return -6
    elif r == "Check_MK Agent":
        return -5
    elif r == "Check_MK Discovery":
        return -4
    elif r == "Check_MK inventory":
        return -3 # FIXME: Remove old name one day
    elif r == "Check_MK HW/SW Inventory":
        return -2
    else:
        return 0

def cmp_version(a, b):
    if a == None or b == None:
        return cmp(a, b)
    aa = map(tryint, a.split("."))
    bb = map(tryint, b.split("."))
    return cmp(aa, bb)


def frexpb(x, base):
    exp = int(math.log(x, base))
    mantissa = x / base**exp
    if mantissa < 1:
        mantissa *= base
        exp -= 1
    return mantissa, exp

def frexp10(x):
    return frexpb(x, 10)


def render_scientific(v, precision=3):
    if v == 0:
        return "0"
    elif v < 0:
        return "-" + render_scientific(v*-1, precision)

    mantissa, exponent = frexp10(float(v))
    # Render small numbers without exponent
    if exponent >= -3 and exponent <= 4:
        return "%%.%df" % max(0, precision - exponent) % v

    return "%%.%dfe%%d" % precision % (mantissa, exponent)


# Render a physical value witha precision of p
# digits. Use K (kilo), M (mega), m (milli), µ (micro)
# p is the number of non-zero digits - not the number of
# decimal places.
# Examples for p = 3:
# a: 0.0002234   b: 4,500,000  c: 137.56
# Result:
# a: 223 µ       b: 4.50 M     c: 138

# Note if the type of v is integer, then the precision cut
# down to the precision of the actual number
def physical_precision(v, precision, unit_symbol):
    if v < 0:
        return "-" + physical_precision(-v, precision, unit_symbol)

    scale_symbol, places_after_comma, scale_factor = calculate_physical_precision(v, precision)

    scaled_value = float(v) / scale_factor
    return (u"%%.%df %%s%%s" % places_after_comma) % (scaled_value, scale_symbol, unit_symbol)


def physical_precision_list(values, precision, unit_symbol):
    if not values:
        reference = 0
    else:
        reference = min([ abs(v) for v in values ])

    scale_symbol, places_after_comma, scale_factor = calculate_physical_precision(reference, precision)

    units = []
    scaled_values = []
    for value in values:
        scaled_value = float(value) / scale_factor
        scaled_values.append(("%%.%df" % places_after_comma) % scaled_value)

    return "%s%s" % (scale_symbol, unit_symbol), scaled_values


def calculate_physical_precision(v, precision):
    if v == 0:
        return "", precision - 1, 1

    # Splitup in mantissa (digits) an exponent to the power of 10
    # -> a: (2.23399998, -2)  b: (4.5, 6)    c: (1.3756, 2)
    mantissa, exponent = frexp10(float(v))

    if type(v) == int:
        precision = min(precision, exponent + 1)

    # Choose a power where no artifical zero (due to rounding) needs to be
    # placed left of the decimal point.
    scale_symbols = {
        -5 : "f",
        -4 : "p",
        -3 : "n",
        -2 : u"µ",
        -1 : "m",
         0 : "",
         1 : "K",
         2 : "M",
         3 : "G",
         4 : "T",
         5 : "P",
    }
    scale = 0

    while exponent < 0 and scale > -5:
        scale -= 1
        exponent += 3

    # scale, exponent = divmod(exponent, 3)
    places_before_comma = exponent + 1
    places_after_comma = precision - places_before_comma
    while places_after_comma < 0 and scale < 5:
        scale += 1
        exponent -= 3
        places_before_comma = exponent + 1
        places_after_comma = precision - places_before_comma

    return scale_symbols[scale], places_after_comma, 1000 ** scale


def nic_speed_human_readable(bits_per_second):
    if bits_per_second == 10000000:
        return "10 Mbit/s"
    elif bits_per_second == 100000000:
        return "100 Mbit/s"
    elif bits_per_second == 1000000000:
        return "1 Gbit/s"
    elif bits_per_second < 1500:
        return "%d bit/s" % bits_per_second
    elif bits_per_second < 1000000:
        return "%s Kbit/s" % drop_dotzero(bits_per_second / 1000.0, digits=1)
    elif bits_per_second < 1000000000:
        return "%s Mbit/s" % drop_dotzero(bits_per_second / 1000000.0, digits=2)
    else:
        return "%s Gbit/s" % drop_dotzero(bits_per_second / 1000000000.0, digits=2)

# Converts a number into a floating point number
# and drop useless zeroes at the end of the fraction
# 45.1 -> "45.1"
# 45.0 -> "45"
def drop_dotzero(v, digits=2):
    t = "%%.%df" % digits % v
    if "." in t:
        return t.rstrip("0").rstrip(".")
    else:
        return t


# Renders a floating point number with the given number
# of non-zero digits. Example if precision is 3:
# 12.40349034         -> 12.4
# 1.23894859348563478 -> 1.24
# 0.00001239898568978 -> 0.0000124
# 12400000.00230923   -> 12400000

def render_float_with_precision(value, precision):
    if value == 0:
        return "0"

    elif value < 0:
        return "-" + render_float_with_precision(-value, precision)

    mantissa, exponent = frexp10(float(value))
    # exponent + 1 is the number of digits left of the .

    # Digits left of . are more than precision -> no fraction.
    if exponent + 1 >= precision:
        return "%.0f" % value

    # Allow so many digits after comma that we have at least 'precision'
    # valid non-zero digits
    else:
        digits = precision - exponent - 1
        return "%%.%df" % digits % value




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


def percent_human_redable(perc, precision=2, drop_zeroes=True):
    if perc > 0:
        perc_precision = max(1, 2 - int(round(math.log(perc, 10))))
    else:
        perc_precision = 1
    text = "%%.%df" % perc_precision % perc
    if drop_zeroes:
        text = text.rstrip("0").rstrip(".")
    return text + "%"


def age_human_readable(secs, min_only=False):
    if secs < 0:
        return "- " + age_human_readable(-secs, min_only)
    elif secs > 0 and secs < 1: # ms
        return physical_precision(secs, 3, _("s"))
    elif min_only:
        mins = secs / 60.0
        return "%.1f %s" % (mins, _("m"))
    elif secs < 10:
        return "%.2f %s" % (secs, _("s"))
    elif secs < 60:
        return "%.1f %s" % (secs, _("s"))
    elif secs < 240:
        return "%d %s" % (secs, _("s"))
    mins = secs / 60
    if mins < 360:
        return "%d %s" % (mins, _("m"))
    hours = mins / 60
    if hours < 48:
        return "%d %s" % (hours, _("h"))
    days = hours / 24.0
    if days < 6:
        d = ("%.1f" % days).rstrip("0").rstrip(".")
        return "%s %s" % (d, _("d"))
    elif days < 999:
        return "%.0f %s" % (days, _("d"))
    else:
        years = days / 365
        if years < 10:
            return "%.1f %s" % (years, _("y"))
        else:
            return "%.0f %s" % (years, _("y"))


def date_human_readable(timestamp):
    # This can be localized:
    return time.strftime(_("%m/%d/%Y"), time.localtime(timestamp))

def datetime_human_readable(timestamp):
    # This can be localized:
    return time.strftime(_("%m/%d/%Y %H:%M:%S"), time.localtime(timestamp))

def date_range_human_readable(start_time, end_time):
    start_time_local = time.localtime(start_time)
    end_time_local = time.localtime(end_time)
    if start_time_local[:3] == end_time_local[:3]: # same day
        return date_human_readable(start_time)

    elif start_time_local[:2] == end_time_local[:2]: # same month
        date_format = _("%m/%d1-%d2/%Y")
        f = date_format.replace("%d2", time.strftime("%d", end_time_local))
        f = f.replace("%d1", "%d")
        return time.strftime(f, start_time_local)

    elif start_time_local[0] == end_time_local[0]: # same year
        date_format = _("%m1/%d1/%Y - %m2/%d2/%Y")
        f = date_format.replace("%d2", time.strftime("%d", end_time_local))
        f = f.replace("%m2", time.strftime("%m", end_time_local))
        f = f.replace("%d1", "%d").replace("%m1", "%m")
        return time.strftime(f, start_time_local)

    else:
        return date_human_readable(start_time) + " - " + \
               date_human_readable(end_time)

# Just print year and month, no day
def date_month_human_readable(timestamp):
    # TODO: %B will currently not be localized
    return time.strftime(_("%B %Y"), time.localtime(timestamp))


def calculate_scaled_number(v, base=1024.0, precision=1):
    base = float(base)

    if v >= base ** 4:
        symbol = "T"
        scale = base ** 4

    elif v >= base ** 3:
        symbol = "G"
        scale = base ** 3

    elif v >= base ** 2:
        symbol = "M"
        scale = base ** 2

    elif v >= base:
        symbol = "k"
        scale = base

    else:
        symbol = ""
        scale = 1

    return symbol, precision, scale


def calculate_scaled_bytes(v, base=1024.0, bytefrac=True):
    digits = 2
    if not bytefrac:
        digits = 0

    return calculate_scaled_number(v, base, precision=digits)


def bytes_human_readable(b, *args, **kwargs):
    if b < 0:
        return "-" + bytes_human_readable(-b, *args, **kwargs)

    if "unit" in kwargs:
        unit = kwargs.pop("unit")
    else:
        unit = "B"

    scale_symbol, places_after_comma, scale_factor = calculate_scaled_bytes(b, *args, **kwargs)

    scaled_value = float(b) / scale_factor
    if scale_symbol == "" and unit == "B":
        return u"%.0f %s%s" % (scaled_value, scale_symbol, unit)
    else:
        return (u"%%.%df %%s%%s" % places_after_comma) % (scaled_value, scale_symbol, unit)


def bytes_human_readable_list(values, *args, **kwargs):
    if not values:
        reference = 0
    else:
        reference = min([ abs(v) for v in values ])

    if "unit" in kwargs:
        unit = kwargs.pop("unit")
    else:
        unit = "B"

    scale_symbol, places_after_comma, scale_factor = calculate_scaled_bytes(reference, *args, **kwargs)

    units = []
    scaled_values = []
    for value in values:
        scaled_value = float(value) / scale_factor
        scaled_values.append(("%%.%df" % places_after_comma) % scaled_value)

    return "%s%s" % (scale_symbol, unit), scaled_values


def metric_number_with_precision(v, *args, **kwargs):
    if v < 0:
        return "-" + metric_number_with_precision(-v, *args, **kwargs)

    subargs = {
        "base": 1000.0,
        "precision": kwargs.get("precision", 2),
    }
    scale_symbol, places_after_comma, scale_factor = calculate_scaled_number(v, *args, **subargs)
    scaled_value = float(v) / scale_factor
    text = ((u"%%.%df %%s" % places_after_comma) % (scaled_value, scale_symbol)).rstrip()
    if kwargs.get("drop_zeroes"):
        text = text.rstrip("0").rstrip(".")
    return text



def metric_number_with_precision_list(values, *args, **kwargs):
    if not values:
        reference = 0
    else:
        reference = min([ abs(v) for v in values ])

    kwargs["base"] = 1000.0
    scale_symbol, places_after_comma, scale_factor = calculate_scaled_number(reference, *args, **kwargs)

    units = []
    scaled_values = []
    for value in values:
        scaled_value = float(value) / scale_factor
        scaled_values.append(("%%.%df" % places_after_comma) % scaled_value)

    return "%s" % scale_symbol, scaled_values


def file_size_human_readable(file_size):
    if file_size < 10000:
        return str(file_size)
    as_string = str(file_size)
    result = ""
    while len(as_string) > 3:
        result = "." + as_string[-3:] + result
        as_string = as_string[:-3]
    result = as_string + result
    return result

#.
#   .--Various Constants---------------------------------------------------.
#   |              ____                _              _                    |
#   |             / ___|___  _ __  ___| |_ __ _ _ __ | |_ ___              |
#   |            | |   / _ \| '_ \/ __| __/ _` | '_ \| __/ __|             |
#   |            | |__| (_) | | | \__ \ || (_| | | | | |_\__ \             |
#   |             \____\___/|_| |_|___/\__\__,_|_| |_|\__|___/             |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Various constants that are needed in more than one module. The      |
#   |  interface type for example are needed in WATO and in the Inventory  |
#   '----------------------------------------------------------------------'

seconds_per_day = 86400

interface_port_types = {
    1:   "other",
    2:   "regular1822",
    3:   "hdh1822",
    4:   "ddnX25",
    5:   "rfc877x25",
    6:   "ethernetCsmacd",
    7:   "iso88023Csmacd",
    8:   "iso88024TokenBus",
    9:   "iso88025TokenRing",
    10:  "iso88026Man",
    11:  "starLan",
    12:  "proteon10Mbit",
    13:  "proteon80Mbit",
    14:  "hyperchannel",
    15:  "fddi",
    16:  "lapb",
    17:  "sdlc",
    18:  "ds1",
    19:  "e1",
    20:  "basicISDN",
    21:  "primaryISDN",
    22:  "propPointToPointSerial",
    23:  "ppp",
    24:  "softwareLoopback",
    25:  "eon",
    26:  "ethernet3Mbit",
    27:  "nsip",
    28:  "slip",
    29:  "ultra",
    30:  "ds3",
    31:  "sip",
    32:  "frameRelay",
    33:  "rs232",
    34:  "para",
    35:  "arcnet",
    36:  "arcnetPlus",
    37:  "atm",
    38:  "miox25",
    39:  "sonet",
    40:  "x25ple",
    41:  "iso88022llc",
    42:  "localTalk",
    43:  "smdsDxi",
    44:  "frameRelayService",
    45:  "v35",
    46:  "hssi",
    47:  "hippi",
    48:  "modem",
    49:  "aal5",
    50:  "sonetPath",
    51:  "sonetVT",
    52:  "smdsIcip",
    53:  "propVirtual",
    54:  "propMultiplexor",
    55:  "ieee80212",
    56:  "fibreChannel",
    57:  "hippiInterface",
    58:  "frameRelayInterconnect",
    59:  "aflane8023",
    60:  "aflane8025",
    61:  "cctEmul",
    62:  "fastEther",
    63:  "isdn",
    64:  "v11",
    65:  "v36",
    66:  "g703at64k",
    67:  "g703at2mb",
    68:  "qllc",
    69:  "fastEtherFX",
    70:  "channel",
    71:  "ieee80211",
    72:  "ibm370parChan",
    73:  "escon",
    74:  "dlsw",
    75:  "isdns",
    76:  "isdnu",
    77:  "lapd",
    78:  "ipSwitch",
    79:  "rsrb",
    80:  "atmLogical",
    81:  "ds0",
    82:  "ds0Bundle",
    83:  "bsc",
    84:  "async",
    85:  "cnr",
    86:  "iso88025Dtr",
    87:  "eplrs",
    88:  "arap",
    89:  "propCnls",
    90:  "hostPad",
    91:  "termPad",
    92:  "frameRelayMPI",
    93:  "x213",
    94:  "adsl",
    95:  "radsl",
    96:  "sdsl",
    97:  "vdsl",
    98:  "iso88025CRFPInt",
    99:  "myrinet",
    100: "voiceEM",
    101: "voiceFXO",
    102: "voiceFXS",
    103: "voiceEncap",
    104: "voiceOverIp",
    105: "atmDxi",
    106: "atmFuni",
    107: "atmIma",
    108: "pppMultilinkBundle",
    109: "ipOverCdlc",
    110: "ipOverClaw",
    111: "stackToStack",
    112: "virtualIpAddress",
    113: "mpc",
    114: "ipOverAtm",
    115: "iso88025Fiber",
    116: "tdlc",
    117: "gigabitEthernet",
    118: "hdlc",
    119: "lapf",
    120: "v37",
    121: "x25mlp",
    122: "x25huntGroup",
    123: "trasnpHdlc",
    124: "interleave",
    125: "fast",
    126: "ip",
    127: "docsCableMaclayer",
    128: "docsCableDownstream",
    129: "docsCableUpstream",
    130: "a12MppSwitch",
    131: "tunnel",
    132: "coffee",
    133: "ces",
    134: "atmSubInterface",
    135: "l2vlan",
    136: "l3ipvlan",
    137: "l3ipxvlan",
    138: "digitalPowerline",
    139: "mediaMailOverIp",
    140: "dtm",
    141: "dcn",
    142: "ipForward",
    143: "msdsl",
    144: "ieee1394",
    145: "if-gsn",
    146: "dvbRccMacLayer",
    147: "dvbRccDownstream",
    148: "dvbRccUpstream",
    149: "atmVirtual",
    150: "mplsTunnel",
    151: "srp",
    152: "voiceOverAtm",
    153: "voiceOverFrameRelay",
    154: "idsl",
    155: "compositeLink",
    156: "ss7SigLink",
    157: "propWirelessP2P",
    158: "frForward",
    159: "rfc1483",
    160: "usb",
    161: "ieee8023adLag",
    162: "bgppolicyaccounting",
    163: "frf16MfrBundle",
    164: "h323Gatekeeper",
    165: "h323Proxy",
    166: "mpls",
    167: "mfSigLink",
    168: "hdsl2",
    169: "shdsl",
    170: "ds1FDL",
    171: "pos",
    172: "dvbAsiIn",
    173: "dvbAsiOut",
    174: "plc",
    175: "nfas",
    176: "tr008",
    177: "gr303RDT",
    178: "gr303IDT",
    179: "isup",
    180: "propDocsWirelessMaclayer",
    181: "propDocsWirelessDownstream",
    182: "propDocsWirelessUpstream",
    183: "hiperlan2",
    184: "propBWAp2Mp",
    185: "sonetOverheadChannel",
    186: "digitalWrapperOverheadChannel",
    187: "aal2",
    188: "radioMAC",
    189: "atmRadio",
    190: "imt",
    191: "mvl",
    192: "reachDSL",
    193: "frDlciEndPt",
    194: "atmVciEndPt",
    195: "opticalChannel",
    196: "opticalTransport",
    197: "propAtm",
    198: "voiceOverCable",
    199: "infiniband",
    200: "teLink",
    201: "q2931",
    202: "virtualTg",
    203: "sipTg",
    204: "sipSig",
    205: "docsCableUpstreamChannel",
    206: "econet",
    207: "pon155",
    208: "pon622",
    209: "bridge",
    210: "linegroup",
    211: "voiceEMFGD",
    212: "voiceFGDEANA",
    213: "voiceDID",
    214: "mpegTransport",
    215: "sixToFour",
    216: "gtp",
    217: "pdnEtherLoop1",
    218: "pdnEtherLoop2",
    219: "opticalChannelGroup",
    220: "homepna",
    221: "gfp",
    222: "ciscoISLvlan",
    223: "actelisMetaLOOP",
    224: "fcipLink",
    225: "rpr",
    226: "qam",
    227: "lmp",
    228: "cblVectaStar",
    229: "docsCableMCmtsDownstream",
    230: "adsl2",
    231: "macSecControlledIF",
    232: "macSecUncontrolledIF",
    233: "aviciOpticalEther",
    234: "atmbond",
    235: "voiceFGDOS",
    236: "mocaVersion1",
    237: "ieee80216WMAN",
    238: "adsl2plus",
    239: "dvbRcsMacLayer",
    240: "dvbTdm",
    241: "dvbRcsTdma",
    242: "x86Laps",
    243: "wwanPP",
    244: "wwanPP2",
    245: "voiceEBS",
    246: "ifPwType",
    247: "ilan",
    248: "pip",
    249: "aluELP",
    250: "gpon",
    251: "vdsl2",
    252: "capwapDot11Profile",
    253: "capwapDot11Bss",
    254: "capwapWtpVirtualRadio",
    255: "bits",
    256: "docsCableUpstreamRfPort",
    257: "cableDownstreamRfPort",
    258: "vmwareVirtualNic",
    259: "ieee802154",
    260: "otnOdu",
    261: "otnOtu",
    262: "ifVfiType",
    263: "g9981",
    264: "g9982",
    265: "g9983",
    266: "aluEpon",
    267: "aluEponOnu",
    268: "aluEponPhysicalUni",
    269: "aluEponLogicalLink",
    270: "aluGponOnu",
    271: "aluGponPhysicalUni",
    272: "vmwareNicTeam",
    277: "docsOfdmDownstream",
    278: "docsOfdmaUpstream",
    279: "gfast",
    280: "sdci",
    281: "xboxWireless",
    282: "fastdsl",
    283: "docsCableScte55d1FwdOob",
    284: "docsCableScte55d1RetOob",
    285: "docsCableScte55d2DsOob",
    286: "docsCableScte55d2UsOob",
    287: "docsCableNdf",
    288: "docsCableNdr",
    289: "ptm",
    290: "ghn",
}

# For usage in Dropdown choices an the like
def dict_choices(types):
    return [ (str(type_id), "%d - %s" % (type_id, type_name))
        for (type_id, type_name)
        in sorted(types.items()) ]

interface_port_type_choices = dict_choices(interface_port_types)


#.
#   .--Floating Options----------------------------------------------------.
#   |                _____ _             _   _                             |
#   |               |  ___| | ___   __ _| |_(_)_ __   __ _                 |
#   |               | |_  | |/ _ \ / _` | __| | '_ \ / _` |                |
#   |               |  _| | | (_) | (_| | |_| | | | | (_| |                |
#   |               |_|   |_|\___/ \__,_|\__|_|_| |_|\__, |                |
#   |                                                |___/                 |
#   |                   ___        _   _                                   |
#   |                  / _ \ _ __ | |_(_) ___  _ __  ___                   |
#   |                 | | | | '_ \| __| |/ _ \| '_ \/ __|                  |
#   |                 | |_| | |_) | |_| | (_) | | | \__ \                  |
#   |                  \___/| .__/ \__|_|\___/|_| |_|___/                  |
#   |                       |_|                                            |
#   +----------------------------------------------------------------------+
#   |  Rendering of filter boxes like (used by availability options and    |
#   |  Werks).
#   '----------------------------------------------------------------------'

def begin_floating_options(div_id, is_open):
    html.open_div(id_=div_id, class_=["view_form"], style="display: none" if not is_open else None)
    html.open_table(class_=["filterform"], cellpadding="0", cellspacing="0", border="0")
    html.open_tr()
    html.open_td()

def end_floating_options(reset_url=None):
    html.close_td()
    html.close_tr()
    html.open_tr()
    html.open_td()
    html.button("apply", _("Apply"), "submit")
    if reset_url:
        html.buttonlink(reset_url, _("Reset to defaults"))

    html.close_td()
    html.close_tr()
    html.close_table()
    html.close_div()

def render_floating_option(name, height, varprefix, valuespec, value):
    html.open_div(class_=["floatfilter", height, name])
    html.div(valuespec.title(), class_=["legend"])
    html.open_div(class_=["content"])
    valuespec.render_input(varprefix + name, value)
    html.close_div()
    html.close_div()


