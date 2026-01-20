#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Checkmk development script to manage werks"""

# pylint: disable=too-many-lines

import argparse
import ast
import datetime
import fcntl
import json
import os
import shlex
import struct
import subprocess
import sys
import termios
import time
import tty
from collections.abc import Iterator, Sequence
from functools import cache
from pathlib import Path
from typing import Literal, NamedTuple, NoReturn

from . import load_werk as cmk_werks_load_werk
from . import parse_werk
from .config import Config, load_config
from .convert import werkv1_metadata_to_werkv2_metadata
from .format import format_as_werk_v1, format_as_werk_v2
from .models import Edition, EditionV3
from .parse import WerkV2ParseResult, WerkV3ParseResult


def edition_v3_to_v2(edition: EditionV3) -> Edition:
    mapping = {
        EditionV3.COMMUNITY: Edition.CRE,
        EditionV3.PRO: Edition.CEE,
        EditionV3.ULTIMATE: Edition.CCE,
        EditionV3.ULTIMATEMT: Edition.CME,
        EditionV3.CLOUD: Edition.CSE,
    }
    return mapping[edition]


class WerkId:
    __slots__ = ("__id",)

    def __init__(self, id: int):  # pylint: disable=redefined-builtin
        self.__id = id

    def __str__(self) -> str:
        return f"{self.__id:0>5}"

    @property
    def id(self) -> int:
        return self.__id

    def __eq__(self, other: object) -> bool:
        if isinstance(other, self.__class__):
            return self.id == other.id
        return False

    def __hash__(self) -> int:
        return hash(self.__id)


class Werk(NamedTuple):
    path: Path
    id: WerkId
    content: WerkV2ParseResult | WerkV3ParseResult

    @property
    def date(self) -> datetime.datetime:
        return datetime.datetime.fromisoformat(self.content.metadata["date"])


WerkVersion = Literal["v1", "v2", "v3"]

WerkMetadata = dict[str, str]


RESERVED_IDS_FILE_PATH = f"{os.getenv('HOME')}/.cmk-werk-ids"

# colored output, if stdout is a tty
if sys.stdout.isatty():
    TTY_RED = "\033[31m"
    TTY_GREEN = "\033[32m"
    TTY_YELLOW = "\033[33m"
    TTY_BLUE = "\033[34m"
    TTY_MAGENTA = "\033[35m"
    TTY_CYAN = "\033[36m"
    TTY_WHITE = "\033[37m"
    TTY_BG_RED = "\033[41m"
    TTY_BG_GREEN = "\033[42m"
    TTY_BG_YELLOW = "\033[43m"
    TTY_BG_BLUE = "\033[44m"
    TTY_BG_MAGENTA = "\033[45m"
    TTY_BG_CYAN = "\033[46m"
    TTY_BG_WHITE = "\033[47m"
    TTY_BOLD = "\033[1m"
    TTY_UNDERLINE = "\033[4m"
    TTY_NORMAL = "\033[0m"

else:
    TTY_RED = ""
    TTY_GREEN = ""
    TTY_YELLOW = ""
    TTY_BLUE = ""
    TTY_MAGENTA = ""
    TTY_CYAN = ""
    TTY_WHITE = ""
    TTY_BG_RED = ""
    TTY_BG_GREEN = ""
    TTY_BG_BLUE = ""
    TTY_BG_MAGENTA = ""
    TTY_BG_CYAN = ""
    TTY_BG_WHITE = ""
    TTY_BOLD = ""
    TTY_UNDERLINE = ""
    TTY_NORMAL = ""


grep_colors = [
    TTY_BOLD + TTY_MAGENTA,
    TTY_BOLD + TTY_CYAN,
    TTY_BOLD + TTY_GREEN,
]


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    # BLAME
    parser_blame = subparsers.add_parser("blame", help="Show who worked on a werk")
    parser_blame.add_argument(
        "id",
        nargs="?",
        type=int,
        help="werk ID",
        default=None,
    )
    parser_blame.set_defaults(func=main_blame)

    # DELETE
    parser_delete = subparsers.add_parser("delete", help="delete werk(s)")
    parser_delete.add_argument(
        "id",
        nargs="+",
        type=int,
        help="werk ID",
    )
    parser_delete.set_defaults(func=main_delete)

    # EDIT
    parser_edit = subparsers.add_parser("edit", help="open werk in editor")
    parser_edit.add_argument(
        "id",
        nargs="?",
        type=int,
        help="werk ID (defaults to newest)",
    )
    parser_edit.set_defaults(func=main_edit)

    # EXPORT
    parser_export = subparsers.add_parser("export", help="List werks")
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
        help="show werks containing all of the given keywords",
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
        help="Show the number of reserved werk IDs or reserve new werk IDs",
    )
    parser_ids.add_argument(
        "count",
        nargs="?",
        type=int,
        help="number of werks to reserve",
    )
    parser_ids.set_defaults(func=main_fetch_ids)

    # LIST
    parser_list = subparsers.add_parser("list", help="List werks")
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
    parser_new = subparsers.add_parser("new", help="Create a new werk")
    parser_new.add_argument(
        "custom_files",
        nargs="*",
        help="files passed to 'git commit'",
    )
    parser_new.set_defaults(func=main_new)

    # PICK
    parser_pick = subparsers.add_parser(
        "pick",
        aliases=["cherry-pick"],
        help="Pick these werks",
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
    parser_show = subparsers.add_parser("show", help="Show several werks")
    parser_show.add_argument(
        "ids",
        nargs="*",
        help="Show these werks, or 'all' for all, of leave out for last",
    )
    parser_show.set_defaults(func=main_show)

    # PREVIEW
    parser_preview = subparsers.add_parser("preview", help="Preview html rendering of a werk")
    parser_preview.add_argument(
        "id",
    )
    parser_preview.set_defaults(func=main_preview)

    # URL
    parser_url = subparsers.add_parser("url", help="Show the online URL of a werk")
    parser_url.add_argument("id", type=int, help="werk ID")
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
    raise RuntimeError(f"Can not find werk with id={werk_id.id}")


def get_tty_size() -> tuple[int, int]:
    try:
        ws = bytearray(8)
        fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, ws)
        lines, columns, _x, _y = struct.unpack("HHHH", ws)
        if lines > 0 and columns > 0:
            return lines, columns
    except OSError:
        pass
    return (24, 99999)


def bail_out(text: str, exit_code: int = 1) -> NoReturn:
    sys.stderr.write(text + "\n")
    sys.exit(exit_code)


BASE_DIR = ""


def goto_werksdir() -> None:
    global BASE_DIR  # pylint: disable=global-statement
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
        raise RuntimeError("No last werk known. Please specify id.") from e


@cache
def get_config() -> Config:
    return load_config(Path("config"), Path("../defines.make"))


def load_werks() -> dict[WerkId, Werk]:
    werks = {}
    for entry in Path(".").iterdir():
        if (werk_id := entry.name.removesuffix(".md")).isdigit():
            try:
                werks[WerkId(int(werk_id))] = load_werk(entry)
            except Exception as e:  # pylint: disable=broad-exception-caught
                sys.stderr.write(f"ERROR: Skipping invalid werk {werk_id}: {e}\n")
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
            except Exception:  # pylint: disable=broad-exception-caught
                pass
    return modified


def werk_is_modified(werkid: WerkId) -> bool:
    return werkid in git_modified_files()


def werk_exists(werkid: WerkId) -> bool:
    return os.path.exists(str(werkid))


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
        if werk_version in ("v2", "v3"):
            f.write(format_as_werk_v2(werk.content))
        else:
            assert isinstance(werk.content, WerkV2ParseResult)
            f.write(format_as_werk_v1(werk.content))

    save_last_werkid(werk.id)


def change_werk_version(werk_path: Path, new_version: str, werk_version: WerkVersion) -> None:
    werk = load_werk(werk_path)
    if isinstance(werk.content, WerkV3ParseResult):
        edition_str = werk.content.metadata.get("edition", "")
        werk.content.metadata["edition"] = edition_v3_to_v2(EditionV3(edition_str)).value
        sys.stdout.write(
            f"Converted edition from '{edition_str}' to '{werk.content.metadata['edition']}'.\n"
        )
    werk.content.metadata["version"] = new_version
    save_werk(werk, werk_version)
    git_add(werk)


def git_add(werk: Werk) -> None:
    os.system(f"git add {werk.path}")  # nosec


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
        os.system(cmd)  # nosec

    else:
        if something_in_git_index():
            dash_a = ""
            os.system(f"cd '{git_top_level()}' ; git add .werks")  # nosec
        else:
            dash_a = "-a"

        cmd = "git commit {} -m {}".format(
            dash_a,
            shlex.quote(title + "\n\n" + werk.content.description),
        )
        os.system(cmd)  # nosec


def git_top_level() -> str:
    with subprocess.Popen(["git", "rev-parse", "--show-toplevel"], stdout=subprocess.PIPE) as info:
        return str(info.communicate()[0].split()[0])


def something_in_git_index() -> bool:
    for line in os.popen("git status --porcelain"):
        if line[0] == "M":
            return True
    return False


def next_werk_id() -> WerkId:
    my_werk_ids = get_werk_ids()
    if not my_werk_ids:
        bail_out(
            "You have no werk IDS left. "
            'You can reserve 10 additional Werk IDS with "werk ids 10".'
            "Important: You need to activate the .venv before (source .venv/bin/activate)"
        )
    return my_werk_ids[0]


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


def main_list(args: argparse.Namespace, fmt: str) -> None:  # pylint: disable=too-many-branches
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
            if werk.content.metadata[tp] not in entries:
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
    def line(*l: int | str) -> None:
        sys.stdout.write('"' + '";"'.join(map(str, l)) + '"\n')

    nr = 1
    for entry in get_config().components:
        # TODO: Our config has been validated, so we should be able to nuke the isinstance horror
        # below.
        if isinstance(entry, tuple) and len(entry) == 2:
            name, alias = entry
        elif isinstance(entry, str):  # type: ignore[unreachable]  # TODO: Hmmm...
            name, alias = entry, entry
        else:
            bail_out(f"invalid component {entry!r}")

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
        if entry == cl:  # type: ignore[comparison-overlap]
            return cl

        if isinstance(entry, tuple) and entry[0] == cl:
            return entry[1]
    return cl


def werk_effort(werk: Werk) -> int:
    return int(werk.content.metadata.get("effort", "0"))


def main_show(args: argparse.Namespace) -> None:
    if "all" in args.ids:
        ids = list(load_werks().keys())
    else:
        ids = [WerkId(id) for id in args.ids] or [get_last_werk()]

    for wid in ids:
        if wid != ids[0]:
            sys.stdout.write(
                "-------------------------------------------------------------------------------\n"
            )
        show_werk(load_werk(werk_path_by_id(wid)))
    save_last_werkid(ids[-1])


def get_input(what: str, default: str = "") -> str:
    sys.stdout.write(f"{what}: ")
    sys.stdout.flush()
    value = sys.stdin.readline().strip()
    if value == "":
        return default
    return value


def getch() -> str:
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


def input_choice(
    what: str, choices: list[str] | list[tuple[str, str]] | list[tuple[str, str, str]]
) -> str:
    next_index = 0
    ctc = {}
    texts = []
    for choice in choices:
        if isinstance(choice, tuple):
            choice = choice[0]

        added = False

        # Find an identifying character for the input choice. In case all possible
        # characters are already used start using unique numbers
        for c in str(choice):
            if c not in ".-_/" and c not in ctc:
                ctc[c] = choice
                texts.append(str(choice).replace(c, TTY_BOLD + c + TTY_NORMAL, 1))
                added = True
                break

        if not added:
            ctc[str(next_index)] = choice
            texts.append(f"{TTY_BOLD}{next_index}{TTY_NORMAL}:{choice}")
            next_index += 1

    while True:
        sys.stdout.write(f"{what} ({', '.join(texts)}): ")
        sys.stdout.flush()
        c = getch()
        if c in ctc:
            sys.stdout.write(f" {TTY_BOLD}{ctc[c]}{TTY_NORMAL}\n")
            return ctc[c]

        sys.stdout.write("\n")


def get_edition_components(edition: str) -> list[tuple[str, str]]:
    return get_config().components + get_config().edition_components.get(edition, [])


WERK_NOTES = """
    .---Werk----------------------------------------------------------------------.
    |                                                                             |
    |             The werk is intended for the user/admin!!                       |
    |                                                                             |
    |    From the titel it should be obvious if the user/admin is affected.       |
    |    Describe what needs to be done in the details. You can also note if no   |
    |    user interaction is required. If necessary add technical details.        |
    |                                                                             |
    '-----------------------------------------------------------------------------'

"""


def main_new(args: argparse.Namespace) -> None:
    sys.stdout.write(TTY_GREEN + WERK_NOTES + TTY_NORMAL)

    metadata: WerkMetadata = {}
    werk_id = next_werk_id()
    metadata["id"] = str(werk_id)

    # this is the metadata format of werkv1
    metadata["date"] = str(int(time.time()))
    metadata["version"] = get_config().current_version
    metadata["title"] = get_input("Title")
    if metadata["title"] == "":
        sys.stderr.write("Cancelled.\n")
        sys.exit(0)
    metadata["class"] = input_choice("Class", get_config().classes)
    metadata["edition"] = input_choice("Edition", get_config().editions)
    metadata["component"] = input_choice("Component", get_edition_components(metadata["edition"]))
    metadata["level"] = input_choice("Level", get_config().levels)
    metadata["compatible"] = input_choice("Compatible", get_config().compatible)

    werk_path = get_werk_filename(werk_id, get_werk_file_version())
    werk = Werk(
        id=werk_id,
        path=werk_path,
        content=WerkV2ParseResult(
            metadata=werkv1_metadata_to_werkv2_metadata(metadata), description="\n"
        ),
    )

    save_werk(werk, get_werk_file_version())
    git_add(werk)
    invalidate_my_werkid(werk_id)
    edit_werk(werk_path, args.custom_files)

    sys.stdout.write(f"Werk {format_werk_id(werk_id)} saved.\n")


def get_werk_arg(arg: WerkId | None) -> WerkId:
    wid = get_last_werk() if arg is None else arg

    werk = load_werk(werk_path_by_id(wid))
    if not werk:
        bail_out("No such werk.\n")
    save_last_werkid(wid)
    return wid


def main_blame(args: argparse.Namespace) -> None:
    wid = get_werk_arg(WerkId(args.id))
    os.system(f"git blame {werk_path_by_id(wid)}")  # nosec


def main_url(args: argparse.Namespace) -> None:
    wid = get_werk_arg(WerkId(args.id))
    sys.stdout.write(get_config().online_url % wid.id + "\n")


def main_delete(args: argparse.Namespace) -> None:
    werks = [WerkId(i) for i in args.id]

    for werk_id in werks:
        if not werk_exists(werk_id):
            bail_out(f"There is no werk {format_werk_id(werk_id)}.")

        werk_path = werk_path_by_id(werk_id)
        werk_to_be_removed_title = load_werk(werk_path).content.metadata["title"]
        try:
            subprocess.check_call(["git", "rm", "-f", f"{werk_path}"])
        except subprocess.CalledProcessError as exc:
            sys.stdout.write(f"Error removing werk file: {exc}.\n")
            continue
        sys.stdout.write(f"Deleted werk {format_werk_id(werk_id)} ({werk_to_be_removed_title}).\n")
        my_ids = get_werk_ids()
        my_ids.append(werk_id)
        store_werk_ids(my_ids)
        sys.stdout.write(f"You lucky bastard now own the werk ID {format_werk_id(werk_id)}.\n")


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
        bail_out("No werk with this id.")
    editor = os.getenv("EDITOR")
    if not editor:
        for p in ["/usr/bin/editor", "/usr/bin/vim", "/bin/vi"]:
            if os.path.exists(p):
                editor = p
                break
    if not editor:
        bail_out("No editor available (please set EDITOR).\n")

    number_of_lines_in_werk = werk_path.read_text(encoding="utf-8").count("\n")
    if os.system(f"bash -c '{editor} +{number_of_lines_in_werk} {werk_path}'") == 0:  # nosec
        werk = load_werk(werk_path)
        git_add(werk)
        if commit:
            git_commit(werk, custom_files)


def main_pick(args: argparse.Namespace) -> None:
    for commit_id in args.commit:
        werk_cherry_pick(commit_id, args.no_commit, get_werk_file_version())


class WerkToPick(NamedTuple):
    source: Path
    destination: Path


def werk_cherry_pick(commit_id: str, no_commit: bool, werk_version: WerkVersion) -> None:
    # First get the werk_id
    result = subprocess.run(
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_id],
        capture_output=True,
        check=True,
    )
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
                f"Trying to pick werk {found_werk_path.source} to {found_werk_path.destination}, "
                "but werk already present. Aborted."
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
            # Converting from .md (v2/v3) to non-.md (v1) format
            werk = load_werk(found_werk_path.source)

            git_move(found_werk_path.source, found_werk_path.destination)
            save_werk(werk, werk_version, found_werk_path.destination)
            # git add will be executed by change_werk_version

        # Change the werk's version before checking the pick return code.
        # Otherwise the dev may forget to change the version
        change_werk_version(found_werk_path.destination, get_config().current_version, werk_version)
        sys.stdout.write(
            f"Changed version of werk {found_werk_path.destination} "
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


def get_werk_ids() -> list[WerkId]:
    try:
        content = Path(RESERVED_IDS_FILE_PATH).read_text(encoding="utf-8")
        if content[0] == "[":
            return [WerkId(i) for i in ast.literal_eval(content)]
        return [WerkId(i) for i in json.loads(content)["ids_by_project"]["cmk"]]
    except Exception as e:  # pylint: disable=broad-exception-caught
        sys.stdout.write(
            f"\n{TTY_RED}Could not load werk ids, fall back to no ids. "
            f"Error was:\n{e}.{TTY_NORMAL}\n\n"
        )
        return []


def invalidate_my_werkid(wid: WerkId) -> None:
    ids = get_werk_ids()
    ids.remove(wid)
    store_werk_ids(ids)
    if not ids:
        sys.stdout.write(f"\n{TTY_RED}This was your last reserved ID.{TTY_NORMAL}\n\n")


def store_werk_ids(l: list[WerkId]) -> None:
    content = Path(RESERVED_IDS_FILE_PATH).read_text(encoding="utf-8")
    werk_ids_as_integer = [i.id for i in l]
    with open(RESERVED_IDS_FILE_PATH, "w", encoding="utf-8") as f:
        if content[0] == "[":
            f.write(repr(werk_ids_as_integer) + "\n")
        else:
            data = json.loads(content)
            data["ids_by_project"]["cmk"] = werk_ids_as_integer
            json.dump(data, f)

    sys.stdout.write(f"Werk IDs stored in the file: {RESERVED_IDS_FILE_PATH}\n")


def current_branch() -> str:
    return [l for l in os.popen("git branch") if l.startswith("*")][0].split()[-1]


def current_repo() -> str:
    return list(os.popen("git config --get remote.origin.url"))[0].strip().split("/")[-1]


def main_fetch_ids(args: argparse.Namespace) -> None:
    if args.count is None:
        sys.stdout.write(f"You have {len(get_werk_ids())} reserved IDs.\n")
        sys.exit(0)

    if current_branch() != "master" or current_repo() != "check_mk":
        bail_out("Werk IDs can only be reserved on the master branch of the check_mk repository.")

    # Get the start werk_id to reserve
    try:
        with open("first_free", encoding="utf-8") as f:
            first_free = int(f.read().strip())
    except (OSError, ValueError):
        first_free = 0

    new_first_free = first_free + args.count
    # enterprise werks were between 8000 and 8749. Skip over this area for new
    # reserved werk ids
    if 8000 <= first_free < 8780 or 8000 <= new_first_free < 8780:
        first_free = 8780
        new_first_free = first_free + args.count

    # cmk-omd werk were between 7500 and 7680. Skip over this area for new
    # reserved werk ids
    if 7500 <= first_free < 7680 or 7500 <= new_first_free < 7680:
        first_free = 7680
        new_first_free = first_free + args.count

    # cma werks are between 9000 and 9999. Skip over this area for new
    # reserved werk ids
    if 9000 <= first_free < 10000 or 9000 <= new_first_free < 10000:
        first_free = 10000
        new_first_free = first_free + args.count

    # Store the werk_ids to reserve
    my_ids = get_werk_ids() + list(WerkId(i) for i in range(first_free, new_first_free))
    store_werk_ids(my_ids)

    # Store the new reserved werk ids
    with open("first_free", "w", encoding="utf-8") as f:
        f.write(str(new_first_free) + "\n")

    sys.stdout.write(
        f"Reserved {args.count} additional IDs now. You have {len(my_ids)} reserved IDs now.\n"
    )

    if os.system(f"git commit -m 'Reserved {args.count} Werk IDS' .") == 0:  # nosec
        sys.stdout.write("--> Successfully committed reserved werk IDS. Please push it soon!\n")
    else:
        bail_out("Cannot commit.")


def main_preview(args: argparse.Namespace) -> None:
    werk_path = werk_path_by_id(WerkId(args.id))
    werk = cmk_werks_load_werk(
        file_content=Path(werk_path).read_text(encoding="utf-8"),
        file_name=werk_path.name,
    )

    def meta_data() -> Iterator[str]:
        for item in werk.model_fields:
            if item in {"title", "description"}:
                continue
            yield f"<dt>{item}<dt><dd>{getattr(werk, item)}</dd>"

    definition_list = "\n".join(meta_data())
    print(
        f'<!DOCTYPE html><html lang="en" style="font-family:sans-serif;">'
        "<head>"
        f"<title>Preview of werk {args.id}</title>"
        "</head>"
        f'<body style="background-color:#ccc; max-width:1600px; padding: 10px; margin:auto;">'
        f"<h1>{werk.title}</h1>"
        f'<div style="background-color:#fff; padding: 10px;">{werk.description}</div>'
        f"<dl>{definition_list}</dl>"
        "</body>"
        "</html>"
    )


def get_werk_file_version() -> WerkVersion:
    """
    as long as there is a single markdown file,
    we assume we should create and pick markdown werks.
    """
    for path in Path(".").iterdir():
        if path.name.endswith(".md") and path.name.removesuffix(".md").isdigit():
            return "v2"
    return "v1"


def get_werk_filename(werk_id: WerkId, werk_version: WerkVersion) -> Path:
    return Path(f"{werk_id.id}.md" if werk_version == "v2" else str(werk_id.id))


#                    _
#    _ __ ___   __ _(_)_ __
#   | '_ ` _ \ / _` | | '_ \
#   | | | | | | (_| | | | | |
#   |_| |_| |_|\__,_|_|_| |_|
#


def main(argv: Sequence[str] | None = None) -> None:
    goto_werksdir()
    main_args = parse_arguments(argv or sys.argv[1:])
    main_args.func(main_args)
