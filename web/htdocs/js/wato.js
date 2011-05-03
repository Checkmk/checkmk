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
// General functions for WATO
// ----------------------------------------------------------------------------

function getElementsByClass(cl) {
    var items = new Array();
    var elements = document.getElementsByTagName('*');
    for(var i = 0; i < elements.length; i++)
        if(elements[i].className == cl)
            items.push(elements[i]);
    return items;
}

/* Used to check all checkboxes which have the given class set */
function wato_check_all(css_class) {
    var items = getElementsByClass(css_class);

    // First check if all boxes are checked
    var all_checked = true;
    for(var i = 0; i < items.length && all_checked == true; i++)
        if(items[i].checked == false)
            all_checked = false;

    // Now set the new state
    for(var i = 0; i < items.length; i++)
        items[i].checked = !all_checked;
}

// ----------------------------------------------------------------------------
// Interactive progress code
// ----------------------------------------------------------------------------


// Keeps the items to be fetched
var progress_items = null;
var progress_perc_step = 0;
// Is set to true while one request is waiting for a response
var progress_running = false;

function progress_handle_response(data, code) {
    var mode = data[0];
    var item = data[1];

    var header = null;
    try {
        var header = eval(code.split("\n", 1)[0]);
    } catch(err) {
        alert('Invalid response: ' + code);    
    }

    if(header === null) {
        alert('Header is null!');
    }

    // Extract the body from the response
    var body = code.split('\n');
    body.splice(0,1);
    body = body.join('<br />');

    // Process statistics
    update_progress_stats(header);

    // Process the bar
    update_progress_bar(header);

    // Process optional body
    if(typeof(body) !== 'undefined' && body != '')
        progress_attach_log(body);

    if(header[0] !== 'continue') {
        alert('ABORT!');
    }

    progress_items.shift();
    progress_running = false;
}

function update_progress_stats(header) {
    for(var i = 1; i < header.length; i++) {
        var o = document.getElementById('progress_stat' + (i - 1));
        if(o) {
            o.innerHTML = parseInt(o.innerHTML) + parseInt(header[i]);
            o = null;
        }
    }
}

function update_progress_bar(header) {
    return false;
}

function progress_attach_log(t) {
    var log = document.getElementById('progress_log');
    log.innerHTML += t + '<br />';
    log = null;
}

function progress_finished() {
    document.getElementById('progress_finished').style.display = '';
}

function progress_scheduler(mode, url_prefix, timeout, items) {
    if(progress_items === null) {
        progress_items     = items;
        progress_perc_step = items.length / 100;
    }

    if(progress_running === false) {
        if(progress_items.length > 0) {
            // Progressing
            progress_running = true;
            get_url(url_prefix + '&_transid=-1&_item=' + escape(progress_items[0]), progress_handle_response, [ mode, progress_items[0] ]);
        } else {
            progress_finished();
            return;
        }
    }

    setTimeout(function() { progress_scheduler(mode, url_prefix, timeout, []); }, timeout);
}
