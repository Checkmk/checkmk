#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The command line tool specific implementations of the omd command and main entry point"""

from __future__ import annotations

import contextlib
import errno
import fcntl
import io
import os
import pwd
import re
import shutil
import subprocess
import sys
import tarfile
import time
import traceback
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import (
    assert_never,
    cast,
    Final,
    IO,
    Literal,
    override,
    TextIO,
)

import omdlib
import omdlib.backup
import omdlib.utils
from omdlib.config_hooks import (
    config_set_all,
    config_set_value,
    ConfigHook,
    ConfigHookChoices,
    ConfigHooks,
    create_config_environment,
    load_config,
    load_config_hooks,
    load_hook_dependencies,
    save_site_conf,
)
from omdlib.console import ok, show_success
from omdlib.contexts import RootContext, SiteContext
from omdlib.dialog import (
    ask_user_choices,
    dialog_config_choice_has_error,
    dialog_menu,
    dialog_message,
    dialog_regex,
    dialog_yesno,
    user_confirms,
)
from omdlib.finalize import CommandType, finalize_site, finalize_site_as_user, FinalizeOutcome
from omdlib.global_options import GlobalOptions
from omdlib.init_scripts import call_init_scripts, check_status
from omdlib.options import (
    Arguments,
    Command,
    CommandOptions,
    is_root,
    main_help,
    parse_args_or_exec_other_omd,
)
from omdlib.package_manager import PackageManager
from omdlib.restore import prepare_restore_as_root, prepare_restore_as_site_user
from omdlib.scripts import _call_script, call_scripts
from omdlib.site_name import site_name_from_uid, sitename_must_be_valid
from omdlib.site_paths import SitePaths
from omdlib.sites import all_sites, is_disabled, main_sites
from omdlib.skel_permissions import (
    get_skel_permissions,
    load_skel_permissions_from,
    Permissions,
    skel_permissions_file_path,
)
from omdlib.system_apache import (
    delete_apache_hook,
    register_with_system_apache,
    unregister_from_system_apache,
)
from omdlib.tmpfs import (
    add_to_fstab,
    fstab_verify,
    prepare_and_populate_tmpfs,
    remove_from_fstab,
    save_tmpfs_dump,
    tmpfs_mounted,
    unmount_tmpfs,
)
from omdlib.type_defs import Config, ConfigChoiceHasError, Replacements, Skeleton
from omdlib.update import get_conflict_mode_update, get_edition, ManageUpdate, PreFlight
from omdlib.update_check import check_update_possible, prepare_conflict_resolution
from omdlib.user_processes import kill_site_user_processes, terminate_site_user_processes
from omdlib.users_and_groups import (
    find_processes_of_user,
    group_exists,
    group_id,
    groupdel,
    switch_to_site_user,
    user_id,
    user_logged_in,
    user_verify,
    useradd,
    userdel,
)
from omdlib.utils import (
    chown_tree,
    create_skeleton_file,
    create_skeleton_files,
    delete_user_file,
    exec_other_omd,
    get_editor,
    is_containerized,
    replace_tags,
)
from omdlib.version import (
    default_version,
    main_version,
    main_versions,
    omd_versions,
    version_exists,
    version_from_site_dir,
)
from omdlib.version_info import VersionInfo

from cmk.ccc import tty
from cmk.ccc.archive import (
    ArchiveSettings,
    CheckmkTarArchive,
    SafeIndexedTarFile,
    SafeStreamedTarFile,
)
from cmk.ccc.exceptions import MKTerminate
from cmk.ccc.resulttype import Error, OK, Result
from cmk.ccc.version import (
    Edition,
    edition_has_enforced_licensing,
)
from cmk.crypto.password import Password
from cmk.crypto.password_hashing import hash_password

ConfigChangeCommands = list[tuple[str, str]]


class StateMarkers:
    good = " " + tty.green + tty.bold + "*" + tty.normal
    warn = " " + tty.bgyellow + tty.black + tty.bold + "!" + tty.normal
    error = " " + tty.bgred + tty.white + tty.bold + "!" + tty.normal


# Is used to duplicate output from stdout/stderr to a logfiles. This
# is e.g. used during "omd update" to have a chance to analyze errors
# during past updates
# TODO: Replace this with regular logging mechanics
class Log(io.StringIO):
    color_replace: Final = re.compile("\033\\[\\d{1,2}m", re.UNICODE)

    def __init__(self, logfile: TextIO, std_stream: TextIO) -> None:
        super().__init__()
        self._std_stream = std_stream
        self._logfile = logfile

    # TODO: Ensure we get Text here
    @override
    def write(self, data: str) -> int:
        text = data
        self._std_stream.write(text)
        self._logfile.write(self.color_replace.sub("", text))
        return len(text)

    @override
    def flush(self) -> None:
        self._logfile.flush()
        self._std_stream.flush()


@contextlib.contextmanager
def with_update_logging_stdout(logfile: Path) -> Iterator[None]:
    original = sys.stdout
    try:
        with open(logfile, "a") as file:
            sys.stdout = Log(logfile=file, std_stream=original)
            yield
    finally:
        sys.stdout = original


@contextlib.contextmanager
def with_update_logging_stderr(logfile: Path) -> Iterator[None]:
    original = sys.stderr
    try:
        with open(logfile, "a") as file:
            sys.stderr = Log(logfile=file, std_stream=original)
            yield
    finally:
        sys.stderr = original


# .
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


def start_site(version_info: VersionInfo, site: SiteContext, config: Config) -> None:
    skelroot = "/omd/versions/%s/skel" % omdlib.__version__
    site_home = SitePaths.from_site_name(site.name).home
    prepare_and_populate_tmpfs(
        config,
        version_info,
        site.name,
        site_home,
        site.tmp_dir,
        site.replacements(),
        site.skel_permissions,
        skelroot,
    )
    call_init_scripts(site_home, "start")


def get_file_permissions(path: str) -> int:
    try:
        return os.stat(path).st_mode & 0o7777
    except Exception:
        return 0


def get_file_owner(path: str) -> str | None:
    try:
        return pwd.getpwuid(os.stat(path).st_uid)[0]
    except Exception:
        return None


def create_version_symlink(site_home: str, version: str) -> None:
    linkname = site_home + "/version"
    if os.path.lexists(linkname):
        os.remove(linkname)
    os.symlink("../../versions/%s" % version, linkname)


def calculate_admin_password(options: CommandOptions) -> Password:
    if pw := options.get("admin-password"):
        return Password(pw)
    return Password.random(12)


def set_admin_password(site_home: str, pw: Password) -> None:
    """Write cmkadmin's password hash to htpasswd

    Raises PasswordTooLongError or ValueError if the password is too long or contains disallowed
    characters.
    """
    with open("%s/etc/htpasswd" % site_home, "w") as f:
        f.write("cmkadmin:%s\n" % hash_password(pw))


def save_version_meta_data(site: SiteContext, version: str) -> None:
    """Make meta information from the version available in the site directory

    the prurpose of this metadir is to be able to upgrade without the old
    version and the symlinks

    Currently it holds the following information
    A) A copy of the versions skel/ directory
    B) A copy of the skel.permissions file
    C) A version file containing the version number of the meta data
    """
    try:
        shutil.rmtree(site.version_meta_dir)
    except FileNotFoundError:
        pass

    skelroot = "/omd/versions/%s/skel" % version
    shutil.copytree(skelroot, "%s/skel" % site.version_meta_dir, symlinks=True)

    shutil.copy(skel_permissions_file_path(version), "%s/skel.permissions" % site.version_meta_dir)

    with open("%s/version" % site.version_meta_dir, "w") as f:
        f.write("%s\n" % version)


def try_chown(filename: str, user: str) -> None:
    if os.path.exists(filename):
        try:
            uid = pwd.getpwnam(user).pw_uid
            gid = pwd.getpwnam(user).pw_gid
            os.chown(filename, uid, gid)
        except Exception as e:
            sys.stderr.write(f"Cannot chown {filename} to {user}: {e}\n")


# Walks all files in the skeleton dir to execute a function for each file
#
# When called with a path in 'exclude_if_in' then paths existing relative to
# that are skipped. This is used for a second run during the update-process: to handle
# files that have vanished in the new version.
#
# The option 'relbase' is optional. It can contain a relative path which can be used
# as base for the walk instead of walking the whole tree.
def walk_skel(
    root: str,
    depth_first: bool,
    exclude_if_in: str | None = None,
    relbase: str = ".",
) -> Iterable[str]:
    # Files that should not be managed by the update process (anymore).
    ignored_files = [
        # We have removed the unused htpasswd skel file, but we don't want to ask users if they wish
        # to delete their existing htpasswd.
        "etc/htpasswd",
        "etc/diskspace.conf",
        "local/lib/python3/cmk/base/plugins/agent_based",
        "local/lib/python3/cmk/base/plugins",
        "local/lib/python3/cmk/base",
        "local/lib/python3/cmk/special_agents",
        "local/share/check_mk/agents/special",
        "local/share/check_mk/checkman",
        "local/share/check_mk/checks",
        "local/share/nagios",
        "local/share/nagios/htdocs",
        "local/share/nagios/htdocs/theme",
    ]

    with contextlib.chdir(root):
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

                if path in ignored_files:
                    continue

                yield path


# .
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
def patch_skeleton_files(
    conflict_mode: Skeleton,
    old_site_name: str,
    new_site: SiteContext,
    old_replacements: Replacements,
    new_replacements: Replacements,
) -> None:
    skelroot = "/omd/versions/%s/skel" % omdlib.__version__
    with contextlib.chdir(skelroot):  # make relative paths
        for dirpath, _dirnames, filenames in os.walk("."):
            if dirpath.startswith("./"):
                dirpath = dirpath[2:]
            new_site_home = SitePaths.from_site_name(new_site.name).home
            targetdir = new_site_home + "/" + dirpath
            if targetdir.startswith(new_site.tmp_dir):
                continue  # Skip files below tmp
            for fn in filenames:
                # Skip some not patchable files that can be found in our standard skel
                if _is_unpatchable_file(fn):
                    continue

                src = dirpath + "/" + fn
                dst = targetdir + "/" + fn
                if (
                    os.path.isfile(src) and not os.path.islink(src) and os.path.exists(dst)
                ):  # not deleted by user
                    try:
                        _patch_template_file(
                            conflict_mode,
                            src,
                            dst,
                            old_site_name,
                            new_site,
                            old_replacements,
                            new_replacements,
                        )
                    except MKTerminate:
                        raise
                    except Exception as e:
                        sys.stderr.write(f"Error patching template file '{dst}': {e}\n")


def _is_unpatchable_file(path: str) -> bool:
    return path.endswith(".png") or path.endswith(".pdf")


def _patch_template_file(
    conflict_mode: Skeleton,
    src: str,
    dst: str,
    old_site_name: str,
    new_site: SiteContext,
    old_replacements: Replacements,
    new_replacements: Replacements,
) -> None:
    # Create patch from old instantiated skeleton file to new one
    content = Path(src).read_bytes()
    filename = Path(f"{dst}.skel.{new_site.name}")
    filename.write_bytes(replace_tags(content, new_replacements))
    try_chown(str(filename), new_site.name)
    filename = Path(f"{dst}.skel.{old_site_name}")
    filename.write_bytes(replace_tags(content, old_replacements))
    try_chown(str(filename), new_site.name)

    # If old and new skeleton file are identical, then do nothing
    old_orig_path = Path(f"{dst}.skel.{old_site_name}")
    new_orig_path = Path(f"{dst}.skel.{new_site.name}")
    if old_orig_path.read_text() == new_orig_path.read_text():
        old_orig_path.unlink()
        new_orig_path.unlink()
        return

    # Now create a patch from old to new and immediately apply on
    # existing - possibly user modified - file.

    new_site_home = SitePaths.from_site_name(new_site.name).home
    result = os.system(  # nosec B605 # BNS:2b5952
        f"diff -u {old_orig_path} {new_orig_path} | {new_site_home}/bin/patch --force --backup --forward --silent {dst}"
    )

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
            (
                "brute",
                f"Simply replace /{old_site_name}/ with /{new_site.name}/ in that file",
            ),
            ("shell", "Open a shell for looking around"),
            ("abort", "Stop here and abort!"),
        ]

        while True:
            match conflict_mode:
                case Skeleton.ABORT:
                    choice = "abort"
                case Skeleton.INSTALL:
                    choice = "install"
                case Skeleton.KEEPOLD:
                    choice = "restore"
                case Skeleton.ASK:
                    choice = ask_user_choices(
                        "Conflicts in " + src + "!",
                        "I've tried to merge your changes with the renaming of %s into %s.\n"
                        "Unfortunately there are conflicts with your changes. \n"
                        "You have the following options: " % (old_site_name, new_site.name),
                        options,
                    )
                case mode:
                    assert_never(mode)

            if choice == "abort":
                sys.exit("Renaming aborted.")
            elif choice == "keep":
                break
            elif choice == "edit":
                with subprocess.Popen(
                    [get_editor(), dst],
                ):
                    pass
            elif choice == "diff":
                os.system(f"diff -u {old_orig_path} {new_orig_path}{pipe_pager()}")  # nosec B605 # BNS:2b5952
            elif choice == "brute":
                os.system(  # nosec B605 # BNS:2b5952
                    f"sed 's@/{old_site_name}/@/{new_site.name}/@g' {dst}.orig > {dst}"
                )
                changed = len(
                    [
                        l
                        for l in os.popen(f"diff {dst}.orig {dst}").readlines()  # nosec B605 # BNS:2b5952
                        if l.startswith(">")
                    ]
                )
                if changed == 0:
                    sys.stdout.write("Found no matching line.\n")
                else:
                    sys.stdout.write(
                        "Did brute-force replace, changed %s%d%s lines:\n"
                        % (tty.bold, changed, tty.normal)
                    )
                    with subprocess.Popen(["diff", "-u", dst + ".orig", dst]):
                        pass
                    break
            elif choice == "you":
                os.system(f"pwd ; diff -u {old_orig_path} {dst}.orig{pipe_pager()}")  # nosec B605 # BNS:2b5952
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
                sys.stdout.write(
                    " %-35s default version with the old site name\n"
                    % (relname + ".skel.%s" % old_site_name)
                )
                sys.stdout.write(
                    " %-35s default version with the new site name\n"
                    % (relname + ".skel.%s" % new_site.name)
                )

                sys.stdout.write("\n Starting BASH. Type CTRL-D to continue.\n\n")
                thedir = "/".join(dst.split("/")[:-1])
                os.system(f"su - {new_site.name} -c 'cd {thedir} ; bash -i'")  # nosec B605 # BNS:2b5952
    # remove unnecessary files
    try:
        os.remove(dst + ".skel." + old_site_name)
        os.remove(dst + ".skel." + new_site.name)
        os.remove(dst + ".orig")
        os.remove(dst + ".rej")
    except Exception:
        pass


# Try to merge changes from old->new version and
# old->user version
def merge_update_file(
    site: SiteContext,
    conflict_mode: Skeleton,
    relpath: str,
    old_version: str,
    new_version: str,
    old_replacements: Replacements,
    new_replacements: Replacements,
) -> None:
    fn = tty.bold + relpath + tty.normal

    site_home = SitePaths.from_site_name(site.name).home
    user_path = Path(site_home, relpath)
    permissions = user_path.stat().st_mode

    if (
        _try_merge(
            site,
            conflict_mode,
            relpath,
            old_version,
            new_version,
            old_replacements,
            new_replacements,
        )
        == 0
    ):
        # ACHTUNG: Hier müssen die Dateien $DATEI-alt, $DATEI-neu und $DATEI.orig
        # gelöscht werden
        sys.stdout.write(StateMarkers.good + " Merged         %s\n" % fn)
        return

    # No success. Should we try merging the users' changes onto the new file?
    # user_patch = os.popen(
    merge_message = " (watch out for >>>>> and <<<<<)"
    editor = get_editor()
    reject_file = Path(f"{user_path}.rej")

    options = [
        ("diff", "Show differences between the new default and your version"),
        ("you", "Show your changes compared with the old default version"),
        ("new", f"Show what has changed from {old_version} to {new_version}"),
    ]
    if reject_file.exists():  # missing if patch has --merge
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
        match conflict_mode:
            case Skeleton.ABORT:
                choice = "abort"
            case Skeleton.INSTALL:
                choice = "install"
            case Skeleton.KEEPOLD:
                choice = "restore"
            case Skeleton.ASK:
                choice = ask_user_choices(
                    "Conflicts in " + relpath + "!",
                    "I've tried to merge the changes from version %s to %s into %s.\n"
                    "Unfortunately there are conflicts with your changes. \n"
                    "You have the following options: " % (old_version, new_version, relpath),
                    options,
                )
            case mode:
                assert_never(mode)

        if choice == "abort":
            raise MKTerminate("Update aborted.")
        if choice == "keep":
            break
        if choice == "edit":
            with subprocess.Popen([editor, user_path]):
                pass
        elif choice == "diff":
            os.system(f"diff -u {user_path}.orig {user_path}-{new_version}{pipe_pager()}")  # nosec B605 # BNS:2b5952
        elif choice == "you":
            os.system(f"diff -u {user_path}-{old_version} {user_path}.orig{pipe_pager()}")  # nosec B605 # BNS:2b5952
        elif choice == "new":
            os.system(  # nosec B605 # BNS:2b5952
                f"diff -u {user_path}-{old_version} {user_path}-{new_version}{pipe_pager()}"
            )
        elif choice == "missing":
            if reject_file.exists():
                sys.stdout.write(tty.bgblue + tty.white + reject_file.read_text() + tty.normal)
            else:
                sys.stdout.write("File %s not found.\n" % reject_file)

        elif choice == "shell":
            relname = relpath.split("/")[-1]
            sys.stdout.write(" %-25s: the current half-merged file\n" % relname)
            sys.stdout.write(
                " %-25s: the default version of %s\n" % (relname + "." + old_version, old_version)
            )
            sys.stdout.write(
                " %-25s: the default version of %s\n" % (relname + "." + new_version, new_version)
            )
            sys.stdout.write(" %-25s: your original version\n" % (relname + ".orig"))
            if reject_file.exists():
                sys.stdout.write(" %-25s: changes that haven't been merged\n" % relname + ".rej")

            sys.stdout.write("\n Starting BASH. Type CTRL-D to continue.\n\n")
            os.system("cd '%s' ; bash -i" % user_path.parent)  # nosec B605 # BNS:2b5952
        elif choice == "restore":
            Path(f"{user_path}.orig").rename(user_path)
            user_path.chmod(permissions)
            sys.stdout.write("Restored your version.\n")
            break
        elif choice == "try again":
            Path(f"{user_path}.orig").rename(user_path)
            with subprocess.Popen([editor, user_path]):
                pass
            if (
                _try_merge(
                    site,
                    conflict_mode,
                    relpath,
                    old_version,
                    new_version,
                    old_replacements,
                    new_replacements,
                )
                == 0
            ):
                sys.stdout.write(
                    f"Successfully merged changes from {old_version} -> {new_version} into {fn}\n"
                )
                return
            sys.stdout.write(" Merge failed again.\n")

        else:  # install
            Path(f"{user_path}-{new_version}").rename(user_path)
            user_path.chmod(permissions)
            sys.stdout.write("Installed default file of version %s.\n" % new_version)
            break

    # Clean up temporary files
    for p in [
        f"{user_path}-{old_version}",
        f"{user_path}-{new_version}",
        "%s.orig" % user_path,
        "%s.rej" % user_path,
    ]:
        try:
            os.remove(p)
        except Exception:
            pass


def _read_skel_content(
    *,
    version: str,
    site_home: str,
    skel_path: Path,
    relpath: str,
    conflict_mode: Skeleton,
) -> bytes:
    while True:
        try:
            return skel_path.read_bytes()
        except Exception:
            # Do not ask the user in non-interactive mode.
            if conflict_mode in [Skeleton.ABORT, Skeleton.INSTALL]:
                sys.exit(f"Skeleton file '{skel_path}' of version {version} not readable.")
            elif conflict_mode == Skeleton.KEEPOLD or not user_confirms(
                site_home,
                conflict_mode,
                "Skeleton file of version %s not readable" % version,
                "The file '%s' is not readable for the site user. "
                "This is most probably due a bug in release 0.42. "
                "You can either fix that problem by making the file "
                "readable with doing as root: chmod +r '%s' "
                "or assume the file as empty. In that case you might "
                "damage your configuration file "
                "in case you have made changes to it in your site. What shall we do?"
                % (skel_path, skel_path),
                relpath,
                "retry",
                "Retry reading the file (after you've fixed it)",
                "ignore",
                "Assume the file to be empty",
            ):
                return b""


def _try_merge(
    site: SiteContext,
    conflict_mode: Skeleton,
    relpath: str,
    old_version: str,
    new_version: str,
    old_replacements: Replacements,
    new_replacements: Replacements,
) -> int:
    site_home = SitePaths.from_site_name(site.name).home
    user_path = Path(site_home, relpath)

    for version, skelroot, replacements in [
        (old_version, site.version_skel_dir, old_replacements),
        (new_version, "/omd/versions/%s/skel" % new_version, new_replacements),
    ]:
        skel_content = _read_skel_content(
            version=version,
            site_home=site_home,
            skel_path=Path(skelroot, relpath),
            relpath=relpath,
            conflict_mode=conflict_mode,
        )
        Path(f"{user_path}-{version}").write_bytes(replace_tags(skel_content, replacements))
    version_patch = os.popen(  # nosec B605 # BNS:2b5952
        f"diff -u {user_path}-{old_version} {user_path}-{new_version}"
    ).read()

    # First try to merge the changes in the version into the users' file
    f = os.popen(  # nosec B605 # BNS:2b5952
        f"{site_home}/bin/patch --force --backup --forward --silent --merge {user_path} >/dev/null",
        "w",
    )
    f.write(version_patch)
    status = f.close()
    if status:
        return status // 256
    return 0


# Compares two files and returns infos wether the file type or contants have changed """
def file_status(
    source_path: str,
    source_replacements: Replacements,
    target_path: str,
    target_replacements: Replacements,
) -> tuple[bool, bool, bool]:
    source_type = filetype(source_path)
    target_type = filetype(target_path)

    if source_type == "file" and target_type == "file":
        changed_content = file_contents(source_path, source_replacements) != file_contents(
            target_path, target_replacements
        )
    else:
        # FIXME: Was ist, wenn aus einer Datei ein Link gemacht wurde? Oder umgekehrt?
        changed_content = (
            source_type == "link"
            and target_type == "link"
            and os.readlink(source_path) != os.readlink(target_path)
        )

    changed_type = source_type != target_type
    changed = changed_type or changed_content

    return (changed_type, changed_content, changed)


def _execute_update_file(
    relpath: str,
    site: SiteContext,
    conflict_mode: Skeleton,
    old_version: str,
    new_version: str,
    old_edition: str,
    new_edition: str,
    old_permissions: Permissions,
    new_permissions: Permissions,
) -> None:
    todo = True
    while todo:
        try:
            update_file(
                relpath,
                site,
                conflict_mode,
                old_version,
                new_version,
                old_edition,
                new_edition,
                old_permissions,
                new_permissions,
            )
            todo = False
        except MKTerminate:
            raise
        except Exception:
            todo = False
            sys.stderr.write(StateMarkers.error * 40 + "\n")
            sys.stderr.write(StateMarkers.error + " Exception      %s\n" % (relpath))
            sys.stderr.write(
                StateMarkers.error
                + " "
                + traceback.format_exc().replace("\n", "\n" + StateMarkers.error + " ")
                + "\n"
            )
            sys.stderr.write(StateMarkers.error * 40 + "\n")

            # If running in interactive mode ask the user to terminate or retry
            # In case of non interactive mode just throw the exception
            if conflict_mode == Skeleton.ASK:
                options = [
                    ("retry", "Retry the operation"),
                    ("continue", "Continue with next files"),
                    ("abort", "Stop here and abort update!"),
                ]
                choice = ask_user_choices(
                    "Problem occurred",
                    "We detected an exception (printed above). You have the "
                    "chance to fix things and retry the operation now.",
                    options,
                )
                if choice == "abort":
                    raise MKTerminate("Update aborted.")
                if choice == "retry":
                    todo = True  # Try again


def update_file(
    relpath: str,
    site: SiteContext,
    conflict_mode: Skeleton,
    old_version: str,
    new_version: str,
    old_edition: str,
    new_edition: str,
    old_permissions: Permissions,
    new_permissions: Permissions,
) -> None:
    old_skel = site.version_skel_dir
    new_skel = "/omd/versions/%s/skel" % new_version

    site_home = SitePaths.from_site_name(site.name).home
    new_replacements = {
        "###SITE###": site.name,
        "###ROOT###": site_home,
        # When calling this during "omd update", the site.version and site.edition still point to
        # the original edition, because we are still in the update prcedure and the version symlink
        # has not been changed yet.
        "###EDITION###": new_edition,
    }

    old_replacements = {
        "###SITE###": site.name,
        "###ROOT###": site_home,
        "###EDITION###": old_edition,
    }

    old_path = old_skel + "/" + relpath
    new_path = new_skel + "/" + relpath
    user_path = site_home + "/" + relpath

    old_type = filetype(old_path)
    new_type = filetype(new_path)
    user_type = filetype(user_path)

    # compare our new version with the user's version
    _type_differs, _content_differs, differs = file_status(
        user_path, new_replacements, new_path, new_replacements
    )

    # compare our old version with the user's version
    user_changed_type, user_changed_content, user_changed = file_status(
        old_path, old_replacements, user_path, old_replacements
    )

    # compare our old with our new version
    _we_changed_type, _we_changed_content, we_changed = file_status(
        old_path, old_replacements, new_path, new_replacements
    )

    non_empty_directory = (
        not os.path.islink(user_path) and os.path.isdir(user_path) and bool(os.listdir(user_path))
    )

    # A --> MISSING FILES

    # Handle cases with missing files first. At least old or new are present,
    # or this function would never have been invoked.
    fn = tty.bold + tty.bgblue + tty.white + relpath + tty.normal
    fn = tty.bold + relpath + tty.normal

    # 1) New version ships new skeleton file -> simply install
    if not old_type and not user_type:
        create_skeleton_file(new_skel, site_home, relpath, new_replacements, new_permissions)
        sys.stdout.write(StateMarkers.good + " Installed %-4s %s\n" % (new_type, fn))

    # 2) new version ships new skeleton file, but user's own file/directory/link
    #    is in the way.
    # 2a) the users file is identical with our new version
    elif not old_type and not differs:
        sys.stdout.write(StateMarkers.good + " Identical new  %s\n" % fn)

    # 2b) user's file has a different content or type
    elif not old_type:
        if user_confirms(
            site_home,
            conflict_mode,
            "Conflict at " + relpath,
            "The new version ships the %s %s, "
            "but you have created a %s in that place "
            "yourself. Shall we keep your %s or replace "
            "is with my %s?" % (new_type, relpath, user_type, user_type, new_type),
            relpath,
            "keep",
            "Keep your %s" % user_type,
            "replace",
            f"Replace your {user_type} with the new default {new_type}",
        ):
            sys.stdout.write(StateMarkers.warn + " Keeping your   %s\n" % fn)
        else:
            create_skeleton_file(new_skel, site_home, relpath, new_replacements, new_permissions)
            sys.stdout.write(StateMarkers.good + " Installed %-4s %s\n" % (new_type, fn))

    # 3) old version had a file which has vanished in new (got obsolete). If the user
    #    has deleted it himself, we are just happy
    elif not new_type and not user_type:
        sys.stdout.write(StateMarkers.good + " Obsolete       %s\n" % fn)

    # 3b) same, but user has not deleted and changed type
    elif not new_type and user_changed_type:
        if user_confirms(
            site_home,
            conflict_mode,
            "Obsolete file " + relpath,
            "The %s %s has become obsolete in "
            "this version, but you have changed it into a "
            "%s. Do you want to keep your %s or "
            "may I remove it for you, please?" % (old_type, relpath, user_type, user_type),
            relpath,
            "keep",
            "Keep your %s" % user_type,
            "remove",
            "Remove it",
        ):
            sys.stdout.write(StateMarkers.warn + " Keeping your   %s\n" % fn)
        else:
            delete_user_file(user_path)
            sys.stdout.write(StateMarkers.warn + " Removed        %s\n" % fn)

    # 3c) same, but user has changed it contents
    elif not new_type and user_changed_content:
        if user_confirms(
            site_home,
            conflict_mode,
            f"Changes in obsolete {old_type} {relpath}",
            "The %s %s has become obsolete in "
            "the new version, but you have changed its contents. "
            "Do you want to keep your %s or "
            "may I remove it for you, please?" % (old_type, relpath, user_type),
            relpath,
            "keep",
            "keep your %s, though it is obsolete" % user_type,
            "remove",
            "remove your %s" % user_type,
        ):
            sys.stdout.write(StateMarkers.warn + " Keeping your   %s\n" % fn)
        else:
            delete_user_file(user_path)
            sys.stdout.write(StateMarkers.warn + " Removed        %s\n" % fn)

    # 3d) same, but it is a directory which is not empty
    elif not new_type and non_empty_directory:
        if user_confirms(
            site_home,
            conflict_mode,
            "Non empty obsolete directory %s" % (relpath),
            "The directory %s has become obsolete in "
            "the new version, but you have contents in it. "
            "Do you want to keep your directory or "
            "may I remove it for you, please?" % (relpath),
            relpath,
            "keep",
            "keep your directory, though it is obsolete",
            "remove",
            "remove your directory",
        ):
            sys.stdout.write(StateMarkers.warn + " Keeping your   %s\n" % fn)
        else:
            delete_user_file(user_path)
            sys.stdout.write(StateMarkers.warn + " Removed        %s\n" % fn)

    # 3e) same, but user hasn't changed anything -> silently delete
    elif not new_type:
        delete_user_file(user_path)
        sys.stdout.write(StateMarkers.good + " Vanished       %s\n" % fn)

    # 4) old and new exist, but user file not. User has deleted that
    #    file. We simply do nothing in that case. The user surely has
    #    a good reason why he deleted the file.
    elif not user_type and not we_changed:
        sys.stdout.write(
            StateMarkers.good + " Unwanted       %s (unchanged, removed by you)\n" % fn
        )

    # 4b) File changed in new version. Simply warn if user has deleted it.
    elif not user_type:
        sys.stdout.write(StateMarkers.warn + " Missing        %s\n" % fn)

    # B ---> UNCHANGED, EASY CASES

    # 5) New version didn't change anything -> no need to update
    elif not we_changed:
        pass

    # 6) User didn't change anything -> take over new version
    elif not user_changed:
        create_skeleton_file(new_skel, site_home, relpath, new_replacements, new_permissions)
        sys.stdout.write(StateMarkers.good + " Updated        %s\n" % fn)

    # 7) User changed, but accidentally exactly as we did -> no action necessary
    elif not differs:
        sys.stdout.write(StateMarkers.good + " Identical      %s\n" % fn)

    # TEST UNTIL HERE

    # C ---> PATCH DAY, HANDLE FILES
    # 7) old, new and user are files. And all are different
    elif old_type == "file" and new_type == "file" and user_type == "file":
        try:
            merge_update_file(
                site,
                conflict_mode,
                relpath,
                old_version,
                new_version,
                old_replacements,
                new_replacements,
            )
        except KeyboardInterrupt:
            raise
        except MKTerminate:
            raise
        except Exception as e:
            sys.stdout.write(StateMarkers.error + " Cannot merge: %s\n" % e)

    # D ---> SYMLINKS
    # 8) all are symlinks, all changed
    elif old_type == "link" and new_type == "link" and user_type == "link":
        if user_confirms(
            site_home,
            conflict_mode,
            "Symbolic link conflict at " + relpath,
            "'%s' is a symlink that pointed to "
            "%s in the old version and to "
            "%s in the new version. But meanwhile you "
            "changed to link target to %s. "
            "Shall I keep your link or replace it with "
            "the new default target?"
            % (relpath, os.readlink(old_path), os.readlink(new_path), os.readlink(user_path)),
            relpath,
            "keep",
            "Keep your symbolic link pointing to %s" % os.readlink(user_path),
            "replace",
            "Change link target to %s" % os.readlink(new_path),
        ):
            sys.stdout.write(StateMarkers.warn + " Keeping your   %s\n" % fn)
        else:
            os.remove(user_path)
            os.symlink(os.readlink(new_path), user_path)
            sys.stdout.write(
                StateMarkers.warn + f" Set link       {fn} to new target {os.readlink(new_path)}\n"
            )

    # E ---> FILE TYPE HAS CHANGED (NASTY)

    # Now we have to handle cases, where the file types of the three
    # versions are not identical and at the same type the user or
    # have changed the third file to. We cannot merge here, the user
    # has to decide wether to keep his version of use ours.

    # 9) We have changed the file type
    elif old_type != new_type:
        if user_confirms(
            site_home,
            conflict_mode,
            "File type change at " + relpath,
            "The %s %s has been changed into a %s in "
            "the new version. Meanwhile you have changed "
            "the %s of your copy of that %s. "
            "Do you want to keep your version or replace "
            "it with the new default? "
            % (old_type, relpath, new_type, user_changed_type and "type" or "content", old_type),
            relpath,
            "keep",
            "Keep your %s" % user_type,
            "replace",
            "Replace it with the new %s" % new_type,
        ):
            sys.stdout.write(StateMarkers.warn + " Keeping your version of %s\n" % fn)
        else:
            create_skeleton_file(new_skel, site_home, relpath, new_replacements, new_permissions)
            sys.stdout.write(
                StateMarkers.warn
                + f" Replaced your {user_type} {relpath} by new default {new_type}.\n"
            )

    # 10) The user has changed the file type, we just the content
    elif old_type != user_type:
        if user_confirms(
            site_home,
            conflict_mode,
            "Type change conflicts with content change at " + relpath,
            "Usually %s is a %s in both the "
            "old and new version. But you have changed it "
            "into a %s. Do you want to keep that or may "
            "I replace your %s with the new default "
            "%s, please?" % (relpath, old_type, user_type, user_type, new_type),
            relpath,
            "keep",
            "Keep your %s" % user_type,
            "replace",
            "Replace it with the new %s" % new_type,
        ):
            sys.stdout.write(StateMarkers.warn + f" Keeping your {user_type} {fn}.\n")
        else:
            create_skeleton_file(new_skel, site_home, relpath, new_replacements, new_permissions)
            sys.stdout.write(
                StateMarkers.warn
                + f" Delete your {user_type} and created new default {new_type} {fn}.\n"
            )

    # 11) This case should never happen, if I've not lost something
    elif user_confirms(
        site_home,
        conflict_mode,
        "Something nasty happened at " + relpath,
        "You somehow fiddled along with "
        "%s, and I do not have the "
        "slightest idea what's going on here. May "
        "I please install the new default %s "
        "here, or do you want to keep your %s?" % (relpath, new_type, user_type),
        relpath,
        "keep",
        "Keep your %s" % user_type,
        "replace",
        "Replace it with the new %s" % new_type,
    ):
        sys.stdout.write(StateMarkers.warn + f" Keeping your {user_type} {fn}.\n")
    else:
        create_skeleton_file(new_skel, site_home, relpath, new_replacements, new_permissions)
        sys.stdout.write(
            StateMarkers.warn
            + f" Delete your {user_type} and created new default {new_type} {fn}.\n"
        )

    # Now the new file/link/directory is in place, deleted or whatever. The
    # user might have interferred and changed things. We need to make sure
    # that file permissions are also updated. But the user might have changed
    # something himself.

    user_type = filetype(user_path)
    old_perm = get_skel_permissions(old_skel, old_permissions, relpath)
    new_perm = get_skel_permissions(new_skel, new_permissions, relpath)
    user_perm = get_file_permissions(user_path)

    # Fix permissions not for links and only if the new type is as expected
    # and the current permissions are not as they should be
    what = permission_action(
        site_home=site_home,
        conflict_mode=conflict_mode,
        relpath=relpath,
        old_type=old_type,
        new_type=new_type,
        user_type=user_type,
        old_perm=old_perm,
        new_perm=new_perm,
        user_perm=user_perm,
    )

    if what == "keep":
        sys.stdout.write(StateMarkers.warn + f" Permissions    {user_perm:04o} {fn} (unchanged)\n")
    elif what == "default":
        try:
            os.chmod(user_path, new_perm)
            sys.stdout.write(
                StateMarkers.good + f" Permissions    {user_perm:04o} -> {new_perm:04o} {fn}\n"
            )
        except Exception as e:
            sys.stdout.write(
                StateMarkers.error
                + f" Permission:    cannot change {user_perm:04o} -> {new_perm:04o} {fn}: {e}\n"
            )


def permission_action(
    *,
    site_home: str,
    conflict_mode: Skeleton,
    relpath: str,
    old_type: str | None,
    new_type: str | None,
    user_type: str | None,
    old_perm: int,
    new_perm: int,
    user_perm: int,
) -> str | None:
    if new_type == "link":
        return None  # Do not touch symlinks

    if user_type is None:
        return None  # Don't change permissions of non existant paths

    if user_type != new_type:
        return None  # Do not touch when type changed by the user

    if user_perm == new_perm:
        return None  # Is already in correct state

    if old_type is None:
        return "default"  # New file, set permissions

    # Special handling to prevent questions about standard situations (CMK-12090)
    if old_perm != new_perm and relpath in (
        "local/share/nagvis/htdocs/userfiles/images/maps",
        "local/share/nagvis/htdocs/userfiles/images/shapes",
        "etc/check_mk/multisite.d",
        "etc/check_mk/conf.d",
        "etc/check_mk/conf.d/wato",
        "etc/ssl/private",
        "etc/ssl/certs",
    ):
        return "default"

    # Permissions have changed in all places, but file type not
    if old_type == new_type and old_perm not in {user_perm, new_perm}:
        if user_confirms(
            site_home,
            conflict_mode,
            "Permission conflict at " + relpath,
            "The proposed permissions of %s have changed from %04o "
            "to %04o in the new version, but you have set %04o. "
            "May I use the new default permissions or do "
            "you want to keep yours?" % (relpath, old_perm, new_perm, user_perm),
            relpath,
            "keep",
            "Keep permissions at %04o" % user_perm,
            "default",
            "Set permission to %04o" % new_perm,
        ):
            return "keep"
        return "default"

    # Permissions have changed, no conflict with user
    if old_type == new_type and user_perm == old_perm:
        return "default"

    # Permissions are not correct: all other cases (where type is as expected)
    if old_perm != new_perm:
        if old_perm == user_perm:
            # The skel permissions are changed but the old skel permissions
            # are still in place. In 2.2 the permissions for other were
            # removed (Werk #15062). This results in a lot of questions for
            # the user. If the user has not adjusted the permissions from
            # the previous default, let's not ask so much questions, just
            # adjust it, a info that the permissions were adjusted will be
            # logged anyways
            return "default"

        if user_confirms(
            site_home,
            conflict_mode,
            "Wrong permission of " + relpath,
            "The proposed permissions of %s are %04o, but currently are "
            "%04o. May I use the new default "
            "permissions or keep yours?" % (relpath, new_perm, user_perm),
            relpath,
            "keep",
            "Keep permissions at %04o" % user_perm,
            "default",
            "Set permission to %04o" % new_perm,
        ):
            return "keep"
        return "default"

    return None


def filetype(p: str) -> str | None:
    # check for symlinks first. Might be dangling. In that
    # case os.path.exists checks the links target for existance
    # and reports it is non-existing.
    if os.path.islink(p):
        return "link"
    if not os.path.exists(p):
        return None
    if os.path.isdir(p):
        return "dir"
    return "file"


def file_contents(path: str, replacements: Replacements) -> bytes:
    """Returns the file contents of a site file or a skel file"""
    if "/skel/" in path and not _is_unpatchable_file(path):
        return _instantiate_skel(path, replacements)

    with open(path, "rb") as f:
        return f.read()


def _instantiate_skel(path: str, replacements: Replacements) -> bytes:
    try:
        with open(path, "rb") as f:
            return replace_tags(f.read(), replacements)
    except Exception:
        # TODO: This is a bad exception handler. Drop it
        return b""  # e.g. due to permission error


def config_change(
    version_info: VersionInfo,
    site: SiteContext,
    config: Config,
    config_hooks: ConfigHooks,
    verbose: bool,
) -> list[str]:
    # Check whether or not site needs to be stopped. Stop and remember to start again later
    site_was_stopped = False
    site_home = SitePaths.from_site_name(site.name).home
    if not site.is_stopped(verbose):
        site_was_stopped = True
        call_init_scripts(site_home, "stop")

    try:
        settings = read_config_change_commands()

        if not settings:
            sys.exit("You need to provide config change commands via stdin: KEY=value\n")

        validate_config_change_commands(config_hooks, settings)

        changed: list[str] = []
        for key, value in settings:
            config_set_value(site, site_home, config, key, value, verbose, save=False)
            changed.append(key)

        save_site_conf(site_home, config)
        return changed
    finally:
        if site_was_stopped:
            start_site(version_info, site, config)


def read_config_change_commands() -> ConfigChangeCommands:
    settings = []
    for l in sys.stdin:
        line = l.strip()
        if not line:
            continue

        try:
            key, value = line.split("=", 1)
            settings.append((key, value))
        except ValueError:
            sys.exit("Invalid config change command: %r" % line)
    return settings


def validate_config_change_commands(
    config_hooks: ConfigHooks, settings: ConfigChangeCommands
) -> None:
    # Validate the provided commands
    for key, value in settings:
        hook = config_hooks.get(key)
        if not hook:
            sys.exit("Invalid config option: %r" % key)

        error_from_config_choice = _error_from_config_choice(hook.choices, value)
        if error_from_config_choice.is_error():
            sys.exit(f"Invalid value for '{value} for {key}'. {error_from_config_choice.error}\n")


def config_set(
    site: SiteContext,
    site_home: str,
    config: Config,
    config_hooks: ConfigHooks,
    args: Arguments,
    verbose: bool,
) -> list[str]:
    if len(args) != 2:
        sys.stderr.write("Please specify variable name and value\n")
        config_usage()
        return []

    if not site.is_stopped(verbose):
        sys.stderr.write("Cannot change config variables while site is running.\n")
        return []

    hook_name = args[0]
    value = args[1]
    hook = config_hooks.get(hook_name)
    if not hook:
        sys.stderr.write("No such variable '%s'\n" % hook_name)
        return []

    error_from_config_choice = _error_from_config_choice(hook.choices, value)
    if error_from_config_choice.is_error():
        sys.stderr.write(f"Invalid value for '{value}'. {error_from_config_choice.error}\n")
        return []

    config_set_value(site, site_home, config, hook_name, value, verbose)
    return [hook_name]


def _error_from_config_choice(choices: ConfigHookChoices, value: str) -> Result[None, str]:
    # Check if value is valid. Choices are either a list of allowed keys or a
    # regular expression
    if isinstance(choices, list):
        if all(value != var for var, _descr in choices):
            return Error("Allowed are: " + ", ".join(var for var, _ in choices))
    elif isinstance(choices, re.Pattern):
        if not choices.match(value):
            return Error("Does not match allowed pattern.")
    elif isinstance(choices, ConfigChoiceHasError):
        return choices(value)
    else:
        assert_never(choices)
    return OK(None)


def config_usage() -> None:
    sys.stdout.write(
        """Usage of config command:

omd config               - interactive configuration menu
omd config show          - show current settings of all configuration variables
omd config show VAR      - show current setting of variable VAR
omd config set VAR VALUE - set VAR to VALUE
omd config change        - change multiple at once. Provide newline separated
                           KEY=value pairs via stdin. The site is restarted
                           automatically once in case it's currently runnig.
"""
    )


def config_show(config: Config, config_hooks: ConfigHooks, args: Arguments) -> None:
    hook: ConfigHook | None
    if len(args) == 0:
        hook_names = sorted(config_hooks.keys())
        for hook_name in hook_names:
            hook = config_hooks[hook_name]
            if hook.unstructured["active"] and not hook.unstructured["deprecated"]:
                sys.stdout.write(f"{hook_name}: {config[hook_name]}\n")
    else:
        output = []
        for hook_name in args:
            hook = config_hooks.get(hook_name)
            if not hook:
                sys.stderr.write("No such variable %s\n" % hook_name)
            else:
                output.append(config[hook_name])

        sys.stdout.write(" ".join(output))
        sys.stdout.write("\n")


def config_configure(
    site: SiteContext, config: Config, config_hooks: ConfigHooks, verbose: bool
) -> Iterator[str]:
    hook_names = sorted(config_hooks.keys())
    current_hook_name: str | None = ""
    menu_open = False
    current_menu = "Basic"

    # force certain order in main menu
    menu_choices = ["Basic", "Web GUI", "Add-ons", "Distributed Monitoring"]

    while True:
        # Rebuild hook information (values possible changed)
        menu: dict[str, list[tuple[str, str]]] = {}
        for hook_name in hook_names:
            hook = config_hooks[hook_name]
            if hook.unstructured["active"] and not hook.unstructured["deprecated"]:
                mp = hook.menu
                entries = menu.get(mp, [])
                entries.append((hook_name, config[hook_name]))
                menu[mp] = entries
                if mp not in menu_choices:
                    menu_choices.append(mp)

        # Handle main menu
        if not menu_open:
            change, current_menu = dialog_menu(
                "Configuration of site %s" % site.name,
                "Interactive setting of site configuration variables. You "
                "can change values only while the site is stopped.",
                [(e, "") for e in menu_choices],
                current_menu,
                "Enter",
                "Exit",
            )
            if not change:
                return
            current_hook_name = None
            menu_open = True

        else:
            change, current_hook_name = dialog_menu(
                current_menu, "", menu[current_menu], current_hook_name, "Change", "Main menu"
            )
            if change:
                try:
                    yield from config_configure_hook(
                        site, config, config_hooks, current_hook_name, verbose
                    )
                except MKTerminate:
                    raise
                except Exception as e:
                    sys.exit(f"Error in hook {current_hook_name}: {e}")
            else:
                menu_open = False


def config_configure_hook(
    site: SiteContext, config: Config, config_hooks: ConfigHooks, hook_name: str, verbose: bool
) -> Iterator[str]:
    site_home = SitePaths.from_site_name(site.name).home
    if not site.is_stopped(verbose):
        if not dialog_yesno(
            "You cannot change configuration value while the "
            "site is running. Do you want me to stop the site now?"
        ):
            return
        call_init_scripts(site_home, "stop")
        dialog_message("The site has been stopped.")

    hook = config_hooks[hook_name]
    title = hook.alias
    descr = hook.description.replace("\n\n", "\001").replace("\n", " ").replace("\001", "\n\n")
    value = config[hook_name]
    choices = hook.choices

    if isinstance(choices, list):
        change, new_value = dialog_menu(title, descr, choices, value, "Change", "Cancel")
    elif isinstance(choices, re.Pattern):
        change, new_value = dialog_regex(title, descr, choices, value, "Change", "Cancel")
    elif isinstance(choices, ConfigChoiceHasError):
        change, new_value = dialog_config_choice_has_error(
            title, descr, choices, value, "Change", "Cancel"
        )
    else:
        assert_never(choices)

    if change:
        config_set_value(site, site_home, config, hook.name, new_value, verbose)
        save_site_conf(site_home, config)
        config_hooks = load_hook_dependencies(site, config_hooks, verbose)
        yield hook_name


def init_action(
    version_info: VersionInfo,
    site: SiteContext,
    config: Config,
    global_opts: GlobalOptions,
    command: Literal["start", "stop", "reload", "restart", "status"],
    args: Arguments,
    options: CommandOptions,
) -> int:
    site_paths = SitePaths.from_site_name(site.name)
    site_home = site_paths.home
    if is_disabled(site_paths.apache_conf):
        sys.exit("This site is disabled.")

    if command in ["start", "restart"]:
        skelroot = "/omd/versions/%s/skel" % omdlib.__version__
        prepare_and_populate_tmpfs(
            config,
            version_info,
            site.name,
            site_home,
            site.tmp_dir,
            site.replacements(),
            site.skel_permissions,
            skelroot,
        )

    if len(args) > 0:
        # restrict to this daemon
        daemon: str | None = args[0]
    else:
        daemon = None

    # OMD guarantees that we are in OMD_ROOT
    with contextlib.chdir(site_home):
        if command == "status":
            return check_status(
                site_home, global_opts.verbose, display=True, daemon=daemon, bare="bare" in options
            )
        return call_init_scripts(site_home, command, daemon)


# .
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


def clear_environment() -> None:
    # first remove *all* current environment variables, except:
    # TERM
    # CMK_CONTAINERIZED: To better detect when running inside container (e.g. used for omd update)
    keep = ["TERM", "CMK_CONTAINERIZED"]
    for key in os.environ:
        if key not in keep:
            del os.environ[key]


def set_environment(site_name: str, config: Config) -> None:
    site_home = SitePaths.from_site_name(site_name).home
    os.environ["OMD_SITE"] = site_name
    os.environ["OMD_ROOT"] = site_home
    os.environ["PATH"] = (
        f"{site_home}/local/bin:{site_home}/bin:/usr/local/bin:/bin:/usr/bin:/sbin:/usr/sbin"
    )
    os.environ["USER"] = site_name

    os.environ["LD_LIBRARY_PATH"] = f"{site_home}/local/lib:{site_home}/lib"
    os.environ["HOME"] = site_home

    # allow user to define further environment variable in ~/etc/environment
    envfile = Path(site_home, "etc", "environment")
    if envfile.exists():
        lineno = 0
        with envfile.open() as opened_file:
            for line in opened_file:
                lineno += 1
                line = line.strip()
                if line == "" or line[0] == "#":
                    continue  # allow empty lines and comments
                parts = line.split("=")
                if len(parts) != 2:
                    sys.exit("%s: syntax error in line %d" % (envfile, lineno))
                varname = parts[0]
                value = parts[1]
                if value.startswith('"'):
                    value = value.strip('"')

                # Add the present environment when someone wants to append some
                if value.startswith("$%s:" % varname):
                    before = os.environ.get(varname)
                    if before:
                        value = before + ":" + value.replace("$%s:" % varname, "")

                if value.startswith("'"):
                    value = value.strip("'")
                os.environ[varname] = value

    create_config_environment(config)


def hostname() -> str:
    try:
        completed_process = subprocess.run(
            ["hostname"],
            shell=False,
            close_fds=True,
            stdout=subprocess.PIPE,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return "localhost"
    return completed_process.stdout.strip()


# return "| $PAGER", if a pager is available
def pipe_pager() -> str:
    pager = os.environ.get("PAGER")
    if not pager and os.path.exists("/usr/bin/less"):
        pager = "less -F -X"
    if pager:
        return "| %s" % pager
    return ""


# .
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


def main_setversion(
    _version_info: object,
    _site: object,
    _global_opts: object,
    args: Arguments,
    _options: object,
    versions_path: Path = Path("/omd/versions/"),
) -> None:
    if len(args) == 0:
        versions = [
            (v, "Version %s" % v)
            for v in omd_versions(versions_path)
            if not v == default_version(versions_path)
        ]

        if use_update_alternatives():
            versions = [("auto", "Auto (Update-Alternatives)")] + versions

        success, version = dialog_menu(
            "Choose new default",
            "Please choose the version to make the new default",
            versions,
            None,
            "Make default",
            "Cancel",
        )
        if not success:
            sys.exit("Aborted.")
    else:
        version = args[0]

    if version != "auto" and not version_exists(version, versions_path):
        sys.exit("The given version does not exist.")
    if version == default_version(versions_path):
        sys.exit("The given version is already default.")

    # Special handling for debian based distros which use update-alternatives
    # to control the path to the omd binary, manpage and so on
    if use_update_alternatives():
        if version == "auto":
            with subprocess.Popen(["update-alternatives", "--auto", "omd"]):
                pass
        else:
            with subprocess.Popen(
                ["update-alternatives", "--set", "omd", "/omd/versions/" + version]
            ):
                pass
    else:
        if os.path.islink("/omd/versions/default"):
            os.remove("/omd/versions/default")
        os.symlink("/omd/versions/%s" % version, "/omd/versions/default")


def use_update_alternatives() -> bool:
    return os.path.exists("/var/lib/dpkg/alternatives/omd")


def main_create(
    version_info: VersionInfo,
    site: SiteContext,
    global_opts: GlobalOptions,
    _args: object,
    options: CommandOptions,
) -> None:
    reuse = False
    if "reuse" in options:
        reuse = True
        if not user_verify(version_info, site):
            sys.exit("Error verifying site user.")

    site_home = SitePaths.from_site_name(site.name).home
    sitename_must_be_valid(site.name, Path(site_home), reuse)

    # Create operating system user for site
    uid = options.get("uid")
    gid = options.get("gid")
    if not reuse:
        useradd(version_info, site, uid, gid)

    if reuse:
        fstab_verify(site.name, site.tmp_dir)
    else:
        create_site_home(site.name)
        add_to_fstab(site.name, site.real_tmp_dir, tmpfs_size=options.get("tmpfs-size"))

    config_settings: Config = {}
    if "no-autostart" in options:
        config_settings["AUTOSTART"] = "off"
        sys.stdout.write("Going to set AUTOSTART to off.\n")

    if "no-tmpfs" in options:
        config_settings["TMPFS"] = "off"
        sys.stdout.write("Going to set TMPFS to off.\n")

    if "no-init" not in options:
        outcome, admin_password = init_site(
            version_info, site, global_opts, config_settings, options
        )
        welcome_message(site, admin_password)
        sys.exit(outcome.value)
    else:
        sys.stdout.write(
            f"Create new site {site.name} in disabled state and with empty {site_home}.\n"
        )
        sys.stdout.write("You can now mount a filesystem to %s.\n" % (site_home))
        sys.stdout.write("Afterwards you can initialize the site with 'omd init'.\n")


def welcome_message(site: SiteContext, admin_password: Password) -> None:
    sys.stdout.write(f"Created new site {site.name} with version {omdlib.__version__}.\n\n")
    sys.stdout.write(
        f"  The site can be started with {tty.bold}omd start {site.name}{tty.normal}.\n"
    )
    sys.stdout.write(
        f"  The default web UI is available at {tty.bold}http://{hostname()}/{site.name}/{tty.normal}\n"
    )
    sys.stdout.write("\n")
    sys.stdout.write(
        f"  The admin user for the web applications is {tty.bold}cmkadmin{tty.normal} with password: {tty.bold}{admin_password.raw}{tty.normal}\n"
    )
    sys.stdout.write(
        f"  For command line administration of the site, log in with {tty.bold}'omd su {site.name}'{tty.normal}.\n"
    )
    sys.stdout.write(
        "  After logging in, you can change the password for cmkadmin with "
        "%s'cmk-passwd cmkadmin'%s.\n" % (tty.bold, tty.normal)
    )
    sys.stdout.write("\n")


def main_init(
    version_info: VersionInfo,
    site: SiteContext,
    global_opts: GlobalOptions,
    _args: object,
    options: CommandOptions,
) -> None:
    site_paths = SitePaths.from_site_name(site.name)
    site_home, apache_conf = site_paths.home, site_paths.apache_conf
    if not is_disabled(apache_conf):
        sys.exit(
            "Cannot initialize site that is not disabled.\n"
            "Please call 'omd disable %s' first." % site.name
        )

    if not os.listdir(site_home):
        if not global_opts.force:
            sys.exit(
                "The site's home directory is not empty. Please add use\n"
                "'omd --force init %s' if you want to erase all data." % site.name
            )

        # We must not delete the directory itself, just its contents.
        # The directory might be a separate filesystem. This is not quite
        # unlikely, since people using 'omd init' are doing this most times
        # because they are working with clusters and separate filesystems for
        # each site.
        sys.stdout.write("Wiping the contents of %s..." % site_home)
        for entry in os.listdir(site_home):
            if entry not in [".", ".."]:
                path = site_home + "/" + entry
                if global_opts.verbose:
                    sys.stdout.write("\n   deleting %s..." % path)
                if os.path.islink(path) or not os.path.isdir(path):
                    os.remove(path)
                else:
                    shutil.rmtree(site_home + "/" + entry)
        ok()

    # Do the things that have been ommited on omd create --disabled
    outcome, admin_password = init_site(
        version_info, site, global_opts, config_settings={}, options=options
    )
    welcome_message(site, admin_password)
    sys.exit(outcome.value)


def init_site(
    version_info: VersionInfo,
    site: SiteContext,
    global_opts: GlobalOptions,
    config_settings: Config,
    options: CommandOptions,
) -> tuple[FinalizeOutcome, Password]:
    apache_reload = "apache-reload" in options

    site_home = SitePaths.from_site_name(site.name).home
    # Create symbolic link to version
    create_version_symlink(site_home, omdlib.__version__)

    # Build up directory structure with symbolic links relative to
    # the version link we just create
    for d in ["bin", "include", "lib", "share"]:
        os.symlink("version/" + d, site_home + "/" + d)

    # Create skeleton files of non-tmp directories
    skelroot = "/omd/versions/%s/skel" % omdlib.__version__
    create_skeleton_files(site_home, site.replacements(), skelroot, site.skel_permissions, ".")

    # Save the skeleton files used to initialize this site
    save_version_meta_data(site, omdlib.__version__)

    # Set the initial password of the default admin user
    admin_password = calculate_admin_password(options)
    set_admin_password(site_home, admin_password)

    # Change ownership of all files and dirs to site user
    chown_tree(site_home, site.name)

    config = load_config(site, global_opts.verbose)
    if config_settings:  # add specific settings
        for hook_name, value in config_settings.items():
            config[hook_name] = value
    create_config_environment(config)

    # Change the few files that config save as created as root
    chown_tree(site_home, site.name)

    outcome = finalize_site(
        version_info, site, config, CommandType.create, apache_reload, global_opts.verbose
    )
    return outcome, admin_password


def main_rm(
    version_info: VersionInfo,
    site: SiteContext,
    global_opts: GlobalOptions,
    _args: object,
    options: CommandOptions,
) -> None:
    if not global_opts.force:
        confirm_text = (
            "PLEASE NOTE: This action removes all configuration files\n"
            "             and variable data of the site.\n"
            "\n"
            "In detail the following steps will be done:\n"
            "- Stop all processes of the site\n"
            "- Unmount tmpfs of the site\n"
            "- Remove tmpfs of the site from fstab\n"
            "- Remove the system user <SITENAME>\n"
            "- Remove the system group <SITENAME>\n"
            "- Remove the site home directory\n"
            "- Restart the system wide apache daemon\n"
            " [yes/NO]:"
        )
        answer: str | None = None
        while answer not in ["", "yes", "no"]:
            answer = input(confirm_text).strip().lower()
        if answer in ["", "no"]:
            sys.exit("Aborted.")
    _main_rm(version_info, site, global_opts, options)


def _main_rm(
    version_info: VersionInfo,
    site: SiteContext,
    global_opts: GlobalOptions,
    options: CommandOptions,
) -> None:
    # omd rm is called as root but the init scripts need to be called as
    # site user but later steps need root privilegies. So a simple user
    # switch to the site user would not work. Better create a subprocess
    # for this dedicated action and switch to the user in that subprocess
    with subprocess.Popen(["omd", "stop", site.name]):
        pass

    reuse = "reuse" in options
    kill = "kill" in options

    if user_logged_in(site.name):
        if not kill:
            sys.exit("User '%s' still logged in or running processes." % site.name)
        else:
            kill_site_user_processes(site.name, global_opts.verbose)

    site_home = SitePaths.from_site_name(site.name).home
    if tmpfs_mounted(site.name):
        unmount_tmpfs(site.name, site_home, site.tmp_dir, kill=kill)

    # Remove include-hook for Apache and tell apache
    # Needs to be cleaned up before removing the site directory. Otherwise a
    # parallel restart / reload of the apache may fail, because the apache hook
    # refers to a not existing site apache config.
    unregister_from_system_apache(
        version_info,
        SitePaths.from_site_name(site.name).apache_conf,
        apache_reload="apache-reload" in options,
        verbose=global_opts.verbose,
    )

    if not reuse:
        remove_from_fstab(site.name, site.tmp_dir)
        sys.stdout.write("Deleting user and group %s..." % site.name)
        os.chdir("/")  # Site directory not longer existant after userdel
        userdel(site.name)
        ok()

    if os.path.exists(site_home):  # should be done by userdel
        sys.stdout.write("Deleting all data (%s)..." % site_home)
        shutil.rmtree(site_home)
        ok()

    if reuse:
        create_site_home(site.name)
        os.mkdir(site.tmp_dir)
        os.chown(site.tmp_dir, user_id(site.name), group_id(site.name))


def create_site_home(site_name: str) -> None:
    site_home = SitePaths.from_site_name(site_name).home
    try:
        os.makedirs(site_home)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    os.chown(site_home, user_id(site_name), group_id(site_name))
    # If the site_home is not world executable files in the site are all not readable/writeable
    os.chmod(site_home, 0o751)  # nosec B103 # BNS:7e6b08


def main_disable(
    version_info: VersionInfo,
    site: SiteContext,
    global_opts: GlobalOptions,
    _args: object,
    options: CommandOptions,
) -> None:
    site_paths = SitePaths.from_site_name(site.name)
    site_home = site_paths.home
    if is_disabled(SitePaths.from_site_name(site.name).apache_conf):
        sys.stderr.write("This site is already disabled.\n")
        sys.exit(0)

    if not site.is_stopped(global_opts.verbose):
        call_init_scripts(site_home, "stop")
    unmount_tmpfs(site.name, site_home, site.tmp_dir, kill="kill" in options)
    sys.stdout.write("Disabling Apache configuration for this site...")
    unregister_from_system_apache(
        version_info,
        SitePaths.from_site_name(site.name).apache_conf,
        apache_reload=False,
        verbose=global_opts.verbose,
    )


def main_enable(
    version_info: VersionInfo,
    site: SiteContext,
    global_opts: GlobalOptions,
    _args: object,
    _options: object,
) -> None:
    config = site.conf
    site_paths = SitePaths.from_site_name(site.name)
    site_home = site_paths.home
    if not is_disabled(site_paths.apache_conf):
        sys.stderr.write("This site is already enabled.\n")
        sys.exit(0)
    sys.stdout.write("Re-enabling Apache configuration for this site...")
    register_with_system_apache(
        version_info,
        site_paths.apache_conf,
        site.name,
        site_home,
        config["APACHE_TCP_ADDR"],
        config["APACHE_TCP_PORT"],
        False,
        verbose=global_opts.verbose,
    )


def main_update_apache_config(
    version_info: VersionInfo,
    site: SiteContext,
    global_opts: GlobalOptions,
    _args: object,
    _options: object,
) -> None:
    config = load_config(site, global_opts.verbose)
    site_paths = SitePaths.from_site_name(site.name)
    site_home = site_paths.home
    if _is_apache_enabled(config):
        register_with_system_apache(
            version_info,
            site_paths.apache_conf,
            site.name,
            site_home,
            config["APACHE_TCP_ADDR"],
            config["APACHE_TCP_PORT"],
            True,
            verbose=global_opts.verbose,
        )
    else:
        unregister_from_system_apache(
            version_info,
            SitePaths.from_site_name(site.name).apache_conf,
            apache_reload=True,
            verbose=global_opts.verbose,
        )


def _is_apache_enabled(config: Config) -> bool:
    return config["APACHE_MODE"] != "none"


def _get_conflict_mode(options: CommandOptions) -> Skeleton:
    conflict_mode = cast(str, options.get("conflict", "ask"))

    if conflict_mode not in ["ask", "install", "keepold", "abort"]:
        sys.exit("Argument to --conflict must be one of ask, install, keepold and abort.")

    return Skeleton(conflict_mode)


def main_mv_or_cp(
    version_info: VersionInfo,
    old_site: SiteContext,
    global_opts: GlobalOptions,
    command_type: CommandType,
    args: Arguments,
    options: CommandOptions,
) -> None:
    conflict_mode = _get_conflict_mode(options)
    action = "rename" if command_type is CommandType.move else "copy"

    if len(args) != 1:
        sys.exit("omd: Usage: omd %s oldname newname" % command_type.short)
    new_site = SiteContext(args[0])

    reuse = False
    if "reuse" in options:
        reuse = True
        if not user_verify(version_info, new_site):
            sys.exit("Error verifying site user.")
        fstab_verify(new_site.name, new_site.tmp_dir)

    new_site_home = SitePaths.from_site_name(new_site.name).home
    sitename_must_be_valid(new_site.name, Path(new_site_home), reuse)

    if not old_site.is_stopped(global_opts.verbose):
        sys.exit(f"Cannot {action} site '{old_site.name}' while it is running.")

    pids = find_processes_of_user(old_site.name)
    if pids:
        sys.exit(
            "Cannot %s site '%s' while there are processes owned by %s.\n"
            "PIDs: %s" % (action, old_site.name, old_site.name, " ".join(pids))
        )

    if command_type is CommandType.move:
        unmount_tmpfs(
            old_site.name,
            SitePaths.from_site_name(old_site.name).home,
            old_site.tmp_dir,
            kill="kill" in options,
        )
        if not reuse:
            remove_from_fstab(old_site.name, old_site.tmp_dir)

    sys.stdout.write(
        "{}ing site {} to {}...".format(
            command_type is CommandType.move and "Mov" or "Copy", old_site.name, new_site.name
        )
    )
    sys.stdout.flush()

    # Create new user. Note: even on mv we need to create a new user.
    # Linux does not (officially) allow to rename a user.
    uid = options.get("uid")
    gid = options.get("gid")
    if not reuse:
        useradd(version_info, new_site, uid, gid)  # None for uid/gid means: let Linux decide

    # Needs to be computed before the site is moved to be able to derive the version from the
    # version symlink
    old_replacements = old_site.replacements()

    old_site_home = SitePaths.from_site_name(old_site.name).home
    if command_type is CommandType.move and not reuse:
        # Rename base directory and apache config
        os.rename(old_site_home, new_site_home)
        delete_apache_hook(SitePaths.from_site_name(old_site.name).apache_conf)
    else:
        # Make exact file-per-file copy with same user but already new name
        if not reuse:
            os.mkdir(new_site_home)

        addopts = []
        for p in omdlib.backup.get_exclude_patterns(options):
            addopts += ["--exclude", "/%s" % p]

        if global_opts.verbose:
            addopts += ["-v"]

        with subprocess.Popen(
            ["rsync", "-arx"] + addopts + [old_site_home + "/", new_site_home + "/"]
        ):
            pass

        httpdlogdir = new_site_home + "/var/log/apache"
        if not os.path.exists(httpdlogdir):
            os.mkdir(httpdlogdir)

        rrdcacheddir = new_site_home + "/var/rrdcached"
        if not os.path.exists(rrdcacheddir):
            os.mkdir(rrdcacheddir)

    # give new user all files
    chown_tree(new_site_home, new_site.name)

    # Change config files from old to new site (see rename_site())
    patch_skeleton_files(
        conflict_mode, old_site.name, new_site, old_replacements, new_site.replacements()
    )

    # In case of mv now delete old user
    if command_type is CommandType.move and not reuse:
        userdel(old_site.name)

    # clean up old site
    if command_type is CommandType.move and reuse:
        _main_rm(version_info, old_site, global_opts, {"reuse": None})

    sys.stdout.write("OK\n")

    # Now switch over to the new site as currently active site
    new_config = load_config(new_site, global_opts.verbose)
    set_environment(new_site.name, new_config)

    # Entry for tmps in /etc/fstab
    if not reuse:
        add_to_fstab(new_site.name, new_site.real_tmp_dir, tmpfs_size=options.get("tmpfs-size"))

    # Needed by the post-rename-site script
    os.environ["OLD_OMD_SITE"] = old_site.name

    outcome = finalize_site(
        version_info,
        new_site,
        new_config,
        command_type,
        "apache-reload" in options,
        global_opts.verbose,
    )
    sys.exit(outcome.value)


def main_diff(
    _version_info: object,
    site: SiteContext,
    global_opts: GlobalOptions,
    args: Arguments,
    options: CommandOptions,
) -> None:
    site_home = SitePaths.from_site_name(site.name).home
    from_version = version_from_site_dir(Path(site_home))
    if from_version is None:
        sys.exit("Failed to determine site version")
    from_skelroot = site.version_skel_dir

    # If arguments are added and those arguments are directories,
    # then we just output the general state of the file. If only
    # one file is specified, we directly show the unified diff.
    # This behaviour can also be forced by the OMD option -v.

    verbose = global_opts.verbose
    if len(args) == 0:
        args = ["."]
    elif len(args) == 1 and os.path.isfile(args[0]):
        verbose = True

    for arg in args:
        diff_list(verbose, options, site, from_skelroot, arg)


def diff_list(
    verbose: bool,
    options: CommandOptions,
    site: SiteContext,
    from_skelroot: str,
    orig_path: str,
) -> None:
    # Compare a list of files/directories with the original state and output differences. In verbose
    # mode, we output the complete diff, otherwise just the state. Only files present in skel/ are
    # handled at all.

    old_perms = site.skel_permissions

    # Prepare paths:
    # orig_path: this was specified by the user
    # rel_path:  path relative to the site's dir
    # abs_path:  absolute path

    # Get absolute path to site_home. This can be (/opt/omd/sites/XXX)
    # due to the symbolic link /omd
    site_home = SitePaths.from_site_name(site.name).home
    old_dir = os.getcwd()
    os.chdir(site_home)
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
    if abs_path.startswith(site_home):
        rel_path = abs_path[len(site_home) + 1 :]
    elif abs_path.startswith(abs_sitedir):
        rel_path = abs_path[len(abs_sitedir) + 1 :]
    else:
        sys.exit("Sorry, 'omd diff' only works for files in the site's directory.")

    if not os.path.isdir(abs_path):
        print_diff(rel_path, verbose, options, site, from_skelroot, site_home, old_perms)
    else:
        if not rel_path:
            rel_path = "."

        for file_path in walk_skel(from_skelroot, depth_first=False, relbase=rel_path):
            print_diff(file_path, verbose, options, site, from_skelroot, site_home, old_perms)


def print_diff(
    rel_path: str,
    verbose: bool,
    options: CommandOptions,
    site: SiteContext,
    source_path: str,
    target_path: str,
    source_perms: Permissions,
) -> None:
    source_file = source_path + "/" + rel_path
    target_file = target_path + "/" + rel_path

    source_perm = get_skel_permissions(source_path, source_perms, rel_path)
    target_perm = get_file_permissions(target_file)

    source_type = filetype(source_file)
    target_type = filetype(target_file)

    changed_type, changed_content, changed = file_status(
        source_file, site.replacements(), target_file, site.replacements()
    )

    if not changed:
        return

    fn = tty.bold + tty.bgblue + tty.white + rel_path + tty.normal
    fn = tty.bold + rel_path + tty.normal

    def print_status(color: str, f: str, status: str, long_out: str) -> None:
        if "bare" in options:
            sys.stdout.write(f"{status} {f}\n")
        elif not verbose:
            sys.stdout.write(color + f" {long_out} {f}\n")
        else:
            arrow = tty.magenta + "->" + tty.normal
            if "c" in status:
                source_content = file_contents(source_file, site.replacements())
                if os.system("which colordiff > /dev/null 2>&1") == 0:  # nosec B605 # BNS:2b5952
                    diff = "colordiff"
                else:
                    diff = "diff"
                subprocess.run(
                    [diff, "-", target_file],
                    close_fds=True,
                    shell=False,
                    input=source_content,
                    check=False,
                )
            elif status == "p":
                sys.stdout.write(f"    {source_perm} {arrow} {target_perm}\n")
            elif "t" in status:
                sys.stdout.write(f"    {source_type} {arrow} {target_type}\n")

    if not target_type:
        print_status(StateMarkers.good, fn, "r", "Removed")
        return

    if changed_type and changed_content:
        print_status(StateMarkers.good, fn, "tc", "Changed type and content")

    elif changed_type and not changed_content:
        print_status(StateMarkers.good, fn, "t", "Changed type")

    elif changed_content and not changed_type:
        print_status(StateMarkers.good, fn, "c", "Changed content")

    if source_perm != target_perm:
        print_status(StateMarkers.warn, fn, "p", "Changed permissions")


def main_update(
    version_info: VersionInfo,
    site: SiteContext,
    global_opts: GlobalOptions,
    _args: object,
    options: CommandOptions,
    versions_path: Path = Path("/omd/versions/"),
) -> None:
    skeleton_mode, conflict_mode = get_conflict_mode_update(options)

    if not site.is_stopped(global_opts.verbose):
        sys.exit("Please completely stop '%s' before updating it." % site.name)

    site_home = SitePaths.from_site_name(site.name).home
    # Unmount tmp. We need to recreate the files and directories
    # from the new version after updating.
    unmount_tmpfs(site.name, site_home, site.tmp_dir)

    # Source version: the version of the site we deal with
    from_version = version_from_site_dir(Path(site_home))
    if from_version is None:
        sys.exit("Failed to determine site version")
    if from_version == global_opts.version:
        sys.exit(f"Site already has version {global_opts.version}.")

    # Target version: the version of the OMD binary
    to_version = omdlib.__version__

    old_from_edition, new_from_edition = get_edition(from_version)
    _old_to_edition, new_to_edition = get_edition(to_version)
    check_update_possible(
        new_from_edition,
        new_to_edition,
        from_version,
        to_version,
        site.name,
        prepare_conflict_resolution(options, global_opts.force),
        versions_path,
    )

    is_tty = sys.stdout.isatty()
    with (
        with_update_logging_stdout(Path(site_home) / "var/log/update.log"),
        with_update_logging_stderr(Path(site_home) / "var/log/update.log"),
    ):
        sys.stdout.write(
            f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Updating site '{site.name}' from version {from_version} to {to_version}...\n\n"
        )

        # Now apply changes of skeleton files. This can be done
        # in two ways:
        # 1. creating a patch from the old default files to the new
        #    default files and applying that to the current files
        # 2. creating a patch from the old default files to the current
        #    files and applying that to the new default files
        # We implement the first method.

        # In case the version_meta is stored in the site and it's the data of the
        # old version we are facing, use these files instead of the files from the
        # version directory. This makes updates possible without the old version.
        old_permissions = site.skel_permissions
        new_permissions = load_skel_permissions_from(skel_permissions_file_path(to_version))

        from_skelroot = site.version_skel_dir
        to_skelroot = "/omd/versions/%s/skel" % to_version

        with ManageUpdate(
            site.name, site.tmp_dir, Path(site_home), Path(from_skelroot), Path(to_skelroot)
        ) as mu:
            # First walk through skeleton files of new version
            for relpath in walk_skel(to_skelroot, depth_first=False):
                _execute_update_file(
                    relpath,
                    site,
                    skeleton_mode,
                    from_version,
                    to_version,
                    old_from_edition,
                    new_to_edition,
                    old_permissions,
                    new_permissions,
                )

            # Now handle files present in old but not in new skel files
            for relpath in walk_skel(from_skelroot, depth_first=True, exclude_if_in=to_skelroot):
                _execute_update_file(
                    relpath,
                    site,
                    skeleton_mode,
                    from_version,
                    to_version,
                    old_from_edition,
                    new_to_edition,
                    old_permissions,
                    new_permissions,
                )

            # Change symbolic link pointing to new version
            create_version_symlink(site_home, to_version)
            save_version_meta_data(site, to_version)

            # Prepare for config_set_all: Refresh the site configuration, because new hooks may introduce
            # new settings and default values.
            config = load_config(site, global_opts.verbose)

            # Let hooks of the new(!) version do their work and update configuration.
            config_set_all(site, config, global_opts.verbose, ())
            save_site_conf(site_home, config)

            # Before the hooks can be executed the tmpfs needs to be mounted. This requires access to the
            # initialized tmpfs.
            mu.prepare_and_populate_tmpfs(
                version_info, config, site.replacements(), site.skel_permissions
            )

            additional_update_env = {
                "OMD_FROM_EDITION": new_from_edition,
                "OMD_FROM_VERSION": from_version,
                "OMD_TO_EDITION": new_to_edition,
                "OMD_TO_VERSION": to_version,
            }
            if conflict_mode != PreFlight.IGNORE:
                command = ["cmk-update-config", "--conflict", conflict_mode.value, "--dry-run"]
                sys.stdout.write(f"Executing '{subprocess.list2cmdline(command)}'")
                returncode = _call_script(
                    is_tty,
                    {
                        **os.environ,
                        "OMD_ROOT": site_home,
                        "OMD_SITE": site.name,
                        **additional_update_env,
                    },
                    command,
                )
                if returncode != 0:
                    sys.exit(returncode)
            else:
                sys.stdout.write("Skipping pre-flight check")
            sys.stdout.write(
                f"\nCompleted verifying site configuration. Your site now has version {to_version}.\n"
            )

        call_scripts(
            site.name,
            "post-update",
            open_pty=is_tty,
            add_env=additional_update_env,
        )

        if new_from_edition != new_to_edition and edition_has_enforced_licensing(
            to_ed := Edition.from_long_edition(new_to_edition)
        ):
            sys.stdout.write(
                f"{tty.bold}You have now upgraded your product to {to_ed.title}. If you have not "
                f"applied a valid license yet, you will be in trial period in {to_ed.title}. If you"
                f" are intending to use Checkmk to monitor more than 750 services after the trial period, you "
                f"must purchase a license. In case you already have a license, please enter your "
                f"license credentials on the product's licensing page "
                f"(Setup > Maintenance > Licensing > Edit settings)..{tty.normal}\n"
            )

        sys.stdout.write("Finished update.\n\n")


def main_umount(
    _version_info: object,
    site: SiteContext | RootContext,
    global_opts: GlobalOptions,
    _args: object,
    options: CommandOptions,
) -> None:
    only_version = options.get("version")

    # if no site is selected, all sites are affected
    exit_status = 0
    if not isinstance(site, SiteContext):
        for site_id in all_sites(Path("/omd/")):
            # Set global vars for the current site
            site = SiteContext(site_id)
            site_home = SitePaths.from_site_name(site_id).home

            if only_version and version_from_site_dir(Path(site_home)) != only_version:
                continue

            # Skip the site even when it is partly running
            if not site.is_stopped(global_opts.verbose):
                sys.stderr.write(
                    "Cannot unmount tmpfs of site '%s' while it is running.\n" % site.name
                )
                continue

            sys.stdout.write(f"{tty.bold}Unmounting tmpfs of site {site.name}{tty.normal}...")
            sys.stdout.flush()

            if not show_success(
                unmount_tmpfs(site.name, site_home, site.tmp_dir, False, kill="kill" in options)
            ):
                exit_status = 1
    else:
        # Skip the site even when it is partly running
        if not site.is_stopped(global_opts.verbose):
            sys.exit("Cannot unmount tmpfs of site '%s' while it is running." % site.name)
        unmount_tmpfs(
            site.name,
            SitePaths.from_site_name(site.name).home,
            site.tmp_dir,
            kill="kill" in options,
        )
    sys.exit(exit_status)


def main_init_action(
    version_info: VersionInfo,
    site: SiteContext | RootContext,
    global_opts: GlobalOptions,
    command: Literal["start", "stop", "restart", "reload", "status"],
    args: Arguments,
    options: CommandOptions,
) -> None:
    if isinstance(site, SiteContext):
        config = site.conf
        site_home = SitePaths.from_site_name(site.name).home
        exit_status = init_action(version_info, site, config, global_opts, command, args, options)

        # When the whole site is about to be stopped check for remaining
        # processes and terminate them
        if command == "stop" and not args and exit_status == 0:
            terminate_site_user_processes(site.name, global_opts.verbose)
            # Even if we are not explicitly executing an unmount of the tmpfs, this may be the
            # "stop" before shutting down the computer. Create a tmpfs dump now, just to be sure.
            save_tmpfs_dump(site_home, site.tmp_dir)

        if command == "start":
            _update_license_usage(site)

        sys.exit(exit_status)

    # if no site is selected, all sites are affected

    only_version = options.get("version")
    bare = "bare" in options
    parallel = "parallel" in options

    max_site_len = max([8] + [len(site_id) for site_id in all_sites(Path("/omd/"))])

    def parallel_output(site_id: str, line: str) -> None:
        sys.stdout.write(("%-" + str(max_site_len) + "s - %s") % (site_id, line))

    exit_states, processes = [], []
    for sitename in all_sites(Path("/omd/")):
        site = SiteContext(sitename)
        site_paths = SitePaths.from_site_name(sitename)
        site_home = SitePaths.from_site_name(sitename).home
        version = version_from_site_dir(Path(site_home))

        if version is None:  # skip partially created sites
            continue

        if only_version and version != only_version:
            continue

        # Skip disabled sites completely
        if is_disabled(site_paths.apache_conf):
            continue

        config = load_config(site, global_opts.verbose)

        # Handle non autostart sites
        if command in ["start", "restart", "reload"] or ("auto" in options and command == "status"):
            if not global_opts.force and config.get("AUTOSTART", "on") != "on":
                if bare:
                    continue

                if not parallel:
                    sys.stdout.write("Ignoring site '%s': AUTOSTART != on\n" % site.name)
                else:
                    parallel_output(site.name, "Ignoring since autostart is disabled\n")

                continue

        if command == "status" and bare:
            sys.stdout.write("[%s]\n" % site.name)
        elif not parallel:
            sys.stdout.write(f"{tty.bold}Doing '{command}' on site {site.name}:{tty.normal}\n")
        else:
            parallel_output(site.name, "Invoking '%s'\n" % (command))
        sys.stdout.flush()

        # We need to open a subprocess, because each site must be started with the account of the
        # site user. And after setuid() we cannot return.
        stdout: int | IO[str] = sys.stdout if not parallel else subprocess.PIPE
        stderr: int | IO[str] = sys.stderr if not parallel else subprocess.STDOUT
        bare_arg = ["--bare"] if bare else []
        p = subprocess.Popen(
            [sys.argv[0], command] + bare_arg + [site.name] + args,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            encoding="utf-8",
        )

        if parallel:
            if p.stdout is not None:
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
    site_buf: dict[str, str] = {}
    while parallel and processes:
        for site_id, p in processes[:]:
            if p.stdout is None:
                raise Exception("stdout needs to be set")

            buf = site_buf.get(site_id, "")
            try:
                while True:
                    b = p.stdout.read(1024)
                    if not b:
                        break
                    buf += b
            except OSError as e:
                if e.errno == errno.EAGAIN:
                    pass
                else:
                    raise

            while True:
                pos = buf.find("\n")
                if pos == -1:
                    break
                line, buf = buf[: pos + 1], buf[pos + 1 :]
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


def _update_license_usage(site: SiteContext) -> None:
    subprocess.Popen(
        [f"/omd/sites/{site.name}/bin/cmk-update-license-usage"],
        start_new_session=True,
    )


def main_config(
    version_info: VersionInfo,
    site: SiteContext,
    global_opts: GlobalOptions,
    args: Arguments,
    _options: object,
) -> None:
    site_home = str(SitePaths.from_site_name(site.name).home)
    if (
        (not args or args[0] != "show")
        and not site.is_stopped(global_opts.verbose)
        and global_opts.force
    ):
        need_start = True
        call_init_scripts(site_home, "stop")
    else:
        need_start = False

    config_hooks = load_config_hooks(site, global_opts.verbose)
    set_hooks: list[str] = []
    config = site.conf
    if len(args) == 0:
        set_hooks = list(config_configure(site, config, config_hooks, global_opts.verbose))
    else:
        command = args[0]
        args = args[1:]
        if command == "show":
            config_show(config, config_hooks, args)
        elif command == "set":
            set_hooks = config_set(site, site_home, config, config_hooks, args, global_opts.verbose)
        elif command == "change":
            set_hooks = config_change(version_info, site, config, config_hooks, global_opts.verbose)
        else:
            config_usage()

    if (
        set(set_hooks).intersection({"APACHE_TCP_ADDR", "APACHE_TCP_PORT", "APACHE_MODE"})
        and not is_containerized()
    ):
        sys.stdout.write(
            f"WARNING: You have to execute 'omd update-apache-config {site.name}' as "
            "root to update and apply the configuration of the system apache.\n"
        )

    if need_start:
        start_site(version_info, site, config)


def main_su(
    _version_info: object,
    site: SiteContext,
    _global_opts: object,
    _args: object,
    _options: object,
) -> None:
    try:
        os.execl("/bin/su", "su", "-", "%s" % site.name)
    except OSError:
        sys.exit("Cannot open a shell for user %s" % site.name)


def _process_backup_tar_and_setup_env(
    tar: SafeIndexedTarFile | SafeStreamedTarFile,
    verbose: bool,
    options: CommandOptions,
    old_site_name: str,
    new_site: SiteContext,
) -> Config:
    site_home = str(SitePaths.from_site_name(new_site.name).home)

    # Now extract all files
    for tarinfo in tar:
        # The files in the tar archive start with the siteid as first element.
        # Remove this first element from the file paths and also care for hard link
        # targets.

        # Remove leading site name from paths
        tarinfo.name = "/".join(tarinfo.name.split("/")[1:])
        if verbose:
            sys.stdout.write("Restoring %s...\n" % tarinfo.name)

        if tarinfo.islnk():
            parts = tarinfo.linkname.split("/")

            if parts[0] == old_site_name:
                new_linkname = "/".join(parts[1:])

                if verbose:
                    sys.stdout.write(
                        f"  Rewriting link target from {tarinfo.linkname} to {new_linkname}\n"
                    )
                tarinfo.linkname = new_linkname

        tar.extract(tarinfo, path=site_home, tar_filter="fully_trusted")
    # give new user all files
    chown_tree(site_home, new_site.name)

    # Change config files from old to new site (see rename_site())
    if old_site_name != new_site.name:
        old_site = SiteContext(old_site_name)
        old_site_home = SitePaths.from_site_name(old_site_name).home
        site_replacements = new_site.replacements()
        old_replacements = {
            "###SITE###": old_site_name,
            "###ROOT###": old_site_home,
            "###EDITION###": site_replacements["###EDITION###"],
        }
        patch_skeleton_files(
            _get_conflict_mode(options),
            old_site.name,
            new_site,
            old_replacements,
            site_replacements,
        )

    # Now switch over to the new site as currently active site
    os.chdir(site_home)

    new_config = load_config(new_site, verbose)

    set_environment(new_site.name, new_config)

    # Needed by the post-rename-site script
    os.environ["OLD_OMD_SITE"] = old_site_name
    return new_config


def _restore_backup_from_tar(
    *,
    tar: SafeIndexedTarFile | SafeStreamedTarFile,
    options: CommandOptions,
    global_opts: GlobalOptions,
    version_info: VersionInfo,
    source_descr: str,
    new_site_name: str | None,
    versions_path: Path = Path("/omd/versions/"),
) -> SiteContext:
    try:
        sitename, version = omdlib.backup.get_site_and_version_from_backup(tar)
    except Exception as e:
        sys.exit("%s" % e)

    if not version_exists(version, versions_path):
        sys.exit(
            "You need to have version %s installed to be able to restore this backup." % version
        )

    if is_root():
        # Ensure the restore is done with the sites version
        if version != omdlib.__version__:
            exec_other_omd(version)

        # Restore site with its original name, or specify a new one
        new_sitename = new_site_name or sitename
    else:
        new_sitename = site_name_from_uid()

    site = SiteContext(new_sitename)

    if is_root():
        sys.stdout.write(f"Restoring site {site.name} from {source_descr}...\n")
        sys.stdout.flush()

        prepare_restore_as_root(version_info, site, options, global_opts.verbose)
        new_config = _process_backup_tar_and_setup_env(
            tar, global_opts.verbose, options, sitename, site
        )
        postprocess_restore_as_root(version_info, site, new_config, options, global_opts.verbose)

    else:
        sys.stdout.write("Restoring site from %s...\n" % source_descr)
        sys.stdout.flush()

        config = load_config(site, global_opts.verbose)
        orig_apache_port = config["APACHE_TCP_PORT"]
        prepare_restore_as_site_user(site, options, global_opts.verbose)
        new_config = _process_backup_tar_and_setup_env(
            tar, global_opts.verbose, options, sitename, site
        )

        postprocess_restore_as_site_user(
            version_info, site, new_config, options, orig_apache_port, global_opts.verbose
        )

    return site


def main_restore(
    version_info: VersionInfo,
    _site: object,
    global_opts: GlobalOptions,
    args: Arguments,
    options: CommandOptions,
) -> None:
    if len(args) == 0:
        sys.exit(
            'You need to provide either a path to the source file or "-" for restore from stdin.'
        )

    source = args[-1]
    source_descr = "stdin" if source == "-" else source
    new_site_name = args[0] if len(args) == 2 else None

    archive_settings = ArchiveSettings(compression="*", bypass_size_validation=True)
    if source == "-":
        tar_reader = CheckmkTarArchive.from_buffer(
            sys.stdin.buffer, streaming=False, **archive_settings
        )
    elif (source_path := Path(source)).exists():
        tar_reader = CheckmkTarArchive.from_path(source_path, streaming=False, **archive_settings)
    else:
        sys.exit("The backup archive does not exist.")

    try:
        with tar_reader as tar:
            _restore_backup_from_tar(
                tar=tar,
                options=options,
                global_opts=global_opts,
                version_info=version_info,
                source_descr=source_descr,
                new_site_name=new_site_name,
            )
    except tarfile.ReadError as e:
        sys.exit("Failed to open the backup: %s" % e)


def postprocess_restore_as_root(
    version_info: VersionInfo,
    site: SiteContext,
    config: Config,
    options: CommandOptions,
    verbose: bool,
) -> None:
    # Entry for tmps in /etc/fstab
    if "reuse" in options:
        command_type = CommandType.restore_existing_site
    else:
        command_type = CommandType.restore_as_new_site
        add_to_fstab(site.name, site.real_tmp_dir, tmpfs_size=options.get("tmpfs-size"))

    outcome = finalize_site(
        version_info, site, config, command_type, "apache-reload" in options, verbose
    )
    sys.exit(outcome.value)


def postprocess_restore_as_site_user(
    version_info: VersionInfo,
    site: SiteContext,
    config: Config,
    options: CommandOptions,
    orig_apache_port: str,
    verbose: bool,
) -> None:
    # Keep the apache port the site currently being replaced had before
    # (we can not restart the system apache as site user)
    config["APACHE_TCP_PORT"] = orig_apache_port
    save_site_conf(SitePaths.from_site_name(site.name).home, config)

    finalize_site_as_user(
        version_info,
        site,
        config,
        (
            CommandType.restore_existing_site
            if "reuse" in options
            else CommandType.restore_as_new_site
        ),
        verbose,
        (),
    )


def main_cleanup(
    version_info: VersionInfo,
    _site: object,
    global_opts: GlobalOptions,
    _args: object,
    _options: object,
    versions_path: Path = Path("/omd/versions/"),
) -> None:
    package_manager = PackageManager.factory(version_info.DISTRO_CODE)
    if package_manager is None:
        sys.exit("Command is not supported on this platform")

    for version in omd_versions(versions_path):
        if version == default_version(versions_path):
            sys.stdout.write(
                "%s%-20s%s Keeping this version, since it is the default.\n"
                % (
                    tty.bold,
                    version,
                    tty.normal,
                ),
            )
            continue

        site_ids = [
            s
            for s in all_sites(Path("/omd/"))
            if version_from_site_dir(Path("/omd/sites/") / s) == version
        ]
        if site_ids:
            sys.stdout.write(
                "%s%-20s%s In use (by %s). Keeping this version.\n"
                % (tty.bold, version, tty.normal, ", ".join(site_ids))
            )
            continue

        matching_installed_packages = package_manager.get_package(
            f"{version_info.OMD_PHYSICAL_BASE}/versions/{version}", global_opts.verbose
        )

        if len(matching_installed_packages) != 1:
            sys.stdout.write(
                "%s%-20s%s Could not determine package. Keeping this version.\n"
                % (tty.bold, version, tty.normal)
            )
            continue

        sys.stdout.write("%s%-20s%s Uninstalling\n" % (tty.bold, version, tty.normal))
        package_manager.uninstall(matching_installed_packages[0], global_opts.verbose)

        # In case there were modifications made to the version the uninstall may leave
        # some files behind. Remove the whole version directory
        version_path: str = os.path.join("/omd/versions", version)
        if os.path.exists(version_path):
            shutil.rmtree(version_path)

    # In case the last version has been removed ensure some things created globally
    # are removed.
    if not omd_versions(versions_path):
        _cleanup_global_files(version_info)


def _cleanup_global_files(version_info: VersionInfo) -> None:
    sys.stdout.write("No version left. Cleaning up global files.\n")
    shutil.rmtree(version_info.OMD_PHYSICAL_BASE, ignore_errors=True)

    for path in [
        "/omd",
        version_info.APACHE_CONF_DIR + "/zzz_omd.conf",
        "/etc/init.d/omd",
        "/usr/bin/omd",
    ]:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass

    if group_exists("omd"):
        groupdel("omd")


# .
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


def _site_environment(site_name: str, command: Command, verbose: bool) -> SiteContext:
    site = SiteContext(site_name)
    site.set_config(load_config(site, verbose))

    # Commands which affect a site and can be called as root *or* as
    # site user should always run with site user privileges. That way
    # we are sure that new files and processes are created under the
    # site user and never as root.
    if not command.no_suid and is_root() and not command.only_root:
        switch_to_site_user(site.name)

    # Make sure environment is in a defined state
    clear_environment()
    set_environment(site.name, site.conf)
    return site


def _run_command(
    command: Command,
    version_info: VersionInfo,
    site: SiteContext | RootContext,
    global_opts: GlobalOptions,
    args: Arguments,
    command_options: CommandOptions,
    orig_working_directory: str,
) -> None:
    try:
        match command.command:
            case "help":
                main_help()
            case "setversion":
                main_setversion(object(), object(), object(), args, object())
            case "version":
                main_version(object(), object(), object(), args, command_options)
            case "versions":
                main_versions(object(), object(), object(), args, command_options)
            case "sites":
                main_sites(object(), object(), object(), object(), command_options)
            case "create":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_create(version_info, site, global_opts, object(), command_options)
            case "init":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_init(version_info, site, global_opts, object(), command_options)
            case "rm":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_rm(version_info, site, global_opts, object(), command_options)
            case "disable":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_disable(version_info, site, global_opts, object(), command_options)
            case "enable":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_enable(version_info, site, global_opts, object(), command_options)
            case "update-apache-config":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_update_apache_config(version_info, site, global_opts, object(), object())
            case "mv":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_mv_or_cp(
                    version_info, site, global_opts, CommandType.move, args, command_options
                )
            case "cp":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_mv_or_cp(
                    version_info, site, global_opts, CommandType.copy, args, command_options
                )
            case "update":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_update(version_info, site, global_opts, object(), command_options)
            case "start":
                main_init_action(version_info, site, global_opts, "start", args, command_options)
            case "stop":
                main_init_action(version_info, site, global_opts, "stop", args, command_options)
            case "restart":
                main_init_action(version_info, site, global_opts, "restart", args, command_options)
            case "reload":
                main_init_action(version_info, site, global_opts, "reload", args, command_options)
            case "status":
                main_init_action(version_info, site, global_opts, "status", args, command_options)
            case "config":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_config(version_info, site, global_opts, args, object())
            case "diff":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_diff(object(), site, global_opts, args, command_options)
            case "su":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                main_su(object(), site, object(), object(), object())
            case "umount":
                main_umount(object(), site, global_opts, object(), command_options)
            case "backup":
                assert command.needs_site == 1 and isinstance(site, SiteContext)
                omdlib.backup.main_backup(
                    object(), site, global_opts, args, command_options, orig_working_directory
                )
            case "restore":
                main_restore(version_info, object(), global_opts, args, command_options)
            case "cleanup":
                main_cleanup(version_info, object(), global_opts, object(), object())
            case _:
                pass  # TODO: Hmmmm...
    except MKTerminate as e:
        sys.exit(str(e))
    except KeyboardInterrupt:
        sys.exit(tty.normal + "Aborted.")


def main() -> None:
    omdlib.backup.ensure_mkbackup_lock_dir_rights()

    version_info = VersionInfo()

    try:
        orig_working_directory = os.getcwd()
    except FileNotFoundError:
        orig_working_directory = "/"

    site_name, global_opts, command, command_options, args = parse_args_or_exec_other_omd(
        sys.argv[1:]
    )

    if not is_root() and command.only_root:
        sys.exit("omd: root permissions are needed for this command.")

    site = (
        RootContext()
        if site_name is None
        else _site_environment(site_name, command, global_opts.verbose)
    )

    _run_command(
        command, version_info, site, global_opts, args, command_options, orig_working_directory
    )
