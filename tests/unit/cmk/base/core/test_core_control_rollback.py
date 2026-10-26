#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""What happens to the core's objects file when an activation fails.

The engine replaces the objects file in place -- it lives outside the versioned
`helper_config/<serial>` directory, so advancing the `latest` link rolls nothing back.
The activation must put the previous one back, whichever step failed.
"""

import socket
import subprocess
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import override

import pytest

import cmk.utils.paths
from cmk.base.community_app import make_app
from cmk.base.config import ConfigCache, CoreObjectsConfig, make_host_tags, make_hosts_config
from cmk.base.configlib.loaded_config import BaseConfig
from cmk.base.core import interface as core_interface
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.core_client import CoreAction, NagiosClient
from cmk.monitoring_config.internal import IntermediateMonitoringConfig, MonitoringConfigBuilder
from cmk.utils import ip_lookup
from tests.testlib.unit.empty_config import EMPTY_CONFIG

_PREVIOUS = "# the configuration that was active before\n"

# exits non-zero, so `nagios -vp` rejects whatever it is handed
_REJECTING_BINARY = Path("/bin/false")


class _NoopRunNagiosClient(NagiosClient):
    """A client that will not actually reload the core.

    Only `run()` goes through `_run_command`; `config_is_valid()` shells out on its own,
    so validation stays real.
    """

    @override
    def _run_command(self, *args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args=(), returncode=0, stdout=b"")


@pytest.fixture(name="site_files")
def fixture_site_files() -> None:
    """The files an activation finds in a real site.

    No cleanup: the autouse `cleanup_after_test` fixture wipes the fake site's OMD_ROOT.
    """
    cmk.utils.paths.trusted_ca_file.parent.mkdir(parents=True, exist_ok=True)
    cmk.utils.paths.trusted_ca_file.touch()
    cmk.utils.paths.nagios_objects_file.parent.mkdir(parents=True, exist_ok=True)
    cmk.utils.paths.nagios_objects_file.write_text(_PREVIOUS)
    # where a rejected config is parked for analysis; always present in a site
    cmk.utils.paths.tmp_dir.mkdir(parents=True, exist_ok=True)


def _activate(
    loaded_config: BaseConfig,
    *,
    nagios_binary: Path | None = None,
    extra_builders: Sequence[MonitoringConfigBuilder] = (),
) -> None:
    """Drive a full activation with dummies for everything that is not under test.

    `nagios_binary` is what the validation will run; the default never exists in the fake
    site, so `config_is_valid` short-circuits and the config is accepted.

    `extra_builders` go behind the ones an activation normally runs, so that a test can
    say what happens when something fails *after* the core has written.
    """
    app = make_app()
    hosts_config = make_hosts_config(loaded_config)
    config_cache = ConfigCache(
        loaded_config,
        hosts_config,
        make_host_tags(loaded_config, hosts_config),
        autochecks_dir=cmk.utils.paths.autochecks_dir,
        discovered_host_labels_dir=cmk.utils.paths.discovered_host_labels_dir,
        builtin_host_labels_file=cmk.utils.paths.builtin_host_labels_file,
        debug=False,
    )
    core, _real_client = app.create_core(loaded_config)
    core_client = _NoopRunNagiosClient(
        objects_file=cmk.utils.paths.nagios_objects_file,
        init_script=cmk.utils.paths.nagios_startscript,
        config_file=cmk.utils.paths.nagios_config_file,
        binary_file=nagios_binary or cmk.utils.paths.nagios_binary,
        cleanup_base=cmk.utils.paths.omd_root,
    )
    core_interface.build_and_activate_monitoring_config(
        action=CoreAction.RELOAD,
        config_cache=config_cache,
        core_objects_config=CoreObjectsConfig(
            loaded_config, config_cache.ruleset_matcher, config_cache.label_manager
        ),
        hosts_config=hosts_config,
        host_tags=make_host_tags(loaded_config, hosts_config),
        final_service_name_config=lambda *a: "",  # noqa: ARG005
        passive_service_name_config=lambda *a: "",  # noqa: ARG005
        enforced_services_table=lambda *a: {},  # noqa: ARG005
        get_ip_stack_config=lambda *a: ip_lookup.IPStackConfig.IPv4,  # noqa: ARG005
        default_address_family=lambda *a: socket.AddressFamily.AF_INET,  # noqa: ARG005
        ip_address_of=ip_lookup.ConfiguredIPLookup(
            lambda *a: HostAddress("127.0.0.1"),  # noqa: ARG005
            allow_empty=(),
            error_handler=ip_lookup.CollectFailedHosts(),
        ),
        ip_address_of_mgmt=lambda *a: None,  # noqa: ARG005
        core_client=core_client,
        plugins=AgentBasedPlugins.empty(),
        config_builders=(*core_interface.config_builders(core), *extra_builders),
        hosts_to_update=None,
        service_depends_on=lambda *a: [],  # noqa: ARG005
        locking_mode=None,
        duplicates=[],
        notify_relay=lambda *a, **kw: None,  # noqa: ARG005
        licensing_handler_factory=app.licensing_handler_factory,
        edition=app.edition,
        loaded_config=loaded_config,
        make_fetcher_trigger=app.make_fetcher_trigger,
    )


def _fail(_intermediate_config: IntermediateMonitoringConfig) -> None:
    raise RuntimeError("the last builder failed")


_FAILING_BUILDER = MonitoringConfigBuilder(name="failing", build=_fail)


@pytest.mark.usefixtures("site_files")
def test_nagios_activation_replaces_the_objects_file() -> None:
    _activate(replace(EMPTY_CONFIG, monitoring_core="nagios"))

    assert cmk.utils.paths.nagios_objects_file.read_text() != _PREVIOUS


@pytest.mark.usefixtures("site_files")
def test_nagios_objects_file_is_restored_when_a_later_builder_fails() -> None:
    with pytest.raises(RuntimeError, match="the last builder failed"):
        _activate(
            replace(EMPTY_CONFIG, monitoring_core="nagios"),
            extra_builders=(_FAILING_BUILDER,),
        )

    assert cmk.utils.paths.nagios_objects_file.read_text() == _PREVIOUS


@pytest.mark.usefixtures("site_files")
def test_nagios_objects_file_is_restored_when_the_core_rejects_the_config() -> None:
    # `config_is_valid` only runs the binary if there is a config file to validate
    cmk.utils.paths.nagios_config_file.parent.mkdir(parents=True, exist_ok=True)
    cmk.utils.paths.nagios_config_file.touch()

    with pytest.raises(MKGeneralException, match="Rolling back"):
        _activate(replace(EMPTY_CONFIG, monitoring_core="nagios"), nagios_binary=_REJECTING_BINARY)

    assert cmk.utils.paths.nagios_objects_file.read_text() == _PREVIOUS
    assert (cmk.utils.paths.tmp_dir / "check_mk_objects.cfg.broken").exists()
