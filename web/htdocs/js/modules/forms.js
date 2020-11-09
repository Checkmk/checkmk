// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import $ from "jquery";
import "select2";
import Tagify from "@yaireo/tagify";
import "element-closest-polyfill";
import Swal from "sweetalert2";

import * as utils from "utils";
import * as ajax from "ajax";

export function enable_dynamic_form_elements(container = null) {
    enable_select2_dropdowns(container);
    enable_label_input_fields(container);
}

// html.dropdown() adds the .select2-enable class for all dropdowns
// that should use the select2 powered dropdowns
export function enable_select2_dropdowns(container) {
    let elements;
    if (!container) container = $(document);

    elements = $(container).find(".select2-enable").not(".vlof_prototype .select2-enable");
    elements.select2({
        dropdownAutoWidth: true,
        minimumResultsForSearch: 5,
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

        let ajax_obj;
        let tagify_args = {
            pattern: /^[^:]+:[^:]+$/,
        };

        if (max_labels !== null) {
            tagify_args["maxTags"] = max_labels;
        }

        let tagify = new Tagify(element, tagify_args);

        tagify.on("invalid", function (e) {
            let message;
            if (e.type == "invalid" && e.detail.message == "number of tags exceeded") {
                message = "Only one tag allowed";
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

            var value = e.detail;
            tagify.settings.whitelist.length = 0; // reset the whitelist

            var post_data =
                "request=" +
                encodeURIComponent(
                    JSON.stringify({
                        search_label: value,
                        world: world,
                    })
                );

            if (ajax_obj) ajax_obj.abort();

            ajax_obj = ajax.call_ajax("ajax_autocomplete_labels.py", {
                method: "POST",
                post_data: post_data,
                response_handler: function (handler_data, ajax_response) {
                    var response = JSON.parse(ajax_response);
                    if (response.result_code != 0) {
                        console.log("Error [" + response.result_code + "]: " + response.result); // eslint-disable-line
                        return;
                    }

                    handler_data.tagify.settings.whitelist = response.result;
                    handler_data.tagify.dropdown.show.call(handler_data.tagify, handler_data.value);
                },
                handler_data: {
                    value: value,
                    tagify: tagify,
                },
            });
        });
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
// TODO: This needs to be styled to match the current user theme
export function confirm_dialog(optional_args, confirm_handler) {
    let args = utils.merge_args(
        {
            icon: "question",
            showCancelButton: true,
            confirmButtonColor: "#444",
            cancelButtonColor: "#444",
            confirmButtonText: "Yes",
            cancelButtonText: "No",
        },
        optional_args
    );

    Swal.fire(args).then(result => {
        if (result.value) {
            confirm_handler();
        }
    });
}

// Makes a form submittable after explicit confirmation
export function add_confirm_on_submit(form_id, message) {
    utils.add_event_handler(
        "submit",
        e => {
            confirm_dialog({html: message}, () => {
                document.getElementById(form_id).submit();
            });
            return utils.prevent_default_events(e);
        },
        document.getElementById(form_id)
    );
}

// Used as onclick handler on links to confirm following the link or not
export function confirm_link(url, message) {
    confirm_dialog({html: message}, () => {
        location.href = url;
    });
}
