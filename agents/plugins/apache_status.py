#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__version__ = "2.1.0b10"

# Checkmk-Agent-Plugin - Apache Server Status
#
# Fetches the server-status page from detected or configured apache
# processes to gather status information about this apache process.
#
# To make this agent plugin work you have to load the status_module
# into your apache process. It is also needed to enable the "server-status"
# handler below the URL "/server-status".
#
# By default this plugin tries to detect all locally running apache processes
# and to monitor them. If this is not good for your environment you might
# create an apache_status.cfg file in MK_CONFDIR and populate the servers
# list to prevent executing the detection mechanism.
#
# It is also possible to override or extend the ssl_ports variable to make the
# check contact other ports than 443 with HTTPS requests.

import os
import re
import sys

if sys.version_info < (2, 6):
    sys.stderr.write("ERROR: Python 2.5 is not supported. Please use Python 2.6 or newer.\n")
    sys.exit(1)

if sys.version_info[0] == 2:
    from urllib2 import HTTPError, Request, URLError, urlopen  # pylint: disable=import-error
else:
    from urllib.error import HTTPError, URLError  # pylint: disable=import-error,no-name-in-module
    from urllib.request import Request, urlopen  # pylint: disable=import-error,no-name-in-module


def get_config():
    config_dir = os.getenv("MK_CONFDIR", "/etc/check_mk")
    config_file = config_dir + "/apache_status.conf"

    if not os.path.exists(config_file):
        config_file = config_dir + "/apache_status.cfg"

    # None or tuple of ((proto, cacert), ipaddress, port, instance_name).
    #  - proto is 'http' or 'https'
    #  - cacert is a path to a CA certificate, or None
    #  - port may be None
    #  - instance_name may be the empty string
    config = {
        "servers": None,
        "ssl_ports": [443],
    }
    if os.path.exists(config_file):
        with open(config_file) as config_file_obj:
            exec(config_file_obj.read(), config)
    return config


def get_instance_name(host, port_nr, conf):
    """
    Get Instance name either from config
    or from detected sites
    """
    search = "%s:%s" % (host, port_nr)
    if search in conf["custom"]:
        return conf["custom"][search]
    if "omd_sites" in conf:
        return conf["omd_sites"].get(search, host)
    return ""


def try_detect_servers(ssl_ports):
    results = []

    for netstat_line in os.popen("netstat -tlnp 2>/dev/null").readlines():
        parts = netstat_line.split()
        # Skip lines with wrong format
        if len(parts) < 7 or "/" not in parts[6]:
            continue

        pid, proc = parts[6].split("/", 1)
        to_replace = re.compile("^.*/")
        proc = to_replace.sub("", proc)

        procs = [
            "apache2",
            "httpd",
            "httpd-prefork",
            "httpd2-prefork",
            "httpd2-worker",
            "httpd.worker",
            "httpd-event",
            "fcgi-pm",
        ]
        # the pid/proc field length is limited to 19 chars. Thus in case of
        # long PIDs, the process names are stripped of by that length.
        # Workaround this problem here
        procs = [p[: 19 - len(pid) - 1] for p in procs]

        # Skip unwanted processes
        if proc not in procs:
            continue

        server_address, _server_port = parts[3].rsplit(":", 1)
        server_port = int(_server_port)

        # Use localhost when listening globally
        if server_address == "0.0.0.0":
            server_address = "127.0.0.1"
        elif server_address == "::":
            server_address = "[::1]"
        elif ":" in server_address:
            server_address = "[%s]" % server_address

        # Switch protocol if port is SSL port. In case you use SSL on another
        # port you would have to change/extend the ssl_port list
        if server_port in ssl_ports:
            scheme = "https"
        else:
            scheme = "http"

        results.append((scheme, server_address, server_port))

    return results


def _unpack(config):
    if isinstance(config, tuple):
        if len(config) == 3:
            # Append empty instance name.
            config += ("",)
        if not isinstance(config[0], tuple):
            # Set cacert option.
            config = ((config[0], None),) + config[1:]
        return config + ("server-status",)
    return (
        (config["protocol"], config.get("cafile", None)),
        config["address"],
        config["port"],
        config.get("instance", ""),
        config.get("page", "server-status"),
    )


def get_ssl_no_verify_context():
    import ssl

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def get_response_body(proto, cafile, address, portspec, page):
    response = get_response(proto, cafile, address, portspec, page)
    return response.read().decode(get_response_charset(response))


# 'context' parameter was added to urlopen in python 3.5 / 2.7
def urlopen_with_ssl(request, timeout):
    result = None
    if (sys.version_info[0] == 3 and sys.version_info >= (3, 5)) or (
        sys.version_info[0] == 2 and sys.version_info >= (2, 7)
    ):
        result = urlopen(request, context=get_ssl_no_verify_context(), timeout=timeout)
    else:
        if sys.version_info[0] == 2:
            from urllib2 import (  # pylint: disable=import-error # isort: skip
                build_opener,
                HTTPSHandler,
                install_opener,
            )
        else:
            from urllib.request import (  # pylint: disable=import-error,no-name-in-module # isort: skip
                build_opener,
                HTTPSHandler,
                install_opener,
            )
        install_opener(build_opener(HTTPSHandler()))
        result = urlopen(request, timeout=timeout)
    return result


def get_response(proto, cafile, address, portspec, page):
    url = "%s://%s%s/%s?auto" % (proto, address, portspec, page)
    request = Request(url, headers={"Accept": "text/plain"})
    is_local = address in ("127.0.0.1", "[::1]", "localhost")
    # Try to fetch the status page for each server
    try:
        if proto == "https" and cafile:
            return urlopen(request, cafile=cafile, timeout=5)
        if proto == "https" and is_local:
            return urlopen_with_ssl(request, timeout=5)
        return urlopen(request, timeout=5)
    except URLError as exc:
        if "unknown protocol" in str(exc):
            # HACK: workaround misconfigurations where port 443 is used for
            # serving non ssl secured http
            url = "http://%s%s/server-status?auto" % (address, portspec)
            return urlopen(url, timeout=5)
        raise


def get_response_charset(response):
    if sys.version_info[0] == 2:
        charset = response.headers.getparam("charset")
    else:
        charset = response.info().get_content_charset()
    return charset or "utf-8"


def get_instance_name_map(cfg):
    instance_name_map = {"custom": cfg.get("CUSTOM_ADDRESS_OVERWRITE", {})}
    if cfg.get("ENABLE_OMD_SITE_DETECTION") and os.path.exists("/usr/bin/omd"):
        for line in os.popen("omd sites").readlines():
            sitename = line.split()[0]
            path = "/opt/omd/sites/%s/etc/apache/listen-port.conf" % sitename
            with open(path) as site_cfg_handle:
                site_raw_conf = site_cfg_handle.readlines()
                site_conf = site_raw_conf[-2].strip().split()[1]
                instance_name_map.setdefault("omd_sites", {})
                instance_name_map["omd_sites"][site_conf] = sitename
    return instance_name_map


def main():
    config = get_config()
    servers = config["servers"]
    ssl_ports = config["ssl_ports"]

    if servers is None:
        servers = try_detect_servers(ssl_ports)

    if not servers:
        return 0

    sys.stdout.write("<<<apache_status:sep(124)>>>\n")
    for server in servers:
        (proto, cafile), address, port, name, page = _unpack(server)
        portspec = ":%d" % port if port else ""

        try:
            response_body = get_response_body(proto, cafile, address, portspec, page)
            for line in response_body.split("\n"):
                if not line.strip():
                    continue
                if line.lstrip()[0] == "<":
                    # Seems to be html output. Skip this server.
                    break
                if not name:
                    name = get_instance_name(address, port, get_instance_name_map(config))
                sys.stdout.write("%s|%s|%s|%s\n" % (address, port, name, line))
        except HTTPError as exc:
            sys.stderr.write("HTTP-Error (%s%s): %s %s\n" % (address, portspec, exc.code, exc))

        except Exception as exc:  # pylint: disable=broad-except
            sys.stderr.write("Exception (%s%s): %s\n" % (address, portspec, exc))

    return 0


if __name__ == "__main__":
    sys.exit(main())
