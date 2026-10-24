#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Builds the Windows Server 2022 Core test image that the *-qemu test tiers
run in, end to end and unattended, with the pinned QEMU, from the Server
2022 Eval ISO (Datacenter, Server Core).

Three QEMU runs, each ended by a clean guest shutdown, so every boot after
the install is a cold one, with a fresh clock and only the devices it needs:
  1. install: Windows Setup from the Eval ISO with an answer floppy, then
     first-logon.ps1 (the guest agent from the virtio-win ISO, the serial
     console, Defender removed, autologon, test signing, time and account
     settings), which powers the guest off
  2. provisioning: first-logon.ps1's result, Eval activation, SQL Server
     2022 Developer with three instances from the SQL ISO on a CD drive,
     NGEN flush, component store cleanup, removal of C:\\setup and TRIM
  3. verification: the device set the tests use, verify-image.ps1
then a zstd-compressed copy. The result is a cleanly shut down disk without
snapshots: a running state only resumes on the CPU it was saved on, so it is
never saved here. Every boot after the install is driven through the guest
agent (qemu-ga).

Run through Bazel, which provides QEMU and the pinned media:
  bazel run --config=test-vm //agents/wnx/test-vm:build-core -- --out <image.qcow2> [--work <dir>] [--keep-work]
--work holds the uncompressed disk (~13 GiB) and the guest's provisioning
logs, defaults to the directory of --out, and is removed after a successful
build unless --keep-work is given. The last line prints the image's Eval
expiry.
"""

import argparse
import contextlib
import io
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass
from pathlib import Path
from types import FrameType

from qemu_windows import machine
from qemu_windows.errors import VmError
from qemu_windows.guest import Guest, PASSWORD, ps_quote
from qemu_windows.qemu import Qemu
from qemu_windows.qga import Qga
from qemu_windows.session import run_in_session, SessionError

# install.wim of the 2022 Eval ISO: 3 = Datacenter Evaluation (Core). Setup
# selects by /IMAGE/NAME, which survives a reordered ISO.
_IMAGE_NAME = "Windows Server 2022 SERVERDATACENTERCORE"

# SQL Server: the build every instance must run after the CU, and the max
# server memory of each instance (install-mssql.ps1 sets it,
# verify-image.ps1 checks both).
MSSQL_VERSION = "16.0.4295.3"
MSSQL_MAX_MEMORY_MB = 512
_SQL_SETUP_LOG = r"C:\Program Files\Microsoft SQL Server\160\Setup Bootstrap\Log"
_SQL_SUMMARY = rf"{_SQL_SETUP_LOG}\Summary.txt"
# first-logon.ps1's marker, written last: 'ok', or what failed.
_DONE = r"C:\setup\done.txt"
_VERIFY = r"C:\Windows\Temp\verify-image.ps1"


class BuildError(Exception):
    """The image build failed; the message says why."""


@dataclass(frozen=True)
class Config:
    # Tools and inputs, from the BUILD target.
    qemu: Path
    qemu_img: Path
    firmware: Path
    media: Path
    virtio_win: Path
    sql_iso: Path
    sql_cu: Path
    odbc: Path
    answer: Path
    first_logon: Path
    install_mssql: Path
    verify: Path
    # The user's options.
    out: Path
    work: Path
    keep_work: bool

    @property
    def image(self) -> Path:
        return self.work / "disk.qcow2"


def parse_args(argv: Sequence[str]) -> Config:
    """The BUILD target's tool options, then the user's."""
    parser = argparse.ArgumentParser(
        usage="%(prog)s <tool options from BUILD> -- --out <image.qcow2>"
        " [--work <dir>] [--keep-work]"
    )
    for tool in (
        *("qemu", "qemu-img", "bios", "media", "virtio-win"),
        *("sql-iso", "sql-cu", "odbc"),
    ):
        parser.add_argument(f"--{tool}", type=Path, required=True)
    for template in ("answer", "first-logon", "install-mssql", "verify"):
        parser.add_argument(f"--{template}", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--keep-work", action="store_true")
    # The user's options may follow a `--` (bazel run passes it on).
    args = parser.parse_args([arg for arg in argv if arg != "--"])
    out = _user_path(args.out)
    return Config(
        qemu=args.qemu.resolve(),
        qemu_img=args.qemu_img.resolve(),
        firmware=args.bios.resolve().parent,
        media=args.media.resolve(),
        virtio_win=args.virtio_win.resolve(),
        sql_iso=args.sql_iso.resolve(),
        sql_cu=args.sql_cu.resolve(),
        odbc=args.odbc.resolve(),
        answer=args.answer.resolve(),
        first_logon=args.first_logon.resolve(),
        install_mssql=args.install_mssql.resolve(),
        verify=args.verify.resolve(),
        out=out,
        work=(_user_path(args.work) if args.work else out.parent) / "test-vm-build-core",
        keep_work=args.keep_work,
    )


def _user_path(path: Path) -> Path:
    # bazel run starts this in the runfiles tree: relative paths are the user's.
    return Path(os.path.realpath(Path(os.environ.get("BUILD_WORKING_DIRECTORY", "."), path)))


def check_paths(config: Config) -> None:
    """Fails before the build on paths it could not use or would overwrite."""
    # QEMU option values are comma-separated, and fat: drives split on ':',
    # as do protocol prefixes of qemu-img file names.
    for path in (config.out, config.work, config.media, config.virtio_win, config.sql_iso):
        if "," in str(path) or ":" in str(path):
            raise BuildError(f"{path}: QEMU cannot take a path with ',' or ':'")
    if config.out.exists():
        raise BuildError(f"{config.out} exists; remove it first")
    # Checked now, not after the build: --work may be elsewhere.
    if not config.out.parent.is_dir() or not os.access(config.out.parent, os.W_OK):
        raise BuildError(f"{config.out.parent} is not a writable directory")


def fill(template: str, **values: str) -> str:
    """The guest password for @@PASSWORD@@, from one place, and @@NAME@@ for
    each further value."""
    text = template
    for name, value in {"PASSWORD": PASSWORD, **values}.items():
        text = text.replace(f"@@{name}@@", value)
    return text


def parse_expiry(verify_output: str) -> str | None:
    """The Eval expiry that verify-image.ps1 prints."""
    found = re.search(r"^EVAL_EXPIRY=(.*)$", verify_output, re.MULTILINE)
    return found[1] if found else None


def main(argv: Sequence[str] | None = None) -> int:
    # Each step line before the output it explains.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(line_buffering=True)
    # Like Ctrl-C: the running QEMU quits on the way out (a SIGKILL instead
    # takes it down through its parent-death signal).
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, _exit_on_signal)
    try:
        config = parse_args(sys.argv[1:] if argv is None else argv)
        check_paths(config)
        config.work.mkdir(parents=True, exist_ok=True)
        machine.check_kvm()
        _install(config)
        _provision(config)
        expires = _verify(config)
        _compress(config, expires)
    except (BuildError, VmError, subprocess.CalledProcessError) as e:
        sys.stderr.write(f"error: {e}\n")
        return 1
    return 0


def _exit_on_signal(signum: int, _frame: FrameType | None) -> None:
    raise SystemExit(128 + signum)


def _step(message: str) -> None:
    sys.stdout.write(f"\n=== [{time.strftime('%T')}] {message}\n")


@contextmanager
def _boot(config: Config, extra: Sequence[str] = ()) -> Iterator[tuple[Qemu, Guest]]:
    """A QEMU run of the image. -no-shutdown keeps QEMU up when the guest
    powers off, so _wait_power_off can tell that from a crash."""
    argv = machine.argv(config.qemu, config.firmware, [machine.Disk("disk", config.image)])
    with Qemu.start(argv, config.work / "vm", ["-no-shutdown", *extra]) as vm:
        sys.stdout.write(f"serial console (SAC, README.md): {vm.console_socket}\n")
        with contextlib.closing(Qga(vm.qga_socket, vm.alive)) as agent:
            yield vm, Guest(agent, vm.check)


def _wait_ready(guest: Guest) -> None:
    """A cold boot of the installed disk, until the guest agent and the
    autologon console session are up."""
    guest.wait_ready(900)
    guest.wait_console(600)


def _shutdown(vm: Qemu, guest: Guest) -> None:
    guest.shutdown()
    _wait_power_off(vm, 300)


def _wait_power_off(vm: Qemu, timeout: float, interval: float = 2) -> None:
    """Until the guest has powered off, then QEMU's exit: the build fails
    rather than go on with a disk the guest did not shut down cleanly (a
    dirty NTFS volume, lost writes). Only a guest that powered off itself
    leaves QEMU in "shutdown"."""
    deadline = time.monotonic() + timeout
    while (state := vm.status()) != "shutdown":
        # Not every round: check() fails on "shutdown" too, which the guest
        # may reach between the two queries.
        if vm.returncode is not None or state in ("io-error", "internal-error"):
            vm.check()
        if time.monotonic() >= deadline:
            raise BuildError(f"the guest did not power off within {timeout / 60:g} min")
        time.sleep(interval)
    if (rc := vm.quit()) != 0:
        raise BuildError(
            f"QEMU exited with status {rc} after the guest powered off:\n{vm.log_text()}"
        )


def _sizes(config: Config, guest: Guest) -> None:
    """Informational only: a failed lookup must not end the build."""
    info = subprocess.run(
        [config.qemu_img, "info", "-U", config.image], check=False, capture_output=True, text=True
    ).stdout
    image = re.search(r"^disk size: (.*)$", info, re.MULTILINE)
    used = guest.powershell(
        "$v = Get-Volume -DriveLetter C; [int64](($v.Size - $v.SizeRemaining) / 1MB)", check=False
    )
    sys.stdout.write(
        f"sizes: qcow2 {image[1] if image else '?'},"
        f" guest C: used {used.stdout.strip() if used.returncode == 0 else '?'} MiB\n"
    )


def _install(config: Config) -> None:
    _step("answer file and first-logon.ps1 with the test credentials")
    answer = config.work / "answer"
    (answer / "setup").mkdir(parents=True, exist_ok=True)
    (answer / "setup/first-logon.ps1").write_bytes(
        fill(config.first_logon.read_bytes().decode()).encode()
    )

    config.image.unlink(missing_ok=True)
    _step("Server Core: unattended install from the Eval ISO, then first-logon.ps1 (~10-30 min)")
    (answer / "autounattend.xml").write_bytes(
        fill(config.answer.read_bytes().decode(), IMAGE_NAME=_IMAGE_NAME).encode()
    )
    subprocess.run(
        [config.qemu_img, "create", "-q", "-f", "qcow2", config.image, "40G"], check=True
    )
    # Setup finds autounattend.xml at the root of the floppy, a FAT view of
    # the answer dir; the ISO boots once, Setup's own reboots then come up
    # from the disk. first-logon.ps1 installs the guest agent from the
    # virtio-win ISO. None of them is attached after this run.
    with _boot(
        config,
        [
            *("-drive", f"file={config.media},if=ide,bus=1,unit=0,media=cdrom,readonly=on"),
            *("-drive", f"file={config.virtio_win},if=ide,bus=1,unit=1,media=cdrom,readonly=on"),
            *("-drive", f"file=fat:floppy:{answer},if=floppy,format=raw,readonly=on"),
            *("-boot", "once=d"),
        ],
    ) as (vm, _guest):
        # Nothing to ask the guest before first-logon.ps1 is done: it then
        # powers the guest off, and the provisioning boot reads how it went.
        # Test signing, the Defender removal and the pagefile take effect
        # with that next boot: a cold one, in a new QEMU without the install
        # media.
        _step("waiting for Setup and first-logon.ps1 to power the guest off")
        _wait_power_off(vm, 90 * 60, interval=15)


def _provision(config: Config) -> None:
    # The SQL ISO on a CD drive: install-mssql.ps1 finds it by its setup.exe.
    sql_cd = ["-drive", f"file={config.sql_iso},if=ide,bus=1,unit=0,media=cdrom,readonly=on"]
    _step("provisioning boot")
    with ExitStack() as boots:
        vm, guest = boots.enter_context(_boot(config, sql_cd))
        _wait_ready(guest)

        _step("first-logon.ps1's result")
        _check_first_logon(guest)

        # Windows activates the Eval in the background, sometime;
        # verify-image.ps1 needs it done. Errors show up here, with slmgr's
        # code, not 30 min later.
        _step("Eval activation")
        activation = ""
        for attempt in range(1, 4):
            activation = guest.run(
                ["cscript.exe", "//nologo", r"C:\Windows\System32\slmgr.vbs", "/ato"], check=False
            ).stdout
            (config.work / "ato.log").write_text(activation)
            if "activated successfully" in activation.lower():
                break
            if attempt == 3:
                raise BuildError(f"Eval activation failed:\n{activation}")
            time.sleep(30)
        sys.stdout.write(activation)

        # SQL Server setup refuses to run while a reboot is pending, hence
        # after the cold boot; and before the NGEN flush, which then also
        # compiles what setup queued. A setup run that asks for a reboot ends
        # install-mssql.ps1 early (C:\setup\mssql\reboot-required): a cold
        # boot, then it carries on with the instances that are still missing,
        # or, after the last one, with the rest of the install. At most one
        # run per instance, plus that one.
        _step("SQL Server 2022 Developer: MSSQLSERVER, SQLEXPRESS_NAME, SQLEXPRESS_WOW (~15 min)")
        guest.powershell(
            r"Remove-Item -Recurse -Force C:\setup\mssql -ErrorAction Ignore;"
            r" New-Item -ItemType Directory -Force C:\setup\mssql\cu | Out-Null"
        )
        copy_start = time.monotonic()
        guest.put(config.odbc, r"C:\setup\mssql\msodbcsql17.msi")
        guest.put(config.sql_cu, rf"C:\setup\mssql\cu\{config.sql_cu.name}")
        guest.put(config.install_mssql, r"C:\setup\mssql\install-mssql.ps1")
        payload = sum(f.stat().st_size for f in (config.odbc, config.sql_cu, config.install_mssql))
        sys.stdout.write(
            f"payload copied: {payload / 1e6:.0f} MB in {time.monotonic() - copy_start:.0f} s\n"
        )
        logs = config.work / "guest-logs"
        logs.mkdir(exist_ok=True)
        for run in range(1, 5):
            _install_mssql(guest, logs)
            # check=True: a failed probe ends the build instead of passing
            # for "no reboot needed".
            if not guest.exists(r"C:\setup\mssql\reboot-required"):
                break
            if run == 4:
                raise BuildError(f"SQL Server setup still asks for a reboot after {run} cold boots")
            _step("cold boot for SQL Server setup")
            guest.powershell(r"Remove-Item C:\setup\mssql\reboot-required")
            _shutdown(vm, guest)
            vm, guest = boots.enter_context(_boot(config, sql_cd))
            _wait_ready(guest)
        try:
            guest.get(_SQL_SUMMARY, logs / "mssql-summary.txt")
        except VmError:
            sys.stdout.write("warning: copying SQL Server setup's Summary.txt failed\n")
        _sizes(config, guest)

        # Left pending, the "NGEN ... Critical" tasks compile the queued .NET
        # assemblies on their idle trigger, i.e. during a test tier.
        _step("compiling queued .NET native images")
        for framework in ("Framework64", "Framework"):
            ngen = rf"C:\Windows\Microsoft.NET\{framework}\v4.0.30319\ngen.exe"
            # Its list of what it compiled is too long for run(): into a log
            # of C:\setup, which goes to guest-logs.
            if guest.powershell(
                f"& {ps_quote(ngen)} executeQueuedItems /nologo"
                rf" | Set-Content -Encoding UTF8 C:\setup\ngen-{framework}.log; exit $LASTEXITCODE",
                check=False,
            ).returncode:
                sys.stdout.write(f"warning: ngen executeQueuedItems ({framework}) failed\n")

        # After the NGEN flush (before it, the flush grows C: by ~0.5 GiB
        # more).
        _step("component store cleanup")
        # Only the image's size depends on it: a failure is a warning, with
        # DISM's error code. A reboot it would leave pending fails
        # verify-image.ps1.
        dism = guest.run(
            ["DISM.exe", "/Online", "/English", "/Cleanup-Image", "/StartComponentCleanup"]
            + ["/ResetBase"],
            check=False,
        )
        # Without the progress bars.
        lines = [
            line
            for line in (dism.stdout + dism.stderr).splitlines()
            if line.strip() and not line.lstrip().startswith("[")
        ]
        if dism.returncode:
            sys.stdout.write("warning: DISM cleanup failed:\n")
            sys.stdout.writelines(f"{line}\n" for line in lines[-6:])
        else:
            sys.stdout.writelines(f"{line}\n" for line in lines[-3:])

        # The provisioning files (first-logon.ps1 with the test password, the
        # SQL payload) stay out of the image; their logs go to the build's
        # work dir, next to install-mssql.log and SQL Server setup's last
        # Summary.txt.
        _step(rf"removing C:\setup (logs to {logs})")
        try:
            names = guest.powershell(r"(Get-ChildItem C:\setup -Filter *.log).Name").stdout
            for name in names.splitlines():
                guest.get(rf"C:\setup\{name}", logs / name)
        except VmError:
            sys.stdout.write("warning: copying the provisioning logs failed\n")
        guest.powershell(r"Remove-Item -Recurse -Force C:\setup")

        # Hands the free clusters back (discard=unmap), so the copy skips them.
        _step("releasing free space")
        if guest.powershell("Optimize-Volume -DriveLetter C -ReTrim", check=False).returncode:
            sys.stdout.write("warning: Optimize-Volume -ReTrim failed\n")
        _sizes(config, guest)

        _step("clean shutdown")
        _shutdown(vm, guest)


def _check_first_logon(guest: Guest) -> None:
    """first-logon.ps1 writes its marker last, before it powers the guest
    off: 'ok', or what failed."""
    try:
        marker = guest.read(_DONE).decode(errors="replace")
    except VmError as e:
        raise BuildError(f"first-logon.ps1 did not finish: {e}") from None
    if "".join(marker.split()) != "ok":
        try:
            log = guest.read(r"C:\setup\first-logon.log").decode("utf-8-sig", errors="replace")
        except VmError as e:
            log = f"(no first-logon.log: {e})"
        raise BuildError(f"first-logon.ps1 failed:\n{marker}\n{log}")


def _install_mssql(guest: Guest, logs: Path) -> None:
    """One run of install-mssql.ps1 in the console session; its full output
    to guest-logs, on the console without the lines the CU's self-extractor
    prints for every file it unpacks."""
    try:
        output = run_in_session(
            guest,
            r"powershell -NoProfile -ExecutionPolicy Bypass -File C:\setup\mssql\install-mssql.ps1"
            f" -SaPassword {guest.password} -MaxMemoryMB {MSSQL_MAX_MEMORY_MB}",
            3600,
        )
    except SessionError as e:
        _log_mssql(logs, e.log)
        try:
            summary = guest.read(_SQL_SUMMARY).decode(errors="replace")
        except VmError:
            summary = ""
        raise BuildError(f"SQL Server install failed (logs: {_SQL_SETUP_LOG}): {e}\n{summary}")
    _log_mssql(logs, output)


def _log_mssql(logs: Path, output: str) -> None:
    with (logs / "install-mssql.log").open("a") as log:
        log.write(output)
    sys.stdout.writelines(
        f"{line}\n" for line in output.splitlines() if not line.startswith("Preparing: ")
    )


def _verify(config: Config) -> str:
    """The Eval expiry, from a boot of exactly the device set the state
    action and the tests use: the checks see the guest as the tests will,
    as the Administrator in the console session (the SQL Server checks log
    in with Windows authentication)."""
    _step("verification boot")
    with _boot(config) as (vm, guest):
        _wait_ready(guest)
        guest.put(config.verify, _VERIFY)
        failure = None
        try:
            verification = run_in_session(
                guest,
                f"powershell -NoProfile -ExecutionPolicy Bypass -File {_VERIFY}"
                f" -SqlVersion {MSSQL_VERSION} -SqlMaxMemoryMB {MSSQL_MAX_MEMORY_MB}",
                900,
            )
        except SessionError as e:
            verification, failure = e.log, e
        (config.work / "verify.log").write_text(verification)
        sys.stdout.write(verification)
        if failure:
            raise BuildError(f"the image failed its verification: {failure}")
        if (expires := parse_expiry(verification)) is None:
            raise BuildError("no EVAL_EXPIRY in the verification output")
        guest.powershell(rf"Remove-Item {_VERIFY}")
        _shutdown(vm, guest)
    return expires


def _compress(config: Config, expires: str) -> None:
    _step("zstd-compressed copy")
    partial = config.out.with_name(config.out.name + ".tmp")
    # -W: out-of-order writes, the copy is only renamed once complete.
    subprocess.run(
        [str(config.qemu_img), "convert", "-W", "-c", "-O", "qcow2"]
        + ["-o", "compression_type=zstd", str(config.image), str(partial)],
        check=True,
    )
    partial.rename(config.out)
    if config.keep_work:
        sys.stdout.write(f"work dir kept: {config.work}\n")
    else:
        shutil.rmtree(config.work)
    sys.stdout.write(f"image: {config.out}\n")
    sys.stdout.write(f"size: {config.out.stat().st_size} bytes\n")
    sys.stdout.write(f"Eval expiry: {expires}\n")


if __name__ == "__main__":
    sys.exit(main())
