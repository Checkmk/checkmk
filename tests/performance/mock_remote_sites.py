#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Mock remote sites for distributed performance tests (CMK-35259).

Each mock remote site emulates exactly the surface a central site talks to
during "Activate Changes" in a distributed setup, so the central site performs
its full per-site activation work (snapshot computation, config sync upload,
broker definition and piggyback hub config computation) against a scalable
number of remote sites without the resource cost of real OMD sites:

* ``login.py``: site login, returning a login secret
  (see ``cmk.gui.watolib.automations.do_site_login``).
* ``automation.py`` commands (see ``cmk.gui.watolib.activate_changes`` and
  ``cmk.gui.watolib.broker_certificates``):
  - ``get-config-sync-state``: stateful; computed from the files previously
    received via config sync, using the same stat/sha256 file info scheme as
    ``_get_config_sync_file_info``.
  - ``receive-config-sync``: unpacks the sync archive into the mock site's
    state directory and applies deletions, like a real remote.
  - ``activate-changes``: returns no warnings; optionally sleeps to emulate
    remote activation time.
  - ``create-broker-certs`` / ``store-broker-certs``: serves a real CSR and
    accepts the signed certificates, like a real remote message broker setup.
* A minimal livestatus TCP endpoint answering ``GET status`` queries so the
  site appears "online" with a compatible version.

Intentionally NOT emulated: the actual remote-site activation work (cmk -U,
core reload) and a running message broker. Wall clock measured on the central
site therefore excludes remote-side costs by design.
"""

import ast
import hashlib
import io
import json
import logging
import os
import shutil
import socketserver
import tarfile
import threading
import time
import urllib.parse
from collections.abc import Iterator
from contextlib import contextmanager
from email.parser import BytesParser
from email.policy import HTTP as HTTP_POLICY
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import override

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from tests.testlib.version import CMKVersion

logger = logging.getLogger(__name__)

_LOGIN_SECRET = "mock-remote-site-login-secret"


def _create_csr_pem(site_id: str) -> bytes:
    """Create a real private key + CSR for the mock site's message broker."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(
            x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, site_id),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, f"checkmk-site-{site_id}"),
                ]
            )
        )
        .sign(private_key, hashes.SHA256())
    )
    return csr.public_bytes(serialization.Encoding.PEM)


class _MockSiteState:
    """Per-site state: synced files and config generation."""

    def __init__(self, site_id: str, state_dir: Path) -> None:
        self.site_id = site_id
        self.state_dir = state_dir
        self.config_generation = 0
        self.lock = threading.Lock()
        state_dir.mkdir(parents=True, exist_ok=True)

    def file_infos(self) -> dict[str, tuple[int, int, str | None, str | None]]:
        """Mirror of cmk.gui.watolib.activate_changes._get_config_sync_file_info."""
        infos: dict[str, tuple[int, int, str | None, str | None]] = {}
        for root, _dirs, files in os.walk(self.state_dir):
            for file_name in files:
                path = Path(root) / file_name
                rel_path = str(path.relative_to(self.state_dir))
                stat = os.lstat(path)
                is_symlink = path.is_symlink()
                infos[rel_path] = (
                    stat.st_mode,
                    stat.st_size,
                    os.readlink(path) if is_symlink else None,
                    hashlib.sha256(path.read_bytes()).hexdigest() if not is_symlink else None,
                )
        return infos

    def apply_sync(self, sync_archive: bytes, to_delete: list[str]) -> None:
        with self.lock:
            for rel_path in to_delete:
                target = self.state_dir / rel_path
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    target.unlink(missing_ok=True)
            with tarfile.open(fileobj=io.BytesIO(sync_archive), mode="r:") as tar:
                tar.extractall(path=self.state_dir, filter="data")
            self.config_generation += 1


class _AutomationHTTPHandler(BaseHTTPRequestHandler):
    """Serves login.py and automation.py for all mock sites (path-routed)."""

    server: _MockHTTPServer  # type: ignore[mutable-override]
    protocol_version = "HTTP/1.1"

    @override
    def log_message(self, format: str, *args: object) -> None:
        logger.debug("mock-http: %s", format % args)

    def _respond(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # Compatibility headers checked by the central site
        self.send_header("x-checkmk-version", self.server.cmk_version)
        self.send_header("x-checkmk-edition", self.server.cmk_edition)
        self.end_headers()
        self.wfile.write(body)

    def _read_request_params(self) -> dict[str, object]:
        """Return POST parameters (urlencoded or multipart/form-data)."""
        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        content_type = self.headers.get("Content-Type", "")
        params: dict[str, object] = {}
        if content_type.startswith("multipart/form-data"):
            message = BytesParser(policy=HTTP_POLICY).parsebytes(
                b"Content-Type: " + content_type.encode() + b"\r\n\r\n" + raw_body
            )
            for part in message.iter_parts():
                name = part.get_param("name", header="content-disposition")
                if not isinstance(name, str):
                    continue
                payload = part.get_payload(decode=True)
                if not isinstance(payload, bytes):
                    continue
                params[name] = payload if part.get_filename() else payload.decode("utf-8")
        else:
            for key, values in urllib.parse.parse_qs(
                raw_body.decode("utf-8"), keep_blank_values=True
            ).items():
                params[key] = values[0]
        return params

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
        parts = parsed.path.strip("/").split("/")
        # expected paths: <site_id>/check_mk/login.py | <site_id>/check_mk/automation.py
        if len(parts) < 3 or parts[1] != "check_mk":
            self._respond(b"Unknown path", status=404)
            return
        site_id, page = parts[0], parts[2]
        state = self.server.sites.get(site_id)
        if state is None:
            self._respond(b"Unknown site", status=404)
            return

        if page == "login.py":
            self._respond(
                repr(
                    {
                        "version": self.server.cmk_version,
                        "edition_short": self.server.cmk_edition,
                        "login_secret": _LOGIN_SECRET,
                    }
                ).encode()
            )
            return

        if page != "automation.py":
            self._respond(b"Unknown page", status=404)
            return

        params = self._read_request_params()
        if params.get("secret") != _LOGIN_SECRET:
            self._respond(b"Invalid automation secret.", status=401)
            return

        command = query.get("command", "")
        logger.debug("mock site %s: automation command %s", site_id, command)
        try:
            self._respond(self._execute(state, command, params).encode())
        except Exception:
            logger.exception("mock site %s: command %s failed", site_id, command)
            self._respond(b"Mock remote site error", status=500)

    def _execute(self, state: _MockSiteState, command: str, params: dict[str, object]) -> str:
        if command == "get-config-sync-state":
            with state.lock:
                return repr((state.file_infos(), state.config_generation))

        if command == "receive-config-sync":
            sync_archive = params["sync_archive"]
            assert isinstance(sync_archive, bytes)
            to_delete = ast.literal_eval(str(params["to_delete"]))
            state.apply_sync(sync_archive, to_delete)
            return repr(True)

        if command == "activate-changes":
            if self.server.activate_delay:
                time.sleep(self.server.activate_delay)
            # domain name -> list of warnings
            return repr({})

        if command == "create-broker-certs":
            return repr({"csr": _create_csr_pem(state.site_id)})

        if command == "store-broker-certs":
            return repr(True)

        if command == "checkmk-remote-automation-get-status":
            # Only used for OMD config change background jobs.
            return repr(
                (
                    {
                        "state": "finished",
                        "is_active": False,
                        "loginfo": {
                            "JobProgressUpdate": [],
                            "JobResult": [],
                            "JobException": [],
                        },
                    },
                    "",
                )
            )

        if command == "sync-remote-site":
            # JSON-serialized (audit_logs, site_changes) tuple, both themselves
            # JSON strings (see cmk.gui.watolib._sync_remote_sites).
            return repr(json.dumps(("[]", "[]")))

        if command == "discovered-host-label-sync":
            # see cmk.gui.watolib.host_label_sync.AutomationDiscoveredHostLabelSync
            return repr({"updated_host_labels": []})

        if command == "checkmk-automation":
            # Generic wrapper for Checkmk base automations executed on the
            # remote site. The response is the RAW serialized automation result
            # (see cmk.gui.wato.pages.automation._execute_cmk_automation), i.e.
            # repr(astuple(<result dataclass>)) for default serialization.
            inner = str(params.get("automation", ""))
            if inner == "delete-hosts":
                return "()"  # serialized DeleteHostsResult (empty dataclass)
            logger.warning(
                "mock site %s: unhandled checkmk-automation %r (params: %s)",
                state.site_id,
                inner,
                list(params),
            )
            raise NotImplementedError(f"Mock remote site: unhandled checkmk-automation {inner!r}")

        if command == "ping":
            return repr(True)

        logger.warning(
            "mock site %s: unhandled automation command %r (params: %s)",
            state.site_id,
            command,
            list(params),
        )
        raise NotImplementedError(f"Mock remote site: unhandled command {command!r}")


class _MockHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    # The central site syncs all mocked sites in parallel; the default listen
    # backlog of 5 causes connection resets at higher site counts.
    request_queue_size = 128

    def __init__(
        self,
        port: int,
        sites: dict[str, _MockSiteState],
        cmk_version: str,
        cmk_edition: str,
        activate_delay: float,
    ) -> None:
        super().__init__(("127.0.0.1", port), _AutomationHTTPHandler)
        self.sites = sites
        self.cmk_version = cmk_version
        self.cmk_edition = cmk_edition
        self.activate_delay = activate_delay


class _LivestatusHandler(socketserver.StreamRequestHandler):
    """Minimal livestatus server: answers "GET status" with canned status data.

    Every other table is reported as empty, which is what a site that monitors
    nothing would answer. Faking rows there would feed bogus values into the
    central site's cron jobs -- e.g. the BI structure fetcher expects strings
    in the services table and crashes on anything else.
    """

    server: _MockLivestatusServer  # type: ignore[mutable-override]

    @override
    def handle(self) -> None:
        while True:
            request_lines: list[str] = []
            while True:
                raw_line = self.rfile.readline()
                if not raw_line:
                    return  # connection closed
                line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                if not line:
                    break
                request_lines.append(line)
            if not request_lines:
                continue
            keep_alive = self._handle_query(request_lines)
            if not keep_alive:
                return

    def _handle_query(self, request_lines: list[str]) -> bool:
        verb, _, table = request_lines[0].partition(" ")
        table = table.strip()
        headers = {}
        for line in request_lines[1:]:
            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip().lower()] = value.strip()

        keep_alive = headers.get("keepalive", "off").lower() == "on"
        if verb == "COMMAND":
            return keep_alive
        if verb != "GET":
            return keep_alive

        columns = headers.get("columns", "").split() if headers.get("columns") else []
        values = self.server.status_values
        rows: list[list[object]] = []
        if table == "status":
            if columns:
                rows = [[values.get(c, 0) for c in columns]]
            else:
                # ColumnHeaders style response: header row + data row
                rows = [list(values.keys()), list(values.values())]

        output_format = headers.get("outputformat", "csv")
        if output_format.startswith("python"):
            body = (repr(rows) + "\n").encode()
        elif output_format == "json":
            body = (json.dumps(rows) + "\n").encode()
        elif rows:  # csv
            body = ("\n".join(";".join(str(v) for v in row) for row in rows) + "\n").encode()
        else:  # csv, no rows
            body = b""

        if headers.get("responseheader", "off").lower() == "fixed16":
            self.wfile.write(b"%3d %11d\n" % (200, len(body)))
        self.wfile.write(body)
        return keep_alive


class _MockLivestatusServer(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 32

    def __init__(self, port: int, status_values: dict[str, object]) -> None:
        super().__init__(("127.0.0.1", port), _LivestatusHandler)
        self.status_values = status_values


class MockRemoteSiteCluster:
    """A scalable cluster of mock remote sites.

    One shared HTTP server (path-routed per site) and one livestatus TCP
    server per site.
    """

    def __init__(
        self,
        count: int,
        cmk_version: CMKVersion,
        cmk_edition: str = "pro",
        state_base_dir: Path | None = None,
        http_port: int = 24080,
        livestatus_base_port: int = 24100,
        activate_delay: float = 0.0,
        site_id_prefix: str = "mock",
    ) -> None:
        self.site_ids = [f"{site_id_prefix}{i:02d}" for i in range(1, count + 1)]
        self.cmk_version = cmk_version
        self.http_port = http_port
        self._state_base_dir = state_base_dir or Path("/tmp/cmk-mock-remote-sites")
        self._livestatus_ports = {
            site_id: livestatus_base_port + i for i, site_id in enumerate(self.site_ids)
        }
        self._sites = {
            site_id: _MockSiteState(site_id, self._state_base_dir / site_id)
            for site_id in self.site_ids
        }
        self._http_server = _MockHTTPServer(
            http_port, self._sites, cmk_version.version, cmk_edition, activate_delay
        )
        status_values: dict[str, object] = {
            "livestatus_version": cmk_version.version,
            "program_version": f"Check_MK {cmk_version.version}",
            "program_start": int(time.time()),
            "num_hosts": 0,
            "num_services": 0,
            "max_long_output_size": 2000,
            "core_pid": 1,
            # The long edition name; checked for licensing compatibility when
            # the central site computes the site state (cmk/gui/sites.py).
            "edition": cmk_edition,
            "naemon": 0,
            "nagios": 0,
            "cmc": 1,
        }
        self._livestatus_servers = {
            site_id: _MockLivestatusServer(port, status_values)
            for site_id, port in self._livestatus_ports.items()
        }
        self._threads: list[threading.Thread] = []

    def start(self) -> None:
        logger.info(
            "Starting mock remote site cluster: %d sites (http port %d)",
            len(self.site_ids),
            self.http_port,
        )
        for server in [self._http_server, *self._livestatus_servers.values()]:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        logger.info("Stopping mock remote site cluster")
        for server in [self._http_server, *self._livestatus_servers.values()]:
            server.shutdown()
            server.server_close()
        for thread in self._threads:
            thread.join(timeout=5)
        self._threads.clear()
        shutil.rmtree(self._state_base_dir, ignore_errors=True)

    def site_connection_config(self, site_id: str) -> dict[str, object]:
        """REST API payload to register this mock site on the central site."""
        base_url = f"http://127.0.0.1:{self.http_port}/{site_id}/check_mk/"
        configuration_connection: dict[str, object] = {
            "enable_replication": True,
            "url_of_remote_site": base_url,
            "disable_remote_configuration": True,
            "ignore_tls_errors": True,
            "direct_login_to_web_gui_allowed": True,
            "user_sync": {"sync_with_ldap_connections": "all"},
            "replicate_event_console": True,
            "replicate_extensions": True,
            "message_broker_port": 5672,
            "is_trusted": False,
        }
        # the site management endpoint only knows authentication_connections since CMK3.0.0
        if self.cmk_version >= CMKVersion("3.0.0b1"):
            configuration_connection["authentication_connections"] = {
                "type": "all",
                "connection_types": ["ldap", "saml"],
            }
        return {
            "basic_settings": {
                "alias": f"Mock remote site {site_id}",
                "site_id": site_id,
            },
            "status_connection": {
                "connection": {
                    "socket_type": "tcp",
                    "host": "127.0.0.1",
                    "port": self._livestatus_ports[site_id],
                    "encrypted": False,
                    "verify": False,
                },
                "proxy": {
                    "use_livestatus_daemon": "direct",
                },
                "connect_timeout": 2,
                "persistent_connection": False,
                "url_prefix": f"/{site_id}/",
                "status_host": {"status_host_set": "disabled"},
                "disable_in_status_gui": False,
            },
            "configuration_connection": configuration_connection,
        }


@contextmanager
def mock_remote_site_cluster(
    count: int,
    cmk_version: CMKVersion,
    activate_delay: float = 0.0,
) -> Iterator[MockRemoteSiteCluster]:
    cluster = MockRemoteSiteCluster(count, cmk_version, activate_delay=activate_delay)
    cluster.start()
    try:
        yield cluster
    finally:
        cluster.stop()
