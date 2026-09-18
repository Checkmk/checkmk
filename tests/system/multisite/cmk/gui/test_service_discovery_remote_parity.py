#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tier 4 of the service discovery guardrail suite: remote-site parity.

Every action is driven through the REST API **on the central site**, against two identically
configured hosts -- one owned by the central site, one by the remote -- fed the same agent output.
What the tier pins is that the answer does not depend on which site owns the host. See
``packages/cmk-check-engine/docs/SERVICE_DISCOVERY_BEHAVIOUR_MATRIX.md`` §7 for the row-by-row
specification and §6.1 for the local/remote asymmetries these tests are built around.

Three properties of the design are worth knowing before adding a case:

* **A parity assertion is blind to any defect that behaves the same way on both sites**, and every
  item of §10 is symmetric except §10.10. The hazard here is therefore a *green* test rather than
  a red one -- §10.19 answers an unknown ``ServiceID`` with ``204`` and writes nothing, §10.18
  discards a write issued during an active scan, and a never-scanned host yields an empty table.
  Each of the three produces a pass that proves nothing. So every test below asserts the resulting
  phases themselves rather than only their equality, and ``_host_pair`` refuses to yield a pair
  whose check table does not hold the services it just configured.
* **The preview reads cached agent data.** ``ServiceDiscoveryBackgroundJob.get_result`` calls
  ``_get_discovery_preview`` with ``prevent_fetching=True``, which becomes
  ``FileCacheOptions(use_only_cache=True)``, so only ``refresh`` and ``tabula_rasa`` fetch.
  ``_host_pair`` therefore scans both hosts before yielding, and a test that changes what the
  agent reports has to rescan for the change to be visible.
* **Both sites run the same version**, so B-F2.3's version-truncated wire format never fires.
  Parity is established **at equal versions** and says nothing about the supported version skew.
"""

import html
import json
import logging
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass

import pytest

from cmk.checkengine.discovery import AutochecksSerializer
from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

logger = logging.getLogger(__name__)

# The `local` check plugin turns each line of a `<<<local>>>` section into one service whose item
# and description are the name in the line, which makes the identifiers a test uses fully
# predictable -- the precondition for §10.19's "assert a positive change, not equality".
_PLUGIN = "local"
_SERVICES = ("SDParityAlpha", "SDParityBeta", "SDParityGamma")
# The row the single-service tests act on; the rest are the untouched controls beside it.
_SUBJECT = _SERVICES[0]
_GHOST = "SDParityGhost"
_LABEL_NAME = "sd-parity"
_LABEL_VALUE = "tier4"

_AGENT_OUTPUT_DIR = "var/check_mk/agent_output"
# `<HOST>` is substituted by `ConfigCache.translate_fetcher_commandline`, so one replicated rule
# serves both hosts while each site keeps its own copy of the output. That split is deliberate: it
# lets a test change what the agent reports without touching the configuration, and therefore
# without an activation.
_DATASOURCE_COMMAND = f"cat ~/{_AGENT_OUTPUT_DIR}/<HOST>"

# The two modes that start a background job; the other five are answered inline.
_JOB_MODES = frozenset({"refresh", "tabula_rasa"})


def _agent_output(services: Sequence[str] = _SERVICES) -> str:
    return (
        "\n".join(
            [
                "<<<local:sep(0)>>>",
                *(f"0 {service} - {service} is fine" for service in services),
                "<<<labels:sep(0)>>>",
                json.dumps({_LABEL_NAME: _LABEL_VALUE}),
            ]
        )
        + "\n"
    )


@dataclass(frozen=True)
class ParityHost:
    """A host together with the site that owns it.

    "Owns" means: fetches its agent data, holds its autochecks and its discovered host labels, and
    monitors it. Which site that is, is precisely what these tests are about, so the pairing is
    made explicit rather than derived at each assertion.
    """

    name: str
    site: Site

    @property
    def autochecks(self) -> str:
        return f"var/check_mk/autochecks/{self.name}.mk"

    @property
    def discovered_host_labels(self) -> str:
        return f"var/check_mk/discovered_host_labels/{self.name}.mk"

    @property
    def agent_output(self) -> str:
        return f"{_AGENT_OUTPUT_DIR}/{self.name}"


def _phases(central_site: Site, host_name: str) -> dict[str, str]:
    """`{check table key: phase}` for one host, read through the central site."""
    result = central_site.openapi.service_discovery.get_discovery_result(host_name)
    extensions = result["extensions"]
    assert isinstance(extensions, dict)
    check_table = extensions["check_table"]
    assert isinstance(check_table, dict)
    return {key: entry["extensions"]["service_phase"] for key, entry in check_table.items()}


def _discovered_services(central_site: Site, host_name: str) -> dict[str, str]:
    """The phases of the services this module configures, keyed by service item."""
    prefix = f"{_PLUGIN}-"
    return {
        key.removeprefix(prefix): phase
        for key, phase in _phases(central_site, host_name).items()
        if key.startswith(prefix)
    }


def _host_labels(central_site: Site, host_name: str) -> dict[str, str]:
    """The *discovered* host labels of one host -- not the merged set `labels_of_host` returns."""
    result = central_site.openapi.service_discovery.get_discovery_result(host_name)
    extensions = result["extensions"]
    assert isinstance(extensions, dict)
    host_labels = extensions["host_labels"]
    assert isinstance(host_labels, dict)
    return {name: entry["value"] for name, entry in host_labels.items()}


def _autocheck_items(host: ParityHost) -> set[str]:
    """The `local` items in `host`'s autochecks file, read on the site that owns it.

    Deserialized with the product's own `AutochecksSerializer` rather than a hand-rolled parse, so
    a change to the on-disk format cannot make this quietly disagree with what wrote the file.
    `AutochecksStore` is not usable here: it reads from the local `autochecks_dir`, while the file
    this wants belongs to whichever site owns the host.
    """
    if not host.site.file_exists(host.autochecks):
        return set()
    entries = AutochecksSerializer().deserialize(host.site.read_file(host.autochecks).encode())
    return {
        entry.item
        for entry in entries
        if str(entry.check_plugin_name) == _PLUGIN and entry.item is not None
    }


def _monitored_services(site: Site, host_name: str) -> set[str]:
    """The services `site` monitors for `host_name`, asked of that site's own livestatus.

    Deliberately not routed through the central site: the point of several assertions below is
    where the effect landed, and the central site's livestatus is multisite and would hide it.
    """
    query = f"GET services\nColumns: description\nFilter: host_name = {host_name}\n"
    return {str(row[0]) for row in site.live.query(query)}


def _wait_for_monitoring(site: Site, host_name: str, service: str, *, present: bool) -> None:
    """Wait until `site`'s own monitoring does -- or no longer does -- carry `service`.

    Every caller runs right after an activation, and the core is briefly unreachable while it
    reloads. The livestatus error is retried rather than folded into the answer: treating an
    unreachable core as "the service is gone" would make the negative case pass for the wrong
    reason. The conftest's own liveness probe retries the same way.
    """

    def _reached() -> bool:
        try:
            return (service in _monitored_services(site, host_name)) is present
        except Exception:  # livestatus is down for the duration of the core reload
            logger.info("livestatus on site %s is not answering yet", site.id)
            return False

    wait_until(
        _reached,
        timeout=120,
        interval=2,
        condition_name=(
            f"{service} {'appears in' if present else 'leaves'} monitoring of {host_name}"
        ),
    )


def _run_mode(central_site: Site, host_name: str, mode: str) -> None:
    """Run one discovery mode, waiting for the job that the two scanning modes start.

    `run_discovery_and_wait_for_completion` asserts the job reached `finished`, which is only
    meaningful for the modes that start one: the other five are answered `200` inline and would be
    judged against whichever job happened to run last.
    """
    discovery = central_site.openapi.service_discovery
    if mode in _JOB_MODES:
        discovery.run_discovery_and_wait_for_completion(host_name, mode=mode, timeout=180)
    else:
        discovery.run_discovery(host_name, mode=mode)


def _wait_until_idle(central_site: Site, host_name: str) -> None:
    def _idle() -> bool:
        status = central_site.openapi.service_discovery.get_discovery_job_status(host_name)
        return not status["extensions"]["active"]

    wait_until(
        _idle, timeout=120, interval=1, condition_name=f"no discovery job active on {host_name}"
    )


def _wait_for_phase(central_site: Site, host_name: str, service: str, phase: str) -> None:
    """Wait until `service` reads as `phase` on `host_name`.

    Needed wherever the expected phase depends on a *rule* rather than on the autochecks file.
    Autochecks are written by the automation on the owning site before the call returns, but a
    disabled-services rule is written into the **central** configuration while the row is
    classified on the site that owns the host. For a remote host the rule gets there by way of
    three hops with no happens-before edge between them -- `_update_config_on_remote_site` unpacks
    the snapshot, the watcher records the change into redis asynchronously, and
    `reload_if_required` compares whenever the next automation happens to arrive -- and that
    window has not been measured. `.get` rather than `[...]`, because a row may be absent from the
    table for a moment rather than merely carrying the wrong phase.
    """
    wait_until(
        lambda: _discovered_services(central_site, host_name).get(service) == phase,
        timeout=60,
        interval=2,
        condition_name=f"{service} reads as {phase!r} on {host_name}",
    )


def _job_progress(central_site: Site, host_name: str) -> Sequence[str]:
    """The progress log of `host_name`'s last discovery job, as the central site reports it.

    For a remote host this is `job_snapshot` taking the `site_is_local` branch it does not have
    and going out over `fetch_service_discovery_background_job_status` -- the same call that makes
    the `execute` endpoint's `409` guard work across the site boundary.
    """
    status = central_site.openapi.service_discovery.get_discovery_job_status(host_name)
    progress: Sequence[str] = status["extensions"]["logs"]["progress"]
    return progress


def _update_phase(central_site: Site, host_name: str, service: str, target_phase: str) -> None:
    """Move one service of `host_name` into `target_phase`, waiting out any active scan first.

    §10.18: `update_service_phase` carries no `409` guard on either site -- unlike the `execute`
    endpoint, whose guard does cross the site boundary via `job_snapshot` /
    `fetch_service_discovery_background_job_status` -- so a write issued while a scan runs is
    answered `204` and discarded. Waiting here is what keeps that from showing up as flakiness.
    """
    _wait_until_idle(central_site, host_name)
    central_site.openapi.service_discovery.update_service_phase(
        host_name, check_type=_PLUGIN, service_item=service, target_phase=target_phase
    )


def _has_pending_change(central_site: Site, action_name: str, host_name: str) -> bool:
    """Whether a change of `action_name` naming `host_name` is pending centrally.

    The change record carries no host field (`ActivationChange` is id/user/action/text/time), so
    the host has to be read out of the rendered text. Matched *with its quotes*, because a bare
    substring match would let one host answer for another whose name extends it -- `sd-cluster`
    inside `sd-cluster-node`, a pair this module already has.

    The text has to be unescaped first: `PendingChanges.add` stores it through
    `escaping.escape_text`, which is `html.escape(..., quote=True)`, so the quotes the product put
    around the host name arrive as `&#x27;`. Matching the raw text would make every *negative*
    assertion below pass for the wrong reason and only the positive ones fail.
    """
    quoted = f"'{host_name}'"
    return any(
        change.get("action_name") == action_name
        and quoted in html.unescape(str(change.get("text", "")))
        for change in central_site.openapi.changes.get_pending()
    )


@contextmanager
def _host_pair(
    central_site: Site,
    remote_site: Site,
    slug: str,
    *,
    services: Sequence[str] = _SERVICES,
) -> Iterator[tuple[ParityHost, ParityHost]]:
    """Two identically configured hosts -- one per site -- both already scanned.

    Everything lives in a folder of its own, which lets the teardown drop the hosts, the datasource
    rule and any `ignored_services` rule the product wrote in the course of a test in one call:
    those are created in the host's own folder (`rulesets.py`'s `_update_rule_of_host`).

    Each test takes its own pair under its own names rather than resetting a shared one, so no test
    can be made to pass or fail by the order it runs in.
    """
    folder = f"/sd_parity_{slug.replace('-', '_')}"
    pair = (
        ParityHost(f"sd-{slug}-central", central_site),
        ParityHost(f"sd-{slug}-remote", remote_site),
    )
    central_site.openapi.folders.create(folder)
    try:
        for host in pair:
            central_site.openapi.hosts.create(
                host.name,
                folder=folder,
                attributes={"site": host.site.id, "ipaddress": "127.0.0.1"},
            )
            host.site.makedirs(_AGENT_OUTPUT_DIR)
            host.site.write_file(host.agent_output, _agent_output(services))
        central_site.openapi.rules.create(
            ruleset_name="datasource_programs",
            value=_DATASOURCE_COMMAND,
            folder=folder,
            conditions={
                "host_name": {"match_on": [member.name for member in pair], "operator": "one_of"}
            },
        )
        central_site.openapi.changes.activate_and_wait_for_completion()

        for host in pair:
            # Without a scan there is nothing for the preview to read -- `prevent_fetching=True`
            # over an empty file cache yields an empty check table, and every assertion below
            # would hold vacuously. The read that follows also consumes the preview this scan
            # stored, since `_load_last_preview` unlinks the file, so later reads recompute.
            _run_mode(central_site, host.name, "refresh")
            discovered = _discovered_services(central_site, host.name)
            assert set(services) <= set(discovered), (
                f"the agent output did not reach {host.name} on site {host.site.id}: "
                f"discovered {sorted(discovered)}"
            )
        logger.info(
            "Parity pair ready in %s: %s", folder, ", ".join(f"{h.name}@{h.site.id}" for h in pair)
        )
        yield pair
    finally:
        central_site.openapi.folders.delete(folder)
        central_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
        for host in pair:
            for path in (host.agent_output, host.autochecks, host.discovered_host_labels):
                if host.site.file_exists(path):
                    host.site.delete_file(path)


def _disable_one_service(central_site: Site, host: ParityHost) -> None:
    """Leave `_SUBJECT` disabled, as a row the mode under test must not touch.

    Chosen over a vanished row because only this one moves under the mutant it is there to catch.
    A `BULK_UPDATE` that stopped honouring `update_source` would retarget the disabled row to
    `unchanged`, and A2's `ignored`/`unchanged` cell is **AC** + **-D** -- the entry is written to
    autochecks and the rule is withdrawn -- so the phase moves to `monitored` and the assertion
    fires. Retargeting a *vanished* row to `unchanged` writes the identical entry back and leaves
    it classified `vanished`, so the phase would not move and the control would prove nothing.
    """
    _update_phase(central_site, host.name, _SUBJECT, "ignored")
    _wait_for_phase(central_site, host.name, _SUBJECT, "ignored")


def _make_one_service_vanish(central_site: Site, host: ParityHost) -> None:
    """Monitor everything, then stop reporting `_GHOST`, so exactly one row is `vanished`.

    Dropping it from the agent output needs no activation -- the output lives on the owning site
    rather than in the replicated configuration -- but it does need a rescan, because the preview
    reads the file cache.
    """
    _run_mode(central_site, host.name, "fix_all")
    host.site.write_file(host.agent_output, _agent_output(_SERVICES))
    _run_mode(central_site, host.name, "refresh")
    assert _discovered_services(central_site, host.name)[_GHOST] == "vanished", (
        f"{_GHOST} did not vanish on {host.name}, so `remove` has nothing to remove"
    )


@dataclass(frozen=True)
class ModeCase:
    """One row of T4.1: what to configure, what to do first, and what the mode must leave behind.

    One object per mode on purpose. The alternative -- a mode list, an expectation table, a
    baseline function and a `services=... if mode == ...` conditional in the test body -- keys
    four separate places on the same string, and adding a mode means finding all four.

    `expected` pins the phases rather than only comparing them across the two sites, because two
    hosts on which a mode did nothing at all are equal too.
    """

    expected: Mapping[str, str]
    services: Sequence[str] = _SERVICES
    baseline: Callable[[Site, ParityHost], None] | None = None


_MODE_CASES: Mapping[str, ModeCase] = {
    # `BULK_UPDATE(new -> unchanged)`: adopt the undecided rows, leave the disabled one alone.
    "new": ModeCase(
        expected={_SUBJECT: "ignored", **dict.fromkeys(_SERVICES[1:], "monitored")},
        baseline=_disable_one_service,
    ),
    # `BULK_UPDATE(vanished -> removed)`: the ghost goes and the three monitored rows are the
    # control -- retargeting those to `removed` would drop them, and they would read `undecided`.
    "remove": ModeCase(
        expected=dict.fromkeys(_SERVICES, "monitored"),
        services=(*_SERVICES, _GHOST),
        baseline=_make_one_service_vanish,
    ),
    "fix_all": ModeCase(expected=dict.fromkeys(_SERVICES, "monitored")),
    "tabula_rasa": ModeCase(expected=dict.fromkeys(_SERVICES, "monitored")),
    # A scan writes nothing, so a freshly created host's rows stay undecided.
    "refresh": ModeCase(expected=dict.fromkeys(_SERVICES, "undecided")),
    "only_host_labels": ModeCase(expected=dict.fromkeys(_SERVICES, "undecided")),
    # §10.5 in its sharper form, which §10.5 records as pinned nowhere else: driven on a host with
    # **no** changed service at all, the mode still retargets every row, because
    # `_get_table_target`'s UPDATE_SERVICE_LABELS arm returns `update_target` for every source but
    # `ignored` and never reads the `update_source="changed"` its caller transmits. Three
    # undecided services are therefore adopted into monitoring. Driving it from a *monitored*
    # baseline would assert nothing at all -- `unchanged -> unchanged` is a no-op today and after
    # the fix alike, and the cell would survive a mutant that made the mode do nothing. The fix
    # keys off `update_source`, at which point these rows stay `undecided` and this cell goes
    # red: intended, since §10.5 lands before the refactoring starts.
    "only_service_labels": ModeCase(expected=dict.fromkeys(_SERVICES, "monitored")),
}


@pytest.mark.parametrize("mode", _MODE_CASES)
def test_mode_parity(central_site: Site, remote_site: Site, mode: str) -> None:
    """Each of the seven modes REST publishes leaves the same result on either site.

    This is the acceptance criterion's "every action is exercised against a host on a remote
    site". Parity is established **at equal versions**: both sites run the same build here, so
    B-F2.3's version-truncated `DiscoveryResult` wire format never fires and this says nothing
    about the supported one-minor-version skew.

    Each mode's baseline and expected phases live together in `_MODE_CASES`; the two `BULK_UPDATE`
    modes carry a row the mode must leave untouched, so the cell fails for a mode that stops
    honouring its `update_source` rather than only for one that stops working.
    """
    case = _MODE_CASES[mode]
    with _host_pair(
        central_site, remote_site, f"mode-{mode.replace('_', '-')}", services=case.services
    ) as pair:
        after: dict[str, dict[str, str]] = {}
        for host in pair:
            if case.baseline is not None:
                case.baseline(central_site, host)
            _run_mode(central_site, host.name, mode)
            after[host.name] = _discovered_services(central_site, host.name)

        central_host, remote_host = pair
        assert after[central_host.name] == after[remote_host.name], (
            f"mode {mode!r} did not agree across the two sites"
        )
        assert after[central_host.name] == dict(case.expected), (
            f"mode {mode!r} left phases the tier does not expect, on both sites alike"
        )


def test_autochecks_written_on_the_owning_site(central_site: Site, remote_site: Site) -> None:
    """`fix_all` writes the autochecks file on the site that owns the host, and nowhere else.

    Direct regression test for the hackathon PoC's worst defect, an apply path that was
    unconditionally local. Its own tests could not have caught it: patching
    `local_discovery_preview` in the central process does not skip the remote branch, it silently
    replaces it with the local one (B-F1), because the remote branch reaches that function only
    via `do_remote_automation` -> `AutomationServiceDiscoveryJob` -> `execute_discovery_job`.

    The evidence is the file's *content*, not the fact that it changed. §10.8 has `fix_all`
    rewriting the autochecks with an empty diff on any host carrying an active, custom, enforced
    or clustered row, so "the file changed" is supplied by that write whether or not a service
    moved. Expect the no-op half of that to disappear when §10.8 lands.
    """
    with _host_pair(central_site, remote_site, "autochecks") as pair:
        central_host, remote_host = pair
        for host in pair:
            assert not host.site.file_exists(host.autochecks), (
                f"{host.name} already has an autochecks file before anything was applied"
            )

        for host in pair:
            _run_mode(central_site, host.name, "fix_all")
            assert _autocheck_items(host) == set(_SERVICES), (
                f"{host.name}'s autochecks on site {host.site.id} do not hold the services"
            )

        assert not central_site.file_exists(remote_host.autochecks), (
            "the remote host's autochecks were written on the central site"
        )
        assert not remote_site.file_exists(central_host.autochecks), (
            "the central host's autochecks were written on the remote site"
        )


def test_disabled_services_rule_is_central_and_reaches_the_remote(
    central_site: Site, remote_site: Site
) -> None:
    """Disabling a remote host's service writes a central rule that the remote then honours.

    Two observations, not one. B-F2.5: `EnabledDisabledServicesEditor` writes `ignored_services`
    into the **central** WATO config, so for a remote host one logical operation spans both sites.
    B-F2.1: the remote's *preview* reflects the rule from the moment a read pre-syncs the central
    configuration across -- the read *is* the sync -- while its *monitoring* only reflects it
    after activation, because `sync_changes_before_remote_automation` drives the activation
    machinery with `prevent_activate=True` and the remote core is never reloaded. The two
    therefore cannot be tested as one before/after contrast.

    What this must **not** assert is that the remote's autochecks file stops holding the service.
    Today it does not (§10.1), for a reason that has nothing to do with remoteness; the
    characterization below records that instead of the intended behaviour.

    No `refresh` runs between the write and the read, on purpose: `get_result` prefers a stored
    preview over recomputing and `_store_last_preview` runs only at the end of a scan, so a
    refresh here would hand back a preview computed *before* the rule existed -- a second way for
    this test to fail that has nothing to do with inotify (§6.1 B-F2.1).

    Incidentally the only end-to-end exercise of the two halves of B-F2.5 and of B-F4:
    `_save_service_enable_disable_rules` asks the **remote** for the service's labels
    (`get_services_labels`) and the **central** site whether a host-specific rule is still needed
    (`analyze_service_rule_matches`, which hard-codes `LocalAutomationConfig()` by design). Step 3
    below is where that arithmetic decides something -- it is what makes the emptied rule be
    deleted rather than left behind with no service patterns.

    Four observations in one test rather than four: each one is a precondition of the next -- the
    reverse direction needs the rule that the forward direction wrote, and the "not yet in
    monitoring" observation is only meaningful before the activation that the last one needs. The
    numbered blocks are where a failure localizes.
    """
    service = _SUBJECT
    with _host_pair(central_site, remote_site, "disabled") as (_central_host, remote_host):
        _run_mode(central_site, remote_host.name, "fix_all")
        central_site.openapi.changes.activate_and_wait_for_completion()
        _wait_for_monitoring(remote_site, remote_host.name, service, present=True)

        rules_before = set(central_site.openapi.rules.get_all_names("ignored_services"))
        _update_phase(central_site, remote_host.name, service, "ignored")

        # 1. The rule is central configuration, even though the host is not.
        new_rules = [
            rule
            for rule in central_site.openapi.rules.get_all("ignored_services")
            if rule["id"] not in rules_before
        ]
        assert len(new_rules) == 1, "disabling a remote host's service wrote no central rule"
        conditions = new_rules[0]["extensions"]["conditions"]
        assert conditions["host_name"]["match_on"] == [remote_host.name], (
            "the generated rule is not scoped to the host it was issued for"
        )

        # 2. The remote honours it in the preview, before any activation.
        _wait_for_phase(central_site, remote_host.name, service, "ignored")
        # ... but monitoring does not, because a sync is not an activation.
        assert service in _monitored_services(remote_site, remote_host.name)
        # §10.1: the disabled service stays in the autochecks file. Characterization, not intent.
        assert service in _autocheck_items(remote_host)

        central_site.openapi.changes.activate_and_wait_for_completion()
        _wait_for_monitoring(remote_site, remote_host.name, service, present=False)

        # 3. The reverse direction: `ignored -> unchanged` takes the rule away again.
        _update_phase(central_site, remote_host.name, service, "monitored")
        assert set(central_site.openapi.rules.get_all_names("ignored_services")) == rules_before, (
            "re-enabling the service left the generated rule behind"
        )
        _wait_for_phase(central_site, remote_host.name, service, "monitored")


# target phase, baseline mode, expected phase afterwards. Each case is chosen so that the
# transition is a real one on both sites: `monitored` starts from an undecided row, the rest from
# a monitored one. `removed` on a still-discovered service is an invalid transition (A2's ✗ cell)
# that drops the autochecks entry, and since the agent still reports the service the classifier
# hands it back as `undecided`.
_PHASE_CASES = (
    ("monitored", None, "monitored"),
    ("undecided", "fix_all", "undecided"),
    ("ignored", "fix_all", "ignored"),
    ("removed", "fix_all", "undecided"),
)


@pytest.mark.parametrize(
    "target_phase, baseline, expected", _PHASE_CASES, ids=[case[0] for case in _PHASE_CASES]
)
def test_update_service_phase_parity(
    central_site: Site,
    remote_site: Site,
    target_phase: str,
    baseline: str | None,
    expected: str,
) -> None:
    """The second entry point into the state machine behaves the same on either site.

    **Asserts a positive change per site, never equality alone.** §10.19: an identifier naming no
    service on the host is answered `204` with nothing written, so a typo in this fixture -- or an
    item spelling that has drifted from the agent output -- would leave both sites untouched and
    "identical result" would still hold. Note which half of that is the hazard: an identifier that
    matches one host and not the other is the benign case, because one side writes, the other
    answers `204`, and the assertion goes red. It is the identifier matching *neither* that passes
    while proving nothing.

    The transition *semantics* are not this tier's to pin -- Tier 1 sweeps all 225 cells of A2 --
    so `expected` is here only to make "something changed" a specific claim. What no lower level
    can catch is that the change happened on the site that owns the host.
    """
    slug = f"phase-{target_phase}"
    with _host_pair(central_site, remote_site, slug) as pair:
        before: dict[str, str] = {}
        after: dict[str, str] = {}
        for host in pair:
            if baseline is not None:
                _run_mode(central_site, host.name, baseline)
            before[host.name] = _discovered_services(central_site, host.name)[_SUBJECT]
            _update_phase(central_site, host.name, _SUBJECT, target_phase)
            # `ignored` is the one target whose phase waits on a rule reaching the owning site;
            # the others follow the autochecks file, which is already written. Waiting for all
            # four keeps that from being a per-target special case, and costs nothing where the
            # value has already settled.
            _wait_for_phase(central_site, host.name, _SUBJECT, expected)
            after[host.name] = _discovered_services(central_site, host.name)[_SUBJECT]

        for host in pair:
            assert before[host.name] != after[host.name], (
                f"nothing changed on {host.name} (site {host.site.id}): the write was accepted and "
                f"discarded, so equality across the sites would prove nothing"
            )
            assert after[host.name] == expected, (
                f"{_SUBJECT} on {host.name} moved to {after[host.name]!r}, not {expected!r}"
            )

        central_host, remote_host = pair
        assert after[central_host.name] == after[remote_host.name], (
            f"target {target_phase!r} did not agree across the two sites"
        )


def test_refresh_and_tabula_rasa_parity(central_site: Site, remote_site: Site) -> None:
    """The scanning modes run on the owning site, report status centrally, and only one files a
    change.

    B-F2.2: the `refresh-autochecks` change is added by `get_check_table` *before* the local/remote
    branch and for `TABULA_RASA` only. So it appears in the central change list for a host whose
    scan and whose autochecks rewrite both happened on the remote, where
    `_perform_automatic_refresh` records nothing -- an acknowledged TODO. The central entry is the
    only audit trail there is, and it says nothing about what actually changed.

    That the central site can see the remote job's state at all is `job_snapshot` crossing the
    boundary through `fetch_service_discovery_background_job_status`; the same call is what makes
    the `execute` endpoint's `409` guard work remotely.
    """
    with _host_pair(central_site, remote_site, "scan") as pair:
        for host in pair:
            _run_mode(central_site, host.name, "refresh")
            # `run_discovery_and_wait_for_completion` already waited for `finished`, so re-asking
            # for the state would assert nothing new. The job's own progress log is the
            # non-redundant evidence: for the remote host it can only have got here through
            # `fetch_service_discovery_background_job_status`.
            assert _job_progress(central_site, host.name), (
                f"no progress log came back for {host.name} on site {host.site.id}"
            )
            assert not _has_pending_change(central_site, "refresh-autochecks", host.name), (
                "`refresh` filed a `refresh-autochecks` change"
            )
        refreshed = {host.name: _discovered_services(central_site, host.name) for host in pair}

        for host in pair:
            _run_mode(central_site, host.name, "tabula_rasa")
            assert _job_progress(central_site, host.name), (
                f"no progress log came back for {host.name} on site {host.site.id}"
            )
            assert _has_pending_change(central_site, "refresh-autochecks", host.name), (
                f"`tabula_rasa` on {host.name} filed no `refresh-autochecks` change centrally"
            )
        rediscovered = {host.name: _discovered_services(central_site, host.name) for host in pair}

        central_host, remote_host = pair
        assert refreshed[central_host.name] == refreshed[remote_host.name]
        assert refreshed[central_host.name] == dict.fromkeys(_SERVICES, "undecided")
        assert rediscovered[central_host.name] == rediscovered[remote_host.name]
        assert rediscovered[central_host.name] == dict.fromkeys(_SERVICES, "monitored")


def test_host_label_parity(central_site: Site, remote_site: Site) -> None:
    """`only_host_labels` writes the discovered host labels on the site that owns the host.

    Unaffected by §10.5: the mode maps to `UPDATE_HOST_LABELS`, which `perform_host_label_discovery`
    serves without ever constructing `Discovery`, so it never reaches `_get_table_target` where
    §10.5 lives. The service rows are asserted to stay put for exactly that reason.
    """
    with _host_pair(central_site, remote_site, "labels") as pair:
        central_host, remote_host = pair
        for host in pair:
            assert not host.site.file_exists(host.discovered_host_labels), (
                f"{host.name} already has discovered host labels before the mode ran"
            )

        for host in pair:
            _run_mode(central_site, host.name, "only_host_labels")
            written = host.site.read_file(host.discovered_host_labels)
            assert _LABEL_NAME in written and _LABEL_VALUE in written, (
                f"{host.name}'s discovered host labels on site {host.site.id} lack the label"
            )
            assert set(_discovered_services(central_site, host.name).values()) == {"undecided"}, (
                f"the mode moved service rows on {host.name}"
            )

        assert not central_site.file_exists(remote_host.discovered_host_labels), (
            "the remote host's discovered host labels were written on the central site"
        )
        assert not remote_site.file_exists(central_host.discovered_host_labels), (
            "the central host's discovered host labels were written on the remote site"
        )

        labels = {host.name: _host_labels(central_site, host.name) for host in pair}
        assert labels[central_host.name] == labels[remote_host.name], (
            "the discovered host labels differ between the two sites"
        )
        assert labels[central_host.name][_LABEL_NAME] == _LABEL_VALUE


_CLUSTERED = _SERVICES[1]  # clustered, and nothing else -- reaches §10.17
_CLUSTERED_AND_DISABLED = _SERVICES[0]  # clustered *and* disabled -- reaches §10.13
_NODE_ONLY = _SERVICES[2]  # the control: discovered on the node and staying there


@contextmanager
def _remote_cluster(
    central_site: Site, remote_site: Site
) -> Iterator[tuple[ParityHost, ParityHost]]:
    """A cluster and its node, both on the remote site, carrying two defects at once.

    The fixture is built to reach §10.13 *and* §10.17, which need incompatible states of the same
    row and therefore get one service each:

    * `_CLUSTERED_AND_DISABLED` is matched by both a *Clustered services* and a *Disabled
      services* rule. The disabled rule carries **no host restriction** on purpose:
      `_node_service_source` tests it on the **cluster** while `appears_on_cluster` tests it on
      the **node**, and that asymmetry is what makes the common case the worst one.
    * `_CLUSTERED` is matched by the clustered rule alone, so it stays a `clustered_*` row and
      reaches `_case_clustered` rather than `_case_ignored`.

    Keeping both in one fixture is what §7 asks for, and it means the expectations here move
    twice: §10.17's fix depends on §10.13's landing first.
    """
    folder = "/sd_parity_cluster"
    node = ParityHost("sd-cluster-node", remote_site)
    cluster = ParityHost("sd-cluster", remote_site)
    central_site.openapi.folders.create(folder)
    try:
        central_site.openapi.hosts.create(
            node.name,
            folder=folder,
            attributes={"site": remote_site.id, "ipaddress": "127.0.0.1"},
        )
        response = central_site.openapi.post(
            "/domain-types/host_config/collections/clusters",
            json={
                "host_name": cluster.name,
                "folder": folder,
                "nodes": [node.name],
                "attributes": {"site": remote_site.id},
            },
        )
        assert response.status_code == 200, response.text

        node.site.makedirs(_AGENT_OUTPUT_DIR)
        node.site.write_file(node.agent_output, _agent_output())
        central_site.openapi.rules.create(
            ruleset_name="datasource_programs",
            value=_DATASOURCE_COMMAND,
            folder=folder,
            conditions={"host_name": {"match_on": [node.name], "operator": "one_of"}},
        )
        central_site.openapi.rules.create(
            ruleset_name="clustered_services",
            value=True,
            folder=folder,
            conditions={
                "host_name": {"match_on": [node.name], "operator": "one_of"},
                "service_description": {
                    "match_on": [f"{_CLUSTERED_AND_DISABLED}$", f"{_CLUSTERED}$"],
                    "operator": "one_of",
                },
            },
        )
        central_site.openapi.rules.create(
            ruleset_name="ignored_services",
            value=True,
            folder=folder,
            conditions={
                "service_description": {
                    "match_on": [f"{_CLUSTERED_AND_DISABLED}$"],
                    "operator": "one_of",
                }
            },
        )
        central_site.openapi.changes.activate_and_wait_for_completion()

        # The cluster has no data source of its own; its preview reads the nodes'. Scan both, as
        # §10.13's and §10.17's reproductions both do -- and read each one once afterwards, for
        # the reason `_host_pair` reads: `get_result` prefers the preview the scan stored and
        # `_load_last_preview` unlinks it, so the first read after a scan is answered from the
        # scan's table and only later ones recompute. Without this read the test's first look at
        # the cluster would be answered from a snapshot taken before it applied anything -- the
        # node would still have no autochecks there, putting the clustered service in `current`
        # with nothing in `preexisting`, so it would read `undecided` instead of `monitored`.
        for host, expected in ((node, set(_SERVICES)), (cluster, {_CLUSTERED})):
            _run_mode(central_site, host.name, "refresh")
            discovered = _discovered_services(central_site, host.name)
            assert expected <= set(discovered), (
                f"the fixture did not take on {host.name}: expected {sorted(expected)} in the "
                f"check table, found {sorted(discovered)}"
            )
        yield node, cluster
    finally:
        central_site.openapi.folders.delete(folder)
        central_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
        for path in (node.agent_output, node.autochecks, node.discovered_host_labels):
            if node.site.file_exists(path):
                node.site.delete_file(path)


def test_clustered_services_on_a_remote_cluster(central_site: Site, remote_site: Site) -> None:
    """Node-table handling for a cluster whose nodes live on the remote site, end to end.

    This is one of the axes that cannot be exercised with a single host (§2.4), and it is the test
    most likely to be written from §11's intended model instead of today's behaviour -- so each
    block below says which of the two it asserts.

    Two of the three blocks are **characterizations of known defects** and are expected to change:

    * §10.13 -- `_node_service_source` returns plain `ignored` instead of `clustered_ignored` for
      a service that is both clustered and disabled, dead since `692c918bf86` (2021) reverted werk
      7128. The node files it under the generic "Disabled services" group, with bulk actions
      enabled, and the cluster does not show it at all.
    * §10.17 -- targeting `ignored` on a `clustered_*` row **from the node** is accepted where the
      GUI documents it as impossible, and then does nothing: `_case_clustered` omits the entry from
      the autochecks it computes, but the write path puts it back, so the only lasting effects are
      a pending change and a core reload for a host where nothing changed. Expected behaviour is a
      rejection.

    One test rather than three because the fixture is the expensive part -- a cluster, a node, two
    scans and an activation -- and all three blocks read the same table. They stay ordered because
    the §10.17 block activates and reloads the remote core.
    """
    with _remote_cluster(central_site, remote_site) as (node, cluster):
        # `fix_all` on the node: `clustered_new` is retargeted to `unchanged` (A1-F1 -- `FIX_ALL`
        # peels off only `vanished` and `ignored`), which writes the clustered entry into the
        # node's autochecks, while the disabled row is left where it is.
        _run_mode(central_site, node.name, "fix_all")
        node_phases = _discovered_services(central_site, node.name)
        cluster_phases = _discovered_services(central_site, cluster.name)

        # Intended behaviour, and the reason the fixture exists: the cluster owns the clustered
        # service, the node reports it as belonging elsewhere, and the node keeps its own.
        assert node_phases[_CLUSTERED] == "clustered_monitored", (
            f"the node reports {_CLUSTERED} as {node_phases[_CLUSTERED]!r}, not as belonging to "
            f"the cluster"
        )
        assert node_phases[_NODE_ONLY] == "monitored"
        assert cluster_phases[_CLUSTERED] == "monitored", (
            f"the cluster reports {_CLUSTERED} as {cluster_phases.get(_CLUSTERED)!r}; a stale "
            f"stored preview would read `undecided` here"
        )
        assert _NODE_ONLY not in cluster_phases, "an unclustered service reached the cluster"
        assert _autocheck_items(node) == {_CLUSTERED, _NODE_ONLY}, (
            "the node's autochecks do not hold the cluster's service and its own"
        )

        # §10.13, characterization: `clustered_ignored` has had no producer since 2021, so the
        # row arrives as plain `ignored` and reaches `_case_ignored` rather than `_case_clustered`.
        assert node_phases[_CLUSTERED_AND_DISABLED] == "ignored", (
            f"the node reports {_CLUSTERED_AND_DISABLED} as "
            f"{node_phases[_CLUSTERED_AND_DISABLED]!r} -- if this is now `clustered_ignored`, "
            f"§10.13 has been fixed and this characterization should be deleted"
        )
        # On the cluster the same service is either absent or shown as vanished, depending on
        # whether a stale autocheck remains; there is none here, so it is simply missing. The one
        # thing it must not be is monitored -- that would mean the disable had no effect at all.
        assert cluster_phases.get(_CLUSTERED_AND_DISABLED) in (None, "vanished"), (
            f"the cluster monitors {_CLUSTERED_AND_DISABLED} despite the disabled-services rule"
        )

        central_site.openapi.changes.activate_and_wait_for_completion()
        _wait_for_monitoring(remote_site, cluster.name, _CLUSTERED, present=True)

        # §10.17, characterization. Expected: a rejection. Actual: `204`, and then nothing --
        # `_case_clustered` leaves the entry out of the autochecks it computes, but
        # `set_autochecks_for_effective_host` carries over every existing entry whose effective
        # host differs from the one being written (`autochecks_owner=node`,
        # `effective_host=node`), and a clustered service's effective host is the *cluster*. So the
        # omission never reaches the file. What does survive is the noise: `apply_changes` fires on
        # the source/target mismatch, so `_save_services` files a `set-autochecks` change and calls
        # the automation for a host whose autochecks come out unchanged.
        rules_before = set(central_site.openapi.rules.get_all_names("ignored_services"))
        _update_phase(central_site, node.name, _CLUSTERED, "ignored")
        assert _autocheck_items(node) == {_CLUSTERED, _NODE_ONLY}, (
            "the clustered entry no longer survives the write -- §10.17 has changed severity, and "
            "the disable now takes effect on the cluster instead of being a silent no-op"
        )
        assert set(central_site.openapi.rules.get_all_names("ignored_services")) == rules_before, (
            "a disabled-services rule was written -- `_case_clustered` has no `add_disabled_rule` "
            "parameter, so §10.17 has changed"
        )
        # The one lasting effect, and the evidence that the request was accepted rather than
        # rejected: without this the two assertions above would also hold for a `400`.
        assert _has_pending_change(central_site, "set-autochecks", node.name), (
            "no `set-autochecks` change was filed, so the write path did not run at all"
        )

        central_site.openapi.changes.activate_and_wait_for_completion()
        # Deliberately the same expectation as before the update: activating the change the
        # no-op filed must not take the service off the cluster either.
        _wait_for_monitoring(remote_site, cluster.name, _CLUSTERED, present=True)
