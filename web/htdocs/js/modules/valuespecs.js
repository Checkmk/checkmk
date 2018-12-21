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
// ails.  You should have  received  a copy of the  GNU  General Public
// License along with GNU Make; see the file  COPYING.  If  not,  write
// to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
// Boston, MA 02110-1301 USA.

import * as utils from "utils";
import * as popup_menu from "popup_menu";

//#   +--------------------------------------------------------------------+
//#   | Functions needed by HTML code from ValueSpec (valuespec.py)        |
//#   '--------------------------------------------------------------------'

export function toggle_option(oCheckbox, divid, negate) {
    var oDiv = document.getElementById(divid);
    if ((oCheckbox.checked && !negate) || (!oCheckbox.checked && negate))
        oDiv.style.display = "";
    else
        oDiv.style.display = "none";
}

export function toggle_dropdown(oDropdown, divid) {
    var oDiv = document.getElementById(divid);
    if (oDropdown.value == "other")
        oDiv.style.display = "";
    else
        oDiv.style.display = "none";
}

export function toggle_tag_dropdown(oDropdown, divid) {
    var oDiv = document.getElementById(divid);
    if (oDropdown.value == "ignore")
        oDiv.style.display = "none";
    else
        oDiv.style.display = "";
}

/* This function is called after the table with of input elements
   has been rendered. It attaches the onFocus-function to the last
   of the input elements. That function will append another
   input field as soon as the user focusses the last field. */
export function list_of_strings_init(divid, split_on_paste, split_separators) {
    var container = document.getElementById(divid);
    var children = container.getElementsByTagName("div");
    var last_input = children[children.length-1].getElementsByTagName("input")[0];
    list_of_strings_add_event_handlers(last_input, split_on_paste, split_separators);
}

function list_of_strings_add_event_handlers(input, split_on_paste, split_separators) {
    var handler_func = function() {
        if (this.value != "") {
            return list_of_strings_extend(this, split_on_paste, split_separators);
        }
    };

    input.onfocus = handler_func;
    input.oninput = handler_func;

    if (split_on_paste) {
        input.onpaste = function(e) {
            // Get pasted data via clipboard API
            var clipboard_data = e.clipboardData || window.clipboardData;
            var pasted = clipboard_data.getData("Text");

            if (this.value != "")
                return true; // The field had a value before: Don't do custom stuff

            // When pasting a string, trim separators and then split by the given separators
            var stripped = pasted.replace(new RegExp("^["+split_separators+"]+|["+split_separators+"]+$", "g"), "");
            if (stripped == "")
                return true; // Only separators in clipboard: Don't do custom stuff
            var splitted = stripped.split(new RegExp("["+split_separators+"]+"));

            // Add splitted parts to the input fields
            var last_input = this;
            for (var i = 0; i < splitted.length; i++) {
                // Put the first item to the current field
                if (i != 0)
                    last_input = list_of_strings_add_new_field(last_input);

                last_input.value = splitted[i];
            }

            // Focus the last populated field
            last_input.focus();

            // And finally add a new empty field to the end (with attached handlers)
            list_of_strings_extend(last_input, split_on_paste, split_separators);

            // Stop original data actually being pasted
            return utils.prevent_default_events(e);
        };
    }
}

function list_of_strings_remove_event_handlers(input) {
    input.oninput = null;
    input.onfocus = null;
    input.onpaste = null;
}

/* Is called when the last input field in a ListOfString gets focus.
   In that case a new input field is being appended. */
function list_of_strings_extend(input, split_on_paste, split_separators) {
    var new_input = list_of_strings_add_new_field(input);

    /* Move focus function from old last to new last input field */
    list_of_strings_add_event_handlers(new_input, split_on_paste, split_separators);
    list_of_strings_remove_event_handlers(input);
}


function list_of_strings_add_new_field(input) {
    /* The input field has a unique name like "extra_emails_2" for the field with
       the index 2. We need to convert this into "extra_emails_3". */

    var old_name = input.name;
    var splitted = old_name.split("_");
    var num = 1 + parseInt(splitted[splitted.length-1]);
    splitted[splitted.length-1] = "" + num;
    var new_name = splitted.join("_");

    /* Now create a new <div> element as a copy from the current one and
       replace this name. We do this by simply copying the HTML code. The
       last field is always empty. Remember: ListOfStrings() always renders
       one exceeding empty element. */

    var div = input.parentNode;
    while (div.parentNode.classList && !div.parentNode.classList.contains("listofstrings"))
        div = div.parentNode;
    var container = div.parentNode;

    var new_div = document.createElement("DIV");
    new_div.innerHTML = div.innerHTML.replace("\"" + old_name + "\"", "\"" + new_name + "\"");
    // IE7 does not have quotes in innerHTML, trying to workaround this here.
    new_div.innerHTML = new_div.innerHTML.replace("=" + old_name + " ", "=" + new_name + " ");
    new_div.innerHTML = new_div.innerHTML.replace("=" + old_name + ">", "=" + new_name + ">");
    container.appendChild(new_div);

    return new_div.getElementsByTagName("input")[0];
}

export function cascading_change(oSelect, varprefix, count) {
    var nr = parseInt(oSelect.value);

    for (var i=0; i<count; i++) {
        var oDiv = document.getElementById(varprefix + "_" + i + "_sub");
        if (oDiv) {
            if (nr == i) {
                oDiv.style.display = "";
            }
            else
                oDiv.style.display = "none";
        }
    }
}

export function textarea_resize(oArea, theme)
{
    var delimiter;
    if (theme == "facelift") {
        delimiter = 16;
    } else {
        delimiter = 6;
    }
    oArea.style.height = (oArea.scrollHeight - delimiter) + "px";
}

export function listof_add(varprefix, magic, style)
{
    var count_field = document.getElementById(varprefix + "_count");
    var count = parseInt(count_field.value);
    var str_count = "" + (count + 1);
    count_field.value = str_count;

    var html_code = valuespec_listof_get_new_entry_html_code(varprefix, magic, str_count);
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

    listof_update_indices(varprefix);
}

function valuespec_listof_get_new_entry_html_code(varprefix, magic, str_count)
{
    var oPrototype = document.getElementById(varprefix + "_prototype");
    var html_code = oPrototype.innerHTML;
    // replace the magic
    var re = new RegExp(magic, "g");
    html_code = html_code.replace(re, str_count);

    // in some cases the magic might be URL encoded. Also replace these occurences.
    re = new RegExp(encodeURIComponent(magic).replace('!', '%21'), "g");

    return html_code.replace(re, str_count);
}

// When deleting we do not fix up indices but simply
// remove the according list entry and add an invisible
// input element with the name varprefix + "_deleted_%nr"
function valuespec_listof_delete(varprefix, nr) {
    var entry = document.getElementById(varprefix + "_entry_" + nr);

    var input = document.createElement("input");
    input.type = "hidden";
    input.name = "_" + varprefix + '_deleted_' + nr;
    input.value = "1";

    entry.parentNode.replaceChild(input, entry);

    listof_update_indices(varprefix);
}

function vs_listof_drop_handler(handler_args, new_index)
{
    var varprefix = handler_args.varprefix;
    var cur_index = handler_args.cur_index;

    var indexof = document.getElementsByName(varprefix + "_indexof_" + cur_index);
    if (indexof.length == 0)
        throw "Failed to find the indexof_fied";
    indexof = indexof[0];

    // Find the tbody parent of the given tag type
    var tbody = indexof;
    while (tbody && tbody.tagName != "TBODY")
        tbody = tbody.parentNode;

    if (!tbody)
        throw "Failed to find the tbody element of " + indexof;

    listof_update_indices(varprefix);
}

function valuespec_listof_sort(varprefix, magic, sort_by) {
    var tbody = document.getElementById(varprefix + "_container");
    var rows = tbody.rows;

    var entries = [], i;
    for (var i = 0, td, sort_field_name, fields; i < rows.length; i++) {
        // Find the index of this row
        td = rows[i].cells[0]; /* TD with buttons */
        if(td.children.length == 0)
            continue;
        var index = td.getElementsByClassName("orig_index")[0].value;

        sort_field_name = varprefix + "_" + index + "_" + sort_by;

        // extract the sort field value and add it to the entries list
        // together with the row to be moved
        fields = document.getElementsByName(sort_field_name);
        if (fields.length == 0) {
            return; // abort sorting
        }

        entries.push({
            sort_value : fields[0].value,
            row_node   : rows[i]
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
            orig_index.value = "" + (i+1);
        }
        index.value = "" + (i+1);
    }
}

export function list_choice_toggle_all(varprefix) {
    var tbl = document.getElementById(varprefix + "_tbl");
    var checkboxes = tbl.getElementsByTagName("input");
    if (!checkboxes)
        return;

    // simply use state of first texbox as base
    var state = ! checkboxes[0].checked;
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


export function passwordspec_randomize(img) {
    var a, c, password = "";
    while (password.length < 8) {
        a = parseInt(Math.random() * 128);
        if ((a >= 97 && a <= 122) ||
            (a >= 65 && a <= 90) ||
            (a >= 48 && a <= 57))  {
            c = String.fromCharCode(a);
            password += c;
        }
    }
    var oInput = img.previousElementSibling;
    if (oInput.tagName != "INPUT")
        oInput = oInput.children[0]; // in complain mode
    oInput.value = password;
}

export function toggle_hidden(img) {
    var oInput = img;
    while (oInput.tagName != "INPUT")
        oInput = oInput.previousElementSibling;
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
    if (!other_field)
        return;

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
    if (!other_field)
        return;

    var helper = document.getElementById(varprefix);
    if (!helper)
        return;

    // Move the selected options to the other select field
    var selected = [], i;
    for (i = 0; i < field.options.length; i++) {
        if (field.options[i].selected) {
            selected.push(field.options[i]);
        }
    }
    if (selected.length == 0)
        return; // when add/remove clicked, but none selected

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
    var choices = [], i;
    for (i = 0; i < select.options.length;i++) {
        choices[i] = [];
        choices[i][0] = select.options[i].text;
        choices[i][1] = select.options[i].value;
    }

    choices.sort(cmp_func);
    while (select.options.length > 0) {
        select.options[0] = null;
    }

    for (i = 0; i < choices.length;i++) {
        var op = new Option(choices[i][0], choices[i][1]);
        select.options[i] = op;
    }

    return;
}

export function iconselector_select(event, varprefix, value) {
    // set value of valuespec
    var obj = document.getElementById(varprefix + "_value");
    obj.value = value;

    var src_img = document.getElementById(varprefix + "_i_" + value);

    // Set the new choosen icon in the valuespecs image
    var img = document.getElementById(varprefix + "_img");
    img.src = src_img.src;

    popup_menu.close_popup();
}

export function iconselector_toggle(varprefix, category_name) {
    // Update the navigation
    var nav_links = document.getElementsByClassName(varprefix+"_nav");
    var i;
    for (i = 0; i < nav_links.length; i++) {
        if (nav_links[i].id == varprefix+"_"+category_name+"_nav")
            utils.add_class(nav_links[i].parentNode, "active");
        else
            utils.remove_class(nav_links[i].parentNode, "active");
    }

    // Now update the category containers
    var containers = document.getElementsByClassName(varprefix+"_container");
    for (i = 0; i < containers.length; i++) {
        if (containers[i].id == varprefix+"_"+category_name+"_container")
            containers[i].style.display = "";
        else
            containers[i].style.display = "none";
    }
}

export function iconselector_toggle_names(event, varprefix) {
    var icons = document.getElementById(varprefix+"_icons");
    if (utils.has_class(icons, "show_names"))
        utils.remove_class(icons, "show_names");
    else
        utils.add_class(icons, "show_names");
}

function vs_listofmultiple_add(varprefix) {
    var choice = document.getElementById(varprefix + '_choice');
    var ident = choice.value;

    if (ident == '')
        return;

    choice.options[choice.selectedIndex].disabled = true; // disable this choice

    // make the filter visible
    var row = document.getElementById(varprefix + '_' + ident + '_row');
    remove_class(row, 'unused');

    // Change the field names to used ones
    vs_listofmultiple_toggle_fields(row, varprefix, true);

    // Set value emtpy after adding one element
    choice.value = '';

    // Add it to the list of active elements
    var active = document.getElementById(varprefix + '_active');
    if (active.value != '')
        active.value += ';'+ident;
    else
        active.value = ident;
}

function vs_listofmultiple_del(varprefix, ident) {
    // make the filter invisible
    var row = document.getElementById(varprefix + '_' + ident + '_row');
    add_class(row, 'unused');

    // Change the field names to unused ones
    vs_listofmultiple_toggle_fields(row, varprefix, false);

    // Make it choosable from the dropdown field again
    var choice = document.getElementById(varprefix + '_choice');
    for (var i = 0; i < choice.children.length; i++)
        if (choice.children[i].value == ident)
            choice.children[i].disabled = false;

    // Remove it from the list of active elements
    var active = document.getElementById(varprefix + '_active');
    var l = active.value.split(';');
    for (var i in l) {
        if (l[i] == ident) {
            l.splice(i, 1);
            break;
        }
    }
    active.value = l.join(';');
}

function vs_listofmultiple_toggle_fields(root, varprefix, enable) {
    if (root.tagName != 'TR')
        return; // only handle rows here
    var types = ['input', 'select', 'textarea'];
    for (var t in types) {
        var fields = root.getElementsByTagName(types[t]);
        for (var i in fields) {
            fields[i].disabled = !enable;
        }
    }
}

function vs_listofmultiple_init(varprefix) {
    document.getElementById(varprefix + '_choice').value = '';

    vs_listofmultiple_disable_selected_options(varprefix);

    // Mark input fields of unused elements as disabled
    var container = document.getElementById(varprefix + '_table');
    var unused = document.getElementsByClassName('unused', container);
    for (var i in unused) {
        vs_listofmultiple_toggle_fields(unused[i], varprefix, false);
    }
}

// The <option> elements in the <select> field of the currently choosen
// elements need to be disabled.
function vs_listofmultiple_disable_selected_options(varprefix)
{
    var active_choices = document.getElementById(varprefix + '_active').value.split(";");

    var choice_field = document.getElementById(varprefix + '_choice');
    for (var i = 0; i < choice_field.children.length; i++) {
        if (active_choices.indexOf(choice_field.children[i].value) !== -1) {
            choice_field.children[i].disabled = true;
        }
    }
}

var g_autocomplete_ajax = null;

function vs_autocomplete(input, completion_ident, completion_params, on_change)
{
    // TextAscii does not set the id attribute on the input field.
    // Set the id to the name of the field here.
    input.setAttribute("id", input.name);

    // Terminate pending request
    if (g_autocomplete_ajax) {
        g_autocomplete_ajax.abort();
    }

    g_autocomplete_ajax = call_ajax("ajax_vs_autocomplete.py?ident=" + encodeURIComponent(completion_ident), {
        response_handler : vs_autocomplete_handle_response,
        error_handler    : vs_autocomplete_handle_error,
        handler_data     : [ input.id, on_change ],
        method           : "POST",
        post_data        : "params="+encodeURIComponent(JSON.stringify(completion_params))
                          +"&value="+encodeURIComponent(input.value)
                          +"&_plain_error=1",
        add_ajax_id      : false
    });
}

function vs_autocomplete_handle_response(handler_data, response_text)
{
    var input_id = handler_data[0];
    var on_change = handler_data[1];

    try {
        var response = eval(response_text);
    } catch(e) {
        vs_autocomplete_show_error(input_id, response_text);
        return;
    }

    if (response.length == 0) {
        vs_autocomplete_close(input_id);
    }
    else {
        // When only one result and values equal, hide the menu
        var input = document.getElementById(input_id);
        if (response.length == 1
            && input
            && response[0][0] == input.value) {
            vs_autocomplete_close(input_id);
            return;
        }

        vs_autocomplete_show_choices(input_id, on_change, response);
    }
}

function vs_autocomplete_handle_error(handler_data, status_code, error_msg)
{
    var input_id = handler_data[0];

    if (status_code == 0)
        return; // aborted (e.g. by subsequent call)
    vs_autocomplete_show_error(input_id, error_msg + " (" + status_code + ")");
}

function vs_autocomplete_show_choices(input_id, on_change, choices)
{
    var code = "<ul>";
    for(var i = 0; i < choices.length; i++) {
        var value = choices[i][0];
        var label = choices[i][1];

        code += "<li onclick=\"vs_autocomplete_choose('"
                    + input_id + "', '" + value + "');"
                    + on_change + "\">" + label + "</li>";
    }
    code += "</ul>";

    vs_autocomplete_show(input_id, code);
}

function vs_autocomplete_choose(input_id, value)
{
    var input = document.getElementById(input_id);
    input.value = value;
    vs_autocomplete_close(input_id);
}

function vs_autocomplete_show_error(input_id, msg)
{
    vs_autocomplete_show(input_id, "<div class=error>ERROR: " + msg + "</div>");
}

function vs_autocomplete_show(input_id, inner_html)
{
    var popup = document.getElementById(input_id + "_popup");
    if (!popup) {
        var input = document.getElementById(input_id);
        popup = document.createElement("div");
        popup.setAttribute("id", input_id + "_popup");
        popup.className = "vs_autocomplete";
        input.parentNode.appendChild(popup);

        // set minimum width of list to input field width
        popup.style.minWidth = input.clientWidth + "px";
    }

    popup.innerHTML = inner_html;
}

function vs_autocomplete_close(input_id)
{
    var popup = document.getElementById(input_id + "_popup");
    if (popup)
        popup.parentNode.removeChild(popup);
}


var vs_color_pickers = [];

function vs_update_color_picker(varprefix, hex, update_picker) {
    if (!/^#[0-9A-F]{6}$/i.test(hex))
        return; // skip invalid/unhandled colors

    document.getElementById(varprefix + "_input").value = hex;
    document.getElementById(varprefix + "_value").value = hex;
    document.getElementById(varprefix + "_preview").style.backgroundColor = hex;

    if (update_picker)
        vs_color_pickers[varprefix].setHex(hex);
}

/* Switch filter, commands and painter options */
function view_toggle_form(button, form_id) {
    var display = "none";
    var down    = "up";

    var form = document.getElementById(form_id);
    if (form && form.style.display == "none") {
        display = "";
        down    = "down";
    }

    // Close all other view forms
    var alldivs = document.getElementsByClassName('view_form');
    for (var i=0; i<alldivs.length; i++) {
        if (alldivs[i] != form) {
            alldivs[i].style.display = "none";
        }
    }

    if (form)
        form.style.display = display;

    // Make other buttons inactive
    var allbuttons = document.getElementsByClassName('togglebutton');
    for (var i=0; i<allbuttons.length; i++) {
        var b = allbuttons[i];
        if (b != button && !has_class(b, "empth") && !has_class(b, "checkbox")) {
            remove_class(b, "down");
            add_class(b, "up");
        }
    }
    remove_class(button, "down");
    remove_class(button, "up");
    add_class(button, down);
}

function wheel_event_name()
{
    if ("onwheel" in window)
        return "wheel";
    else if (cmk.utils.browser.is_firefox())
        return "DOMMouseScroll";
    else
        return "mousewheel";
}

function wheel_event_delta(event)
{
    return event.deltaY ? event.deltaY
                        : event.detail ? event.detail * (-120)
                                       : event.wheelDelta;
}

function init_optiondial(id)
{
    var container = document.getElementById(id);
    make_unselectable(container);
    cmk.utils.add_event_handler(wheel_event_name(), optiondial_wheel, container);
}

var g_dial_direction = 1;
var g_last_optiondial = null;
function optiondial_wheel(event) {
    event = event || window.event;
    var delta = wheel_event_delta(event);

    // allow updates every 100ms
    if (g_last_optiondial > cmk.utils.time() - 0.1) {
        return prevent_default_events(event);
    }
    g_last_optiondial = cmk.utils.time();

    var container = cmk.utils.get_target(event);
    if (event.nodeType == 3) // defeat Safari bug
        container = container.parentNode;
    while (!container.className)
        container = container.parentNode;

    if (delta > 0)
        g_dial_direction = -1;
    container.onclick(event);
    g_dial_direction = 1;

    return prevent_default_events(event);
}

// used for refresh und num_columns
function view_dial_option(oDiv, viewname, option, choices) {
    // prevent double click from select text
    var new_choice = choices[0]; // in case not contained in choices
    for (var c = 0, choice = null, val = null; c < choices.length; c++) {
        choice = choices[c];
        val = choice[0];
        if (has_class(oDiv, "val_" + val)) {
            new_choice = choices[(c + choices.length + g_dial_direction) % choices.length];
            change_class(oDiv, "val_" + val, "val_" + new_choice[0]);
            break;
        }
    }

    // Start animation
    var step = 0;
    var speed = 10;

    for (var way = 0; way <= 10; way +=1) {
        step += speed;
        setTimeout(function(option, text, way, direction) {
            return function() {
                turn_dial(option, text, way, direction);
            };
        }(option, "", way, g_dial_direction), step);
    }

    for (var way = -10; way <= 0; way +=1) {
        step += speed;
        setTimeout(function(option, text, way, direction) {
            return function() {
                turn_dial(option, text, way, direction);
            };
        }(option, new_choice[1], way, g_dial_direction), step);
    }

    var url = "ajax_set_viewoption.py?view_name=" + viewname +
              "&option=" + option + "&value=" + new_choice[0];
    call_ajax(url, {
        method           : "GET",
        response_handler : function(handler_data, response_body) {
            if (handler_data.option == "refresh")
                set_reload(handler_data.new_value);
            else
                cmk.utils.schedule_reload('', 400.0);
        },
        handler_data     : {
            new_value : new_choice[0],
            option    : option
        }
    });
}

// way ranges from -10 to 10 means centered (normal place)
function turn_dial(option, text, way, direction)
{
    var oDiv = document.getElementById("optiondial_" + option).getElementsByTagName("DIV")[0];
    if (text && oDiv.innerHTML != text)
        oDiv.innerHTML = text;
    oDiv.style.top = (way * 1.3 * direction) + "px";
}

function make_unselectable(elem)
{
    elem.onselectstart = function() { return false; };
    elem.style.MozUserSelect = "none";
    elem.style.KhtmlUserSelect = "none";
    elem.unselectable = "on";
}

// TODO: Is gColumnSwitchTimeout and view_switch_option needed at all?
// TODO: Where is handleReload defined?
/* Switch number of view columns, refresh and checkboxes. If the
   choices are missing, we do a binary toggle. */
gColumnSwitchTimeout = null;
function view_switch_option(oDiv, viewname, option, choices) {
    var new_value;
    if (has_class(oDiv, "down")) {
        new_value = false;
        change_class(oDiv, "down", "up");
    }
    else {
        new_value = true;
        change_class(oDiv, "up", "down");
    }
    var new_choice = [ new_value, '' ];

    var url = "ajax_set_viewoption.py?view_name=" + viewname +
               "&option=" + option + "&value=" + new_choice[0];

    call_ajax(url, {
        method           : "GET",
        response_handler : function(handler_data, response_body) {
            if (handler_data.option == "refresh") {
                set_reload(handler_data.new_value);
            } else if (handler_data.option == "show_checkboxes") {
                cmk.selection.set_selection_enabled(handler_data.new_value);
            }

            handleReload('');
        },
        handler_data     : {
            new_value : new_value,
            option    : option
        }
    });

}

var g_hosttag_groups = {};

function host_tag_update_value(prefix, grp) {
    var value_select = document.getElementById(prefix + '_val');

    // Remove all options
    value_select.options.length = 0;

    if(grp === '')
        return; // skip over when empty group selected

    var opt = null;
    for (var i = 0, len = g_hosttag_groups[grp].length; i < len; i++) {
        opt = document.createElement('option');
        opt.value = g_hosttag_groups[grp][i][0];
        opt.text  = g_hosttag_groups[grp][i][1];
        value_select.appendChild(opt);
    }
}
