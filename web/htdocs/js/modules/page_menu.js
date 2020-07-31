// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import "element-closest-polyfill";
import * as foldable_container from "foldable_container";

var suggestions_id = null;

export function add_suggestions(sugg_id, open) {
    if (open)
        utils.add_class(document.body, "suggestions");
    suggestions_id = sugg_id;
}


function page_menu_entries() {
    return Array.prototype.slice.call(document.getElementsByClassName("menu"));
}


export function close_active_menu() {
    const menu = page_menu_entries().find(elem => utils.has_class(elem, "active"));
    if (menu)
        utils.remove_class(menu, "active");
}


function outside_click_listener(event) {
    const menu = page_menu_entries().find(elem => utils.has_class(elem, "active"));
    if (!menu) {
        // the menu is already closed, but click handler is still in place
        remove_outside_click_listener();
        return;
    }

    const container = menu.parentElement;
    if (container.contains(event.target)) {
        // click inside the opened menu
        return;
    }

    utils.remove_class(menu, "active");
    remove_outside_click_listener();
}


function remove_outside_click_listener() {
    document.removeEventListener("click", outside_click_listener);
}


export function toggle(menu_title) {
    var menu = menu_title.nextSibling;
    if (utils.has_class(menu, "active")) {
        utils.remove_class(menu, "active");
        return;
    }

    utils.add_class(menu, "active");
    document.addEventListener("click", outside_click_listener);

    /* focus on search, if any */
    for (let input of menu.getElementsByClassName("text")) {
        input.focus();
        input.select();
        break;
    }
}


export function switch_menu(menu_title) {
    const menu = menu_title.nextSibling;
    if (utils.has_class(menu, "active")) {
        return;
    }

    const menus = page_menu_entries();
    if (!menus.some(elem => utils.has_class(elem, "active"))) {
        return;
    }

    close_active_menu();
    utils.add_class(menu, "active");
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

export function open_popup(popup_id) {
    close_active_menu();
    var popup = document.getElementById(popup_id);
    utils.add_class(popup, "active");
}

export function close_popup(a) {
    var popup = a.closest(".page_menu_popup");
    utils.remove_class(popup, "active");
}

export function toggle_suggestions() {
    var oBody = document.body;
    var open;
    if (utils.has_class(oBody, "suggestions")) {
        utils.remove_class(oBody, "suggestions");
        open = "off";
    }
    else {
        utils.add_class(oBody, "suggestions");
        open = "on";
    }
    foldable_container.persist_tree_state("suggestions", suggestions_id, open);
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

export function position_popup_filter_list(oList)
{
    let par = oList.parentNode;
    par.removeChild(oList);
    par.parentNode.parentNode.appendChild(oList);
    utils.add_simplebar_scrollbar(oList);
}

export function toggle_popup_filter_list(oList)
{
    let oTogglers = document.getElementsByClassName("add_filter");
    if (oList.style.display == "none") {
        oList.style.display = "block";
        oTogglers.forEach(oToggler=>oToggler.className += " active");
    }
    else {
        oList.style.display = "none";
        oTogglers.forEach(oToggler=>oToggler.className = oToggler.className.replace(" active", ""));
    }
}

export function toggle_filter_group_display(oFilterGroup)
{
    if (oFilterGroup.style.display == "none")
        oFilterGroup.style.display = "block";
    else
        oFilterGroup.style.display = "none";
}

export function add_filter_scroll_update()
{
    let oScrollable = document.getElementById("popup_filters_content").getElementsByClassName("simplebar-content-wrapper")[0];
    try { // scrollTo() is not supported in IE
        oScrollable.scrollTo({top: 0, left: 0, behavior: "smooth"});
    }
    catch (e) {
        oScrollable.scrollTop = 0;
    }
}

export function open_page_menu_input(pageMenuInputId)
{
    close_active_menu();
    let oPageMenuInput = document.getElementById(pageMenuInputId);
    utils.add_class(oPageMenuInput, "active");
}

export function close_page_menu_input(pageMenuInputId)
{
    let oPageMenuInput = document.getElementById(pageMenuInputId);
    utils.remove_class(oPageMenuInput, "active");
}
