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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

// ----------------------------------------------------------------------------
// general function
// ----------------------------------------------------------------------------

// Make JS understand Python source code
var True = true;
var False = false;

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

// The nextSibling attribute points also to "text nodes" which might
// be created by spaces or even newlines in the HTML code and not to
// the next painted dom object.
// This works around the problem and really returns the next object.
function real_next_sibling(o) {
    var n = o.nextSibling;
    while (n.nodeType != 1)
      n = n.nextSibling;
    return n;
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

// Again, some IE 7 fun: The IE7 mixes up name and id attributes of objects.
// When using getElementById() where we really only want to match objects by
// their id, the clever IE7 also searches objects by their names, wow. crap.
if (navigator.appVersion.indexOf("MSIE 7.") != -1)
{
    document._getElementById = document.getElementById;
    document.getElementById = function(id) {
        var e = document._getElementById(id);
        if (e) {
            if (e.attributes['id'].value == id)
                return e;
            else {
                for (var i = 1; i < document.all[id].length; i++) {
                    if(document.all[id][i].attributes['id'].value == id)
                        return document.all[id][i];
                }
            }
        }
        return null;
    };
}

function getTarget(event) {
  return event.target ? event.target : event.srcElement;
}

function getButton(event) {
  if (event.which == null)
    /* IE case */
    return (event.button < 2) ? "LEFT" : ((event.button == 4) ? "MIDDLE" : "RIGHT");
  else
    /* All others */
    return (event.which < 2) ? "LEFT" : ((event.which == 2) ? "MIDDLE" : "RIGHT");
}

// Adds document/window global event handlers
function add_event_handler(type, func) {
    if (window.addEventListener) {
        // W3 standard browsers
        window.addEventListener(type, func, false);
    }
    else if (window.attachEvent) {
        // IE<9
        document.documentElement.attachEvent("on" + type, func);
    }
    else {
        window["on" + type] = func;
    }
}

function del_event_handler(type, func) {
    if (window.removeEventListener) {
        // W3 stadnard browsers
        window.removeEventListener(type, func, false);
    }
    else if (window.detachEvent) {
        // IE<9
        document.documentElement.detachEvent("on"+type, func);
    }
    else {
        window["on" + type] = null;
    }
}


function prevent_default_events(event) {
    if (event.preventDefault)
        event.preventDefault();
    if (event.stopPropagation)
        event.stopPropagation();
    event.returnValue = false;
}

function hilite_icon(oImg, onoff) {
    src = oImg.src;
    if (onoff == 0)
        oImg.src = oImg.src.replace("hi.png", "lo.png");
    else
        oImg.src = oImg.src.replace("lo.png", "hi.png");
}


function get_url(url, handler, data, errorHandler, addAjaxId) {
    if (window.XMLHttpRequest) {
        var AJAX = new XMLHttpRequest();
    } else {
        var AJAX = new ActiveXObject("Microsoft.XMLHTTP");
    }

    var addAjaxId = (typeof addAjaxId === "undefined") ? true : addAjaxId;

    // Dynamic part to prevent caching
    var dyn = '';
    if (addAjaxId) {
        dyn = "_ajaxid="+Math.floor(Date.parse(new Date()) / 1000);
        if (url.indexOf('\?') !== -1) {
            dyn = "&"+dyn;
        } else {
            dyn = "?"+dyn;
        }
    }

    if (!AJAX) {
        return null;
    }

    AJAX.open("GET", url + dyn, true);
    if (typeof handler === 'function') {
        AJAX.onreadystatechange = function() {
            if (AJAX && AJAX.readyState == 4) {
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
        }
    }

    AJAX.send(null);
    return AJAX;
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

function post_url(url, params) {
    if (window.XMLHttpRequest) {
        var AJAX = new XMLHttpRequest();
    } else {
        var AJAX = new ActiveXObject("Microsoft.XMLHTTP");
    }

    AJAX.open("POST", url);

    AJAX.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    AJAX.setRequestHeader("Content-length", params.length);
    AJAX.setRequestHeader("Connection", "close");

    AJAX.onreadystatechange = function() {
        if (AJAX && AJAX.readyState == 4) {
            if (AJAX.status == 401) {
                // This is reached when someone is not authenticated anymore
                // but has some webservices running which are still fetching
                // infos via AJAX. Reload the whole frameset or only the
                // single page in that case.
                if(top)
                    top.location.reload();
                else
                    document.location.reload();
            }
            else if (AJAX.status != 200) {
                alert('Error ' + AJAX.status + ' during POST to URL ' + url);
            }
        }
    }
    AJAX.send(params);
}


function bulkUpdateContents(ids, codes) {
    var codes = eval(codes);
    for (var i = 0, len = ids.length; i < len; i++) {
        if (restart_snapins.indexOf(ids[i].replace('snapin_', '')) !== -1) {
            // Snapins which rely on the restart time of nagios receive
            // an empty code here when nagios has not been restarted
            // since sidebar rendering or last update, skip it
            if(codes[i] != '') {
                updateContents(ids[i], codes[i]);
                sidebar_restart_time = Math.floor(Date.parse(new Date()) / 1000);
            }
        } else {
            updateContents(ids[i], codes[i]);
        }
    }
}

// Updates the contents of a snapin or dashboard container after get_url
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
  executeJSbyObject(obj);
}

function executeJSbyObject(obj) {
  // Before switching to asynchronous requests this worked in firefox
  // out of the box. Now it seems not to work with ff too. So now
  // executing the javascript manually.
  // if (!isFirefox()) {
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

function is_ie_below_9() {
    return document.all && !document.addEventListener;
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
function getUrlParam(name, url) {
    var url = (typeof url === 'undefined') ? window.location : url;

    var name = name.replace('[', '\\[').replace(']', '\\]');
    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)");
    var results = regex.exec(url);
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
function makeuri(addvars, url) {
    var url = (typeof(url) === 'undefined') ? window.location.href : url;

    var tmp = url.split('?');
    var base = tmp[0];
    if(tmp.length > 1) {
        // Remove maybe existing anchors
        tmp = tmp[1].split('#');
        // Split to array of param-strings (key=val)
        tmp = tmp[0].split('&');
    } else {
        // Uri has no parameters
        tmp = [];
    }

    var len = tmp.length;
    var params = [];
    var pair = null;

    // Skip unwanted parmas
    for(var i = 0; i < tmp.length; i++) {
        pair = tmp[i].split('=');
        if(pair[0][0] == '_' && pair[0] != "_username" && pair[0] != "_secret") // Skip _<vars>
            continue;
        if(addvars.hasOwnProperty(pair[0])) // Skip vars present in addvars
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

function update_togglebutton(id, enabled) {
    var on  = document.getElementById(id + '_on');
    var off = document.getElementById(id + '_off');
    if (!on || !off)
        return;

    if (enabled) {
        on.style.display = 'block';
        off.style.display = 'none';
    } else {
        on.style.display = 'none';
        off.style.display = 'block';
    }
}

function update_headinfo(text)
{
    var oDiv = document.getElementById("headinfo");
    if (oDiv) {
        oDiv.innerHTML = text;
    }
}

function toggle_input_fields(container, type, disable) {
    var fields = container.getElementsByTagName(type);
    for(var a = 0; a < fields.length; a++) {
        fields[a].disabled = disable;
    }
}

function toggle_other_filters(fname, disable_others) {
    for(var i = 0; i < g_filter_groups[fname].length; i++) {
        var other_fname = g_filter_groups[fname][i];
        var oSelect = document.getElementById('filter_' + other_fname);

        // When the filter is active, disable the other filters and vice versa

        // Disable the "filter mode" dropdown
        oSelect.disabled = disable_others;

        // Now dig into the filter and rename all input fields.
        // If disabled add an "_disabled" to the end of the var
        // If enabled remve "_disabled" from the end of the var
        var oFloatFilter = real_next_sibling(oSelect);
        if (oFloatFilter) {
            toggle_input_fields(oFloatFilter, 'input', disable_others);
            toggle_input_fields(oFloatFilter, 'select', disable_others);
            oFloatFilter = null;
        }

        oSelect = null;
    }
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

    if(!valid_response) {
        if (code.match(/_login/)) {
            // Login failed! This usually happens when one uses a distributed
            // multisite setup but the transparent authentication is somehow
            // broken. Display an error message trying to assist.
            var container = document.getElementById(data['container']);
            container.innerHTML = '<div class="error">Unable to fetch graphs of the host. Maybe you have a '
                                + 'distributed setup and not set up the authentication correctly yet.</div>';
        } else {
            fallback_graphs(data);
        }
    }
}

// Fallback bei doofer/keiner Antwort
function fallback_graphs(data) {
    for(var s = 0; s < 8; s++) {
        create_graph(data, '&host=' + data['host'] + '&srv=' + data['service'] + '&source=' + s);
    }
}

function create_graph(data, params) {
    var urlvars = params + '&theme=multisite&baseurl='+data['base_url'];

    if (typeof(data['start']) !== 'undefined' && typeof(data['end']) !== 'undefined')
        urlvars += '&start='+data['start']+'&end='+data['end'];

    var container = document.getElementById(data['container']);

    var img = document.createElement('img');
    img.src = data['pnp_url'] + 'index.php/image?view=' + data['view'] + urlvars;

    if (data.with_link) {
        var graph_container = document.createElement('div');
        graph_container.setAttribute('class', 'graph')

        var view   = data['view'] == '' ? 0 : data['view'];
        // needs to be extracted from "params", hack!
        var source = parseInt(getUrlParam('source', params));

        // Add the control for adding the graph to a dashboard
        var visualadd = document.createElement('a');
        visualadd.title = data['add_txt'];
        visualadd.className = 'visualadd';
        visualadd.onclick = function(host, service, view, source) {
            return function(event) {
                toggle_add_to_visual(event, this, 'pnpgraph',
                    { 'host': host, 'service': service },
                    { 'timerange': view, 'source': source }
                );
            }
        }(data['host'], data['service'], view, source);

        graph_container.appendChild(visualadd);

        var link = document.createElement('a');
        link.href = data['pnp_url'] + 'index.php/graph?' + urlvars;
        link.appendChild(img);
        graph_container.appendChild(link);

        container.appendChild(graph_container);
    }
    else {
        container.appendChild(img);
    }

    img = null;
    link = null;
    container = null;
    urlvars = null;
}

function render_pnp_graphs(container, site, host, service, pnpview, base_url, pnp_url, with_link, add_txt, from_ts, to_ts) {
    from_ts = (typeof from_ts === 'undefined') ? null : from_ts;
    to_ts   = (typeof to_ts === 'undefined') ? null : to_ts;

    var data = { 'container': container, 'base_url': base_url,
                 'pnp_url':   pnp_url,   'site':     site,
                 'host':      host,      'service':  service,
                 'with_link': with_link, 'view':     pnpview,
                 'add_txt':   add_txt};

    if (from_ts !== null && to_ts !== null) {
        data['start'] = from_ts;
        data['end'] = to_ts;
    }

    var url = pnp_url + 'index.php/json?&host=' + encodeURIComponent(host)
              + '&srv=' + encodeURIComponent(service) + '&source=0&view=' + pnpview;
    get_url(url, pnp_response_handler, data, pnp_error_response_handler, false);
}

// Renders contents for the PNP hover menus
function pnp_hover_contents(url) {
    var c = get_url_sync(url);
    // It is possible that, if using multisite based authentication, pnp sends a 302 redirect
    // to the login page which is transparently followed by XmlHttpRequest. There is no chance
    // to catch the redirect. So we try to check the response content. If it does not contain
    // the expected code, simply display an error message.
    if(c.indexOf('/image?') === -1) {
        // Error! unexpected response
        c = '<div style="background-color:#BA2C2C;width:350px;padding:5px"> '
          + 'ERROR: Received an unexpected response '
          + 'while trying to display the PNP-Graphs. Maybe there is a problem with the '
          + 'authentication.</div>';
    }
    return c;
}

// ----------------------------------------------------------------------------
// Handle Enter key in textfields
// ----------------------------------------------------------------------------
function textinput_enter_submit(e, submit) {
    var keyCode = e.which || e.keyCode;
    if (keyCode == 13) {
        if (submit) {
            var button = document.getElementById(submit);
            if (button)
                button.click();
        }
        if (e.preventDefault) e.preventDefault();
        e.returnValue = false;
        e.cancelBubble = true;
        return false;
    }
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
            '&site='     + encodeURIComponent(site) +
            '&host='     + encodeURIComponent(host) +
            '&service='  + service + // Already URL-encoded!
            '&wait_svc=' + wait_svc,
            actionResponseHandler, oImg);
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

function toggleRefreshFooter(s) {
    var o = document.getElementById('foot_refresh');
    var o2 = document.getElementById('foot_refresh_time');
    if(o) {
        if(s == 0) {
            o.style.display = 'none';
        } else {
            o.style.display = 'inline-block';
            if(o2) {
                o2.innerHTML = s;
            }
        }
    }
    o = null;
}

// When called with one or more parameters parameters it reschedules the
// timer to the given interval. If the parameter is 0 the reload is stopped.
// When called with two parmeters the 2nd one is used as new url.
function setReload(secs, url) {
    if (typeof url === 'undefined')
        url = '';

    if (gReloadTimer) {
        toggleRefreshButton(0, false);
        toggleRefreshButton(gReloadTime, false);
        clearTimeout(gReloadTimer);
    }

    toggleRefreshButton(secs, true);
    toggleRefreshFooter(secs);

    if (secs !== 0) {
        gReloadTime  = secs;
        startReloadTimer(url);
    }
}

function startReloadTimer(url) {
    if (gReloadTimer)
        clearTimeout(gReloadTimer);
    if (gReloadTime)
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

    var oDate = document.getElementById('headerdate');
    if (oDate) {
        var day   = ("0" + t.getDate()).slice(-2);
        var month = ("0" + (t.getMonth() + 1)).slice(-2);
        var year  = t.getFullYear();
        var date_format = oDate.getAttribute("format");
        oDate.innerHTML = date_format.replace(/yyyy/, year).replace(/mm/, month).replace(/dd/, day);
    }
    day    = null;
    month  = null;
    year   = null;
    format = null;
    oDate  = null;
    min    = null;
    hours  = null;
    t      = null;
    oTime  = null;
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
    if (!document.getElementById('data_container') || url !== '') {
        if (url === '')
            window.location.reload(false);
        else
            window.location.href = url;
    }
    else {
        // Enforce specific display_options to get only the content data.
        // All options in "opts" will be forced. Existing upper-case options will be switched.
        var display_options = getUrlParam('display_options');
        // Removed 'w' to reflect original rengering mechanism during reload
        // For example show the "Your query produced more than 1000 results." message
        // in views even during reload.
        var opts = [ 'h', 't', 'b', 'f', 'c', 'o', 'd', 'e', 'r', 'u' ];
        for (var i = 0; i < opts.length; i++) {
            if (display_options.indexOf(opts[i].toUpperCase()) > -1)
                display_options = display_options.replace(opts[i].toUpperCase(), opts[i]);
            else
                display_options += opts[i];
        }
        opts = null;

        // Add optional display_options if not defined in original display_options
        var opts = [ 'w' ];
        for (var i = 0; i < opts.length; i++) {
            if (display_options.indexOf(opts[i].toUpperCase()) == -1)
                display_options += opts[i];
        }
        opts = null;

        var params = {'_display_options': display_options};
        var real_display_options = getUrlParam('display_options');
        if(real_display_options !== '')
            params['display_options'] = real_display_options;

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
    if (typeof step === 'undefined')
        if (state == 1)
            step = 1;
        else
            step = 8;

    // Relace XX.png at the end of the image with the
    // current rotating angle
    oImg.src = oImg.src.substr(0, oImg.src.length - 6) + step + "0.png";

    if (state == 1) {
        if (step == 9) {
            oImg = null;
            return;
        }
        step += 1;
    }
    else {
        if (step == 0) {
            oImg = null;
            return;
        }
        step -= 1;
    }

    setTimeout(function() { folding_step(oImg, state, step); }, fold_steps[step]);
}

/* Check if an element has a certain css class. */
function has_class(o, cn) {
    if (typeof(o.className) === 'undefined')
        return false;
    var parts = o.className.split(' ');
    for (x=0; x<parts.length; x++) {
        if (parts[x] == cn)
            return true;
    }
    return false;
}

function remove_class(o, cn) {
    var parts = o.className.split(' ');
    var new_parts = Array();
    for (x=0; x<parts.length; x++) {
        if (parts[x] != cn)
            new_parts.push(parts[x]);
    }
    o.className = new_parts.join(" ");
}

function add_class(o, cn) {
    if (!has_class(o, cn))
        o.className += " " + cn;
}

function change_class(o, a, b) {
    remove_class(o, a);
    add_class(o, b);
}


function toggle_tree_state(tree, name, oContainer, fetch_url) {
    var state;
    if (has_class(oContainer, 'closed')) {
        change_class(oContainer, 'closed', 'open');
        if (fetch_url && !oContainer.innerHTML) {
            oContainer.innerHTML = get_url_sync(fetch_url);
        }
        state = 'on';
        if (oContainer.tagName == 'TR') { // handle in-table toggling
            while (oContainer = oContainer.nextSibling)
                change_class(oContainer, 'closed', 'open');
        }
    }
    else {
        change_class(oContainer, 'open', 'closed');
        state = 'off';
        if (oContainer.tagName == 'TR') { // handle in-table toggling
            while (oContainer = oContainer.nextSibling)
                change_class(oContainer, 'open', 'closed');
        }
    }
    get_url('tree_openclose.py?tree=' + encodeURIComponent(tree)
            + '&name=' + encodeURIComponent(name) + '&state=' + state);
    oContainer = null;
}


// fetch_url: dynamically load content of opened element.
function toggle_foldable_container(treename, id, fetch_url) {
    // Check, if we fold a NG-Norm
    var oNform = document.getElementById('nform.' + treename + '.' + id);
    if (oNform) {
        var oImg = oNform.childNodes[0];
        toggle_folding(oImg, oImg.src[oImg.src.length - 6] == '0');
        var oTr = oNform.parentNode.nextSibling;
        toggle_tree_state(treename, id, oTr, fetch_url);
    }
    else {
        var oImg = document.getElementById('treeimg.' + treename + '.' + id);
        var oBox = document.getElementById('tree.' + treename + '.' + id);
        toggle_tree_state(treename, id, oBox, fetch_url);
        toggle_folding(oImg, !has_class(oBox, "closed"));
        oImg = null;
        oBox = null;
    }
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

// The unique ID to identify the current page and its selections of a user
var g_page_id = '';
// The unique identifier of the selection
var g_selection = '';
// Tells us if the row selection is enabled at the moment
var g_selection_enabled = false;
// Holds the row numbers of all selected rows
var g_selected_rows = [];

function find_checkbox(oTd) {
    // Find the checkbox of this oTdent to gather the number of cells
    // to highlight after the checkbox
    // 1. Go up to the row
    // 2. search backwards for the next checkbox
    // 3. loop the number of columns to highlight
    var allTds = oTd.parentNode.childNodes;
    var found = false;
    var checkbox = null;
    for(var a = allTds.length - 1; a >= 0 && checkbox === null; a--) {
        if(found === false) {
            if(allTds[a] == oTd) { /* that's me */
                found = true;
            }
            else
                continue;
        }

        // Found the clicked column, now walking the cells backward from the
        // current cell searching for the next checkbox
        var oTds = allTds[a].childNodes;
        for(var x = 0; x < oTds.length; x++) {
            if(oTds[x].tagName === 'INPUT' && oTds[x].type == 'checkbox') {
                checkbox = oTds[x];
                break;
            }
        }
        oTds = null;
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
    if (on)
        add_class(elem, "checkbox_hover");
    else
        remove_class(elem, "checkbox_hover");
}

function update_row_selection_information() {
    // First update the header information (how many rows selected)
    var count = g_selected_rows.length;
    var oDiv = document.getElementById("headinfo");
    if (oDiv) {
        var current_text = oDiv.innerHTML;
        if (current_text.indexOf('/') != -1) {
            var parts = current_text.split('/');
            current_text = parts[1];
        }
        oDiv.innerHTML = count + "/" + current_text;
    }
}

function set_rowselection(action, rows) {
    post_url('ajax_set_rowselection.py', 'id=' + g_page_id
             + '&selection=' + g_selection
             + '&action=' + action
             + '&rows=' + rows.join(','));
}

function select_all_rows(elems, only_failed) {
    if (typeof only_failed === 'undefined') {
        only_failed = false;
    }

    for(var i = 0; i < elems.length; i++) {
        if (!only_failed || elems[i].classList.contains('failed')) {
            elems[i].checked = true;
            if (g_selected_rows.indexOf(elems[i].name) === -1)
                g_selected_rows.push(elems[i].name);
        }
    }

    update_row_selection_information();
    set_rowselection('add', g_selected_rows);
}

function remove_selected_rows(elems) {
    set_rowselection('del', g_selected_rows);

    for(var i = 0; i < elems.length; i++) {
        elems[i].checked = false;
        var row_pos = g_selected_rows.indexOf(elems[i].name);
        if(row_pos > -1)
            g_selected_rows.splice(row_pos, 1);
        row_pos = null;
    }

    update_row_selection_information();
}

function toggle_box(e, elem) {
    var row_pos = g_selected_rows.indexOf(elem.name);

    if(row_pos > -1) {
        g_selected_rows.splice(row_pos, 1);
        set_rowselection('del', [elem.name]);
    } else {
        g_selected_rows.push(elem.name);
        set_rowselection('add', [elem.name]);
    }

    update_row_selection_information();
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

    // Is SHIFT pressed?
    // Yes:
    //   Select all from the last selection

    // Is the current row already selected?
    var row_pos = g_selected_rows.indexOf(checkbox.name);
    if(row_pos > -1) {
        // Yes: Unselect it
        checkbox.checked = false;
        g_selected_rows.splice(row_pos, 1);
        set_rowselection('del', [checkbox.name]);
    } else {
        // No:  Select it
        checkbox.checked = true;
        g_selected_rows.push(checkbox.name);
        set_rowselection('add', [checkbox.name]);
    }
    update_row_selection_information();

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
        group_end = rows.length;

    // Found the group start and end row of the checkbox!
    var group_rows = [];
    for(var a = group_start; a < group_end; a++) {
        if(rows[a].tagName === 'TR') {
            group_rows.push(rows[a]);
        }
    }
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
    var none_selected = true;
    var some_failed = false;
    for(var i = 0; i < checkboxes.length; i++) {
        if (g_selected_rows.indexOf(checkboxes[i].name) === -1)
            all_selected = false;
        else
            none_selected = false;
        if (checkboxes[i].classList && checkboxes[i].classList.contains('failed'))
            some_failed = true;
    }

    // Toggle the state
    if (all_selected)
        remove_selected_rows(checkboxes);
    else
        select_all_rows(checkboxes, some_failed && none_selected);

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

            for(var a = 0; a < childs.length; a++) {
                if(childs[a].type == 'checkbox') {
                    checkboxes.push(childs[a]);
                }
            }


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
            elem = null;
        });
    }
    childs = null;

    update_row_selection_information();
}

function init_rowselect() {
    var tables = document.getElementsByClassName('data');
    for(var i = 0; i < tables.length; i++)
        if(tables[i].tagName === 'TABLE')
            table_init_rowselect(tables[i]);
    tables = null;
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
        if (oNode.tagName == "DIV" && !has_class(oNode, "togglebutton"))
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

/* This function is called after the table with of input elements
   has been rendered. It attaches the onFocus-function to the last
   of the input elements. That function will append another
   input field as soon as the user focusses the last field. */
function list_of_strings_init(divid) {
    var oContainer = document.getElementById(divid);
    var numChilds = oContainer.childNodes.length;
    var oLastChild = oContainer.childNodes[numChilds-1];
    list_of_strings_add_focus(oLastChild);
}

function list_of_strings_add_focus(oLastChild) {
    /* look for <input> in last child node and attach focus handler to it. */
    var input = oLastChild.getElementsByTagName("input");
    if (input.length == 1)
        input[0].onfocus = function(e) { return list_of_strings_extend(this); };
}


/* Is called when the last input field in a ListOfString gets focus.
   In that case a new input field is being appended. */
function list_of_strings_extend(oInput, j) {

    /* The input field has a unique name like "extra_emails_2" for the field with
       the index 2. We need to convert this into "extra_emails_3". */

    var oldName = oInput.name;
    var splitted = oldName.split("_");
    var num = 1 + parseInt(splitted[splitted.length-1]);
    splitted[splitted.length-1] = "" + num;
    var newName = splitted.join("_");

    /* Now create a new <div> element as a copy from the current one and
       replace this name. We do this by simply copying the HTML code. The
       last field is always empty. Remember: ListOfStrings() always renders
       one exceeding empty element. */

    var oDiv = oInput.parentNode;
    while (oDiv.parentNode.classList && !oDiv.parentNode.classList.contains("listofstrings"))
        oDiv = oDiv.parentNode;
    var oContainer = oDiv.parentNode;

    var oNewDiv = document.createElement("DIV");
    oNewDiv.innerHTML = oDiv.innerHTML.replace('"' + oldName + '"', '"' + newName + '"');
    // IE7 does not have quotes in innerHTML, trying to workaround this here.
    oNewDiv.innerHTML = oNewDiv.innerHTML.replace('=' + oldName + ' ', '=' + newName + ' ');
    oNewDiv.innerHTML = oNewDiv.innerHTML.replace('=' + oldName + '>', '=' + newName + '>');
    oContainer.appendChild(oNewDiv);

    /* Move focus function from old last to new last input field */
    list_of_strings_add_focus(oNewDiv);
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

function valuespec_textarea_resize(oArea) {
    oArea.style.height = (oArea.scrollHeight - 6) + "px"  ;
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

  var oTbody = oTable.childNodes[0];
  if(oTbody == undefined) { // no row -> no <tbody> present!
      oTbody = document.createElement('tbody');
      oTable.appendChild(oTbody);
  }

  // Hack for IE. innerHTML does not work on tbody/tr correctly.
  var container = document.createElement('div');
  container.innerHTML = '<table><tbody><tr>' + htmlcode + '</tr></tbody></tr>';
  var oTr = container.childNodes[0].childNodes[0].childNodes[0] // TR
  oTbody.appendChild(oTr);

  executeJSbyObject(oTable.lastChild);

  valuespec_listof_fixarrows(oTbody);
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
    var oTable = oTbody.parentNode;

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
    if(!oTbody || typeof(oTbody.rows) == undefined) {
        return;
    }

    for(var i = 0, row; row = oTbody.rows[i]; i++) {
        if(row.cells.length == 0)
            continue;
        var oTd = row.cells[0]; /* TD with buttons */
        if(row.cells[0].childNodes.length == 0)
            continue;
        var oIndex = oTd.childNodes[0];
        oIndex.value = "" + (parseInt(i) + 1);
        if (oTd.childNodes.length > 4) { /* movable */
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
            if (i >= oTbody.rows.length - 1) {
                oDownTrans.style.display = "";
                oDown.style.display = "none";
            }
            else {
                oDownTrans.style.display = "none";
                oDown.style.display = "";
            }
        }
    }
}

function vs_list_choice_toggle_all(varprefix) {
    var tbl = document.getElementById(varprefix + "_tbl");
    var checkboxes = tbl.getElementsByTagName("input");
    if (!checkboxes)
        return;

    // simply use state of first texbox as base
    var state = ! checkboxes[0].checked;
    for (var i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = state;
    }
}

function vs_textascii_button(img, text, how) {
    var oInput = img.previousElementSibling;
    while (oInput.tagName == "A")
        oInput = oInput.previousElementSibling;
    if (oInput.tagName != "INPUT")
        oInput = oInput.firstChild; // complain mode
    oInput.value = text + oInput.value; // TODO: how
    oInput.focus();
}


function vs_passwordspec_randomize(img) {
    password = "";
    while (password.length < 8) {
        a = parseInt(Math.random() * 128);
        if ((a >= 97 && a <= 122) ||
            (a >= 65 && a <= 90) ||
            (a >= 48 && a <= 57))  {
            c = String.fromCharCode(a);
            password += c;
        }
    }
    var oInput = img.previousElementSibling;
    if (oInput.tagName != "INPUT")
        oInput = oInput.firstChild; // in complain mode
    oInput.value = password;
}

function vs_duallist_enlarge(field_suffix, varprefix) {
    var field = document.getElementById(varprefix + '_' + field_suffix);
    if (field.id != varprefix + '_selected') {
        // The other field is the one without "_unselected" suffix
        var other_id = varprefix + '_selected';
        var positive = true;
    } else {
        // The other field is the one with "_unselected" suffix
        var other_id = varprefix + '_unselected';
        var positive = false;
    }

    var other_field = document.getElementById(other_id);
    if (!other_field)
        return;

    remove_class(other_field, 'large');
    add_class(other_field, 'small');
    remove_class(field, 'small');
    add_class(field, 'large');
}

function vs_duallist_switch(field_suffix, varprefix, keeporder) {
    var field = document.getElementById(varprefix + '_' + field_suffix);
    if (field.id != varprefix + '_selected') {
        // The other field is the one without "_unselected" suffix
        var other_id = varprefix + '_selected';
        var positive = true;
    } else {
        // The other field is the one with "_unselected" suffix
        var other_id = varprefix + '_unselected';
        var positive = false;
    }

    var other_field = document.getElementById(other_id);
    if (!other_field)
        return;

    var helper = document.getElementById(varprefix);
    if (!helper)
        return;

    // Move the selected options to the other select field
    var selected = [];
    for (var i = 0; i < field.options.length; i++) {
        if (field.options[i].selected) {
            selected.push(field.options[i]);
        }
    }
    if (selected.length == 0)
        return; // when add/remove clicked, but none selected

    // Now loop over all selected elements and add them to the other field
    for (var i = 0; i < selected.length; i++) {
        // remove option from origin
        field.removeChild(selected[i]);

        // Determine the correct child to insert. If keeporder is being set,
        // then new elements will aways be appended. That way the user can
        // create an order of his choice. This is being used if DualListChoice
        // has the option custom_order = True
        var sibling = false;

        if (!keeporder) {
            sibling = other_field.firstChild;
            while (sibling != null) {
                if (sibling.nodeType == 1 && sibling.label.toLowerCase() > selected[i].label.toLowerCase())
                    break;
                sibling = sibling.nextSibling
            }
        }

        if (sibling)
            other_field.insertBefore(selected[i], sibling);
        else
            other_field.appendChild(selected[i]);

        selected[i].selected = false;
    }

    // Update internal helper field which contains a list of all selected keys
    if (positive)
        var pos_field = other_field;
    else
        var pos_field = field;
    var texts = [];
    for (var i = 0; i < pos_field.options.length; i++) {
        texts.push(pos_field.options[i].value);
    }
    helper.value = texts.join('|')
}

function vs_iconselector_select(event, varprefix, value) {
    // set value of valuespec
    var obj = document.getElementById(varprefix + '_value');
    obj.value = value;

    var src_img = document.getElementById(varprefix + '_i_' + value);

    // Set the new choosen icon in the valuespecs image
    var img = document.getElementById(varprefix + '_img');
    img.src = src_img.src;

    toggle_popup(event, varprefix);
}

function vs_listofmultiple_add(varprefix) {
    var choice = document.getElementById(varprefix + '_choice');
    var ident = choice.value;

    if (ident == '')
        return;

    choice.options[choice.selectedIndex].disabled = true; // disable this choice

    // make the filter visible
    var row = document.getElementById(varprefix + '_' + ident + '_row');
    remove_class(row, 'unused');

    // Change the field names to used ones
    vs_listofmultiple_toggle_fields(row, varprefix, true);

    // Set value emtpy after adding one element
    choice.value = '';

    // Add it to the list of active elements
    var active = document.getElementById(varprefix + '_active');
    if (active.value != '')
        active.value += ';'+ident;
    else
        active.value = ident;
}

function vs_listofmultiple_del(varprefix, ident) {
    // make the filter invisible
    var row = document.getElementById(varprefix + '_' + ident + '_row');
    add_class(row, 'unused');

    // Change the field names to unused ones
    vs_listofmultiple_toggle_fields(row, varprefix, false);

    // Make it choosable from the dropdown field again
    var choice = document.getElementById(varprefix + '_choice');
    for (var i = 0; i < choice.childNodes.length; i++)
        if (choice.childNodes[i].value == ident)
            choice.childNodes[i].disabled = false;

    // Remove it from the list of active elements
    var active = document.getElementById(varprefix + '_active');
    var l = active.value.split(';');
    for (var i in l) {
        if (l[i] == ident) {
            l.splice(i, 1);
            break;
        }
    }
    active.value = l.join(';');
}

function vs_listofmultiple_toggle_fields(root, varprefix, enable) {
    if (root.tagName != 'TR')
        return; // only handle rows here
    var types = ['input', 'select', 'textarea'];
    for (var t in types) {
        var fields = root.getElementsByTagName(types[t]);
        for (var i in fields) {
            fields[i].disabled = !enable;
        }
    }
}

function vs_listofmultiple_init(varprefix) {
    document.getElementById(varprefix + '_choice').value = '';

    // Mark fields of unused elements as disabled
    var container = document.getElementById(varprefix + '_table');
    var unused = document.getElementsByClassName('unused', container);
    for (var i in unused) {
        vs_listofmultiple_toggle_fields(unused[i], varprefix, false);
    }
}

function help_enable() {
    var aHelp = document.getElementById('helpbutton');
    aHelp.style.display = "inline-block";
}

function help_toggle() {
    var aHelp = document.getElementById('helpbutton');
    if (aHelp.className == "active") {
        aHelp.className = "passive";
        help_switch(false);
    }
    else {
        aHelp.className = "active";
        help_switch(true);
    }
}

function help_switch(how) {
    // recursive scan for all div class=help elements
    var helpdivs = document.getElementsByClassName('help');
    for (var i=0; i<helpdivs.length; i++) {
        helpdivs[i].style.display = how ? "block" : "none";
    }

    // small hack for wato ruleset lists, toggle the "float" and "nofloat"
    // classes on those objects to make the layout possible
    var rulesetdivs = document.getElementsByClassName('ruleset');
    for (var i = 0; i < rulesetdivs.length; i++) {
        if (how) {
            if (has_class(rulesetdivs[i], 'float')) {
                remove_class(rulesetdivs[i], 'float');
                add_class(rulesetdivs[i], 'nofloat');
            }
        } else {
            if (has_class(rulesetdivs[i], 'nofloat')) {
                remove_class(rulesetdivs[i], 'nofloat');
                add_class(rulesetdivs[i], 'float');
            }
        }
    }

    get_url("ajax_switch_help.py?enabled=" + (how ? "yes" : ""));
}

/* Switch filter, commands and painter options */
function view_toggle_form(oButton, idForm) {
    var oForm = document.getElementById(idForm);
    if (oForm) {
        if (oForm.style.display == "none") {
            var display = "";
            var down = "down";
        }
        else {
            var display = "none";
            var down = "up";
        }
    }

    // Close all other view forms
    var alldivs = document.getElementsByClassName('view_form');
    for (var i=0; i<alldivs.length; i++) {
        if (alldivs[i] != oForm) {
            alldivs[i].style.display = "none";
        }
    }

    if (oForm)
        oForm.style.display = display;

    // Make other buttons inactive
    var allbuttons = document.getElementsByClassName('togglebutton');
    for (var i=0; i<allbuttons.length; i++) {
        var b = allbuttons[i];
        if (b != oButton && !has_class(b, "empth") && !has_class(b, "checkbox")) {
            remove_class(b, "down")
            add_class(b, "up")
        }
    }
    remove_class(oButton, "down");
    remove_class(oButton, "up");
    add_class(oButton, down);
}

function init_optiondial(id) {
    oDiv = document.getElementById(id);
    make_unselectable(oDiv);

    var eventname = (/Firefox/i.test(navigator.userAgent)) ? "DOMMouseScroll" : "mousewheel"

     if (oDiv.attachEvent) //if IE (and Opera depending on user setting)
             oDiv.attachEvent("on" + eventname, optiondial_wheel)
     else if (oDiv.addEventListener) //WC3 browsers
             oDiv.addEventListener(eventname, optiondial_wheel, false)

}

var dial_direction = 1;
function optiondial_wheel(e) {
    var evt = window.event || e;
    var delta = evt.detail ? evt.detail * (-120) : evt.wheelDelta;

    var oDiv;
    if (evt.target) oDiv = evt.target;
    else if (evt.srcElement) oDiv = evt.srcElement;
    if (evt.nodeType == 3) // defeat Safari bug
        oDiv = oDiv.parentNode;
    while (!oDiv.className)
        oDiv = oDiv.parentNode;


    code = ('' + (oDiv.onclick)).replace("this", "oDiv").replace("onclick", "dial_wheel_function");
    eval(code);
    if (delta > 0)
        dial_direction = -1;
    dial_wheel_function(e);
    dial_direction = 1;

    if (evt.preventDefault)
        evt.preventDefault();
    else
        return false;

}

// used for refresh und num_columns
function view_dial_option(oDiv, viewname, option, choices) {
    // prevent double click from select text
    var new_choice = choices[0]; // in case not contained in choices
    for (var c=0; c<choices.length; c++) {
        choice = choices[c];
        val = choice[0];
        title = choice[1];
        if (has_class(oDiv, "val_" + val)) {
            var new_choice = choices[(c + choices.length + dial_direction) % choices.length];
            change_class(oDiv, "val_" + val, "val_" + new_choice[0]);
            break;
        }
    }

    // Start animation
    step = 0;
    speed = 10;
    for (var way = 0; way <= 10; way +=1) {
        step += speed;
        setTimeout("turn_dial('" + option + "', '', " + way + "," + dial_direction + ")", step);
    }
    for (var way = -10; way <= 0; way +=1) {
        step += speed;
        setTimeout("turn_dial('" + option + "', '" + new_choice[1] + "', " + way + "," + dial_direction + ")", step);
    }

    get_url_sync("ajax_set_viewoption.py?view_name=" + viewname +
            "&option=" + option + "&value=" + new_choice[0]);
    if (option == "refresh")
        setReload(new_choice[0]);
    else {
        if (gReloadTimer)
            clearTimeout(gReloadTimer);
        gReloadTimer = setTimeout("handleReload('')", 400.0);
    }
    // handleReload('');
}
// way ranges from -10 to 10 means centered (normal place)
function turn_dial(option, text, way, direction) {
    var oDiv = document.getElementById("optiondial_" + option).firstChild;
    if (text && oDiv.innerHTML != text)
        oDiv.innerHTML = text;
    oDiv.style.top = (way * 1.3 * direction) + "px";
}


function make_unselectable(elem) {
    elem.onselectstart = function() { return false; };
    elem.style.MozUserSelect = "none";
    elem.style.KhtmlUserSelect = "none";
    elem.unselectable = "on";
}

/* Switch number of view columns, refresh and checkboxes. If the
   choices are missing, we do a binary toggle. */
gColumnSwitchTimeout = null;
function view_switch_option(oDiv, viewname, option, choices) {
    if (has_class(oDiv, "down")) {
        new_value = false;
        change_class(oDiv, "down", "up");
    }
    else {
        new_value = true;
        change_class(oDiv, "up", "down");
    }
    new_choice = [ new_value, '' ];

    get_url_sync("ajax_set_viewoption.py?view_name=" + viewname +
            "&option=" + option + "&value=" + new_choice[0]);

    if (option == "refresh") {
        setReload(new_choice[0]);
    } else if (option == "show_checkboxes") {
        g_selection_enabled = new_value;
    }

    handleReload('');
}

var g_hosttag_groups = {};

function host_tag_update_value(prefix, grp) {
    var value_select = document.getElementById(prefix + '_val');

    // Remove all options
    value_select.options.length = 0;

    if(grp === '')
        return; // skip over when empty group selected

    var opt = null;
    for (var i = 0, len = g_hosttag_groups[grp].length; i < len; i++) {
        opt = document.createElement('option');
        opt.value = g_hosttag_groups[grp][i][0];
        opt.text  = g_hosttag_groups[grp][i][1];
        value_select.appendChild(opt);
    }
    opt = null;
    value_select = null;
}

// .-Availability----------------------------------------------------------.
// |             _             _ _       _     _ _ _ _                     |
// |            / \__   ____ _(_) | __ _| |__ (_) (_) |_ _   _             |
// |           / _ \ \ / / _` | | |/ _` | '_ \| | | | __| | | |            |
// |          / ___ \ V / (_| | | | (_| | |_) | | | | |_| |_| |            |
// |         /_/   \_\_/ \__,_|_|_|\__,_|_.__/|_|_|_|\__|\__, |            |
// |                                                     |___/             |
// '-----------------------------------------------------------------------'

function timeline_hover(row_nr, onoff)
{
    var table = document.getElementsByClassName("timelineevents")[0];
    var row = table.children[0].children[row_nr+1];
    if (onoff)
        add_class(row, 'hilite');
    else {
        remove_class(row, 'hilite');
    }
}

//   .--Keybindings---------------------------------------------------------.
//   |        _  __          _     _           _ _                          |
//   |       | |/ /___ _   _| |__ (_)_ __   __| (_)_ __   __ _ ___          |
//   |       | ' // _ \ | | | '_ \| | '_ \ / _` | | '_ \ / _` / __|         |
//   |       | . \  __/ |_| | |_) | | | | | (_| | | | | | (_| \__ \         |
//   |       |_|\_\___|\__, |_.__/|_|_| |_|\__,_|_|_| |_|\__, |___/         |
//   |                 |___/                             |___/              |
//   +----------------------------------------------------------------------+

// var keybindings will be defined dynamically by htmllib.py
var keybindings_pressedkeys = [];

function keybindings_keydown(e) {
    if (!e) e = window.event;
    var keyCode = e.which || e.keyCode;
    keybindings_pressedkeys.push(keyCode);
    return keybindings_check(e);
}

function keybindings_keyup(e) {
    if (!e) e = window.event;
    var keyCode = e.which || e.keyCode;
    for (var i in keybindings_pressedkeys) {
        if (keybindings_pressedkeys[i] == keyCode) {
            keybindings_pressedkeys.splice(i, 1);
            break;
        }
    }
}

function keybindings_focus(e) {
    keybindings_pressedkeys = [];
}


function keybindings_check(e) {
    for (var i in keybindings) {
        var keylist = keybindings[i][0];
        if (keybindings_check_keylist(keylist)) {
            if (e.stopPropagation)
                e.stopPropagation();
            e.cancelBubble = true;
            var jscode = keybindings[i][1];
            eval(jscode);
            return false;
        }
    }
    return true;
}

function keybindings_check_keylist(keylist)
{
    for (var i in keylist) {
        if (keybindings_pressedkeys.indexOf(keylist[i]) < 0)
            return false;
    }
    return true;
}

//   .--Popups--------------------------------------------------------------.
//   |                  ____                                                |
//   |                 |  _ \ ___  _ __  _   _ _ __  ___                    |
//   |                 | |_) / _ \| '_ \| | | | '_ \/ __|                   |
//   |                 |  __/ (_) | |_) | |_| | |_) \__ \                   |
//   |                 |_|   \___/| .__/ \__,_| .__/|___/                   |
//   |                            |_|         |_|                           |
//   +----------------------------------------------------------------------+

function toggle_popup(event, id)
{
    if(!event)
        event = window.event;

    var obj = document.getElementById(id + '_popup');
    if(obj) {
        if(obj.style.display == 'none') {
            obj.style.display = 'block';
        } else {
            obj.style.display = 'none';
        }
        obj = null;
    }

    if (event.stopPropagation)
        event.stopPropagation();
    event.cancelBubble = true;

    // Disable the default events for all the different browsers
    if (event.preventDefault)
        event.preventDefault();
    else
        event.returnValue = false;
    return false;
}

// Add to Visual

var add_visual_data          = null;
var visualadd_popup_id       = null;
var visualadd_popup_contents = {};

function close_visualadd_popup()
{
    var menu = document.getElementById('visualadd_popup');
    if (menu) {
        // hide the open menu
        menu.parentNode.removeChild(menu);
        menu = null;
    }
    visualadd_popup_id = null;
}

// Registerd as click handler on the page while the visualadd menu is opened
// This is used to close the menu when the user clicks elsewhere
function handle_visualadd_close(event) {
    var target = getTarget(event);

    // Check whether or not a parent of the clicked node is the popup menu
    while (target && target.id != 'visualadd_popup' && !has_class(target, 'visualadd')) {
        target = target.parentNode;
    }

    if (target) {
        return true; // clicked menu or statusicon
    }

    close_visualadd_popup();
    del_event_handler('click', handle_visualadd_close);
}

function toggle_add_to_visual(event, trigger_obj, element_type, context, params)
{
    if(!event)
        event = window.event;
    var container = trigger_obj.parentNode;
    var ident;
    for (var i in container.parentNode.childNodes) {
        if (container.parentNode.childNodes[i] == container) {
            ident = i;
            break;
        }
    }

    close_visualadd_popup();

    if (visualadd_popup_id === ident) {
        visualadd_popup_id = null;
        return; // same icon clicked: just close the menu
    }
    visualadd_popup_id = ident;

    add_event_handler('click', handle_visualadd_close);

    menu = document.createElement('div');
    menu.setAttribute('id', 'visualadd_popup');
    menu.className = "popup_menu";

    // populate the menu using a webservice, because the list of dashboards
    // is not known in the javascript code. But it might have been cached
    // before. In this case do not perform a second request.
    if (ident in visualadd_popup_contents)
        menu.innerHTML = visualadd_popup_contents[ident];
    else
        get_url('ajax_popup_add_visual.py', add_dashboard_response_handler, [ident, event]);

    add_visual_data = [ element_type, context, params ];

    container.appendChild(menu);
    fix_visualadd_menu_position(event, menu);
}

function add_dashboard_response_handler(data, response_text)
{
    var ident = data[0];
    var event = data[1];
    visualadd_popup_contents[ident] = response_text;
    var menu = document.getElementById('visualadd_popup');
    if (menu) {
        menu.innerHTML = response_text;
        fix_visualadd_menu_position(event, menu);
    }
}

function fix_visualadd_menu_position(event, menu) {
    //
    //// When menu is out of screen on the right, move to left
    //if (menu.offsetLeft + menu.clientWidth > pageWidth()) {
    //    menu.style.left = (menu.offsetLeft - menu.clientWidth - 15) + 'px';
    //    menu.style.right = 'auto';
    //}

    // menu.offsetTop does not take whole page offset into account, because
    // it is positioned relative to another element. Take this into account
    var offset_top = menu.offsetTop + menu.offsetParent.offsetTop;

    // When menu is out of screen on the top, move to bottom
    console.log(offset_top)
    if (offset_top < 0) {
        menu.style.top = (menu.offsetTop + menu.clientHeight) + 'px';
        menu.style.bottom = 'auto';
    }
}

function add_to_visual(visual_type, visual_name)
{
    close_visualadd_popup();

    var context_txt = [];
    for (var key in add_visual_data[1]) {
        var ty = typeof(add_visual_data[1][key]);
        context_txt.push(key+':'+ty+':'+add_visual_data[1][key]);
    }

    var params_txt = [];
    for (var key in add_visual_data[2]) {
        var ty = typeof(add_visual_data[2][key]);
        params_txt.push(key+':'+ty+':'+add_visual_data[2][key]);
    }

    response = get_url_sync('ajax_add_visual.py?visual_type=' + visual_type
                                  + '&visual_name=' + visual_name
                                  + '&type=' + add_visual_data[0]
                                  + '&context=' + encodeURIComponent(context_txt.join('|'))
                                  + '&params=' + encodeURIComponent(params_txt.join('|')));
    add_visual_data = null;

    // After adding a dashlet, go to the choosen dashboard
    if (response)
        window.location.href = response;
}

var g_sidebar_reload_timer = null;

function reload_sidebar()
{
    if (parent && parent.frames[0]) {
        // reload sidebar, but preserve eventual quicksearch field value and focus
        var val = '';
        var focused = false;
        var field = parent.frames[0].document.getElementById('mk_side_search_field');
        if (field) {
            val = field.value;
            focused = parent.frames[0].document.activeElement == field;
        }

        parent.frames[0].document.reloading = 1;
        parent.frames[0].document.location.reload();

        if (field) {
            g_sidebar_reload_timer = setInterval(function (value, has_focus) {
                return function() {
                    if (!parent.frames[0].document.reloading
                        && parent.frames[0].document.readyState === 'complete') {
                        var field = parent.frames[0].document.getElementById('mk_side_search_field');
                        if (field) {
                            field.value = value;
                            if (has_focus) {
                                field.focus();

                                // Move caret to end
                                if (field.setSelectionRange !== undefined)
                                    field.setSelectionRange(value.length, value.length);
                            }
                            field = null;
                        }

                        clearInterval(g_sidebar_reload_timer);
                        g_sidebar_reload_timer = null;
                    }
                };
            }(val, focused), 50);

            field = null;
        }
    }
}
