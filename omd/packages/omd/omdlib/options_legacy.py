#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: DO NOT MODIFY THIS FILE. This file is only for backwards compatibility with older omd
# versions, which are affected by a security vulnerability, see https://checkmk.com/werk/18891
# Unless you work on extending the backwards compatibility, you are looking at the wrong file.

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Final, NamedTuple

from omdlib.global_options import GlobalOptions
from omdlib.options import ExecOtherOmd, RmCommand, SuCommand
from omdlib.version_utils import werk_18891_warning


class Option(NamedTuple):
    long_opt: str
    short_opt: str | None
    needs_arg: bool
    description: str


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


exclude_options = [
    Option("no-rrds", None, False, "do not copy RRD files (performance data)"),
    Option("no-logs", None, False, "do not copy the monitoring history and log files"),
    Option(
        "no-past",
        "N",
        False,
        "do not copy RRD files, agent files, the monitoring history, and log files",
    ),
]


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
            Option(
                "admin-password",
                None,
                True,
                "set initial password instead of generating one",
            ),
            Option("reuse", None, False, "do not create a site user, reuse existing one"),
            Option(
                "no-init",
                "n",
                False,
                "leave new site directory empty (a later omd init does this",
            ),
            Option(
                "no-autostart",
                "A",
                False,
                "set AUTOSTART to off (useful for test sites)",
            ),
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
            Option(
                "reuse",
                None,
                False,
                "assume --reuse on create, do not delete site user/group",
            ),
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
                "non-interactive conflict resolution. ARG is install, keepold, abort, ignore or ask",
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
        description=(
            "Start services of one or all sites. This command reports one of the following exit codes.\n"
            " * 0: All services started successfully.\n"
            " * 1: The command failed to start any service.\n"
            " * 2: When targeting a single site, this indicates that one or more services failed to start. "
            "When targeting multiple sites, this indicates that an unspecific error occurred."
        ),
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
            Option(
                "kill",
                None,
                False,
                "kill processes using the tmpfs before unmounting it",
            ),
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


def _parse_global_arguments_dispatcher(args: Sequence[str]) -> tuple[GlobalOptions, int]:
    global_args_count = 0
    version: str | None = None
    force = False
    verbose = False
    interactive = False
    while (global_args_count < len(args)) and (token := args[global_args_count]).startswith("-"):
        flags = [token[2:]] if token.startswith("--") else list(token[1:])
        for flag in flags:
            match flag:
                case "V" | "version":
                    if global_args_count >= len(args):
                        sys.exit(f"Option {flag} needs an argument.")
                    global_args_count += 1
                    version = args[global_args_count]
                case "f" | "force":
                    force = True
                    interactive = False
                case "i" | "interactive":
                    force = False
                    interactive = True
                case "v" | "verbose":
                    verbose = True
                case _:
                    sys.exit(
                        f"Invalid global option {token}.\nCall omd help for available options."
                    )
        global_args_count += 1
    return GlobalOptions(
        version=version, verbose=verbose, force=force, interactive=interactive
    ), global_args_count


def _to_args(global_opts: GlobalOptions) -> list[str]:
    args = []
    match global_opts.force, global_opts.interactive:
        case False, False:
            pass
        case True, False:
            args.append("--force")
        case False, True:
            args.append("--interactive")
        case True, True:
            raise NotImplementedError()
    if global_opts.verbose:
        args.append("--verbose")
    return args


@dataclass(frozen=True)
class DispatcherError:
    message: str


@dataclass(frozen=True)
class ArgsToDispatch:
    version: str
    target_site: str
    command: list[str]


def _parse_command_options(  # pylint: disable=too-many-branches
    description: str, args: Sequence[str], options: list[Option]
) -> tuple[Sequence[str], dict[str, str | None]]:
    # Give a short overview over the command specific options
    # when the user specifies --help or -h:
    if any(arg in ["-h", "--help"] for arg in args):
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

    set_options: dict[str, str | None] = {}

    while len(args) >= 1 and args[0][0] == "-" and len(args[0]) > 1:
        opt = args[0]
        args = args[1:]

        if opt.startswith("--"):
            # Handle --foo=bar
            if "=" in opt:
                opt, optarg = opt.split("=", 1)
                found_option = next((o for o in options if o.long_opt == opt[2:]), None)
                if found_option is None:
                    sys.exit("Invalid option '%s'" % opt)
                if not found_option.needs_arg:
                    sys.exit("The option %s does not take an argument" % opt)
                set_options[found_option.long_opt] = optarg
            else:
                found_option = next((o for o in options if o.long_opt == opt[2:]), None)
                if found_option is None:
                    sys.exit("Invalid option '%s'" % opt)

                optarg = None
                if found_option.needs_arg:
                    if not args:
                        sys.exit("Option '%s' needs an argument." % opt)
                    optarg, args = args[0], args[1:]
                set_options[found_option.long_opt] = optarg
        else:
            found_options: list[Option] = []
            for char in opt:
                for option in options:
                    if option.short_opt == char:
                        found_options.append(option)

            if not found_options:
                sys.exit("Invalid option '%s'" % opt)

            for option in found_options:
                optarg = None
                if option.needs_arg:
                    if not args:
                        sys.exit("Option '%s' needs an argument." % opt)
                    optarg, args = args[0], args[1:]
                set_options[option.long_opt] = optarg
    return (args, set_options)


def main_help() -> None:
    sys.stdout.write(
        "Manage multiple monitoring sites comfortably with OMD. The Open Monitoring Distribution.\n"
    )

    sys.stdout.write("Usage (called as root):\n\n")

    for (
        command,
        _only_root,
        _no_suid,
        needs_site,
        _site_must_exist,
        _confirm,
        synopsis,
        _command_options,
        descr,
        _confirm_text,
    ) in COMMANDS:
        if needs_site == 2:
            synopsis = "[SITE] " + synopsis
        elif needs_site == 1:
            synopsis = "SITE " + synopsis

        synopsis_width = "23"
        sys.stdout.write((" omd %-10s %-" + synopsis_width + "s %s\n") % (command, synopsis, descr))
    sys.stdout.write(
        "\nGeneral Options:\n"
        " -V <version>                    set specific version, useful in combination with update/create\n"
        " -f, --force                     use force mode, useful in combination with update\n"
        " omd COMMAND -h, --help          show available options of COMMAND\n"
    )


def _get_command(command_arg: str) -> Command:
    for command in COMMANDS:
        if command.command == command_arg:
            return command

    sys.stderr.write("omd: no such command: %s\n" % command_arg)
    main_help()
    sys.exit(1)


def parse_arguments_dispatcher(  # pylint: disable=too-many-branches
    target_version: str, args: Sequence[str]
) -> ArgsToDispatch | DispatcherError | ExecOtherOmd | SuCommand | RmCommand:
    # Function is only valid in root context.
    global_opts, global_args_count = _parse_global_arguments_dispatcher(args)
    if global_args_count == len(args):
        main_help()
        sys.exit(1)
    command = _get_command(args[global_args_count])
    remaining_arguments, options = _parse_command_options(
        command.description, args[global_args_count + 1 :], command.options
    )
    args_before_site_name_count = len(args) - len(remaining_arguments)
    match command.command:
        case "help" | "version" | "versions" | "sites" | "cleanup":
            # These commands are safe to execute unconditionally.
            return ExecOtherOmd(version=target_version)
        case "setversion":
            # No vulnerability, but allows changing to vulnerable version.
            return DispatcherError(message=werk_18891_warning(target_version))
        case "restore":
            return DispatcherError(message=werk_18891_warning(target_version))
        case (
            "create"
            | "init"
            | "disable"
            | "enable"
            | "update-apache-config"
            | "mv"
            | "cp"
            | "backup"
        ):
            # These commands cannot be correctly executed after root privileges are dropped.
            # And we can't use the vulnerable versions omd these commands without dropping the
            # privileges first.
            return DispatcherError(message=werk_18891_warning(target_version))
        case "rm":
            if args_before_site_name_count >= len(args):
                sys.exit("omd: please specify site.")
            target_site = args[args_before_site_name_count]
            # Allow `omd rm` with the wrong version. This behaviour is already happening,
            # if your site is missing the version indicator, thus is probably acceptable. All
            # supported sites have the correct behaviour anyway.
            return RmCommand(target_site, global_opts, options)
        case "su":
            if args_before_site_name_count >= len(args):
                sys.exit("omd: please specify site.")
            target_site = args[args_before_site_name_count]
            # Allow running with the wrong version. This is the only option for a user with a
            # vulnerable version anyway. Might as well automated it.
            return SuCommand(target_site)
        case (
            "start"
            | "stop"
            | "restart"
            | "reload"
            | "status"
            | "umount"
            | "update"
            | "config"
            | "diff"
        ):
            if args_before_site_name_count >= len(args):
                if command.needs_site == 2:
                    # Invoking `omd -V 2.3.0p24 start` as root is not allowed.
                    return DispatcherError(message=werk_18891_warning(target_version))
                sys.exit("omd: please specify site.")
            target_site = args[args_before_site_name_count]
            return ArgsToDispatch(
                version=target_version,
                target_site=target_site,
                command=[
                    *_to_args(global_opts),
                    *args[global_args_count:args_before_site_name_count],
                    *args[args_before_site_name_count + 1 :],
                ],
            )
        case _:
            raise NotImplementedError()
