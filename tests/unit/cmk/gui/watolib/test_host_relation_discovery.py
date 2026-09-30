#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import replace
from typing import cast, override

import pytest

import cmk.ruleset_matcher.tags
import cmk.utils.paths
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.config import get_default_config, make_config_object
from cmk.gui.i18n import _l
from cmk.gui.logged_in import LoggedInSuperUser, LoggedInUser, UserDefaultConfig
from cmk.gui.utils.host_relation_kinds import (
    DirectedRelationKind,
    NameEvidence,
    RELATION_KINDS,
    RelationEnd,
    RelationKind,
)
from cmk.gui.utils.host_relations import RelationDirection, RelationLink, relations_or_empty
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.host_attributes import HostAttributes, HostContactGroupSpec
from cmk.gui.watolib.host_relation_discovery import (
    discover_relations,
    Evidence,
    Finding,
    HostPair,
    link_relations,
    LinkOutcome,
    MarkedValue,
    NameReason,
    NamesTellApart,
    NameWords,
    outcome_counts,
    Proposals,
    propose_relations,
    relation_to_find,
    RelationEntry,
    RelationToFind,
    run_summary,
    scan_for_evidence,
    ScannedHost,
    Scope,
    SharedAttribute,
    SharedLabel,
    suggest_evidence,
    Suggestions,
    ValueExample,
    ValueReason,
    ValueTellsApart,
)
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree, Host, make_folder_tree
from cmk.gui.watolib.pending_changes import (
    NoopPendingChangesStore,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.site_changes import ChangeSpec
from cmk.livestatus_client import SiteConfigurations
from cmk.utils.redis import disable_redis

_SUPERUSER = LoggedInSuperUser()


def _scanned(name: str, *, labels: dict[str, str] | None = None, **attributes: str) -> ScannedHost:
    return ScannedHost(
        name=HostName(name),
        labels=labels or {},
        attributes=cast("HostAttributes", attributes),
    )


def _evidence(
    *,
    shared: SharedLabel | SharedAttribute | None = None,
    relations: Mapping[str, Sequence[str]] | None = None,
    kinds: Mapping[str, RelationKind] = RELATION_KINDS,
) -> Evidence:
    """What a scan is asked for, by the words the kinds under test declare themselves.

    A user names the relations to look for and what to look for them by; a test that is not
    about that answer asks for what the kinds it hands in stand for, with ``shared`` given to
    every one of them.
    """
    words = (
        relations
        if relations is not None
        else {
            kind_id: evidence.tokens
            for kind_id, kind in kinds.items()
            if (evidence := kind.name_evidence) is not None
        }
    )
    return _findings(
        [
            (kind_id, RelationToFind(marker=NameWords(tuple(spelled)), shared=shared))
            for kind_id, spelled in words.items()
        ]
    )


def _findings(relations: Sequence[tuple[str, RelationToFind]]) -> Evidence:
    """What a scan is asked for, one finding per entry, in this order."""
    return Evidence(
        findings=[
            Finding(id=f"finding-{at}", kind_id=kind_id, found_by=found_by)
            for at, (kind_id, found_by) in enumerate(relations)
        ]
    )


def _found(
    hosts: Sequence[ScannedHost],
    *,
    shared: SharedLabel | SharedAttribute | None = None,
    relations: Mapping[str, Sequence[str]] | None = None,
    kinds: Mapping[str, RelationKind] = RELATION_KINDS,
) -> Proposals:
    return propose_relations(
        hosts, evidence=_evidence(shared=shared, relations=relations, kinds=kinds), kinds=kinds
    )


def _proposed(
    hosts: Sequence[ScannedHost],
    *,
    shared: SharedLabel | SharedAttribute | None = None,
    relations: Mapping[str, Sequence[str]] | None = None,
    kinds: Mapping[str, RelationKind] = RELATION_KINDS,
) -> list[tuple[str, str]]:
    return [
        (str(proposal.pair.source), str(proposal.pair.target))
        for proposal in _found(hosts, shared=shared, relations=relations, kinds=kinds).pairs
    ]


def _questioned(
    hosts: Sequence[ScannedHost],
    *,
    shared: SharedLabel | SharedAttribute | None = None,
    kinds: Mapping[str, RelationKind] = RELATION_KINDS,
) -> list[list[str]]:
    return [
        [str(member) for member in question.members]
        for question in _found(hosts, shared=shared, kinds=kinds).groups
    ]


def _management_kind_spelled(
    *tokens: str, direction: RelationDirection = "parent"
) -> Mapping[str, RelationKind]:
    """The one kind there is, as a later version might declare it to be recognised.

    Stands in for the kind that does not exist yet: a pair may only name a relation this
    version knows, so extensibility is shown on the evidence rather than on a made-up id.
    """
    kind = RELATION_KINDS["management"]
    return {kind.id: replace(kind, name_evidence=NameEvidence(tokens=tokens, direction=direction))}


def _outcomes(entries: Sequence[RelationEntry]) -> list[tuple[str, str, LinkOutcome]]:
    return [(str(entry.pair.source), str(entry.pair.target), entry.outcome) for entry in entries]


@pytest.mark.parametrize(
    "name, expected",
    [
        pytest.param("srv-01-ilo", ("srv-01", "ilo"), id="token at the end"),
        pytest.param("ilo-srv-01", ("srv-01", "ilo"), id="token at the start"),
        pytest.param("idrac.srv-01", ("srv-01", "idrac"), id="token as the first label"),
        pytest.param("srv_01_ilo", ("srv_01", "ilo"), id="underscores"),
        pytest.param("srv_01-ilo", ("srv_01", "ilo"), id="mixed separators"),
        pytest.param("SRV-01-ILO", ("SRV-01", "ILO"), id="upper case"),
        pytest.param("srv-01-idrac", ("srv-01", "idrac"), id="a token that ends in another"),
        pytest.param(
            "srv-01-ilo.example.com",
            ("srv-01.example.com", "ilo"),
            id="a domain stays where it is",
        ),
        pytest.param(
            "srv-01.ilo.example.com",
            ("srv-01.example.com", "ilo"),
            id="a management domain",
        ),
        pytest.param(
            "srv-01.mgmt.example.com",
            ("srv-01.example.com", "mgmt"),
            id="a management domain of another name",
        ),
    ],
)
def test_a_board_name_leads_to_the_host_it_belongs_to(name: str, expected: tuple[str, str]) -> None:
    base, _word = expected

    assert _proposed([_scanned(name), _scanned(base)]) == [(name, base)]


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("srv-01", id="no token at all"),
        pytest.param("ilonka-01", id="a token inside a word"),
        pytest.param("srv-01-ilo2", id="a token a word begins with"),
        pytest.param("ilo", id="nothing but the token"),
        pytest.param("srv-01.example.com", id="a plain fully qualified name"),
    ],
)
def test_a_name_that_says_nothing_about_a_board_belongs_to_nobody(name: str) -> None:
    partners = [
        _scanned(other) for other in ("srv-01", "01", "srv", "example.com") if other != name
    ]

    assert _proposed([_scanned(name), *partners]) == []


def test_a_board_is_proposed_for_the_host_it_shares_a_domain_with() -> None:
    assert _proposed([_scanned("srv-01.example.com"), _scanned("srv-01.ilo.example.com")]) == [
        ("srv-01.ilo.example.com", "srv-01.example.com")
    ]


def test_a_board_is_proposed_for_the_host_its_name_is_derived_from() -> None:
    assert _proposed([_scanned("srv-01"), _scanned("srv-01-ilo")]) == [("srv-01-ilo", "srv-01")]


def test_a_board_whose_host_is_not_in_setup_is_not_proposed() -> None:
    assert _proposed([_scanned("srv-01-ilo"), _scanned("gateway")]) == []


def test_nothing_is_proposed_from_a_shared_value_that_was_not_asked_for() -> None:
    assert (
        _proposed(
            [
                _scanned("bmc-77", labels={"cmdb/serial": "5XJ9K2"}),
                _scanned("blade-77", labels={"cmdb/serial": "5XJ9K2"}),
            ]
        )
        == []
    )


def test_a_shared_label_pairs_two_hosts_that_no_name_derives_from_the_other() -> None:
    assert _proposed(
        [
            _scanned("bmc-77", labels={"cmdb/serial": "5XJ9K2"}),
            _scanned("blade-77", labels={"cmdb/serial": "5XJ9K2"}),
        ],
        shared=SharedLabel("cmdb/serial"),
    ) == [("bmc-77", "blade-77")]


def test_a_shared_attribute_reads_the_same_way() -> None:
    assert _proposed(
        [
            _scanned("bmc-77", cmdb_serial="5XJ9K2"),
            _scanned("blade-77", cmdb_serial="5XJ9K2"),
        ],
        shared=SharedAttribute("cmdb_serial"),
    ) == [("bmc-77", "blade-77")]


def test_one_board_is_proposed_for_every_host_sharing_its_value() -> None:
    assert _proposed(
        [
            _scanned("chassis-bmc", labels={"chassis": "a"}),
            _scanned("blade-1", labels={"chassis": "a"}),
            _scanned("blade-2", labels={"chassis": "a"}),
            _scanned("blade-3", labels={"chassis": "b"}),
        ],
        shared=SharedLabel("chassis"),
    ) == [("chassis-bmc", "blade-1"), ("chassis-bmc", "blade-2")]


def test_a_value_shared_by_two_boards_is_neither_paired_nor_asked_about() -> None:
    found = _found(
        [
            _scanned("chassis-bmc", labels={"chassis": "a"}),
            _scanned("blade-1-ilo", labels={"chassis": "a"}),
            _scanned("blade-1", labels={"chassis": "a"}),
            _scanned("blade-2", labels={"chassis": "a"}),
        ],
        shared=SharedLabel("chassis"),
    )

    assert (found.pairs, found.groups) == ([], [])


def test_hosts_sharing_a_value_with_no_board_among_them_are_asked_about() -> None:
    hosts = [
        _scanned("srv-01", labels={"cmdb/serial": "5XJ9K2"}),
        _scanned("srv-02", labels={"cmdb/serial": "5XJ9K2"}),
    ]

    assert _proposed(hosts, shared=SharedLabel("cmdb/serial")) == []
    assert _questioned(hosts, shared=SharedLabel("cmdb/serial")) == [["srv-01", "srv-02"]]


def test_a_whole_group_with_no_board_among_it_is_one_question() -> None:
    hosts = [
        _scanned(name, labels={"chassis": "9Z4T2"})
        for name in ("srv-01", "srv-02", "srv-03", "srv-04")
    ]

    assert _questioned(hosts, shared=SharedLabel("chassis")) == [
        ["srv-01", "srv-02", "srv-03", "srv-04"]
    ]


def test_a_host_carrying_a_value_nobody_else_carries_is_no_question() -> None:
    assert (
        _questioned(
            [_scanned("srv-01", labels={"cmdb/serial": "5XJ9K2"})],
            shared=SharedLabel("cmdb/serial"),
        )
        == []
    )


def test_a_group_a_name_settles_is_not_asked_about() -> None:
    hosts = [
        _scanned("blade-77", labels={"cmdb/serial": "5XJ9K2"}),
        _scanned("bmc-77", labels={"cmdb/serial": "5XJ9K2"}),
    ]

    assert _questioned(hosts, shared=SharedLabel("cmdb/serial")) == []


def test_a_question_names_the_end_the_answer_would_sit_at() -> None:
    (question,) = _found(
        [
            _scanned("srv-01", labels={"cmdb/serial": "5XJ9K2"}),
            _scanned("srv-02", labels={"cmdb/serial": "5XJ9K2"}),
        ],
        shared=SharedLabel("cmdb/serial"),
    ).groups

    assert (question.kind_id, question.direction) == ("management", "parent")
    assert (
        question.evidence
        == 'All of them carry the host label "cmdb/serial" with the value "5XJ9K2".'
    )


def test_a_kind_that_is_not_discovered_at_all_is_not_asked_about_either() -> None:
    kind = RELATION_KINDS["management"]

    assert (
        _questioned(
            [
                _scanned("srv-01", labels={"cmdb/serial": "5XJ9K2"}),
                _scanned("srv-02", labels={"cmdb/serial": "5XJ9K2"}),
            ],
            shared=SharedLabel("cmdb/serial"),
            kinds={kind.id: replace(kind, name_evidence=None)},
        )
        == []
    )


def test_a_word_a_user_added_is_read_out_of_host_names() -> None:
    hosts = [_scanned("srv-01"), _scanned("srv-01-oob")]

    assert _proposed(hosts) == []
    assert _proposed(hosts, relations={"management": ["ilo", "oob"]}) == [("srv-01-oob", "srv-01")]


def test_only_the_words_a_user_gave_are_read_out_of_host_names() -> None:
    hosts = [_scanned("srv-01"), _scanned("srv-01-ilo"), _scanned("srv-02"), _scanned("srv-02-oob")]

    assert _proposed(hosts, relations={"management": ["oob"]}) == [("srv-02-oob", "srv-02")]


def test_a_relation_not_asked_for_is_not_read_from_host_names() -> None:
    assert _proposed([_scanned("srv-01"), _scanned("srv-01-ilo")], relations={}) == []


def test_a_relation_not_asked_for_is_not_asked_about_either() -> None:
    """A scan offers the relations the user asked for, and a question is one of its offers."""
    assert not _found(
        [
            _scanned("srv-01", labels={"cmdb/serial": "5XJ9K2"}),
            _scanned("srv-02", labels={"cmdb/serial": "5XJ9K2"}),
        ],
        shared=SharedLabel("cmdb/serial"),
        relations={},
    ).groups


def _a_second_kind() -> RelationKind:
    """A relation this version does not have, to show two of them side by side.

    Only questions are shown on it: a pair may only name a relation this version knows.
    """
    return DirectedRelationKind(
        id="clustering",
        title=_l("Clustering"),
        parent=RelationEnd(row=_l("is cluster node of"), noun=_l("Cluster node")),
        child=RelationEnd(row=_l("is cluster of"), noun=_l("Cluster")),
        name_evidence=NameEvidence(tokens=("node",), direction="parent"),
    )


def test_each_relation_reads_the_shared_value_it_was_given() -> None:
    """The value says the hosts are one machine; which relation that makes of them is the row."""
    found = propose_relations(
        [
            _scanned("box-a", labels={"cmdb/box": "BX-1"}),
            _scanned("box-b", labels={"cmdb/box": "BX-1"}),
            _scanned("rack-a", labels={"cmdb/rack": "R-7"}),
            _scanned("rack-b", labels={"cmdb/rack": "R-7"}),
        ],
        evidence=_findings(
            [
                (
                    "management",
                    RelationToFind(marker=NameWords(("ilo",)), shared=SharedLabel("cmdb/box")),
                ),
                (
                    "clustering",
                    RelationToFind(marker=NameWords(("node",)), shared=SharedLabel("cmdb/rack")),
                ),
            ]
        ),
        kinds={**RELATION_KINDS, "clustering": _a_second_kind()},
    )

    assert sorted(
        (group.kind_id, tuple(str(member) for member in group.members)) for group in found.groups
    ) == [
        ("clustering", ("rack-a", "rack-b")),
        ("management", ("box-a", "box-b")),
    ]


def test_a_marked_host_is_the_one_at_the_deciding_end() -> None:
    """The CMDB case: the serial number pairs them, the mark says which of them is the board."""
    found = propose_relations(
        [
            _scanned("w-4711", labels={"cmdb/sn": "S-1", "cmdb/kind": "server"}),
            _scanned("w-4712", labels={"cmdb/sn": "S-1", "cmdb/kind": "board"}),
        ],
        evidence=_findings(
            [
                (
                    "management",
                    RelationToFind(
                        marker=MarkedValue(where=SharedLabel("cmdb/kind"), value="board"),
                        shared=SharedLabel("cmdb/sn"),
                    ),
                )
            ]
        ),
    )

    assert found.groups == []
    assert [(str(proposal.pair.source), str(proposal.pair.target)) for proposal in found.pairs] == [
        ("w-4712", "w-4711")
    ]


def test_a_custom_host_attribute_marks_an_end_the_same_way() -> None:
    found = propose_relations(
        [
            _scanned("w-4711", cmdb_sn="S-1"),
            _scanned("w-4712", cmdb_sn="S-1", cmdb_kind="board"),
        ],
        evidence=_findings(
            [
                (
                    "management",
                    RelationToFind(
                        marker=MarkedValue(where=SharedAttribute("cmdb_kind"), value="board"),
                        shared=SharedAttribute("cmdb_sn"),
                    ),
                )
            ]
        ),
    )

    assert [(str(proposal.pair.source), str(proposal.pair.target)) for proposal in found.pairs] == [
        ("w-4712", "w-4711")
    ]


def test_a_relation_marked_by_a_value_is_not_read_out_of_host_names() -> None:
    """A mark says which host is which, nothing about what the other host is called."""
    assert not _found(
        [_scanned("srv-01"), _scanned("srv-01-ilo")],
        relations={},
    ).pairs


def test_hosts_nothing_marks_are_asked_about_rather_than_paired() -> None:
    found = propose_relations(
        [
            _scanned("w-4711", labels={"cmdb/sn": "S-1"}),
            _scanned("w-4712", labels={"cmdb/sn": "S-1"}),
        ],
        evidence=_findings([("management", RelationToFind(shared=SharedLabel("cmdb/sn")))]),
    )

    assert found.pairs == []
    assert [tuple(str(member) for member in group.members) for group in found.groups] == [
        ("w-4711", "w-4712")
    ]


def test_a_group_is_asked_about_once_per_relation_that_asked_for_a_shared_value() -> None:
    """A relation going by names alone does not get to ask about a value it never read."""
    found = propose_relations(
        [
            _scanned("box-a", labels={"cmdb/box": "BX-1"}),
            _scanned("box-b", labels={"cmdb/box": "BX-1"}),
        ],
        evidence=_findings(
            [
                (
                    "management",
                    RelationToFind(marker=NameWords(("ilo",)), shared=SharedLabel("cmdb/box")),
                ),
                ("clustering", RelationToFind(marker=NameWords(("node",)))),
            ]
        ),
        kinds={**RELATION_KINDS, "clustering": _a_second_kind()},
    )

    assert [group.kind_id for group in found.groups] == ["management"]


def test_a_pair_both_readings_find_is_proposed_once() -> None:
    hosts = [
        _scanned("srv-01", labels={"cmdb/serial": "5XJ9K2"}),
        _scanned("srv-01-ilo", labels={"cmdb/serial": "5XJ9K2"}),
    ]

    assert _proposed(hosts, shared=SharedLabel("cmdb/serial")) == [("srv-01-ilo", "srv-01")]


def test_the_name_is_what_a_proposal_says_it_was_found_by() -> None:
    (proposal,) = _found([_scanned("srv-01"), _scanned("srv-01-ilo")]).pairs

    assert proposal.evidence == 'The name is "srv-01" with "ilo" added.'


def test_a_shared_value_names_the_label_the_value_and_the_word_that_found_the_board() -> None:
    (proposal,) = _found(
        [
            _scanned("bmc-77", labels={"cmdb/serial": "5XJ9K2"}),
            _scanned("blade-77", labels={"cmdb/serial": "5XJ9K2"}),
        ],
        shared=SharedLabel("cmdb/serial"),
    ).pairs

    assert proposal.evidence == (
        'Both carry the host label "cmdb/serial" with the value "5XJ9K2".'
        ' "bmc-77" has "bmc" in its name.'
    )


def test_a_shared_value_names_the_mark_that_found_the_board() -> None:
    (proposal,) = propose_relations(
        [
            _scanned("w-4711", labels={"cmdb/sn": "S-1", "cmdb/kind": "server"}),
            _scanned("w-4712", labels={"cmdb/sn": "S-1", "cmdb/kind": "board"}),
        ],
        evidence=_findings(
            [
                (
                    "management",
                    RelationToFind(
                        marker=MarkedValue(where=SharedLabel("cmdb/kind"), value="board"),
                        shared=SharedLabel("cmdb/sn"),
                    ),
                )
            ]
        ),
    ).pairs

    assert proposal.evidence == (
        'Both carry the host label "cmdb/sn" with the value "S-1".'
        ' "w-4712" carries the host label "cmdb/kind" with the value "board".'
    )


def test_the_names_a_relation_is_found_by_are_the_ones_its_kind_declares() -> None:
    hosts = [_scanned("srv-01"), _scanned("srv-01-sp"), _scanned("srv-02"), _scanned("srv-02-ilo")]

    assert _proposed(hosts, kinds=_management_kind_spelled("sp")) == [("srv-01-sp", "srv-01")]


def test_the_end_a_found_host_sits_at_is_the_one_its_kind_declares() -> None:
    (proposal,) = _found(
        [_scanned("srv-01"), _scanned("srv-01-ilo")],
        kinds=_management_kind_spelled("ilo", direction="child"),
    ).pairs

    assert proposal.pair.source_direction == "child"


def test_a_kind_that_declares_no_names_is_not_discovered() -> None:
    kind = RELATION_KINDS["management"]

    assert (
        _proposed(
            [_scanned("srv-01"), _scanned("srv-01-ilo")],
            kinds={kind.id: replace(kind, name_evidence=None)},
        )
        == []
    )


def test_a_pair_names_the_relation_the_way_the_wire_spells_it() -> None:
    pair = HostPair(
        source=HostName("srv-01-ilo"),
        target=HostName("srv-01"),
        kind_id="management",
        source_direction="parent",
    )

    assert pair.choice_name == "management_parent"


def test_a_pair_of_a_host_with_itself_is_refused() -> None:
    with pytest.raises(ValueError, match="itself"):
        HostPair(
            source=HostName("srv-01"),
            target=HostName("srv-01"),
            kind_id="management",
            source_direction="parent",
        )


def test_a_pair_naming_an_end_the_relation_does_not_have_is_refused() -> None:
    with pytest.raises(ValueError, match="symmetric"):
        HostPair(
            source=HostName("srv-01-ilo"),
            target=HostName("srv-01"),
            kind_id="management",
            source_direction="symmetric",
        )


@pytest.fixture(name="tree")
def _tree() -> Iterator[FolderTree]:
    # Built explicitly rather than through the request-global folder_tree(), so that no Flask
    # request context is needed - the same way test_hosts_and_folders.py builds one.
    cmk.utils.paths.profile_dir.mkdir(parents=True, exist_ok=True)
    raw_config = get_default_config()
    raw_config["tags"] = cmk.ruleset_matcher.tags.get_effective_tag_config(raw_config["wato_tags"])
    with disable_redis():
        tree = make_folder_tree(make_config_object(raw_config))
        tree.invalidate_caches()

    yield tree

    shutil.rmtree(tree.root_folder().filesystem_path(), ignore_errors=True)
    os.makedirs(tree.root_folder().filesystem_path())


def _noop_pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=NoopPendingChangesStore(),
        hooks=(make_audit_log_change_hook(use_git=False),),
    )


def _create_host(folder: Folder, name: str, attributes: HostAttributes | None = None) -> Host:
    folder.create_hosts(
        [(HostName(name), attributes or HostAttributes(), [])],
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    return folder.hosts()[HostName(name)]


def _create_other_half(
    folder: Folder, name: str, board: str, *, labels: Mapping[str, str] | None = None
) -> Host:
    """A host holding its half of a relation to a board that does not exist yet, so that the
    board, created afterwards, holds none - the way a hand written "hosts.mk" can leave it."""
    host = _create_host(folder, name, HostAttributes({"labels": dict(labels or {})}))
    host.attributes["relations"] = [
        {"kind": "management", "direction": "child", "host": HostName(board)}
    ]
    folder.save_hosts(pprint_value=False, acting_user=_SUPERUSER)
    return host


def _contact_groups(*names: str) -> HostContactGroupSpec:
    return HostContactGroupSpec(
        groups=list(names),
        recurse_perms=False,
        use=False,
        use_for_services=False,
        recurse_use=False,
    )


def _user_of_one_contact_group(
    contact_group: str, *, sees_all_folders: bool = True
) -> LoggedInUser:
    user_ = LoggedInUser(
        None,
        UserPermissions({}, {}, {}, []),
        defaults=UserDefaultConfig(
            users={}, default_language="en", default_show_mode="default_show_less"
        ),
        explicitly_given_permissions=frozenset(
            {
                "wato.use",
                "wato.edit",
                "wato.edit_hosts",
                "wato.manage_hosts",
                "wato.manage_folders",
                *(["wato.see_all_folders"] if sees_all_folders else []),
            }
        ),
    )
    user_.attributes["contactgroups"] = [contact_group]
    return user_


def test_a_scan_reads_every_host_of_setup(tree: FolderTree) -> None:
    root = tree.root_folder()
    for name in ("srv-01", "srv-01-ilo", "gateway"):
        _create_host(root, name)

    found = discover_relations(tree, evidence=_evidence(), acting_user=_SUPERUSER)

    assert found.hosts_scanned == 3
    assert _outcomes(found.entries) == [("srv-01-ilo", "srv-01", LinkOutcome.LINK)]


def test_a_label_setup_holds_pairs_two_hosts(tree: FolderTree) -> None:
    root = tree.root_folder()
    for name in ("blade-77", "bmc-77"):
        _create_host(root, name, HostAttributes({"labels": {"cmdb/serial": "5XJ9K2"}}))
    tree.invalidate_caches()

    found = discover_relations(
        tree,
        evidence=_evidence(shared=SharedLabel("cmdb/serial")),
        acting_user=_SUPERUSER,
    )

    assert _outcomes(found.entries) == [("bmc-77", "blade-77", LinkOutcome.LINK)]


def test_a_group_nothing_settles_is_handed_on_as_a_question(tree: FolderTree) -> None:
    root = tree.root_folder()
    for name in ("srv-01", "srv-02"):
        _create_host(root, name, HostAttributes({"labels": {"cmdb/serial": "5XJ9K2"}}))
    tree.invalidate_caches()

    found = discover_relations(
        tree,
        evidence=_evidence(shared=SharedLabel("cmdb/serial")),
        acting_user=_SUPERUSER,
    )

    (question,) = found.groups
    assert found.entries == []
    assert question.outcome is LinkOutcome.UNDECIDED
    assert question.settled is None
    assert question.refusals == {}


def test_a_group_a_run_has_answered_is_not_asked_again(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_host(root, "srv-01", HostAttributes({"labels": {"cmdb/serial": "5XJ9K2"}}))
    _create_host(
        root,
        "srv-02",
        HostAttributes(
            {
                "labels": {"cmdb/serial": "5XJ9K2"},
                "relations": [
                    {"kind": "management", "direction": "parent", "host": HostName("srv-01")}
                ],
            }
        ),
    )
    tree.invalidate_caches()

    (question,) = discover_relations(
        tree,
        evidence=_evidence(shared=SharedLabel("cmdb/serial")),
        acting_user=_SUPERUSER,
    ).groups

    assert question.outcome is LinkOutcome.ALREADY_LINKED
    assert question.settled == HostName("srv-02")


def test_a_group_whose_members_hold_only_the_other_half_is_not_asked_again(
    tree: FolderTree,
) -> None:
    root = tree.root_folder()
    _create_other_half(root, "srv-01", "srv-02", labels={"cmdb/serial": "5XJ9K2"})
    _create_host(root, "srv-02", HostAttributes({"labels": {"cmdb/serial": "5XJ9K2"}}))
    tree.invalidate_caches()

    (question,) = discover_relations(
        tree,
        evidence=_evidence(shared=SharedLabel("cmdb/serial")),
        acting_user=_SUPERUSER,
    ).groups

    assert question.settled == HostName("srv-02")


def test_a_member_of_a_group_that_cannot_be_written_cannot_be_named(tree: FolderTree) -> None:
    parent = tree.root_folder().create_subfolder(
        "parent",
        "Parent",
        HostAttributes({"contactgroups": _contact_groups("cg")}),
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    own = parent.create_subfolder(
        "own",
        "Own",
        HostAttributes(),
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    other = parent.create_subfolder(
        "other",
        "Other",
        HostAttributes({"contactgroups": _contact_groups("another_cg")}),
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    _create_host(own, "srv-01", HostAttributes({"labels": {"cmdb/serial": "5XJ9K2"}}))
    _create_host(
        other,
        "srv-02",
        HostAttributes(
            {"labels": {"cmdb/serial": "5XJ9K2"}, "contactgroups": _contact_groups("cg")}
        ),
    )
    tree.invalidate_caches()

    (question,) = discover_relations(
        tree,
        evidence=_evidence(shared=SharedLabel("cmdb/serial")),
        acting_user=_user_of_one_contact_group("cg"),
    ).groups

    assert set(question.refusals) == {HostName("srv-01"), HostName("srv-02")}


def test_a_relation_that_is_already_stored_is_reported_as_such(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_host(root, "srv-01")
    _create_host(
        root,
        "srv-01-ilo",
        HostAttributes(
            {
                "relations": [
                    {"kind": "management", "direction": "parent", "host": HostName("srv-01")}
                ]
            }
        ),
    )
    tree.invalidate_caches()

    found = discover_relations(tree, evidence=_evidence(), acting_user=_SUPERUSER)

    assert _outcomes(found.entries) == [("srv-01-ilo", "srv-01", LinkOutcome.ALREADY_LINKED)]


def test_a_relation_only_its_target_holds_is_reported_as_stored(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_other_half(root, "srv-01", "srv-01-ilo")
    _create_host(root, "srv-01-ilo")
    tree.invalidate_caches()

    found = discover_relations(tree, evidence=_evidence(), acting_user=_SUPERUSER)

    assert _outcomes(found.entries) == [("srv-01-ilo", "srv-01", LinkOutcome.ALREADY_LINKED)]


def test_a_pair_the_user_cannot_write_is_reported_instead_of_offered(tree: FolderTree) -> None:
    parent = tree.root_folder().create_subfolder(
        "parent",
        "Parent",
        HostAttributes({"contactgroups": _contact_groups("cg")}),
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    own = parent.create_subfolder(
        "own",
        "Own",
        HostAttributes(),
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    other = parent.create_subfolder(
        "other",
        "Other",
        HostAttributes({"contactgroups": _contact_groups("another_cg")}),
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    _create_host(own, "srv-01")
    _create_host(other, "srv-01-ilo", HostAttributes({"contactgroups": _contact_groups("cg")}))
    tree.invalidate_caches()

    found = discover_relations(
        tree, evidence=_evidence(), acting_user=_user_of_one_contact_group("cg")
    )

    assert _outcomes(found.entries) == [("srv-01-ilo", "srv-01", LinkOutcome.NOT_WRITABLE)]
    assert found.entries[0].detail == 'No permission to edit the hosts in the folder "Other".'


def _subfolder(parent: Folder, name: str, attributes: HostAttributes | None = None) -> Folder:
    return parent.create_subfolder(
        name,
        name.title(),
        attributes or HostAttributes(),
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )


def _folder_of_its_own(tree: FolderTree, name: str, contact_group: str) -> Folder:
    return _subfolder(
        tree.root_folder(), name, HostAttributes({"contactgroups": _contact_groups(contact_group)})
    )


def test_a_host_the_user_may_not_edit_is_reported_instead_of_offered(tree: FolderTree) -> None:
    folder = _folder_of_its_own(tree, "open", "cg")
    _create_host(folder, "srv-01-ilo")
    _create_host(folder, "srv-01", HostAttributes({"contactgroups": _contact_groups("other_cg")}))
    tree.invalidate_caches()

    found = discover_relations(
        tree, evidence=_evidence(), acting_user=_user_of_one_contact_group("cg")
    )

    assert _outcomes(found.entries) == [("srv-01-ilo", "srv-01", LinkOutcome.NOT_WRITABLE)]
    assert found.entries[0].detail == 'No permission to edit the host "srv-01".'


def test_a_member_the_user_may_not_edit_cannot_be_named(tree: FolderTree) -> None:
    folder = _folder_of_its_own(tree, "open", "cg")
    for name in ("srv-01", "srv-02"):
        _create_host(folder, name, HostAttributes({"labels": {"cmdb/serial": "5XJ9K2"}}))
    _create_host(
        folder,
        "srv-03",
        HostAttributes(
            {"labels": {"cmdb/serial": "5XJ9K2"}, "contactgroups": _contact_groups("other_cg")}
        ),
    )
    tree.invalidate_caches()

    (question,) = discover_relations(
        tree,
        evidence=_evidence(shared=SharedLabel("cmdb/serial")),
        acting_user=_user_of_one_contact_group("cg"),
    ).groups

    assert set(question.refusals) == {
        HostName("srv-01"),
        HostName("srv-02"),
        HostName("srv-03"),
    }


def test_a_scan_reads_no_host_of_a_folder_the_user_may_not_see(tree: FolderTree) -> None:
    """The discovery names hosts; it must not name one the folder view would hide."""
    _create_host(_folder_of_its_own(tree, "own", "cg"), "srv-01")
    _create_host(_folder_of_its_own(tree, "other", "another_cg"), "srv-01-ilo")
    tree.invalidate_caches()

    found = discover_relations(
        tree,
        evidence=_evidence(),
        acting_user=_user_of_one_contact_group("cg", sees_all_folders=False),
    )

    assert (found.hosts_scanned, found.entries) == (1, [])


def test_the_suggestions_name_no_host_of_a_folder_the_user_may_not_see(tree: FolderTree) -> None:
    _create_host(_folder_of_its_own(tree, "own", "cg"), "srv-01")
    _create_host(_folder_of_its_own(tree, "other", "another_cg"), "srv-01-ilo")
    tree.invalidate_caches()

    suggested = scan_for_evidence(
        tree,
        attribute_names=[],
        acting_user=_user_of_one_contact_group("cg", sees_all_folders=False),
    )

    assert (suggested.hosts_scanned, suggested.words) == (1, [])


def test_a_folder_scope_finds_the_relations_with_one_host_in_it(tree: FolderTree) -> None:
    """The boards have a folder of their own; the hosts they manage are found wherever they are."""
    root = tree.root_folder()
    _create_host(_subfolder(root, "oob"), "srv-01-ilo")
    _create_host(_subfolder(root, "dc1"), "srv-01")
    _create_host(root, "srv-02-ilo")
    _create_host(root, "srv-02")
    tree.invalidate_caches()

    found = discover_relations(
        tree, evidence=_evidence(), acting_user=_SUPERUSER, scope=Scope(folder="oob")
    )

    assert _outcomes(found.entries) == [("srv-01-ilo", "srv-01", LinkOutcome.LINK)]


def test_a_folder_scope_takes_in_its_subfolders(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_host(_subfolder(_subfolder(root, "oob"), "rack1"), "srv-01-ilo")
    _create_host(root, "srv-01")
    tree.invalidate_caches()

    found = discover_relations(
        tree, evidence=_evidence(), acting_user=_SUPERUSER, scope=Scope(folder="oob")
    )

    assert _outcomes(found.entries) == [("srv-01-ilo", "srv-01", LinkOutcome.LINK)]


def test_a_site_scope_finds_the_relations_with_one_host_on_it(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_host(root, "srv-01-ilo", HostAttributes({"site": SiteId("remote")}))
    _create_host(root, "srv-01")
    _create_host(root, "srv-02-ilo")
    _create_host(root, "srv-02")
    tree.invalidate_caches()

    found = discover_relations(
        tree, evidence=_evidence(), acting_user=_SUPERUSER, scope=Scope(site=SiteId("remote"))
    )

    assert _outcomes(found.entries) == [("srv-01-ilo", "srv-01", LinkOutcome.LINK)]


def _chassis_across_three_folders(tree: FolderTree, *, stored: bool = False) -> None:
    """A chassis with its board in /oob and a blade each in /dc1 and /dc2."""
    root = tree.root_folder()
    labels = {"asset/chassis": "CH-1"}
    board = HostAttributes({"labels": labels})
    if stored:
        board["relations"] = [
            {"kind": "management", "direction": "parent", "host": HostName("blade-1")}
        ]
    _create_host(_subfolder(root, "dc1"), "blade-1", HostAttributes({"labels": labels}))
    _create_host(_subfolder(root, "dc2"), "blade-2", HostAttributes({"labels": labels}))
    _create_host(_subfolder(root, "oob"), "chassis-1", board)
    tree.invalidate_caches()


def test_a_host_named_from_outside_the_scope_is_related_only_to_the_members_inside(
    tree: FolderTree,
) -> None:
    """Every relation an answer stores has a host in scope, as the scope promises."""
    _chassis_across_three_folders(tree)

    (question,) = discover_relations(
        tree,
        evidence=_evidence(shared=SharedLabel("asset/chassis")),
        acting_user=_SUPERUSER,
        scope=Scope(folder="dc1"),
    ).groups

    assert question.proposal.partners(HostName("chassis-1")) == [HostName("blade-1")]


def test_a_group_whose_relations_in_scope_are_stored_is_not_asked_again(tree: FolderTree) -> None:
    _chassis_across_three_folders(tree, stored=True)

    (question,) = discover_relations(
        tree,
        evidence=_evidence(shared=SharedLabel("asset/chassis")),
        acting_user=_SUPERUSER,
        scope=Scope(folder="dc1"),
    ).groups

    assert question.settled == HostName("chassis-1")


def test_a_folder_removed_before_the_scan_holds_nothing(tree: FolderTree) -> None:
    _create_host(tree.root_folder(), "srv-01-ilo")
    _create_host(tree.root_folder(), "srv-01")
    tree.invalidate_caches()

    found = discover_relations(
        tree, evidence=_evidence(), acting_user=_SUPERUSER, scope=Scope(folder="gone")
    )

    assert (found.hosts_scanned, found.entries) == (0, [])


def test_a_scan_counts_the_hosts_of_its_scope(tree: FolderTree) -> None:
    """The hosts elsewhere are read as the other end, but what was looked at is the scope."""
    root = tree.root_folder()
    _create_host(_subfolder(root, "oob"), "srv-01-ilo")
    _create_host(root, "srv-01")
    _create_host(root, "srv-02")
    tree.invalidate_caches()

    found = discover_relations(
        tree, evidence=_evidence(), acting_user=_SUPERUSER, scope=Scope(folder="oob")
    )

    assert found.hosts_scanned == 1


def test_the_suggestions_count_the_hosts_of_their_scope(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_host(_subfolder(root, "oob"), "srv-01-ilo")
    _create_host(root, "srv-01")
    _create_host(root, "srv-02")
    tree.invalidate_caches()

    suggested = scan_for_evidence(
        tree, attribute_names=[], acting_user=_SUPERUSER, scope=Scope(folder="oob")
    )

    assert suggested.hosts_scanned == 1


def test_the_suggestions_count_only_the_pairs_a_scope_takes_in(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_host(_subfolder(root, "oob"), "srv-01-ilo")
    for name in ("srv-01", "srv-02-ilo", "srv-02", "srv-03-ilo", "srv-03"):
        _create_host(root, name)
    tree.invalidate_caches()

    suggested = scan_for_evidence(
        tree, attribute_names=[], acting_user=_SUPERUSER, scope=Scope(folder="oob")
    )

    assert [(finding.word, finding.pairs) for finding in suggested.words] == [("ilo", 1)]


def test_the_suggestions_count_only_the_values_a_scope_takes_in(tree: FolderTree) -> None:
    oob = _subfolder(tree.root_folder(), "oob")
    for serial in range(1, 7):
        labels = HostAttributes({"labels": {"cmdb/sn": f"S-{serial}"}})
        _create_host(oob if serial <= 3 else tree.root_folder(), f"w-{serial}a", labels)
        _create_host(tree.root_folder(), f"w-{serial}b", labels)
    tree.invalidate_caches()

    suggested = scan_for_evidence(
        tree,
        attribute_names=[],
        acting_user=_SUPERUSER,
        in_names=False,
        scope=Scope(folder="oob"),
    )

    assert [(finding.where, finding.groups) for finding in suggested.values] == [
        (SharedLabel("cmdb/sn"), 3)
    ]


def test_a_conflict_one_of_whose_claims_is_stored_is_not_asked_again(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_host(
        root, "srv-01", HostAttributes({"labels": {"cmdb/sn": "S-1", "cmdb/kind": "board"}})
    )
    _create_host(root, "srv-01-ilo", HostAttributes({"labels": {"cmdb/sn": "S-1"}}))
    evidence = _findings(
        [
            ("management", RelationToFind(marker=NameWords(("ilo",)))),
            (
                "management",
                RelationToFind(
                    marker=MarkedValue(where=SharedLabel("cmdb/kind"), value="board"),
                    shared=SharedLabel("cmdb/sn"),
                ),
            ),
        ]
    )
    (conflict,) = discover_relations(tree, evidence=evidence, acting_user=_SUPERUSER).conflicts
    by_name = next(claim for claim in conflict.claims if claim.finding == "finding-0")
    link_relations(
        [by_name.pair],
        tree,
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
        progress=lambda _entry: None,
    )

    again = discover_relations(tree, evidence=evidence, acting_user=_SUPERUSER)

    assert again.conflicts == []
    assert _outcomes(again.entries) == [("srv-01-ilo", "srv-01", LinkOutcome.ALREADY_LINKED)]


class _RecordingPendingChangesStore(PendingChangesStore):
    def __init__(self, recorded: list[ChangeSpec]) -> None:
        self._recorded = recorded

    @override
    def append(self, site_id: SiteId, entry: ChangeSpec) -> None:
        self._recorded.append(entry)


def _recording_pending_changes(recorded: list[ChangeSpec]) -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("NO_SITE"),
        acting_user=None,
        store=_RecordingPendingChangesStore(recorded),
        hooks=(make_audit_log_change_hook(use_git=False),),
    )


def _accept_everything(
    tree: FolderTree,
    *,
    acting_user: LoggedInUser = _SUPERUSER,
    pending_changes: PendingChanges | None = None,
) -> Sequence[RelationEntry]:
    """Store what a scan just found, the way the page does after the user confirms it."""
    found = discover_relations(tree, evidence=_evidence(), acting_user=acting_user)
    return link_relations(
        [entry.pair for entry in found.entries if entry.outcome is LinkOutcome.LINK],
        tree,
        pprint_value=False,
        pending_changes=pending_changes or _noop_pending_changes(),
        acting_user=acting_user,
        progress=lambda _entry: None,
    )


def _stored_relations(tree: FolderTree, host_name: str) -> Sequence[RelationLink]:
    """What the tree says this host's relations are, rather than what one folder instance of
    it is left holding in memory."""
    host = tree.host(HostName(host_name))
    assert host is not None
    return relations_or_empty(host.attributes.get("relations", []))


def test_an_accepted_relation_is_stored_on_both_hosts(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_host(root, "srv-01")
    _create_host(root, "srv-01-ilo")

    _accept_everything(tree)

    assert _stored_relations(tree, "srv-01-ilo") == [
        {"kind": "management", "direction": "parent", "host": HostName("srv-01")}
    ]
    assert _stored_relations(tree, "srv-01") == [
        {"kind": "management", "direction": "child", "host": HostName("srv-01-ilo")}
    ]


def _changes_of(recorded: Sequence[ChangeSpec]) -> dict[str, list[ChangeSpec]]:
    """The recorded changes, per host they are logged under."""
    per_host: dict[str, list[ChangeSpec]] = {}
    for change in recorded:
        assert change["object"] is not None
        per_host.setdefault(change["object"].ident, []).append(change)
    return per_host


def _link(*pairs: tuple[str, str], tree: FolderTree, pending_changes: PendingChanges) -> None:
    link_relations(
        [
            HostPair(
                source=HostName(source),
                target=HostName(target),
                kind_id="management",
                source_direction="parent",
            )
            for source, target in pairs
        ],
        tree,
        pprint_value=False,
        pending_changes=pending_changes,
        acting_user=_SUPERUSER,
        progress=lambda _entry: None,
    )


def test_every_host_the_run_changed_is_logged_under_its_own_name(tree: FolderTree) -> None:
    root = tree.root_folder()
    for name in ("srv-01", "srv-01-ilo", "srv-02", "srv-02-ilo"):
        _create_host(root, name)
    recorded: list[ChangeSpec] = []

    _accept_everything(tree, pending_changes=_recording_pending_changes(recorded))

    assert sorted(_changes_of(recorded)) == ["srv-01", "srv-01-ilo", "srv-02", "srv-02-ilo"]


def test_a_board_several_pairs_change_is_logged_once(tree: FolderTree) -> None:
    root = tree.root_folder()
    for name in ("chassis-oa", "blade-1", "blade-2"):
        _create_host(root, name)
    recorded: list[ChangeSpec] = []

    _link(
        ("chassis-oa", "blade-1"),
        ("chassis-oa", "blade-2"),
        tree=tree,
        pending_changes=_recording_pending_changes(recorded),
    )

    assert len(_changes_of(recorded)["chassis-oa"]) == 1


def test_the_change_of_a_host_shows_every_relation_the_run_gave_it(tree: FolderTree) -> None:
    root = tree.root_folder()
    for name in ("chassis-oa", "blade-1", "blade-2"):
        _create_host(root, name)
    recorded: list[ChangeSpec] = []

    _link(
        ("chassis-oa", "blade-1"),
        ("chassis-oa", "blade-2"),
        tree=tree,
        pending_changes=_recording_pending_changes(recorded),
    )

    (change,) = _changes_of(recorded)["chassis-oa"]
    assert "blade-1" in str(change["diff_text"]) and "blade-2" in str(change["diff_text"])


def test_the_change_of_a_host_updates_it_and_its_counterparts(tree: FolderTree) -> None:
    root = tree.root_folder()
    for name in ("srv-01", "srv-01-ilo", "srv-02", "srv-02-ilo"):
        _create_host(root, name)
    recorded: list[ChangeSpec] = []

    _accept_everything(tree, pending_changes=_recording_pending_changes(recorded))

    (change,) = _changes_of(recorded)["srv-01"]
    assert sorted(change["domain_settings"]["check_mk"]["hosts_to_update"]) == [
        "srv-01",
        "srv-01-ilo",
    ]


def test_scanning_again_after_a_run_offers_nothing_further(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_host(root, "srv-01")
    _create_host(root, "srv-01-ilo")
    _accept_everything(tree)
    recorded: list[ChangeSpec] = []

    again = _accept_everything(tree, pending_changes=_recording_pending_changes(recorded))

    assert list(again) == []
    assert recorded == []
    assert _outcomes(
        discover_relations(tree, evidence=_evidence(), acting_user=_SUPERUSER).entries
    ) == [("srv-01-ilo", "srv-01", LinkOutcome.ALREADY_LINKED)]


def test_a_host_that_is_gone_by_the_time_the_run_starts_is_reported(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_host(root, "srv-01")

    done = link_relations(
        [
            HostPair(
                source=HostName("ghost"),
                target=HostName("srv-01"),
                kind_id="management",
                source_direction="parent",
            )
        ],
        tree,
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
        progress=lambda _entry: None,
    )

    assert _outcomes(done) == [("ghost", "srv-01", LinkOutcome.NOT_WRITABLE)]
    assert done[0].detail == "The host is gone."


def test_a_relation_only_its_target_holds_is_not_stored_again(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_other_half(root, "srv-01", "srv-01-ilo")
    _create_host(root, "srv-01-ilo")
    tree.invalidate_caches()

    done = link_relations(
        [
            HostPair(
                source=HostName("srv-01-ilo"),
                target=HostName("srv-01"),
                kind_id="management",
                source_direction="parent",
            )
        ],
        tree,
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
        progress=lambda _entry: None,
    )

    assert _outcomes(done) == [("srv-01-ilo", "srv-01", LinkOutcome.ALREADY_LINKED)]


def test_a_pair_that_cannot_be_written_leaves_the_others_stored(tree: FolderTree) -> None:
    root = tree.root_folder()
    open_folder = root.create_subfolder(
        "open",
        "Open",
        HostAttributes({"contactgroups": _contact_groups("cg")}),
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    closed = root.create_subfolder(
        "closed",
        "Closed",
        HostAttributes({"contactgroups": _contact_groups("another_cg")}),
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    _create_host(open_folder, "srv-01")
    _create_host(open_folder, "srv-01-ilo")
    _create_host(open_folder, "srv-02")
    _create_host(closed, "srv-02-ilo", HostAttributes({"contactgroups": _contact_groups("cg")}))
    tree.invalidate_caches()
    acting_user = _user_of_one_contact_group("cg")
    found = discover_relations(tree, evidence=_evidence(), acting_user=acting_user)

    done = link_relations(
        [entry.pair for entry in found.entries],
        tree,
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=acting_user,
        progress=lambda _entry: None,
    )

    assert sorted(_outcomes(done)) == [
        ("srv-01-ilo", "srv-01", LinkOutcome.LINK),
        ("srv-02-ilo", "srv-02", LinkOutcome.NOT_WRITABLE),
    ]
    assert _stored_relations(tree, "srv-01") == [
        {"kind": "management", "direction": "child", "host": HostName("srv-01-ilo")}
    ]
    assert _stored_relations(tree, "srv-02") == []


def test_a_pair_its_target_refuses_leaves_no_half_on_its_source(tree: FolderTree) -> None:
    folder = tree.root_folder().create_subfolder(
        "open",
        "Open",
        HostAttributes({"contactgroups": _contact_groups("cg")}),
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
    )
    for name in ("srv-01", "srv-01-ilo", "srv-02-ilo"):
        _create_host(folder, name)
    _create_host(folder, "srv-02", HostAttributes({"contactgroups": _contact_groups("other_cg")}))
    tree.invalidate_caches()

    done = link_relations(
        [
            HostPair(
                source=HostName(f"{name}-ilo"),
                target=HostName(name),
                kind_id="management",
                source_direction="parent",
            )
            for name in ("srv-02", "srv-01")
        ],
        tree,
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_user_of_one_contact_group("cg"),
        progress=lambda _entry: None,
    )

    assert _outcomes(done) == [
        ("srv-02-ilo", "srv-02", LinkOutcome.NOT_WRITABLE),
        ("srv-01-ilo", "srv-01", LinkOutcome.LINK),
    ]
    assert _stored_relations(tree, "srv-02-ilo") == []


def _entry(source: str, target: str, outcome: LinkOutcome) -> RelationEntry:
    return RelationEntry(
        pair=HostPair(
            source=HostName(source),
            target=HostName(target),
            kind_id="management",
            source_direction="parent",
        ),
        outcome=outcome,
    )


def test_every_outcome_is_counted_even_the_ones_with_no_entry() -> None:
    counts = outcome_counts([LinkOutcome.LINK, LinkOutcome.ALREADY_LINKED])

    assert counts == {
        LinkOutcome.LINK: 1,
        LinkOutcome.ALREADY_LINKED: 1,
        LinkOutcome.STORED_OTHERWISE: 0,
        LinkOutcome.NOT_WRITABLE: 0,
        LinkOutcome.UNDECIDED: 0,
    }


def test_a_summary_names_only_the_outcomes_the_run_had() -> None:
    assert run_summary([_entry("a-ilo", "a", LinkOutcome.LINK)]) == "1 stored"


def test_two_findings_of_one_relation_are_read_together() -> None:
    """Part of a fleet is named after its servers, part is only in the CMDB."""
    found = propose_relations(
        [
            _scanned("srv-01"),
            _scanned("srv-01-ilo"),
            _scanned("w-4711", labels={"cmdb/sn": "S-1"}),
            _scanned("w-4712", labels={"cmdb/sn": "S-1", "cmdb/kind": "board"}),
        ],
        evidence=_findings(
            [
                ("management", RelationToFind(marker=NameWords(("ilo",)))),
                (
                    "management",
                    RelationToFind(
                        marker=MarkedValue(where=SharedLabel("cmdb/kind"), value="board"),
                        shared=SharedLabel("cmdb/sn"),
                    ),
                ),
            ]
        ),
    )

    assert sorted(
        (str(proposal.pair.source), str(proposal.pair.target)) for proposal in found.pairs
    ) == [("srv-01-ilo", "srv-01"), ("w-4712", "w-4711")]


def test_a_group_two_findings_ask_about_is_asked_about_once() -> None:
    found = propose_relations(
        [
            _scanned("w-4711", labels={"cmdb/sn": "S-1"}),
            _scanned("w-4712", labels={"cmdb/sn": "S-1"}),
        ],
        evidence=_findings(
            [
                ("management", RelationToFind(shared=SharedLabel("cmdb/sn"))),
                ("management", RelationToFind(shared=SharedLabel("cmdb/sn"))),
            ]
        ),
    )

    assert len(found.groups) == 1


def _named_and_shared(*hosts: str) -> Proposals:
    """The hosts share one serial number, and only the names say which is the board."""
    return propose_relations(
        [_scanned(name, labels={"cmdb/sn": "S-1"}) for name in hosts],
        evidence=_findings(
            [
                ("management", RelationToFind(marker=NameWords(("ilo",)))),
                ("management", RelationToFind(shared=SharedLabel("cmdb/sn"))),
            ]
        ),
    )


def test_a_group_a_name_of_another_finding_pairs_is_not_asked_about() -> None:
    assert _named_and_shared("srv-01", "srv-01-ilo").groups == []


def test_a_group_asks_only_about_the_hosts_no_other_finding_pairs() -> None:
    (question,) = _named_and_shared("srv-01", "srv-01-ilo", "oa-1", "blade-1").groups

    assert question.members == ["oa-1", "blade-1"]


def test_words_mark_and_pair_a_relation_on_their_own() -> None:
    assert relation_to_find("management", words=["ilo"]) == RelationToFind(
        marker=NameWords(("ilo",))
    )


def test_a_value_mark_goes_with_a_value_both_hosts_carry() -> None:
    mark = MarkedValue(where=SharedLabel("cmdb/kind"), value="board")

    assert relation_to_find(
        "management", marked_by=mark, paired_by=SharedLabel("cmdb/sn")
    ) == RelationToFind(marker=mark, shared=SharedLabel("cmdb/sn"))


def test_a_relation_that_cannot_be_discovered_is_refused() -> None:
    with pytest.raises(ValueError, match="made_up"):
        relation_to_find("made_up", words=["ilo"])


@pytest.mark.parametrize(
    "words, marked_by, paired_by",
    [
        pytest.param((), None, None, id="nothing at all"),
        pytest.param(
            (), MarkedValue(where=SharedLabel("cmdb/kind"), value="board"), None, id="a mark alone"
        ),
        pytest.param(
            ("ilo",),
            MarkedValue(where=SharedLabel("cmdb/kind"), value="board"),
            SharedLabel("cmdb/sn"),
            id="words and a mark",
        ),
        pytest.param(("my-board",), None, None, id="a word no name could carry"),
        pytest.param(("",), None, None, id="an empty word"),
    ],
)
def test_a_finding_that_could_not_find_anything_is_refused(
    words: Sequence[str],
    marked_by: MarkedValue | None,
    paired_by: SharedLabel | None,
) -> None:
    with pytest.raises(ValueError):
        relation_to_find("management", words=words, marked_by=marked_by, paired_by=paired_by)


def _suggested(
    hosts: Sequence[ScannedHost],
    *,
    words: Sequence[str] = (),
    values: Sequence[SharedLabel | SharedAttribute] = (),
    attribute_names: Sequence[str] = (),
    in_names: bool = True,
    in_values: bool = True,
    kinds: Mapping[str, RelationKind] = RELATION_KINDS,
) -> Suggestions:
    return suggest_evidence(
        hosts,
        attribute_names=attribute_names,
        words=words,
        values=values,
        in_names=in_names,
        in_values=in_values,
        inside=frozenset(host.name for host in hosts),
        kinds=kinds,
    )


def _words(suggestions: Suggestions) -> list[tuple[str, int, str | None]]:
    return [(finding.word, finding.pairs, finding.kind_id) for finding in suggestions.words]


def test_a_word_a_kind_declares_is_suggested_as_that_kind() -> None:
    (finding,) = _suggested([_scanned("srv-01"), _scanned("srv-01-ilo")]).words

    assert (finding.word, finding.pairs, finding.kind_id) == ("ilo", 1, "management")
    assert finding.examples == [(HostName("srv-01-ilo"), HostName("srv-01"))]


def test_a_word_no_kind_declares_is_suggested_for_the_user_to_name() -> None:
    assert _words(_suggested([_scanned("srv-01"), _scanned("srv-01-oob")])) == [("oob", 1, None)]


def _named_and_sharing_a_serial() -> list[ScannedHost]:
    return [
        _scanned(name, labels={"cmdb/sn": f"S-{machine}"})
        for machine in range(3)
        for name in (f"srv-0{machine}", f"srv-0{machine}-ilo")
    ]


def test_looking_in_the_names_alone_reports_no_shared_value() -> None:
    suggested = _suggested(
        _named_and_sharing_a_serial(), attribute_names=["asset"], in_values=False
    )

    assert _words(suggested) == [("ilo", 3, "management")]
    assert (suggested.values, suggested.label_names, suggested.attribute_names) == ([], [], [])


def test_looking_in_the_shared_values_alone_reports_no_word() -> None:
    suggested = _suggested(_named_and_sharing_a_serial(), in_names=False)

    assert suggested.words == []
    assert [finding.where for finding in suggested.values] == [SharedLabel("cmdb/sn")]


@pytest.mark.parametrize(
    "names",
    [
        pytest.param(("ilo-srv-01", "srv-01"), id="word at the start"),
        pytest.param(("srv_01_ilo", "srv_01"), id="underscores"),
        pytest.param(("SRV-01-ILO", "SRV-01"), id="upper case"),
        pytest.param(("idrac.srv-01", "srv-01"), id="word as a label of its own"),
        pytest.param(("srv-01.ilo.example.com", "srv-01.example.com"), id="a management domain"),
    ],
)
def test_a_word_is_found_wherever_a_scan_would_read_one(names: tuple[str, str]) -> None:
    assert [
        finding.kind_id for finding in _suggested([_scanned(name) for name in names]).words
    ] == ["management"]


def test_a_number_is_not_a_word() -> None:
    assert _words(_suggested([_scanned("srv"), _scanned("srv-01")])) == []


def test_a_number_the_user_typed_is_counted_the_way_the_scan_reads_it() -> None:
    hosts = [_scanned("srv"), _scanned("srv-01")]

    assert _words(_suggested(hosts, words=["01"])) == [("01", 1, None)]
    assert _proposed(hosts, relations={"management": ["01"]}) == [("srv-01", "srv")]


def test_a_word_is_counted_once_per_pair_and_regardless_of_case() -> None:
    hosts = [_scanned(name) for name in ("a", "a-ilo", "B", "B-ILO", "c")]

    assert _words(_suggested(hosts)) == [("ilo", 2, "management")]


def test_declared_words_come_first_then_the_most_frequent() -> None:
    hosts = [
        _scanned(name)
        for name in ("a", "a-db", "b", "b-db", "c", "c-bmc", "d", "d-oob", "e", "e-oob", "f-oob")
    ]

    assert _words(_suggested(hosts)) == [
        ("bmc", 1, "management"),
        ("db", 2, None),
        ("oob", 2, None),
    ]


def test_only_a_handful_of_undeclared_words_is_offered() -> None:
    hosts = [
        _scanned(name) for index in range(12) for name in (f"srv{index}", f"srv{index}-w{index}")
    ]

    assert len(_suggested(hosts).words) == 8


def test_a_word_the_user_typed_is_reported_even_without_a_pair() -> None:
    assert _words(_suggested([_scanned("srv-01")], words=["OOB"])) == [("oob", 0, None)]


def test_a_label_whose_values_each_sit_on_two_hosts_is_suggested() -> None:
    hosts = [
        _scanned("w-4711", labels={"cmdb/sn": "S-1"}),
        _scanned("w-4712", labels={"cmdb/sn": "S-1"}),
        _scanned("w-4713", labels={"cmdb/sn": "S-2"}),
        _scanned("w-4714", labels={"cmdb/sn": "S-2"}),
        _scanned("w-4715", labels={"cmdb/sn": "S-3"}),
        _scanned("w-4716", labels={"cmdb/sn": "S-3"}),
        _scanned("w-4717", labels={"cmdb/sn": "S-4"}),
    ]

    (finding,) = _suggested(hosts).values

    assert finding.where == SharedLabel("cmdb/sn")
    assert (finding.groups, finding.largest_group) == (3, 2)
    assert finding.examples == [
        ValueExample(value="S-1", hosts=[HostName("w-4711"), HostName("w-4712")], size=2),
        ValueExample(value="S-2", hosts=[HostName("w-4713"), HostName("w-4714")], size=2),
    ]


def test_a_chassis_label_is_suggested_as_well() -> None:
    hosts = [
        _scanned(f"blade-{chassis}{slot}", labels={"chassis": chassis})
        for chassis in ("a", "b", "c")
        for slot in range(8)
    ]

    (finding,) = _suggested(hosts).values

    assert (finding.where, finding.largest_group) == (SharedLabel("chassis"), 8)


def test_a_custom_attribute_is_suggested_the_same_way() -> None:
    hosts = [
        _scanned(name, cmdb_serial=serial)
        for name, serial in (("a", "1"), ("b", "1"), ("c", "2"), ("d", "2"), ("e", "3"), ("f", "3"))
    ]

    (finding,) = _suggested(hosts, attribute_names=["cmdb_serial"]).values

    assert finding.where == SharedAttribute("cmdb_serial")


def test_a_label_with_two_values_is_a_category_rather_than_an_identity() -> None:
    hosts = [
        _scanned(f"w-{index}", labels={"cmdb/kind": "board" if index % 2 else "server"})
        for index in range(6)
    ]

    assert _suggested(hosts).values == []


def test_a_label_shared_by_too_many_hosts_says_nothing_about_belonging_together() -> None:
    hosts = [_scanned(f"srv-{index}", labels={"os": "linux"}) for index in range(30)]
    hosts += [_scanned(f"win-{index}", labels={"os": "windows"}) for index in range(3)]

    assert _suggested(hosts).values == []


def test_checkmks_own_labels_are_never_suggested() -> None:
    hosts = [
        _scanned(name, labels={"cmk/os_family": family})
        for name, family in (("a", "x"), ("b", "x"), ("c", "y"), ("d", "y"))
    ]

    assert _suggested(hosts).values == []


def test_every_label_name_is_offered_for_marking_a_board() -> None:
    hosts = [_scanned("a", labels={"cmdb/kind": "board", "cmk/site": "heute"})]

    assert _suggested(hosts).label_names == ["cmdb/kind", "cmk/site"]


def test_a_value_the_user_added_is_reported_however_widely_it_is_shared() -> None:
    hosts = [
        _scanned(f"srv-{index}", labels={"location": "muc" if index < 8 else "ber"})
        for index in range(16)
    ]

    (finding,) = _suggested(hosts, values=[SharedLabel("location")]).values

    assert (finding.where, finding.groups, finding.largest_group) == (
        SharedLabel("location"),
        2,
        8,
    )
    assert sorted(example.value for example in finding.examples) == ["ber", "muc"]


def test_a_value_the_user_added_that_no_two_hosts_share_is_reported_as_such() -> None:
    (finding,) = _suggested(
        [_scanned("a", labels={"cmdb/sn": "1"}), _scanned("b", labels={"cmdb/sn": "2"})],
        values=[SharedLabel("cmdb/sn")],
    ).values

    assert (finding.groups, finding.largest_group, finding.examples) == (0, 0, [])


def test_a_checkmk_label_the_user_added_is_read_after_all() -> None:
    hosts = [_scanned(name, labels={"cmk/site": "heute"}) for name in ("a", "b")]

    (finding,) = _suggested(hosts, values=[SharedLabel("cmk/site")]).values

    assert finding.groups == 1


def test_an_attribute_the_user_added_is_read_even_if_setup_does_not_list_it() -> None:
    hosts = [_scanned(name, cmdb_serial="1") for name in ("a", "b")]

    (finding,) = _suggested(hosts, values=[SharedAttribute("cmdb_serial")]).values

    assert finding.where == SharedAttribute("cmdb_serial")


def test_a_value_both_found_and_added_is_offered_once() -> None:
    hosts = [_scanned(f"w-{index}", labels={"cmdb/sn": f"S-{index // 2}"}) for index in range(6)]

    assert [
        finding.where for finding in _suggested(hosts, values=[SharedLabel("cmdb/sn")]).values
    ] == [SharedLabel("cmdb/sn")]


def test_a_pair_found_by_its_names_says_which_word_found_it() -> None:
    (proposal,) = _found([_scanned("srv-01"), _scanned("srv-01-ilo")]).pairs

    assert proposal.reason == NameReason("ilo")


def test_a_pair_and_a_group_found_by_a_value_say_which_value_found_them() -> None:
    found = _found(
        [
            _scanned("bmc-77", labels={"cmdb/serial": "5XJ9K2"}),
            _scanned("blade-77", labels={"cmdb/serial": "5XJ9K2"}),
            _scanned("srv-01", labels={"cmdb/serial": "A1"}),
            _scanned("srv-02", labels={"cmdb/serial": "A1"}),
        ],
        shared=SharedLabel("cmdb/serial"),
    )

    assert [proposal.reason for proposal in found.pairs] == [
        ValueReason(SharedLabel("cmdb/serial"), "5XJ9K2")
    ]
    assert [group.reason for group in found.groups] == [
        ValueReason(SharedLabel("cmdb/serial"), "A1")
    ]


def test_a_proposal_names_the_finding_it_came_from() -> None:
    (proposal,) = propose_relations(
        [_scanned("srv-01"), _scanned("srv-01-ilo")],
        evidence=Evidence(
            findings=[
                Finding(
                    id="word:ilo",
                    kind_id="management",
                    found_by=RelationToFind(marker=NameWords(("ilo",))),
                )
            ]
        ),
    ).pairs

    assert proposal.finding == "word:ilo"


def test_the_same_relation_found_twice_is_the_first_findings() -> None:
    found = propose_relations(
        [
            _scanned("srv-01", labels={"cmdb/sn": "S-1"}),
            _scanned("srv-01-ilo", labels={"cmdb/sn": "S-1"}),
        ],
        evidence=_findings(
            [
                ("management", RelationToFind(marker=NameWords(("ilo",)))),
                (
                    "management",
                    RelationToFind(marker=NameWords(("ilo",)), shared=SharedLabel("cmdb/sn")),
                ),
            ]
        ),
    )

    assert [proposal.finding for proposal in found.pairs] == ["finding-0"]
    assert found.conflicts == []


def test_two_findings_that_disagree_about_two_hosts_propose_neither() -> None:
    """The name says srv-01-ilo is the board, the CMDB says srv-01 is: that is for the user."""
    found = propose_relations(
        [
            _scanned("srv-01", labels={"cmdb/sn": "S-1", "cmdb/kind": "board"}),
            _scanned("srv-01-ilo", labels={"cmdb/sn": "S-1"}),
        ],
        evidence=_findings(
            [
                ("management", RelationToFind(marker=NameWords(("ilo",)))),
                (
                    "management",
                    RelationToFind(
                        marker=MarkedValue(where=SharedLabel("cmdb/kind"), value="board"),
                        shared=SharedLabel("cmdb/sn"),
                    ),
                ),
            ]
        ),
    )

    assert found.pairs == []
    (conflict,) = found.conflicts
    assert conflict.hosts == (HostName("srv-01"), HostName("srv-01-ilo"))
    assert sorted((str(c.pair.source), c.finding) for c in conflict.claims) == [
        ("srv-01", "finding-1"),
        ("srv-01-ilo", "finding-0"),
    ]


def _cmdb_fleet(kinds: Sequence[str] = ("board", "server")) -> list[ScannedHost]:
    """Three machines the CMDB pairs by serial number, and marks by what each host is."""
    return [
        _scanned(f"w-{machine}{kind[0]}", labels={"cmdb/sn": f"S-{machine}", "cmdb/kind": kind})
        for machine in range(3)
        for kind in kinds
    ]


def test_a_value_only_one_host_per_machine_carries_tells_the_hosts_apart() -> None:
    (finding,) = _suggested(_cmdb_fleet()).values

    assert finding.told_apart == ValueTellsApart(
        where=SharedLabel("cmdb/kind"), values=[("board", 3), ("server", 3)], suggested=None
    )


def test_a_value_with_a_vendor_word_in_it_is_suggested_as_the_deciding_end() -> None:
    (finding,) = _suggested(_cmdb_fleet(kinds=("bmc", "server"))).values

    assert isinstance(finding.told_apart, ValueTellsApart)
    assert finding.told_apart.suggested == "bmc"


def test_a_vendor_word_in_one_name_per_machine_tells_the_hosts_apart() -> None:
    hosts = [
        _scanned(name, labels={"cmdb/sn": f"S-{machine}"})
        for machine in range(3)
        for name in (f"blade-{machine}", f"bmc-{machine}")
    ]

    (finding,) = _suggested(hosts).values

    assert finding.told_apart == NamesTellApart(kind_id="management", words=["bmc"], groups=3)


def test_hosts_nothing_tells_apart_are_left_to_the_user() -> None:
    hosts = [
        _scanned(f"w-{index}", labels={"cmdb/sn": f"S-{index // 2}", "location": "muc"})
        for index in range(6)
    ]

    (finding,) = _suggested(hosts).values

    assert finding.told_apart is None


def test_the_value_that_pairs_the_hosts_does_not_also_tell_them_apart() -> None:
    hosts = [
        _scanned(f"w-{index}", labels={"cmdb/sn": f"S-{index // 2}", "cmdb/rack": "R1"})
        for index in range(6)
    ]

    (finding,) = _suggested(hosts, values=[SharedLabel("cmdb/rack")]).values[:1]

    assert finding.where == SharedLabel("cmdb/sn")
    assert finding.told_apart is None


def test_a_relation_stored_the_other_way_round_is_not_offered_again(tree: FolderTree) -> None:
    root = tree.root_folder()
    _create_host(root, "srv-01")
    _create_host(root, "srv-01-ilo")
    link_relations(
        [
            HostPair(
                source=HostName("srv-01-ilo"),
                target=HostName("srv-01"),
                kind_id="management",
                source_direction="child",
            )
        ],
        tree,
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
        progress=lambda _entry: None,
    )

    found = discover_relations(tree, evidence=_evidence(), acting_user=_SUPERUSER)

    assert _outcomes(found.entries) == [("srv-01-ilo", "srv-01", LinkOutcome.STORED_OTHERWISE)]


def test_a_run_does_not_replace_a_relation_somebody_stored_in_the_meantime(
    tree: FolderTree,
) -> None:
    root = tree.root_folder()
    _create_host(root, "srv-01")
    _create_host(root, "srv-01-ilo")
    board = HostPair(
        source=HostName("srv-01-ilo"),
        target=HostName("srv-01"),
        kind_id="management",
        source_direction="parent",
    )
    by_hand = replace(board, source_direction="child")

    def store(pair: HostPair) -> Sequence[RelationEntry]:
        return link_relations(
            [pair],
            tree,
            pprint_value=False,
            pending_changes=_noop_pending_changes(),
            acting_user=_SUPERUSER,
            progress=lambda _entry: None,
        )

    store(by_hand)
    (entry,) = store(board)

    assert entry.outcome is LinkOutcome.STORED_OTHERWISE
    assert _stored_relations(tree, "srv-01-ilo") == [
        {"kind": "management", "direction": "child", "host": HostName("srv-01")}
    ]


def test_hosts_sharing_a_value_with_more_hosts_than_a_machine_are_neither_paired_nor_asked() -> (
    None
):
    """A category - "board", "server" - relates nothing: every board would be every server's."""
    hosts = [_scanned("bmc-0", labels={"cmdb/kind": "board"})] + [
        _scanned(f"srv-{index}", labels={"cmdb/kind": "board"}) for index in range(25)
    ]

    found = _found(hosts, shared=SharedLabel("cmdb/kind"))

    assert (found.pairs, found.groups) == ([], [])


def test_a_value_the_user_added_says_how_many_of_its_values_are_too_widely_shared() -> None:
    hosts = [
        _scanned(f"w-{index}", labels={"cmdb/kind": "board" if index < 30 else "server"})
        for index in range(60)
    ]

    (finding,) = _suggested(hosts, values=[SharedLabel("cmdb/kind")]).values

    assert (finding.groups, finding.too_wide, finding.told_apart) == (0, 2, None)
    assert [example.value for example in finding.examples] == ["board", "server"]


def test_an_example_under_a_scope_names_its_hosts_in_scope_first(tree: FolderTree) -> None:
    """The host in scope is what made the value count, so it is the one the page has to show."""
    labels = HostAttributes({"labels": {"chassis": "C-7"}})
    for name in ("a-srv", "b-srv", "c-srv", "d-srv", "e-srv"):
        _create_host(tree.root_folder(), name, labels)
    _create_host(_subfolder(tree.root_folder(), "oob"), "z-board", labels)
    tree.invalidate_caches()

    (finding,) = scan_for_evidence(
        tree,
        attribute_names=[],
        acting_user=_SUPERUSER,
        values=[SharedLabel("chassis")],
        in_names=False,
        scope=Scope(folder="oob"),
    ).values

    assert finding.examples[0].hosts[0] == HostName("z-board")


def test_an_example_names_a_few_of_the_hosts_sharing_its_value_and_counts_them_all() -> None:
    """A category shared by thousands of hosts is shown by four of them - the page names no more."""
    hosts = [
        _scanned(f"w-{index:02}", labels={"cmdb/kind": "board" if index < 30 else "server"})
        for index in range(60)
    ]

    (finding,) = _suggested(hosts, values=[SharedLabel("cmdb/kind")]).values

    assert finding.examples[0] == ValueExample(
        value="board",
        hosts=[HostName("w-00"), HostName("w-01"), HostName("w-02"), HostName("w-03")],
        size=30,
    )
