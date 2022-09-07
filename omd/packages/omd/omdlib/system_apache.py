#!/usr/bin/env python3
# -*- encoding: utf-8; py-indent-offset: 4 -*-
#
#       U  ___ u  __  __   ____
#        \/"_ \/U|' \/ '|u|  _"\
#        | | | |\| |\/| |/| | | |
#    .-,_| |_| | | |  | |U| |_| |\
#     \_)-\___/  |_|  |_| |____/ u
#          \\   <<,-,,-.   |||_
#         (__)   (./  \.) (__)_)
#
# This file is part of OMD - The Open Monitoring Distribution.
# The official homepage is at <http://omdistro.org>.
#
# OMD  is  free software;  you  can  redistribute it  and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the  Free Software  Foundation  in  version 2.  OMD  is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import os
import subprocess
import sys

import omdlib.utils
from omdlib.console import show_success
from omdlib.contexts import SiteContext
from omdlib.version_info import VersionInfo

__all__ = [
    "register_with_system_apache",
    "unregister_from_system_apache",
    "delete_apache_hook",
    "is_apache_hook_up_to_date",
]


def register_with_system_apache(
    version_info: VersionInfo, site: SiteContext, apache_reload: bool
) -> None:
    """Apply the site specific configuration to the system global apache

    Basically update the apache configuration to register the mod_proxy configuration
    and the reload or restart the system apache.

    Root permissions are needed to make this work.
    """
    create_apache_hook(site, apache_hook_version())
    apply_apache_config(version_info, apache_reload)


def unregister_from_system_apache(
    version_info: VersionInfo, site: SiteContext, apache_reload: bool
) -> None:
    delete_apache_hook(site.name)
    apply_apache_config(version_info, apache_reload)


def apply_apache_config(version_info: VersionInfo, apache_reload: bool) -> None:
    if apache_reload:
        reload_apache(version_info)
    else:
        restart_apache(version_info)


def is_apache_hook_up_to_date(site: SiteContext) -> bool:
    with open(os.path.join(omdlib.utils.omd_base_path(), "omd/apache/%s.conf" % site.name)) as f:
        header = f.readline()
        return header == apache_hook_header(apache_hook_version()) + "\n"


def apache_hook_header(version: int) -> str:
    return f"# version: {version}"


def apache_hook_version() -> int:
    return 2


def create_apache_hook(site: SiteContext, version: int) -> None:
    """
    Note: If you change the content of this file, you will have to increase the
    apache_hook_version(). It will trigger a mechanism in `omd update` that notifies users about the
    fact that they have to call `omd update-apache-config SITE` afterwards.
    """

    # This file was left over in skel to be compatible with Checkmk sites created before #9493 and
    # haven't switched over to the new mode with `omd update-apache-config SITE` yet.
    # On first execution of this function, the file can be removed to prevent confusions.
    apache_own_path = os.path.join(site.dir, "etc/apache/apache-own.conf")
    try:
        os.remove(apache_own_path)
    except FileNotFoundError:
        pass

    hook_path = os.path.join(omdlib.utils.omd_base_path(), "omd/apache/%s.conf" % site.name)
    with open(hook_path, "w") as f:
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

  <Proxy http://{site.conf['APACHE_TCP_ADDR']}:{site.conf['APACHE_TCP_PORT']}/{site.name}>
    Order allow,deny
    allow from all
  </Proxy>

  <Location /{site.name}>
    # Setting "retry=0" to prevent 60 second caching of problem states e.g. when
    # the site apache is down and someone tries to access the page.
    # "disablereuse=On" prevents the apache from keeping the connection which leads to
    # wrong devlivered pages sometimes
    ProxyPass http://{site.conf['APACHE_TCP_ADDR']}:{site.conf['APACHE_TCP_PORT']}/{site.name} retry=0 disablereuse=On timeout=120
    ProxyPassReverse http://{site.conf['APACHE_TCP_ADDR']}:{site.conf['APACHE_TCP_PORT']}/{site.name}
  </Location>
</IfModule>

<IfModule !mod_proxy_http.c>
  Alias /{site.name} /omd/sites/{site.name}
  <Directory /omd/sites/{site.name}>
    Deny from all
    ErrorDocument 403 "<h1>Checkmk: Incomplete Apache Installation</h1>You need mod_proxy and
    mod_proxy_http in order to run the web interface of Checkmk."
  </Directory>
</IfModule>

<Location /{site.name}>
  ErrorDocument 503 "<meta http-equiv='refresh' content='60'><h1>Checkmk: Site Not Started</h1>You need to start this site in order to access the web interface.<!-- IE shows its own short useless error message otherwise: placeholder -->"
</Location>
"""
        )
        os.chmod(hook_path, 0o664)  # Ensure the site user can read the files created by root


def delete_apache_hook(sitename: str) -> None:
    hook_path = os.path.join(omdlib.utils.omd_base_path(), "omd/apache/%s.conf" % sitename)
    try:
        os.remove(hook_path)
    except FileNotFoundError:
        return
    except Exception as e:
        sys.stderr.write("Cannot remove apache hook %s: %s\n" % (hook_path, e))


def has_old_apache_hook_in_site(site: SiteContext) -> bool:
    with open(os.path.join(omdlib.utils.omd_base_path(), "omd/apache/%s.conf" % site.name)) as f:
        return f.readline().startswith("Include ")


def create_old_apache_hook(site: SiteContext) -> None:
    apache_own_path = os.path.join(site.dir, "etc/apache/apache-own.conf")
    with open(apache_own_path, "w") as f:
        f.write(
            f"""# This file is read in by the global Apache. It is
# owned by OMD. Do not add anything here. Rather
# create your own files in conf.d/

# Make sure that symlink /omd does not make problems
<Directory />
  Options +FollowSymlinks
</Directory>

<IfModule mod_proxy_http.c>
  ProxyRequests Off
  ProxyPreserveHost On

  # Include file created by 'omd config', which
  # sets the TCP port of the site local webserver
  Include /omd/sites/{site.name}/etc/apache/proxy-port.conf
</IfModule>

<IfModule !mod_proxy_http.c>
  Alias /{site.name} /omd/sites/{site.name}
  <Directory /omd/sites/{site.name}>
    Deny from all
    ErrorDocument 403 "<h1>OMD: Incomplete Apache2 Installation</h1>You need mod_proxy and mod_proxy_http in order to run the web interface of OMD."
  </Directory>
</IfModule>

<Location /{site.name}>
  ErrorDocument 503 "<meta http-equiv='refresh' content='60'><h1>OMD: Site Not Started</h1>You need to start this site in order to access the web interface.<!-- IE shows its own short useless error message otherwise: placeholder -->"
</Location>

# Set site specific environment
SetEnv OMD_SITE {site.name}
SetEnv OMD_ROOT /omd/sites/{site.name}
SetEnv OMD_MODE own
"""
        )


def init_cmd(version_info: VersionInfo, name: str, action: str) -> str:
    return version_info.INIT_CMD % {
        "name": name,
        "action": action,
    }


def reload_apache(version_info: VersionInfo) -> None:
    sys.stdout.write("Reloading Apache...")
    sys.stdout.flush()
    show_success(subprocess.call([version_info.APACHE_CTL, "graceful"]) >> 8)


def restart_apache(version_info: VersionInfo) -> None:
    if (
        os.system(  # nosec
            init_cmd(version_info, version_info.APACHE_INIT_NAME, "status") + " >/dev/null 2>&1"
        )
        >> 8
        == 0
    ):
        sys.stdout.write("Restarting Apache...")
        sys.stdout.flush()
        show_success(
            os.system(  # nosec
                init_cmd(version_info, version_info.APACHE_INIT_NAME, "restart") + " >/dev/null"
            )
            >> 8
        )
