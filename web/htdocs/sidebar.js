// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2010             mk@mathias-kettner.de |
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

// Load stylesheet for sidebar

// Get object of script (myself)
var oSidebar = document.getElementById("check_mk_sidebar");

var url = '';
for(var i in oSidebar.childNodes)
    if(oSidebar.childNodes[i].nodeName == 'SCRIPT') {
        url = oSidebar.childNodes[i].src.replace("sidebar.js", "");
        break;
    }

if(url == '')
    alert('ERROR: Unable to determine the script location. Problem finding sidebar.js inside the check_mk_sidebar container.');


var oLink = document.createElement('link');
oLink.href = url + "check_mk.css";
oLink.rel = 'stylesheet';
oLink.type = 'text/css';
document.body.appendChild(oLink);

var oDiv = document.createElement('div');
oDiv.innerHTML = get_url(url + 'sidebar.py');
oSidebar.appendChild(oDiv);

// Cleaning up DOM links
oDiv = null;
oLink = null;
oSidebar = null;

function get_url(url) {
    if (window.XMLHttpRequest) {
        var AJAX = new XMLHttpRequest();
    } else {
        var AJAX = new ActiveXObject("Microsoft.XMLHTTP");
    }

    // Dynamic part to prevent caching
    var dyn = "_t="+Date.parse(new Date());
    if(url.indexOf('\?') !== -1) {
        dyn = "&"+dyn;
    } else {
        dyn = "?"+dyn;
    }
    
    if (AJAX) {
        AJAX.open("GET", url + dyn, false);
        AJAX.send(null);
        return AJAX.responseText;
    } else {
        return false;
    }
}

function toggle_sidebar_snapin(oH2, url) {
    var childs = oH2.parentNode.childNodes;
    for (var i in childs) {
        child = childs[i];
        if (child.tagName == "DIV") {
            var oContent = child;
            break;
        }
    }
    // FIXME: Does oContent really exist?
    var closed = oContent.style.display == "none";
    if (closed)
        oContent.style.display = "";
    else
        oContent.style.display = "none";
    /* make this persistent -> save */
    get_url(url + (closed ? "open" : "closed")); 
    oContent = null;
    childs = null;
}

function switch_site(baseuri, switchvar) {
    get_url(baseuri + "/switch_site.py?" + switchvar);
    parent.frames[1].location.reload(); /* reload main frame */
}

function sidebar_scheduler() {
    var timestamp = Date.parse(new Date()) / 1000;
    var newcontent = "";
    for (var i in refresh_snapins) { 
        name    = refresh_snapins[i][0];
        refresh = refresh_snapins[i][1];
        if (timestamp % refresh == 0) {
            newcontent = get_url(url + "/sidebar_snapin.py?name=" + name);
            var oSnapin = document.getElementById("snapin_" + name);
            oSnapin.innerHTML = newcontent;
            oSnapin = null;
        }
    }
    setTimeout(function(){sidebar_scheduler();}, 1000);
}

function add_bookmark(baseurl) {
    href = parent.frames[1].location;
    title = parent.frames[1].document.title;
    get_url(baseurl + "/add_bookmark.py?title=" + escape(title) + "&href=" + escape(href));
}

function hilite_icon(oImg, onoff) {
    src = oImg.src;
    if (onoff == 0)
        oImg.src = oImg.src.replace("hi.png", "lo.png");
    else
        oImg.src = oImg.src.replace("lo.png", "hi.png");
}
