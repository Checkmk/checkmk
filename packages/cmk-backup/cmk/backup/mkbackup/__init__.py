#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import fcntl
import getopt
import glob
import os
import signal
import sys
import textwrap
import time
import traceback
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import NamedTuple, NoReturn

import cmk.ccc.version as cmk_version
from cmk.backup.utils.config import Config
from cmk.backup.utils.job import Job
from cmk.backup.utils.targets import TargetId
from cmk.backup.utils.targets.aws_s3_bucket import (
    S3Target,
)
from cmk.backup.utils.targets.azure_blob_storage import (
    BlobStorageTarget,
)
from cmk.backup.utils.targets.local import (
    LocalTarget,
)
from cmk.backup.utils.targets.protocol import Target
from cmk.backup.utils.type_defs import SiteBackupInfo
from cmk.backup.utils.utils import (
    current_site_id,
    do_site_backup,
    do_site_restore,
    hostname,
    Log,
    log,
    SITE_BACKUP_MARKER,
    State,
)
from cmk.ccc import daemon
from cmk.ccc.exceptions import (
    MKGeneralException,
    MKTerminate,
)
from cmk.utils import render, schedule

################
# Utility Code #
################


g_stdout_log = None
g_stderr_log = None


def start_logging(state: State) -> None:
    global g_stdout_log, g_stderr_log
    g_stdout_log = Log(1, state)
    g_stderr_log = Log(2, state)


def stop_logging() -> None:
    global g_stdout_log, g_stderr_log
    g_stderr_log = None
    g_stdout_log = None


target_classes: Mapping[str, type[Target]] = {
    "local": LocalTarget,
    "aws_s3_bucket": S3Target,
    "azure_blob_storage": BlobStorageTarget,
}


def load_target(config: Config, target_id: TargetId) -> Target:
    target_config = config.all_targets[target_id]
    target_type, params = target_config["remote"]
    try:
        return target_classes[target_type](target_id, params)
    except KeyError:
        raise MKGeneralException(
            f"Target type, {target_type}, not implemented. Choose one of {target_classes}"
        )


def backup_state(job: Job) -> State:
    path = Path(os.environ["OMD_ROOT"]) / "var" / "check_mk" / "backup"
    name = f"{job.local_id}.state"
    return State(path / name)


def restore_state() -> State:
    path = Path("/tmp")  # nosec B108 # BNS:13b2c8
    name = f"restore-{current_site_id()}.state"
    return State(path / name)


#   List: Alle Backups auflisten
#       Als Site-Nutzer sieht man nur die Site-Backups (auch die, die
#       durch die Systembackups erstellt wurden)
#   - Job-ID
#
#   Beispielbefehle:
#     # listet alle Backups auf die man sehen darf
#     mkbackup list nfs
#
#     # listet alle Backups auf die man sehen darf die zu diesem Job gehören
#     mkbackup list nfs --job=xxx
#
#   Restore:
#   - Job-ID
#   - Backup-ID
#     - Als Site-Nutzer muss man die Backup-ID eines Site-Backups angeben
#
#   Beispielbefehle:
#     # listet alle Backups auf die man sehen darf
#     mkbackup restore nfs backup-id-20
#
#   Show: Zeigt Metainfos zu einem Backup an
#   - Job-ID
#   - Backup-ID
#
#   Beispielbefehle:
#     mkbackup show nfs backup-id-20


class Arg(NamedTuple):
    id: str
    description: str


class Opt(NamedTuple):
    description: str


class Mode(NamedTuple):
    description: str
    args: list[Arg]
    opts: dict[str, Opt]
    runner: Callable[[list[str], dict[str, str], Config], None]


modes = {
    "backup": Mode(
        description=(
            "Starts creating a new backup. When executed as Check_MK site user, a backup of the "
            "current site is executed to the target of the given backup job."
        ),
        args=[
            Arg(
                id="Job-ID",
                description="The ID of the backup job to work with",
            ),
        ],
        opts={
            "background": Opt(description="Fork and execute the program in the background."),
        },
        runner=lambda args, opts, config: mode_backup(args[0], opts=opts, config=config),
    ),
    "restore": Mode(
        description=(
            "Starts the restore of a backup. In case you want to restore an encrypted backup, "
            "you have to provide the passphrase of the used backup key via the environment "
            "variable 'MKBACKUP_PASSPHRASE'. For example: MKBACKUP_PASSPHRASE='secret' mkbackup "
            "restore ARGS."
        ),
        args=[
            Arg(
                id="Target-ID",
                description="The ID of the backup target to work with",
            ),
            Arg(
                id="Backup-ID",
                description="The ID of the backup to restore",
            ),
        ],
        opts={
            "background": Opt(description="Fork and execute the program in the background."),
            "no-verify": Opt(
                description="Disable verification of the backup files to restore from."
            ),
        },
        runner=lambda args, opts, config: mode_restore(args[0], args[1], opts=opts, config=config),
    ),
    "jobs": Mode(
        description="Lists all configured backup jobs of the current user context.",
        args=[],
        opts={},
        runner=lambda _args, _opts, config: mode_jobs(config=config),
    ),
    "targets": Mode(
        description="Lists all configured backup targets of the current user context.",
        args=[],
        opts={},
        runner=lambda _args, _opts, config: mode_targets(config=config),
    ),
    "list": Mode(
        description="Output the list of all backups found on the given backup target",
        args=[
            Arg(
                id="Target-ID",
                description="The ID of the backup target to work with",
            ),
        ],
        opts={},
        runner=lambda args, _opts, config: mode_list(args[0], config=config),
    ),
}


def get_lock_file() -> Path:
    # `omd` will delete the files, which are not in `.restore_working_dir`. This would break the
    # file locks, since processes would then hold a stale file descriptor.
    return Path(os.environ["OMD_ROOT"], ".restore_working_dir", "mkbackup.lock")


def mode_backup(local_job_id: str, opts: dict[str, str], config: Config) -> None:
    job = load_job(local_job_id, config)
    target = load_target(config, job.config["target"])
    target.check_ready()

    # This lock protects multiple state files (`backup_state`) and the to which the backup is
    # written. `omd backup` also has its own locking mechanism to protect the actual backup process.
    with exclusive_owner(
        get_lock_file(),
        "Another backup or restore is already running.",
    ):
        state = backup_state(job)
        save_next_run(job, state)

        if "background" in opts:
            daemon.daemonize()
            state.update_and_save(pid=os.getpid())

        start_logging(state)
        log(f"--- Starting backup ({job.id} to {target.id}) ---")

        success = False
        try:
            state.update_and_save(state="running")
            temp_path = target.start_backup(job)
            info = do_site_backup(temp_path, job, state, opt_verbose, opt_debug)
            target.finish_backup(info, job)
            complete_backup(state, info)
            success = True

        except MKGeneralException as e:
            sys.stderr.write(f"{e}\n")
            if opt_debug:
                raise

        except Exception:
            if opt_debug:
                raise
            sys.stderr.write("An exception occurred:\n")
            sys.stderr.write(traceback.format_exc())

        finally:
            stop_logging()
            state.update_and_save(
                state="finished",
                finished=time.time(),
                success=success,
            )


def complete_backup(state_admin: State, info: SiteBackupInfo) -> None:
    state_admin.update_and_save(size=info.size)
    duration = time.time() - (state_admin.current_state.started or 0)
    log(
        f"--- Backup completed (Duration: {render.timespan(duration)}, Size: {render.fmt_bytes(info.size)}, IO: {render.fmt_bytes(state_admin.current_state.bytes_per_second or 0)}/s) ---"
    )


def load_job(local_job_id: str, config: Config) -> Job:
    g_job_id = globalize_job_id(local_job_id)

    if local_job_id not in config.site.jobs:
        raise MKGeneralException("This backup job does not exist.")

    job = Job(config=config.site.jobs[local_job_id], local_id=local_job_id, id=g_job_id)
    return job


def globalize_job_id(local_job_id: str) -> str:
    parts = [SITE_BACKUP_MARKER, hostname(), current_site_id(), local_job_id]
    return "-".join(p.replace("-", "+") for p in parts)


def save_next_run(job: Job, state: State) -> None:
    schedule_cfg = job.config["schedule"]
    if not schedule_cfg:
        next_schedule: str | float | None = None

    elif schedule_cfg["disabled"]:
        next_schedule = "disabled"

    else:
        # find the next time of all configured times
        times = []
        for timespec in schedule_cfg["timeofday"]:
            times.append(schedule.next_scheduled_time(schedule_cfg["period"], timespec))
        next_schedule = min(times)

    state.update_and_save(next_schedule=next_schedule)


def cleanup_backup_job_states() -> None:
    path = f"{os.environ['OMD_ROOT']}/var/check_mk/backup"

    for f in glob.glob(f"{path}/*.state"):
        if os.path.basename(f) != "restore.state" and not os.path.basename(f).startswith(
            "restore-"
        ):
            os.unlink(f)


@contextmanager
def exclusive_owner(path: Path, message: str) -> Iterator[None]:
    """Ensure that this process is unique per site (analogous to a PID file lock).

    Child processes that exec a new program will not inherit this lock (O_CLOEXEC).
    Forked children that do not exec will still inherit it.

    This implementation is deliberately minimal. It foregoes handling edge cases (e.g., io_uring
    lingering, orphaned inodes after unlinking, or symlink TOCTOU attacks) in favor of the
    following strict assumptions:

    * `path` must be in a dedicated directory protected by access permissions (e.g., `/run` or
      `/var/lock`). Do not use shared sticky-bit directories like `/tmp`.
    * `path` must reside on a local filesystem. `flock` semantics are unreliable on network mounts
      (NFS) and FAT. In practice this is not a concern: Linux has supported advisory NFS locks via
      lockd/NLM since 2.6.12 (2005), and FAT does not support symlinks, making it unsuitable for
      hosting a Checkmk site regardless. `flock` is used elsewhere already (e.g. CMC and
      `cmk.ccc.store`).
    * `path` must never be deleted while the process is running, as `flock` locks the underlying
       inode, not the path.
    * `flock` is per-process, not per-thread. It does not prevent race conditions between threads.

    For locking implementations that securely handles these edge cases, see:
    * TigerBeetle: https://github.com/tigerbeetle/tigerbeetle/blob/f051a0b0e15c77b292a4ca1e9409db41e35703e1/src/io/linux.zig#L1609-L1652
    * Systemd: https://github.com/systemd/systemd/blob/37c272228dbdbcb4f60609d273d1352ccac061b7/src/tmpfiles/tmpfiles.c#L761
    * Filelock: https://github.com/tox-dev/filelock/blob/eb526ec4edfd91aef607b54bf77a467f04b8f897/src/filelock/_unix.py#L33-L111
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDONLY | os.O_CREAT | os.O_CLOEXEC, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit(message)
        yield
    finally:
        with suppress(OSError):
            os.close(fd)


def mode_restore(target_id: str, backup_id: str, opts: dict[str, str], config: Config) -> None:
    target = load_target(config, TargetId(target_id))
    target.check_ready()

    # This lock protects multiple state files (`restore_state`) and there are not multiple processes
    # writting to the site directory. `omd restore` will detect site processes running, so it can't
    # run concurrently to begin with.
    with exclusive_owner(
        get_lock_file(),
        "Another backup or restore is already running.",
    ):
        state = restore_state()

        if "background" in opts:
            daemon.daemonize()
            state.update_and_save(pid=os.getpid())

        start_logging(state)

        log(f"--- Collecting data for restore ({backup_id}) ---")
        backup = target.get_backup(backup_id)

        log(f"--- Starting restore ({backup_id}) ---")

        success = False
        try:
            state.update_and_save(state="running")

            do_site_restore(backup, state, opt_debug)
            complete_restore(state)
            success = True

        except MKGeneralException as e:
            sys.stderr.write(f"{e}\n")
            if opt_debug:
                raise

        except Exception:
            if opt_debug:
                raise
            sys.stderr.write("An exception occurred:\n")
            sys.stderr.write(traceback.format_exc())

        finally:
            stop_logging()
            state.update_and_save(
                state="finished",
                finished=time.time(),
                success=success,
            )


def complete_restore(state: State) -> None:
    cleanup_backup_job_states()
    duration = time.time() - (state.current_state.started or 0)
    log(
        f"--- Restore completed (Duration: {render.timespan(duration)}, IO: {render.fmt_bytes(state.current_state.bytes_per_second or 0)}/s) ---"
    )


def mode_list(target_id: str, config: Config) -> None:
    if target_id not in config.all_targets:
        raise MKGeneralException(
            f"This backup target does not exist. Choose one of: {', '.join(config.all_targets.keys())}"
        )
    target = load_target(config, TargetId(target_id))
    target.check_ready()

    fmt = "%-20s %-16s %52s\n"
    fmt_detail = (" " * 30) + " %-20s %48s\n"
    sys.stdout.write(fmt % ("Job", "Details", ""))
    sys.stdout.write("%s\n" % ("-" * 100))
    for backup_id, info in target.list_backups():
        from_info = info.hostname
        from_info += f" (Site: {info.site_id})"
        sys.stdout.write(fmt % (info.job_id, "Backup-ID:", backup_id))

        sys.stdout.write(fmt_detail % ("From:", from_info))
        sys.stdout.write(fmt_detail % ("Finished:", render.date_and_time(info.finished)))
        sys.stdout.write(fmt_detail % ("Size:", render.fmt_bytes(info.size)))
        if info.config["encrypt"] is not None:
            sys.stdout.write(fmt_detail % ("Encrypted:", info.config["encrypt"]))
        else:
            sys.stdout.write(fmt_detail % ("Encrypted:", "No"))
        sys.stdout.write("\n")
    sys.stdout.write("\n")


def mode_jobs(config: Config) -> None:
    fmt = "%-29s %-30s\n"
    sys.stdout.write(fmt % ("Job-ID", "Title"))
    sys.stdout.write("%s\n" % ("-" * 60))
    for job_id, job_cfg in sorted(config.site.jobs.items(), key=lambda x_y: x_y[0]):
        sys.stdout.write(fmt % (job_id, job_cfg["title"]))


def mode_targets(config: Config) -> None:
    fmt = "%-29s %-30s\n"
    sys.stdout.write(fmt % ("Target-ID", "Title"))
    sys.stdout.write("%s\n" % ("-" * 60))
    for job_id, job_cfg in sorted(config.all_targets.items(), key=lambda x_y1: x_y1[0]):
        sys.stdout.write(fmt % (job_id, job_cfg["title"]))


def usage(error: str | None = None) -> NoReturn:
    if error:
        sys.stderr.write(f"ERROR: {error}\n")
    sys.stdout.write("Usage: mkbackup [OPTIONS] MODE [MODE_ARGUMENTS...] [MODE_OPTIONS...]\n")
    sys.stdout.write("\n")
    sys.stdout.write("OPTIONS:\n")
    sys.stdout.write("\n")
    sys.stdout.write("    --verbose     Enable verbose output, twice for more details\n")
    sys.stdout.write("    --debug       Let Python exceptions come through\n")
    sys.stdout.write("    --version     Print the version of the program\n")
    sys.stdout.write("\n")
    sys.stdout.write("MODES:\n")
    sys.stdout.write("\n")

    for mode_name, mode in sorted(modes.items()):
        mode_indent = " " * 18
        wrapped_descr = textwrap.fill(
            mode.description,
            width=82,
            initial_indent=f"    {mode_name:13} ",
            subsequent_indent=mode_indent,
        )
        sys.stdout.write(wrapped_descr + "\n")
        sys.stdout.write("\n")
        if mode.args:
            sys.stdout.write(f"{mode_indent}MODE ARGUMENTS:\n")
            sys.stdout.write("\n")
            for arg in mode.args:
                sys.stdout.write(f"{mode_indent}  {arg.id:10} {arg.description}\n")
            sys.stdout.write("\n")

        opts = mode_options(mode)
        if opts:
            sys.stdout.write(f"{mode_indent}MODE OPTIONS:\n")
            sys.stdout.write("\n")

            for opt_id, opt in sorted(opts.items(), key=lambda k_v: k_v[0]):
                sys.stdout.write(f"{mode_indent}  --{opt_id:13} {opt.description}\n")
            sys.stdout.write("\n")

    sys.stdout.write("\n")
    sys.exit(3)


def mode_options(mode: Mode) -> dict[str, Opt]:
    opts = {}
    opts.update(mode.opts)
    return opts


def interrupt_handler(signum: int, _frame: object) -> NoReturn:
    raise MKTerminate(f"Caught signal: {signum}")


def register_signal_handlers() -> None:
    signal.signal(signal.SIGTERM, interrupt_handler)


opt_verbose = 0
opt_debug = False


def parse_arguments():
    global opt_verbose, opt_debug
    short_options = "h"
    long_options = ["help", "version", "verbose", "debug"]

    try:
        opts, args = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.GetoptError as e:
        usage(f"{e}")

    for o, _unused_a in opts:
        if o in ["-h", "--help"]:
            usage()
        elif o == "--version":
            sys.stdout.write(f"mkbackup {cmk_version.__version__}\n")
            sys.exit(0)
        elif o == "--verbose":
            opt_verbose += 1
        elif o == "--debug":
            opt_debug = True

    try:
        mode_name = args.pop(0)
    except IndexError:
        usage("Missing operation mode")

    try:
        mode = modes[mode_name]
    except KeyError:
        usage("Invalid operation mode")

    # Load the mode specific options
    try:
        mode_opts, mode_args = getopt.getopt(args, "", list(mode_options(mode).keys()))
    except getopt.GetoptError as e:
        usage(f"{e}")

    # Validate arguments
    if len(mode_args) != len(mode.args):
        usage("Invalid number of arguments for this mode")

    return mode, mode_args, mode_opts, opts


def main() -> None:
    register_signal_handlers()
    config = Config.load()
    mode, mode_args, mode_opts, opts = parse_arguments()
    try:
        current_site_id()
    except KeyError:
        raise MKGeneralException("Running outside of site context.")
    opt_dict = {k.lstrip("-"): v for k, v in opts + mode_opts}
    mode.runner(mode_args, opt_dict, config)


def cli_main() -> int:
    try:
        main()
    except MKTerminate as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    except KeyboardInterrupt:
        sys.stderr.write("Terminated.\n")
        return 0

    except MKGeneralException as exc:
        sys.stderr.write(f"{exc}\n")
        if opt_debug:
            raise
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(cli_main())
