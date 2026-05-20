#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager

from livestatus import SiteConfiguration, SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.script_helpers import gui_context
from cmk.gui.watolib.audit_log import AuditLogStore, make_audit_log_change_hook
from cmk.gui.watolib.objref import ObjectRef, ObjectRefType
from cmk.gui.watolib.pending_changes import (
    _ScopeKind,
    Change,
    ChangeEvent,
    ChangeScope,
    NoopPendingChangesStore,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.sidebar_reload import (
    is_sidebar_reload_needed,
    sidebar_reload_change_hook,
)


def _site_config() -> SiteConfiguration:
    return SiteConfiguration(
        alias="",
        disable_wato=False,
        disabled=False,
        id=SiteId("x"),
        insecure=False,
        is_trusted=False,
        message_broker_port=5672,
        multisiteurl="",
        persist=False,
        proxy=None,
        replicate_ec=False,
        replicate_mkps=False,
        replication=None,
        socket=("local", None),
        status_host=None,
        timeout=5,
        url_prefix="/x/",
        user_login=True,
        user_attribute_sync_connections="all",
    )


class _RecordingStore(PendingChangesStore):
    """Captures appends so tests can assert on the per-site record."""

    def __init__(self) -> None:
        self.appended: list[tuple[SiteId, dict[str, object]]] = []

    def append(self, site_id: SiteId, entry: Mapping[str, object]) -> None:
        self.appended.append((site_id, dict(entry)))


def _default_request() -> Change:
    return Change(
        action_name="test-action",
        text="Did a thing",
        domains=["check_mk"],
    )


def _pending_changes(
    *,
    activation_site_ids: Iterable[str] = ("local", "remote"),
    local_site: str = "local",
    store: PendingChangesStore | None = None,
    hooks: tuple[Callable[[ChangeEvent], None], ...] = (),
) -> tuple[PendingChanges, _RecordingStore]:
    captured = store if isinstance(store, _RecordingStore) else _RecordingStore()
    return (
        PendingChanges(
            activation_sites=SiteConfigurations(
                {SiteId(i): _site_config() for i in activation_site_ids}
            ),
            local_site=SiteId(local_site),
            acting_user=UserId("calvin"),
            store=store if store is not None else captured,
            hooks=hooks,
        ),
        captured,
    )


@contextmanager
def _audit_log_cleanup() -> Iterator[None]:
    try:
        yield
    finally:
        AuditLogStore()._path.unlink(missing_ok=True)


def test_change_scope_all_activation_sites() -> None:
    scope = ChangeScope.all_activation_sites()
    assert scope.kind is _ScopeKind.ALL_ACTIVATION_SITES
    assert scope.explicit_sites == frozenset()


def test_change_scope_explicit_sites() -> None:
    scope = ChangeScope.sites([SiteId("a"), SiteId("b")])
    assert scope.kind is _ScopeKind.EXPLICIT_SITES
    assert scope.explicit_sites == frozenset({SiteId("a"), SiteId("b")})


def test_change_scope_local_site() -> None:
    scope = ChangeScope.local_site()
    assert scope.kind is _ScopeKind.LOCAL_SITE


def test_all_activation_sites_writes_every_site() -> None:
    pending_changes, store = _pending_changes(activation_site_ids=("a", "b", "c"))
    pending_changes.add(_default_request(), ChangeScope.all_activation_sites())
    assert {site for site, _ in store.appended} == {
        SiteId("a"),
        SiteId("b"),
        SiteId("c"),
    }


def test_local_site_writes_only_local() -> None:
    pending_changes, store = _pending_changes(
        activation_site_ids=("local", "remote"), local_site="local"
    )
    pending_changes.add(_default_request(), ChangeScope.local_site())
    assert {site for site, _ in store.appended} == {SiteId("local")}


def test_explicit_sites_intersects_with_activation_sites() -> None:
    pending_changes, store = _pending_changes(activation_site_ids=("a", "b", "c"))
    pending_changes.add(_default_request(), ChangeScope.sites([SiteId("a"), SiteId("b")]))
    assert {site for site, _ in store.appended} == {SiteId("a"), SiteId("b")}


def test_explicit_sites_with_unknown_site_falls_back_to_local() -> None:
    # Mirrors the CMK-32211 fix: a caller-supplied site id that the local
    # instance does not know (e.g. a remote site name leaking through) must
    # not silently disappear — the local site is added so the change is
    # still logged.
    pending_changes, store = _pending_changes(
        activation_site_ids=("local", "known_remote"), local_site="local"
    )
    pending_changes.add(
        _default_request(),
        ChangeScope.sites([SiteId("known_remote"), SiteId("nonexistent")]),
    )
    assert {site for site, _ in store.appended} == {
        SiteId("known_remote"),
        SiteId("local"),
    }


def test_explicit_sites_all_unknown_writes_local_only() -> None:
    pending_changes, store = _pending_changes(
        activation_site_ids=("local", "known"), local_site="local"
    )
    pending_changes.add(
        _default_request(),
        ChangeScope.sites([SiteId("ghost1"), SiteId("ghost2")]),
    )
    assert {site for site, _ in store.appended} == {SiteId("local")}


def test_record_required_fields_present() -> None:
    pending_changes, store = _pending_changes(activation_site_ids=("a",))
    pending_changes.add(
        Change(
            action_name="create-host",
            text="Created host node1",
            domains=["check_mk", "multisite"],
            object_ref=ObjectRef(ObjectRefType.Host, "node1"),
            diff_text="diff",
        ),
        ChangeScope.all_activation_sites(),
    )
    _, entry = store.appended[0]
    assert entry["action_name"] == "create-host"
    assert entry["text"] == "Created host node1"
    assert entry["domains"] == ["check_mk", "multisite"]
    assert entry["object"] == ObjectRef(ObjectRefType.Host, "node1")
    assert entry["diff_text"] == "diff"
    assert entry["user_id"] == UserId("calvin")
    assert isinstance(entry["id"], str)
    assert isinstance(entry["time"], float)


def test_record_force_flags_default_to_none() -> None:
    pending_changes, store = _pending_changes(activation_site_ids=("a",))
    pending_changes.add(_default_request(), ChangeScope.all_activation_sites())
    _, entry = store.appended[0]
    assert entry["force_sync"] is None
    assert entry["force_restart"] is None
    assert entry["force_apache_reload"] is False


def test_record_force_flags_passed_through_verbatim() -> None:
    pending_changes, store = _pending_changes(activation_site_ids=("a",))
    pending_changes.add(
        Change(
            action_name="test-action",
            text="Did a thing",
            domains=["check_mk"],
            force_sync=True,
            force_restart=False,
            force_apache_reload=True,
        ),
        ChangeScope.all_activation_sites(),
    )
    _, entry = store.appended[0]
    assert entry["force_sync"] is True
    assert entry["force_restart"] is False
    assert entry["force_apache_reload"] is True


def test_record_has_been_activated_not_written() -> None:
    # New schema: has_been_activated is recomputed at read time, never
    # stored. Old field name must not appear in fresh records.
    pending_changes, store = _pending_changes(activation_site_ids=("a",))
    pending_changes.add(_default_request(), ChangeScope.all_activation_sites())
    _, entry = store.appended[0]
    assert "has_been_activated" not in entry


def test_record_same_change_id_across_all_affected_sites() -> None:
    pending_changes, store = _pending_changes(activation_site_ids=("a", "b", "c"))
    pending_changes.add(_default_request(), ChangeScope.all_activation_sites())
    ids = {entry["id"] for _, entry in store.appended}
    assert len(ids) == 1


def test_record_separate_add_calls_produce_distinct_ids() -> None:
    pending_changes, store = _pending_changes(activation_site_ids=("a",))
    pending_changes.add(_default_request(), ChangeScope.all_activation_sites())
    pending_changes.add(_default_request(), ChangeScope.all_activation_sites())
    ids = [entry["id"] for _, entry in store.appended]
    assert len(set(ids)) == 2


def test_hooks_fire_in_registration_order() -> None:
    order: list[str] = []
    pending_changes, _ = _pending_changes(
        activation_site_ids=("a",),
        hooks=(
            lambda _ev: order.append("first"),
            lambda _ev: order.append("second"),
            lambda _ev: order.append("third"),
        ),
    )
    pending_changes.add(_default_request(), ChangeScope.all_activation_sites())
    assert order == ["first", "second", "third"]


def test_hooks_receive_change_event() -> None:
    captured: list[ChangeEvent] = []
    pending_changes, _ = _pending_changes(activation_site_ids=("a", "b"), hooks=(captured.append,))
    request = Change(action_name="x", text="Did a thing", domains=["check_mk"])
    pending_changes.add(request, ChangeScope.all_activation_sites())
    assert len(captured) == 1
    assert captured[0].request is request
    assert captured[0].user_id == UserId("calvin")
    assert captured[0].affected_sites == frozenset({SiteId("a"), SiteId("b")})


def test_hooks_fire_after_store_append() -> None:
    observation: list[str] = []

    class TracingStore(PendingChangesStore):
        def append(self, site_id: SiteId, entry: Mapping[str, object]) -> None:
            observation.append("store")

    def hook(_ev: ChangeEvent) -> None:
        observation.append("hook")

    pending_changes, _ = _pending_changes(
        activation_site_ids=("a",), store=TracingStore(), hooks=(hook,)
    )
    pending_changes.add(_default_request(), ChangeScope.all_activation_sites())
    assert observation == ["store", "hook"]


def test_noop_store_discards_all_writes() -> None:
    # Build a NoopPendingChangesStore directly to confirm it silently
    # accepts and drops writes.
    store = NoopPendingChangesStore()
    store.append(
        SiteId("a"),
        {
            "id": "x",
            "action_name": "t",
            "text": "t",
            "object": None,
            "user_id": None,
            "domains": [],
            "time": 0.0,
            "force_sync": None,
            "force_restart": None,
            "force_apache_reload": False,
            "domain_settings": {},
            "prevent_discard_changes": False,
            "diff_text": None,
        },
    )


def test_noop_store_does_not_suppress_hooks() -> None:
    # Suppressing the on-disk write does not suppress hooks — callers who
    # want full silence pass empty hooks too.
    fired: list[ChangeEvent] = []
    pending_changes = PendingChanges(
        activation_sites=SiteConfigurations({SiteId("a"): _site_config()}),
        local_site=SiteId("a"),
        acting_user=UserId("calvin"),
        store=NoopPendingChangesStore(),
        hooks=(fired.append,),
    )
    pending_changes.add(_default_request(), ChangeScope.all_activation_sites())
    assert len(fired) == 1


def test_audit_log_change_hook_forwards_action_message_user_and_diff() -> None:
    with _audit_log_cleanup(), gui_context():
        hook = make_audit_log_change_hook(use_git=False)
        hook(
            ChangeEvent(
                request=Change(
                    action_name="audit-action",
                    text="audit message",
                    domains=["check_mk"],
                    diff_text="some-diff",
                ),
                user_id=UserId("calvin"),
                affected_sites=frozenset({SiteId("a")}),
            )
        )
        entries = list(AuditLogStore().read())
    assert len(entries) == 1
    assert entries[0].action == "audit-action"
    assert entries[0].text == "audit message"
    assert entries[0].user_id == "calvin"
    assert entries[0].diff_text == "some-diff"


def test_audit_log_change_hook_forwards_object_ref() -> None:
    with _audit_log_cleanup(), gui_context():
        hook = make_audit_log_change_hook(use_git=False)
        ref = ObjectRef(ObjectRefType.Host, "node1")
        hook(
            ChangeEvent(
                request=Change(
                    action_name="test-action",
                    text="Did a thing",
                    domains=["check_mk"],
                    object_ref=ref,
                ),
                user_id=UserId("calvin"),
                affected_sites=frozenset({SiteId("a")}),
            )
        )
        entries = list(AuditLogStore().read())
    assert entries[0].object_ref == ref


def test_sidebar_reload_change_hook_marks_sidebar_for_reload() -> None:
    with gui_context():
        assert not is_sidebar_reload_needed()
        sidebar_reload_change_hook(
            ChangeEvent(
                request=_default_request(),
                user_id=UserId("calvin"),
                affected_sites=frozenset({SiteId("a")}),
            )
        )
        assert is_sidebar_reload_needed()
