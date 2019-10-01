// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
// +------------------------------------------------------------------+
//
// This file is part of Check_MK.
// The official homepage is at http://mathias-kettner.de/check_mk.
//
// check_mk is free software;  you can redistribute it and/or modify it
// under the  terms of the  GNU General Public License  as published by
// the Free Software Foundation in version 2.  check_mk is  distributed
// in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
// out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
// PARTICULAR PURPOSE. See the  GNU General Public License for more de-
// tails.  You should have received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import * as utils from "utils";
import * as ajax from "ajax";

export function toggle_subtree(oImg, lazy)
{
    if (oImg.tagName == "SPAN") { // clicked on title,
        oImg = oImg.previousElementSibling;
    }
    var oSubtree = oImg.parentNode.getElementsByTagName("ul")[0];
    var url = "bi_save_treestate.py?path=" + encodeURIComponent(oSubtree.id);
    var do_open;

    if (utils.has_class(oImg, "closed")) {
        utils.change_class(oSubtree, "closed", "open");
        utils.toggle_folding(oImg, true);

        url += "&state=open";
        do_open = true;
    }
    else {
        utils.change_class(oSubtree, "open", "closed");
        utils.toggle_folding(oImg, false);

        url += "&state=closed";
        do_open = false;
    }

    if (lazy && do_open)
        ajax.get_url(url, bi_update_tree, oImg);
    else
        ajax.get_url(url);
}

function bi_update_tree(container)
{
    // Deactivate clicking - the update can last a couple
    // of seconds. In that time we must inhibit further clicking.
    container.onclick = null;

    // First find enclosding <div class=bi_tree_container>
    var bi_container = container;
    while (bi_container && !utils.has_class(bi_container, "bi_tree_container")) {
        bi_container = bi_container.parentNode;
    }

    ajax.post_url("bi_render_tree.py", bi_container.id, bi_update_tree_response, bi_container);
}

function bi_update_tree_response(bi_container, code) {
    bi_container.innerHTML = code;
    utils.execute_javascript_by_object(bi_container);
}

export function toggle_box(container, lazy)
{
    var url = "bi_save_treestate.py?path=" + encodeURIComponent(container.id);
    var do_open;

    if (utils.has_class(container, "open")) {
        if (lazy)
            return; // do not close in lazy mode
        utils.change_class(container, "open", "closed");
        url += "&state=closed";
        do_open = false;
    }
    else {
        utils.change_class(container, "closed", "open");
        url += "&state=open";
        do_open = true;
    }

    // TODO: Make asynchronous
    if (lazy && do_open)
        ajax.get_url(url, bi_update_tree, container);
    else {
        ajax.get_url(url);
        // find child nodes that belong to this node and
        // control visibility of those. Note: the BI child nodes
        // are *no* child nodes in HTML but siblings!
        var found = 0;
        for (var i in container.parentNode.children) {
            var onode = container.parentNode.children[i];

            if (onode == container)
                found = 1;

            else if (found) {
                if (do_open)
                    onode.style.display = "inline-block";
                else
                    onode.style.display = "none";
                return;
            }
        }
    }
}

export function toggle_assumption(link, site, host, service)
{
    var img = link.getElementsByTagName("img")[0];

    // get current state
    var path_parts = img.src.split("/");
    var file_part = path_parts.pop();
    var current = file_part.replace(/icon_assume_/, "").replace(/.png/, "");

    if (current == "none")
        // Assume WARN when nothing assumed yet
        current = "1";
    else if (current == "3" || (service == "" && current == "2"))
        // Assume OK when unknown assumed (or when critical assumed for host)
        current = "0";
    else if (current == "0")
        // Disable assumption when ok assumed
        current = "none";
    else
        // In all other cases increase the assumption
        current = parseInt(current) + 1;

    var url = "bi_set_assumption.py?site=" + encodeURIComponent(site)
            + "&host=" + encodeURIComponent(host);
    if (service) {
        url += "&service=" + encodeURIComponent(service);
    }
    url += "&state=" + current;
    img.src = path_parts.join("/") + "/icon_assume_" + current + ".png";
    ajax.get_url(url);
}
