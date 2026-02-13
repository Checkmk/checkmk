#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
import shlex
import subprocess
import sys
from pathlib import Path

from omdlib.config_choices import ApacheTCPAddrHasError, NetworkPortHasError
from omdlib.console import show_success
from omdlib.utils import is_containerized
from omdlib.version_info import VersionInfo

__all__ = [
    "register_with_system_apache",
    "unregister_from_system_apache",
    "delete_apache_hook",
    "is_apache_hook_up_to_date",
]


def register_with_system_apache(
    version_info: VersionInfo,
    apache_config: Path,
    site_name: str,
    apache_tcp_addr: str,
    apache_tcp_port: str,
    apache_reload: bool,
    verbose: bool,
) -> None:
    """Apply the site specific configuration to the system global apache

    Basically update the apache configuration to register the mod_proxy configuration
    and the reload or restart the system apache.

    Root permissions are needed to make this work.
    """
    if (err := ApacheTCPAddrHasError()(apache_tcp_addr)).is_error():
        sys.exit(f"Invalid value for '{apache_tcp_addr}' for APACHE_TCP_ADDR'. {err.error}\n")
    if (err := NetworkPortHasError()(apache_tcp_port)).is_error():
        sys.exit(f"Invalid value for '{apache_tcp_port}' for APACHE_TCP_PORT'. {err.error}\n")

    create_apache_hook(
        apache_config, site_name, apache_tcp_addr, apache_tcp_port, apache_hook_version()
    )
    apply_apache_config(version_info, apache_reload, verbose)


def unregister_from_system_apache(
    version_info: VersionInfo, apache_config: Path, apache_reload: bool, verbose: bool
) -> None:
    delete_apache_hook(apache_config)
    apply_apache_config(version_info, apache_reload, verbose)


def apply_apache_config(version_info: VersionInfo, apache_reload: bool, verbose: bool) -> None:
    if apache_reload:
        reload_apache(version_info)
    else:
        restart_apache(version_info, verbose)


def is_apache_hook_up_to_date(apache_config: Path) -> bool:
    with open(apache_config) as f:
        header = f.readline()
        return header == apache_hook_header(apache_hook_version()) + "\n"


def apache_hook_header(version: int) -> str:
    return f"# version: {version}"


def apache_hook_version() -> int:
    return 3


def _site_not_started_html(site_name: str) -> str:
    """Self-contained HTML for the 503 error page when a site's Apache is not running.

    Everything is inlined (CSS, SVG logo) because the site has no running assets to serve.
    Must avoid double-quote characters — Apache's ErrorDocument wraps this in double quotes.
    """
    if os.path.exists("/etc/cma/cma.conf"):
        instructions = "<p>Start it via the Webconf.</p>"
    elif is_containerized():
        instructions = "<p>Restart the container to access the web interface.</p>"
    else:
        instructions = (
            "<p>Start it to access the web interface.</p>"
            "<p style='display: flex; gap: 5px; justify-content: center;'>Run <code>omd start </code> as the site user.</p>"
        )

    # fmt: off
    header = (
        "<!DOCTYPE html>"
        "<html lang='en'>"
        "<head>"
        "<title>Checkmk: Site Not Started</title>"
        "<meta http-equiv='refresh' content='60'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<link rel='icon' type='image/svg+xml' href='data:image/svg+xml;base64,"
        "PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyOSAzNiI+"
        "PHBhdGggZmlsbD0iIzE1ZDFhMCIgZD0ibTE0LjE4NzEsMS42NDEzbDE0LjEzNzEsOC4xODI0djE2LjM1"
        "NjZsLTE0LjEzNzEsOC4xNzgzTC4wNSwyNi4xNzYyVjkuODE5NkwxNC4xODcxLDEuNjQxM1pNNC45MDcz"
        "LDEzLjU1MDZ2NS40Mjg3bDYuNjU4Ni00LjMwMjR2MTEuMjAxMmwyLjYyNTMsMS41MTU2LDIuNjIxMi0x"
        "LjUxNTZ2LTExLjIwMTJsNi42NTQ0LDQuMzAyNHYtNS40Mjg3bC05LjI3OTgtNS44MTM4LTkuMjc5OCw1"
        "LjgxMzhoMFoiLz48L3N2Zz4='>"
        "<style>"
        "*{margin:0;padding:0;box-sizing:border-box}"
        "body{background:rgb(28,34,40);color:#fff;"
        "font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;"
        "display:flex;justify-content:center;align-items:center;min-height:100vh}"
        ".c{text-align:center;background:rgb(32,39,46);border-radius:12px;"
        "padding:48px;max-width:520px;width:90%}"
        ".l{margin-bottom:32px}"
        "h1{font-size:24px;font-weight:600;margin-bottom:16px}"
        "p{color:rgba(255,255,255,0.6);font-size:15px;line-height:1.6;margin-bottom:12px}"
        "code{background:rgba(255,255,255,0.1);padding:2px 8px;border-radius:4px;"
        "font-family:SFMono-Regular,Consolas,Liberation Mono,Menlo,monospace;"
        "font-size:14px;color:#15d1a0}"
        ".r{color:rgba(255,255,255,0.35);font-size:13px;margin-top:24px}"
        "</style>"
        "</head>"
        "<body>"
        "<div class='c'>"
        "<div class='l'>"
        "<svg xmlns='http://www.w3.org/2000/svg' width='180' height='54' viewBox='0 0 120 36'>"
        "<path fill='#15d1a0' d='m41.6868,24.1058c-2.7785,0-4.3314-1.5735-4.3314-4.497v-2.1119"
        "c0-2.9235,1.5363-4.497,4.3107-4.497,2.5715,0,4.0457,1.3499,4.145,3.673h-1.1222"
        "c-.1242-1.7806-1.1429-2.6543-2.9897-2.6543-2.1326,0-3.1926,1.1636-3.1926,3.5446v1.9918"
        "c0,2.3852,1.0559,3.5446,3.1926,3.5446,1.8468,0,2.8614-.8696,2.9897-2.6502h1.1222"
        "c-.0994,2.2775-1.5363,3.673-4.1243,3.673m6.8822-.2609v-15.1392h1.1636v6.3894"
        "c.7412-1.3417,2.1616-2.1491,3.6937-2.1119,2.1988,0,3.321,1.3292,3.321,3.8386v7.0271"
        "h-1.1677v-6.907c0-1.9462-.7454-2.9028-2.3438-2.9028-1.4949,0-2.6543.8282-3.5073,2.7578"
        "v7.0478h-1.1595Zm15.6775.2443c-2.9028,0-4.497-1.5735-4.497-4.497v-2.1119"
        "c0-2.9235,1.557-4.497,4.3976-4.497s4.3769,1.5735,4.3769,4.497v1.3085h-7.611v.7247"
        "c0,2.4059,1.0766,3.5653,3.2962,3.5653,1.909,0,2.9897-.8696,3.1098-2.3438h1.1222"
        "c-.1449,2.1781-1.6812,3.3624-4.1906,3.3624m-3.3376-6.3025h6.4888v-.2277"
        "c0-2.4059-1.0559-3.5653-3.2548-3.5653s-3.234,1.1636-3.234,3.5653v.2277Z"
        "m14.4932,6.3025c-2.7785,0-4.3314-1.5735-4.3314-4.497v-2.1119"
        "c0-2.9235,1.5363-4.497,4.3107-4.497,2.5715,0,4.0457,1.3499,4.145,3.673h-1.1222"
        "c-.1242-1.7806-1.1429-2.6543-2.9897-2.6543-2.1367,0-3.1926,1.1636-3.1926,3.5446v1.9918"
        "c0,2.3852,1.0559,3.5446,3.1926,3.5446,1.8468,0,2.8614-.8696,2.9897-2.6502h1.1222"
        "c-.0994,2.2775-1.5363,3.673-4.1243,3.673m6.8822-.265v-15.1433h1.1636v10.4351"
        "l5.9298-5.9132h1.4949l-4.3562,4.3314,4.4391,6.2818h-1.4079l-3.8593-5.4536-2.2402,2.1988"
        "v3.2548h-1.1595l-.0042.0083h0Zm10.6628,0v-10.7084h1.5528l.0663,1.6812"
        "c.6708-1.2216,1.9711-1.9669,3.3624-1.9255,1.4949,0,2.5094.6418,2.9442,1.8675"
        ".6998-1.1843,1.9835-1.9007,3.3624-1.8675,2.1367,0,3.321,1.2878,3.321,3.6481v7.3004"
        "h-1.8261v-7.1555c0-1.4286-.6253-2.1119-1.7392-2.1119s-2.0332.704-2.8241,2.2609v7.0106"
        "h-1.8261v-7.1555c0-1.4286-.6253-2.1119-1.7433-2.1119s-2.0332.704-2.8241,2.3645v6.907"
        "h-1.8303l.0041-.0041h0Zm17.8763,0v-15.1433h1.8261v9.7063l4.936-5.2672h2.2775"
        "l-4.1078,4.3562,4.1906,6.3439h-2.1781l-3.2755-5.0146-1.8468,1.9255v3.0891h-1.8261"
        "l.0042.0041h0Z'/>"
        "<path fill='#15d1a0' d='m14.1871,1.6413l14.1371,8.1824v16.3566l-14.1371,8.1783"
        "L.05,26.1762V9.8196L14.1871,1.6413ZM4.9073,13.5506v5.4287l6.6586-4.3024v11.2012"
        "l2.6253,1.5156,2.6212-1.5156v-11.2012l6.6544,4.3024v-5.4287l-9.2798-5.8138-9.2798,5.8138"
        "h0Z'/>"
        "</svg>"
        "</div>"
        "<h1>Site Not Started</h1>"
        f"<p>The site <code>{site_name}</code> is not running.</p>"
    )
    footer = (
        "<div class='r'>This page refreshes automatically every 60 seconds.</div>"
        "</div>"
        "</body></html>"
    )
    # fmt: on
    return header + instructions + footer


def create_apache_hook(
    apache_config: Path,
    site_name: str,
    apache_tcp_addr: str,
    apache_tcp_port: str,
    version: int,
) -> None:
    """
    Note: If you change the content of this file, you will have to increase the
    apache_hook_version(). It will trigger a mechanism in `omd update` that notifies users about the
    fact that they have to call `omd update-apache-config SITE` afterwards.
    """

    not_started_html = _site_not_started_html(site_name)
    apache_config.parent.mkdir(parents=True, exist_ok=True)
    with open(apache_config, "w") as f:
        f.write(
            f"""{apache_hook_header(version)}
# This file is managed by 'omd' and will automatically be overwritten. Better do not edit manually

# Make sure that symlink /omd does not make problems
<Directory />
  Options +FollowSymlinks
</Directory>

<IfModule mod_proxy_http.c>
  ProxyRequests Off
  ProxyPreserveHost On

  <Proxy http://{apache_tcp_addr}:{apache_tcp_port}/{site_name}>
    Order allow,deny
    allow from all
  </Proxy>

  <Location /{site_name}>
    # Setting "retry=0" to prevent 60 second caching of problem states e.g. when
    # the site apache is down and someone tries to access the page.
    # "disablereuse=On" prevents the apache from keeping the connection which leads to
    # wrong devlivered pages sometimes
    ProxyPass http://{apache_tcp_addr}:{apache_tcp_port}/{site_name} retry=0 disablereuse=On timeout=120
    ProxyPassReverse http://{apache_tcp_addr}:{apache_tcp_port}/{site_name}
  </Location>
</IfModule>

<IfModule !mod_proxy_http.c>
  Alias /{site_name} /omd/sites/{site_name}
  <Directory /omd/sites/{site_name}>
    Deny from all
    ErrorDocument 403 "<h1>Checkmk: Incomplete Apache Installation</h1>You need mod_proxy and
    mod_proxy_http in order to run the web interface of Checkmk."
  </Directory>
</IfModule>

<Location /{site_name}>
  ErrorDocument 503 "{not_started_html}"
</Location>
"""
        )
        os.chmod(apache_config, 0o644)  # Ensure the site user can read the files created by root


def delete_apache_hook(apache_config: Path) -> None:
    try:
        os.remove(apache_config)
    except FileNotFoundError:
        return
    except Exception as e:
        sys.stderr.write(f"Cannot remove apache hook {apache_config}: {e}\n")


def init_cmd(version_info: VersionInfo, name: str, action: str) -> str:
    return version_info.INIT_CMD % {
        "name": name,
        "action": action,
    }


def reload_apache(version_info: VersionInfo) -> None:
    sys.stdout.write("Reloading Apache...")
    sys.stdout.flush()
    show_success(subprocess.call([version_info.APACHE_CTL, "graceful"]) >> 8)


def restart_apache(version_info: VersionInfo, verbose: bool) -> None:
    status_cmd = init_cmd(version_info, version_info.APACHE_INIT_NAME, "status")
    status_exit_code = subprocess.call(
        shlex.split(status_cmd), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if status_exit_code == 0:
        sys.stdout.write("Restarting Apache...")
        sys.stdout.flush()
        restart_cmd = shlex.split(init_cmd(version_info, version_info.APACHE_INIT_NAME, "restart"))
        show_success(subprocess.call(restart_cmd, stdout=subprocess.DEVNULL))
    else:
        if verbose:
            sys.stdout.write(f"Non-zero exit code {status_exit_code} from {status_cmd}.\n")
        sys.stdout.write("Skipping Apache restart.\n")
