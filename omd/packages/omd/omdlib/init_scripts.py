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
"""Handling of site-internal init scripts"""

import logging
import os
import subprocess
import sys
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from omdlib.contexts import SiteContext

from omdlib.utils import chdir

import cmk.utils.tty as tty
from cmk.utils.log import VERBOSE

logger = logging.getLogger("cmk.omd")


def call_init_scripts(
    site: "SiteContext",
    command: str,
    daemon: Optional[str] = None,
    exclude_daemons: Optional[List[str]] = None,
) -> int:
    # Restart: Do not restart each service after another,
    # but first do stop all, then start all again! This
    # preserves the order.
    if command == "restart":
        # TODO: Why is the result of call_init_scripts not returned?
        call_init_scripts(site, "stop", daemon)
        call_init_scripts(site, "start", daemon)
        return 0

    # OMD guarantees OMD_ROOT to be the current directory
    with chdir(site.dir):
        if daemon:
            success = _call_init_script("%s/etc/init.d/%s" % (site.dir, daemon), command)

        else:
            # Call stop scripts in reverse order. If daemon is set,
            # then only that start script will be affected
            rc_dir, scripts = _init_scripts(site.name)
            if command == "stop":
                scripts.reverse()
            success = True

            for script in scripts:
                if exclude_daemons and script in exclude_daemons:
                    continue

                if not _call_init_script("%s/%s" % (rc_dir, script), command):
                    success = False

    if success:
        return 0
    return 2


def check_status(  # pylint: disable=too-many-branches
    site: "SiteContext", display: bool = True, daemon: Optional[str] = None, bare: bool = False
) -> int:
    num_running = 0
    num_unused = 0
    num_stopped = 0
    rc_dir, scripts = _init_scripts(site.name)
    components = [s.split("-", 1)[-1] for s in scripts]
    if daemon and daemon not in components:
        if not bare:
            sys.stderr.write("ERROR: This daemon does not exist.\n")
        return 3
    is_verbose = logger.isEnabledFor(VERBOSE)
    for script in scripts:
        komponent = script.split("/")[-1].split("-", 1)[-1]
        if daemon and komponent != daemon:
            continue

        state = os.system("%s/%s status >/dev/null 2>&1" % (rc_dir, script)) >> 8  # nosec

        if display and (state != 5 or is_verbose):
            if bare:
                sys.stdout.write(komponent + " ")
            else:
                sys.stdout.write("%-16s" % (komponent + ":"))
                sys.stdout.write(tty.bold)

        if bare:
            if state != 5 or is_verbose:
                sys.stdout.write("%d\n" % state)

        if state == 0:
            if display and not bare:
                sys.stdout.write(tty.green + "running\n")
            num_running += 1
        elif state == 5:
            if display and is_verbose and not bare:
                sys.stdout.write(tty.blue + "unused\n")
            num_unused += 1
        else:
            if display and not bare:
                sys.stdout.write(tty.red + "stopped\n")
            num_stopped += 1
        if display and not bare:
            sys.stdout.write(tty.normal)

    if num_stopped > 0 and num_running == 0:
        exit_code = 1
        ovstate = tty.red + "stopped"
    elif num_running > 0 and num_stopped == 0:
        exit_code = 0
        ovstate = tty.green + "running"
    elif num_running == 0 and num_stopped == 0:
        exit_code = 0
        ovstate = tty.blue + "unused"
    else:
        exit_code = 2
        ovstate = tty.yellow + "partially running"
    if display:
        if bare:
            sys.stdout.write("OVERALL %d\n" % exit_code)
        else:
            sys.stdout.write("-----------------------\n")
            sys.stdout.write("Overall state:  %s\n" % (tty.bold + ovstate + tty.normal))
    return exit_code


# TODO: Use site context
def _init_scripts(sitename: str) -> Tuple[str, List[str]]:
    rc_dir = "/omd/sites/%s/etc/rc.d" % sitename
    try:
        scripts = sorted(os.listdir(rc_dir))
        return rc_dir, scripts
    except Exception:
        return rc_dir, []


def _call_init_script(scriptpath: str, command: str) -> bool:
    if not os.path.exists(scriptpath):
        sys.stderr.write("ERROR: This daemon does not exist.\n")
        return False

    try:
        return subprocess.call([scriptpath, command]) in [0, 5]
    except OSError as e:
        sys.stderr.write("ERROR: Failed to run '%s': %s\n" % (scriptpath, e))
        return False
