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


//#   .-General------------------------------------------------------------.
//#   |                   ____                           _                 |
//#   |                  / ___| ___ _ __   ___ _ __ __ _| |                |
//#   |                 | |  _ / _ \ '_ \ / _ \ '__/ _` | |                |
//#   |                 | |_| |  __/ | | |  __/ | | (_| | |                |
//#   |                  \____|\___|_| |_|\___|_|  \__,_|_|                |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   | Generic library functions used anywhere in Check_MK                |
//#   '--------------------------------------------------------------------'

function has_class(o, cn) {
    if (typeof(o.className) === 'undefined')
        return false;
    var parts = o.className.split(' ');
    for (var x=0; x<parts.length; x++) {
        if (parts[x] == cn)
            return true;
    }
    return false;
}

function remove_class(o, cn) {
    var parts = o.className.split(' ');
    var new_parts = Array();
    for (var x=0; x<parts.length; x++) {
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

// Handle Enter key in textfields
function textinput_enter_submit(e, submit) {
    if (!e) {
        e = window.event;
    }

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

function has_canvas_support() {
    return document.createElement('canvas').getContext;
}

// convert percent to angle(rad)
function rad(g) {
    return (g * 360 / 100 * Math.PI) / 180;
}

// Returns timestamp in seconds incl. subseconds as decimal
function time() {
    return (new Date()).getTime() / 1000;
}

// simple implementation of function default arguments when
// using objects as function parameters. Example:
// function xxx(args) {
//     args = merge_args({
//         'arg2': 'default_val',
//     });
// }
// xxx({
//   'arg1': 'val1',
//   'arg3': 'val3',
// })
function merge_args()
{
    var defaults = arguments[0];
    var args = arguments[1] || {};

    for (var name in args)
        defaults[name] = args[name];

    return defaults;
}

// Tells the caller whether or not there are graphs on the current page
function has_graphing()
{
    return typeof g_graphs !== 'undefined';
}

function has_cross_domain_ajax_support()
{
    return 'withCredentials' in new XMLHttpRequest();
}

// Relative to viewport
function mouse_position(event) {
    return {
        x: event.clientX,
        y: event.clientY
    };
}

// mouse offset to the top/left coordinates of an object
function mouse_offset(obj, event){
    var obj_pos   = obj.getBoundingClientRect();
    var mouse_pos = mouse_position(event);
    return {
        "x": mouse_pos.left - obj_pos.x,
        "y": mouse_pos.top - obj_pos.y
    };
}

// mouse offset to the middle coordinates of an object
function mouse_offset_to_middle(obj, event){
    var obj_pos   = obj.getBoundingClientRect();
    var mouse_pos = mouse_position(event);
    return {
        "x": mouse_pos.x - (obj_pos.left + obj_pos.width/2),
        "y": mouse_pos.y - (obj_pos.top + obj_pos.height/2)
    };
}

function sort_select(select, cmp_func) {
    var choices = [];
    for (var i = 0; i < select.options.length;i++) {
        choices[i] = [];
        choices[i][0] = select.options[i].text;
        choices[i][1] = select.options[i].value;
    }

    choices.sort(cmp_func);
    while (select.options.length > 0) {
        select.options[0] = null;
    }

    for (var i = 0; i < choices.length;i++) {
        var op = new Option(choices[i][0], choices[i][1]);
        select.options[i] = op;
    }

    return;
}


//#.
//#   .-Events-------------------------------------------------------------.
//#   |                    _____                 _                         |
//#   |                   | ____|_   _____ _ __ | |_ ___                   |
//#   |                   |  _| \ \ / / _ \ '_ \| __/ __|                  |
//#   |                   | |___ \ V /  __/ | | | |_\__ \                  |
//#   |                   |_____| \_/ \___|_| |_|\__|___/                  |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   | User interaction event related                                     |
//#   '--------------------------------------------------------------------'

function getTarget(event) {
    return event.target ? event.target : event.srcElement;
}

function get_event_offset_x(event) {
    return event.offsetX == undefined ? event.layerX : event.offsetX;
}

function get_event_offset_y(event) {
    return event.offsetY == undefined ? event.layerY : event.offsetY;
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
function add_event_handler(type, func, obj) {
    obj = (typeof(obj) === 'undefined') ? window : obj;

    if (obj.addEventListener) {
        // W3 standard browsers
        obj.addEventListener(type, func, false);
    }
    else if (obj.attachEvent) {
        // IE<9
        obj.attachEvent("on" + type, func);
    }
    else {
        obj["on" + type] = func;
    }
}

function del_event_handler(type, func, obj) {
    obj = (typeof(obj) === 'undefined') ? window : obj;

    if (obj.removeEventListener) {
        // W3 stadnard browsers
        obj.removeEventListener(type, func, false);
    }
    else if (obj.detachEvent) {
        // IE<9
        obj.detachEvent("on"+type, func);
    }
    else {
        obj["on" + type] = null;
    }
}

function prevent_default_events(event) {
    if (event.preventDefault)
        event.preventDefault();
    if (event.stopPropagation)
        event.stopPropagation();
    event.returnValue = false;
    return false;
}

//#.
//#   .-Browser Fixes------------------------------------------------------.
//#   |    ____                                    _____ _                 |
//#   |   | __ ) _ __ _____      _____  ___ _ __  |  ___(_)_  _____  ___   |
//#   |   |  _ \| '__/ _ \ \ /\ / / __|/ _ \ '__| | |_  | \ \/ / _ \/ __|  |
//#   |   | |_) | | | (_) \ V  V /\__ \  __/ |    |  _| | |>  <  __/\__ \  |
//#   |   |____/|_|  \___/ \_/\_/ |___/\___|_|    |_|   |_/_/\_\___||___/  |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   | Browser detection and browser related workarounds                  |
//#   '--------------------------------------------------------------------'

// FIXME: cleanup
var browser         = navigator.userAgent.toLowerCase();
var weAreOpera      = browser.indexOf("opera") != -1;
var weAreFirefox    = browser.indexOf("firefox") != -1 || browser.indexOf("namoroka") != -1;

function is_ie_below_9() {
    return document.all && !document.addEventListener;
}

// Some browsers don't support indexOf on arrays. This implements the
// missing method
if (!Array.prototype.indexOf)
{
    Array.prototype.indexOf = function(elt /*, from*/) {
        var len = this.length;

        var from = Number(arguments[1]) || 0;
        from = (from < 0)
             ? Math.ceil(from)
             : Math.floor(from);
        if (from < 0)
            from += len;

        for (; from < len; from++) {
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
        tagName = tagName || '*';
        var _tags = root.getElementsByTagName(tagName);
        var _nodeList = [];

        for (var i = 0, _tag; _tag = _tags[i++];) {
            if (has_class(_tag, className)) {
                _nodeList.push(_tag);
            }
        }
        return _nodeList;
    };
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

// Not available in IE <9
if (!("nextElementSibling" in document.documentElement)) {
    Object.defineProperty(Element.prototype, "nextElementSibling", {
        get: function(){
            var e = this.nextSibling;
            while(e && 1 !== e.nodeType)
                e = e.nextSibling;
            return e;
        }
    });
}

// Not available in IE <9
if (!("children" in document.documentElement)) {
    Object.defineProperty(Element.prototype, "children", {
        get: function(){
            var typefilter = function(n){return n && n.nodeType == 1;};
            return Array.prototype.slice.call(this.childNodes).filter(typefilter);
        }
    });
}


// Not available in IE <9
if (!("lastElementChild" in document.documentElement)) {
    Object.defineProperty(Element.prototype, "lastElementChild", {
        get: function(){
            return this.children[this.children.length - 1];
        }
    });
}


//#.
//#   .-AJAX---------------------------------------------------------------.
//#   |                         _       _   _    __  __                    |
//#   |                        / \     | | / \   \ \/ /                    |
//#   |                       / _ \ _  | |/ _ \   \  /                     |
//#   |                      / ___ \ |_| / ___ \  /  \                     |
//#   |                     /_/   \_\___/_/   \_\/_/\_\                    |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   | AJAX call related functions                                        |
//#   '--------------------------------------------------------------------'

function call_ajax(url, optional_args)
{
    var args = merge_args({
        add_ajax_id      : true,
        plain_error      : false,
        response_handler : null,
        error_handler    : null,
        handler_data     : null,
        method           : "GET",
        post_data        : null,
        sync             : false
    }, optional_args);

    var AJAX = window.XMLHttpRequest ? new XMLHttpRequest()
                                     : new ActiveXObject("Microsoft.XMLHTTP");
    if (!AJAX)
        return null;

    // Dynamic part to prevent caching
    if (args.add_ajax_id) {
        url += url.indexOf('\?') !== -1 ? "&" : "?";
        url += "_ajaxid="+Math.floor(Date.parse(new Date()) / 1000);
    }

    if (args.plain_error) {
        url += url.indexOf('\?') !== -1 ? "&" : "?";
        url += "_plain_error=1";
    }

    try {
        AJAX.open(args.method, url, !args.sync);
    } catch (e) {
        if (args.error_handler) {
            args.error_handler(args.handler_data, null, e);
            return null;
        } else {
            throw e;
        }
    }

    if (args.method == "POST") {
        AJAX.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    }

    if (!args.sync) {
        AJAX.onreadystatechange = function() {
            if (AJAX && AJAX.readyState == 4) {
                if (AJAX.status == 200) {
                    if (args.response_handler)
                        args.response_handler(args.handler_data, AJAX.responseText);
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
                    if (args.error_handler)
                        args.error_handler(args.handler_data, AJAX.status, AJAX.statusText);
                }
            }
        };
    }

    AJAX.send(args.post_data);
    return AJAX;
}

function get_url(url, handler, data, errorHandler, addAjaxId)
{
    var args = {
        response_handler: handler
    };

    if (typeof data !== 'undefined')
        args.handler_data = data;

    if (typeof errorHandler !== 'undefined')
        args.error_handler = errorHandler;

    if (typeof addAjaxId !== 'undefined')
        args.add_ajax_id = addAjaxId;

    call_ajax(url, args);
}

function post_url(url, post_params, responseHandler, handler_data, errorHandler)
{
    var args = {
        method: "POST",
        post_data: post_params
    };

    if (typeof responseHandler !== 'undefined') {
        args.response_handler = responseHandler;
    }

    if (typeof handler_data !== 'undefined')
        args.handler_data = handler_data;

    if (typeof errorHandler !== 'undefined')
        args.error_handler = errorHandler;

    call_ajax(url, args);
}

function bulkUpdateContents(ids, codes)
{
    codes = eval(codes);
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
function updateContents(id, code)
{
    var obj = document.getElementById(id);
    if (obj) {
        obj.innerHTML = code;
        executeJS(id);
    }
}

// There may be some javascript code in the html code rendered by
// sidebar.py. Execute it here. This is needed in some browsers.
function executeJS(id)
{
    executeJSbyObject(document.getElementById(id));
}

var g_current_script = null;

function executeJSbyObject(obj)
{
    var aScripts = obj.getElementsByTagName('script');
    for(var i = 0; i < aScripts.length; i++) {
        if (aScripts[i].src && aScripts[i].src !== '') {
            var oScr = document.createElement('script');
            oScr.src = aScripts[i].src;
            document.getElementsByTagName("HEAD")[0].appendChild(oScr);
        }
        else {
            try {
                g_current_script = aScripts[i];
                eval(aScripts[i].text);
                g_current_script = null;
            } catch(e) {
                console.log(e);
                alert(aScripts[i].text + "\nError:" + e.message);
            }
        }
    }
}

//#.
//#   .-URL Handling-------------------------------------------------------.
//#   |     _   _ ____  _       _   _                 _ _ _                |
//#   |    | | | |  _ \| |     | | | | __ _ _ __   __| | (_)_ __   __ _    |
//#   |    | | | | |_) | |     | |_| |/ _` | '_ \ / _` | | | '_ \ / _` |   |
//#   |    | |_| |  _ <| |___  |  _  | (_| | | | | (_| | | | | | | (_| |   |
//#   |     \___/|_| \_\_____| |_| |_|\__,_|_| |_|\__,_|_|_|_| |_|\__, |   |
//#   |                                                           |___/    |
//#   +--------------------------------------------------------------------+
//#   |                                                                    |
//#   '--------------------------------------------------------------------'

// Function gets the value of the given url parameter
function getUrlParam(name, url) {
    name = name.replace('[', '\\[').replace(']', '\\]');
    url = (typeof url === 'undefined') ? window.location : url;

    var regex = new RegExp("[\\?&]" + name + "=([^&#]*)");
    var results = regex.exec(url);
    if(results === null)
        return '';
    return results[1];
}

/**
 * Function creates a new cleaned up URL
 * - Can add/overwrite parameters
 * - Removes _* parameters
 */
function makeuri(addvars, url) {
    url = (typeof(url) === 'undefined') ? window.location.href : url;

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
        params.push(encodeURIComponent(key) + '=' + encodeURIComponent(addvars[key]));
    }

    return base + '?' + params.join('&');
}

// ----------------------------------------------------------------------------
// GUI styling
// ----------------------------------------------------------------------------

function update_togglebutton(id, enabled)
{
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
        var oFloatFilter = oSelect.nextElementSibling;
        if (oFloatFilter) {
            toggle_input_fields(oFloatFilter, 'input', disable_others);
            toggle_input_fields(oFloatFilter, 'select', disable_others);
        }
    }
}

//#.
//#   .-Graphing-----------------------------------------------------------.
//#   |               ____                 _     _                         |
//#   |              / ___|_ __ __ _ _ __ | |__ (_)_ __   __ _             |
//#   |             | |  _| '__/ _` | '_ \| '_ \| | '_ \ / _` |            |
//#   |             | |_| | | | (_| | |_) | | | | | | | | (_| |            |
//#   |              \____|_|  \__,_| .__/|_| |_|_|_| |_|\__, |            |
//#   |                             |_|                  |___/             |
//#   +--------------------------------------------------------------------+
//#   | Performance graph handling                                         |
//#   '--------------------------------------------------------------------'

function pnp_error_response_handler(data, status_code, status_msg) {
    // PNP versions that do not have the JSON webservice respond with
    // 404. Current version with the webservice answer 500 if the service
    // in question does not have any PNP graphs. So we paint the fallback
    // graphs only if the respone code is 404 (not found).
    if (parseInt(status_code) == 404)
        fallback_graphs(data);
}

function pnp_response_handler(data, code) {
    var valid_response = true;
    var response = [];
    try {
        response = eval(code);
        for(var i = 0; i < response.length; i++) {
            var view = data['view'] == '' ? '0' : data['view'];
            create_pnp_graph(data, '&' + response[i]['image_url'].replace('#', '%23').replace('&view='+view, ''));
        }
    } catch(e) {
        valid_response = false;
    }

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
        create_pnp_graph(data, '&host=' + data['host'] + '&srv=' + data['service'] + '&source=' + s);
    }
}

function create_pnp_graph(data, params) {
    var urlvars = params + '&theme='+data['theme']+'&baseurl='+data['base_url'];

    if (typeof(data['start']) !== 'undefined' && typeof(data['end']) !== 'undefined')
        urlvars += '&start='+data['start']+'&end='+data['end'];

    var container = document.getElementById(data['container']);

    var img = document.createElement('img');
    img.src = data['pnp_url'] + 'index.php/image?view=' + data['view'] + urlvars;

    if (data.with_link) {
        var graph_container = document.createElement('div');
        graph_container.setAttribute('class', 'pnp_graph');

        var view   = data['view'] == '' ? 0 : data['view'];
        // needs to be extracted from "params", hack!
        var source = parseInt(getUrlParam('source', params)) + 1;

        // Add the control for adding the graph to a visual
        var visualadd = document.createElement('a');
        visualadd.title = data['add_txt'];
        visualadd.className = 'popup_trigger';
        visualadd.innerHTML = '<img src="images/icon_menu.png" class="icon">';
        visualadd.onclick = function(host, service, view, source) {
            return function(event) {
                toggle_popup(event, this, 'add_visual', 'add_visual',
                    ['pnpgraph',
                     { 'host': host, 'service': service },
                     { 'timerange': view, 'source': source }],
                    "add_type=pnpgraph",
                    null,
                    false
                );
            };
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

function render_pnp_graphs(container, site, host, service, pnpview, base_url, pnp_url, with_link, add_txt, from_ts, to_ts, pnp_theme)
{
    from_ts = (typeof from_ts === 'undefined') ? null : from_ts;
    to_ts   = (typeof to_ts === 'undefined') ? null : to_ts;

    var data = { 'container': container, 'base_url': base_url,
                 'pnp_url':   pnp_url,   'site':     site,
                 'host':      host,      'service':  service,
                 'with_link': with_link, 'view':     pnpview,
                 'add_txt':   add_txt,   'theme':    pnp_theme };

    if (from_ts !== null && to_ts !== null) {
        data['start'] = from_ts;
        data['end'] = to_ts;
    }

    var url = pnp_url + 'index.php/json?&host=' + encodeURIComponent(host)
              + '&srv=' + encodeURIComponent(service) + '&source=0&view=' + pnpview;
    get_url(url, pnp_response_handler, data, pnp_error_response_handler, false);
}

function show_hover_graphs(event, site_id, host_name, service_description, pnp_popup_url, force_pnp_graphing)
{
    event = event || window.event;

    show_hover_menu(event, "<div class=\"message\">Loading...</div>");

    if (force_pnp_graphing)
        show_pnp_hover_graphs(pnp_popup_url);
    else
        show_check_mk_hover_graphs(site_id, host_name, service_description);

    return prevent_default_events(event);
}

function show_check_mk_hover_graphs(site_id, host_name, service)
{
    var url = 'host_service_graph_popup.py?site='+encodeURIComponent(site_id)
                                        +'&host_name='+encodeURIComponent(host_name)
                                        +'&service='+encodeURIComponent(service);

    call_ajax(url, {
        response_handler : handle_check_mk_hover_graphs_response,
        error_handler    : handle_hover_graphs_error,
        method           : 'GET'
    });
}

function show_pnp_hover_graphs(url)
{
    call_ajax(url, {
        response_handler : handle_pnp_hover_graphs_response,
        error_handler    : handle_hover_graphs_error,
        method           : 'GET'
    });
}

function handle_check_mk_hover_graphs_response(_unused, code)
{
    if (code.indexOf('pnp4nagios') !== -1) {
        // fallback to pnp graph handling (received an URL with the previous ajax call)
        show_pnp_hover_graphs(code);
        return;
    }

    g_hover_menu.innerHTML = code;
    executeJSbyObject(g_hover_menu);
}


function handle_pnp_hover_graphs_response(_unused, code)
{
    // In case of PNP hover graph handling:
    // It is possible that, if using multisite based authentication, pnp sends a 302 redirect
    // to the login page which is transparently followed by XmlHttpRequest. There is no chance
    // to catch the redirect. So we try to check the response content. If it does not contain
    // the expected code, simply display an error message.
    if (code.indexOf('/image?') === -1) {
        // Error! unexpected response
        code = '<div class="error"> '
             + 'ERROR: Received an unexpected response '
             + 'while trying to display the PNP Graphs. Maybe there is a problem with the '
             + 'authentication.</div>';
    }

    g_hover_menu.innerHTML = code;
    executeJSbyObject(g_hover_menu);
}


function handle_hover_graphs_error(_unused, status_code, error_msg)
{
    g_hover_menu.innerHTML = '<div class=error>Update failed (' + status_code + ')</div>';
}


//#.
//#   .-Reschedule---------------------------------------------------------.
//#   |          ____                _              _       _              |
//#   |         |  _ \ ___  ___  ___| |__   ___  __| |_   _| | ___         |
//#   |         | |_) / _ \/ __|/ __| '_ \ / _ \/ _` | | | | |/ _ \        |
//#   |         |  _ <  __/\__ \ (__| | | |  __/ (_| | |_| | |  __/        |
//#   |         |_| \_\___||___/\___|_| |_|\___|\__,_|\__,_|_|\___|        |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   | Rescheduling of host/service checks                                |
//#   '--------------------------------------------------------------------'

// Protocol is:
// For regular response:
// [ 'OK', 'last check', 'exit status plugin', 'output' ]
// For timeout:
// [ 'TIMEOUT', 'output' ]
// For error:
// [ 'ERROR', 'output' ]
// Everything else:
// <undefined> - Unknown format. Simply echo.

function reschedule_check_response_handler(img, code) {
    var validResponse = true;
    var response = null;

    remove_class(img, "reloading");

    try {
        response = eval(code);
    } catch(e) {
        validResponse = false;
    }

    if(validResponse && response[0] === 'OK') {
        window.location.reload();
    } else if(validResponse && response[0] === 'TIMEOUT') {
        add_class(img, "reload_failed");
        img.title = 'Timeout while performing action: ' + response[1];
    } else if(validResponse) {
        add_class(img, "reload_failed");
        img.title = 'Problem while processing - Response: ' + response.join(' ');
    } else {
        add_class(img, "reload_failed");
        img.title = 'Invalid response: ' + response;
    }
}

function reschedule_check(oLink, site, host, service, wait_svc) {
    var img = oLink.getElementsByTagName("IMG")[0];
    remove_class(img, "reload_failed");
    add_class(img, "reloading");

    get_url('ajax_reschedule.py' +
            '?site='     + encodeURIComponent(site) +
            '&host='     + encodeURIComponent(host) +
            '&service='  + service + // Already URL-encoded!
            '&wait_svc=' + wait_svc,
            reschedule_check_response_handler, img);
}

//#.
//#   .-Page Reload--------------------------------------------------------.
//#   |        ____                    ____      _                 _       |
//#   |       |  _ \ __ _  __ _  ___  |  _ \ ___| | ___   __ _  __| |      |
//#   |       | |_) / _` |/ _` |/ _ \ | |_) / _ \ |/ _ \ / _` |/ _` |      |
//#   |       |  __/ (_| | (_| |  __/ |  _ <  __/ | (_) | (_| | (_| |      |
//#   |       |_|   \__,_|\__, |\___| |_| \_\___|_|\___/ \__,_|\__,_|      |
//#   |                   |___/                                            |
//#   +--------------------------------------------------------------------+
//#   |                                                                    |
//#   '--------------------------------------------------------------------'

// Stores the reload timer object (of views and also dashboards)
var g_reload_timer = null;
// Stores the reload pause timer object once the regular reload has
// been paused e.g. by modifying a graphs timerange or vertical axis.
var g_reload_pause_timer = null;
// This stores the refresh time of the page (But never 0)
var g_reload_interval = 0; // seconds
// This flag tells the handle_content_reload_error() function to add an
// error message about outdated data to the content container or not.
// The error message is only being added on the first error.
var g_reload_error = false;

function update_foot_refresh(secs)
{
    var o = document.getElementById('foot_refresh');
    var o2 = document.getElementById('foot_refresh_time');
    if (o) {
        if(secs == 0) {
            o.style.display = 'none';
        } else {
            o.style.display = 'inline-block';
            if(o2) {
                o2.innerHTML = secs;
            }
        }
    }
}

function update_header_timer()
{
    var oTime = document.getElementById('headertime');
    if (!oTime)
        return;

    var t = new Date();

    var hours = t.getHours();
    if (hours < 10)
        hours = "0" + hours;

    var min = t.getMinutes();
    if (min < 10)
        min = "0" + min;

    oTime.innerHTML = hours + ':' + min;

    var oDate = document.getElementById('headerdate');
    if (oDate) {
        var day   = ("0" + t.getDate()).slice(-2);
        var month = ("0" + (t.getMonth() + 1)).slice(-2);
        var year  = t.getFullYear();
        var date_format = oDate.getAttribute("format");
        oDate.innerHTML = date_format.replace(/yyyy/, year).replace(/mm/, month).replace(/dd/, day);
    }
}

// When called with one or more parameters parameters it reschedules the
// timer to the given interval. If the parameter is 0 the reload is stopped.
// When called with two parmeters the 2nd one is used as new url.
function set_reload(secs, url)
{
    stop_reload_timer();

    update_foot_refresh(secs);

    if (secs !== 0) {
        g_reload_interval = secs;
        schedule_reload(url);
    }
}


// Issues the timer for the next page reload. If some timer is already
// running, this timer is terminated and replaced by the new one.
function schedule_reload(url, milisecs)
{
    if (typeof url === 'undefined')
        url = ''; // reload current page (or just the content)

    if (typeof milisecs === 'undefined')
        milisecs = parseFloat(g_reload_interval) * 1000; // use default reload interval

    stop_reload_timer();

    g_reload_timer = setTimeout(function() {
        do_reload(url);
    }, milisecs);
}


function handle_content_reload(_unused, code) {
    g_reload_error = false;
    var o = document.getElementById('data_container');
    o.innerHTML = code;
    executeJS('data_container');

    // Update the header time
    update_header_timer();

    schedule_reload();
}


function handle_content_reload_error(_unused, status_code, error_msg)
{
    if(!g_reload_error) {
        var o = document.getElementById('data_container');
        o.innerHTML = '<div class=error>Update failed (' + status_code
                      + '). The shown data might be outdated</div>' + o.innerHTML;
        g_reload_error = true;
    }

    // Continue update after the error
    schedule_reload();
}


function stop_reload_timer()
{
    if (g_reload_timer) {
        clearTimeout(g_reload_timer);
        g_reload_timer = null;
    }
}


function do_reload(url)
{
    // Reschedule the reload in case the browser window / tab is not visible
    // for the user. Retry after short time.
    if (!is_window_active()) {
        setTimeout(function(){ do_reload(url); }, 250);
        return;
    }

    // Nicht mehr die ganze Seite neu laden, wenn es ein DIV "data_container" gibt.
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
        // Removed 'w' to reflect original rendering mechanism during reload
        // For example show the "Your query produced more than 1000 results." message
        // in views even during reload.
        var opts = [ 'h', 't', 'b', 'f', 'c', 'o', 'd', 'e', 'r', 'u' ];
        for (var i = 0; i < opts.length; i++) {
            if (display_options.indexOf(opts[i].toUpperCase()) > -1)
                display_options = display_options.replace(opts[i].toUpperCase(), opts[i]);
            else
                display_options += opts[i];
        }

        // Add optional display_options if not defined in original display_options
        opts = [ 'w' ];
        for (var i = 0; i < opts.length; i++) {
            if (display_options.indexOf(opts[i].toUpperCase()) == -1)
                display_options += opts[i];
        }

        var params = {'_display_options': display_options};
        var real_display_options = getUrlParam('display_options');
        if(real_display_options !== '')
            params['display_options'] = real_display_options;

        params['_do_actions'] = getUrlParam('_do_actions');

        // For dashlet reloads add a parameter to mark this request as reload
        if (window.location.href.indexOf("dashboard_dashlet.py") != -1)
            params["_reload"] = "1";

        if (g_selection_enabled)
            params["selection"] = g_selection;

        call_ajax(makeuri(params), {
            response_handler : handle_content_reload,
            error_handler    : handle_content_reload_error,
            method           : 'GET'
        });
    }
}


// Sets the reload timer in pause mode for X seconds. This is shown to
// the user with a pause overlay icon. The icon also shows the time when
// the pause ends. Once the user clicks on the pause icon or the time
// is reached, the whole page is reloaded.
function pause_reload(seconds)
{
    stop_reload_timer();
    draw_reload_pause_overlay(seconds);
    set_reload_pause_timer(seconds);
}


function set_reload_pause_timer(seconds)
{
    if (g_reload_pause_timer)
        clearTimeout(g_reload_pause_timer);

    g_reload_pause_timer = setTimeout(function () {
        update_reload_pause_timer(seconds);
    }, 1000);
}


function update_reload_pause_timer(seconds_left)
{
    seconds_left -= 1;

    if (seconds_left <= 0) {
        window.location.reload(false);
    }
    else {
        // update the pause counter
        var counter = document.getElementById("reload_pause_counter");
        if (counter) {
            counter.innerHTML = seconds_left;
        }

        g_reload_pause_timer = setTimeout(function() {
            update_reload_pause_timer(seconds_left);
        }, 1000);
    }
}


function stop_reload_pause_timer()
{
    if (!g_reload_pause_timer)
        return;

    clearTimeout(g_reload_pause_timer);
    g_reload_pause_timer = null;

    var counter = document.getElementById("reload_pause_counter");
    if (counter)
        counter.style.display = "none";
}


function draw_reload_pause_overlay(seconds)
{
    var container = document.getElementById("reload_pause");
    var counter;
    if (container) {
        // only render once. Just update the counter.
        counter = document.getElementById("reload_pause_counter");
        counter.innerHTML = seconds;
        return;
    }

    container = document.createElement("a");
    container.setAttribute("id", "reload_pause");
    container.href = "javascript:window.location.reload(false)";
    // FIXME: Localize
    container.title = "Page update paused. Click for reload.";

    var p1 = document.createElement("div");
    p1.className = "pause_bar p1";
    container.appendChild(p1);

    var p2 = document.createElement("div");
    p2.className = "pause_bar p2";
    container.appendChild(p2);

    container.appendChild(document.createElement("br"));

    counter = document.createElement("a");
    counter.setAttribute("id", "reload_pause_counter");
    // FIXME: Localize
    counter.title = "Click to stop the countdown.";
    counter.href = "javascript:stop_reload_pause_timer()";
    container.appendChild(counter);

    document.body.appendChild(container);
}

//#.
//#   .-Foldable Container-------------------------------------------------.
//#   |     _____     _     _       _     _       ____            _        |
//#   |    |  ___|__ | | __| | __ _| |__ | | ___ / ___|___  _ __ | |_      |
//#   |    | |_ / _ \| |/ _` |/ _` | '_ \| |/ _ \ |   / _ \| '_ \| __|     |
//#   |    |  _| (_) | | (_| | (_| | |_) | |  __/ |__| (_) | | | | |_ _    |
//#   |    |_|  \___/|_|\__,_|\__,_|_.__/|_|\___|\____\___/|_| |_|\__(_)   |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   |                                                                    |
//#   '--------------------------------------------------------------------'

function toggle_folding(img, to_be_opened) {
    if (to_be_opened) {
        change_class(img, "closed", "open");
    } else {
        change_class(img, "open", "closed");
    }
}

function toggle_tree_state(tree, name, oContainer, fetch_url) {
    var state;
    if (has_class(oContainer, 'closed')) {
        change_class(oContainer, 'closed', 'open');

        if (fetch_url && !oContainer.innerHTML) {
            call_ajax(fetch_url, {
                method           : "GET",
                response_handler : function(handler_data, response_body) {
                    handler_data.container.innerHTML = response_body;
                },
                handler_data     : {
                    container: oContainer
                }
            });
        }

        state = 'on';
        if (oContainer.tagName == 'TR') { // handle in-table toggling
            while (oContainer = oContainer.nextElementSibling)
                change_class(oContainer, 'closed', 'open');
        }
    }
    else {
        change_class(oContainer, 'open', 'closed');
        state = 'off';
        if (oContainer.tagName == 'TR') { // handle in-table toggling
            while (oContainer = oContainer.nextElementSibling)
                change_class(oContainer, 'open', 'closed');
        }
    }

    persist_tree_state(tree, name, state);
}

function persist_tree_state(tree, name, state)
{
    get_url('tree_openclose.py?tree=' + encodeURIComponent(tree)
            + '&name=' + encodeURIComponent(name) + '&state=' + state);
}

// fetch_url: dynamically load content of opened element.
function toggle_foldable_container(treename, id, fetch_url) {
    // Check, if we fold a NG-Norm
    var oNform = document.getElementById('nform.' + treename + '.' + id);
    if (oNform) {
        var oImg = oNform.children[0];
        var oTr = oNform.parentNode.nextElementSibling;
        toggle_tree_state(treename, id, oTr, fetch_url);

        if (oImg)
            toggle_folding(oImg, !has_class(oTr, "closed"));
    }
    else {
        var oImg = document.getElementById('treeimg.' + treename + '.' + id);
        var oBox = document.getElementById('tree.' + treename + '.' + id);
        toggle_tree_state(treename, id, oBox, fetch_url);

        if (oImg)
            toggle_folding(oImg, !has_class(oBox, "closed"));
    }
}


function toggle_grouped_rows(tree, id, cell, num_rows)
{
    var group_title_row = cell.parentNode;

    if (has_class(group_title_row, "closed")) {
        remove_class(group_title_row, "closed");
        var display = "";
        var toggle_img_open = true;
        var state = "on";
    }
    else {
        add_class(group_title_row, "closed");
        var display = "none";
        var toggle_img_open = false;
        var state = "off";
    }

    toggle_folding(cell.getElementsByTagName("IMG")[0], toggle_img_open);
    persist_tree_state(tree, id, state);

    var row = group_title_row;
    for (var i = 0; i < num_rows; i++) {
        row = row.nextElementSibling;
        row.style.display = display;
    }
}

//#.
//#   .-Row Selector-------------------------------------------------------.
//#   |      ____                 ____       _           _                 |
//#   |     |  _ \ _____      __ / ___|  ___| | ___  ___| |_ ___  _ __     |
//#   |     | |_) / _ \ \ /\ / / \___ \ / _ \ |/ _ \/ __| __/ _ \| '__|    |
//#   |     |  _ < (_) \ V  V /   ___) |  __/ |  __/ (__| || (_) | |       |
//#   |     |_| \_\___/ \_/\_/   |____/ \___|_|\___|\___|\__\___/|_|       |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   |                                                                    |
//#   '--------------------------------------------------------------------'

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
    var allTds = oTd.parentNode.children;
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
        var oTds = allTds[a].children;
        for(var x = 0; x < oTds.length; x++) {
            if(oTds[x].tagName === 'INPUT' && oTds[x].type == 'checkbox') {
                checkbox = oTds[x];
                break;
            }
        }
    }
    return checkbox;
}

function highlight_row(elem, on) {
    var checkbox = find_checkbox(elem);
    if(checkbox !== null) {
        iter_cells(checkbox, function(elem) {
            highlight_elem(elem, on);
        });
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
    if(target.tagName != 'TD' && target.tagName != 'LABEL')
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
    // 2. iterate over the children and search for the group header of the checkbox
    //    - Save the TR with class groupheader
    //    - End this search once found the checkbox element
    var this_row = checkbox.parentNode.parentNode;
    var rows     = this_row.parentNode.children;

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
                group_end = i;
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
    var row_childs = cell.parentNode.children;
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
}

// Container is an DOM element to search below or a list of DOM elements
// to search below
function get_all_checkboxes(container) {
    var checkboxes = [];

    if(typeof(container) === 'object' && container.length && !container.tagName) {
        // Array given - at the moment this is a list of TR objects
        // Skip the header checkboxes
        for(var i = 0; i < container.length; i++) {
            var childs = container[i].getElementsByTagName('input');

            for(var a = 0; a < childs.length; a++) {
                if(childs[a].type == 'checkbox') {
                    checkboxes.push(childs[a]);
                }
            }
        }
    } else {
        // One DOM node given
        var childs = container.getElementsByTagName('input');

        for(var i = 0; i < childs.length; i++)
            if(childs[i].type == 'checkbox')
                checkboxes.push(childs[i]);
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
}

//#.
//#   .-ElementDrag--------------------------------------------------------.
//#   |     _____ _                           _   ____                     |
//#   |    | ____| | ___ _ __ ___   ___ _ __ | |_|  _ \ _ __ __ _  __ _    |
//#   |    |  _| | |/ _ \ '_ ` _ \ / _ \ '_ \| __| | | | '__/ _` |/ _` |   |
//#   |    | |___| |  __/ | | | | |  __/ | | | |_| |_| | | | (_| | (_| |   |
//#   |    |_____|_|\___|_| |_| |_|\___|_| |_|\__|____/|_|  \__,_|\__, |   |
//#   |                                                           |___/    |
//#   +--------------------------------------------------------------------+
//#   | Generic GUI element dragger. The user can grab an elment, drag it  |
//#   | and moves a parent element of the picked element to another place. |
//#   | On dropping, the page is being reloaded for persisting the move.   |
//#   '--------------------------------------------------------------------

var g_element_dragging = null;

function element_drag_start(event, dragger, dragging_tag, drop_handler)
{
    if (!event)
        event = window.event;

    var button = getButton(event);

    // Skip calls when already dragging or other button than left mouse
    if (g_element_dragging !== null || button != 'LEFT')
        return true;

    // Find the first parent of the given tag type
    var dragging = dragger;
    while (dragging && dragging.tagName != dragging_tag)
        dragging = dragging.parentNode;

    if (dragging.tagName != dragging_tag)
        throw "Failed to find the parent node of " + dragger + " having the tag " + dragging_tag;

    add_class(dragging, "dragging");

    g_element_dragging = {
        "dragging"     : dragging,
        "moved"        : false,
        "drop_handler" : drop_handler,
    };

    return prevent_default_events(event);
}

function element_dragging(event)
{
    if (!event)
        event = window.event;

    if (g_element_dragging === null)
        return true;

    position_dragging_object(event);
}

function position_dragging_object(event)
{
    var dragging  = g_element_dragging.dragging,
        container = g_element_dragging.dragging.parentNode;

    var get_previous = function(node) {
        var previous = node.previousElementSibling;

        // In case this is a header TR, don't move it above this!
        // TODO: Does not work with all tables! See comment in finalize_dragging()
        if (previous && previous.children && previous.children[0].tagName == "TH")
            return null;

        return previous;
    };

    var get_next = function(node) {
        return node.nextElementSibling;
    };

    // Move it up?
    var previous = get_previous(dragging);
    while (previous && mouse_offset_to_middle(previous, event).y < 0) {
        g_element_dragging.moved = true;
        container.insertBefore(dragging, previous);
        previous = get_previous(dragging);
    }

    // Move it down?
    var next = get_next(dragging);
    while (next && mouse_offset_to_middle(next, event).y > 0) {
        g_element_dragging.moved = true;
        container.insertBefore(dragging, next.nextElementSibling);
        next = get_next(dragging);
    }
}

function element_drag_stop(event)
{
    if (!event)
        event = window.event;

    if (g_element_dragging === null)
        return true;

    finalize_dragging();
    g_element_dragging = null;

    return prevent_default_events(event);
}

function finalize_dragging()
{
    var dragging = g_element_dragging.dragging;
    remove_class(dragging, "dragging");

    if (!g_element_dragging.moved)
        return; // Nothing changed. Fine.

    var elements = dragging.parentNode.children;

    var index = Array.prototype.slice.call(elements).indexOf(dragging);

    // TODO: This currently makes the draggig work with tables having:
    // - no header
    // - one header line
    // Known things that don't work:
    // - second header (actions in tables)
    // - footer (like in WATO host list)
    var has_header = elements[0].children[0].tagName == 'TH';
    if (has_header)
        index -= 1;

    g_element_dragging.drop_handler(index);
}

function element_drag_url_drop_handler(base_url, index)
{
    var url = base_url + "&_index="+encodeURIComponent(index);
    location.href = url;

    //call_ajax(url, {
    //    method           : "GET",
    //    response_handler : handle_finalize_dragging,
    //    error_handler    : handle_finalize_dragging_error,
    //    plain_error      : true
    //});
}

function handle_finalize_dragging(handler_data, response_text)
{
    if (response_text != "")
        alert("Failed to persist drag result: " + response_text);
}

function handle_finalize_dragging_error(handler_data, status_code, error_msg)
{
    if (status_code != 0)
        alert("Failed to persist drag result: (" + status_code + "): " + error_msg);
}

// TODO: Only register when needed?
add_event_handler('mousemove', function(event) {
    return element_dragging(event);
});

// TODO: Only register when needed?
add_event_handler('mouseup', function(event) {
    return element_drag_stop(event);
});

//#.
//#   .-Context Button-----------------------------------------------------.
//#   |  ____            _            _     ____        _   _              |
//#   | / ___|___  _ __ | |_ _____  _| |_  | __ ) _   _| |_| |_ ___  _ __  |
//#   || |   / _ \| '_ \| __/ _ \ \/ / __| |  _ \| | | | __| __/ _ \| '_ \ |
//#   || |__| (_) | | | | ||  __/>  <| |_  | |_) | |_| | |_| || (_) | | | ||
//#   | \____\___/|_| |_|\__\___/_/\_\\__| |____/ \__,_|\__|\__\___/|_| |_||
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   | Context button scoring and visibility                              |
//#   '--------------------------------------------------------------------'

function count_context_button(oA)
{
    // Extract view name from id of parent div element
    var id = oA.parentNode.id;
    var AJAX = call_ajax("count_context_button.py?id=" + id, {
        sync:true
    });
    return AJAX.responseText;
}

function unhide_context_buttons(toggle_button)
{
    var cells = toggle_button.parentNode.parentNode;
    var children = cells.children;
    for (var i = 0; i < children.length; i++) {
        var node = children[i];
        if (node.tagName == "DIV" && !has_class(node, "togglebutton"))
            node.style.display = "";
    }
    toggle_button.parentNode.style.display = "none";
}

//#.
//#   .-ValueSpecs---------------------------------------------------------.
//#   |        __     __    _            ____                              |
//#   |        \ \   / /_ _| |_   _  ___/ ___| _ __   ___  ___ ___         |
//#   |         \ \ / / _` | | | | |/ _ \___ \| '_ \ / _ \/ __/ __|        |
//#   |          \ V / (_| | | |_| |  __/___) | |_) |  __/ (__\__ \        |
//#   |           \_/ \__,_|_|\__,_|\___|____/| .__/ \___|\___|___/        |
//#   |                                       |_|                          |
//#   +--------------------------------------------------------------------+
//#   | Functions needed by HTML code from ValueSpec (valuespec.py)        |
//#   '--------------------------------------------------------------------'

function valuespec_toggle_option(oCheckbox, divid, negate) {
    var oDiv = document.getElementById(divid);
    if ((oCheckbox.checked && !negate) || (!oCheckbox.checked && negate))
        oDiv.style.display = "";
    else
        oDiv.style.display = "none";
}

function valuespec_toggle_dropdown(oDropdown, divid) {
    var oDiv = document.getElementById(divid);
    if (oDropdown.value == "other") oDiv.style.display = "";
    else
        oDiv.style.display = "none";
}

function valuespec_toggle_dropdownn(oDropdown, divid) {
    var oDiv = document.getElementById(divid);
    if (oDropdown.value == "ignore")
        oDiv.style.display = "none";
    else
        oDiv.style.display = "";
}

/* This function is called after the table with of input elements
   has been rendered. It attaches the onFocus-function to the last
   of the input elements. That function will append another
   input field as soon as the user focusses the last field. */
function list_of_strings_init(divid) {
    var oContainer = document.getElementById(divid);
    var oDivChildren = oContainer.getElementsByTagName("div");
    var oLastChild = oDivChildren[oDivChildren.length-1];
    list_of_strings_add_focus(oLastChild);
}

function list_of_strings_add_focus(oLastChild) {
    /* look for <input> in last child node and attach focus handler to it. */
    var input = oLastChild.getElementsByTagName("input");
    if (input.length == 1) {
        var handler_func = function(e) {
            if (this.value != "") {
                return list_of_strings_extend(this);
            }
        };

        input[0].onfocus = handler_func;
        input[0].oninput = handler_func;
    }
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

    oInput.oninput = null;
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

function valuespec_textarea_resize(oArea, theme)
{
    if (theme == "facelift") {
        delimiter = 16;
    } else {
        delimiter = 6;
    }
    oArea.style.height = (oArea.scrollHeight - delimiter) + "px";
}

function valuespec_listof_add(varprefix, magic)
{
    var oCountInput = document.getElementById(varprefix + "_count");
    var count = parseInt(oCountInput.value);
    var strcount = "" + (count + 1);
    oCountInput.value = strcount;
    var oPrototype = document.getElementById(varprefix + "_prototype").children[0].children[0]; // TR
    var htmlcode = oPrototype.innerHTML;
    // replace the magic
    var re = new RegExp(magic, "g");
    htmlcode = htmlcode.replace(re, strcount);

    // in some cases the magic might be URL encoded. Also replace these occurences.
    re       = new RegExp(encodeURIComponent(magic).replace('!', '%21'), "g");
    htmlcode = htmlcode.replace(re, strcount);

    var oTable = document.getElementById(varprefix + "_table");

    var oTbody = oTable.children[0];
    if(oTbody == undefined) { // no row -> no <tbody> present!
        oTbody = document.createElement('tbody');
        oTable.appendChild(oTbody);
    }

    // Hack for IE. innerHTML does not work on tbody/tr correctly.
    var container = document.createElement('div');
    container.innerHTML = '<table><tbody><tr>' + htmlcode + '</tr></tbody></tr>';
    var oTr = container.children[0].children[0].children[0]; // TR
    oTbody.appendChild(oTr);

    executeJSbyObject(oTable.lastElementChild);

    valuespec_listof_fixarrows(oTbody);
}

// When deleting we do not fix up indices but simply
// remove the according table row and add an invisible
// input element with the name varprefix + "_deleted_%nr"
function valuespec_listof_delete(oA, varprefix, nr) {
    var oTr = oA.parentNode.parentNode; // TR
    var oTbody = oTr.parentNode;
    var oInput = document.createElement("input");
    oInput.type = "hidden";
    oInput.name = "_" + varprefix + '_deleted_' + nr;
    oInput.value = "1";
    var oTable = oTbody.parentNode;
    oTable.parentNode.insertBefore(oInput, oTable);
    oTbody.removeChild(oTr);
    valuespec_listof_fixarrows(oTbody);
}

function vs_listof_drop_handler(handler_args, new_index)
{
    var varprefix = handler_args.varprefix;
    var cur_index = handler_args.cur_index;

    var indexof = document.getElementsByName(varprefix + "_indexof_" + cur_index);
    if (indexof.length == 0)
        throw "Failed to find the indexof_fied";
    indexof = indexof[0];

    // Find the tbody parent of the given tag type
    var tbody = indexof;
    while (tbody && tbody.tagName != "TBODY")
        tbody = tbody.parentNode;

    if (!tbody)
        throw "Failed to find the tbody element of " + indexof;

    valuespec_listof_fixarrows(tbody);
}

function valuespec_listof_sort(varprefix, magic, sort_by) {
    var table = document.getElementById(varprefix + "_table");
    var tbody = table.firstChild;
    var rows = tbody.rows;

    var entries = [];
    for (var i = 0, td, sort_field_name, fields; i < rows.length; i++) {
        // Find the index of this row
        td = rows[i].cells[0]; /* TD with buttons */
        if(td.children.length == 0)
            continue;
        var index = td.getElementsByClassName("orig_index")[0].value;

        sort_field_name = varprefix + "_" + index + "_" + sort_by;

        // extract the sort field value and add it to the entries list
        // together with the row to be moved
        fields = document.getElementsByName(sort_field_name);
        if (fields.length == 0) {
            return; // abort sorting
        }

        entries.push({
            sort_value : fields[0].value,
            row_node   : rows[i]
        });
    }

    entries.sort(function (a, b) {
        if (a.sort_value.toLowerCase() < b.sort_value.toLowerCase()) {
             return -1;
        }
        if (a.sort_value.toLowerCase() > b.sort_value.toLowerCase()) {
            return 1;
        }
        return 0;
    });

    // Remove all rows from the list and then add the rows back to it
    // in sorted order

    while (tbody.firstChild) {
        tbody.removeChild(tbody.firstChild);
    }

    for (var i = 0; i < entries.length; i++) {
        tbody.appendChild(entries[i].row_node);
    }

    valuespec_listof_fixarrows(tbody);
}


function valuespec_listof_fixarrows(oTbody) {
    if(!oTbody || typeof(oTbody.rows) == undefined) {
        return;
    }

    for(var i = 0, row; row = oTbody.rows[i]; i++) {
        if(row.cells.length == 0)
            continue;

        var oTd = row.cells[0]; /* TD with buttons */
        if(oTd.children.length == 0)
            continue;

        var oIndex = oTd.getElementsByClassName("index")[0];
        if (oIndex.value === "") {
            // initialization of recently added row
            var orig_index = oTd.getElementsByClassName("orig_index")[0];
            orig_index.value = "" + (i+1);
        }
        oIndex.value = "" + (i+1);

        if (oTd.childNodes.length > 4) { /* movable */
            var buttons = oTd.getElementsByClassName("iconbutton");

            var oUpTrans = buttons[1];
            var oUp      = buttons[2];
            if (i == 0) {
                oUpTrans.style.display = "";
                oUp.style.display = "none";
            }
            else {
                oUpTrans.style.display = "none";
                oUp.style.display = "";
            }
            var oDownTrans = buttons[3];
            var oDown      = buttons[4];
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

function vs_rule_comment_prefix_date_and_user(img, text) {
    var container = img.parentNode.parentNode;
    var textarea = container.getElementsByTagName("textarea")[0];

    if (!textarea) {
        console.log("Failed to find textarea object");
        return;
    }

    textarea.value = text + "\n" + textarea.value;
    textarea.focus();
    textarea.setSelectionRange(text.length, text.length);
}


function vs_passwordspec_randomize(img) {
    var a, c, password = "";
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
        oInput = oInput.children[0]; // in complain mode
    oInput.value = password;
}

function vs_toggle_hidden(img) {
    var oInput = img;
    while (oInput.tagName != "INPUT")
        oInput = oInput.previousElementSibling;
    if (oInput.type == "text") {
        oInput.type = "password";
    } else {
        oInput.type = "text";
    }
}

function vs_duallist_enlarge(field_suffix, varprefix) {
    var field = document.getElementById(varprefix + '_' + field_suffix);
    if (field.id != varprefix + '_selected') {
        // The other field is the one without "_unselected" suffix
        var other_id = varprefix + '_selected';
    } else {
        // The other field is the one with "_unselected" suffix
        var other_id = varprefix + '_unselected';
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
        other_field.appendChild(selected[i]);

        selected[i].selected = false;
    }

    // Determine the correct child to insert. If keeporder is being set,
    // then new elements will aways be appended. That way the user can
    // create an order of his choice. This is being used if DualListChoice
    // has the option custom_order = True
    if (!keeporder) {
        var collator = new Intl.Collator(undefined, {numeric: true, sensitivity: 'base'});
        sort_select(other_field, collator.compare);
    }

    // Update internal helper field which contains a list of all selected keys
    var pos_field = positive ? other_field : field;

    var texts = [];
    for (var i = 0; i < pos_field.options.length; i++) {
        texts.push(pos_field.options[i].value);
    }
    helper.value = texts.join('|');
}

function vs_iconselector_select(event, varprefix, value) {
    // set value of valuespec
    var obj = document.getElementById(varprefix + '_value');
    obj.value = value;

    var src_img = document.getElementById(varprefix + '_i_' + value);

    // Set the new choosen icon in the valuespecs image
    var img = document.getElementById(varprefix + '_img');
    img.src = src_img.src;

    close_popup();
}

function vs_iconselector_toggle(varprefix, category_name) {
    // Update the navigation
    var nav_links = document.getElementsByClassName(varprefix+'_nav');
    for (var i = 0; i < nav_links.length; i++) {
        if (nav_links[i].id == varprefix+'_'+category_name+'_nav')
            add_class(nav_links[i].parentNode, 'active');
        else
            remove_class(nav_links[i].parentNode, 'active');
    }

    // Now update the category containers
    var containers = document.getElementsByClassName(varprefix+'_container');
    for (var i = 0; i < containers.length; i++) {
        if (containers[i].id == varprefix+'_'+category_name+'_container')
            containers[i].style.display = '';
        else
            containers[i].style.display = 'none';
    }
}

function vs_iconselector_toggle_names(event, varprefix) {
    var icons = document.getElementById(varprefix+'_icons');
    if (has_class(icons, "show_names"))
        remove_class(icons, "show_names");
    else
        add_class(icons, "show_names");
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
    for (var i = 0; i < choice.children.length; i++)
        if (choice.children[i].value == ident)
            choice.children[i].disabled = false;

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

    vs_listofmultiple_disable_selected_options(varprefix);

    // Mark input fields of unused elements as disabled
    var container = document.getElementById(varprefix + '_table');
    var unused = document.getElementsByClassName('unused', container);
    for (var i in unused) {
        vs_listofmultiple_toggle_fields(unused[i], varprefix, false);
    }
}

// The <option> elements in the <select> field of the currently choosen
// elements need to be disabled.
function vs_listofmultiple_disable_selected_options(varprefix)
{
    var active_choices = document.getElementById(varprefix + '_active').value.split(";");

    var choice_field = document.getElementById(varprefix + '_choice');
    for (var i = 0; i < choice_field.children.length; i++) {
        if (active_choices.indexOf(choice_field.children[i].value) !== -1) {
            choice_field.children[i].disabled = true;
        }
    }
}

var g_autocomplete_ajax = null;

function vs_autocomplete(input, completion_ident, completion_params, on_change)
{
    // TextAscii does not set the id attribute on the input field.
    // Set the id to the name of the field here.
    input.setAttribute("id", input.name);

    // Terminate pending request
    if (g_autocomplete_ajax) {
        g_autocomplete_ajax.abort();
    }

    g_autocomplete_ajax = call_ajax("ajax_vs_autocomplete.py?ident=" + encodeURIComponent(completion_ident), {
        response_handler : vs_autocomplete_handle_response,
        error_handler    : vs_autocomplete_handle_error,
        handler_data     : [ input.id, on_change ],
        method           : "POST",
        post_data        : "params="+encodeURIComponent(JSON.stringify(completion_params))
                          +"&value="+encodeURIComponent(input.value)
                          +"&_plain_error=1",
        add_ajax_id      : false
    });
}

function vs_autocomplete_handle_response(handler_data, response_text)
{
    var input_id = handler_data[0];
    var on_change = handler_data[1];

    try {
        var response = eval(response_text);
    } catch(e) {
        vs_autocomplete_show_error(input_id, response_text);
        return;
    }

    if (response.length == 0) {
        vs_autocomplete_close(input_id);
    }
    else {
        // When only one result and values equal, hide the menu
        var input = document.getElementById(input_id);
        if (response.length == 1
            && input
            && response[0][0] == input.value) {
            vs_autocomplete_close(input_id);
            return;
        }

        vs_autocomplete_show_choices(input_id, on_change, response);
    }
}

function vs_autocomplete_handle_error(handler_data, status_code, error_msg)
{
    var input_id = handler_data[0];

    if (status_code == 0)
        return; // aborted (e.g. by subsequent call)
    vs_autocomplete_show_error(input_id, error_msg + " (" + status_code + ")");
}

function vs_autocomplete_show_choices(input_id, on_change, choices)
{
    var code = "<ul>";
    for(var i = 0; i < choices.length; i++) {
        var value = choices[i][0];
        var label = choices[i][1];

        code += "<li onclick=\"vs_autocomplete_choose('"
                    + input_id + "', '" + value + "');"
                    + on_change + "\">" + label + "</li>";
    }
    code += "</ul>";

    vs_autocomplete_show(input_id, code);
}

function vs_autocomplete_choose(input_id, value)
{
    var input = document.getElementById(input_id);
    input.value = value;
    vs_autocomplete_close(input_id);
}

function vs_autocomplete_show_error(input_id, msg)
{
    vs_autocomplete_show(input_id, "<div class=error>ERROR: " + msg + "</div>");
}

function vs_autocomplete_show(input_id, inner_html)
{
    var popup = document.getElementById(input_id + "_popup");
    if (!popup) {
        var input = document.getElementById(input_id);
        popup = document.createElement("div");
        popup.setAttribute("id", input_id + "_popup");
        popup.className = "vs_autocomplete";
        input.parentNode.appendChild(popup);

        // set minimum width of list to input field width
        popup.style.minWidth = input.clientWidth + "px";
    }

    popup.innerHTML = inner_html;
}

function vs_autocomplete_close(input_id)
{
    var popup = document.getElementById(input_id + "_popup");
    if (popup)
        popup.parentNode.removeChild(popup);
}


var vs_color_pickers = [];

function vs_update_color_picker(varprefix, hex, update_picker) {
    if (!/^#[0-9A-F]{6}$/i.test(hex))
        return; // skip invalid/unhandled colors

    document.getElementById(varprefix + "_input").value = hex;
    document.getElementById(varprefix + "_value").value = hex;
    document.getElementById(varprefix + "_preview").style.backgroundColor = hex;

    if (update_picker)
        vs_color_pickers[varprefix].setHex(hex);
}

//#.
//#   .-Help Toggle--------------------------------------------------------.
//#   |          _   _      _         _____                 _              |
//#   |         | | | | ___| |_ __   |_   _|__   __ _  __ _| | ___         |
//#   |         | |_| |/ _ \ | '_ \    | |/ _ \ / _` |/ _` | |/ _ \        |
//#   |         |  _  |  __/ | |_) |   | | (_) | (_| | (_| | |  __/        |
//#   |         |_| |_|\___|_| .__/    |_|\___/ \__, |\__, |_|\___|        |
//#   |                      |_|                |___/ |___/                |
//#   +--------------------------------------------------------------------+
//#   |                                                                    |
//#   '--------------------------------------------------------------------'

function enable_help()
{
    var help = document.getElementById('helpbutton');
    help.style.display = "inline-block";
}

function toggle_help()
{
    var help = document.getElementById('helpbutton');
    if (has_class(help, "active")) {
        remove_class(help, "active");
        add_class(help, "passive");
        switch_help(false);
    } else {
        add_class(help, "active");
        remove_class(help, "passive");
        switch_help(true);
    }
}

function switch_help(how)
{
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
function view_toggle_form(button, form_id) {
    var display = "none";
    var down    = "up";

    var form = document.getElementById(form_id);
    if (form && form.style.display == "none") {
        display = "";
        down    = "down";
    }

    // Close all other view forms
    var alldivs = document.getElementsByClassName('view_form');
    for (var i=0; i<alldivs.length; i++) {
        if (alldivs[i] != form) {
            alldivs[i].style.display = "none";
        }
    }

    if (form)
        form.style.display = display;

    // Make other buttons inactive
    var allbuttons = document.getElementsByClassName('togglebutton');
    for (var i=0; i<allbuttons.length; i++) {
        var b = allbuttons[i];
        if (b != button && !has_class(b, "empth") && !has_class(b, "checkbox")) {
            remove_class(b, "down");
            add_class(b, "up");
        }
    }
    remove_class(button, "down");
    remove_class(button, "up");
    add_class(button, down);
}

function wheel_event_name()
{
    if ("onwheel" in window)
        return "wheel";
    else if (weAreFirefox)
        return "DOMMouseScroll";
    else
        return "mousewheel";
}

function wheel_event_delta(event)
{
    return event.deltaY ? event.deltaY
                        : event.detail ? event.detail * (-120)
                                       : event.wheelDelta;
}

function init_optiondial(id)
{
    var container = document.getElementById(id);
    make_unselectable(container);
    add_event_handler(wheel_event_name(), optiondial_wheel, container);
}

var g_dial_direction = 1;
var g_last_optiondial = null;
function optiondial_wheel(event) {
    event = event || window.event;
    var delta = wheel_event_delta(event);

    // allow updates every 100ms
    if (g_last_optiondial > time() - 0.1) {
        return prevent_default_events(event);
    }
    g_last_optiondial = time();

    var container = getTarget(event);
    if (event.nodeType == 3) // defeat Safari bug
        container = container.parentNode;
    while (!container.className)
        container = container.parentNode;

    if (delta > 0)
        g_dial_direction = -1;
    container.onclick(event);
    g_dial_direction = 1;

    return prevent_default_events(event);
}

// used for refresh und num_columns
function view_dial_option(oDiv, viewname, option, choices) {
    // prevent double click from select text
    var new_choice = choices[0]; // in case not contained in choices
    for (var c = 0, choice = null, val = null; c < choices.length; c++) {
        choice = choices[c];
        val = choice[0];
        if (has_class(oDiv, "val_" + val)) {
            new_choice = choices[(c + choices.length + g_dial_direction) % choices.length];
            change_class(oDiv, "val_" + val, "val_" + new_choice[0]);
            break;
        }
    }

    // Start animation
    var step = 0;
    var speed = 10;

    for (var way = 0; way <= 10; way +=1) {
        step += speed;
        setTimeout(function(option, text, way, direction) {
            return function() {
                turn_dial(option, text, way, direction);
            };
        }(option, "", way, g_dial_direction), step);
    }

    for (var way = -10; way <= 0; way +=1) {
        step += speed;
        setTimeout(function(option, text, way, direction) {
            return function() {
                turn_dial(option, text, way, direction);
            };
        }(option, new_choice[1], way, g_dial_direction), step);
    }

    var url = "ajax_set_viewoption.py?view_name=" + viewname +
              "&option=" + option + "&value=" + new_choice[0];
    call_ajax(url, {
        method           : "GET",
        response_handler : function(handler_data, response_body) {
            if (handler_data.option == "refresh")
                set_reload(handler_data.new_value);
            else
                schedule_reload('', 400.0);
        },
        handler_data     : {
            new_value : new_choice[0],
            option    : option
        }
    });
}

// way ranges from -10 to 10 means centered (normal place)
function turn_dial(option, text, way, direction)
{
    var oDiv = document.getElementById("optiondial_" + option).getElementsByTagName("DIV")[0];
    if (text && oDiv.innerHTML != text)
        oDiv.innerHTML = text;
    oDiv.style.top = (way * 1.3 * direction) + "px";
}

function make_unselectable(elem)
{
    elem.onselectstart = function() { return false; };
    elem.style.MozUserSelect = "none";
    elem.style.KhtmlUserSelect = "none";
    elem.unselectable = "on";
}

// TODO: Is gColumnSwitchTimeout and view_switch_option needed at all?
// TODO: Where is handleReload defined?
/* Switch number of view columns, refresh and checkboxes. If the
   choices are missing, we do a binary toggle. */
gColumnSwitchTimeout = null;
function view_switch_option(oDiv, viewname, option, choices) {
    var new_value;
    if (has_class(oDiv, "down")) {
        new_value = false;
        change_class(oDiv, "down", "up");
    }
    else {
        new_value = true;
        change_class(oDiv, "up", "down");
    }
    var new_choice = [ new_value, '' ];

    var url = "ajax_set_viewoption.py?view_name=" + viewname +
               "&option=" + option + "&value=" + new_choice[0];

    call_ajax(url, {
        method           : "GET",
        response_handler : function(handler_data, response_body) {
            if (handler_data.option == "refresh") {
                set_reload(handler_data.new_value);
            } else if (handler_data.option == "show_checkboxes") {
                g_selection_enabled = handler_data.new_value;
            }

            handleReload('');
        },
        handler_data     : {
            new_value : new_value,
            option    : option
        }
    });

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
}

//#.
//#   .-Availability-------------------------------------------------------.
//#   |             _             _ _       _     _ _ _ _                  |
//#   |            / \__   ____ _(_) | __ _| |__ (_) (_) |_ _   _          |
//#   |           / _ \ \ / / _` | | |/ _` | '_ \| | | | __| | | |         |
//#   |          / ___ \ V / (_| | | | (_| | |_) | | | | |_| |_| |         |
//#   |         /_/   \_\_/ \__,_|_|_|\__,_|_.__/|_|_|_|\__|\__, |         |
//#   |                                                     |___/          |
//#   +--------------------------------------------------------------------+
//#   |                                                                    |
//#   '--------------------------------------------------------------------'

function timeline_hover(row_nr, onoff)
{
    var row = document.getElementById("timetable_" + row_nr);
    if (!row)
        return;

    if (onoff) {
        add_class(row, 'hilite');
    } else {
        remove_class(row, 'hilite');
    }
}


function timetable_hover(row_nr, onoff)
{
    var slice = document.getElementById("timeline_" + row_nr);
    if (!slice)
        return;

    if (onoff) {
        add_class(slice, 'hilite');
    } else {
        remove_class(slice, 'hilite');
    }
}


//#.
//#   .--SLA-----------------------------------------------------------------.
//#   |                         ____  _        _                             |
//#   |                        / ___|| |      / \                            |
//#   |                        \___ \| |     / _ \                           |
//#   |                         ___) | |___ / ___ \                          |
//#   |                        |____/|_____/_/   \_\                         |
//#   |                                                                      |
//#   +----------------------------------------------------------------------+
//#   |                                                                      |
//#   '----------------------------------------------------------------------'


function sla_details_period_hover(td, sla_period, onoff)
{
    if (has_class(td, "lock_hilite")) {
        return;
    }

    var sla_period_elements = document.getElementsByClassName(sla_period)
    for(var i = 0; i < sla_period_elements.length; i++)
    {
        if (onoff) {
            add_class(sla_period_elements[i], 'sla_hilite');
        }
        else {
            remove_class(sla_period_elements[i], 'sla_hilite');
        }
    }
}


function sla_details_period_click(td, sla_period)
{
    var sla_period_elements = document.getElementsByClassName(sla_period);
    var onoff = has_class(td, "lock_hilite")
    for(var i = 0; i < sla_period_elements.length; i++)
    {
        if (onoff) {
            remove_class(sla_period_elements[i], 'sla_hilite');
            remove_class(sla_period_elements[i], 'lock_hilite');
        }
        else {
            add_class(sla_period_elements[i], 'sla_hilite');
            add_class(sla_period_elements[i], 'lock_hilite');
        }
    }
}


function sla_details_table_hover(tr, row_id, onoff) {
    var sla_period_elements = tr.closest("table").closest("tbody").getElementsByClassName(row_id);
    for(var i = 0; i < sla_period_elements.length; i++)
    {

        if (onoff) {
            add_class(sla_period_elements[i], 'sla_hilite');
            add_class(sla_period_elements[i], 'sla_error_hilite');
        }
        else {
            remove_class(sla_period_elements[i], 'sla_error_hilite');
            if (!has_class(sla_period_elements[i], "lock_hilite")) {
                remove_class(sla_period_elements[i], 'sla_hilite');
            }
        }
    }
}


//#.
//#   .-Keybindings--------------------------------------------------------.
//#   |        _  __          _     _           _ _                        |
//#   |       | |/ /___ _   _| |__ (_)_ __   __| (_)_ __   __ _ ___        |
//#   |       | ' // _ \ | | | '_ \| | '_ \ / _` | | '_ \ / _` / __|       |
//#   |       | . \  __/ |_| | |_) | | | | | (_| | | | | | (_| \__ \       |
//#   |       |_|\_\___|\__, |_.__/|_|_| |_|\__,_|_|_| |_|\__, |___/       |
//#   |                 |___/                             |___/            |
//#   +--------------------------------------------------------------------+
//#   |                                                                    |
//#   '--------------------------------------------------------------------'

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

//#.
//#   .-Popup Menu---------------------------------------------------------.
//#   |       ____                           __  __                        |
//#   |      |  _ \ ___  _ __  _   _ _ __   |  \/  | ___ _ __  _   _       |
//#   |      | |_) / _ \| '_ \| | | | '_ \  | |\/| |/ _ \ '_ \| | | |      |
//#   |      |  __/ (_) | |_) | |_| | |_) | | |  | |  __/ | | | |_| |      |
//#   |      |_|   \___/| .__/ \__,_| .__/  |_|  |_|\___|_| |_|\__,_|      |
//#   |                 |_|         |_|                                    |
//#   +--------------------------------------------------------------------+
//#   | Floating popup menus with content fetched via AJAX calls           |
//#   '--------------------------------------------------------------------'

var popup_data      = null;
var popup_id        = null;
var popup_contents  = {};

function close_popup()
{
    del_event_handler('click', handle_popup_close);

    var menu = document.getElementById('popup_menu');
    if (menu) {
        // hide the open menu
        menu.parentNode.removeChild(menu);
    }
    popup_id = null;

    if (on_popup_close)
        eval(on_popup_close);
}

// Registerd as click handler on the page while the popup menu is opened
// This is used to close the menu when the user clicks elsewhere
function handle_popup_close(event) {
    var target = getTarget(event);

    // Check whether or not a parent of the clicked node is the popup menu
    while (target && target.id != 'popup_menu' && !has_class(target, 'popup_trigger')) { // FIXME
        target = target.parentNode;
    }

    if (target) {
        return true; // clicked menu or statusicon
    }

    close_popup();
}

// trigger_obj: DOM object of trigger object (e.g. icon)
// ident:       page global uinique identifier of the popup
// what:        type of popup (used for constructing webservice url 'ajax_popup_'+what+'.py')
//              This can be null for fixed content popup windows. In this case
//              "data" and "url_vars" are not used and can be left null.
//              The static content of the menu is given in the "menu_content" parameter.
// data:        json data which can be used by actions in popup menus
// url_vars:    vars are added to ajax_popup_*.py calls for rendering the popup menu
// resizable:   Allow the user to resize the popup by drag/drop (not persisted)
var on_popup_close = null;
function toggle_popup(event, trigger_obj, ident, what, data, url_vars, menu_content, onclose, resizable)
{
    on_popup_close = onclose;

    if (!event)
        event = window.event;
    var container = trigger_obj.parentNode;

    if (popup_id) {
        if (popup_id === ident) {
            close_popup();
            return; // same icon clicked: just close the menu
        }
        else {
            close_popup();
        }
    }
    popup_id = ident;

    add_event_handler('click', handle_popup_close);

    var menu = document.createElement('div');
    menu.setAttribute('id', 'popup_menu');
    menu.className = 'popup_menu';

    if (resizable)
        add_class(menu, 'resizable');

    container.appendChild(menu);
    fix_popup_menu_position(event, menu);

    var wrapper = document.createElement("div");
    wrapper.className = 'wrapper';
    menu.appendChild(wrapper);

    var content = document.createElement('div');
    content.className = 'content';
    wrapper.appendChild(content);

    if (resizable) {
        // Add a handle because we can not customize the styling of the default resize handle using css
        var resize = document.createElement('div');
        resize.className = "resizer";
        wrapper.appendChild(resize);
    }

    // update the menus contents using a webservice
    if (what) {
        popup_data = data;

        content.innerHTML = '<img src="images/icon_reload.png" class="icon reloading">';

        // populate the menu using a webservice, because the list of dashboards
        // is not known in the javascript code. But it might have been cached
        // before. In this case do not perform a second request.
        // LM: Don't use the cache for the moment. There might be too many situations where
        // we don't want the popup to be cached.
        //if (ident in popup_contents)
        //    menu.innerHTML = popup_contents[ident];
        //else
        url_vars = !url_vars ? '' : '?'+url_vars;
        get_url('ajax_popup_'+what+'.py'+url_vars, handle_render_popup_contents, {
            ident: ident,
            content: content,
            event: event,
        });
    } else {
        content.innerHTML = menu_content;
        executeJSbyObject(content);
    }
}

function handle_render_popup_contents(data, response_text)
{
    popup_contents[data.ident] = response_text;
    if (data.content) {
        data.content.innerHTML = response_text;
        fix_popup_menu_position(data.event, data.content);
    }
}

function fix_popup_menu_position(event, menu) {
    var rect = menu.getBoundingClientRect();

    // Check whether or not the menu is out of the bottom border
    // -> if so, move the menu up
    if (rect.bottom > (window.innerHeight || document.documentElement.clientHeight)) {
        var height = rect.bottom - rect.top;
        if (rect.top - height < 0) {
            // would hit the top border too, then put the menu to the top border
            // and hope that it fits within the screen
            menu.style.top    = '-' + (rect.top - 15) + 'px';
            menu.style.bottom = 'auto';
        } else {
            menu.style.top    = 'auto';
            menu.style.bottom = '15px';
        }
    }

    // Check whether or not the menu is out of right border and
    // a move to the left would fix the issue
    // -> if so, move the menu to the left
    if (rect.right > (window.innerWidth || document.documentElement.clientWidth)) {
        var width = rect.right - rect.left;
        if (rect.left - width < 0) {
            // would hit the left border too, then put the menu to the left border
            // and hope that it fits within the screen
            menu.style.left  = '-' + (rect.left - 15) + 'px';
            menu.style.right = 'auto';
        } else {
            menu.style.left  = 'auto';
            menu.style.right = '15px';
        }
    }
}

// TODO: Remove this function as soon as all visuals have been
// converted to pagetypes.py
function add_to_visual(visual_type, visual_name)
{
    var element_type = popup_data[0];
    var create_info = {
        'context': popup_data[1],
        'params': popup_data[2],
    }
    var create_info_json = JSON.stringify(create_info);

    close_popup();

    popup_data = null;

    var url = 'ajax_add_visual.py'
        + '?visual_type=' + visual_type
        + '&visual_name=' + visual_name
        + '&type=' + element_type;

    call_ajax(url, {
        method : "POST",
        post_data: "create_info=" + encodeURIComponent(create_info_json),
        plain_error : true,
        response_handler: function(handler_data, response_body) {
            // After adding a dashlet, go to the choosen dashboard
            if (response_body.substr(0, 2) == "OK") {
                window.location.href = response_body.substr(3);
            } else {
                alert("Failed to add element: "+response_body);
            }
        }
    });
}

// FIXME: Adapt error handling which has been addded to add_to_visual() in the meantime
function pagetype_add_to_container(page_type, page_name)
{
    var element_type = popup_data[0]; // e.g. 'pnpgraph'
    // complex JSON struct describing the thing
    var create_info  = {
        "context"    : popup_data[1],
        "parameters" : popup_data[2]
    };
    var create_info_json = JSON.stringify(create_info);

    close_popup();

    popup_data = null;

    var url = 'ajax_pagetype_add_element.py'
              + '?page_type=' + page_type
              + '&page_name=' + page_name
              + '&element_type=' + element_type;

    call_ajax(url, {
        method           : "POST",
        post_data        : "create_info=" + encodeURIComponent(create_info_json),
        response_handler : function(handler_data, response_body) {
            // We get to lines of response. The first is an URL we should be
            // redirected to. The second is "true" if we should reload the
            // sidebar.
            if (response_body) {
                var parts = response_body.split('\n');
                if (parts[1] == "true")
                    reload_sidebar();
                if (parts[0])
                    window.location.href = parts[0];
            }
        }
    });
}

function graph_export(page)
{
    var request = {
        "specification": popup_data[2]["definition"]["specification"],
        "data_range": popup_data[2]["data_range"],
    };
    location.href = page + ".py?request=" + encodeURIComponent(JSON.stringify(request));
}

//#.
//#   .-HoverMenu----------------------------------------------------------.
//#   |          _   _                     __  __                          |
//#   |         | | | | _____   _____ _ __|  \/  | ___ _ __  _   _         |
//#   |         | |_| |/ _ \ \ / / _ \ '__| |\/| |/ _ \ '_ \| | | |        |
//#   |         |  _  | (_) \ V /  __/ |  | |  | |  __/ | | | |_| |        |
//#   |         |_| |_|\___/ \_/ \___|_|  |_|  |_|\___|_| |_|\__,_|        |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   | Mouseover hover menu, used for performance graph popups            |
//#   '--------------------------------------------------------------------'

var g_hover_menu = null;

function hide_hover_menu()
{
    if (g_hover_menu) {
        g_hover_menu.style.display = 'none';
        document.body.style.cursor = 'auto';
    }
}

function show_hover_menu(event, code)
{
    event = event || window.event;
    var x = event.clientX;
    var y = event.clientY;

    hide_hover_menu();

    var hoverSpacer = 5;

    // document.body.scrollTop does not work in IE
    var scrollTop = document.body.scrollTop ? document.body.scrollTop :
                                              document.documentElement.scrollTop;
    var scrollLeft = document.body.scrollLeft ? document.body.scrollLeft :
                                                document.documentElement.scrollLeft;

    if (g_hover_menu === null) {
        g_hover_menu = document.createElement('div');
        g_hover_menu.setAttribute('id', 'hover_menu');
        document.body.appendChild(g_hover_menu);
    }
    g_hover_menu.innerHTML = code;
    executeJSbyObject(g_hover_menu);

    // Change cursor to "hand" when displaying hover menu
    document.body.style.cursor = 'pointer';

    // hide the menu first to avoid an "up-then-over" visual effect
    g_hover_menu.style.display = 'none';
    g_hover_menu.style.left = (x + hoverSpacer + scrollLeft) + 'px';
    g_hover_menu.style.top = (y + hoverSpacer + scrollTop) + 'px';
    g_hover_menu.style.display = '';

    /**
     * Check if the menu is "in screen" or too large.
     * If there is some need for reposition try to reposition the hover menu
     */

    var hoverPosAndSizeOk = true;
    if (!hover_menu_in_screen(g_hover_menu, hoverSpacer))
        hoverPosAndSizeOk = false;

    if (!hoverPosAndSizeOk) {
        g_hover_menu.style.left = (x - hoverSpacer - g_hover_menu.clientWidth) + 'px';

        if (hover_menu_in_screen(g_hover_menu, hoverSpacer))
            hoverPosAndSizeOk = true;
    }

    // And if the hover menu is still not on the screen move it to the left edge
    // and fill the whole screen width
    if (!hover_menu_in_screen(g_hover_menu, hoverSpacer)) {
        g_hover_menu.style.left = hoverSpacer + scrollLeft + 'px';
        g_hover_menu.style.width = pageWidth() - (2*hoverSpacer) + 'px';
    }

    var hoverTop = parseInt(g_hover_menu.style.top.replace('px', ''));
    // Only move the menu to the top when the new top will not be
    // out of sight
    if (hoverTop +g_hover_menu.clientHeight > pageHeight() && hoverTop -g_hover_menu.clientHeight >= 0)
        g_hover_menu.style.top = hoverTop -g_hover_menu.clientHeight - hoverSpacer + 'px';
}

function hover_menu_in_screen(hoverMenu, hoverSpacer)
{
    var hoverLeft = parseInt(hoverMenu.style.left.replace('px', ''));
    var scrollLeft = document.body.scrollLeft ? document.body.scrollLeft :
                                                document.documentElement.scrollLeft;

    if(hoverLeft + hoverMenu.clientWidth >= pageWidth() - scrollLeft)
        return false;

    if(hoverLeft - hoverSpacer < 0)
        return false;
    return true;
}

//#.
//#   .-BI-----------------------------------------------------------------.
//#   |                              ____ ___                              |
//#   |                             | __ )_ _|                             |
//#   |                             |  _ \| |                              |
//#   |                             | |_) | |                              |
//#   |                             |____/___|                             |
//#   |                                                                    |
//#   +--------------------------------------------------------------------+
//#   | BI GUI specific                                                    |
//#   '--------------------------------------------------------------------'

function bi_toggle_subtree(oImg, lazy)
{
    if (oImg.tagName == "SPAN") { // clicked on title,
        oImg = oImg.previousElementSibling;
    }
    var oSubtree = oImg.parentNode.getElementsByTagName("ul")[0];
    var url = "bi_save_treestate.py?path=" + encodeURIComponent(oSubtree.id);
    var do_open;

    if (has_class(oImg, "closed")) {
        change_class(oSubtree, "closed", "open");
        toggle_folding(oImg, true);

        url += "&state=open";
        do_open = true;
    }
    else {
        change_class(oSubtree, "open", "closed");
        toggle_folding(oImg, false);

        url += "&state=closed";
        do_open = false;
    }

    if (lazy && do_open)
        get_url(url, bi_update_tree, oImg);
    else
        get_url(url);
}

function bi_update_tree(container, code)
{
    // Deactivate clicking - the update can last a couple
    // of seconds. In that time we must inhibit further clicking.
    container.onclick = null;

    // First find enclosding <div class=bi_tree_container>
    var bi_container = container;
    while (bi_container && !has_class(bi_container, "bi_tree_container")) {
        bi_container = bi_container.parentNode;
    }

    post_url("bi_render_tree.py", bi_container.id, bi_update_tree_response, bi_container);
}

function bi_update_tree_response(bi_container, code) {
    bi_container.innerHTML = code;
    executeJSbyObject(bi_container);
}

function bi_toggle_box(container, lazy)
{
    var url = "bi_save_treestate.py?path=" + encodeURIComponent(container.id);
    var do_open;

    if (has_class(container, "open")) {
        if (lazy)
            return; // do not close in lazy mode
        change_class(container, "open", "closed");
        url += "&state=closed";
        do_open = false;
    }
    else {
        change_class(container, "closed", "open");
        url += "&state=open";
        do_open = true;
    }

    // TODO: Make asynchronous
    if (lazy && do_open)
        get_url(url, bi_update_tree, container);
    else {
        get_url(url);
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

function toggle_assumption(link, site, host, service)
{
    var img = link.getElementsByTagName("img")[0];

    // get current state
    var current = img.src;
    while (current.indexOf('/') > -1)
        current = current.substr(current.indexOf('/') + 1);
    current = current.replace(/button_assume_/, "").replace(/.png/, "");

    if (current == 'none')
        // Assume WARN when nothing assumed yet
        current = '1';
    else if (current == '3' || (service == '' && current == '2'))
        // Assume OK when unknown assumed (or when critical assumed for host)
        current = '0';
    else if (current == '0')
        // Disable assumption when ok assumed
        current = 'none';
    else
        // In all other cases increas the assumption
        current = parseInt(current) + 1;

    var url = "bi_set_assumption.py?site=" + encodeURIComponent(site)
            + '&host=' + encodeURIComponent(host);
    if (service) {
        url += '&service=' + encodeURIComponent(service);
    }
    url += '&state=' + current;
    img.src = "images/button_assume_" + current + ".png";
    get_url(url);
}

//#.
//#   .-Crash-Report-------------------------------------------------------.
//#   |    ____               _           ____                       _     |
//#   |   / ___|_ __ __ _ ___| |__       |  _ \ ___ _ __   ___  _ __| |_   |
//#   |  | |   | '__/ _` / __| '_ \ _____| |_) / _ \ '_ \ / _ \| '__| __|  |
//#   |  | |___| | | (_| \__ \ | | |_____|  _ <  __/ |_) | (_) | |  | |_   |
//#   |   \____|_|  \__,_|___/_| |_|     |_| \_\___| .__/ \___/|_|   \__|  |
//#   |                                            |_|                     |
//#   +--------------------------------------------------------------------+
//#   | Posting crash report to official Check_MK crash reporting API      |
//#   '--------------------------------------------------------------------'

function submit_crash_report(url, post_data)
{
    document.getElementById("pending_msg").style.display = "block";

    if (has_cross_domain_ajax_support()) {
        call_ajax(url, {
            method           : "POST",
            post_data        : post_data,
            response_handler : handle_crash_report_response,
            error_handler    : handle_crash_report_error,
            handler_data     : {
                base_url: url
            }
        });
    }
    else if (typeof XDomainRequest !== "undefined") {
        // IE < 9 does not support cross domain ajax requests in the standard way.
        // workaround this issue by doing some iframe / form magic
        submit_crash_report_with_ie(url, post_data);
    }
    else {
        handle_crash_report_error(null, null, "Your browser does not support direct crash reporting.");
    }
}


function submit_crash_report_with_ie(url, post_data) {
    var handler_data = {
        base_url: url
    };
    var xdr = new XDomainRequest();
    xdr.onload = function() {
        handle_crash_report_response(handler_data, xdr.responseText);
    };
    xdr.onerror = function() {
        handle_crash_report_error(handler_data, null, xdr.responseText);
    };
    xdr.onprogress = function() {};
    xdr.open("post", url);
    xdr.send(post_data);
}


function handle_crash_report_response(handler_data, response_body)
{
    hide_crash_report_processing_msg();

    if (response_body.substr(0, 2) == "OK") {
        var id = response_body.split(" ")[1];
        var success_container = document.getElementById("success_msg");
        success_container.style.display = "block";
        success_container.innerHTML = success_container.innerHTML.replace(/###ID###/, id);
    }
    else {
        var fail_container = document.getElementById("fail_msg");
        fail_container.style.display = "block";
        fail_container.children[0].innerHTML += " ("+response_body+").";
    }
}

function handle_crash_report_error(handler_data, status_code, error_msg)
{
    hide_crash_report_processing_msg();

    var fail_container = document.getElementById("fail_msg");
    fail_container.style.display = "block";
    if (status_code) {
        fail_container.children[0].innerHTML += " (HTTP: "+status_code+").";
    }
    else if (error_msg) {
        fail_container.children[0].innerHTML += " ("+error_msg+").";
    }
    else {
        fail_container.children[0].innerHTML += " (Maybe <tt>"+handler_data["base_url"]+"</tt> not reachable).";
    }
}

function hide_crash_report_processing_msg()
{
    var msg = document.getElementById("pending_msg");
    msg.parentNode.removeChild(msg);
}

function download_gui_crash_report(data_url)
{
    var link = document.createElement("a");
    link.download = "Check_MK_GUI_Crash-" + (new Date().toISOString()) + ".tar.gz";
    link.href = data_url;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    delete link;
}

//#.
//#   .-Backup-------------------------------------------------------------.
//#   |                  ____             _                                |
//#   |                 | __ )  __ _  ___| | ___   _ _ __                  |
//#   |                 |  _ \ / _` |/ __| |/ / | | | '_ \                 |
//#   |                 | |_) | (_| | (__|   <| |_| | |_) |                |
//#   |                 |____/ \__,_|\___|_|\_\\__,_| .__/                 |
//#   |                                             |_|                    |
//#   +--------------------------------------------------------------------+
//#   |                                                                    |
//#   '--------------------------------------------------------------------'

function refresh_job_details(url, ident, is_site)
{
    setTimeout(function() {
        do_job_detail_refresh(url, ident, is_site);
    }, 1000);
}

function do_job_detail_refresh(url, ident, is_site)
{
    call_ajax(url, {
        method           : "GET",
        post_data        : "job=" + encodeURIComponent(ident),
        response_handler : handle_job_detail_response,
        error_handler    : handle_job_detail_error,
        handler_data     : {
            "url"     : url,
            "ident"   : ident,
            "is_site" : is_site,
        }
    });
}

function handle_job_detail_response(handler_data, response_body)
{
    // when a message was shown and now not anymore, assume the job has finished
    var had_message = document.getElementById("job_detail_msg") ? true : false;

    var container = document.getElementById("job_details");
    container.innerHTML = response_body;

    if (!had_message) {
        refresh_job_details(handler_data["url"], handler_data["ident"], handler_data["is_site"]);
    }
    else {
        reload_sidebar();
        window.location.reload();
    }
}

function handle_job_detail_error(handler_data, status_code, error_msg)
{
    hide_job_detail_msg();

    if (status_code == 0)
        return; // ajax request aborted. Stop refresh.

    var container = document.getElementById("job_details");

    var msg = document.createElement("div");
    container.insertBefore(msg, container.children[0]);
    msg.setAttribute("id", "job_detail_msg");
    msg.className = "message";

    var txt = "Could not update the job details.";
    if (handler_data.is_site)
        txt += " The site will be started again after the restore.";
    else
        txt += " Maybe the device is currently being rebooted.";

    txt += "<br>Will continue trying to refresh the job details.";

    txt += "<br><br>HTTP status code: "+status_code;
    if (error_msg)
        txt += ", Error: "+error_msg;

    msg.innerHTML = txt;

    refresh_job_details(handler_data["url"], handler_data["ident"], handler_data["is_site"]);
}

function hide_job_detail_msg()
{
    var msg = document.getElementById("job_detail_msg");
    if (msg)
        msg.parentNode.removeChild(msg);
}

//#.
//#   .--Visibility----------------------------------------------------------.
//#   |               __     ___     _ _     _ _ _ _                         |
//#   |               \ \   / (_)___(_) |__ (_) (_) |_ _   _                 |
//#   |                \ \ / /| / __| | '_ \| | | | __| | | |                |
//#   |                 \ V / | \__ \ | |_) | | | | |_| |_| |                |
//#   |                  \_/  |_|___/_|_.__/|_|_|_|\__|\__, |                |
//#   |                                                |___/                 |
//#   +----------------------------------------------------------------------+
//#   | Code for detecting the visibility of the current browser window/tab  |
//#   '----------------------------------------------------------------------'

var g_visibility_detection_enabled = true;

// Whether or not the current browser window/tab is visible to the user
function is_window_active()
{
    return !has_class(document.body, "hidden");
}

function initialize_visibility_detection() 
{
    var hidden_attr_name = "hidden";

    // Standards:
    if (hidden_attr_name in document)
        document.addEventListener("visibilitychange", on_visibility_change);
    else if ((hidden_attr_name = "mozHidden") in document)
        document.addEventListener("mozvisibilitychange", on_visibility_change);
    else if ((hidden_attr_name = "webkitHidden") in document)
        document.addEventListener("webkitvisibilitychange", on_visibility_change);
    else if ((hidden_attr_name = "msHidden") in document)
        document.addEventListener("msvisibilitychange", on_visibility_change);

    // This feature will not support IE 9 and lower or other incompatible
    // browsers. By enabling the code below we could add the support, but
    // we need to be sure that these assignments don't conflict with other
    // already registered event handlers.
    //else if ("onfocusin" in document) {
    //    // IE 9 and lower:
    //    document.onfocusin = document.onfocusout = onchange;
    //}
    //else {
    //    // All others:
    //    window.onpageshow = window.onpagehide
    //        = window.onfocus = window.onblur = onchange;
    //}

    window.addEventListener("beforeunload", disable_visibility_detection);

    function disable_visibility_detection(evt) {
        g_visibility_detection_enabled = false;
    }

    function on_visibility_change(evt) {
        var v = "visible", h = "hidden",
            evtMap = {
              focus:v, focusin:v, pageshow:v, blur:h, focusout:h, pagehide:h
            };

        if (!g_visibility_detection_enabled)
            return;

        remove_class(document.body, "visible");
        remove_class(document.body, "hidden");

        evt = evt || window.event;

        var new_class;
        if (evt.type in evtMap) {
            new_class = evtMap[evt.type];
        } else {
            new_class = this[hidden_attr_name] ? "hidden" : "visible";
        }
        
        //console.log([evt.type, new_class, document.hidden, location.href]);
        add_class(document.body, new_class);
    }

    // set the initial state (but only if browser supports the Page Visibility API)
    if (document[hidden_attr_name] !== undefined)
        on_visibility_change({type: document[hidden_attr_name] ? "blur" : "focus"});
}
