#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tier 2 -- side effects and local/remote dispatch.

Specified in ``packages/cmk-check-engine/docs/SERVICE_DISCOVERY_BEHAVIOUR_MATRIX.md`` §7.

Tier 1 is pure: it drives ``compute_discovery_transition`` and asserts on the returned
``DiscoveryTransition``. This tier drives the layer above -- ``perform_fix_all``,
``perform_service_discovery``, ``perform_host_label_discovery``, ``get_check_table`` and the REST
endpoint's ``_update_single_service_phase`` -- and asserts on what *leaves the process*: which
automation went to which site, which pending change was recorded, which permission was demanded,
which host flag was cleared.

**Only the automation transport is patched** (B-F1, §6.2): ``check_mk_local_automation_serialized``
and ``check_mk_remote_automation_serialized``, plus the ``do_remote_automation`` and
``sync_changes_before_remote_automation`` that ``get_check_table`` calls directly. The one
exception is an observation seam: the REST endpoint builds its own ``PendingChanges`` instead of
taking one, so the quarantine tests patch its ``make_pending_changes`` to hand back the same
recording instance every other test here receives as an argument. Patching
``local_discovery_preview`` -- as the existing ``test_services.py`` does throughout -- would erase
the local/remote branch this tier exists to pin, because that helper hard-codes
``LocalAutomationConfig()`` and is therefore never reached on the remote path.

The file has two sections. Everything above ``Quarantine`` pins behaviour that is correct today and
must stay correct through the rewrite. The quarantine section holds the §10 divergences that live
in this layer; each is one ``xfail(strict=True)`` test for the intended behaviour plus one plain
test for today's, under Tier 1b's rule: ``strict`` is spelled out because the repository default is
non-strict, the ``reason=`` names the §10 section, and both halves are deleted together when the
ticket lands.
"""

import ast
import contextlib
import dataclasses
import json
from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
from typing import override
from unittest import mock
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from werkzeug.datastructures import ETags

from cmk.automations.results import (
    AnalyzeServiceRuleMatchesResult,
    DeleteHostsResult,
    GetServicesLabelsResult,
    SerializedResult,
    ServiceDiscoveryPreviewResult,
    ServiceDiscoveryResult,
    SetAutochecksV2Result,
    UpdateHostLabelsResult,
)
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import __version__, Version
from cmk.checkengine.discovery import CheckPreviewEntry, DiscoverySettings
from cmk.checkengine.plugins import SectionName
from cmk.gui.config import Config
from cmk.gui.exceptions import MKAuthException
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.openapi.api_endpoints.service_discovery import update_service_phase
from cmk.gui.openapi.api_endpoints.service_discovery.models.request_models import (
    UpdateDiscoveryPhaseModel,
)
from cmk.gui.openapi.api_endpoints.service_discovery.update_service_phase import (
    UPDATE_PHASE_PERMISSIONS,
)
from cmk.gui.openapi.framework import ApiContext, APIVersion
from cmk.gui.quick_setup.v0_unstable.predefined._complete import _run_service_discovery
from cmk.gui.utils.roles import UserPermissionSerializableConfig
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.automations import make_automation_config
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree, Host
from cmk.gui.watolib.pending_changes import (
    Change,
    ChangeScope,
    NoopPendingChangesStore,
    PendingChanges,
)
from cmk.gui.watolib.services import (
    Discovery,
    DiscoveryAction,
    DiscoveryResult,
    DiscoveryState,
    get_check_table,
    perform_fix_all,
    perform_host_label_discovery,
    perform_service_discovery,
    ServiceDiscoveryBackgroundJob,
)
from cmk.livestatus_client import (
    LocalSocketInfo,
    SiteConfiguration,
    SiteConfigurations,
    UnixSocketDetails,
    UnixSocketInfo,
)
from cmk.ruleset_matcher.labels import HostLabel, HostLabelValueDict
from cmk.utils.automation_config import LocalAutomationConfig, RemoteAutomationConfig
from cmk.web.utils.permission_verification import BasePerm
from tests.unit.cmk.gui.watolib.discovery_matrix import (
    DESCRIPTION,
    make_entry,
    PLUGIN,
    SERVICE,
)

HOST_NAME = HostName("heute")

REMOTE_SITE = SiteId("remote")
REMOTE = RemoteAutomationConfig(
    site_id=REMOTE_SITE,
    base_url="http://remote/check_mk/",
    secret="secret",
    insecure=False,
)
LOCAL = LocalAutomationConfig()

_THIS_VERSION = Version.from_str(__version__)

_HOST_LABEL = HostLabel("cmk/check_mk_server", "yes", SectionName("labels"))

_USER_PERMISSION_CONFIG = UserPermissionSerializableConfig({}, {}, [])


# --------------------------------------------------------------------------------------------
# Scaffolding
# --------------------------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AutomationCall:
    """One automation that left the process.

    ``site`` is ``None`` for the local transport and the remote site's id otherwise -- which is
    exactly the distinction T2.2 is about, and the reason this records the transport rather than
    the ``automation_config`` object.
    """

    command: str
    site: SiteId | None
    args: tuple[str, ...]


class Transport:
    """Records the automations issued, and answers them with canned results.

    Patched in at ``check_mk_local_automation_serialized`` /
    ``check_mk_remote_automation_serialized``, i.e. *below* the local/remote branch in
    ``_automation_serialized`` and below every ``cmk.gui.watolib.check_mk_automations`` helper, so
    that no test has to mock a helper that hard-codes its own automation config.
    """

    def __init__(self) -> None:
        self.calls: list[AutomationCall] = []
        self.synced_sites: list[SiteId] = []
        self.remote_jobs: list[tuple[SiteId, str, tuple[tuple[str, str], ...]]] = []
        self.preview = preview_result([])
        self.remote_check_table = discovery_result([])

    @property
    def commands(self) -> list[str]:
        return [c.command for c in self.calls]

    def sites_for(self, command: str) -> list[SiteId | None]:
        return [c.site for c in self.calls if c.command == command]

    def args_for(self, command: str) -> list[tuple[str, ...]]:
        return [c.args for c in self.calls if c.command == command]

    def _answer(self, command: str, args: Sequence[str]) -> SerializedResult:
        match command:
            case "service-discovery-preview":
                return self.preview.serialize(_THIS_VERSION)
            case "set-autochecks-v2":
                return SetAutochecksV2Result().serialize(_THIS_VERSION)
            case "update-host-labels":
                return UpdateHostLabelsResult().serialize(_THIS_VERSION)
            case "get-services-labels":
                # args are [host_name, *service_names]; the caller indexes the result by name.
                return GetServicesLabelsResult(labels={name: {} for name in args[1:]}).serialize(
                    _THIS_VERSION
                )
            case "analyze-service-rule-matches":
                return AnalyzeServiceRuleMatchesResult(results={}).serialize(_THIS_VERSION)
            case "service-discovery":
                return ServiceDiscoveryResult(hosts={}).serialize(_THIS_VERSION)
            case _:
                raise AssertionError(f"unexpected automation {command!r}")

    def local(
        self, *, command: str, args: Sequence[str] | None = None, **_kw: object
    ) -> tuple[Sequence[str], SerializedResult]:
        self.calls.append(AutomationCall(str(command), None, tuple(args or ())))
        return ["cmk", "--automation", str(command)], self._answer(str(command), args or ())

    def remote(
        self,
        *,
        automation_config: RemoteAutomationConfig,
        command: str,
        args: Sequence[str] | None = None,
        **_kw: object,
    ) -> SerializedResult:
        self.calls.append(
            AutomationCall(str(command), automation_config.site_id, tuple(args or ()))
        )
        return self._answer(str(command), args or ())

    def do_remote_automation(
        self,
        automation_config: RemoteAutomationConfig,
        command: str,
        vars_: Sequence[tuple[str, str]],
        debug: bool = False,
        **_kw: object,
    ) -> object:
        self.remote_jobs.append(
            (automation_config.site_id, command, tuple((k, v) for k, v in vars_))
        )
        return self.remote_check_table.serialize(_THIS_VERSION)

    def sync(self, site_id: SiteId, debug: bool) -> None:
        self.synced_sites.append(site_id)


@pytest.fixture(name="transport")
def fixture_transport(mocker: MockerFixture) -> Transport:
    transport = Transport()
    mocker.patch(
        "cmk.gui.watolib.check_mk_automations.check_mk_local_automation_serialized",
        side_effect=transport.local,
    )
    mocker.patch(
        "cmk.gui.watolib.check_mk_automations.check_mk_remote_automation_serialized",
        side_effect=transport.remote,
    )
    mocker.patch(
        "cmk.gui.watolib.services.do_remote_automation",
        side_effect=transport.do_remote_automation,
    )
    mocker.patch(
        "cmk.gui.watolib.services.sync_changes_before_remote_automation",
        side_effect=transport.sync,
    )
    return transport


class RecordingPendingChanges(PendingChanges):
    """Records the ``(Change, ChangeScope)`` pairs as the caller asked for them.

    The recorded scope is the one *requested*, not the one resolved against the configured
    activation sites: the contract T2.3 and T2.7 pin is which sites the discovery code says a
    change belongs to, which is independent of how a particular test site list resolves it.
    """

    def __init__(self) -> None:
        super().__init__(
            activation_sites=SiteConfigurations({}),
            local_site=SiteId("NO_SITE"),
            acting_user=None,
            store=NoopPendingChangesStore(),
            hooks=(make_audit_log_change_hook(use_git=False),),
        )
        self.recorded: list[tuple[Change, ChangeScope]] = []

    @override
    def add(self, request: Change, scope: ChangeScope) -> None:
        self.recorded.append((request, scope))
        super().add(request, scope)

    def actions(self) -> list[str]:
        return [change.action_name for change, _scope in self.recorded]

    def only(self, action_name: str) -> tuple[Change, ChangeScope]:
        matching = [entry for entry in self.recorded if entry[0].action_name == action_name]
        assert len(matching) == 1, f"expected one {action_name!r} change, got {self.actions()}"
        return matching[0]


@pytest.fixture(name="pending_changes")
def fixture_pending_changes() -> RecordingPendingChanges:
    return RecordingPendingChanges()


@pytest.fixture(name="demanded_permissions")
def fixture_demanded_permissions(mocker: MockerFixture) -> list[str]:
    """Every permission name the code under test demanded, in order.

    Recorded by wrapping ``LoggedInUser.need_permission`` rather than by denying a permission and
    catching the exception: the tests here are logged in as admin, so the *demand* is observable
    without building a role for every case. "Never demanded" is what an authorization gap looks
    like from the inside (§10.4).
    """
    demanded: list[str] = []
    original = LoggedInUser.need_permission

    def record(self: LoggedInUser, permission: str | BasePerm) -> None:
        if isinstance(permission, str):
            demanded.append(permission)
        original(self, permission)

    mocker.patch.object(LoggedInUser, "need_permission", record)
    return demanded


def site_configuration(site_id: SiteId, *, remote_url: str | None = None) -> SiteConfiguration:
    """A minimal valid entry for the configured-sites table: local unless ``remote_url`` is given.

    Two places need one: the folder tree resolves a host's site when it writes or deletes the host,
    and the REST endpoint derives its automation config from it. ``socket`` and ``replication`` are
    what ``make_automation_config`` reads to decide local from remote, so a remote entry gets a
    non-local socket rather than only a different id.
    """
    socket: UnixSocketInfo | LocalSocketInfo = (
        ("unix", UnixSocketDetails(path=f"/omd/sites/{site_id}/tmp/run/live"))
        if remote_url
        else ("local", None)
    )
    config = SiteConfiguration(
        alias=str(site_id),
        disable_wato=False,
        disabled=False,
        id=site_id,
        insecure=False,
        is_trusted=True,
        message_broker_port=5672,
        multisiteurl=remote_url or "",
        persist=False,
        proxy=None,
        replicate_ec=False,
        replicate_mkps=False,
        replication="slave" if remote_url else None,
        socket=socket,
        status_host=None,
        timeout=5,
        url_prefix=f"/{site_id}/",
        user_login=True,
    )
    if remote_url:
        config["secret"] = REMOTE.secret
    return config


@contextlib.contextmanager
def _host_in_the_root_folder(attributes: HostAttributes) -> Iterator[Host]:
    root_folder = folder_tree().root_folder()
    root_folder.create_hosts(
        [(HOST_NAME, attributes, None)],
        pprint_value=False,
        pending_changes=RecordingPendingChanges(),
        acting_user=user,
    )
    host = root_folder.host(HOST_NAME)
    assert host is not None
    try:
        yield host
    finally:
        root_folder.delete_hosts(
            [HOST_NAME],
            automation=lambda *args, **kwargs: DeleteHostsResult(),
            pprint_value=False,
            debug=False,
            pending_changes=RecordingPendingChanges(),
            acting_user=user,
        )


@pytest.fixture(name="sample_host")
def fixture_sample_host(
    request_context: None,
    with_admin_login: UserId,
) -> Generator[Host]:
    """A host on the site this process runs on, so ``LOCAL`` is its transport."""
    with _host_in_the_root_folder(HostAttributes()) as host:
        # The site is inherited, not set; the assertion is what makes `remote_host` a contrast
        # rather than a second spelling of the same thing.
        assert host.site_id() != REMOTE_SITE
        yield host


@pytest.fixture(name="remote_site")
def fixture_remote_site(request_context: None) -> Generator[None]:
    """Adds ``REMOTE_SITE`` to the sites the folder tree knows about.

    The tree resolves a host's site every time it writes or deletes that host, against a snapshot
    of the site table taken when it was first built -- so a host on a site the tree has never heard
    of cannot even be created. The entry is built to yield exactly the module-level ``REMOTE``,
    asserted here, so that "the host's site" and "the automation config the test passes" cannot
    drift apart.
    """
    tree = folder_tree()
    original = tree.config
    tree.config = dataclasses.replace(
        original,
        sites=SiteConfigurations(
            {
                **original.sites,
                REMOTE_SITE: site_configuration(REMOTE_SITE, remote_url=REMOTE.base_url),
            }
        ),
    )
    assert make_automation_config(tree.config.sites[REMOTE_SITE]) == REMOTE
    try:
        yield
    finally:
        tree.config = original


@pytest.fixture(name="remote_host")
def fixture_remote_host(
    remote_site: None,
    with_admin_login: UserId,
) -> Generator[Host]:
    """A host that really lives on ``REMOTE_SITE`` -- every ``REMOTE`` parametrization uses this.

    With a host whose ``site_id()`` is the local one, "the change is scoped to the host's site" and
    "to the central site" are the same assertion, and both halves of a local/remote parametrization
    state the identical thing. Passing ``REMOTE`` for a host that is local would also make the
    pre-sync target -- ``sync_changes_before_remote_automation(host.site_id())``, not the
    automation config's site -- indistinguishable from the local site.
    """
    with _host_in_the_root_folder(HostAttributes(site=REMOTE_SITE)) as host:
        assert host.site_id() == REMOTE_SITE
        yield host


def entry(check_source: str) -> CheckPreviewEntry:
    """A preview entry for this host, reusing Tier 1's builder so both tiers agree on the shape."""
    return make_entry(check_source, found_on_nodes=[HOST_NAME])


def preview_result(
    entries: Sequence[CheckPreviewEntry],
    *,
    discovered_labels: Sequence[HostLabel] = (),
) -> ServiceDiscoveryPreviewResult:
    """A preview result for this host.

    ``discovered_labels`` becomes this host's entry in ``labels_by_host``, which is the field the
    label update reads -- not ``host_labels``, which the discovery code never writes from.
    """
    return ServiceDiscoveryPreviewResult(
        output="",
        check_table=list(entries),
        nodes_check_table={},
        host_labels={},
        new_labels={},
        vanished_labels={},
        changed_labels={},
        labels_by_host={HOST_NAME: list(discovered_labels)} if discovered_labels else {},
        source_results=[],
        config_warnings=[],
    )


def discovery_result(
    entries: Sequence[CheckPreviewEntry],
    *,
    discovered_labels: Sequence[HostLabel] = (),
    vanished_labels: Mapping[str, HostLabelValueDict] | None = None,
) -> DiscoveryResult:
    """A result as a caller of ``perform_*`` would have read it a moment earlier."""
    return DiscoveryResult(
        job_status={"is_active": False},
        check_table_created=1,
        check_table=list(entries),
        nodes_check_table={},
        host_labels={},
        new_labels={},
        vanished_labels=dict(vanished_labels or {}),
        changed_labels={},
        labels_by_host={HOST_NAME: list(discovered_labels)} if discovered_labels else {},
        sources=[],
        config_warnings=(),
    )


def read_check_table(
    host: Host,
    action: DiscoveryAction,
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig = LOCAL,
    pending_changes: PendingChanges,
) -> DiscoveryResult:
    """``get_check_table`` with the arguments that never vary between these tests."""
    return get_check_table(
        host,
        action,
        automation_config=automation_config,
        user_permission_config=_USER_PERMISSION_CONFIG,
        raise_errors=False,
        debug=False,
        use_git=False,
        pending_changes=pending_changes,
    )


def accept_undecided(
    host: Host,
    result: DiscoveryResult,
    *,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    pending_changes: PendingChanges,
) -> DiscoveryResult:
    """The most ordinary write there is: move one undecided service into monitoring."""
    return perform_service_discovery(
        DiscoveryAction.SINGLE_UPDATE,
        result,
        None,
        DiscoveryState.MONITORED,
        host=host,
        selected_services=(SERVICE,),
        raise_errors=False,
        automation_config=automation_config,
        user_permission_config=_USER_PERMISSION_CONFIG,
        pprint_value=False,
        debug=False,
        use_git=False,
        pending_changes=pending_changes,
    )


# --------------------------------------------------------------------------------------------
# T2.1 -- read-path dispatch
# --------------------------------------------------------------------------------------------


@pytest.mark.usefixtures("inline_background_jobs")
def test_get_check_table_reads_locally_through_the_local_transport(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
) -> None:
    """The local branch runs the job in-process and the preview goes out on the local transport."""
    transport.preview = preview_result([entry(DiscoveryState.UNDECIDED)])

    result = read_check_table(
        sample_host,
        DiscoveryAction.NONE,
        pending_changes=pending_changes,
    )

    assert transport.commands == ["service-discovery-preview"]
    assert transport.sites_for("service-discovery-preview") == [None]
    assert transport.remote_jobs == []
    assert [e.description for e in result.check_table] == [DESCRIPTION]


@pytest.mark.usefixtures("inline_background_jobs")
def test_get_check_table_reads_remotely_by_syncing_then_delegating_the_job(
    remote_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
) -> None:
    """The remote branch syncs first, then hands the whole job to the remote site.

    No preview automation is issued locally: the remote site runs its own ``get_check_table`` and
    returns a serialized ``DiscoveryResult``. The options payload is asserted verbatim because it
    is the wire contract between the two sites.
    """
    transport.remote_check_table = discovery_result([entry(DiscoveryState.UNDECIDED)])

    result = read_check_table(
        remote_host,
        DiscoveryAction.NONE,
        automation_config=REMOTE,
        pending_changes=pending_changes,
    )

    assert transport.commands == []
    assert transport.synced_sites == [REMOTE_SITE]
    assert transport.remote_jobs == [
        (
            REMOTE_SITE,
            "service-discovery-job",
            (
                ("host_name", str(HOST_NAME)),
                (
                    "options",
                    json.dumps(
                        {
                            "ignore_errors": True,
                            "action": DiscoveryAction.NONE,
                            "debug": False,
                        }
                    ),
                ),
            ),
        )
    ]
    assert [e.description for e in result.check_table] == [DESCRIPTION]


# --------------------------------------------------------------------------------------------
# T2.2 -- every write path uses the automation config it was handed
# --------------------------------------------------------------------------------------------

#: The three automations that change something on the monitored site. Each one takes an
#: ``automation_config`` argument; each one must use the caller's.
WRITE_COMMANDS = frozenset({"set-autochecks-v2", "update-host-labels", "get-services-labels"})


@pytest.mark.usefixtures("inline_background_jobs")
def test_write_paths_use_the_given_automation_config(
    remote_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
) -> None:
    """Every write reaches the site the caller named -- the PoC's worst defect, inverted.

    Two calls, because no single action exercises all three writes: ``perform_fix_all`` with
    discovered host labels covers ``update-host-labels`` and ``set-autochecks-v2``, and disabling a
    monitored service covers ``get-services-labels`` (the disabled-services editor's lookup) and
    ``set-autochecks-v2`` again. The assertion is on the transport, not on a recorded argument: a
    hard-coded ``LocalAutomationConfig()`` shows up as a *local* automation while the caller asked
    for a remote site, which is precisely how §10.10 fails one caller up.
    """
    perform_fix_all(
        discovery_result([entry(DiscoveryState.UNDECIDED)], discovered_labels=[_HOST_LABEL]),
        host=remote_host,
        raise_errors=False,
        automation_config=REMOTE,
        user_permission_config=_USER_PERMISSION_CONFIG,
        pprint_value=False,
        debug=False,
        use_git=False,
        pending_changes=pending_changes,
    )
    perform_service_discovery(
        DiscoveryAction.SINGLE_UPDATE,
        discovery_result([entry(DiscoveryState.MONITORED)]),
        None,
        DiscoveryState.IGNORED,
        host=remote_host,
        selected_services=(SERVICE,),
        raise_errors=False,
        automation_config=REMOTE,
        user_permission_config=_USER_PERMISSION_CONFIG,
        pprint_value=False,
        debug=False,
        use_git=False,
        pending_changes=pending_changes,
    )

    observed = {call.command for call in transport.calls} & WRITE_COMMANDS
    assert observed == WRITE_COMMANDS, (
        f"the scenario no longer exercises every write path: {sorted(observed)}"
    )
    # Rule matching is a question about the *central* configuration and is not a write path:
    # `analyze_service_rule_matches` hard-codes `LocalAutomationConfig()`, and that is correct
    # rather than a missed parameter, so do not "fix" it into a dispatched call. What the
    # correctness rests on is that the remote host is in the central site's `all_hosts` -- WATO
    # writes every host of the folder tree there with no site filter -- so it survives the
    # `intersection_update(_all_configured_hosts)` inside `set_all_processed_hosts` instead of
    # landing in no candidate set and matching nothing at all. Beyond that: folder path, tags and
    # explicit labels are central data, and the service labels arrive as an argument that
    # `get_services_labels` already fetched from the owning site. Full reasoning, including the two
    # genuinely per-site inputs and what was decided about each, in the behaviour matrix's §6.1
    # "Not an asymmetry: rule matching is central by design" (B-F4).
    assert [call.command for call in transport.calls if call.site is None] == [
        "analyze-service-rule-matches"
    ]


# --------------------------------------------------------------------------------------------
# T2.3 / T2.4 -- what the central site does around a remote automation
# --------------------------------------------------------------------------------------------


#: The two transports, each with the host it belongs to. Requested by name and resolved with
#: ``getfixturevalue`` because the host has to be created by a fixture but selected per case.
TRANSPORTS: Sequence[tuple[str, LocalAutomationConfig | RemoteAutomationConfig]] = (
    ("sample_host", LOCAL),
    ("remote_host", REMOTE),
)


@pytest.mark.usefixtures("inline_background_jobs")
@pytest.mark.parametrize("host_fixture, automation_config", TRANSPORTS, ids=["local", "remote"])
def test_tabula_rasa_records_its_change_centrally_on_both_transports(
    request: pytest.FixtureRequest,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    host_fixture: str,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
) -> None:
    """B-F2.2: ``refresh-autochecks`` is recorded before the local/remote branch.

    That is what makes it a *central* change: the work happens on the site owning the host, but the
    change is recorded where ``get_check_table`` runs. The scope is the *host's* site, which is why
    the remote case needs a host that is actually remote -- otherwise the two parametrizations
    could not tell "the host's site" from "the site this process runs on".
    """
    host = request.getfixturevalue(host_fixture)

    read_check_table(
        host,
        DiscoveryAction.TABULA_RASA,
        automation_config=automation_config,
        pending_changes=pending_changes,
    )

    change, scope = pending_changes.only("refresh-autochecks")
    assert change.object_ref == host.object_ref()
    assert list(change.domains) == ["check_mk"]
    assert scope == ChangeScope.sites([host.site_id()])


@pytest.mark.usefixtures("inline_background_jobs")
@pytest.mark.parametrize(
    "host_fixture, automation_config, expected_syncs",
    [("sample_host", LOCAL, []), ("remote_host", REMOTE, [REMOTE_SITE])],
    ids=["local", "remote"],
)
def test_changes_are_synced_before_a_remote_automation_only(
    request: pytest.FixtureRequest,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    host_fixture: str,
    automation_config: LocalAutomationConfig | RemoteAutomationConfig,
    expected_syncs: Sequence[SiteId],
) -> None:
    """B-F2.1: exactly one pre-sync, of the host's site, on the remote path; none on the local one."""
    read_check_table(
        request.getfixturevalue(host_fixture),
        DiscoveryAction.NONE,
        automation_config=automation_config,
        pending_changes=pending_changes,
    )

    assert transport.synced_sites == list(expected_syncs)


# --------------------------------------------------------------------------------------------
# T2.5 -- job lifecycle per action (§6 Matrix B)
#
# Four tests rather than one parametrization: "does it start a job", "does it stop one", "does it
# fetch" and "does it rediscover" are four different observations that do not share a shape.
# --------------------------------------------------------------------------------------------

#: The only two actions that run the background job. Everything else reads the cached preview.
SCANNING_ACTIONS = frozenset({DiscoveryAction.REFRESH, DiscoveryAction.TABULA_RASA})


@pytest.mark.usefixtures("inline_background_jobs")
@pytest.mark.parametrize("job_running", [False, True], ids=["idle", "running"])
@pytest.mark.parametrize("action", list(DiscoveryAction))
def test_only_refresh_and_tabula_rasa_start_the_background_job(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    mocker: MockerFixture,
    action: DiscoveryAction,
    job_running: bool,
) -> None:
    """Both halves of the guard: the right action, and no job already running.

    ``is_active`` is parametrized rather than left at its default, because a start guard that had
    lost its ``not job.is_active()`` term would be indistinguishable from the correct one against a
    host that never has a job running -- and re-starting a running scan is precisely the
    second-click case §10.18 is about.
    """
    mocker.patch.object(ServiceDiscoveryBackgroundJob, "is_active", return_value=job_running)
    start = mocker.spy(ServiceDiscoveryBackgroundJob, "start")

    read_check_table(
        sample_host,
        action,
        pending_changes=pending_changes,
    )

    assert start.call_count == (1 if action in SCANNING_ACTIONS and not job_running else 0)


@pytest.mark.usefixtures("inline_background_jobs")
@pytest.mark.parametrize("job_running", [False, True], ids=["idle", "running"])
@pytest.mark.parametrize("action", list(DiscoveryAction))
def test_only_stop_stops_a_running_background_job(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    mocker: MockerFixture,
    action: DiscoveryAction,
    job_running: bool,
) -> None:
    """``stop`` is guarded by *both* the action and the job actually running."""
    mocker.patch.object(ServiceDiscoveryBackgroundJob, "is_active", return_value=job_running)
    stop = mocker.patch.object(ServiceDiscoveryBackgroundJob, "stop")

    read_check_table(
        sample_host,
        action,
        pending_changes=pending_changes,
    )

    assert stop.call_count == (1 if action is DiscoveryAction.STOP and job_running else 0)


@pytest.mark.usefixtures("inline_background_jobs")
@pytest.mark.parametrize(
    "action, expected_fetching",
    [
        (DiscoveryAction.NONE, [False]),
        (DiscoveryAction.SINGLE_UPDATE, [False]),
        # The job fetches, then the scan fetches again; ``get_result`` reads the stored preview.
        (DiscoveryAction.REFRESH, [True, True]),
        # The job fetches, rediscovers, and ``get_result`` then re-reads without fetching.
        (DiscoveryAction.TABULA_RASA, [True, False]),
    ],
)
def test_prevent_fetching_per_preview_call(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    action: DiscoveryAction,
    expected_fetching: list[bool],
) -> None:
    """Which preview calls talk to the host, in order.

    Observed through the ``@nofetch`` automation argument rather than through the
    ``prevent_fetching`` keyword, so the assertion survives a refactoring of the helper that builds
    the argument list.
    """
    read_check_table(
        sample_host,
        action,
        pending_changes=pending_changes,
    )

    assert [
        "@nofetch" not in args for args in transport.args_for("service-discovery-preview")
    ] == expected_fetching


@pytest.mark.usefixtures("inline_background_jobs")
@pytest.mark.parametrize("action", list(DiscoveryAction))
def test_only_tabula_rasa_rediscovers_and_it_adopts_everything(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    action: DiscoveryAction,
) -> None:
    """``TABULA_RASA`` is the one action that runs a real discovery, with every flag set.

    All five ``DiscoverySettings`` flags are ``True``, which is what makes it equivalent to
    "accept all" against freshly fetched data rather than a distinct semantics (§5, KNW-2342).
    """
    read_check_table(
        sample_host,
        action,
        pending_changes=pending_changes,
    )

    rediscoveries = transport.args_for("service-discovery")
    if action is not DiscoveryAction.TABULA_RASA:
        assert rediscoveries == []
        return

    assert len(rediscoveries) == 1
    args = rediscoveries[0]
    assert "@scan" in args
    settings = DiscoverySettings.from_automation_arg(args[args.index("@scan") + 1])
    assert settings == DiscoverySettings(
        update_host_labels=True,
        add_new_services=True,
        remove_vanished_services=True,
        update_changed_service_labels=True,
        update_changed_service_parameters=True,
    )


# --------------------------------------------------------------------------------------------
# T2.6 -- the wire format between sites
# --------------------------------------------------------------------------------------------


#: Position of ``sources`` in the serialized tuple -- read from the type rather than written as a
#: literal, so adding a field ahead of it moves the index instead of silently checking a neighbour.
_SOURCES_FIELD = DiscoveryResult._fields.index("sources")


@pytest.mark.parametrize(
    "peer_version, fields, sources_type",
    [
        # config_warnings was added in 2.5.0b1 and is truncated for older peers.
        ("2.4.0", 10, dict),
        ("2.5.0b1", 11, dict),
        ("3.0.0b1", 11, list),
    ],
)
def test_discovery_result_wire_shape_per_peer(
    peer_version: str, fields: int, sources_type: type
) -> None:
    """B-F2.3: what a peer of a given version is sent.

    Two independent compatibility shims live in ``serialize``: the trailing field is dropped for
    peers that cannot read it, and ``sources`` is re-keyed into a dict for peers that still expect
    the old source-ident mapping. Both are asserted here because both are silent -- a peer receives
    a well-formed payload either way.
    """
    result = discovery_result([entry(DiscoveryState.UNDECIDED)])._replace(sources=[(0, "Success")])

    raw = ast.literal_eval(result.serialize(Version.from_str(peer_version)))

    assert len(raw) == fields
    assert isinstance(raw[_SOURCES_FIELD], sources_type)


@pytest.mark.parametrize("peer_version", ["2.5.0b1", "3.0.0b1", __version__])
def test_discovery_result_round_trips_for_peers_carrying_every_field(peer_version: str) -> None:
    """The deserializer accepts both ``sources`` shapes and restores the same result."""
    original = discovery_result([entry(DiscoveryState.UNDECIDED)])._replace(
        sources=[(0, "Success")]
    )

    restored = DiscoveryResult.deserialize(original.serialize(Version.from_str(peer_version)))

    assert restored.check_table == original.check_table
    assert restored.check_table_created == original.check_table_created
    assert restored.labels_by_host == original.labels_by_host
    assert list(restored.sources) == list(original.sources)


# --------------------------------------------------------------------------------------------
# T2.7 -- pending changes
# --------------------------------------------------------------------------------------------


@pytest.mark.usefixtures("inline_background_jobs")
@pytest.mark.parametrize(
    "source, target, force_sync",
    [
        # Accepting a service touches the autochecks only -- no rule, so no config sync needed.
        (DiscoveryState.UNDECIDED, DiscoveryState.MONITORED, False),
        # Disabling one writes a Disabled services rule, which the remote site needs before the
        # autochecks make sense.
        (DiscoveryState.MONITORED, DiscoveryState.IGNORED, True),
    ],
    ids=["accept", "disable"],
)
def test_set_autochecks_change_carries_the_sync_requirement(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    source: str,
    target: str,
    force_sync: bool,
) -> None:
    """``force_sync`` is the transition's ``need_sync``, not a constant."""
    perform_service_discovery(
        DiscoveryAction.SINGLE_UPDATE,
        discovery_result([entry(source)]),
        None,
        target,
        host=sample_host,
        selected_services=(SERVICE,),
        raise_errors=False,
        automation_config=LOCAL,
        user_permission_config=_USER_PERMISSION_CONFIG,
        pprint_value=False,
        debug=False,
        use_git=False,
        pending_changes=pending_changes,
    )

    change, scope = pending_changes.only("set-autochecks")
    assert change.object_ref == sample_host.object_ref()
    assert list(change.domains) == ["check_mk"]
    assert change.force_sync is force_sync
    assert scope == ChangeScope.sites([sample_host.site_id()])


@pytest.mark.usefixtures("inline_background_jobs")
def test_update_host_labels_change_is_recorded_for_the_labelled_host(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
) -> None:
    """The change is scoped to the host the labels belong to, not to the acting site."""
    perform_host_label_discovery(
        DiscoveryAction.UPDATE_HOST_LABELS,
        discovery_result([], discovered_labels=[_HOST_LABEL]),
        host=sample_host,
        raise_errors=False,
        automation_config=LOCAL,
        user_permission_config=_USER_PERMISSION_CONFIG,
        pprint_value=False,
        debug=False,
        use_git=False,
        pending_changes=pending_changes,
    )

    change, scope = pending_changes.only("update-host-labels")
    assert change.object_ref == sample_host.object_ref()
    assert list(change.domains) == ["check_mk"]
    assert scope == ChangeScope.sites([sample_host.site_id()])


# --------------------------------------------------------------------------------------------
# T2.8 -- what the GUI's context manager does around every action
# --------------------------------------------------------------------------------------------


@pytest.mark.usefixtures("inline_background_jobs")
def test_service_discovery_context_demands_wato_services(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    demanded_permissions: list[str],
) -> None:
    """Entering the context is the only place ``wato.services`` is demanded on a GUI path."""
    accept_undecided(
        sample_host,
        discovery_result([entry(DiscoveryState.UNDECIDED)]),
        automation_config=LOCAL,
        pending_changes=pending_changes,
    )

    assert "wato.services" in demanded_permissions


@pytest.mark.usefixtures("inline_background_jobs")
@pytest.mark.parametrize("flagged", [True, False], ids=["flagged", "not-flagged"])
def test_discovery_failed_flag_is_written_only_when_it_was_set(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    mocker: MockerFixture,
    flagged: bool,
) -> None:
    """The clear is guarded, so on virtually every call it is a no-op.

    Asserting the guard rather than the call: ``clear_discovery_failed`` runs on every ``perform_*``
    but only reaches ``save_hosts`` when the attribute is actually present, which is why P-F3's
    original "one hosts.mk write per click" cost claim was wrong (§5.1).
    """
    if flagged:
        sample_host.set_discovery_failed(pprint_value=False, acting_user=user)
    save_hosts = mocker.spy(Folder, "save_hosts")

    accept_undecided(
        sample_host,
        discovery_result([entry(DiscoveryState.UNDECIDED)]),
        automation_config=LOCAL,
        pending_changes=pending_changes,
    )

    assert save_hosts.call_count == (1 if flagged else 0)
    assert sample_host.discovery_failed() is False


@pytest.mark.usefixtures("inline_background_jobs")
def test_discovery_failed_flag_is_left_alone_for_a_locked_host(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    mocker: MockerFixture,
) -> None:
    """A host managed by a configuration bundle must not be written to by the discovery page."""
    sample_host.set_discovery_failed(pprint_value=False, acting_user=user)
    mocker.patch.object(Host, "locked", return_value=True)
    save_hosts = mocker.spy(Folder, "save_hosts")

    accept_undecided(
        sample_host,
        discovery_result([entry(DiscoveryState.UNDECIDED)]),
        automation_config=LOCAL,
        pending_changes=pending_changes,
    )

    # The discovery itself still runs: without this, an ``accept_undecided`` that did nothing at
    # all would satisfy both assertions below.
    assert "set-autochecks-v2" in transport.commands
    assert save_hosts.call_count == 0
    assert sample_host.discovery_failed() is True


# --------------------------------------------------------------------------------------------
# T2.9 -- Discovery on its own enforces nothing
# --------------------------------------------------------------------------------------------


@pytest.mark.usefixtures("inline_background_jobs")
def test_discovery_alone_demands_no_wato_services(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    demanded_permissions: list[str],
) -> None:
    """``Discovery`` demands per-target permissions and nothing else.

    This is a layering fact, not an endorsement: ``_service_discovery_context`` is where
    ``wato.services`` is enforced, and ``Discovery`` -- the shape the REST endpoint uses -- is
    below that line. It stays true after §10.4 is fixed, because that fix is at the endpoint. The
    endpoint-level gap is the quarantined ``test_update_service_phase_*_wato_services`` pair.
    """
    Discovery(
        sample_host,
        DiscoveryAction.SINGLE_UPDATE,
        update_target=DiscoveryState.MONITORED,
        update_source=None,
        selected_services=(SERVICE,),
        user_need_permission=user.need_permission,
    ).do_discovery(
        discovery_result([entry(DiscoveryState.UNDECIDED)]),
        HOST_NAME,
        automation_config=LOCAL,
        pprint_value=False,
        debug=False,
        use_git=False,
        pending_changes=pending_changes,
    )

    assert demanded_permissions == ["wato.service_discovery_to_monitored"]


# --------------------------------------------------------------------------------------------
# T2.10 -- host labels are independent of the service transition
# --------------------------------------------------------------------------------------------


@pytest.mark.usefixtures("inline_background_jobs")
def test_host_labels_are_written_even_when_no_service_changes(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
) -> None:
    """``fix_all`` on a table with nothing to do still updates the discovered host labels.

    The transition is ``None`` here -- no row's source differs from its target -- so an
    implementation that hangs the label update off the transition would silently skip it.

    This replaces ``test_services.py``'s ``test_perform_fix_all_clears_host_labels_without_service
    _changes`` (CMK-31896 / CMK-32535), whose subject this is: it asserted the same property one
    step downstream, on the label deltas of the re-read result, and did so through a patched
    ``local_discovery_preview`` -- the helper whose hard-coded ``LocalAutomationConfig()`` this
    file exists not to patch. Its two assertions are kept below.
    """
    transport.preview = preview_result([entry(DiscoveryState.MONITORED)])

    result = perform_fix_all(
        discovery_result(
            [entry(DiscoveryState.MONITORED)],
            discovered_labels=[_HOST_LABEL],
            vanished_labels={"cmk/os_family": {"value": "linux", "plugin_name": "check_mk"}},
        ),
        host=sample_host,
        raise_errors=False,
        automation_config=LOCAL,
        user_permission_config=_USER_PERMISSION_CONFIG,
        pprint_value=False,
        debug=False,
        use_git=False,
        pending_changes=pending_changes,
    )

    assert "update-host-labels" in transport.commands
    assert "set-autochecks-v2" not in transport.commands
    # `perform_fix_all` returns a fresh read -- hence the table above -- so the deltas the caller
    # passed in are gone from the result it gets back.
    assert [e.description for e in result.check_table] == [DESCRIPTION]
    assert result.vanished_labels == {}
    assert result.changed_labels == {}


@pytest.mark.usefixtures("inline_background_jobs")
def test_host_labels_are_written_before_services(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
) -> None:
    """Ordering, when both happen: labels first, then the autochecks."""
    perform_fix_all(
        discovery_result([entry(DiscoveryState.UNDECIDED)], discovered_labels=[_HOST_LABEL]),
        host=sample_host,
        raise_errors=False,
        automation_config=LOCAL,
        user_permission_config=_USER_PERMISSION_CONFIG,
        pprint_value=False,
        debug=False,
        use_git=False,
        pending_changes=pending_changes,
    )

    commands = transport.commands
    assert commands.index("update-host-labels") < commands.index("set-autochecks-v2")


# --------------------------------------------------------------------------------------------
# Quarantine
#
# Divergences of §10 that live in this layer. Each is a pair: one `xfail(strict=True)` test stating
# the intended behaviour, one plain test pinning today's. When a ticket lands, delete both halves;
# the strict xfail turns the fix into a red suite until that happens, so the second half cannot be
# forgotten.
# --------------------------------------------------------------------------------------------


@pytest.fixture(name="update_ignored_phase")
def fixture_update_ignored_phase(
    mocker: MockerFixture,
    pending_changes: RecordingPendingChanges,
) -> Callable[[Host], int]:
    """Runs the endpoint's whole handler for `PUT .../update_discovery_phase` and returns its status.

    ``update_service_phase_v1`` rather than the ``_update_single_service_phase`` it delegates to:
    the endpoint's four ``need_permission`` calls are in the handler, not in the helper, and a fix
    for §10.4 or §10.9(b) may land in either. A tripwire below the layer the ticket names would
    keep failing after a correct fix and never fire -- which is the whole point of `strict=True`.

    Only two things stand in for the request: a ``Config`` carrying one local site, from which the
    handler derives its own automation config, and the patched ``make_pending_changes``, because
    the handler builds a ``PendingChanges`` instead of taking one and the tests have to see it.
    """
    mocker.patch.object(update_service_phase, "make_pending_changes", return_value=pending_changes)

    def run(host: Host) -> int:
        return update_service_phase.update_service_phase_v1(
            ApiContext.new(
                config=Config(
                    sites=SiteConfigurations({host.site_id(): site_configuration(host.site_id())})
                ),
                version=APIVersion.V1,
                etag_if_match=ETags(),
                host_url="http://localhost/",
                user=user,
                token=None,
            ),
            UpdateDiscoveryPhaseModel(
                check_type=PLUGIN,
                service_item=None,
                target_phase="ignored",
            ),
            host,
        ).status_code

    return run


# --- T2.11 / §10.18: a write issued while a scan is running --------------------------------
#
# Characterization only, no xfail partner. §10.18's fix is a `409` driven by a
# `check_table_created` precondition the *client* sends: the field belongs to the request model,
# which the harness below supplies by hand, so a fix would answer `409` only for a request that
# carries the precondition -- and an xfail here would have to guess its spelling to send one. The
# tripwire for this ticket is T3.6, which drives a real request and only has to change the status
# it expects. The two plain tests below pin the mechanism the precondition replaces.


@pytest.mark.usefixtures("inline_background_jobs")
def test_read_during_active_job_yields_an_empty_table(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    mocker: MockerFixture,
) -> None:
    """The mechanism behind §10.18, on the read side.

    While the job runs, ``get_result`` returns the requesting process's own
    ``_pre_discovery_preview`` -- which is the empty one built in ``__init__``, because the job's
    real pre-scan snapshot lives in the job process. ``check_table_created == 0`` is the marker the
    §10.18 fix turns into an explicit precondition.
    """
    mocker.patch.object(ServiceDiscoveryBackgroundJob, "is_active", return_value=True)

    result = read_check_table(
        sample_host,
        DiscoveryAction.NONE,
        pending_changes=pending_changes,
    )

    assert list(result.check_table) == []
    assert result.check_table_created == 0
    assert transport.commands == []


@pytest.mark.usefixtures("inline_background_jobs")
def test_update_during_active_job_writes_nothing_and_says_nothing(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    update_ignored_phase: Callable[[Host], int],
    mocker: MockerFixture,
) -> None:
    """Today: the requested change is discarded and the endpoint answers 204 anyway."""
    mocker.patch.object(ServiceDiscoveryBackgroundJob, "is_active", return_value=True)

    assert update_ignored_phase(sample_host) == 204

    assert transport.commands == []
    assert pending_changes.recorded == []


# --- T2.12 / §10.4: the endpoint's authorization surface ------------------------------------
#
# The tripwire is on the permissions the endpoint *declares*, not on the ones it demands.
# `PermissionValidator` raises in a testing context when an endpoint checks a permission it has
# not declared (`openapi/restful_objects/validators.py:559-572`), so no fix for §10.4 can land
# without adding `wato.services` to `UPDATE_PHASE_PERMISSIONS` -- whereas *where* the
# `need_permission` call ends up is a free choice, and an xfail that guessed wrong would keep
# failing after the fix and never fire. The declaration is also what the generated API
# documentation shows a client, which is half of what the ticket is about.


@pytest.mark.usefixtures("inline_background_jobs")
def test_update_service_phase_writes_without_asking_for_manage_services(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    demanded_permissions: list[str],
    update_ignored_phase: Callable[[Host], int],
) -> None:
    """Today: it disables a service -- autochecks *and* a rule -- demanding neither permission."""
    transport.preview = preview_result([entry(DiscoveryState.MONITORED)])

    assert update_ignored_phase(sample_host) == 204

    assert "wato.services" not in UPDATE_PHASE_PERMISSIONS
    assert "wato.services" not in demanded_permissions
    assert "wato.edit" not in demanded_permissions
    assert "set-autochecks-v2" in transport.commands
    assert pending_changes.actions() == ["new-rule", "set-autochecks"]


@pytest.mark.xfail(
    strict=True,
    reason="CMK-38594 (§10.4): update_discovery_phase bypasses wato.services and wato.edit, so a "
    "role denied 'Manage services' can still write ignored_services rules and delete services",
)
def test_update_service_phase_requires_manage_services() -> None:
    assert "wato.services" in UPDATE_PHASE_PERMISSIONS


# --- T2.13 / §10.9(a): the clear runs after the write ---------------------------------------


@contextlib.contextmanager
def no_folder_write_permission() -> Iterator[None]:
    """Make the folder write that clearing the flag performs fail, as it does for a non-contact.

    Scoped tightly around the action rather than patched for the whole test: the ``sample_host``
    fixture's teardown deletes the host, which writes the folder too, and would otherwise inherit
    the failure.
    """
    with mock.patch.object(
        Folder, "save_hosts", side_effect=MKAuthException("no permissions to the folder")
    ):
        yield


@pytest.mark.usefixtures("inline_background_jobs")
def test_clearing_the_discovery_failed_flag_can_fail_after_the_autochecks_were_written(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
) -> None:
    """Today: the discovery is written, and *then* the clear raises.

    ``save_hosts`` is made to raise here rather than building a folder-contact scenario, because
    the documented cause is exactly that: clearing the flag reaches ``Folder.save_hosts``, which
    requires folder *write*, while the discovery page requires only host read plus
    ``wato.services``. The point of the test is the ordering, not the permission machinery.
    """
    sample_host.set_discovery_failed(pprint_value=False, acting_user=user)

    with no_folder_write_permission(), pytest.raises(MKAuthException):
        accept_undecided(
            sample_host,
            discovery_result([entry(DiscoveryState.UNDECIDED)]),
            automation_config=LOCAL,
            pending_changes=pending_changes,
        )

    assert "set-autochecks-v2" in transport.commands
    assert pending_changes.actions() == ["set-autochecks"]


@pytest.mark.xfail(
    strict=True,
    reason="CMK-38595 (§10.9a): clear_discovery_failed reaches Folder.save_hosts, which needs "
    "folder write, on context-manager exit -- so a permission the page never required fails the "
    "request after the autochecks and the pending change are already committed",
)
@pytest.mark.usefixtures("inline_background_jobs")
def test_a_failing_flag_clear_leaves_no_half_finished_discovery(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
) -> None:
    sample_host.set_discovery_failed(pprint_value=False, acting_user=user)

    raised = False
    with no_folder_write_permission():
        try:
            accept_undecided(
                sample_host,
                discovery_result([entry(DiscoveryState.UNDECIDED)]),
                automation_config=LOCAL,
                pending_changes=pending_changes,
            )
        except MKAuthException:
            raised = True

    # Both branches, not just `not (raised and written)`: that form is also satisfied by a request
    # that neither raised nor wrote anything, which is not a fix but a silently dropped write, and
    # a strict xfail would report it as one.
    if raised:
        # The permission is checked before anything is written ...
        assert "set-autochecks-v2" not in transport.commands
        assert pending_changes.actions() == []
    else:
        # ... or the clear no longer needs a permission the page never asked for.
        assert "set-autochecks-v2" in transport.commands
        assert pending_changes.actions() == ["set-autochecks"]


# --- T2.14 / §10.9(b): the endpoint never clears the flag -----------------------------------


@pytest.mark.usefixtures("inline_background_jobs")
def test_update_service_phase_leaves_the_discovery_failed_flag_set(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    update_ignored_phase: Callable[[Host], int],
) -> None:
    """Today: a successful update leaves the host flagged as "discovery failed" forever."""
    transport.preview = preview_result([entry(DiscoveryState.MONITORED)])
    sample_host.set_discovery_failed(pprint_value=False, acting_user=user)

    assert update_ignored_phase(sample_host) == 204

    assert "set-autochecks-v2" in transport.commands
    assert sample_host.discovery_failed() is True


@pytest.mark.xfail(
    strict=True,
    reason="CMK-38595 (§10.9b): update_service_phase bypasses _service_discovery_context, so it "
    "never clears inventory_failed -- bulk discovery's 'only hosts that failed previously' set "
    "never converges for a client that only uses this endpoint",
)
@pytest.mark.usefixtures("inline_background_jobs")
def test_update_service_phase_clears_the_discovery_failed_flag(
    sample_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    update_ignored_phase: Callable[[Host], int],
) -> None:
    # The table below is what makes this a *successful* update: with the default empty preview there
    # is no transition, nothing is written, and this tripwire stays silent after a correct fix.
    transport.preview = preview_result([entry(DiscoveryState.MONITORED)])
    sample_host.set_discovery_failed(pprint_value=False, acting_user=user)

    assert update_ignored_phase(sample_host) == 204

    assert "set-autochecks-v2" in transport.commands
    assert sample_host.discovery_failed() is False


# --- T2.15 / §10.10: quick setup applies remote-site hosts locally --------------------------


@pytest.fixture(name="quick_setup_fix_all")
def fixture_quick_setup_fix_all(mocker: MockerFixture) -> MagicMock:
    """Stub out everything quick setup does around the one call site under test.

    ``_get_service_discovery_result`` polls a remote background job, which has nothing to do with
    the defect; ``perform_fix_all`` is recorded rather than run, because the question is only which
    ``automation_config`` reaches it.
    """
    mocker.patch(
        "cmk.gui.quick_setup.v0_unstable.predefined._complete._get_service_discovery_result",
        return_value=discovery_result([entry(DiscoveryState.UNDECIDED)]),
    )
    return mocker.patch(
        "cmk.gui.quick_setup.v0_unstable.predefined._complete.perform_fix_all",
        return_value=discovery_result([]),
    )


def run_quick_setup_discovery(pending_changes: PendingChanges) -> None:
    _run_service_discovery(
        folder_tree(),
        str(HOST_NAME),
        REMOTE_SITE,
        automation_config=REMOTE,
        user_permission_config=_USER_PERMISSION_CONFIG,
        pprint_value=False,
        debug=False,
        use_git=False,
        pending_changes=pending_changes,
    )


@pytest.mark.usefixtures("inline_background_jobs")
def test_quick_setup_reads_remotely_and_writes_locally(
    remote_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    quick_setup_fix_all: MagicMock,
) -> None:
    """Today: the check table is fetched from the remote site, the apply runs on the central one."""
    run_quick_setup_discovery(pending_changes)

    assert transport.synced_sites == [REMOTE_SITE]
    assert [site for site, _command, _vars in transport.remote_jobs] == [REMOTE_SITE]
    assert quick_setup_fix_all.call_args.kwargs["automation_config"] == LocalAutomationConfig()


@pytest.mark.xfail(
    strict=True,
    reason="CMK-38596 (§10.10): quick setup derives the right automation config, uses it for the "
    "read, and then passes LocalAutomationConfig() to perform_fix_all -- so a remote-site bundle's "
    "autochecks land in the central site's var/check_mk/autochecks/",
)
@pytest.mark.usefixtures("inline_background_jobs")
def test_quick_setup_writes_to_the_site_it_read_from(
    remote_host: Host,
    transport: Transport,
    pending_changes: RecordingPendingChanges,
    quick_setup_fix_all: MagicMock,
) -> None:
    run_quick_setup_discovery(pending_changes)

    assert quick_setup_fix_all.call_args.kwargs["automation_config"] == REMOTE
