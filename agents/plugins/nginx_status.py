#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Checkmk-Agent-Plug-in - Nginx Server Status
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

import ipaddress
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

__version__ = "2.4.0p21"

USER_AGENT = "checkmk-agent-nginx_status-" + __version__

if sys.version_info < (2, 6):
    sys.stderr.write("ERROR: Python 2.5 is not supported. Please use Python 2.6 or newer.\n")
    sys.exit(1)

if sys.version_info[0] == 2:
    import urllib2  # pylint: disable=import-error

    urllib2.getproxies = lambda: {}
else:
    import urllib

    urllib.getproxies = lambda: {}  # type: ignore[attr-defined]

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    binary_type = bytes
else:
    text_type = unicode  # pylint: disable=undefined-variable # noqa: F821
    binary_type = str


# Borrowed from six
def ensure_str(s, encoding="utf-8", errors="strict"):
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


def try_detect_servers(ssl_ports):
    pids = []
    results = []
    for netstat_line in os.popen("netstat -tlnp 2>/dev/null").readlines():
        parts = netstat_line.split()
        # Skip lines with wrong format
        if len(parts) < 7 or "/" not in parts[6]:
            continue

        pid, proc = parts[6].split("/", 1)
        to_replace = re.compile("^.*/")
        proc = to_replace.sub("", proc)

        procs = ["nginx", "nginx:", "nginx.conf"]
        # the pid/proc field length is limited to 19 chars. Thus in case of
        # long PIDs, the process names are stripped of by that length.
        # Workaround this problem here
        procs = [p[: 19 - len(pid) - 1] for p in procs]

        # Skip unwanted processes
        if proc not in procs:
            continue

        # Add only the first found port of a single server process
        if pid in pids:
            continue
        pids.append(pid)

        server_proto = "http"
        server_address, _server_port = parts[3].rsplit(":", 1)
        server_port = int(_server_port)

        # Use localhost when listening globally
        if server_address == "0.0.0.0":
            server_address = "127.0.0.1"
        elif server_address == "::":
            server_address = "::1"

        # Switch protocol if port is SSL port. In case you use SSL on another
        # port you would have to change/extend the ssl_port list
        if server_port in ssl_ports:
            server_proto = "https"

        results.append((server_proto, server_address, server_port))

    return results


def _is_ip_v6_address(address: str) -> bool:
    """Check if the given address is an IPv6 address."""
    try:
        return ipaddress.ip_address(address).version == 6
    except ValueError:
        return False


def _make_url(proto: str, address: str, port: int, page: str) -> str:
    """Construct a URL from its components, taking care of IPv6 addresses."""
    if _is_ip_v6_address(address):
        return "%s://[%s]:%s/%s" % (proto, address, port, page)
    return "%s://%s:%s/%s" % (proto, address, port, page)


def main():  # pylint: disable=too-many-branches
    config_dir = os.getenv("MK_CONFDIR", "/etc/check_mk")
    config_file = config_dir + "/nginx_status.cfg"

    config = {}  # type: dict
    if os.path.exists(config_file):
        with open(config_file) as open_config_file:
            config_src = open_config_file.read()
            exec(config_src, globals(), config)  # nosec B102 # BNS:a29406
    # None or list of (proto, ipaddress, port) tuples.
    # proto is 'http' or 'https'
    servers = config.get("servers")
    ssl_ports = config.get("ssl_ports", [443])

    if servers is None:
        servers = try_detect_servers(ssl_ports)

    if not servers:
        sys.exit(0)

    sys.stdout.write("<<<nginx_status>>>\n")
    for server in servers:
        if isinstance(server, tuple):
            proto, address, port = server
            page = "nginx_status"
        else:
            proto = server["protocol"]
            address = server["address"]
            port = server["port"]
            page = server.get("page", "nginx_status")

        try:
            if proto not in ["http", "https"]:
                raise ValueError("Scheme '%s' is not allowed" % proto)

            url = _make_url(proto, address, port, page)
            # Try to fetch the status page for each server
            try:
                request = Request(url, headers={"Accept": "text/plain", "User-Agent": USER_AGENT})
                fd = urlopen(request)  # nosec B310 # BNS:6b61d9
            except URLError as e:
                if "SSL23_GET_SERVER_HELLO:unknown protocol" in str(e):
                    # HACK: workaround misconfigurations where port 443 is used for
                    # serving non ssl secured http
                    fd = urlopen(  # pylint: disable=consider-using-with
                        _make_url("http", address, port, page)
                    )  # nosec B310 # BNS:6b61d9
                else:
                    raise

            for line in ensure_str(fd.read()).split("\n"):
                if not line or line.isspace():
                    continue
                if line.lstrip()[0] == "<":
                    # seems to be html output. Skip this server.
                    break
                sys.stdout.write("%s %s %s\n" % (address, port, line))
        except HTTPError as e:
            sys.stderr.write("HTTP-Error (%s:%d): %s %s\n" % (address, port, e.code, e))

        except Exception as e:
            sys.stderr.write("Exception (%s:%d): %s\n" % (address, port, e))


if __name__ == "__main__":
    main()
