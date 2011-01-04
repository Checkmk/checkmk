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

// ----------------------------------------------------------------------------
// general function
// ----------------------------------------------------------------------------

function hilite_icon(oImg, onoff) {
    src = oImg.src;
    if (onoff == 0)
        oImg.src = oImg.src.replace("hi.png", "lo.png");
    else
        oImg.src = oImg.src.replace("lo.png", "hi.png");
}


function get_url(url, handler, data, errorHandler) {
    if (window.XMLHttpRequest) {
        var AJAX = new XMLHttpRequest();
    } else {
        var AJAX = new ActiveXObject("Microsoft.XMLHTTP");
    }
    
    // Dynamic part to prevent caching
    var dyn = "_t="+Date.parse(new Date());
    if (url.indexOf('\?') !== -1) {
        dyn = "&"+dyn;
    } else {
        dyn = "?"+dyn;
    }
    
    if (AJAX) {
        AJAX.open("GET", url + dyn, true);
        if (typeof handler === 'function')
            AJAX.onreadystatechange = function() {
                if (AJAX.readyState == 4)
                    if(AJAX.status == 200)
                        handler(data, AJAX.responseText);
                    else
                        if(typeof errorHandler !== 'undefined')
                            errorHandler(data, AJAX.status);
            }
        AJAX.send(null);
        return true;
    } else {
        return false;
    }
}

function get_url_sync(url) {
    if (window.XMLHttpRequest) {
        var AJAX = new XMLHttpRequest();
    } else {
        var AJAX = new ActiveXObject("Microsoft.XMLHTTP");
    }
    
    AJAX.open("GET", url, false);                             
    AJAX.send(null);
    return AJAX.responseText;                                         
}


// ----------------------------------------------------------------------------
// GUI styling
// ----------------------------------------------------------------------------

function filter_activation(oid)
{
    var selectobject = document.getElementById(oid);
    var usage = selectobject.value;
    var oTd = selectobject.parentNode.parentNode.childNodes[2];
    var pTd = selectobject.parentNode;
    pTd.setAttribute("className", "usage" + usage);
    pTd.setAttribute("class",     "usage" + usage); 
    oTd.setAttribute("class",     "widget" + usage);
    oTd.setAttribute("className", "widget" + usage);

    var disabled = usage != "hard" && usage != "show";
    for (var i in oTd.childNodes) {
        oNode = oTd.childNodes[i];
        if (oNode.nodeName == "INPUT" || oNode.nodeName == "SELECT") {
            oNode.disabled = disabled;
        }
    }

    p = null;
    oTd = null;
    selectobject = null;
}

var gNumOpenTabs = 0;

function toggle_tab(linkobject, oid)
{
    var table = document.getElementById(oid);
    if (table.style.display == "none") {
        table.style.display = "";
        linkobject.setAttribute("className", "left open");
        linkobject.setAttribute("class", "left open");

        // Stop the refresh while at least one tab is open
        gNumOpenTabs += 1;
        setReload(0);
    }
    else {
        table.style.display = "none";
        linkobject.setAttribute("className", "left closed");
        linkobject.setAttribute("class", "left closed");

        // Re-Enable the reload
        gNumOpenTabs -= 1;
        if(gNumOpenTabs == 0)
            setReload(gReloadTime);
    }
    table = null;
}

function hover_tab(linkobject)
{
    linkobject.style.backgroundImage = "url(images/metanav_button_hi.png)";
}

function unhover_tab(linkobject)
{
    linkobject.style.backgroundImage = "url(images/metanav_button.png)";
}

// ----------------------------------------------------------------------------
// PNP graph handling
// ----------------------------------------------------------------------------

function pnp_error_response_handler(data, statusCode) {
    fallback_graphs(data);
}

function pnp_response_handler(data, code) {
    var valid_response = true;
    var response = null;
    try {
        response = eval(code);
        for(var i in response) {
            var graph = response[i];
            create_graph(data, '&' + graph['image_url'].replace('&view=1', ''));
            i = null;
        }
    } catch(e) {
        valid_response = false;
    }

    if(!valid_response)
        fallback_graphs(data);
}

// Fallback bei doofer/keiner Antwort
function fallback_graphs(data) {
   for(var i in [0, 1, 2, 3, 4, 5, 6, 7]) {
       create_graph(data, '&host=' + data['host'] + '&srv=' + data['service'] + '&source=' + i);
   }
}

function create_graph(data, params) {
    var urlvars = params + '&theme=multisite&baseurl='+data['base_url'];
    var container = document.getElementById(data['container']);

    var img = document.createElement('img');
    img.src = data['pnp_url'] + 'index.php/image?view=' + data['view'] + urlvars;

    if (data.with_link) {
        var link = document.createElement('a');
        link.href = data['pnp_url'] + 'index.php/graph?' + urlvars;
        link.appendChild(img);
        container.appendChild(link);
    }
    else {
        container.appendChild(img);
    }

    img = null;
    link = null;
    container = null;
    urlvars = null;
}

function render_pnp_graphs(container, site, host, service, pnpview, base_url, pnp_url, with_link) {
    var data = { 'container': container, 'base_url': base_url,
                 'pnp_url':   pnp_url,   'site':     site,
                 'host':      host,      'service':  service,
                 'with_link': with_link, 'view':     pnpview};
    get_url(pnp_url + 'index.php/json?&host=' + host + '&srv=' + service + '&source=0',
            pnp_response_handler, data, pnp_error_response_handler);
}

// ----------------------------------------------------------------------------
// Synchronous action handling
// ----------------------------------------------------------------------------
// Protocol is:
// For regular response:
// [ 'OK', 'last check', 'exit status plugin', 'output' ]
// For timeout:
// [ 'TIMEOUT', 'output' ]
// For error:
// [ 'ERROR', 'output' ]
// Everything else:
// <undefined> - Unknown format. Simply echo.

function actionResponseHandler(oImg, code) {
    var validResponse = true;
    var response = null;

    try {
        response = eval(code);
    } catch(e) {
        validResponse = false;
    }

    if(validResponse && response[0] === 'OK') {
        oImg.src   = 'images/icon_reload.gif';
        window.location.reload();
    } else if(validResponse && response[0] === 'TIMEOUT') {
        oImg.src   = 'images/icon_reload_failed.gif';
        oImg.title = 'Timeout while performing action: ' + response[1];
    } else if(validResponse) {
        oImg.src   = 'images/icon_reload_failed.gif';
        oImg.title = 'Problem while processing - Response: ' + response.join(' ');
    } else {
        oImg.src   = 'images/icon_reload_failed.gif';
        oImg.title = 'Invalid response: ' + response;
    }

    response = null;
    validResponse = null;
    oImg = null;
}

function performAction(oLink, action, type, site, name1, name2) {
    var oImg = oLink.childNodes[0];
    oImg.src = 'images/icon_reloading.gif';

    // Chrome and IE are not animating the gif during sync ajax request
    // So better use the async request here
    get_url('nagios_action.py?action='+action+'&site='+site+'&host='+name1+'&service='+name2,
            actionResponseHandler, oImg);
    oImg = null;
}

/* -----------------------------------------------------
   view editor
   -------------------------------------------------- */
function delete_view_column(oImg) {
    var oDiv = oImg;
    while (oDiv.nodeName != "DIV")
        oDiv = oDiv.parentNode;
    oDiv.parentNode.removeChild(oDiv);
    oDiv = null;
}


// ----------------------------------------------------------------------------
// page reload stuff
// ----------------------------------------------------------------------------

//Stores the reload timer object
var gReloadTimer = null;
// This stores the last refresh time of the page (But never 0)
var gReloadTime = 0;

// Highlights/Unhighlights a refresh button
function toggleRefreshButton(s, enable) {
    var o = document.getElementById('button-refresh-' + s);
    if(o) {
        if(enable) {
            o.setAttribute("className", "left w40 selected");
            o.setAttribute("class", "left w40 selected");
        } else {
            o.setAttribute("className", "left w40");
            o.setAttribute("class", "left w40");
        }
    }
    o = null;
}


// When called with one or more parameters parameters it reschedules the
// timer to the given interval. If the parameter is 0 the reload is stopped.
// When called with two parmeters the 2nd one is used as new url.
function setReload(secs, url) {
    if(typeof url === 'undefined')
        url = '';
    
    if (gReloadTimer) {
        toggleRefreshButton(0, false);
        toggleRefreshButton(gReloadTime, false);
        clearTimeout(gReloadTimer);
    }

    toggleRefreshButton(secs, true);

    if (secs !== 0) {
        gReloadTime  = secs;
        gReloadTimer = setTimeout("handleReload('" + url + "')", Math.ceil(parseFloat(secs) * 1000));
    }
}

function handleReload(url) {
    if (url === '')
        window.location.reload(false);
    else
        window.location.href = url;
}
