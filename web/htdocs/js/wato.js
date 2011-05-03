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
var progress_items     = null;
// Number of total items to handle
var progress_total_num = 0;
// The URL to redirect to after finish/abort button pressed
var progress_end_url   = '';
// Is set to true while one request is waiting for a response
var progress_running = false;
// Is set to true to put the processing to sleep
var progress_paused  = false;
// Is set to true when the user hit aborted/finished
var progress_ended   = false;

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
    body = body.join('');

    // Process statistics
    update_progress_stats(header);

    // Process the bar
    update_progress_bar(header);

    // Process optional body
    if(typeof(body) !== 'undefined' && body != '')
        progress_attach_log(body);

    if(header[0] === 'pause') {
        progress_pause();
    } else if(header[0] === 'abort') {
        return;
    }

    progress_items.shift();
    progress_running = false;
}

/* Is called when the user or the response wants the processing to be paused */
function progress_pause() {
    progress_paused = true;
    progress_attach_log('+++ PAUSE<br />');
    document.getElementById('progress_pause').style.display = 'none';
    document.getElementById('progress_proceed').style.display = '';
}

/* Is called when the user or the response wants the processing to be proceeded after pause */
function progress_proceed() {
    progress_paused = false;
    progress_attach_log('+++ PROCEEDING<br />');
    document.getElementById('progress_pause').style.display = '';
    document.getElementById('progress_proceed').style.display = 'none';
}

/* Is called when the processing is completely finished */
function progress_finished() {
    update_progress_title('');
    document.getElementById('progress_bar').className = 'finished';

    document.getElementById('progress_finished').style.display = '';
    document.getElementById('progress_pause').style.display    = 'none';
    document.getElementById('progress_proceed').style.display  = 'none';
    document.getElementById('progress_abort').style.display    = 'none';
}

/* Is called by the users abort/finish button click */
function progress_end() {
    // Mark as ended to catch currently running requests
    progress_ended = true;
    location.href = progress_end_url;
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
    var num_done  = progress_total_num - progress_items.length + 1;
    var perc_done = num_done / progress_total_num * 100;

    var bar      = document.getElementById('progress_bar');
    var leftCell = bar.firstChild.firstChild.firstChild;
    leftCell.style.width = (bar.clientWidth * perc_done / 100) + 'px';
    leftCell = null;
    bar      = null;

    return false;
}

function update_progress_title(t) {
    document.getElementById('progress_title').innerHTML = t;
}

function progress_attach_log(t) {
    var log = document.getElementById('progress_log');
    log.innerHTML += t;
    log.scrollTop = log.scrollHeight;
    log = null;
}

function progress_scheduler(mode, url_prefix, end_url, timeout, items) {
    // Initialize
    if(progress_items === null) {
        progress_items     = items;
        progress_total_num = items.length;
        progress_end_url   = end_url;
    }

    // Escape the loop when ended
    if(progress_ended)
        return false;

    // Regular processing when not paused and not already running
    if(!progress_paused && !progress_running) {
        if(progress_items.length > 0) {
            // Progressing
            progress_running = true;
            update_progress_title(progress_items[0]);
            get_url(url_prefix + '&_transid=-1&_item=' + escape(progress_items[0]), progress_handle_response, [ mode, progress_items[0] ]);
        } else {
            progress_finished();
            return;
        }
    }

    setTimeout(function() { progress_scheduler(mode, url_prefix, "", timeout, []); }, timeout);
}
