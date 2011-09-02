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

// Some browsers don't support indexOf on arrays. This implements the
// missing method
if (!Array.prototype.indexOf)
{
  Array.prototype.indexOf = function(elt /*, from*/)
  {
    var len = this.length;

    var from = Number(arguments[1]) || 0;
    from = (from < 0)
         ? Math.ceil(from)
         : Math.floor(from);
    if (from < 0)
      from += len;

    for (; from < len; from++)
    {
      if (from in this &&
          this[from] === elt)
        return from;
    }
    return -1;
  };
}

// This implements getElementsByClassName() for IE<9
if (!document.getElementsByClassName) {
  document.getElementsByClassName = function(className, root, tagName) {
    root = root || document.body;
 
    // at least try with querySelector (IE8 standards mode)
    // about 5x quicker than below
    if (root.querySelectorAll) {
        tagName = tagName || '';
        return root.querySelectorAll(tagName + '.' + className);
    }
 
    // and for others... IE7-, IE8 (quirks mode), Firefox 2-, Safari 3.1-, Opera 9-
    var tagName = tagName || '*', _tags = root.getElementsByTagName(tagName), _nodeList = [];
    for (var i = 0, _tag; _tag = _tags[i++];) {
        if (this.hasClass(_tag, className)) {
            _nodeList.push(_tag);
        }
    }
    return _nodeList;
}
}

function getTarget(event) {
  return event.target ? event.target : event.srcElement;
}

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
    var dyn = "_ajaxid="+Date.parse(new Date());
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
                    if (AJAX.status == 200) {
                        handler(data, AJAX.responseText);
                    }
                    else {
                        if (typeof errorHandler !== 'undefined')
                            errorHandler(data, AJAX.status);
                    }
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


// Updates the contents of a snapin container after get_url
function updateContents(id, code) {
  var obj = document.getElementById(id);
  if (obj) {
    obj.innerHTML = code;
    executeJS(id);
    obj = null;
  }
}

// There may be some javascript code in the html code rendered by
// sidebar.py. Execute it here. This is needed in some browsers.
function executeJS(objId) {
  // Before switching to asynchronous requests this worked in firefox
  // out of the box. Now it seems not to work with ff too. So now
  // executing the javascript manually.
  // if (!isFirefox()) {
  var obj = document.getElementById(objId);
  var aScripts = obj.getElementsByTagName('script');
  for(var i = 0; i < aScripts.length; i++) {
    if (aScripts[i].src && aScripts[i].src !== '') {
      var oScr = document.createElement('script');
      oScr.src = aScripts[i].src;
      document.getElementsByTagName("HEAD")[0].appendChild(oScr);
      oScr = null;
    } else {
      try {
    	  eval(aScripts[i].text);
      } catch(e) {alert(aScripts[i].text + "\nError:" + e.message);}
    }
  }
  aScripts = null;
  obj = null;
}

function isFirefox() {
  return navigator.userAgent.indexOf("Firefox") > -1;
}
function pageHeight() {
  var h;
  
  if (window.innerHeight !== null && typeof window.innerHeight !== 'undefined' && window.innerHeight !== 0)
    h = window.innerHeight;
  else if (document.documentElement && document.documentElement.clientHeight)
    h = document.documentElement.clientHeight;
  else if (document.body !== null)
    h = document.body.clientHeight;
  else
    h = null;
  
  return h;
}

function pageWidth() {
  var w;
  
  if (window.innerWidth !== null && typeof window.innerWidth !== 'undefined' && window.innerWidth !== 0)
    w = window.innerWidth;
  else if (document.documentElement && document.documentElement.clientWidth)
    w = document.documentElement.clientWidth;
  else if (document.body !== null)
    w = document.body.clientWidth;
  else
    w = null;
  
  return h;
}

/**
 * Function gets the value of the given url parameter
 */
function getUrlParam(name) {
    var name = name.replace('[', '\\[').replace(']', '\\]');
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)");
    var results = regex.exec(window.location);
    if(results === null)
        return '';
    else
        return results[1];
}

/**
 * Function creates a new cleaned up URL
 * - Can add/overwrite parameters
 * - Removes _* parameters
 */
function makeuri(addvars) {
    var tmp = window.location.href.split('?');
    var base = tmp[0];
    tmp = tmp[1].split('#');
    tmp = tmp[0].split('&');
    var len = tmp.length;
    var params = [];
    var pair = null;

    // Skip unwanted parmas
    for(var i = 0; i < tmp.length; i++) {
        pair = tmp[i].split('=');
        if(pair[0][0] == '_')
            continue;
        params.push(tmp[i]);
    }

    // Add new params
    for (var key in addvars) {
        params.push(key + '=' + addvars[key]);
    }
    
    return base + '?' + params.join('&')
}

// ----------------------------------------------------------------------------
// GUI styling
// ----------------------------------------------------------------------------

function filter_activation(oid)
{
    var selectobject = document.getElementById(oid);
    if (!selectobject) {
        alert("Could not find element " + oid + "!");
        return;
    }
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

function toggle_tab(linkobject, oid)
{
    var table = document.getElementById(oid);
    if (table.style.display == "none") {
        table.style.display = "";
        linkobject.setAttribute("className", "left open");
        linkobject.setAttribute("class", "left open");
    }
    else {
        table.style.display = "none";
        linkobject.setAttribute("className", "left closed");
        linkobject.setAttribute("class", "left closed");
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
    // PNP versions that do not have the JSON webservice respond with
    // 404. Current version with the webservice answer 500 if the service
    // in question does not have any PNP graphs. So we paint the fallback
    // graphs only if the respone code is 404 (not found).
    if (parseInt(statusCode) == 404) 
        fallback_graphs(data);
}

function pnp_response_handler(data, code) {
    var valid_response = true;
    var response = null;
    try {
        response = eval(code);
        for(var i = 0; i < response.length; i++) {
            var graph = response[i];
            var view = data['view'] == '' ? '0' : data['view'];
            create_graph(data, '&' + graph['image_url'].replace('&view='+view, ''));
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
    for(var i = 0; i < 8; i++) {
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
    get_url(pnp_url + 'index.php/json?&host=' + host + '&srv=' + service + '&source=0&view=' + pnpview,
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

function get_column_container(oImg) {
    var oNode = oImg;
    while (oNode.nodeName != "DIV")
        oNode = oNode.parentNode;
    return oNode;
}

function toggle_button(oDiv, name, display) {
    var parts = oDiv.id.split('_');
    var type  = parts[0];
    var num   = parts[2];
    var o     = document.getElementById(type+'_'+name+'_'+num);
    if (o)
        if (display)
            o.style.display = '';
        else
            o.style.display = 'none';
    o = null;
}

function column_swap_ids(o1, o2) {
    var parts = o1.id.split('_');
    var type  = parts[0];
    var num1  = parts[2];
    var num2  = o2.id.split('_')[2];

    var o1 = null, o2 = null;
    var objects = [ '', '_editor', '_up', '_down', '_label', '_link', '_tooltip' ];
    for(var i = 0,len = objects.length; key = type+objects[i]+'_', i < len; i++) {
        o1 = document.getElementById(key + num1);
        o2 = document.getElementById(key + num2);
        if(o1 && o2) {
            if(o1.id && o2.id) {
                o1.id = key + num2;
                o2.id = key + num1;
            }
            if(o1.name && o2.name) {
                o1.name = key + num2;
                o2.name = key + num1;
            }
            if(objects[i] === '_label') {
                o1.innerHTML = 'Column ' + num2 + ':'
                o2.innerHTML = 'Column ' + num1 + ':'
            }
        }
    }
    objects = null;
    o1 = null;
    o2 = null;
}

function add_view_column_handler(id, code) {
    // Can not simply add the new code to the innerHTML code of the target
    // container. So first creating a temporary container and fetch the
    // just created DOM node of the editor fields to add it to the real
    // container afterwards.
		var tmpContainer = document.createElement('div');
		tmpContainer.innerHTML = code;
		var oNewEditor = tmpContainer.lastChild;

    var oContainer = document.getElementById('ed_'+id).firstChild;
    oContainer.appendChild(oNewEditor);
		tmpContainer = null;

    if (oContainer.lastChild.previousSibling)
        fix_buttons(oContainer, oContainer.lastChild.previousSibling);
    oContainer = null;
}

function add_view_column(id, datasourcename, prefix) {
    get_url('get_edit_column.py?ds=' + datasourcename + '&pre=' + prefix
          + '&num=' + (document.getElementById('ed_'+id).firstChild.childNodes.length + 1),
            add_view_column_handler, id);
}

function delete_view_column(oImg) {
    var oNode = get_column_container(oImg);
    var oContainer = oNode.parentNode;

    var prev = oNode.previousSibling;
    var next = oNode.nextSibling;

    oContainer.removeChild(oNode);

    if (prev)
        fix_buttons(oContainer, prev);
    if (next)
        fix_buttons(oContainer, next);

    oContainer = null;
    oNode = null;
}

function fix_buttons(oContainer, oNode) {
    var num = oContainer.childNodes.length;
    if (num === 0)
        return;

    if (oContainer.firstChild == oNode)
        toggle_button(oNode, 'up', false);
    else
        toggle_button(oNode, 'up', true);
    if (oContainer.lastChild == oNode)
        toggle_button(oNode, 'down', false);
    else
        toggle_button(oNode, 'down', true);
}

function move_column_up(oImg) {
    var oNode = get_column_container(oImg);
    var oContainer = oNode.parentNode;
    
    // The column is the first one - skip moving
    if (oNode.previousSibling === null)
        return;

    oContainer.insertBefore(oNode, oNode.previousSibling);

    fix_buttons(oContainer, oNode);
    fix_buttons(oContainer, oNode.nextSibling);

    column_swap_ids(oNode, oNode.nextSibling);

    oContainer = null;
    oNode = null;
    oImg = null;
}

function move_column_down(oImg) {
    var oNode = get_column_container(oImg);
    var oContainer = oNode.parentNode;
    
    // The column is the last one - skip moving
    if (oNode.nextSibling === null)
        return;

    if (oContainer.lastChild == oNode.nextSibling)
        oContainer.appendChild(oNode);
    else
        oContainer.insertBefore(oNode, oNode.nextSibling.nextSibling);

    fix_buttons(oContainer, oNode);
    fix_buttons(oContainer, oNode.previousSibling);

    column_swap_ids(oNode, oNode.previousSibling);

    oContainer = null;
    oNode = null;
    oImg = null;
}

function toggle_join_fields(prefix, n, obj) {
    var r1 = document.getElementById(prefix + 'join_index_row' + n);
    var r2 = document.getElementById(prefix + 'title_row' + n)
    if(obj.options[obj.selectedIndex].text.substr(0, 8) == 'SERVICE:') {
        r1.style.display = '';
        r2.style.display = '';
    } else {
        r1.style.display = 'none';
        r2.style.display = 'none';
        r1.childNodes[1].firstChild.value = '';
        r2.childNodes[1].firstChild.value = '';
    }
    r1 = null;
    r2 = null;
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
        startReloadTimer(url);
    }
}

function startReloadTimer(url) {
    gReloadTimer = setTimeout("handleReload('" + url + "')", Math.ceil(parseFloat(gReloadTime) * 1000));
}

function updateHeaderTime() {
    var oTime = document.getElementById('headertime');
    if(!oTime)
        return;

    var t = new Date();

    var hours = t.getHours();
    if(hours < 10)
        hours = "0" + hours;

    var min = t.getMinutes();
    if(min < 10)
        min = "0" + min;

    oTime.innerHTML = hours + ':' + min

    min   = null;
    hours = null;
    t     = null;
    oTime = null;
}

var g_reload_error = false;
function handleContentReload(_unused, code) {
    g_reload_error = false;
    var o = document.getElementById('data_container');
    o.innerHTML = code;
    executeJS('data_container');

    // Update the header time
    updateHeaderTime();

    aScripts = null;
    o = null;
    startReloadTimer('');
}

function handleContentReloadError(data, statusCode) {
    if(!g_reload_error) {
        var o = document.getElementById('data_container');
        o.innerHTML = '<div class=error>Update failed (' + statusCode
                      + '). The shown data might be outdated</div>' + o.innerHTML;
        o = null;
        g_reload_error = true;
    }

    // Continue update after the error
    startReloadTimer('');
}

function handleReload(url) {
    // FiXME: Nicht mehr die ganze Seite neu laden, wenn es ein DIV "data_container" gibt.
    // In dem Fall wird die aktuelle URL aus "window.location.href" geholt, für den Refresh
    // modifiziert, der Inhalt neu geholt und in das DIV geschrieben.
    if(!document.getElementById('data_container') || url !== '') {
        if (url === '')
            window.location.reload(false);
        else
            window.location.href = url;
    } else {
        // Enforce specific display_options to get only the content data
        var display_options = getUrlParam('display_options');
        var opts = [ 'h', 't', 'b', 'f', 'c', 'o', 'd', 'e', 'r' ];
        for(var i = 0; i < opts.length; i++) {
            if(display_options.indexOf(opts[i].toUpperCase()) > -1)
                display_options = display_options.replace(opts[i].toUpperCase(), opts[i]);
            else
                display_options += opts[i];
        }
        opts = null;

        var params = {'_display_options': display_options};
        var real_display_options = getUrlParam('display_options');
        if(real_display_options !== '')
            params['display_options'] = real_display_options;

        // Handle user selections. If g_selected_rows has elements replace/set the
        // parameter selected_rows with the current selected rows as value.
        // otherwhise clear the parameter
        params['selected_rows'] = g_selected_rows.join(',');

        var url = makeuri(params);
        display_options = null;
        get_url(url, handleContentReload, '', handleContentReloadError);
        url = null;
    }
}

// --------------------------------------------------------------------------
// BI
// --------------------------------------------------------------------------
//
var fold_steps = [ 0, 10, 10, 15, 20, 30, 40, 55, 80 ];

function toggle_folding(oImg, state) {
    // state
    // 0: is currently opened and should be closed now
    // 1: is currently closed and should be opened now
    setTimeout(function() { folding_step(oImg, state); }, 0);
}

function folding_step(oImg, state, step) {
    // Initialize unset step
    if(typeof step === 'undefined')
        if(state == 1)
            step = 1;
        else
            step = 8;
    
    oImg.src = "images/tree_" + step + "0.png";

    if(state == 1) {
        if(step == 9) {
            oImg = null;
            return;
        }
        step += 1;
    } else {
        if(step == 0) {
            oImg = null;
            return;
        }
        step -= 1;
    }

    setTimeout(function() { folding_step(oImg, state, step); }, fold_steps[step]);
}

function toggle_tree_state(tree, name, oContainer) {
    var state;
    if(oContainer.style.display == 'none') {
        oContainer.style.display = '';
        state = 'on';
    } else {
        oContainer.style.display = 'none';
        state = 'off';
    }
    get_url('tree_openclose.py?tree=' + escape(tree) + '&name=' + escape(name) + '&state=' + state);
    oContainer = null;
}

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

function toggle_foldable_container(treename, id) {
    var oImg = document.getElementById('treeimg.' + treename + '.' + id);
    var oBox = document.getElementById('tree.' + treename + '.' + id);
    toggle_tree_state(treename, id, oBox);
    toggle_folding(oImg, oBox.style.display != "none");
    oImg = null;
    oBox = null;
}

// TODO: Why is this not in a bi.js?
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

/*
 * +----------------------------------------------------------------------+
 * |       ____                          _           _                    |
 * |      |  _ \ _____      __  ___  ___| | ___  ___| |_ ___  _ __        |
 * |      | |_) / _ \ \ /\ / / / __|/ _ \ |/ _ \/ __| __/ _ \| '__|       |
 * |      |  _ < (_) \ V  V /  \__ \  __/ |  __/ (__| || (_) | |          |
 * |      |_| \_\___/ \_/\_/   |___/\___|_|\___|\___|\__\___/|_|          |
 * |                                                                      |
 * +----------------------------------------------------------------------+
 */

// Holds the row numbers of all selected rows
var g_selected_rows = [];

function lightenColor(color, rD, gD, bD) {
    if(color == 'transparent' || color == 'rgba(0, 0, 0, 0)')
        return color;

    if(color.charAt(0) === 'r') {
        var parts = color.substring(color.indexOf('(')+1, color.indexOf(')')).split(',', 3);
        var r = parseInt(parts[0]);
        var g = parseInt(parts[1]);
        var b = parseInt(parts[2]);
    } else if(color.charAt(0) === '#' && color.length == 7) {
        var r = parseInt(color.substring(1, 3), 16);
        var g = parseInt(color.substring(3, 5), 16);
        var b = parseInt(color.substring(5, 7), 16);
    } else if(color.charAt(0) === '#' && color.length == 4) {
        var r = parseInt(color.substring(1, 2) + color.substring(1, 2), 16);
        var g = parseInt(color.substring(2, 3) + color.substring(2, 3), 16);
        var b = parseInt(color.substring(3, 4) + color.substring(3, 4), 16);
    } else {
        alert('Invalid color definition: ' + color);
        return color;
    }

    var brightness = (r*299 + g*587 + b*114) / 1000;
    if (brightness > 125) {
        rD *= -1;
        gD *= -1;
        bD *= -1;
    }

    r += rD;  if (r > 255) r = 255;  if (r < 0) r = 0;
    g += gD;  if (g > 255) g = 255;  if (g < 0) g = 0;
    b += bD;  if (b > 255) b = 255;  if (b < 0) b = 0;

    code  = r < 16 ? "0"+r.toString(16) : r.toString(16);
    code += g < 16 ? "0"+g.toString(16) : g.toString(16);
    code += b < 16 ? "0"+b.toString(16) : b.toString(16);

    return "#" + code.toUpperCase();
}

function real_style(obj, attr) {
    var st;
    if(document.defaultView && document.defaultView.getComputedStyle)
        st = document.defaultView.getComputedStyle(obj, null).getPropertyValue(attr);
    else
        st = obj.currentStyle[attr];

    if(typeof(st) == 'undefined') { 
        st = 'transparent';
    }

    // If elem is a TD and has no background find the backround of the parent
    // e.g. the TR and then set this color as background for the TD
    if(obj.tagName == 'TD' && (st == 'transparent' || st == 'rgba(0, 0, 0, 0)'))
        st = real_style(obj.parentNode, attr);

    return st;
}

function highlight_row(row_num, on, ty) {
    var elems = document.getElementsByClassName('dr_' + row_num);
    for(var i = 0; i < elems.length; i++)
        highlight_elem(elems[i], on, ty);
}

function highlight_elem(elem, on, ty) {
    // Find all elements below "elem" with a defined background-color and change it
    var bg_color = real_style(elem, 'background-color');
    if(on) {
        if(ty == 'hover' && typeof(elem['click_orig_bg']) === 'undefined') {
            elem[ty + '_orig_bg'] = bg_color;
            var x = lightenColor(elem['hover_orig_bg'], 40, 40, -20);
            elem.style.backgroundColor = lightenColor(elem['hover_orig_bg'], 40, 40, -20);
        } else if(ty == 'click') {
            elem[ty + '_orig_bg'] = bg_color;
            if(typeof(elem['hover_orig_bg']) !== 'undefined')
                var calc_bg_color = elem['hover_orig_bg'];
            else
                var calc_bg_color = bg_color;
            var x = lightenColor(calc_bg_color, 40, 40, -40);
            elem.style.backgroundColor = lightenColor(calc_bg_color, 40, 40, -40);
        }
    } else {
        // Restore selection color when hovering over selected objects
        if(ty == 'hover' && typeof(elem['click_orig_bg']) !== 'undefined') {
        } else if(ty == 'hover') {
            elem.style.backgroundColor = elem[ty + '_orig_bg'];
            elem[ty + '_orig_bg'] = undefined;
        } else {
            elem.style.backgroundColor = elem[ty + '_orig_bg'];
            elem[ty + '_orig_bg'] = undefined;
        }
    }

    var childs = elem.childNodes;
    for(var i = 0; i < childs.length; i++)
        if(childs[i].nodeName !== '#text')
            highlight_elem(childs[i], on, ty);
}

function remove_selected_rows(row_num) {
    for(var i = g_selected_rows.length - 1; i >= 0; i--) {
        if(g_selected_rows[i] != row_num) {
            highlight_row(g_selected_rows[i], false, 'click');
            highlight_row(g_selected_rows[i], false, 'hover');
            g_selected_rows.splice(i, 1);
        }
    }
}

function toggle_row(e, row) {
    if(!e)
        e = window.event;

    // Skip handling clicks on links/images/...
    var target = getTarget(e);
    if(target.tagName != 'TD')
        return true;

    var row_num = parseInt(row.row_num);

    // When CTRL is not pressed, remove the selection
    if(!e.ctrlKey)
        remove_selected_rows(row_num);

    // Is SHIFT pressed?
    // Yes:
    //   Select all from the last selection

    // Is the current row already selected?
    var row_pos = g_selected_rows.indexOf(row_num);
    if(row_pos > -1) {
        // Yes: Unselect it
        highlight_row(row_num, false, 'click');
        g_selected_rows.splice(row_pos, 1);
    } else {
        // No:  Select it
        highlight_row(row_num, true, 'click');
        g_selected_rows.push(row_num);
    }

    if(e.stopPropagation)
        e.stopPropagation();
    e.cancelBubble = true;

    // Disable the default events for all the different browsers
    if(e.preventDefault)
        e.preventDefault();
    else
        e.returnValue = false;
    return false;
}

function disable_selection(e) {
    if(!e)
        e = window.event;

    // Skip handling clicks on links/images/...
    var target = getTarget(e);
    if(target.tagName != 'TD')
        return true;

    // Firefox handling
    if(typeof target.style.MozUserSelect != 'undefined')
        target.style.MozUserSelect = 'none';

    // All others
    return false;
}

function get_row_num(elem) {
    // FIXME: Maybe performance problem. Would be better to have a
    // dedicated attribute for the data row number
    var classes = elem.className.split(' ');
    for(var i = 0; i < classes.length; i++)
        if(classes[i].indexOf('dr_') > -1)
            return parseInt(classes[i].split('_', 2)[1]);
}

function table_init_rowselect(oTable) {
    // Get all "data row" elements
    var childs = document.getElementsByClassName('dr');

    for(var i = 0; i < childs.length; i++) {
        if(childs[i].tagName != 'TD' && childs[i].tagName != 'DIV')
            continue;

        var elem = childs[i];
        var row_num = get_row_num(elem);
        elem.row_num = row_num;

        // Handle the initial selections
        if(g_selected_rows.indexOf(row_num) > -1) {
            highlight_elem(elem, true, 'hover');
            highlight_elem(elem, true, 'click');
        }

        elem.onmouseover = function() {
            highlight_row(this.row_num, true, 'hover');
        };
        elem.onmouseout = function() {
            highlight_row(this.row_num, false, 'hover');
        };
        elem.onclick = function(e) {
            toggle_row(e, this);
        }
        // Disable selections in IE and then in mozilla
        elem.onselectstart = function(e) {disable_selection(e);}
        elem.onmousedown = function(e) {disable_selection(e);}
        row_num = null;
        elem = null;
    }
    childs = null;
}

function init_rowselect() {
    var tables = document.getElementsByClassName('data');
    for(var i = 0; i < tables.length; i++)
        if(tables[i].tagName === 'TABLE')
            table_init_rowselect(tables[i]);
    tables = null;
}

// Adds a hidden field with the selected rows to the form if
// some are selected
function add_row_selections(form) {
    var num_selected = g_selected_rows.length;
    // Skip when none selected
    if(num_selected == 0)
        return true;

    var field = document.createElement('input');
    field.name = 'selected_rows';
    field.type = 'hidden';
    field.value = g_selected_rows.join(',');

    form.appendChild(field);
    field = null;
}
