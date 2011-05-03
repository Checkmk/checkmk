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

function progress_handle_response(data, code) {
    var mode = data[0];
    var item = data[1];

    var arr = code.split("\n", 1);
    var head = arr[0];
    var body = arr[1];
    var header = null;
    try {
        var header = eval(head);
    } catch(err) {
        alert('Invalid response: ' + code);    
    }
    alert('Header: ' + header + ' Body: ' + body);
}

function progress_scheduler(mode, items, timeout) {
    if(items.length > 0) {
        // Progressing
        get_url('wato.py?mode=' + escape(ty) + '&phase=action&_item=' + escape(items[0]) + '&_transid=-1', progress_handle_response, [ mode, items[0] ]);
    } else {
        // Finished
        alert('finished');
    }

    setTimeout(function() { progress_scheduler(mode, items, timeout); }, timeout);
}
