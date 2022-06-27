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

from omdlib.console import show_success
from omdlib.contexts import SiteContext
from omdlib.version_info import VersionInfo

__all__ = [
    "register_with_system_apache",
    "unregister_from_system_apache",
    "delete_apache_hook",
]


def register_with_system_apache(
    version_info: VersionInfo, site: SiteContext, apache_reload: bool
) -> None:
    """Apply the site specific configuration to the system global apache

    Basically update the apache configuration to register the mod_proxy configuration
    and the reload or restart the system apache.

    Root permissions are needed to make this work.
    """
    create_apache_hook(site)
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


def create_apache_hook(site: SiteContext) -> None:
    with open("/omd/apache/%s.conf" % site.name, "w") as f:
        f.write("Include %s/etc/apache/mode.conf\n" % site.dir)


def delete_apache_hook(sitename: str) -> None:
    hook_path = "/omd/apache/%s.conf" % sitename
    try:
        os.remove(hook_path)
    except FileNotFoundError:
        return
    except Exception as e:
        sys.stderr.write("Cannot remove apache hook %s: %s\n" % (hook_path, e))


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
