#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import Counter
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import ClassVar, Self

import cmk.ec.export as ec  # astrein: disable=module-layers
import cmk.utils.paths
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.web.utils.urls import HTTPVariable


def service_levels() -> Sequence[tuple[int, str]]:
    return active_config.mkeventd_service_levels


def action_choices(omit_hidden: bool = False) -> list[tuple[str, str]]:
    # The possible actions are configured in mkeventd.mk,
    # not in multisite.mk (like the service levels). That
    # way we have not direct access to them but need
    # to load them from the configuration.
    return [("@NOTIFY", _("Send monitoring notification"))] + [
        (a["id"], a["title"])
        for a in eventd_configuration().get("actions", [])
        if not omit_hidden or not a.get("hidden")
    ]


@request_memoize()
def eventd_configuration() -> ec.ConfigFromWATO:
    return ec.load_config(ec.create_paths(cmk.utils.paths.omd_root))


@dataclass(frozen=True)
class _Ref:
    """Tells a rule pack or rule by its ID, and which of the ones with the ID it is

    Several ones may have the same ID, e.g. hand-written ones, or a modified rule pack of an MKP and
    the one installing the MKP again added. A page may be outdated, so it tells rule packs and rules
    by their references instead of their positions. A reference tells how many have its ID, too, so
    it tells none once their number changed, e.g. if one before it was deleted meanwhile. Among as
    many with the ID it may still tell another one, as nothing else tells them apart.
    """

    OCCURRENCE_VAR: ClassVar[str]
    """The variable telling the occurrence, see to_vars()"""
    OCCURRENCES_VAR: ClassVar[str]
    """The variable telling the number of occurrences, see to_vars()"""

    id_: str
    occurrence: int = 0
    """How many ones before it have its ID"""
    occurrences: int = 1
    """How many ones have its ID"""

    @classmethod
    def _of_ids(cls, ids: Iterable[str]) -> list[Self]:
        ids = list(ids)
        occurrences = Counter(ids)
        before: Counter[str] = Counter()
        refs = []
        for id_ in ids:
            refs.append(cls(id_, before[id_], occurrences[id_]))
            before[id_] += 1
        return refs

    @classmethod
    def from_request(cls, varname: str) -> Self:
        """The reference the variables of to_vars() tell"""
        return cls(
            request.get_str_input_mandatory(varname),
            request.get_integer_input_mandatory(cls.OCCURRENCE_VAR, 0),
            request.get_integer_input_mandatory(cls.OCCURRENCES_VAR, 1),
        )

    @classmethod
    def from_form_value(cls, value: str) -> Self | None:
        """The reference the value of form_value() tells, if any"""
        position, _sep, id_ = value.partition(":")
        occurrence, slash, occurrences = position.partition("/")
        try:
            return cls(id_, int(occurrence), int(occurrences) if slash else 1)
        except ValueError:  # No number, or one with more digits than Python converts
            return None

    @classmethod
    def existing_position(cls, ids: Sequence[str], varname: str, unknown: str) -> int:
        """The position of the one the variables of to_vars() tell, refusing one which doesn't exist"""
        return cls._existing_position(cls.from_request(varname), ids, varname, unknown)

    @classmethod
    def existing_position_in_form(cls, ids: Sequence[str], varname: str, unknown: str) -> int:
        """Like existing_position(), but for the variable with the value of form_value()"""
        ref = cls.from_form_value(request.get_str_input_mandatory(varname))
        return cls._existing_position(ref, ids, varname, unknown)

    @classmethod
    def _existing_position(
        cls, ref: Self | None, ids: Sequence[str], varname: str, unknown: str
    ) -> int:
        if ref is None or (nr := ref.position_in(ids)) is None:
            raise MKUserError(varname, unknown)
        return nr

    def to_vars(self, varname: str) -> list[HTTPVariable]:
        """The variables telling the reference

        The first one with an ID needs no occurrence, and the only one no number of occurrences."""
        occurrence = [(self.OCCURRENCE_VAR, self.occurrence)] if self.occurrence else []
        occurrences = [(self.OCCURRENCES_VAR, self.occurrences)] if self.occurrences != 1 else []
        return [(varname, self.id_), *occurrence, *occurrences]

    def form_value(self) -> str:
        """Tells the reference in a form field, e.g. "1/2:id" for the second of two with the ID

        The occurrence comes first, so that the value can be split even if the ID contains a colon.
        Like in to_vars(), the only one with an ID needs no number of occurrences."""
        occurrences = f"/{self.occurrences}" if self.occurrences != 1 else ""
        return f"{self.occurrence}{occurrences}:{self.id_}"

    def position_in(self, ids: Sequence[str]) -> int | None:
        """The position of the one it tells among the ones with the IDs, if any

        There is none once the number of ones with its ID changed."""
        positions = [nr for nr, other_id in enumerate(ids) if other_id == self.id_]
        if len(positions) != self.occurrences or not 0 <= self.occurrence < len(positions):
            return None
        return positions[self.occurrence]


class RulePackRef(_Ref):
    # The rule list and the rule editor tell rules with "occurrence" and "occurrences".
    OCCURRENCE_VAR = "rule_pack_occurrence"
    OCCURRENCES_VAR = "rule_pack_occurrences"

    @classmethod
    def of(cls, rule_packs: Iterable[ec.ECRulePack]) -> list[Self]:
        """The references to each of the rule packs"""
        return cls._of_ids(rule_pack["id"] for rule_pack in rule_packs)


class RuleRef(_Ref):
    OCCURRENCE_VAR = "occurrence"
    OCCURRENCES_VAR = "occurrences"

    @classmethod
    def of(cls, rules: Iterable[ec.Rule]) -> list[Self]:
        """The references to each of the rules of a rule pack

        Nobody validates hand-written rules, and the Event Console compiles no disabled ones, so
        they may lack an ID. Such a rule has the empty one."""
        return cls._of_ids(rule.get("id", "") for rule in rules)


def rule_pack_editor_vars(pack: RulePackRef) -> list[HTTPVariable]:
    """The variables of the link to the editor of the rule pack"""
    return [("mode", "mkeventd_edit_rule_pack"), *pack.to_vars("rule_pack")]


def rule_editor_vars(
    pack: RulePackRef, rule: RuleRef | None = None, varname: str = "edit_rule"
) -> list[HTTPVariable]:
    """The variables of the link to the editor of the rule of the rule pack

    Without a rule the editor adds a new one, with the variable "clone_rule" a copy of the rule."""
    return [
        ("mode", "mkeventd_edit_rule"),
        *pack.to_vars("rule_pack"),
        *(rule.to_vars(varname) if rule else []),
    ]


def rules_with_editor_vars(
    rule_packs: Sequence[ec.ECRulePack],
) -> Iterator[tuple[ec.Rule, list[HTTPVariable]]]:
    """Each rule of the rule packs, with the variables of rule_editor_vars() for it"""
    for rule_pack, pack in zip(rule_packs, RulePackRef.of(rule_packs), strict=True):
        rules = list(rule_pack.get("rules", []))
        for rule, rule_ref in zip(rules, RuleRef.of(rules), strict=True):
            yield rule, rule_editor_vars(pack, rule_ref)


def dissolve_mkp_proxies(rule_packs: Sequence[ec.ECRulePack]) -> Sequence[ec.ECRulePackSpec]:
    return [
        rule_pack.get_rule_pack_spec() if isinstance(rule_pack, ec.MkpRulePackProxy) else rule_pack
        for rule_pack in rule_packs
    ]


def save_active_config() -> None:
    ec.save_active_config(
        dissolve_mkp_proxies(ec.load_rule_packs(ec.create_paths(cmk.utils.paths.omd_root))),
        cmk.utils.paths.omd_root,
        active_config.mkeventd_pprint_rules,
    )
