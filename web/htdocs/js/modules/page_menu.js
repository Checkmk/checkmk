// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import "element-closest-polyfill";
import * as foldable_container from "foldable_container";
import * as popup_menu from "popup_menu";

// Closes the active page menu dropdown
export function close_active_dropdown() {
    popup_menu.close_popup();
}

export function set_checkbox_entry(id_stem, checked) {
    var oEntryChecked = document.getElementById("menu_entry_" + id_stem + "_checked");
    var oEntryUnhecked = document.getElementById("menu_entry_" + id_stem + "_unchecked");

    if (checked) {
        utils.change_class(oEntryChecked, "invisible", "visible");
        utils.change_class(oEntryUnhecked, "visible", "invisible");
    }
    else {
        utils.change_class(oEntryChecked, "visible", "invisible");
        utils.change_class(oEntryUnhecked, "invisible", "visible");
    }
}

// Make a dropdown usable
export function enable_dropdown(id) {
    toggle_dropdown_enabled(id, true);
}

// Set a dropdown to be not usable (inactive)
export function disable_dropdown(id) {
    toggle_dropdown_enabled(id, false);
}

function toggle_dropdown_enabled(id, enabled) {
    var dropdown = document.getElementById("page_menu_dropdown_" + id);
    if (enabled) {
        utils.remove_class(dropdown, "disabled");
    }
    else {
        utils.add_class(dropdown, "disabled");
    }
}

export function enable_menu_entry(id, enabled) {
    var from, to;
    if (enabled) {
        from = "disabled";
        to = "enabled";
    }
    else {
        from = "enabled";
        to = "disabled";
    }
    var oEntry = document.getElementById("menu_entry_" + id);
    utils.change_class(oEntry, from, to);

    var oShortCut = document.getElementById("menu_shortcut_" + id);
    if (oShortCut)
        utils.change_class(oShortCut, from, to);
}

export function enable_menu_entries(css_class, enabled) {
    let from, to;
    if (enabled) {
        from = "disabled";
        to = "enabled";
    }
    else {
        from = "enabled";
        to = "disabled";
    }

    const elements = document.getElementById("page_menu_bar").querySelectorAll(".entry." + css_class);
    for (const element of elements) {
        utils.change_class(element, from, to);
    }
}

// Toggles a PageMenuEntryPopup from a page menu entry
export function toggle_popup(popup_id) {
    let popup = document.getElementById(popup_id);
    let was_open = utils.has_class(popup, "active");

    close_active_dropdown();
    close_active_popups();

    if (was_open)
        do_close_popup(popup);
    else
        do_open_popup(popup);
}

// Opens a PageMenuEntryPopup from a page menu entry
export function open_popup(popup_id) {
    close_active_dropdown();
    close_active_popups();

    do_open_popup(document.getElementById(popup_id));
}

function do_open_popup(popup) {
    utils.add_class(popup, "active");

    // Call registered hook
    if (Object.prototype.hasOwnProperty.call(on_open, popup.id)) {
        on_open[popup.id]();
    }
}

// Closes all open PageMenuEntryPopup
function close_active_popups() {
    document.querySelectorAll(".page_menu_popup").forEach((popup) => {
        do_close_popup(popup);
    });
}

// Close a specific PageMenuEntryPopup
export function close_popup(a) {
    do_close_popup(a.closest(".page_menu_popup"));
}

function do_close_popup(popup) {
    utils.remove_class(popup, "active");

    // Call registered hook
    if (Object.prototype.hasOwnProperty.call(on_close, popup.id)) {
        on_close[popup.id]();
    }
}

const on_open = {};
const on_close = {};

export function register_on_open_handler(popup_id, handler) {
    on_open[popup_id] = handler;
}

export function register_on_close_handler(popup_id, handler) {
    on_close[popup_id] = handler;
}

export function toggle_suggestions() {
    var oPageMenuBar = document.getElementById("page_menu_bar");
    var open;
    if (utils.has_class(oPageMenuBar, "hide_suggestions")) {
        utils.remove_class(oPageMenuBar, "hide_suggestions");
        open = "on";
    } else {
        utils.add_class(oPageMenuBar, "hide_suggestions");
        open = "off";
    }
    foldable_container.persist_tree_state("suggestions", "all", open);
}

export function form_submit(form_name, button_name)
{
    var oForm = document.getElementById("form_" + form_name);
    var field = document.createElement("input");
    field.type = "hidden";
    field.name = button_name;
    field.value = "SET";
    oForm.appendChild(field);
    oForm.submit();
}

// Show / hide all entries of this group
export function toggle_popup_filter_list(trigger, filter_list_id)
{
    utils.toggle_class(trigger, "active", "inactive");
    utils.toggle_class(document.getElementById(filter_list_id), "active", "inactive");
}

export function toggle_filter_group_display(filter_group)
{
    utils.toggle_class(filter_group, "active", "inactive");
}

export function on_filter_popup_open()
{
    utils.update_url_parameter("_show_filter_form", "1");
}

export function on_filter_popup_close()
{
    utils.update_url_parameter("_show_filter_form", "0");
}

// Scroll to the top after adding new filters
export function update_filter_list_scroll(filter_list_id)
{
    let filter_list = document.getElementById(filter_list_id);
    let scrollable = filter_list.getElementsByClassName("simplebar-content-wrapper")[0];
    try { // scrollTo() is not supported in IE
        setTimeout(() => { scrollable.scrollTo({top: 0, left: 0, behavior: "smooth"}); }, 200);
    }
    catch (e) {
        scrollable.scrollTop = 0;
    }
}

export function update_page_state_top_line(text)
{
    let container = document.getElementById("page_state_top_line");
    container.innerHTML = text;
}

export function side_popup_add_simplebar_scrollbar(popup_id)
{
    let popup = document.getElementById(popup_id);
    let content = popup.getElementsByClassName("side_popup_content")[0];
    utils.add_simplebar_scrollbar_to_object(content);
}
