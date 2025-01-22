#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from contextlib import contextmanager
from typing import Any, Literal, TypeGuard

import cmk.gui.view_utils
from cmk.gui.config import active_config
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import Row
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.urls import makeuri_contextless, urlencode_vars

from .helpers import get_state_assumption_key

# possible aggregated states
MISSING = -2  # currently unused
PENDING = -1
OK = 0
WARN = 1
CRIT = 2
UNKNOWN = 3
UNAVAIL = 4

BIAggrTreeState = tuple[dict[str, Any], Any, dict[str, Any], list]
BILeafTreeState = tuple[dict[str, Any], Any, dict[str, Any]]


class ABCFoldableTreeRenderer(abc.ABC):
    def __init__(
        self,
        row: Row,
        omit_root: bool,
        expansion_level: int,
        only_problems: bool,
        lazy: bool,
        wrap_texts: Literal["wrap", "nowrap"] = "nowrap",
        show_frozen_difference: bool = False,
    ) -> None:
        self._row = row
        self._show_frozen_difference = show_frozen_difference
        self._omit_root = omit_root
        self._expansion_level = expansion_level
        self._only_problems = only_problems
        self._lazy = lazy
        self._wrap_texts = wrap_texts
        self._load_tree_state()

    def _load_tree_state(self) -> None:
        self._treestate = user.get_tree_states("bi")
        if self._expansion_level != user.bi_expansion_level:
            self._treestate = {}
            user.set_tree_states("bi", self._treestate)
            user.save_tree_states()

    @abc.abstractmethod
    def css_class(self) -> str:
        raise NotImplementedError()

    def render(self) -> HTML:
        with output_funnel.plugged():
            self._show_tree()
            return HTML.without_escaping(output_funnel.drain())

    def _show_tree(self) -> None:
        tree = self._get_tree()
        affected_hosts = self._row["aggr_hosts"]
        title = self._row["aggr_tree"]["title"]
        group = self._row["aggr_group"]

        url_id = urlencode_vars(
            [
                ("aggregation_id", self._row["aggr_tree"]["aggregation_id"]),
                ("show_frozen_difference", "yes" if self._show_frozen_difference else ""),
                ("group", group),
                ("title", title),
                ("omit_root", "yes" if self._omit_root else ""),
                ("renderer", self.__class__.__name__),
                ("only_problems", "yes" if self._only_problems else ""),
                ("reqhosts", ",".join("%s#%s" % sitehost for sitehost in affected_hosts)),
            ]
        )

        html.open_div(id_=url_id, class_="bi_tree_container")
        self._show_subtree(
            tree,
            path=tuple([("frozen_" if self._show_frozen_difference else "") + tree[2]["title"]]),
            show_host=len(affected_hosts) > 1,
        )
        html.close_div()

    @abc.abstractmethod
    def _show_subtree(
        self,
        tree: BIAggrTreeState | BILeafTreeState,
        path: tuple[str, ...],
        show_host: bool,
        frozen_marker_set: bool = False,
    ) -> None:
        raise NotImplementedError()

    def _get_tree(self) -> BIAggrTreeState:
        tree = self._row["aggr_treestate"]
        if self._only_problems:
            tree = self._filter_tree_only_problems(tree)
        return tree

    # Convert tree to tree contain only node in non-OK state
    def _filter_tree_only_problems(self, tree: BIAggrTreeState) -> BIAggrTreeState:
        state, assumed_state, node, subtrees = tree
        # remove subtrees in state OK
        new_subtrees: list[BIAggrTreeState | BILeafTreeState] = []
        for subtree in subtrees:
            effective_state = subtree[1] if subtree[1] is not None else subtree[0]
            if effective_state["state"] not in [OK, PENDING]:
                if is_leaf(subtree):
                    new_subtrees.append(subtree)
                elif is_aggr(subtree):
                    new_subtrees.append(self._filter_tree_only_problems(subtree))

        return state, assumed_state, node, new_subtrees

    def _path_id(self, path: tuple[str, ...]) -> str:
        return "/".join(path)

    def _is_open(self, path: tuple[str, ...]) -> bool:
        is_open = self._treestate.get(self._path_id(path))
        if is_open is None:
            is_open = len(path) <= self._expansion_level

        # Make sure that in case of BI Boxes (omit root) the root level is *always* visible
        if not is_open and self._omit_root and len(path) == 1:
            is_open = True

        return is_open

    def _omit_content(self, path: tuple[str, ...]) -> bool:
        return self._lazy and not self._is_open(path)

    def _get_mousecode(self, path: tuple[str, ...]) -> str:
        return "%s(this, %d);" % (self._toggle_js_function(), self._omit_content(path))

    @abc.abstractmethod
    def _toggle_js_function(self) -> str:
        raise NotImplementedError()

    def _show_leaf(self, tree: BILeafTreeState, show_host: bool) -> None:
        site, host = tree[2]["host"]
        service = tree[2].get("service")

        # Four cases:
        # (1) zbghora17 . Host status   (show_host == True, service is None)
        # (2) zbghora17 . CPU load      (show_host == True, service is not None)
        # (3) Host Status               (show_host == False, service is None)
        # (4) CPU load                  (show_host == False, service is not None)

        if show_host or not service:
            host_url = makeuri_contextless(
                request,
                [("view_name", "hoststatus"), ("site", site), ("host", host)],
                filename="view.py",
            )

        if service:
            service_url = makeuri_contextless(
                request,
                [("view_name", "service"), ("site", site), ("host", host), ("service", service)],
                filename="view.py",
            )

        with self._show_node(tree, show_host):
            self._assume_icon(site, host, service)

            if show_host:
                html.a(host.replace(" ", "&nbsp;"), href=host_url)
                html.b(HTML.without_escaping("&diams;"), class_="bullet")

            if not service:
                html.a(_("Host&nbsp;status"), href=host_url)
            else:
                html.a(service.replace(" ", "&nbsp;"), href=service_url)

    @abc.abstractmethod
    def _show_node(self, tree, show_host, mousecode=None, img_class=None):
        raise NotImplementedError()

    def _assume_icon(self, site, host, service):
        ass = user.bi_assumptions.get(get_state_assumption_key(site, host, service))
        current_state = str(ass).lower()

        html.icon_button(
            url=None,
            title=_("Assume another state for this item (reload page to activate)"),
            icon="assume_%s" % current_state,
            onclick="cmk.bi.toggle_assumption(this, '{}', '{}', '{}');".format(
                site, host, service.replace("\\", "\\\\") if service else ""
            ),
            cssclass="assumption",
        )

    def _render_bi_state(self, state: int) -> str:
        return {
            PENDING: _("PD"),
            OK: _("OK"),
            WARN: _("WA"),
            CRIT: _("CR"),
            UNKNOWN: _("UN"),
            MISSING: _("MI"),
            UNAVAIL: _("NA"),
        }.get(state, _("??"))


class FoldableTreeRendererTree(ABCFoldableTreeRenderer):
    def css_class(self) -> str:
        return "aggrtree"

    def _toggle_js_function(self) -> str:
        return "cmk.bi.toggle_subtree"

    def _show_subtree(
        self,
        tree: BIAggrTreeState | BILeafTreeState,
        path: tuple[str, ...],
        show_host: bool,
        frozen_marker_set: bool = False,
    ) -> None:
        if is_leaf(tree):
            self._show_leaf(tree, show_host)
            return
        if not is_aggr(tree):
            raise ValueError("Invalid tree state")

        html.open_span(class_="title")

        is_empty = len(tree[3]) == 0
        if is_empty:
            mc = None
        else:
            mc = self._get_mousecode(path)

        css_class = "open" if self._is_open(path) else "closed"

        with self._show_node(tree, show_host, mousecode=mc, img_class=css_class):
            if tree[2].get("icon"):
                html.write_html(html.render_icon(tree[2]["icon"]))
                html.write_text_permissive("&nbsp;")

            if tree[2].get("docu_url"):
                html.icon_button(
                    tree[2]["docu_url"],
                    _("Context information about this rule"),
                    "url",
                    target="_blank",
                )
                html.write_text_permissive("&nbsp;")

            html.write_text_permissive(tree[2]["title"])

        if not is_empty:
            html.open_ul(
                id_="%d:%s" % (self._expansion_level or 0, self._path_id(path)),
                class_=["subtree", css_class],
            )

            if not self._omit_content(path):
                for node in tree[3]:
                    self._show_child(path, node, show_host, frozen_marker_set)

            html.close_ul()

        html.close_span()

    def _show_child(
        self,
        path: tuple[str, ...],
        node: BIAggrTreeState | BILeafTreeState,
        show_host: bool,
        frozen_marker_set: bool,
    ) -> None:
        if not node[2].get("hidden"):
            new_path = tuple([*path, node[2]["title"]])
            frozen_marker = node[2].get("frozen_marker")
            frozen_aggregation_css = ""
            tooltip_text = ""
            if not frozen_marker_set and frozen_marker and self._show_frozen_difference:
                if frozen_marker.status == "new":
                    if is_leaf(new_path):
                        tooltip_text = _("This node is not in the frozen aggregation")
                    else:
                        tooltip_text = _("These nodes are not in the frozen aggregation")
                    frozen_aggregation_css = "frozen_aggregation missing_in_frozen_aggregation"
                else:
                    if is_leaf(new_path):
                        tooltip_text = _("This node is only in the frozen aggregation")
                    else:
                        tooltip_text = _("These nodes are only in the frozen aggregation")
                    frozen_aggregation_css = "frozen_aggregation only_in_frozen_aggregation"
            html.open_li(class_=frozen_aggregation_css)
            if frozen_aggregation_css and frozen_marker:
                html.span(
                    "+" if frozen_marker.status == "new" else "-",
                    class_=["frozen_marker", frozen_marker.status],
                    title=tooltip_text,
                )
            self._show_subtree(
                node,
                new_path,
                show_host,
                frozen_marker_set or bool(frozen_aggregation_css),
            )
            html.close_li()

    @contextmanager
    def _show_node(  # pylint: disable=too-many-branches
        self,
        tree,
        show_host,
        mousecode=None,
        img_class=None,
    ):
        # Check if we have an assumed state: comparing assumed state (tree[1]) with state (tree[0])
        if tree[1] and tree[0] != tree[1]:
            addclass = ["assumed"]
            effective_state = tree[1]
        else:
            addclass = []
            effective_state = tree[0]

        class_ = [
            "content",
            "state",
            "state%d" % (effective_state["state"] if effective_state["state"] is not None else -1),
        ] + addclass
        html.open_span(class_=class_)
        html.write_text_permissive(self._render_bi_state(effective_state["state"]))
        html.close_span()

        if mousecode:
            if img_class:
                html.img(
                    src=theme.url("images/tree_closed.svg"),
                    class_=["treeangle", img_class],
                    onclick=mousecode,
                )

            html.open_span(class_=["content", "name"])

        icon_name, icon_title = None, None
        # TODO: Check whehter tree[0]["in_downtime"] == 2 is possible at all. Seems like this is
        #       deprecated and that by now the "in_downtime" field holds a boolean value
        if tree[0]["in_downtime"] == 2:
            icon_name = "downtime"
            icon_title = _("This element is currently in a scheduled downtime.")

        elif tree[0]["in_downtime"] == 1:
            # only display host downtime if the service has no own downtime
            icon_name = "downtime"
            icon_title = _("One of the subelements is in a scheduled downtime.")

        if tree[0]["acknowledged"]:
            icon_name = "ack"
            icon_title = _("This problem has been acknowledged.")

        if not tree[0]["in_service_period"]:
            icon_name = "outof_serviceperiod"
            icon_title = _("This element is currently not in its service period.")

        if icon_name and icon_title:
            html.icon(icon_name, title=icon_title, class_=["icon", "bi"])
        try:
            yield
        finally:
            if mousecode:
                if str(effective_state["state"]) in tree[2].get("state_messages", {}):
                    html.b(HTML.without_escaping("&diams;"), class_="bullet")
                    html.write_text_permissive(
                        tree[2]["state_messages"][str(effective_state["state"])]
                    )

                html.close_span()

            output: HTML = cmk.gui.view_utils.format_plugin_output(
                effective_state["output"],
                request=request,
                shall_escape=active_config.escape_plugin_output,
            )

            if output:
                output = (
                    HTMLWriter.render_b(HTML.without_escaping("&diams;"), class_="bullet") + output
                )
            else:
                output = HTML.empty()

            css_classes = ["content", "output"]
            html.span(output, class_=css_classes)


class FoldableTreeRendererBoxes(ABCFoldableTreeRenderer):
    def css_class(self) -> str:
        return "aggrtree_box"

    def _toggle_js_function(self) -> str:
        return "cmk.bi.toggle_box"

    def _show_subtree(
        self,
        tree: BIAggrTreeState | BILeafTreeState,
        path: tuple[str, ...],
        show_host: bool,
        frozen_marker_set: bool = False,
    ) -> None:
        # Check if we have an assumed state: comparing assumed state (tree[1]) with state (tree[0])
        if tree[1] and tree[0] != tree[1]:
            addclass = ["assumed"]
            effective_state = tree[1]
        else:
            addclass = []
            effective_state = tree[0]

        if is_leaf(tree):
            leaf = "leaf"
            mc = None
        else:
            leaf = "noleaf"
            mc = self._get_mousecode(path)

        classes = [
            "bibox_box",
            leaf,
            "open" if self._is_open(path) else "closed",
            "state",
            "state%d" % effective_state["state"],
        ] + addclass

        omit = self._omit_root and len(path) == 1
        if not omit:
            html.open_span(
                id_="%d:%s" % (self._expansion_level or 0, self._path_id(path)),
                class_=classes,
                onclick=mc,
            )

            if is_leaf(tree):
                self._show_leaf(tree, show_host)
            else:
                html.write_text_permissive(tree[2]["title"].replace(" ", "&nbsp;"))

            html.close_span()

        if is_aggr(tree) and not self._omit_content(path):
            html.open_span(
                class_="bibox",
                style="display: none;" if not self._is_open(path) and not omit else "",
            )
            for node in tree[3]:
                new_path = tuple(list(path) + [node[2]["title"]])
                self._show_subtree(node, new_path, show_host)
            html.close_span()

    @contextmanager
    def _show_node(self, tree, show_host, mousecode=None, img_class=None):
        yield

    def _assume_icon(self, site, host, service):
        return  # No assume icon with boxes


class ABCFoldableTreeRendererTable(FoldableTreeRendererTree):
    _mirror = False

    def _show_tree(self) -> None:
        td_style = None if self._wrap_texts == "wrap" else "white-space: nowrap;"

        tree = self._get_tree()
        depth = _status_tree_depth(tree)
        leaves = self._gen_table(tree, depth, len(self._row["aggr_hosts"]) > 1)

        html.open_table(class_=["aggrtree", "ltr"])
        odd = "odd"
        for code, colspan, parents in leaves:
            html.open_tr()

            leaf_td = HTMLWriter.render_td(
                code, class_=["leaf", odd], style=td_style, colspan=colspan
            )
            odd = "even" if odd == "odd" else "odd"

            tds = [leaf_td]
            for rowspan, c in parents:
                tds.append(
                    HTMLWriter.render_td(c, class_=["node"], style=td_style, rowspan=rowspan)
                )

            if self._mirror:
                tds.reverse()

            html.write_html(HTML.empty().join(tds))
            html.close_tr()

        html.close_table()

    def _gen_table(
        self, tree: BIAggrTreeState | BILeafTreeState, height: int, show_host: bool
    ) -> list[tuple[HTML, int, list]]:
        if is_leaf(tree):
            return self._gen_leaf(tree, height, show_host)
        if is_aggr(tree):
            return self._gen_node(tree, height, show_host)
        raise ValueError("Invalid tree state")

    def _gen_leaf(
        self, tree: BILeafTreeState, height: int, show_host: bool
    ) -> list[tuple[HTML, int, list]]:
        with output_funnel.plugged():
            self._show_leaf(tree, show_host)
            content = HTML.without_escaping(output_funnel.drain())
        return [(content, height, [])]

    def _gen_node(
        self, tree: BIAggrTreeState, height: int, show_host: bool
    ) -> list[tuple[HTML, int, list]]:
        leaves: list[Any] = []
        for node in tree[3]:
            if not node[2].get("hidden"):
                leaves += self._gen_table(node, height - 1, show_host)

        with output_funnel.plugged():
            html.open_div(class_="aggr_tree")
            with self._show_node(tree, show_host):
                html.write_text_permissive(tree[2]["title"])
            html.close_div()
            content = HTML.without_escaping(output_funnel.drain())

        if leaves:
            leaves[0][2].append((len(leaves), content))

        return leaves


def is_leaf(tree: BIAggrTreeState | BILeafTreeState) -> TypeGuard[BILeafTreeState]:
    return len(tree) == 3


def is_aggr(tree: BIAggrTreeState | BILeafTreeState) -> TypeGuard[BIAggrTreeState]:
    return len(tree) == 4


def _status_tree_depth(tree: BIAggrTreeState | BILeafTreeState) -> int:
    if not is_aggr(tree):
        return 1

    subtrees = tree[3]
    maxdepth = 0
    for node in subtrees:
        maxdepth = max(maxdepth, _status_tree_depth(node))
    return maxdepth + 1


class FoldableTreeRendererBottomUp(ABCFoldableTreeRendererTable): ...


class FoldableTreeRendererTopDown(ABCFoldableTreeRendererTable):
    _mirror = True


__all__ = [
    "ABCFoldableTreeRenderer",
    "FoldableTreeRendererTree",
    "FoldableTreeRendererBoxes",
    "FoldableTreeRendererTopDown",
    "FoldableTreeRendererBottomUp",
]
