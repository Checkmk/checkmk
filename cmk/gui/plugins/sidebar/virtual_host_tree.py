#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Dict, List  # pylint: disable=unused-import

import cmk.gui.config as config
import cmk.gui.sites as sites
import cmk.gui.watolib as watolib
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib import HTML

from cmk.gui.plugins.wato.check_mk_configuration import transform_virtual_host_trees
from . import SidebarSnapin, snapin_registry


@snapin_registry.register
class VirtualHostTree(SidebarSnapin):
    @staticmethod
    def type_name():
        return "tag_tree"

    def _load(self):
        self._load_trees()
        self._load_user_settings()

    def _load_trees(self):
        self._trees = {
            tree["id"]: tree  #
            for tree in transform_virtual_host_trees(config.virtual_host_trees)
        }

    def _load_user_settings(self):
        tree_conf = config.user.load_file("virtual_host_tree", {"tree": 0, "cwd": {}})
        if isinstance(tree_conf, int):
            tree_conf = {"tree": tree_conf, "cwd": {}}  # convert from old style

        tree_id = tree_conf["tree"]

        # Fallback to first defined tree in case the user selected does not exist anymore
        if tree_id not in self._trees and self._trees:
            tree_id = self._tree_choices()[0][0]

        self._cwds = tree_conf["cwd"]
        self._current_tree_id = tree_id
        self._current_tree_path = self._cwds.get(self._current_tree_id, [])

    def _save_user_settings(self):
        config.user.save_file("virtual_host_tree", {
            "tree": self._current_tree_id,
            "cwd": self._cwds
        })

    @classmethod
    def title(cls):
        return _("Virtual Host Tree")

    @classmethod
    def description(cls):
        return _("This snapin shows tree views of your hosts based on their tag "
                 "classifications. You can configure which tags to use in your "
                 "global settings of Multisite.")

    def show(self):
        self._load()
        if not config.virtual_host_trees:
            url = 'wato.py?varname=virtual_host_trees&mode=edit_configvar'
            html.p(
                _('You have not defined any virtual host trees. You can do this '
                  'in the <a href="%s" target="main">global settings</a>.') % url)
            return

        self._show_tree_selection()
        self._show_tree()

    def _show_tree_selection(self):
        html.begin_form("vtree")

        html.dropdown("vtree",
                      self._tree_choices(),
                      deflt="%s" % self._current_tree_id,
                      onchange='virtual_host_tree_changed(this)',
                      style="width:210px" if self._current_tree_path else None)

        # Give chance to change one level up, if we are in a subtree
        if self._current_tree_path:
            upurl = "javascript:virtual_host_tree_enter('%s')" % "|".join(
                self._current_tree_path[:-1])
            html.icon_button(upurl, _("Go up one tree level"), "back")

        html.br()
        html.end_form()
        html.final_javascript(self._javascript())

    def _show_tree(self):
        tree_spec = self._trees[self._current_tree_id]["tree_spec"]

        tree = self._compute_tag_tree(tree_spec)
        html.open_div(class_="tag_tree")
        self._render_tag_tree_level(tree_spec, [], self._current_tree_path, _("Virtual Host Tree"),
                                    tree)
        html.close_div()

    def _tree_choices(self):
        return sorted([(tree["id"], tree["title"]) for tree in self._trees.values()],
                      key=lambda x: x[1])

    def _render_tag_tree_level(self, tree_spec, path, cwd, title, tree):
        if (not self._is_tag_subdir(path=path, cwd=cwd) and
                not self._is_tag_subdir(path=cwd, cwd=path)):
            return

        if path != cwd and self._is_tag_subdir(path, cwd):
            bullet = self._tag_tree_bullet(self._tag_tree_worst_state(tree), path, False)
            if self._tag_tree_has_svc_problems(tree):
                bullet += html.render_icon_button(
                    self._tag_tree_url(tree_spec, path, "svcproblems"),
                    _("Show the service problems contained in this branch"),
                    "svc_problems",
                    target="main")

            if path:
                html.begin_foldable_container("tag-tree", ".".join(map(str, path)), False,
                                              HTML(bullet + title))

        for (node_title, node_value), subtree in sorted(tree.get("_children", {}).items()):
            subpath = path + [node_value or ""]
            url = self._tag_tree_url(tree_spec, subpath, "allhosts")

            if "_num_hosts" in subtree:
                node_title += " (%d)" % subtree["_num_hosts"]

            node_title = html.render_a(node_title, href=url, target="main")

            if "_children" not in subtree:
                if self._is_tag_subdir(path, cwd):
                    html.write(self._tag_tree_bullet(subtree.get("_state", 0), subpath, True))
                    if subtree.get("_svc_problems"):
                        url = self._tag_tree_url(tree_spec, subpath, "svcproblems")
                        html.icon_button(url,
                                         _("Show the service problems contained in this branch"),
                                         "svc_problems",
                                         target="main")
                    html.write(node_title)
                    html.br()
            else:
                self._render_tag_tree_level(tree_spec, subpath, cwd, node_title, subtree)

        if path and path != cwd and self._is_tag_subdir(path, cwd):
            html.end_foldable_container()

    def _is_tag_subdir(self, path, cwd):
        if not cwd:
            return True
        if not path:
            return False
        if path[0] != cwd[0]:
            return False
        return self._is_tag_subdir(path[1:], cwd[1:])

    def _tag_tree_bullet(self, state, path, leaf):
        code = (u'<div class="tagtree %sstatebullet state%d">&nbsp;</div>' %
                ((leaf and "leaf " or ""), state))
        if not leaf:
            code = ('<a title="%s" href="javascript:virtual_host_tree_enter(\'%s\');">%s</a>' %
                    (_("Display the tree only below this node"), "|".join(path), code))
        return code + " "

    def _tag_tree_url(self, tree_spec, node_values, viewname):
        urlvars = [("view_name", viewname), ("filled_in", "filter")]
        if viewname == "svcproblems":
            urlvars += [("st1", "on"), ("st2", "on"), ("st3", "on")]

        urlvars += self._get_tag_url_vars(tree_spec, node_values)
        urlvars += self._get_folder_url_vars(node_values)

        return html.makeuri_contextless(urlvars, "view.py")

    def _get_tag_url_vars(self, tree_spec, node_values):
        urlvars = []

        tag_tree_spec = [
            l for l in tree_spec if not l.startswith("foldertree:") and not l.startswith("folder:")
        ]
        tag_node_values = [
            v for v in node_values
            if not v.startswith("foldertree:") and not v.startswith("folder:")
        ]

        for nr, (level_spec, tag) in enumerate(zip(tag_tree_spec, tag_node_values)):
            if level_spec.startswith("topic:"):
                for tag_group in config.tags.tag_groups:
                    for grouped_tag in tag_group.tags:
                        if grouped_tag.id == tag:
                            urlvars.append(("host_tag_%d_grp" % nr, tag_group.id))
                            urlvars.append(("host_tag_%d_op" % nr, "is"))
                            urlvars.append(("host_tag_%d_val" % nr, grouped_tag.id))
                            break

            else:
                urlvars.append(("host_tag_%d_grp" % nr, level_spec))
                urlvars.append(("host_tag_%d_op" % nr, "is"))
                urlvars.append(("host_tag_%d_val" % nr, tag or ""))

        return urlvars

    def _get_folder_url_vars(self, node_values):
        urlvars = []
        folder_components = {}
        for level_spec in node_values:
            if level_spec.startswith("folder:") or level_spec.startswith("foldertree:"):
                level, component = level_spec.split(":")[1:]
                folder_components[int(level)] = component

        if folder_components:
            wato_path = []
            for i in range(max(folder_components.keys())):
                level = i + 1
                if level not in folder_components:
                    wato_path.append("*")
                else:
                    wato_path.append(folder_components[level])

            urlvars.append(("wato_folder", "/".join(wato_path)))

        return urlvars

    def _tag_tree_worst_state(self, tree):
        if not tree.values():
            return 3
        if "_state" in tree:
            return tree["_state"]

        states = map(self._tag_tree_worst_state, tree.values())
        for x in states:
            if x == 2:
                return 2
        return max(states)

    def _tag_tree_has_svc_problems(self, tree):
        if "_svc_problems" in tree:
            return tree["_svc_problems"]

        for x in tree.values():
            if self._tag_tree_has_svc_problems(x):
                return True
        return False

    def _javascript(self):
        return """
function virtual_host_tree_changed(field)
{
    var tree_id = field.value;
    cmk.ajax.call_ajax('sidebar_ajax_tag_tree.py?tree_id=' + escape(tree_id), {
        response_handler : function(handler_data, response_body) {
            cmk.sidebar.refresh_single_snapin("tag_tree");
        }
    });
}

function virtual_host_tree_enter(path)
{
    cmk.ajax.call_ajax('sidebar_ajax_tag_tree_enter.py?path=' + escape(path), {
        response_handler : function(handler_data, response_body) {
            cmk.sidebar.refresh_single_snapin("tag_tree");
        }
    });
}
"""

    def _compute_tag_tree(self, tree_spec):
        tag_groups, topics = self._get_tag_config()
        tree = {}  # type: Dict[Any, Any]
        for host_row in self._get_all_hosts():
            self._add_host_to_tree(tree_spec, tree, host_row, tag_groups, topics)
        return tree

    def _add_host_to_tree(self, tree_spec, tree, host_row, tag_groups, topics):
        _site, _host_name, wato_folder, state, _num_ok, num_warn, \
            num_crit, num_unknown, custom_variables = host_row

        if wato_folder.startswith("/wato/"):
            folder_path = wato_folder[6:-9]
            folder_path_components = folder_path.split("/")
            if watolib.Folder.folder_exists(folder_path):
                folder_titles = watolib.get_folder_title_path(folder_path)[1:]  # omit main folder
        else:
            folder_titles = []

        state, have_svc_problems = self._calculate_state(state, num_crit, num_unknown, num_warn)

        tags = set(custom_variables.get("TAGS", []).split())

        # Now go through the levels of the tree. Each level may either be
        # - a tag group id, or
        # - "topic:" plus the name of a tag topic. That topic should only contain
        #   checkbox tags, or:
        # - "folder:3", where 3 is the folder level (starting at 1)
        # The problem with the "topic" entries is, that a host may appear several
        # times!

        parent_level_branches = [tree]

        for level_spec in tree_spec:
            this_level_branches = []
            for tree_entry in parent_level_branches:
                if level_spec.startswith("topic:"):
                    topic = level_spec[6:]
                    if topic not in topics:
                        continue  # silently skip not existing topics

                    # Iterate over all host tag groups with that topic
                    for tag_group in topics[topic]:
                        for tag in tag_group.tags:
                            if tag.id in tags:
                                this_level_branches.append(
                                    tree_entry.setdefault("_children", {}).setdefault(
                                        (tag.title, tag.id), {}))

                elif level_spec.startswith("folder:"):
                    level = int(level_spec.split(":", 1)[1])

                    if level <= len(folder_titles):
                        node_title = folder_titles[level - 1]
                        node_value = "folder:%d:%s" % (level, folder_path_components[level - 1])
                    else:
                        node_title = _("Hosts in this folder")
                        node_value = "folder:%d:" % level

                    this_level_branches.append(
                        tree_entry.setdefault("_children", {}).setdefault((node_title, node_value),
                                                                          {}))

                elif level_spec.startswith("foldertree:"):
                    path_components = []
                    foldertree_tree_entry = tree_entry
                    for path_component in folder_path_components:
                        path_components.append(path_component)

                        level = len(path_components)
                        if level <= len(folder_titles):
                            node_title = folder_titles[level - 1]
                            node_value = "foldertree:%d:%s" % (level, path_components[level - 1])
                        else:
                            node_title = _("Main folder")
                            node_value = "foldertree:%d:" % level

                        foldertree_tree_entry = foldertree_tree_entry.setdefault(
                            "_children", {}).setdefault((node_title, node_value), {})

                        if path_components == folder_path_components:  # Direct host parent
                            this_level_branches.append(foldertree_tree_entry)

                else:
                    # It' a tag group
                    if level_spec not in tag_groups:
                        continue  # silently skip not existant tag groups

                    tag_value, tag_title = self._get_tag_group_value(tag_groups[level_spec], tags)

                    if self._trees[self._current_tree_id].get("exclude_empty_tag_choices", False) \
                       and tag_value is None:
                        continue

                    this_level_branches.append(
                        tree_entry.setdefault("_children", {}).setdefault((tag_title, tag_value),
                                                                          {}))

            parent_level_branches = this_level_branches

        # Add the numbers/state of this host to the last level the host is invovled with
        for tree_entry in this_level_branches:
            tree_entry.setdefault("_num_hosts", 0)
            tree_entry.setdefault("_state", 0)

            tree_entry["_num_hosts"] += 1
            tree_entry["_svc_problems"] = tree_entry.get("_svc_problems",
                                                         False) or have_svc_problems

            if state == 2 or tree_entry["_state"] == 2:
                tree_entry["_state"] = 2
            else:
                tree_entry["_state"] = max(state, tree_entry["_state"])

    # Prepare list of host tag groups and topics
    def _get_tag_config(self):
        tag_groups = {}
        topics = {}  # type: Dict[str, List[Any]]
        for tag_group in config.tags.tag_groups:
            if tag_group.topic:
                topics.setdefault(tag_group.topic, []).append(tag_group)
            tag_groups[tag_group.id] = tag_group

        return tag_groups, topics

    def _get_all_hosts(self):
        try:
            sites.live().set_prepend_site(True)
            query = "GET hosts\n" \
                    "Columns: host_name filename state num_services_ok num_services_warn " \
                    "num_services_crit num_services_unknown custom_variables"
            hosts = sites.live().query(query)
        finally:
            sites.live().set_prepend_site(False)

        return sorted(hosts)

    def _calculate_state(self, state, num_crit, num_unknown, num_warn):
        # make state reflect the state of the services + host
        have_svc_problems = False
        if state:
            state += 1  # shift 1->2 (DOWN->CRIT) and 2->3 (UNREACH->UNKNOWN)

        if num_crit:
            state = 2
            have_svc_problems = True

        elif num_unknown:
            if state != 2:
                state = 3
            have_svc_problems = True

        elif num_warn:
            if not state:
                state = 1
            have_svc_problems = True

        return state, have_svc_problems

    def _get_tag_group_value(self, tag_group, tags):
        for grouped_tag in tag_group.tags:
            if grouped_tag.id in tags:
                return grouped_tag.id, grouped_tag.title

        # Not found -> try empty entry
        for grouped_tag in tag_group.tags:
            if grouped_tag.id is None:
                return None, grouped_tag.title

        # No empty entry found -> get default (i.e. first entry)
        return tag_group.tags[0].id, tag_group.tags[0].title

    def page_handlers(self):
        return {
            "sidebar_ajax_tag_tree": self._ajax_tag_tree,
            "sidebar_ajax_tag_tree_enter": self._ajax_tag_tree_enter,
        }

    def _ajax_tag_tree(self):
        html.set_output_format("json")
        self._load()
        new_tree = html.request.var("tree_id")

        if new_tree not in self._trees:
            raise MKUserError("conf", _("This virtual host tree does not exist."))

        self._current_tree_id = new_tree
        self._save_user_settings()
        html.write("OK")

    # TODO: Validate path in current tree
    def _ajax_tag_tree_enter(self):
        html.set_output_format("json")
        self._load()
        path = (html.request.get_str_input_mandatory("path").split("|")
                if html.request.var("path") else [])
        self._cwds[self._current_tree_id] = path
        self._save_user_settings()
        html.write("OK")

    @classmethod
    def refresh_regularly(cls):
        return True

    @classmethod
    def allowed_roles(cls):
        return ["admin", "user", "guest"]
