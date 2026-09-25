#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shutil
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import replace
from typing import cast

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
from cmk.gui.utils.host_relations import RelationDirection
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.host_attributes import HostAttributes, HostContactGroupSpec
from cmk.gui.watolib.host_relation_discovery import (
    discover_relations,
    Evidence,
    Finding,
    HostPair,
    LinkOutcome,
    MarkedValue,
    NameReason,
    NameWords,
    outcome_counts,
    Proposals,
    propose_relations,
    relation_to_find,
    RelationEntry,
    RelationToFind,
    ScannedHost,
    SharedAttribute,
    SharedLabel,
    ValueReason,
)
from cmk.gui.watolib.hosts_and_folders import Folder, FolderTree, Host, make_folder_tree
from cmk.gui.watolib.pending_changes import NoopPendingChangesStore, PendingChanges
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
    return _create_host(
        folder,
        name,
        HostAttributes(
            {
                "labels": dict(labels or {}),
                "relations": [
                    {"kind": "management", "direction": "child", "host": HostName(board)}
                ],
            }
        ),
    )


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


def _folder_of_its_own(tree: FolderTree, name: str, contact_group: str) -> Folder:
    return tree.root_folder().create_subfolder(
        name,
        name.title(),
        HostAttributes({"contactgroups": _contact_groups(contact_group)}),
        pprint_value=False,
        pending_changes=_noop_pending_changes(),
        acting_user=_SUPERUSER,
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


def test_hosts_sharing_a_value_with_more_hosts_than_a_machine_are_neither_paired_nor_asked() -> (
    None
):
    """A category - "board", "server" - relates nothing: every board would be every server's."""
    hosts = [_scanned("bmc-0", labels={"cmdb/kind": "board"})] + [
        _scanned(f"srv-{index}", labels={"cmdb/kind": "board"}) for index in range(25)
    ]

    found = _found(hosts, shared=SharedLabel("cmdb/kind"))

    assert (found.pairs, found.groups) == ([], [])
