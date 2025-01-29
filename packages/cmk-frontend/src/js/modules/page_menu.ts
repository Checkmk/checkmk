/**
 * Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
 * This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
 * conditions defined in the file COPYING, which is part of this source code package.
 */

import "element-closest-polyfill";

import $ from "jquery";

import {persist_tree_state} from "./foldable_container";
import {confirm_dialog} from "./forms";
import {close_popup as popup_menu_close_popup} from "./popup_menu";
import {
    add_class,
    add_simplebar_scrollbar_to_object,
    change_class,
    has_class,
    remove_class,
    toggle_class,
    update_url_parameter,
} from "./utils";

// Closes the active page menu dropdown
export function close_active_dropdown() {
    popup_menu_close_popup();
}

export function set_checkbox_entry(id_stem: string, checked: boolean) {
    const oEntryChecked = document.getElementById(
        "menu_entry_" + id_stem + "_checked",
    );
    const oEntryUnhecked = document.getElementById(
        "menu_entry_" + id_stem + "_unchecked",
    );

    if (checked) {
        change_class(oEntryChecked, "invisible", "visible");
        change_class(oEntryUnhecked, "visible", "invisible");
    } else {
        change_class(oEntryChecked, "visible", "invisible");
        change_class(oEntryUnhecked, "invisible", "visible");
    }
}

// Make a dropdown usable
export function enable_dropdown(id: string) {
    toggle_dropdown_enabled(id, true);
}

// Set a dropdown to be not usable (inactive)
export function disable_dropdown(id: string) {
    toggle_dropdown_enabled(id, false);
}

function toggle_dropdown_enabled(id: string, enabled: boolean) {
    const dropdown = document.getElementById("page_menu_dropdown_" + id);
    if (enabled) {
        remove_class(dropdown, "disabled");
    } else {
        add_class(dropdown, "disabled");
    }
}

export function update_down_duration_button(
    new_selection_id: string | null = null,
) {
    const active_elements = document.getElementsByClassName(
        "button duration active",
    ) as HTMLCollectionOf<HTMLElement>;
    if (active_elements) {
        for (const element of active_elements) {
            remove_class(element, "active");
        }
    }
    if (new_selection_id) {
        const target_button = document.getElementById(new_selection_id);
        if (target_button) add_class(target_button, "active");
    }
}

export function ack_problems_update_expiration_active_state(
    changed_input: HTMLInputElement,
) {
    if (changed_input.type == "checkbox") {
        // Toggle the date and time picker input fields' "active" class
        for (const what of ["date", "time"]) {
            const input_field = document.getElementById(
                what + "__ack_expire_" + what,
            ) as HTMLInputElement;
            if (input_field) toggle_class(input_field, "active", "");
        }
    } else {
        // Activate, i.e. check, the expiration checkbox
        const checkbox_input = document.getElementById(
            "cb__ack_expire",
        ) as HTMLInputElement;
        if ($(checkbox_input).prop("checked") == false) checkbox_input.click();
    }
}

export function check_menu_entry_by_checkboxes(id: string) {
    const checkboxes = document.getElementsByClassName(
        "page_checkbox",
    ) as HTMLCollectionOf<HTMLInputElement>;
    for (let i = 0; i < checkboxes.length; i++) {
        if (checkboxes[i].checked) {
            enable_menu_entry(id, true);
            return;
        }
    }
    enable_menu_entry(id, false);
}

export function enable_menu_entry(id: string, enabled: boolean) {
    let from, to;
    if (enabled) {
        from = "disabled";
        to = "enabled";
    } else {
        from = "enabled";
        to = "disabled";
    }
    const oEntry = document.getElementById("menu_entry_" + id);
    change_class(oEntry, from, to);

    if (enabled && oEntry?.getAttribute("title")) {
        oEntry.removeAttribute("title");
    }

    const oShortCut = document.getElementById("menu_shortcut_" + id);
    if (oShortCut) change_class(oShortCut, from, to);

    const oSuggestion = document.getElementById("menu_suggestion_" + id);
    if (oSuggestion) change_class(oSuggestion.parentElement, from, to);
}

export function enable_menu_entries(css_class: string, enabled: boolean) {
    const page_menu = document.getElementById("page_menu_bar");
    if (!page_menu) {
        return;
    }

    let from, to;
    if (enabled) {
        from = "disabled";
        to = "enabled";
    } else {
        from = "enabled";
        to = "disabled";
    }

    for (const element of page_menu.querySelectorAll<HTMLElement>(
        ".entry." + css_class,
    )) {
        change_class(element, from, to);
    }
}

// Toggles a PageMenuEntryPopup from a page menu entry
export function toggle_popup(popup_id: string) {
    const popup = document.getElementById(popup_id);
    const was_open = has_class(popup, "active");

    close_active_dropdown();
    close_active_popups();

    if (was_open) do_close_popup(popup!);
    else do_open_popup(popup);
}

// Opens a PageMenuEntryPopup from a page menu entry
export function open_popup(popup_id: string) {
    close_active_dropdown();
    close_active_popups();

    do_open_popup(document.getElementById(popup_id));
}

function do_open_popup(popup: HTMLElement | undefined | null | string) {
    // This prevents an exception when a view is rendered as a dashlet.
    // Since a dashlet is in an iframe, it can't access the popup_filters menu
    // The whole dashboard will do this anyway, but having no error on the
    // console and in the gui crawler is nice.
    if (
        window.location.pathname.endsWith("/check_mk/dashboard_dashlet.py") &&
        popup === "popup_filters"
    ) {
        return;
    }
    if (popup === null || popup === undefined) {
        return;
    }

    if (!(popup instanceof HTMLElement))
        throw new Error("popup should be an HTMLElement");

    add_class(popup, "active");

    // Call registered hook
    if (Object.prototype.hasOwnProperty.call(on_open, popup.id)) {
        on_open[popup.id]();
    }
}

// Closes all open PageMenuEntryPopup
function close_active_popups() {
    document
        .querySelectorAll<HTMLElement>(".page_menu_popup")
        .forEach(popup => {
            do_close_popup(popup);
        });
}

// Close a specific PageMenuEntryPopup
export function close_popup(a: HTMLAnchorElement) {
    do_close_popup(a.closest<HTMLElement>(".page_menu_popup")!);
}

function do_close_popup(popup: HTMLElement) {
    remove_class(popup, "active");

    // Call registered hook
    if (Object.prototype.hasOwnProperty.call(on_close, popup.id)) {
        on_close[popup.id]();
    }
}

const on_open: Record<string, () => void> = {} as any;
const on_close: Record<string, () => void> = {} as any;

export function register_on_open_handler(
    popup_id: string,
    handler: () => void,
) {
    on_open[popup_id] = handler;
}

export function register_on_close_handler(
    popup_id: string,
    handler: () => void,
) {
    on_close[popup_id] = handler;
}

let on_toggle_suggestions: null | (() => void) = null;

export function register_on_toggle_suggestions_handler(handler: () => void) {
    on_toggle_suggestions = handler;
}

export function toggle_suggestions() {
    const oPageMenuBar = document.getElementById("page_menu_bar");
    let open: "on" | "off";
    if (has_class(oPageMenuBar, "hide_suggestions")) {
        remove_class(oPageMenuBar, "hide_suggestions");
        open = "on";
    } else {
        add_class(oPageMenuBar, "hide_suggestions");
        open = "off";
    }
    persist_tree_state("suggestions", "all", open);

    // Call registered hook
    if (on_toggle_suggestions !== null) {
        on_toggle_suggestions();
    }
}

export function form_submit(form_name: string, button_name: string) {
    const form = document.getElementById("form_" + form_name);
    const field = document.createElement("input");
    field.type = "submit";
    field.name = button_name;
    field.value = "SET";
    field.style.display = "none";
    form?.appendChild(field);

    field.click();
}

interface ConfirmedFromSubmitOptions {
    title: string;
    html: string;
    confirmButtonText: string;
    cancelButtonText: string;
    icon: "warning" | "question";
    customClass: {
        confirmButton: "confirm_warning" | "confirm_question";
        icon: "confirm_icon confirm_warning" | "confirm_icon confirm_question";
    };
}
// Helper for building form submit links after confirming a dialog
export function confirmed_form_submit(
    form_name: string,
    button_name: string,
    options: ConfirmedFromSubmitOptions,
) {
    confirm_dialog(options, () => {
        form_submit(form_name, button_name);
    });
}

// Show / hide all entries of this group
export function toggle_popup_filter_list(
    trigger: HTMLAnchorElement,
    filter_list_id: string,
) {
    toggle_class(trigger, "active", "inactive");
    toggle_class(document.getElementById(filter_list_id), "active", "inactive");
}

export function toggle_filter_group_display(filter_group: HTMLAnchorElement) {
    toggle_class(filter_group, "active", "inactive");
}

export function on_filter_popup_open() {
    update_url_parameter("_show_filter_form", "1");
}

export function on_filter_popup_close() {
    update_url_parameter("_show_filter_form", "0");
}

// Scroll to the top after adding new filters
export function update_filter_list_scroll(filter_list_id: string) {
    const filter_list = document.getElementById(filter_list_id);
    const scrollable = filter_list!.getElementsByClassName(
        "simplebar-content-wrapper",
    )[0];
    try {
        // scrollTo() is not supported in IE
        setTimeout(() => {
            scrollable.scrollTo({top: 0, left: 0, behavior: "smooth"});
        }, 200);
    } catch (e) {
        scrollable.scrollTop = 0;
    }
}

export function side_popup_add_simplebar_scrollbar(popup_id: string) {
    const popup = document.getElementById(popup_id);
    const content = popup!.getElementsByClassName(
        "side_popup_content",
    )[0] as HTMLElement;
    add_simplebar_scrollbar_to_object(content);
}

export function inpage_search_init(
    reset_button_id: string,
    was_submitted: boolean,
) {
    const reset_button = document.getElementById(
        reset_button_id,
    ) as HTMLButtonElement;
    if (!reset_button) return;

    if (!was_submitted) {
        reset_button.disabled = true;
    }
}

export function toggle_navigation_page_menu_entry() {
    const iframe = window.frameElement;
    const hide_navigation = document.getElementById(
        "menu_entry_hide_navigation",
    )!;
    const show_navigation = document.getElementById(
        "menu_entry_show_navigation",
    )!;

    if (iframe !== null) {
        remove_class(hide_navigation, "hidden");
        add_class(show_navigation, "hidden");
    } else {
        remove_class(show_navigation, "hidden");
        add_class(hide_navigation, "hidden");
    }
}
