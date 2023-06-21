// Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import $ from "jquery";
import "select2";
import Tagify from "@yaireo/tagify";
import "element-closest-polyfill";
import Swal from "sweetalert2";

import * as utils from "utils";
import * as ajax from "ajax";
import {toggle_label_row_opacity, initialize_autocompleters} from "valuespecs";

export function enable_dynamic_form_elements(
    container: HTMLElement | null = null
) {
    enable_select2_dropdowns(container);
    enable_label_input_fields(container);
}

var g_previous_timeout_id: number | null = null;
var g_ajax_obj;

export function enable_select2_dropdowns(container) {
    let elements;
    if (!container) container = $(document);

    elements = $(container)
        .find(".select2-enable")
        .not(".vlof_prototype .select2-enable");
    elements.select2({
        dropdownAutoWidth: true,
        minimumResultsForSearch: 5,
    });
    initialize_autocompleters(container);

    // workaround for select2-input not being in focus
    $(document).on("select2:open", e => {
        (
            document.querySelector(
                ".select2-search__field"
            ) as HTMLSelectElement
        )?.focus();
        if (
            e.target.id.match("labels.*vs") &&
            e.target instanceof HTMLSelectElement
        )
            toggle_label_row_opacity(e.target, true);
    });
    $(document).on("select2:close", e => {
        if (
            e.target.id.match("labels.*vs") &&
            e.target instanceof HTMLSelectElement
        )
            toggle_label_row_opacity(e.target, false);
    });
}

function enable_label_input_fields(container) {
    if (!container) container = document;

    let elements = container.querySelectorAll("input.labels");
    elements.forEach(element => {
        // Do not tagify objects that are part of a ListOf valuespec template
        if (element.closest(".vlof_prototype") !== null) {
            return;
        }

        let max_labels = element.getAttribute("data-max-labels");
        let world = element.getAttribute("data-world");

        let tagify_args = {
            pattern: /^[^:]+:[^:]+$/,
            dropdown: {
                enabled: 1, // show dropdown on first character
                caseSensitive: false,
            },
            editTags: {
                clicks: 1, // single click to edit a tag
                keepInvalid: false, // if after editing, tag is invalid, auto-revert
            },
        };

        if (max_labels !== null) {
            tagify_args["maxTags"] = max_labels;
        }

        let tagify = new Tagify(element, tagify_args);

        // Add custom validation function that ensures that a single label key is only used once
        tagify.settings.validate = (t => {
            return add_label => {
                let label_key = add_label.value.split(":", 1)[0];
                let key_error_msg =
                    "Only one value per KEY can be used at a time.";
                if (tagify.settings.maxTags == 1) {
                    let label_type = element.getAttribute("class");
                    let existing_tags = document.querySelectorAll(
                        `.tagify.${label_type.replace(
                            " ",
                            "."
                        )} .tagify__tag-text`
                    );
                    let existing_keys_array = Array.prototype.map.call(
                        existing_tags,
                        function (x) {
                            return x.textContent.split(":")[0];
                        }
                    );

                    if (
                        existing_keys_array.includes(label_key) &&
                        !t.state.editing
                    ) {
                        return key_error_msg;
                    }
                } else {
                    for (const existing_label of t.value) {
                        // Do not check the current edited value. KEY would be
                        // always present leading to invalid value
                        if (t.state.editing) {
                            continue;
                        }
                        let existing_key = existing_label.value.split(
                            ":",
                            1
                        )[0];

                        if (label_key == existing_key) {
                            return key_error_msg;
                        }
                    }
                }
                return true;
            };
        })(tagify);

        tagify.on("invalid", function (e) {
            let message;
            if (
                e.type == "invalid" &&
                e.detail.message == "number of tags exceeded"
            ) {
                message = "Only one tag allowed";
            } else if (
                (e.type == "invalid" &&
                    e.detail.message.includes("Only one value per KEY")) ||
                e.detail.message == "already exists"
            ) {
                message =
                    "Only one value per KEY can be used at a time." +
                    e.detail.data.value +
                    " is already used.";
            } else {
                message =
                    "Labels need to be in the format <tt>[KEY]:[VALUE]</tt>. For example <tt>os:windows</tt>.</div>";
            }

            $("div.label_error").remove(); // Remove all previous errors

            // Print a validation error message
            var msg = document.createElement("div");
            msg.classList.add("message", "error", "label_error");

            msg.innerHTML = message;
            element.parentNode.insertBefore(msg, element.nextSibling);
        });

        tagify.on("add", function () {
            $("div.label_error").remove(); // Remove all previous errors
        });

        // Realize the auto completion dropdown field by using an ajax call
        tagify.on("input", function (e) {
            $("div.label_error").remove(); // Remove all previous errors

            var value = e.detail.value;
            tagify.settings.whitelist.length = 0; // reset the whitelist

            // show loading animation and hide the suggestions dropdown
            tagify.loading(true).dropdown.hide.call(tagify);

            var post_data =
                "request=" +
                encodeURIComponent(
                    JSON.stringify({
                        ident: "label",
                        value: value,
                        params: {world: world},
                    })
                );

            if (g_previous_timeout_id !== null) {
                clearTimeout(g_previous_timeout_id);
            }
            g_previous_timeout_id = window.setTimeout(function () {
                kill_previous_autocomplete_call();
                ajax_call_autocomplete_labels(
                    post_data,
                    tagify,
                    value,
                    element
                );
            }, 300);
        });
    });
}

function kill_previous_autocomplete_call() {
    if (g_ajax_obj) {
        g_ajax_obj.abort();
        g_ajax_obj = null;
    }
}

function ajax_call_autocomplete_labels(post_data, tagify, value, element) {
    g_ajax_obj = ajax.call_ajax("ajax_vs_autocomplete.py", {
        method: "POST",
        post_data: post_data,
        response_handler: function (handler_data, ajax_response) {
            var response = JSON.parse(ajax_response);
            if (response.result_code != 0) {
                console.log(
                    "Error [" + response.result_code + "]: " + response.result
                ); // eslint-disable-line
                return;
            }

            let result_objects: Object[] = [];
            response.result.choices.forEach((entry: string[]) => {
                result_objects.push({value: entry[1]});
            });

            handler_data.tagify.settings.whitelist.splice(
                10,
                response.result.length,
                ...result_objects
            );
            // render the suggestions dropdown
            handler_data.tagify.loading(false);
            handler_data.tagify.dropdown.show.call(
                handler_data.tagify,
                handler_data.value
            );

            let tagify__input =
                element?.parentElement?.querySelector(".tagify__input");
            if (tagify__input) {
                let max = value.length;
                handler_data.tagify.suggestedListItems.forEach(entry => {
                    max = Math.max(entry.value.length, max);
                });
                let fontSize = parseInt(
                    window
                        .getComputedStyle(tagify__input, null)
                        .getPropertyValue("font-size")
                );
                // Minimum width set by tagify
                let size = Math.max(110, max * (fontSize / 2 + 1));
                tagify__input.style.width = size.toString() + "px";
                tagify__input.parentElement.style.width =
                    (size + 10).toString() + "px";
            }
        },
        handler_data: {
            value: value,
            tagify: tagify,
        },
    });
}

// Handle Enter key in textfields
export function textinput_enter_submit(e, submit) {
    if (!e) e = window.event;

    var keyCode = e.which || e.keyCode;
    if (keyCode == 13) {
        if (submit) {
            var button = document.getElementById(submit);
            if (button) button.click();
        }
        return utils.prevent_default_events(e);
    }
}

// Helper function to display nice popup confirm dialogs
export function confirm_dialog(optional_args, confirm_handler) {
    const default_custom_class_args = {
        title: "confirm_title",
        container: "confirm_container",
        popup: "confirm_popup",
        content: "confirm_content",
        htmlContainer: "confirm_content",
        actions: "confirm_actions",
        icon: "confirm_icon",
        confirmButton: "hot",
    };

    let custom_class_args;
    if ("customClass" in optional_args) {
        custom_class_args = {
            ...default_custom_class_args,
            ...optional_args["customClass"],
        };
        delete optional_args["customClass"];
    } else {
        custom_class_args = default_custom_class_args;
    }

    const default_args = {
        // https://sweetalert2.github.io/#configuration
        target: "#page_menu_popups",
        position: "top-start",
        grow: "row",
        allowOutsideClick: false,
        backdrop: false,
        showClass: {
            popup: "",
            backdrop: "",
        },
        hideClass: {
            popup: "",
            backdrop: "",
        },
        buttonsStyling: false,
        showCancelButton: true,
        confirmButtonText: "Yes",
        cancelButtonText: "No",
        icon: "question",
        customClass: custom_class_args,
    };

    let args = {
        ...default_args,
        ...optional_args,
    };

    Swal.fire(args).then(result => {
        if (confirm_handler && result.value) {
            confirm_handler();
        }
    });
}

// Makes a form submittable after explicit confirmation
export function add_confirm_on_submit(form_id, message) {
    let form = document.getElementById(form_id);
    if (form instanceof HTMLElement) {
        form.addEventListener("submit", e => {
            confirm_dialog({html: message}, () => {
                (document.getElementById(form_id) as HTMLFormElement)?.submit();
            });
            return utils.prevent_default_events(e!);
        });
    } else
        throw new Error(
            `Can not add confirm on submit: The Form with the id ${form_id} does not exist`
        );
}

// Used as onclick handler on links to confirm following the link or not
export function confirm_link(url, message, custom_args) {
    confirm_dialog({html: message, ...custom_args}, () => {
        location.href = url;
    });
}

// On submit of the filter form (filter popup), remove unnecessary HTTP variables
export function on_filter_form_submit_remove_vars(form_id) {
    const form = document.getElementById(form_id) as HTMLFormElement;
    _remove_listof_vars(form);
}

function _remove_listof_vars(form: HTMLFormElement) {
    const rm_classes: string[] = ["vlof_prototype", "orig_index"];
    for (const rm_class of rm_classes) {
        const elements: HTMLCollection = form.getElementsByClassName(rm_class);
        while (elements.length > 0) {
            elements[0].parentNode!.removeChild(elements[0]);
        }
    }
}

export function replace_error_msg_with_confirm_dialog() {
    const dialog = document.getElementsByClassName(
        "really"
    )[0] as HTMLDivElement;
    const error_msg = document.getElementsByClassName(
        "error"
    )[0] as HTMLDivElement;

    error_msg.replaceWith(dialog);
    utils.remove_class(dialog, "hidden");
}

export function add_filter_form_error_listener(elem_id: string) {
    const elem = document.getElementById(elem_id) as HTMLElement;
    if (!elem) return;

    const observer = new MutationObserver(() => {
        // Disable the form submit button if there are any errors
        const errors: HTMLCollection = elem.getElementsByClassName("error");
        const submit_button = document.getElementById(
            "_apply"
        )! as HTMLInputElement;
        if (errors.length > 0) {
            submit_button.disabled = true;
        } else {
            submit_button.disabled = false;
        }
    });

    observer.observe(elem, {childList: true, subtree: true});
}
