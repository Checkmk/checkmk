#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import getopt
import os
import sys
import time
from typing import NamedTuple, NoReturn

import paramiko

from cmk.utils.password_store import replace_passwords

_LOCAL_DIR = "var/check_mk/active_checks/check_sftp"


def usage() -> NoReturn:
    sys.stderr.write(
        f"""USAGE: check_sftp OPTIONS

OPTIONS:
  --host HOST                SFTP server address
  --user USER                Username for sftp login
  --secret SECRET            Secret/Password for sftp login
  --port PORT                Alternative port number (default is 22)
  --get-remote FILE          Path on the remote to the file that should be pulled from server (relative to the remote home)
  --get-local DIRECTORY      Path where the pulled file should be stored (relative to '{_LOCAL_DIR}' in the site's directory)
  --put-local FILE           Path to the file to push to server (relative to '{_LOCAL_DIR}' in the site's directory). If the file does not exist, it will be created with a test message.
  --put-remote DIRECTORY     Path on the remote where the pushed file should be stored (relative to the remote home)
  --get-timestamp PATH       Path to the file on the remote server for which the timestamp should be checked
  --timeout SECONDS          Set timeout for connection (default is 10 seconds)
  --look-for-keys            Search for discoverable keys in the user's "~/.ssh" directory
  -v, --verbose              Output some more detailed information
  -h, --help                 Show this help message and exit
"""
    )
    sys.exit(1)


class SecurityError(ValueError):
    """Raised when a security issue is detected, such as attempted path traversal."""


class Args(NamedTuple):
    host: None | str
    user: None | str
    pass_: None | str
    port: int
    get_remote: None | str
    get_local: None | str
    put_local: None | str
    put_remote: None | str
    timestamp: None | str
    timeout: float
    verbose: bool
    look_for_keys: bool


def parse_arguments(sys_args: list[str]) -> Args:  # pylint: disable=too-many-branches
    opt_host = None
    opt_user = None
    opt_pass = None
    opt_port = 22
    opt_get_remote = None
    opt_get_local = None
    opt_put_local = None
    opt_put_remote = None
    opt_timestamp = None
    opt_timeout = 10.0
    opt_verbose = False
    opt_look_for_keys = False

    short_options = "hv"
    long_options = [
        "host=",
        "user=",
        "secret=",
        "port=",
        "get-remote=",
        "get-local=",
        "put-local=",
        "put-remote=",
        "get-timestamp=",
        "verbose",
        "help",
        "timeout=",
        "look-for-keys",
    ]

    try:
        opts, _args = getopt.getopt(sys_args, short_options, long_options)
    except getopt.GetoptError as err:
        sys.stderr.write("%s\n" % err)
        sys.exit(1)

    for opt, arg in opts:
        if opt in ["-h", "--help"]:
            usage()
        elif opt in ["--host"]:
            opt_host = arg
        elif opt in ["--user"]:
            opt_user = arg
        elif opt in ["--secret"]:
            opt_pass = arg
        elif opt in ["--port"]:
            opt_port = int(arg)
        elif opt in ["--timeout"]:
            opt_timeout = float(arg)
        elif opt in ["--put-local"]:
            opt_put_local = arg
        elif opt in ["--put-remote"]:
            opt_put_remote = arg
        elif opt in ["--get-local"]:
            opt_get_local = arg
        elif opt in ["--get-remote"]:
            opt_get_remote = arg
        elif opt in ["--get-timestamp"]:
            opt_timestamp = arg
        elif opt in ["--look-for-keys"]:
            opt_look_for_keys = True
        elif opt in ["-v", "--verbose"]:
            opt_verbose = True

    return Args(
        opt_host,
        opt_user,
        opt_pass,
        opt_port,
        opt_get_remote,
        opt_get_local,
        opt_put_local,
        opt_put_remote,
        opt_timestamp,
        opt_timeout,
        opt_verbose,
        opt_look_for_keys,
    )


def output_check_result(s: str) -> None:
    sys.stdout.write("%s\n" % s)


class CheckSftp:
    @property
    def local_directory(self) -> str:
        return f"{self.omd_root}/{_LOCAL_DIR}"

    def is_in_local_directory(self, path: str) -> bool:
        return os.path.normpath(path).startswith(self.local_directory)

    class TransferOptions(NamedTuple):
        local: str
        remote: str

    def __init__(self, client: paramiko.SSHClient, omd_root: str, args: Args):
        self.omd_root = omd_root
        self.host: str = args.host or "localhost"
        self.user: str | None = args.user
        self.pass_: str | None = args.pass_
        self.port: int = args.port
        self.timeout: float = args.timeout
        self.look_for_keys: bool = args.look_for_keys
        self.verbose: bool = args.verbose

        self.connection = self.connect(client)

        remote_workdir = self.connection.getcwd()
        assert remote_workdir is not None  # help mypy -- we just set it above, see getcwd() docs

        self.upload_options: None | CheckSftp.TransferOptions = (
            None
            if args.put_local is None
            else self.process_put_options(
                self.local_directory, args.put_local, remote_workdir, args.put_remote
            )
        )

        self.download_options: None | CheckSftp.TransferOptions = (
            None
            if args.get_remote is None
            else self.process_get_options(
                remote_workdir, args.get_remote, self.local_directory, args.get_local
            )
        )

        self.timestamp_path: None | str = (
            os.path.normpath(f"{remote_workdir}/{args.timestamp}") if args.timestamp else None
        )

    @staticmethod
    def resolve_transfer_paths(src_file: str, dst_dir: str) -> tuple[str, str]:
        """Normalize the paths and append the src file name to the destination directory."""
        return (
            os.path.normpath(src_file),
            os.path.normpath(f"{dst_dir}/{src_file.split('/')[-1]}"),
        )

    def process_put_options(
        self, local_base: str, local_file: str, remote_base: str, remote_dir: str | None
    ) -> None | TransferOptions:
        local, remote = self.resolve_transfer_paths(
            f"{local_base}/{local_file}", f"{remote_base}/{remote_dir or '.'}"
        )

        if not self.is_in_local_directory(local):
            raise SecurityError("Invalid local path for put operation")

        return CheckSftp.TransferOptions(local, remote)

    def process_get_options(
        self, remote_base: str, remote_file: str, local_base: str, local_dir: str | None
    ) -> None | TransferOptions:
        remote, local = self.resolve_transfer_paths(
            f"{remote_base}/{remote_file}", f"{local_base}/{local_dir or '.'}"
        )

        if not self.is_in_local_directory(local):
            raise SecurityError("Invalid local path for get operation")

        return CheckSftp.TransferOptions(local, remote)

    def connect(self, client: paramiko.SSHClient) -> paramiko.sftp_client.SFTPClient:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
        client.connect(
            hostname=self.host,
            username=self.user,
            password=self.pass_,
            port=self.port,
            timeout=self.timeout,
            look_for_keys=self.look_for_keys,
        )
        sftp = client.open_sftp()
        sftp.chdir(".")  # make sure we have a working directory, see sftp.getcwd() docs
        return sftp

    @staticmethod
    def remote_has_file(sftp: paramiko.sftp_client.SFTPClient, path: str) -> bool:
        try:
            sftp.stat(path)
            return True
        except FileNotFoundError:
            return False

    @staticmethod
    def get_timestamp(sftp: paramiko.sftp_client.SFTPClient, path: str) -> float | None:
        return sftp.stat(path).st_mtime

    def check_file_upload(self) -> None:
        assert self.upload_options is not None
        local_file = self.upload_options.local

        if not os.path.isfile(local_file):
            os.makedirs(os.path.dirname(local_file), exist_ok=True)
            with open(local_file, "w") as f:
                f.write("This is a test by Check_MK\n")

        self.connection.put(local_file, self.upload_options.remote)

    def check_file_download(self) -> None:
        assert self.download_options is not None
        os.makedirs(os.path.dirname(self.download_options.local), exist_ok=True)
        self.connection.get(self.download_options.remote, self.download_options.local)

    def run_optional_checks(self) -> tuple[int, list[str]]:
        status, messages = 0, []

        # Remove the uploaded file if it didn't exist. But only at the very end, since
        # we might need it for the download check.
        new_file_on_remote: None | str = None

        if self.upload_options is not None:
            try:
                if not self.remote_has_file(self.connection, self.upload_options.remote):
                    new_file_on_remote = self.upload_options.remote

                self.check_file_upload()
                messages.append("Successfully put file to SFTP server")
            except Exception:
                if self.verbose:
                    raise
                status = max(status, 2)
                messages.append("Could not put file to SFTP server! (!!)")

        if self.download_options is not None:
            try:
                self.check_file_download()
                messages.append("Successfully got file from SFTP server")
            except Exception:
                if self.verbose:
                    raise
                status = max(status, 2)
                messages.append("Could not get file from SFTP server! (!!)")

        if self.timestamp_path is not None:
            try:
                timestamp = self.get_timestamp(self.connection, self.timestamp_path)
                messages.append(
                    "Timestamp of {} is: {}".format(
                        self.timestamp_path.split("/")[-1], time.ctime(timestamp)
                    )
                )
            except Exception:
                if self.verbose:
                    raise
                status = max(status, 2)
                messages.append("Could not get timestamp of file! (!!)")

        if new_file_on_remote is not None:
            self.connection.remove(new_file_on_remote)

        return status, messages


def main() -> int:
    if (omd_root := os.getenv("OMD_ROOT")) is None:
        sys.stderr.write("This check must be executed from within a site\n")
        sys.exit(1)

    replace_passwords()
    args = parse_arguments(sys.argv[1:])

    try:
        check = CheckSftp(paramiko.SSHClient(), omd_root, args)
    except SecurityError as e:
        if args.verbose:
            raise
        output_check_result(f"Security issue detected: {e}")
        return 2
    except Exception:
        if args.verbose:
            raise
        output_check_result("Connection failed!")
        return 2

    login_info = ["Login successful"]
    status, checks_info = check.run_optional_checks()
    output_check_result(", ".join(login_info + checks_info))
    return status
