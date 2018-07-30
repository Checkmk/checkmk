#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2016             mk@mathias-kettner.de |
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

"""This module contains constants and functions for neat output formating
on ttys while being compatible when the command is not attached to a TTY"""

import fcntl
import sys
import struct
import termios
import io

if sys.stdout.isatty():
    red       = '\033[31m'
    green     = '\033[32m'
    yellow    = '\033[33m'
    blue      = '\033[34m'
    magenta   = '\033[35m'
    cyan      = '\033[36m'
    white     = '\033[37m'
    bgblue    = '\033[44m'
    bgmagenta = '\033[45m'
    bgwhite   = '\033[47m'
    bold      = '\033[1m'
    underline = '\033[4m'
    normal    = '\033[0m'
else:
    red       = ''
    green     = ''
    yellow    = ''
    blue      = ''
    magenta   = ''
    cyan      = ''
    white     = ''
    bgblue    = ''
    bgmagenta = ''
    bold      = ''
    underline = ''
    normal    = ''

ok = green + bold + 'OK' + normal

states = {
    0: green,
    1: yellow,
    2: red,
    3: magenta
}

def colorset(fg=-1, bg=-1, attr=-1):
    if not sys.stdout.isatty():
        return ""

    if attr >= 0:
        return "\033[3%d;4%d;%dm" % (fg, bg, attr)
    elif bg >= 0:
        return "\033[3%d;4%dm" % (fg, bg)
    elif fg >= 0:
        return "\033[3%dm" % fg
    else:
        return normal


def get_size():
    try:
        ws = struct.pack("HHHH", 0, 0, 0, 0)
        ws = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, ws)
        lines, columns = struct.unpack("HHHH", ws)[:2]
        if lines > 0 and columns > 0:
            return lines, columns
    except io.UnsupportedOperation:
        pass # When sys.stdout is StringIO() or similar, then .fileno() is not available
    except IOError, e:
        if e.errno == 25:
            # Inappropriate ioctl for device: Occurs when redirecting output
            pass
        elif e.errno == 22:
            # Invalid argument: Occurs e.g. when executing from cron
            pass
        else:
            raise

    return (24, 80)


# TODO: Is this a good place?
# TODO: Cleanup this function!
def print_table(headers, colors, rows, indent = ""):
    lengths = [ len(h) for h in headers ]

    def make_utf8(x):
        if type(x) == unicode:
            return x.encode('utf-8')
        else:
            return "%s" % (x,)

    for row in rows:
        lengths = [ max(len(make_utf8(c)), l) for c, l in zip(row, lengths) ]

    fmt = indent
    sep = ""
    for l,c in zip(lengths, colors):
        fmt += c + sep + "%-" + str(l) + "s" + normal
        sep = " "

    first = True
    fmt += "\n"
    for row in [ headers ] + rows:
        sys.stdout.write(fmt % tuple([ make_utf8(c) for c in row[:len(headers)] ]))
        if first:
            first = False
            sys.stdout.write(fmt % tuple([ "-" * l for l in lengths ]))
