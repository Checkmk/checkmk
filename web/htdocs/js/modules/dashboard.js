// Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

import * as utils from "utils";
import * as ajax from "ajax";
import * as forms from "forms";
import * as page_menu from "page_menu";

var reload_on_resize = {};
export var dashboard_properties = {};

export function set_reload_on_resize(dashlet_id, url) {
    reload_on_resize[dashlet_id] = url;
}

export function set_dashboard_properties(properties) {
    dashboard_properties = properties;
    // HACK: We JSON-encode refresh/resize actions twice, so undo one layer here...
    dashboard_properties.refresh_dashlets.forEach(function(refresh) {
        refresh[2] = eval(refresh[2]);
    });
    var resize_actions = dashboard_properties.on_resize_dashlets;
    for (var nr in resize_actions) {
        resize_actions[nr] = eval(resize_actions[nr]);
    }
}

function size_dashlets() {
    var size_info = calculate_dashlets();
    var oDash = null;
    var oDashTitle = null;
    var oDashInner = null;
    var oDashControls = null;

    for (var d_number = 0; d_number < size_info.length; d_number++) {
        var dashlet = size_info[d_number];
        var d_left    = dashlet[0];
        var d_top     = dashlet[1];
        var d_width   = dashlet[2];
        var d_height  = dashlet[3];
        var disstyle = "block";

        // check if dashlet has title and resize its width
        oDashTitle = document.getElementById("dashlet_title_" + d_number);
        var has_title = false;
        if (oDashTitle) {
            has_title = true;
            //if browser window to small prevent js error
            if (d_width <= 20) {
                d_width = 21;
            }
            // 14 => 9 title padding + empty space on right of dashlet
            oDashTitle.style.width  = (d_width - 19) + "px";
            oDashTitle.style.display = disstyle;
            oDashTitle.style.left = dashboard_properties.dashlet_padding[3] + "px";
            oDashTitle.style.top = dashboard_properties.dashlet_padding[4] + 8 + "px";
        }

        // resize outer div
        oDash = document.getElementById("dashlet_" + d_number);
        if (oDash) {
            oDash.style.display  = disstyle;
            oDash.style.left     = d_left + "px";
            oDash.style.top      = d_top + "px";
            oDash.style.width    = d_width + "px";
            oDash.style.height   = d_height + "px";
        }

        var top_padding = dashboard_properties.dashlet_padding[0];
        if (!has_title)
            top_padding = dashboard_properties.dashlet_padding[4];

        var netto_height = d_height - top_padding - dashboard_properties.dashlet_padding[2];
        var netto_width  = d_width  - dashboard_properties.dashlet_padding[1] - dashboard_properties.dashlet_padding[3];

        // resize content div
        oDashInner = document.getElementById("dashlet_inner_" + d_number);
        if (oDashInner) {
            oDashInner.style.display  = disstyle;

            var old_width  = oDashInner.clientWidth;
            var old_height = oDashInner.clientHeight;

            oDashInner.style.left   = dashboard_properties.dashlet_padding[3] + "px";
            oDashInner.style.top    = top_padding + "px";
            if (!has_title) {
                oDashInner.style.top = top_padding + 8 + "px";
            }
            if (netto_width > 0)
                oDashInner.style.width  = netto_width + "px";
            if (netto_height > 0) {
                oDashInner.style.height = netto_height + "px";
                if (!has_title) {
                    oDashInner.style.height = netto_height - 8 + "px";
                }
            }

            if (old_width != oDashInner.clientWidth || old_height != oDashInner.clientHeight) {
                if (!g_resizing || parseInt(g_resizing.parentNode.parentNode.id.replace("dashlet_", "")) != d_number) {
                    dashlet_resized(d_number, oDashInner);
                }
            }
        }

        // resize controls container when in edit mode
        oDashControls = document.getElementById("dashlet_controls_" + d_number);
        if (oDashControls) {
            set_control_size(oDashControls, d_width, d_height);
        }
    }
}

export function adjust_single_metric_font_size(oTdMetricValue) {
    var originalFontSize = parseFloat(oTdMetricValue.style.fontSize);
    var oAMetricValue = oTdMetricValue.childNodes[0];
    if (oAMetricValue.scrollWidth > oTdMetricValue.clientWidth * 9/10)
        oTdMetricValue.style.fontSize = originalFontSize * 9/10 + "px";
    else
        oTdMetricValue.style.fontSize = oTdMetricValue.clientHeight * 4/5 + "px";

    if (oAMetricValue.scrollWidth > oTdMetricValue.clientWidth * 9/10)
        adjust_single_metric_font_size(oTdMetricValue);
}

function set_control_size(dash_controls, width, height)
{
    dash_controls.style.width = (width - dashboard_properties.dashlet_padding[1] - dashboard_properties.dashlet_padding[3]) + "px";
    dash_controls.style.height = (height - dashboard_properties.dashlet_padding[2] - dashboard_properties.dashlet_padding[4]) + "px";
    dash_controls.style.left = dashboard_properties.dashlet_padding[3] + "px";
    dash_controls.style.top = dashboard_properties.dashlet_padding[4] + "px";
}

function is_dynamic(x) {
    return x == dashboard_properties.MAX || x == dashboard_properties.GROW;
}

function align_to_grid(px) {
    return ~~(px / dashboard_properties.grid_size) * dashboard_properties.grid_size;
}

function vec(x, y) {
    this.x = x || 0;
    this.y = y || 0;
}

vec.prototype = {
    divide: function(s) {
        return new vec(~~(this.x / s), ~~(this.y / s));
    },
    add: function(v) {
        return new vec(this.x + v.x, this.y + v.y);
    },
    make_absolute: function(size_v) {
        return new vec(this.x < 0 ? this.x + size_v.x + 1 : this.x - 1,
            this.y < 0 ? this.y + size_v.y + 1 : this.y - 1);
    },
    // Compute the initial size of the dashlet. If dashboard_properties.MAX is used,
    // then the dashlet consumes all space in its growing direction,
    // regardless of any other dashlets.
    initial_size: function(pos_v, grid_v) {
        return new vec(
            (this.x == dashboard_properties.MAX ? grid_v.x - Math.abs(pos_v.x) + 1 : (this.x == dashboard_properties.GROW ? dashboard_properties.dashlet_min_size[0] : this.x)),
            (this.y == dashboard_properties.MAX ? grid_v.y - Math.abs(pos_v.y) + 1 : (this.y == dashboard_properties.GROW ? dashboard_properties.dashlet_min_size[1] : this.y))
        );
    },
    // return codes:
    //  0: absolute size, no growth
    //  1: grow direction right, down
    // -1: grow direction left, up
    compute_grow_by: function(size_v) {
        return new vec(
            (size_v.x != dashboard_properties.GROW ? 0 : (this.x < 0 ? -1 : 1)),
            (size_v.y != dashboard_properties.GROW ? 0 : (this.y < 0 ? -1 : 1))
        );
    },
    toString: function() {
        return this.x+"/"+this.y;
    }
};

function calculate_dashlets() {
    var screen_size = new vec(g_dashboard_width, g_dashboard_height);
    var raster_size = screen_size.divide(dashboard_properties.grid_size);
    var used_matrix = {};
    var positions   = [];

    // first place all dashlets at their absolute positions
    var nr, top, left, right, bottom, grow_by;
    for (nr = 0; nr < dashboard_properties.dashlets.length; nr++) {
        var dashlet = dashboard_properties.dashlets[nr];

        // Relative position is as noted in the declaration. 1,1 => top left origin,
        // -1,-1 => bottom right origin, 0 is not allowed here
        // starting from 1, negative means: from right/bottom
        var rel_position = new vec(dashlet.x, dashlet.y);

        // Compute the absolute position, this time from 0 to raster_size-1
        var abs_position = rel_position.make_absolute(raster_size);

        // The size in raster-elements. A 0 for a dimension means growth. No negative values here.
        var size = new vec(dashlet.w, dashlet.h);

        // Compute the minimum used size for the dashlet. For growth-dimensions we start with 1
        var used_size = size.initial_size(rel_position, raster_size);

        // Now compute the rectangle that is currently occupied. The coords
        // of bottomright are *not* included.
        if (rel_position.x > 0) {
            left = abs_position.x;
            right = left + used_size.x;
        }
        else {
            right = abs_position.x;
            left = right - used_size.x;
        }

        if (rel_position.y > 0) {
            top = abs_position.y;
            bottom = top + used_size.y;
        }
        else {
            bottom = abs_position.y;
            top = bottom - used_size.y;
        }

        // Allocate used squares in matrix. If not all squares we need are free,
        // then the dashboard is too small for all dashlets (as it seems).
        for (var x = left; x < right; x++) {
            for (var y = top; y < bottom; y++) {
                used_matrix[x+" "+y] = true;
            }
        }
        // Helper variable for how to grow, both x and y in [-1, 0, 1]
        grow_by = rel_position.compute_grow_by(size);

        positions.push([left, top, right, bottom, grow_by]);
    }

    var try_allocate = function(left, top, right, bottom) {
        var x, y;
        // Try if all needed squares are free
        for (x = left; x < right; x++)
            for (y = top; y < bottom; y++)
                if (x+" "+y in used_matrix)
                    return false;

        // Allocate all needed squares
        for (x = left; x < right; x++)
            for (y = top; y < bottom; y++)
                used_matrix[x+" "+y] = true;

        return true;
    };

    // Now try to expand all elastic rectangles as far as possible
    // FIXME: Das hier muesste man optimieren
    var at_least_one_expanded = true;
    while (at_least_one_expanded) {
        at_least_one_expanded = false;
        var new_positions = [];
        for (nr = 0; nr < positions.length; nr++) {
            left    = positions[nr][0];
            top     = positions[nr][1];
            right   = positions[nr][2];
            bottom  = positions[nr][3];
            grow_by = positions[nr][4];

            // try to grow in X direction by one
            if (grow_by.x > 0 && right < raster_size.x && try_allocate(right, top, right+1, bottom)) {
                at_least_one_expanded = true;
                right += 1;
            }
            else if (grow_by.x < 0 && left > 0 && try_allocate(left-1, top, left, bottom)) {
                at_least_one_expanded = true;
                left -= 1;
            }

            // try to grow in Y direction by one
            if (grow_by.y > 0 && bottom < raster_size.y && try_allocate(left, bottom, right, bottom+1)) {
                at_least_one_expanded = true;
                bottom += 1;
            }
            else if (grow_by.y < 0 && top > 0 && try_allocate(left, top-1, right, top)) {
                at_least_one_expanded = true;
                top -= 1;
            }
            new_positions.push([left, top, right, bottom, grow_by]);
        }
        positions = new_positions;
    }

    var size_info = [];
    for (nr = 0; nr < positions.length; nr++) {
        left    = positions[nr][0];
        top     = positions[nr][1];
        right   = positions[nr][2];
        bottom  = positions[nr][3];
        size_info.push([
            left * dashboard_properties.grid_size,
            top * dashboard_properties.grid_size,
            (right - left) * dashboard_properties.grid_size,
            (bottom - top) * dashboard_properties.grid_size
        ]);
    }
    return size_info;
}

var g_dashboard_resizer = null;
var g_dashboard_top     = null;
var g_dashboard_left    = null;
var g_dashboard_width   = null;
var g_dashboard_height  = null;

export function calculate_dashboard() {
    if (g_dashboard_resizer !== null)
        return; // another resize is processed
    g_dashboard_resizer = true;

    g_dashboard_top    = dashboard_properties.header_height;
    g_dashboard_left   = dashboard_properties.screen_margin;
    g_dashboard_width  = utils.page_width() - dashboard_properties.screen_margin;
    g_dashboard_height = utils.page_height() - dashboard_properties.header_height;

    var oDash = document.getElementById("dashboard");
    oDash.style.width    = g_dashboard_width + "px";
    oDash.style.height   = g_dashboard_height + "px";

    size_dashlets();
    g_dashboard_resizer = null;
}

export function execute_dashboard_scheduler(initial) {
    // Stop reload of the dashlets in case the browser window / tab is not visible
    // for the user. Retry after short time.
    if (!utils.is_window_active()) {
        setTimeout(function(){ execute_dashboard_scheduler(initial); }, 250);
        return;
    }

    var timestamp = Date.parse(new Date()) / 1000;
    for(var i = 0; i < dashboard_properties.refresh_dashlets.length; i++) {
        var nr      = dashboard_properties.refresh_dashlets[i][0];
        var refresh = dashboard_properties.refresh_dashlets[i][1];
        var url     = dashboard_properties.refresh_dashlets[i][2];

        if ((initial && document.getElementById("dashlet_inner_" + nr).innerHTML == "")
                || (refresh > 0 && timestamp % refresh == 0)) {
            if (typeof(url) === "string") {
                if (url.indexOf("?") !== -1)
                    url += "&mtime=" + dashboard_properties.dashboard_mtime;
                else
                    url += "?mtime=" + dashboard_properties.dashboard_mtime;
                ajax.get_url(url, dashboard_update_contents, "dashlet_inner_" + nr);
            }
            else {
                url(); // Execute "on_refresh" javascript function
            }
        }
    }

    // Update timestamp every minute
    // Required if there are no refresh_dashlets present or all refresh times are > 60sec
    if (timestamp % 60 == 0)
        utils.update_header_timer();

    setTimeout(function() {
        execute_dashboard_scheduler(0);
    }, 1000);
}

function dashboard_update_contents(id, response_text) {
    utils.update_header_timer();

    // Call the generic function to replace the dashlet inner code
    utils.update_contents(id, response_text);
}

//
// DASHBOARD EDITING
//

var g_editing = false;

export function toggle_dashboard_edit() {
    g_editing = !g_editing;

    // Toggle the page menu elements
    let toggle_suggestion = document.getElementById("menu_suggestion_toggle_edit");
    let toggle_shortcut = document.getElementById("menu_shortcut_toggle_edit");
    let toggle_entry = document.getElementById("menu_entry_toggle_edit");
    if (g_editing) {
        utils.add_class(toggle_suggestion, "edit");
        utils.add_class(toggle_shortcut, "edit");
        utils.add_class(toggle_entry, "edit");
        page_menu.enable_dropdown("add_dashlets");
    } else {
        utils.remove_class(toggle_suggestion, "edit");
        utils.remove_class(toggle_shortcut, "edit");
        utils.remove_class(toggle_entry, "edit");
        page_menu.disable_dropdown("add_dashlets");
    }

    var dashlet_divs = document.getElementsByClassName("dashlet");
    for (var i = 0; i < dashlet_divs.length; i++)
        dashlet_toggle_edit(dashlet_divs[i]);

    // Remove/Add edit=1 parameter from URL to make page reload handling correct
    utils.update_url_parameter("edit", g_editing ? "1" : "0");

    toggle_grid();
}

function toggle_grid() {
    if (!g_editing) {
        utils.remove_class(document.getElementById("dashboard"), "grid");
    } else {
        utils.add_class(document.getElementById("dashboard"), "grid");
    }
}

// The resize controls are transparent areas at the border of the
// snapin which give the user the option to dragresize the dashlets
// in the dimension where absolute sizes are to be used.
//
// render top/bottom or left/right areas depending on dimension i
function render_resize_controls(controls, i) {
    for (var a = 0; a < 2; a++) {
        var resize = document.createElement("div");
        resize.className = "resize resize"+i+" resize"+i+"_"+a;
        controls.appendChild(resize);
    }
}

function render_sizer(controls, nr, i, anchor_id, size) {
    // 0 ~ X, 1 ~ Y
    var sizer = document.createElement("div");
    sizer.className = "sizer sizer"+i+" anchor"+anchor_id;

    // create the sizer label
    var sizer_lbl = document.createElement("div");
    sizer_lbl.className = "sizer_lbl sizer_lbl"+i+" anchor"+anchor_id;

    if (size == dashboard_properties.MAX) {
        sizer.className += " max";
        //sizer_lbl.innerHTML = "MAX";
        sizer.title = "Use maximum available space in this direction";
    }
    else if (size == dashboard_properties.GROW) {
        sizer.className += " grow";
        //sizer_lbl.innerHTML = "GROW";
        sizer.title = "Grow in this direction";
    }
    else {
        sizer.className += " abs";
        sizer.title = "Fixed size (drag border for resize)";
        render_resize_controls(controls, i);
    }

    // js magic stuff - closures!
    sizer.onclick = function(dashlet_id, sizer_id) {
        return function() {
            toggle_sizer(dashlet_id, sizer_id);
        };
    }(nr, i);
    sizer_lbl.onclick = sizer.onclick;
    sizer_lbl.title = sizer.title;

    controls.appendChild(sizer);
    if (is_dynamic(size))
        controls.appendChild(sizer_lbl);
}

function render_corner_resizers(controls) {
    for (var corner_id = 0; corner_id < 4; corner_id++) {
        var resize = document.createElement("div");
        resize.className = "resize resize_corner resize_corner"+corner_id;
        controls.appendChild(resize);
    }
}

function dashlet_toggle_edit(dashlet_obj, edit) {
    var nr = parseInt(dashlet_obj.id.replace("dashlet_", ""));
    var dashlet = dashboard_properties.dashlets[nr];

    edit = edit === undefined ? g_editing : edit;

    var controls;
    if (edit) {
        // gray out the inner parts of the dashlet
        utils.add_class(dashlet_obj, "edit");

        // Create the dashlet controls
        controls = document.createElement("div");
        controls.setAttribute("id", "dashlet_controls_"+nr);
        controls.className = "controls";
        dashlet_obj.appendChild(controls);
        set_control_size(controls, dashlet_obj.clientWidth, dashlet_obj.clientHeight);

        // IE < 9: Without this fix the controls container is not working
        if (utils.browser.is_ie_below_9()) {
            controls.style.background = "url(about:blank)";
        }

        // Which is the anchor corner?
        var anchor_id = get_anchor_id(dashlet);

        // Create the size / grow indicators and resizer control elements
        var i;
        if (utils.has_class(dashlet_obj, "resizable")) {
            for (i = 0; i < 2; i ++) {
                if (i == 0)
                    render_sizer(controls, nr, i, anchor_id, dashlet.w);
                else
                    render_sizer(controls, nr, i, anchor_id, dashlet.h);
            }

            if (!is_dynamic(dashlet.w) && !is_dynamic(dashlet.h))
                render_corner_resizers(controls);
        }

        // Create the anchors
        for (i = 0; i < 4; i++) {
            var anchor = document.createElement("a");
            anchor.className = "anchor anchor"+i;
            anchor.title = "Currently growing from here";
            if (anchor_id != i) {
                anchor.className += " off";
                anchor.title = "Click to start growing from here";
            }

            // js magic stuff - closures!
            anchor.onclick = function(dashlet_id, anchor_id) {
                return function() {
                    toggle_anchor(dashlet_id, anchor_id);
                };
            }(nr, i);

            controls.appendChild(anchor);
        }

        // Add edit dashlet button
        var edit_button = document.createElement("a");
        edit_button.className = "edit";
        edit_button.title = "Edit properties of this dashlet";
        edit_button.onclick = function(dashlet_id, board_name) {
            return function() {
                var back_url = utils.makeuri({}, window.location.href, "dashboard.py");
                location.href = utils.makeuri_contextless({
                    "name": board_name,
                    "id": dashlet_id,
                    "back": back_url
                }, "edit_dashlet.py");
            };
        }(nr, dashboard_properties.dashboard_name);
        controls.appendChild(edit_button);

        // Add clone dashlet button
        var clone = document.createElement("a");
        clone.className = "clone";
        clone.title = "Clone this dashlet";
        clone.onclick = function(dashlet_id, board_name) {
            return function() {
                var back_url = utils.makeuri({}, window.location.href, "dashboard.py");
                location.href = utils.makeuri_contextless({
                    "id": dashlet_id,
                    "name": board_name,
                    "back": back_url
                }, "clone_dashlet.py");
            };
        }(nr, dashboard_properties.dashboard_name);
        controls.appendChild(clone);

        // Add delete dashlet button
        var del = document.createElement("a");
        del.className = "del";
        del.title = "Delete this dashlet";
        del.onclick = function(dashlet_id, board_name) {
            return function() {
                forms.confirm_dialog("Do you really want to delete this dashlet?", function() {
                    var back_url = utils.makeuri({}, window.location.href, "dashboard.py");
                    location.href = utils.makeuri_contextless({
                        "name": board_name,
                        "id": dashlet_id,
                        "back": back_url
                    }, "delete_dashlet.py");
                });
            };
        }(nr, dashboard_properties.dashboard_name);
        controls.appendChild(del);

    } else {
        // make the inner parts visible again
        utils.remove_class(dashlet_obj, "edit");

        // Remove all dashlet controls
        controls = document.getElementById("dashlet_controls_"+nr);
        controls.parentNode.removeChild(controls);
    }
}

// In case of cycling from ABS to again ABS, restore the previous ABS coords
var g_last_absolute_widths  = {};
var g_last_absolute_heights = {};

function toggle_sizer(nr, sizer_id) {
    var dashlet = dashboard_properties.dashlets[nr];
    var dashlet_obj = document.getElementById("dashlet_"+nr);

    if (sizer_id == 0) {
        if (dashlet.w > 0) {
            g_last_absolute_widths[nr] = dashlet.w;
            dashlet.w = dashboard_properties.GROW;
        }
        else if (dashlet.w == dashboard_properties.GROW) {
            if (!(nr in g_last_absolute_widths))
                g_last_absolute_widths[nr] = dashlet_obj.clientWidth / dashboard_properties.grid_size;
            dashlet.w = dashboard_properties.MAX;
        }
        else if (dashlet.w == dashboard_properties.MAX) {
            if (nr in g_last_absolute_widths)
                dashlet.w = g_last_absolute_widths[nr];
            else
                dashlet.w = dashlet_obj.clientWidth / dashboard_properties.grid_size;
        }
    }
    else {
        if (dashlet.h > 0) {
            g_last_absolute_heights[nr] = dashlet.h;
            dashlet.h = dashboard_properties.GROW;
        }
        else if (dashlet.h == dashboard_properties.GROW) {
            if (!(nr in g_last_absolute_heights))
                g_last_absolute_heights[nr] = dashlet_obj.clientHeight / dashboard_properties.grid_size;
            dashlet.h = dashboard_properties.MAX;
        }
        else if (dashlet.h == dashboard_properties.MAX) {
            if (nr in g_last_absolute_heights)
                dashlet.h = g_last_absolute_heights[nr];
            else
                dashlet.h = dashlet_obj.clientHeight / dashboard_properties.grid_size;
        }
    }

    rerender_dashlet_controls(dashlet_obj);
    size_dashlets();
    persist_dashlet_pos(nr);
}

var A_TOP_LEFT     = 0;
var A_TOP_RIGHT    = 1;
var A_BOTTOM_RIGHT = 2;
var A_BOTTOM_LEFT  = 3;

// Calculates the ID of the current dashlet anchor depending
// on the current coordinates
function get_anchor_id(dashlet) {
    var anchor_id;
    if (dashlet.x > 0 && dashlet.y > 0)
        anchor_id = A_TOP_LEFT;
    else if (dashlet.x <= 0 && dashlet.y > 0)
        anchor_id = A_TOP_RIGHT;
    else if (dashlet.x <= 0 && dashlet.y <= 0)
        anchor_id = A_BOTTOM_RIGHT;
    else if (dashlet.x > 0 && dashlet.y <= 0)
        anchor_id = A_BOTTOM_LEFT;
    return anchor_id;
}

function toggle_anchor(nr, anchor_id) {
    if (anchor_id == get_anchor_id(dashboard_properties.dashlets[nr]))
        return; // anchor has not changed, skip it!

    calculate_relative_dashlet_coords(nr, anchor_id);

    // Visualize the change within the dashlet
    rerender_dashlet_controls(document.getElementById("dashlet_"+nr));

    // Apply the change to all rendered dashlets
    size_dashlets();

    persist_dashlet_pos(nr);
}

// We do not want to recompute the dimensions of growing dashlets here,
// use the current effective size
function calculate_relative_dashlet_coords(nr, anchor_id) {
    var dashlet = dashboard_properties.dashlets[nr];

    // When the anchor id is not set explicit here autodetect the anchor
    // id which is currently used by the dashlet. Otherwise this function
    // will set a new anchor for the dashlet and recalculate the coordinates
    if (anchor_id === undefined) {
        anchor_id = get_anchor_id(dashlet);
    }

    var dashlet_obj = document.getElementById("dashlet_" + nr);

    var x = align_to_grid(dashlet_obj.offsetLeft) / dashboard_properties.grid_size;
    var y = align_to_grid(dashlet_obj.offsetTop) / dashboard_properties.grid_size;
    var w = align_to_grid(dashlet_obj.clientWidth) / dashboard_properties.grid_size;
    var h = align_to_grid(dashlet_obj.clientHeight) / dashboard_properties.grid_size;

    var screen_size  = new vec(g_dashboard_width, g_dashboard_height);
    var raster_size  = screen_size.divide(dashboard_properties.grid_size);

    // Update fixed sizes in coord structure
    if (!is_dynamic(dashlet.w))
        dashlet.w = w;
    if (!is_dynamic(dashlet.h))
        dashlet.h = h;

    if (anchor_id == A_TOP_LEFT) {
        dashlet.x = x;
        dashlet.y = y;
    }
    else if (anchor_id == A_TOP_RIGHT) {
        dashlet.x = (x + w) - (raster_size.x + 2);
        dashlet.y = y;
    }
    else if (anchor_id == A_BOTTOM_RIGHT) {
        dashlet.x = (x + w) - (raster_size.x + 2);
        dashlet.y = (y + h) - (raster_size.y + 2);
    }
    else if (anchor_id == A_BOTTOM_LEFT) {
        dashlet.x = x;
        dashlet.y = (y + h) - (raster_size.y + 2);
    }
    dashlet.x += 1;
    dashlet.y += 1;
}

function rerender_dashlet_controls(dashlet_obj) {
    dashlet_toggle_edit(dashlet_obj, false);
    dashlet_toggle_edit(dashlet_obj, true);
}

/**
 * Dragging of dashlets
 */

var g_dragging = false;
var g_drag_start = null;

function drag_dashlet_start(event) {
    if (!event)
        event = window.event;

    if (!g_editing)
        return true;

    var target = utils.get_target(event);
    var button = utils.get_button(event);

    if (g_dragging === false && button == "LEFT" && utils.has_class(target, "controls")) {
        g_dragging = target.parentNode;
        var nr = parseInt(g_dragging.id.replace("dashlet_", ""));
        var dashlet = dashboard_properties.dashlets[nr];

        // minimal dashlet sizes in pixels
        var min_w = dashboard_properties.dashlet_min_size[0] * dashboard_properties.grid_size;
        var min_h = dashboard_properties.dashlet_min_size[1] * dashboard_properties.grid_size;

        // reduce the dashlet to the minimum dashlet size for movement bound checks
        var x = g_dragging.offsetLeft;
        var y = g_dragging.offsetTop;
        var w = g_dragging.clientWidth;
        var h = g_dragging.clientHeight;

        var anchor_id = get_anchor_id(dashlet);
        if (anchor_id == A_TOP_LEFT) {
            if (is_dynamic(dashlet.w))
                w = min_w;
            if (is_dynamic(dashlet.h))
                h = min_h;
        }
        else if (anchor_id == A_TOP_RIGHT) {
            if (is_dynamic(dashlet.w)) {
                x = x + w - min_w;
                w = min_w;
            }
            if (is_dynamic(dashlet.h))
                h = min_h;
        }
        else if (anchor_id == A_BOTTOM_RIGHT) {
            if (is_dynamic(dashlet.w)) {
                x = x + w - min_w;
                w = min_w;
            }
            if (is_dynamic(dashlet.h)) {
                y = y + h - min_h;
                h = min_h;
            }
        }
        else if (anchor_id == A_BOTTOM_LEFT) {
            if (is_dynamic(dashlet.w))
                w = min_w;
            if (is_dynamic(dashlet.h)) {
                y = y + h - min_h;
                h = min_h;
            }
        }

        g_drag_start = {
            // mouse position in px relative to dashboard
            "m_x": event.clientX - g_dashboard_left,
            "m_y": event.clientY - g_dashboard_top,
            // x/y position of shrunk dashlet in px relative to dashboard
            "x": x,
            "y": y,
            // size of shrunk dashlet in px
            "w": w,
            "h": h,
        };

        edit_visualize(g_dragging, true);

        utils.prevent_default_events(event);
        return false;
    }
    return true;
}

function drag_dashlet(event) {
    if (!event)
        event = window.event;

    // mosue coords in px relative to dashboard
    var mouse_x = event.clientX - g_dashboard_left;
    var mouse_y = event.clientY - g_dashboard_top;

    if (!g_dragging)
        return true;

    var nr = parseInt(g_dragging.id.replace("dashlet_", ""));
    var dashlet_obj = g_dragging;

    // get the relative mouse position offset to the dragging beginning
    var diff_x = align_to_grid(g_drag_start.m_x - mouse_x);
    var diff_y = align_to_grid(g_drag_start.m_y - mouse_y);

    var x = g_drag_start.x - diff_x;
    var y = g_drag_start.y - diff_y;
    var w = g_drag_start.w;
    var h = g_drag_start.h;

    var board_w = align_to_grid(g_dashboard_width);
    var board_h = align_to_grid(g_dashboard_height);

    if (x < 0) {
        // reached left limit: left screen border
        dashlet_obj.style.left  = "0px";
        dashlet_obj.style.width = w + "px";
    }
    else if (x + w > board_w) {
        // reached right limit: right screen border
        dashlet_obj.style.left  = (board_w - w) + "px";
        dashlet_obj.style.width = w + "px";
    }
    else {
        dashlet_obj.style.left  = x + "px";
        dashlet_obj.style.width = w + "px";
    }

    if (y < 0) {
        // reached top limit: top screen border
        dashlet_obj.style.top   = "0px";
        dashlet_obj.style.height = h + "px";
    }
    else if (y + h > board_h) {
        // reached bottom limit: bottom screen border
        dashlet_obj.style.top    = (board_h - h) + "px";
        dashlet_obj.style.height = h + "px";
    }
    else {
        dashlet_obj.style.top    = y + "px";
        dashlet_obj.style.height = h + "px";
    }

    // Calculates new data for the internal coord structure
    calculate_relative_dashlet_coords(nr);

    // Redo dynamic sizing and rendering
    size_dashlets();
}

function drag_dashlet_stop(event) {
    if (!event)
        event = window.event;

    if (!g_dragging)
        return true;

    edit_visualize(g_dragging, false);
    var nr = parseInt(g_dragging.id.replace("dashlet_", ""));
    g_dragging   = false;
    g_drag_start = null;

    persist_dashlet_pos(nr);

    return false;
}

function persist_dashlet_pos(nr) {
    var dashlet = dashboard_properties.dashlets[nr];

    if (!Number.isInteger(dashlet.x) || !Number.isInteger(dashlet.y)
        || !Number.isInteger(dashlet.w) || !Number.isInteger(dashlet.h)) {
        alert("Error: Invalid dashlet coordinates found. Please report "
            + "this issue (" + JSON.stringify(dashlet) + ").");
        return;
    }

    ajax.get_url("ajax_dashlet_pos.py?name=" + dashboard_properties.dashboard_name + "&id=" + nr
            + "&x=" + dashboard_properties.dashlets[nr].x + "&y=" + dashboard_properties.dashlets[nr].y
            + "&w=" + dashboard_properties.dashlets[nr].w + "&h=" + dashboard_properties.dashlets[nr].h,
            handle_dashlet_post_response, null, undefined, false); // eslint-disable-line indent
}

function handle_dashlet_post_response(_unused, response_text) {
    var parts = response_text.split(" ");
    if (parts[0] != "OK") {
        alert("Error: " + response_text);
    } else {
        dashboard_properties.dashboard_mtime = parseInt(parts[1]);
    }
}

function edit_visualize(obj, show) {
    if (show)
        obj.style.zIndex = 80;
    else
        obj.style.zIndex = 1;
}

/**
 * Resizing of dashlets
 */

// false or the resizer dom object currently being worked with
var g_resizing     = false;
var g_resize_start = null;

function resize_dashlet_start(event) {
    if (!event)
        event = window.event;

    if (!g_editing)
        return true;

    var target = utils.get_target(event);
    var button = utils.get_button(event);

    if (g_resizing === false && button == "LEFT" && utils.has_class(target, "resize")) {
        var dashlet_obj = target.parentNode.parentNode;

        g_resizing = target;
        g_resize_start = {
            // mouse position in px
            "m_x": event.clientX,
            "m_y": event.clientY,
            // initial position in px
            "x": dashlet_obj.offsetLeft,
            "y": dashlet_obj.offsetTop,
            // initial size in px
            "w": dashlet_obj.clientWidth,
            "h": dashlet_obj.clientHeight
        };

        edit_visualize(dashlet_obj, true);

        utils.prevent_default_events(event);
        return false;
    }
    return true;
}

function get_horizontal_direction(resizer) {
    if (utils.has_class(resizer, "resize0_0") || utils.has_class(resizer, "resize_corner0") || utils.has_class(resizer, "resize_corner3"))
        return "left";
    else if (utils.has_class(resizer, "resize0_1") || utils.has_class(resizer, "resize_corner1") || utils.has_class(resizer, "resize_corner2"))
        return "right";
}

function get_vertical_direction(resizer) {
    if (utils.has_class(resizer, "resize1_0") || utils.has_class(resizer, "resize_corner0") || utils.has_class(resizer, "resize_corner1"))
        return "top";
    else if (utils.has_class(resizer, "resize1_1") || utils.has_class(resizer, "resize_corner2") || utils.has_class(resizer, "resize_corner3"))
        return "bottom";
}

function resize_dashlet(event) {
    if (!event)
        event = window.event;

    if (!g_resizing)
        return true;

    var dashlet_obj = g_resizing.parentNode.parentNode;
    var nr = parseInt(dashlet_obj.id.replace("dashlet_", ""));

    var diff_x = align_to_grid(Math.abs(g_resize_start.m_x - event.clientX));
    var diff_y = align_to_grid(Math.abs(g_resize_start.m_y - event.clientY));

    if (event.clientX > g_resize_start.m_x)
        diff_x *= -1;
    if (event.clientY > g_resize_start.m_y)
        diff_y *= -1;

    var board_w = align_to_grid(g_dashboard_width);
    var board_h = align_to_grid(g_dashboard_height);

    var min_w = dashboard_properties.dashlet_min_size[0] * dashboard_properties.grid_size;
    var min_h = dashboard_properties.dashlet_min_size[1] * dashboard_properties.grid_size;

    if (get_horizontal_direction(g_resizing) == "left") {
        // resizing with left border
        var new_x = g_resize_start.x - diff_x;
        if (new_x < 0) {
            // reached left limit: left screen border
            dashlet_obj.style.left  = "0px";
            dashlet_obj.style.width = (g_resize_start.w + g_resize_start.x) + "px";
        }
        else if (g_resize_start.w + diff_x < min_w) {
            // reached right limit: minimum dashlet width
            dashlet_obj.style.width = min_w + "px";
        }
        else {
            // normal resize step
            dashlet_obj.style.left  = new_x + "px";
            dashlet_obj.style.width = (g_resize_start.w + diff_x) + "px";
        }
    }
    else if (get_horizontal_direction(g_resizing) == "right") {
        // resizing with right border
        if (g_resize_start.x + g_resize_start.w - diff_x > board_w) {
            // reached right limit: right screen border
            dashlet_obj.style.width = (board_w - g_resize_start.x) + "px";
        }
        else if (g_resize_start.w - diff_x < min_w) {
            // reached left limit: minimum dashlet width
            dashlet_obj.style.width = min_w + "px";
        }
        else {
            // normal resize step
            dashlet_obj.style.width = (g_resize_start.w - diff_x) + "px";
        }
    }

    if (get_vertical_direction(g_resizing) == "top") {
        // resizing with top border
        var new_y = g_resize_start.y - diff_y;
        if (new_y < 0) {
            // reached top limit: top screen border
            dashlet_obj.style.top    = "0px";
            dashlet_obj.style.height = (g_resize_start.h + g_resize_start.y) + "px";
        }
        else if (g_resize_start.h + diff_y < min_h) {
            // reached bottom limit: minimum dashlet height
            dashlet_obj.style.height = min_h + "px";
        }
        else {
            // normal resize step
            dashlet_obj.style.top    = new_y + "px";
            dashlet_obj.style.height = (g_resize_start.h + diff_y) + "px";
        }
    }
    else if (get_vertical_direction(g_resizing) == "bottom") {
        // resizing with bottom border
        if (g_resize_start.y + g_resize_start.h - diff_y >= board_h) {
            // reached bottom limit: bottom screen border
            dashlet_obj.style.height = (board_h - g_resize_start.y) + "px";
        }
        else if (g_resize_start.h - diff_y < min_h) {
            // reached top limit: minimum dashlet height
            dashlet_obj.style.height = min_h + "px";
        }
        else {
            // normal resize step
            dashlet_obj.style.height = (g_resize_start.h - diff_y) + "px";
        }
    }

    // Calculates new data for the internal coord structure
    calculate_relative_dashlet_coords(nr);

    // Redo dynamic sizing and rendering
    size_dashlets();
}

function resize_dashlet_stop(event) {
    if (!event)
        event = window.event;

    if (!g_resizing)
        return true;

    var dashlet_obj = g_resizing.parentNode.parentNode;
    var nr = parseInt(dashlet_obj.id.replace("dashlet_", ""));
    edit_visualize(dashlet_obj, false);
    g_resizing = false;

    dashlet_resized(nr, dashlet_obj);
    persist_dashlet_pos(nr);
    return false;
}

function dashlet_resized(nr, dashlet_obj) {
    if (typeof reload_on_resize[nr] != "undefined") {
        var base_url = reload_on_resize[nr];
        var iframe = document.getElementById("dashlet_iframe_" + nr);
        iframe.src = base_url + "&width=" + dashlet_obj.clientWidth
                              + "&height=" + dashlet_obj.clientHeight;
    }

    if (typeof dashboard_properties.on_resize_dashlets[nr] != "undefined") {
        dashboard_properties.on_resize_dashlets[nr]();
    }
}

export function has_canvas_support() {
    return document.createElement("canvas").getContext;
}

/*
 * Register the global event handlers, used for dragging of dashlets,
 * dialog control and resizing of dashlets
 */
export function register_event_handlers() {
    utils.add_event_handler("mousemove", function(e) {
        return drag_dashlet(e) && resize_dashlet(e);
    });
    utils.add_event_handler("mousedown", function(e) {
        return drag_dashlet_start(e) && resize_dashlet_start(e);
    });
    utils.add_event_handler("mouseup", function(e) {
        return drag_dashlet_stop(e) && resize_dashlet_stop(e);
    });

    // Totally disable the context menu for all dashboards
    utils.add_event_handler("contextmenu", function(e) {
        utils.prevent_default_events(e);
        return false;
    });
}
