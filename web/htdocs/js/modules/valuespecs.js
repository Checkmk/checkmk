// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import {set} from "lodash";
import $ from "jquery";
import * as utils from "utils";
import * as popup_menu from "popup_menu";
import * as ajax from "ajax";
import * as forms from "forms";
import * as colorpicker from "colorpicker";
import * as d3 from "d3";

//#   +--------------------------------------------------------------------+
//#   | Functions needed by HTML code from ValueSpec (valuespec.py)        |
//#   '--------------------------------------------------------------------'

export function toggle_option(oCheckbox, divid, negate) {
    var oDiv = document.getElementById(divid);
    if ((oCheckbox.checked && !negate) || (!oCheckbox.checked && negate)) oDiv.style.display = "";
    else oDiv.style.display = "none";
}

export function toggle_dropdown(oDropdown, divid) {
    var oDiv = document.getElementById(divid);
    if (oDropdown.value == "other") oDiv.style.display = "";
    else oDiv.style.display = "none";
}

export function toggle_tag_dropdown(oDropdown, divid) {
    var oDiv = document.getElementById(divid);
    if (oDropdown.value == "ignore") oDiv.style.display = "none";
    else oDiv.style.display = "";
}

/* This function is called after the table with of input elements
   has been rendered. It attaches the onFocus-function to the last
   of the input elements. That function will append another
   input field as soon as the user focusses the last field. */
export function list_of_strings_init(divid, split_on_paste, split_separators) {
    var container = document.getElementById(divid);
    var children = container.getElementsByTagName("div");
    var last_input = children[children.length - 1].getElementsByTagName("input")[0];
    if (!last_input) last_input = children[children.length - 1].getElementsByTagName("select")[0];
    list_of_strings_add_event_handlers(last_input, split_on_paste, split_separators);
}

function list_of_strings_add_event_handlers(input, split_on_paste, split_separators) {
    var handler_func = function () {
        if (this.value != "") {
            return list_of_strings_extend(this, split_on_paste, split_separators);
        }
    };
    let new_entries_from_event = e => {
        // Get pasted data via clipboard API
        var clipboard_data = e.clipboardData || window.clipboardData;
        var pasted = clipboard_data.getData("Text");

        // When pasting a string, trim separators and then split by the given separators
        var stripped = pasted.replace(
            new RegExp("^[" + split_separators + "]+|[" + split_separators + "]+$", "g"),
            ""
        );
        return stripped.split(new RegExp("[" + split_separators + "]+"));
    };

    let setup_new_entries = (anchor, event) => {
        let entries = new_entries_from_event(event);
        let last_input = anchor;
        // Add splitted parts to the input fields
        entries.forEach((entry, i) => {
            // Put the first item to the current field
            if (i != 0) last_input = list_of_strings_add_new_field(last_input);

            if (last_input.tagName == "INPUT") last_input.value = entry;
            else set_select2_element(last_input, entry);
        });

        // Focus the last populated field
        last_input.focus();
        // And finally add a new empty field to the end (with attached handlers)
        list_of_strings_extend(last_input, split_on_paste, split_separators);

        // Stop original data actually being pasted
        return utils.prevent_default_events(event);
    };

    if (input.tagName == "INPUT") {
        input.onfocus = handler_func;
        input.oninput = handler_func;

        if (split_on_paste) {
            input.onpaste = function (event) {
                if (this.value != "") return true; // The field had a value before: Don't do custom stuff
                return setup_new_entries(this, event);
            };
        }
    } else {
        $(input).on("select2:select", handler_func);

        if (split_on_paste) {
            $(input).on("select2:open", ee => {
                let search_field = $(".select2-search input");
                search_field.on("paste", event => {
                    if (search_field.val() != "") return true; // The field had a value before: Don't do custom stuff
                    return setup_new_entries(input, event.originalEvent);
                });
            });
        }
    }
}

function list_of_strings_remove_event_handlers(input) {
    if (input.tagName == "INPUT") {
        input.oninput = null;
        input.onfocus = null;
        input.onpaste = null;
    } else {
        $(input).off("select2:select");
        $(input).off("select2:open");
    }
}

/* Is called when the last input field in a ListOfString gets focus.
   In that case a new input field is being appended. */
function list_of_strings_extend(input, split_on_paste, split_separators) {
    var new_input = list_of_strings_add_new_field(input);

    /* Move focus function from old last to new last input field */
    list_of_strings_add_event_handlers(new_input, split_on_paste, split_separators);
    list_of_strings_remove_event_handlers(input);
}

export function list_of_strings_add_new_field(input) {
    /* The input field has a unique name like "extra_emails_2" for the field with
       the index 2. We need to convert this into "extra_emails_3". */

    var old_name = input.name;
    var splitted = old_name.split("_");
    var num = 1 + parseInt(splitted[splitted.length - 1]);
    splitted[splitted.length - 1] = "" + num;
    var new_name = splitted.join("_");

    /* Now create a new <div> element as a copy from the current one and
       replace this name. We do this by simply copying the HTML code. The
       last field is always empty. Remember: ListOfStrings() always renders
       one exceeding empty element. */

    var div = input.parentNode;
    while (div.parentNode.classList && !div.parentNode.classList.contains("listofstrings"))
        div = div.parentNode;
    var container = div.parentNode;

    let tagtype = input.tagName == "INPUT" ? "input" : "select";
    let new_div = document.createElement("DIV");
    if (input.tagName == "INPUT") {
        new_div.innerHTML = div.innerHTML.replace('"' + old_name + '"', '"' + new_name + '"');
        // IE7 does not have quotes in innerHTML, trying to workaround this here.
        new_div.innerHTML = new_div.innerHTML.replace("=" + old_name + " ", "=" + new_name + " ");
        new_div.innerHTML = new_div.innerHTML.replace("=" + old_name + ">", "=" + new_name + ">");
    } else {
        // shallow because select2 ands dynamically some spans with form_elements
        let new_select = input.cloneNode();
        new_select.name = new_name;
        new_select.id = new_name;
        delete new_select.dataset.select2Id;
        new_div.appendChild(new_select);
    }
    forms.enable_dynamic_form_elements(new_div);
    container.appendChild(new_div);

    return new_div.getElementsByTagName(tagtype)[0];
}

let cascading_sub_valuespec_parameters = {};

export function add_cascading_sub_valuespec_parameters(varprefix, parameters) {
    cascading_sub_valuespec_parameters[varprefix] = parameters;
}

export function cascading_change(oSelect, varprefix, count) {
    var nr = parseInt(oSelect.value);

    for (var i = 0; i < count; i++) {
        var vp = varprefix + "_" + i;
        var container = document.getElementById(vp + "_sub");
        if (!container) continue;

        container.style.display = nr == i ? "" : "none";

        // In case the rendering has been postponed for this cascading
        // valuespec ask the configured AJAX page for rendering the sub
        // valuespec input elements
        if (
            nr == i &&
            container.childElementCount == 0 &&
            cascading_sub_valuespec_parameters.hasOwnProperty(vp)
        ) {
            show_cascading_sub_valuespec(vp, cascading_sub_valuespec_parameters[vp]);
        }
    }
}

function show_cascading_sub_valuespec(varprefix, parameters) {
    var post_data = "request=" + encodeURIComponent(JSON.stringify(parameters["request_vars"]));

    ajax.call_ajax(parameters["page_name"] + ".py", {
        method: "POST",
        post_data: post_data,
        response_handler: function (handler_data, ajax_response) {
            var response = JSON.parse(ajax_response);
            if (response.result_code != 0) {
                console.log("Error [" + response.result_code + "]: " + response.result); // eslint-disable-line
                return;
            }

            var container = document.getElementById(handler_data.varprefix + "_sub");
            container.innerHTML = response.result.html_code;

            utils.execute_javascript_by_object(container);
            forms.enable_dynamic_form_elements(container);
        },
        handler_data: {
            varprefix: varprefix,
        },
    });
}

export function textarea_resize(oArea) {
    oArea.style.height = oArea.scrollHeight - 6 + "px";
}

export function listof_add(varprefix, magic, style) {
    var count_field = document.getElementById(varprefix + "_count");
    var count = parseInt(count_field.value);
    var str_count = "" + (count + 1);
    count_field.value = str_count;

    var html_code = listof_get_new_entry_html_code(varprefix, magic, str_count);
    var container = document.getElementById(varprefix + "_container");

    var new_child;
    var tmp_container = document.createElement("div");
    if (style == "floating") {
        tmp_container.innerHTML = html_code;
        new_child = tmp_container.children[0];
    } else {
        // Hack for IE. innerHTML does not work correctly directly on tbody/tr
        tmp_container.innerHTML = "<table><tbody>" + html_code + "</tbody></tr>";
        new_child = tmp_container.children[0].children[0].children[0]; // TR
    }

    container.appendChild(new_child);
    utils.execute_javascript_by_object(new_child);
    forms.enable_dynamic_form_elements(new_child);

    listof_update_indices(varprefix);
}

function listof_get_new_entry_html_code(varprefix, magic, str_count) {
    var oPrototype = document.getElementById(varprefix + "_prototype");
    var html_code = oPrototype.innerHTML;
    // replace the magic
    var re = new RegExp(magic, "g");
    html_code = html_code.replace(re, str_count);

    // in some cases the magic might be URL encoded. Also replace these occurences.
    re = new RegExp(encodeURIComponent(magic).replace("!", "%21"), "g");

    return html_code.replace(re, str_count);
}

export function listof_delete(varprefix, nr) {
    var entry = document.getElementById(varprefix + "_entry_" + nr);
    entry.parentNode.removeChild(entry);
    listof_update_indices(varprefix);
}

export function listof_drop_handler(handler_args) {
    var varprefix = handler_args.varprefix;
    var cur_index = handler_args.cur_index;

    var indexof = document.getElementsByName(varprefix + "_indexof_" + cur_index);
    if (indexof.length == 0) throw "Failed to find the indexof_fied";
    indexof = indexof[0];

    // Find the tbody parent of the given tag type
    var tbody = indexof;
    while (tbody && tbody.tagName != "TBODY") tbody = tbody.parentNode;

    if (!tbody) throw "Failed to find the tbody element of " + indexof;

    listof_update_indices(varprefix);
}

export function listof_sort(varprefix, magic, sort_by) {
    var tbody = document.getElementById(varprefix + "_container");
    var rows = tbody.rows;

    var entries = [],
        i,
        td,
        sort_field_name,
        fields;
    for (i = 0; i < rows.length; i++) {
        // Find the index of this row
        td = rows[i].cells[0]; /* TD with buttons */
        if (td.children.length == 0) continue;
        var index = td.getElementsByClassName("orig_index")[0].value;

        sort_field_name = varprefix + "_" + index + "_" + sort_by;

        // extract the sort field value and add it to the entries list
        // together with the row to be moved
        fields = document.getElementsByName(sort_field_name);
        if (fields.length == 0) {
            return; // abort sorting
        }

        entries.push({
            sort_value: fields[0].value,
            row_node: rows[i],
        });
    }

    entries.sort(function (a, b) {
        if (a.sort_value.toLowerCase() < b.sort_value.toLowerCase()) {
            return -1;
        }
        if (a.sort_value.toLowerCase() > b.sort_value.toLowerCase()) {
            return 1;
        }
        return 0;
    });

    // Remove all rows from the list and then add the rows back to it
    // in sorted order

    while (tbody.firstChild) {
        tbody.removeChild(tbody.firstChild);
    }

    for (i = 0; i < entries.length; i++) {
        tbody.appendChild(entries[i].row_node);
    }

    listof_update_indices(varprefix);
}

export function listof_update_indices(varprefix) {
    var container = document.getElementById(varprefix + "_container");

    for (var i = 0; i < container.children.length; i++) {
        var child_node = container.children[i];
        var index = child_node.getElementsByClassName("index")[0];
        if (index.value === "") {
            // initialization of recently added row
            var orig_index = child_node.getElementsByClassName("orig_index")[0];
            orig_index.value = "" + (i + 1);
        }
        index.value = "" + (i + 1);
    }
}

export function list_choice_toggle_all(varprefix) {
    var tbl = document.getElementById(varprefix + "_tbl");
    var checkboxes = tbl.getElementsByTagName("input");
    if (!checkboxes) return;

    // simply use state of first texbox as base
    var state = !checkboxes[0].checked;
    for (var i = 0; i < checkboxes.length; i++) {
        checkboxes[i].checked = state;
    }
}

export function rule_comment_prefix_date_and_user(img, text) {
    var container = img.parentNode.parentNode;
    var textarea = container.getElementsByTagName("textarea")[0];

    if (!textarea) {
        //console.log("Failed to find textarea object");
        return;
    }

    textarea.value = text + "\n" + textarea.value;
    textarea.focus();
    textarea.setSelectionRange(text.length, text.length);
}

export function passwordspec_randomize(img, pwlen) {
    var a,
        c,
        password = "";
    while (password.length < pwlen) {
        a = parseInt(Math.random() * 128);
        if ((a >= 97 && a <= 122) || (a >= 65 && a <= 90) || (a >= 48 && a <= 57)) {
            c = String.fromCharCode(a);
            password += c;
        }
    }
    var oInput = img.previousElementSibling;
    if (oInput.tagName != "INPUT") oInput = oInput.children[0]; // in complain mode
    oInput.value = password;
}

export function toggle_hidden(img) {
    var oInput = img;
    while (oInput.tagName != "INPUT") oInput = oInput.previousElementSibling;
    if (oInput.type == "text") {
        oInput.type = "password";
    } else {
        oInput.type = "text";
    }
}

export function duallist_enlarge(field_suffix, varprefix) {
    var field = document.getElementById(varprefix + "_" + field_suffix);
    var other_id;
    if (field.id != varprefix + "_selected") {
        // The other field is the one without "_unselected" suffix
        other_id = varprefix + "_selected";
    } else {
        // The other field is the one with "_unselected" suffix
        other_id = varprefix + "_unselected";
    }

    var other_field = document.getElementById(other_id);
    if (!other_field) return;

    utils.remove_class(other_field, "large");
    utils.add_class(other_field, "small");
    utils.remove_class(field, "small");
    utils.add_class(field, "large");
}

export function duallist_switch(field_suffix, varprefix, keeporder) {
    var field = document.getElementById(varprefix + "_" + field_suffix);
    var other_id, positive;
    if (field.id != varprefix + "_selected") {
        // The other field is the one without "_unselected" suffix
        other_id = varprefix + "_selected";
        positive = true;
    } else {
        // The other field is the one with "_unselected" suffix
        other_id = varprefix + "_unselected";
        positive = false;
    }

    var other_field = document.getElementById(other_id);
    if (!other_field) return;

    var helper = document.getElementById(varprefix);
    if (!helper) return;

    // Move the selected options to the other select field
    var selected = [],
        i;
    for (i = 0; i < field.options.length; i++) {
        if (field.options[i].selected) {
            selected.push(field.options[i]);
        }
    }
    if (selected.length == 0) return; // when add/remove clicked, but none selected

    // Now loop over all selected elements and add them to the other field
    for (i = 0; i < selected.length; i++) {
        // remove option from origin
        field.removeChild(selected[i]);
        other_field.appendChild(selected[i]);

        selected[i].selected = false;
    }

    // Determine the correct child to insert. If keeporder is being set,
    // then new elements will aways be appended. That way the user can
    // create an order of his choice. This is being used if DualListChoice
    // has the option custom_order = True
    if (!keeporder) {
        var collator = new Intl.Collator(undefined, {numeric: true, sensitivity: "base"});
        sort_select(other_field, collator.compare);
    }

    // Update internal helper field which contains a list of all selected keys
    var pos_field = positive ? other_field : field;

    var texts = [];
    for (i = 0; i < pos_field.options.length; i++) {
        texts.push(pos_field.options[i].value);
    }
    helper.value = texts.join("|");
}

function sort_select(select, cmp_func) {
    var choices = [],
        i;
    for (i = 0; i < select.options.length; i++) {
        choices[i] = [];
        choices[i][0] = select.options[i].text;
        choices[i][1] = select.options[i].value;
        choices[i][2] = select.options[i].disabled;
    }

    choices.sort(cmp_func);
    while (select.options.length > 0) {
        select.options[0] = null;
    }

    for (i = 0; i < choices.length; i++) {
        var op = new Option(choices[i][0], choices[i][1]);
        op.disabled = choices[i][2];
        select.options[i] = op;
    }

    return;
}

export function iconselector_select(event, varprefix, value) {
    // set value of valuespec
    const obj = document.getElementById(varprefix + "_value");
    obj.value = value;

    const src_img = document.getElementById(varprefix + "_i_" + value);

    // Set the new choosen icon in the valuespecs image
    let img = document.getElementById(varprefix + "_img");
    img.src = src_img.src;

    popup_menu.close_popup();
}

export function iconselector_toggle(varprefix, category_name) {
    // Update the navigation
    var nav_links = document.getElementsByClassName(varprefix + "_nav");
    var i;
    for (i = 0; i < nav_links.length; i++) {
        if (nav_links[i].id == varprefix + "_" + category_name + "_nav")
            utils.add_class(nav_links[i].parentNode, "active");
        else utils.remove_class(nav_links[i].parentNode, "active");
    }

    // Now update the category containers
    var containers = document.getElementsByClassName(varprefix + "_container");
    for (i = 0; i < containers.length; i++) {
        if (containers[i].id == varprefix + "_" + category_name + "_container")
            containers[i].style.display = "";
        else containers[i].style.display = "none";
    }
}

export function iconselector_toggle_names(event, varprefix) {
    var icons = document.getElementById(varprefix + "_icons");
    if (utils.has_class(icons, "show_names")) utils.remove_class(icons, "show_names");
    else utils.add_class(icons, "show_names");
}

export function listofmultiple_add(varprefix, choice_page_name, page_request_vars, trigger) {
    let ident;
    if (trigger) {
        // trigger given: Special case for ViewFilterList style choice rendering
        ident = trigger.id.replace(varprefix + "_add_", "");
        utils.add_class(trigger, "disabled");
    } else {
        let choice = document.getElementById(varprefix + "_choice");
        ident = choice.value;

        if (ident == "") return;

        trigger = choice.options[choice.selectedIndex];

        // disable this choice in the "add choice" select field
        trigger.disabled = true;
    }

    var request = {
        varprefix: varprefix,
        ident: ident,
    };

    // Add given valuespec specific request vars
    for (var prop in page_request_vars) {
        if (page_request_vars.hasOwnProperty(prop)) {
            request[prop] = page_request_vars[prop];
        }
    }

    var post_data = "request=" + encodeURIComponent(JSON.stringify(request));

    ajax.call_ajax(choice_page_name + ".py", {
        method: "POST",
        post_data: post_data,
        handler_data: {
            trigger: trigger,
            ident: ident,
        },
        response_handler: function (handler_data, ajax_response) {
            var table = document.getElementById(varprefix + "_table");
            var tbody = table.getElementsByTagName("tbody")[0];

            var response = JSON.parse(ajax_response);
            if (response.result_code != 0) {
                console.log("Error [" + response.result_code + "]: " + response.result); // eslint-disable-line
                return;
            }

            let ident = handler_data.ident;
            // Update select2 to make the disabled attribute be recognized by the dropdown
            // (See https://github.com/select2/select2/issues/3347)
            let choice = document.getElementById(varprefix + "_choice");
            if (choice) {
                let choice_select2 = $(choice).select2();
                // Unselect the chosen option
                choice_select2.val(null).trigger("change");
            }

            var tmp_container = document.createElement("tbody");
            tmp_container.innerHTML = response.result.html_code;
            var new_row = tmp_container.childNodes[0];
            if (new_row.tagName != "TR") {
                console.log("Error: Invalid choice HTML code: " + response.result.html_code); // eslint-disable-line
                return;
            }

            tbody.insertBefore(new_row, tbody.firstChild);
            forms.enable_dynamic_form_elements(new_row);
            utils.execute_javascript_by_object(new_row);

            // Add it to the list of active elements
            var active = document.getElementById(varprefix + "_active");
            if (active.value != "") active.value += ";" + ident;
            else active.value = ident;

            // Put in a line break following the table if the added row is the first
            if (tbody.childNodes.length == 1)
                table.parentNode.insertBefore(document.createElement("br"), table.nextSibling);

            // Enable the reset button
            let reset_button = document.getElementById(varprefix + "_reset");
            if (reset_button) reset_button.disabled = false;
        },
    });
}

export function listofmultiple_del(varprefix, ident) {
    // make the filter invisible
    var row = document.getElementById(varprefix + "_" + ident + "_row");
    var tbody = row.parentNode;
    tbody.removeChild(row);

    // Make it choosable from the dropdown field again
    var choice = document.getElementById(varprefix + "_choice");
    if (choice) {
        var i;
        for (i = 0; i < choice.options.length; i++)
            if (choice.options[i].value == ident) choice.options[i].disabled = false;

        // Update select2 to make the disabled attribute be recognized by the dropdown
        // (See https://github.com/select2/select2/issues/3347)
        $(choice).select2();
    } else {
        // trigger given: Special case for ViewFilterList style choice rendering
        choice = document.getElementById(varprefix + "_add_" + ident);
        utils.remove_class(choice, "disabled");
    }

    // Remove it from the list of active elements
    var active = document.getElementById(varprefix + "_active");
    var l = active.value.split(";");
    for (i = 0; i < l.length; i++) {
        if (l[i] == ident) {
            l.splice(i, 1);
            break;
        }
    }
    active.value = l.join(";");

    // Remove the line break following the table if the deleted row was the last
    if (tbody.childNodes.length == 0) {
        var table = document.getElementById(varprefix + "_table");
        var br = table.nextSibling;
        if (br.nodeName == "BR") br.parentNode.removeChild(br);
    }

    // Enable the reset button
    let reset_button = document.getElementById(varprefix + "_reset");
    if (reset_button) reset_button.disabled = false;
}

export function listofmultiple_init(varprefix, was_submitted) {
    var table = document.getElementById(varprefix + "_table");
    var tbody = table.getElementsByTagName("tbody")[0];

    let choice_field = document.getElementById(varprefix + "_choice");
    if (choice_field) choice_field.value = "";

    listofmultiple_disable_selected_options(varprefix);
    // Put in a line break following the table if it's not empty
    if (tbody.childNodes.length >= 1)
        table.parentNode.insertBefore(document.createElement("br"), table.nextSibling);

    // Disable the reset button if the form was not submitted yet
    let reset_button = document.getElementById(varprefix + "_reset");
    if (reset_button && !was_submitted) {
        reset_button.disabled = true;
    }
}

// The <option> elements in the <select> field of the currently chosen
// elements need to be disabled.
function listofmultiple_disable_selected_options(varprefix) {
    let active = document.getElementById(varprefix + "_active");
    if (active.value == "") {
        return;
    }

    let active_choices = active.value.split(";");
    let choice_field = document.getElementById(varprefix + "_choice");
    let i;
    if (choice_field) {
        for (i = 0; i < choice_field.options.length; i++) {
            if (active_choices.indexOf(choice_field.options[i].value) !== -1) {
                choice_field.options[i].disabled = true;
            }
        }
    } else {
        // trigger given: Special case for ViewFilterList style choice rendering
        let choice;
        for (i = 0; i < active_choices.length; i++) {
            choice = document.getElementById(varprefix + "_add_" + active_choices[i]);
            utils.add_class(choice, "disabled");
        }
    }
}

function set_select2_element(elem, value) {
    if (!value || value == "null") return;
    let newval = new Option(value, value, false, true);
    $(elem).append(newval).trigger("change");
}

function hook_select2_hint(elem, source_id) {
    let source_field = $(source_id);
    if (!source_field) return;
    set_select2_element(elem, source_field.val()); // page initialization
    source_field.on("change", () => set_select2_element(elem, source_field.val()));
}

let dynamicParamsCallbacks = {
    nop(autocompleter, elem) {
        return {
            ...autocompleter.params,
        };
    },
    tag_group_options_autocompleter(autocompleter, elem) {
        return {
            group_id: document.getElementById(elem.id.replace(/_val$/, "_grp")).value,
            ...autocompleter.params,
        };
    },
    host_and_service_hinted_autocompleter(autocompleter, elem) {
        // fetch metrics, filtered by hostname and service from another input field
        // DropdownChoiceWithHostAndServiceHints
        let obj = {};
        let hint = document.getElementById(`${elem.id}_hostname_hint`).value;
        if (hint) {
            set(obj, "context.host.host", hint);
        }
        hint = document.getElementById(`${elem.id}_service_hint`).value;
        if (hint) {
            set(obj, "context.service.service", hint);
        }

        return {
            ...obj,
            ...autocompleter.params,
        };
    },
    host_hinted_autocompleter(autocompleter, elem) {
        // fetch services, filtered by host name of another input field
        let host_id = elem.id.endsWith("_service_hint")
            ? `${elem.id.slice(0, -13)}_hostname_hint`
            : "context_host_p_host";
        let val_or_empty = obj => (obj ? {host: {host: obj.value}} : {});

        return {
            context: val_or_empty(document.getElementById(host_id)),
            ...autocompleter.params,
        };
    },
};

function ajax_autocomplete_request(value, elem, autocompleter) {
    let callback = dynamicParamsCallbacks[autocompleter.dynamic_params_callback_name || "nop"];
    return (
        "request=" +
        encodeURIComponent(
            JSON.stringify({
                ident: autocompleter.ident,
                params: callback(autocompleter, elem),
                value: value,
            })
        )
    );
}

function select2_ajax_vs_autocomplete(elem, autocompleter) {
    let value = term =>
        term.term !== undefined
            ? term.term
            : ["hostname", "service"].find(el => autocompleter.ident.includes(el))
            ? elem.value
            : "";

    return {
        url: "ajax_vs_autocomplete.py",
        delay: 250,
        type: "POST",
        data: term => ajax_autocomplete_request(value(term), elem, autocompleter),
        processResults: resp => ({
            results: resp.result.choices.map(x => ({
                id: x[0],
                text: x[1],
                disabled: x[0] === null, // Reached max limit message non selectable
            })),
        }),
    };
}

function select2_vs_autocomplete(container) {
    $(container)
        .find("select.ajax-vals")
        .each((i, elem) => {
            let autocompleter = JSON.parse(elem.dataset.autocompleter);

            console.log(autocompleter);

            // TODO: move placeholder_title to python autocompleter config!
            let field_element =
                ["hostname", "service", "metric", "graph"].find(el =>
                    autocompleter.ident.includes(el)
                ) || "item";
            let placeholder_title = `(Select ${field_element})`;
            if (autocompleter.ident === "wato_folder_choices")
                placeholder_title = "(Select target folder)";

            $(elem)
                .select2({
                    width: "style",
                    allowClear: true,
                    placeholder: placeholder_title,
                    ajax: select2_ajax_vs_autocomplete(elem, autocompleter),
                })
                .on("select2:open", () => {
                    if (["hostname", "service"].includes(field_element))
                        $(".select2-search input").val(elem.value);
                });

            if (elem.id.endsWith("_hostname_hint")) hook_select2_hint(elem, "#context_host_p_host");

            if (elem.id.endsWith("_service_hint"))
                hook_select2_hint(elem, "#context_service_p_service");

            // CustomGraph editor clearing
            if (elem.id.endsWith(`_metric_${field_element}_hint`)) {
                let tail = field_element.length + 6;
                let metric_field_id = `#${elem.id.slice(0, -tail)}`;
                $(elem).on("change.select2", () => {
                    $(metric_field_id).empty();
                    if (field_element === "hostname") $(metric_field_id + "_service_hint").empty();
                });
            }

            // Query set value. Horrible Select2 default options query
            if (elem.value !== "") {
                let term = elem.value;
                $.ajax({
                    type: "POST",
                    url: "ajax_vs_autocomplete.py",
                    data: ajax_autocomplete_request(term, elem, autocompleter),
                }).then(data => {
                    let pick = data.result.choices.find(el => el[0] === term);
                    if (pick) {
                        let option = new Option(pick[1], pick[0], true, true);
                        $(elem).empty().append(option).trigger("change");
                    }
                });
            }
        });
}

export function initialize_autocompleters(container) {
    select2_vs_autocomplete(container);
}

var vs_color_pickers = [];

export function add_color_picker(varprefix, value) {
    vs_color_pickers[varprefix] = colorpicker.ColorPicker(
        document.getElementById(varprefix + "_picker"),
        function (hex) {
            update_color_picker(varprefix, hex, false);
        }
    );

    document.getElementById(varprefix + "_input").oninput = function () {
        update_color_picker(varprefix, this.value, true);
    };

    update_color_picker(varprefix, value, true);
}

function update_color_picker(varprefix, hex, update_picker) {
    if (!/^#[0-9A-F]{6}$/i.test(hex)) return; // skip invalid/unhandled colors

    document.getElementById(varprefix + "_input").value = hex;
    document.getElementById(varprefix + "_value").value = hex;
    document.getElementById(varprefix + "_preview").style.backgroundColor = hex;

    if (update_picker) vs_color_pickers[varprefix].setHex(hex);
}

export function visual_filter_list_reset(varprefix, page_request_vars, page_name, reset_ajax_page) {
    let request = {
        varprefix: varprefix,
        page_request_vars: page_request_vars,
        page_name: page_name,
    };
    const post_data = "request=" + encodeURIComponent(JSON.stringify(request));

    ajax.call_ajax(reset_ajax_page + ".py", {
        method: "POST",
        post_data: post_data,
        handler_data: {
            varprefix: varprefix,
        },
        response_handler: function (handler_data, ajax_response) {
            let response = JSON.parse(ajax_response);
            const filters_html = response.result.filters_html;
            let filter_list = document.getElementById(varprefix + "_popup_filter_list_selected");
            filter_list.getElementsByClassName("simplebar-content")[0].innerHTML = filters_html;
            utils.add_simplebar_scrollbar(varprefix + "_popup_filter_list");
            listofmultiple_disable_selected_options(varprefix);
            forms.enable_dynamic_form_elements();
        },
    });

    // Disable the reset button
    let reset_button = document.getElementById(varprefix + "_reset");
    reset_button.disabled = true;
}

export function update_unit_selector(selectbox, metric_prefix) {
    let change_unit_to_match_metric = metric => {
        const post_data = "request=" + encodeURIComponent(JSON.stringify({metric: metric}));
        ajax.call_ajax("ajax_vs_unit_resolver.py", {
            method: "POST",
            post_data: post_data,
            response_handler: (_indata, response) => {
                let json_data = JSON.parse(response);
                // Error handling is: If request failed do nothing
                if (json_data.result_code == 0)
                    $("#" + selectbox + "_sel")
                        .val(json_data.result.option_place)
                        .trigger("change");
            },
        });
    };
    let metric_selector = $("#" + metric_prefix);
    change_unit_to_match_metric(metric_selector.val());
    metric_selector.on("change", event => change_unit_to_match_metric(event.target.value));
}

export function fetch_ca_from_server(varprefix) {
    const address = document.querySelector(`input[name='${varprefix + "_address"}']`).value;
    const port = document.querySelector(`input[name='${varprefix + "_port"}']`).value;

    ajax.post_url(
        "ajax_fetch_ca.py",
        "address=" + encodeURIComponent(address) + "&port=" + encodeURIComponent(port),
        (_data, ajax_response) => {
            const response = JSON.parse(ajax_response);

            const status = document.getElementById(varprefix + "_status");
            const content = document.querySelector(`textarea[name='${varprefix}']`);
            if (response.result_code !== 0) {
                status.innerText = response.result;
                content.value = "";
            } else {
                status.innerHTML = response.result.summary;
                content.value = response.result.cert_pem;
            }
        }
    );
}
