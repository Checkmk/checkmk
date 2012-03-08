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

var classRegexes = {};

function hasClass(obj, cls) {
    if(!classRegexes[cls])
        classRegexes[cls] = new RegExp('(\\s|^)'+cls+'(\\s|$)');
    return obj.className.match(classRegexes[cls]);
}

// simple string replace that replaces all occurrances.
// Unbelievable that JS does not have a builtin way to
// to that.
function replace_all(haystack, needle, r) {
    while (haystack.search(needle) != -1)
        haystack = haystack.replace(needle, r);
    return haystack;
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
        if (hasClass(_tag, className)) {
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
                    else if (AJAX.status == 401) {
                        // This is reached when someone is not authenticated anymore
                        // but has some webservices running which are still fetching
                        // infos via AJAX. Reload the whole frameset or only the
                        // single page in that case.
                        if(top)
                            top.location.reload();
                        else
                            document.location.reload();
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

function isWebkit() {
  return navigator.userAgent.indexOf("WebKit") > -1;
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

  return w;
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
        if (oNode.tagName == "INPUT" || oNode.tagName == "SELECT") {
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
    var response = [];
    try {
        response = eval(code);
        for(var i = 0; i < response.length; i++) {
            var view = data['view'] == '' ? '0' : data['view'];
            create_graph(data, '&' + response[i]['image_url'].replace('#', '%23').replace('&view='+view, ''));
        }
        view = null;
        i = null;
    } catch(e) {
        valid_response = false;
    }
    response = null;

    if(!valid_response)
        fallback_graphs(data);
}

// Fallback bei doofer/keiner Antwort
function fallback_graphs(data) {
    for(var s = 0; s < 8; s++) {
        create_graph(data, '&host=' + data['host'] + '&srv=' + data['service'] + '&source=' + s);
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
    get_url(pnp_url + 'index.php/json?&host=' + encodeURIComponent(host) + '&srv=' + encodeURIComponent(service) + '&source=0&view=' + pnpview,
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

function performAction(oLink, action, site, host, service, wait_svc) {
    var oImg = oLink.childNodes[0];

    if(wait_svc != service)
        oImg.src = 'images/icon_reloading_cmk.gif';
    else
        oImg.src = 'images/icon_reloading.gif';

    // Chrome and IE are not animating the gif during sync ajax request
    // So better use the async request here
    get_url('nagios_action.py?action=' + action +
            '&site='     + escape(site) +
            '&host='     + escape(host) +
            '&service='  + escape(service) +
            '&wait_svc=' + escape(wait_svc),
            actionResponseHandler, oImg);
    oImg = null;
}

/* -----------------------------------------------------
   view editor
   -------------------------------------------------- */

function get_column_container(oImg) {
    var oNode = oImg;
    while (oNode.tagName != "DIV")
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
        var opts = [ 'h', 't', 'b', 'f', 'c', 'o', 'd', 'e', 'r', 'w' ];
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
        params['_do_actions'] = getUrlParam('_do_actions')

        var url = makeuri(params);
        display_options = null;
        get_url(url, handleContentReload, '', handleContentReloadError);
        url = null;
    }
}

// --------------------------------------------------------------------------
// Folding
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


function toggle_foldable_container(treename, id) {
    var oImg = document.getElementById('treeimg.' + treename + '.' + id);
    var oBox = document.getElementById('tree.' + treename + '.' + id);
    toggle_tree_state(treename, id, oBox);
    toggle_folding(oImg, oBox.style.display != "none");
    oImg = null;
    oBox = null;
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

//
function rgbToHsv(r, g, b) {
    var r = (r / 255),
        g = (g / 255),
        b = (b / 255);

    var min = Math.min(Math.min(r, g), b),
        max = Math.max(Math.max(r, g), b),
        delta = max - min;

    var value = max, saturation, hue;

    // Hue
    if (max == min) {
        hue = 0;
    } else if (max == r) {
        hue = (60 * ((g-b) / (max-min))) % 360;
    } else if (max == g) {
        hue = 60 * ((b-r) / (max-min)) + 120;
    } else if (max == b) {
        hue = 60 * ((r-g) / (max-min)) + 240;
    }

    if (hue < 0)
        hue += 360;

    // Saturation
    if (max == 0) {
        saturation = 0;
    } else {
        saturation = 1 - (min/max);
    }
    return [Math.round(hue), Math.round(saturation * 100), Math.round(value * 100)];
}

function hsvToRgb(h,s,v) {

    var s = s / 100,
        v = v / 100;

    var hi = Math.floor((h/60) % 6);
    var f = (h / 60) - hi;
    var p = v * (1 - s);
    var q = v * (1 - f * s);
    var t = v * (1 - (1 - f) * s);

    var rgb = [];

    switch (hi) {
        case 0: rgb = [v,t,p];break;
        case 1: rgb = [q,v,p];break;
        case 2: rgb = [p,v,t];break;
        case 3: rgb = [p,q,v];break;
        case 4: rgb = [t,p,v];break;
        case 5: rgb = [v,p,q];break;
    }

    var r = Math.min(255, Math.round(rgb[0]*256)),
        g = Math.min(255, Math.round(rgb[1]*256)),
        b = Math.min(255, Math.round(rgb[2]*256));

    return [r,g,b];
}

function lightenColor(color, val) {
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

    var hsv = rgbToHsv(r, g, b);
    hsv[2] -= val;
    var rgb = hsvToRgb(hsv[0], hsv[1], hsv[2]);

    r = rgb[0];
    g = rgb[1];
    b = rgb[2];

    code  = r < 16 ? "0"+r.toString(16) : r.toString(16);
    code += g < 16 ? "0"+g.toString(16) : g.toString(16);
    code += b < 16 ? "0"+b.toString(16) : b.toString(16);

    return "#" + code.toUpperCase();
}

function real_style(obj, attr, ieAttr) {
    var st;
    if(document.defaultView && document.defaultView.getComputedStyle) {
        st = document.defaultView.getComputedStyle(obj, null).getPropertyValue(attr);
    } else {
        st = obj.currentStyle[ieAttr];
    }

    if(typeof(st) == 'undefined') {
        st = 'transparent';
    }

    // If elem is a TD and has no background find the backround of the parent
    // e.g. the TR and then set this color as background for the TD
    // But only do this when the TR is not in the highlight scope
    if(obj.tagName == 'TD'
       && obj.parentNode.row_num === undefined
       && (st == 'transparent' || st == 'rgba(0, 0, 0, 0)'))
        st = real_style(obj.parentNode, attr, ieAttr);

    return st;
}

function find_checkbox(elem) {
    // Find the checkbox of this element to gather the number of cells
    // to highlight after the checkbox
    // 1. Go up to the row
    // 2. search backwards for the next checkbox
    // 3. loop the number of columns to highlight
    var childs = elem.parentNode.childNodes;
    var found = false;
    var checkbox = null;
    for(var a = childs.length - 1; a >= 0 && checkbox === null; a--) {
        if(found === false) {
            if(childs[a] == elem) {
                found = true;
            }
            continue;
        }

        // Found the clicked column, now walking the cells backward from the
        // current cell searching for the next checkbox
        var elems = childs[a].childNodes;
        for(var x = 0; x < elems.length; x++) {
            if(elems[x].tagName === 'INPUT' && elems[x].type == 'checkbox') {
                checkbox = elems[x];
                break;
            }
        }
        elems = null;
    }
    return checkbox;
}

function highlight_row(elem, on) {
    var checkbox = find_checkbox(elem);
    if(checkbox !== null) {
        iter_cells(checkbox, function(elem) {
            highlight_elem(elem, on);
        });
        checkbox = null;
    }
    return false;
}

function highlight_elem(elem, on) {
    // Find all elements below "elem" with a defined background-color and change it
    var bg_color = real_style(elem, 'background-color', 'backgroundColor');
    if (bg_color == 'white')
        bg_color = "#ffffff";

    if(on) {
        elem['hover_orig_bg'] = bg_color;
        elem.style.backgroundColor = lightenColor(elem['hover_orig_bg'], -20);
    } else {
        elem.style.backgroundColor = elem['hover_orig_bg'];
        elem['hover_orig_bg'] = undefined;
    }

    var childs = elem.childNodes;
    for(var i = 0; i < childs.length; i++)
        if(childs[i].tagName !== undefined && childs[i].tagName !== 'OPTION')
            highlight_elem(childs[i], on);
}

function select_all_rows(elems) {
    for(var i = 0; i < elems.length; i++) {
        elems[i].checked = true;
        if(g_selected_rows.indexOf(elems[i].name) === -1)
            g_selected_rows.push(elems[i].name);
    }
}

function remove_selected_rows(elems) {
    for(var i = 0; i < elems.length; i++) {
        elems[i].checked = false;
        var row_pos = g_selected_rows.indexOf(elems[i].name);
        if(row_pos > -1)
            g_selected_rows.splice(row_pos, 1);
        row_pos = null;
    }
}

function toggle_box(e, elem) {
    var row_pos = g_selected_rows.indexOf(elem.name);
    if(row_pos > -1) {
        g_selected_rows.splice(row_pos, 1);
    } else {
        g_selected_rows.push(elem.name);
    }
}

function toggle_row(e, elem) {
    if(!e)
        e = window.event;

    // Skip handling clicks on links/images/...
    var target = getTarget(e);
    if(target.tagName != 'TD')
        return true;

    // Find the checkbox for this element
    var checkbox = find_checkbox(elem);
    if(checkbox === null)
        return;

    // When CTRL is not pressed, remove the selection
    //if(!e.ctrlKey)
    //    remove_selected_rows(row_num);

    // Is SHIFT pressed?
    // Yes:
    //   Select all from the last selection

    // Is the current row already selected?
    var row_pos = g_selected_rows.indexOf(checkbox.name);
    if(row_pos > -1) {
        // Yes: Unselect it
        checkbox.checked = false;
        g_selected_rows.splice(row_pos, 1);
    } else {
        // No:  Select it
        checkbox.checked = true;
        g_selected_rows.push(checkbox.name);
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

// FIXME: If current "row text selection" behavior is ok - remove this
//function disable_selection(e) {
//    if(!e)
//        e = window.event;
//
//    // Skip handling clicks on links/images/...
//    var target = getTarget(e);
//    if(target.tagName != 'TD')
//        return true;
//
//    // Firefox handling
//    if(typeof target.style.MozUserSelect != 'undefined')
//        target.style.MozUserSelect = 'none';
//
//    // All others
//    return false;
//}

// Toggles the datarows of the group which the given checkbox is part of.
function toggle_group_rows(checkbox) {
    // 1. Find the first tbody parent
    // 2. iterate over the childNodes and search for the group header of the checkbox
    //    - Save the TR with class groupheader
    //    - End this search once found the checkbox element
    var this_row = checkbox.parentNode.parentNode;
    var rows     = this_row.parentNode.childNodes;

    var in_this_group = false;
    var group_start   = null;
    var group_end     = null;
    for(var i = 0; i < rows.length; i++) {
        if(rows[i].tagName !== 'TR')
            continue;

        if(!in_this_group) {
            // Search for the start of our group
            // Save the current group row element
            if(rows[i].className === 'groupheader')
                group_start = i + 1;

            // Found the row of the checkbox? Then finished with this loop
            if(rows[i] === this_row)
                in_this_group = true;
        } else {
            // Found the start of our group. Now search for the end
            if(rows[i].className === 'groupheader') {
                group_end = i - 1;
                break;
            }
        }
    }

    if(group_start === null)
        group_start = 0;
    if(group_end === null)
        group_end = rows.length - 1;

    // Found the group start and end row of the checkbox!
    var group_rows = [];
    for(var a = group_start; a < group_end; a++)
        if(rows[a].tagName === 'TR')
            group_rows.push(rows[a]);
    toggle_all_rows(group_rows);
    group_rows = null;

    tbody   = null;
    this_tr = null;
}

// Is used to select/deselect all rows in the current view. This can optionally
// be called with a container element. If given only the elements within this
// container are highlighted.
// It is also possible to give an array of DOM elements as parameter to toggle
// all checkboxes below these objects.
function toggle_all_rows(obj) {
    var checkboxes = get_all_checkboxes(obj || document);

    var all_selected = true;
    for(var i = 0; i < checkboxes.length && all_selected == true; i++)
        if(g_selected_rows.indexOf(checkboxes[i].name) === -1)
            all_selected = false;

    // Toggle the state
    if(all_selected) {
        remove_selected_rows(checkboxes);
    } else {
        select_all_rows(checkboxes);
    }
}

// Iterates over all the cells of the given checkbox and executes the given
// function for each cell
function iter_cells(checkbox, func) {
    var num_columns = parseInt(checkbox.value);
    // Now loop the next N cells to call the func for each cell
    // 1. Get row element
    // 2. Find the current td
    // 3. find the next N tds
    var cell = checkbox.parentNode;
    var row_childs = cell.parentNode.childNodes;
    var found = false;
    for(var c = 0; c < row_childs.length && num_columns > 0; c++) {
        if(found === false) {
            if(row_childs[c] == cell) {
                found = true;
            } else {
                continue;
            }
        }

        if(row_childs[c].tagName == 'TD') {
            func(row_childs[c]);
            num_columns--;
        }
    }
    cell = null;
    row_childs = null;
}

// Container is an DOM element to search below or a list of DOM elements
// to search below
function get_all_checkboxes(container) {
    var checkboxes = [];

    if(typeof(container) === 'object' && container.length) {
        // Array given - at the moment this is a list of TR objects
        // Skip the header checkboxes
        for(var i = 0; i < container.length; i++) {
            var childs = container[i].getElementsByTagName('input');

            for(var a = 0; a < childs.length; a++)
                if(childs[a].type == 'checkbox')
                    checkboxes.push(childs[a]);

            childs = null;
        }
    } else {
        // One DOM node given
        var childs = container.getElementsByTagName('input');

        for(var i = 0; i < childs.length; i++)
            if(childs[i].type == 'checkbox')
                checkboxes.push(childs[i]);

        childs = null;
    }

    return checkboxes;
}

function table_init_rowselect(oTable) {
    var childs = get_all_checkboxes(oTable);
    for(var i = 0; i < childs.length; i++) {
        // Perform initial selections
        if (g_selected_rows.indexOf(childs[i].name) > -1)
            childs[i].checked = true;
        else
            childs[i].checked = false;

        childs[i].onchange = function(e) {
            toggle_box(e, this);
        };

        iter_cells(childs[i], function(elem) {
            elem.onmouseover = function() {
                return highlight_row(this, true);
            };
            elem.onmouseout = function() {
                return highlight_row(this, false);
            };
            elem.onclick = function(e) {
                return toggle_row(e, this);
            };
            // Disable selections in IE and then in mozilla
            //elem.onselectstart = function(e) {
            //    return disable_selection(e);
            //};
            //elem.onmousedown = function(e) {
            //    return disable_selection(e);
            //};
            elem = null;
        });
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

function has_canvas_support() {
    return document.createElement('canvas').getContext;
}

// convert percent to angle(rad)
function rad(g) {
    return (g * 360 / 100 * Math.PI) / 180;
}

// TEST
function count_context_button(oA)
{
    // Extract view name from id of parent div element
    var id = oA.parentNode.id;
    get_url_sync("count_context_button.py?id=" + id);
}

function unhide_context_buttons(oA)
{
    var oNode;
    var oTd = oA.parentNode.parentNode;
    for (var i in oTd.childNodes) {
        oNode = oTd.childNodes[i];
        if (oNode.tagName == "DIV" && oNode.id != "toggle")
            oNode.style.display = "";
    }
    oA.parentNode.style.display = "none";
    oNode = null;
    oDiv = null;
}

// .-----------------------------------------------------------------------.
// |          __     __    _            ____                               |
// |          \ \   / /_ _| |_   _  ___/ ___| _ __   ___  ___              |
// |           \ \ / / _` | | | | |/ _ \___ \| '_ \ / _ \/ __|             |
// |            \ V / (_| | | |_| |  __/___) | |_) |  __/ (__              |
// |             \_/ \__,_|_|\__,_|\___|____/| .__/ \___|\___|             |
// |                                         |_|                           |
// +-----------------------------------------------------------------------+
// | Functions needed by HTML code from ValueSpec (valuespec.py)           |
// '-----------------------------------------------------------------------'

function valuespec_toggle_option(oCheckbox, divid, negate) {
    var oDiv = document.getElementById(divid);
    if ((oCheckbox.checked && !negate) || (!oCheckbox.checked && negate))
        oDiv.style.display = "";
    else
        oDiv.style.display = "none";
    oDiv = null;
}

function valuespec_toggle_dropdown(oDropdown, divid) {
    var oDiv = document.getElementById(divid);
    if (oDropdown.value == "other") oDiv.style.display = "";
    else
        oDiv.style.display = "none";
    oDiv = null;
}

function valuespec_toggle_dropdownn(oDropdown, divid) {
    var oDiv = document.getElementById(divid);
    if (oDropdown.value == "ignore")
        oDiv.style.display = "none";
    else
        oDiv.style.display = "";
    oDiv = null;
}

function list_of_strings_init(tableid) {
    var oTable = document.getElementById(tableid);
    var oTBody = oTable.childNodes[0];
    var oTr = oTBody.childNodes[oTBody.childNodes.length - 1];
    var oTd = oTr.childNodes[0];
    for (var j in oTd.childNodes) {
        var o = oTd.childNodes[j];
        if (o.tagName == "INPUT") {
            o.onfocus = function(e) { return list_of_strings_extend(this); };
        }
    }
}

function list_of_strings_extend(oInput, j) {
    var oldName = oInput.name;
    // Transform e.g extra_emails_12 -> extra_emails_13
    var splitted = oldName.split("_");
    var num = 1 + parseInt(splitted[splitted.length-1]);
    splitted[splitted.length-1] = "" + num;
    var newName = splitted.join("_");

    var oTr = oInput.parentNode.parentNode;
    var oTBody = oTr.parentNode;
    var oNewTr = document.createElement("TR"); 
    oNewTr.innerHTML = oTr.innerHTML.replace('"' + oldName + '"', '"' + newName + '"');
    oTBody.appendChild(oNewTr);
    var oNewTd = oNewTr.childNodes[0];
    for (var j in oNewTd.childNodes) {
        var o = oNewTd.childNodes[j];
        if (o.tagName == "INPUT") {
            o.onfocus = function(e) { return list_of_strings_extend(this); };
        }
    }
    // Remove handle from old last element
    oInput.onfocus = null;
}

function valuespec_cascading_change(oSelect, varprefix, count) { 
    var nr = parseInt(oSelect.value);

    for (var i=0; i<count; i++) {
        var oDiv = document.getElementById(varprefix + "_" + i + "_sub"); 
        if (oDiv) {
            if (nr == i) {
                oDiv.style.display = ""; 
            }
            else
                oDiv.style.display = "none";
        }
    }
}

function valuespec_listof_add(varprefix, magic) {
  var oCountInput = document.getElementById(varprefix + "_count");
  var count = parseInt(oCountInput.value);
  var strcount = "" + (count + 1);
  oCountInput.value = strcount;
  var oPrototype = document.getElementById(varprefix + "_prototype").childNodes[0].childNodes[0]; // TR
  var htmlcode = oPrototype.innerHTML;
  htmlcode = replace_all(htmlcode, magic, strcount);
  var oTable = document.getElementById(varprefix + "_table");
  if (count == 0) {  // first: no <tbody> present!
      oTable.innerHTML = "<tbody><tr>" + htmlcode + "</tr></tbody>";
      valuespec_listof_fixarrows(oTable.childNodes[0]);
  }
  else {
      var oTbody = oTable.childNodes[0];
      var oTr = document.createElement("tr")
      oTr.innerHTML = htmlcode;
      oTbody.appendChild(oTr);
      valuespec_listof_fixarrows(oTbody);
  }
}

// When deleting we do not fix up indices but simply
// remove the according table row and add an invisible
// input element with the name varprefix + "_deleted_%nr"
function valuespec_listof_delete(oA, varprefix, nr) {
    var oTr = oA.parentNode.parentNode; // TR
    var oTbody = oTr.parentNode;
    oInput = document.createElement("input");
    oInput.type = "hidden";
    oInput.name = "_" + varprefix + '_deleted_' + nr
    oInput.value = "1"
    var oTable = oTbody.parentNode;
    oTable.parentNode.insertBefore(oInput, oTable);
    oTbody.removeChild(oTr);
    valuespec_listof_fixarrows(oTbody);
}

function valuespec_listof_move(oA, varprefix, nr, where) {
    var oTr = oA.parentNode.parentNode; // TR to move
    var oTbody = oTr.parentNode;

    if (where == "up")  {
        var sib = oTr.previousSibling;
        oTbody.removeChild(oTr);
        oTbody.insertBefore(oTr, sib);
    }
    else /* down */ {
        var sib = oTr.nextSibling;
        oTbody.removeChild(oTr);
        if (sib == oTbody.lastChild)
            oTbody.appendChild(oTr);
        else
            oTbody.insertBefore(oTr, sib.nextSibling);
    }
    valuespec_listof_fixarrows(oTbody);
}


function valuespec_listof_fixarrows(oTbody) {
    for (var i in oTbody.childNodes) {
        var oTd = oTbody.childNodes[i].childNodes[0]; /* TD with buttons */
        var oIndex = oTd.childNodes[0];
        oIndex.value = "" + (parseInt(i) + 1);
        var oUpTrans = oTd.childNodes[2];
        var oUp      = oTd.childNodes[3];
        if (i == 0) {
            oUpTrans.style.display = "";
            oUp.style.display = "none";
        }
        else {
            oUpTrans.style.display = "none";
            oUp.style.display = "";
        }
        var oDownTrans = oTd.childNodes[4];
        var oDown      = oTd.childNodes[5];
        if (i >= oTbody.childNodes.length - 1) {
            oDownTrans.style.display = "";
            oDown.style.display = "none";
        }
        else {
            oDownTrans.style.display = "none";
            oDown.style.display = "";
        }
    }
}
