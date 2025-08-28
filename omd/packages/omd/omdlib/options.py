#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import sys
from pathlib import Path
from typing import Final, NamedTuple

import omdlib
from omdlib.global_options import GlobalOptions, parse_global_opts
from omdlib.site_name import site_name_from_uid
from omdlib.site_paths import SitePaths
from omdlib.utils import exec_other_omd, site_exists
from omdlib.version import version_from_site_dir

CommandOptions = dict[str, str | None]
Arguments = list[str]


class Option(NamedTuple):
    long_opt: str
    short_opt: str | None
    needs_arg: bool
    description: str


exclude_options = [
    Option("no-rrds", None, False, "do not copy RRD files (performance data)"),
    Option("no-logs", None, False, "do not copy the monitoring history and log files"),
    Option(
        "no-agents",
        None,
        False,
        "do not copy agent files created by the bakery (does not affect raw edition)",
    ),
    Option(
        "no-past",
        "N",
        False,
        "do not copy RRD files, agent files, the monitoring history, and log files",
    ),
]


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
class Command(NamedTuple):
    command: str
    only_root: bool
    no_suid: bool
    needs_site: int
    # TODO: Refactor to bool
    site_must_exist: int
    confirm: bool
    args_text: str
    options: list[Option]
    description: str
    confirm_text: str


COMMANDS: Final = [
    Command(
        command="help",
        only_root=False,
        no_suid=False,
        needs_site=0,
        site_must_exist=0,
        confirm=False,
        args_text="",
        options=[],
        description="Show general help",
        confirm_text="",
    ),
    Command(
        command="setversion",
        only_root=True,
        no_suid=False,
        needs_site=0,
        site_must_exist=0,
        confirm=False,
        args_text="VERSION",
        options=[],
        description="Sets the default version of OMD which will be used by new sites",
        confirm_text="",
    ),
    Command(
        command="version",
        only_root=False,
        no_suid=False,
        needs_site=0,
        site_must_exist=0,
        confirm=False,
        args_text="[SITE]",
        options=[
            Option("bare", "b", False, "output plain text optimized for parsing"),
        ],
        description="Show version of OMD",
        confirm_text="",
    ),
    Command(
        command="versions",
        only_root=False,
        no_suid=False,
        needs_site=0,
        site_must_exist=0,
        confirm=False,
        args_text="",
        options=[
            Option("bare", "b", False, "output plain text optimized for parsing"),
        ],
        description="List installed OMD versions",
        confirm_text="",
    ),
    Command(
        command="sites",
        only_root=False,
        no_suid=False,
        needs_site=0,
        site_must_exist=0,
        confirm=False,
        args_text="",
        options=[
            Option("bare", "b", False, "output plain text for easy parsing"),
        ],
        description="Show list of sites",
        confirm_text="",
    ),
    Command(
        command="create",
        only_root=True,
        no_suid=False,
        needs_site=1,
        site_must_exist=0,
        confirm=False,
        args_text="",
        options=[
            Option("uid", "u", True, "create site user with UID ARG"),
            Option("gid", "g", True, "create site group with GID ARG"),
            Option("admin-password", None, True, "set initial password instead of generating one"),
            Option("reuse", None, False, "do not create a site user, reuse existing one"),
            Option(
                "no-init", "n", False, "leave new site directory empty (a later omd init does this"
            ),
            Option("no-autostart", "A", False, "set AUTOSTART to off (useful for test sites)"),
            Option(
                "apache-reload",
                None,
                False,
                "Issue a reload of the system apache instead of a restart",
            ),
            Option("no-tmpfs", None, False, "set TMPFS to off"),
            Option(
                "tmpfs-size",
                "t",
                True,
                "specify the maximum size of the tmpfs (defaults to 50% of RAM), examples: 500M, 20G, 60%",
            ),
        ],
        description="Create a new site (-u UID, -g GID)",
        confirm_text="This command performs the following actions on your system:\n"
        "- Create the system user <SITENAME>\n"
        "- Create the system group <SITENAME>\n"
        "- Create and populate the site home directory\n"
        "- Restart the system wide apache daemon\n"
        "- Add tmpfs for the site to fstab and mount it",
    ),
    Command(
        command="init",
        only_root=True,
        no_suid=False,
        needs_site=1,
        site_must_exist=1,
        confirm=False,
        args_text="",
        options=[
            Option(
                "apache-reload",
                None,
                False,
                "Issue a reload of the system apache instead of a restart",
            ),
        ],
        description="Populate site directory with default files and enable the site",
        confirm_text="",
    ),
    Command(
        command="rm",
        only_root=True,
        no_suid=True,
        needs_site=1,
        site_must_exist=1,
        confirm=True,
        args_text="",
        options=[
            Option("reuse", None, False, "assume --reuse on create, do not delete site user/group"),
            Option("kill", None, False, "kill processes of the site before deleting it"),
            Option(
                "apache-reload",
                None,
                False,
                "Issue a reload of the system apache instead of a restart",
            ),
        ],
        description="Remove a site (and its data)",
        confirm_text="PLEASE NOTE: This action removes all configuration files\n"
        "             and variable data of the site.\n"
        "\n"
        "In detail the following steps will be done:\n"
        "- Stop all processes of the site\n"
        "- Unmount tmpfs of the site\n"
        "- Remove tmpfs of the site from fstab\n"
        "- Remove the system user <SITENAME>\n"
        "- Remove the system group <SITENAME>\n"
        "- Remove the site home directory\n"
        "- Restart the system wide apache daemon\n",
    ),
    Command(
        command="disable",
        only_root=True,
        no_suid=False,
        needs_site=1,
        site_must_exist=1,
        confirm=False,
        args_text="",
        options=[
            Option("kill", None, False, "kill processes using tmpfs before unmounting it"),
        ],
        description="Disable a site (stop it, unmount tmpfs, remove Apache hook)",
        confirm_text="",
    ),
    Command(
        command="enable",
        only_root=True,
        no_suid=False,
        needs_site=1,
        site_must_exist=1,
        confirm=False,
        args_text="",
        options=[],
        description="Enable a site (reenable a formerly disabled site)",
        confirm_text="",
    ),
    Command(
        command="update-apache-config",
        only_root=True,
        no_suid=False,
        needs_site=1,
        site_must_exist=1,
        confirm=False,
        args_text="",
        options=[],
        description="Update the system apache config of a site (and reload apache)",
        confirm_text="",
    ),
    Command(
        command="mv",
        only_root=True,
        no_suid=False,
        needs_site=1,
        site_must_exist=1,
        confirm=False,
        args_text="NEWNAME",
        options=[
            Option("uid", "u", True, "create site user with UID ARG"),
            Option("gid", "g", True, "create site group with GID ARG"),
            Option("reuse", None, False, "do not create a site user, reuse existing one"),
            Option(
                "conflict",
                None,
                True,
                "non-interactive conflict resolution. ARG is install, keepold, abort or ask",
            ),
            Option(
                "tmpfs-size",
                "t",
                True,
                "specify the maximum size of the tmpfs (defaults to 50% of RAM), examples: 500M, 20G, 60%",
            ),
            Option(
                "apache-reload",
                None,
                False,
                "Issue a reload of the system apache instead of a restart",
            ),
        ],
        description="Rename a site",
        confirm_text="",
    ),
    Command(
        command="cp",
        only_root=True,
        no_suid=False,
        needs_site=1,
        site_must_exist=1,
        confirm=False,
        args_text="NEWNAME",
        options=[
            Option("uid", "u", True, "create site user with UID ARG"),
            Option("gid", "g", True, "create site group with GID ARG"),
            Option("reuse", None, False, "do not create a site user, reuse existing one"),
        ]
        + exclude_options
        + [
            Option(
                "conflict",
                None,
                True,
                "non-interactive conflict resolution. ARG is install, keepold, abort or ask",
            ),
            Option(
                "tmpfs-size",
                "t",
                True,
                "specify the maximum size of the tmpfs (defaults to 50% of RAM), examples: 500M, 20G, 60%",
            ),
            Option(
                "apache-reload",
                None,
                False,
                "Issue a reload of the system apache instead of a restart",
            ),
        ],
        description="Make a copy of a site",
        confirm_text="",
    ),
    Command(
        command="update",
        only_root=False,
        no_suid=False,
        needs_site=1,
        site_must_exist=1,
        confirm=False,
        args_text="",
        options=[
            Option(
                "conflict",
                None,
                True,
                "non-interactive conflict resolution. ARG is install, keepold, abort or ask",
            )
        ],
        description="Update site to other version of OMD",
        confirm_text="",
    ),
    Command(
        command="start",
        only_root=False,
        no_suid=False,
        needs_site=2,
        site_must_exist=1,
        confirm=False,
        args_text="[SERVICE]",
        options=[
            Option("version", "V", True, "only start services having version ARG"),
            Option("parallel", "p", False, "Invoke start of sites in parallel"),
        ],
        description="Start services of one or all sites",
        confirm_text="",
    ),
    Command(
        command="stop",
        only_root=False,
        no_suid=False,
        needs_site=2,
        site_must_exist=1,
        confirm=False,
        args_text="[SERVICE]",
        options=[
            Option("version", "V", True, "only stop sites having version ARG"),
            Option("parallel", "p", False, "Invoke stop of sites in parallel"),
        ],
        description="Stop services of site(s) and terminate processes owned by the site user",
        confirm_text="",
    ),
    Command(
        command="restart",
        only_root=False,
        no_suid=False,
        needs_site=2,
        site_must_exist=1,
        confirm=False,
        args_text="[SERVICE]",
        options=[
            Option("version", "V", True, "only restart sites having version ARG"),
        ],
        description="Restart services of site(s)",
        confirm_text="",
    ),
    Command(
        command="reload",
        only_root=False,
        no_suid=False,
        needs_site=2,
        site_must_exist=1,
        confirm=False,
        args_text="[SERVICE]",
        options=[
            Option("version", "V", True, "only reload sites having version ARG"),
        ],
        description="Reload services of site(s)",
        confirm_text="",
    ),
    Command(
        command="status",
        only_root=False,
        no_suid=False,
        needs_site=2,
        site_must_exist=1,
        confirm=False,
        args_text="[SERVICE]",
        options=[
            Option("version", "V", True, "show only sites having version ARG"),
            Option("auto", None, False, "show only sites with AUTOSTART = on"),
            Option("bare", "b", False, "output plain format optimized for parsing"),
        ],
        description="Show status of services of site(s)",
        confirm_text="",
    ),
    Command(
        command="config",
        only_root=False,
        no_suid=False,
        needs_site=1,
        site_must_exist=1,
        confirm=False,
        args_text="...",
        options=[],
        description="Show and set site configuration parameters.\n\n\
Usage:\n\
 omd config [site]\t\t\tinteractive mode\n\
 omd config [site] show\t\t\tshow configuration settings\n\
 omd config [site] set VAR VAL\t\tset specific setting VAR to VAL",
        confirm_text="",
    ),
    Command(
        command="diff",
        only_root=False,
        no_suid=False,
        needs_site=1,
        site_must_exist=1,
        confirm=False,
        args_text="([RELBASE])",
        options=[
            Option("bare", "b", False, "output plain diff format, no beautifying"),
        ],
        description="Shows differences compared to the original version files",
        confirm_text="",
    ),
    Command(
        command="su",
        only_root=True,
        no_suid=False,
        needs_site=1,
        site_must_exist=1,
        confirm=False,
        args_text="",
        options=[],
        description="Run a shell as a site-user",
        confirm_text="",
    ),
    Command(
        command="umount",
        only_root=False,
        no_suid=False,
        needs_site=2,
        site_must_exist=1,
        confirm=False,
        args_text="",
        options=[
            Option("version", "V", True, "unmount only sites with version ARG"),
            Option("kill", None, False, "kill processes using the tmpfs before unmounting it"),
        ],
        description="Umount ramdisk volumes of site(s)",
        confirm_text="",
    ),
    Command(
        command="backup",
        only_root=False,
        no_suid=True,
        needs_site=1,
        site_must_exist=1,
        confirm=False,
        args_text="[SITE] [-|ARCHIVE_PATH]",
        options=exclude_options
        + [
            Option("no-compression", None, False, "do not compress tar archive"),
        ],
        description="Create a backup tarball of a site, writing it to a file or stdout",
        confirm_text="",
    ),
    Command(
        command="restore",
        only_root=False,
        no_suid=False,
        needs_site=0,
        site_must_exist=0,
        confirm=False,
        args_text="[SITE] handler=[-|ARCHIVE_PATH]",
        options=[
            Option("uid", "u", True, "create site user with UID ARG"),
            Option("gid", "g", True, "create site group with GID ARG"),
            Option("reuse", None, False, "do not create a site user, reuse existing one"),
            Option(
                "kill",
                None,
                False,
                "kill processes of site when reusing an existing one before restoring",
            ),
            Option(
                "apache-reload",
                None,
                False,
                "Issue a reload of the system apache instead of a restart",
            ),
            Option(
                "conflict",
                None,
                True,
                "non-interactive conflict resolution. ARG is install, keepold, abort or ask",
            ),
            Option(
                "tmpfs-size",
                "t",
                True,
                "specify the maximum size of the tmpfs (defaults to 50% of RAM)",
            ),
        ],
        description="Restores the backup of a site to an existing site or creates a new site",
        confirm_text="",
    ),
    Command(
        command="cleanup",
        only_root=True,
        no_suid=False,
        needs_site=0,
        site_must_exist=0,
        confirm=False,
        args_text="",
        options=[],
        description="Uninstall all Check_MK versions that are not used by any site.",
        confirm_text="",
    ),
]


def _get_command(command_arg: str) -> Command:
    for command in COMMANDS:
        if command.command == command_arg:
            return command

    sys.stderr.write("omd: no such command: %s\n" % command_arg)
    main_help()
    sys.exit(1)


def _parse_command_options(
    description: str, args: Arguments, options: list[Option]
) -> tuple[Arguments, CommandOptions]:
    # Give a short overview over the command specific options
    # when the user specifies --help:
    if len(args) and args[0] in ["-h", "--help"]:
        sys.stdout.write("%s\n\n" % description)
        if options:
            sys.stdout.write("Possible options for this command:\n")
        else:
            sys.stdout.write("No options for this command\n")
        for option in options:
            args_text = "{}--{}".format(
                "-%s," % option.short_opt if option.short_opt else "",
                option.long_opt,
            )
            sys.stdout.write(
                " %-15s %3s  %s\n"
                % (args_text, option.needs_arg and "ARG" or "", option.description)
            )
        sys.exit(0)

    set_options: CommandOptions = {}

    while len(args) >= 1 and args[0][0] == "-" and len(args[0]) > 1:
        opt = args[0]
        args = args[1:]

        found_options: list[Option] = []
        if opt.startswith("--"):
            # Handle --foo=bar
            if "=" in opt:
                opt, optarg = opt.split("=", 1)
                args = [optarg] + args
                for option in options:
                    if option.long_opt == opt[2:] and not option.needs_arg:
                        sys.exit("The option %s does not take an argument" % opt)

            for option in options:
                if option.long_opt == opt[2:]:
                    found_options = [option]
        else:
            for char in opt:
                for option in options:
                    if option.short_opt == char:
                        found_options.append(option)

        if not found_options:
            sys.exit("Invalid option '%s'" % opt)

        for option in found_options:
            arg = None
            if option.needs_arg:
                if not args:
                    sys.exit("Option '%s' needs an argument." % opt)
                arg = args[0]
                args = args[1:]
            set_options[option.long_opt] = arg
    return (args, set_options)


def is_root() -> bool:
    return os.getuid() == 0


def main_help() -> None:
    sys.stdout.write(
        "Manage multiple monitoring sites comfortably with OMD. The Open Monitoring Distribution.\n"
    )

    if is_root():
        sys.stdout.write("Usage (called as root):\n\n")
    else:
        sys.stdout.write("Usage (called as site user):\n\n")

    for (
        command,
        only_root,
        _no_suid,
        needs_site,
        _site_must_exist,
        _confirm,
        synopsis,
        _command_options,
        descr,
        _confirm_text,
    ) in COMMANDS:
        if only_root and not is_root():
            continue

        if is_root():
            if needs_site == 2:
                synopsis = "[SITE] " + synopsis
            elif needs_site == 1:
                synopsis = "SITE " + synopsis

        synopsis_width = "23" if is_root() else "16"
        sys.stdout.write((" omd %-10s %-" + synopsis_width + "s %s\n") % (command, synopsis, descr))
    sys.stdout.write(
        "\nGeneral Options:\n"
        " -V <version>                    set specific version, useful in combination with update/create\n"
        " -f, --force                     use force mode, useful in combination with update\n"
        " omd COMMAND -h, --help          show available options of COMMAND\n"
    )


def _exec_omd_version_of_site(site_name: str, site_home: str, command: Command) -> None:
    if command.site_must_exist and not site_exists(Path(site_home)):
        sys.exit(
            "omd: The site '%s' does not exist. You need to execute "
            "omd as root or site user." % site_name
        )
    # Commands operating on an existing site *must* run omd in
    # the same version as the site has! Sole exception: update.
    # That command must be run in the target version
    if command.site_must_exist and command.command != "update":
        v = version_from_site_dir(Path(site_home))
        if v is None:  # Site has no home directory or version link
            if command.command == "rm":
                sys.stdout.write(
                    "WARNING: This site has an empty home directory and is not\n"
                    "assigned to any OMD version. You are running version %s.\n"
                    % omdlib.__version__
                )
            elif command.command != "init":
                sys.exit(
                    "This site has an empty home directory /omd/sites/%s.\n"
                    "If you have created that site with 'omd create --no-init %s'\n"
                    "then please first do an 'omd init %s'." % (3 * (site_name,))
                )
        elif omdlib.__version__ != v:
            exec_other_omd(v)


def parse_args_or_exec_other_omd(
    main_args: list[str],
) -> tuple[str | None, GlobalOptions, Command, CommandOptions, Arguments]:
    global_opts, main_args = parse_global_opts(main_args)
    if global_opts.version is not None and global_opts.version != omdlib.__version__:
        # Switch to other version of bin/omd
        exec_other_omd(global_opts.version)

    if len(main_args) < 1:
        main_help()
        sys.exit(1)

    args = main_args[1:]

    command = _get_command(main_args[0])

    # Parse command options. We need to do this now in order to know
    # if a site name has been specified or not.
    args, command_options = _parse_command_options(command.description, args, command.options)

    # Some commands need a site to be specified. If we are
    # called as root, this must be done explicitly. If we
    # are site user, the site name is our user name
    if command.needs_site > 0:
        if is_root():
            if len(args) >= 1:
                site_name = args[0]
                args = args[1:]
            elif command.needs_site == 1:
                sys.exit("omd: please specify site.")
            else:
                site_name = None
        else:
            site_name = site_name_from_uid()
    else:
        site_name = None

    if site_name is not None:
        _exec_omd_version_of_site(site_name, SitePaths.from_site_name(site_name).home, command)
    return site_name, global_opts, command, command_options, args
