#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Wrapper functions for interactive dialogs using the dialog cmd tool"""

import os
import subprocess
import sys
import termios
from re import Pattern
from tty import setraw

from omdlib.type_defs import ConfigChoiceHasError

from cmk.ccc import tty
from cmk.ccc.exceptions import MKTerminate

DialogResult = tuple[bool, str]


def dialog_menu(
    title: str,
    text: str,
    choices: list[tuple[str, str]],
    defvalue: str | None,
    oktext: str,
    canceltext: str,
) -> DialogResult:
    args = ["--ok-label", oktext, "--cancel-label", canceltext]
    if defvalue is not None:
        args += ["--default-item", defvalue]
    args += ["--title", title, "--menu", text, "0", "0", "0"]  # "20", "60", "17" ]
    for choice_text, value in choices:
        args += [choice_text, value]
    return _run_dialog(args)


def dialog_regex(
    title: str, text: str, regex: Pattern, value: str, oktext: str, canceltext: str
) -> DialogResult:
    while True:
        args = [
            "--ok-label",
            oktext,
            "--cancel-label",
            canceltext,
            "--title",
            title,
            "--inputbox",
            text,
            "0",
            "0",
            value,
        ]
        change, new_value = _run_dialog(args)
        if not change:
            return False, value
        if not regex.match(new_value):
            dialog_message("Invalid value. Please try again.")
            value = new_value
        else:
            return True, new_value


def dialog_config_choice_has_error(
    title: str, text: str, pattern: ConfigChoiceHasError, value: str, oktext: str, canceltext: str
) -> DialogResult:
    while True:
        args = [
            "--ok-label",
            oktext,
            "--cancel-label",
            canceltext,
            "--title",
            title,
            "--inputbox",
            text,
            "0",
            "0",
            value,
        ]
        change, new_value = _run_dialog(args)
        if not change:
            return False, value
        validity = pattern(new_value)
        if validity.is_error():
            dialog_message(validity.error)
            value = new_value
        else:
            return True, new_value


def dialog_yesno(
    text: str,
    yeslabel: str = "yes",
    nolabel: str = "no",
    default_no: bool = False,
    scrollbar: bool = False,
) -> bool:
    command: list[str] = ["--yes-label", yeslabel, "--no-label", nolabel]
    if default_no:
        command += ["--defaultno"]
    if scrollbar:
        command += ["--scrollbar"]
    state, _response = _run_dialog(command + ["--yesno", text, "0", "0"])
    return state


def dialog_message(text: str, buttonlabel: str = "OK") -> None:
    _run_dialog(["--ok-label", buttonlabel, "--msgbox", text, "0", "0"])


def _run_dialog(args: list[str]) -> DialogResult:
    dialog_env = {
        "TERM": os.environ.get("TERM", "linux"),
        # TODO: Why de_DE?
        "LANG": "de_DE.UTF-8",
    }
    completed_process = subprocess.run(
        ["dialog", "--shadow"] + args,
        env=dialog_env,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        check=False,
    )
    # dialog returns 1 on the nolabel answer. But a return code of 1 is
    # used for errors. So we need to check the output.
    if completed_process.returncode != 0 and completed_process.stderr != "":
        sys.stderr.write(completed_process.stderr + "\n")
    return completed_process.returncode == 0, completed_process.stderr


def user_confirms(
    site_home: str,
    conflict_mode: str,
    title: str,
    message: str,
    relpath: str,
    yes_choice: str,
    yes_text: str,
    no_choice: str,
    no_text: str,
) -> bool:
    # Handle non-interactive mode
    if conflict_mode == "abort":
        raise MKTerminate("Update aborted.")
    if conflict_mode == "install":
        return False
    if conflict_mode == "keepold":
        return True

    user_path = site_home + "/" + relpath
    options = [
        (yes_choice, yes_text),
        (no_choice, no_text),
        ("shell", "Open a shell for looking around"),
        ("abort", "Stop here and abort update!"),
    ]
    while True:
        choice = ask_user_choices(title, message, options)
        if choice == "abort":
            raise MKTerminate("Update aborted.")

        if choice == "shell":
            thedir = "/".join(user_path.split("/")[:-1])
            sys.stdout.write("\n Starting BASH. Type CTRL-D to continue.\n\n")
            subprocess.run(["bash", "-i"], cwd=thedir, check=False)
        else:
            return choice == yes_choice


# TODO: Use standard textwrap module?
def _wrap_text(text: str, width: int) -> list[str]:
    def fillup(line, width):
        if len(line) < width:
            line += " " * (width - len(line))
        return line

    def justify(line: str, width: int) -> str:
        need_spaces = float(width - len(line))
        spaces = float(line.count(" "))
        newline = ""
        x = 0.0
        s = 0.0
        words = line.split()
        newline = words[0]
        for word in words[1:]:
            newline += " "
            x += 1.0
            if s / x < need_spaces / spaces:  # fixed: true-division
                newline += " "
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
            line += " "
            col += 1
        line += word
        col += netto
    if line != "":
        wrapped.append(fillup(line, width))

    # remove trailing empty lines
    while wrapped[-1].strip() == "":
        wrapped = wrapped[:-1]
    return wrapped


def _getch() -> str:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        setraw(sys.stdin.fileno())
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    if ord(ch) == 3:
        raise KeyboardInterrupt()
    return ch


def ask_user_choices(title: str, message: str, choices: list[tuple[str, str]]) -> str:
    sys.stdout.write("\n")

    def pl(line):
        sys.stdout.write(" %s %-76s %s\n" % (tty.bgcyan + tty.white, line, tty.normal))

    pl("")
    sys.stdout.write(" %s %-76s %s\n" % (tty.bgcyan + tty.white + tty.bold, title, tty.normal))
    for line in _wrap_text(message, 76):
        pl(line)
    pl("")
    chars: list[str] = []
    empty_line = " %s%-78s%s\n" % (tty.bgblue + tty.white, "", tty.normal)
    sys.stdout.write(empty_line)
    for choice, choice_title in choices:
        sys.stdout.write(
            " %s %s%s%s%-10s %-65s%s\n"
            % (
                tty.bgblue + tty.white,
                tty.bold,
                choice[0],
                tty.normal + tty.bgblue + tty.white,
                choice[1:],
                choice_title,
                tty.normal,
            )
        )
        for c in choice:
            if c.lower() not in chars:
                chars.append(c)
                break
    sys.stdout.write(empty_line)

    choicetxt = (tty.bold + tty.magenta + "/").join(
        [
            (tty.bold + tty.white + char + tty.normal + tty.bgmagenta)
            for (char, _c) in zip(chars, choices)
        ]
    )
    l = len(choices) * 2 - 1
    sys.stdout.write(f" {tty.bgmagenta} {choicetxt}")
    sys.stdout.write(f" ==> {tty.bgred}   {tty.bgmagenta}")
    sys.stdout.write(" " * (69 - l))
    sys.stdout.write("\b" * (71 - l))
    sys.stdout.write(tty.normal)
    while True:
        a = _getch()
        for char, (choice, choice_title) in zip(chars, choices):
            if a == char:
                sys.stdout.write(tty.bold + tty.bgred + tty.white + a + tty.normal + "\n\n")
                return choice
