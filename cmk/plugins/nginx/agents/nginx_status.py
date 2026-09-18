#!/usr/bin/env python3
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

try:
    from collections.abc import Container, Sequence

    _ = Container, Sequence  # make ruff happy
except ImportError:
    # We need typing only for testing
    pass

__version__ = "3.0.0b1"

USER_AGENT = "checkmk-agent-nginx_status-" + __version__


import urllib  # noqa: E402

urllib.getproxies = dict  # type: ignore[attr-defined]


def extract_stats_from_iproute2(lines, ssl_ports):
    # type: (Sequence[str], Container[int]) -> list[tuple[str, str, int]]
    results = []

    line_maxsplit = 5
    seen_process_ids = set()
    process_regex = re.compile(r'^\w+:\(\("(nginx|nginx.conf)",pid=(\d+).*$')

    for line in lines[1:]:  # skip column headers
        parts = line.split(None, line_maxsplit)
        if len(parts) < 6:  # kernel-owned sockets (e.g. nfsd) have no process column
            continue
        _, _, _, local_addr, _, process_info = parts

        process_match = process_regex.match(process_info)
        if process_match is None:
            continue

        pid = process_match.group(2)
        if pid in seen_process_ids:
            continue

        seen_process_ids.add(pid)

        raw_host, raw_port = local_addr.rsplit(":", 1)

        if raw_host == "0.0.0.0":
            host = "127.0.0.1"
        elif raw_host == "[::]":
            host = "::1"
        else:
            host = raw_host

        port = int(raw_port)
        proto = "https" if port in ssl_ports else "http"

        results.append((proto, host, port))

    return results


def extract_stats_from_netstat(lines, ssl_ports):
    # type: (Sequence[str], Container[int]) -> list[tuple[str, str, int]]
    pids = []
    results = []
    for netstat_line in lines:
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


def try_detect_servers(ssl_ports):
    # type: (Container[int]) -> list[tuple[str, str, int]]
    """Fetch network statistics for nginx server(s).

    Try and fetch the stats from the `ss` utility. If tool not available, fallback to the `netstat`
    utility (deprecated). If both network utilities are unavailable or nginx is not running on the
    machine, no statistics will be returned.
    """
    iproute2_lines = os.popen("ss -tlnp 2>/dev/null").readlines()
    if iproute2_lines:
        return extract_stats_from_iproute2(iproute2_lines, ssl_ports)

    netstat_lines = os.popen("netstat -tlnp 2>/dev/null").readlines()
    return extract_stats_from_netstat(netstat_lines, ssl_ports)


def _is_ip_v6_address(address):
    # type: (str) -> bool
    """Check if the given address is an IPv6 address."""
    try:
        return ipaddress.ip_address(address).version == 6
    except ValueError:
        return False


def _make_url(proto, address, port, page):
    # type: (str, str, int, str) -> str
    """Construct a URL from its components, taking care of IPv6 addresses."""
    if _is_ip_v6_address(address):
        return "%s://[%s]:%s/%s" % (proto, address, port, page)
    return "%s://%s:%s/%s" % (proto, address, port, page)


def parse_ssl_ports(raw):
    # type: (object) -> list[int]
    if not isinstance(raw, list) or not all(isinstance(port, int) for port in raw):
        raise ValueError("ssl_ports must be a list of ints, got %r" % (raw,))
    return [port for port in raw if isinstance(port, int)]


def parse_servers(raw):
    # type: (object) -> list[tuple[str, str, int, str]] | None
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError("servers must be a list, got %r" % (raw,))
    return [_parse_server(server) for server in raw]


def _parse_server(raw_server):
    # type: (object) -> tuple[str, str, int, str]
    if isinstance(raw_server, tuple):
        return _parse_server_tuple(raw_server)
    if isinstance(raw_server, dict):
        return _parse_server_dict(raw_server)
    raise ValueError("Invalid server config object. Expected tuple or dict")


def _parse_server_dict(raw_server_dict):
    # type: (dict[str, object]) -> tuple[str, str, int, str]
    proto = raw_server_dict.get("protocol")
    address = raw_server_dict.get("address")
    port = raw_server_dict.get("port")
    page = raw_server_dict.get("page", "nginx_status")
    if not (
        isinstance(proto, str)
        and isinstance(address, str)
        and isinstance(port, int)
        and isinstance(page, str)
    ):
        raise ValueError("invalid server dict entry %r" % (raw_server_dict,))
    return proto, address, port, page


def _parse_server_tuple(raw_server_tuple):
    # type: (tuple[object, ...]) -> tuple[str, str, int, str]
    if len(raw_server_tuple) != 3:
        raise ValueError(
            "Wrong length of server tuple %r. Expected 3 elements" % (raw_server_tuple,)
        )
    proto, address, port = raw_server_tuple
    if not (isinstance(proto, str) and isinstance(address, str) and isinstance(port, int)):
        raise ValueError("invalid server tuple entry %r" % (raw_server_tuple,))
    return proto, address, port, "nginx_status"


def main():
    # type: () -> None
    config_dir = os.getenv("MK_CONFDIR", "/etc/check_mk")
    config_file = config_dir + "/nginx_status.cfg"

    config = {}  # type: dict[str, object]
    if os.path.exists(config_file):
        with open(config_file) as open_config_file:
            config_src = open_config_file.read()
            exec(config_src, globals(), config)  # nosec B102 # BNS:a29406
    # None or list of (proto, ipaddress, port) tuples.
    # proto is 'http' or 'https'
    try:
        ssl_ports = parse_ssl_ports(config.get("ssl_ports", [443]))
        servers = parse_servers(config.get("servers"))
    except ValueError as e:
        sys.stderr.write("%s: %s\n" % (config_file, e))
        sys.exit(1)

    if servers is None:
        servers = [
            (proto, address, port, "nginx_status")
            for proto, address, port in try_detect_servers(ssl_ports)
        ]

    if not servers:
        sys.exit(0)

    sys.stdout.write("<<<nginx_status>>>\n")
    for proto, address, port, page in servers:
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
                    fd = urlopen(_make_url("http", address, port, page))  # nosec B310 # BNS:6b61d9
                else:
                    raise

            for line in fd.read().decode("utf-8").split("\n"):
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
