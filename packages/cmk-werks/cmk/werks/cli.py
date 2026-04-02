#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk development script to manage Werks"""

# mypy: disable-error-code="comparison-overlap"

import argparse
import datetime
import errno
import os
import shlex
import subprocess
import sys
import time
import traceback
from collections.abc import Iterator, Sequence
from contextlib import suppress
from functools import cache
from pathlib import Path
from typing import Literal, NamedTuple

from . import load_werk as cmk_werks_load_werk
from . import parse_werk
from .config import Config, load_config, try_load_current_version_from_defines_make
from .format import format_as_markdown_werk
from .in_out_elements import (
    ask_user_if_not_provided,
    bail_out,
    get_input,
    get_tty_size,
    grep_colors,
    TTY_BG_WHITE,
    TTY_BLUE,
    TTY_BOLD,
    TTY_CYAN,
    TTY_GREEN,
    TTY_NORMAL,
    TTY_RED,
)
from .models import EditionV2, EditionV3
from .parse import WerkV3ParseResult
from .schemas.werk import Stash, Werk, WerkId

WerkVersion = Literal["v1", "markdown"]

WerkMetadata = dict[str, str]

WERK_ID_RANGES = {
    # start is inclusive, end is exclusive, as it is in range()
    "cma": [(9_000, 10_000)],
    "cmk": [(10_000, 1_000_000)],
    "cloudmk": [(1_000_000, 2_000_000)],
}


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    # BLAME
    parser_blame = subparsers.add_parser("blame", help="Show who worked on a Werk")
    parser_blame.add_argument(
        "id",
        nargs="?",
        type=int,
        help="Werk ID",
        default=None,
    )
    parser_blame.set_defaults(func=main_blame)

    # DELETE
    parser_delete = subparsers.add_parser("delete", help="delete Werk(s)")
    parser_delete.add_argument(
        "id",
        nargs="+",
        type=int,
        help="Werk ID",
    )
    parser_delete.set_defaults(func=main_delete)

    # EDIT
    parser_edit = subparsers.add_parser("edit", help="open Werk in editor")
    parser_edit.add_argument(
        "id",
        nargs="?",
        type=int,
        help="Werk ID (defaults to newest)",
    )
    parser_edit.set_defaults(func=main_edit)

    # EXPORT
    parser_export = subparsers.add_parser("export", help="List Werks")
    parser_export.add_argument(
        "-r",
        "--reverse",
        action="store_true",
        help="reverse order",
    )
    parser_export.add_argument(
        "filter",
        nargs="*",
        help="filter for edition, component, state, class, or target version",
    )
    parser_export.set_defaults(func=lambda args: main_list(args, "csv"))

    # GREP
    parser_grep = subparsers.add_parser(
        "grep",
        help="show Werks containing all of the given keywords",
    )
    parser_grep.add_argument("-v", "--verbose", action="store_true")
    parser_grep.add_argument(
        "keywords",
        nargs="+",
        help="keywords to grep",
    )
    parser_grep.set_defaults(func=main_grep)

    # IDS
    parser_ids = subparsers.add_parser(
        "ids",
        help="Show the number of reserved Werk IDs or reserve new Werk IDs",
    )
    parser_ids.add_argument(
        "count",
        nargs="?",
        type=int,
        help="number of Werks to reserve",
    )
    parser_ids.set_defaults(func=main_fetch_ids)

    # LIST
    parser_list = subparsers.add_parser("list", help="List Werks")
    parser_list.add_argument(
        "-r",
        "--reverse",
        action="store_true",
        help="reverse order",
    )
    parser_list.add_argument(
        "filter",
        nargs="*",
        help="filter for edition, component, state, class, or target version",
    )
    parser_list.set_defaults(func=lambda args: main_list(args, "console"))

    # NEW
    parser_new = subparsers.add_parser("new", help="Create a new Werk")
    parser_new.add_argument(
        "custom_files",
        nargs="*",
        help="files passed to 'git commit'",
    )
    parser_new.add_argument(
        "--title",
        help="Werk title",
    )
    parser_new.add_argument(
        "--class",
        dest="class_",
        choices=[item[0] for item in get_config().classes],
        help="Werk class",
    )
    parser_new.add_argument(
        "--edition",
        choices=[item[0] for item in get_config().editions],
        help="Checkmk edition",
    )
    parser_new.add_argument(
        "--component",
        # Can't use get_edition_components here, because it needs the edition which is an argument itself
        # But will be validated in main_create before creating the Werk
        choices=[item[0] for item in get_config().all_components()],
        help="Component name (see .werks/config)",
    )
    parser_new.add_argument(
        "--level",
        choices=[item[0] for item in get_config().levels],
        help="Werk level",
    )
    parser_new.add_argument(
        "--compatible",
        choices=[item[0] for item in get_config().compatible],
        help="Compatibility",
    )
    parser_new.add_argument(
        "--description-file",
        type=Path,
        help="Read description from file. Provide absolute path",
    )
    parser_new.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode. Will fail if required information is missing.",
    )
    parser_new.set_defaults(func=main_new)

    # PICK
    parser_pick = subparsers.add_parser(
        "pick",
        aliases=["cherry-pick"],
        help="Pick these Werks",
    )
    parser_pick.add_argument(
        "-n",
        "--no-commit",
        action="store_true",
        help="do not commit at the end",
    )
    parser_pick.add_argument(
        "commit",
        nargs="+",
        help="Pick these commits",
    )
    parser_pick.set_defaults(func=main_pick)

    # SHOW
    parser_show = subparsers.add_parser("show", help="Show several Werks")
    parser_show.add_argument(
        "ids",
        nargs="*",
        help="Show these Werks, or 'all' for all, of leave out for last",
    )
    parser_show.set_defaults(func=main_show)

    # PREVIEW
    parser_preview = subparsers.add_parser("preview", help="Preview html rendering of a Werk")
    parser_preview.add_argument(
        "id",
    )
    parser_preview.set_defaults(func=main_preview)

    # MEISTERWERK (removed)
    parser_meisterwerk = subparsers.add_parser(
        "meisterwerk", help="[Removed] The meisterwerk service has been shut down"
    )
    parser_meisterwerk.set_defaults(func=main_meisterwerk_removed)

    # URL
    parser_url = subparsers.add_parser("url", help="Show the online URL of a Werk")
    parser_url.add_argument("id", type=int, help="Werk ID")
    parser_url.set_defaults(func=main_url)

    return parser.parse_args(argv)


def werk_path_by_id(werk_id: WerkId) -> Path:
    # NOTE: this only works for existing werks!
    path = Path(str(werk_id.id))
    if path.exists():
        return path
    path = Path(f"{werk_id.id}.md")
    if path.exists():
        return path
    raise RuntimeError(f"Can not find Werk with id={werk_id.id}")


BASE_DIR = ""


def goto_werksdir() -> None:
    global BASE_DIR
    BASE_DIR = os.path.abspath(".")
    while not os.path.exists(".werks") and os.path.abspath(".") != "/":
        os.chdir("..")

    try:
        os.chdir(".werks")
    except OSError:
        sys.stderr.write("Cannot find directory .werks\n")
        sys.exit(1)


def get_last_werk() -> WerkId:
    try:
        with open(".last", encoding="utf-8") as f_last:
            return WerkId(int(f_last.read()))
    except Exception as e:
        raise RuntimeError("No last Werk known. Please specify id.") from e


@cache
def get_config() -> Config:
    current_version = try_load_current_version_from_defines_make(Path("../defines.make"))
    return load_config(Path("config"), current_version=current_version)


def load_werks() -> dict[WerkId, Werk]:
    werks = {}
    for entry in Path(".").iterdir():
        if (werk_id := entry.name.removesuffix(".md")).isdigit():
            try:
                werks[WerkId(int(werk_id))] = load_werk(entry)
            except Exception as e:
                sys.stderr.write(f"ERROR: Skipping invalid Werk {werk_id}: {e}\n")
    return werks


def save_last_werkid(wid: WerkId) -> None:
    try:
        with open(".last", "w", encoding="utf-8") as f:
            f.write(f"{wid}\n")
    except OSError:
        pass


@cache
def git_modified_files() -> set[WerkId]:
    # this is called from `werk list` via werk_is_modified
    # so we can assume, that this won't change during runtime of this script
    modified = set()
    for line in os.popen("git status --porcelain"):
        if line[0] in "AM" and ".werks/" in line:
            try:
                wid = line.rsplit("/", 1)[-1].strip()
                modified.add(WerkId(int(wid)))
            except Exception:
                pass
    return modified


def werk_is_modified(werkid: WerkId) -> bool:
    return werkid in git_modified_files()


def werk_exists(werkid: WerkId) -> bool:
    return os.path.exists(str(werkid)) or os.path.exists(f"{werkid}.md")


def load_werk(werk_path: Path) -> Werk:
    parsed = parse_werk(
        file_content=werk_path.read_text(encoding="utf-8"), file_name=werk_path.name
    )

    werk = Werk(
        path=werk_path,
        id=WerkId(int(werk_path.name.removesuffix(".md"))),
        content=parsed,
    )

    return werk


def save_werk(werk: Werk, werk_version: WerkVersion, destination: Path | None = None) -> None:
    if destination is None:
        destination = werk.path
    with destination.open("w") as f:
        if werk_version == "markdown":
            f.write(format_as_markdown_werk(werk.content))
        else:
            raise NotImplementedError(
                "Writing v1 Werks is no longer supported. "
                "Please use the Werk tool of the 2.2.0 branch.\n"
                "Contact the component owner of 'Development Tools' if this blocks you."
            )

    save_last_werkid(werk.id)


def change_werk_version(werk_path: Path, new_version: str, werk_version: WerkVersion) -> None:
    werk = load_werk(werk_path)
    werk.content.metadata["version"] = new_version
    save_werk(werk, werk_version)
    _git_add(werk_path)


def _git_add(werk_path: Path) -> None:
    os.system(f"git add {werk_path}")  # nosec B605 # BNS:a52d7f


def git_move(source: Path, destination: Path) -> None:
    subprocess.check_call(["git", "mv", str(source), str(destination)])


def git_commit(werk: Werk, custom_files: list[str]) -> None:
    title = werk.content.metadata["title"]
    for classid, _classname, prefix in get_config().classes:
        if werk.content.metadata["class"] == classid:
            if prefix:
                title = f"{prefix} {title}"

    title = f"{werk.content.metadata['id'].rjust(5, '0')} {title}"

    if custom_files:
        files_to_commit = custom_files
        default_files = [".werks"]
        for entry in default_files:
            files_to_commit.append(f"{git_top_level()}/{entry}")

        os.chdir(BASE_DIR)
        cmd = "git commit {} -m {}".format(
            " ".join(files_to_commit),
            shlex.quote(title + "\n\n" + werk.content.description),
        )
        os.system(cmd)  # nosec B605 # BNS:a52d7f

    else:
        if something_in_git_index():
            dash_a = ""
            os.system(f"cd '{git_top_level()}' ; git add .werks")  # nosec B605 # BNS:a52d7f
        else:
            dash_a = "-a"

        cmd = "git commit {} -m {}".format(
            dash_a,
            shlex.quote(title + "\n\n" + werk.content.description),
        )
        os.system(cmd)  # nosec B605 # BNS:a52d7f


def git_top_level() -> str:
    with subprocess.Popen(["git", "rev-parse", "--show-toplevel"], stdout=subprocess.PIPE) as info:
        return info.communicate()[0].decode().split()[0]


def something_in_git_index() -> bool:
    for line in os.popen("git status --porcelain"):
        if line[0] == "M":
            return True
    return False


def add_comment(werk: Werk, title: str, comment: str) -> None:
    werk.content.metadata["description"] += f"""
{time.strftime("%F %T")}: {title}
{comment}"""


def list_werk(werk: Werk) -> None:
    if werk_is_modified(werk.id):
        bold = TTY_BOLD + TTY_CYAN + "(*) "
    else:
        bold = ""
    _lines, cols = get_tty_size()
    title = werk.content.metadata["title"][: cols - 45]
    sys.stdout.write(
        f"{format_werk_id(werk.id)} "
        f"{str(werk.date.date()):9} "
        f"{colored_class(werk.content.metadata['class'], 8)} "
        f"{werk.content.metadata['edition']:3} "
        f"{werk.content.metadata['component']:13} "
        f"{werk.content.metadata['compatible']:6} "
        f"{TTY_BOLD}{werk.content.metadata['level']}{TTY_NORMAL} "
        f"{werk.content.metadata['version']:8} "
        f"{bold}{title}{TTY_NORMAL}\n"
    )


def format_werk_id(werk_id: WerkId) -> str:
    return TTY_BG_WHITE + TTY_BLUE + f"{werk_id}" + TTY_NORMAL


def colored_class(classname: str, digits: int) -> str:
    if classname == "fix":
        return TTY_BOLD + TTY_RED + ("%-" + str(digits) + "s") % classname + TTY_NORMAL
    return ("%-" + str(digits) + "s") % classname


def show_werk(werk: Werk) -> None:
    list_werk(werk)
    sys.stdout.write(f"\n{werk.content.description}\n")


def main_list(args: argparse.Namespace, fmt: str) -> None:
    # arguments are tags from state, component and class. Multiple values
    # in one class are orred. Multiple types are anded.

    werks: list[Werk] = list(load_werks().values())
    versions = sorted({werk.content.metadata["version"] for werk in werks})

    filters: dict[str, list[str]] = {}

    for a in args.filter:
        if a == "current":
            a = get_config().current_version

        hit = False
        for tp, values in [
            ("edition", get_config().editions),
            ("component", get_config().all_components()),
            ("level", get_config().levels),
            ("class", get_config().classes),
            ("version", versions),
            ("compatible", get_config().compatible),
        ]:
            for v in values:  # type: ignore[attr-defined] # all of them are iterable.
                if isinstance(v, tuple):
                    v = v[0]
                if v.startswith(a):
                    entries = filters.get(tp, [])
                    entries.append(v)
                    filters[tp] = entries
                    hit = True
                    break
            if hit:
                break
        if not hit:
            bail_out(
                f"No such edition, component, state, class, or target version: {a}",
                0,
            )

    # Filter
    newwerks = []
    for werk in werks:
        skip = False
        for tp, entries in filters.items():
            value = werk.content.metadata[tp]
            if tp == "edition":
                with suppress(ValueError):
                    value = EditionV3.from_v2(EditionV2(value)).value
            if value not in entries:
                skip = True
                break
        if not skip:
            newwerks.append(werk)

    werks = sorted(newwerks, key=lambda w: w.date, reverse=args.reverse)

    # Output
    if fmt == "console":
        for werk in werks:
            list_werk(werk)
    else:
        output_csv(werks)


# CSV Table has the following columns:
# Component;ID;Title;Class;Effort
def output_csv(werks: list[Werk]) -> None:
    def line(*parts: int | str) -> None:
        sys.stdout.write('"' + '";"'.join(map(str, parts)) + '"\n')

    nr = 1
    for entry in get_config().components:
        if len(entry) != 2:
            bail_out(f"invalid component {entry!r}")
        name, alias = entry

        line("", "", "", "", "")

        total_effort = 0
        for werk in werks:
            if werk.content.metadata["component"] == name:
                total_effort += werk_effort(werk)
        line("", f"{nr}. {alias}", "", total_effort)
        nr += 1

        for werk in werks:
            if werk.content.metadata["component"] == name:
                line(
                    werk.content.metadata["id"],
                    werk.content.metadata["title"],
                    werk_class(werk),
                    werk_effort(werk),
                )
                line(
                    "",
                    werk.content.description.replace("\n", " ").replace('"', "'"),
                    "",
                    "",
                )


def werk_class(werk: Werk) -> str:
    cl = werk.content.metadata["class"]
    for entry in get_config().classes:
        # typing: why would this be? LH: Tuple[str, str, str], RH: str
        if entry == cl:
            return cl

        if entry[0] == cl:
            return entry[1]
    return cl


def werk_effort(werk: Werk) -> int:
    return int(werk.content.metadata.get("effort", "0"))


def main_show(args: argparse.Namespace) -> None:
    if "all" in args.ids:
        ids = list(load_werks().keys())
    else:
        ids = [WerkId(i) for i in args.ids] or [get_last_werk()]

    for wid in ids:
        if wid != ids[0]:
            sys.stdout.write(
                "-------------------------------------------------------------------------------\n"
            )
        show_werk(load_werk(werk_path_by_id(wid)))
    save_last_werkid(ids[-1])


def get_edition_components(edition: str) -> list[tuple[str, str]]:
    return get_config().components + get_config().edition_components.get(edition, [])


_SECURITY_WERK_DESCRIPTION_TEMPLATE = """\
<!--
TODO: Please fill in the template below. Reach out to team security for help and missing info.
Remove this and the other comments.
-->

<!--
Description of the problem and fix, as usual. Feel free to use sub-sections.
-->
<PROBLEM DESCRIPTION>

### Who is Affected

<!--
Help users understand if this issue is relevant to their setup. Often, everyone is affected. Then say just that.
However, if only some editions, specific configurations or optional components are affected it helps users a lot to know that their setup is safe.
-->
<AFFECTED SETUPS>

### Affected Checkmk Versions

<!--
List all versions affected, regardless if they receive the fix or not.
Start from the most recent release (including beta releases) until most recent EOL, inclusive.
-->
* 2.5.0
* 2.4.0
* 2.3.0
* 2.2.0 (EOL)

### Vulnerability Management

We have rated the issue with a CVSS Score of <CVSS SCORE> <SEVERITY> (`CVSS:4.0/<VECTOR>`) and assigned `<CVE ID>`.

We thank <REPORTER NAME> (<AFFILIATION>) for reporting this issue.
<!-- Or: This issue was found by internal review. -->
<!-- Or: This issue was found in a commissioned penetration test conducted by <PENTESTER COMPANY>. -->

### Indicators of Compromise

<!--
Describe how users can check if the vulnerability has been exploited on their system (usually checking specific logs, files, ...).
Leave out the whole section if nothing can be said.
-->
<INDICATORS>

### Mitigations

<!--
Can users take any mitigating measures besides updating? For example disabling affected features.
Leave out the whole section if nothing can be said.
-->
<MITIGATIONS>

"""

WERK_NOTES = """
    .---Werk----------------------------------------------------------------------.
    |                                                                             |
    |             The Werk is intended for the user/admin!!                       |
    |                                                                             |
    |    It should be obvious from the title if a user/admin is affected.         |
    |    Describe what needs to be done in the details. You can also note if no   |
    |    user interaction is required. If necessary, add technical details.       |
    |                                                                             |
    '-----------------------------------------------------------------------------'

"""


def main_new(args: argparse.Namespace) -> None:
    if args.non_interactive:
        if not all(
            [
                args.title,
                args.class_,
                args.edition,
                args.component,
                args.level,
                args.compatible,
                args.description_file,
            ]
        ):
            bail_out(
                "In non-interactive mode, all of the following arguments are required: "
                "--title, --class, --edition, --component, --level, --compatible, and --description-file.\n"
            )
    else:
        sys.stdout.write(TTY_GREEN + WERK_NOTES + TTY_NORMAL)

    stash = Stash.load_from_file()
    werk_id = stash.pick_id(project=get_config().project)

    metadata: WerkMetadata = {}

    metadata["id"] = str(werk_id)
    metadata["date"] = datetime.datetime.now(datetime.UTC).isoformat()
    metadata["version"] = get_config().current_version
    metadata["title"] = args.title or get_input("Title")
    if metadata["title"] == "":
        sys.stderr.write("Cancelled.\n")
        sys.exit(0)
    metadata["class"] = ask_user_if_not_provided("Class", get_config().classes, args.class_)
    metadata["edition"] = ask_user_if_not_provided("Edition", get_config().editions, args.edition)
    metadata["component"] = ask_user_if_not_provided(
        "Component", get_edition_components(metadata["edition"]), args.component
    )
    metadata["level"] = ask_user_if_not_provided("Level", get_config().levels, args.level)
    # For now, we want to display the legacy values "compat" and "incomp" in the choice, to not
    # break existing workflows of users, but we keep the impact minimal by only translating them
    # back and forth locally here.
    yes = get_config().compatible[0][0]
    no = get_config().compatible[1][0]
    metadata["compatible"] = {"compat": yes, "incomp": no}[
        ask_user_if_not_provided(
            "Compatible",
            ["compat", "incomp"],
            {yes: "compat", no: "incomp"}.get(args.compatible),
        )
    ]
    if args.description_file:
        description = args.description_file.read_text(encoding="utf-8")
    elif metadata["class"] == "security":
        description = _SECURITY_WERK_DESCRIPTION_TEMPLATE
    else:
        # Interactive modes opens the editor, so the user can add
        # the description to the freshly created werk
        description = "\n"

    werk_path = get_werk_filename(werk_id, get_werk_file_version())
    werk = Werk(
        id=werk_id,
        path=werk_path,
        content=WerkV3ParseResult(metadata=metadata, description=description),
    )
    save_werk(werk, get_werk_file_version())

    if args.non_interactive:
        if get_config().create_commit:
            _git_add(werk_path)
            git_commit(werk, args.custom_files)
    else:
        edit_werk(werk_path, args.custom_files)

    stash.free_id(werk_id)
    stash.dump_to_file()

    sys.stdout.write(f"Werk {format_werk_id(werk_id)} saved.\n")
    sys.stderr.write(
        "NOTE: It is your responsibility to verify the Werk quality.\n"
        "You can use the '/werk' Claude Code skill for automated checks.\n"
    )


def main_meisterwerk_removed(_args: argparse.Namespace) -> None:
    sys.stderr.write(
        "ERROR: The 'meisterwerk' service has been shut down and this subcommand has been removed.\n"
        "Please use the '/werk' skill in Claude Code instead.\n"
    )
    sys.exit(1)


def get_werk_arg(arg: WerkId | None) -> WerkId:
    wid = get_last_werk() if arg is None else arg

    werk = load_werk(werk_path_by_id(wid))
    if not werk:
        bail_out("No such Werk.\n")
    save_last_werkid(wid)
    return wid


def main_blame(args: argparse.Namespace) -> None:
    wid = get_werk_arg(WerkId(args.id))
    os.system(f"git blame {werk_path_by_id(wid)}")  # nosec B605 # BNS:a52d7f


def main_url(args: argparse.Namespace) -> None:
    wid = get_werk_arg(WerkId(args.id))
    sys.stdout.write(get_config().online_url % wid.id + "\n")


def main_delete(args: argparse.Namespace) -> None:
    werks = [WerkId(i) for i in args.id]

    for werk_id in werks:
        if not werk_exists(werk_id):
            bail_out(f"There is no Werk {format_werk_id(werk_id)}.")

        werk_path = werk_path_by_id(werk_id)
        werk_to_be_removed_title = load_werk(werk_path).content.metadata["title"]
        try:
            subprocess.check_call(["git", "rm", "-f", f"{werk_path}"])
        except subprocess.CalledProcessError as exc:
            sys.stdout.write(f"Error removing Werk file: {exc}.\n")
            continue
        sys.stdout.write(f"Deleted Werk {format_werk_id(werk_id)} ({werk_to_be_removed_title}).\n")
        stash = Stash.load_from_file()
        stash.add_id(werk_id, project=get_config().project)
        stash.dump_to_file()
        sys.stdout.write(f"You lucky bastard now own the Werk ID {format_werk_id(werk_id)}.\n")


def grep(line: str, kw: str, n: int) -> str | None:
    lc = kw.lower()
    i = line.lower().find(lc)
    if i == -1:
        return None
    col = grep_colors[n % len(grep_colors)]
    return line[0:i] + col + line[i : i + len(kw)] + TTY_NORMAL + line[i + len(kw) :]


def main_grep(args: argparse.Namespace) -> None:
    for werk in load_werks().values():
        one_kw_didnt_match = False
        title = werk.content.metadata["title"]
        lines = werk.content.description.split("\n")
        bodylines = set()

        # *all* of the keywords must match in order for the
        # werk to be displayed
        i = 0
        for kw in args.keywords:
            i += 1
            this_kw_matched = False

            # look for keyword in title
            match = grep(title, kw, i)
            if match:
                werk.content.metadata["title"] = match
                title = match
                this_kw_matched = True

            # look for keyword in description
            for j, line in enumerate(lines):
                match = grep(line, kw, i)
                if match:
                    bodylines.add(j)
                    lines[j] = match
                    this_kw_matched = True

            if not this_kw_matched:
                one_kw_didnt_match = True

        if not one_kw_didnt_match:
            list_werk(werk)
            if args.verbose:
                for x in sorted(list(bodylines)):
                    sys.stdout.write(f"  {lines[x]}\n")


def main_edit(args: argparse.Namespace) -> None:
    werkid = WerkId(args.id) if args.id is not None else get_last_werk()
    edit_werk(
        werk_path_by_id(werkid), None, commit=False
    )  # custom files are pointless if commit=False
    save_last_werkid(werkid)


def edit_werk(werk_path: Path, custom_files: list[str] | None = None, commit: bool = True) -> None:
    if custom_files is None:
        custom_files = []
    if not werk_path.exists():
        bail_out("No Werk with this id.")
    editor = os.getenv("EDITOR")
    if not editor:
        for p in ["/usr/bin/editor", "/usr/bin/vim", "/bin/vi"]:
            if os.path.exists(p):
                editor = p
                break
    if not editor:
        bail_out("No editor available (please set EDITOR).\n")

    initial_werk_text = werk_path.read_text(encoding="utf-8")
    number_of_lines_in_werk = initial_werk_text.count("\n")
    werk = None

    while True:
        if os.system(f"bash -c '{editor} +{number_of_lines_in_werk} {werk_path}'") != 0:  # nosec B605 # BNS:a52d7f
            bail_out("Editor returned error, something is very wrong!")

        try:
            werk = load_werk(werk_path)
            # validate the werk, to make sure the commit part at the bottom will work
            cmk_werks_load_werk(file_content=werk.path.read_text(), file_name=werk.path.name)
            break
        except Exception:
            sys.stdout.write(initial_werk_text + "\n\n")
            sys.stdout.write(traceback.format_exc() + "\n\n")
            sys.stdout.write(
                "Could not load the Werk, see exception above.\n"
                "You may copy the initial Werk text above the exception to fix your Werk.\n"
                "Will reopen the editor, after you acknowledged with enter\n"
            )
            input()

    if werk is None:
        bail_out("This should not have happened, Werk is None during edit_werk.")

    _git_add(werk_path)
    if commit and get_config().create_commit:
        git_commit(werk, custom_files)


def main_pick(args: argparse.Namespace) -> None:
    for commit_id in args.commit:
        werk_cherry_pick(commit_id, args.no_commit, get_werk_file_version())


class WerkToPick(NamedTuple):
    source: Path
    destination: Path


def werk_cherry_pick(commit_id: str, no_commit: bool, werk_version: WerkVersion) -> None:
    # First get the werk_id
    try:
        result = subprocess.run(
            ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        sys.stderr.buffer.write(exc.stderr)
        sys.exit(exc.returncode)
    found_werk_path: WerkToPick | None = None
    for line in result.stdout.splitlines():
        filename = Path(line.decode("utf-8"))
        if filename.parent.name == ".werks" and filename.name.removesuffix(".md").isdigit():
            # we os.chdir into the werks folder, so now we can not use the git paths as is
            found_werk_path = WerkToPick(
                source=Path(filename.name),
                destination=get_werk_filename(
                    WerkId(int(filename.name.removesuffix(".md"))), werk_version
                ),
            )

    if found_werk_path is not None:
        if found_werk_path.source.exists() or found_werk_path.destination.exists():
            bail_out(
                f"Trying to pick Werk {found_werk_path.source} to {found_werk_path.destination}, "
                "but Werk already present. Aborted."
            )

    # Cherry-pick the commit in question from the other branch
    cmd = ["git", "cherry-pick"]
    if no_commit:
        cmd.append("--no-commit")
    cmd.append(commit_id)
    pick = subprocess.run(cmd, check=False)

    if found_werk_path is not None:
        # Find werks that have been cherry-picked and change their version
        # to our current checkmk version.

        # maybe we need to adapt the filename:
        if found_werk_path.source.suffix != found_werk_path.destination.suffix:
            # but this also means we need to change the content
            werk = load_werk(found_werk_path.source)
            git_move(found_werk_path.source, found_werk_path.destination)
            save_werk(werk, werk_version, found_werk_path.destination)
            # git add will be executed by change_werk_version

        # Change the werk's version before checking the pick return code.
        # Otherwise the dev may forget to change the version
        change_werk_version(found_werk_path.destination, get_config().current_version, werk_version)
        sys.stdout.write(
            f"Changed version of Werk {found_werk_path.destination} "
            f"to {get_config().current_version}.\n"
        )

    if pick.returncode:
        # Exit with the result of the pick. This may be a merge conflict, so
        # other tools may need to know about this.
        sys.exit(pick.returncode)

    # Commit
    if found_werk_path is not None:
        # This allows for picking regular commits as well
        if not no_commit:
            subprocess.run(["git", "add", found_werk_path.destination.name], check=True)
            subprocess.run(["git", "commit", "--no-edit", "--amend"], check=True)
        else:
            sys.stdout.write("We don't commit yet. Here is the status:\n")
            sys.stdout.write("Please commit with git commit -C '{commit_id}'\n\n")
            subprocess.run(["git", "status"], check=True)


def current_branch() -> str:
    result = subprocess.run(["git", "branch", "--show-current"], check=True, capture_output=True)
    return result.stdout.strip().decode("utf-8")


def current_repo() -> str:
    return (
        list(os.popen("git config --get remote.origin.url"))[0]
        .strip()
        .split("@")[-1]
        .removesuffix(".git")
    )


def _reserve_werk_ids(
    ranges: list[tuple[int, int]], first_free: int, count: int
) -> tuple[int, list[WerkId]]:
    buffer: list[WerkId] = []
    while ranges:
        start, end = ranges.pop(0)
        if first_free > end:
            # range already complelty exhausted
            continue
        if first_free < start:
            # first_free is not in our range!
            raise RuntimeError("Configuration error: first_free no in range!")
        new_first_free = first_free + count
        if new_first_free < end:
            return new_first_free, buffer + list(
                WerkId(i) for i in range(first_free, new_first_free)
            )
        buffer += list(WerkId(i) for i in range(first_free, end))
        count -= end - first_free
        if not ranges:
            raise RuntimeError(
                "Not enough ids available, please add a fresh range to WERK_ID_RANGES"
            )
        first_free = ranges[0][0]

    raise RuntimeError("could not allocate ids")


def main_fetch_ids(args: argparse.Namespace) -> None:
    stash = Stash.load_from_file()

    if args.count is None:
        per_project = "\n".join(
            f"{project}: {len(ids)}" for project, ids in stash.ids_by_project.items()
        )
        sys.stdout.write(f"You have {stash.count()} reserved IDs:\n{per_project}\n")
        sys.exit(0)

    if current_branch() != get_config().branch or current_repo() != get_config().repo:
        bail_out(
            f"Werk IDs can only be reserved on the '{get_config().branch}' branch on "
            f"'{get_config().repo}', not '{current_branch()}' on '{current_repo()}'."
        )

    # Get the start werk_id to reserve
    try:
        with open("first_free", encoding="utf-8") as f:
            first_free = int(f.read().strip())
    except (OSError, ValueError) as e:
        raise RuntimeError("Could not load .werks/first_free") from e

    project = get_config().project
    if project not in WERK_ID_RANGES:
        raise RuntimeError(f"project {project} has no Werk ID range")
    ranges = WERK_ID_RANGES[project].copy()

    new_first_free, fresh_ids = _reserve_werk_ids(ranges, first_free, args.count)

    stash = Stash.load_from_file()
    for werk_id in fresh_ids:
        stash.add_id(werk_id, project=project)
    stash.dump_to_file()

    # Store the new reserved werk ids
    with open("first_free", "w", encoding="utf-8") as f:
        f.write(str(new_first_free) + "\n")

    sys.stdout.write(
        f"Reserved {args.count} additional IDs now. You have {stash.count()} reserved IDs now.\n"
    )

    if get_config().create_commit:
        if os.system(f"git commit --no-verify -m 'Reserved {args.count} Werk IDS' .") == 0:  # nosec B605 # BNS:a52d7f
            sys.stdout.write("--> Successfully committed reserved Werk IDS. Please push it soon!\n")
        else:
            bail_out("Cannot commit.")
    else:
        sys.stdout.write(
            "--> Reserved Werk IDs. Commit and push it soon, otherwise someone else reserves the same IDs!\n"
        )


def main_preview(args: argparse.Namespace) -> None:
    werk_path = werk_path_by_id(WerkId(args.id))
    werk = cmk_werks_load_werk(
        file_content=Path(werk_path).read_text(encoding="utf-8"), file_name=werk_path.name
    )

    def meta_data() -> Iterator[str]:
        for item in werk.__class__.model_fields:
            if item in {"title", "description"}:
                continue
            yield f"<dt>{item}<dt><dd>{getattr(werk, item)}</dd>"

    definition_list = "\n".join(meta_data())
    sys.stdout.write(
        f'<!DOCTYPE html><html lang="en" style="font-family:sans-serif;">'
        "<head>"
        f"<title>Preview of Werk {args.id}</title>"
        "</head>"
        f'<body style="background-color:#ccc; max-width:1600px; padding: 10px; margin:auto;">'
        f"<h1>{werk.title}</h1>"
        f'<div style="background-color:#fff; padding: 10px;">{werk.description}</div>'
        f"<dl>{definition_list}</dl>"
        "</body>"
        "</html>\n"
    )


def get_werk_file_version() -> WerkVersion:
    """
    as long as there is a single markdown file,
    we assume we should create and pick markdown Werks.
    """
    for path in Path(".").iterdir():
        if path.name.endswith(".md") and path.name.removesuffix(".md").isdigit():
            return "markdown"
    if {p.name for p in Path(".").iterdir()} == {"config", "first_free"}:
        # folder is empty, there are only mandatory files
        return "markdown"
    return "v1"


def get_werk_filename(werk_id: WerkId, werk_version: WerkVersion) -> Path:
    return Path(f"{werk_id.id}.md" if werk_version == "markdown" else str(werk_id.id))


#                    _
#    _ __ ___   __ _(_)_ __
#   | '_ ` _ \ / _` | | '_ \
#   | | | | | | (_| | | | | |
#   |_| |_| |_|\__,_|_|_| |_|
#


def main(argv: Sequence[str] | None = None) -> None:
    try:
        goto_werksdir()
        main_args = parse_arguments(argv or sys.argv[1:])
        main_args.func(main_args)
    except OSError as e:
        # ignore BrokenPipeError: [Errno 32] Broken pipe
        if e.errno != errno.EPIPE:
            raise


if __name__ == "__main__":
    main()
