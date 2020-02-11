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
"""Site configuration and config hooks

Hooks are scripts in lib/omd/hooks that are being called with one
of the following arguments:

default - return the default value of the hook. Mandatory
set     - implements a new setting for the hook
choices - available choices for enumeration hooks
depends - exists with 1, if this hook misses its dependent hook settings
"""

import os
import re
import sys
import logging
import subprocess
from typing import (  # pylint: disable=unused-import
    Tuple, Pattern, Union, Dict, TYPE_CHECKING, List, Iterable)

from cmk.utils.log import VERBOSE
from cmk.utils.exceptions import MKTerminate

if TYPE_CHECKING:
    from omdlib.contexts import SiteContext  # pylint: disable=unused-import

logger = logging.getLogger("cmk.omd")

ConfigHookChoiceItem = Tuple[str, str]
ConfigHookChoices = Union[None, Pattern, List[ConfigHookChoiceItem]]
ConfigHook = Dict[str, Union[str, bool, ConfigHookChoices]]
ConfigHooks = Dict[str, ConfigHook]
ConfigHookResult = Tuple[int, str]


# Put all site configuration (explicit and defaults) into environment
# variables beginning with CONFIG_
def create_config_environment(site):
    # type: (SiteContext) -> None
    for varname, value in site.conf.items():
        os.environ["CONFIG_" + varname] = value


# TODO: RENAME
def save_site_conf(site):
    # type: (SiteContext) -> None
    confdir = site.dir + "/etc/omd"

    if not os.path.exists(confdir):
        os.mkdir(confdir)

    f = open(site.dir + "/etc/omd/site.conf", "w")

    for hook_name, value in sorted(site.conf.items(), key=lambda x: x[0]):
        f.write("CONFIG_%s='%s'\n" % (hook_name, value))


# Get information about all hooks. Just needed for
# the "omd config" command.
def load_config_hooks(site):
    # type: (SiteContext) -> ConfigHooks
    config_hooks = {}  # type: ConfigHooks

    hook_dir = site.dir + "/lib/omd/hooks"
    for hook_name in os.listdir(hook_dir):
        try:
            if hook_name[0] != '.':
                hook = _config_load_hook(site, hook_name)
                # only load configuration hooks
                if hook.get("choices", None) is not None:
                    config_hooks[hook_name] = hook
        except MKTerminate:
            raise
        except Exception:
            pass
    config_hooks = load_hook_dependencies(site, config_hooks)
    return config_hooks


def _config_load_hook(site, hook_name):
    # type: (SiteContext, str) -> ConfigHook
    hook = {
        "name": hook_name,
        "deprecated": False,
    }  # type: ConfigHook

    description = ""
    description_active = False
    for line in open(site.dir + "/lib/omd/hooks/" + hook_name):
        if line.startswith("# Alias:"):
            hook["alias"] = line[8:].strip()
        elif line.startswith("# Menu:"):
            hook["menu"] = line[7:].strip()
        elif line.startswith("# Deprecated: yes"):
            hook["deprecated"] = True
        elif line.startswith("# Description:"):
            description_active = True
        elif line.startswith("#  ") and description_active:
            description += line[3:].strip() + "\n"
        else:
            description_active = False
    hook["description"] = description

    def get_hook_info(info):
        # type: (str) -> str
        return call_hook(site, hook_name, [info])[1]

    # The choices can either be a list of possible keys. Then
    # the hook outputs one live for each choice where the key and a
    # description are separated by a colon. Or it outputs one line
    # where that line is an extended regular expression matching the
    # possible values.
    choicestxt = get_hook_info("choices").split("\n")
    choices = None  # type: ConfigHookChoices
    if len(choicestxt) == 1:
        regextext = choicestxt[0].strip()
        if regextext != "":
            choices = re.compile(regextext + "$")
        else:
            choices = None
    else:
        choices = []
        try:
            for line in choicestxt:
                val, descr = line.split(":", 1)
                val = val.strip()
                descr = descr.strip()
                choices.append((val, descr))
        except Exception as e:
            raise MKTerminate("Invalid output of hook: %s: %s" % (choicestxt, e))

    hook["choices"] = choices
    return hook


def load_hook_dependencies(site, config_hooks):
    # type: (SiteContext, ConfigHooks) -> ConfigHooks
    for hook_name in sort_hooks(list(config_hooks.keys())):
        hook = config_hooks[hook_name]
        exitcode, _content = call_hook(site, hook_name, ["depends"])
        if exitcode:
            hook["active"] = False
        else:
            hook["active"] = True
    return config_hooks


# Always sort CORE hook to the end because it runs "cmk -U" which
# relies on files created by other hooks.
def sort_hooks(hook_names):
    # type: (List[str]) -> Iterable[str]
    return sorted(hook_names, key=lambda n: (n == "CORE", n))


def hook_exists(site, hook_name):
    # type: (SiteContext, str) -> bool
    hook_file = site.dir + "/lib/omd/hooks/" + hook_name
    return os.path.exists(hook_file)


def call_hook(site, hook_name, args):
    # type: (SiteContext, str, List[str]) -> ConfigHookResult

    cmd = [site.dir + "/lib/omd/hooks/" + hook_name] + args
    hook_env = os.environ.copy()
    hook_env.update({
        "OMD_ROOT": site.dir,
        "OMD_SITE": site.name,
    })

    logger.log(VERBOSE, "Calling hook: %s", subprocess.list2cmdline(cmd))

    p = subprocess.Popen(
        cmd,
        env=hook_env,
        close_fds=True,
        shell=False,
        stdout=subprocess.PIPE,
        encoding="utf-8",
    )
    content = p.communicate()[0].strip()
    exitcode = p.poll()

    if exitcode and args[0] != "depends":
        sys.stderr.write("Error running %s: %s\n" % (subprocess.list2cmdline(cmd), content))

    return exitcode, content
