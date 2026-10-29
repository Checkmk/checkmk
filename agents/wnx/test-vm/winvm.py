#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Starts the test VMs that core-vm runs and works with them (README.md,
"Exploring the test VM"):

  winvm start [--headless]        starts a VM: PowerShell in this terminal, or
                                  in the background, printing the VM's ID
  winvm list                      the running VMs
  winvm put LOCAL [REMOTE]        copies a file into the guest
  winvm get REMOTE [LOCAL]        copies a file out of the guest
  winvm exec [--] SCRIPT...       runs a PowerShell script in the guest
  winvm stop [--all]              ends the VM (or all of them)
  winvm completion bash|nu|zsh    the shell's completion script

--vm ID picks the VM; it may be left out while only one runs. Guest paths
take / or \\ and start with their drive. put, get and exec go through the
guest agent, as LocalSystem. start runs core-vm through Bazel in the
checkout of the working directory, which builds the VM state when it is out
of date: winvm itself needs neither the image nor --config=test-vm.
"""

import argparse
import contextlib
import json
import os
import re
import secrets
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import TextIO

from qemu_windows.errors import VmError
from qemu_windows.guest import Guest, GuestError, ps_quote
from qemu_windows.qga import Qga
from vm_registry import default_root, locked, Registry, RegistryError, START_TOKEN, stop, Vm

Connect = Callable[[Vm], contextlib.AbstractContextManager[Guest]]

SUBCOMMANDS = ("start", "list", "put", "get", "exec", "stop", "completion")
# Each subcommand's options, for completion.
_OPTIONS = {
    "start": ("--headless",),
    "put": ("--vm",),
    "get": ("--vm",),
    "exec": ("--vm",),
    "stop": ("--vm", "--all"),
}
SHELLS = ("bash", "nu", "zsh")
_DRIVE = re.compile(r"[A-Za-z]:\\")
# exec's output, read back as a file: the guest agent hands over a program's
# captured output at about 8 KB/s, a file at disk speed.
_OUTPUT = "C:\\Windows\\Temp\\winvm-{}.out"
# A guest directory listing for completion is reused for this long.
_LISTING_TTL = 5.0
_CORE_VM = ("bazel", "run", "--config=test-vm", "//agents/wnx/test-vm:core-vm")
# What Bazel logs right before it runs core-vm. Until then it may fetch the
# image and build the VM state, which takes as long as it takes (Ctrl-C ends
# it); from then on, `start --headless` gives core-vm _RUN_TIMEOUT for its
# VM: the checks and the resume.
_RUNNING = "Running command line:"
_RUN_TIMEOUT = 300.0
# What Bazel's log shows on the way, and what to tell meanwhile.
_PHASES = (
    (
        re.compile(r"Fetching.*win2022", re.IGNORECASE),
        "fetching the test image, about 5 GiB: 30 to 45 minutes over the VPN",
    ),
    (
        re.compile(r"Booting and saving the Windows test VM"),
        "building the VM state, a few minutes on the first start after a change",
    ),
)
# How long a start's log is kept once its VM has gone (or never ran).
_KEEP_LOG = 86400.0


class UsageError(Exception):
    pass


class StartError(Exception):
    pass


def main(
    argv: Sequence[str] | None = None,
    *,
    registry: Registry | None = None,
    connect: Connect | None = None,
    out: TextIO = sys.stdout,
    cwd: Path | None = None,
) -> int:
    registry = registry or Registry(default_root())
    cwd = cwd or Path(os.environ.get("BUILD_WORKING_DIRECTORY") or os.getcwd())
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["__complete"]:
        words = complete(args[1:], registry, connect or connect_at_once)
        out.writelines(f"{word}\n" for word in words)
        return 0
    connect = connect or _connect
    parsed = _parser().parse_args(args)
    try:
        match parsed.command:
            case "start":
                checkout = find_checkout(cwd)
                if not parsed.headless:
                    os.chdir(checkout)
                    os.execvp(_CORE_VM[0], _CORE_VM)
                out.write(f"{start_headless(checkout, registry).id}\n")
            case "list":
                list_vms(registry, out)
            case "completion":
                out.write(completion_script(parsed.shell))
            case "stop":
                for vm in registry.vms() if parsed.all else [registry.find(parsed.vm)]:
                    stop(vm)
                    out.write(f"{vm.id} stopped\n")
            case "put":
                with connect(registry.find(parsed.vm)) as guest:
                    put(guest, cwd / parsed.local, parsed.remote, out)
            case "get":
                with connect(registry.find(parsed.vm)) as guest:
                    get(guest, parsed.remote, parsed.local, cwd, out)
            case "exec":
                script = parsed.script[1:] if parsed.script[:1] == ["--"] else parsed.script
                with connect(registry.find(parsed.vm)) as guest:
                    return exec_script(guest, " ".join(script), out)
            case command:
                raise UsageError(f"unknown command {command}")
    except (UsageError, StartError, RegistryError, VmError, OSError) as e:
        sys.stderr.write(f"error: {e}\n")
        return 1
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="winvm", description="Works with the test VMs that core-vm runs."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start", help="starts a VM, in PowerShell in this terminal")
    start.add_argument(
        "--headless", action="store_true", help="in the background instead; prints its ID"
    )
    vm = argparse.ArgumentParser(add_help=False)
    vm.add_argument("--vm", help="the VM's ID (winvm list); needed while several run")
    commands.add_parser("list", help="the running VMs")
    put_cmd = commands.add_parser("put", parents=[vm], help="copies a file into the guest")
    put_cmd.add_argument("local")
    put_cmd.add_argument("remote", nargs="?", help="a file or directory, default C:\\")
    get_cmd = commands.add_parser("get", parents=[vm], help="copies a file out of the guest")
    get_cmd.add_argument("remote")
    get_cmd.add_argument("local", nargs="?", help="a file or directory, default .")
    exec_cmd = commands.add_parser("exec", parents=[vm], help="runs a PowerShell script")
    exec_cmd.add_argument("script", nargs=argparse.REMAINDER)
    stop_cmd = commands.add_parser("stop", parents=[vm], help="ends the VM")
    stop_cmd.add_argument("--all", action="store_true", help="ends all of this user's VMs")
    completion = commands.add_parser("completion", help="prints a shell's completion script")
    completion.add_argument("shell", choices=SHELLS)
    return parser


@contextlib.contextmanager
def _connect(vm: Vm) -> Iterator[Guest]:
    with locked(vm), contextlib.closing(Qga(vm.qga, lambda: True)) as agent:
        guest = Guest(agent, lambda: None)
        guest.wait_ready(60)
        yield guest


@contextlib.contextmanager
def connect_at_once(vm: Vm) -> Iterator[Guest]:
    """The VM's guest, for completion, which must not keep the shell
    waiting: a VM busy with another command fails at once."""
    with locked(vm, wait=False), contextlib.closing(Qga(vm.qga, lambda: True)) as agent:
        guest = Guest(agent, lambda: None)
        guest.wait_ready(2)
        yield guest


def find_checkout(cwd: Path) -> Path:
    """The check_mk checkout cwd is in: its MODULE.bazel and core-vm's
    package, not a module's MODULE.bazel further down."""
    for directory in (cwd, *cwd.parents):
        if (directory / "MODULE.bazel").is_file() and (
            directory / "agents/wnx/test-vm/BUILD.bazel"
        ).is_file():
            return directory
    raise StartError("run winvm start inside a check_mk checkout")


def start_headless(
    checkout: Path, registry: Registry, timeout: float = _RUN_TIMEOUT, err: TextIO | None = None
) -> Vm:
    """Starts core-vm --no-shell in the background and returns its VM once
    it has registered, timeout s after core-vm itself started at the latest.
    The VM is told from others by a token core-vm registers; core-vm's output
    goes to the log log_of() names, which outlives the VM, so that it still
    says why a VM ended."""
    err = err or sys.stderr
    token = secrets.token_hex(8)
    registry.root.mkdir(mode=0o700, parents=True, exist_ok=True)
    running = {vm.token for vm in registry.vms()}
    for old in registry.root.glob("start-*.log"):
        with contextlib.suppress(OSError):
            if (
                old.stem.removeprefix("start-") not in running
                and time.time() - old.stat().st_mtime > _KEEP_LOG
            ):
                old.unlink()
    log = registry.root / f"start-{token}.log"
    with log.open("wb") as output:
        # A session of its own: it outlives this process and the terminal.
        process = subprocess.Popen(
            [*_CORE_VM, "--", "--no-shell"],
            cwd=checkout,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env=os.environ | {START_TOKEN: token},
        )
    err.write(f"starting a test VM in {checkout} (log: {log})\n")
    deadline = None
    told: set[str] = set()
    try:
        while not (vm := _registered(registry, token)):
            if process.poll() is not None:
                raise StartError(
                    f"`bazel run ... core-vm` ended (exit {process.returncode}) before its VM ran:\n"
                    f"{_tail(log)}"
                )
            text = log.read_text(errors="replace")
            if deadline is None and _RUNNING in text:
                deadline = time.monotonic() + timeout
            if deadline is not None and time.monotonic() >= deadline:
                os.killpg(process.pid, signal.SIGTERM)
                raise StartError(
                    f"core-vm ran {timeout:g} s without its VM, stopped it:\n{_tail(log)}"
                )
            for pattern, phase in _PHASES:
                if phase not in told and pattern.search(text):
                    told.add(phase)
                    err.write(f"{phase}\n")
            time.sleep(0.5)
    except KeyboardInterrupt:
        # A VM that registered meanwhile stays, for `winvm stop`.
        if vm := _registered(registry, token):
            raise StartError(f"interrupted; {vm.id} runs, `winvm stop --vm {vm.id}` ends it")
        os.killpg(process.pid, signal.SIGTERM)
        raise StartError("interrupted, stopped the VM's start") from None
    return vm


def log_of(registry: Registry, vm: Vm) -> Path | None:
    """The log of a VM `winvm start --headless` started."""
    log = registry.root / f"start-{vm.token}.log"
    return log if vm.token and log.exists() else None


def _registered(registry: Registry, token: str) -> Vm | None:
    return next((vm for vm in registry.vms() if vm.token == token), None)


def _tail(log: Path, lines: int = 20) -> str:
    return "\n".join(log.read_text(errors="replace").splitlines()[-lines:])


def list_vms(registry: Registry, out: TextIO) -> None:
    vms = registry.vms()
    if not vms:
        out.write("no test VM is running\n")
        return
    out.write(f"{'ID':<6}{'AGE':>6}  WORKTREE\n")
    for vm in vms:
        out.write(f"{vm.id:<6}{_age(time.time() - vm.started):>6}  {vm.worktree}\n")
        if log := log_of(registry, vm):
            out.write(f"{'':<14}log: {log}\n")


def put(guest: Guest, local: Path, remote: str | None, out: TextIO) -> None:
    """local into the guest as remote, or into remote if that is a
    directory (by default C:\\)."""
    if not local.is_file():
        raise UsageError(f"{local}: no such file")
    target = put_target(local.name, remote, lambda path: _is_guest_directory(guest, path))
    guest.put(local, target)
    out.write(f"{local} -> {target}\n")


def put_target(name: str, remote: str | None, is_directory: Callable[[str], bool]) -> str:
    """Where put copies the file name to: remote, or into remote if that
    ends in a separator or is_directory() says it is one (by default
    C:\\)."""
    target = guest_path(remote) if remote is not None else "C:\\"
    if target.endswith("\\") or is_directory(target):
        return target.rstrip("\\") + "\\" + name
    return target


def get(guest: Guest, remote: str, local: str | None, cwd: Path, out: TextIO) -> None:
    """remote out of the guest as local, or into local if that is a
    directory (by default the working directory)."""
    source, target = get_paths(remote, local, cwd)
    guest.get(source, target)
    out.write(f"{source} -> {target}\n")


def get_paths(remote: str, local: str | None, cwd: Path) -> tuple[str, Path]:
    """The guest file get copies, and where to: local (relative to cwd), or
    into local if that is a directory or ends in / (by default cwd)."""
    source = guest_path(remote)
    if not (name := source.rpartition("\\")[2]):
        raise UsageError(f"{remote}: not a file")
    target = cwd / local if local is not None else cwd
    if target.is_dir() or (local is not None and local.endswith("/")):
        target = target / name
    return source, target


def exec_script(guest: Guest, script: str, out: TextIO) -> int:
    """Runs script in C:\\ and shows its output: its exit code, or 1 if
    PowerShell reports a failure."""
    output = _OUTPUT.format(f"{os.getpid()}-{time.time_ns()}")
    result = guest.powershell(
        "\n".join(
            [
                "$ErrorActionPreference = 'Continue'",
                "Set-Location C:\\",
                f"& {{\n{script}\n}} *> {ps_quote(output)}",
                "$ok = $?",
                "if ($LASTEXITCODE) { exit $LASTEXITCODE }",
                "if (-not $ok) { exit 1 }",
            ]
        ),
        check=False,
    )
    with contextlib.suppress(GuestError):
        out.write(_decode(guest.read(output)))
        guest.run(["cmd.exe", "/d", "/c", "del", "/q", output], check=False)
    out.write(result.stdout + result.stderr)
    return result.returncode


def guest_path(path: str) -> str:
    """path with \\ as separator, if it is a guest path with its drive."""
    windows = path.replace("/", "\\")
    if not _DRIVE.match(windows):
        raise UsageError(f"{path}: give guest paths with their drive, like C:\\dir or C:/dir")
    return windows


def complete(words: Sequence[str], registry: Registry, connect: Connect) -> list[str]:
    """Completions for the last of words, the arguments after `winvm` up
    to the cursor. Host paths are left to the shell."""
    *before, current = words or [""]
    if before and before[-1] == "--vm":
        return [vm.id for vm in registry.vms() if vm.id.startswith(current)]
    vm_id = None
    positional = []
    for previous, word in zip(["", *before], before):
        if previous == "--vm":
            vm_id = word
        elif not word.startswith("-"):
            positional.append(word)
    if not positional:
        return [command for command in SUBCOMMANDS if command.startswith(current)]
    command, arguments = positional[0], positional[1:]
    if current.startswith("-"):
        return [option for option in _OPTIONS.get(command, ()) if option.startswith(current)]
    if command == "completion" and not arguments:
        return [shell for shell in SHELLS if shell.startswith(current)]
    if (command, len(arguments)) in (("get", 0), ("put", 1)):
        try:
            vm = registry.find(vm_id)
        except RegistryError:
            return []
        return _complete_guest_path(vm, current, connect)
    return []


def _complete_guest_path(vm: Vm, prefix: str, connect: Connect) -> list[str]:
    separator = "/" if "/" in prefix else "\\"
    if not re.match(r"[A-Za-z]:[\\/]", prefix):
        drive = f"C:{separator}"
        return [drive] if drive.lower().startswith(prefix.lower()) else []
    directory, _, partial = prefix.replace("/", "\\").rpartition("\\")
    typed = prefix[: len(prefix) - len(partial)]
    return [
        typed + name + (separator if is_directory else "")
        for name, is_directory in _listing(vm, directory + "\\", connect)
        if name.lower().startswith(partial.lower())
    ]


def _listing(vm: Vm, directory: str, connect: Connect) -> list[tuple[str, bool]]:
    """The names in a guest directory, and whether each is a directory;
    kept for a few seconds in the VM's registry directory, as completion
    asks again for every key."""
    cache = vm.dir / "listing.json"
    with contextlib.suppress(OSError, ValueError, KeyError):
        cached = json.loads(cache.read_text())
        if cached["directory"] == directory and time.time() - cached["time"] < _LISTING_TTL:
            return [(name, is_directory) for name, is_directory in cached["names"]]
    try:
        with connect(vm) as guest:
            names = list_guest_directory(guest, directory)
    except VmError, RegistryError:
        return []
    with contextlib.suppress(OSError):
        cache.write_text(json.dumps({"directory": directory, "time": time.time(), "names": names}))
    return names


def list_guest_directory(guest: Guest, directory: str) -> list[tuple[str, bool]]:
    # cmd's dir, which starts far faster than PowerShell. Its lines:
    # 10/29/2026  02:51 PM    <DIR>          Program Files
    result = guest.run(["cmd.exe", "/d", "/c", "dir", "/a", "/-c", directory], check=False)
    names = []
    for line in result.stdout.splitlines():
        if match := re.match(r"\S+\s+\S+\s+\S+\s+(<\w+>|\d+)\s+(.+)$", line):
            kind, name = match.groups()
            if name not in (".", ".."):
                names.append((re.sub(r" \[.*\]$", "", name), kind.startswith("<")))
    return names


def _is_guest_directory(guest: Guest, path: str) -> bool:
    # `if exist DIR\*` holds for a directory, also an empty one.
    return (
        guest.run(
            [
                "cmd.exe",
                "/d",
                "/c",
                "if",
                "exist",
                path + "\\*",
                "(exit",
                "0)",
                "else",
                "(exit",
                "1)",
            ],
            check=False,
        ).returncode
        == 0
    )


def _decode(data: bytes) -> str:
    # PowerShell 5.1's redirections write UTF-16 with a BOM.
    text = data.decode("utf-16") if data.startswith(b"\xff\xfe") else data.decode(errors="replace")
    return text.replace("\r", "")


def _age(seconds: float) -> str:
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{int(seconds // size)}{unit}"
    return f"{int(seconds)}s"


def completion_script(shell: str) -> str:
    return _COMPLETION[shell]


_COMPLETION = {
    "bash": r"""# winvm completion for bash: eval "$(winvm completion bash)"
_winvm() {
    # Without winvm, -o default completes files.
    type -P winvm >/dev/null || return 0
    local cur words cword
    if declare -F _get_comp_words_by_ref >/dev/null; then
        _get_comp_words_by_ref -n : cur words cword
    else
        words=("${COMP_WORDS[@]}")
        cword=$COMP_CWORD
        cur=${COMP_WORDS[COMP_CWORD]}
    fi
    mapfile -t COMPREPLY < <(winvm __complete "${words[@]:1:cword-1}" "${cur//\\ / }")
    if declare -F __ltrim_colon_completions >/dev/null; then
        __ltrim_colon_completions "$cur"
    fi
    COMPREPLY=("${COMPREPLY[@]// /\\ }")
    if [[ ${#COMPREPLY[@]} -eq 1 && ${COMPREPLY[0]} == *[/\\] ]]; then
        compopt -o nospace
    fi
}
complete -o default -F _winvm winvm
""",
    "zsh": r"""# winvm completion for zsh: eval "$(winvm completion zsh)"
_winvm() {
    (( ${+commands[winvm]} )) || { _files; return }
    local -a candidates
    candidates=("${(@f)$(winvm __complete "${(@)words[2,CURRENT]}")}")
    if (( ${#candidates} )) && [[ -n ${candidates[1]} ]]; then
        local candidate
        for candidate in "${candidates[@]}"; do
            if [[ $candidate == *[/\\] ]]; then
                compadd -Q -S '' -- "$candidate"
            else
                compadd -Q -- "$candidate"
            fi
        done
    else
        _files
    fi
}
compdef _winvm winvm
""",
    "nu": r"""# winvm completion for nushell, as a module of another name than winvm (nushell
# refuses a module that exports an extern of its own name):
# winvm completion nu | save -f winvm-completions.nu; use winvm-completions.nu *
# nushell (0.116) hands the completer a record: its command holds the
# extern's name ("winvm put") and the words typed for it, "" after a space.
def "nu-complete winvm" [place: record] {
    # Without winvm, null completes files. `which` would find the extern.
    if not ($env.PATH | any {|dir| $dir | path join winvm | path exists }) {
        return null
    }
    let name = $place.command | first | split row " " | skip 1
    let typed = $place.command | skip 1 | each { str trim -c '"' | str trim -c '`' }
    let completions = (^winvm __complete ...$name ...$typed | lines)
    if ($completions | is-empty) { null } else { $completions }
}

# Works with the test VMs that core-vm runs.
export extern "winvm" [
    command?: string
]

# Starts a VM: PowerShell in this terminal, or in the background.
export extern "winvm start" [
    --headless
]

# The running VMs.
export extern "winvm list" []

# Copies a file into the guest.
export extern "winvm put" [
    local: path
    remote?: string@"nu-complete winvm"
    --vm: string@"nu-complete winvm"
]

# Copies a file out of the guest.
export extern "winvm get" [
    remote: string@"nu-complete winvm"
    local?: path
    --vm: string@"nu-complete winvm"
]

# Runs a PowerShell script in the guest.
export extern "winvm exec" [
    --vm: string@"nu-complete winvm"
    ...script: string
]

# Ends the VM, or all of them.
export extern "winvm stop" [
    --vm: string@"nu-complete winvm"
    --all
]

# Prints a shell's completion script.
export extern "winvm completion" [
    shell: string@[bash nu zsh]
]
""",
}


if __name__ == "__main__":
    sys.exit(main())
