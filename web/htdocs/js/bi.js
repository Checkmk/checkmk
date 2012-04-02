// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2012             mk@mathias-kettner.de |
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

function toggle_subtree(oImg)
{
    var oSubtree = oImg.parentNode.childNodes[6];
    var url = "bi_save_treestate.py?path=" + escape(oSubtree.id);

    if (oSubtree.style.display == "none") {
        oSubtree.style.display = "";
        url += "&state=open";
        toggle_folding(oImg, 1);
    }
    else {
        oSubtree.style.display = "none";
        url += "&state=closed";
        toggle_folding(oImg, 0);
    }
    oSubtree = null;
    get_url(url);
}

function toggle_bi_box(oDiv)
{
    // oDiv.style.display = "none";
    if (oDiv.style.borderStyle != "dashed") {
        oDiv.style.boxShadow = "none";
        oDiv.style.borderStyle = "dashed";
        oDiv.style.BiBoxHidden = true;
    }
    else {
        oDiv.style.boxShadow = "1px 1px 3px #000";
        oDiv.style.borderStyle = "solid";
        oDiv.style.BiBoxHidden = false;
    }

    // find child nodes that belong to this node
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


function toggle_assumption(oImg, site, host, service)
{
    // get current state
    var current = oImg.src;
    while (current.indexOf('/') > -1)
        current = current.substr(current.indexOf('/') + 1);
    current = current.substr(7);
    current = current.substr(0, current.length - 4);
    if (current == 'none')
        current = '1';
    else if (current == '3')
        current = '0'
    else if (current == '0')
        current = 'none'
    else if (current == '2' && service == '')
        current = 'none'
    else
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
