#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import grp
import os
import pwd
import shlex
import subprocess
from typing import TYPE_CHECKING

import psutil

if TYPE_CHECKING:
    from omdlib.contexts import SiteContext
    from omdlib.version_info import VersionInfo

from omdlib.site_paths import SitePaths

from cmk.ccc import tty
from cmk.ccc.exceptions import MKTerminate

# .
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


def find_processes_of_user(username: str) -> list[str]:
    try:
        completed_process = subprocess.run(
            ["pgrep", "-u", username],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            close_fds=True,
            encoding="utf-8",
            check=False,
        )
        return completed_process.stdout.split()
    except Exception:
        return []


def groupdel(groupname: str) -> None:
    try:
        completed_process = subprocess.run(
            ["groupdel", groupname],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            close_fds=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as e:
        raise MKTerminate("\n" + tty.error + f": Failed to delete group '{groupname}': {e}")

    if completed_process.returncode:
        raise MKTerminate(
            "\n" + tty.error + f": Failed to delete group '{groupname}': {completed_process.stderr}"
        )


# TODO: Cleanup: Change uid/gid to int
def useradd(
    version_info: "VersionInfo",
    site: "SiteContext",
    uid: str | None = None,
    gid: str | None = None,
) -> None:
    site_home = SitePaths.from_site_name(site.name).home
    # Create user for running site 'name'
    _groupadd(site.name, gid)
    useradd_options = version_info.USERADD_OPTIONS
    if uid is not None:
        useradd_options += " -u %d" % int(uid)

    cmd = f"useradd {useradd_options} -r -d '{site_home}' -c 'OMD site {site.name}' -g {site.name} -G omd {site.name} -s /bin/bash"
    if subprocess.call(shlex.split(cmd)) != 0:
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
def _groupadd(groupname: str, gid: str | None = None) -> None:
    cmd = ["groupadd", "-r"]
    if gid is not None:
        cmd += ["-g", "%d" % int(gid)]
    cmd.append(groupname)
    if subprocess.run(cmd, close_fds=True, stdin=subprocess.DEVNULL, check=False).returncode:
        raise MKTerminate("Cannot create group for site user.")


def _add_user_to_group(version_info: "VersionInfo", user: str, group: str) -> bool:
    cmd = version_info.ADD_USER_TO_GROUP % {"user": user, "group": group}
    return subprocess.call(shlex.split(cmd), stdout=subprocess.DEVNULL) == 0


def userdel(name: str) -> None:
    if user_exists(name):
        try:
            completed_process = subprocess.run(
                ["userdel", "-r", name],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                close_fds=True,
                encoding="utf-8",
                check=False,
            )
        except OSError as e:
            raise MKTerminate("\n" + tty.error + f": Failed to delete user '{name}': {e}")

        if completed_process.returncode:
            raise MKTerminate(
                "\n" + tty.error + f": Failed to delete user '{name}': {completed_process.stderr}"
            )

    # On some OSes (e.g. debian) the group is automatically removed if
    # it bears the same name as the user. So first check for the group.
    if group_exists(name):
        groupdel(name)


def user_id(name: str) -> bool | int:
    try:
        return pwd.getpwnam(name).pw_uid
    except Exception:
        return False


def user_exists(name: str) -> bool:
    try:
        pwd.getpwnam(name)
        return True
    except Exception:
        return False


def group_exists(name: str) -> bool:
    try:
        grp.getgrnam(name)
        return True
    except Exception:
        return False


def group_id(name: str) -> int:
    return grp.getgrnam(name).gr_gid


def user_logged_in(name: str) -> bool:
    """Check if processes of named user are existing"""
    return any(p for p in psutil.process_iter() if p.username() == name)


def user_verify(
    version_info: "VersionInfo", site: "SiteContext", allow_populated: bool = False
) -> bool:
    name = site.name
    site_home = SitePaths.from_site_name(site.name).home

    if not user_exists(name):
        raise MKTerminate(tty.error + ": user %s does not exist" % name)

    user = _user_by_id(user_id(name))
    if user.pw_dir != site_home:
        raise MKTerminate(
            tty.error + f": Wrong home directory for user {name}, must be {site_home}"
        )

    if not os.path.exists(site_home):
        raise MKTerminate(
            tty.error + f": home directory for user {name} ({site_home}) does not exist"
        )

    if not allow_populated and os.path.exists(site_home + "/version"):
        raise MKTerminate(
            tty.error + f": home directory for user {name} ({site_home}) must be empty"
        )

    if not _file_owner_verify(site_home, user.pw_uid, user.pw_gid):
        raise MKTerminate(
            tty.error
            + f": home directory ({site_home}) is not owned by user {name} and group {name}"
        )

    group = _group_by_id(user.pw_gid)
    if group is None or group.gr_name != name:
        raise MKTerminate(tty.error + ": primary group for siteuser must be %s" % name)

    if not _user_has_group(version_info.APACHE_USER, name):
        raise MKTerminate(
            tty.error + f": apache user {version_info.APACHE_USER} must be member of group {name}"
        )

    if not _user_has_group(name, "omd"):
        raise MKTerminate(tty.error + ": siteuser must be member of group omd")

    return True


def _file_owner_verify(path: str, uid: int, gid: int) -> bool:
    try:
        s = os.stat(path)
        if s.st_uid != uid or s.st_gid != gid:
            return False
    except Exception:
        return False
    return True


def _user_has_group(user: str, group: str) -> bool:
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


def _user_by_id(id_: int) -> pwd.struct_passwd:
    return pwd.getpwuid(id_)


def _group_by_id(id_: int) -> grp.struct_group:
    return grp.getgrgid(id_)


def switch_to_site_user(site: "SiteContext") -> None:
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
    os.umask(0o077)


def _groups_of(username: str) -> list[int]:
    # Note: Do NOT use grp.getgrall to fetch all availabile groups
    # Certain setups might have ldap group authorization and may start excessive queries
    return list(map(int, subprocess.check_output(["id", "-G", username]).split()))
