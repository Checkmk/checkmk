// +------------------------------------------------------------------+
// |             ____ _               _        __  __ _  __           |
// |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
// |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
// |           | |___| | | |  __/ (__|   <    | |  | | . \            |
// |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
// |                                                                  |
// | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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
        if (elements[i].className == cl)
            items.push(elements[i]);
    return items;
}

/* Used to check all checkboxes which have the given class set */
function wato_check_all(css_class) {
    var items = getElementsByClass(css_class);

    // First check if all boxes are checked
    var all_checked = true;
    for(var i = 0; i < items.length && all_checked == true; i++)
        if (items[i].checked == false)
            all_checked = false;

    // Now set the new state
    for(var i = 0; i < items.length; i++)
        items[i].checked = !all_checked;
}

/* Make attributes visible or not when clicked on a checkbox */
function wato_toggle_attribute(oCheckbox, attrname) {
    var oEntry =   document.getElementById("attr_entry_" + attrname);
    var oDefault = document.getElementById("attr_default_" + attrname);

    // Permanent invisible attributes do
    // not have attr_entry / attr_default
    if( !oEntry ){
       return;
    }
    if (oCheckbox.checked) {
        oEntry.style.display = "";
        oDefault.style.display = "none";
    }
    else {
        oEntry.style.display = "none";
        oDefault.style.display = "";
    }
    oEntry = null;
    oDefault = null;
}

/* Switch the visibility of all host attributes during the configuration
   of attributes of a host */
function wato_fix_visibility() {
    /* First collect the current selection of all host attributes.
       They are in the same table as we are */
    var currentTags = [];

    var oHostTags = document.getElementById("wato_host_tags");
    // Skip this function when no tags defined
    if (!oHostTags)
        return;

    var oTable = oHostTags.childNodes[0]; /* tbody */
    oHostTags = null;
    for (var i in oTable.childNodes) {
        var oTr = oTable.childNodes[i];
        if (oTr.tagName == 'TR') {
            var oTdLegend = oTr.childNodes[0];
            if (oTdLegend.className != "legend") {
                continue;
            }
            var oTdContent = oTr.childNodes[1];
            /* If the Checkbox is unchecked try to get a value from the inherited_tags */
            var oCheckbox = oTdLegend.childNodes[1].childNodes[0];
            if (oCheckbox.checked == false ){
                var attrname = oCheckbox.parentNode.parentNode.id;
                if(attrname in inherited_tags && inherited_tags[attrname] !== null){
                    currentTags = currentTags.concat(inherited_tags[attrname].split("|"));
                }
            } else {
                /* Find the <select>/<checkbox> object in this tr */
                /*                td.content    div           select/checkbox */
                var oElement = oTdContent.childNodes[0].childNodes[0];
                if( oElement.type == 'checkbox' && oElement.checked ){ // <checkbox>
                    currentTags = currentTags.concat(oElement.getAttribute('tags').split("|"));
                } else if(oElement.tagName == 'SELECT') { // <select>
                    currentTags = currentTags.concat(oElement.value.split("|"));
                }
            }
        }
    }

    var hide_topics = volatile_topics.slice(0);
    /* Now loop over all attributes that have conditions. Those are
       stored in the global variable wato_depends_on_tags, which is filled
       during the creation of the web page. */

    for (var i in wato_check_attributes) {
        var attrname = wato_check_attributes[i];
        /* Now comes the tricky part: decide whether that attribute should
           be visible or not: */
        var display = "";

        // Always invisible
        if( hide_attributes.indexOf(attrname) > -1 ){
            display = "none";
        }

        // Visibility depends on roles
        if( display == "" && attrname in wato_depends_on_roles){
            for (var i in wato_depends_on_roles[attrname]) {
                var role = wato_depends_on_roles[attrname][i];
                var negate = role[0] == '!';
                var rolename = negate ? role.substr(1) : role;
                var have_role = user_roles.indexOf(rolename) != -1;
                if (have_role == negate) {
                    display = "none";
                    break;
                }
            }
        }

        // Visibility depends on tags
        if( display == "" && attrname in wato_depends_on_tags){
            for (var i in wato_depends_on_tags[attrname]) {
                var tag = wato_depends_on_tags[attrname][i];
                var negate = tag[0] == '!';
                var tagname = negate ? tag.substr(1) : tag;
                var have_tag = currentTags.indexOf(tagname) != -1;
                if (have_tag == negate) {
                    display = "none";
                    break;
                }
            }
        }


        var oTr = document.getElementById("attr_" + attrname);
        if(oTr) {
            oTr.style.display = display;

            // Prepare current visibility information which is used
            // within the attribut validation in wato
            // Hidden attributes are not validated at all
            var oAttrDisp = document.getElementById("attr_display_" + attrname);
            if (!oAttrDisp) {
                var oAttrDisp = document.createElement("input");
                oAttrDisp.name  = "attr_display_" + attrname;
                oAttrDisp.id  = "attr_display_" + attrname;
                oAttrDisp.type = "hidden";
                oAttrDisp.className = "text";
                oTr.appendChild(oAttrDisp);
            }
            if ( display == "none" ) {
                // Uncheck checkboxes of hidden fields
                var chkbox = oAttrDisp.parentNode.childNodes[0].childNodes[1].childNodes[0];
                chkbox.checked = false;
                wato_toggle_attribute(chkbox, attrname);

                oAttrDisp.value = "0";
            } else {
                oAttrDisp.value = "1";
            }
            oAttrDisp = null;

            // There is at least one item in this topic -> show it
            var topic = oTr.parentNode.childNodes[0].textContent;
            if( display == "" ){
                var index = hide_topics.indexOf(topic);
                if( index != -1 )
                    delete hide_topics[index];
            }
        }
    }

    // FIXME: use generic identifier for each form
    var available_forms = [ "form_edithost", "form_editfolder", "form_bulkedit" ];
    for ( var try_form in available_forms ){
            var my_form = document.getElementById(available_forms[try_form]);
            if (my_form != null) {
            for (var child in my_form.childNodes){
                oTr = my_form.childNodes[child];
                if (oTr.className == "nform"){
                    if( hide_topics.indexOf(oTr.childNodes[0].childNodes[0].textContent) > -1 )
                        oTr.style.display = "none";
                    else
                        oTr.style.display = "";
                }
            }
            break;
        }
    }
}

// ----------------------------------------------------------------------------
// Interactive progress code
// ----------------------------------------------------------------------------


// WATO mode during progress
var progress_mode      = null;
// WATO url belonging to progress
var progress_url       = null;
// timeout for progress
var progress_timeout   = null;
// Keeps the items to be fetched
var progress_items     = null;
// items failed, needed for retry
var failed_items       = null;
// Number of total items to handle
var progress_total_num = 0;
// Contains the total number of items which have been successfully processed
// This is e.g. used to decide if the dialog needs to redirect to end_url
// or to the term_url
var progress_found = 0;
// The fields which signal that something has been successfully processed.
// this is used together with progress_found to find out the correct redirect url
var progress_success_stats = [];
// The fields which signal that something has failed
var progress_fail_stats = [];
// The URL to redirect to after finish/abort button pressed
var progress_end_url   = '';
// The URL to redirect to after finish/abort button pressed when nothing found
var progress_term_url   = '';
// The text to show in the progress bar after finished processing
var progress_fin_txt   = '';
// Is set to true while one request is waiting for a response
var progress_running = false;
// Is set to true to put the processing to sleep
var progress_paused  = false;
// Is set to true when the user hit aborted/finished
var progress_ended   = false;

function progress_handle_error(data, code) {
    // code contains no parsable response but the http code
    progress_handle_response(data, '', code);
}

function progress_handle_response(data, code, http_code) {
    var mode = data[0];
    var item = data[1];

    var header = null;
    var body = null;
    if(http_code !== undefined) {
        // If the request failed report the item as failed
        // - Report failed state
        // - Update the total count (item 0 = 1)
        // - Update the failed stats
        header = [ 'failed', 1 ];
        for(var i = 1; i <= Math.max.apply(Math, progress_fail_stats); i++) {
            if(progress_fail_stats.indexOf(i) !== -1) {
                header.push(1);
            } else {
                header.push(0);
            }
        }
        body = 'Inventory of ' + item + ' failed\n'
              +'<div class=exc><h1>HTTP-Request failed</h1>'
              +'HTTP-Code: ' + http_code + '<br />'
              +'Parameters: ' + data + '</div>\n';
    } else {
        // Regular response processing
        try {
            var header = eval(code.split("\n", 1)[0]);
            if (header === null)
                alert('Header is null!');
        } catch(err) {
            alert('Invalid response: ' + code);
        }

        // Extract the body from the response
        var body = code.split('\n');
        body.splice(0,1);
        body = body.join('');
    }

    // Process statistics
    update_progress_stats(header);

    // Process the bar
    update_progress_bar(header);

    // Process optional body
    if (typeof(body) !== 'undefined' && body != '')
        progress_attach_log(body);

    if (header[0] === 'pause')
        progress_pause();
    else if (header[0] == 'failed')
        failed_items.push(item);
    else if (header[0] === 'abort')
        return;

    progress_items.shift();
    progress_running = false;
}

/* Is called when the user or the response wants the processing to be paused */
function progress_pause() {
    progress_paused = true;
    //progress_attach_log('+++ PAUSE<br />');
    document.getElementById('progress_pause').style.display = 'none';
    document.getElementById('progress_proceed').style.display = '';
}

/* Is called when the user or the response wants the processing to be proceeded after pause */
function progress_proceed() {
    progress_paused = false;
    //progress_attach_log('+++ PROCEEDING<br />');
    document.getElementById('progress_pause').style.display = '';
    document.getElementById('progress_proceed').style.display = 'none';
}

function progress_retry() {
    document.getElementById('progress_retry').style.display    = 'none';
    document.getElementById('progress_pause').style.display    = '';
    document.getElementById('progress_abort').style.display    = '';
    progress_clean_log();
    clear_progress_stats();
    progress_items = failed_items;
    failed_items = Array();
    progress_scheduler(progress_mode, progress_url, progress_timeout, [], "", "");
}



/* Is called when the processing is completely finished */
function progress_finished() {
    update_progress_title(progress_fin_txt);
    document.getElementById('progress_bar').className = 'finished';

    document.getElementById('progress_finished').style.display = '';
    document.getElementById('progress_pause').style.display    = 'none';
    document.getElementById('progress_proceed').style.display  = 'none';
    document.getElementById('progress_abort').style.display    = 'none';
    if (failed_items.length > 0)
        document.getElementById('progress_retry').style.display = '';

}

/* Is called by the users abort/finish button click */
function progress_end() {
    // Mark as ended to catch currently running requests
    progress_ended = true;
    if(progress_found > 0)
        location.href = progress_end_url;
    else
        location.href = progress_term_url;
}

function clear_progress_stats() {
    progress_found = 0
    for(var i = 1; i < 100; i++) {
        var o = document.getElementById('progress_stat' + (i - 1));
        if (o) {
            o.innerHTML = "0";
            o = null;
        }
        else
            break;
    }
}

function update_progress_stats(header) {
    for(var i = 1; i < header.length; i++) {
        var o = document.getElementById('progress_stat' + (i - 1));
        if (o) {
            for(var a = 0; a < progress_success_stats.length; a++)
                if(progress_success_stats[a] == i)
                    progress_found += parseInt(header[i]);

            o.innerHTML = parseInt(o.innerHTML) + parseInt(header[i]);
            o = null;
        }
    }
}

function update_progress_bar(header) {
    var num_done  = progress_total_num - progress_items.length + 1;
    var perc_done = num_done / progress_total_num * 100;

    var bar      = document.getElementById('progress_bar');
    var cell = bar.firstChild.firstChild.firstChild;
    cell.style.width = perc_done + "%";
    cell = bar.firstChild.firstChild.childNodes[1];
    cell.style.width = (100 - perc_done) + "%";
    cell = null;
    bar  = null;
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

function progress_clean_log() {
    var log = document.getElementById('progress_log');
    log.innerHTML = '';
    log.scrollTop = 0;
    log = null;
}

function progress_scheduler(mode, url_prefix, timeout, items, end_url, success_stats, fail_stats, term_url, finished_txt) {
    // Initialize
    if (progress_items === null) {
        progress_items         = items;
        failed_items           = Array();
        progress_total_num     = items.length;
        progress_end_url       = end_url;
        progress_term_url      = term_url;
        progress_success_stats = success_stats;
        progress_fail_stats    = fail_stats;
        progress_fin_txt       = finished_txt;
        progress_mode          = mode;
        progress_url           = url_prefix;
        progress_timeout       = timeout;
    }

    // Escape the loop when ended
    if (progress_ended)
        return false;

    // Regular processing when not paused and not already running
    if (!progress_paused && !progress_running) {
        if (progress_items.length > 0) {
            // Progressing
            progress_running = true;
            // Remove leading pipe signs (when having no folder set)
            update_progress_title(progress_items[0].replace(/^\|*/g, ''));
            get_url(url_prefix + '&_transid=-1&_item=' + escape(progress_items[0]),
                progress_handle_response,    // regular handler (http code 200)
                [ mode, progress_items[0] ], // data to hand over to handlers
                progress_handle_error        // error handler
            );
        } else {
            progress_finished();
            return;
        }
    }

    setTimeout(function() { progress_scheduler(mode, url_prefix, timeout, [], "", ""); }, timeout);
}

function update_bulk_moveto(val) {
    var fields = getElementsByClass('bulk_moveto');
    for(var i = 0; i < fields.length; i++)
        for(var a = 0; a < fields[i].options.length; a++)
            if(fields[i].options[a].value == val)
                fields[i].options[a].selected = true;
    fields = null;
}

//   .----------------------------------------------------------------------.
//   |              _        _   _            _   _                         |
//   |             / \   ___| |_(_)_   ____ _| |_(_) ___  _ __              |
//   |            / _ \ / __| __| \ \ / / _` | __| |/ _ \| '_ \             |
//   |           / ___ \ (__| |_| |\ V / (_| | |_| | (_) | | | |            |
//   |          /_/   \_\___|\__|_| \_/ \__,_|\__|_|\___/|_| |_|            |
//   |                                                                      |
//   +----------------------------------------------------------------------+

function wato_do_activation(est) {
    var siteid = 'local';

    // Hide the activate changes button
    var button = document.getElementById('act_changes_button');
    if(button) {
        button.style.display = 'none';
        button = null;
    }

    get_url("wato_ajax_activation.py",
            wato_activation_result, siteid);
    replication_progress[siteid] = 20; // 10 of 10 10ths
    setTimeout("replication_step('"+siteid+"',"+est+");", est/10);
}

function wato_activation_result(siteid, code) {
    replication_progress[siteid] = 0;
    var oState = document.getElementById("repstate_" + siteid);
    var oMsg   = document.getElementById("repmsg_" + siteid);
    if (code.substr(0, 3) == "OK:") {
        oState.innerHTML = "<div class='repprogress ok' style='width: 160px;'>OK</div>";
        oMsg.innerHTML = code.substr(3);

        // Reload page after 2 secs
        setTimeout(wato_replication_finish, 1000);
    } else {
        oState.innerHTML = '';
        oMsg.innerHTML = code;

        // Show the activate changes button again
        var button = document.getElementById('act_changes_button');
        if(button) {
            button.style.display = '';
            button = null;
        }
    }
    oState = null;
    oMsg = null;
}

//   +----------------------------------------------------------------------+
//   |           ____            _ _           _   _                        |
//   |          |  _ \ ___ _ __ | (_) ___ __ _| |_(_) ___  _ __             |
//   |          | |_) / _ \ '_ \| | |/ __/ _` | __| |/ _ \| '_ \            |
//   |          |  _ <  __/ |_) | | | (_| (_| | |_| | (_) | | | |           |
//   |          |_| \_\___| .__/|_|_|\___\__,_|\__|_|\___/|_| |_|           |
//   |                    |_|                                               |
//   +----------------------------------------------------------------------+
var replication_progress = new Array();

function wato_do_replication(siteid, est) {
    get_url("wato_ajax_replication.py?site=" + siteid,
            wato_replication_result, siteid);
    replication_progress[siteid] = 20; // 10 of 10 10ths
    setTimeout("replication_step('"+siteid+"',"+est+");", est/10);
}

function replication_step(siteid, est) {
    if (replication_progress[siteid] > 0) {
        replication_progress[siteid]--;
        var oDiv = document.getElementById("repstate_" + siteid);
        p = replication_progress[siteid];
        oDiv.innerHTML = "<div class=repprogress style='width: " + ((20-p)*8) + "px;'></div>"
        setTimeout("replication_step('"+siteid+"',"+est+");", est/20);
    }
}


// num_replsites is set by the page code in wat.py to the number async jobs started
// in total
function wato_replication_result(siteid, code) {
    replication_progress[siteid] = 0;
    var oDiv = document.getElementById("repstate_" + siteid);
    if (code.substr(0, 3) == "OK:") {
        oDiv.innerHTML = "<div class='repprogress ok' style='width: 160px;'>" +
              code.substr(3) + "</div>";
        num_replsites--;
    }
    else
        oDiv.innerHTML = code;

    if (0 == num_replsites) {
        setTimeout(wato_replication_finish, 1000);
    }
}

function wato_replication_finish() {
    // check if we have a sidebar-main frame setup
    if (this.parent && parent && parent.frames[1] == this)
        parent.frames[0].location.reload(); // reload sidebar

    // always reload main
    // this.location.reload();
    var oDiv = document.getElementById("act_changes_button");
    oDiv.style.display = "none";
    oDiv = null

    // Hide the pending changes container
    var oPending = document.getElementById("pending_changes");
    if (oPending) {
        oPending.style.display = "none";
        oPending = null
    }
}

function wato_randomize_secret(id, len) {
    var secret = "";
    for (var i=0; i<len; i++) {
        var c = parseInt(26 * Math.random() + 64);
        secret += String.fromCharCode(c);
    }
    var oInput = document.getElementById(id);
    oInput.value = secret;
}

// ----------------------------------------------------------------------------
// Folderlist
// ----------------------------------------------------------------------------

function wato_open_folder(event, link) {
    if (!event)
        event = window.event;
    var target = getTarget(event);
    if(target.tagName != 'DIV') {
        // Skip this event on clicks on other elements than the pure div
        return false;
    }

    location.href = link;
}

function wato_toggle_folder(event, oDiv, on) {
    if (!event)
        event = window.event;

    // Skip mouseout event when moving mouse over a child element of the
    // folder element
    if (!on) {
        var node = event.toElement || event.relatedTarget;
        while (node) {
            if (node == oDiv) {
                return false;
            }
            node = node.parentNode;
        }
    }

    var obj = oDiv.parentNode;
    var id = obj.id.substr(7);

    var elements = ['edit', 'move', 'delete'];
    for(var num in elements) {
        var elem = document.getElementById(elements[num] + '_' + id);
        if(elem) {
            if(on) {
                elem.style.display = 'inline';
            } else {
                elem.style.display = 'none';
            }
        }
    }

    if(on) {
        obj.style.backgroundImage = 'url("images/folder_open.png")';
    } else {
        obj.style.backgroundImage = 'url("images/folder_closed.png")';

        // Hide the eventual open move dialog
        var move_dialog = document.getElementById('move_dialog_' + id);
        if(move_dialog) {
            move_dialog.style.display = 'none';
            move_dialog = null;
        }
    }
    elem = null;
    obj = null;
}

function wato_toggle_move_folder(event, oButton) {
    if(!event)
        event = window.event;

    var id = oButton.id.substr(5);
    var obj = document.getElementById('move_dialog_' + id);
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
