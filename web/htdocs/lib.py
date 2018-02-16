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
from cmk.regex import regex
import cmk.store as store
import cmk.paths

from log import logger

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


def log_exception(msg=None):
    if msg is None:
        msg = _('Internal error')
    logger.error("%s %s: %s" % (html.request_uri(), msg, traceback.format_exc()))


# TODO: Remove this helper function. Replace with explicit checks and covnersion
# in using code.
def savefloat(f):
    try:
        return float(f)
    except:
        return 0.0


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


def age_human_readable(secs):
    if secs < 0:
        return "- " + age_human_readable(-secs)
    elif secs > 0 and secs < 1: # ms
        return physical_precision(secs, 3, _("s"))
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
