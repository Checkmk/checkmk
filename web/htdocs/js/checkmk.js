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

// Tells the caller whether or not there are graphs on the current page
function has_graphing()
{
    return typeof g_graphs !== 'undefined';
}

// mouse offset to the top/left coordinates of an object
function mouse_offset(obj, event){
    var obj_pos   = obj.getBoundingClientRect();
    var mouse_pos = cmk.utils.mouse_position(event);
    return {
        "x": mouse_pos.left - obj_pos.x,
        "y": mouse_pos.top - obj_pos.y
    };
}

function update_bulk_moveto(val) {
    var fields = document.getElementsByClassName("bulk_moveto");
    for(var i = 0; i < fields.length; i++)
        for(var a = 0; a < fields[i].options.length; a++)
            if(fields[i].options[a].value == val)
                fields[i].options[a].selected = true;
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

function get_event_offset_x(event) {
    return event.offsetX == undefined ? event.layerX : event.offsetX;
}

function get_event_offset_y(event) {
    return event.offsetY == undefined ? event.layerY : event.offsetY;
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
        var source = parseInt(cmk.utils.get_url_param('source', params)) + 1;

        // Add the control for adding the graph to a visual
        var visualadd = document.createElement('a');
        visualadd.title = data['add_txt'];
        visualadd.className = 'popup_trigger';
        visualadd.innerHTML = '<img src="images/icon_menu.png" class="icon">';
        visualadd.onclick = function(host, service, view, source) {
            return function(event) {
                cmk.popup_menu.toggle_popup(event, this, 'add_visual', 'add_visual',
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

    cmk.hover.show(event, "<div class=\"message\">Loading...</div>");

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

    cmk.hover.update_content(code);
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

    cmk.hover.update_content(code);
}


function handle_hover_graphs_error(_unused, status_code, error_msg)
{
    var code = '<div class=error>Update failed (' + status_code + ')</div>';
    cmk.hover.update_content(code);
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

// Stores the reload pause timer object once the regular reload has
// been paused e.g. by modifying a graphs timerange or vertical axis.
var g_reload_pause_timer = null;

// When called with one or more parameters parameters it reschedules the
// timer to the given interval. If the parameter is 0 the reload is stopped.
// When called with two parmeters the 2nd one is used as new url.
function set_reload(secs, url)
{
    cmk.utils.stop_reload_timer();
    cmk.utils.set_reload_interval(secs);
    if (secs !== 0) {
        cmk.utils.schedule_reload(url);
    }
}


// Sets the reload timer in pause mode for X seconds. This is shown to
// the user with a pause overlay icon. The icon also shows the time when
// the pause ends. Once the user clicks on the pause icon or the time
// is reached, the whole page is reloaded.
function pause_reload(seconds)
{
    cmk.utils.stop_reload_timer();
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

    cmk.utils.toggle_folding(cell.getElementsByTagName("IMG")[0], toggle_img_open);
    cmk.foldable_container.persist_tree_state(tree, id, state);

    var row = group_title_row;
    for (var i = 0; i < num_rows; i++) {
        row = row.nextElementSibling;
        row.style.display = display;
    }
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
    cmk.selection.toggle_all_rows(group_rows);
}

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

function unhide_context_buttons(oA)
{
    var oNode;
    var oTd = oA.parentNode.parentNode;
    for (var i in oTd.children) {
        oNode = oTd.children[i];
        if (oNode.tagName == "DIV" && !has_class(oNode, "togglebutton"))
            oNode.style.display = "";
    }
    oA.parentNode.style.display = "none";
}
