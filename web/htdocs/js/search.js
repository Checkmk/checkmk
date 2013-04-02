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

var aSearchResults = [];
var aSearchContents = '';
var iCurrent = null;
var mkSearchTargetFrame = 'main';
var oldValue = "";

// Register an input field to be a search field and add eventhandlers
function mkSearchAddField(field, targetFrame) {
    var oField = document.getElementById(field);
    if(oField) {
        if(typeof targetFrame != 'undefined') {
            mkSearchTargetFrame = targetFrame;
        }

        oField.onkeydown = function(e) { if (!e) e = window.event; return mkSearchKeyDown(e, oField); }
        oField.onkeyup   = function(e) { if (!e) e = window.event; return mkSearchKeyUp(e, oField);}
        oField.onclick   = function(e) { mkSearchClose(); return true; }

        // On doubleclick toggle the list
        oField.ondblclick  = function(e) { if (!e) e = window.event; mkSearchToggle(e, oField); }
    }
}

mkSearchAddField("mk_side_search_field", "main");

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
                mkSearch(e, oField);
            }
        break;
    }
}

function mkSearchFindUrl(aSearchObjects, objType, oField) {
    var namepart = mkSearchCleanupString(oField.value, objType);
    // first try to find if namepart is a complete object name
    // found in our list and is unique (found in only one site)
    var url = null;
    var selected_obj = null;
    var found = 0;
    for (var i in aSearchObjects) {
        var objSite  = aSearchObjects[i][0];
        var objName  = aSearchObjects[i][1];
        if (mkSearchMatch(objName, namepart)) {
            found ++;
            if (url != null) { // found second match -> not unique
                url = null;
                break; // abort
            }
            url = mkSearchGetUrl(objType, objName, objSite, found);
            selected_obj = objName;
        }
    }
    if (url != null) {
        if(objType == 'h')
            oField.value = selected_obj;
        else
            oField.value = objType + ':' + selected_obj;
        return url;
    }

    // not found, not unique or only prefix -> display a view that shows more objects
    return mkSearchGetUrl(objType, namepart, '', found);
}

// On key press down event handler
function mkSearchButton() {
    var oField = document.getElementById("mk_side_search_field");
    var ev = { "which" : 0, "keyCode" : 13 }
    return mkSearchKeyDown(ev, oField);
}

function mkSearchKeyDown(e, oField) {
    var keyCode = e.which || e.keyCode;

    switch (keyCode) {
            // Return/Enter
            case 13:
                if (iCurrent != null) {
                    mkSearchNavigate();
                    if(aSearchResults[iCurrent].type == 'h')
	                      oField.value = aSearchResults[iCurrent].name;
                    else
	                      oField.value = aSearchResults[iCurrent].type + ':' + aSearchResults[iCurrent].name;
                    mkSearchClose();
                } else {
                    if (oField.value == "")
                        return; /* search field empty, rather not show all services! */
                    // When nothing selected, navigate with the current contents of the field
                    var objType = mkSearchGetTypePrefix(oField.value);
                    var aSearchObjects = mkSearchGetSearchObjects(objType);
                    var url = mkSearchFindUrl(aSearchObjects, objType, oField);
                    top.frames[mkSearchTargetFrame].location.href = url;
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
                    mkSearch(e, oField);
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
    if (aSearchResults[iCurrent])
        top.frames[mkSearchTargetFrame].location.href = aSearchResults[iCurrent].url;
}

// Move one step of given size in the result list
function mkSearchMoveElement(step) {
    if(iCurrent == null) {
        iCurrent = -1;
    }

    iCurrent += step;

    if(iCurrent < 0)
        iCurrent = aSearchResults.length-1;

    if(iCurrent > aSearchResults.length-1)
        iCurrent = 0;

    var oResults = document.getElementById('mk_search_results');
    if (!oResults)
        return;
    oResults = oResults.childNodes;

    var a = 0;
    for(var i = 0; i < oResults.length; i++) {
        if(oResults[i].tagName == 'A') {
            if(a == iCurrent) {
                oResults[i].setAttribute('class', 'active');
                oResults[i].setAttribute('className', 'active');
            } else {
                oResults[i].setAttribute('class', 'inactive');
                oResults[i].setAttribute('className', 'inactive');
            }
            a++;
        }
    }
    oResults = null;
}

// Is the result list shown at the moment?
function mkSearchResultShown() {
    var oContainer = document.getElementById('mk_search_results');
    if(oContainer) {
        oContainer = null;
        return true;
    } else
        return false;
}

// Toggle the result list
function mkSearchToggle(e, oField) {
    if(mkSearchResultShown()) {
        mkSearchClose();
    } else {
        mkSearch(e, oField);
    }
}

// Close the result list
function mkSearchClose() {
    var oContainer = document.getElementById('mk_search_results');
    if(oContainer) {
        oContainer.parentNode.removeChild(oContainer);
        oContainer = null;
    }

    aSearchResults = [];
    iCurrent = null;
}

function mkSearchGetTypePrefix(s) {
    if(s.indexOf('hg:') == 0)
        return 'hg';
    else if(s.indexOf('s:') == 0)
        return 's';
    else if(s.indexOf('sg:') == 0)
        return 'sg';
    else
        return 'h';
}

function mkSearchCleanupString(s, objType) {
    return s.replace(RegExp('^'+objType+':', 'i'), '');
}

function mkSearchGetSearchObjects(objType) {
    if(objType == 'h' && typeof aSearchHosts !== 'undefined')
        return aSearchHosts;
    else if(objType == 'hg' && typeof aSearchHostgroups !== 'undefined')
        return aSearchHostgroups;
    else if(objType == 's' && typeof aSearchServices !== 'undefined')
        return aSearchServices;
    else if(objType == 'sg' && typeof aSearchServicegroups !== 'undefined')
        return aSearchServicegroups;
    else
        return [];
}

function is_ipaddress(add, prefix) {
    if (prefix)
        return add.match(/^[0-9]{1,3}(\.[0-9]{1,3}){0,2}\.?$/);
    else
        return add.match(/^([0-9]{1,3}\.){3}[0-9]{1,3}$/);
}

function mkSearchGetUrl(objType, objName, objSite, numMatches) {
    objName = objName.replace(/\*/g,"\.\*");
    if (numMatches == null)
        numMatches = 0;

    if(objType == 'h')
        if(numMatches == 1)
            return 'view.py?view_name=host&host=' + objName + '&site=' + objSite;
        else if(numMatches > 1)
            return 'view.py?view_name=hosts&host=' + objName;
        else if (is_ipaddress(objName, true))
            return 'view.py?view_name=searchsvc&search=Search&filled_in=filter&host_address_prefix=yes&host_address=' + objName;
        else if (is_ipaddress(objName, false))
            return 'view.py?view_name=searchsvc&search=Search&filled_in=filter&host_address_prefix=no&host_address=' + objName;
        else
            return 'view.py?view_name=searchsvc&search=Search&filled_in=filter&service=' + objName;
    else if(objType == 'hg')
        if(numMatches == 1)
            return 'view.py?view_name=hostgroup&hostgroup=' + objName + '&site=' + objSite;
        else
            // FIXME: not correct. Need a page where the name parameter can be a part match
            return 'view.py?view_name=hostgroup&hostgroup=' + objName + '&site=' + objSite;
    else if(objType == 'sg')
        if(numMatches == 1)
            return 'view.py?view_name=servicegroup&servicegroup=' + objName + '&site=' + objSite;
        else
            // FIXME: not correct. Need a page where the name parameter can be a part match
            return 'view.py?view_name=servicegroup&servicegroup=' + objName + '&site=' + objSite;
    else if(objType == 's')
        if(numMatches == 1)
            return 'view.py?view_name=servicedesc&service=' + objName + '&site=' + objSite;
        else
            // FIXME: not correct. Need a page where the name parameter can be a part match
            return 'view.py?view_name=servicedesc&service=' + objName + '&site=' + objSite;
}

// This performs a case insensitive search of a substring in a string
// Returns true if found and false if not
function mkSearchMatch(base, search) {
    if (!base)
        return false;
    return base.toLowerCase().indexOf(search.toLowerCase()) > -1;
}

function mkSearchAddSearchResults(aSearchObjects, objType, val) {
    val = mkSearchCleanupString(val, objType);
    // Build matching regex
    // var oMatch = new RegExp('^'+val, 'gi');
    // switch to infix search
    // var oMatch = new RegExp(val, 'gi');
    // 1.1.8: do not use regexes. We would have to quote . and /. User
    // is not aware of regexes.

    var objName, objSite;
    aSearchContents = '';
    var numHits = 0;

    // First check, if all matched items have the same
    // site. If not, we will display the site name in
    // brackets after the item
    var the_only_site = null;
    var show_site = false;
    for (var i = 0; i < aSearchObjects.length; i++) {
        objName  = aSearchObjects[i][1];
        if (mkSearchMatch(objName, val)) {
            objSite  = aSearchObjects[i][0];
            if (the_only_site == null)
                the_only_site = objSite;
            else if (the_only_site != objSite) {
                show_site = true;
                break;
            }
        }
    }

    for (var i = 0; i < aSearchObjects.length; i++) {
        objSite  = aSearchObjects[i][0];
        objName  = aSearchObjects[i][1];

        if (mkSearchMatch(objName, val)) {
            var url = mkSearchGetUrl(objType, objName, objSite, 1);
            var oResult = {
                'id': 'result_' + objName,
                'name': objName,
                'site': objSite,
                'type': objType,
                'url': url
            };

            // limit the number of search hits
            numHits ++;
            if (numHits > aSearchLimit)
                break;

            // Add id to search result array
            aSearchResults.push(oResult);
            aSearchContents += '<a id="' + oResult.id + '" class="' + oResult.type
                + '" href="' + oResult.url
                + '" onclick="mkSearchClose()" target="' + mkSearchTargetFrame
                + '">' + objName
            if (show_site)
                aSearchContents += " (" + objSite + ")"
            aSearchContents += "</a>\n";
        }
    }
}

// Build a new result list and show it up
function mkSearch(e, oField) {
    if(oField == null) {
        return;
    }

    var val = oField.value;
    if (val == oldValue)
        return;

    if (aSearchResults[0] && val == oldValue)
        return; // nothing changed. No new search neccessary
    oldValue = val;

    aSearchResults = [];
    var objType = mkSearchGetTypePrefix(val);
    var aSearchObjects = mkSearchGetSearchObjects(objType);

    if (!aSearchObjects || !aSearchObjects[0]) {
        // alert("No objects to search for");
        return;
    }

    mkSearchAddSearchResults(aSearchObjects, objType, val);

    if(aSearchContents != '') {
        var oContainer = document.getElementById('mk_search_results');
        if(!oContainer) {
            var oContainer = document.createElement('div');
            oContainer.setAttribute('id', 'mk_search_results');
        }
        oContainer.innerHTML = aSearchContents;
        oField.parentNode.appendChild(oContainer);
        oContainer = null;
    } else {
        mkSearchClose();
    }

    oField = null;
}
