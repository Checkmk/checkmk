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

var iCurrent = null;
var oCurrent = null;
var oldValue = "";
var g_ajax_obj = null;

// Register an input field to be a search field and add eventhandlers
function mkSearchAddField(field) {
    var oField = document.getElementById(field);
    if(oField) {
        oField.onkeydown = function(e) { if (!e) e = window.event; return mkSearchKeyDown(e, oField); }
        oField.onkeyup   = function(e) { if (!e) e = window.event; return mkSearchKeyUp(e, oField); }
        oField.onclick   = function(e) { mkSearchClose(); return true; }

        // On doubleclick toggle the list
        oField.ondblclick  = function(e) { mkSearchToggle(oField); }
    }
}

mkSearchAddField("mk_side_search_field");

// On key release event handler
function mkSearchKeyUp(e, oField) {

    var keyCode = e.which || e.keyCode;

    switch (keyCode) {
        // 18: Return/Enter
        // 27: Escape
        case 13:
        case 27:
            mkSearchClose();
            e.returnValue = false;
            e.cancelBubble = true;
        break;

        // Other keys
        default:
            if (oField.value == "") {
                e.returnValue = false;
                e.cancelBubble = true;
                mkSearchClose();
            }
            else {
                mkSearch(oField);
            }
        break;
    }
}

// On key press down event handler
function mkSearchButton() {
    var oField = document.getElementById("mk_side_search_field");
    var ev = { "which" : 0, "keyCode" : 13 }
    return mkSearchKeyDown(ev, oField);
}

function search_dropdown_value() {
    if (oCurrent)
        return oCurrent.id.replace('result_', '');
    else
        return null;
}

function mkSearchKeyDown(e, oField) {
    var keyCode = e.which || e.keyCode;

    switch (keyCode) {
        // Return/Enter
        case 13:
            if (oCurrent != null) {
                mkSearchNavigate();
	        oField.value = search_dropdown_value()
                mkSearchClose();
            } else {
                if (oField.value == "")
                    return; /* search field empty, rather not show all services! */
                // When nothing selected, navigate with the current contents of the field
                top.frames['main'].location.href = 'search_open.py?q=' + encodeURIComponent(oField.value);
                mkTermSearch();
                mkSearchClose();
            }

            e.returnValue = false;
            e.cancelBubble = true;
        break;

        // Escape
        case 27:
            mkSearchClose();
            e.returnValue = false;
            e.cancelBubble = true;
        break;

        // Tab
        case 9:
            if(mkSearchResultShown()) {
                mkSearchClose();
            }
            return;
        break;

        // Up/Down arrow (Must not be handled in onkeyup since this does not fire repeated events)
        case 38:
        case 40:
            if(!mkSearchResultShown()) {
                mkSearch(oField);
            }

            mkSearchMoveElement(keyCode == 38 ? -1 : 1);

            e.preventDefault();
            return false;
        break;
    }
    oldValue = oField.value;
}

// Navigate to the target of the selected event
function mkSearchNavigate() {
    top.frames['main'].location.href = oCurrent.href;
}

// Move one step of given size in the result list
function mkSearchMoveElement(step) {
    if(iCurrent == null) {
        iCurrent = -1;
    }

    iCurrent += step;

    var oResults = document.getElementById('mk_search_results');
    if (!oResults)
        return;

    if(iCurrent < 0)
        iCurrent = oResults.children.length-1;

    if(iCurrent > oResults.children.length-1)
        iCurrent = 0;

    oResults = oResults.childNodes;

    var a = 0;
    for(var i = 0; i < oResults.length; i++) {
        if(oResults[i].tagName == 'A') {
            if(a == iCurrent) {
                oCurrent = oResults[i];
                oResults[i].setAttribute('class', 'active');
            } else {
                oResults[i].setAttribute('class', 'inactive');
            }
            a++;
        }
    }
    oResults = null;
}

// Is the result list shown at the moment?
function mkSearchResultShown() {
    return document.getElementById('mk_search_results') ? true : false;
}

// Toggle the result list
function mkSearchToggle(oField) {
    if(mkSearchResultShown()) {
        mkSearchClose();
    } else {
        mkSearch(oField);
    }
}

// Close the result list
function mkSearchClose() {
    var oContainer = document.getElementById('mk_search_results');
    if(oContainer) {
        oContainer.parentNode.removeChild(oContainer);
        oContainer = null;
    }

    iCurrent = null;
    oCurrent = null;
}

function handle_search_response(oField, code) {
    if (code != '') {
        var oContainer = document.getElementById('mk_search_results');
        if(!oContainer) {
            var oContainer = document.createElement('div');
            oContainer.setAttribute('id', 'mk_search_results');
            oField.parentNode.appendChild(oContainer);
        }

        oContainer.innerHTML = code;
        oContainer = null;
    } else {
        mkSearchClose();
    }
    oField = null
}

function handle_search_error(oField, statusCode) {

}

function mkTermSearch() {
    // Terminate eventually already running request
    if (g_ajax_obj) {
        g_ajax_obj.abort();
        g_ajax_obj = null;
    }
}

// Build a new result list and show it up
function mkSearch(oField) {
    if(oField == null)
        return;

    var val = oField.value;
    if (mkSearchResultShown() && val == oldValue)
        return; // nothing changed, no new search
    oldValue = val;

    mkTermSearch();
    g_ajax_obj = get_url('ajax_search.py?q=' + encodeURIComponent(val),
            handle_search_response, oField, handle_search_error);

    oField = null;
}
