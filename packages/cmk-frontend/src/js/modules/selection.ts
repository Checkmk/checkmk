/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import {call_ajax} from "./ajax";
import type {FunctionSpec} from "./utils";
import {
    add_class,
    get_row_info,
    has_row_info,
    querySelectorAllByClassName,
    remove_class,
    update_row_info,
} from "./utils";

interface SelectionProperties {
    page_id: null | string;
    selection_id: null | string;
    selected_rows: string[];
}

let selection_properties: SelectionProperties = {
    // The unique ID to identify the current page and its selections of a user
    page_id: null,
    selection_id: null,
    // Holds the row numbers of all selected rows
    selected_rows: [],
};

// Tells us if the row selection is enabled at the moment
let g_selection_enabled = false;

export function is_selection_enabled() {
    return g_selection_enabled;
}

export function set_selection_enabled(state: boolean) {
    g_selection_enabled = state;
}

export function get_selection_id() {
    return selection_properties.selection_id;
}

export function init_rowselect(properties: SelectionProperties) {
    selection_properties = properties;

    const tables = querySelectorAllByClassName("data");
    for (let i = 0; i < tables.length; i++)
        if (tables[i].tagName === "TABLE") table_init_rowselect(tables[i]);
}

function table_init_rowselect(oTable: HTMLElement) {
    const childs: HTMLInputElement[] = get_all_checkboxes(oTable);
    for (let i = 0; i < childs.length; i++) {
        // Perform initial selections
        if (selection_properties.selected_rows.indexOf(childs[i].name) > -1)
            childs[i].checked = true;
        else childs[i].checked = false;

        childs[i].onchange = function (e) {
            toggle_box(e, <HTMLInputElement>this);
        };

        iter_cells(childs[i], function (elem: HTMLElement) {
            elem.onmouseover = function () {
                return highlight_row(<HTMLElement>this, true);
            };
            elem.onmouseout = function () {
                return highlight_row(<HTMLElement>this, false);
            };
            elem.onclick = function (e: Event) {
                return toggle_row(e, <HTMLElement>this);
            };
        });
    }

    update_row_selection_information();
}

// Container is an DOM element to search below or a list of DOM elements
// to search below
function get_all_checkboxes(
    container: HTMLElement | HTMLElement[] | HTMLDocument,
) {
    const checkboxes: HTMLInputElement[] = [];
    let childs;
    if (container instanceof HTMLElement || container instanceof HTMLDocument) {
        // One DOM node given
        childs = container.getElementsByTagName("input");

        for (let i = 0; i < childs.length; i++)
            if (childs[i].type == "checkbox") checkboxes.push(childs[i]);
    } else {
        // Array given - at the moment this is a list of TR objects
        // Skip the header checkboxes
        for (let i = 0; i < container.length; i++) {
            childs = container[i].getElementsByTagName("input");

            for (let a = 0; a < childs.length; a++) {
                if (childs[a].type == "checkbox") {
                    checkboxes.push(childs[a]);
                }
            }
        }
    }

    return checkboxes;
}

function toggle_box(_e: Event, elem: HTMLInputElement) {
    const row_pos = selection_properties.selected_rows.indexOf(elem.name);

    if (row_pos > -1) {
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
function iter_cells(
    checkbox: HTMLInputElement,
    func: (elem: HTMLElement) => void,
) {
    let num_columns = parseInt(checkbox.value);
    // Now loop the next N cells to call the func for each cell
    // 1. Get row element
    // 2. Find the current td
    // 3. find the next N tds
    const cell = checkbox.parentNode;
    const row_childs = cell!.parentNode!.children;
    let found = false;
    for (let c = 0; c < row_childs.length && num_columns > 0; c++) {
        if (found === false) {
            if (row_childs[c] == cell) {
                found = true;
            } else {
                continue;
            }
        }

        const cur_cell = row_childs[c];
        if (cur_cell instanceof HTMLTableCellElement) {
            func(cur_cell);
            num_columns--;
        }
    }
}

function highlight_row(elem: HTMLElement, on: boolean) {
    const checkbox = find_checkbox(elem);
    if (checkbox !== null) {
        iter_cells(checkbox, function (elem: HTMLElement) {
            highlight_elem(elem, on);
        });
    }
    return false;
}

function find_checkbox(oTd: HTMLElement): null | HTMLInputElement {
    // Find the checkbox of this oTdent to gather the number of cells
    // to highlight after the checkbox
    // 1. Go up to the row
    // 2. search backwards for the next checkbox
    // 3. loop the number of columns to highlight
    const allTds = oTd.parentNode!.children;
    let found = false;
    let checkbox: null | HTMLInputElement = null;
    for (let a = allTds.length - 1; a >= 0 && checkbox === null; a--) {
        if (found === false) {
            if (allTds[a] == oTd) {
                /* that's me */
                found = true;
            } else continue;
        }

        // Found the clicked column, now walking the cells backward from the
        // current cell searching for the next checkbox
        const oTds = allTds[a].children;
        for (let x = 0; x < oTds.length; x++) {
            const el = oTds[x];
            if (el instanceof HTMLInputElement && el.type == "checkbox") {
                checkbox = el;
                break;
            }
        }
    }
    return checkbox;
}

function highlight_elem(elem: HTMLElement, on: boolean) {
    if (on) add_class(elem, "checkbox_hover");
    else remove_class(elem, "checkbox_hover");
}

function toggle_row(e: Event, elem: HTMLElement) {
    // Skip handling clicks on links/images/...
    const target = e.target;
    if (
        target instanceof HTMLElement &&
        target.tagName != "TD" &&
        target.tagName != "LABEL"
    )
        return true;

    // Find the checkbox for this element
    const checkbox = find_checkbox(elem);
    if (checkbox === null) return;

    // Is SHIFT pressed?
    // Yes:
    //   Select all from the last selection

    // Is the current row already selected?
    const row_pos = selection_properties.selected_rows.indexOf(checkbox.name);
    if (row_pos > -1) {
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

    if (e.stopPropagation) e.stopPropagation();
    e.cancelBubble = true;

    // Disable the default events for all the different browsers
    if (e.preventDefault) e.preventDefault();
    else e.returnValue = false;
    return false;
}

function set_rowselection(
    action: string,
    rows: string[],
    post_selection_functions: FunctionSpec[] = [],
) {
    call_ajax("ajax_set_rowselection.py", {
        method: "POST",
        post_data:
            "id=" +
            selection_properties.page_id +
            "&selection=" +
            selection_properties.selection_id +
            "&action=" +
            action +
            "&rows=" +
            rows.join(","),
        response_handler: function (_data: unknown, _response: unknown) {
            post_selection_functions.forEach(f_spec =>
                f_spec.function(...f_spec.arguments),
            );
        },
    });
}

// Update the header information (how many rows selected)
function update_row_selection_information() {
    if (!has_row_info()) return; // Nothing to update

    const count = selection_properties.selected_rows.length;
    let current_text = get_row_info();

    // First remove the text added by previous calls to this functions
    if (current_text.indexOf("/") != -1) {
        const parts = current_text.split("/");
        current_text = parts[1];
    }

    update_row_info(count + "/" + current_text);
}

// Is used to select/deselect all rows in the current view. This can optionally
// be called with a container element. If given only the elements within this
// container are highlighted.
// It is also possible to give an array of DOM elements as parameter to toggle
// all checkboxes below these objects.
export function toggle_all_rows(obj?: HTMLElement | HTMLElement[]) {
    const checkboxes = get_all_checkboxes(obj || document);

    let all_selected = true;
    let none_selected = true;
    let some_failed = false;
    for (let i = 0; i < checkboxes.length; i++) {
        if (
            selection_properties.selected_rows.indexOf(checkboxes[i].name) ===
            -1
        )
            all_selected = false;
        else none_selected = false;
        if (
            checkboxes[i].classList &&
            checkboxes[i].classList.contains("failed")
        )
            some_failed = true;
    }

    const entry = document.getElementById(
        "menu_entry_checkbox_selection",
    ) as HTMLDivElement;
    const img: HTMLImageElement | null = entry
        ? entry.getElementsByTagName("img")[0]
        : null;
    // Toggle the state
    if (all_selected) {
        remove_selected_rows(checkboxes);
        if (img) img.src = img.src.replace("toggle_on", "toggle_off");
    } else {
        select_all_rows(checkboxes, some_failed && none_selected);
        if (img) img.src = img.src.replace("toggle_off", "toggle_on");
    }
}

function remove_selected_rows(elems: HTMLInputElement[]) {
    set_rowselection("del", selection_properties.selected_rows);

    for (let i = 0; i < elems.length; i++) {
        elems[i].checked = false;
        const row_pos = selection_properties.selected_rows.indexOf(
            elems[i].name,
        );
        if (row_pos > -1) selection_properties.selected_rows.splice(row_pos, 1);
    }

    update_row_selection_information();
}

function select_all_rows(elems: HTMLInputElement[], only_failed?: boolean) {
    if (typeof only_failed === "undefined") {
        only_failed = false;
    }

    for (let i = 0; i < elems.length; i++) {
        if (!only_failed || elems[i].classList.contains("failed")) {
            elems[i].checked = true;
            if (
                selection_properties.selected_rows.indexOf(elems[i].name) === -1
            )
                selection_properties.selected_rows.push(elems[i].name);
        }
    }

    update_row_selection_information();
    set_rowselection("add", selection_properties.selected_rows);
}

// Toggles the datarows of the group which the given checkbox is part of.
export function toggle_group_rows(checkbox: HTMLInputElement) {
    // 1. Find the first tbody parent
    // 2. iterate over the children and search for the group header of the checkbox
    //    - Save the TR with class groupheader
    //    - End this search once found the checkbox element
    const this_row = checkbox.parentNode!.parentNode!;
    const rows = this_row.parentNode!.children;

    let in_this_group = false;
    let group_start: number | null = null;
    let group_end: number | null = null;
    for (let i = 0; i < rows.length; i++) {
        if (rows[i].tagName !== "TR") continue;

        if (!in_this_group) {
            // Search for the start of our group
            // Save the current group row element
            if (rows[i].className === "groupheader") group_start = i + 1;

            // Found the row of the checkbox? Then finished with this loop
            if (rows[i] === this_row) in_this_group = true;
        } else {
            // Found the start of our group. Now search for the end
            if (rows[i].className === "groupheader") {
                group_end = i;
                break;
            }
        }
    }

    if (group_start === null) group_start = 0;
    if (group_end === null) group_end = rows.length;

    // Found the group start and end row of the checkbox!
    const group_rows: HTMLTableRowElement[] = [];
    for (let a = group_start; a < group_end!; a++) {
        if (rows[a].tagName === "TR") {
            group_rows.push(rows[a] as HTMLTableRowElement);
        }
    }
    toggle_all_rows(group_rows);
}

export function update_bulk_moveto(val: string) {
    const fields = document.getElementsByClassName(
        "bulk_moveto",
    ) as HTMLCollectionOf<HTMLSelectElement>;
    for (let i = 0; i < fields.length; i++)
        for (let a = 0; a < fields[i].options.length; a++)
            if (fields[i].options[a].value == val)
                fields[i].options[a].selected = true;
}

export function execute_bulk_action_for_single_host(
    elem: HTMLElement,
    action_fct: () => void,
    action_args: any[],
) {
    const td =
        elem.tagName === "TD"
            ? elem
            : (elem.closest("td")! as HTMLTableCellElement);
    const checkbox: HTMLInputElement = find_checkbox(td)!;

    const post_selection_fct: FunctionSpec = {
        function: action_fct,
        arguments: action_args,
    };
    // Select only this element's row
    set_rowselection("set", [checkbox.name], [post_selection_fct]);
}
