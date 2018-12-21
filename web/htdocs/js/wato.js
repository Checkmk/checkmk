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

// ----------------------------------------------------------------------------
// General functions for WATO
// ----------------------------------------------------------------------------

/* Used to check all checkboxes which have the given class set */
function wato_check_all(css_class) {
    var items = document.getElementsByClassName(css_class);

    // First check if all boxes are checked
    var all_checked = true, i;
    for(i = 0; i < items.length && all_checked == true; i++)
        if (items[i].checked == false)
            all_checked = false;

    // Now set the new state
    for(i = 0; i < items.length; i++)
        items[i].checked = !all_checked;
}

/* Make attributes visible or not when clicked on a checkbox */
function wato_toggle_attribute(oCheckbox, attrname) {
    var oEntry =   document.getElementById("attr_entry_" + attrname);
    var oDefault = document.getElementById("attr_default_" + attrname);

    // Permanent invisible attributes do
    // not have attr_entry / attr_default
    if (!oEntry){
        return;
    }

    if (oCheckbox.checked) {
        oEntry.style.display = "";
        oDefault.style.display = "none";
    }
    else {
        oEntry.style.display = "none";
        oDefault.style.display = "";
    }
}

/* Switch the visibility of all host attributes during the configuration
   of attributes of a host */
function wato_fix_visibility() {
    /* First collect the current selection of all host attributes.
       They are in the same table as we are */
    var current_tags = _get_effective_tags();
    if (!current_tags)
        return;

    var hide_topics = volatile_topics.slice(0);
    /* Now loop over all attributes that have conditions. Those are
       stored in the global variable wato_depends_on_tags, which is filled
       during the creation of the web page. */

    var index;
    for (var i = 0; i < wato_check_attributes.length; i++) {
        var attrname = wato_check_attributes[i];
        /* Now comes the tricky part: decide whether that attribute should
           be visible or not: */
        var display = "";

        // Always invisible
        if (hide_attributes.indexOf(attrname) > -1){
            display = "none";
        }

        // Visibility depends on roles
        if (display == "" && attrname in wato_depends_on_roles) {
            for (index = 0; index < wato_depends_on_roles[attrname].length; index++) {
                var role = wato_depends_on_roles[attrname][index];
                var negate = role[0] == "!";
                var rolename = negate ? role.substr(1) : role;
                var have_role = user_roles.indexOf(rolename) != -1;
                if (have_role == negate) {
                    display = "none";
                    break;
                }
            }
        }

        // Visibility depends on tags
        if (display == "" && attrname in wato_depends_on_tags) {
            for (index = 0; index < wato_depends_on_tags[attrname].length; index++) {
                var tag = wato_depends_on_tags[attrname][index];
                var negate_tag = tag[0] == "!";
                var tagname = negate_tag ? tag.substr(1) : tag;
                var have_tag = current_tags.indexOf(tagname) != -1;
                if (have_tag == negate_tag) {
                    display = "none";
                    break;
                }
            }
        }


        var oTr = document.getElementById("attr_" + attrname);
        if(oTr) {
            oTr.style.display = display;

            // Prepare current visibility information which is used
            // within the attribut validation in wato
            // Hidden attributes are not validated at all
            var oAttrDisp = document.getElementById("attr_display_" + attrname);
            if (!oAttrDisp) {
                oAttrDisp = document.createElement("input");
                oAttrDisp.name  = "attr_display_" + attrname;
                oAttrDisp.id  = "attr_display_" + attrname;
                oAttrDisp.type = "hidden";
                oAttrDisp.className = "text";
                oTr.appendChild(oAttrDisp);
            }
            if ( display == "none" ) {
                // Uncheck checkboxes of hidden fields
                var chkbox = oAttrDisp.parentNode.childNodes[0].childNodes[1].childNodes[0];
                chkbox.checked = false;
                wato_toggle_attribute(chkbox, attrname);

                oAttrDisp.value = "0";
            } else {
                oAttrDisp.value = "1";
            }

            // There is at least one item in this topic -> show it
            var topic = oTr.parentNode.childNodes[0].textContent;
            if (display == ""){
                index = hide_topics.indexOf(topic);
                if (index != -1)
                    delete hide_topics[index];
            }
        }
    }

    // FIXME: use generic identifier for each form
    var available_forms = [ "form_edit_host", "form_editfolder" ];
    for (var try_form = 0; try_form < available_forms.length; try_form++) {
        var my_form = document.getElementById(available_forms[try_form]);
        if (my_form != null) {
            for (var child in my_form.childNodes){
                oTr = my_form.childNodes[child];
                if (oTr.className == "nform"){
                    if( hide_topics.indexOf(oTr.childNodes[0].childNodes[0].textContent) > -1 )
                        oTr.style.display = "none";
                    else
                        oTr.style.display = "";
                }
            }
            break;
        }
    }
}

function _get_effective_tags()
{
    var current_tags = [];

    var container_ids = [ "wato_host_tags", "data_sources", "address" ];

    for (var a = 0; a < container_ids.length; a++) {
        var container_id = container_ids[a];

        var oHostTags = document.getElementById(container_id);

        if (!oHostTags)
            continue;

        var oTable = oHostTags.childNodes[0]; /* tbody */

        for (var i = 0; i < oTable.childNodes.length; i++) {
            var oTr = oTable.childNodes[i];
            var add_tag_id = null;
            if (oTr.tagName == "TR") {
                var oTdLegend = oTr.childNodes[0];
                if (oTdLegend.className != "legend") {
                    continue;
                }
                var oTdContent = oTr.childNodes[1];
                /* If the Checkbox is unchecked try to get a value from the inherited_tags */
                var oCheckbox = oTdLegend.getElementsByTagName("input")[0];
                if (oCheckbox.checked == false ){
                    var attrname = "attr_" + oCheckbox.name.replace(/.*_change_/, "");
                    if (attrname in inherited_tags && inherited_tags[attrname] !== null){
                        add_tag_id = inherited_tags[attrname];
                    }
                } else {
                    /* Find the <select>/<checkbox> object in this tr */
                    var elements = oTdContent.getElementsByTagName("input");
                    if (elements.length == 0)
                        elements = oTdContent.getElementsByTagName("select");

                    if (elements.length == 0)
                        continue;

                    var oElement = elements[0];
                    if (oElement.type == "checkbox" && oElement.checked) {
                        add_tag_id = oElement.name.substr(4);
                    } else if (oElement.tagName == "SELECT") {
                        add_tag_id = oElement.value;
                    }
                }
            }

            current_tags.push(add_tag_id);
            if (wato_aux_tags_by_tag[add_tag_id]) {
                current_tags = current_tags.concat(wato_aux_tags_by_tag[add_tag_id]);
            }
        }
    }
    return current_tags;
}


function wato_randomize_secret(id, len)
{
    var secret = "";
    for (var i=0; i<len; i++) {
        var c = parseInt(26 * Math.random() + 64);
        secret += String.fromCharCode(c);
    }
    var oInput = document.getElementById(id);
    oInput.value = secret;
}

function toggle_container(id)
{
    var obj = document.getElementById(id);
    if (has_class(obj, "hidden"))
        remove_class(obj, "hidden");
    else
        add_class(obj, "hidden");
}

function update_bulk_moveto(val) {
    var fields = document.getElementsByClassName("bulk_moveto");
    for(var i = 0; i < fields.length; i++)
        for(var a = 0; a < fields[i].options.length; a++)
            if(fields[i].options[a].value == val)
                fields[i].options[a].selected = true;
}

// .-Profile Repl----------------------------------------------------------.
// |          ____             __ _ _        ____            _             |
// |         |  _ \ _ __ ___  / _(_) | ___  |  _ \ ___ _ __ | |            |
// |         | |_) | '__/ _ \| |_| | |/ _ \ | |_) / _ \ '_ \| |            |
// |         |  __/| | | (_) |  _| | |  __/ |  _ <  __/ |_) | |            |
// |         |_|   |_|  \___/|_| |_|_|\___| |_| \_\___| .__/|_|            |
// |                                                  |_|                  |
// +-----------------------------------------------------------------------+

var profile_replication_progress = new Array();

function wato_do_profile_replication(siteid, est, progress_text) {
    call_ajax("wato_ajax_profile_repl.py", {
        response_handler : function (handler_data, response_json) {
            var response = JSON.parse(response_json);
            var success = response.result_code === 0;
            var msg = response.result;

            set_profile_replication_result(handler_data["site_id"], success, msg);
        },
        error_handler    : function (handler_data, status_code, error_msg) {
            set_profile_replication_result(handler_data["site_id"], false,
                "Failed to perform profile replication [" + status_code + "]: " + error_msg);
        },
        method           : "POST",
        post_data        : "request=" + encodeURIComponent(JSON.stringify({
            "site": siteid
        })),
        handler_data     : {
            "site_id": siteid
        },
        add_ajax_id      : false
    });

    profile_replication_progress[siteid] = 20; // 10 of 10 10ths
    setTimeout("profile_replication_step('"+siteid+"', "+est+", '"+progress_text+"');", est/20);
}

function profile_replication_set_status(siteid, image, text) {
    var oImg = document.getElementById("site-" + siteid).childNodes[0];
    oImg.title = text;
    oImg.src = "images/icon_"+image+".png";
}

function profile_replication_step(siteid, est, progress_text) {
    if (profile_replication_progress[siteid] > 0) {
        profile_replication_progress[siteid]--;
        var perc = (20.0 - profile_replication_progress[siteid]) * 100 / 20;
        var img;
        if (perc >= 75)
            img = "repl_75";
        else if (perc >= 50)
            img = "repl_50";
        else if (perc >= 25)
            img = "repl_25";
        else
            img = "repl_pending";
        profile_replication_set_status(siteid, img, progress_text);
        setTimeout("profile_replication_step('"+siteid+"',"+est+", '"+progress_text+"');", est/20);
    }
}

function set_profile_replication_result(site_id, success, msg) {
    profile_replication_progress[site_id] = 0;

    var icon_name = success ? "repl_success" : "repl_failed";

    profile_replication_set_status(site_id, icon_name, msg);

    // g_num_replsites is set by the page code in wato.py to the number async jobs started
    // in total
    g_num_replsites--;

    if (0 == g_num_replsites) {
        setTimeout(wato_profile_replication_finish, 1000);
    }
}

function wato_profile_replication_finish() {
    // check if we have a sidebar-main frame setup
    if (this.parent && parent && parent.frames[1] == this)
        cmk.utils.reload_sidebar();
}

// ----------------------------------------------------------------------------
// Folderlist
// ----------------------------------------------------------------------------

function wato_open_folder(event, link) {
    if (!event)
        event = window.event;
    var target = getTarget(event);
    if(target.tagName != "DIV") {
        // Skip this event on clicks on other elements than the pure div
        return false;
    }

    location.href = link;
}

function wato_toggle_folder(event, oDiv, on) {
    if (!event)
        event = window.event;

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
    for(var num in elements) {
        var elem = document.getElementById(elements[num] + "_" + id);
        if(elem) {
            if(on) {
                elem.style.display = "inline";
            } else {
                elem.style.display = "none";
            }
        }
    }

    if(on) {
        add_class(obj, "open");
    } else {
        remove_class(obj, "open");

        // Hide the eventual open move dialog
        var move_dialog = document.getElementById("move_dialog_" + id);
        if(move_dialog) {
            move_dialog.style.display = "none";
        }
    }
}
