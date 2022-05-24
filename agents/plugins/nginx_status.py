#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__version__ = "2.0.0p26"

# Checkmk-Agent-Plugin - Nginx Server Status
#
# Fetches the stub nginx_status page from detected or configured nginx
# processes to gather status information about this process.
#
# Take a look at the check man page for details on how to configure this
# plugin and check.
#
# By default this plugin tries to detect all locally running processes
# and to monitor them. If this is not good for your environment you might
# create an nginx_status.cfg file in MK_CONFDIR and populate the servers
# list to prevent executing the detection mechanism.

import os
import re
import sys

if sys.version_info < (2, 6):
    sys.stderr.write("ERROR: Python 2.5 is not supported. Please use Python 2.6 or newer.\n")
    sys.exit(1)

if sys.version_info[0] == 2:
    from urllib2 import Request, urlopen  # pylint: disable=import-error
    from urllib2 import URLError, HTTPError  # pylint: disable=import-error
    import urllib2  # pylint: disable=import-error
    urllib2.getproxies = lambda: {}
else:
    from urllib.request import Request, urlopen  # pylint: disable=import-error,no-name-in-module
    from urllib.error import URLError, HTTPError  # pylint: disable=import-error,no-name-in-module
    import urllib
    urllib.getproxies = lambda: {}  # type: ignore[attr-defined]

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    binary_type = bytes
else:
    text_type = unicode  # pylint: disable=undefined-variable
    binary_type = str


# Borrowed from six
def ensure_str(s, encoding='utf-8', errors='strict'):
    """Coerce *s* to `str`.

    For Python 2:
      - `unicode` -> encoded to `str`
      - `str` -> `str`

    For Python 3:
      - `str` -> `str`
      - `bytes` -> decoded to `str`
    """
    if not isinstance(s, (text_type, binary_type)):
        raise TypeError("not expecting type '%s'" % type(s))
    if PY2 and isinstance(s, text_type):
        s = s.encode(encoding, errors)
    elif PY3 and isinstance(s, binary_type):
        s = s.decode(encoding, errors)
    return s


config_dir = os.getenv("MK_CONFDIR", "/etc/check_mk")
config_file = config_dir + "/nginx_status.cfg"

# None or list of (proto, ipaddress, port) tuples.
# proto is 'http' or 'https'
servers = None
ssl_ports = [
    443,
]

if os.path.exists(config_file):
    exec(open(config_file).read())


def try_detect_servers():
    pids = []
    results = []
    for netstat_line in os.popen('netstat -tlnp 2>/dev/null').readlines():
        parts = netstat_line.split()
        # Skip lines with wrong format
        if len(parts) < 7 or '/' not in parts[6]:
            continue

        pid, proc = parts[6].split('/', 1)
        to_replace = re.compile('^.*/')
        proc = to_replace.sub('', proc)

        procs = ['nginx', 'nginx:', 'nginx.conf']
        # the pid/proc field length is limited to 19 chars. Thus in case of
        # long PIDs, the process names are stripped of by that length.
        # Workaround this problem here
        procs = [p[:19 - len(pid) - 1] for p in procs]

        # Skip unwanted processes
        if proc not in procs:
            continue

        # Add only the first found port of a single server process
        if pid in pids:
            continue
        pids.append(pid)

        server_proto = 'http'
        server_address, _server_port = parts[3].rsplit(':', 1)
        server_port = int(_server_port)

        # Use localhost when listening globally
        if server_address == '0.0.0.0':
            server_address = '127.0.0.1'
        elif server_address == '::':
            server_address = '::1'

        # Switch protocol if port is SSL port. In case you use SSL on another
        # port you would have to change/extend the ssl_port list
        if server_port in ssl_ports:
            server_proto = 'https'

        results.append((server_proto, server_address, server_port))

    return results


if servers is None:
    servers = try_detect_servers()

if not servers:
    sys.exit(0)

sys.stdout.write('<<<nginx_status>>>\n')
for server in servers:
    if isinstance(server, tuple):
        proto, address, port = server
        page = 'nginx_status'
    else:
        proto = server['protocol']
        address = server['address']
        port = server['port']
        page = server.get('page', 'nginx_status')

    try:
        url = '%s://%s:%s/%s' % (proto, address, port, page)
        # Try to fetch the status page for each server
        try:
            request = Request(url, headers={"Accept": "text/plain"})
            fd = urlopen(request)
        except URLError as e:
            if 'SSL23_GET_SERVER_HELLO:unknown protocol' in str(e):
                # HACK: workaround misconfigurations where port 443 is used for
                # serving non ssl secured http
                url = 'http://%s:%s/%s' % (address, port, page)
                fd = urlopen(url)
            else:
                raise

        for line in ensure_str(fd.read()).split('\n'):
            if not line.strip():
                continue
            if line.lstrip()[0] == '<':
                # seems to be html output. Skip this server.
                break
            sys.stdout.write("%s %s %s\n" % (address, port, line))
    except HTTPError as e:
        sys.stderr.write('HTTP-Error (%s:%d): %s %s\n' % (address, port, e.code, e))

    except Exception as e:
        sys.stderr.write('Exception (%s:%d): %s\n' % (address, port, e))
