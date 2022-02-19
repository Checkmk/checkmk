// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";

// fetch_url: dynamically load content of opened element.
export function toggle(treename, id, fetch_url, save_state) {
    var img = document.getElementById("treeimg." + treename + "." + id);
    var box = document.getElementById("tree." + treename + "." + id);

    toggle_tree_state(treename, id, box, fetch_url, save_state);
    if (img) utils.toggle_folding(img, !utils.has_class(box, "closed"));
}

function toggle_tree_state(tree, name, oContainer, fetch_url, save_state) {
    var outer_container = oContainer.parentNode;
    var state;

    if (utils.has_class(oContainer, "closed")) {
        utils.change_class(oContainer, "closed", "open");
        utils.change_class(outer_container, "closed", "open");

        if (fetch_url && !oContainer.innerHTML) {
            ajax.call_ajax(fetch_url, {
                method: "GET",
                response_handler: function (handler_data, response_body) {
                    handler_data.container.innerHTML = response_body;
                },
                handler_data: {
                    container: oContainer,
                },
            });
        }

        state = "on";
    } else {
        utils.change_class(oContainer, "open", "closed");
        utils.change_class(outer_container, "open", "closed");
        state = "off";
    }

    if (save_state) persist_tree_state(tree, name, state);
}

export function persist_tree_state(tree, name, state) {
    ajax.get_url(
        "tree_openclose.py?tree=" +
            encodeURIComponent(tree) +
            "&name=" +
            encodeURIComponent(name) +
            "&state=" +
            state
    );
}
