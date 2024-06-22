#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
import shlex
import subprocess
import sys
from pathlib import Path

from omdlib.console import show_success
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
    site_dir: str,
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
    create_apache_hook(
        apache_config, site_name, site_dir, apache_tcp_addr, apache_tcp_port, apache_hook_version()
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
    return 2


def create_apache_hook(
    apache_config: Path,
    site_name: str,
    site_dir: str,
    apache_tcp_addr: str,
    apache_tcp_port: str,
    version: int,
) -> None:
    """
    Note: If you change the content of this file, you will have to increase the
    apache_hook_version(). It will trigger a mechanism in `omd update` that notifies users about the
    fact that they have to call `omd update-apache-config SITE` afterwards.
    """

    # This file was left over in skel to be compatible with Checkmk sites created before #9493 and
    # haven't switched over to the new mode with `omd update-apache-config SITE` yet.
    # On first execution of this function, the file can be removed to prevent confusions.
    apache_own_path = os.path.join(site_dir, "etc/apache/apache-own.conf")
    try:
        os.remove(apache_own_path)
    except FileNotFoundError:
        pass

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
  ErrorDocument 503 "<meta http-equiv='refresh' content='60'><h1>Checkmk: Site Not Started</h1>You need to start this site in order to access the web interface.<!-- IE shows its own short useless error message otherwise: placeholder -->"
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
