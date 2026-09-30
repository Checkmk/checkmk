#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""GUI-only "Relations" between hosts (management boards <-> OS hosts).

This is a pure Setup/GUI feature. It links a management-board host to the OS hosts it manages
(and vice versa) so both sides are navigable, and it is surfaced in the monitoring without ever
changing how a host is checked or notified.

Links are stored in the ``relations`` host attribute of **both** hosts, each from its own side,
and one save writes both halves - so every host knows what it is related to by looking at itself,
and whoever saves last decides what a pair says.

For the monitoring the relations are resolved centrally at activation time (see
:mod:`cmk.gui.watolib.host_relations_export`). The reverse of every stored half is derived in the
same pass, so a half whose counterpart row was lost still materializes on both sides.
"""

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from typing import Literal, Protocol

from cmk.ccc.hostaddress import HostName, HostNameValidationError
from cmk.ccc.site import SiteId
from cmk.gui.exceptions import MKUserError
from cmk.gui.form_specs.generators.config_host_name import create_config_host_name
from cmk.gui.form_specs.unstable import not_empty
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import HTMLGenerator
from cmk.gui.i18n import _, ungettext
from cmk.gui.log import logger
from cmk.gui.utils.host_relation_kinds import (
    DirectedRelationKind,
    known_relations,
    RELATION_KINDS,
    RelationKind,
)
from cmk.gui.utils.host_relations import (
    parse_relations_value,
    referenced_host_names,
    RelationDirection,
    RelationLink,
    relations_or_empty,
    RelationsValue,
    ResolvedRelation,
    reverse_direction,
)
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.rulesets.internal.form_specs import (
    ButtonGroupSize,
    CascadingSingleChoiceExtended,
    CascadingSingleChoiceLayout,
    DictGroupExtended,
    DictionaryGroupLayout,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
    StringAutocompleter,
)
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    InputHint,
    List,
)
from cmk.rulesets.v1.form_specs.validators import ValidationError
from cmk.web.utils.html import HTML
from cmk.web.utils.icons import IconNames, StaticIcon

_LOGGER = logger.getChild("host_relations")


class RelatedHost(Protocol):
    """What :func:`resolve_all_relations` reads off a host - no more than this.

    Spelled out so the resolver can be exercised without building a whole folder tree, and so the
    contract is in the signature rather than in a cast at the call site.
    """

    @property
    def attributes(self) -> HostAttributes: ...

    def name(self) -> HostName: ...

    def site_id(self) -> SiteId: ...


def _validate_related_host_name(value: str) -> None:
    try:
        HostName(value)
    except HostNameValidationError as exc:
        raise ValidationError(Message("This is not a usable host name.")) from exc


def _related_host_choice() -> StringAutocompleter:
    return create_config_host_name(
        title=Title("Host"),
        help_text=Help("The monitored host at the other end of this relation."),
        prefill=InputHint("Select related host"),
        # A row is turned back into a link outside any validation, so a name rejected there is a
        # crash report rather than a message next to the field. The length check also marks the
        # field required in the dialog.
        custom_validate=(
            not_empty(error_msg=Message("Select the host this relation points to.")),
            _validate_related_host_name,
        ),
    )


def relation_choice_name(kind_id: str, direction: RelationDirection) -> str:
    """One end of a relation kind as a single identifier, as the relation discovery names it.

    Joined by an underscore rather than by a separator that reads better, so that it can serve as
    an element name. That is unambiguous because a direction contains none and a kind id is an
    identifier.
    """
    return f"{kind_id}_{direction}"


def _offered_kind() -> RelationKind:
    """The kind every row of the dialog is of.

    The type is not a choice yet, so the direction can be worded by the one kind there is. A
    second kind makes the directions depend on the type and fails here until they do.
    """
    (kind,) = RELATION_KINDS.values()
    return kind


def _direction_to_disk(choice: object) -> object:
    assert isinstance(choice, tuple)
    return choice[0]


def _direction_toggle(kind: RelationKind) -> TransformDataForLegacyFormatOrRecomposeFunction:
    """The direction as a toggle between the ends of the kind, stored as the plain direction.

    Sized small to sit at the height of the fields next to it.
    """
    directions = kind.directions()
    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=CascadingSingleChoiceExtended(
            title=Title("Direction"),
            help_text=Help(
                "What this host is to the selected one: its management board, or an OS "
                "host managed by it."
            ),
            elements=[
                CascadingSingleChoiceElement(
                    name=direction,
                    # Already a translatable string, held lazily by the kind.
                    title=Title(  # astrein: disable=localization-checker
                        str(kind.end(direction).row)
                    ),
                    parameter_form=FixedValue(value=None),
                )
                for direction in directions
            ],
            prefill=DefaultValue(directions[0]),
            layout=CascadingSingleChoiceLayout.button_group,
            button_group_size=ButtonGroupSize.small,
        ),
        from_disk=lambda direction: (direction, None),
        to_disk=_direction_to_disk,
    )


def _relation_row() -> Dictionary:
    """One row of the host dialog: the relation type, the direction and the host it applies to.

    The keys are those of a :class:`RelationLink`, so a row is the stored link. The direction
    titles describe the end the host being edited sits at towards the selected host, so a row
    reads left to right as "this host is management board of <related host>".
    """
    kind = _offered_kind()
    row = DictGroupExtended(layout=DictionaryGroupLayout.horizontal)
    return Dictionary(
        # Not rendered by the list, but names the row for screen readers.
        title=Title("Relation"),
        elements={
            "kind": DictElement(
                required=True,
                group=row,
                parameter_form=SingleChoiceExtended[str](
                    title=Title("Type"),
                    help_text=Help(
                        "What the two hosts are to each other. Management board is the only "
                        "relation type so far."
                    ),
                    elements=[
                        SingleChoiceElementExtended(
                            name=kind.id,
                            # Already a translatable string, held lazily by the kind.
                            title=Title(str(kind.title)),  # astrein: disable=localization-checker
                        )
                    ],
                    prefill=DefaultValue(kind.id),
                    frozen=True,
                ),
            ),
            "direction": DictElement(
                required=True, group=row, parameter_form=_direction_toggle(kind)
            ),
            "host": DictElement(required=True, group=row, parameter_form=_related_host_choice()),
        },
    )


def host_relations_form_spec() -> TransformDataForLegacyFormatOrRecomposeFunction:
    """FormSpec of the ``relations`` attribute: one row per relation.

    A row is edited as the :class:`RelationLink` it stores - the self-describing mapping the
    export and the monitoring views read. That is what a hand written "hosts.mk" shows, and a
    named key can gain a sibling in a later version where a tuple position cannot.
    """
    return TransformDataForLegacyFormatOrRecomposeFunction(
        # "Related hosts" is taken by the section this sits in.
        title=Title("Relations"),
        help_text=Help(
            "Link this host to other monitored hosts. Type and direction say what this host is "
            "to the selected one - the management board of that host, for instance, "
            "or an OS host managed by it. A relation concerns both hosts, so it is stored on "
            "both: it appears here right away when someone records it on the other host, and "
            "adding or removing one here changes that host too."
        ),
        wrapped_form_spec=List[Mapping[str, object]](
            add_element_label=Label("Add new relation"),
            remove_element_label=Label("Remove this relation"),
            no_element_label=Label("No relations"),
            editable_order=False,
            element_template=_relation_row(),
        ),
        # A link of a kind or direction the dialog has no choice for cannot be shown as a row.
        from_disk=lambda raw: known_relations(parse_relations_value(raw)),
        # Unusable rows are kept out by the validators of the row.
        to_disk=parse_relations_value,
    )


ResolvedRelations = dict[HostName, list[ResolvedRelation]]


@dataclass(frozen=True)
class RelationConflict:
    """What speaks against storing a link, as a value rather than as its wording.

    Comparable, so that an edit can tell the contradictions it introduces from the ones that were
    already stored, without that answer hanging on how a sentence happens to read.
    """

    reason: Literal["self_link", "contradicting_directions", "duplicate"]
    host: HostName | None = None
    kind_id: str | None = None

    def message(self) -> str:
        match self.reason:
            case "self_link":
                return _("A host cannot be linked to itself.")
            case "contradicting_directions":
                assert self.kind_id is not None
                kind = RELATION_KINDS[self.kind_id]
                # Only a directed kind has two ends to contradict each other; a symmetric one
                # stores the same direction on both hosts and can never get here.
                assert isinstance(kind, DirectedRelationKind)
                return _(
                    "This host is linked to '%(host)s' both as its '%(end)s' and as its "
                    "'%(other_end)s'. A host can only sit at one end of a relation."
                ) % {
                    "host": self.host,
                    "end": kind.parent.noun,
                    "other_end": kind.child.noun,
                }
            case "duplicate":
                return _("'%(host)s' is linked more than once. Remove the duplicate.") % {
                    "host": self.host
                }


def relation_conflicts(
    links: Sequence[RelationLink], owner: HostName
) -> Sequence[RelationConflict]:
    """Everything that speaks against storing ``links`` on ``owner``, in reporting order.

    Only what the value says about *this* host; those contradictions are rejected on save. What
    the counterpart stores, and whether it still exists, is reported instead (see
    :func:`cmk.gui.watolib.builtin_attributes.validate_host_relations`): rejecting it here would
    make one host unsavable because someone else broke the other.

    Links are grouped per relation, not per linked host: two links naming the same host are a
    contradiction only as the two ends of the *same* relation. Only the kinds this version knows
    are grouped - what a relation of a later version says about itself is not for this one to
    judge, and it could not word the refusal anyway. Linking a host to itself is refused whatever
    the kind: that is wrong without knowing what the relation means.
    """
    conflicts: list[RelationConflict] = []

    if any(link["host"] == owner for link in links):
        conflicts.append(RelationConflict(reason="self_link"))

    directions_by_relation: dict[tuple[HostName, str], list[RelationDirection]] = {}
    for link in known_relations(links):
        if link["host"] == owner:
            continue
        directions_by_relation.setdefault((link["host"], link["kind"]), []).append(
            link["direction"]
        )

    for (host_name, kind_id), directions in directions_by_relation.items():
        distinct = set(directions)
        if len(distinct) > 1:
            conflicts.append(
                RelationConflict(reason="contradicting_directions", host=host_name, kind_id=kind_id)
            )
        if len(directions) > len(distinct):
            conflicts.append(RelationConflict(reason="duplicate", host=host_name, kind_id=kind_id))

    return conflicts


def relations_or_user_error(raw: object) -> RelationsValue:
    """The links of a stored ``relations`` value, as a user error if it cannot be read at all."""
    try:
        return parse_relations_value(raw)
    except ValueError as exc:
        raise MKUserError(
            None, _("The relations of this host are malformed: %(error)s") % {"error": exc}
        ) from exc


def resolve_all_relations(all_hosts: Mapping[HostName, RelatedHost]) -> ResolvedRelations:
    """Resolve every host's relations (both directions) into concrete host names.

    Both halves of a relation are stored, so one pass over the ``relations`` attribute of every
    host sees every relation twice. The reverse of each half is derived anyway: that is what makes
    a hand written ``hosts.mk`` holding only one half still materialize on both sides.

    Reads each host's *own* attributes, not its effective ones. That is deliberate - a
    folder-level value would mean every host in the folder pointing at the same board - and it is
    only safe because the attribute is not inheritable
    (``HostAttributeRelations.show_in_folder() -> False``).

    The result maps each host to the list of hosts related to it, with the end that host sits at
    towards each of them - the same reading as the stored links, so the materialized value and
    the one in "hosts.mk" say the same thing. Duplicates are removed, so a stored pair collapses
    into one relation per side. Hosts without relations are omitted.
    """
    # A relation identifies itself, so a dict keyed by it is the set of them that keeps the
    # order they were resolved in.
    resolved: defaultdict[HostName, dict[ResolvedRelation, None]] = defaultdict(dict)
    # Asked once per related host rather than once per link: site_id() walks the folder chain up
    # to a file system check, and a board with many OS hosts is one host holding many links.
    sites: dict[HostName, str] = {}

    def _site_of(host: RelatedHost) -> str:
        if (site := sites.get(name := host.name())) is None:
            site = sites[name] = str(host.site_id())
        return site

    def _drop_reason(owner: HostName, other: HostName) -> str | None:
        if owner == other:
            return "self-reference"
        if other not in all_hosts:
            return "related host does not exist"
        return None

    def _add(
        owner: HostName, kind_id: str, direction: RelationDirection, other: RelatedHost
    ) -> None:
        relation = ResolvedRelation(
            kind=kind_id, direction=direction, host=other.name(), site=_site_of(other)
        )
        resolved[owner][relation] = None

    def _unknown_direction(owner: HostName, direction: str) -> None:
        _LOGGER.debug(
            "Relation of host %(owner)r dropped: direction %(direction)r is unknown to this"
            " version.",
            {"owner": owner, "direction": direction},
        )

    def _unknown_kind(owner: HostName, link: RelationLink) -> None:
        _LOGGER.debug(
            "Relation of host %(owner)r dropped: this version does not know a %(kind)r relation"
            " with a %(direction)r end.",
            {"owner": owner, "kind": link["kind"], "direction": link["direction"]},
        )

    for host_name, host in all_hosts.items():
        try:
            parsed = parse_relations_value(
                host.attributes.get("relations", []),
                on_unknown_direction=partial(_unknown_direction, host_name),
            )
        except ValueError as exc:
            # Only a hand written "hosts.mk" gets here, and a debug line would hide it from
            # whoever wonders where their relations went.
            _LOGGER.warning(
                "Skipping malformed 'relations' attribute of host %(host)r: %(error)s",
                {"host": host_name, "error": exc},
            )
            continue
        for link in known_relations(parsed, on_unknown=partial(_unknown_kind, host_name)):
            if (reason := _drop_reason(host_name, link["host"])) is not None:
                _LOGGER.debug(
                    "Relation %(owner)r -> %(other)r (%(kind)s/%(direction)s) dropped: %(reason)s.",
                    {
                        "owner": host_name,
                        "other": link["host"],
                        "kind": link["kind"],
                        "direction": link["direction"],
                        "reason": reason,
                    },
                )
                continue
            other = all_hosts[link["host"]]
            _add(host_name, link["kind"], link["direction"], other)
            _add(other.name(), link["kind"], reverse_direction(link["direction"]), host)

    return {owner: list(relations) for owner, relations in resolved.items()}


#: Related hosts the deletion dialog names one by one before it only counts them - a longer list
#: pushes the buttons of the dialog out of sight.
MAX_LISTED_RELATED_HOSTS = 10


def relations_deletion_note(
    host: RelatedHost, host_url: Callable[[HostName], str | None]
) -> HTML | None:
    """Extra confirmation text for deleting ``host``, or ``None`` if it has no relations.

    ``host_url`` says where the name of a related host links to, and ``None`` leaves it as plain
    text - for a host the user may not see, or one that its counterpart still names although it
    no longer exists.
    """
    if not (
        related := referenced_host_names(relations_or_empty(host.attributes.get("relations", [])))
    ):
        return None
    listed = sorted(related)[:MAX_LISTED_RELATED_HOSTS]
    items = [
        HTMLWriter.render_li(
            HTMLWriter.render_a(name, href=url)
            if (url := host_url(name)) is not None
            else HTML.with_escaping(name)
        )
        for name in listed
    ]
    if unlisted := len(related) - len(listed):
        items.append(HTMLWriter.render_li(_("and %(count)d more") % {"count": unlisted}))
    heading = ungettext(
        "This host has %(count)d related host:",
        "This host has %(count)d related hosts:",
        len(related),
    ) % {"count": len(related)}
    footer = _(
        "Deleting %(host)s removes these relations. The related hosts themselves are not deleted."
    ) % {"host": host.name()}
    # No size: the theme sizes this icon, because its "img.icon.png" rule beats every size class
    # the component renders.
    return HTMLWriter.render_div(
        HTMLGenerator.render_static_icon(StaticIcon(IconNames.warning))
        + HTMLWriter.render_div(
            HTML.with_escaping(heading)
            + HTMLWriter.render_ul(HTML.empty().join(items))
            + HTML.with_escaping(footer)
        ),
        class_="confirm_warning_note",
    )
