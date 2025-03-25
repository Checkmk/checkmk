#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from contextlib import AbstractContextManager, nullcontext
from typing import Any

from cmk.utils.tags import TagGroupID, TagID

from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _u
from cmk.gui.type_defs import Choices
from cmk.gui.user_sites import get_activation_site_choices, get_configured_site_choices
from cmk.gui.valuespec import (
    DictionaryEntry,
    DropdownChoice,
    DualListChoice,
    JSONValue,
    Labels,
    ListOf,
    ListOfStrings,
    MonitoredHostname,
    ValueSpec,
    ValueSpecText,
)
from cmk.gui.watolib.hosts_and_folders import folder_tree

from .._group_selection import sorted_host_group_choices
from ._rule_conditions import DictHostTagCondition


def multifolder_host_rule_match_conditions() -> list[DictionaryEntry]:
    return [
        site_rule_match_condition(only_sites_with_replication=True),
        _multi_folder_rule_match_condition(),
    ] + common_host_rule_match_conditions()


def site_rule_match_condition(only_sites_with_replication: bool) -> DictionaryEntry:
    return (
        "match_site",
        DualListChoice(
            title=_("Match sites"),
            help=_("This condition makes the rule match only hosts of the selected sites."),
            choices=(
                get_activation_site_choices
                if only_sites_with_replication
                else get_configured_site_choices
            ),
        ),
    )


def _multi_folder_rule_match_condition() -> DictionaryEntry:
    return (
        "match_folders",
        ListOf(
            valuespec=FullPathFolderChoice(
                title=_("Folder"),
                help=_(
                    "This condition makes the rule match only hosts that are managed "
                    "via Setup and that are contained in this folder - either directly "
                    "or in one of its subfolders."
                ),
            ),
            add_label=_("Add additional folder"),
            title=_("Match folders"),
            movable=False,
        ),
    )


class FullPathFolderChoice(DropdownChoice):
    def __init__(self, title: str, help: str) -> None:  # pylint: disable=redefined-builtin
        super().__init__(title=title, help=help, choices=folder_tree().folder_choices_fulltitle)


def common_host_rule_match_conditions() -> list[DictionaryEntry]:
    return [
        (
            "match_hosttags",
            DictHostTagCondition(
                title=_("Match host tags"),
                help_txt=_(
                    "Rule only applies to hosts that meet all of the host tag "
                    "conditions listed here",
                ),
            ),
        ),
        (
            "match_hostlabels",
            Labels(
                world=Labels.World.CORE,
                title=_("Match host labels"),
                help=_("Use this condition to select hosts based on the configured host labels."),
            ),
        ),
        (
            "match_hostgroups",
            DualListChoice(
                title=_("Match host groups"),
                help=_("The host must be in one of the selected host groups"),
                choices=sorted_host_group_choices,
                allow_empty=False,
            ),
        ),
        (
            "match_hosts",
            ListOfStrings(
                valuespec=MonitoredHostname(),  # type: ignore[arg-type]  # should be Valuespec[str]
                title=_("Match hosts"),
                size=24,
                orientation="horizontal",
                allow_empty=False,
                empty_text=_(
                    "Please specify at least one host. Disable the option if you want to allow all hosts."
                ),
            ),
        ),
        (
            "match_exclude_hosts",
            ListOfStrings(
                valuespec=MonitoredHostname(),  # type: ignore[arg-type]  # should be Valuespec[str]
                title=_("Exclude hosts"),
                size=24,
                orientation="horizontal",
            ),
        ),
    ]


class HostTagCondition(ValueSpec[Sequence[str]]):
    """ValueSpec for editing a tag-condition"""

    def render_input(self, varprefix: str, value: Sequence[str]) -> None:
        self._render_condition_editor(varprefix, value)

    def from_html_vars(self, varprefix: str) -> Sequence[str]:
        return self._get_tag_conditions(varprefix)

    def _get_tag_conditions(self, varprefix: str) -> Sequence[str]:
        """Retrieve current tag condition settings from HTML variables"""

        def gettagvalue(tgid: TagGroupID) -> TagID | None:
            v = request.var(varprefix + "tagvalue_" + tgid)
            if v is None:
                return None
            return TagID(v)

        if varprefix:
            varprefix += "_"

        # Main tags
        tag_list = []
        for tag_group in active_config.tags.tag_groups:
            if tag_group.is_checkbox_tag_group:
                tagvalue = tag_group.default_value
            else:
                tagvalue = gettagvalue(tag_group.id)

            # Not all tags are submitted, see cmk.gui.forms.remove_unused_vars.
            # So simply skip None values.
            if tagvalue is None:
                continue

            mode = request.var(varprefix + "tag_" + tag_group.id)
            if mode == "is":
                tag_list.append(tagvalue)
            elif mode == "isnot":
                tag_list.append(TagID("!" + tagvalue))

        # Auxiliary tags
        for aux_tag in active_config.tags.aux_tag_list.get_tags():
            mode = request.var(varprefix + "auxtag_" + aux_tag.id)
            if mode == "is":
                tag_list.append(aux_tag.id)
            elif mode == "isnot":
                tag_list.append(TagID("!" + aux_tag.id))

        return tag_list

    def canonical_value(self) -> Sequence[str]:
        return []

    def value_to_html(self, value: Sequence[str]) -> ValueSpecText:
        return "|".join(value)

    def validate_datatype(self, value: Sequence[str], varprefix: str) -> None:
        if not isinstance(value, list):
            raise MKUserError(
                varprefix, _("The list of host tags must be a list, but is %r") % type(value)
            )
        for x in value:
            if not isinstance(x, str):
                raise MKUserError(
                    varprefix,
                    _("The list of host tags must only contain strings but also contains %r") % x,
                )

    def _render_condition_editor(self, varprefix: str, tag_specs: Sequence[str]) -> None:
        """Render HTML input fields for editing a tag based condition"""
        if varprefix:
            varprefix += "_"

        if not active_config.tags.get_tag_ids():
            html.write_text_permissive(
                _('You have not configured any <a href="wato.py?mode=tags">tags</a>.')
            )
            return

        tag_groups_by_topic = dict(active_config.tags.get_tag_groups_by_topic())
        aux_tags_by_topic = dict(active_config.tags.get_aux_tags_by_topic())

        all_topics = active_config.tags.get_topic_choices()
        make_foldable = len(all_topics) > 1

        for topic_id, topic_title in all_topics:
            container: AbstractContextManager[bool] = (
                foldable_container(
                    treename="topic",
                    id_=varprefix + topic_title,
                    isopen=True,
                    title=_u(topic_title),
                )
                if make_foldable
                else nullcontext(False)
            )
            with container:
                html.open_table(class_=["hosttags"])

                for tag_group in tag_groups_by_topic.get(topic_id, []):
                    html.open_tr()
                    html.td("%s: &nbsp;" % _u(tag_group.title or ""), class_="title")

                    choices = tag_group.get_non_empty_tag_choices()
                    default_tag, deflt = self._current_tag_setting(choices, tag_specs)
                    self._tag_condition_dropdown(varprefix, "tag", deflt, tag_group.id)
                    if tag_group.is_checkbox_tag_group:
                        html.write_text_permissive(" " + _("set"))
                    else:
                        html.dropdown(
                            varprefix + "tagvalue_" + tag_group.id,
                            [(t[0], _u(t[1])) for t in choices if t[0] is not None],
                            deflt=default_tag,
                        )

                    html.close_div()
                    html.close_td()
                    html.close_tr()

                for aux_tag in aux_tags_by_topic.get(topic_id, []):
                    html.open_tr()
                    html.td("%s: &nbsp;" % _u(aux_tag.title), class_="title")
                    default_tag, deflt = self._current_tag_setting(
                        [(aux_tag.id, _u(aux_tag.title))], tag_specs
                    )
                    self._tag_condition_dropdown(varprefix, "auxtag", deflt, aux_tag.id)
                    html.write_text_permissive(" " + _("set"))
                    html.close_div()
                    html.close_td()
                    html.close_tr()

                html.close_table()

    def _current_tag_setting(
        self, choices: Sequence[tuple[str | None, str]], tag_specs: Sequence[str]
    ) -> tuple[Any, str]:
        """Determine current (default) setting of tag by looking into tag_specs (e.g. [ "snmp", "!tcp", "test" ] )"""
        default_tag = None
        ignore = True
        for t in tag_specs:
            if t[0] == "!":
                n = True
                t = t[1:]
            else:
                n = False
            if t in [x[0] for x in choices]:
                default_tag = t
                ignore = False
                negate = n
        if ignore:
            deflt = "ignore"
        elif negate:
            deflt = "isnot"
        else:
            deflt = "is"
        return default_tag, deflt

    def _tag_condition_dropdown(self, varprefix: str, tagtype: str, deflt: str, id_: str) -> None:
        """Show dropdown with "is/isnot/ignore" and beginning of div that is switched visible by is/isnot"""
        html.open_td()
        dropdown_id = varprefix + tagtype + "_" + id_
        onchange = f"cmk.valuespecs.toggle_tag_dropdown(this, '{varprefix}tag_sel_{id_}');"
        choices: Choices = [
            ("ignore", _("ignore")),
            ("is", _("is")),
            ("isnot", _("isnot")),
        ]
        html.dropdown(dropdown_id, choices, deflt=deflt, onchange=onchange)
        html.close_td()

        html.open_td(class_="tag_sel")
        if html.form_submitted():
            div_is_open = request.var(dropdown_id, "ignore") != "ignore"
        else:
            div_is_open = deflt != "ignore"
        html.open_div(
            id_=f"{varprefix}tag_sel_{id_}",
            style="display: none;" if not div_is_open else None,
        )

    def mask(self, value: Sequence[str]) -> Sequence[str]:
        return value

    def value_to_json(self, value: Sequence[str]) -> JSONValue:
        raise NotImplementedError()  # FIXME! Violates LSP!

    def value_from_json(self, json_value: JSONValue) -> Sequence[str]:
        raise NotImplementedError()  # FIXME! Violates LSP!
