#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import getopt
import os
import sys
import time
from typing import NamedTuple, NoReturn, TypedDict

import paramiko

from cmk.utils.password_store import replace_passwords


def usage() -> NoReturn:
    sys.stderr.write(
        """
USAGE: check_sftp [OPTIONS] HOST

OPTIONS:
  --host HOST                SFTP server address
  --user USER                Username for sftp login
  --secret SECRET            Secret/Password for sftp login
  --port PORT                Alternative port number (default is 22 for the connection)
  --get-remote FILE          Path to the file which to pull from SFTP server (e.g.
                             /tmp/testfile.txt)
  --get-local PATH           Path to store the pulled file locally (e.g. $OMD_ROOT/tmp/)
  --put-local FILE           Path to the file to push to the sftp server. See above for example
  --put-remote PATH          Path to save the pushed file (e.g. /tmp/)
  --get-timestamp PATH       Path to the file for getting the timestamp of this file
  --timeout SECONDS          Set timeout for connection (default is 10 seconds)
  --verbose                  Output some more detailed information
  --look-for-keys            Search for discoverable keys in the user's "~/.ssh" directory
  -h, --help                 Show this help message and exit
    """
    )
    sys.exit(1)


def connection(
    opt_host: str | None,
    opt_user: str | None,
    opt_pass: str | None,
    opt_port: int,
    opt_timeout: float,
    opt_look_for_keys: bool,
) -> paramiko.sftp_client.SFTPClient:

    # The typing says that the connect method requires a hostname. Previously we passed None to it
    # if the argument was not set and paramiko did not check for that but passed it to
    # socket.getaddrinfo which assumes localhost.
    # I suggest we just be explicit about the default value here.
    if opt_host is None:
        opt_host = "localhost"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
    client.connect(
        opt_host,
        username=opt_user,
        password=opt_pass,
        port=opt_port,
        timeout=opt_timeout,
        look_for_keys=opt_look_for_keys,
    )
    return client.open_sftp()


class PathDict(TypedDict, total=False):
    put_filename: str
    get_filename: str
    local_get_path: str
    local_put_path: str
    remote_get_path: str
    remote_put_path: str
    timestamp_filename: str
    timestamp_path: str


def get_paths(
    opt_put_local: str | None,
    opt_get_local: str | None,
    opt_put_remote: str | None,
    opt_get_remote: str | None,
    opt_timestamp: str | None,
    omd_root: str | None,
    working_dir: str,
) -> PathDict:
    paths: PathDict = {}
    if opt_put_local:
        put_filename = opt_put_local.split("/")[-1]
        paths["put_filename"] = put_filename
        paths["local_put_path"] = f"{omd_root}/{opt_put_local}"
        if opt_put_remote:
            paths["remote_put_path"] = f"{working_dir}/{opt_put_remote}/{put_filename}"
        else:
            paths["remote_put_path"] = f"{working_dir}/{put_filename}"

    if opt_get_remote:
        get_filename = opt_get_remote.split("/")[-1]
        paths["get_filename"] = get_filename
        paths["remote_get_path"] = f"{working_dir}/{opt_get_remote}"
        if opt_get_local:
            paths["local_get_path"] = f"{omd_root}/{opt_get_local}/{get_filename}"
        else:
            paths["local_get_path"] = f"{omd_root}/{get_filename}"

    if opt_timestamp:
        paths["timestamp_filename"] = opt_timestamp.split("/")[-1]
        paths["timestamp_path"] = f"{working_dir}/{opt_timestamp}"

    return paths


def file_available(
    opt_put_local: str,
    opt_put_remote: str | None,
    sftp: paramiko.sftp_client.SFTPClient,
    working_dir: str,
) -> bool:
    filename = opt_put_local.split("/")[-1]
    return filename in sftp.listdir(f"{working_dir}/{opt_put_remote}")


def create_testfile(path: str) -> None:
    if os.path.isfile(path):
        return
    with open(path, "w") as f:
        f.write("This is a test by Check_MK\n")


def put_file(sftp: paramiko.sftp_client.SFTPClient, source: str, destination: str) -> None:
    sftp.put(source, destination)


def get_file(sftp: paramiko.sftp_client.SFTPClient, source: str, destination: str) -> None:
    sftp.get(source, destination)


def get_timestamp(sftp: paramiko.sftp_client.SFTPClient, path: str) -> int | None:
    return sftp.stat(path).st_mtime


def output_check_result(s: str) -> None:
    sys.stdout.write("%s\n" % s)


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


def parse_arguments(sys_args: None | list[str]) -> Args:  # pylint: disable=too-many-branches
    if sys_args is None:
        sys_args = sys.argv[1:]

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
        if opt in ["-h", "help"]:
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


def run_check(  # pylint: disable=too-many-branches
    sys_args: None | list[str] = None,
) -> tuple[int, str]:
    args = parse_arguments(sys_args)

    messages = []
    overall_state = 0
    try:  # Establish connection
        sftp = connection(
            args.host, args.user, args.pass_, args.port, args.timeout, args.look_for_keys
        )
        messages.append("Login successful")
    except Exception:
        if args.verbose:
            raise
        return 2, "Connection failed!"

    # Let's prepare for some other tests...
    omd_root = os.getenv("OMD_ROOT")
    if omd_root is None:
        sys.stderr.write("This check must be executed from within a site\n")
        sys.exit(1)

    sftp.chdir(".")
    working_dir = sftp.getcwd()
    assert working_dir is not None  # help mypy -- we just set it above, see getcwd() docs

    paths = get_paths(
        args.put_local,
        args.get_local,
        args.put_remote,
        args.get_remote,
        args.timestamp,
        omd_root,
        working_dir,
    )

    # .. and eventually execute them!
    if args.put_local is not None:
        try:  # Put a file to the server
            create_testfile(paths["local_put_path"])
            testfile_already_present = file_available(
                args.put_local, args.put_remote, sftp, working_dir
            )

            put_file(sftp, paths["local_put_path"], paths["remote_put_path"])
            if not testfile_already_present:
                sftp.remove(paths["remote_put_path"])

            messages.append("Successfully put file to SFTP server")
        except Exception:
            if args.verbose:
                raise
            overall_state = max(overall_state, 2)
            messages.append("Could not put file to SFTP server! (!!)")

    if args.get_remote is not None:
        try:  # Get a file from the server
            get_file(sftp, paths["remote_get_path"], paths["local_get_path"])
            messages.append("Successfully got file from SFTP server")
        except Exception:
            if args.verbose:
                raise
            overall_state = max(overall_state, 2)
            messages.append("Could not get file from SFTP server! (!!)")

    if args.timestamp is not None:
        try:  # Get timestamp of a remote file
            timestamp = get_timestamp(sftp, paths["timestamp_path"])
            messages.append(
                "Timestamp of {} is: {}".format(paths["timestamp_filename"], time.ctime(timestamp))
            )
        except Exception:
            if args.verbose:
                raise
            overall_state = max(overall_state, 2)
            messages.append("Could not get timestamp of file! (!!)")

    return overall_state, ", ".join(messages)


def main() -> int:
    replace_passwords()
    exitcode, info = run_check()
    output_check_result(info)
    return exitcode
