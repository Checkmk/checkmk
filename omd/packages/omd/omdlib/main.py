#!/usr/bin/env python
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
"""The command line tool specific implementations of the omd command and main entry point"""

import abc
import contextlib
import errno
import fcntl
import grp
import os
import pwd
import random
import re
import shlex
import shutil
import signal
import string
import subprocess
import sys
import tarfile
import termios
import time
import traceback
import tty
from typing import Dict  # pylint: disable=unused-import

import psutil  # type: ignore
from passlib.hash import sha256_crypt  # type: ignore
from pathlib2 import Path

import omdlib
import omdlib.backup
import omdlib.certs
from cmk.utils.paths import mkbackup_lock_dir

#   .--Logging-------------------------------------------------------------.
#   |                _                      _                              |
#   |               | |    ___   __ _  __ _(_)_ __   __ _                  |
#   |               | |   / _ \ / _` |/ _` | | '_ \ / _` |                 |
#   |               | |__| (_) | (_| | (_| | | | | | (_| |                 |
#   |               |_____\___/ \__, |\__, |_|_| |_|\__, |                 |
#   |                           |___/ |___/         |___/                  |
#   +----------------------------------------------------------------------+
#   | Helper functions for output on the TTY                               |
#   '----------------------------------------------------------------------'

# colored output, if stdout is a tty
if sys.stdout.isatty():
    tty_black = '\033[30m'
    tty_red = '\033[31m'
    tty_green = '\033[32m'
    tty_yellow = '\033[33m'
    tty_blue = '\033[34m'
    tty_magenta = '\033[35m'
    tty_cyan = '\033[36m'
    tty_white = '\033[37m'
    tty_bgblack = '\033[40m'
    tty_bgred = '\033[41m'
    tty_bggreen = '\033[42m'
    tty_bgyellow = '\033[43m'
    tty_bgblue = '\033[44m'
    tty_bgmagenta = '\033[45m'
    tty_bgcyan = '\033[46m'
    tty_bgwhite = '\033[47m'
    tty_bold = '\033[1m'
    tty_underline = '\033[4m'
    tty_normal = '\033[0m'
    tty_ok = tty_green + tty_bold + 'OK' + tty_normal
    tty_error = tty_red + tty_bold + 'ERROR' + tty_normal
    tty_warn = tty_yellow + tty_bold + 'WARNING' + tty_normal
else:
    tty_black = ''
    tty_red = ''
    tty_green = ''
    tty_yellow = ''
    tty_blue = ''
    tty_magenta = ''
    tty_cyan = ''
    tty_white = ''
    tty_bgred = ''
    tty_bggreen = ''
    tty_bgyellow = ''
    tty_bgblue = ''
    tty_bgmagenta = ''
    tty_bgcyan = ''
    tty_bold = ''
    tty_underline = ''
    tty_normal = ''
    tty_ok = 'OK'
    tty_error = 'ERROR'
    tty_warn = 'WARNING'


class StateMarkers(object):
    good = " " + tty_green + tty_bold + "*" + tty_normal
    warn = " " + tty_bgyellow + tty_black + tty_bold + "!" + tty_normal
    error = " " + tty_bgred + tty_white + tty_bold + "!" + tty_normal


def ok():
    sys.stdout.write(tty_ok + "\n")


def bail_out(message):
    sys.exit(message)


# Is used to duplicate output from stdout/stderr to a logfiles. This
# is e.g. used during "omd update" to have a chance to analyze errors
# during past updates
class Log(object):
    def __init__(self, fd, logfile):
        self.log = open(logfile, 'a')
        self.fd = fd

        if self.fd == 1:
            self.orig = sys.stdout
            sys.stdout = self
        else:
            self.orig = sys.stderr
            sys.stderr = self

        self.color_replace = re.compile("\033\\[\\d{1,2}m", re.UNICODE)

    def __del__(self):
        if self.fd == 1:
            sys.stdout = self.orig
        else:
            sys.stderr = self.orig
        self.log.close()

    def write(self, data):
        self.orig.write(data)
        self.log.write(self.color_replace.sub('', data))

    def flush(self):
        self.log.flush()
        self.orig.flush()


g_stdout_log = None
g_stderr_log = None


def start_logging(logfile):
    global g_stdout_log, g_stderr_log
    g_stdout_log = Log(1, logfile)
    g_stderr_log = Log(2, logfile)


def stop_logging():
    global g_stdout_log, g_stderr_log
    g_stdout_log = None
    g_stderr_log = None


def show_success(exit_code):
    if exit_code is True or exit_code == 0:
        ok()
    else:
        sys.stdout.write(tty_error + "\n")
    return exit_code


@contextlib.contextmanager
def chdir(path):
    """Change working directory and return on exit"""
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


#.
#   .--Dialog--------------------------------------------------------------.
#   |                     ____  _       _                                  |
#   |                    |  _ \(_) __ _| | ___   __ _                      |
#   |                    | | | | |/ _` | |/ _ \ / _` |                     |
#   |                    | |_| | | (_| | | (_) | (_| |                     |
#   |                    |____/|_|\__,_|_|\___/ \__, |                     |
#   |                                           |___/                      |
#   +----------------------------------------------------------------------+
#   |  Wrapper functions for interactive dialogs using the dialog cmd tool |
#   '----------------------------------------------------------------------'

patch_supports_merge = None


def patch_has_merge():
    # check wether our version of patch supports the option '--merge'
    global patch_supports_merge
    if patch_supports_merge is None:
        patch_supports_merge = (
            os.system(  # nosec
                "true | PATH=/omd/versions/default/bin:$PATH patch --merge >/dev/null 2>&1") == 0)
        if not patch_supports_merge:
            sys.stdout.write("Your version of patch does not support --merge.\n")
    return patch_supports_merge


def run_dialog(args):
    env = {"TERM": getenv("TERM", "linux"), "LANG": "de_DE.UTF-8"}
    p = subprocess.Popen(["dialog", "--shadow"] + args, env=env, stderr=subprocess.PIPE)
    response = p.stderr.read()
    return os.waitpid(p.pid, 0)[1] == 0, response


def dialog_menu(title, text, choices, defvalue, oktext, canceltext):
    args = ["--ok-label", oktext, "--cancel-label", canceltext]
    if defvalue is not None:
        args += ["--default-item", defvalue]
    args += ["--title", title, "--menu", text, "0", "0", "0"]  # "20", "60", "17" ]
    for choice_text, value in choices:
        args += [choice_text, value]
    return run_dialog(args)


def dialog_regex(title, text, regex, value, oktext, canceltext):
    while True:
        args = [
            "--ok-label", oktext, "--cancel-label", canceltext, "--title", title, "--inputbox",
            text, "0", "0", value
        ]
        change, new_value = run_dialog(args)
        if not change:
            return False, value
        elif not regex.match(new_value):
            dialog_message("Invalid value. Please try again.")
            value = new_value
        else:
            return True, new_value


def dialog_yesno(text, yeslabel="yes", nolabel="no"):
    state, _response = run_dialog(
        ["--yes-label", yeslabel, "--no-label", nolabel, "--yesno", text, "0", "0"])
    return state


def dialog_message(text, buttonlabel="OK"):
    run_dialog(["--ok-label", buttonlabel, "--msgbox", text, "0", "0"])


def user_confirms(site, title, message, relpath, yes_choice, yes_text, no_choice, no_text):
    # Handle non-interactive mode
    if opt_conflict == "abort":
        bail_out("Update aborted.")
    elif opt_conflict == "install":
        return False
    elif opt_conflict == "keepold":
        return True

    user_path = site.dir + "/" + relpath
    options = [(yes_choice, yes_text), (no_choice, no_text),
               ("shell", "Open a shell for looking around"),
               ("abort", "Stop here and abort update!")]
    while True:
        choice = ask_user_choices(title, message, options)
        if choice == "abort":
            bail_out("Update aborted.")
        elif choice == "shell":
            thedir = "/".join(user_path.split("/")[:-1])
            sys.stdout.write("\n Starting BASH. Type CTRL-D to continue.\n\n")
            subprocess.Popen(["bash", "-i"], cwd=thedir).wait()
        else:
            return choice == yes_choice


def wrap_text(text, width):
    def fillup(line, width):
        if len(line) < width:
            line += " " * (width - len(line))
        return line

    def justify(line, width):
        need_spaces = float(width - len(line))
        spaces = float(line.count(' '))
        newline = ""
        x = 0.0
        s = 0.0
        words = line.split()
        newline = words[0]
        for word in words[1:]:
            newline += ' '
            x += 1.0
            if s / x < need_spaces / spaces:
                newline += ' '
                s += 1
            newline += word
        return newline

    wrapped = []
    line = ""
    col = 0
    for word in text.split():
        netto = len(word)
        if line != "" and netto + col + 1 > width:
            wrapped.append(justify(line, width))
            col = 0
            line = ""
        if line != "":
            line += ' '
            col += 1
        line += word
        col += netto
    if line != "":
        wrapped.append(fillup(line, width))

    # remove trailing empty lines
    while wrapped[-1].strip() == "":
        wrapped = wrapped[:-1]
    return wrapped


def getch():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    if ord(ch) == 3:
        raise KeyboardInterrupt()
    return ch


def ask_user_choices(title, message, choices):
    sys.stdout.write("\n")

    def pl(line):
        sys.stdout.write(" %s %-76s %s\n" % (tty_bgcyan + tty_white, line, tty_normal))

    pl("")
    sys.stdout.write(" %s %-76s %s\n" % (tty_bgcyan + tty_white + tty_bold, title, tty_normal))
    for line in wrap_text(message, 76):
        pl(line)
    pl("")
    chars = []
    empty_line = " %s%-78s%s\n" % (tty_bgblue + tty_white, "", tty_normal)
    sys.stdout.write(empty_line)
    for choice, choice_title in choices:
        sys.stdout.write(" %s %s%s%s%-10s %-65s%s\n" %
                         (tty_bgblue + tty_white, tty_bold, choice[0], tty_normal + tty_bgblue +
                          tty_white, choice[1:], choice_title, tty_normal))
        for c in choice:
            if c.lower() not in chars:
                chars.append(c)
                break
    sys.stdout.write(empty_line)

    choicetxt = (tty_bold + tty_magenta + "/").join([
        (tty_bold + tty_white + char + tty_normal + tty_bgmagenta)
        for (char, _c) in zip(chars, choices)
    ])
    l = len(choices) * 2 - 1
    sys.stdout.write(" %s %s" % (tty_bgmagenta, choicetxt))
    sys.stdout.write(" ==> %s   %s" % (tty_bgred, tty_bgmagenta))
    sys.stdout.write(" " * (69 - l))
    sys.stdout.write("\b" * (71 - l))
    sys.stdout.write(tty_normal)
    while True:
        a = getch()
        for char, (choice, choice_title) in zip(chars, choices):
            if a == char:
                sys.stdout.write(tty_bold + tty_bgred + tty_white + a + tty_normal + "\n\n")
                return choice


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
    try:
        return subprocess.Popen(["pgrep", "-u", username],
                                stdin=open(os.devnull, "r"),
                                stdout=subprocess.PIPE,
                                close_fds=True).stdout.read().split()
    except:
        return []


def groupdel(groupname):
    try:
        p = subprocess.Popen(["groupdel", groupname],
                             stdin=open(os.devnull, "r"),
                             stdout=open(os.devnull, "w"),
                             stderr=subprocess.PIPE,
                             close_fds=True)
    except OSError as e:
        bail_out("\n" + tty_error + ": Failed to delete group '%s': %s" % (groupname, e))

    stderr = p.communicate()[1]
    if p.returncode != 0:
        bail_out("\n" + tty_error + ": Failed to delete group '%s': %s" % (groupname, stderr))


def groupadd(groupname, gid=None):
    cmd = ["groupadd"]
    if gid is not None:
        cmd += ["-g", "%d" % int(gid)]
    cmd.append(groupname)

    if subprocess.Popen(
            cmd,
            close_fds=True,
            stdin=open(os.devnull, "r"),
    ).wait() != 0:
        bail_out("Cannot create group for site user.")


def useradd(site, uid=None, gid=None):
    # Create user for running site 'name'
    groupadd(site.name, gid)
    useradd_options = g_info.USERADD_OPTIONS
    if uid is not None:
        useradd_options += " -u %d" % int(uid)
    if os.system(  # nosec
            "useradd %s -r -d '%s' -c 'OMD site %s' -g %s -G omd %s -s /bin/bash" %
        (useradd_options, site.dir, site.name, site.name, site.name)) != 0:
        groupdel(site.name)
        bail_out("Error creating site user.")

    # On SLES11+ there is a standard group "trusted" that the OMD site users should be members
    # of to be able to access CRON.
    if group_exists("trusted"):
        add_user_to_group(site.name, "trusted")

    # Add Apache to new group. It needs to be able to write in to the
    # command pipe and possible other stuff
    add_user_to_group(g_info.APACHE_USER, site.name)


def add_user_to_group(user, group):
    cmd = g_info.ADD_USER_TO_GROUP % {"user": user, "group": group}
    return os.system(cmd + " >/dev/null") == 0  # nosec


def userdel(name):
    if user_exists(name):
        try:
            p = subprocess.Popen(["userdel", "-r", name],
                                 stdin=open(os.devnull, "r"),
                                 stdout=open(os.devnull, "w"),
                                 stderr=subprocess.PIPE,
                                 close_fds=True)
        except OSError as e:
            bail_out("\n" + tty_error + ": Failed to delete user '%s': %s" % (name, e))

        stderr = p.communicate()[1]
        if p.returncode != 0:
            bail_out("\n" + tty_error + ": Failed to delete user '%s': %s" % (name, stderr))

    # On some OSes (e.g. debian) the group is automatically removed if
    # it bears the same name as the user. So first check for the group.
    if group_exists(name):
        groupdel(name)


def user_by_id(id_):
    try:
        return pwd.getpwuid(id_)
    except:
        return None


def user_id(name):
    try:
        return pwd.getpwnam(name).pw_uid
    except:
        return False


def user_exists(name):
    try:
        pwd.getpwnam(name)
        return True
    except:
        return False


def user_has_group(user, group):
    try:
        u = user_by_id(user_id(user))
        g = group_by_id(u.pw_gid)
        if g.gr_name == group:
            return True
        g = group_by_id(group_id(group))
        if user in g.gr_mem:
            return True
    except:
        return False


def group_exists(name):
    try:
        grp.getgrnam(name)
        return True
    except:
        return False


def group_by_id(id_):
    try:
        return grp.getgrgid(id_)
    except:
        return None


def group_id(name):
    try:
        g = grp.getgrnam(name)
        return g.gr_gid
    except:
        return None


def user_logged_in(name):
    """Check if processes of named user are existing"""
    return any(p for p in psutil.process_iter() if p.username() == name)


def user_verify(site, allow_populated=False):
    name = site.name

    if not user_exists(name):
        bail_out(tty_error + ": user %s does not exist" % name)

    user = user_by_id(user_id(name))
    if user.pw_dir != site.dir:
        bail_out(tty_error + ": Wrong home directory for user %s, must be %s" % (name, site.dir))

    if not os.path.exists(site.dir):
        bail_out(tty_error + ": home directory for user %s (%s) does not exist" % (name, site.dir))

    if not allow_populated and os.path.exists(site.dir + "/version"):
        bail_out(tty_error + ": home directory for user %s (%s) must be empty" % (name, site.dir))

    if not file_owner_verify(site.dir, user.pw_uid, user.pw_gid):
        bail_out(tty_error + ": home directory (%s) is not owned by user %s and group %s" %
                 (site.dir, name, name))

    group = group_by_id(user.pw_gid)
    if group is None or group.gr_name != name:
        bail_out(tty_error + ": primary group for siteuser must be %s" % name)

    if not user_has_group(g_info.APACHE_USER, name):
        bail_out(tty_error + ": apache user %s must be member of group %s" %
                 (g_info.APACHE_USER, name))

    if not user_has_group(name, "omd"):
        bail_out(tty_error + ": siteuser must be member of group omd")

    return True


def switch_to_site_user(site):
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
    os.setgroups(groups_of(site.name))
    os.setuid(uid)


def groups_of(username):
    # Note: Do NOT use grp.getgrall to fetch all availabile groups
    # Certain setups might have ldap group authorization and may start excessive queries
    return map(int, os.popen("id -G '%s'" % username).read().split())


#.
#   .--Sites---------------------------------------------------------------.
#   |                        ____  _ _                                     |
#   |                       / ___|(_) |_ ___  ___                          |
#   |                       \___ \| | __/ _ \/ __|                         |
#   |                        ___) | | ||  __/\__ \                         |
#   |                       |____/|_|\__\___||___/                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Helper functions for dealing with sites                             |
#   '----------------------------------------------------------------------'


def site_name():
    return pwd.getpwuid(os.getuid()).pw_name


def is_root():
    return os.getuid() == 0


def all_sites():
    l = [s for s in os.listdir("/omd/sites") if os.path.isdir(os.path.join("/omd/sites/", s))]
    l.sort()
    return l


def start_site(site):
    prepare_and_populate_tmpfs(site)
    call_init_scripts(site, "start")


def stop_if_not_stopped(site):
    if not site.is_stopped():
        stop_site(site)


def stop_site(site):
    call_init_scripts(site, "stop")


#.
#   .--Skeleton------------------------------------------------------------.
#   |                ____  _        _      _                               |
#   |               / ___|| | _____| | ___| |_ ___  _ __                   |
#   |               \___ \| |/ / _ \ |/ _ \ __/ _ \| '_ \                  |
#   |                ___) |   <  __/ |  __/ || (_) | | | |                 |
#   |               |____/|_|\_\___|_|\___|\__\___/|_| |_|                 |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Deal with file owners, permissions and the the skel hierarchy       |
#   '----------------------------------------------------------------------'

g_skel_permissions = {}  # type: Dict[str, int]


def read_skel_permissions():
    global g_skel_permissions
    g_skel_permissions = load_skel_permissions(omdlib.__version__)
    if not g_skel_permissions:
        bail_out("%s is missing or currupted." % skel_permissions_file_path(omdlib.__version__))


def load_skel_permissions(version):
    return load_skel_permissions_from(skel_permissions_file_path(version))


def load_skel_permissions_from(path):
    perms = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line == "" or line[0] == "#":
                continue
            path, perm = line.split()
            mode = int(perm, 8)
            perms[path] = mode
        return perms


def skel_permissions_file_path(version):
    return "/omd/versions/%s/share/omd/skel.permissions" % version


def get_skel_permissions(skel_path, perms, relpath):
    try:
        return perms[relpath]
    except KeyError:
        return get_file_permissions("%s/%s" % (skel_path, relpath))


def get_file_permissions(path):
    try:
        return os.stat(path).st_mode & 07777
    except:
        return 0


def get_file_owner(path):
    try:
        return pwd.getpwuid(os.stat(path).st_uid)[0]
    except:
        return None


def create_version_symlink(site, version):
    linkname = site.dir + "/version"
    if os.path.lexists(linkname):
        os.remove(linkname)
    os.symlink("../../versions/%s" % version, linkname)


def calculate_admin_password(options):
    if options.get("admin-password"):
        return options["admin-password"]
    return random_password()


def set_admin_password(site, pw):
    file("%s/etc/htpasswd" % site.dir, "w").write("cmkadmin:%s\n" % hash_password(pw))


def file_owner_verify(path, uid, gid):
    try:
        s = os.stat(path)
        if s.st_uid != uid or s.st_gid != gid:
            return False
    except:
        return False
    return True


def create_skeleton_files(site, directory):
    read_skel_permissions()
    replacements = site.replacements
    # Hack: exclude tmp if dir is '.'
    exclude_tmp = directory == "."
    skelroot = "/omd/versions/%s/skel" % omdlib.__version__
    with chdir(skelroot):  # make relative paths
        for dirpath, dirnames, filenames in os.walk(directory):
            if dirpath.startswith("./"):
                dirpath = dirpath[2:]
            for entry in dirnames + filenames:
                if exclude_tmp:
                    if dirpath == "." and entry == "tmp":
                        continue
                    if dirpath == "tmp" or dirpath.startswith("tmp/"):
                        continue
                create_skeleton_file(skelroot, site.dir, dirpath + "/" + entry, replacements)


def save_version_meta_data(site, version):
    """Make meta information from the version available in the site directory

    Currently it holds the following information
    A) A copy of the versions skel/ directory
    B) A copy of the skel.permissions file
    C) A version file containing the version number of the meta data
    """
    try:
        shutil.rmtree(site.version_meta_dir)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

    skelroot = "/omd/versions/%s/skel" % version
    shutil.copytree(skelroot, "%s/skel" % site.version_meta_dir, symlinks=True)

    shutil.copy(skel_permissions_file_path(version), "%s/skel.permissions" % site.version_meta_dir)

    with open("%s/version" % site.version_meta_dir, "w") as f:
        f.write("%s\n" % version)


def delete_user_file(user_path):
    if not os.path.islink(user_path) and os.path.isdir(user_path):
        shutil.rmtree(user_path)
    else:
        os.remove(user_path)


def delete_directory_contents(d):
    for f in os.listdir(d):
        delete_user_file(d + '/' + f)


def create_skeleton_file(skelbase, userbase, relpath, replacements):
    skel_path = skelbase + "/" + relpath
    user_path = userbase + "/" + relpath

    # Remove old version, if existing (needed during update)
    if os.path.exists(user_path):
        delete_user_file(user_path)

    # Create directories, symlinks and files
    if os.path.islink(skel_path):
        os.symlink(os.readlink(skel_path), user_path)
    elif os.path.isdir(skel_path):
        os.makedirs(user_path)
    else:
        file(user_path, "w").write(replace_tags(file(skel_path).read(), replacements))

    if not os.path.islink(skel_path):
        mode = g_skel_permissions.get(relpath)
        if mode is None:
            if os.path.isdir(skel_path):
                mode = 0755
            else:
                mode = 0644
        os.chmod(user_path, mode)


def chown_tree(directory, user):
    uid = pwd.getpwnam(user).pw_uid
    gid = pwd.getpwnam(user).pw_gid
    os.chown(directory, uid, gid)
    for dirpath, dirnames, filenames in os.walk(directory):
        for entry in dirnames + filenames:
            os.lchown(dirpath + "/" + entry, uid, gid)


def try_chown(filename, user):
    if os.path.exists(filename):
        try:
            uid = pwd.getpwnam(user).pw_uid
            gid = pwd.getpwnam(user).pw_gid
            os.chown(filename, uid, gid)
        except Exception as e:
            sys.stderr.write("Cannot chown %s to %s: %s\n" % (filename, user, e))


def instantiate_skel(site, path):
    try:
        t = file(path).read()
        return replace_tags(t, site.replacements)
    except:
        return ""  # e.g. due to permission error


# Walks all files in the skeleton dir to execute a function for each file
# The given handler is called with the provided args. Additionally the relative
# path of the file to handle is handed over in the 'relpath' parameter.

# When called with a path in 'exclude_if_in' then paths existing relative to
# that are skipped. This is used for a second run during the update-process: to handle
# files that have vanished in the new version.

# The option 'relbase' is optional. It can contain a relative path which can be used
# as base for the walk instead of walking the whole tree.


# The function returns a set of already handled files.
def walk_skel(root, handler, args, depth_first, exclude_if_in=None, relbase='.'):
    with chdir(root):
        # Note: os.walk first finds level 1 directories, then deeper
        # layers. If we need a real depth search instead, where we first
        # handle deep directories and files, then the top level ones.
        walk_entries = list(os.walk(relbase))
        if depth_first:
            walk_entries.reverse()

        for dirpath, dirnames, filenames in walk_entries:
            if dirpath.startswith("./"):
                dirpath = dirpath[2:]
            if dirpath.startswith("tmp"):
                continue

            # In depth first search first handle files, then directories
            if depth_first:
                entries = filenames + dirnames
            else:
                entries = dirnames + filenames
            for entry in entries:
                path = dirpath + "/" + entry
                if path.startswith("./"):
                    path = path[2:]

                if exclude_if_in and os.path.exists(exclude_if_in + "/" + path):
                    continue

                todo = True
                while todo:
                    try:
                        handler(path, *args)
                        todo = False
                    except Exception:
                        todo = False
                        sys.stderr.write(StateMarkers.error * 40 + "\n")
                        sys.stderr.write(StateMarkers.error + " Exception      %s\n" % (path))
                        sys.stderr.write(
                            StateMarkers.error + " " +
                            traceback.format_exc().replace('\n', "\n" + StateMarkers.error + " ") +
                            "\n")
                        sys.stderr.write(StateMarkers.error * 40 + "\n")

                        # If running in interactive mode ask the user to terminate or retry
                        # In case of non interactive mode just throw the exception
                        if opt_conflict == 'ask':
                            options = [("retry", "Retry the operation"),
                                       ("continue", "Continue with next files"),
                                       ("abort", "Stop here and abort update!")]
                            choice = ask_user_choices(
                                'Problem occured',
                                'We detected an exception (printed above). You have the '
                                'chance to fix things and retry the operation now.', options)
                            if choice == 'abort':
                                bail_out("Update aborted.")
                            elif choice == 'retry':
                                todo = True  # Try again


#.
#   .--omd update----------------------------------------------------------.
#   |                           _                   _       _              |
#   |        ___  _ __ ___   __| |  _   _ _ __   __| | __ _| |_ ___        |
#   |       / _ \| '_ ` _ \ / _` | | | | | '_ \ / _` |/ _` | __/ _ \       |
#   |      | (_) | | | | | | (_| | | |_| | |_) | (_| | (_| | ||  __/       |
#   |       \___/|_| |_| |_|\__,_|  \__,_| .__/ \__,_|\__,_|\__\___|       |
#   |                                    |_|                               |
#   +----------------------------------------------------------------------+
#   |  Complex handling of skeleton and user files during update           |
#   '----------------------------------------------------------------------'


# Change site specific information in files originally create from
# skeleton files. Skip files below tmp/
def patch_skeleton_files(old_site, new_site):
    skelroot = "/omd/versions/%s/skel" % omdlib.__version__
    with chdir(skelroot):  # make relative paths
        for dirpath, _dirnames, filenames in os.walk("."):
            if dirpath.startswith("./"):
                dirpath = dirpath[2:]
            targetdir = new_site.dir + "/" + dirpath
            if targetdir.startswith(new_site.tmp_dir):
                continue  # Skip files below tmp
            for fn in filenames:
                src = dirpath + "/" + fn
                dst = targetdir + "/" + fn
                if os.path.isfile(src) and not os.path.islink(src) \
                    and os.path.exists(dst): # not deleted by user
                    try:
                        patch_template_file(src, dst, old_site, new_site)
                    except Exception as e:
                        sys.stderr.write("Error patching template file '%s': %s\n" % (dst, e))


def patch_template_file(src, dst, old_site, new_site):
    # Create patch from old instantiated skeleton file to new one
    content = file(src).read()
    for site in [old_site, new_site]:
        filename = "%s.skel.%s" % (dst, site.name)
        file(filename, "w").write(replace_tags(content, site.replacements))
        try_chown(filename, new_site.name)

    # If old and new skeleton file are identical, then do nothing
    old_orig_path = "%s.skel.%s" % (dst, old_site.name)
    new_orig_path = "%s.skel.%s" % (dst, new_site.name)
    if file(old_orig_path).read() == file(new_orig_path).read():
        os.remove(old_orig_path)
        os.remove(new_orig_path)
        return

    # Now create a patch from old to new and immediately apply on
    # existing - possibly user modified - file.

    result = os.system(  # nosec
        "diff -u %s %s | %s/bin/patch --force --backup --forward --silent %s" %
        (old_orig_path, new_orig_path, new_site.dir, dst))
    try_chown(dst, new_site.name)
    try_chown(dst + ".rej", new_site.name)
    try_chown(dst + ".orig", new_site.name)
    if result == 0:
        sys.stdout.write(StateMarkers.good + " Converted      %s\n" % src)
    else:
        # Make conflict resolution interactive - similar to omd update
        options = [
            ("diff", "Show conversion patch, that I've tried to apply"),
            ("you", "Show your changes compared with the original default version"),
            ("edit", "Edit half-converted file (watch out for >>>> and <<<<)"),
            ("try again", "Edit your original file and try again"),
            ("keep", "Keep half-converted version of the file"),
            ("restore", "Restore your original version of the file"),
            ("install", "Install the default version of the file"),
            ("brute",
             "Simply replace /%s/ with /%s/ in that file" % (old_site.name, new_site.name)),
            ("shell", "Open a shell for looking around"),
            ("abort", "Stop here and abort!"),
        ]

        while True:
            if opt_conflict in ["abort", "install"]:
                choice = opt_conflict
            elif opt_conflict == "keepold":
                choice = "restore"
            else:
                choice = ask_user_choices(
                    "Conflicts in " + src + "!",
                    "I've tried to merge your changes with the renaming of %s into %s.\n"
                    "Unfortunately there are conflicts with your changes. \n"
                    "You have the following options: " % (old_site.name, new_site.name), options)

            if choice == "abort":
                bail_out("Renaming aborted.")
            elif choice == "keep":
                break
            elif choice == "edit":
                os.system("%s '%s'" % (get_editor(), dst))  # nosec
            elif choice == "diff":
                os.system("diff -u %s %s%s" % (old_orig_path, new_orig_path, pipe_pager()))  # nosec
            elif choice == "brute":
                os.system(  # nosec
                    "sed 's@/%s/@/%s/@g' %s.orig > %s" % (old_site.name, new_site.name, dst, dst))
                changed = len([
                    l for l in os.popen("diff %s.orig %s" % (dst, dst)).readlines()  # nosec
                    if l.startswith(">")
                ])
                if changed == 0:
                    sys.stdout.write("Found no matching line.\n")
                else:
                    sys.stdout.write("Did brute-force replace, changed %s%d%s lines:\n" %
                                     (tty_bold, changed, tty_normal))
                    os.system("diff -u %s.orig %s" % (dst, dst))  # nosec
                    break
            elif choice == "you":
                os.system(  # nosec
                    "pwd ; diff -u %s %s.orig%s" % (old_orig_path, dst, pipe_pager()))
            elif choice == "restore":
                os.rename(dst + ".orig", dst)
                sys.stdout.write("Restored your version.\n")
                break
            elif choice == "install":
                os.rename(new_orig_path, dst)
                sys.stdout.write("Installed default file (with site name %s).\n" % new_site.name)
                break
            elif choice == "shell":
                relname = src.split("/")[-1]
                sys.stdout.write(" %-35s the half-converted file\n" % (relname,))
                sys.stdout.write(" %-35s your original version\n" % (relname + ".orig"))
                sys.stdout.write(" %-35s the failed parts of the patch\n" % (relname + ".rej"))
                sys.stdout.write(" %-35s default version with the old site name\n" %
                                 (relname + ".skel.%s" % old_site.name))
                sys.stdout.write(" %-35s default version with the new site name\n" %
                                 (relname + ".skel.%s" % new_site.name))

                sys.stdout.write("\n Starting BASH. Type CTRL-D to continue.\n\n")
                thedir = "/".join(dst.split("/")[:-1])
                os.system("su - %s -c 'cd %s ; bash -i'" % (new_site.name, thedir))  # nosec

    # remove unnecessary files
    try:
        os.remove(dst + ".skel." + old_site.name)
        os.remove(dst + ".skel." + new_site.name)
        os.remove(dst + ".orig")
        os.remove(dst + ".rej")
    except:
        pass


# Try to merge changes from old->new version and
# old->user version
def merge_update_file(site, relpath, old_version, new_version):
    fn = tty_bold + relpath + tty_normal

    user_path = site.dir + "/" + relpath
    permissions = os.stat(user_path).st_mode

    if _try_merge(site, relpath, old_version, new_version) == 0:
        # ACHTUNG: Hier müssen die Dateien $DATEI-alt, $DATEI-neu und $DATEI.orig
        # gelöscht werden
        sys.stdout.write(StateMarkers.good + " Merged         %s\n" % fn)
        return

    # No success. Should we try merging the users' changes onto the new file?
    # user_patch = os.popen(
    merge_message = ' (watch out for >>>>> and <<<<<)' if patch_has_merge() else ''
    editor = get_editor()
    reject_file = user_path + ".rej"

    options = [("diff", "Show differences between the new default and your version"),
               ("you", "Show your changes compared with the old default version"),
               ("new", "Show what has changed from %s to %s" % (old_version, new_version))]
    if os.path.exists(reject_file):  # missing if patch has --merge
        options.append(("missing", "Show which changes from the update have not been merged"))
    options += [
        ("edit", "Edit half-merged file%s" % merge_message),
        ("try again", "Edit your original file and try again"),
        ("keep", "Keep half-merged version of the file"),
        ("restore", "Restore your original version of the file"),
        ("install", "Install the new default version"),
        ("shell", "Open a shell for looking around"),
        ("abort", "Stop here and abort update!"),
    ]

    while True:
        if opt_conflict in ["install", "abort"]:
            choice = opt_conflict
        elif opt_conflict == "keepold":
            choice = "restore"
        else:
            choice = ask_user_choices(
                "Conflicts in " + relpath + "!",
                "I've tried to merge the changes from version %s to %s into %s.\n"
                "Unfortunately there are conflicts with your changes. \n"
                "You have the following options: " % (old_version, new_version, relpath), options)

        if choice == "abort":
            bail_out("Update aborted.")
        elif choice == "keep":
            break
        elif choice == "edit":
            os.system("%s '%s'" % (editor, user_path))  # nosec
        elif choice == "diff":
            os.system(  # nosec
                "diff -u %s.orig %s-%s%s" % (user_path, user_path, new_version, pipe_pager()))
        elif choice == "you":
            os.system(  # nosec
                "diff -u %s-%s %s.orig%s" % (user_path, old_version, user_path, pipe_pager()))
        elif choice == "new":
            os.system(  # nosec
                "diff -u %s-%s %s-%s%s" %
                (user_path, old_version, user_path, new_version, pipe_pager()))
        elif choice == "missing":
            if os.path.exists(reject_file):
                sys.stdout.write(tty_bgblue + tty_white + file(reject_file).read() + tty_normal)
            else:
                sys.stdout.write("File %s not found.\n" % reject_file)

        elif choice == "shell":
            relname = relpath.split("/")[-1]
            sys.stdout.write(" %-25s: the current half-merged file\n" % relname)
            sys.stdout.write(" %-25s: the default version of %s\n" %
                             (relname + "." + old_version, old_version))
            sys.stdout.write(" %-25s: the default version of %s\n" %
                             (relname + "." + new_version, new_version))
            sys.stdout.write(" %-25s: your original version\n" % (relname + ".orig"))
            if os.path.exists(reject_file):
                sys.stdout.write(" %-25s: changes that haven't been merged\n" % relname + ".rej")

            sys.stdout.write("\n Starting BASH. Type CTRL-D to continue.\n\n")
            thedir = "/".join(user_path.split("/")[:-1])
            os.system("cd '%s' ; bash -i" % thedir)  # nosec
        elif choice == "restore":
            os.rename(user_path + ".orig", user_path)
            os.chmod(user_path, permissions)
            sys.stdout.write("Restored your version.\n")
            break
        elif choice == "try again":
            os.rename(user_path + ".orig", user_path)
            os.system("%s '%s'" % (editor, user_path))  # nosec
            if _try_merge(site, relpath, old_version, new_version) == 0:
                sys.stdout.write("Successfully merged changes from %s -> %s into %s\n" %
                                 (old_version, new_version, fn))
                return
            else:
                sys.stdout.write(" Merge failed again.\n")

        else:  # install
            os.rename("%s-%s" % (user_path, new_version), user_path)
            os.chmod(user_path, permissions)
            sys.stdout.write("Installed default file of version %s.\n" % new_version)
            break

    # Clean up temporary files
    for p in [
            "%s-%s" % (user_path, old_version),
            "%s-%s" % (user_path, new_version),
            "%s.orig" % user_path,
            "%s.rej" % user_path
    ]:
        try:
            os.remove(p)
        except:
            pass


def _try_merge(site, relpath, old_version, new_version):
    user_path = site.dir + "/" + relpath

    for version, skelroot in [(old_version, site.version_skel_dir),
                              (new_version, "/omd/versions/%s/skel" % new_version)]:
        p = "%s/%s" % (skelroot, relpath)
        while True:
            try:
                skel_content = file(p).read()
                break
            except:
                # Do not ask the user in non-interactive mode.
                if opt_conflict in ["abort", "install"]:
                    bail_out("Skeleton file '%s' of version %s not readable." % (p, version))
                elif opt_conflict == "keepold" or not user_confirms(
                        site, "Skeleton file of version %s not readable" % version,
                        "The file '%s' is not readable for the site user. "
                        "This is most probably due a bug in release 0.42. "
                        "You can either fix that problem by making the file "
                        "readable with doing as root: chmod +r '%s' "
                        "or assume the file as empty. In that case you might "
                        "damage your configuration file "
                        "in case you have made changes to it in your site. What shall we do?" %
                    (p, p), relpath, "retry", "Retry reading the file (after you've fixed it)",
                        "ignore", "Assume the file to be empty"):
                    skel_content = ""
                    break
        file("%s-%s" % (user_path, version),
             "w").write(replace_tags(skel_content, site.replacements))
    version_patch = os.popen(  # nosec
        "diff -u %s-%s %s-%s" % (user_path, old_version, user_path, new_version)).read()

    # First try to merge the changes in the version into the users' file
    merge = '--merge' if patch_has_merge() else ''
    f = os.popen(  # nosec
        "PATH=/omd/versions/default/bin:$PATH patch --force --backup --forward --silent %s %s >/dev/null"
        % (merge, user_path), "w")
    f.write(version_patch)
    status = f.close()
    if status:
        return status / 256
    return 0


# Compares two files and returns infos wether the file type or contants have changed """
def file_status(site, source_path, target_path):
    source_type = filetype(source_path)
    target_type = filetype(target_path)

    if source_type == "file":
        source_content = file_contents(site, source_path)

    if target_type == "file":
        target_content = file_contents(site, target_path)

    changed_type = source_type != target_type
    # FIXME: Was ist, wenn aus einer Datei ein Link gemacht wurde? Oder umgekehrt?
    changed_content = (source_type == "file" \
                       and target_type == "file" \
                       and source_content != target_content) or \
                      (source_type == "link" \
                       and target_type == "link" \
                       and os.readlink(source_path) != os.readlink(target_path))
    changed = changed_type or changed_content

    return (changed_type, changed_content, changed)


def update_file(relpath, site, old_version, new_version, old_perms):
    old_skel = site.version_skel_dir
    new_skel = "/omd/versions/%s/skel" % new_version

    replacements = site.replacements

    old_path = old_skel + "/" + relpath
    new_path = new_skel + "/" + relpath
    user_path = site.dir + "/" + relpath

    old_type = filetype(old_path)
    new_type = filetype(new_path)
    user_type = filetype(user_path)

    # compare our new version with the user's version
    _type_differs, _content_differs, differs = file_status(site, user_path, new_path)

    # compare our old version with the user's version
    user_changed_type, user_changed_content, user_changed = file_status(site, old_path, user_path)

    # compare our old with our new version
    _we_changed_type, _we_changed_content, we_changed = file_status(site, old_path, new_path)

    non_empty_directory = not os.path.islink(user_path) and os.path.isdir(user_path) and bool(
        os.listdir(user_path))

    #     if opt_verbose:
    #         sys.stdout.write("%s%s%s:\n" % (tty_bold, relpath, tty_normal))
    #         sys.stdout.write("  you       : %s\n" % user_type)
    #         sys.stdout.write("  %-10s: %s\n" % (old_version, old_type))
    #         sys.stdout.write("  %-10s: %s\n" % (new_version, new_type))

    # A --> MISSING FILES

    # Handle cases with missing files first. At least old or new are present,
    # or this function would never have been invoked.
    fn = tty_bold + tty_bgblue + tty_white + relpath + tty_normal
    fn = tty_bold + relpath + tty_normal

    # 1) New version ships new skeleton file -> simply install
    if not old_type and not user_type:
        create_skeleton_file(new_skel, site.dir, relpath, replacements)
        sys.stdout.write(StateMarkers.good + " Installed %-4s %s\n" % (new_type, fn))

    # 2) new version ships new skeleton file, but user's own file/directory/link
    #    is in the way.
    # 2a) the users file is identical with our new version
    elif not old_type and not differs:
        sys.stdout.write(StateMarkers.good + " Identical new  %s\n" % fn)

    # 2b) user's file has a different content or type
    elif not old_type:
        if user_confirms(
                site, "Conflict at " + relpath, "The new version ships the %s %s, "
                "but you have created a %s in that place "
                "yourself. Shall we keep your %s or replace "
                "is with my %s?" % (new_type, relpath, user_type, user_type, new_type), relpath,
                "keep", "Keep your %s" % user_type, "replace",
                "Replace your %s with the new default %s" % (user_type, new_type)):
            sys.stdout.write(StateMarkers.warn + " Keeping your   %s\n" % fn)
        else:
            create_skeleton_file(new_skel, site.dir, relpath, replacements)
            sys.stdout.write(StateMarkers.good + " Installed %-4s %s\n" % (new_type, fn))

    # 3) old version had a file which has vanished in new (got obsolete). If the user
    #    has deleted it himself, we are just happy
    elif not new_type and not user_type:
        sys.stdout.write(StateMarkers.good + " Obsolete       %s\n" % fn)

    # 3b) same, but user has not deleted and changed type
    elif not new_type and user_changed_type:
        if user_confirms(
                site, "Obsolete file " + relpath, "The %s %s has become obsolete in "
                "this version, but you have changed it into a "
                "%s. Do you want to keep your %s or "
                "may I delete it for you, please?" % (old_type, relpath, user_type, user_type),
                relpath, "keep", "Keep your %s" % user_type, "delete", "Delete it"):
            sys.stdout.write(StateMarkers.warn + " Keeping your   %s\n" % fn)
        else:
            delete_user_file(user_path)
            sys.stdout.write(StateMarkers.warn + " Deleted        %s\n" % fn)

    # 3c) same, but user has changed it contents
    elif not new_type and user_changed_content:
        if user_confirms(
                site, "Changes in obsolete %s %s" % (old_type, relpath),
                "The %s %s has become obsolete in "
                "the new version, but you have changed its contents. "
                "Do you want to keep your %s or "
                "may I delete it for you, please?" % (old_type, relpath, user_type), relpath,
                "keep", "keep your %s, though it is obsolete" % user_type, "delete",
                "delete your %s" % user_type):
            sys.stdout.write(StateMarkers.warn + " Keeping your   %s\n" % fn)
        else:
            delete_user_file(user_path)
            sys.stdout.write(StateMarkers.warn + " Deleted        %s\n" % fn)

    # 3d) same, but it is a directory which is not empty
    elif not new_type and non_empty_directory:
        if user_confirms(
                site, "Non empty obsolete directory %s" % (relpath),
                "The directory %s has become obsolete in "
                "the new version, but you have contents in it. "
                "Do you want to keep your directory or "
                "may I delete it for you, please?" % (relpath), relpath, "keep",
                "keep your directory, though it is obsolete", "delete", "delete your directory"):
            sys.stdout.write(StateMarkers.warn + " Keeping your   %s\n" % fn)
        else:
            delete_user_file(user_path)
            sys.stdout.write(StateMarkers.warn + " Deleted        %s\n" % fn)

    # 3e) same, but user hasn't changed anything -> silently delete
    elif not new_type:
        delete_user_file(user_path)
        sys.stdout.write(StateMarkers.good + " Vanished       %s\n" % fn)

    # 4) old and new exist, but user file not. User has deleted that
    #    file. We simply do nothing in that case. The user surely has
    #    a good reason why he deleted the file.
    elif not user_type and not we_changed:
        sys.stdout.write(StateMarkers.good +
                         " Unwanted       %s (unchanged, deleted by you)\n" % fn)

    # 4b) File changed in new version. Simply warn if user has deleted it.
    elif not user_type:
        sys.stdout.write(StateMarkers.warn + " Missing        %s\n" % fn)

    # B ---> UNCHANGED, EASY CASES

    # 5) New version didn't change anything -> no need to update
    elif not we_changed:
        pass

    # 6) User didn't change anything -> take over new version
    elif not user_changed:
        create_skeleton_file(new_skel, site.dir, relpath, replacements)
        sys.stdout.write(StateMarkers.good + " Updated        %s\n" % fn)

    # 7) User changed, but accidentally exactly as we did -> no action neccessary
    elif not differs:
        sys.stdout.write(StateMarkers.good + " Identical      %s\n" % fn)

    # TEST UNTIL HERE

    # C ---> PATCH DAY, HANDLE FILES
    # 7) old, new and user are files. And all are different
    elif old_type == "file" and new_type == "file" and user_type == "file":
        try:
            merge_update_file(site, relpath, old_version, new_version)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            sys.stdout.write(StateMarkers.error + " Cannot merge: %s\n" % e)

    # D ---> SYMLINKS
    # 8) all are symlinks, all changed
    elif old_type == "link" and new_type == "link" and user_type == "link":
        if user_confirms(
                site, "Symbolic link conflict at " + relpath, "'%s' is a symlink that pointed to "
                "%s in the old version and to "
                "%s in the new version. But meanwhile you "
                "changed to link target to %s. "
                "Shall I keep your link or replace it with "
                "the new default target?" %
            (relpath, os.readlink(old_path), os.readlink(new_path), os.readlink(user_path)),
                relpath, "keep", "Keep your symbolic link pointing to %s" % os.readlink(user_path),
                "replace", "Change link target to %s" % os.readlink(new_path)):
            sys.stdout.write(StateMarkers.warn + " Keeping your   %s\n" % fn)
        else:
            os.remove(user_path)
            os.symlink(os.readlink(new_path), user_path)
            sys.stdout.write(StateMarkers.warn + " Set link       %s to new target %s\n" %
                             (fn, os.readlink(new_path)))

    # E ---> FILE TYPE HAS CHANGED (NASTY)

    # Now we have to handle cases, where the file types of the three
    # versions are not identical and at the same type the user or
    # have changed the third file to. We cannot merge here, the user
    # has to decide wether to keep his version of use ours.

    # 9) We have changed the file type
    elif old_type != new_type:
        if user_confirms(
                site, "File type change at " + relpath, "The %s %s has been changed into a %s in "
                "the new version. Meanwhile you have changed "
                "the %s of your copy of that %s. "
                "Do you want to keep your version or replace "
                "it with the new default? " %
            (old_type, relpath, new_type, user_changed_type and "type" or "content", old_type),
                relpath, "keep", "Keep your %s" % user_type, "replace",
                "Replace it with the new %s" % new_type):
            sys.stdout.write(StateMarkers.warn + " Keeping your version of %s\n" % fn)
        else:
            create_skeleton_file(new_skel, site.dir, relpath, replacements)
            sys.stdout.write(StateMarkers.warn + " Replaced your %s %s by new default %s.\n" %
                             (user_type, relpath, new_type))

    # 10) The user has changed the file type, we just the content
    elif old_type != user_type:
        if user_confirms(
                site, "Type change conflicts with content change at " + relpath,
                "Usually %s is a %s in both the "
                "old and new version. But you have changed it "
                "into a %s. Do you want to keep that or may "
                "I replace your %s with the new default "
                "%s, please?" % (relpath, old_type, user_type, user_type, new_type), relpath,
                "keep", "Keep your %s" % user_type, "replace",
                "Replace it with the new %s" % new_type):
            sys.stdout.write(StateMarkers.warn + " Keeping your %s %s.\n" % (user_type, fn))
        else:
            create_skeleton_file(new_skel, site.dir, relpath, replacements)
            sys.stdout.write(StateMarkers.warn +
                             " Delete your %s and created new default %s %s.\n" %
                             (user_type, new_type, fn))

    # 11) This case should never happen, if I've not lost something
    else:
        if user_confirms(
                site, "Something nasty happened at " + relpath, "You somehow fiddled along with "
                "%s, and I do not have the "
                "slightest idea what's going on here. May "
                "I please install the new default %s "
                "here, or do you want to keep your %s?" % (relpath, new_type, user_type), relpath,
                "keep", "Keep your %s" % user_type, "replace",
                "Replace it with the new %s" % new_type):
            sys.stdout.write(StateMarkers.warn + " Keeping your %s %s.\n" % (user_type, fn))
        else:
            create_skeleton_file(new_skel, site.dir, relpath, replacements)
            sys.stdout.write(StateMarkers.warn +
                             " Delete your %s and created new default %s %s.\n" %
                             (user_type, new_type, fn))

    # Now the new file/link/directory is in place, deleted or whatever. The
    # user might have interferred and changed things. We need to make sure
    # that file permissions are also updated. But the user might have changed
    # something himself.

    user_type = filetype(user_path)
    old_perm = get_skel_permissions(old_skel, old_perms, relpath)
    new_perm = get_skel_permissions(new_skel, g_skel_permissions, relpath)
    user_perm = get_file_permissions(user_path)

    # Fix permissions not for links and only if the new type is as expected
    # and the current permissions are not as the should be
    what = None
    if new_type != "link" \
        and user_type == new_type \
        and user_perm != new_perm:

        # Permissions have changed, but file type not
        if old_type == new_type \
            and user_perm != old_perm \
            and old_perm != new_perm:
            if user_confirms(
                    site, "Permission conflict at " + relpath,
                    "The proposed permissions of %s have changed from %04o "
                    "to %04o in the new version, but you have set %04o. "
                    "May I use the new default permissions or do "
                    "you want to keep yours?" % (relpath, old_perm, new_perm, user_perm), relpath,
                    "keep", "Keep permissions at %04o" % user_perm, "default",
                    "Set permission to %04o" % new_perm):
                what = "keep"
            else:
                what = "default"

        # Permissions have changed, no conflict with user
        elif old_type == new_type \
            and user_perm == old_perm:
            what = "default"

        # Permissions are not correct: all other cases (where type is as expected)
        elif old_perm != new_perm:
            if user_confirms(
                    site, "Wrong permission of " + relpath,
                    "The proposed permissions of %s are %04o, but currently are "
                    "%04o. May I use the new default "
                    "permissions or keep yours?" % (relpath, new_perm, user_perm), relpath, "keep",
                    "Keep permissions at %04o" % user_perm, "default",
                    "Set permission to %04o" % new_perm):
                what = "keep"
            else:
                what = "default"

        if what == "keep":
            sys.stdout.write(StateMarkers.warn + " Permissions    %04o %s (unchanged)\n" %
                             (user_perm, fn))
        elif what == "default":
            try:
                os.chmod(user_path, new_perm)
                sys.stdout.write(StateMarkers.good + " Permissions    %04o -> %04o %s\n" %
                                 (user_perm, new_perm, fn))
            except Exception as e:
                sys.stdout.write(StateMarkers.error +
                                 " Permission:    cannot change %04o -> %04o %s: %s\n" %
                                 (user_perm, new_perm, fn, e))


def filetype(p):
    # check for symlinks first. Might be dangling. In that
    # case os.path.exists checks the links target for existance
    # and reports it is non-existing.
    if os.path.islink(p):
        tp = "link"
    elif not os.path.exists(p):
        tp = None
    elif os.path.isdir(p):
        tp = "dir"
    else:
        tp = "file"

    return tp


# Returns the file contents of a site file or a skel file
def file_contents(site, path):
    if '/skel/' in path:
        return instantiate_skel(site, path)
    return file(path).read()


#.
#   .--tmpfs---------------------------------------------------------------.
#   |                     _                    __                          |
#   |                    | |_ _ __ ___  _ __  / _|___                      |
#   |                    | __| '_ ` _ \| '_ \| |_/ __|                     |
#   |                    | |_| | | | | | |_) |  _\__ \                     |
#   |                     \__|_| |_| |_| .__/|_| |___/                     |
#   |                                  |_|                                 |
#   +----------------------------------------------------------------------+
#   |  Helper functions for dealing with the tmpfs                         |
#   '----------------------------------------------------------------------'


def tmpfs_mounted(sitename):
    # Problem here: if /omd is a symbolic link somewhere else,
    # then in /proc/mounts the physical path will appear and be
    # different from tmp_path. We just check the suffix therefore.
    path_suffix = "sites/%s/tmp" % sitename
    for line in file("/proc/mounts"):
        try:
            _device, mp, fstype, _options, _dump, _fsck = line.split()
            if mp.endswith(path_suffix) and fstype == 'tmpfs':
                return True
        except:
            continue
    return False


def prepare_and_populate_tmpfs(site):
    prepare_tmpfs(site)

    if not os.listdir(site.tmp_dir):
        create_skeleton_files(site, "tmp")
        chown_tree(site.tmp_dir, site.name)
        _mark_tmpfs_initialized(site)
    _create_livestatus_tcp_socket_link(site)


def prepare_tmpfs(site):
    if tmpfs_mounted(site.name):
        return  # Fine: Mounted

    if site.conf["TMPFS"] != "on":
        sys.stdout.write("Preparing tmp directory %s..." % site.tmp_dir)
        sys.stdout.flush()

        if os.path.exists(site.tmp_dir):
            return

        try:
            os.mkdir(site.tmp_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:  # File exists
                raise
        return

    sys.stdout.write("Creating temporary filesystem %s..." % site.tmp_dir)
    sys.stdout.flush()
    if not os.path.exists(site.tmp_dir):
        os.mkdir(site.tmp_dir)

    mount_options = shlex.split(g_info.MOUNT_OPTIONS)
    p = subprocess.Popen(["mount"] + mount_options + [site.tmp_dir],
                         shell=False,
                         stdin=open(os.devnull),
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    exit_code = p.wait()
    if exit_code == 0:
        ok()
        return  # Fine: Mounted

    sys.stdout.write(p.stdout.read())
    if is_dockerized():
        sys.stdout.write(tty_warn + ": "
                         "Could not mount tmpfs. You may either start the container in "
                         "privileged mode or use the \"docker run\" option \"--tmpfs\" to "
                         "make docker do the tmpfs mount for the site.\n")

    sys.stdout.write(tty_warn + ": You may continue without tmpfs, but the "
                     "performance of Check_MK may be degraded.\n")


def _mark_tmpfs_initialized(site):
    """Write a simple file marking the time of the tmpfs structure initialization

    The st_ctime of the file will be used by Checkmk to know when the tmpfs file
    structure was initialized."""
    with Path(site.tmp_dir, "initialized").open("w", encoding="utf-8") as f:
        f.write(u"")


def is_dockerized():
    return os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")


def tmpfs_is_managed_by_node(site):
    """When running in a container, and the tmpfs is managed by the node, the
    mount is visible, but can not be unmounted. umount exits with 32 in this
    case. Treat this case like there is no tmpfs and only the directory needs
    to be cleaned."""
    if not is_dockerized():
        return False

    if not tmpfs_mounted(site.name):
        return False

    return subprocess.call(["umount", site.tmp_dir],
                           stdout=open(os.devnull, "w"),
                           stderr=subprocess.STDOUT) in [1, 32]


def unmount_tmpfs(site, output=True, kill=False):
    # Clear directory hierarchy when not using a tmpfs
    # During omd update TMPFS hook might not be set so assume
    # that the hook is enabled by default.
    # If kill is True, then we do an fuser -k on the tmp
    # directory first.
    if not tmpfs_mounted(site.name) or tmpfs_is_managed_by_node(site):
        tmp = site.tmp_dir
        if os.path.exists(tmp):
            if output:
                sys.stdout.write("Cleaning up tmp directory...")
                sys.stdout.flush()
            delete_directory_contents(tmp)
            if output:
                ok()
        return True

    if output:
        sys.stdout.write("Unmounting temporary filesystem...")

    for _t in range(0, 10):
        if not tmpfs_mounted(site.name):
            if output:
                ok()
            return True

        if subprocess.call(["umount", site.tmp_dir]) == 0:
            if output:
                ok()
            return True

        if kill:
            if output:
                sys.stdout.write("Killing processes still using '%s'\n" % site.tmp_dir)
            subprocess.call(["fuser", "--silent", "-k", site.tmp_dir])

        if output:
            sys.stdout.write(kill and "K" or ".")
            sys.stdout.flush()
        time.sleep(1)

    if output:
        bail_out(tty_error + ": Cannot unmount temporary filesystem.")
    else:
        return False


# Extracted to separate function to be able to monkeypatch the path for tests
def fstab_path():
    return "/etc/fstab"


def add_to_fstab(site, tmpfs_size=None):
    if not os.path.exists(fstab_path()):
        return  # Don't do anything in case there is no fstab

    # tmpfs                   /opt/omd/sites/b01/tmp  tmpfs   user,uid=b01,gid=b01 0 0
    mountpoint = "/opt" + site.tmp_dir
    sys.stdout.write("Adding %s to %s.\n" % (mountpoint, fstab_path()))

    # No size option: using up to 50% of the RAM
    sizespec = ''
    if tmpfs_size is not None and re.match('^[0-9]+(G|M|%)$', tmpfs_size):
        sizespec = ',size=%s' % tmpfs_size

    # Ensure the fstab has a newline char at it's end before appending
    previous_fstab = file(fstab_path()).read()
    complete_last_line = previous_fstab and not previous_fstab.endswith("\n")

    with file(fstab_path(), "a+") as fstab:
        if complete_last_line:
            fstab.write("\n")

        fstab.write("tmpfs  %s tmpfs noauto,user,mode=755,uid=%s,gid=%s%s 0 0\n" % \
        (mountpoint, site.name, site.name, sizespec))


def remove_from_fstab(site):
    if not os.path.exists("/etc/fstab"):
        return  # Don't do anything in case there is no fstab

    mountpoint = site.tmp_dir
    sys.stdout.write("Removing %s from /etc/fstab..." % mountpoint)
    newtab = file("/etc/fstab.new", "w")
    for line in file("/etc/fstab"):
        if "uid=%s," % site.name in line and mountpoint in line:
            continue
        newtab.write(line)
    os.rename("/etc/fstab.new", "/etc/fstab")
    ok()


#.
#   .--init.d--------------------------------------------------------------.
#   |                        _       _ _        _                          |
#   |                       (_)_ __ (_) |_   __| |                         |
#   |                       | | '_ \| | __| / _` |                         |
#   |                       | | | | | | |_ | (_| |                         |
#   |                       |_|_| |_|_|\__(_)__,_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Handling of site-internal init scripts                              |
#   '----------------------------------------------------------------------'


def init_scripts(sitename):
    rc_dir = "/omd/sites/%s/etc/rc.d" % sitename
    try:
        scripts = os.listdir(rc_dir)
        scripts.sort()
        return rc_dir, scripts
    except:
        return rc_dir, []


def call_init_script(scriptpath, command):
    if not os.path.exists(scriptpath):
        sys.stderr.write('ERROR: This daemon does not exist.\n')
        return False

    try:
        return subprocess.call([scriptpath, command]) in [0, 5]
    except OSError as e:
        sys.stderr.write("ERROR: Failed to run '%s': %s\n" % (scriptpath, e))
        if e.errno == errno.EACCES:
            return False


def call_init_scripts(site, command, daemon=None, exclude_daemons=None):
    # Restart: Do not restart each service after another,
    # but first do stop all, then start all again! This
    # preserves the order.
    if command == "restart":
        call_init_scripts(site, "stop", daemon)
        call_init_scripts(site, "start", daemon)
        return

    # OMD guarantees OMD_ROOT to be the current directory
    with chdir(site.dir):
        if daemon:
            success = call_init_script("%s/etc/init.d/%s" % (site.dir, daemon), command)

        else:
            # Call stop scripts in reverse order. If daemon is set,
            # then only that start script will be affected
            rc_dir, scripts = init_scripts(site.name)
            if command == "stop":
                scripts.reverse()
            success = True

            for script in scripts:
                if exclude_daemons and script in exclude_daemons:
                    continue

                if not call_init_script("%s/%s" % (rc_dir, script), command):
                    success = False

    if success:
        return 0
    return 2


def check_status(site, display=True, daemon=None, bare=False):
    num_running = 0
    num_unused = 0
    num_stopped = 0
    rc_dir, scripts = init_scripts(site.name)
    components = [s.split('-', 1)[-1] for s in scripts]
    if daemon and daemon not in components:
        if not bare:
            sys.stderr.write('ERROR: This daemon does not exist.\n')
        return 3
    for script in scripts:
        komponent = script.split("/")[-1].split('-', 1)[-1]
        if daemon and komponent != daemon:
            continue

        state = os.system("%s/%s status >/dev/null 2>&1" % (rc_dir, script)) >> 8  # nosec

        if display and (state != 5 or opt_verbose):
            if bare:
                sys.stdout.write(komponent + " ")
            else:
                sys.stdout.write("%-16s" % (komponent + ":"))
                sys.stdout.write(tty_bold)

        if bare:
            if state != 5 or opt_verbose:
                sys.stdout.write("%d\n" % state)

        if state == 0:
            if display and not bare:
                sys.stdout.write(tty_green + "running\n")
            num_running += 1
        elif state == 5:
            if display and opt_verbose and not bare:
                sys.stdout.write(tty_blue + "unused\n")
            num_unused += 1
        else:
            if display and not bare:
                sys.stdout.write(tty_red + "stopped\n")
            num_stopped += 1
        if display and not bare:
            sys.stdout.write(tty_normal)

    if num_stopped > 0 and num_running == 0:
        exit_code = 1
        ovstate = tty_red + "stopped"
    elif num_running > 0 and num_stopped == 0:
        exit_code = 0
        ovstate = tty_green + "running"
    elif num_running == 0 and num_stopped == 0:
        exit_code = 0
        ovstate = tty_blue + "unused"
    else:
        exit_code = 2
        ovstate = tty_yellow + "partially running"
    if display:
        if bare:
            sys.stdout.write("OVERALL %d\n" % exit_code)
        else:
            sys.stdout.write("-----------------------\n")
            sys.stdout.write("Overall state:  %s\n" % (tty_bold + ovstate + tty_normal))
    return exit_code


#.
#   .--Config & Hooks------------------------------------------------------.
#   |  ____             __ _          ___     _   _             _          |
#   | / ___|___  _ __  / _(_) __ _   ( _ )   | | | | ___   ___ | | _____   |
#   || |   / _ \| '_ \| |_| |/ _` |  / _ \/\ | |_| |/ _ \ / _ \| |/ / __|  |
#   || |__| (_) | | | |  _| | (_| | | (_>  < |  _  | (_) | (_) |   <\__ \  |
#   | \____\___/|_| |_|_| |_|\__, |  \___/\/ |_| |_|\___/ \___/|_|\_\___/  |
#   |                        |___/                                         |
#   +----------------------------------------------------------------------+
#   |  Site configuration and config hooks                                 |
#   '----------------------------------------------------------------------'

# Hooks are scripts in lib/omd/hooks that are being called with one
# of the following arguments:
#
# default - return the default value of the hook. Mandatory
# set     - implements a new setting for the hook
# choices - available choices for enumeration hooks
# depends - exists with 1, if this hook misses its dependent hook settings


# Put all site configuration (explicit and defaults) into environment
# variables beginning with CONFIG_
def create_config_environment(site):
    for varname, value in site.conf.items():
        putenv("CONFIG_" + varname, value)


# TODO: RENAME
def save_site_conf(site):
    confdir = site.dir + "/etc/omd"

    if not os.path.exists(confdir):
        os.mkdir(confdir)

    f = file(site.dir + "/etc/omd/site.conf", "w")

    for hook_name, value in sorted(site.conf.items(), key=lambda x: x[0]):
        f.write("CONFIG_%s='%s'\n" % (hook_name, value))


# Get information about all hooks. Just needed for
# the "omd config" command.
def load_config_hooks(site):
    config_hooks = {}

    hook_files = []
    if site.hook_dir:
        hook_files = os.listdir(site.hook_dir)
    for hook_name in hook_files:
        try:
            if hook_name[0] != '.':
                hook = config_load_hook(site, hook_name)
                # only load configuration hooks
                if hook.get("choices", None) is not None:
                    config_hooks[hook_name] = hook
        except:
            pass
    config_hooks = load_hook_dependencies(site, config_hooks)
    return config_hooks


def config_load_hook(site, hook_name):
    hook = {
        "name": hook_name,
        "deprecated": False,
    }

    if not site.hook_dir:
        # IMHO this should be unreachable...
        bail_out("Site has no version and therefore no hooks")

    description = ""
    description_active = False
    for line in file(site.hook_dir + hook_name):
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
        return call_hook(site, hook_name, [info])[1]

    # The choices can either be a list of possible keys. Then
    # the hook outputs one live for each choice where the key and a
    # description are separated by a colon. Or it outputs one line
    # where that line is an extended regular expression matching the
    # possible values.
    choicestxt = get_hook_info("choices").split("\n")
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
        except:
            bail_out("Invalid output of hook: %s" % choicestxt)

    hook["choices"] = choices
    return hook


def load_hook_dependencies(site, config_hooks):
    for hook_name in sort_hooks(config_hooks.keys()):
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
    return sorted(hook_names, key=lambda n: (n == "CORE", n))


def hook_exists(site, hook_name):
    if not site.hook_dir:
        return False
    hook_file = site.hook_dir + hook_name
    return os.path.exists(hook_file)


def call_hook(site, hook_name, args):
    if not site.hook_dir:
        # IMHO this should be unreachable...
        bail_out("Site has no version and therefore no hooks")

    hook_file = site.hook_dir + hook_name
    argsstring = " ".join(["'%s'" % arg for arg in args])
    command = hook_file + " " + argsstring
    if opt_verbose:
        sys.stdout.write("Calling hook: %s\n" % command)
    putenv("OMD_ROOT", site.dir)
    putenv("OMD_SITE", site.name)
    pipe = os.popen(command)  # nosec
    content = pipe.read().strip()
    exitcode = pipe.close()
    if exitcode and args[0] != "depends":
        sys.stderr.write("Error running %s: %s\n" % (command, content))
    return exitcode, content


def initialize_site_ca(site):
    """Initialize the site local CA and create the default site certificate
    This will be used e.g. for serving SSL secured livestatus"""
    ca = omdlib.certs.CertificateAuthority(
        ca_path=Path(site.dir) / "etc" / "ssl",
        ca_name="Site '%s' local CA" % site.name,
    )
    ca.initialize()
    if not ca.site_certificate_path(site.name).exists():
        ca.create_site_certificate(site.name)


def config_change(site, config_hooks):
    # Check whether or not site needs to be stopped. Stop and remember to start again later
    site_was_stopped = False
    if not site.is_stopped():
        site_was_stopped = True
        stop_site(site)

    try:
        settings = read_config_change_commands()

        if not settings:
            bail_out("You need to provide config change commands via stdin: KEY=value\n")

        validate_config_change_commands(config_hooks, settings)

        for key, value in settings:
            config_set_value(site, config_hooks, key, value, save=False)

        save_site_conf(site)
    finally:
        if site_was_stopped:
            start_site(site)


def read_config_change_commands():
    settings = []
    for l in sys.stdin:
        line = l.strip()
        if not line:
            continue

        try:
            key, value = line.split("=", 1)
            settings.append((key, value))
        except ValueError:
            bail_out("Invalid config change command: %r" % line)
    return settings


def validate_config_change_commands(config_hooks, settings):
    # Validate the provided commands
    for key, value in settings:
        hook = config_hooks.get(key)
        if not hook:
            bail_out("Invalid config option: %r" % key)

        # Check if value is valid. Choices are either a list of allowed
        # keys or a regular expression
        if isinstance(hook["choices"], list):
            choices = [var for (var, _descr) in hook["choices"]]
            if value not in choices:
                bail_out("Invalid value %r for %r. Allowed are: %s\n" % \
                        (value, key, ", ".join(choices)))
        else:
            if not hook["choices"].match(value):
                bail_out("Invalid value %r for %r. Does not match allowed pattern.\n" %
                         (value, key))


def config_set(site, config_hooks, args):
    if len(args) != 2:
        sys.stderr.write("Please specify variable name and value\n")
        config_usage()
        return

    if not site.is_stopped():
        sys.stderr.write("Cannot change config variables while site is running.\n")
        return

    hook_name = args[0]
    value = args[1]
    hook = config_hooks.get(hook_name)
    if not hook:
        sys.stderr.write("No such variable '%s'\n" % hook_name)
        return

    # Check if value is valid. Choices are either a list of allowed
    # keys or a regular expression
    if isinstance(hook["choices"], list):
        choices = [var for (var, _descr) in hook["choices"]]
        if value not in choices:
            sys.stderr.write("Invalid value for '%s'. Allowed are: %s\n" % \
                    (value, ", ".join(choices)))
            return
    else:
        if not hook["choices"].match(value):
            sys.stderr.write("Invalid value for '%s'. Does not match allowed pattern.\n" % value)
            return

    config_set_value(site, config_hooks, hook_name, value)


def config_set_all(site, ignored_hooks=None):
    # type: (SiteContext, list) -> None
    if ignored_hooks is None:
        ignored_hooks = []

    for hook_name in sort_hooks(site.conf.keys()):
        value = site.conf[hook_name]
        # Hooks might vanish after and up- or downdate
        if hook_exists(site, hook_name) and hook_name not in ignored_hooks:
            exitcode, output = call_hook(site, hook_name, ["set", value])
            if not exitcode:
                if output and output != value:
                    site.conf[hook_name] = output
                    putenv("CONFIG_" + hook_name, output)


def config_set_value(site, config_hooks, hook_name, value, save=True):
    # TODO: Warum wird hier nicht call_hook() aufgerufen!!

    # Call hook with 'set'. If it outputs something, that will
    # be our new value (i.e. hook disagrees with the new setting!)
    commandline = "%s/lib/omd/hooks/%s set '%s'" % (site.dir, hook_name, value)
    if is_root():
        sys.stderr.write("I am root. This should never happen!\n")
        sys.exit(1)

        # commandline = 'su -p -l %s -c "%s"' % (site.name, commandline)
    answer = os.popen(commandline).read()  # nosec
    if len(answer) > 0:
        value = answer.strip()

    site.conf[hook_name] = value
    putenv("CONFIG_" + hook_name, value)

    if save:
        save_site_conf(site)


def config_usage():
    sys.stdout.write("""Usage of config command:

omd config               - interactive configuration menu
omd config show          - show current settings of all configuration variables
omd config show VAR      - show current setting of variable VAR
omd config set VAR VALUE - set VAR to VALUE
omd config change        - change multiple at once. Provide newline separated
                           KEY=value pairs via stdin. The site is restarted
                           automatically once in case it's currently runnig.
""")


def config_show(site, config_hooks, args):
    if len(args) == 0:
        hook_names = config_hooks.keys()
        hook_names.sort()
        for hook_name in hook_names:
            hook = config_hooks[hook_name]
            if hook["active"] and not hook["deprecated"]:
                sys.stdout.write("%s: %s\n" % (hook_name, site.conf[hook_name]))
    else:
        output = []
        for hook_name in args:
            hook = config_hooks.get(hook_name)
            if not hook:
                sys.stderr.write("No such variable %s\n" % hook_name)
            else:
                output.append(site.conf[hook_name])

        sys.stdout.write(" ".join(output))
        sys.stdout.write("\n")


def config_configure(site, config_hooks):
    hook_names = config_hooks.keys()
    hook_names.sort()
    current_hook_name = ""
    menu_open = False
    current_menu = "Basic"

    # force certain order in main menu
    menu_choices = ["Basic", "Web GUI", "Addons", "Distributed Monitoring"]

    while True:
        # Rebuild hook information (values possible changed)
        menu = {}
        for hook_name in hook_names:
            hook = config_hooks[hook_name]
            if hook["active"] and not hook["deprecated"]:
                mp = hook.get("menu", "Other")
                entries = menu.get(mp, [])
                entries.append((hook_name, site.conf[hook_name]))
                menu[mp] = entries
                if mp not in menu_choices:
                    menu_choices.append(mp)

        # Handle main menu
        if not menu_open:
            change, current_menu = \
                dialog_menu("Configuration of site %s" % site.name,
                        "Interactive setting of site configuration variables. You "
                        "can change values only while the site is stopped.",
                        [ (e, "") for e in menu_choices ],
                        current_menu,
                        "Enter",
                        "Exit")
            if not change:
                return
            current_hook_name = None
            menu_open = True

        else:
            change, current_hook_name = \
                dialog_menu(
                    current_menu,
                    "",
                    menu[current_menu],
                    current_hook_name,
                    "Change",
                    "Main menu")
            if change:
                try:
                    config_configure_hook(site, config_hooks, current_hook_name)
                except Exception as e:
                    bail_out("Error in hook %s: %s" % (current_hook_name, e))
            else:
                menu_open = False


def config_configure_hook(site, config_hooks, hook_name):
    if not site.is_stopped():
        if not dialog_yesno("You cannot change configuration value while the "
                            "site is running. Do you want me to stop the site now?"):
            return
        stop_site(site)
        dialog_message("The site has been stopped.")

    hook = config_hooks[hook_name]
    title = hook["alias"]
    descr = hook["description"].replace("\n\n", "\001").replace("\n", " ").replace("\001", "\n\n")
    value = site.conf[hook_name]
    choices = hook["choices"]
    if isinstance(choices, list):
        dialog_function = dialog_menu
    else:
        dialog_function = dialog_regex
    change, new_value = \
        dialog_function(title, descr, choices, value, "Change", "Cancel")
    if change:
        config_set_value(site, config_hooks, hook["name"], new_value)
        site.conf[hook_name] = new_value
        save_site_conf(site)
        config_hooks = load_hook_dependencies(site, config_hooks)


def init_action(site, command, args, options):
    if site.is_disabled():
        bail_out("This site is disabled.")

    if command in ["start", "restart"]:
        prepare_and_populate_tmpfs(site)

    if len(args) > 0:
        daemon = args[0]  # restrict to this daemon
    else:
        daemon = None

    # OMD guarantees that we are in OMD_ROOT
    with chdir(site.dir):
        if command == "status":
            return check_status(site, display=True, daemon=daemon, bare="bare" in options)
        return call_init_scripts(site, command, daemon)


#.
#   .--Helpers-------------------------------------------------------------.
#   |                  _   _      _                                        |
#   |                 | | | | ___| |_ __   ___ _ __ ___                    |
#   |                 | |_| |/ _ \ | '_ \ / _ \ '__/ __|                   |
#   |                 |  _  |  __/ | |_) |  __/ |  \__ \                   |
#   |                 |_| |_|\___|_| .__/ \___|_|  |___/                   |
#   |                              |_|                                     |
#   +----------------------------------------------------------------------+
#   |  Various helper functions                                            |
#   '----------------------------------------------------------------------'


def fstab_verify(site):
    """Ensure that there is an fstab entry for the tmpfs of the site.
    In case there is no fstab (seen in some containers) assume everything
    is OK without fstab entry."""

    if not os.path.exists("/etc/fstab"):
        return True

    mountpoint = site.tmp_dir
    for line in file("/etc/fstab"):
        if "uid=%s," % site.name in line and mountpoint in line:
            return True
    bail_out(tty_error + ": fstab entry for %s does not exist" % mountpoint)


# No using os.putenv, os.getenv os.unsetenv directly because
# they seem not to work correctly in debian 503.
#
# Unsetting all vars with os.unsetenv and after that using os.getenv to read
# some vars did not bring the expected result that the environment was empty.
# The vars were still set.
#
# Same for os.putenv. Executing os.getenv right after os.putenv did not bring
# the expected result.
#
# Directly modifying os.environ seems to work.
def putenv(key, value):
    os.environ[key] = value


def getenv(key, default=None):
    if not key in os.environ:
        return default
    return os.environ[key]


def clear_environment():
    # first remove *all* current environment variables
    keep = ["TERM"]
    for key in os.environ.keys():
        if key not in keep:
            del os.environ[key]


def set_environment(site):
    putenv("OMD_SITE", site.name)
    putenv("OMD_ROOT", site.dir)
    putenv(
        "PATH",
        "%s/local/bin:%s/bin:/usr/local/bin:/bin:/usr/bin:/sbin:/usr/sbin" % (site.dir, site.dir))
    putenv("USER", site.name)

    putenv("LD_LIBRARY_PATH", "%s/local/lib:%s/lib" % (site.dir, site.dir))
    putenv("HOME", site.dir)

    # allow user to define further environment variable in ~/etc/environment
    envfile = site.dir + "/etc/environment"
    if os.path.exists(envfile):
        lineno = 0
        for line in file(envfile):
            lineno += 1
            line = line.strip()
            if line == "" or line[0] == "#":
                continue  # allow empty lines and comments
            parts = line.split("=")
            if len(parts) != 2:
                bail_out("%s: syntax error in line %d" % (envfile, lineno))
            varname = parts[0]
            value = parts[1]
            if value.startswith('"'):
                value = value.strip('"')

            # Add the present environment when someone wants to append some
            if value.startswith("$%s:" % varname):
                before = getenv(varname, None)
                if before:
                    value = before + ":" + value.replace("$%s:" % varname, '')

            if value.startswith("'"):
                value = value.strip("'")
            putenv(varname, value)

    create_config_environment(site)


def hostname():
    try:
        return os.popen("hostname").read().strip()
    except:
        return "localhost"


def create_apache_hook(site):
    file("/omd/apache/%s.conf" % site.name, "w")\
        .write("Include %s/etc/apache/mode.conf\n" % site.dir)


def delete_apache_hook(sitename):
    hook_path = "/omd/apache/%s.conf" % sitename
    if not os.path.exists(hook_path):
        return
    try:
        os.remove(hook_path)
    except Exception as e:
        sys.stderr.write("Cannot remove apache hook %s: %s\n" % (hook_path, e))


def init_cmd(name, action):
    return g_info.INIT_CMD % {
        'name': name,
        'action': action,
    }


def reload_apache():
    sys.stdout.write("Reloading Apache...")
    sys.stdout.flush()
    show_success(subprocess.call([g_info.APACHE_CTL, "graceful"]) >> 8)


def restart_apache():
    if os.system(  # nosec
            init_cmd(g_info.APACHE_INIT_NAME, 'status') + ' >/dev/null 2>&1') >> 8 == 0:
        sys.stdout.write("Restarting Apache...")
        sys.stdout.flush()
        show_success(
            os.system(init_cmd(g_info.APACHE_INIT_NAME, 'restart') + ' >/dev/null') >> 8)  # nosec


def replace_tags(content, replacements):
    for var, value in replacements.items():
        content = content.replace(var, value)
    return content


def get_editor():
    editor = getenv("VISUAL", getenv("EDITOR", "/usr/bin/vi"))
    if not os.path.exists(editor):
        editor = 'vi'
    return editor


# return "| $PAGER", if a pager is available
def pipe_pager():
    pager = getenv("PAGER")
    if not pager and os.path.exists("/usr/bin/less"):
        pager = "less -F -X"
    if pager:
        return "| %s" % pager
    return ""


def call_scripts(site, phase):
    path = site.dir + "/lib/omd/scripts/" + phase
    if os.path.exists(path):
        putenv("OMD_ROOT", site.dir)
        putenv("OMD_SITE", site.name)
        for f in os.listdir(path):
            if f[0] == '.':
                continue
            sys.stdout.write('Executing %s script "%s"...' % (phase, f))
            p = subprocess.Popen(  # nosec
                '%s/%s' % (path, f),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            stdout = p.stdout.read()
            exitcode = p.wait()
            if exitcode == 0:
                sys.stdout.write(tty_ok + '\n')
            else:
                sys.stdout.write(tty_error + ' (exit code: %d)\n' % exitcode)
            if stdout:
                sys.stdout.write('Output: %s\n' % stdout)


def check_site_user(site, site_must_exist):
    if not site.is_site_context():
        return

    if not site_must_exist:
        return

    if not site.exists():
        bail_out("omd: The site '%s' does not exist. You need to execute "
                 "omd as root or site user." % site.name)


#.
#   .--Commands------------------------------------------------------------.
#   |         ____                                          _              |
#   |        / ___|___  _ __ ___  _ __ ___   __ _ _ __   __| |___          |
#   |       | |   / _ \| '_ ` _ \| '_ ` _ \ / _` | '_ \ / _` / __|         |
#   |       | |__| (_) | | | | | | | | | | | (_| | | | | (_| \__ \         |
#   |        \____\___/|_| |_| |_|_| |_| |_|\__,_|_| |_|\__,_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Implementation of actual omd commands                               |
#   '----------------------------------------------------------------------'


def main_help(site, args=None, options=None):
    if args is None:
        args = []
    if options is None:
        options = {}

    if is_root():
        sys.stdout.write("Usage (called as root):\n\n")
    else:
        sys.stdout.write("Usage (called as site user):\n\n")

    for command, only_root, _no_suid, needs_site, _site_must_exist, _confirm, synopsis, _command_function, _command_options, descr, _confirm_text in commands:
        if only_root and not is_root():
            continue

        if is_root():
            if needs_site == 2:
                synopsis = "[SITE] " + synopsis
            elif needs_site == 1:
                synopsis = "SITE " + synopsis

        synopsis_width = '23' if is_root() else '16'
        sys.stdout.write((" omd %-10s %-" + synopsis_width + "s %s\n") % (command, synopsis, descr))
    sys.stdout.write(
        "\nGeneral Options:\n"
        " -V <version>                    set specific version, useful in combination with update/create\n"
        " omd COMMAND -h, --help          show available options of COMMAND\n")


def main_setversion(site, args, options=None):
    if options is None:
        options = {}

    if len(args) == 0:
        versions = [(v, "Version %s" % v) for v in omd_versions() if not v == default_version()]

        if use_update_alternatives():
            versions = [('auto', 'Auto (Update-Alternatives)')] + versions

        success, version = dialog_menu("Choose new default",
                                       "Please choose the version to make the new default",
                                       versions, None, "Make default", "Cancel")
        if not success:
            bail_out("Aborted.")
    else:
        version = args[0]

    if version != 'auto' and not version_exists(version):
        bail_out("The given version does not exist.")
    if version == default_version():
        bail_out("The given version is already default.")

    # Special handling for debian based distros which use update-alternatives
    # to control the path to the omd binary, manpage and so on
    if use_update_alternatives():
        if version == 'auto':
            os.system("update-alternatives --auto omd")  # nosec
        else:
            os.system("update-alternatives --set omd /omd/versions/%s" % version)  # nosec
    else:
        if os.path.islink("/omd/versions/default"):
            os.remove("/omd/versions/default")
        os.symlink("/omd/versions/%s" % version, "/omd/versions/default")


def use_update_alternatives():
    return os.path.exists("/var/lib/dpkg/alternatives/omd")


def main_version(site, args, options=None):
    if options is None:
        options = {}

    if len(args) > 0:
        site = SiteContext(args[0])
        if not site.exists():
            bail_out("No such site: %s" % site.name)
        version = site.version
    else:
        version = omdlib.__version__

    if "bare" in options:
        sys.stdout.write(version + "\n")
    else:
        sys.stdout.write("OMD - Open Monitoring Distribution Version %s\n" % version)


def main_versions(site, args, options=None):
    if options is None:
        options = {}

    for v in omd_versions():
        if v == default_version() and "bare" not in options:
            sys.stdout.write("%s (default)\n" % v)
        else:
            sys.stdout.write("%s\n" % v)


def default_version():
    return os.path.basename(os.path.realpath("/omd/versions/default"))


def omd_versions():
    try:
        return sorted([v for v in os.listdir("/omd/versions") if v != "default"])
    except OSError as e:
        if e.errno == errno.ENOENT:
            return []
        else:
            raise


def version_exists(v):
    return v in omd_versions()


def main_sites(site, args, options=None):
    if options is None:
        options = {}

    if sys.stdout.isatty() and "bare" not in options:
        sys.stdout.write("SITE             VERSION          COMMENTS\n")
    for sitename in all_sites():
        site = SiteContext(sitename)
        tags = []
        if "bare" in options:
            sys.stdout.write("%s\n" % site.name)
        else:
            disabled = site.is_disabled()
            v = site.version
            if v is None:
                v = "(none)"
                tags.append("empty site dir")
            elif v == default_version():
                tags.append("default version")
            if disabled:
                tags.append(tty_bold + tty_red + "disabled" + tty_normal)
            sys.stdout.write("%-16s %-16s %s " % (site.name, v, ", ".join(tags)))
            sys.stdout.write("\n")


# Bail out if name for new site is not valid (needed by create/mv/cp)
def sitename_must_be_valid(site, reuse=False):
    # Make sanity checks before starting any action
    if not reuse and site.exists():
        bail_out("Site '%s' already existing." % site.name)
    if not reuse and group_exists(site.name):
        bail_out("Group '%s' already existing." % site.name)
    if not reuse and user_exists(site.name):
        bail_out("User '%s' already existing." % site.name)
    if not re.match("^[a-zA-Z_][a-zA-Z_0-9]{0,15}$", site.name):
        bail_out(
            "Invalid site name. Must begin with a character, may contain characters, digits and _ and have length 1 up to 16"
        )


def main_create(site, args, options=None):
    if options is None:
        options = {}

    reuse = False
    if "reuse" in options:
        reuse = True
        if not user_verify(site):
            bail_out("Error verifying site user.")

    sitename_must_be_valid(site, reuse)

    # Create operating system user for site
    uid = options.get("uid")
    gid = options.get("gid")
    if not reuse:
        useradd(site, uid, gid)

    if reuse:
        fstab_verify(site)
    else:
        create_site_dir(site)
        add_to_fstab(site, tmpfs_size=options.get('tmpfs-size'))

    config_settings = {}
    if "no-autostart" in options:
        config_settings["AUTOSTART"] = "off"
        sys.stdout.write("Going to set AUTOSTART to off.\n")

    if "no-tmpfs" in options:
        config_settings["TMPFS"] = "off"
        sys.stdout.write("Going to set TMPFS to off.\n")

    if "no-init" not in options:
        admin_password = init_site(site, config_settings, options)
        welcome_message(site, admin_password)

    else:
        sys.stdout.write("Create new site %s in disabled state and with empty %s.\n" %
                         (site.name, site.dir))
        sys.stdout.write("You can now mount a filesystem to %s.\n" % (site.dir))
        sys.stdout.write("Afterwards you can initialize the site with 'omd init'.\n")


def welcome_message(site, admin_password):
    sys.stdout.write("Created new site %s with version %s.\n\n" % (site.name, omdlib.__version__))
    sys.stdout.write("  The site can be started with %somd start %s%s.\n" %
                     (tty_bold, site.name, tty_normal))
    sys.stdout.write("  The default web UI is available at %shttp://%s/%s/%s\n" %
                     (tty_bold, hostname(), site.name, tty_normal))
    sys.stdout.write("\n")
    sys.stdout.write(
        "  The admin user for the web applications is %scmkadmin%s with password: %s%s%s\n" %
        (tty_bold, tty_normal, tty_bold, admin_password, tty_normal))
    sys.stdout.write(
        "  (It can be changed with 'htpasswd -m ~/etc/htpasswd cmkadmin' as site user.\n)")
    sys.stdout.write("\n")
    sys.stdout.write("  Please do a %ssu - %s%s for administration of this site.\n" %
                     (tty_bold, site.name, tty_normal))
    sys.stdout.write("\n")


def main_init(site, args, options):
    if not site.is_disabled():
        bail_out("Cannot initialize site that is not disabled.\n"
                 "Please call 'omd disable %s' first." % site.name)

    if not site.is_empty():
        if not opt_force:
            bail_out("The site's home directory is not empty. Please add use\n"
                     "'omd --force init %s' if you want to erase all data." % site.name)

        # We must not delete the directory itself, just its contents.
        # The directory might be a separate filesystem. This is not quite
        # unlikely, since people using 'omd init' are doing this most times
        # because they are working with clusters and separate filesystems for
        # each site.
        sys.stdout.write("Wiping the contents of %s..." % site.dir)
        for entry in os.listdir(site.dir):
            if entry not in ['.', '..']:
                path = site.dir + "/" + entry
                if opt_verbose:
                    sys.stdout.write("\n   deleting %s..." % path)
                if os.path.islink(path) or not os.path.isdir(path):
                    os.remove(path)
                else:
                    shutil.rmtree(site.dir + "/" + entry)
        ok()

    # Do the things that have been ommited on omd create --disabled
    admin_password = init_site(site, config_settings=None, options=options)
    welcome_message(site, admin_password)


def init_site(site, config_settings=None, options=False):
    apache_reload = "apache-reload" in options

    # Create symbolic link to version
    create_version_symlink(site, omdlib.__version__)

    # Build up directory structure with symbolic links relative to
    # the version link we just create
    for d in ['bin', 'include', 'lib', 'share']:
        os.symlink("version/" + d, site.dir + "/" + d)

    # Create skeleton files of non-tmp directories
    create_skeleton_files(site, '.')

    # Save the skeleton files used to initialize this site
    save_version_meta_data(site, omdlib.__version__)

    # Set the initial password of the default admin user
    admin_password = calculate_admin_password(options)
    set_admin_password(site, admin_password)

    # Special hack for 1.5: Requirement is to activate the new facelift theme
    # for new sites. Normally we use the "WATO sample configuration" for setting
    # specific options for sites created with the new version. But this sample
    # configuration is not set too late to affect the first login.
    # It is set when a user accesses WATO for the first time, which happens
    # after the first login.
    # It is a open task to move this initial configuration step to an earlier
    # stage for the 1.6. But this is nothing we can change now for the 1.5
    # because it would involve some bigger changes.
    # We decided to reach this goal using hard coded specific hack here for the
    # 1.5 and solve the issue completely (also for the other sample config) in
    # the future.
    with open(os.path.join(site.dir, "etc/check_mk/multisite.d/wato/global.mk"), "w") as f:
        f.write("# Created by 'omd create'\n" "ui_theme = 'facelift'\n")

    # Change ownership of all files and dirs to site user
    chown_tree(site.dir, site.name)

    site.load_config()  # load default values from all hooks
    if config_settings:  # add specific settings
        for hook_name, value in config_settings.items():
            site.conf[hook_name] = value
    create_config_environment(site)

    # Change the few files that config save as created as root
    chown_tree(site.dir, site.name)

    finalize_site(site, "create", apache_reload)

    return admin_password


# Is being called at the end of create, cp and mv.
# What is "create", "mv" or "cp". It is used for
# running the appropriate hooks.
def finalize_site(site, what, apache_reload):

    # Now we need to do a few things as site user. Note:
    # - We cannot use setuid() here, since we need to get back to root.
    # - We cannot use seteuid() here, since the id command call will then still
    #   report root and confuse some tools
    # - We cannot sue setresuid() here, since that is not supported an Python 2.4
    # So we need to fork() and use a real setuid() here and leave the main process
    # at being root.
    pid = os.fork()
    if pid == 0:
        try:
            # From now on we run as normal site user!
            switch_to_site_user(site)

            # avoid executing hook 'TMPFS' and cleaning an initialized tmp directory
            # see CMK-3067
            finalize_site_as_user(site, what, ignored_hooks=["TMPFS"])
            sys.exit(0)
        except Exception as e:
            bail_out(e)
    else:
        _wpid, status = os.waitpid(pid, 0)
        if status:
            bail_out("Error in non-priviledged sub-process.")

    # Finally reload global apache - with root permissions - and
    # create include-hook for Apache and reload apache
    create_apache_hook(site)
    if apache_reload:
        reload_apache()
    else:
        restart_apache()


def finalize_site_as_user(site, what, ignored_hooks=None):
    # Mount and create contents of tmpfs. This must be done as normal
    # user. We also could do this at 'omd start', but this might confuse
    # users. They could create files below tmp which would be shadowed
    # by the mount.
    prepare_and_populate_tmpfs(site)

    # Run all hooks in order to setup things according to the
    # configuration settings
    config_set_all(site, ignored_hooks)
    initialize_site_ca(site)
    save_site_conf(site)

    call_scripts(site, 'post-' + what)


def main_rm(site, args, options=None):
    if options is None:
        options = {}

    # omd rm is called as root but the init scripts need to be called as
    # site user but later steps need root privilegies. So a simple user
    # switch to the site user would not work. Better create a subprocess
    # for this dedicated action and switch to the user in that subprocess
    os.system('omd stop %s' % site.name)  # nosec

    reuse = "reuse" in options
    kill = "kill" in options

    if user_logged_in(site.name):
        if not kill:
            bail_out("User '%s' still logged in or running processes." % site.name)
        else:
            kill_site_user_processes(site, exclude_current_and_parents=True)

    if tmpfs_mounted(site.name):
        unmount_tmpfs(site, kill=kill)

    # Remove include-hook for Apache and tell apache
    # Needs to be cleaned up before removing the site directory. Otherwise a
    # parallel restart / reload of the apache may fail, because the apache hook
    # refers to a not existing site apache config.
    delete_apache_hook(site.name)

    if not reuse:
        remove_from_fstab(site)
        sys.stdout.write("Deleting user and group %s..." % site.name)
        os.chdir("/")  # Site directory not longer existant after userdel
        userdel(site.name)
        ok()

    if os.path.exists(site.dir):  # should be done by userdel
        sys.stdout.write("Deleting all data (%s)..." % site.dir)
        shutil.rmtree(site.dir)
        ok()

    if reuse:
        create_site_dir(site)
        os.mkdir(site.tmp_dir)
        os.chown(site.tmp_dir, user_id(site.name), group_id(site.name))

    if "apache-reload" in options:
        reload_apache()
    else:
        restart_apache()


def create_site_dir(site):
    try:
        os.makedirs(site.dir)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    os.chown(site.dir, user_id(site.name), group_id(site.name))


def main_disable(site, args, options):
    if site.is_disabled():
        sys.stderr.write("This site is already disabled.\n")
        sys.exit(0)

    stop_if_not_stopped(site)
    unmount_tmpfs(site, kill="kill" in options)
    sys.stdout.write("Disabling Apache configuration for this site...")
    delete_apache_hook(site.name)
    ok()
    restart_apache()


def main_enable(site, args, options):
    if not site.is_disabled():
        sys.stderr.write("This site is already enabled.\n")
        sys.exit(0)
    sys.stdout.write("Re-enabling Apache configuration for this site...")
    create_apache_hook(site)
    ok()
    restart_apache()


def set_conflict_option(options):
    global opt_conflict
    opt_conflict = options.get("conflict", "ask")

    if opt_conflict not in ["ask", "install", "keepold", "abort"]:
        bail_out("Argument to --conflict must be one of ask, install, keepold and abort.")


def main_mv_or_cp(old_site, what, args, options=None):
    if options is None:
        options = {}

    set_conflict_option(options)
    action = 'rename' if what == 'mv' else 'copy'

    if len(args) != 1:
        bail_out("omd: Usage: omd %s oldname newname" % what)
    new_site = SiteContext(args[0])

    reuse = False
    if "reuse" in options:
        reuse = True
        if not user_verify(new_site):
            bail_out("Error verifying site user.")
        fstab_verify(new_site)

    sitename_must_be_valid(new_site, reuse)

    if not old_site.is_stopped():
        bail_out("Cannot %s site '%s' while it is running." % (action, old_site.name))

    pids = find_processes_of_user(old_site.name)
    if pids:
        bail_out("Cannot %s site '%s' while there are processes owned by %s.\n"
                 "PIDs: %s" % (action, old_site.name, old_site.name, " ".join(pids)))

    if what == "mv":
        unmount_tmpfs(old_site, kill="kill" in options)
        if not reuse:
            remove_from_fstab(old_site)

    sys.stdout.write("%sing site %s to %s..." %
                     (what == "mv" and "Mov" or "Copy", old_site.name, new_site.name))
    sys.stdout.flush()

    # Create new user. Note: even on mv we need to create a new user.
    # Linux does not (officially) allow to rename a user.
    uid = options.get("uid")
    gid = options.get("gid")
    if not reuse:
        useradd(new_site, uid, gid)  # None for uid/gid means: let Linux decide

    if what == "mv" and not reuse:
        # Rename base directory and apache config
        os.rename(old_site.dir, new_site.dir)
        delete_apache_hook(old_site.name)
    else:
        # Make exact file-per-file copy with same user but already new name
        if not reuse:
            os.mkdir(new_site.dir)

        addopts = ""
        for p in omdlib.backup.get_exclude_patterns(options):
            addopts += " --exclude '/%s'" % p

        if opt_verbose:
            addopts += " -v"

        os.system("rsync -arx %s '%s/' '%s/'" % (addopts, old_site.dir, new_site.dir))  # nosec

        httpdlogdir = new_site.dir + "/var/log/apache"
        if not os.path.exists(httpdlogdir):
            os.mkdir(httpdlogdir)

        rrdcacheddir = new_site.dir + "/var/rrdcached"
        if not os.path.exists(rrdcacheddir):
            os.mkdir(rrdcacheddir)

    # give new user all files
    chown_tree(new_site.dir, new_site.name)

    # Change config files from old to new site (see rename_site())
    patch_skeleton_files(old_site, new_site)

    # In case of mv now delete old user
    if what == "mv" and not reuse:
        userdel(old_site.name)

    # clean up old site
    if what == "mv" and reuse:
        main_rm(old_site, [], {'reuse': None})

    sys.stdout.write("OK\n")

    # Now switch over to the new site as currently active site
    new_site.load_config()
    set_environment(new_site)

    # Entry for tmps in /etc/fstab
    if not reuse:
        add_to_fstab(new_site, tmpfs_size=options.get('tmpfs-size'))

    finalize_site(new_site, what, "apache-reload" in options)


def main_diff(site, args, options=None):
    if options is None:
        options = {}

    from_version = site.version
    from_skelroot = site.version_skel_dir

    # If arguments are added and those arguments are directories,
    # then we just output the general state of the file. If only
    # one file is specified, we directly show the unified diff.
    # This behaviour can also be forced by the OMD option -v.

    if len(args) == 0:
        args = ["."]
    elif len(args) == 1 and os.path.isfile(args[0]):
        global opt_verbose
        opt_verbose = True

    for arg in args:
        diff_list(options, site, from_skelroot, from_version, arg)


def diff_list(options, site, from_skelroot, from_version, orig_path):
    # Compare a list of files/directories with the original state
    # and output differences. If opt_verbose then we output the complete
    # diff, otherwise just the state. Only files present in skel/ are
    # handled at all.

    read_skel_permissions()

    old_perms = site.skel_permissions

    # Prepare paths:
    # orig_path: this was specified by the user
    # rel_path:  path relative to the site's dir
    # abs_path:  absolute path

    # Get absolute path to site dir. This can be (/opt/omd/sites/XXX)
    # due to the symbolic link /omd
    old_dir = os.getcwd()
    os.chdir(site.dir)
    abs_sitedir = os.getcwd()
    os.chdir(old_dir)

    # Create absolute paths first
    abs_path = orig_path
    if not abs_path.startswith("/"):
        if abs_path == ".":
            abs_path = ""
        elif abs_path.startswith("./"):
            abs_path = abs_path[2:]
        abs_path = os.getcwd() + "/" + abs_path
    abs_path = abs_path.rstrip("/")

    # Make sure that path does not lie outside the OMD site
    if abs_path.startswith(site.dir):
        rel_path = abs_path[len(site.dir) + 1:]
    elif abs_path.startswith(abs_sitedir):
        rel_path = abs_path[len(abs_sitedir) + 1:]
    else:
        bail_out("Sorry, 'omd diff' only works for files in the site's directory.")

    if not os.path.isdir(abs_path):
        print_diff(rel_path, options, site, from_skelroot, site.dir, from_version, old_perms)
    else:
        if not rel_path:
            rel_path = "."
        walk_skel(from_skelroot,
                  print_diff, (options, site, from_skelroot, site.dir, from_version, old_perms),
                  depth_first=False,
                  relbase=rel_path)


def print_diff(rel_path, options, site, source_path, target_path, source_version, source_perms):
    source_file = source_path + '/' + rel_path
    target_file = target_path + '/' + rel_path

    source_perm = get_skel_permissions(source_path, source_perms, rel_path)
    target_perm = get_file_permissions(target_file)

    source_type = filetype(source_file)
    target_type = filetype(target_file)

    changed_type, changed_content, changed = file_status(site, source_file, target_file)

    if not changed:
        return

    fn = tty_bold + tty_bgblue + tty_white + rel_path + tty_normal
    fn = tty_bold + rel_path + tty_normal

    def print_status(color, f, status, long_out):
        if "bare" in options:
            sys.stdout.write("%s %s\n" % (status, f))
        elif not opt_verbose:
            sys.stdout.write(color + " %s %s\n" % (long_out, f))
        else:
            arrow = tty_magenta + '->' + tty_normal
            if 'c' in status:
                source_content = instantiate_skel(site, source_file)
                if os.system("which colordiff > /dev/null 2>&1") == 0:  # nosec
                    diff = "colordiff"
                else:
                    diff = "diff"
                os.popen(  # nosec
                    "bash -c \"%s -u <(cat) '%s'\"" % (diff, target_file),
                    "w").write(source_content)
            elif status == 'p':
                sys.stdout.write("    %s %s %s\n" % (source_perm, arrow, target_perm))
            elif 't' in status:
                sys.stdout.write("    %s %s %s\n" % (source_type, arrow, target_type))

    if not target_type:
        print_status(StateMarkers.good, fn, 'd', 'Deleted')
        return

    elif changed_type and changed_content:
        print_status(StateMarkers.good, fn, 'tc', 'Changed type and content')

    elif changed_type and not changed_content:
        print_status(StateMarkers.good, fn, 't', 'Changed type')

    elif changed_content and not changed_type:
        print_status(StateMarkers.good, fn, 'c', 'Changed content')

    if source_perm != target_perm:
        print_status(StateMarkers.warn, fn, 'p', 'Changed permissions')


def main_update(site, args, options=None):
    if options is None:
        options = {}

    set_conflict_option(options)

    if not site.is_stopped():
        bail_out("Please completely stop '%s' before updating it." % site.name)

    # Unmount tmp. We need to recreate the files and directories
    # from the new version after updating.
    unmount_tmpfs(site)

    # Source version: the version of the site we deal with
    from_version = site.version

    # Target version: the version of the OMD binary
    to_version = omdlib.__version__

    # source and target are identical if 'omd update' is called
    # from within a site. In that case we make the user choose
    # the target version explicitely and the re-exec the bin/omd
    # of the target version he has choosen.
    if from_version == to_version:
        possible_versions = [v for v in omd_versions() if v != from_version]
        possible_versions.sort(reverse=True)
        if len(possible_versions) == 0:
            bail_out("There is no other OMD version to update to.")
        elif len(possible_versions) == 1:
            to_version = possible_versions[0]
        else:
            success, to_version = dialog_menu(
                "Choose target version", "Please choose the version this site should be updated to",
                [(v, "Version %s" % v) for v in possible_versions], possible_versions[0],
                "Update now", "Cancel")
            if not success:
                bail_out("Aborted.")
        exec_other_omd(site, to_version, "update")

    # This line is reached, if the version of the OMD binary (the target)
    # is different from the current version of the site.
    if not opt_force and not dialog_yesno(
            "You are going to update the site %s from version %s to version %s. "
            "This will include updating all of you configuration files and merging "
            "changes in the default files with changes made by you. In case of conflicts "
            "your help will be needed." %
        (site.name, from_version, to_version), "Update!", "Abort"):
        bail_out("Aborted.")

    # In case the user changes the installed Check_MK Edition during update let the
    # user confirm this step.
    from_edition, to_edition = _get_edition(from_version), _get_edition(to_version)
    if from_edition != to_edition and not opt_force and not dialog_yesno(
            "You are updating from %s Edition to %s Edition. Is this intended?" %
        (from_edition.title(), to_edition.title())):
        bail_out("Aborted.")

    start_logging(site.dir + '/var/log/update.log')

    sys.stdout.write("%s - Updating site '%s' from version %s to %s...\n\n" %
                     (time.strftime('%Y-%m-%d %H:%M:%S'), site.name, from_version, to_version))

    # etc/icinga/icinga.d/pnp4nagios.cfg was created by the PNP4NAGIOS OMD hook in previous
    # versions. Since we have removed Icinga 1 the "omd update" command tries to remove the
    # directory and complains about a non empty directory because of this left over symlink.
    # The hook could clean it up on it's own, but it would be too late and the warning is
    # displayed. We want to reduce the confusions about this, so we remove this file in
    # advance here.
    # This may be cleaned up one day, e.g. with 1.8 or 1.9. The worst that
    # would happen is that the users will be asked what to do.
    if os.path.lexists(site.dir + "/etc/icinga/icinga.d/pnp4nagios.cfg"):
        os.unlink(site.dir + "/etc/icinga/icinga.d/pnp4nagios.cfg")

    # Now apply changes of skeleton files. This can be done
    # in two ways:
    # 1. creating a patch from the old default files to the new
    #    default files and applying that to the current files
    # 2. creating a patch from the old default files to the current
    #    files and applying that to the new default files
    # We implement the first method.

    # read permissions
    read_skel_permissions()

    # In case the version_meta is stored in the site and it's the data of the
    # old version we are facing, use these files instead of the files from the
    # version directory. This makes updates possible without the old version.
    old_perms = site.skel_permissions

    from_skelroot = site.version_skel_dir
    to_skelroot = "/omd/versions/%s/skel" % to_version

    # First walk through skeleton files of new version
    walk_skel(to_skelroot,
              update_file, (site, from_version, to_version, old_perms),
              depth_first=False)

    # Now handle files present in old but not in new skel files
    walk_skel(from_skelroot,
              update_file, (site, from_version, to_version, old_perms),
              depth_first=True,
              exclude_if_in=to_skelroot)

    # Change symbolic link pointing to new version
    create_version_symlink(site, to_version)
    save_version_meta_data(site, to_version)

    call_scripts(site, 'update-pre-hooks')

    # Let hooks of the new(!) version do their work and update configuration.
    # For this we need to refresh the site configuration, because new hooks
    # may introduce new settings and default values.
    site.load_config()
    config_set_all(site)
    initialize_livestatus_tcp_tls_after_update(site)
    initialize_site_ca(site)
    save_site_conf(site)

    call_scripts(site, 'post-update')

    sys.stdout.write('Finished update.\n\n')
    stop_logging()


def initialize_livestatus_tcp_tls_after_update(site):
    """Keep unencrypted livestatus for old sites

    In case LIVESTATUS_TCP is on prior to the update, don't enable the
    encryption for compatibility. Only enable it for new sites (by the
    default setting)."""
    if site.conf["LIVESTATUS_TCP"] != "on":
        return  # Livestatus TCP not enabled, no need to set this option

    if "LIVESTATUS_TCP_TLS" in site.read_site_config():
        return  # Is already set in this site

    config_set_value(site, {}, "LIVESTATUS_TCP_TLS", value="off", save=True)


def _create_livestatus_tcp_socket_link(site):
    """Point the xinetd to the livestatus socket inteded by LIVESTATUS_TCP_TLS"""
    link_path = site.tmp_dir + "/run/live-tcp"
    target = "live-tls" if site.conf["LIVESTATUS_TCP_TLS"] == "on" else "live"

    if os.path.lexists(link_path):
        os.unlink(link_path)

    parent_dir = os.path.dirname(link_path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)

    os.symlink(target, link_path)


def _get_edition(omd_version):
    """Returns the long Check_MK Edition name or "unknown" of the given OMD version"""
    parts = omd_version.split(".")
    if parts[-1] == "demo":
        edition_short = parts[-2]
    else:
        edition_short = parts[-1]

    if edition_short == "cre":
        return "raw"
    elif edition_short == "cee":
        return "enterprise"
    elif edition_short == "cme":
        return "managed"
    return "unknown"


def main_umount(site, args, options=None):
    if options is None:
        options = {}

    only_version = options.get("version")

    # if no site is selected, all sites are affected
    exit_status = 0
    if not site.is_site_context():
        for site_id in all_sites():
            # Set global vars for the current site
            site = SiteContext(site_id)

            if only_version and site.version != only_version:
                continue

            # Skip the site even when it is partly running
            if not site.is_stopped():
                sys.stderr.write("Cannot unmount tmpfs of site '%s' while it is running.\n" %
                                 site.name)
                continue

            sys.stdout.write("%sUnmounting tmpfs of site %s%s..." %
                             (tty_bold, site.name, tty_normal))
            sys.stdout.flush()

            if not show_success(unmount_tmpfs(site, False, kill="kill" in options)):
                exit_status = 1
    else:
        # Skip the site even when it is partly running
        if not site.is_stopped():
            bail_out("Cannot unmount tmpfs of site '%s' while it is running." % site.name)
        unmount_tmpfs(site, kill="kill" in options)
    sys.exit(exit_status)


def main_init_action(site, command, args, options=None):
    if options is None:
        options = {}

    if site.is_site_context():
        exit_status = init_action(site, command, args, options)

        # When the whole site is about to be stopped check for remaining
        # processes and terminate them
        if command == "stop" and not args and exit_status == 0:
            terminate_site_user_processes(site)

        sys.exit(exit_status)

    # if no site is selected, all sites are affected

    only_version = options.get("version")
    bare = "bare" in options
    parallel = "parallel" in options

    max_site_len = max([8] + [len(site_id) for site_id in all_sites()])

    def parallel_output(site_id, line):
        sys.stdout.write(("%-" + str(max_site_len) + "s - %s") % (site_id, line))

    exit_states, processes = [], []
    for sitename in all_sites():
        site = SiteContext(sitename)

        if site.version is None:  # skip partially created sites
            continue

        if only_version and site.version != only_version:
            continue

        # Skip disabled sites completely
        if site.is_disabled():
            continue

        site.load_config()

        # Handle non autostart sites
        if command in [ "start", "restart", "reload" ] or \
            ( "auto" in options and command == "status" ):
            if not opt_force and not site.is_autostart():
                if bare:
                    continue
                elif not parallel:
                    sys.stdout.write("Ignoring site '%s': AUTOSTART != on\n" % site.name)
                else:
                    parallel_output(site.name, "Ignoring since autostart is disabled\n")
                continue

        if command == "status" and bare:
            sys.stdout.write('[%s]\n' % site.name)
        elif not parallel:
            sys.stdout.write("%sDoing '%s' on site %s:%s\n" %
                             (tty_bold, command, site.name, tty_normal))
        else:
            parallel_output(site.name, "Invoking '%s'\n" % (command))
        sys.stdout.flush()

        # We need to open a subprocess, because each site must be started with the account of the
        # site user. And after setuid() we cannot return.
        stdout = sys.stdout if not parallel else subprocess.PIPE
        stderr = sys.stderr if not parallel else subprocess.STDOUT
        bare_arg = ["--bare"] if bare else []
        p = subprocess.Popen([sys.argv[0], command] + bare_arg + [site.name] + args,
                             stdin=open(os.devnull, "r"),
                             stdout=stdout,
                             stderr=stderr)

        if parallel:
            # Make the output non blocking
            fd = p.stdout.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

            processes.append((site.name, p))
        else:
            exit_states.append(p.wait())
            if not bare:
                sys.stdout.write("\n")

    # In parallel mode wait for completion of all processes and collect
    # the output produced on stdout in the meantime. Since the processes
    # work in parallel and we want to have nearly "live" output, we process
    # the output line by line and prefix each line with the ID of the site.
    # The output of a single process must not block the output of the others,
    # so it seems we need to do some low level stuff here :-/.
    site_buf = {}
    while parallel and processes:
        for site_id, p in processes[:]:
            buf = site_buf.get(site_id, "")
            try:
                while True:
                    b = p.stdout.read(1024)
                    if not b:
                        break
                    buf += b
            except IOError as e:
                if e.errno == errno.EAGAIN:
                    pass
                else:
                    raise

            while True:
                pos = buf.find("\n")
                if pos == -1:
                    break
                line, buf = buf[:pos + 1], buf[pos + 1:]
                parallel_output(site_id, line)

            site_buf[site_id] = buf

            if not buf and p.poll() is not None:
                exit_states.append(p.returncode)
                processes.remove((site_id, p))
        time.sleep(0.01)

    # Do not simply take the highest exit code from the single sites.
    # We want to be able to output the fact that either none of the
    # sites is running or just some of the sites. For this we transform
    # the sites states 1 (not running) to 2 (partially running) if at least
    # one other site has state 0 (running) or 2 (partially running).
    if 1 in exit_states and (0 in exit_states or 2 in exit_states):
        exit_status = 2  # not all sites running, but at least one
    elif exit_states:
        exit_status = max(exit_states)
    else:
        exit_status = 0  # No OMD site existing

    sys.exit(exit_status)


def main_config(site, args, options=None):
    if options is None:
        options = {}

    if (len(args) == 0 or args[0] != "show") and \
        not site.is_stopped() and opt_force:
        need_start = True
        stop_site(site)
    else:
        need_start = False

    config_hooks = load_config_hooks(site)
    if len(args) == 0:
        config_configure(site, config_hooks)
    else:
        command = args[0]
        args = args[1:]
        if command == "show":
            config_show(site, config_hooks, args)
        elif command == "set":
            config_set(site, config_hooks, args)
        elif command == "change":
            config_change(site, config_hooks)
        else:
            config_usage()

    if need_start:
        start_site(site)


def main_su(site, args, options=None):
    if options is None:
        options = {}

    try:
        os.execl("/bin/su", "su", "-", "%s" % site.name)
    except OSError:
        bail_out("Cannot open a shell for user %s" % site.name)


def main_backup(site, args, options=None):
    if options is None:
        options = {}

    if len(args) == 0:
        bail_out("You need to provide either a path to the destination "
                 "file or \"-\" for backup to stdout.")

    dest = args[0]

    if dest == '-':
        fh = sys.stdout
        tar_mode = 'w|'
    else:
        if dest[0] != '/':
            dest = g_orig_wd + '/' + dest
        fh = file(dest, 'w')
        tar_mode = 'w:'

    if "no-compression" not in options:
        tar_mode += "gz"

    try:
        omdlib.backup.backup_site_to_tarfile(site, fh, tar_mode, options, opt_verbose)
    except IOError as e:
        bail_out("Failed to perform backup: %s" % e)


def main_restore(site, args, options=None):
    if options is None:
        options = {}

    set_conflict_option(options)

    if len(args) == 0:
        bail_out("You need to provide either a path to the source "
                 "file or \"-\" for restore from stdin.")

    source = args[-1]
    if source == '-':
        fh = sys.stdin
        tar_mode = 'r|*'
    elif os.path.exists(source):
        fh = file(source)
        tar_mode = 'r:*'
    else:
        bail_out("The backup archive does not exist.")

    try:
        tar = tarfile.open(fileobj=fh, mode=tar_mode)
    except tarfile.ReadError as e:
        bail_out("Failed to open the backup: %s" % e)

    try:
        sitename, version = omdlib.backup.get_site_and_version_from_backup(tar)
    except Exception as e:
        bail_out(e)

    if not version_exists(version):
        bail_out("You need to have version %s installed to be able to restore "
                 "this backup." % version)

    if is_root():
        # Ensure the restore is done with the sites version
        if version != omdlib.__version__:
            exec_other_omd(site, version, "restore")

        # Restore site with its original name, or specify a new one
        new_sitename = sitename
        if len(args) == 2:
            new_sitename = args[0]
    else:
        new_sitename = site_name()

    site = SiteContext(new_sitename)

    source_txt = 'stdin' if source == '-' else source
    if is_root():
        sys.stdout.write("Restoring site %s from %s...\n" % (site.name, source_txt))
        sys.stdout.flush()

        prepare_restore_as_root(site, options)

    else:
        sys.stdout.write("Restoring site from %s...\n" % source_txt)
        sys.stdout.flush()

        site.load_config()
        orig_apache_port = site.conf["APACHE_TCP_PORT"]

        prepare_restore_as_site_user(site, options)

    # Now extract all files
    for tarinfo in tar:
        # The files in the tar archive start with the siteid as first element.
        # Remove this first element from the file paths and also care for hard link
        # targets.

        # Remove leading site name from paths
        tarinfo.name = '/'.join(tarinfo.name.split('/')[1:])
        if opt_verbose:
            sys.stdout.write("Restoring %s...\n" % tarinfo.name)

        if tarinfo.islnk():

            parts = tarinfo.linkname.split('/')

            if parts[0] == sitename:
                new_linkname = '/'.join(parts[1:])

                if opt_verbose:
                    sys.stdout.write("  Rewriting link target from %s to %s\n" %
                                     (tarinfo.linkname, new_linkname))
                tarinfo.linkname = new_linkname

        tar.extract(tarinfo, path=site.dir)
    tar.close()

    site.load_config()

    # give new user all files
    chown_tree(site.dir, site.name)

    # Change config files from old to new site (see rename_site())
    if sitename != site.name:
        old_site = SiteContext(sitename)
        patch_skeleton_files(old_site, site)

    # Now switch over to the new site as currently active site
    os.chdir(site.dir)
    set_environment(site)

    if is_root():
        postprocess_restore_as_root(site, options)
    else:
        postprocess_restore_as_site_user(site, options, orig_apache_port)


def prepare_restore_as_root(site, options):
    reuse = False
    if "reuse" in options:
        reuse = True
        if not user_verify(site, allow_populated=True):
            bail_out("Error verifying site user.")
        fstab_verify(site)

    sitename_must_be_valid(site, reuse)

    if reuse:
        if not site.is_stopped() and not "kill" in options:
            bail_out("Cannot restore '%s' while it is running." % (site.name))
        else:
            os.system('omd stop %s' % site.name)  # nosec
        unmount_tmpfs(site, kill="kill" in options)

    if not reuse:
        uid = options.get("uid")
        gid = options.get("gid")
        useradd(site, uid, gid)  # None for uid/gid means: let Linux decide
    else:
        sys.stdout.write("Deleting existing site data...\n")
        shutil.rmtree(site.dir)
        ok()

    os.mkdir(site.dir)


def prepare_restore_as_site_user(site, options):
    if not site.is_stopped() and not "kill" in options:
        bail_out("Cannot restore site while it is running.")

    verify_directory_write_access(site)

    sys.stdout.write("Stopping site processes...\n")
    stop_site(site)
    kill_site_user_processes(site, exclude_current_and_parents=True)
    ok()

    unmount_tmpfs(site)

    sys.stdout.write("Deleting existing site data...")
    for f in os.listdir(site.dir):
        path = site.dir + "/" + f
        if os.path.islink(path) or os.path.isfile(path):
            os.unlink(path)
        else:
            shutil.rmtree(path)
    ok()


# Scans all site directories and ensures the site user is able to write all directories.
# This is needed to prevent eventual permission issues during the rmtree process.
def verify_directory_write_access(site):
    wrong = []
    for dirpath, dirnames, _filenames in os.walk(site.dir):
        for dirname in dirnames:
            path = dirpath + "/" + dirname
            if os.path.islink(path):
                continue

            if not os.access(path, os.W_OK):
                wrong.append(path)

    if wrong:
        bail_out("Unable to start restore because of a permission issue.\n\n"
                 "The restore needs to be able to clean the whole site to be able to restore "
                 "the backup. Missing write access on the following paths:\n\n"
                 "    %s" % "\n    ".join(wrong))


def terminate_site_user_processes(site):
    """Sends a SIGTERM to all running site processes and waits up to 5 seconds for termination

    In case one or more processes are still running after the timeout, the method will make
    the current OMD call terminate.
    """

    pids = site_user_processes(site, exclude_current_and_parents=True)
    if not pids:
        return

    sys.stdout.write("Stopping %d remaining site processes..." % len(pids))

    timeout_at = time.time() + 5
    sent_terminate = False
    while pids and time.time() < timeout_at:
        for pid in pids[:]:
            try:
                if not sent_terminate:
                    if opt_verbose:
                        sys.stdout.write("%d..." % pid)
                    os.kill(pid, signal.SIGTERM)
                else:
                    os.kill(pid, signal.SIG_DFL)
            except OSError as e:
                if e.errno == errno.ESRCH:  # No such process
                    pids.remove(pid)
                else:
                    raise

        sent_terminate = True
        time.sleep(0.1)

    if pids:
        bail_out("\nFailed to stop remaining site processes: %s" % ", ".join(map(str, pids)))
    else:
        ok()


def kill_site_user_processes(site, exclude_current_and_parents=False):
    pids = site_user_processes(site, exclude_current_and_parents)
    tries = 5
    while tries > 0 and pids:
        for pid in pids[:]:
            try:
                if opt_verbose:
                    sys.stdout.write("Killing process %d...\n" % pid)
                os.kill(pid, signal.SIGKILL)
            except OSError as e:
                if e.errno == errno.ESRCH:
                    pids.remove(pid)  # No such process
                else:
                    raise
        time.sleep(1)
        tries -= 1

    if pids:
        bail_out("Failed to kill site processes: %s" % ", ".join(map(str, pids)))


def get_current_and_parent_pids():
    """Return list of PIDs of the current process and parent process tree till pid 0"""
    pids = []
    process = psutil.Process()
    while process and process.pid != 0:
        pids.append(process.pid)
        process = process.parent()
    return pids


def site_user_processes(site, exclude_current_and_parents):
    """Return list of PIDs of all running site user processes (that are not excluded)"""
    exclude = []
    if exclude_current_and_parents:
        exclude = get_current_and_parent_pids()

    p = subprocess.Popen(["ps", "-U", site.name, "-o", "pid", "--no-headers"],
                         close_fds=True,
                         stdin=open(os.devnull),
                         stdout=subprocess.PIPE)
    exclude.append(p.pid)

    pids = []
    for l in p.communicate()[0].split("\n"):
        line = l.strip()
        if not line:
            continue

        pid = int(line)

        if pid in exclude:
            continue

        pids.append(pid)
    return pids


def postprocess_restore_as_root(site, options):
    # Entry for tmps in /etc/fstab
    if "reuse" not in options:
        add_to_fstab(site, tmpfs_size=options.get('tmpfs-size'))

    finalize_site(site, "restore", "apache-reload" in options)


def postprocess_restore_as_site_user(site, options, orig_apache_port):
    # Keep the apache port the site currently being replaced had before
    # (we can not restart the system apache as site user)
    site.conf["APACHE_TCP_PORT"] = orig_apache_port
    save_site_conf(site)

    finalize_site_as_user(site, "restore")


def main_cleanup(site, args, options=None):
    if options is None:
        options = {}

    package_manager = PackageManager.factory()
    if package_manager is None:
        bail_out("Command is not supported on this platform")

    for version in omd_versions():
        site_ids = [s for s in all_sites() if SiteContext(s).version == version]
        if site_ids:
            sys.stdout.write("%s%-20s%s In use (by %s). Keeping this version.\n" %
                             (tty_bold, version, tty_normal, ", ".join(site_ids)))
            continue

        version_path = os.path.join("/omd/versions", version)

        packages = package_manager.find_packages_of_path(version_path)
        if len(packages) != 1:
            sys.stdout.write("%s%-20s%s Could not determine package. Keeping this version.\n" %
                             (tty_bold, version, tty_normal))
            continue

        sys.stdout.write("%s%-20s%s Uninstalling\n" % (tty_bold, version, tty_normal))
        package_manager.uninstall(packages[0])

        # In case there were modifications made to the version the uninstall may leave
        # some files behind. Remove the whole version directory
        if os.path.exists(version_path):
            shutil.rmtree(version_path)

    # In case the last version has been removed ensure some things created globally
    # are removed.
    if not omd_versions():
        _cleanup_global_files()


def _cleanup_global_files():
    sys.stdout.write("No version left. Cleaning up global files.\n")
    shutil.rmtree(g_info.OMD_PHYSICAL_BASE, ignore_errors=True)

    for path in [
            "/omd",
            g_info.APACHE_CONF_DIR + "/zzz_omd.conf",
            "/etc/init.d/omd",
            "/usr/bin/omd",
    ]:
        try:
            os.unlink(path)
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise

    if group_exists("omd"):
        groupdel("omd")


class PackageManager(object):
    __metaclass__ = abc.ABCMeta

    @classmethod
    def factory(cls):
        if os.path.exists("/etc/cma"):
            return None

        distro_code = g_info.DISTRO_CODE
        if distro_code.startswith("el") \
           or distro_code.startswith("sles"):
            return PackageManagerRPM()
        return PackageManagerDEB()

    @abc.abstractmethod
    def uninstall(self, package_name):
        raise NotImplementedError()

    def _execute_uninstall(self, cmd):
        p = self._execute(cmd)
        output = p.communicate()[0]
        if p.wait() != 0:
            bail_out("Failed to uninstall package:\n%s" % output)

    def _execute(self, cmd):
        if opt_verbose:
            sys.stdout.write("Executing: %s\n" % subprocess.list2cmdline(cmd))

        return subprocess.Popen(cmd,
                                shell=False,
                                close_fds=True,
                                stdin=open(os.devnull),
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT)


class PackageManagerDEB(PackageManager):
    def uninstall(self, package_name):
        self._execute_uninstall(["apt-get", "-y", "purge", package_name])

    def find_packages_of_path(self, path):
        real_path = os.path.realpath(path)

        p = self._execute(["dpkg", "-S", real_path])
        output = p.communicate()[0]
        if p.wait() != 0:
            bail_out("Failed to find packages:\n%s" % output)

        for line in output.split("\n"):
            if line.endswith(": %s" % real_path):
                return line.split(": ", 1)[0].split(", ")

        return []


class PackageManagerRPM(PackageManager):
    def uninstall(self, package_name):
        self._execute_uninstall(["rpm", "-e", package_name])

    def find_packages_of_path(self, path):
        real_path = os.path.realpath(path)

        p = self._execute(["rpm", "-qf", real_path])
        output = p.communicate()[0]

        if p.wait() == 1 and "not owned" in output:
            return []

        elif p.wait() != 0:
            bail_out("Failed to find packages:\n%s" % output)

        return output.strip().split("\n")


class AbstractSiteContext(object):
    """Object wrapping site specific information"""
    __metaclass__ = abc.ABCMeta

    def __init__(self, sitename):
        super(AbstractSiteContext, self).__init__()
        self._sitename = sitename
        self._config_loaded = False
        self._config = {}

    @property
    def name(self):
        return self._sitename

    @abc.abstractproperty
    def dir(self):
        raise NotImplementedError()

    @abc.abstractproperty
    def tmp_dir(self):
        raise NotImplementedError()

    @property
    def version_meta_dir(self):
        return "%s/.version_meta" % self.dir

    @property
    def conf(self):
        """{ "CORE" : "nagios", ... } (contents of etc/omd/site.conf plus defaults from hooks)"""
        if not self._config_loaded:
            raise Exception("Config not loaded yet")
        return self._config

    @abc.abstractmethod
    def load_config(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def exists(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def is_empty(self):
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def is_site_context():
        raise NotImplementedError()


class SiteContext(AbstractSiteContext):
    @property
    def dir(self):
        return "/omd/sites/" + self._sitename

    @property
    def tmp_dir(self):
        return "%s/tmp" % self.dir

    # TODO: Clean up the None case!
    @property
    def version(self):
        """The version of a site is solely determined by the link ~SITE/version"""
        version_link = self.dir + "/version"
        try:
            return os.readlink(version_link).split("/")[-1]
        except:
            return None

    @property
    def hook_dir(self):
        if self.version is None:
            return None
        return "/omd/versions/%s/lib/omd/hooks/" % self.version

    @property
    def replacements(self):
        """Dictionary of key/value for replacing macros in skel files"""
        return {
            "###SITE###": self.name,
            "###ROOT###": self.dir,
        }

    def load_config(self):
        """Load all variables from omd/sites.conf. These variables always begin with
        CONFIG_. The reason is that this file can be sources with the shell.

        Puts these variables into the config dict without the CONFIG_. Also
        puts the variables into the process environment."""
        self._config = self.read_site_config()

        # Get the default values of all config hooks that are not contained
        # in the site configuration. This can happen if there are new hooks
        # after an update or when a site is being created.
        if self.hook_dir and os.path.exists(self.hook_dir):
            for hook_name in sort_hooks(os.listdir(self.hook_dir)):
                if hook_name[0] != '.' and hook_name not in self._config:
                    content = call_hook(self, hook_name, ["default"])[1]
                    self._config[hook_name] = content

        self._config_loaded = True

    def read_site_config(self):
        """Read and parse the file site.conf of a site into a dictionary and returns it"""
        config = {}
        confpath = "%s/etc/omd/site.conf" % (self.dir)
        if not os.path.exists(confpath):
            return {}

        for line in file(confpath):
            line = line.strip()
            if line == "" or line[0] == "#":
                continue
            var, value = line.split("=", 1)
            if not var.startswith("CONFIG_"):
                sys.stderr.write("Ignoring invalid variable %s.\n" % var)
            else:
                config[var[7:].strip()] = value.strip().strip("'")

        return config

    def exists(self):
        # In dockerized environments the tmpfs may be managed by docker (when
        # using the --tmpfs option).  In this case the site directory is
        # created as parent of the tmp directory to mount the tmpfs during
        # container initialization. Detect this situation and don't treat the
        # site as existing in that case.
        if is_dockerized():
            if not os.path.exists(self.dir):
                return False
            if os.listdir(self.dir) == ["tmp"]:
                return False
            return True

        return os.path.exists(self.dir)

    def is_empty(self):
        for entry in os.listdir(self.dir):
            if entry not in ['.', '..']:
                return False
        return True

    def is_autostart(self):
        """Determines whether a specific site is set to autostart."""
        return self.conf.get('AUTOSTART', 'on') == 'on'

    def is_disabled(self):
        """Whether or not this site has been disabled with 'omd disable'"""
        apache_conf = "/omd/apache/%s.conf" % self.name
        return not os.path.exists(apache_conf)

    def is_stopped(self):
        """Check if site is completely stopped"""
        return check_status(self, display=False) == 1

    @staticmethod
    def is_site_context():
        return True

    @property
    def skel_permissions(self):
        # type: () -> Dict[str, int]
        """Returns the skeleton permissions. Load either from version meta directory
        or from the original version skel.permissions file"""
        if not self._has_version_meta_data():
            return load_skel_permissions(self.version)

        return load_skel_permissions_from(self.version_meta_dir + "/skel.permissions")

    @property
    def version_skel_dir(self):
        """Returns the current version skel directory. In case the meta data is
        available and fits the sites version use that one instead of the version
        skel directory."""
        if not self._has_version_meta_data():
            return "/omd/versions/%s/skel" % self.version
        return self.version_meta_dir + "/skel"

    def _has_version_meta_data(self):
        if not os.path.exists(self.version_meta_dir):
            return False

        if self._version_meta_data_version() != self.version:
            return False

        return True

    def _version_meta_data_version(self):
        with open(self.version_meta_dir + "/version") as f:
            return f.read().strip()


class RootContext(AbstractSiteContext):
    def __init__(self):
        super(RootContext, self).__init__(sitename=None)

    @property
    def dir(self):
        return "/"

    @property
    def tmp_dir(self):
        return "/tmp"

    def version(self):
        return omdlib.__version__

    def load_config(self):
        pass

    def exists(self):
        return False

    def is_empty(self):
        return False

    @staticmethod
    def is_site_context():
        return False


class VersionInfo(object):
    """Provides OMD version/platform specific infos"""
    def __init__(self, version):
        self._version = version

        # Register all relevant vars
        self.USERADD_OPTIONS = ""
        self.APACHE_USER = ""
        self.ADD_USER_TO_GROUP = ""
        self.MOUNT_OPTIONS = ""
        self.INIT_CMD = ""
        self.APACHE_CTL = ""
        self.APACHE_INIT_NAME = ""
        self.OMD_PHYSICAL_BASE = ""
        self.APACHE_CONF_DIR = ""
        self.DISTRO_CODE = ""

    def load(self):
        """Update vars with real values from info file"""
        for k, v in self._read_info().items():
            setattr(self, k, v)

    def _read_info(self):
        info = {}
        info_dir = "/omd/versions/" + omdlib.__version__ + "/share/omd"
        for f in os.listdir(info_dir):
            if f.endswith(".info"):
                for line in file(info_dir + "/" + f):
                    try:
                        line = line.strip()
                        # Skip comment and empty lines
                        if line.startswith('#') or line == '':
                            continue
                        # Remove everything after the first comment sign
                        if '#' in line:
                            line = line[:line.index('#')].strip()
                        var, value = line.split('=')
                        value = value.strip()
                        if var.endswith("+"):
                            var = var[:-1]  # remove +
                            info[var.strip()] += " " + value
                        else:
                            info[var.strip()] = value
                    except Exception:
                        bail_out('Unable to parse line "%s" in file "%s"' %
                                 (line, info_dir + "/" + f))
        return info


exclude_options = [
    ("no-rrds", None, False, "do not copy RRD files (performance data)"),
    ("no-logs", None, False, "do not copy the monitoring history and log files"),
    ("no-past", "N", False, "do not copy RRD files, the monitoring history and log files"),
]

commands = [
    #  command       The id of the command
    #  only_root     This option is only available when omd command is run as root
    #  no_suid       The command is available for root and site-user, but no switch
    #                to the site user is performed before execution the mode function
    #  needs_site    When run as root:
    #                0: No site must be specified
    #                1: A site must be specified
    #                2: A site is optional
    #  must_exist    Site must be existant for this command
    #  confirm       Is a confirm dialog shown before command execution?
    #  args          Help text for command individual arguments
    #  function      Handler function for this command
    #  options_spec  List of individual arguments for this command
    #  description   Text for the help of omd
    #  confirm_text  Confirm text to show before calling the handler function
    ("help", False, False, 0, 0, False, "", main_help, [], "Show general help", ""),
    ("setversion", True, False, 0, 0, False, "VERSION", main_setversion, [],
     "Sets the default version of OMD which will be used by new sites", ""),
    ("version", False, False, 0, 0, False, "[SITE]", main_version,
     [("bare", "b", False, "output plain text optimized for parsing")], "Show version of OMD", ""),
    ("versions", False, False, 0, 0, False, "", main_versions, [
        ("bare", "b", False, "output plain text optimized for parsing")
    ], "List installed OMD versions", ""),
    ("sites", False, False, 0, 0, False, "", main_sites,
     [("bare", "b", False, "output plain text for easy parsing")], "Show list of sites", ""),
    ("create", True, False, 1, 0, False, "", main_create, [
        ("uid", "u", True, "create site user with UID ARG"),
        ("gid", "g", True, "create site group with GID ARG"),
        ("admin-password", None, True, "set initial password instead of generating one"),
        ("reuse", None, False, "do not create a site user, reuse existing one"),
        ("no-init", "n", False, "leave new site directory empty (a later omd init does this"),
        ("no-autostart", "A", False, "set AUTOSTART to off (useful for test sites)"),
        ("apache-reload", False, False, "Issue a reload of the system apache instead of a restart"),
        ("no-tmpfs", None, False, "set TMPFS to off"),
        ("tmpfs-size", "t", True,
         "specify the maximum size of the tmpfs (defaults to 50% of RAM), examples: 500M, 20G, 60%"
        ),
    ], "Create a new site (-u UID, -g GID)",
     "This command performs the following actions on your system:\n"
     "- Create the system user <SITENAME>\n"
     "- Create the system group <SITENAME>\n"
     "- Create and populate the site home directory\n"
     "- Restart the system wide apache daemon\n"
     "- Add tmpfs for the site to fstab and mount it"),
    ("init", True, False, 1, 1, False, "", main_init, [
        ("apache-reload", False, False, "Issue a reload of the system apache instead of a restart"),
    ], "Populate site directory with default files and enable the site", ""),
    ("rm", True, True, 1, 1, True, "", main_rm, [
        ("reuse", None, False, "assume --reuse on create, do not delete site user/group"),
        ("kill", None, False, "kill processes of the site before deleting it"),
        ("apache-reload", False, False, "Issue a reload of the system apache instead of a restart"),
    ], "Remove a site (and its data)", "PLEASE NOTE: This action removes all configuration files\n"
     "             and variable data of the site.\n"
     "\n"
     "In detail the following steps will be done:\n"
     "- Stop all processes of the site\n"
     "- Unmount tmpfs of the site\n"
     "- Remove tmpfs of the site from fstab\n"
     "- Remove the system user <SITENAME>\n"
     "- Remove the system group <SITENAME>\n"
     "- Remove the site home directory\n"
     "- Restart the system wide apache daemon\n"),
    ("disable", True, False, 1, 1, False, "", main_disable, [
        ("kill", None, False, "kill processes using tmpfs before unmounting it")
    ], "Disable a site (stop it, unmount tmpfs, remove Apache hook)", ""),
    ("enable", True, False, 1, 1, False, "", main_enable, [],
     "Enable a site (reenable a formerly disabled site)", ""),
    ("mv", True, False, 1, 1, False, "NEWNAME",
     lambda site, args, opts: main_mv_or_cp(site, "mv", args, opts), [
         ("uid", "u", True, "create site user with UID ARG"),
         ("gid", "g", True, "create site group with GID ARG"),
         ("reuse", None, False, "do not create a site user, reuse existing one"),
         ("conflict", None, True,
          "non-interactive conflict resolution. ARG is install, keepold, abort or ask"),
         ("tmpfs-size", "t", True,
          "specify the maximum size of the tmpfs (defaults to 50% of RAM), examples: 500M, 20G, 60%"
         ),
         ("apache-reload", False, False,
          "Issue a reload of the system apache instead of a restart"),
     ], "Rename a site", ""),
    ("cp", True, False, 1, 1, False, "NEWNAME",
     lambda site, args, opts: main_mv_or_cp(site, "cp", args, opts),
     [("uid", "u", True, "create site user with UID ARG"),
      ("gid", "g", True, "create site group with GID ARG"),
      ("reuse", None, False, "do not create a site user, reuse existing one")] + exclude_options +
     [
         ("conflict", None, True,
          "non-interactive conflict resolution. ARG is install, keepold, abort or ask"),
         ("tmpfs-size", "t", True,
          "specify the maximum size of the tmpfs (defaults to 50% of RAM), examples: 500M, 20G, 60%"
         ),
         ("apache-reload", False, False,
          "Issue a reload of the system apache instead of a restart"),
     ], "Make a copy of a site", ""),
    ("update", False, False, 1, 1, False, "", main_update, [
        ("conflict", None, True,
         "non-interactive conflict resolution. ARG is install, keepold, abort or ask")
    ], "Update site to other version of OMD", ""),
    ("start", False, False, 2, 1, False, "[SERVICE]",
     lambda site, args, opts: main_init_action(site, "start", args, opts), [
         ("version", "V", True, "only start services having version ARG"),
         ("parallel", "p", False, "Invoke start of sites in parallel"),
     ], "Start services of one or all sites", ""),
    ("stop", False, False, 2, 1, False, "[SERVICE]",
     lambda site, args, opts: main_init_action(site, "stop", args, opts), [
         ("version", "V", True, "only stop sites having version ARG"),
         ("parallel", "p", False, "Invoke stop of sites in parallel"),
     ], "Stop services of site(s)", ""),
    ("restart", False, False, 2, 1, False, "[SERVICE]",
     lambda site, args, opts: main_init_action(site, "restart", args, opts), [
         ("version", "V", True, "only restart sites having version ARG")
     ], "Restart services of site(s)", ""),
    ("reload", False, False, 2, 1, False, "[SERVICE]",
     lambda site, args, opts: main_init_action(site, "reload", args, opts), [
         ("version", "V", True, "only reload sites having version ARG")
     ], "Reload services of site(s)", ""),
    ("status", False, False, 2, 1, False, "[SERVICE]",
     lambda site, args, opts: main_init_action(site, "status", args, opts), [
         ("version", "V", True, "show only sites having version ARG"),
         ("auto", None, False, "show only sites with AUTOSTART = on"),
         ("bare", "b", False, "output plain format optimized for parsing"),
     ], "Show status of services of site(s)", ""),
    ("config", False, False, 1, 1, False, "...", main_config, [],
     "Show and set site configuration parameters", ""),
    ("diff", False, False, 1, 1, False, "([RELBASE])", main_diff, [
        ("bare", "b", False, "output plain diff format, no beautifying")
    ], "Shows differences compared to the original version files", ""),
    ("su", True, False, 1, 1, False, "", main_su, [], "Run a shell as a site-user", ""),
    ("umount", False, False, 2, 1, False, "", main_umount, [
        ("version", "V", True, "unmount only sites with version ARG"),
        ("kill", None, False, "kill processes using the tmpfs before unmounting it")
    ], "Umount ramdisk volumes of site(s)", ""),
    ("backup", False, True, 1, 1, False, "[SITE] [-|ARCHIVE_PATH]", main_backup, exclude_options + [
        ("no-compression", None, False, "do not compress tar archive"),
    ], "Create a backup tarball of a site, writing it to a file or stdout", ""),
    ("restore", False, False, 0, 0, False, "[SITE] [-|ARCHIVE_PATH]", main_restore, [
        ("uid", "u", True, "create site user with UID ARG"),
        ("gid", "g", True, "create site group with GID ARG"),
        ("reuse", None, False, "do not create a site user, reuse existing one"),
        ("kill", None, False,
         "kill processes of site when reusing an existing one before restoring"),
        ("apache-reload", False, False, "Issue a reload of the system apache instead of a restart"),
        ("conflict", None, True,
         "non-interactive conflict resolution. ARG is install, keepold, abort or ask"),
        ("tmpfs-size", "t", True, "specify the maximum size of the tmpfs (defaults to 50% of RAM)"),
    ], "Restores the backup of a site to an existing site or creates a new site", ""),
    ("cleanup", True, False, 0, 0, False, "", main_cleanup, [],
     "Uninstall all Check_MK versions that are not used by any site.", ""),
]


def handle_global_option(main_args, opt, orig):
    global opt_verbose
    global opt_force
    global opt_interactive

    def opt_arg(main_args):
        # TODO: Fix the code and remove the pragma below!
        if len(main_args) < 1:  # pylint: disable=used-before-assignment
            bail_out("Option %s needs an argument." % opt)
        arg = main_args[0]
        main_args = main_args[1:]
        return arg, main_args

    if opt in ['V', 'version']:
        # Switch to other version of bin/omd
        version, main_args = opt_arg(main_args)
        if version != omdlib.__version__:
            omd_path = "/omd/versions/%s/bin/omd" % version
            if not os.path.exists(omd_path):
                bail_out("OMD version '%s' is not installed." % version)
            os.execv(omd_path, sys.argv)
            bail_out("Cannot execute %s." % omd_path)
    elif opt in ['f', 'force']:
        opt_force = True
        opt_interactive = False
    elif opt in ['i', 'interactive']:
        opt_force = False
        opt_interactive = True
    elif opt in ['v', 'verbose']:
        opt_verbose = True
    else:
        bail_out("Invalid global option %s.\n" "Call omd help for available options." % orig)

    return main_args


def parse_command_options(args, options_spec):
    # Give a short overview over the command specific options
    # when the user specifies --help:
    if len(args) and args[0] in ['-h', '--help']:
        sys.stdout.write("Possible options for this command:\n")
        for llong, sshort, needarg, help_txt in options_spec:
            args_text = "%s--%s" % (sshort and "-%s," % sshort or "", llong)
            sys.stdout.write(" %-15s %3s  %s\n" % (args_text, needarg and "ARG" or "", help_txt))
        sys.exit(0)

    options = {}

    while len(args) >= 1 and args[0][0] == '-' and len(args[0]) > 1:
        opt = args[0]
        args = args[1:]
        entries = []
        if opt.startswith("--"):
            # Handle --foo=bar
            if "=" in opt:
                opt, optarg = opt.split("=", 1)
                args = [optarg] + args
                for e in options_spec:
                    if e[0] == opt[2:] and not e[2]:
                        bail_out("The option %s does not take an argument" % opt)

            for e in options_spec:
                if e[0] == opt[2:]:
                    entries = [e]
        else:
            for char in opt:
                for e in options_spec:
                    if e[1] == char:
                        entries.append(e)

        if len(entries) == 0:
            bail_out("Invalid option '%s'" % opt)

        for llong, sshort, needs_arg, help_txt in entries:
            arg = None
            if needs_arg:
                if len(args) == 0:
                    bail_out("Option '%s' needs an argument." % opt)
                arg = args[0]
                args = args[1:]
            options[llong] = arg
    return (args, options)


def exec_other_omd(site, version, command):
    # Rerun with omd of other version
    omd_path = "/omd/versions/%s/bin/omd" % version
    if os.path.exists(omd_path):
        if command == "update":
            # Prevent inheriting environment variables from this versions/site environment
            # into the execed omd call. The OMD call must import the python version related
            # modules and libaries. This only works when PYTHONPATH and LD_LIBRARY_PATH are
            # not already set when calling "omd update"
            try:
                del os.environ["PYTHONPATH"]
            except KeyError:
                pass

            try:
                del os.environ["LD_LIBRARY_PATH"]
            except KeyError:
                pass

        os.execv(omd_path, sys.argv)
        bail_out("Cannot run bin/omd of version %s." % version)
    else:
        bail_out("Site %s uses version %s which is not installed.\n"
                 "Please reinstall that version and retry this command." % (site.name, version))


def random_password():
    return ''.join(random.choice(string.ascii_letters + string.digits) for i in range(8))


def hash_password(password):
    return sha256_crypt.hash(password)


def ensure_mkbackup_lock_dir_rights():
    # Some details regarding this nested try/except blocks:
    # * On /run/lock/ the sticky bit is set, which means only the *creator* of a folder in this directory is
    #   allowed to change the meta data of a created folder
    # * We need to ensure that the folder exists *and* that it has the needed permissions. We have 3 cases:
    #   1) The directory does not yet exist. Here we can create it and change the needed permissions
    #   2) The directory does already exist. Here we do not need to do anything else and we hope for the
    #       creating process to have set the needed rights
    #   3) The directory does not exist and we cannot create it. This is a real issue so give the user a hint.
    try:
        lock_dir_as_path = Path(mkbackup_lock_dir)
        lock_dir_as_path.mkdir(mode=0o0770, exist_ok=True, parents=True)
        try:
            os.chown(mkbackup_lock_dir, -1, grp.getgrnam("omd").gr_gid)
            lock_dir_as_path.chmod(0o0770)
        except OSError:
            pass
    except IOError:
        sys.stdout.write("Unable to create %s needed for mkbackup. "
                         "This may be due to the fact that your SITE "
                         "User isn't allowed to create the backup directory. "
                         "You could resolve this issue by running 'sudo omd start' as root "
                         "(and not as SITE user)." % mkbackup_lock_dir)


#.
#   .--Main----------------------------------------------------------------.
#   |                        __  __       _                                |
#   |                       |  \/  | __ _(_)_ __                           |
#   |                       | |\/| |/ _` | | '_ \                          |
#   |                       | |  | | (_| | | | | |                         |
#   |                       |_|  |_|\__,_|_|_| |_|                         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |  Main entry point                                                    |
#   '----------------------------------------------------------------------'

# Some global variables
# TODO: Clean em all up
opt_verbose = False
opt_interactive = False
opt_force = False
opt_conflict = "ask"

g_info = VersionInfo(omdlib.__version__)
g_orig_wd = "/"


# Handle global options. We might convert this to getopt
# later. But a problem here is that we have options appearing
# *before* the command and command specific ones. We handle
# the options before the command here only
# TODO: Refactor these global variables
# TODO: Refactor to argparse. Be aware of the pitfalls of the OMD command line scheme
def main():
    ensure_mkbackup_lock_dir_rights()
    global g_orig_wd

    site = RootContext()
    main_args = sys.argv[1:]

    while len(main_args) >= 1 and main_args[0].startswith("-"):
        opt = main_args[0]
        main_args = main_args[1:]
        if opt.startswith("--"):
            main_args = handle_global_option(main_args, opt[2:], opt)
        else:
            for c in opt[1:]:
                main_args = handle_global_option(main_args, c, opt)

    if len(main_args) < 1:
        main_help(site)
        sys.exit(1)

    command = main_args[0]
    args = main_args[1:]

    found = False

    only_root, no_suid, needs_site, site_must_exist, \
      confirm, _argumentlist, command_function, option_spec, \
      _description, confirm_text = 10 * [None]

    for c, only_root, no_suid, needs_site, site_must_exist, confirm, _argumentlist, \
        command_function, option_spec, _description, confirm_text in commands:
        if c == command:
            found = True
            break

    if not found:
        sys.stderr.write("omd: no such command: %s\n" % command)
        main_help(site)
        sys.exit(1)

    if not is_root() and only_root:
        bail_out("omd: root permissions are needed for this command.")

    # Parse command options. We need to do this now in order to know,
    # if a site name has been specified or not
    args, command_options = parse_command_options(args, option_spec)

    # Some commands need a site to be specified. If we are
    # called as root, this must be done explicitely. If we
    # are site user, the site name is our user name
    if needs_site > 0:
        if is_root():
            if len(args) >= 1:
                site = SiteContext(args[0])
                args = args[1:]
            elif needs_site == 1:
                bail_out("omd: please specify site.")
        else:
            site = SiteContext(site_name())

    check_site_user(site, site_must_exist)

    # Commands operating on an existing site *must* run omd in
    # the same version as the site has! Sole exception: update.
    # That command must be run in the target version
    if site.is_site_context() and site_must_exist and command != "update":
        v = site.version
        if v is None:  # Site has no home directory or version link
            if command == "rm":
                sys.stdout.write("WARNING: This site has an empty home directory and is not\n"
                                 "assigned to any OMD version. You are running version %s.\n" %
                                 omdlib.__version__)
            elif command != "init":
                bail_out("This site has an empty home directory /omd/sites/%s.\n"
                         "If you have created that site with 'omd create --no-init %s'\n"
                         "then please first do an 'omd init %s'." % (3 * (site.name,)))
        elif omdlib.__version__ != v:
            exec_other_omd(site, v, command)

    g_info.load()
    site.load_config()

    # Commands which affect a site and can be called as root *or* as
    # site user should always run with site user priviledges. That way
    # we are sure that new files and processes are created under the
    # site user and never as root.
    try:
        g_orig_wd = os.getcwd()
    except OSError as e:
        if e.errno == errno.ENOENT:
            g_orig_wd = "/"
        else:
            raise

    if not no_suid and site.is_site_context() and is_root() and not only_root:
        switch_to_site_user(site)

    # Make sure environment is in a defined state
    if site.is_site_context():
        clear_environment()
        set_environment(site)

    if (opt_interactive or confirm) and not opt_force:
        sys.stdout.write("%s (yes/NO): " % confirm_text)
        sys.stdout.flush()
        a = sys.stdin.readline().strip()
        if a.lower() != "yes":
            sys.exit(0)

    try:
        command_function(site, args, command_options)
    except KeyboardInterrupt:
        bail_out(tty_normal + "Aborted.")
