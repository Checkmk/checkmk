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

//#   .-Foldable Container-------------------------------------------------.
//#   |     _____     _     _       _     _       ____            _        |
//#   |    |  ___|__ | | __| | __ _| |__ | | ___ / ___|___  _ __ | |_      |
//#   |    | |_ / _ \| |/ _` |/ _` | '_ \| |/ _ \ |   / _ \| '_ \| __|     |
//#   |    |  _| (_) | | (_| | (_| | |_) | |  __/ |__| (_) | | | | |_ _    |
//#   |    |_|  \___/|_|\__,_|\__,_|_.__/|_|\___|\____\___/|_| |_|\__(_)   |
//#   |                                                                    |
//#   '--------------------------------------------------------------------'

// fetch_url: dynamically load content of opened element.
export function toggle(treename, id, fetch_url) {
    // Check, if we fold a NG-Norm
    var oImg;
    var oNform = document.getElementById("nform." + treename + "." + id);
    if (oNform) {
        oImg = oNform.children[0];
        var oTr = oNform.parentNode.nextElementSibling;
        toggle_tree_state(treename, id, oTr, fetch_url);

        if (oImg)
            utils.toggle_folding(oImg, !utils.has_class(oTr, "closed"));
    }
    else {
        oImg = document.getElementById("treeimg." + treename + "." + id);
        var oBox = document.getElementById("tree." + treename + "." + id);
        toggle_tree_state(treename, id, oBox, fetch_url);

        if (oImg)
            utils.toggle_folding(oImg, !utils.has_class(oBox, "closed"));
    }
}

function toggle_tree_state(tree, name, oContainer, fetch_url) {
    var state;
    if (utils.has_class(oContainer, "closed")) {
        utils.change_class(oContainer, "closed", "open");

        if (fetch_url && !oContainer.innerHTML) {
            ajax.call_ajax(fetch_url, {
                method           : "GET",
                response_handler : function(handler_data, response_body) {
                    handler_data.container.innerHTML = response_body;
                },
                handler_data     : {
                    container: oContainer
                }
            });
        }

        state = "on";
        if (oContainer.tagName == "TR") { // handle in-table toggling
            while ((oContainer = oContainer.nextElementSibling))
                utils.change_class(oContainer, "closed", "open");
        }
    }
    else {
        utils.change_class(oContainer, "open", "closed");
        state = "off";
        if (oContainer.tagName == "TR") { // handle in-table toggling
            while ((oContainer = oContainer.nextElementSibling))
                utils.change_class(oContainer, "open", "closed");
        }
    }

    persist_tree_state(tree, name, state);
}

export function persist_tree_state(tree, name, state)
{
    ajax.get_url("tree_openclose.py?tree=" + encodeURIComponent(tree)
            + "&name=" + encodeURIComponent(name) + "&state=" + state);
}
