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
// tails.  You should have received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import * as utils from "utils";
import * as ajax from "ajax";

var selection_properties = {
    // The unique ID to identify the current page and its selections of a user
    "page_id": null,
    "selection_id": null,
    // Holds the row numbers of all selected rows
    "selected_rows": [],
};

// Tells us if the row selection is enabled at the moment
var g_selection_enabled = false;

export function is_selection_enabled() {
    return g_selection_enabled;
}

export function set_selection_enabled(state) {
    g_selection_enabled = state;
}

export function get_selection_id() {
    return selection_properties.selection_id;
}

export function init_rowselect(properties) {
    selection_properties = properties;

    var tables = document.getElementsByClassName("data");
    for(var i = 0; i < tables.length; i++)
        if(tables[i].tagName === "TABLE")
            table_init_rowselect(tables[i]);
}

function table_init_rowselect(oTable) {
    var childs = get_all_checkboxes(oTable);
    for(var i = 0; i < childs.length; i++) {
        // Perform initial selections
        if (selection_properties.selected_rows.indexOf(childs[i].name) > -1)
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

// Container is an DOM element to search below or a list of DOM elements
// to search below
function get_all_checkboxes(container) {
    var checkboxes = [], childs, i;
    if(typeof(container) === "object" && container.length && !container.tagName) {
        // Array given - at the moment this is a list of TR objects
        // Skip the header checkboxes
        for(i = 0; i < container.length; i++) {
            childs = container[i].getElementsByTagName("input");

            for(var a = 0; a < childs.length; a++) {
                if(childs[a].type == "checkbox") {
                    checkboxes.push(childs[a]);
                }
            }
        }
    } else {
        // One DOM node given
        childs = container.getElementsByTagName("input");

        for(i = 0; i < childs.length; i++)
            if(childs[i].type == "checkbox")
                checkboxes.push(childs[i]);
    }

    return checkboxes;
}

function toggle_box(e, elem) {
    var row_pos = selection_properties.selected_rows.indexOf(elem.name);

    if(row_pos > -1) {
        selection_properties.selected_rows.splice(row_pos, 1);
        set_rowselection("del", [elem.name]);
    } else {
        selection_properties.selected_rows.push(elem.name);
        set_rowselection("add", [elem.name]);
    }

    update_row_selection_information();
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
    for (var c = 0; c < row_childs.length && num_columns > 0; c++) {
        if(found === false) {
            if(row_childs[c] == cell) {
                found = true;
            } else {
                continue;
            }
        }

        if (row_childs[c].tagName == "TD") {
            func(row_childs[c]);
            num_columns--;
        }
    }
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
            if(oTds[x].tagName === "INPUT" && oTds[x].type == "checkbox") {
                checkbox = oTds[x];
                break;
            }
        }
    }
    return checkbox;
}

function highlight_elem(elem, on) {
    if (on)
        utils.add_class(elem, "checkbox_hover");
    else
        utils.remove_class(elem, "checkbox_hover");
}

function toggle_row(e, elem) {
    if(!e)
        e = window.event;

    // Skip handling clicks on links/images/...
    var target = utils.get_target(e);
    if(target.tagName != "TD" && target.tagName != "LABEL")
        return true;

    // Find the checkbox for this element
    var checkbox = find_checkbox(elem);
    if(checkbox === null)
        return;

    // Is SHIFT pressed?
    // Yes:
    //   Select all from the last selection

    // Is the current row already selected?
    var row_pos = selection_properties.selected_rows.indexOf(checkbox.name);
    if(row_pos > -1) {
        // Yes: Unselect it
        checkbox.checked = false;
        selection_properties.selected_rows.splice(row_pos, 1);
        set_rowselection("del", [checkbox.name]);
    } else {
        // No:  Select it
        checkbox.checked = true;
        selection_properties.selected_rows.push(checkbox.name);
        set_rowselection("add", [checkbox.name]);
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

function set_rowselection(action, rows) {
    ajax.post_url("ajax_set_rowselection.py", "id=" + selection_properties.page_id
        + "&selection=" + selection_properties.selection_id
        + "&action=" + action
        + "&rows=" + rows.join(","));
}

function update_row_selection_information() {
    // First update the header information (how many rows selected)
    var count = selection_properties.selected_rows.length;
    var oDiv = document.getElementById("headinfo");
    if (oDiv) {
        var current_text = oDiv.innerHTML;
        if (current_text.indexOf("/") != -1) {
            var parts = current_text.split("/");
            current_text = parts[1];
        }
        oDiv.innerHTML = count + "/" + current_text;
    }
}

// Is used to select/deselect all rows in the current view. This can optionally
// be called with a container element. If given only the elements within this
// container are highlighted.
// It is also possible to give an array of DOM elements as parameter to toggle
// all checkboxes below these objects.
export function toggle_all_rows(obj) {
    var checkboxes = get_all_checkboxes(obj || document);

    var all_selected = true;
    var none_selected = true;
    var some_failed = false;
    for(var i = 0; i < checkboxes.length; i++) {
        if (selection_properties.selected_rows.indexOf(checkboxes[i].name) === -1)
            all_selected = false;
        else
            none_selected = false;
        if (checkboxes[i].classList && checkboxes[i].classList.contains("failed"))
            some_failed = true;
    }

    // Toggle the state
    if (all_selected)
        remove_selected_rows(checkboxes);
    else
        select_all_rows(checkboxes, some_failed && none_selected);
}

function remove_selected_rows(elems) {
    set_rowselection("del", selection_properties.selected_rows);

    for(var i = 0; i < elems.length; i++) {
        elems[i].checked = false;
        var row_pos = selection_properties.selected_rows.indexOf(elems[i].name);
        if(row_pos > -1)
            selection_properties.selected_rows.splice(row_pos, 1);
    }

    update_row_selection_information();
}

function select_all_rows(elems, only_failed) {
    if (typeof only_failed === "undefined") {
        only_failed = false;
    }

    for (var i = 0; i < elems.length; i++) {
        if (!only_failed || elems[i].classList.contains("failed")) {
            elems[i].checked = true;
            if (selection_properties.selected_rows.indexOf(elems[i].name) === -1)
                selection_properties.selected_rows.push(elems[i].name);
        }
    }

    update_row_selection_information();
    set_rowselection("add", selection_properties.selected_rows);
}

// Toggles the datarows of the group which the given checkbox is part of.
export function toggle_group_rows(checkbox) {
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
        if(rows[i].tagName !== "TR")
            continue;

        if(!in_this_group) {
            // Search for the start of our group
            // Save the current group row element
            if(rows[i].className === "groupheader")
                group_start = i + 1;

            // Found the row of the checkbox? Then finished with this loop
            if(rows[i] === this_row)
                in_this_group = true;
        } else {
            // Found the start of our group. Now search for the end
            if(rows[i].className === "groupheader") {
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
        if(rows[a].tagName === "TR") {
            group_rows.push(rows[a]);
        }
    }
    toggle_all_rows(group_rows);
}

export function update_bulk_moveto(val) {
    var fields = document.getElementsByClassName("bulk_moveto");
    for(var i = 0; i < fields.length; i++)
        for(var a = 0; a < fields[i].options.length; a++)
            if(fields[i].options[a].value == val)
                fields[i].options[a].selected = true;
}
