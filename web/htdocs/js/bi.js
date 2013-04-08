// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

function bi_toggle_subtree(oImg, lazy)
{
    if (oImg.tagName == "SPAN") { // clicked on title,
        oImg = oImg.previousSibling;
    }
    var oSubtree = oImg.parentNode.childNodes[6];
    var url = "bi_save_treestate.py?path=" + escape(oSubtree.id);
    var do_open;

    if (oSubtree.style.display == "none") {
        oSubtree.style.display = "";
        url += "&state=open";
        toggle_folding(oImg, 1);
        do_open = true;
    }
    else {
        oSubtree.style.display = "none";
        url += "&state=closed";
        toggle_folding(oImg, 0);
        do_open = false;
    }
    oSubtree = null;
    if (lazy && do_open)
        get_url(url, bi_update_tree, oImg);
    else
        get_url(url);

}

function bi_update_tree(oImg, code)
{
    // Deactivate clicking - the update can last a couple
    // of seconds. In that time we must inhibit further clicking.
    oImg.onclick = null;

    // First find enclosding <div class=bi_tree_container>
    var oDiv = oImg;
    while (oDiv.className != "bi_tree_container") {
        oDiv = oDiv.parentNode;
    }
    var url = "bi_render_tree.py?" + oDiv.id;
    get_url(url, bi_update_tree_response, oDiv);
}

function bi_update_tree_response(oDiv, code) {
    oDiv.innerHTML = code;
    executeJSbyObject(oDiv);
}

function bi_toggle_box(oDiv, lazy)
{
    var url = "bi_save_treestate.py?path=" + escape(oDiv.id);
    var do_open;

    if (oDiv.className.indexOf("open") >= 0) {
        if (lazy)
            return; // do not close in lazy mode
        oDiv.className = oDiv.className.replace(/open/, "closed");
        url += "&state=closed";
        do_open = false;
    }
    else {
        oDiv.className = oDiv.className.replace(/closed/, "open");
        url += "&state=open";
        do_open = true;
    }

    if (lazy && do_open)
        get_url(url, bi_update_tree, oDiv);
    else {
        get_url(url);
        // find child nodes that belong to this node and
        // control visibility of those. Note: the BI child nodes
        // are *no* child nodes in HTML but siblings!
        var found = 0;
        for (var i in oDiv.parentNode.childNodes) {
            var onode = oDiv.parentNode.childNodes[i];
            if (onode == oDiv)
                found = 1;
            else if (found == 1)
                found ++;
            else if (found) {
                if (onode.style.display)
                    onode.style.display = "";
                else
                    onode.style.display = "none";
                return;
            }
        }
    }

}


function toggle_assumption(oImg, site, host, service)
{
    // get current state
    var current = oImg.src;
    while (current.indexOf('/') > -1)
        current = current.substr(current.indexOf('/') + 1);
    current = current.substr(7);
    current = current.substr(0, current.length - 4);
    if (current == 'none')
        // Assume WARN when nothing assumed yet
        current = '1';
    else if (current == '3' || (service == '' && current == '2'))
        // Assume OK when unknown assumed (or when critical assumed for host)
        current = '0'
    else if (current == '0')
        // Disable assumption when ok assumed
        current = 'none'
    else
        // In all other cases increas the assumption
        current = parseInt(current) + 1;

    var url = "bi_set_assumption.py?site=" + encodeURIComponent(site)
            + '&host=' + encodeURIComponent(host);
    if (service) {
        url += '&service=' + encodeURIComponent(service);
    }
    url += '&state=' + current;
    oImg.src = "images/assume_" + current + ".png";
    get_url(url);
}
