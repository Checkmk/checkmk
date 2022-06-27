// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import $ from "jquery";
import * as utils from "utils";

// ----------------------------------------------------------------------------
// General functions for WATO
// ----------------------------------------------------------------------------

interface Dialog {
    inherited_tags;
    check_attributes;
    aux_tags_by_tag;
    depends_on_tags;
    depends_on_roles;
    volatile_topics;
    user_roles;
    hide_attributes;
}
var dialog_properties: null | Dialog = null;

export function prepare_edit_dialog(attrs) {
    dialog_properties = attrs;
}

/* Switch the visibility of all host attributes during the configuration
   of attributes of a host */
export function fix_visibility() {
    /* First collect the current selection of all host attributes.
       They are in the same table as we are */
    var current_tags = get_effective_tags();
    if (!current_tags) return;
    dialog_properties = dialog_properties!;
    var hide_topics = dialog_properties.volatile_topics.slice(0);
    /* Now loop over all attributes that have conditions. Those are
       stored in the global variable depends_on_tags, which is filled
       during the creation of the web page. */

    var index;
    for (var i = 0; i < dialog_properties.check_attributes.length; i++) {
        var attrname = dialog_properties.check_attributes[i];
        /* Now comes the tricky part: decide whether that attribute should
           be visible or not: */
        var display = "";

        // Always invisible
        if (dialog_properties.hide_attributes.indexOf(attrname) > -1) {
            display = "none";
        }

        // Visibility depends on roles
        if (display == "" && attrname in dialog_properties.depends_on_roles) {
            for (
                index = 0;
                index < dialog_properties.depends_on_roles[attrname].length;
                index++
            ) {
                var role = dialog_properties.depends_on_roles[attrname][index];
                var negate = role[0] == "!";
                var rolename = negate ? role.substr(1) : role;
                var have_role =
                    dialog_properties.user_roles.indexOf(rolename) != -1;
                if (have_role == negate) {
                    display = "none";
                    break;
                }
            }
        }

        // Visibility depends on tags
        if (display == "" && attrname in dialog_properties.depends_on_tags) {
            for (
                index = 0;
                index < dialog_properties.depends_on_tags[attrname].length;
                index++
            ) {
                var tag = dialog_properties.depends_on_tags[attrname][index];
                var negate_tag = tag[0] == "!";
                var tagname = negate_tag ? tag.substr(1) : tag;
                var have_tag = current_tags.indexOf(tagname) != -1;
                if (have_tag == negate_tag) {
                    display = "none";
                    break;
                }
            }
        }

        var oTr = document.getElementById(
            "attr_" + attrname
        ) as HTMLTableRowElement;
        if (oTr) {
            oTr.style.display = display;

            // Prepare current visibility information which is used
            // within the attribut validation in wato
            // Hidden attributes are not validated at all
            var oAttrDisp = <HTMLInputElement>(
                document.getElementById("attr_display_" + attrname)
            );
            if (!oAttrDisp) {
                oAttrDisp = document.createElement("input");
                oAttrDisp.name = "attr_display_" + attrname;
                oAttrDisp.id = "attr_display_" + attrname;
                oAttrDisp.type = "hidden";
                oAttrDisp.className = "text";
                oTr.appendChild(oAttrDisp);
            }
            if (display == "none") {
                // Uncheck checkboxes of hidden fields
                var input_fields = oTr.cells[0].getElementsByTagName("input");
                var chkbox = input_fields[0];
                chkbox.checked = false;
                toggle_attribute(chkbox, attrname);

                oAttrDisp.value = "0";
            } else {
                oAttrDisp.value = "1";
            }

            // There is at least one item in this topic -> show it
            var topic = oTr.parentNode!.childNodes[0].textContent;
            if (display == "") {
                index = hide_topics.indexOf(topic);
                if (index != -1) delete hide_topics[index];
            }
        }
    }

    // FIXME: use generic identifier for each form
    var available_forms = ["form_edit_host", "form_editfolder"];
    for (var try_form = 0; try_form < available_forms.length; try_form++) {
        var my_form = document.getElementById(available_forms[try_form]);
        if (my_form != null) {
            for (var child in my_form.childNodes) {
                oTr = my_form.childNodes[child] as HTMLTableRowElement;
                if (oTr.className == "nform") {
                    if (
                        hide_topics.indexOf(
                            oTr.childNodes[0].childNodes[0].textContent
                        ) > -1
                    )
                        oTr.style.display = "none";
                    else oTr.style.display = "";
                }
            }
            break;
        }
    }
}

/* Make attributes visible or not when clicked on a checkbox */
export function toggle_attribute(oCheckbox, attrname) {
    var oEntry = document.getElementById("attr_entry_" + attrname);
    var oDefault = document.getElementById("attr_default_" + attrname);

    // Permanent invisible attributes do
    // not have attr_entry / attr_default
    if (!oEntry) {
        return;
    }

    if (oCheckbox.checked) {
        oEntry.style.display = "";
        oDefault!.style.display = "none";
    } else {
        oEntry.style.display = "none";
        oDefault!.style.display = "";
    }
}

function get_containers() {
    return document
        .getElementById("form_edit_host")
        ?.querySelectorAll(
            "table.nform"
        ) as NodeListOf<HTMLTableSectionElement>;
}

function get_effective_tags() {
    var current_tags: HTMLElement[] = [];

    var containers = get_containers()!;

    for (var a = 0; a < containers.length; a++) {
        var tag_container = containers[a];
        for (var i = 0; i < tag_container.rows.length; i++) {
            dialog_properties = dialog_properties!;
            var row = tag_container.rows[i];
            var add_tag_id;
            if (row.tagName == "TR") {
                var legend_cell = row.cells[0];
                if (!utils.has_class(legend_cell, "legend")) {
                    continue;
                }
                var content_cell = row.cells[1];

                /*
                 * If the Checkbox is unchecked try to get a value from the inherited_tags
                 *
                 * The checkbox may be disabled. In this case there is a hidden field with the original
                 * name of the checkbox. Get that value instead of the checkbox checked state.
                 */
                var input_fields = legend_cell.getElementsByTagName("input");
                if (input_fields.length == 0) continue;
                var checkbox = input_fields[0];
                var attr_enabled = false;
                if (checkbox.name.indexOf("ignored_") === 0) {
                    var hidden_field = input_fields[input_fields.length - 1];
                    attr_enabled = hidden_field.value == "on";
                } else {
                    attr_enabled = checkbox.checked;
                }

                if (attr_enabled == false) {
                    var attr_ident =
                        "attr_" + checkbox.name.replace(/.*_change_/, "");
                    if (
                        attr_ident in dialog_properties.inherited_tags &&
                        dialog_properties.inherited_tags[attr_ident] !== null
                    ) {
                        add_tag_id =
                            dialog_properties.inherited_tags[attr_ident];
                    }
                } else {
                    /* Find the <select>/<checkbox> object in this tr */
                    var elements: HTMLCollectionOf<HTMLElement> =
                        content_cell.getElementsByTagName("input");
                    if (elements.length == 0)
                        elements = content_cell.getElementsByTagName("select");

                    if (elements.length == 0) continue;

                    var oElement = elements[0] as HTMLInputElement;
                    if (oElement.type == "checkbox" && oElement.checked) {
                        add_tag_id = oElement.name.substr(4);
                    } else if (oElement.tagName == "SELECT") {
                        add_tag_id = oElement.value;
                    }
                }
            }

            current_tags.push(add_tag_id);
            if (dialog_properties.aux_tags_by_tag[add_tag_id]) {
                current_tags = current_tags.concat(
                    dialog_properties.aux_tags_by_tag[add_tag_id]
                );
            }
        }
    }
    return current_tags;
}

export function randomize_secret(id, len) {
    var secret = "";
    for (var i = 0; i < len; i++) {
        var c = parseInt(String(26 * Math.random() + 64));
        secret += String.fromCharCode(c);
    }
    var oInput = document.getElementById(id) as HTMLInputElement;
    oInput.value = secret;
}

export function toggle_container(id) {
    var obj = document.getElementById(id);
    if (utils.has_class(obj, "hidden")) utils.remove_class(obj, "hidden");
    else utils.add_class(obj, "hidden");
}

// ----------------------------------------------------------------------------
// Folderlist
// ----------------------------------------------------------------------------

export function open_folder(event, link) {
    if (!event) event = window.event;
    var target = utils.get_target(event);
    if (target.tagName != "DIV") {
        // Skip this event on clicks on other elements than the pure div
        return false;
    }

    location.href = link;
}

export function toggle_folder(event, oDiv, on) {
    if (!event) event = window.event;

    // Skip mouseout event when moving mouse over a child element of the
    // folder element
    if (!on) {
        var node = event.toElement || event.relatedTarget;
        while (node) {
            if (node == oDiv) {
                return false;
            }
            node = node.parentNode;
        }
    }

    var obj = oDiv.parentNode;
    var id = obj.id.substr(7);

    var elements = ["edit", "popup_trigger_move", "delete"];
    for (var num in elements) {
        var elem = document.getElementById(elements[num] + "_" + id);
        if (elem) {
            if (on) {
                elem.style.display = "inline";
            } else {
                elem.style.display = "none";
            }
        }
    }

    if (on) {
        utils.add_class(obj, "open");
    } else {
        utils.remove_class(obj, "open");

        // Hide the eventual open move dialog
        var move_dialog = document.getElementById("move_dialog_" + id);
        if (move_dialog) {
            move_dialog.style.display = "none";
        }
    }
}

export function toggle_rule_condition_type(select_id) {
    var value = (document.getElementById(select_id) as HTMLInputElement).value;
    $(".condition").hide();
    $(".condition." + value).show();
}
