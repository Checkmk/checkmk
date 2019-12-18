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

import pwd
import grp
import os
import subprocess
from typing import Union, List, Tuple, Optional, TYPE_CHECKING  # pylint: disable=unused-import
import psutil  # type: ignore[import]

if TYPE_CHECKING:
    from omdlib.contexts import SiteContext  # pylint: disable=unused-import
    from omdlib.version_info import VersionInfo  # pylint: disable=unused-import

import cmk.utils.tty as tty
from cmk.utils.exceptions import MKTerminate

#.
#   .--Users/Groups--------------------------------------------------------.
#   |     _   _                      ______                                |
#   |    | | | |___  ___ _ __ ___   / / ___|_ __ ___  _   _ _ __  ___      |
#   |    | | | / __|/ _ \ '__/ __| / / |  _| '__/ _ \| | | | '_ \/ __|     |
#   |    | |_| \__ \  __/ |  \__ \/ /| |_| | | | (_) | |_| | |_) \__ \     |
#   |     \___/|___/\___|_|  |___/_/  \____|_|  \___/ \__,_| .__/|___/     |
#   |                                                      |_|             |
#   +----------------------------------------------------------------------+
#   |  Helper functions for dealing with Linux users and groups            |
#   '----------------------------------------------------------------------'


def find_processes_of_user(username):
    # type: (str) -> List[str]
    try:
        p = subprocess.Popen(["pgrep", "-u", username],
                             stdin=open(os.devnull, "r"),
                             stdout=subprocess.PIPE,
                             close_fds=True,
                             encoding="utf-8")
        if p.stdout is None:
            raise Exception()
        return p.stdout.read().split()
    except Exception:
        return []


def groupdel(groupname):
    # type: (str) -> None
    try:
        p = subprocess.Popen(["groupdel", groupname],
                             stdin=open(os.devnull, "r"),
                             stdout=open(os.devnull, "w"),
                             stderr=subprocess.PIPE,
                             close_fds=True,
                             encoding="utf-8")
    except OSError as e:
        raise MKTerminate("\n" + tty.error + ": Failed to delete group '%s': %s" % (groupname, e))

    stderr = p.communicate()[1]
    if p.returncode != 0:
        raise MKTerminate("\n" + tty.error + ": Failed to delete group '%s': %s" %
                          (groupname, stderr))


# TODO: Cleanup: Change uid/gid to int
def useradd(version_info, site, uid=None, gid=None):
    # type: (VersionInfo, SiteContext, Optional[str], Optional[str]) -> None
    # Create user for running site 'name'
    _groupadd(site.name, gid)
    useradd_options = version_info.USERADD_OPTIONS
    if uid is not None:
        useradd_options += " -u %d" % int(uid)
    if os.system(  # nosec
            "useradd %s -r -d '%s' -c 'OMD site %s' -g %s -G omd %s -s /bin/bash" %
        (useradd_options, site.dir, site.name, site.name, site.name)) != 0:
        groupdel(site.name)
        raise MKTerminate("Error creating site user.")

    # On SLES11+ there is a standard group "trusted" that the OMD site users should be members
    # of to be able to access CRON.
    if group_exists("trusted"):
        _add_user_to_group(version_info, site.name, "trusted")

    # Add Apache to new group. It needs to be able to write in to the
    # command pipe and possible other stuff
    _add_user_to_group(version_info, version_info.APACHE_USER, site.name)


# TODO: refactor gid to int
def _groupadd(groupname, gid=None):
    # type: (str, Optional[str]) -> None
    cmd = ["groupadd"]
    if gid is not None:
        cmd += ["-g", "%d" % int(gid)]
    cmd.append(groupname)

    if subprocess.Popen(
            cmd,
            close_fds=True,
            stdin=open(os.devnull, "r"),
    ).wait() != 0:
        raise MKTerminate("Cannot create group for site user.")


def _add_user_to_group(version_info, user, group):
    # type: (VersionInfo, str, str) -> bool
    cmd = version_info.ADD_USER_TO_GROUP % {"user": user, "group": group}
    return os.system(cmd + " >/dev/null") == 0  # nosec


def userdel(name):
    # type: (str) -> None
    if user_exists(name):
        try:
            p = subprocess.Popen(["userdel", "-r", name],
                                 stdin=open(os.devnull, "r"),
                                 stdout=open(os.devnull, "w"),
                                 stderr=subprocess.PIPE,
                                 close_fds=True,
                                 encoding="utf-8")
        except OSError as e:
            raise MKTerminate("\n" + tty.error + ": Failed to delete user '%s': %s" % (name, e))

        stderr = p.communicate()[1]
        if p.returncode != 0:
            raise MKTerminate("\n" + tty.error + ": Failed to delete user '%s': %s" %
                              (name, stderr))

    # On some OSes (e.g. debian) the group is automatically removed if
    # it bears the same name as the user. So first check for the group.
    if group_exists(name):
        groupdel(name)


def user_id(name):
    # type: (str) -> Union[bool, int]
    try:
        return pwd.getpwnam(name).pw_uid
    except Exception:
        return False


def user_exists(name):
    # type: (str) -> bool
    try:
        pwd.getpwnam(name)
        return True
    except Exception:
        return False


def group_exists(name):
    # type: (str) -> bool
    try:
        grp.getgrnam(name)
        return True
    except Exception:
        return False


def group_id(name):
    # type: (str) -> int
    return grp.getgrnam(name).gr_gid


def user_logged_in(name):
    # type: (str) -> bool
    """Check if processes of named user are existing"""
    return any(p for p in psutil.process_iter() if p.username() == name)


def user_verify(version_info, site, allow_populated=False):
    # type: (VersionInfo, SiteContext, bool) -> bool
    name = site.name

    if not user_exists(name):
        raise MKTerminate(tty.error + ": user %s does not exist" % name)

    user = _user_by_id(user_id(name))
    if user.pw_dir != site.dir:
        raise MKTerminate(tty.error + ": Wrong home directory for user %s, must be %s" %
                          (name, site.dir))

    if not os.path.exists(site.dir):
        raise MKTerminate(tty.error + ": home directory for user %s (%s) does not exist" %
                          (name, site.dir))

    if not allow_populated and os.path.exists(site.dir + "/version"):
        raise MKTerminate(tty.error + ": home directory for user %s (%s) must be empty" %
                          (name, site.dir))

    if not _file_owner_verify(site.dir, user.pw_uid, user.pw_gid):
        raise MKTerminate(tty.error + ": home directory (%s) is not owned by user %s and group %s" %
                          (site.dir, name, name))

    group = _group_by_id(user.pw_gid)
    if group is None or group.gr_name != name:
        raise MKTerminate(tty.error + ": primary group for siteuser must be %s" % name)

    if not _user_has_group(version_info.APACHE_USER, name):
        raise MKTerminate(tty.error + ": apache user %s must be member of group %s" %
                          (version_info.APACHE_USER, name))

    if not _user_has_group(name, "omd"):
        raise MKTerminate(tty.error + ": siteuser must be member of group omd")

    return True


def _file_owner_verify(path, uid, gid):
    # type: (str, int, int) -> bool
    try:
        s = os.stat(path)
        if s.st_uid != uid or s.st_gid != gid:
            return False
    except Exception:
        return False
    return True


def _user_has_group(user, group):
    # type: (str, str) -> bool
    try:
        u = _user_by_id(user_id(user))
        g = _group_by_id(u.pw_gid)
        if g.gr_name == group:
            return True
        g = _group_by_id(group_id(group))
        if user in g.gr_mem:
            return True
        return False
    except Exception:
        return False


def _user_by_id(id_):
    # type: (int) -> pwd.struct_passwd
    return pwd.getpwuid(id_)


def _group_by_id(id_):
    # type: (int) -> grp.struct_group
    return grp.getgrgid(id_)


def switch_to_site_user(site):
    # type: (SiteContext) -> None
    p = pwd.getpwnam(site.name)
    uid = p.pw_uid
    gid = p.pw_gid
    os.chdir(p.pw_dir)
    os.setgid(gid)

    # Darn. The site user might have been put into further groups.
    # This is e.g. needed if you want to access the livestatus socket
    # from one site by another. We make use of the "id" command here.
    # If you know something better, that does not rely on an external
    # command (and that does not try to parse around /etc/group, of
    # course), then please tell mk -> mk@mathias-kettner.de.
    os.setgroups(_groups_of(site.name))
    os.setuid(uid)


def _groups_of(username):
    # type: (str) -> List[int]
    group_ids = {g.gr_gid for g in grp.getgrall() if username in g.gr_mem}
    group_ids.add(pwd.getpwnam(username).pw_gid)
    return list(group_ids)
