#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import socket
import ssl
import subprocess
import sys
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import final, Self

import httpx
from tenacity import RetryError, Retrying, stop_after_delay, wait_fixed

from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.testlib.agent_receiver.builder import AgentReceiverSite


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@final
class AgentReceiverRunner:
    def __init__(self, site: AgentReceiverSite) -> None:
        self._site = site
        self._port = _find_free_port()
        self._process: subprocess.Popen[bytes] | None = None

    @property
    def site(self) -> AgentReceiverSite:
        return self._site

    @property
    def base_url(self) -> str:
        return f"https://127.0.0.1:{self._port}"

    @property
    def _log_file(self) -> Path:
        return self._site.config.log_path.parent / "runner.log"

    def _default_ssl_context(self) -> ssl.SSLContext:
        return ssl.create_default_context(cafile=str(self._site.config.agent_cert_store_path))

    def http_client(self) -> httpx.Client:
        """Return an httpx.Client that trusts the site's CA bundle."""
        return httpx.Client(base_url=self.base_url, verify=self._default_ssl_context())

    @contextmanager
    def mtls_client(self, cert: CertificateWithPrivateKey) -> Generator[httpx.Client]:
        """Return an httpx.Client performing mTLS with the given certificate and key."""
        ctx = self._default_ssl_context()
        with (
            tempfile.NamedTemporaryFile(suffix=".pem") as cert_file,
            tempfile.NamedTemporaryFile(suffix=".pem") as key_file,
        ):
            cert_file.write(cert.certificate.dump_pem().bytes)
            cert_file.flush()
            key_file.write(cert.private_key.dump_pem(None).bytes)
            key_file.flush()
            ctx.load_cert_chain(certfile=cert_file.name, keyfile=key_file.name)
            with httpx.Client(base_url=self.base_url, verify=ctx) as client:
                yield client

    def start(self) -> None:
        if self._process is not None:
            raise RuntimeError("already running")
        config = self._site.config
        self._process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "gunicorn",
                "--error-logfile",
                str(self._log_file),
                "--log-level",
                "debug",
                "--keyfile",
                str(config.site_cert_path),
                "--certfile",
                str(config.site_cert_path),
                "--ca-certs",
                str(config.agent_cert_store_path),
                "--cert-reqs",
                "1",
                "--workers",
                "1",
                "-b",
                f"127.0.0.1:{self._port}",
                "-k",
                "cmk.agent_receiver.worker.ClientCertWorker",
                "--no-control-socket",
                "cmk.agent_receiver.main:main_app()",
            ],
            env=os.environ | self._site.env,
        )

    def stop(self) -> None:
        if self._process is not None:
            if self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait()
            self._process = None

    @contextmanager
    def running(self) -> Generator[Self]:
        self.start()
        try:
            yield self
        finally:
            self.stop()
            self._print_logs()

    def _print_logs(self) -> None:
        print("\n==== agent-receiver runner logs ====")
        if self._log_file.exists():
            content = self._log_file.read_text()
            print(content if content.strip() else "(empty)")
        else:
            print(f"No log file at {self._log_file}")
        print("==== end of agent-receiver runner logs ====\n")

    def wait_for_running(self, timeout: float = 120.0) -> None:
        if self._process is None:
            raise RuntimeError("not started")
        # Use a short per-connection timeout: the uvicorn worker may take a few seconds
        # to load the app. During that time the master binds the port and queues TCP
        # connections, but the SSL handshake hangs until the worker is ready. A 2s
        # connect timeout lets us retry quickly instead of blocking the full budget.
        last_exc: BaseException | None = None
        with httpx.Client(
            verify=self._default_ssl_context(), timeout=httpx.Timeout(5.0, connect=2.0)
        ) as client:
            try:
                for attempt in Retrying(
                    stop=stop_after_delay(timeout),
                    wait=wait_fixed(0.1),
                    reraise=False,
                ):
                    with attempt:
                        try:
                            resp = client.get(
                                f"{self.base_url}/{self._site.config.site_name}"
                                "/agent-receiver/openapi.json"
                            )
                            assert resp.status_code == 200
                        except Exception as exc:
                            last_exc = exc
                            raise
            except RetryError:
                returncode = self._process.poll()
                logs = self._log_file.read_text() if self._log_file.exists() else "(no log file)"
                raise RuntimeError(
                    f"Agent receiver did not start within {timeout}s "
                    f"(returncode={returncode}).\n"
                    f"Last error: {last_exc!r}\n"
                    f"Logs:\n{logs}"
                ) from None
