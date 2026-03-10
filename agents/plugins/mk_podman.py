#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import configparser
import json
import os
import pwd
import shlex
import socket
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from shutil import which
from typing import Any, Literal, TypedDict, TypeVar, Union

# override decorator is only available in Python 3.12+
try:
    from typing import override
except ImportError:
    _F = TypeVar("_F", bound=Callable[..., object])

    def override(func: _F, /) -> _F:
        return func


__version__ = "2.5.0b1"

DEFAULT_CFG_FILE = Path(os.getenv("MK_CONFDIR", "")) / "mk_podman.cfg"

DEFAULT_CFG_SECTION = {
    "socket_detection_method": "auto",
    "socket_paths": "",
    "piggyback_name_method": "nodename_name",
}

DEFAULT_SOCKET_PATH = "/run/podman/podman.sock"

DEFAULT_SCHEME = "http+unix://"

CLI_TIMEOUT_SECONDS = 30

PODMAN_API_VERSION = "v4.0.0"


# The checks below result in agent sections being created. This
# is a way to end the plugin in case it is being executed on a non-podman host
if (
    not os.path.isdir("/var/lib/podman")
    and not os.path.isdir("/run/podman")
    and not which("podman")
):
    sys.stderr.write("mk_podman.py: Does not seem to be a podman host. Terminating.\n")
    sys.exit(1)


class AutomaticSocketDetectionMethod(Enum):
    AUTO = "auto"
    ONLY_ROOT_SOCKET = "only_root_socket"
    ONLY_USER_SOCKETS = "only_user_sockets"


class PiggybackNameMethod(Enum):
    NAME = "name"
    NODENAME_NAME = "nodename_name"
    NAME_ID = "name_id"


class PodmanConfig(TypedDict):
    socket_detection: Union[AutomaticSocketDetectionMethod, tuple[Literal["manual"], Sequence[str]]]
    piggyback_name_method: PiggybackNameMethod


def _parse_piggyback_name_method(value: str, cfg_file: Path) -> PiggybackNameMethod:
    try:
        return PiggybackNameMethod(value)
    except ValueError:
        write_section(
            Error(
                "config",
                f"Invalid piggyback_name_method '{value}' in {cfg_file}. "
                f"Valid options are: {', '.join(m.value for m in PiggybackNameMethod)}. "
                "Using default 'nodename_name'.",
            )
        )
        return PiggybackNameMethod.NODENAME_NAME


def load_cfg(cfg_file: Path = DEFAULT_CFG_FILE) -> Union[PodmanConfig, None]:
    config = configparser.ConfigParser(DEFAULT_CFG_SECTION)

    if not cfg_file.is_file():
        return None

    try:
        config.read(cfg_file)
        section_name = "PODMAN" if config.sections() else "DEFAULT"
        conf_dict = dict(config.items(section_name))

        method = conf_dict["socket_detection_method"]
        socket_paths_str = conf_dict["socket_paths"]
        piggyback_name_method = _parse_piggyback_name_method(
            conf_dict.get("piggyback_name_method", "name"), cfg_file
        )

        if method == "manual" and socket_paths_str:
            socket_paths = [p.strip() for p in socket_paths_str.split(",") if p.strip()]
            return PodmanConfig(
                socket_detection=("manual", socket_paths),
                piggyback_name_method=piggyback_name_method,
            )
        return PodmanConfig(
            socket_detection=AutomaticSocketDetectionMethod(method),
            piggyback_name_method=piggyback_name_method,
        )

    except Exception as e:
        write_section(
            Error(
                "config",
                f"Failed to load config file {cfg_file}: {e}. Using 'auto' method as default.",
            )
        )
        return None


def find_user_sockets() -> Sequence[str]:
    run_user_dir = "/run/user"

    if not os.path.isdir(run_user_dir):
        return []

    return [
        os.path.join(run_user_dir, entry, "podman", "podman.sock")
        for entry in os.listdir(run_user_dir)
        if os.path.exists(os.path.join(run_user_dir, entry, "podman", "podman.sock"))
    ]


def find_podman_users_from_conmon() -> Sequence[Union[str, None]]:
    users: set[str] = set()

    try:
        # Use UID instead of username to avoid truncation issues with ps
        result = subprocess.run(
            ["ps", "-e", "-o", "uid=", "-o", "comm="],
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_SECONDS,
            check=False,
        )
        if result.returncode != 0:
            sys.stderr.write(
                f"mk_podman.py: 'ps' command failed (rc={result.returncode}): "
                f"{result.stderr.strip()}. Falling back to root user only.\n"
            )
            return [None]

        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "conmon":
                try:
                    uid = int(parts[0])
                    if uid != 0:
                        pw_entry = pwd.getpwuid(uid)
                        users.add(pw_entry.pw_name)
                except (ValueError, KeyError):
                    # Skip if UID is invalid or user not found
                    continue
    except Exception as e:
        sys.stderr.write(
            f"mk_podman.py: Failed to discover podman users from conmon: {e}. "
            "Falling back to root user only.\n"
        )
        return [None]

    # Always include root/current user first
    result_list: list[Union[str, None]] = [None]
    result_list.extend(sorted(users))
    return result_list


def get_socket_paths(config: Union[PodmanConfig, None]) -> Sequence[str]:
    if (
        config is None
        or (socket_detection := config["socket_detection"]) is AutomaticSocketDetectionMethod.AUTO
    ):
        socket_paths = [DEFAULT_SOCKET_PATH]
        socket_paths.extend(find_user_sockets())
        return socket_paths

    if socket_detection is AutomaticSocketDetectionMethod.ONLY_ROOT_SOCKET:
        return [DEFAULT_SOCKET_PATH]

    if socket_detection is AutomaticSocketDetectionMethod.ONLY_USER_SOCKETS:
        return find_user_sockets()

    return socket_detection[1]


@dataclass(frozen=True)
class JSONSection:
    name: str
    content: str


@dataclass(frozen=True)
class Error:
    label: str
    message: str


def write_sections(sections: Sequence[Union[JSONSection, Error]]) -> None:
    for section in sections:
        write_section(section)


def write_section(section: Union[JSONSection, Error]) -> None:
    if isinstance(section, JSONSection):
        write_serialized_section(section.name, section.content)
    elif isinstance(section, Error):
        write_serialized_section(
            "errors",
            json.dumps({"endpoint": section.label, "message": section.message}),
        )


def write_serialized_section(name: str, json_content: str) -> None:
    sys.stdout.write(f"<<<podman_{name}:sep(0)>>>\n")
    sys.stdout.write(f"{json_content}\n")
    sys.stdout.flush()


def write_piggyback_section(target_host: str, section: Union[JSONSection, Error]) -> None:
    sys.stdout.write(f"<<<<{target_host}>>>>\n")
    write_section(section)
    sys.stdout.write("<<<<>>>>\n")
    sys.stdout.flush()


try:
    from requests import Session
    from requests.adapters import HTTPAdapter
    from urllib3.connection import HTTPConnection
    from urllib3.connectionpool import HTTPConnectionPool
except ImportError:
    write_section(
        Error(
            label="Missing Python dependency: requests.",
            message="Import error: No module named 'requests'. "
            "Install the OS package (for example: python3-requests on RHEL/Rocky via EPEL) "
            "or the pip package 'requests'. ",
        )
    )
    sys.exit(0)


# This was taken from cmk.utils.unixsocket_http
# But, since we don't have access to that module here, we reimplement it.
def make_unixsocket_session(
    socket_path: Path,
    target_base_url: str,
) -> Session:
    session = Session()
    session.trust_env = False
    session.mount(
        target_base_url,
        _LocalAdapter(socket_path),
    )
    return session


class _LocalConnection(HTTPConnection):
    def __init__(self, socket_path: Path) -> None:
        super().__init__("localhost")
        self._socket_path = socket_path

    @override
    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(str(self._socket_path))


class _LocalConnectionPool(HTTPConnectionPool):
    def __init__(self, socket_path: Path) -> None:
        super().__init__("localhost")
        self._connection = _LocalConnection(socket_path)

    # TODO: Why does `@override` not work here?
    def _new_conn(self) -> _LocalConnection:
        return self._connection


class _LocalAdapter(HTTPAdapter):
    def __init__(self, socket_path: Path) -> None:
        super().__init__()
        self._connection_pool = _LocalConnectionPool(socket_path)

    @override
    def get_connection(
        self,
        url: Union[str, bytes],
        proxies: object = None,
    ) -> _LocalConnectionPool:
        return self._connection_pool

    @override
    def get_connection_with_tls_context(
        self,
        request: object,
        verify: object,
        proxies: object = None,
        cert: object = None,
    ) -> _LocalConnectionPool:
        return self._connection_pool


# =============================================================================
# CLI-based query functions (for socket-less configurations)
# =============================================================================


def run_podman_command(
    args: Sequence[str], run_as_user: Union[str, None] = None
) -> Union[str, Error]:
    try:
        cmd = ["podman", *args]
        if run_as_user and os.geteuid() == 0:
            cmd = ["su", "-", "--", run_as_user, "-c", shlex.join(cmd)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_SECONDS,
            check=False,
        )
        if result.returncode != 0:
            return Error(f"podman {' '.join(args)}", result.stderr.strip())
        return result.stdout
    except subprocess.TimeoutExpired:
        return Error(
            f"podman {' '.join(args)}", f"Command timed out after {CLI_TIMEOUT_SECONDS} seconds"
        )
    except FileNotFoundError:
        return Error(f"podman {' '.join(args)}", "podman command not found")
    except Exception as e:
        return Error(f"podman {' '.join(args)}", str(e))


def _strip_login_banner(output: str) -> str:
    """Strip login banner/MOTD lines printed by 'su -' before the actual JSON output."""
    for i, line in enumerate(output.splitlines()):
        if line.lstrip().startswith(("{", "[")):
            return "\n".join(output.splitlines()[i:])
    return output


def _run_cli_json_query(
    args: Sequence[str],
    section_name: str,
    default: Any = None,
    run_as_user: Union[str, None] = None,
    transform: Union[Callable[[Any], Any], None] = None,
) -> Union[JSONSection, Error]:
    result = run_podman_command(args, run_as_user)
    if isinstance(result, Error):
        return result
    try:
        result = _strip_login_banner(result)
        data = json.loads(result) if result.strip() else default
        if transform is not None:
            data = transform(data)
        return JSONSection(section_name, json.dumps(data))
    except json.JSONDecodeError as e:
        return Error(f"podman {' '.join(args)}", f"Failed to parse JSON: {e}")


def query_containers_cli(
    run_as_user: Union[str, None] = None,
) -> Union[JSONSection, Error]:
    return _run_cli_json_query(
        ["ps", "--all", "--format", "json"],
        "containers",
        default=[],
        run_as_user=run_as_user,
        transform=lambda cs: [c for c in cs if not c.get("IsInfra", False)],
    )


def query_disk_usage_cli(
    run_as_user: Union[str, None] = None,
) -> Union[JSONSection, Error]:
    return _run_cli_json_query(
        ["system", "df", "--format", "json"], "disk_usage", default={}, run_as_user=run_as_user
    )


def query_engine_cli(
    run_as_user: Union[str, None] = None,
) -> Union[JSONSection, Error]:
    return _run_cli_json_query(
        ["info", "--format", "json"], "engine", default={}, run_as_user=run_as_user
    )


def query_pods_cli(
    run_as_user: Union[str, None] = None,
) -> Union[JSONSection, Error]:
    return _run_cli_json_query(
        ["pod", "ps", "--format", "json"], "pods", default=[], run_as_user=run_as_user
    )


def query_container_inspect_cli(
    container_id: str,
    run_as_user: Union[str, None] = None,
) -> Union[JSONSection, Error]:
    return _run_cli_json_query(
        ["inspect", container_id],
        "container_inspect",
        default=[],
        run_as_user=run_as_user,
        transform=lambda d: d[0] if isinstance(d, list) and d else d,
    )


def query_raw_stats_cli(
    run_as_user: Union[str, None] = None,
) -> Union[Mapping[str, object], Error]:
    result = run_podman_command(["stats", "--all", "--no-stream", "--format", "json"], run_as_user)
    if isinstance(result, Error):
        return result
    try:
        result = _strip_login_banner(result)
        stats_list = json.loads(result) if result.strip() else []
        # Convert to the same format as the API response
        return {"Stats": stats_list}
    except json.JSONDecodeError as e:
        return Error("podman stats", f"Failed to parse JSON: {e}")


def handle_containers_stats_cli(
    containers: Sequence[Mapping[str, object]],
    container_stats: Mapping[str, object],
    piggyback_name_method: PiggybackNameMethod,
    nodename: Union[str, None] = None,
    run_as_user: Union[str, None] = None,
) -> None:
    for container in containers:
        container_id = str(container.get("Id", ""))
        target_host = get_piggyback_host(
            container_id,
            get_container_name(container.get("Names")),
            piggyback_name_method,
            nodename,
        )
        if not target_host:
            continue

        write_piggyback_section(
            target_host=target_host,
            section=query_container_inspect_cli(container_id, run_as_user),
        )

        if stats := container_stats.get(container_id) or container_stats.get(container_id[:12]):
            write_piggyback_section(
                target_host=target_host,
                section=JSONSection("container_stats", json.dumps(stats)),
            )


def run_cli_queries_for_user(
    piggyback_name_method: PiggybackNameMethod,
    run_as_user: Union[str, None] = None,
) -> None:
    containers_section = query_containers_cli(run_as_user)
    engine_section = query_engine_cli(run_as_user)

    write_sections(
        [
            containers_section,
            query_disk_usage_cli(run_as_user),
            engine_section,
            query_pods_cli(run_as_user),
        ]
    )

    nodename = extract_nodename_from_engine(engine_section)

    raw_container_stats = query_raw_stats_cli(run_as_user)
    container_stats = (
        extract_container_stats(raw_container_stats)
        if not isinstance(raw_container_stats, Error)
        else {}
    )

    if not isinstance(containers_section, Error):
        handle_containers_stats_cli(
            containers=json.loads(containers_section.content),
            container_stats=container_stats,
            piggyback_name_method=piggyback_name_method,
            nodename=nodename,
            run_as_user=run_as_user,
        )
    else:
        write_section(containers_section)


def run_cli_queries(piggyback_name_method: PiggybackNameMethod) -> None:
    podman_users = find_podman_users_from_conmon()

    for user in podman_users:
        run_cli_queries_for_user(piggyback_name_method, user)


# =============================================================================
# Socket-based query functions
# =============================================================================


def build_url_human_readable(socket_path: str, endpoint_uri: str) -> str:
    return f"{socket_path}{endpoint_uri}"


def build_url_callable(socket_path: str, endpoint_uri: str) -> str:
    return f"{DEFAULT_SCHEME}{socket_path.replace('/', '%2F')}{endpoint_uri}"


def query_containers(session: Session, socket_path: str) -> Union[JSONSection, Error]:
    endpoint = f"/{PODMAN_API_VERSION}/libpod/containers/json"
    try:
        response = session.get(build_url_callable(socket_path, endpoint), params={"all": "true"})
        response.raise_for_status()
        output = [c for c in response.json() if not c.get("IsInfra", False)]
    except Exception as e:
        return Error(build_url_human_readable(socket_path, endpoint), str(e))
    return JSONSection("containers", json.dumps(output))


def query_disk_usage(session: Session, socket_path: str) -> Union[JSONSection, Error]:
    endpoint = f"/{PODMAN_API_VERSION}/libpod/system/df"
    try:
        response = session.get(build_url_callable(socket_path, endpoint))
        response.raise_for_status()
    except Exception as e:
        return Error(build_url_human_readable(socket_path, endpoint), str(e))
    return JSONSection("disk_usage", json.dumps(response.json()))


def query_engine(session: Session, socket_path: str) -> Union[JSONSection, Error]:
    endpoint = f"/{PODMAN_API_VERSION}/libpod/info"
    try:
        response = session.get(build_url_callable(socket_path, endpoint))
        response.raise_for_status()
    except Exception as e:
        return Error(build_url_human_readable(socket_path, endpoint), str(e))
    return JSONSection("engine", json.dumps(response.json()))


def query_pods(session: Session, socket_path: str) -> Union[JSONSection, Error]:
    endpoint = f"/{PODMAN_API_VERSION}/libpod/pods/json"
    try:
        response = session.get(build_url_callable(socket_path, endpoint), params={"all": "true"})
        response.raise_for_status()
    except Exception as e:
        return Error(build_url_human_readable(socket_path, endpoint), str(e))
    return JSONSection("pods", json.dumps(response.json()))


def query_container_inspect(
    session: Session,
    socket_path: str,
    container_id: str,
) -> Union[JSONSection, Error]:
    endpoint = f"/{PODMAN_API_VERSION}/libpod/containers/{container_id}/json"
    try:
        response = session.get(build_url_callable(socket_path, endpoint))
        response.raise_for_status()
        section: Union[JSONSection, Error] = JSONSection(
            "container_inspect", json.dumps(response.json())
        )
    except Exception as e:
        section = Error(build_url_human_readable(socket_path, endpoint), str(e))
    return section


def query_raw_stats(session: Session, socket_path: str) -> Union[Mapping[str, object], Error]:
    endpoint = f"/{PODMAN_API_VERSION}/libpod/containers/stats"
    try:
        response = session.get(
            build_url_callable(socket_path, endpoint),
            params={"stream": "false", "all": "true"},
        )
        response.raise_for_status()
        result: Mapping[str, object] = response.json()
        return result
    except Exception as e:
        return Error(build_url_human_readable(socket_path, endpoint), str(e))


def extract_container_stats(stats_data: Mapping[str, object]) -> Mapping[str, object]:
    if not isinstance(stats := stats_data.get("Stats", []), list):
        return {}

    result = {}
    for stat in stats:
        container_id = stat.get("ContainerID") or stat.get("id")
        if container_id:
            result[container_id] = stat

    return result


def get_container_name(names: object) -> str:
    if isinstance(names, list) and names:
        return str(names[0]).lstrip("/")
    return "unnamed"


def extract_nodename_from_engine(engine_section: Union[JSONSection, Error]) -> Union[str, None]:
    if isinstance(engine_section, Error):
        return None
    try:
        data = json.loads(engine_section.content)
        return str(data["host"]["hostname"])
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def get_piggyback_host(
    container_id: str,
    container_name: str,
    piggyback_name_method: PiggybackNameMethod,
    nodename: Union[str, None] = None,
) -> Union[str, None]:
    if not container_id:
        return None

    if piggyback_name_method is PiggybackNameMethod.NODENAME_NAME:
        if nodename is None:
            nodename = os.uname()[1]
        return f"{nodename}_{container_name}"

    if piggyback_name_method is PiggybackNameMethod.NAME_ID:
        return f"{container_name}_{container_id[:12]}"

    # Default: PiggybackNameMethod.NAME (fallback when no specific method matches)
    return container_name


def should_use_cli(config: Union[PodmanConfig, None]) -> bool:
    socket_paths = get_socket_paths(config)
    for socket_path in socket_paths:
        if os.path.exists(socket_path):
            return False

    if which("podman"):
        return True

    return False


def handle_containers_stats(
    containers: Sequence[Mapping[str, object]],
    container_stats: Mapping[str, object],
    socket_path: str,
    session: Session,
    piggyback_name_method: PiggybackNameMethod = PiggybackNameMethod.NODENAME_NAME,
    nodename: Union[str, None] = None,
) -> None:
    for container in containers:
        container_id = str(container.get("Id", ""))
        target_host = get_piggyback_host(
            container_id,
            get_container_name(container.get("Names")),
            piggyback_name_method,
            nodename,
        )
        if not target_host or not container_id:
            continue

        write_piggyback_section(
            target_host=target_host,
            section=query_container_inspect(session, socket_path, container_id),
        )

        if stats := container_stats.get(container_id):
            write_piggyback_section(
                target_host=target_host,
                section=JSONSection("container_stats", json.dumps(stats)),
            )


def _get_piggyback_name_method(config: Union[PodmanConfig, None]) -> PiggybackNameMethod:
    if config is None:
        return PiggybackNameMethod.NODENAME_NAME
    return config["piggyback_name_method"]


def main() -> None:
    config = load_cfg()
    piggyback_name_method = _get_piggyback_name_method(config)

    # Write empty errors section to indicate successful start
    write_serialized_section("errors", json.dumps({}))

    if should_use_cli(config):
        run_cli_queries(piggyback_name_method)
        return

    # Socket-based queries
    socket_paths = get_socket_paths(config)

    for socket_path_str in socket_paths:
        socket_path = Path(socket_path_str)
        with make_unixsocket_session(
            socket_path=socket_path,
            target_base_url=DEFAULT_SCHEME,
        ) as session:
            containers_section = query_containers(session, socket_path_str)
            engine_section = query_engine(session, socket_path_str)

            write_sections(
                [
                    containers_section,
                    query_disk_usage(session, socket_path_str),
                    engine_section,
                    query_pods(session, socket_path_str),
                ]
            )

            nodename = extract_nodename_from_engine(engine_section)

            raw_container_stats = query_raw_stats(session, socket_path_str)
            container_stats = (
                extract_container_stats(raw_container_stats)
                if not isinstance(raw_container_stats, Error)
                else {}
            )

            if not isinstance(containers_section, Error):
                handle_containers_stats(
                    containers=json.loads(containers_section.content),
                    container_stats=container_stats,
                    socket_path=socket_path_str,
                    session=session,
                    piggyback_name_method=piggyback_name_method,
                    nodename=nodename,
                )
            else:
                write_section(containers_section)


if __name__ == "__main__":
    main()
