#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import shutil
import tarfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from tests.testlib.site import (
    get_site_factory,
    Site,
    tracing_config_from_env,
)

from cmk.ccc.hostaddress import HostName

from .lib import (
    create_special_agent_host,
    create_special_agent_rule,
    Hosts,
    MOCKUP_DUMPS_DIR,
    run_mockup_server,
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def redfish_hosts(
    site: Site, dell_server_port: int, hpe_server_port: int, raritan_server_port: int
) -> Iterator[Hosts]:
    hosts = Hosts(
        dell_ok=HostName("blackfin-snapper"),
        hpe_ok=HostName("queen-snapper"),
        raritan_ok=HostName("sockeye-salmon"),
    )

    created = {
        create_special_agent_host(site, hosts.dell_ok): create_special_agent_rule(
            site, hosts.dell_ok, "redfish", port=dell_server_port
        ),
        create_special_agent_host(site, hosts.hpe_ok): create_special_agent_rule(
            site, hosts.hpe_ok, "redfish", port=hpe_server_port
        ),
        create_special_agent_host(site, hosts.raritan_ok): create_special_agent_rule(
            site, hosts.raritan_ok, "redfish_power", port=raritan_server_port
        ),
    }

    for host_name in created:
        site.openapi.service_discovery.run_discovery_and_wait_for_completion(host_name)

    site.openapi.changes.activate_and_wait_for_completion()
    for host_name in created:
        site.schedule_check(host_name, "Check_MK")
    try:
        yield hosts
    finally:
        for host_name, rule_id in created.items():
            site.openapi.hosts.delete(host_name)
            site.openapi.rules.delete(rule_id)
        site.openapi.changes.activate_and_wait_for_completion()


@pytest.fixture(scope="session", name="dell_server_port")
def _run_mockup_dell_server(tmp_dump_dir: Path) -> Iterator[int]:
    yield from _make_mockup_server(tmp_dump_dir, "dell", 8080)


@pytest.fixture(scope="session", name="hpe_server_port")
def _run_mockup_hpe_server(tmp_dump_dir: Path) -> Iterator[int]:
    yield from _make_mockup_server(tmp_dump_dir, "hpe", 8081)


@pytest.fixture(scope="session", name="raritan_server_port")
def _run_mockup_raritan_server(tmp_dump_dir: Path) -> Iterator[int]:
    yield from _make_mockup_server(tmp_dump_dir, "raritan_pdu", 8082)


@pytest.fixture(scope="session", name="tmp_dump_dir")
def _make_dump_dir(tmpdir_factory: pytest.TempdirFactory) -> Iterator[Path]:
    dump_dir = Path(tmpdir_factory.mktemp("dumps"))
    try:
        yield dump_dir
    finally:
        shutil.rmtree(dump_dir)


def _make_mockup_server(tmp_dump_dir: Path, dataset: str, port: int) -> Iterator[int]:
    with _unpack_dump(dataset, tmp_dump_dir) as dump_path:
        with run_mockup_server(dataset_path=dump_path, port=port) as server:
            try:
                yield port
            finally:
                server.terminate()
                if server.wait():
                    assert server.stderr is not None
                    logger.error(server.stderr.read())


@contextmanager
def _unpack_dump(dataset: str, tmpdir: Path) -> Iterator[Path]:
    dump = MOCKUP_DUMPS_DIR / f"{dataset}.tgz"
    target = tmpdir / dataset

    with tarfile.open(dump, "r:gz") as tar:
        tar.extractall(path=tmpdir)

    try:
        yield target
    finally:
        shutil.rmtree(target)


@pytest.fixture(scope="session", autouse=True)
def instrument_requests() -> None:
    RequestsInstrumentor().instrument()


@pytest.fixture(scope="session", name="site")
def _make_site(request: pytest.FixtureRequest) -> Iterator[Site]:
    with get_site_factory(prefix="int_").get_test_site_ctx(
        "redfish",
        description=request.node.name,
        auto_restart_httpd=True,
        tracing_config=tracing_config_from_env(os.environ),
    ) as this_site:
        yield this_site
